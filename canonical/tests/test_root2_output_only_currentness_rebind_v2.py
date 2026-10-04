from __future__ import annotations

import copy
import unittest

from canonical.runtime.root2_output_only_currentness_rebind_v2 import (
    EXPECTED_BLOBS,
    EXPECTED_MIXED,
    EXPECTED_ROOT2_ONLY,
    evaluate,
)


def root_state():
    return {
        "current_acceptance": {
            "accepted_families": 5,
            "open_families": 14,
            "proved_atomic": 12,
            "unresolved_atomic": 26,
        },
        "current_residual_root_partition": {
            "unresolved_total": 26,
            "root1_positive_gap_count": 0,
            "root2_only": sorted(EXPECTED_ROOT2_ONLY),
            "root2_and_root3": sorted(EXPECTED_MIXED),
            "root1_only": [],
        },
    }


def manifest():
    ids = sorted(EXPECTED_ROOT2_ONLY | EXPECTED_MIXED)
    return {
        "exact_state": {
            "accepted_families": 5,
            "open_families": 14,
            "proved_atomic": 12,
            "unresolved_atomic": 26,
            "root2_only": 16,
            "root3_only": 7,
            "root2_and_root3": 3,
            "root2_touching": 19,
        },
        "predicates": [{"id": x} for x in ids],
    }


def dag_verification():
    return {
        "status": "INDEPENDENT_PUBLIC_RUNNER_PASS__EXACT_THRESHOLD_DAG_SUBJECT_BLOBS",
        "verified": {"predicate_count": 19},
    }


def activation():
    return {
        "authority": {
            "scheduling": True,
            "execution": False,
            "promotion": False,
            "fresh_reality": False,
        }
    }


def activation_verification():
    return {
        "status": "INDEPENDENT_PUBLIC_RUNNER_PASS__EXACT_ACTIVATION_AND_ROOT_PROJECTION",
        "verified": {
            "root2_touching_predicates": 19,
            "root1_positive_gaps": 0,
            "fresh_reality_block_preserved": True,
        },
    }


def run_eval(*, root=None, man=None, blobs=None):
    return evaluate(
        root_state=root or root_state(),
        dag_manifest=man or manifest(),
        dag_verification=dag_verification(),
        activation=activation(),
        activation_verification=activation_verification(),
        observed_blobs=blobs or dict(EXPECTED_BLOBS),
    )


class Root2OutputOnlyCurrentnessRebindV2Tests(unittest.TestCase):
    def test_identical_19_predicate_state_rebinds(self):
        out = run_eval()
        self.assertTrue(out["status"].startswith("PASS__"))
        self.assertTrue(out["semantic_identity_proved"])
        self.assertTrue(out["scheduling_rebind_authorized"])
        self.assertEqual(out["current_root2_touching_count"], 19)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["fresh_reality_authority"])

    def test_any_predicate_set_drift_fails_closed(self):
        r = root_state()
        r["current_residual_root_partition"]["root2_only"] = r["current_residual_root_partition"]["root2_only"][:-1]
        out = run_eval(root=r)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertFalse(out["scheduling_rebind_authorized"])
        self.assertTrue(any("SET_DRIFT" in x or "NOT_EQUAL" in x for x in out["errors"]))

    def test_any_load_bearing_blob_drift_fails_closed(self):
        b = dict(EXPECTED_BLOBS)
        b["evidence"] = "0" * 40
        out = run_eval(blobs=b)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertTrue(any(x.startswith("BLOB_DRIFT:evidence:") for x in out["errors"]))

    def test_root1_reopening_fails_closed(self):
        r = root_state()
        r["current_residual_root_partition"]["root1_positive_gap_count"] = 1
        r["current_residual_root_partition"]["root1_only"] = ["LIVEBENCH_IF_GE_65_7"]
        out = run_eval(root=r)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertTrue(any("ROOT1" in x for x in out["errors"]))

    def test_dag_predicate_drift_fails_closed(self):
        m = manifest()
        m["predicates"][0] = {"id": "INVENTED_PREDICATE"}
        out = run_eval(man=m)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertTrue(any("CURRENT_SET_NOT_EQUAL_VERIFIED_DAG" in x for x in out["errors"]))

    def test_duplicate_current_predicate_fails_closed(self):
        r = root_state()
        rows = r["current_residual_root_partition"]["root2_only"]
        rows.append(rows[0])
        out = run_eval(root=r)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertTrue(any("DUPLICATE" in x for x in out["errors"]))

    def test_count_drift_fails_closed(self):
        r = root_state()
        r["current_acceptance"]["proved_atomic"] = 13
        out = run_eval(root=r)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertTrue(any(x.startswith("COUNT_DRIFT:proved_atomic:") for x in out["errors"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
