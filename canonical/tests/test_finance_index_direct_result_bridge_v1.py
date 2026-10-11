from __future__ import annotations
import unittest

from canonical.runtime import finance_index_direct_result_bridge_v1 as bridge


def subject():
    return {
        "schema": bridge.SUBJECT_SCHEMA,
        "repository": "moxnixmdj/brain",
        "git_commit_sha": "1" * 40,
        "execution_profile_git_blob_sha": "2" * 40,
        "configuration_git_blob_sha": "3" * 40,
        "execution_bundle_sha256": "4" * 64,
    }


def bundle(
    score=61.0,
    *,
    rounded=False,
    source_kind="OWNER_EVALUATOR",
    source_uri="https://artificialanalysis.ai/results/brain",
):
    s = subject()
    sd = bridge.subject_digest(s)
    ev = "5" * 64
    result = {
        "schema": bridge.RESULT_SCHEMA,
        "status": "VERIFIED_COMPARABLE_BRAIN_SCORE",
        "benchmark": bridge.EXPECTED_BENCHMARK,
        "benchmark_version": bridge.EXPECTED_BENCHMARK_VERSION,
        "evaluator": bridge.EXPECTED_EVALUATOR,
        "unit": bridge.EXPECTED_UNIT,
        "score_scale": bridge.EXPECTED_SCORE_SCALE,
        "score_rounding_applied": rounded,
        "brain_score": score,
        "threshold": bridge.THRESHOLD,
        "subject_sha256": sd,
        "evidence_sha256": ev,
        "result_source_kind": source_kind,
        "result_source_uri": source_uri,
    }
    st = bridge.authority_statement_sha256(
        subject_sha256=sd,
        brain_score=float(score),
        evidence_sha256=ev,
        result_source_kind=source_kind,
        result_source_uri=source_uri,
    )
    authority = {
        "schema": bridge.AUTHORITY_SCHEMA,
        "verified": True,
        "source_kind": source_kind,
        "verifier_id": (
            "ARTIFICIAL_ANALYSIS"
            if source_kind == "OWNER_EVALUATOR"
            else "INDEPENDENT_VERIFIER_X"
        ),
        "statement_sha256": st,
        "evidence_sha256": ev,
        "verification_authority_mutated": False,
        "auth_method": (
            "OWNER_PUBLISHED_RESULT"
            if source_kind == "OWNER_EVALUATOR"
            else "INDEPENDENT_REPLAY"
        ),
        "auth_artifact_sha256": "6" * 64,
        "receipt_sha256": "",
    }
    authority["receipt_sha256"] = bridge._sha(
        {k: v for k, v in authority.items() if k != "receipt_sha256"}
    )
    return s, result, authority


class TestFinanceIndexDirectResultBridgeV1(unittest.TestCase):
    def test_exact_61_passes(self):
        out = bridge.compile_direct_result(*bundle(61.0))
        self.assertTrue(out["mathematically_sufficient"])

    def test_60_999_fails(self):
        out = bridge.compile_direct_result(*bundle(60.999))
        self.assertFalse(out["mathematically_sufficient"])

    def test_rounded_display_score_rejected(self):
        s, r, a = bundle(61.0, rounded=True)
        with self.assertRaisesRegex(
            bridge.FinanceIndexResultBridgeError,
            "ROUNDED_OR_DISPLAY_SCORE_FORBIDDEN",
        ):
            bridge.compile_direct_result(s, r, a)

    def test_wrong_subject_rejected(self):
        s, r, a = bundle()
        r["subject_sha256"] = "7" * 64
        with self.assertRaisesRegex(
            bridge.FinanceIndexResultBridgeError,
            "RESULT_SUBJECT_MISMATCH",
        ):
            bridge.compile_direct_result(s, r, a)

    def test_forged_authority_rejected(self):
        s, r, a = bundle()
        a["receipt_sha256"] = "8" * 64
        with self.assertRaisesRegex(
            bridge.FinanceIndexResultBridgeError,
            "RESULT_AUTHORITY_RECEIPT_INVALID",
        ):
            bridge.compile_direct_result(s, r, a)

    def test_self_verifier_rejected(self):
        s, r, a = bundle(
            source_kind="INDEPENDENT_VERIFIER",
            source_uri="https://verifier.example/result",
        )
        a["verifier_id"] = "BRAIN"
        a["receipt_sha256"] = bridge._sha(
            {k: v for k, v in a.items() if k != "receipt_sha256"}
        )
        with self.assertRaisesRegex(
            bridge.FinanceIndexResultBridgeError,
            "RESULT_AUTHORITY_RECEIPT_INVALID",
        ):
            bridge.compile_direct_result(s, r, a)

    def test_wrong_owner_host_rejected(self):
        s, r, a = bundle(source_uri="https://example.com/result")
        with self.assertRaisesRegex(
            bridge.FinanceIndexResultBridgeError,
            "OWNER_RESULT_SOURCE_NOT_ARTIFICIAL_ANALYSIS",
        ):
            bridge.compile_direct_result(s, r, a)

    def test_display_scale_rejected(self):
        s, r, a = bundle()
        r["score_scale"] = "DISPLAYED_ROUNDED_INDEX_POINTS"
        with self.assertRaisesRegex(
            bridge.FinanceIndexResultBridgeError,
            "RESULT_TUPLE_MISMATCH:score_scale",
        ):
            bridge.compile_direct_result(s, r, a)


if __name__ == "__main__":
    unittest.main(verbosity=2)
