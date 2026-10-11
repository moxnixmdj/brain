from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import current_escape_o_objective_acceptance_law_gate_v2 as gate

GDP = "PROWORK_GDPVAL_GE_1846"
AA = "PROWORK_AA_BRIEFCASE_GE_1822__SHARED_MEASUREMENT_WITH_ARTIFACT"
TB = "TB_SCIENCE_GE_58_7"
CURSOR = "CODING_CURSORBENCH_GE_57_8"
OTHER_O = [
    "CODING_TB4_GE_66_4",
    "CODING_FRONTIERCODE_GE_54_4",
    CURSOR,
    GDP,
    "AUTOMATIONBENCH_GE_40",
    "HLE_TOOLS_GE_67_7",
    "CHARTOGRAPHY_TOOLS_GE_89",
    "OSWORLD_2_1_PARTIAL_GE_81_8",
    "FINANCE_ACCOUNTING_INDEX_GE_61",
    "FINANCE_AGENT_V2_GE_58_59",
    "MYSTERYMECHANISM_INTRINSIC_OPUS55_NONINFERIORITY_OR_STRONGER",
]


def _blob(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _write(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def make_repo(root: Path, *, o=None, q=None, parked=None, corrupt_count=False) -> None:
    o = list(OTHER_O if o is None else o)
    q = [AA] if q is None else list(q)
    parked = [TB] if parked is None else list(parked)
    all_ids = o + q + parked

    manifest_rel = "canonical/governance/ESCAPE_PROGRESS_13_REACHED_STATE_ROUTE_MANIFEST_20261010_V2.json"
    manifest = root / manifest_rel
    _write(manifest, {
        "schema": gate.MANIFEST_SCHEMA,
        "rows": [{"obligation_id": x} for x in all_ids],
    })

    verify_rel = "canonical/verification/GDPVAL_FIXED_BAR_OWNER_PAIRWISE_NONNECESSITY_VERIFICATION_20261009_V1.json"
    verify_path = root / verify_rel
    _write(verify_path, {
        "schema": gate.GDPVAL_VERIFY_SCHEMA,
        "status": "PASS__SOURCE_BINDINGS_CURRENT__WOLFRAM_SYMBOLIC_NONNECESSITY_TRUE__ZERO_CREDIT",
        "conclusion": "EXACT_OWNER_PAIRWISE_SEMANTICS_IS_NOT_NECESSARY_FOR_CURRENT_FIXED_BAR_E1_ACCEPTANCE__PRESERVE_AS_DORMANT_ALTERNATIVE_ROUTE_ONLY",
    })

    reclass_rel = "canonical/governance/GDPVAL_CURRENT_FIXED_BAR_ENGINE_RECLASSIFICATION_20261011_V1.json"
    reclass_path = root / reclass_rel
    _write(reclass_path, {
        "schema": gate.GDPVAL_RECLASS_SCHEMA,
        "status": "CURRENT_PRIMARY_ROUTE_RECLASSIFIED__GDPVAL_MOVED_Q_TO_O_FOR_FIXED_BAR_E1__ZERO_CREDIT",
        "target_obligation": GDP,
        "source_bindings": {
            "fixed_bar_nonnecessity_verification": {
                "path": verify_rel,
                "git_blob_sha": _blob(verify_path),
            }
        },
        "current_acceptance_shape": {
            "acceptance_relation_class": "OBJECTIVE_FIXED_BAR",
            "hidden_owner_pairwise_relation_is_free_variable_of_decision": False,
        },
        "engine_effect": {
            "previous": "Q_ACCEPTANCE_RELATION_ROBUST_COMMON_POLICY",
            "current": "O_OBJECTIVE_ACCEPTANCE_INSTANTIATION",
            "new_primitive_required": False,
        },
    })

    cut_rel = gate.CUT_PATH.as_posix()
    cut_path = root / cut_rel
    cut_status = "CURRENT_ACTIVE_ESCAPE_COLLAPSED_TO_TWO_REUSE_ENGINES__O11_ACTIVE__Q1_ACTIVE__TB_PARKED__GDPVAL_FIXED_BAR_RECLASSIFIED_Q_TO_O__ZERO_CREDIT"
    _write(cut_path, {
        "schema": gate.CUT_SCHEMA,
        "status": cut_status,
        "source_bindings": {
            "manifest": [manifest_rel, _blob(manifest)],
            "gdpval_fixed_bar_reclassification": [reclass_rel, _blob(reclass_path)],
        },
        "current_partition": {
            "total_escape_rows": len(all_ids),
            "active_rows": (len(o) + len(q) + 1) if corrupt_count else len(o) + len(q),
            "parked_rows": len(parked),
            "active_gap_b_rows": 0,
            "active_o_rows": len(o),
            "active_q_rows": len(q),
            "active_o_obligation_ids": o,
            "active_q_obligation_ids": q,
            "parked_obligation_ids": parked,
        },
    })

    _write(root / gate.CURRENT_RESIDUAL_PATH, {
        "schema": gate.CURRENT_RESIDUAL_SCHEMA,
        "status": "DERIVED_CURRENT_CLASSIFICATION__TEST",
        "escape_current_topology": {
            "frozen_obligation_count": 13,
            "active_gap_a_acquisition_rows": 12,
            "active_gap_b_strict_progress_rows": 0,
            "parked_unresolved_rows": 1,
            "parked_obligation_ids": [TB],
        },
        "current_escape_two_engine_minimum_delta_cut": {
            "path": cut_rel,
            "git_blob_sha": _blob(cut_path),
            "status": cut_status,
        },
    })

def claim(oid: str) -> dict:
    return {"policy": {"predicate_id": oid}, "evidence": {}, "current_identity": {}}


class CurrentProjectionGateTests(unittest.TestCase):
    def test_projection_is_exact_11_o_1_q_1_parked(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            make_repo(root)
            o, q, parked, _ = gate._current_projection(root)
            self.assertEqual(len(o), 11)
            self.assertEqual(q, {AA})
            self.assertEqual(parked, {TB})
            self.assertIn(GDP, o)

    @patch.object(gate, "evaluate_claim")
    def test_gdpval_is_now_admitted_as_o(self, kernel):
        kernel.return_value = {"status": "PROVEN", "reason": "ok"}
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); make_repo(root)
            out = gate.evaluate({"obligation_id": GDP, "claim_spec": claim(GDP)}, repo_root=root)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["status"], "PASS__CURRENT_O_OBJECTIVE_ACCEPTANCE_LAW_PROOF_READY")
        self.assertEqual(out["current_o_count"], 11)
        self.assertEqual(out["current_q_count"], 1)
        self.assertEqual(out["current_parked_count"], 1)
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["terminal_authority"])

    @patch.object(gate, "evaluate_claim")
    def test_ordinary_o_row_still_routes_to_kernel(self, kernel):
        kernel.return_value = {"status": "PROVEN", "reason": "ok"}
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); make_repo(root)
            out = gate.evaluate({"obligation_id": CURSOR, "claim_spec": claim(CURSOR)}, repo_root=root)
        self.assertTrue(out["pass"])
        kernel.assert_called_once()

    def test_aa_rejected_as_current_q(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); make_repo(root)
            out = gate.evaluate({"obligation_id": AA, "claim_spec": claim(AA)}, repo_root=root)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "NOT_APPLICABLE__CURRENT_Q_ROW")

    def test_tb_rejected_as_current_parked(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); make_repo(root)
            out = gate.evaluate({"obligation_id": TB, "claim_spec": claim(TB)}, repo_root=root)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "NOT_APPLICABLE__CURRENT_PARKED_ROW")

    def test_predicate_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); make_repo(root)
            out = gate.evaluate({"obligation_id": GDP, "claim_spec": claim(CURSOR)}, repo_root=root)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "CLAIM_PREDICATE_ID_MISMATCH")

    @patch.object(gate, "evaluate_claim")
    def test_kernel_unknown_stays_open_zero_credit(self, kernel):
        kernel.return_value = {"status": "UNKNOWN", "reason": "SCOPE_RECEIPT_MISSING"}
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); make_repo(root)
            out = gate.evaluate({"obligation_id": GDP, "claim_spec": claim(GDP)}, repo_root=root)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "OPEN__CURRENT_O_OBJECTIVE_ACCEPTANCE")
        self.assertEqual(out["reason"], "SCOPE_RECEIPT_MISSING")
        self.assertEqual(out["acceptance_credit_delta"], 0)
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_partition_count_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); make_repo(root, corrupt_count=True)
            out = gate.evaluate({"obligation_id": GDP, "claim_spec": claim(GDP)}, repo_root=root)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("CURRENT_ACTIVE_COUNT_MISMATCH", out["reason"])

    def test_manifest_binding_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); make_repo(root)
            manifest = root / "canonical/governance/ESCAPE_PROGRESS_13_REACHED_STATE_ROUTE_MANIFEST_20261010_V2.json"
            manifest.write_text(manifest.read_text() + "\n", encoding="utf-8")
            out = gate.evaluate({"obligation_id": GDP, "claim_spec": claim(GDP)}, repo_root=root)
        self.assertFalse(out["pass"])
        self.assertIn("CURRENT_CUT_MANIFEST_BLOB_DRIFT", out["reason"])

    def test_current_residual_cut_pointer_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); make_repo(root)
            current_path = root / gate.CURRENT_RESIDUAL_PATH
            current = json.loads(current_path.read_text(encoding="utf-8"))
            current["current_escape_two_engine_minimum_delta_cut"]["git_blob_sha"] = "0" * 40
            _write(current_path, current)
            out = gate.evaluate({"obligation_id": GDP, "claim_spec": claim(GDP)}, repo_root=root)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("CURRENT_TWO_ENGINE_CUT_BLOB_DRIFT", out["reason"])

    def test_gdpval_reclassification_verification_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); make_repo(root)
            verify_path = root / "canonical/verification/GDPVAL_FIXED_BAR_OWNER_PAIRWISE_NONNECESSITY_VERIFICATION_20261009_V1.json"
            verify_path.write_text(verify_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            out = gate.evaluate({"obligation_id": GDP, "claim_spec": claim(GDP)}, repo_root=root)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("GDPVAL_RECLASSIFICATION_VERIFICATION_BLOB_DRIFT", out["reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
