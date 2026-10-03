from __future__ import annotations
import copy
import unittest

from canonical.runtime.p1_shared_failure_semantics_batch_normalizer_v1 import (
    SURFACES, normalize_case, validate_batch,
)

def case(surface: str, semantics: str, batch: str = "NEXT-UNSEEN-BATCH"):
    return {
        "behavior_id":"TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001",
        "surface_id":surface,
        "source_batch_id":batch,
        "task":{
            "trajectory":[
                {
                    "action_id":"A0","reads":[],"writes":["x"],"depends_on":[],
                    "checks":[{"kind":"INVARIANT","id":"A0:k","pass":False,
                               "evidence":["receipt:A0"],"failure_semantics":semantics}]
                }
            ],
            "terminal_failed_resources":["x"],
        },
    }

class Tests(unittest.TestCase):
    def test_explicit_semantics_pass(self):
        self.assertTrue(normalize_case(case(SURFACES[0],"DIRECT_CONTRACT"))["status"].startswith("PASS"))

    def test_missing_semantics_never_defaults(self):
        x=case(SURFACES[0],"DIRECT_CONTRACT")
        del x["task"]["trajectory"][0]["checks"][0]["failure_semantics"]
        self.assertEqual(normalize_case(x)["reason"],"FAILURE_SEMANTICS_MISSING__NO_DEFAULT_ALLOWED")

    def test_failed_check_requires_receipts(self):
        x=case(SURFACES[0],"DIRECT_CONTRACT")
        x["task"]["trajectory"][0]["checks"][0]["evidence"]=[]
        self.assertEqual(normalize_case(x)["reason"],"FAILED_CHECK_SUPPORTING_RECEIPTS_REQUIRED")

    def test_unknown_surface_fails(self):
        self.assertEqual(normalize_case(case("OTHER","DIRECT_CONTRACT"))["reason"],"SURFACE_NOT_FROZEN")

    def test_batch_requires_all_three_surfaces_and_both_semantics(self):
        xs=[
            case(SURFACES[0],"DIRECT_CONTRACT"),
            case(SURFACES[1],"DERIVED_UPSTREAM"),
            case(SURFACES[2],"DIRECT_CONTRACT"),
        ]
        out=validate_batch(xs)
        self.assertEqual(out["status"],"PASS__SHARED_BATCH_PREEXECUTION_SCHEMA")
        self.assertEqual(out["case_count"],3)
        self.assertFalse(out["execution_authority"])

    def test_missing_surface_fails(self):
        xs=[case(SURFACES[0],"DIRECT_CONTRACT"),case(SURFACES[1],"DERIVED_UPSTREAM")]
        self.assertEqual(validate_batch(xs)["reason"],"ALL_THREE_FROZEN_SURFACES_REQUIRED")

    def test_only_direct_fails(self):
        xs=[case(s,"DIRECT_CONTRACT") for s in SURFACES]
        self.assertEqual(validate_batch(xs)["reason"],"DIRECT_AND_DERIVED_SEMANTICS_BOTH_REQUIRED")

    def test_multiple_batch_ids_fail(self):
        xs=[
            case(SURFACES[0],"DIRECT_CONTRACT","B1"),
            case(SURFACES[1],"DERIVED_UPSTREAM","B1"),
            case(SURFACES[2],"DIRECT_CONTRACT","B2"),
        ]
        self.assertEqual(validate_batch(xs)["reason"],"MULTIPLE_SOURCE_BATCH_IDS")

    def test_normalizer_preserves_task_and_semantics(self):
        x=case(SURFACES[0],"DERIVED_UPSTREAM")
        before=copy.deepcopy(x["task"])
        out=normalize_case(x)
        self.assertEqual(out["public_case"]["task"],before)
        self.assertEqual(
            out["public_case"]["task"]["trajectory"][0]["checks"][0]["failure_semantics"],
            "DERIVED_UPSTREAM",
        )

if __name__=="__main__":
    unittest.main(verbosity=2)
