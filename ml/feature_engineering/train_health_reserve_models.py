"""Point-in-time, user-disjoint synthetic Health Reserve model benchmark."""
from __future__ import annotations
import argparse, hashlib, json, os, re, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
sys.path.insert(0, os.environ.get('DUMOSENSE_ML_DEPS', str(ROOT.parent / '.deps')))
import joblib, numpy as np, pandas as pd, sklearn
from catboost import CatBoostClassifier, CatBoostRegressor
from lightgbm import LGBMClassifier, LGBMRegressor
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import IsolationForest, RandomForestClassifier, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (accuracy_score, average_precision_score, balanced_accuracy_score,
 brier_score_loss, confusion_matrix, f1_score, log_loss, mean_absolute_error,
 mean_squared_error, precision_score, r2_score, recall_score, roc_auc_score)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

SEED=42
CAT_COLS=['income_type','employment_status','currency_code','country_code','region_code','plan_frequency','cashflow_coverage','latest_healthcare_coverage_status','latest_reserve_status']
TABLES=['health_reserve_assessments.csv','financial_profiles.csv','financial_transactions.csv','family_dependents.csv',
 'health_reserve_goals.csv','health_reserve_activity.csv','healthcare_exposure_items.csv',
 'health_reserve_contribution_plans.csv','health_reserve_affordability_outcomes.csv']
EXPOSURE_CATS=['maternity_care','emergency_care','diagnostics','medicines','specialist_care','hospital_care','other']
TX_CATS=['healthcare_specialist_consultation','healthcare_diagnostic_laboratory','healthcare_pharmacy_medicines','healthcare_emergency_consultation']

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()
def dt(s): return pd.to_datetime(s,errors='coerce')
def num(s): return pd.to_numeric(s,errors='coerce')
def split_user(u):
 b=int(hashlib.sha256(('hr-point-in-time-v1-'+str(u)).encode()).hexdigest()[:8],16)%10
 return 'train' if b<6 else ('development' if b<8 else 'test')
def load_tables(root):
 d={}
 for f in TABLES:
  sep=';' if f=='health_reserve_activity.csv' else ','
  p=root/f
  if not p.exists(): raise FileNotFoundError(f'Required input missing: {p}')
  d[f.removesuffix('.csv')]=pd.read_csv(p,sep=sep)
 return d

def engineer(t):
 print('validating and joining input tables',flush=True)
 assessments,profiles,tx,deps,goals,activity,exposures,plans,outcomes=[t[k] for k in [
  'health_reserve_assessments','financial_profiles','financial_transactions','family_dependents','health_reserve_goals',
  'health_reserve_activity','healthcare_exposure_items','health_reserve_contribution_plans','health_reserve_affordability_outcomes']]
 for df,key in [(profiles,'financial_profile_id'),(plans,'plan_id'),(outcomes,'outcome_id')]:
  if df[key].duplicated().any(): raise ValueError(f'duplicate key {key}')
 if outcomes.groupby('plan_id').size().ne(3).any(): raise ValueError('Each plan must have exactly three follow-up records')
 p=plans.copy(); p['choice_timestamp']=dt(p.choice_timestamp)
 print('parsed choice dates',flush=True)
 p=p.merge(profiles,on=['financial_profile_id','user_id'],how='left',validate='one_to_one',suffixes=('','_profile'))
 # Retain only selected linked profiles that were effective and recorded by choice. Do not backfill with later profile snapshots.
 effective=dt(p.effective_from).le(p.choice_timestamp)
 recorded=dt(p.recorded_at).le(p.choice_timestamp)
 ends=dt(p.effective_to)
 active=ends.isna()|ends.gt(p.choice_timestamp)
 p.loc[~(effective&recorded&active),'financial_profile_id']=np.nan
 print('validated profile snapshots',flush=True)
 # The direct plan/profile link is the only permissible profile snapshot; invalid snapshots are made unavailable.
 numeric_profile=['monthly_income','essential_monthly_expenses','debt_repayments','other_monthly_obligations','existing_liquid_savings','income_stability_index']
 for c in numeric_profile: p[c]=num(p[c]).where(p.financial_profile_id.notna())
 p['net_monthly_cashflow']=p.monthly_income-p.essential_monthly_expenses-p.debt_repayments-p.other_monthly_obligations
 p['monthly_obligations']=p.essential_monthly_expenses+p.debt_repayments+p.other_monthly_obligations
 p['obligations_to_income_ratio']=p.monthly_obligations/p.monthly_income.replace(0,np.nan)
 p['net_cashflow_to_income_ratio']=p.net_monthly_cashflow/p.monthly_income.replace(0,np.nan)
 p['liquid_savings_months']=p.existing_liquid_savings/p.monthly_obligations.replace(0,np.nan)
 p['selected_contribution']=num(p.user_selected_monthly_contribution)
 p['contribution_to_income_ratio']=p.selected_contribution/p.monthly_income.replace(0,np.nan)
 p['contribution_to_positive_net_cashflow_ratio']=p.selected_contribution/p.net_monthly_cashflow.where(p.net_monthly_cashflow>0)
 p['contribution_to_estimated_surplus_ratio']=p.selected_contribution/num(p.estimated_monthly_surplus).where(num(p.estimated_monthly_surplus)>0)
 p['surplus_after_selected_contribution']=p.net_monthly_cashflow-p.selected_contribution
 # Precompute histories; event time AND knowledge/record time must be <= choice.
 tx=tx.copy(); tx['event_dt']=dt(tx.transaction_date); tx['known_dt']=dt(tx.recorded_at); tx['amount']=num(tx.amount)
 print('parsed transaction history',flush=True)
 act=activity.copy(); act['event_dt']=dt(act.activity_date); act['known_dt']=dt(act.recorded_at); act['amount']=num(act.amount)
 print('parsed reserve activity',flush=True)
 dep=deps.copy(); dep['from_dt']=dt(dep.effective_from); dep['to_dt']=dt(dep.effective_to); dep['known_dt']=dt(dep.recorded_at)
 print('parsed dependents',flush=True)
 goal=goals.copy(); goal['created_dt']=dt(goal.created_at); goal['target_dt']=dt(goal.target_date)
 print('parsed goals',flush=True)
 exp=exposures.copy(); exp['created_dt']=dt(exp.created_at); exp['amount']=num(exp.estimated_amount)
 assessments=assessments.copy(); assessments['assessed_dt']=dt(assessments.assessed_at)
 print('parsed exposures',flush=True)
 print('indexing user histories',flush=True)
 tx_by_user={k:v for k,v in tx.groupby('user_id',sort=False)}
 print('grouped transactions',flush=True)
 act_by_user={k:v for k,v in act.groupby('user_id',sort=False)}
 print('grouped activity',flush=True)
 dep_by_user={k:v for k,v in dep.groupby('user_id',sort=False)}
 print('grouped dependents',flush=True)
 goal_by_user={k:v for k,v in goal.groupby('user_id',sort=False)}
 print('grouped goals',flush=True)
 exp_by_user={k:v for k,v in exp.groupby('user_id',sort=False)}
 assessment_by_user={k:v.sort_values('assessed_dt') for k,v in assessments.groupby('user_id',sort=False)}
 # Attach follow-up outcomes as targets only.
 outcomes=outcomes.copy(); outcomes['review_period_start']=dt(outcomes.review_period_start); outcomes['review_period_end']=dt(outcomes.review_period_end)
 outcomes['reported_contribution']=num(outcomes.reported_contribution)
 agg=outcomes.sort_values('review_period_end').groupby('plan_id').agg(
  followup_count=('outcome_id','size'), statuses=('sustainability_status',lambda s:tuple(s)),
  reported=('reported_contribution',lambda s:tuple(s)), simulated=('observation_status',lambda s:int((s=='simulated').sum()))).reset_index()
 p=p.merge(agg,on='plan_id',how='left',validate='one_to_one')
 p['target_status']=p.statuses.map(lambda s:'unknown' if not isinstance(s,tuple) or any(x in ('unknown','not_observed') for x in s) else ('sustainable' if all(x=='sustainable' for x in s) else 'adjusted_down'))
 p['target_sustainable']=(p.target_status=='sustainable').astype(int)
 def history(row):
  uid=row.user_id; t0=row.choice_timestamp; out={}
  if pd.isna(t0): return out
  txu=tx_by_user.get(uid,tx.iloc[0:0]); actu=act_by_user.get(uid,act.iloc[0:0])
  depu=dep_by_user.get(uid,dep.iloc[0:0]); goalu=goal_by_user.get(uid,goal.iloc[0:0]); expu=exp_by_user.get(uid,exp.iloc[0:0])
  ass=assessment_by_user.get(uid,assessments.iloc[0:0]); ass=ass[ass.assessed_dt.le(t0)]
  out['prior_assessment_count']=len(ass)
  if len(ass):
   latest=ass.iloc[-1]
   for col in ['healthcare_coverage_status','reserve_status']: out[f'latest_{col}']=latest[col]
   for col in ['estimated_healthcare_exposure','emergency_health_resources','monthly_financial_obligations','number_of_dependants','current_preparedness_amount','preparedness_target','preparedness_gap','preparedness_ratio']:
    out[f'latest_{col}']=num(pd.Series([latest[col]])).iloc[0]
   if len(ass)>1:
    first=ass.iloc[0]
    out['preparedness_ratio_change_since_first']=float(latest.preparedness_ratio-first.preparedness_ratio)
    out['healthcare_exposure_change_since_first']=float(latest.estimated_healthcare_exposure-first.estimated_healthcare_exposure)
   else:
    out['preparedness_ratio_change_since_first']=np.nan; out['healthcare_exposure_change_since_first']=np.nan
  else:
   out['latest_healthcare_coverage_status']=np.nan; out['latest_reserve_status']=np.nan
   for col in ['estimated_healthcare_exposure','emergency_health_resources','monthly_financial_obligations','number_of_dependants','current_preparedness_amount','preparedness_target','preparedness_gap','preparedness_ratio']:
    out[f'latest_{col}']=np.nan
   out['preparedness_ratio_change_since_first']=np.nan; out['healthcare_exposure_change_since_first']=np.nan
  for days,tag in [(30,'30d'),(90,'90d')]:
   start=t0-pd.Timedelta(days=days)
   q=txu[txu.event_dt.lt(t0)&txu.known_dt.le(t0)&txu.event_dt.ge(start)]
   inc=q[q.transaction_type.eq('income')]; spend=q[q.transaction_type.eq('expense')]
   out[f'tx_income_total_{tag}']=float(inc.amount.sum()); out[f'tx_income_mean_{tag}']=float(inc.amount.mean()) if len(inc) else np.nan
   out[f'tx_income_std_{tag}']=float(inc.amount.std(ddof=0)) if len(inc) else np.nan; out[f'tx_income_count_{tag}']=len(inc)
   out[f'tx_expense_total_{tag}']=float(spend.amount.sum()); out[f'tx_expense_mean_{tag}']=float(spend.amount.mean()) if len(spend) else np.nan
   out[f'tx_expense_std_{tag}']=float(spend.amount.std(ddof=0)) if len(spend) else np.nan; out[f'tx_expense_count_{tag}']=len(spend)
   out[f'tx_net_amount_{tag}']=float(inc.amount.sum()-spend.amount.sum())
   out[f'tx_recurring_income_share_{tag}']=float(inc.is_recurring.astype(str).str.lower().isin(['true','1']).mean()) if len(inc) else np.nan
   for cat in TX_CATS:
    out[f'tx_{cat}_amount_{tag}']=float(spend.loc[spend.category.eq(cat),'amount'].sum())
  for days,tag in [(30,'30d'),(90,'90d')]:
   start=t0-pd.Timedelta(days=days)
   q=actu[actu.event_dt.lt(t0)&actu.known_dt.le(t0)&actu.event_dt.ge(start)]
   alloc=q[q.activity_type.eq('reported_allocation')]; withdraw=q[q.activity_type.eq('reported_withdrawal')]
   out[f'activity_allocation_total_{tag}']=float(alloc.amount.sum()); out[f'activity_withdrawal_total_{tag}']=float(withdraw.amount.sum())
   out[f'activity_count_{tag}']=len(q); out[f'activity_amount_mean_{tag}']=float(q.amount.mean()) if len(q) else np.nan
   out[f'activity_net_{tag}']=float(alloc.amount.sum()-withdraw.amount.sum())
  active_dep=depu[depu.from_dt.le(t0)&(depu.to_dt.isna()|depu.to_dt.gt(t0))&depu.known_dt.le(t0)]
  out['active_dependent_count']=len(active_dep)
  out['dependent_full_count']=int(active_dep.financial_dependency_level.eq('full').sum()); out['dependent_partial_count']=int(active_dep.financial_dependency_level.eq('partial').sum())
  out['dependent_full_share']=out['dependent_full_count']/len(active_dep) if len(active_dep) else np.nan
  for band in ['0_5','6_12','13_17','18_29','30_59','60_plus']: out[f'dependent_age_{band}_count']=int(active_dep.age_band.eq(band).sum())
  goals_u=goalu[goalu.created_dt.le(t0)&goalu.goal_status.eq('active')]
  out['active_goal_count']=len(goals_u); targets=num(goals_u.selected_target).dropna()
  out['active_goal_target_sum']=float(targets.sum())
  due=goals_u.target_dt.dropna(); out['goal_months_to_target_mean']=float(((due-t0).dt.days.clip(lower=0)/30.4375).mean()) if len(due) else np.nan
  # Goal targets are context only; contribution suggestions, rule capacity and follow-up results are never predictors.
  hist_exp=expu[expu.created_dt.le(t0)]
  out['prior_exposure_total']=float(hist_exp.amount.sum()); out['prior_exposure_count']=len(hist_exp)
  out['prior_exposure_to_income_ratio']=out['prior_exposure_total']/row.monthly_income if pd.notna(row.monthly_income) and row.monthly_income>0 else np.nan
  for cat in EXPOSURE_CATS: out[f'exposure_{cat}_amount']=float(hist_exp.loc[hist_exp.service_category.eq(cat),'amount'].sum())
  return out
 rows=[]
 for i,(_,r) in enumerate(p.iterrows()):
  rows.append(history(r))
  if (i+1)%1000==0: print(f'engineered point-in-time histories for {i+1}/{len(p)} plans',flush=True)
 engineered=pd.DataFrame(rows,index=p.index)
 p=pd.concat([p,engineered],axis=1)
 # Mean follow-up realization ratio is label-only, divided by plan amount at selection time.
 def realized(row):
  vals=row.reported
  if not isinstance(vals,tuple) or len(vals)!=3 or pd.isna(row.selected_contribution) or row.selected_contribution<=0 or any(pd.isna(v) for v in vals): return np.nan
  return float(np.mean(vals)/row.selected_contribution)
 p['target_realization_ratio']=p.apply(realized,axis=1)
 eligible=p[(p.choice_status=='selected')&(p.target_status.isin(['sustainable','adjusted_down']))&p.target_realization_ratio.notna()].copy()
 eligible['split']=eligible.user_id.map(split_user)
 # IDs, timestamps, label construction columns, proxy recommendation fields and all post-choice outcomes are excluded.
 excluded={'user_id','plan_id','goal_id','financial_profile_id','choice_timestamp','created_at','effective_from','effective_to','recorded_at','target_date','updated_at','recommendation_run_id','statuses','reported','target_status','target_sustainable','target_realization_ratio','followup_count','simulated','split','user_selected_monthly_contribution','estimated_monthly_surplus','rule_based_capacity_estimate','system_suggested_monthly_contribution','choice_status','plan_status','data_source','target_source','selected_target','user_proposed_target','goal_status','income_type_profile','employment_status_profile','currency_code_profile','country_code_profile','region_code_profile'}
 excluded.update(c for c in p.columns if c.endswith(('_dt','_timestamp')) or c.startswith(('review_','reported_','followup_')))
 cats=[c for c in CAT_COLS if c in p.columns]
 nums=[c for c in p.columns if c not in excluded and c not in cats and pd.api.types.is_numeric_dtype(p[c])]
 features=nums+cats
 return eligible,p,features,nums,cats

def prep(nums,cats,scale=False):
 n=[('imputer',SimpleImputer(strategy='median',add_indicator=True))]
 if scale:n.append(('scale',StandardScaler()))
 return ColumnTransformer([('num',Pipeline(n),nums),('cat',Pipeline([('imputer',SimpleImputer(strategy='most_frequent')),('onehot',OneHotEncoder(handle_unknown='ignore'))]),cats)],sparse_threshold=0.0)
def config(family,task):
 if family=='linear': return [{'C':v} for v in (.01,.1,10,100)] if task=='classification' else [{'alpha':v} for v in (.1,1,10,1000)]
 if family=='random_forest': return [{'n_estimators':400,'max_depth':d,'min_samples_leaf':l,'max_features':mf} for d,l,mf in ((4,5,'sqrt'),(8,10,'sqrt'),(None,20,.8),(8,20,.8))]
 if family=='catboost': return [{'iterations':it,'depth':d,'learning_rate':.03,'l2_leaf_reg':5} for it,d in ((200,3),(300,4),(500,5),(500,7))]
 if family=='lightgbm': return [{'n_estimators':it,'num_leaves':leaves,'min_child_samples':30,'learning_rate':.03,'reg_lambda':5} for it,leaves in ((150,7),(200,15),(400,7),(400,15))]
def est(f,t,c):
 if f=='linear': return LogisticRegression(max_iter=2000,random_state=SEED,**c) if t=='classification' else Ridge(**c)
 if f=='random_forest':
  args={'n_jobs':1,'random_state':SEED,**c}; return RandomForestClassifier(**args) if t=='classification' else RandomForestRegressor(**args)
 if f=='catboost':
  args={'random_seed':SEED,'thread_count':1,'verbose':False,'allow_writing_files':False,**c}; return CatBoostClassifier(**args) if t=='classification' else CatBoostRegressor(loss_function='RMSE',**args)
 if f=='lightgbm':
  args={'n_jobs':1,'random_state':SEED,'verbosity':-1,**c}; return LGBMClassifier(**args) if t=='classification' else LGBMRegressor(**args)
def cm(y,pred,prob): return {'n':int(len(y)),'accuracy':float(accuracy_score(y,pred)),'balanced_accuracy':float(balanced_accuracy_score(y,pred)),'macro_f1':float(f1_score(y,pred,average='macro')),'precision_adjusted_down':float(precision_score(y,pred,zero_division=0)),'recall_adjusted_down':float(recall_score(y,pred,zero_division=0)),'roc_auc':float(roc_auc_score(y,prob)),'average_precision_adjusted_down':float(average_precision_score(y,prob)),'brier':float(brier_score_loss(y,prob)),'log_loss':float(log_loss(y,prob,labels=[0,1])),'confusion_matrix_sustainable_adjusted_down':confusion_matrix(y,pred,labels=[1,0]).tolist()}
def rm(y,p): return {'n':int(len(y)),'mae_realization_ratio':float(mean_absolute_error(y,p)),'rmse_realization_ratio':float(np.sqrt(mean_squared_error(y,p))),'r2':float(r2_score(y,p)),'within_10pp':float(np.mean(np.abs(y-p)<=.1))}
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--data-dir',type=Path,required=True); ap.add_argument('--output-dir',type=Path,required=True); ap.add_argument('--reuse-engineered-from',type=Path,default=None); a=ap.parse_args()
 print('loading source tables',flush=True)
 t=load_tables(a.data_dir)
 if a.reuse_engineered_from:
  all_rows=pd.read_csv(a.reuse_engineered_from/'engineered_plan_dataset.csv')
  previous=json.loads((a.reuse_engineered_from/'metrics.json').read_text(encoding='utf-8'))
  frame=all_rows[(all_rows.choice_status=='selected')&all_rows.target_status.isin(['sustainable','adjusted_down'])&all_rows.target_realization_ratio.notna()].copy()
  features=previous['feature_names']; nums=previous['features']['numeric']; cats=previous['features']['categorical']
  print('reusing previously engineered point-in-time features',flush=True)
 else:
  frame,all_rows,features,nums,cats=engineer(t)
 print(f'feature rows ready: {len(frame)} eligible plans, {len(features)} predictors',flush=True)
 all_rows['split']=all_rows.user_id.map(split_user)
 parts={k:frame[frame.split.eq(k)].copy() for k in ['train','development','test']}
 if any(len(v)==0 or v.user_id.duplicated().any() for v in parts.values()): raise ValueError('Empty partition or user overlap')
 users=[set(v.user_id) for v in parts.values()]
 if users[0]&users[1] or users[0]&users[2] or users[1]&users[2]: raise ValueError('User split leakage')
 tr,dv,te=(parts[k] for k in ['train','development','test']); x=lambda d:d[features]
 empty_numeric=[c for c in nums if tr[c].notna().sum()==0]
 nums=[c for c in nums if c not in empty_numeric]; features=nums+cats
 print(f'removed all-empty training predictors: {empty_numeric}',flush=True)
 x=lambda d:d[features]
 out=a.output_dir; out.mkdir(parents=True,exist_ok=False); (out/'weights').mkdir()
 # Persist the complete auditable engineered table with split and targets; IDs only for traceability, never model input.
 all_rows.to_csv(out/'engineered_plan_dataset.csv',index=False)
 results={}; models={}; thresholds={}; family_names=['linear','random_forest','catboost','lightgbm']
 ytr=tr.target_sustainable.to_numpy(); ydv=dv.target_sustainable.to_numpy(); yte=te.target_sustainable.to_numpy()
 rtr=tr.target_realization_ratio.to_numpy(); rdv=dv.target_realization_ratio.to_numpy(); rte=te.target_realization_ratio.to_numpy()
 for fam in family_names:
  results[fam]={}
  for task,y_train,y_dev in [('classification',ytr,ydv),('regression',rtr,rdv)]:
   best=None
   for cfg in config(fam,task):
    m=Pipeline([('preprocess',prep(nums,cats,scale=(fam=='linear'))),('model',est(fam,task,cfg))]); m.fit(x(tr),y_train)
    if task=='classification':
     prob=m.predict_proba(x(dv))[:,1]
     for threshold_candidate in np.linspace(.20,.80,31):
      pv=(prob>=threshold_candidate).astype(int); met=cm(y_dev,pv,prob); rank=(met['balanced_accuracy'],met['macro_f1'])
      if best is None or rank>best[0]: best=(rank,m,cfg,met,float(threshold_candidate))
     continue
    else: pv=m.predict(x(dv)); met=rm(y_dev,pv); rank=(-met['mae_realization_ratio'],-met['rmse_realization_ratio'])
    if best is None or rank>best[0]: best=(rank,m,cfg,met,None)
   m=best[1]; models[(fam,task)]=m; joblib.dump(m,out/'weights'/f'{fam}_{task}.joblib',compress=3)
   pred=m.predict(x(te))
   if task=='classification':
    threshold=best[4]; thresholds[fam]=threshold; prob=m.predict_proba(x(te))[:,1]
    results[fam][task]={'selected_config':best[2],'development':best[3],'test':cm(yte,(prob>=threshold).astype(int),prob),'decision_threshold_from_development':threshold}
   else: results[fam][task]={'selected_config':best[2],'development':best[3],'test':rm(rte,pred)}
  print('trained',fam,flush=True)
 an=Pipeline([('preprocess',prep(nums,cats,scale=True)),('model',IsolationForest(n_estimators=300,contamination='auto',random_state=SEED,n_jobs=1))]); an.fit(x(tr))
 joblib.dump(an,out/'weights'/'isolation_forest.joblib',compress=3); threshold=float(np.quantile(-an.score_samples(x(dv)),.90)); score=-an.score_samples(x(te))
 ymedian=float(np.median(rtr)); baseline={'majority_class_accuracy':float(np.mean(yte==(int(ytr.mean()>=.5)))),'majority_class':'sustainable' if ytr.mean()>=.5 else 'adjusted_down','regression_persistence_selected_amount':rm(rte,np.ones(len(rte))),'regression_train_median':rm(rte,np.full(len(rte),ymedian))}
 features_meta={'numeric':nums,'categorical':cats,'removed_all_empty_numeric':empty_numeric,'excluded':['all identifiers as predictors','timestamps','system_suggested_monthly_contribution','rule_based_capacity_estimate','follow-up/status/strain/outcome fields','scenario table (created after plan choice)']}
 metrics={'run_id':out.name,'release_status':'synthetic_engineering_validation_only','data_origin':'synthetic simulation; do not use for personal contribution advice or emergency-readiness decisions','task_scope':'four supervised model families, each with classification and regression artifacts, plus Isolation Forest anomaly comparator','classification_target':'sustainable iff all 3 later follow-ups are sustainable; adjusted_down if any of the 3 is adjusted down','regression_target':'mean of 3 later reported contributions / selected monthly contribution','point_in_time_policy':'latest assessment assessed_at <= plan choice; transaction/activity event and recorded times <= plan choice; active effective-dated profiles/dependents recorded by choice; goals/exposures created by choice; later scenarios excluded','counts':{'plans':len(all_rows),'eligible':len(frame),'excluded_unknown_or_unselected':len(all_rows)-len(frame),'labels':{str(k):int(v) for k,v in frame.target_status.value_counts().items()},'outcomes':len(t['health_reserve_affordability_outcomes']),'transactions':len(t['financial_transactions']),'activity_rows':len(t['health_reserve_activity']),'dependents':len(t['family_dependents']),'goals':len(t['health_reserve_goals']),'exposure_items':len(t['healthcare_exposure_items']),'assessments':len(t['health_reserve_assessments'])},'split':{k:{'plans':len(v),'users':v.user_id.nunique(),'sustainable':int(v.target_sustainable.sum()),'adjusted_down':int((v.target_sustainable==0).sum())} for k,v in parts.items()},'features':features_meta,'feature_count':len(features),'baselines':baseline,'models':results,'decision_thresholds_development':thresholds,'hyperparameter_search':'four configurations per supervised family and task; class thresholds selected on development data by balanced accuracy then macro-F1','isolation_forest':{'threshold_dev_p90':threshold,'test_flag_count':int((score>=threshold).sum()),'test_flag_rate':float(np.mean(score>=threshold)),'labelled_accuracy':None,'meaning':'unlabeled anomaly score only; not affordability'},'limits':['all labels and input histories are synthetic','only one plan per synthetic user and only three simulated follow-ups','no observed personal affordability or causal evidence','no clinical/emergency readiness target','not production validated'],'versions':{'python':sys.version.split()[0],'numpy':np.__version__,'pandas':pd.__version__,'scikit_learn':sklearn.__version__},'source_sha256':{f:sha(a.data_dir/f) for f in TABLES},'training_script_sha256':sha(Path(__file__).resolve()),'seed':SEED,'split_rule':'SHA-256 user hash; deterministic user-disjoint 60/20/20','threshold':'classifier thresholds selected using development data only; anomaly cutoff development p90','feature_names':features}
 (out/'metrics.json').write_text(json.dumps(metrics,indent=2,allow_nan=False)+'\n',encoding='utf8')
 pred=te[['plan_id','user_id','target_status','target_sustainable','target_realization_ratio','split']].copy()
 for fam in family_names:
  cls=models[(fam,'classification')]; reg=models[(fam,'regression')]; pr=cls.predict_proba(x(te))[:,1]
  pred[f'{fam}_prob_sustainable']=pr; pred[f'{fam}_class_sustainable']=(pr>=thresholds[fam]).astype(int); pred[f'{fam}_realization_ratio']=reg.predict(x(te))
 pred['isolation_score']=score; pred.to_csv(out/'test_predictions.csv',index=False)
 file_hashes={str(z.relative_to(out)).replace('\\','/'):sha(z) for z in out.rglob('*') if z.is_file()}
 (out/'manifest.json').write_text(json.dumps({'run_id':out.name,'release_status':metrics['release_status'],'sha256':file_hashes},indent=2)+'\n',encoding='utf8')
 print(json.dumps({'run':str(out),'counts':metrics['counts'],'classification_test':{k:v['classification']['test'] for k,v in results.items()},'regression_test':{k:v['regression']['test'] for k,v in results.items()},'baseline':baseline,'manifest_files':len(file_hashes)},indent=2))
if __name__=='__main__': main()
