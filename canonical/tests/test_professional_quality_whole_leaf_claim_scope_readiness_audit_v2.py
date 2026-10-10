from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import professional_quality_whole_leaf_claim_scope_readiness_audit_v2 as a


def blob(p: Path) -> str:
    raw = p.read_bytes()
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def write(p: Path, value) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        value if isinstance(value, str) else json.dumps(value, indent=2) + "\n",
        encoding="utf-8",
    )


def setup_repo():
    td = tempfile.TemporaryDirectory()
    root = Path(td.name)
    ledger = root / a.LEDGER_PATH
    write(ledger, {"leaves": [{"leaf_id": "L1"}, {"leaf_id": "L2"}]})
    old = a.LEDGER_BLOB
    a.LEDGER_BLOB = blob(ledger)
    return td, root, old


def write_v2_quartet(root: Path, leaf: str = "L1") -> None:
    write(root / "canonical/governance/claim.json", {
        "schema": a.gate.CLAIM_SCOPE_SCHEMA, "leaf_id": leaf
    })
    write(root / "canonical/verification/claim_verify.json", {
        "schema": a.gate.CLAIM_VERIFY_SCHEMA, "leaf_id": leaf
    })
    write(root / "canonical/governance/cert.json", {
        "schema": a.gate.CERT_SCHEMA, "leaf_id": leaf
    })
    write(root / "canonical/verification/cert_verify.json", {
        "schema": a.gate.CERT_VERIFY_SCHEMA, "leaf_id": leaf
    })


class WholeLeafClaimScopeReadinessAuditV2Tests(unittest.TestCase):
    def test_no_candidates_requires_claim_scope_or_totality(self):
        td, root, old = setup_repo()
        try:
            out = a.audit(repo_root=root)
            self.assertTrue(out["pass"], out)
            self.assertEqual(out["leaf_count"], 2)
            self.assertEqual(out["admissible_scope_certificate_count"], 0)
            self.assertEqual(out["claim_scope_or_totality_required_count"], 2)
            self.assertTrue(all(
                x["state"] == "CLAIM_SCOPE_OR_TOTALITY_PROOF_REQUIRED"
                for x in out["leaves"]
            ))
        finally:
            a.LEDGER_BLOB = old
            td.cleanup()

    def test_partial_v2_quartet_fails_closed_per_leaf(self):
        td, root, old = setup_repo()
        try:
            write(root / "canonical/governance/claim.json", {
                "schema": a.gate.CLAIM_SCOPE_SCHEMA, "leaf_id": "L1"
            })
            out = a.audit(repo_root=root)
            row = next(x for x in out["leaves"] if x["leaf_id"] == "L1")
            self.assertEqual(
                row["state"],
                "FAIL_CLOSED_AMBIGUOUS_OR_INCOMPLETE_V2_CANDIDATE_SET",
            )
            self.assertFalse(row["whole_leaf_scope_complete"])
        finally:
            a.LEDGER_BLOB = old
            td.cleanup()

    def test_legacy_v1_certificate_pair_has_zero_v2_admission_authority(self):
        td, root, old = setup_repo()
        try:
            write(root / "canonical/governance/legacy_cert.json", {
                "schema": "PROJECT_BRAIN_PROFESSIONAL_QUALITY_WHOLE_LEAF_SCOPE_CERTIFICATE_V1",
                "leaf_id": "L1",
            })
            write(root / "canonical/verification/legacy_verify.json", {
                "schema": "PROJECT_BRAIN_PROFESSIONAL_QUALITY_WHOLE_LEAF_SCOPE_SEMANTIC_VERIFY_V1",
                "leaf_id": "L1",
            })
            out = a.audit(repo_root=root)
            row = next(x for x in out["leaves"] if x["leaf_id"] == "L1")
            self.assertEqual(row["state"], "CLAIM_SCOPE_OR_TOTALITY_PROOF_REQUIRED")
            self.assertFalse(out["legacy_v1_artifacts_have_v2_admission_authority"])
            self.assertEqual(out["admissible_scope_certificate_count"], 0)
        finally:
            a.LEDGER_BLOB = old
            td.cleanup()

    def test_exact_v2_quartet_delegates_to_claim_scoped_gate(self):
        td, root, old = setup_repo()
        try:
            write_v2_quartet(root)
            with patch.object(a.gate, "verify_entry", return_value={
                "pass": True,
                "status": "PASS__TEST_V2",
                "whole_leaf_domain_equivalence_proved": True,
                "whole_leaf_scope_complete": True,
            }) as verify:
                out = a.audit(repo_root=root)
            row = next(x for x in out["leaves"] if x["leaf_id"] == "L1")
            self.assertEqual(
                row["state"],
                "ADMISSIBLE_V2_CLAIM_SCOPE_AND_SCOPE_CERTIFICATE",
            )
            self.assertTrue(row["whole_leaf_domain_equivalence_proved"])
            self.assertTrue(row["whole_leaf_scope_complete"])
            self.assertEqual(out["admissible_claim_scope_count"], 1)
            self.assertEqual(out["admissible_scope_certificate_count"], 1)
            verify.assert_called_once()
        finally:
            a.LEDGER_BLOB = old
            td.cleanup()

    def test_gate_rejection_remains_rejected(self):
        td, root, old = setup_repo()
        try:
            write_v2_quartet(root)
            with patch.object(a.gate, "verify_entry", return_value={
                "pass": False,
                "status": "FAIL_CLOSED",
                "reason": "WHOLE_LEAF_DOMAIN_EQUIVALENCE_REQUIRED",
                "whole_leaf_domain_equivalence_proved": False,
                "whole_leaf_scope_complete": False,
            }):
                out = a.audit(repo_root=root)
            row = next(x for x in out["leaves"] if x["leaf_id"] == "L1")
            self.assertEqual(
                row["state"],
                "V2_CANDIDATE_REJECTED_BY_CLAIM_SCOPED_GATE",
            )
            self.assertEqual(
                row["gate_reason"],
                "WHOLE_LEAF_DOMAIN_EQUIVALENCE_REQUIRED",
            )
            self.assertEqual(out["admissible_scope_certificate_count"], 0)
        finally:
            a.LEDGER_BLOB = old
            td.cleanup()

    def test_stale_ledger_fails_closed(self):
        td, root, old = setup_repo()
        try:
            a.LEDGER_BLOB = "0" * 40
            out = a.audit(repo_root=root)
            self.assertFalse(out["pass"])
            self.assertEqual(out["reason"], "WHOLE_LEAF_LEDGER_STALE")
        finally:
            a.LEDGER_BLOB = old
            td.cleanup()


if __name__ == "__main__":
    unittest.main(verbosity=2)
