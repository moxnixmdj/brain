from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime.coverage_claim_scope_guard_v1 import compute_claim_id
from canonical.runtime import claim_instance_assurance_binder_v1 as binder
from canonical.runtime import claim_instance_assurance_runtime_v1 as runtime


def _mission(root: Path) -> str:
    path = root / "canonical/governance/CURRENT_MISSION_OBJECTIVE.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema": "MISSION", "status": "ACTIVE"}))
    return binder.git_blob_sha(path.read_bytes())


def _receipt():
    return {
        "schema": binder.R7_RECEIPT_SCHEMA,
        "status": "PASS__REAL_PROFESSIONAL_CODE_EDIT_AB__OLD_FAIL_NEW_PASS__CLAIM_SCOPED_R7_CAUSAL_INSTANCE__ZERO_TERMINAL_CREDIT",
        "root_id": binder.R7_ROOT,
        "claim_scope": {
            "kind": "EXACT_SINGLE_EDIT_PROFESSIONAL_CODE_INTERVENTION_INSTANCE",
            "artifact": "canonical/runtime/assurance_closure_compiler_v1.py",
            "intervention": "MAKE_SUPPORTED_DEFEATER_DOMINANCE_ORDER_INDEPENDENT",
            "claimed_effect": "THE_ORDER_REGRESSION_TEST_CHANGES_FROM_FAIL_ON_PREDECESSOR_TO_PASS_ON_REPAIRED_RUNTIME",
            "reusable_global_design_rule_claimed": False,
        },
        "r7_defeater_disposition": {
            "C28_PREDICTIVE_PRESCRIPTIVE_GAP": {
                "claim_scoped_state": "DISCHARGED_FOR_THIS_EXACT_INSTANCE"
            },
            "C29_COMPOUND_EDIT_ATTRIBUTION": {
                "claim_scoped_state": "PROVEN_IRRELEVANT_TO_THIS_CLAIM_SCOPE"
            },
            "C30_TREATMENT_VERSION_NONINVARIANCE": {
                "claim_scoped_state": "DISCHARGED_FOR_THIS_EXACT_INSTANCE"
            },
            "C31_EDIT_SEQUENCE_INTERACTION": {
                "claim_scoped_state": "PROVEN_IRRELEVANT_TO_THIS_CLAIM_SCOPE"
            },
        },
        "conclusions": {
            "exact_claim_scoped_professional_edit_causality_proved": True,
            "r7_global_root_closed": False,
        },
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


def _claim(receipt, mission_sha):
    claim = {
        "claim_kind": "PROPERTY_CERTIFICATE",
        "mission_blob_sha": mission_sha,
        "scope_sha256": binder.sha256_value(receipt["claim_scope"]),
        "target_predicate_sha256": binder.sha256_value(
            receipt["claim_scope"]["claimed_effect"]
        ),
        "semantics_sha256": binder.sha256_value(receipt["r7_defeater_disposition"]),
        "epoch": "2026-10-10",
        "authority_id": "PROJECT_BRAIN_CURRENT_MISSION_OBJECTIVE",
        "terminal_credit_delta": 0,
    }
    claim["claim_id"] = compute_claim_id(claim)
    return claim


def _bundle(root: Path, *, mission_sha: str | None = None):
    actual_mission = _mission(root)
    r = _receipt()
    path = root / "canonical/verification/r7.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(r, indent=2) + "\n").encode()
    path.write_bytes(raw)
    return {
        "schema": binder.BUNDLE_SCHEMA,
        "claim": _claim(r, mission_sha or actual_mission),
        "required_root_ids": [binder.R7_ROOT],
        "evidence": [{
            "adapter_id": "PROFESSIONAL_QUALITY_R7_SINGLE_EDIT_CAUSAL_INSTANCE_V1",
            "path": "canonical/verification/r7.json",
            "git_blob_sha": binder.git_blob_sha(raw),
        }],
    }


class ClaimInstanceAssuranceRuntimeV1Tests(unittest.TestCase):
    def test_exact_current_mission_claim_closes_all_four_gates(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out = runtime.evaluate(_bundle(root), repo_root=root)
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["status"], "PASS__FROZEN_CLAIM_INSTANCE_ASSURANCE_CLOSED"
        )
        self.assertTrue(out["representation_closure"])
        self.assertTrue(out["proof_closure"])
        self.assertTrue(out["execution_closure"])
        self.assertTrue(out["adversarial_closure"])
        self.assertEqual(out["closure_scope"], "FROZEN_CLAIM_INSTANCE_ONLY")
        self.assertFalse(out["global_domain_closure"])
        self.assertFalse(out["global_mission_completion_derivable"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_stale_mission_claim_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out = runtime.evaluate(
                _bundle(root, mission_sha="0" * 40),
                repo_root=root,
            )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "CLAIM_SCOPE_INVALID")
        self.assertIn(
            "MISSION_BINDING_STALE",
            out["binder_result"]["claim_errors"],
        )

    def test_tampered_evidence_bytes_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bundle = _bundle(root)
            (root / bundle["evidence"][0]["path"]).write_text("{}\n")
            out = runtime.evaluate(bundle, repo_root=root)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "EVIDENCE_GIT_BLOB_SHA_MISMATCH")

    def test_unregistered_adapter_cannot_create_assurance(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bundle = _bundle(root)
            bundle["evidence"][0]["adapter_id"] = "CALLER_ASSERTS_ASSURED"
            out = runtime.evaluate(bundle, repo_root=root)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "EVIDENCE_ADAPTER_UNREGISTERED")

    def test_global_claim_kind_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bundle = _bundle(root)
            bundle["claim"]["claim_kind"] = "GLOBAL_OPEN_ENDED_MISSION_COMPLETE"
            bundle["claim"]["claim_id"] = compute_claim_id(bundle["claim"])
            out = runtime.evaluate(bundle, repo_root=root)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "CLAIM_SCOPE_INVALID")
        self.assertIn("CLAIM_KIND_NOT_ALLOWED", out["binder_result"]["claim_errors"])


if __name__ == "__main__":
    unittest.main()
