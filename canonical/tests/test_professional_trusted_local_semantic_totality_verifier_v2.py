from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
import unittest

from canonical.runtime import professional_trusted_local_semantic_totality_verifier_v2 as v


CLAIM_ID = "1" * 64
SCOPE_ID = "scope://professional-quality/whole-leaf/" + CLAIM_ID
OBLIGATION = "EXACT_TEST_SEMANTIC_OBLIGATION"


def row():
    return {
        "leaf_id": "PQ::R1_TARGET_SPECIFICATION::SEMANTIC",
        "root_id": "R1_TARGET_SPECIFICATION",
        "claim_id": CLAIM_ID,
        "claim_scope": {
            "leaf_acceptance": v.FULL_ACCEPTANCE,
            "scope_definition": {
                "domain_definition": {
                    "leaf_obligation": OBLIGATION,
                }
            },
        },
        "scope_certificate": {
            "scope_certificate": {
                "target_scope_id": SCOPE_ID,
            }
        },
    }


def batch():
    return {
        "pass": True,
        "rows": [row()],
        "unique_claim_id_count": 1,
    }


def blob(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def make(root: Path):
    problem_rel = "canonical/evidence/test-semantic-problem.json"
    verify_rel = "canonical/verification/test-semantic-problem-verify.json"
    cert_rel = "canonical/evidence/test-semantic-cert.json"
    problem_path = root / problem_rel
    verify_path = root / verify_rel
    cert_path = root / cert_rel
    for p in (problem_path, verify_path, cert_path):
        p.parent.mkdir(parents=True, exist_ok=True)

    bar_hash = hashlib.sha256(v.POSITIVE_BAR.encode()).hexdigest()
    exact = {
        "semantic_property_claim_id": CLAIM_ID,
        "semantic_scope_claim_id": SCOPE_ID,
        "semantic_obligation": OBLIGATION,
        "positive_semantic_bar": v.POSITIVE_BAR,
        "real_exact_run": True,
        "content_addressed": True,
    }
    cover_problem = {
        "state_id": "test-state",
        "worlds": [{"world_id": "w0"}],
        "world_set_completeness_receipt": {
            "independent_verified": True,
            "exact_byte_bound": True,
            "conclusion": "success",
            "policy_relevant_world_set_complete": True,
            "state_id": "test-state",
            "semantic_claim_id": CLAIM_ID,
            "claim_scoped_world_set_complete": True,
        },
        "policies": [{
            "policy_id": "p0",
            "adequate_world_ids": ["w0"],
            "cost_units": 1,
            "adequacy_receipt": {
                "independent_verified": True,
                "exact_byte_bound": True,
                "conclusion": "success",
                "policy_id": "p0",
                "policy_adequate_on_every_listed_world": True,
                "policy_safe_on_every_listed_world": True,
                "hard_constraint_scope_complete": True,
                "brain_owned": True,
                "deployed_exact": True,
                "resource_bound_proved": True,
                "semantic_claim_id": CLAIM_ID,
                "positive_semantic_bar_satisfied_on_every_listed_world": True,
                "positive_semantic_bar_sha256": bar_hash,
            },
        }],
        "discriminators": [],
    }
    problem = {**exact, "policy_cover_problem": cover_problem}
    problem_path.write_text(json.dumps(problem, sort_keys=True), encoding="utf-8")
    problem_sha = v._digest(problem)
    independent = {
        "pass": True,
        "independent_verified": True,
        "independent_verifier_id": "independent-test-verifier",
        "problem_sha256": problem_sha,
        "semantic_property_claim_id": CLAIM_ID,
        "semantic_scope_claim_id": SCOPE_ID,
        "positive_semantic_bar_sha256": bar_hash,
        "policy_relevant_world_set_complete": True,
        "policy_cover_replay_pass": True,
    }
    verify_path.write_text(json.dumps(independent, sort_keys=True), encoding="utf-8")
    cert = {
        "schema": v.CERT_SCHEMA,
        **exact,
        "policy_cover_problem_ref": {"path": problem_rel, "git_blob_sha": blob(problem_path)},
        "policy_cover_verification_ref": {"path": verify_rel, "git_blob_sha": blob(verify_path)},
        "policy_cover_problem_sha256": problem_sha,
    }
    cert_path.write_text(json.dumps(cert, sort_keys=True), encoding="utf-8")
    return cert_path, problem_path, verify_path


class Tests(unittest.TestCase):
    @patch.object(v.claim_batch, "verify")
    def test_exact_claim_bound_positive_witness_passes(self, verify):
        verify.return_value = batch()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cert, _, _ = make(root)
            out = v.verify_certificate(root=root, certificate_path=cert, expected_claim_id=CLAIM_ID)
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["local_positive_semantic_witness_verified"])
        self.assertTrue(out["semantic_positive_bar_bound"])
        self.assertFalse(out["whole_leaf_property_truth_authority"])
        self.assertFalse(out["terminal_authority"])

    @patch.object(v.claim_batch, "verify")
    def test_wrong_claim_id_fails(self, verify):
        verify.return_value = batch()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cert, _, _ = make(root)
            out = v.verify_certificate(root=root, certificate_path=cert, expected_claim_id="2" * 64)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "CLAIM_ID_NOT_UNIQUE_CURRENT_V2_V9_CLAIM")

    @patch.object(v.claim_batch, "verify")
    def test_positive_bar_overclaim_or_drift_fails(self, verify):
        verify.return_value = batch()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cert, _, _ = make(root)
            doc = json.loads(cert.read_text())
            doc["positive_semantic_bar"] = "WEAKER_BAR"
            cert.write_text(json.dumps(doc), encoding="utf-8")
            out = v.verify_certificate(root=root, certificate_path=cert, expected_claim_id=CLAIM_ID)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "CERTIFICATE_BINDING_MISMATCH:positive_semantic_bar")

    @patch.object(v.claim_batch, "verify")
    def test_policy_receipt_must_bind_claim(self, verify):
        verify.return_value = batch()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cert, problem, verify_path = make(root)
            p = json.loads(problem.read_text())
            p["policy_cover_problem"]["policies"][0]["adequacy_receipt"]["semantic_claim_id"] = "3" * 64
            problem.write_text(json.dumps(p, sort_keys=True), encoding="utf-8")
            c = json.loads(cert.read_text())
            c["policy_cover_problem_ref"]["git_blob_sha"] = blob(problem)
            c["policy_cover_problem_sha256"] = v._digest(p)
            cert.write_text(json.dumps(c), encoding="utf-8")
            out = v.verify_certificate(root=root, certificate_path=cert, expected_claim_id=CLAIM_ID)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "POLICY_ADEQUACY_CLAIM_MISMATCH")

    @patch.object(v.claim_batch, "verify")
    def test_independent_receipt_must_match_problem_digest(self, verify):
        verify.return_value = batch()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cert, _, verify_path = make(root)
            d = json.loads(verify_path.read_text())
            d["problem_sha256"] = "0" * 64
            verify_path.write_text(json.dumps(d, sort_keys=True), encoding="utf-8")
            c = json.loads(cert.read_text())
            c["policy_cover_verification_ref"]["git_blob_sha"] = blob(verify_path)
            cert.write_text(json.dumps(c), encoding="utf-8")
            out = v.verify_certificate(root=root, certificate_path=cert, expected_claim_id=CLAIM_ID)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "INDEPENDENT_VERIFY_MISMATCH:problem_sha256")

    @patch.object(v.claim_batch, "verify")
    def test_current_acceptance_drift_fails_closed(self, verify):
        b = batch()
        b["rows"][0]["claim_scope"]["leaf_acceptance"] = "OLD_OR_WEAKER_ACCEPTANCE"
        verify.return_value = b
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cert, _, _ = make(root)
            out = v.verify_certificate(root=root, certificate_path=cert, expected_claim_id=CLAIM_ID)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "CURRENT_CLAIM_ACCEPTANCE_DRIFT")


if __name__ == "__main__":
    unittest.main(verbosity=2)
