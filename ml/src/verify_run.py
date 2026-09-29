"""Independent artifact audit using stdlib arithmetic, not engine functions."""
import argparse,csv,hashlib,json,math,statistics
from pathlib import Path

def load(p):
    def reject(v):raise ValueError('Nonfinite JSON '+v)
    return json.loads(p.read_text(encoding='utf-8-sig'),parse_constant=reject)

def verify(run):
    manifest=load(run/'manifest.json');assert manifest['status']=='completed'
    hashes={}
    for name,meta in manifest['artifacts'].items():
        digest=hashlib.sha256((run/name).read_bytes()).hexdigest()
        assert digest==meta['sha256'],name
        hashes[name]=True
    rows=[json.loads(l) for l in (run/'session_intelligence_results.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len({r['session_id'] for r in rows})==len(rows)
    raw={r['session_id']:r for r in csv.DictReader(open(manifest['inputs']['cognitive_results']['path'],encoding='utf-8'))}
    groups={};mismatches=[]
    for r in rows:
        assert r['current_performance']['accuracy']==float(raw[r['session_id']]['accuracy_rate'])
        for scope,key in [('per_domain',(r['user_id'],r['cognitive_domain'])),('cross_domain',(r['user_id'],))]:
            group=groups.setdefault((scope,key),[])
            prior=[x['current_performance']['accuracy'] for x in group if x['index_time']<r['index_time']]
            z=None
            if len(prior)>=3:
                median=statistics.median(prior);scale=1.4826*statistics.median(abs(v-median) for v in prior)
                if scale>=1e-8:z=(r['current_performance']['accuracy']-median)/scale
            saved=r['deviation'][scope]
            if (z is None)!=(saved is None) or z is not None and not math.isclose(z,saved,rel_tol=1e-10,abs_tol=1e-10):mismatches.append(r['session_id'])
            assert r['baselines'][scope]['n_valid']==len(prior)
            group.append(r)
    assert not mismatches,mismatches[:5]
    aligned=list(csv.DictReader(open(run/'ground_truth_session_alignment.csv',encoding='utf-8')))
    reported=load(run/'evaluation_results.json');count_checks={}
    cols={'per_domain':'per_domain_state','cross_domain':'cross_domain_state','hybrid':'hybrid_state','hybrid_persistent':'hybrid_state_persistent','adjusted':'adjusted_state','rt':'rt_state'}
    for strategy,col in cols.items():
        eligible=[r for r in aligned if r['trajectory_type'] in ('stable_pattern','temporary_change','gradual_change')]
        for kind,a in [('all',eligible),('evaluable',[r for r in eligible if r[col]!='insufficient_data'])]:
            counts=dict(TP=0,TN=0,FP=0,FN=0)
            for r in a:
                true=r['trajectory_type']!='stable_pattern';pred=r[col] in ('temporary_change','gradual_change','persistent_change')
                counts['TP' if true and pred else 'FN' if true else 'FP' if pred else 'TN']+=1
            rep=reported[strategy] if kind=='all' else reported[strategy]['evaluable']
            assert all(rep[k]==v for k,v in counts.items()),(strategy,kind)
            if kind=='all':
                assert sum(reported[strategy]['false_negative_reasons'].values())==counts['FN']
                assert all(n>=0 for n in reported[strategy]['false_negative_reasons'].values())
            count_checks[strategy+'_'+kind]=counts
    return dict(passed=True,run_id=run.name,records=len(rows),baseline_mismatches=len(mismatches),artifact_hashes_verified=len(hashes),confusion_matrices=count_checks)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('run');args=parser.parse_args()
    print(json.dumps(verify(Path(args.run)),indent=2))
