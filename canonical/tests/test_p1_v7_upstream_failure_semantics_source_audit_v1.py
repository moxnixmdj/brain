import copy
import json
import unittest
from pathlib import Path

from canonical.runtime.p1_v7_upstream_failure_semantics_source_audit_v1 import evaluate, execute

ROOT=Path(__file__).resolve().parents[2]

def load_docs():
    def load(p):
        return json.loads((ROOT/p).read_text(encoding="utf-8"))
    return {
        "binding":load("canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json"),
        "manifest":load("canonical/governance/TERMINAL_PORTFOLIO_BINDING_MANIFESTS_V1.json"),
        "wave":load("canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json"),
        "ident":load("canonical/verification/P1_V7_DIRECT_SURFACE_TRANSPORT_AND_IDENTIFIABILITY_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"),
        "preflight":load("canonical/verification/FOUR_DIRECT_PROOF_MUTATION_PREFLIGHT_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"),
        "typed_v4":load("canonical/verification/TRAJECTORY_TYPED_IR_V4_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"),
        "info_v2":load("canonical/verification/TRAJECTORY_INFORMATION_SAFE_V2_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"),
        "invariant_evidence":load("canonical/capabilities/opus55/TRAJECTORY_INVARIANT_CHECKER_HELDOUT_EVIDENCE_V1.json"),
        "invariant_candidate":load("canonical/capabilities/opus55/TRAJECTORY_INVARIANT_CHECKER_CANDIDATE_V1.json"),
    }

class Tests(unittest.TestCase):
    def test_current_frozen_source_set_classifies_information_residual(self):
        out=execute()
        self.assertEqual(out["classification"],"INFORMATION_OR_SPECIFICATION_RESIDUAL",out)
        self.assertEqual(
            out["status"],
            "FAIL_CLOSED__NO_EXPLICIT_BOUND_UPSTREAM_FAILURE_SEMANTICS_SOURCE_IN_FROZEN_P1_EVIDENCE_SET__ZERO_CREDIT",
        )
        self.assertEqual(out["surface_count"],3)
        self.assertEqual(out["aggregate_p1_receipt_count"],2)
        self.assertFalse(out["event_level_transport_declared_in_aggregate_receipts"])
        self.assertEqual(out["complete_explicit_source_documents"],[])
        self.assertEqual(out["terminal_results_replayed"],0)
        self.assertEqual(out["new_reality_units_consumed"],0)
        self.assertEqual(out["capability_credit_delta"],0)
        self.assertEqual(out["family_credit_delta"],0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])

    def test_explicit_existing_source_prevents_negative_classification(self):
        docs=load_docs()
        docs["binding"]["synthetic_transport_for_test"]={
            "field":"failure_semantics",
            "values":["DIRECT_CONTRACT","DERIVED_UPSTREAM"],
        }
        out=evaluate(docs)
        self.assertEqual(out["classification"],"CANDIDATE_SOURCE_PRESENT",out)
        self.assertIn("binding",out["complete_explicit_source_documents"])

    def test_visible_information_drift_fails_closed(self):
        docs=load_docs()
        docs["binding"]["candidate_visible_information"]=docs["binding"]["candidate_visible_information"][:-1]
        out=evaluate(docs)
        self.assertEqual(out["classification"],"INVALID_INPUT_OR_AUTHORITY_DRIFT",out)

    def test_identifiability_premise_is_load_bearing(self):
        docs=load_docs()
        docs["ident"]["verified_consequences"]=[]
        out=evaluate(docs)
        self.assertEqual(out["classification"],"INVALID_INPUT_OR_AUTHORITY_DRIFT",out)

if __name__=="__main__":
    unittest.main(verbosity=2)
