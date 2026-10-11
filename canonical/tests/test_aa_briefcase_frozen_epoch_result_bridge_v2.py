from __future__ import annotations

from hashlib import sha256
import json
import unittest

from canonical.runtime import aa_briefcase_frozen_epoch_result_bridge_v2 as m


def _sha(value):
    return sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def fixtures():
    reg = {"predicates": [
        {"id": m.PREDICATES[0], "surface": "AA-Briefcase v1.1", "acceptance": "AA-Briefcase v1.1 >= 1822 Elo"},
        {"id": m.PREDICATES[1], "surface": "AA-Briefcase v1.1", "acceptance": "AA-Briefcase v1.1 >= 1822 Elo"},
    ]}
    base = dict(m.EXPECTED)
    base["score"] = 1822
    binds = {
        "bindings": [dict(base, predicate_id=p) for p in m.PREDICATES],
        "shared_target_tuple": {"predicates": list(m.PREDICATES)},
    }
    root = {"predicates": [{"id": p, "class": "RELATIVE_RATING_THRESHOLD"} for p in m.PREDICATES]}
    subject = {
        "schema": m.SUBJECT_SCHEMA,
        "repository": "moxnixmdj/brain",
        "git_commit_sha": "a" * 40,
        "execution_profile_git_blob_sha": "b" * 40,
        "configuration_git_blob_sha": "c" * 40,
        "execution_bundle_sha256": "d" * 64,
    }
    subject_sha = _sha(subject)
    result = {
        "schema": m.RESULT_SCHEMA,
        "status": "VERIFIED_COMPARABLE_BRAIN_SCORE",
        "benchmark": "AA-Briefcase",
        "benchmark_version": "1.1",
        "evaluator": "Artificial Analysis",
        "harness": m.EXPECTED["harness"],
        "fallback_policy": m.EXPECTED["fallback_policy"],
        "unit": "Elo",
        "brain_score": 1822,
        "subject_sha256": subject_sha,
        "rating_epoch": m.FROZEN_RATING_EPOCH,
        "rating_epoch_verified": True,
        "opus55_reference_score": 1822,
        "evidence_sha256": "e" * 64,
        "result_source_kind": "OWNER_EVALUATOR",
        "result_source_uri": "https://artificialanalysis.ai/evaluations/aa-briefcase",
    }
    statement = _sha({
        "claim": "AA_BRIEFCASE_FROZEN_EPOCH_RESULT_AUTHENTICATED",
        "benchmark": m.EXPECTED["benchmark"],
        "benchmark_version": m.EXPECTED["benchmark_version"],
        "evaluator": m.EXPECTED["evaluator"],
        "harness": m.EXPECTED["harness"],
        "fallback_policy": m.EXPECTED["fallback_policy"],
        "unit": m.EXPECTED["unit"],
        "rating_epoch": m.FROZEN_RATING_EPOCH,
        "subject_sha256": subject_sha,
        "brain_score": 1822.0,
        "opus55_reference_score": 1822.0,
        "evidence_sha256": result["evidence_sha256"],
        "result_source_kind": result["result_source_kind"],
        "result_source_uri": result["result_source_uri"],
    })
    authority_payload = {
        "schema": m.AUTHORITY_SCHEMA,
        "verified": True,
        "source_kind": "OWNER_EVALUATOR",
        "verifier_id": "ARTIFICIAL_ANALYSIS_OWNER_EVALUATOR",
        "statement_sha256": statement,
        "evidence_sha256": result["evidence_sha256"],
        "verification_authority_mutated": False,
        "auth_method": "OWNER_PUBLISHED_RESULT",
        "auth_artifact_sha256": "f" * 64,
    }
    authority = {**authority_payload, "receipt_sha256": _sha(authority_payload)}
    return reg, binds, root, subject, result, authority


class T(unittest.TestCase):
    def test_exact_subject_authenticated_1822_passes_both(self):
        out = m.compile_hardened_bridge(*fixtures())
        self.assertEqual(out["predicate_results"], {p: True for p in m.PREDICATES})
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_below_threshold_fails_both(self):
        x = list(fixtures())
        x[4] = dict(x[4], brain_score=1821.9)
        subject_sha = x[4]["subject_sha256"]
        result = x[4]
        statement = _sha({
            "claim": "AA_BRIEFCASE_FROZEN_EPOCH_RESULT_AUTHENTICATED",
            "benchmark": m.EXPECTED["benchmark"],
            "benchmark_version": m.EXPECTED["benchmark_version"],
            "evaluator": m.EXPECTED["evaluator"],
            "harness": m.EXPECTED["harness"],
            "fallback_policy": m.EXPECTED["fallback_policy"],
            "unit": m.EXPECTED["unit"],
            "rating_epoch": m.FROZEN_RATING_EPOCH,
            "subject_sha256": subject_sha,
            "brain_score": 1821.9,
            "opus55_reference_score": 1822.0,
            "evidence_sha256": result["evidence_sha256"],
            "result_source_kind": result["result_source_kind"],
            "result_source_uri": result["result_source_uri"],
        })
        p = dict(x[5])
        p["statement_sha256"] = statement
        p["receipt_sha256"] = _sha({k: v for k, v in p.items() if k != "receipt_sha256"})
        x[5] = p
        self.assertFalse(any(m.compile_hardened_bridge(*x)["predicate_results"].values()))

    def test_result_for_other_subject_is_rejected(self):
        x = list(fixtures())
        x[4] = dict(x[4], subject_sha256="9" * 64)
        with self.assertRaisesRegex(m.BridgeError, "RESULT_SUBJECT_MISMATCH"):
            m.compile_hardened_bridge(*x)

    def test_forged_authority_digest_is_rejected(self):
        x = list(fixtures())
        x[5] = dict(x[5], receipt_sha256="0" * 64)
        with self.assertRaisesRegex(m.BridgeError, "RESULT_AUTHORITY_RECEIPT_INVALID"):
            m.compile_hardened_bridge(*x)

    def test_authority_bound_to_wrong_statement_is_rejected(self):
        x = list(fixtures())
        p = dict(x[5])
        p["statement_sha256"] = "1" * 64
        p["receipt_sha256"] = _sha({k: v for k, v in p.items() if k != "receipt_sha256"})
        x[5] = p
        with self.assertRaisesRegex(m.BridgeError, "RESULT_AUTHORITY_RECEIPT_INVALID"):
            m.compile_hardened_bridge(*x)

    def test_authority_evidence_mismatch_is_rejected(self):
        x = list(fixtures())
        p = dict(x[5])
        p["evidence_sha256"] = "2" * 64
        p["receipt_sha256"] = _sha({k: v for k, v in p.items() if k != "receipt_sha256"})
        x[5] = p
        with self.assertRaisesRegex(m.BridgeError, "RESULT_AUTHORITY_RECEIPT_INVALID"):
            m.compile_hardened_bridge(*x)

    def test_self_verification_is_rejected(self):
        x = list(fixtures())
        p = dict(x[5])
        p["verifier_id"] = "BRAIN"
        p["receipt_sha256"] = _sha({k: v for k, v in p.items() if k != "receipt_sha256"})
        x[5] = p
        with self.assertRaisesRegex(m.BridgeError, "RESULT_AUTHORITY_RECEIPT_INVALID"):
            m.compile_hardened_bridge(*x)

    def test_boolean_only_legacy_result_cannot_enter_v2(self):
        x = list(fixtures())
        x[4] = {
            "schema": "X",
            "status": "VERIFIED_COMPARABLE_BRAIN_SCORE",
            "independent_or_owner_verified": True,
            "brain_score": 1822,
        }
        with self.assertRaisesRegex(m.BridgeError, "RESULT_FIELDS_INVALID"):
            m.compile_hardened_bridge(*x)


if __name__ == "__main__":
    unittest.main(verbosity=2)
