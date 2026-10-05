from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from canonical.runtime.opus55_target_identity_truth_lock_v1 import (
    TargetIdentityError,
    audit,
    validate_manifest,
)


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = json.loads(
    (ROOT / "canonical/governance/OPUS55_TARGET_IDENTITY_TRUTH_LOCK_20261005_V1.json")
    .read_text(encoding="utf-8")
)
ROOT2 = json.loads(
    (ROOT / "canonical/governance/ROOT2_OUTPUT_ONLY_THRESHOLD_COMPILATION_V3.json")
    .read_text(encoding="utf-8")
)


class TargetIdentityTruthLockTests(unittest.TestCase):
    def test_current_repo_manifest_passes(self):
        out = audit(ROOT)
        self.assertEqual(out["root2_target_count"], 18)
        self.assertEqual(out["class_counts"]["FROZEN_ABSOLUTE"], 10)
        self.assertEqual(out["class_counts"]["FROZEN_RELATIVE_SNAPSHOT"], 3)
        self.assertEqual(out["class_counts"]["HARNESS_CONDITIONAL"], 1)
        self.assertEqual(out["class_counts"]["MATCHED_COMPARATOR"], 4)
        self.assertEqual(out["acceptance_credit_delta"], 0)
        self.assertFalse(out["fresh_reality_authority"])

    def test_live_elo_observation_cannot_become_authoritative(self):
        candidate = copy.deepcopy(MANIFEST)
        candidate["live_external_observations"][0]["authoritative_for_acceptance"] = True
        with self.assertRaisesRegex(
            TargetIdentityError, "LIVE_OBSERVATION_IMPROPERLY_AUTHORITATIVE"
        ):
            validate_manifest(candidate, ROOT2)

    def test_live_elo_cannot_rebase_frozen_gdpval_target(self):
        candidate = copy.deepcopy(MANIFEST)
        for record in candidate["targets"]:
            if record["predicate_id"] == "PROWORK_GDPVAL_GE_1846":
                record["target_value"] = 1867
        with self.assertRaisesRegex(TargetIdentityError, "FROZEN_TARGET_REBASE"):
            validate_manifest(candidate, ROOT2)

    def test_tb_science_current_harness_cannot_replace_release_target(self):
        candidate = copy.deepcopy(MANIFEST)
        for record in candidate["targets"]:
            if record["predicate_id"] == "TB_SCIENCE_GE_58_7":
                record["target_value"] = 63.3
        with self.assertRaisesRegex(TargetIdentityError, "FROZEN_TARGET_REBASE"):
            validate_manifest(candidate, ROOT2)

    def test_root2_membership_drift_fails_closed(self):
        candidate_root2 = copy.deepcopy(ROOT2)
        candidate_root2["predicates"] = candidate_root2["predicates"][:-1]
        with self.assertRaisesRegex(TargetIdentityError, "ROOT2_18_SET_DRIFT"):
            validate_manifest(MANIFEST, candidate_root2)

    def test_target_identity_tuple_is_exhaustive_and_exact(self):
        candidate = copy.deepcopy(MANIFEST)
        candidate["identity_tuple"].remove("FALLBACK_POLICY")
        with self.assertRaisesRegex(
            TargetIdentityError, "IDENTITY_TUPLE_INCOMPLETE_OR_DRIFTED"
        ):
            validate_manifest(candidate, ROOT2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
