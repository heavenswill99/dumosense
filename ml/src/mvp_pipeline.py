"""Auditable local ML worker. No database writes, network listeners, or alert delivery."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import traceback
import warnings
import numpy as np
import pandas as pd
from engine_v3 import (CONFIG, VERSION, ROOT, POSITIVE, TRUTH, build_master_table,
                       compute_baseline_sequence, audit_temporal_leakage,
                       apply_persistence_filter_user_aware, evaluate_v3, metrics, fit_mixedlm)

STRATEGIES = {'per_domain':'per_domain_state', 'cross_domain':'cross_domain_state',
              'hybrid':'hybrid_state', 'hybrid_persistent':'hybrid_state_persistent',
              'adjusted':'adjusted_state', 'rt':'rt_state'}

def clean(value):
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [clean(v) for v in value]
    if isinstance(value, (np.integer, np.bool_)):
        return value.item()
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else None
    if value is pd.NaT or value is pd.NA:
        return None
    if isinstance(value, (datetime, pd.Timestamp)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    return value

def write_json(path, obj):
    path = Path(path)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(clean(obj), indent=2, allow_nan=False), encoding='utf-8')
    os.replace(tmp, path)

def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for b in iter(lambda: stream.read(1024*1024), b''):
            h.update(b)
    return h.hexdigest()

def user_split(uid):
    bucket = int(hashlib.sha256(('mindguard-42-' + str(uid)).encode()).hexdigest()[:8], 16) % 10
    return 'train' if bucket < 6 else 'development' if bucket < 8 else 'test'

def state(z, threshold):
    return 'insufficient_data' if z is None or not np.isfinite(z) else 'temporary_change' if abs(z) >= threshold else 'stable_pattern'

def baseline_columns(cr, group_cols, value_col, prefix, config):
    baselines = [None] * len(cr)
    values = cr[value_col].to_numpy(dtype=float)
    times = cr.index_time.to_numpy(dtype='datetime64[ns]')
    for positions in cr.groupby(group_cols, sort=False).indices.values():
        results = compute_baseline_sequence(values[positions], times[positions],
                    config['min_obs_baseline'], config['mad_scale'], config['epsilon'])
        for pos, result in zip(positions, results):
            baselines[int(pos)] = result
    cr[prefix + '_baseline'] = baselines
    cr[prefix + '_z'] = [b['z'] for b in baselines]
    cr[prefix + '_state'] = [state(b['z'], config['z_threshold']) for b in baselines]

def align_truth(cr, gt):
    gt = gt.loc[gt.product_code.eq('MINDGUARD')].copy()
    gt['truth_id'] = ['GT-' + str(i) for i in gt.index]
    for c in ['trajectory_start_date','trajectory_end_date']:
        gt[c] = pd.to_datetime(gt[c], errors='coerce', utc=True)
    if gt[['trajectory_start_date','trajectory_end_date']].isna().any().any() or (gt.trajectory_end_date < gt.trajectory_start_date).any():
        raise ValueError('Invalid ground-truth interval')
    joined = cr.merge(gt[['user_id','truth_id','trajectory_type','trajectory_start_date','trajectory_end_date']], on='user_id', how='inner')
    selected = joined.loc[(joined.started_at >= joined.trajectory_start_date) & (joined.started_at <= joined.trajectory_end_date)].copy()
    counts = selected.groupby('session_id').size()
    ambiguous = set(counts[counts > 1].index)
    selected = selected.loc[~selected.session_id.isin(ambiguous)].copy()
    return selected, dict(matched=len(selected), unmatched=int(len(cr)-len(counts)),
                         ambiguous_sessions=len(ambiguous), excluded_ambiguous_ids=sorted(ambiguous)[:20],
                         label_contract='User-level interval labels at session start; onset/direction semantics not independently established')

def align_context(cr, source, label):
    source = source.copy()
    source['recorded_at'] = pd.to_datetime(source.recorded_at, errors='coerce', utc=True)
    invalid = int(source.recorded_at.isna().sum())
    source = source.dropna(subset=['recorded_at'])
    id_col = 'checkin_id' if label == 'wellbeing' else 'context_id'
    source = source.sort_values(['recorded_at',id_col])
    right = source[['user_id','recorded_at',id_col]].rename(columns={'recorded_at':label+'_timestamp',id_col:label+'_id'})
    left = cr[['session_id','user_id','index_time']].sort_values('index_time')
    joined = pd.merge_asof(left, right, by='user_id', left_on='index_time', right_on=label+'_timestamp', direction='backward')
    violations = int((joined[label+'_timestamp'] > joined.index_time).sum())
    return joined, dict(n_checked=len(cr), matched=int(joined[label+'_id'].notna().sum()),
                        invalid_source_timestamps=invalid, violations=violations,
                        usage='Descriptive context only; not a causal adjustment or alert trigger')

def evaluate_all(frame):
    return {s:evaluate_v3(frame, col, s, ('hybrid' if s=='hybrid_persistent' else s)+'_baseline') for s,col in STRATEGIES.items()}

def bootstrap(frame, col, seed=42, iterations=400):
    e = frame.loc[frame.trajectory_type.isin(TRUTH)].copy()
    if e.empty:
        return dict(status='unavailable', reason='No eligible labelled rows')
    aggregates=[]
    for _,g in e.groupby('user_id'):
        m=metrics(g.trajectory_type.isin(POSITIVE),g[col].isin(POSITIVE))
        aggregates.append([m[k] for k in ['TP','TN','FP','FN']])
    a=np.asarray(aggregates); rng=np.random.default_rng(seed); values=[]
    for _ in range(iterations):
        tp,tn,fp,fn=a[rng.integers(0,len(a),len(a))].sum(axis=0)
        if tp+fn and tn+fp:
            values.append([tp/(tp+fn),tn/(tn+fp),(tp/(tp+fn)+tn/(tn+fp))/2])
    return dict(method='percentile bootstrap resampling users with all their sessions', iterations=iterations,
                users=len(a), intervals_95={k:np.quantile(np.asarray(values)[:,i],[.025,.975]).tolist()
                for i,k in enumerate(['sensitivity','specificity','balanced_accuracy'])} if values else {})

def model_analysis(cr, run, warn):
    from threadpoolctl import threadpool_limits
    results={}
    with threadpool_limits(limits=1):
        for name in ['accuracy','rt']:
            data=cr.copy()
            formula='accuracy_rate ~ time_days + C(difficulty_level)' if name=='accuracy' else 'np.log(median_reaction_time_ms) ~ time_days + C(difficulty_level)'
            attempts=[]
            for optimizer in ['lbfgs','bfgs']:
                caught=[]
                try:
                    with warnings.catch_warnings(record=True) as caught:
                        warnings.simplefilter('always')
                        result,pred=fit_mixedlm(data,formula=formula,return_predictions=True,optimizer=optimizer)
                    attempts.append(dict(optimizer=optimizer,status='converged'))
                    results[name]=dict(status='fitted',outcome='accuracy' if name=='accuracy' else 'log median RT',attempts=attempts,**result)
                    pred.to_csv(run/(name+'_model_predictions.csv'),index=False)
                    break
                except Exception as exc:
                    attempts.append(dict(optimizer=optimizer,status='failed',error=str(exc)))
                    results[name]=dict(status='failed',error=str(exc),attempts=attempts)
                finally:
                    warn.extend(dict(stage=name+'_MixedLM_'+optimizer,category=w.category.__name__,message=str(w.message)) for w in caught)
        import statsmodels.formula.api as smf
        data=cr.copy(); data['log_rt']=np.log(data.median_reaction_time_ms)
        data['time_days']=(data.started_at-data.started_at.min()).dt.total_seconds()/86400
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            ols=smf.ols('log_rt ~ time_days + C(difficulty_level) + C(cognitive_domain)', data=data).fit(cov_type='cluster',cov_kwds={'groups':data.user_id})
        warn.extend(dict(stage='rt_clustered_OLS',category=w.category.__name__,message=str(w.message)) for w in caught)
        results['rt_clustered_ols']=dict(status='fitted',n_observations=int(ols.nobs),r_squared=float(ols.rsquared),
             coefficients=ols.params.to_dict(),std_errors=ols.bse.to_dict(),confidence_intervals=ols.conf_int().T.to_dict('list'))
        import statsmodels.api as sm
        import patsy
        design=patsy.dmatrix('time_days + C(difficulty_level) + C(cognitive_domain)',data,return_type='dataframe')
        counts=np.column_stack([data.correct_responses,data.total_trials-data.correct_responses])
        if (counts<0).any() or (data.total_trials<=0).any():raise ValueError('Invalid trial counts')
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            binomial=sm.GLM(counts,design,family=sm.families.Binomial()).fit(cov_type='cluster',cov_kwds={'groups':data.user_id})
        warn.extend(dict(stage='accuracy_binomial',category=w.category.__name__,message=str(w.message)) for w in caught)
        results['accuracy_binomial_clustered']=dict(status='fitted',converged=bool(binomial.converged),
            n_observations=int(binomial.nobs),formula='trial successes/failures ~ time_days + difficulty + domain',
            coefficients=binomial.params.to_dict(),std_errors=binomial.bse.to_dict(),
            confidence_intervals=binomial.conf_int().T.to_dict('list'),deviance=float(binomial.deviance),
            note='Bounded binomial mean, user-clustered SE, descriptive in-sample model')
        results['rt_selection']=dict(model='rt_mixedlm' if results['rt']['status']=='fitted' else 'rt_clustered_ols',
            reason='Converged finite fit with all optimizer attempts retained' if results['rt']['status']=='fitted' else 'MixedLM failed; user-clustered OLS remains available')
    return results

def strict_export(cr, context, run, run_id):
    lookup=context.set_index('session_id').to_dict('index')
    path=run/'session_intelligence_results.jsonl'
    with path.open('w',encoding='utf-8') as f:
        for r in cr.to_dict('records'):
            b=r['hybrid_baseline']; z=b['z']
            item=dict(schema_version='1.0',model_version=VERSION,run_id=run_id,
                session_id=r['session_id'],user_id=r['user_id'],cognitive_domain=r['cognitive_domain'],
                index_time=r['index_time'], started_at=r['started_at'],
                current_performance=dict(accuracy=r['accuracy_rate'],median_rt_ms=r['median_reaction_time_ms']),
                data_sufficiency=dict(baseline_available=z is not None,baseline_n=b['n_valid'],
                     baseline_source=r['hybrid_source'],reason=b['reason']),
                baseline=b, baselines={p:r[p+'_baseline'] for p in ['per_domain','cross_domain','rt','adjusted']},
                deviation={p:r[p+'_z'] for p in ['per_domain','cross_domain','hybrid','adjusted','rt']},
                change={s:r[c] for s,c in STRATEGIES.items()},context=lookup[r['session_id']],
                split=r['split'],release_status='internal_validation_only',
                input_period=dict(history_end=b['ts_max_prior'],current_result=r['index_time']))
            f.write(json.dumps(clean(item),allow_nan=False)+'\n')
    return path

def verify_export(path, cr):
    expected=cr.set_index('session_id'); seen=set(); failures=[]; count=0
    def reject(x):
        raise ValueError('Nonfinite JSON constant: '+x)
    with path.open(encoding='utf-8') as f:
        for line in f:
            r=json.loads(line,parse_constant=reject); count+=1; sid=r['session_id']
            if sid in seen: failures.append('duplicate session '+sid)
            seen.add(sid); b=r['baseline']; av=r['data_sufficiency']['baseline_available']
            if av != (b['z'] is not None) or av and b['n_valid']<3: failures.append('invalid availability '+sid)
            if av == (r['change']['hybrid']=='insufficient_data'): failures.append('state/availability '+sid)
            if r['current_performance']['accuracy']!=expected.at[sid,'accuracy_rate']: failures.append('accuracy '+sid)
            if b['ts_max_prior'] and pd.Timestamp(b['ts_max_prior'])>=pd.Timestamp(r['index_time']): failures.append('future baseline '+sid)
    if seen != set(expected.index): failures.append('session set mismatch')
    return dict(records=count,passed=not failures,failures=failures[:20])

def surrogate_analysis(cr, run, warn):
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, confusion_matrix
    features=['per_domain_z','cross_domain_z','rt_z']
    available=cr.hybrid_state.ne('insufficient_data')
    train=cr.loc[available & cr.split.eq('train')]; test=cr.loc[available & cr.split.eq('test')]
    if train.empty or test.empty:
        return dict(status='unavailable',reason='No evaluable train or test sessions')
    X=train[features].fillna(0); Y=train.hybrid_state; T=test[features].fillna(0)
    model=RandomForestClassifier(n_estimators=60,max_depth=8,min_samples_leaf=5,random_state=42,n_jobs=1)
    model.fit(X,Y); pred=model.predict(T)
    assert not set(train.user_id)&set(test.user_id)
    result=dict(status='fitted',purpose='Engine fidelity only; decision features are deliberately included',
      features=features,train_rows=len(train),test_rows=len(test),train_users=train.user_id.nunique(),test_users=test.user_id.nunique(),
      user_overlap=0,accuracy=accuracy_score(test.hybrid_state,pred),macro_f1=f1_score(test.hybrid_state,pred,average='macro'),
      balanced_accuracy=balanced_accuracy_score(test.hybrid_state,pred),classes=model.classes_.tolist(),
      confusion_matrix=confusion_matrix(test.hybrid_state,pred,labels=model.classes_).tolist(),
      majority_baseline=float(test.hybrid_state.eq(Y.mode().iloc[0]).mean()))
    ablations={}
    for removed in [['per_domain_z'],['cross_domain_z'],['per_domain_z','cross_domain_z']]:
        cols=[c for c in features if c not in removed]
        m=RandomForestClassifier(n_estimators=40,max_depth=8,min_samples_leaf=5,random_state=42,n_jobs=1).fit(X[cols],Y)
        ablations['without_'+','.join(removed)]=accuracy_score(test.hybrid_state,m.predict(T[cols]))
    result['ablation_accuracy']=ablations
    try:
        import shap
        sample=T.iloc[:200]; explanation=shap.TreeExplainer(model)(sample)
        arr=explanation.values
        importance=np.mean(np.abs(arr),axis=tuple(i for i in range(arr.ndim) if i!=1))
        write_json(run/'shap_values.json',dict(session_ids=test.session_id.iloc[:200].tolist(),features=features,
                  values=arr,base_values=explanation.base_values,classes=model.classes_.tolist()))
        result['shap']=dict(status='computed',explained_rows=len(sample),mean_abs_values=dict(zip(features,importance)))
    except Exception as exc:
        result['shap']=dict(status='failed',error=str(exc))
        warn.append(dict(stage='shap',category=type(exc).__name__,message=str(exc)))
    return result

def generate_plots(cr,evaluation,run):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from scipy.stats import probplot
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    names=list(evaluation); axes[0].barh(names,[cr[STRATEGIES[s]].ne('insufficient_data').mean() for s in names])
    axes[0].set(xlim=(0,1),xlabel='Fraction of sessions with a score',title='Baseline coverage')
    axes[1].barh(names,[evaluation[s]['evaluable']['balanced_accuracy'] or 0 for s in names])
    axes[1].axvline(.5,color='red',linestyle='--');axes[1].set(xlim=(0,1),xlabel='Balanced accuracy',title='Retrospective evaluable cases')
    fig.suptitle(run.name); fig.tight_layout();fig.savefig(run/'coverage_performance.png',dpi=140);plt.close(fig)
    for outcome in ['accuracy','rt']:
        path=run/(outcome+'_model_predictions.csv')
        if not path.exists():continue
        p=pd.read_csv(path);fig,axes=plt.subplots(1,2,figsize=(10,4))
        axes[0].scatter(p.fitted,p.residual,s=2,alpha=.1);axes[0].axhline(0,color='red')
        axes[0].set(xlabel='Actual model fitted value',ylabel='Actual residual',title=outcome+' in-sample fit')
        probplot(p.residual,plot=axes[1]);fig.suptitle(run.name);fig.tight_layout();fig.savefig(run/(outcome+'_diagnostics.png'),dpi=140);plt.close(fig)

def baseline_tradeoff(cr, config):
    output={}
    for prefix,value in [('per_domain','accuracy_rate'),('cross_domain','accuracy_rate'),('adjusted','adjusted_accuracy'),('rt','negative_log_rt')]:
        baselines=cr[prefix+'_baseline'].tolist()
        output[prefix]=[]
        for n in [2,3,4,5]:
            eligible=np.asarray([b['n_valid']>=n and b['rs'] is not None and b['rs']>=config['epsilon'] for b in baselines]) & np.isfinite(cr[value].to_numpy())
            output[prefix].append(dict(minimum_prior=n,scorable_sessions=int(eligible.sum()),total_sessions=len(cr),coverage=float(eligible.mean())))
    stability=[]
    sequences=[g.accuracy_rate.to_numpy() for _,g in cr.groupby(['user_id','cognitive_domain'])]
    for n in [2,3,4,5]:
        changes=[abs(float(np.median(v[:n+1]))-float(np.median(v[:n]))) for v in sequences if len(v)>n]
        stability.append(dict(n=n,trajectories=len(changes),median_absolute_baseline_change=float(np.median(changes)) if changes else None))
    return dict(coverage=output,stability=stability,definition='Change between median of first n and first n+1 chronologically available same-domain observations',selection='Minimum three is an engineering configuration, not proven optimal')

def generate_report(summary,run):
    text=['# Dumosense ML worker validation',f"Run: {summary['run_id']}",
      'Scope: nonclinical retrospective synthetic-data analysis. No patient-facing alert release is approved by this run.',
      '## Dataset',json.dumps(summary['dataset'],indent=2),
      '## Full retrospective evaluation',
      'Abstentions count as no alert in the all-labelled view. Conditional metrics exclude abstentions.',
      '| Strategy | Coverage | Sensitivity | Conditional sensitivity | Conditional FPR | Conditional balanced accuracy |',
      '|---|---:|---:|---:|---:|---:|']
    fmt=lambda x:'Unavailable' if x is None else f'{100*x:.2f}%'
    for s,e in summary['evaluation'].items():
        v=e['evaluable'];text.append(f"| {s} | {fmt(e['coverage'])} | {fmt(e['sensitivity'])} | {fmt(v['sensitivity'])} | {fmt(v['FPR'])} | {fmt(v['balanced_accuracy'])} |")
    text+=['## Selected research configuration',json.dumps(clean(summary['selection']),indent=2),
       '## Internal held-out results',json.dumps(clean(summary['heldout']),indent=2),
       'The dataset has informed prior development. This split is internal retrospective validation, not untouched external validation.',
       '## False-negative attribution',json.dumps({s:e['false_negative_reasons'] for s,e in summary['evaluation'].items()},indent=2),
       '## Model fits',json.dumps(clean(summary['models']),indent=2),
       'RMSE/MAE are in-sample. Fixed-effect variance uses ddof=0. REML AIC/BIC are unavailable by design.',
       '## Verification',json.dumps(clean(summary['verification']),indent=2),
       '## Release assessment',json.dumps(clean(summary['release']),indent=2),
       '## Limitations',
       '- Truth labels are user-level interval annotations; event onset, direction and recovery truth are not independently established.',
       '- No clinical or external validation. The held-out sample must not be used for repeated tuning.',
       '- Raw cross-domain pooling is a comparison, not an established personal cognitive baseline.',
       '- Context is descriptive, never a causal explanation. Surrogate SHAP measures fidelity only.',
       '- Gradual change and recovery are not claimed by this point-deviation worker.',
       '- Authenticated backend, consent enforcement at request time, delivery, monitoring, and deployment tests remain integration requirements.',
       'See manifest.json for source/input/artifact hashes, test_results.json for executed tests, and captured_warnings.json for warnings.']
    (run/'STATISTICAL_MODEL_REPORT.md').write_text('\n\n'.join(text)+'\n',encoding='utf-8')

def run_pipeline(args):
    config=dict(CONFIG); config['data_dir']=Path(args.data_dir);config['validation_dir']=Path(args.validation_dir)
    out=Path(args.output_dir);out.mkdir(parents=True,exist_ok=True)
    run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ');run=out/'runs'/run_id;run.mkdir(parents=True)
    manifest=dict(run_id=run_id,status='running',started_at=datetime.now(timezone.utc).isoformat(),version=VERSION)
    write_json(run/'manifest.json',manifest);warn=[];start=time.monotonic()
    def log(message):
        line=datetime.now(timezone.utc).isoformat()+' '+message
        print(line,flush=True)
        with (run/'execution_log.txt').open('a',encoding='utf-8') as f:f.write(line+'\n')
    previous_warning_handler=warnings.showwarning
    def record_warning(message,category,filename,lineno,file=None,line=None):
        warn.append(dict(stage='pipeline',category=category.__name__,message=str(message),filename=filename,line=lineno))
        log('WARNING '+category.__name__+': '+str(message))
    warnings.showwarning=record_warning
    try:
        log('Running regression tests before data processing')
        tests=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(ROOT/'tests'),'-p','test_mvp*.py','-v'],capture_output=True,text=True,encoding='utf-8',errors='replace',env={**os.environ,'PYTHONPATH':str(ROOT/'src'),'PYTHONDONTWRITEBYTECODE':'1'})
        write_json(run/'test_results.json',dict(exit_code=tests.returncode,stdout=tests.stdout,stderr=tests.stderr))
        if tests.returncode:raise RuntimeError('Regression tests failed; see test_results.json')
        tables=['cognitive_results','assessment_sessions','assessment_types','users','user_profiles','context_records','wellbeing_checkins']
        paths={n:config['data_dir']/(n+'.csv') for n in tables};paths['synthetic_ground_truth']=config['validation_dir']/'synthetic_ground_truth.csv'
        log('Loading and checking inputs')
        data={n:pd.read_csv(p) for n,p in paths.items()}
        manifest['inputs']={n:dict(path=str(p),sha256=sha(p),rows=len(data[n])) for n,p in paths.items()}
        manifest['sources']={str(p.relative_to(ROOT)):sha(p) for folder in ['src','tests'] for p in (ROOT/folder).glob('*.py')}
        manifest['dependencies']={n:importlib.metadata.version(n) for n in ['numpy','pandas','scipy','statsmodels','scikit-learn','matplotlib']}
        manifest['python']=platform.python_version();write_json(run/'config.json',config)
        cr=build_master_table(data);cr['split']=cr.user_id.map(user_split)
        log(f'Validated {len(cr)} sessions from {cr.user_id.nunique()} users')
        cutoff=cr.index_time.quantile(.60)
        train=cr.loc[cr.split.eq('train') & cr.index_time.lt(cutoff)]
        reference=train.groupby(['cognitive_domain','difficulty_level']).accuracy_rate.agg(['mean','std','size'])
        reference.loc[(reference['size']<20)|(reference['std']<=1e-8),['mean','std']]=np.nan
        reference.to_csv(run/'training_reference.csv')
        joined=cr.join(reference[['mean','std']],on=['cognitive_domain','difficulty_level'])
        cr['adjusted_accuracy']=(joined.accuracy_rate-joined['mean'])/joined['std']
        cr['negative_log_rt']=-np.log(cr.median_reaction_time_ms)
        for groups,value,prefix in [(['user_id','cognitive_domain'],'accuracy_rate','per_domain'),(['user_id'],'accuracy_rate','cross_domain'),(['user_id'],'adjusted_accuracy','adjusted'),(['user_id','cognitive_domain'],'negative_log_rt','rt')]:
            log('Computing '+prefix+' baselines');baseline_columns(cr,groups,value,prefix,config)
        cr['hybrid_baseline']=[p if p['z'] is not None else c for p,c in zip(cr.per_domain_baseline,cr.cross_domain_baseline)]
        cr['hybrid_z']=[b['z'] for b in cr.hybrid_baseline]
        cr['hybrid_source']=['per_domain' if p['z'] is not None else 'cross_domain' if c['z'] is not None else 'none' for p,c in zip(cr.per_domain_baseline,cr.cross_domain_baseline)]
        cr['hybrid_state']=[state(b['z'],config['z_threshold']) for b in cr.hybrid_baseline]
        cr['hybrid_state_persistent']=apply_persistence_filter_user_aware(cr.hybrid_state.tolist(),cr.user_id.tolist(),config['persistence_required'])
        audit={p:audit_temporal_leakage(cr,p+'_baseline','index_time') for p in ['per_domain','cross_domain','adjusted','rt']}
        if any(v['n_violations'] or v['missing_provenance'] or v['n_excluded'] for v in audit.values()):raise ValueError('Baseline provenance audit failed')
        context=cr[['session_id']].copy();context_audit={}
        for source,label in [('context_records','context'),('wellbeing_checkins','wellbeing')]:
            aligned,a=align_context(cr,data[source],label);context_audit[label]=a
            context=context.merge(aligned[['session_id',label+'_timestamp',label+'_id']],on='session_id',validate='one_to_one')
        log('Aligning labels and computing evaluation')
        ev,alignment=align_truth(cr,data['synthetic_ground_truth']);evaluation=evaluate_all(ev)
        ev.drop(columns=[c for c in ev if c.endswith('_baseline')]).to_csv(run/'ground_truth_session_alignment.csv',index=False)
        development=ev.loc[ev.split.eq('development') & ev.index_time.ge(cutoff)].copy()
        test=ev.loc[ev.split.eq('test') & ev.index_time.ge(cutoff)].copy()
        candidates=[]
        for s in ['per_domain','hybrid','adjusted','rt']:
            for t in [1.5,2.,2.5,3.]:
                d=development.copy();d['candidate']=[state(z,t) for z in d[s+'_z']]
                m=evaluate_v3(d,'candidate',s,s+'_baseline')
                candidates.append(dict(strategy=s,threshold=t,balanced_accuracy=m['balanced_accuracy'],metrics=m))
        valid=[c for c in candidates if c['balanced_accuracy'] is not None]
        if not valid:raise ValueError('Insufficient development labels for selection')
        selected=max(valid,key=lambda c:(c['balanced_accuracy'],c['threshold']))
        test['selected_state']=[state(z,selected['threshold']) for z in test[selected['strategy']+'_z']]
        heldout=evaluate_v3(test,'selected_state',selected['strategy'],selected['strategy']+'_baseline')
        heldout['confidence']=bootstrap(test,'selected_state');heldout['always_no_alert']=metrics(test.loc[test.trajectory_type.isin(TRUTH),'trajectory_type'].isin(POSITIVE),np.zeros(test.trajectory_type.isin(TRUTH).sum(),bool))
        selected={k:v for k,v in selected.items() if k!='metrics'}
        selected.update(cutoff=cutoff,split='SHA256 user groups 60/20/20; development/test evaluation after frozen training cutoff',target='any accuracy or RT deviation; not diagnosis')
        write_json(run/'development_candidates.json',candidates);write_json(run/'split_assignments.json',cr[['user_id','split']].drop_duplicates().to_dict('records'))
        test.drop(columns=[c for c in test if c.endswith('_baseline')]).to_csv(run/'heldout_predictions.csv',index=False)
        write_json(run/'evaluation_results.json',evaluation);write_json(run/'heldout_results.json',heldout)
        log('Fitting actual accuracy and RT models')
        models=model_analysis(cr,run,warn);write_json(run/'model_results.json',models)
        log('Computing surrogate fidelity and SHAP')
        surrogate=surrogate_analysis(cr.loc[(cr.split.eq('train') & cr.index_time.lt(cutoff)) | (cr.split.eq('test') & cr.index_time.ge(cutoff))],run,warn)
        write_json(run/'surrogate_results.json',surrogate)
        profile=data['user_profiles'][['user_id','age_group','sex']]
        test_profiles=test.merge(profile,on='user_id',how='left',validate='many_to_one');fairness={}
        for col in ['age_group','sex']:
            fairness[col]={str(g):dict(evaluation=evaluate_v3(frame,'selected_state',selected['strategy'],selected['strategy']+'_baseline'),confidence=bootstrap(frame,'selected_state',iterations=200)) for g,frame in test_profiles.groupby(col,dropna=False)}
        write_json(run/'subgroup_results.json',fairness)
        log('Exporting and independently checking session records')
        path=strict_export(cr,context,run,run_id);verification=verify_export(path,cr)
        if not verification['passed']:raise ValueError('Session export verification failed')
        counts=cr.groupby(['user_id','cognitive_domain']).size()
        density=dict(n_user_domain_combinations=len(counts),median_sessions_per_user_domain=float(counts.median()),
            users_with_cognitive_data=cr.user_id.nunique(),median_sessions_per_user=float(cr.groupby('user_id').size().median()),
            trajectory_counts={f'>={n}':int((counts>=n).sum()) for n in range(1,7)})
        availability={p:dict(available=int(cr[p+'_state'].ne('insufficient_data').sum()),total=len(cr),reasons=dict(Counter(b['reason'] for b in cr[p+'_baseline'] if b['z'] is None))) for p in ['per_domain','cross_domain','hybrid','rt','adjusted']}
        release=dict(software_checks='passed',synthetic_worker='verified',patient_facing_alerts='blocked',
             reasons=['Synthetic data only; external validity unestablished','Authenticated backend and live consent enforcement not implemented in this ML repository','Near-chance historical discrimination; no agreed deployment acceptance thresholds'],
             intended_use='Offline research and backend integration testing; no automatic alert delivery')
        summary=dict(run_id=run_id,pipeline_version=VERSION,dataset=dict(registered_users=len(data['users']),completed_sessions=len(cr),users_with_cognitive_data=cr.user_id.nunique()),
            density=density,availability=availability,evaluation=evaluation,heldout=heldout,selection=selected,models=models,
            temporal_leakage=audit,context_audit=context_audit,alignment=alignment,verification=verification,release=release)
        write_json(run/'baseline_tradeoff.json',baseline_tradeoff(cr,config))
        write_json(run/'longitudinal_density.json',density);write_json(run/'statistical_models_results.json',summary)
        generate_plots(cr,evaluation,run);generate_report(summary,run)
        write_json(run/'captured_warnings.json',warn)
        manifest.update(status='completed',finished_at=datetime.now(timezone.utc).isoformat(),seconds=time.monotonic()-start)
        log('Completed: calculations verified; patient-facing alert release remains blocked')
        manifest['artifacts']={p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in run.iterdir() if p.is_file() and p.name!='manifest.json'}
        write_json(run/'manifest.json',manifest)
        write_json(out/'latest_successful_run.json',dict(run_id=run_id,path=str(run),manifest_sha256=sha(run/'manifest.json'),release_status='internal_validation_only'))
        return 0
    except BaseException as exc:
        log('FAILED: '+str(exc));log(traceback.format_exc());write_json(run/'captured_warnings.json',warn)
        manifest.update(status='failed',error=str(exc),finished_at=datetime.now(timezone.utc).isoformat())
        write_json(run/'manifest.json',manifest)
        return 1
    finally:
        warnings.showwarning=previous_warning_handler

def cli():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir',default=str(CONFIG['data_dir']))
    parser.add_argument('--validation-dir',default=str(CONFIG['validation_dir']))
    parser.add_argument('--output-dir',default=str(CONFIG['output_dir']))
    try:
        return run_pipeline(parser.parse_args())
    except OSError as exc:
        print('Cannot initialize run directory: '+str(exc),file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(cli())
