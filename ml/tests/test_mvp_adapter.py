import unittest
from insight_adapter import build_insight

class InsightTests(unittest.TestCase):
    def record(self):
        return dict(user_id='u',run_id='r',session_id='s',model_version='m',index_time='2026-01-01',
          current_performance={'accuracy':.8},baselines={'per_domain':{'z':None}})
    def test_wrong_user_denied(self):
        with self.assertRaises(PermissionError):build_insight(self.record(),authenticated_user_id='other',consent_verified=True)
    def test_consent_denied(self):
        with self.assertRaises(PermissionError):build_insight(self.record(),authenticated_user_id='u',consent_verified=False)
    def test_missing_provenance_denied(self):
        r=self.record();del r['run_id']
        with self.assertRaises(ValueError):build_insight(r,authenticated_user_id='u',consent_verified=True)
    def test_no_alert_and_traceable(self):
        result=build_insight(self.record(),authenticated_user_id='u',consent_verified=True)
        self.assertFalse(result['delivery']['automatic_alert']);self.assertEqual(result['traceability']['session_id'],'s')
        self.assertEqual(result['insight']['insight_type'],'insufficient_data')
    def test_deterministic_id(self):
        kw=dict(authenticated_user_id='u',consent_verified=True)
        self.assertEqual(build_insight(self.record(),**kw),build_insight(self.record(),**kw))
