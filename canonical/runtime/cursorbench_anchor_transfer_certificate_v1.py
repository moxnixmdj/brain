#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from typing import Any, Mapping

TARGET = 0.578
ANCHOR_MODEL = "OPUS_5_5_MAX"
BENCHMARK = "CURSORBENCH_4_0"

class CertificateError(ValueError):
    pass

def _canonical_sha256(x: Any) -> str:
    raw = json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def verify_anchor_transfer(cert: Mapping[str, Any]) -> dict[str, Any]:
    if cert.get("benchmark") != BENCHMARK:
        raise CertificateError("BENCHMARK_MISMATCH")
    if cert.get("anchor_model") != ANCHOR_MODEL:
        raise CertificateError("ANCHOR_MODEL_MISMATCH")
    anchor = cert.get("anchor_score")
    if not isinstance(anchor, (int, float)) or isinstance(anchor, bool):
        raise CertificateError("ANCHOR_SCORE_MISSING_OR_INVALID")
    if abs(float(anchor) - TARGET) > 1e-12:
        raise CertificateError("ANCHOR_SCORE_MUST_EQUAL_0_578")

    route = cert.get("route")
    if route == "DIRECT_BRAIN_SCORE_LOWER_BOUND":
        lb = cert.get("brain_score_lower_bound")
        if not isinstance(lb, (int, float)) or isinstance(lb, bool):
            raise CertificateError("BRAIN_SCORE_LOWER_BOUND_MISSING_OR_INVALID")
        proved = float(lb) >= TARGET
        reason = "DIRECT_LOWER_BOUND"
    elif route == "TARGET_SCOPED_SCORE_NONINFERIORITY":
        same_eval = cert.get("same_frozen_evaluator_relation") is True
        noninferior = cert.get("brain_score_ge_anchor_score") is True
        proved = same_eval and noninferior
        reason = "ANCHOR_TRANSFER"
    elif route == "COMPLETE_SCORE_INPUT_EQUIVALENCE":
        same_func = cert.get("same_frozen_score_functional") is True
        complete = cert.get("complete_score_relevant_input_equivalence") is True
        proved = same_func and complete
        reason = "EXTENSIONAL_SCORE_EQUALITY"
    elif route == "INPUT_DOMINANCE_WITH_MONOTONICITY":
        same_func = cert.get("same_frozen_score_functional") is True
        dominance = cert.get("complete_score_relevant_input_dominance") is True
        monotone = cert.get("score_functional_monotonicity_proved") is True
        proved = same_func and dominance and monotone
        reason = "MONOTONE_DOMINANCE"
    else:
        raise CertificateError("UNSUPPORTED_ROUTE")

    evidence = cert.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        raise CertificateError("CONTENT_ADDRESSED_EVIDENCE_REQUIRED")
    for item in evidence:
        if not isinstance(item, Mapping):
            raise CertificateError("EVIDENCE_ITEM_INVALID")
        sha = item.get("sha256")
        if not isinstance(sha, str) or len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
            raise CertificateError("EVIDENCE_SHA256_INVALID")

    return {
        "schema": "PROJECT_BRAIN_CURSORBENCH_ANCHOR_TRANSFER_CERTIFICATE_RESULT_V1",
        "benchmark": BENCHMARK,
        "anchor_model": ANCHOR_MODEL,
        "anchor_score": TARGET,
        "route": route,
        "threshold_met": bool(proved),
        "reason": reason,
        "certificate_sha256": _canonical_sha256(cert),
        "credit_allowed": bool(proved),
    }

if __name__ == "__main__":
    import sys
    cert = json.load(sys.stdin)
    print(json.dumps(verify_anchor_transfer(cert), sort_keys=True))
