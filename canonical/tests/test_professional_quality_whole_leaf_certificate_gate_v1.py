from __future__ import annotations
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import professional_quality_whole_leaf_certificate_gate_v1 as gate


LEAF = "PQ::R1_TARGET_SPECIFICATION::SEMANTIC"
CERT_BLOB = "a" * 40
VERIFIER_BLOB = "b" * 40
TESTS_BLOB = "c" * 40
TRANSCRIPT = "d" * 64


def scope_cert():
    return {
        "id": "PQ_R1_SEMANTIC_SCOPE_CERT_V1",
        "target_scope_id": LEAF,
        "basis": "UNIVERSAL_FORMAL_SCOPE_PROOF",
        "verified": True,
        "independent": True,
        "scope_relation": "EXACT",
        "formal_completeness": True,
        "all_admissible_target_inputs_proved": True,
        "premise_set_id": "content-addressed-premise-set-v1",
    }


def cert():
    return {
        "schema": gate.CERT_SCHEMA,
        "leaf_id": LEAF,
        "scope_certificate": scope_cert(),
        "evidence_refs": [
            {"path": "canonical/verification/source.json", "git_blob_sha": "e" * 40}
        ],
        "global_leaf_closure_claimed": False,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


def verification():
    return {
        "schema": gate.VERIFY_SCHEMA,
        "status": "PASS__INDEPENDENT_WHOLE_LEAF_SCOPE_SEMANTIC_VERIFICATION",
        "leaf_id": LEAF,
        "certificate_git_blob_sha": CERT_BLOB,
        "scope_compiler_git_blob_sha": gate.SCOPE_COMPILER_BLOB,
        "semantic_verifier_git_blob_sha": VERIFIER_BLOB,
        "semantic_tests_git_blob_sha": TESTS_BLOB,
        "scope_complete": True,
        "verified_basis": "UNIVERSAL_FORMAL_SCOPE_PROOF",
        "independent_replay": {"pass": True, "transcript_sha256": TRANSCRIPT},
        "semantic_truth_authority": False,
        "execution_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


def evaluate(c=None, v=None):
    return gate.evaluate_documents(
        certificate=c or cert(),
        verification=v or verification(),
        expected_leaf_id=LEAF,
        certificate_blob=CERT_BLOB,
        semantic_verifier_blob=VERIFIER_BLOB,
        semantic_tests_blob=TESTS_BLOB,
    )


class WholeLeafCertificateGateTests(unittest.TestCase):
    def test_valid_scope_certificate_admitted_without_property_or_quality_authority(self):
        out = evaluate()
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["whole_leaf_scope_complete"])
        self.assertFalse(out["leaf_property_truth_authority"])
        self.assertFalse(out["semantic_truth_authority"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["quality_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_universal_scope_compiler_rejection_is_load_bearing(self):
        c = cert()
        c["scope_certificate"]["all_admissible_target_inputs_proved"] = False
        out = evaluate(c=c)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "UNIVERSAL_SCOPE_COMPILER_REJECTED")

    def test_leaf_identity_drift_fails_closed(self):
        c = cert()
        c["leaf_id"] = "PQ::R2_CANDIDATE_SEARCH::SEMANTIC"
        out = evaluate(c=c)
        self.assertEqual(out["reason"], "CERT_LEAF_MISMATCH")

    def test_certificate_cannot_self_grant_global_leaf_closure(self):
        c = cert()
        c["global_leaf_closure_claimed"] = True
        out = evaluate(c=c)
        self.assertEqual(out["reason"], "CERT_GLOBAL_LEAF_SELF_CLAIM_FORBIDDEN")

    def test_certificate_cannot_self_grant_quality_authority(self):
        c = cert()
        c["quality_authority"] = True
        out = evaluate(c=c)
        self.assertEqual(out["reason"], "CERT_SELF_AUTHORITY_FORBIDDEN:quality_authority")

    def test_verification_must_bind_exact_certificate_blob(self):
        v = verification()
        v["certificate_git_blob_sha"] = "0" * 40
        out = evaluate(v=v)
        self.assertEqual(out["reason"], "VERIFY_CERTIFICATE_BLOB_MISMATCH")

    def test_verification_must_bind_exact_semantic_verifier_blob(self):
        v = verification()
        v["semantic_verifier_git_blob_sha"] = "0" * 40
        out = evaluate(v=v)
        self.assertEqual(out["reason"], "VERIFY_SEMANTIC_VERIFIER_BLOB_MISMATCH")

    def test_independent_replay_is_required(self):
        v = verification()
        v["independent_replay"]["pass"] = False
        out = evaluate(v=v)
        self.assertEqual(out["reason"], "INDEPENDENT_REPLAY_REQUIRED")

    def test_independent_replay_transcript_is_content_addressed(self):
        v = verification()
        v["independent_replay"]["transcript_sha256"] = "short"
        out = evaluate(v=v)
        self.assertEqual(out["reason"], "INDEPENDENT_REPLAY_TRANSCRIPT_INVALID")

    def test_verification_cannot_grant_terminal_authority(self):
        v = verification()
        v["terminal_authority"] = True
        out = evaluate(v=v)
        self.assertEqual(out["reason"], "VERIFY_AUTHORITY_OVERCLAIM:terminal_authority")

    def test_lossless_decomposition_child_open_fails_closed(self):
        c = cert()
        c["scope_certificate"] = {
            "id": "PQ_R1_DECOMP",
            "target_scope_id": LEAF,
            "basis": "LOSSLESS_DECOMPOSITION",
            "verified": True,
            "independent": True,
            "scope_relation": "EXACT",
            "coverage_complete": True,
            "coverage_relation": "EXACT_UNION",
            "coverage_proof_verified": True,
            "children": [{
                "id": "child",
                "target_scope_id": LEAF + "::child",
                "basis": "UNIVERSAL_FORMAL_SCOPE_PROOF",
                "verified": True,
                "independent": True,
                "scope_relation": "EXACT",
                "formal_completeness": False,
                "all_admissible_target_inputs_proved": False,
                "premise_set_id": "x",
            }],
        }
        v = verification()
        v["verified_basis"] = "LOSSLESS_DECOMPOSITION"
        out = evaluate(c=c, v=v)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "UNIVERSAL_SCOPE_COMPILER_REJECTED")

    def test_byte_resolver_accepts_exact_python_bytes_and_rejects_stale_hash(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "canonical/runtime/x.py"
            p.parent.mkdir(parents=True)
            p.write_text("x=1\n", encoding="utf-8")
            blob = gate._blob(p)
            path, actual, error = gate._resolve_bytes(
                root,
                {"path": "canonical/runtime/x.py", "git_blob_sha": blob},
                "X",
            )
            self.assertIsNone(error)
            self.assertEqual(path, p)
            self.assertEqual(actual, blob)
            _, _, error = gate._resolve_bytes(
                root,
                {"path": "canonical/runtime/x.py", "git_blob_sha": "0" * 40},
                "X",
            )
            self.assertEqual(error, "X_BLOB_STALE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
