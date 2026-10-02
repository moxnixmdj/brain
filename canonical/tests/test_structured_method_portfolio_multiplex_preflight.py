from __future__ import annotations
import json,tempfile,unittest
from pathlib import Path
from canonical.runtime.structured_method_portfolio_multiplex_preflight import evaluate,BINDING,REQUIRED_DEPS

def valid():
    return {
      "behavior_id":"STRUCTURED_METHOD_COMPLETE_CALCULATION_GRAPH_001",
      "proof_mode":"PORTFOLIO_MULTIPLEXED_DETERMINISTIC_TERMINAL_PROOF",
      "portfolio_bindings":["T0","T1"],
      "direct_surface_bindings":[
        "T0/FRONTIERCODE_V1_1::P0_STRUCTURED_METHOD_GRAPH_DIRECT_PROOF",
        "T1/FINANCE_ACCOUNTING_INDEX::P0_STRUCTURED_METHOD_GRAPH_DIRECT_PROOF",
        "T1/FINANCE_AGENT_V2::P0_STRUCTURED_METHOD_GRAPH_DIRECT_PROOF",
      ],
      "candidate_visible_information":["NORMALIZED_APPLICABLE_RULES","INPUT_SCHEMA"],
      "candidate_must_not_receive":[
        "HIDDEN_VERIFIER","REFERENCE_GRAPH","GOLD_REQUIREMENT_LINEAGE",
        "GOLD_JUSTIFIED_EXCLUSIONS","GOLD_EDGE_ACCEPTANCE_RESULT",
        "MUTATION_LABELS_OR_EXPECTED_FAILURE_REASON",
      ],
      "evaluator":{"required_mutations":[
        "DELETE_MATERIAL_EDGE","REWIRE_MATERIAL_EDGE","DROP_REQUIRED_CONSUMER",
        "DELETE_JUSTIFIED_EXCLUSION","MUTATE_TYPE_OR_DIMENSION",
        "DELETE_DECLARED_INVARIANT","MUTATE_REQUIRED_OUTPUT",
      ]},
      "terminal_acceptance":{
        "prewave_binding_is_terminal_result":False,
        "standalone_synthetic_whole_domain_score_forbidden":True,
        "terminal_evidence_source":"THE_FROZEN_T0_T1_TERMINAL_OBSERVATIONS",
        "any_load_bearing_structured_method_failure_blocks_behavior_proof":True,
      },
      "contamination":{
        "post_freeze_case_specific_tuning":False,"case_replacement":False,
        "result_to_runtime_feedback_during_wave":False,
        "evaluator_or_threshold_edit_after_first_terminal_result":False,
      },
      "execution_authority":False,"terminal_results_observed":0,
      "capability_credit_delta":0,"family_credit_delta":0,
    }

class Tests(unittest.TestCase):
    def test_live_binding(self):
        root=Path(__file__).resolve().parents[2]
        out=evaluate(root)
        self.assertTrue(out["pass"],out)

    def run_fixture(self,mutate=None,missing_dep=None):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for rel in REQUIRED_DEPS:
                if rel==missing_dep: continue
                p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text("{}",encoding="utf-8")
            d=valid()
            if mutate: mutate(d)
            p=root/BINDING;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d),encoding="utf-8")
            return evaluate(root)

    def test_valid(self):
        self.assertTrue(self.run_fixture()["pass"])

    def test_hidden_graph_leak_fails(self):
        out=self.run_fixture(lambda d:d["candidate_visible_information"].append("REFERENCE_GRAPH"))
        self.assertFalse(out["pass"])

    def test_missing_mutation_fails(self):
        out=self.run_fixture(lambda d:d["evaluator"]["required_mutations"].pop())
        self.assertFalse(out["pass"])

    def test_synthetic_overclaim_fails(self):
        out=self.run_fixture(lambda d:d["terminal_acceptance"].__setitem__("standalone_synthetic_whole_domain_score_forbidden",False))
        self.assertFalse(out["pass"])

    def test_missing_portfolio_fails(self):
        out=self.run_fixture(lambda d:d.__setitem__("portfolio_bindings",["T0"]))
        self.assertFalse(out["pass"])

    def test_missing_dependency_fails(self):
        out=self.run_fixture(missing_dep=REQUIRED_DEPS[0])
        self.assertFalse(out["pass"])
        self.assertTrue(any(x.startswith("DEPENDENCY_MISSING:") for x in out["errors"]))

if __name__=="__main__":
    unittest.main(verbosity=2)
