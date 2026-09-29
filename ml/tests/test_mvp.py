"""Independent fixtures for the authoritative MVP worker (no files modified)."""
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
import pandas as pd
from engine_v3 import (robust_z_score, compute_baseline_sequence, metrics, evaluate_v3,
                      apply_persistence_filter_user_aware, audit_temporal_leakage)
from mvp_pipeline import (clean, write_json, sha, state, baseline_columns, CONFIG,
                         align_truth, align_context, user_split, generate_report)

class BaselineTests(unittest.TestCase):
    def test_exact_z(self):
        z,reason=robust_z_score([1,2,3],4)
        self.assertAlmostEqual(z,2/1.4826);self.assertIsNone(reason)
    def test_short_history(self):self.assertEqual(robust_z_score([1,2],4)[1],'insufficient_history')
    def test_zero_mad(self):self.assertEqual(robust_z_score([1,1,1],4)[1],'degenerate_scale')
    def test_current_infinity(self):self.assertEqual(robust_z_score([1,2,3],np.inf)[1],'invalid_current')
    def test_nonfinite_history_excluded(self):self.assertEqual(robust_z_score([1,2,np.nan,np.inf],4)[1],'insufficient_history')
    def test_invalid_config(self):
        with self.assertRaises(ValueError):robust_z_score([1,2],3,min_obs=0)
    def test_ties_and_unsorted(self):
        ts=pd.to_datetime(['2026-01-04','2026-01-01','2026-01-02','2026-01-03','2026-01-04'],utc=True)
        out=compute_baseline_sequence([4,1,2,3,100],ts)
        self.assertEqual(out[0]['n_prior'],3);self.assertEqual(out[4]['n_prior'],3)
        self.assertAlmostEqual(out[0]['z'],2/1.4826)
        self.assertEqual(out[1]['n_prior'],0)
        self.assertEqual(out[0]['ts_max_prior'],'2026-01-03T00:00:00+00:00')
    def test_invalid_timestamp_no_fallback(self):
        self.assertEqual(compute_baseline_sequence([1,2,3,4],[None]*4)[3]['reason'],'invalid_timestamp')
    def test_future_invariant(self):
        ts=pd.date_range('2026-01-01',periods=5,tz='UTC')
        a=compute_baseline_sequence([1,2,3,4,5],ts)
        b=compute_baseline_sequence([1,2,3,4,500],ts)
        self.assertEqual(a[:4],b[:4])
    def test_provenance_when_unavailable(self):
        out=compute_baseline_sequence([1,1],pd.date_range('2026-01-01',periods=2,tz='UTC'))
        self.assertEqual(out[1]['n_prior'],1);self.assertIsNotNone(out[1]['ts_max_prior'])
    def test_length_mismatch(self):
        with self.assertRaises(ValueError):compute_baseline_sequence([1],[1,2])

class EvaluationTests(unittest.TestCase):
    def frame(self):
        return pd.DataFrame(dict(trajectory_type=['temporary_change']*4+['stable_pattern']*2,
          prediction=['temporary_change','insufficient_data','stable_pattern','stable_pattern','temporary_change','stable_pattern'],
          hybrid_state=['temporary_change','insufficient_data','stable_pattern','temporary_change','temporary_change','stable_pattern'],
          baseline=[{'reason':None},{'reason':'degenerate_scale'},{'reason':None},{'reason':None},{'reason':None},{'reason':None}]))
    def test_true_positives_not_false_negatives(self):
        e=evaluate_v3(self.frame(),'prediction','hybrid','baseline')
        self.assertEqual((e['TP'],e['TN'],e['FP'],e['FN']),(1,1,1,3))
        self.assertEqual(e['false_negative_reasons'],{'degenerate_scale':1,'deviation_below_threshold':2})
        self.assertEqual(e['evaluable']['FN'],2)
    def test_persistence_attribution(self):
        e=evaluate_v3(self.frame(),'prediction','hybrid_persistent','baseline')
        self.assertEqual(e['false_negative_reasons']['persistence_not_met'],1)
        self.assertEqual(sum(e['false_negative_reasons'].values()),3)
    def test_empty_undefined(self):
        m=metrics([],[]);self.assertIsNone(m['sensitivity']);self.assertIsNone(m['f1'])
    def test_zero_f1_is_zero(self):self.assertEqual(metrics([True,False],[False,True])['f1'],0)
    def test_metric_arithmetic(self):
        m=metrics([True,True,False,False],[True,False,True,False])
        self.assertEqual(m['balanced_accuracy'],.5);self.assertEqual(m['precision'],.5)
    def test_positive_and_negative_alerts(self):
        self.assertEqual(state(-3,2),state(3,2));self.assertEqual(state(None,2),'insufficient_data')

class TemporalTests(unittest.TestCase):
    def test_dictionary_audit_detects_tie(self):
        f=pd.DataFrame([dict(session_id='a',started_at='2026-01-02',bl={'n_prior':3,'ts_max_prior':'2026-01-02'})])
        self.assertEqual(audit_temporal_leakage(f,'bl')['n_violations'],1)
    def test_missing_provenance_not_pass(self):
        f=pd.DataFrame([dict(session_id='a',started_at='2026-01-02',bl={'n_prior':3,'ts_max_prior':None})])
        self.assertEqual(audit_temporal_leakage(f,'bl')['missing_provenance'],1)
    def test_persistence_boundary(self):
        p='temporary_change';s='stable_pattern'
        self.assertEqual(apply_persistence_filter_user_aware([p,p,p,p],['a','b','a','b']),[s,s,p,p])
    def test_insufficient_resets(self):
        self.assertEqual(apply_persistence_filter_user_aware(['temporary_change','insufficient_data','temporary_change'],['a']*3),['stable_pattern','insufficient_data','stable_pattern'])
    def test_persistence_mismatch(self):
        with self.assertRaises(ValueError):apply_persistence_filter_user_aware(['a'],[])
    def test_context_no_future(self):
        cr=pd.DataFrame(dict(session_id=['s'],user_id=['u'],index_time=pd.to_datetime(['2026-01-02'],utc=True)))
        src=pd.DataFrame(dict(user_id=['u','u'],recorded_at=['2026-01-01','2026-01-03'],context_id=['old','future']))
        out,a=align_context(cr,src,'context');self.assertEqual(out.context_id.iloc[0],'old');self.assertEqual(a['violations'],0)
    def test_overlapping_labels_excluded(self):
        cr=pd.DataFrame(dict(session_id=['s'],user_id=['u'],started_at=pd.to_datetime(['2026-01-02'],utc=True)))
        gt=pd.DataFrame(dict(user_id=['u','u'],product_code=['MINDGUARD']*2,trajectory_type=['stable_pattern','temporary_change'],trajectory_start_date=['2026-01-01']*2,trajectory_end_date=['2026-01-03']*2))
        out,a=align_truth(cr,gt);self.assertTrue(out.empty);self.assertEqual(a['ambiguous_sessions'],1)

class PersistenceTests(unittest.TestCase):
    def test_strict_json_sanitizer(self):
        s=json.dumps(clean({'x':np.nan,'y':np.inf,'n':np.int64(2)}),allow_nan=False)
        self.assertEqual(json.loads(s),{'x':None,'y':None,'n':2})
    def test_atomic_json_and_hash(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.json';write_json(p,{'a':1});h=sha(p);write_json(p,{'a':2})
            self.assertNotEqual(sha(p),h);self.assertFalse(p.with_name('x.json.tmp').exists())
    def test_split_deterministic(self):
        self.assertEqual(user_split('u1'),user_split('u1'))
        self.assertIn(user_split('u1'),['train','development','test'])
    def test_groups_do_not_share_history(self):
        cr=pd.DataFrame(dict(user_id=['a','b','a','a','a'],index_time=pd.date_range('2026-01-01',periods=5,tz='UTC'),accuracy_rate=[1,100,2,3,4]))
        baseline_columns(cr,['user_id'],'accuracy_rate','x',CONFIG)
        self.assertAlmostEqual(cr.x_z.iloc[-1],2/1.4826)
        self.assertEqual(cr.x_baseline.iloc[1]['n_prior'],0)

if __name__=='__main__':unittest.main(verbosity=2)
