from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from canonical.runtime import escape_progress_shared_gap_audit_v1 as v1
from canonical.runtime import escape_progress_shared_gap_audit_v2 as v2

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = json.loads((ROOT / v2.MANIFEST_REL).read_text(encoding="utf-8"))
BINDING = json.loads((ROOT / v2.BINDING_REL).read_text(encoding="utf-8"))
FROZEN_V1 = json.loads(
    (ROOT / v2.FROZEN_V1_MANIFEST_REL).read_text(encoding="utf-8")
)
FROZEN_IDS = [row["obligation_id"] for row in FROZEN_V1["rows"]]


def _seal(row):
    material = dict(row)
    material["proof_sha256"] = v1._sha(material)
    return material


def _proofs():
    out = {}
    for row in MANIFEST["rows"]:
        oid = row["obligation_id"]
        if row["route_group"] == v2.GAP_A:
            out[oid] = _seal(
                {
                    "obligation_id": oid,
                    "route_group": v2.GAP_A,
                    "currently_acquirable": True,
                    "finite_outcome_ids": ["yes", "no"],
                    "outcome_map_complete": True,
                    "decision_region_size_before": 2,
                    "max_nonterminal_decision_region_size_after": 1,
                    "authenticated_truth_preserving": True,
                    "safe": True,
                }
            )
        else:
            out[oid] = _seal(
                {
                    "obligation_id": oid,
                    "route_group": v2.GAP_B,
                    "verified_action_id": "verified:" + oid,
                    "action_executable_now": True,
                    "progress_measure": {
                        "kind": "FINITE_NATURAL_RANK",
                        "current_rank": 2,
                        "minimum_rank": 0,
                        "well_founded": True,
                    },
                    "allowed_outcomes": [
                        {
                            "outcome_id": "done",
                            "terminal": True,
                            "strictly_decreases_measure": False,
                        },
                        {
                            "outcome_id": "progress",
                            "terminal": False,
                            "strictly_decreases_measure": True,
                        },
                    ],
                    "safe": True,
                }
            )
    return out


def _git_blob(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


class EscapeProgressSharedGapAuditV2Tests(unittest.TestCase):
    def test_current_successor_manifest_validates_as_10_a_3_b_and_stays_open(self):
        result = v2.audit_repo()
        self.assertTrue(result["pass"], result)
        self.assertFalse(result["cc_r3_proved"])
        self.assertEqual(result["row_count"], 13)
        self.assertEqual(result["gap_a_count"], 10)
        self.assertEqual(result["gap_b_count"], 3)
        self.assertEqual(result["open_row_count"], 13)
        self.assertEqual(
            result["manifest_declared_counts"],
            {v2.GAP_A: 10, v2.GAP_B: 3},
        )
        self.assertEqual(
            result["binding_declared_counts"],
            {v2.GAP_A: 10, v2.GAP_B: 3},
        )
        self.assertEqual(result["terminal_credit_delta"], 0)

    def test_finance_index_is_gap_a_in_current_successor(self):
        row = next(
            row
            for row in MANIFEST["rows"]
            if row["obligation_id"] == "FINANCE_ACCOUNTING_INDEX_GE_61"
        )
        self.assertEqual(row["route_group"], v2.GAP_A)

    def test_complete_valid_content_addressed_proofs_close_13_of_13(self):
        result = v2.audit(
            MANIFEST,
            BINDING,
            _proofs(),
            frozen_obligation_ids=FROZEN_IDS,
        )
        self.assertTrue(result["pass"], result)
        self.assertTrue(result["cc_r3_proved"])
        self.assertEqual(result["closed_row_count"], 13)
        self.assertEqual(result["open_row_count"], 0)
        self.assertEqual(result["open_predicates"], [])

    def test_gap_a_missing_strict_shrink_stays_open(self):
        proofs = _proofs()
        oid = next(
            row["obligation_id"]
            for row in MANIFEST["rows"]
            if row["route_group"] == v2.GAP_A
        )
        proof = dict(proofs[oid])
        proof.pop("proof_sha256")
        proof["max_nonterminal_decision_region_size_after"] = proof[
            "decision_region_size_before"
        ]
        proofs[oid] = _seal(proof)
        result = v2.audit(
            MANIFEST,
            BINDING,
            proofs,
            frozen_obligation_ids=FROZEN_IDS,
        )
        self.assertTrue(result["pass"])
        self.assertFalse(result["cc_r3_proved"])
        self.assertIn(
            f"{oid}:STRICT_DECISION_REGION_SHRINK_NOT_PROVED",
            result["open_predicates"],
        )

    def test_gap_b_nonprogress_outcome_stays_open(self):
        proofs = _proofs()
        oid = next(
            row["obligation_id"]
            for row in MANIFEST["rows"]
            if row["route_group"] == v2.GAP_B
        )
        proof = dict(proofs[oid])
        proof.pop("proof_sha256")
        proof["allowed_outcomes"] = [
            {
                "outcome_id": "stuck",
                "terminal": False,
                "strictly_decreases_measure": False,
            }
        ]
        proofs[oid] = _seal(proof)
        result = v2.audit(
            MANIFEST,
            BINDING,
            proofs,
            frozen_obligation_ids=FROZEN_IDS,
        )
        self.assertTrue(result["pass"])
        self.assertFalse(result["cc_r3_proved"])
        self.assertTrue(
            any(
                "OUTCOME_NOT_EXACTLY_TERMINAL_OR_DECREASING" in item
                for item in result["open_predicates"]
            )
        )

    def test_declared_count_mismatch_fails_closed(self):
        binding = deepcopy(BINDING)
        binding["shared_gaps"][v2.GAP_A]["obligation_count"] = 9
        result = v2.audit(
            MANIFEST,
            binding,
            frozen_obligation_ids=FROZEN_IDS,
        )
        self.assertFalse(result["pass"])
        self.assertFalse(result["cc_r3_proved"])
        self.assertTrue(
            any(
                "MANIFEST_BINDING_COUNT_MISMATCH" in item
                or "BINDING_SUCCESSOR_GAP_A_COUNT_MISMATCH" in item
                for item in result["errors"]
            )
        )

    def test_unknown_route_group_fails_closed(self):
        manifest = deepcopy(MANIFEST)
        manifest["rows"][0]["route_group"] = "UNKNOWN"
        result = v2.audit(
            manifest,
            BINDING,
            frozen_obligation_ids=FROZEN_IDS,
        )
        self.assertFalse(result["pass"])
        self.assertFalse(result["cc_r3_proved"])
        self.assertTrue(
            any("UNKNOWN_ROUTE_GROUP" in item for item in result["errors"])
        )

    def test_finance_reversion_to_gap_b_is_killed_by_current_counts(self):
        manifest = deepcopy(MANIFEST)
        finance = next(
            row
            for row in manifest["rows"]
            if row["obligation_id"] == "FINANCE_ACCOUNTING_INDEX_GE_61"
        )
        finance["route_group"] = v2.GAP_B
        result = v2.audit(
            manifest,
            BINDING,
            frozen_obligation_ids=FROZEN_IDS,
        )
        self.assertFalse(result["pass"])
        self.assertEqual(result["gap_a_count"], 9)
        self.assertEqual(result["gap_b_count"], 4)
        self.assertTrue(
            any("ROW_GROUP_COUNT_MISMATCH" in item for item in result["errors"])
        )

    def test_frozen_obligation_order_or_set_drift_fails_closed(self):
        manifest = deepcopy(MANIFEST)
        manifest["rows"][0], manifest["rows"][1] = (
            manifest["rows"][1],
            manifest["rows"][0],
        )
        result = v2.audit(
            manifest,
            BINDING,
            frozen_obligation_ids=FROZEN_IDS,
        )
        self.assertFalse(result["pass"])
        self.assertIn(
            "FROZEN_OBLIGATION_ORDER_OR_SET_DRIFT",
            result["errors"],
        )

    def test_unknown_proof_row_fails_closed(self):
        proofs = _proofs()
        proofs["NOT_A_FROZEN_ROW"] = _seal(
            {
                "obligation_id": "NOT_A_FROZEN_ROW",
                "route_group": v2.GAP_A,
                "currently_acquirable": True,
                "finite_outcome_ids": ["x"],
                "outcome_map_complete": True,
                "decision_region_size_before": 2,
                "max_nonterminal_decision_region_size_after": 1,
                "authenticated_truth_preserving": True,
                "safe": True,
            }
        )
        result = v2.audit(
            MANIFEST,
            BINDING,
            proofs,
            frozen_obligation_ids=FROZEN_IDS,
        )
        self.assertFalse(result["pass"])
        self.assertTrue(
            any("PROOFS_FOR_UNKNOWN_ROWS" in item for item in result["errors"])
        )

    def test_historical_v1_manifest_and_audit_are_unchanged_and_replayable(self):
        self.assertEqual(
            _git_blob(ROOT / v2.FROZEN_V1_MANIFEST_REL),
            v2.FROZEN_V1_MANIFEST_GIT_BLOB_SHA,
        )
        self.assertEqual(
            _git_blob(ROOT / v2.HISTORICAL_AUDIT_REL),
            v2.HISTORICAL_AUDIT_GIT_BLOB_SHA,
        )
        historical = v1.audit_repo()
        self.assertTrue(historical["pass"])
        self.assertFalse(historical["cc_r3_proved"])
        self.assertEqual(historical["gap_a_count"], 9)
        self.assertEqual(historical["gap_b_count"], 4)

    def test_repo_input_blob_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for rel in (
                v2.MANIFEST_REL,
                v2.BINDING_REL,
                v2.FROZEN_V1_MANIFEST_REL,
                v2.HISTORICAL_AUDIT_REL,
            ):
                src = ROOT / rel
                dst = root / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)

            manifest_path = root / v2.MANIFEST_REL
            manifest_path.write_text(
                manifest_path.read_text(encoding="utf-8") + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                v2.EscapeProgressAuditV2Error,
                "SOURCE_GIT_BLOB_DRIFT",
            ):
                v2.audit_repo(root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
