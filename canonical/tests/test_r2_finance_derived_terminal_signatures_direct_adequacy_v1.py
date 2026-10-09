from __future__ import annotations
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch

from canonical.runtime import finance_coreference_derived_terminal_signatures_v1 as engine
from canonical.runtime import finance_coreference_derived_terminal_signatures_verify_v1 as verifier
from canonical.runtime import r2_finance_derived_terminal_signatures_direct_adequacy_v1 as route

def problem(chosen:str):
    other="B" if chosen=="A" else "A"
    return {
      "schema":"PROJECT_BRAIN_TYPED_DECISION_PROBLEM_V1","decision_id":"coref-"+chosen,
      "question":"Which bounded action?",
      "alternatives":[{"id":"A","label":"A"},{"id":"B","label":"B"}],"constraints":[],
      "evidence":[
        {"id":"strong-"+chosen,"alternative":chosen,"relation":"SUPPORTS","confidence":0.9,"strength":1.0,
         "independence_group":"g-"+chosen,"claim":"strong","provenance":[{"source":"fixture","ref":"strong"}]},
        {"id":"weak-"+other,"alternative":other,"relation":"SUPPORTS","confidence":0.2,"strength":1.0,
         "independence_group":"g-"+other,"claim":"weak","provenance":[{"source":"fixture","ref":"weak"}]}],
      "policy":{"minimum_support_ratio":0.6,"maximum_conflict_ratio":0.5,
                "minimum_independent_support_groups":1,"minimum_net_margin":0.1}}

def source(*,different=False,with_observation=False):
    out={"schema":engine.INPUT_SCHEMA,"domain":"FINANCE","source_id":"finance:derived:test",
      "marked_mention_universe_complete":True,
      "segments":[{"kind":"TEXT","text":"The "},
        {"kind":"MENTION","mention_id":"bank","text":"bank","entity_class":"NONPERSON","number":"SINGULAR"},
        {"kind":"TEXT","text":" rejected the "},
        {"kind":"MENTION","mention_id":"waiver","text":"waiver","entity_class":"NONPERSON","number":"SINGULAR"},
        {"kind":"TEXT","text":". The request challenged "},
        {"kind":"REFERENCE","mention_id":"it","text":"it"},{"kind":"TEXT","text":"."}],
      "reference_id":"it","ambiguity_owner":"USER_INTENT",
      "antecedent_decision_problems":{"bank":problem("A"),"waiver":problem("B" if different else "A")},
      "observations":[]}
    if with_observation:
        out["observations"]=[{"observation_id":"explicit_reference_binding","cost_units":1,
          "outcome_map_complete":True,"outcomes":{"bank":"SOURCE_EXPLICIT_BANK","waiver":"SOURCE_EXPLICIT_WAIVER"}}]
    return out

def goal():
    return ("Using the structurally complete marked finance coreference typed-decision source at "
            "canonical/cases/source.json, derive and independently verify candidate terminal decisions "
            "and the decision-relevant ambiguity control and save it to canonical/out/result.json.")

class Tests(unittest.TestCase):
    def test_same_derived_terminal_decision_avoids_resolution(self):
        s=source(); out=engine.compute(s)
        self.assertEqual(out["decision"]["action"],"CONTINUE_WITHOUT_DISAMBIGUATION")
        self.assertTrue(verifier.verify(s,out)["verified"])

    def test_distinct_derived_terminals_request_clarification_without_separator(self):
        s=source(different=True); out=engine.compute(s)
        self.assertEqual(out["decision"]["action"],"ASK_USER_MINIMUM_CLARIFICATION")
        self.assertTrue(verifier.verify(s,out)["verified"])

    def test_distinct_derived_terminals_choose_minimum_declared_discriminator(self):
        s=source(different=True,with_observation=True); out=engine.compute(s)
        self.assertEqual(out["decision"]["action"],"ACQUIRE_MINIMUM_TERMINALLY_RELEVANT_DISCRIMINATOR")
        self.assertEqual(out["decision"]["next_observation_id"],"explicit_reference_binding")
        self.assertTrue(verifier.verify(s,out)["verified"])

    def test_missing_candidate_problem_fails_closed(self):
        s=source(); s["antecedent_decision_problems"].pop("bank")
        with self.assertRaisesRegex(engine.DerivedTerminalSignatureError,"CANDIDATE_COVERAGE"): engine.compute(s)

    def test_hidden_reference_in_text_fails_closed(self):
        s=source(); s["segments"][0]["text"]="It said the "
        with self.assertRaisesRegex(Exception,"SUPPORTED_REFERENCE_FORM_MUST_BE_MARKED"): engine.compute(s)

    def test_verifier_rejects_tampered_derived_terminal(self):
        s=source(); out=engine.compute(s)
        out["antecedent_terminal_signatures"]["bank"]["terminal_signature"]["selected_alternative"]="B"
        self.assertFalse(verifier.verify(s,out)["verified"])

    def test_verifier_rejects_tampered_typed_decision_result(self):
        s=source(); out=engine.compute(s); out["typed_decision_results"]["bank"]["selected_alternative"]="B"
        self.assertFalse(verifier.verify(s,out)["verified"])

    def test_route_preflight_is_pure_and_run_is_transactional(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); inp=root/"canonical/cases/source.json"; op=root/"canonical/out/result.json"
            inp.parent.mkdir(parents=True); inp.write_text(json.dumps(source(),sort_keys=True),encoding="utf-8")
            req={"task_id":"derived-terminals","goal":goal()}; before=inp.read_bytes()
            pf=route.preflight(req,repo_root=root); self.assertTrue(pf["matched"],pf)
            self.assertFalse(op.exists()); self.assertEqual(inp.read_bytes(),before)
            out=route.run(req,repo_root=root); self.assertTrue(out["pass"],out)
            self.assertTrue(out["terminal_signatures_derived_not_caller_asserted"])
            self.assertTrue(op.is_file()); self.assertEqual(inp.read_bytes(),before)

    def test_route_rolls_back_on_postwrite_verifier_failure(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); inp=root/"canonical/cases/source.json"; op=root/"canonical/out/result.json"
            inp.parent.mkdir(parents=True); op.parent.mkdir(parents=True)
            s=source(); inp.write_text(json.dumps(s,sort_keys=True),encoding="utf-8"); op.write_text('{"old":true}\n')
            req={"task_id":"derived-terminals-rollback","goal":goal()}; old=op.read_bytes()
            real=route.verifier.verify; calls={"n":0}
            def injected(a,b):
                calls["n"]+=1
                if calls["n"]>=3: return {"verified":False,"producer_independent":True,"reason":"forced"}
                return real(a,b)
            with patch.object(route.verifier,"verify",side_effect=injected):
                out=route.run(req,repo_root=root)
            self.assertFalse(out["pass"],out); self.assertTrue(out["rollback_complete"],out); self.assertEqual(op.read_bytes(),old)

if __name__=="__main__": unittest.main(verbosity=2)
