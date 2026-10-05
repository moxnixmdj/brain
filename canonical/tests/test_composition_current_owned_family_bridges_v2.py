from __future__ import annotations
import json,copy,unittest
from pathlib import Path
from canonical.runtime.composition_current_owned_family_bridges_v2 import derive

ROOT=Path(__file__).resolve().parents[2]
def load(p): return json.loads((ROOT/p).read_text(encoding="utf-8"))

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.args=[
            load("canonical/capabilities/opus55/OPUS_5_5_USEFUL_CAPABILITY_ENVELOPE_V1.json"),
            load("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"),
            load("canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json"),
            load("canonical/governance/COMPOSITION_COMPONENT_PROOF_SLICE_INPUT_V1.json"),
            load("canonical/capabilities/opus55/OPUS55_LONG_HORIZON_MEMORY_AND_CONTINUITY_V1.json"),
            load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"),
            load("canonical/verification/COMPOSITION_BEHAVIORAL_BRIDGE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"),
            load("canonical/verification/DELEGATION_ACCEPTANCE_REDUCTION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"),
            load("canonical/verification/DELEGATION_V4_UNIVERSAL_SCOPE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"),
        ]

    def test_exact_current_sources_derive_two_unverified_candidates(self):
        out=derive(*self.args)
        self.assertTrue(out["status"].startswith("PASS"))
        self.assertEqual([r["component_id"] for r in out["candidate_receipts"]],["memory","delegation"])
        self.assertTrue(all(r["verified"] is False and r["independent"] is False for r in out["candidate_receipts"]))
        self.assertEqual(out["expected_after_independent_verification"]["scoped_proved_interface_count"],2)
        self.assertEqual(out["expected_after_independent_verification"]["open_interface_count"],10)

    def test_memory_exclusions_are_preserved_exactly(self):
        out=derive(*self.args)
        pkg=self.args[4]
        mem=out["candidate_receipts"][0]
        self.assertEqual(mem["included_scope"],pkg["claim_scope"])
        self.assertEqual(mem["excluded_scope"],pkg["excluded_scope"])

    def test_fails_if_memory_protocol_reopens(self):
        a=copy.deepcopy(self.args)
        row=next(x for x in a[1]["protocols"] if x["family"]=="LONG_HORIZON_MEMORY_AND_CONTINUITY")
        row["status"]="DEFINED_RESULT_OPEN"
        self.assertFalse(derive(*a)["status"].startswith("PASS"))

    def test_fails_if_delegation_scope_completeness_removed(self):
        a=copy.deepcopy(self.args)
        c=next(x for x in a[5]["claims"] if x["predicate_id"]=="DELEGATION_TERMINAL_SUCCESS_NONINFERIOR")
        c["scope_complete"]=False
        self.assertFalse(derive(*a)["status"].startswith("PASS"))

    def test_fails_if_tool_discovery_falsely_promoted(self):
        a=copy.deepcopy(self.args)
        c=next(x for x in a[5]["claims"] if x["predicate_id"]=="TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR")
        c["state"]="PROVED"
        self.assertFalse(derive(*a)["status"].startswith("PASS"))

    def test_fails_on_composition_manifest_drift(self):
        a=copy.deepcopy(self.args)
        a[2]["source_task_dimensions"]=a[2]["source_task_dimensions"][:-1]
        self.assertFalse(derive(*a)["status"].startswith("PASS"))

    def test_zero_authority(self):
        out=derive(*self.args)
        self.assertEqual(out["capability_credit_delta"],0)
        self.assertEqual(out["family_credit_delta"],0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])

if __name__=="__main__":
    unittest.main(verbosity=2)
