from __future__ import annotations

import copy
import unittest

from canonical.runtime.osworld_v21_reference_release_equivalence_v1 import (
    OFFICIAL_HASH_MANIFEST_SHA256,
    OFFICIAL_RELEASE,
    OFFICIAL_TASK_COMMIT,
    TASK_COUNT,
    evaluate,
)


def good():
    return (
        {
            "release": OFFICIAL_RELEASE,
            "task_commit": OFFICIAL_TASK_COMMIT,
            "task_hash_manifest_sha256": OFFICIAL_HASH_MANIFEST_SHA256,
            "task_count": TASK_COUNT,
            "all_task_files_unmodified_verified": True,
        },
        {
            "task_release": OFFICIAL_RELEASE,
            "hash_manifest_sha256": OFFICIAL_HASH_MANIFEST_SHA256,
            "matched": TASK_COUNT,
            "integrity_checked_before_every_run": True,
            "each_run_manifest_carries_same_values": True,
        },
        {
            "unique_tasks_replayed": TASK_COUNT,
            "instruction_task_record_identity_checks_passed": TASK_COUNT,
            "canonical_release_hash_match": True,
        },
    )


class TestOSWorldV21ReferenceReleaseEquivalence(unittest.TestCase):
    def test_exact_chain_passes_without_credit_inflation(self):
        out = evaluate(*good())
        self.assertTrue(out["pass"])
        self.assertTrue(out["public_instruction_semantics_authenticated_to_official_v21"])
        self.assertFalse(out["anthropic_sep10_population_equivalence"])
        self.assertFalse(out["harness_equivalence"])
        self.assertFalse(out["score_authority"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_manifest_mutation_fails_closed(self):
        a, b, c = good()
        b = copy.deepcopy(b)
        b["hash_manifest_sha256"] = "0" * 64
        out = evaluate(a, b, c)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "REFERENCE_HASH_MANIFEST_MISMATCH")

    def test_release_mutation_fails_closed(self):
        a, b, c = good()
        b = copy.deepcopy(b)
        b["task_release"] = "other"
        out = evaluate(a, b, c)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "REFERENCE_RELEASE_MISMATCH")

    def test_partial_task_coverage_fails_closed(self):
        a, b, c = good()
        c = copy.deepcopy(c)
        c["instruction_task_record_identity_checks_passed"] = 107
        out = evaluate(a, b, c)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "INSTRUCTION_TASK_RECORD_IDENTITY_INCOMPLETE")

    def test_missing_pre_run_integrity_fails_closed(self):
        a, b, c = good()
        b = copy.deepcopy(b)
        b["integrity_checked_before_every_run"] = False
        out = evaluate(a, b, c)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "PRE_RUN_INTEGRITY_CHECK_REQUIRED")

    def test_owner_task_file_verification_required(self):
        a, b, c = good()
        a = copy.deepcopy(a)
        a["all_task_files_unmodified_verified"] = False
        out = evaluate(a, b, c)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "OFFICIAL_TASK_FILE_VERIFICATION_REQUIRED")


if __name__ == "__main__":
    unittest.main()
