from __future__ import annotations
import copy
import unittest

from canonical.runtime.tool_discovery_current_acceptance_promotion_v1 import (
    FAMILY,TARGET,compile_promotion,load,verify
)

class ToolDiscoveryCurrentAcceptancePromotionV1Tests(unittest.TestCase):
    def inputs(self):
        return dict(
          evidence=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"),
          registry=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"),
          authority=load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"),
          reduction_receipt=load("canonical/verification/TOOL_DISCOVERY_ACCEPTANCE_REDUCTION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"),
        )

    def test_live_current_world_promotes_exactly_one_atom(self):
        out=verify()
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["proved_predicates"],12)
        self.assertEqual(out["unresolved_predicates"],26)
        self.assertEqual(out["prior_acceptance"],"4/19_PASS__15/19_OPEN")
        self.assertEqual(out["candidate_acceptance"],"5/19_PASS__14/19_OPEN")
        self.assertTrue(out["tool_discovery_family_pass"])
        self.assertEqual(out["verified_owned_family_count_unchanged"],2)
        claim=next(x for x in out["candidate_evidence"]["claims"] if x["predicate_id"]==TARGET)
        self.assertEqual(claim["state"],"PROVED")
        self.assertTrue(claim["scope_complete"])
        self.assertEqual(claim["proof_kind"],"ABSOLUTE_CEILING_WITH_UNIVERSAL_FORMAL_SCOPE_COMPLETENESS")

    def test_failed_reduction_receipt_blocks_promotion(self):
        x=self.inputs()
        x["reduction_receipt"]=copy.deepcopy(x["reduction_receipt"])
        x["reduction_receipt"]["independent_runner"]["conclusion"]="failure"
        self.assertFalse(compile_promotion(**x)["pass"])

    def test_old_scope_blocker_must_still_be_exactly_current(self):
        x=self.inputs()
        x["evidence"]=copy.deepcopy(x["evidence"])
        row=next(r for r in x["evidence"]["claims"] if r["predicate_id"]==TARGET)
        row["blocker"]="OTHER"
        self.assertFalse(compile_promotion(**x)["pass"])

    def test_no_other_tool_atom_may_be_open(self):
        x=self.inputs()
        x["evidence"]=copy.deepcopy(x["evidence"])
        row=next(r for r in x["evidence"]["claims"] if r["predicate_id"]=="TOOL_LEARNING_SECOND_TASK_TRANSFER")
        row["state"]="OPEN"
        self.assertFalse(compile_promotion(**x)["pass"])

    def test_current_acceptance_world_must_not_have_drifted(self):
        x=self.inputs()
        x["authority"]=copy.deepcopy(x["authority"])
        x["authority"]["truth"]["opus55_acceptance"]="5/19_PASS__14/19_OPEN"
        self.assertFalse(compile_promotion(**x)["pass"])


if __name__=="__main__":
    unittest.main(verbosity=2)
