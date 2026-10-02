from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path
from canonical.runtime.m0_portfolio_multiplex_preflight import evaluate

class M0MultiplexPreflightTests(unittest.TestCase):
    def build(self, mutate=None):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            deps=[
                "canonical/runtime/source_contract_compiler.py",
                "canonical/runtime/independent_acceptance_model.py",
                "canonical/runtime/m0a_raw_source_terminal_suite_v2.py",
                "canonical/governance/TERMINAL_PORTFOLIO_BINDING_MANIFESTS_V1.json",
                "canonical/governance/TERMINAL_PORTFOLIO_PREWAVE_PROTOCOL_V1.json",
            ]
            for rel in deps:
                p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text("{}",encoding="utf-8")
            d={
              "behavior_id":"SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001",
              "proof_mode":"PORTFOLIO_MULTIPLEXED_OPEN_DOMAIN_TERMINAL_PROOF",
              "portfolio_bindings":["T0","T1","T2","T3"],
              "candidate_visible_information":["TASK_VISIBLE_RAW_SPECIFICATION"],
              "candidate_must_not_receive":["HIDDEN_VERIFIER","REFERENCE_SOLUTION","GOLD_NORMALIZED_REQUIREMENTS","GOLD_ACCEPTANCE_CONSEQUENCES","MUTATION_LABELS_OR_EXPECTED_FAILURE_REASON"],
              "evaluator":{"required_mutations":["DROP_REQUIRED_ATOM","INVERT_REQUIREMENT_POLARITY","DELETE_MATERIAL_CONDITION","COLLAPSE_AMBIGUITY_TO_ARBITRARY_SINGLE_INTERPRETATION","REMOVE_INDEPENDENT_ACCEPTANCE_FAILURE_MODE"]},
              "terminal_acceptance":{"prewave_binding_is_terminal_result":False,"standalone_synthetic_whole_domain_score_forbidden":True,"terminal_evidence_source":"THE_FROZEN_T0_T1_T2_T3_OBSERVATIONS"},
              "contamination":{"post_freeze_case_specific_tuning":False,"case_replacement":False,"result_to_runtime_feedback_during_wave":False,"evaluator_or_threshold_edit_after_first_terminal_result":False},
              "execution_authority":False,"terminal_results_observed":0,"capability_credit_delta":0,"family_credit_delta":0,
            }
            if mutate: mutate(d)
            p=root/"canonical/governance/M0_PORTFOLIO_MULTIPLEX_TERMINAL_BINDING_V1.json";p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d),encoding="utf-8")
            return evaluate(root)
    def test_valid(self):
        self.assertTrue(self.build()["pass"])
    def test_hidden_oracle_leak_fails(self):
        out=self.build(lambda d:d["candidate_visible_information"].append("REFERENCE_SOLUTION"))
        self.assertFalse(out["pass"])
    def test_synthetic_overclaim_fails(self):
        out=self.build(lambda d:d["terminal_acceptance"].__setitem__("standalone_synthetic_whole_domain_score_forbidden",False))
        self.assertFalse(out["pass"])

if __name__=="__main__":
    unittest.main()
