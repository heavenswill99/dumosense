"""Dumosense deterministic statistics; importing this module never starts a run."""
from pathlib import Path
from collections import Counter
import math
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CONFIG = dict(data_dir=ROOT.parent / 'data' / 'synthetic',
              validation_dir=ROOT.parent / 'validation', output_dir=ROOT / 'outputs',
              min_obs_baseline=3, z_threshold=2.0, persistence_required=2,
              mad_scale=1.4826, epsilon=1e-8, seed=42)
VERSION = 'STAT_ENGINE_MVP_1.0'
POSITIVE = {'temporary_change', 'persistent_change', 'gradual_change'}
TRUTH = {'stable_pattern', 'temporary_change', 'gradual_change'}

def robust_z_score(prior_values, current_value, min_obs=3, mad_scale=1.4826, epsilon=1e-8):
    if min_obs < 1 or mad_scale <= 0 or epsilon <= 0:
        raise ValueError('Invalid baseline configuration')
    prior = np.asarray(prior_values, dtype=float)
    prior = prior[np.isfinite(prior)]
    if not np.isfinite(current_value):
        return None, 'invalid_current'
    if len(prior) < min_obs:
        return None, 'insufficient_history'
    median = np.median(prior)
    scale = mad_scale * np.median(np.abs(prior - median))
    if scale < epsilon:
        return None, 'degenerate_scale'
    z = float((current_value - median) / scale)
    return (z, None) if math.isfinite(z) else (None, 'invalid_computation')

def compute_baseline_sequence(values, timestamps, min_obs=3, mad_scale=1.4826, epsilon=1e-8):
    """Strictly earlier result-availability timestamps, including unsorted inputs.

    No positional fallback for missing timestamps. Tied results never see one another.
    Exact expanding median/MAD: quadratic per short user trajectory, not claimed O(n).
    """
    vals = np.asarray(values, dtype=float)
    ts = pd.DatetimeIndex(pd.to_datetime(timestamps, errors='coerce', utc=True))
    # Compare integer nanoseconds once per group rather than constructing pandas
    # masks for every observation. NaT uses the minimum int64 sentinel.
    ticks = ts.as_unit('ns').asi8
    nat = np.iinfo(np.int64).min
    if len(vals) != len(ts):
        raise ValueError('Value/timestamp length mismatch')
    out = []
    valid = np.isfinite(vals) & (ticks != nat)
    for v, tick in zip(vals, ticks):
        mask = (ticks < tick) & valid if tick != nat else np.zeros(len(vals), dtype=bool)
        prior = vals[mask]
        z, reason = robust_z_score(prior, v, min_obs, mad_scale, epsilon)
        if tick == nat:
            z, reason = None, 'invalid_timestamp'
        med = float(np.median(prior)) if len(prior) else None
        mad = float(np.median(np.abs(prior - med))) if len(prior) else None
        out.append(dict(z=z, n_prior=int(mask.sum()), n_valid=int(mask.sum()),
                        median=med, mad=mad, rs=mad_scale * mad if mad is not None else None,
                        reason=reason, ts_max_prior=pd.Timestamp(int(ticks[mask].max()),tz='UTC').isoformat() if mask.any() else None))
    return out

def apply_persistence_filter_user_aware(states, user_ids, required=2):
    if len(states) != len(user_ids) or required < 1:
        raise ValueError('Invalid persistence arguments')
    counts, out = {}, []
    for state, uid in zip(states, user_ids):
        counts[uid] = counts.get(uid, 0) + 1 if state in POSITIVE else 0
        out.append('stable_pattern' if state in POSITIVE and counts[uid] < required else state)
    return out

def audit_temporal_leakage(cr, baseline_results_col, started_at_col='started_at'):
    baselines=cr[baseline_results_col].tolist()
    valid=np.asarray([isinstance(b,dict) for b in baselines])
    index=pd.DatetimeIndex(pd.to_datetime(cr[started_at_col],errors='coerce',utc=True))
    maximum=pd.DatetimeIndex(pd.to_datetime([b.get('ts_max_prior') if isinstance(b,dict) else None for b in baselines],errors='coerce',utc=True,format='ISO8601'))
    counts=np.asarray([b.get('n_prior',0) if isinstance(b,dict) else 0 for b in baselines])
    checked=valid & index.notna()
    missing=checked & (counts>0) & maximum.isna()
    violations=checked & maximum.notna() & (maximum>=index)
    return dict(n_checked=int(checked.sum()),n_excluded=int((~checked).sum()),n_violations=int(violations.sum()),
                missing_provenance=int(missing.sum()),representative_failing_ids=cr.loc[violations,'session_id'].head(10).tolist(),
                audit_method='strict result-availability comparison')


def metrics(truth, prediction):
    truth, prediction = np.asarray(truth, bool), np.asarray(prediction, bool)
    tp, tn = int((truth & prediction).sum()), int((~truth & ~prediction).sum())
    fp, fn = int((~truth & prediction).sum()), int((truth & ~prediction).sum())
    div = lambda a, b: a / b if b else None
    sensitivity, specificity = div(tp, tp + fn), div(tn, tn + fp)
    return dict(n=len(truth), TP=tp, TN=tn, FP=fp, FN=fn,
                sensitivity=sensitivity, specificity=specificity, FPR=div(fp, fp + tn),
                precision=div(tp, tp + fp), f1=div(2 * tp, 2 * tp + fp + fn),
                balanced_accuracy=(sensitivity + specificity) / 2
                if sensitivity is not None and specificity is not None else None)

def evaluate_v3(eval_df, predicted_col, strategy_name, baseline_results_col=None):
    eligible = eval_df.loc[eval_df.trajectory_type.isin(TRUTH)].copy()
    truth = eligible.trajectory_type.isin(POSITIVE)
    pred = eligible[predicted_col].isin(POSITIVE)
    out = metrics(truth, pred)
    available = eligible[predicted_col].ne('insufficient_data')
    out['evaluable'] = metrics(truth[available], pred[available])
    out['coverage'] = float(available.mean()) if len(eligible) else None
    out['abstentions'] = int((~available).sum())
    out['convention'] = 'E2E: abstention mapped to no alert; conditional metrics exclude abstentions'
    reasons = Counter()
    for row in eligible.loc[truth & ~pred].to_dict('records'):
        if row[predicted_col] == 'insufficient_data':
            bl = row.get(baseline_results_col) if baseline_results_col else None
            reason = bl.get('reason') if isinstance(bl, dict) else None
            reasons[reason or 'unknown_unavailable'] += 1
        elif 'persistent' in strategy_name and row.get('hybrid_state') in POSITIVE:
            reasons['persistence_not_met'] += 1
        else:
            reasons['deviation_below_threshold'] += 1
    if sum(reasons.values()) != out['FN'] or any(n < 0 for n in reasons.values()):
        raise AssertionError('False-negative attribution does not reconcile')
    out.update(false_negative_reasons=dict(reasons), false_negative_reasons_sum=sum(reasons.values()), fn_reconciled=True)
    return out

def build_master_table(data):
    cr, sessions, types = (data[k].copy() for k in ['cognitive_results', 'assessment_sessions', 'assessment_types'])
    for frame, key in [(cr, 'session_id'), (sessions, 'session_id'), (types, 'assessment_type_id')]:
        if frame[key].isna().any() or frame[key].duplicated().any():
            raise ValueError(f'Missing or duplicate key: {key}')
    sessions = sessions.loc[sessions.session_status.eq('completed')]
    cr = cr.merge(sessions[['session_id', 'user_id', 'started_at', 'completed_at', 'consent_id']],
                  on='session_id', how='left', validate='one_to_one', suffixes=('', '_session'))
    if cr.started_at.isna().any() or not cr.user_id.eq(cr.user_id_session).all():
        raise ValueError('Result has missing/completion-invalid session or mismatched user')
    cr = cr.merge(types[['assessment_type_id', 'cognitive_domain']], on='assessment_type_id', how='left', validate='many_to_one')
    for c in ['started_at', 'completed_at', 'calculated_at']:
        cr[c] = pd.to_datetime(cr[c], errors='coerce', utc=True)
        if cr[c].isna().any():
            raise ValueError(f'Invalid required timestamp: {c}')
    if (cr.completed_at < cr.started_at).any() or (cr.calculated_at < cr.completed_at).any():
        raise ValueError('Invalid session/result chronology')
    if cr.cognitive_domain.isna().any() or not cr.accuracy_rate.between(0, 1).all():
        raise ValueError('Invalid domain or accuracy')
    if not np.isfinite(cr.median_reaction_time_ms).all() or (cr.median_reaction_time_ms <= 0).any():
        raise ValueError('Invalid reaction time')
    cr['index_time'] = cr.calculated_at
    return cr.sort_values(['user_id', 'index_time', 'session_id']).reset_index(drop=True)

def fit_mixedlm(cr, formula='accuracy_rate ~ time_days + C(difficulty_level)', return_predictions=False, optimizer='lbfgs'):
    from statsmodels.regression.mixed_linear_model import MixedLM
    cr = cr.copy()
    cr['time_days'] = (cr.started_at - cr.started_at.min()).dt.total_seconds() / 86400
    model = MixedLM.from_formula(formula, groups=cr.user_id, data=cr, missing='raise').fit(reml=True, method=optimizer, maxiter=100)
    if not model.converged:
        raise ValueError('MixedLM did not converge: ' + optimizer)
    rv, rs = float(model.cov_re.iloc[0, 0]), float(model.scale)
    fixed = np.asarray(model.model.exog @ model.fe_params)
    vf = float(np.var(fixed, ddof=0))
    total = rv + rs + vf
    try:
        fitted = np.asarray(model.fittedvalues)
        mode = 'conditional (fixed and fitted random effects)'
    except ValueError:
        fitted, mode = fixed, 'fixed effects only: random covariance singular'
    y = np.asarray(model.model.endog)
    result = dict(formula=formula, converged=bool(model.converged), n_observations=int(model.nobs),
                  n_users=int(cr.user_id.nunique()), log_likelihood=float(model.llf),
                  AIC=None, BIC=None, AIC_BIC_note='Unavailable by design for REML',
                  random_effect_variance=rv, residual_variance=rs, fixed_effect_variance=vf,
                  ICC=rv/(rv+rs), marginal_R2=vf/total, conditional_R2=(vf+rv)/total,
                  variance_convention='population variance of X beta (ddof=0), random intercept REML variance, residual REML variance',
                  RMSE_in_sample=float(np.sqrt(np.mean((y-fitted)**2))), MAE_in_sample=float(np.mean(np.abs(y-fitted))),
                  prediction_mode=mode, coefficients=model.fe_params.to_dict(), std_errors=model.bse_fe.to_dict(),
                  confidence_intervals=model.conf_int().loc[model.fe_params.index].T.to_dict('list'),
                  optimizer=optimizer, max_iterations=100, ML_REML='REML')
    if not all(np.isfinite(result[k]) for k in ['log_likelihood','ICC','marginal_R2','conditional_R2']):
        raise ValueError('Nonfinite mixed-model estimate')
    predictions = pd.DataFrame(dict(session_id=cr.session_id, observed=y, fitted=fitted, residual=y-fitted))
    return (result, predictions) if return_predictions else result

if __name__ == '__main__':
    from mvp_pipeline import cli
    raise SystemExit(cli())
