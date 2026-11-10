"""Optimize the synthetic Health Reserve benchmark from a verified engineered run."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from importlib.metadata import version
from pathlib import Path

sys.path.insert(0, os.environ.get('DUMOSENSE_ML_DEPS', str(Path(__file__).resolve().parents[1] / '.deps')))

import joblib
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier, CatBoostRegressor
from lightgbm import LGBMClassifier, LGBMRegressor
from scipy.stats import loguniform, spearmanr
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import IsolationForest, RandomForestClassifier, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, QuantileRegressor, Ridge
from sklearn.metrics import (
    accuracy_score, average_precision_score, balanced_accuracy_score, brier_score_loss,
    confusion_matrix, f1_score, log_loss, mean_absolute_error, mean_squared_error,
    precision_score, r2_score, recall_score, roc_auc_score,
)
from sklearn.model_selection import GroupKFold, ParameterSampler, RandomizedSearchCV, StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from threadpoolctl import threadpool_limits

SEED = 42
FAMILIES = ('linear', 'random_forest', 'catboost', 'lightgbm')
CASHFLOW = ('monthly_income', 'essential_monthly_expenses', 'debt_repayments',
            'other_monthly_obligations', 'existing_liquid_savings', 'income_stability_index',
            'net_monthly_cashflow', 'obligations_to_income_ratio', 'liquid_savings_months',
            'selected_contribution', 'contribution_to_income_ratio',
            'contribution_to_positive_net_cashflow_ratio', 'surplus_after_selected_contribution',
            'active_dependent_count', 'income_type', 'employment_status')


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def load_benchmark(root):
    manifest = read_json(root / 'manifest.json')['sha256']
    required = {'engineered_plan_dataset.csv', 'metrics.json', 'test_predictions.csv'}
    required.update(f'weights/{family}_{task}.joblib' for family in FAMILIES
                    for task in ('classification', 'regression'))
    required.add('weights/isolation_forest.joblib')
    if any(sha(root / name) != manifest.get(name) for name in required):
        raise ValueError('Source run is incomplete or its hashes do not match')
    metrics = read_json(root / 'metrics.json')
    if metrics['release_status'] != 'synthetic_engineering_validation_only':
        raise ValueError('Expected a synthetic benchmark')
    frame = pd.read_csv(root / 'engineered_plan_dataset.csv', float_precision='round_trip')
    frame = frame.loc[frame.choice_status.eq('selected') & frame.target_realization_ratio.notna()
                      & frame.target_status.isin(['sustainable', 'adjusted_down'])].copy()
    features = metrics['feature_names']
    if (frame.user_id.duplicated().any() or frame.plan_id.duplicated().any()
            or not frame.target_sustainable.eq(frame.target_status.eq('sustainable').astype(int)).all()
            or not set(CASHFLOW).issubset(features) or any(f.startswith('target_') for f in features)
            or not np.isfinite(frame.target_realization_ratio).all()):
        raise ValueError('Unexpected cohort, targets or features')
    parts = {s: frame.loc[frame.split.eq(s)].set_index('plan_id') for s in ('train', 'development', 'test')}
    if any(len(part) != metrics['split'][s]['plans'] for s, part in parts.items()) or sum(map(len, parts.values())) != len(frame):
        raise ValueError('Cohort sizes do not match the frozen run')
    old = pd.read_csv(root / 'test_predictions.csv', float_precision='round_trip').set_index('plan_id')
    test = parts['test']
    if not old.index.is_unique or set(old.index) != set(test.index):
        raise ValueError('Previous and current test cohorts differ')
    old = old.loc[test.index]
    if not (old.user_id.eq(test.user_id).all() and old.target_sustainable.eq(test.target_sustainable).all()
            and np.array_equal(old.target_realization_ratio, test.target_realization_ratio)):
        raise ValueError('Previous and current evaluation targets differ')
    return metrics, parts, old


def preprocess(columns, categorical, scale=False):
    cats = [c for c in columns if c in categorical]
    nums = [c for c in columns if c not in categorical]
    numeric = [('impute', SimpleImputer(strategy='median', add_indicator=True, keep_empty_features=True))]
    if scale:
        numeric.append(('scale', StandardScaler()))
    return ColumnTransformer([
        ('numeric', Pipeline(numeric), nums),
        ('categorical', Pipeline([
            ('impute', SimpleImputer(strategy='most_frequent', keep_empty_features=True)),
            ('encode', OneHotEncoder(handle_unknown='ignore', sparse_output=False)),
        ]), cats),
    ], verbose_feature_names_out=True).set_output(transform='pandas')


def search_space(family, classify):
    if family == 'linear':
        if classify:
            return [(LogisticRegression(max_iter=1500, random_state=SEED), {'C': loguniform(.003, 20)})]
        return [(Ridge(), {'alpha': loguniform(1, 5000)}),
                (QuantileRegressor(solver='highs'), {'alpha': loguniform(.0001, .03)})]
    if family == 'random_forest':
        cls = RandomForestClassifier if classify else RandomForestRegressor
        return [(cls(n_estimators=100, random_state=SEED, n_jobs=2),
                 {'max_depth': [3, 5, 8, None], 'min_samples_leaf': [12, 24, 48], 'max_features': [.25, .5, 1.]})]
    if family == 'catboost':
        params = {'iterations': [100, 180, 260], 'depth': [3, 4, 5],
                  'learning_rate': loguniform(.025, .13), 'l2_leaf_reg': loguniform(2, 25)}
        fixed = dict(random_seed=SEED, thread_count=2, verbose=False, allow_writing_files=False)
        model = CatBoostClassifier(**fixed) if classify else CatBoostRegressor(**fixed)
        return [(model, params)] if classify else [(model, {**params, 'loss_function': ['Quantile:alpha=0.5', 'RMSE']})]
    params = {'n_estimators': [80, 140, 220], 'num_leaves': [4, 8, 14], 'min_child_samples': [25, 50, 90],
              'learning_rate': loguniform(.025, .13), 'reg_lambda': loguniform(1, 30)}
    fixed = dict(random_state=SEED, n_jobs=2, verbosity=-1)
    model = LGBMClassifier(**fixed) if classify else LGBMRegressor(alpha=.5, **fixed)
    return [(model, params)] if classify else [(model, {**params, 'objective': ['quantile', 'regression_l1', 'regression']})]


def optimize(family, classify, train, features, cats, n_trials):
    spaces = []
    for columns in (list(CASHFLOW), features):
        for model, params in search_space(family, classify):
            spaces.append({'prep': [preprocess(columns, cats, family == 'linear')], 'model': [model],
                           **{f'model__{name}': values for name, values in params.items()}})
    # Guarantee that each feature set and each distinct linear loss is tried.
    candidates = [{k: [v] for k, v in trial.items()} for i, space in enumerate(spaces)
                  for trial in ParameterSampler(space, n_iter=n_trials, random_state=SEED + i)]
    folds = StratifiedGroupKFold(3, shuffle=True, random_state=SEED) if classify else GroupKFold(3)
    target = train.target_sustainable if classify else train.target_realization_ratio
    cv = list(folds.split(train, target, groups=train.user_id))
    search = RandomizedSearchCV(Pipeline([('prep', 'passthrough'), ('model', spaces[0]['model'][0])]),
                               candidates, n_iter=len(candidates), cv=cv, n_jobs=1, error_score='raise',
                               scoring='roc_auc' if classify else 'neg_mean_absolute_error', random_state=SEED)
    search.fit(train[features], target)
    trials = []
    for i, params in enumerate(search.cv_results_['params']):
        score = float(search.cv_results_['mean_test_score'][i])
        trials.append({'feature_set': 'cashflow' if params['prep'].transformers[0][2] == [c for c in CASHFLOW if c not in cats] else 'full',
                       'estimator': type(params['model']).__name__,
                       'parameters': {k.removeprefix('model__'): float(v) if isinstance(v, np.floating) else v
                                      for k, v in params.items() if k.startswith('model__')},
                       'cv_score': score if classify else -score,
                       'selected': bool(i == search.best_index_)})
    return search.best_estimator_, trials


def classification(y, p, threshold):
    decision = p >= threshold
    return {'accuracy': accuracy_score(y, decision), 'balanced_accuracy': balanced_accuracy_score(y, decision),
            'macro_f1': f1_score(y, decision, average='macro'), 'roc_auc': roc_auc_score(y, p),
            'precision_adjusted_down': precision_score(y, decision, pos_label=0, zero_division=0),
            'recall_adjusted_down': recall_score(y, decision, pos_label=0),
            'average_precision_adjusted_down': average_precision_score(1 - y, 1 - p),
            'brier': brier_score_loss(y, p), 'log_loss': log_loss(y, p),
            'confusion_matrix_sustainable_adjusted_down': confusion_matrix(y, decision, labels=[1, 0]).tolist()}


def threshold_for(y, p):
    return max(np.linspace(.25, .75, 101), key=lambda t: (balanced_accuracy_score(y, p >= t), -abs(t - .5)))


def regression(y, p):
    return {'mae': mean_absolute_error(y, p), 'rmse': float(np.sqrt(mean_squared_error(y, p))),
            'r2': r2_score(y, p), 'within_10_percentage_points': float(np.mean(np.abs(y - p) <= .1))}


def tune_isolation(train, dev, features, cats):
    trials = []
    for columns in (list(CASHFLOW), features):
        for samples, max_features in ((128, .6), (256, .8), (512, 1.), (1024, .8)):
            settings = dict(n_estimators=256, max_samples=samples, max_features=max_features, n_jobs=2)
            p = preprocess(columns, cats).fit(train[features])
            tr, dv = p.transform(train[features]), p.transform(dev[features])
            a, b = [IsolationForest(**settings, random_state=s).fit(tr) for s in (SEED, SEED + 1)]
            sa, sb = -a.score_samples(dv), -b.score_samples(dv)
            fa, fb = sa >= np.quantile(sa, .9), sb >= np.quantile(sb, .9)
            jaccard = float((fa & fb).sum() / (fa | fb).sum())
            record = {'max_samples': samples, 'max_features': max_features, 'n_estimators': 256,
                      'feature_set': 'full' if columns is features else 'cashflow', 'dev_flag_jaccard': jaccard,
                      'dev_score_rank_correlation': float(spearmanr(sa, sb).statistic)}
            trials.append((record, Pipeline([('prep', p), ('model', a)]), float(np.quantile(sa, .9))))
    best, model, cutoff = max(trials, key=lambda t: (t[0]['dev_flag_jaccard'], t[0]['dev_score_rank_correlation']))
    return model, cutoff, best, [x[0] for x in trials]


def paired_interval(deltas):
    rng = np.random.default_rng(SEED)
    means = rng.choice(deltas, (2000, len(deltas)), replace=True).mean(axis=1)
    return {'mean': float(np.mean(deltas)), 'bootstrap_95_percent_interval': np.quantile(means, [.025, .975]).tolist()}


def run(args):
    source, parts, old = load_benchmark(args.source_run)
    train, dev, test = (parts[k] for k in ('train', 'development', 'test'))
    features, cats = source['feature_names'], source['features']['categorical']
    xd, xt = dev[features], test[features]
    cd, ct = dev.target_sustainable.to_numpy(), test.target_sustainable.to_numpy()
    rd, rt = dev.target_realization_ratio.to_numpy(), test.target_realization_ratio.to_numpy()
    out = args.output_dir
    (out / 'weights').mkdir(parents=True, exist_ok=False)
    median = DummyRegressor(strategy='median').fit(train[['selected_contribution']], train.target_realization_ratio)
    median_value = float(median.constant_.item())
    joblib.dump(median, out / 'weights' / 'median_baseline.joblib', compress=3)
    median_dev, median_test = np.full(len(dev), median_value), np.full(len(test), median_value)
    baseline_loss = np.abs(rt - median_test)
    preds = test[['target_sustainable', 'target_realization_ratio']].copy()
    models, class_candidates, reg_candidates = {}, {}, {'median_baseline': mean_absolute_error(rd, median_dev)}
    for family in FAMILIES:
        classifier, class_trials = optimize(family, True, train, features, cats, args.trials_per_space)
        regressor, reg_trials = optimize(family, False, train, features, cats, args.trials_per_space)
        dp = classifier.predict_proba(xd)[:, 1]
        threshold = float(threshold_for(cd, dp))
        dev_class = classification(cd, dp, threshold)
        class_candidates[family] = dev_class['balanced_accuracy']
        raw = regressor.predict(xd)
        # Include zero weight so the train median is always an available fallback.
        mix = float(min(np.linspace(0, 1, 21), key=lambda w: mean_absolute_error(rd, median_dev + w * (raw - median_dev))))
        reg_candidates[family] = mean_absolute_error(rd, median_dev + mix * (raw - median_dev))
        p, pred_raw = classifier.predict_proba(xt)[:, 1], regressor.predict(xt)
        pred = median_test + mix * (pred_raw - median_test)
        for name, model, expected in ((f'{family}_classification', classifier, p), (f'{family}_regression', regressor, pred_raw)):
            path = out / 'weights' / f'{name}.joblib'
            joblib.dump(model, path, compress=3)
            restored = joblib.load(path)
            actual = restored.predict_proba(xt)[:, 1] if name.endswith('classification') else restored.predict(xt)
            np.testing.assert_allclose(actual, expected, rtol=0, atol=1e-12)
        old_p = old[f'{family}_prob_sustainable'].to_numpy()
        old_r = old[f'{family}_realization_ratio'].to_numpy()
        old_threshold = source['decision_thresholds_development'][family]
        models[family] = {
            'classification': {'threshold_probability_sustainable': threshold, 'development': dev_class,
                               'test': classification(ct, p, threshold), 'previous_test_corrected': classification(ct, old_p, old_threshold),
                               'trials': class_trials},
            'regression': {'blend_model_weight': mix, 'development_mae': reg_candidates[family],
                           'test': regression(rt, pred), 'raw_model_test': regression(rt, pred_raw),
                           'previous_test': regression(rt, old_r),
                           'mae_difference_vs_median': paired_interval(np.abs(rt - pred) - baseline_loss), 'trials': reg_trials},
        }
        preds[f'{family}_prob_sustainable'] = p
        preds[f'{family}_class_sustainable'] = (p >= threshold).astype(int)
        preds[f'{family}_ratio_raw'] = pred_raw
        preds[f'{family}_ratio_blended'] = pred
        print('Optimized and verified', family, flush=True)
    isolation, cutoff, best, trials = tune_isolation(train, dev, features, cats)
    path = out / 'weights' / 'isolation_forest.joblib'
    joblib.dump(isolation, path, compress=3)
    score = -isolation.score_samples(xt)
    np.testing.assert_allclose(-joblib.load(path).score_samples(xt), score, rtol=0, atol=1e-12)
    np.testing.assert_array_equal(joblib.load(out / 'weights' / 'median_baseline.joblib').predict(test[['selected_contribution']]), median_test)
    preds['isolation_score'] = score
    preds['isolation_flag'] = (score >= cutoff).astype(int)
    preds['median_baseline_ratio'] = median_test
    preds.to_csv(out / 'test_predictions.csv')
    metrics = {'run_id': out.name, 'release_status': 'synthetic_engineering_validation_only',
               'previous_run': source['run_id'], 'split': source['split'], 'feature_names': features,
               'source_manifest_sha256': sha(args.source_run / 'manifest.json'), 'source_data_sha256': source['source_sha256'],
               'optimizer_sha256': sha(Path(__file__)), 'versions': {'python': sys.version.split()[0], **{
                   p: version(p) for p in ('scikit-learn', 'numpy', 'pandas', 'scipy', 'catboost', 'lightgbm', 'joblib')}},
               'search': {'seed': SEED, 'trials_per_space': args.trials_per_space, 'folds': 3,
                          'selection': 'Train user-group CV by ROC AUC or MAE. Select thresholds, blend weights and research candidates on development. Test cohort reused for comparison.'},
               'median_baseline': {'value': median_value, 'development_mae': reg_candidates['median_baseline'], 'test': regression(rt, median_test)},
               'majority_class_test': classification(ct, np.full(len(ct), train.target_sustainable.mean()), .5),
               'research_selection': {'classifier_by_development_balanced_accuracy': max(class_candidates, key=class_candidates.get),
                                      'ratio_by_development_mae': min(reg_candidates, key=reg_candidates.get)},
               'isolation_forest': {'selection': best, 'trials': trials, 'cutoff': cutoff, 'test_flag_rate': float(np.mean(score >= cutoff)),
                                    'previous_test_flag_rate': source['isolation_forest']['test_flag_rate'], 'labelled_accuracy': None},
               'models': models}
    write_json(out / 'metrics.json', metrics)
    write_json(out / 'manifest.json', {'run_id': out.name, 'sha256': {
        f.relative_to(out).as_posix(): sha(f) for f in sorted(out.rglob('*')) if f.is_file()}})
    print('Finished:', out, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-run', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--trials-per-space', type=int, default=5)
    args = parser.parse_args()
    if args.trials_per_space < 2:
        parser.error('--trials-per-space must be at least 2')
    with threadpool_limits(limits=2):
        run(args)
