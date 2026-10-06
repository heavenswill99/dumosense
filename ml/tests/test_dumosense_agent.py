import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from dumosense_ai.agent import route, run
from dumosense_ai.knowledge import retrieve

class FakeModel:
    def __init__(self, result): self.result = result
    def generate(self, context): return self.result

class AgentTest(unittest.TestCase):
    def inputs(self):
        mg = {"user_id": "u", "run_id": "m", "model_version": "MG", "session_id": "s",
              "index_time": "2026-01-10T12:00:00Z", "current_performance": {"accuracy": .8},
              "baselines": {"per_domain": {"n_valid": 0, "median": None, "ts_max_prior": None}}}
        hr = {"user_id": "u", "model_version": "HR", "reserve_assessment_id": "h",
              "assessed_at": "2026-01-10T12:00:00", "score": 6,
              "obligation_buffer_months": 3.0, "prior_assessment_count": 0,
              "prior_median_buffer_months": None}
        return dict(authenticated_user_id="u", trusted_access={p:{"consent_verified":True,
               "enrollment_verified":True} for p in ("MINDGUARD","HEALTH_RESERVE")},
               source_records={"MINDGUARD":mg,"HEALTH_RESERVE":hr},
               source_runs={"MINDGUARD":{"status":"completed","run_id":"m","model_version":"MG","product_code":"MINDGUARD"},
                            "HEALTH_RESERVE":{"status":"completed","run_id":"h","model_version":"HR","product_code":"HEALTH_RESERVE"}})
    def test_intent_and_tool_selection(self):
        cases = [("How is my memory?", "mindguard", 1),
                 ("Show my reserve buffer", "health_reserve", 1),
                 ("How am I doing overall?", "combined", 2),
                 ("Compare memory and savings", "combined", 2)]
        for q, intent, count in cases:
            with self.subTest(q=q):
                p=route(q); self.assertEqual(p.intent,intent); self.assertEqual(len(p.tools),count)
    def test_combined_keeps_products_separate(self):
        x=run("How am I doing overall?",**self.inputs())
        self.assertEqual(x["status"],"deterministic")
        self.assertEqual([s["product_code"] for s in x["context"]["states"]],
                         ["MINDGUARD","HEALTH_RESERVE"])
        self.assertEqual(len(x["plan"]["called_tools"]),2)
    def test_only_requested_tool_called(self):
        x=run("My memory",**self.inputs())
        self.assertEqual(x["plan"]["called_tools"],["get_mindguard_state"])
    def test_missing_access_fails_closed(self):
        kw=self.inputs(); kw["trusted_access"]["HEALTH_RESERVE"]["consent_verified"]=False
        with self.assertRaises(PermissionError): run("overall",**kw)
    def test_emergency_and_out_of_scope_call_no_tools(self):
        for q,status in [("I can't breathe", "escalate"),("What's the weather?","abstain")]:
            x=run(q,**self.inputs());self.assertEqual(x["status"],status)
            self.assertEqual(x["plan"]["called_tools"],[])
    def test_generation_rejects_unsupported_claim(self):
        fake=FakeModel({"text":"You have dementia.","action_class":"review_history","evidence_ids":[]})
        x=run("my memory",local_model=fake,**self.inputs())
        self.assertEqual(x["status"],"generation_rejected")
    def test_combined_generation_cannot_omit_a_product(self):
        baseline = run("overall", **self.inputs())
        mind_only = baseline["context"]["states"][0]["observation"]
        fake = FakeModel({"text": mind_only, "action_class": "review_history",
                          "evidence_ids": []})
        self.assertEqual(run("overall", local_model=fake,
                             **self.inputs())["status"], "generation_rejected")
    def test_generation_rejects_unapproved_action_or_fake_citation(self):
        for bad in [{"text":"Review your history.","action_class":"buy_insurance","evidence_ids":[]},
                    {"text":"Review your history.","action_class":"review_history","evidence_ids":["made-up"]}]:
            self.assertEqual(run("my memory",local_model=FakeModel(bad),**self.inputs())["status"],"generation_rejected")
    def test_approved_local_evidence(self):
        with TemporaryDirectory() as temp:
            path=Path(temp)/"knowledge.jsonl"
            path.write_text("\n".join(json.dumps(x) for x in [
              {"approved":True,"source_id":"S1","title":"Memory methodology","version":"1","excerpt":"Memory assessment accuracy is recorded per session."},
              {"approved":False,"source_id":"S2","title":"Memory claim","version":"1","excerpt":"Unreviewed claim."}]),encoding="utf-8")
            hits=retrieve("memory assessment",path)
            self.assertEqual([x["source_id"] for x in hits],["S1"])
            x=run("my memory",evidence=hits,**self.inputs())
            self.assertEqual(x["plan"]["evidence_ids"],["S1"])

if __name__ == "__main__": unittest.main()
