"""Generic pairwise semantic non-identifiability kernel V1.

The kernel proves only a negative identification result:

If two independently authenticated, semantically distinct interpretations are
both compatible with the exact same source bytes, then that source alone cannot
uniquely identify one semantic interpretation.

This theorem does not require an exhaustive hypothesis universe. It does not
select a true interpretation, infer language semantics, or grant terminal
authority.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import re
from typing import Any, Callable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_SEMANTIC_PAIR_NONIDENTIFIABILITY_V1"
COMPATIBILITY_SCHEMA = (
    "PROJECT_BRAIN_SEMANTIC_INTERPRETATION_COMPATIBILITY_RECEIPT_V1"
)
DISTINCTNESS_SCHEMA = (
    "PROJECT_BRAIN_SEMANTIC_INTERPRETATION_DISTINCTNESS_RECEIPT_V1"
)
_SHA = re.compile(r"^[0-9a-f]{64}$")


def _base(status: str, *, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "semantic_nonidentifiability_authority": False,
        "semantic_truth_authority": False,
        "unique_semantic_identity_identified": False,
        "hypothesis_space_completeness_required": False,
        "open_world_semantic_completeness_claimed": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _verify_compatibility(
    raw: Any,
    *,
    source_id: str,
    source_sha256: str,
    verifier: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None,
) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(raw, Mapping) or not callable(verifier):
        return None, "COMPATIBILITY_RECEIPT_AND_VERIFIER_REQUIRED"
    out = verifier(deepcopy(dict(raw)))
    if not isinstance(out, Mapping):
        return None, "COMPATIBILITY_VERIFIER_RETURNED_NO_RECEIPT"
    out = deepcopy(dict(out))
    required = {
        "pass": True,
        "schema": COMPATIBILITY_SCHEMA,
        "source_id": source_id,
        "source_sha256": source_sha256,
        "source_compatible": True,
        "verification_authority_mutated": False,
    }
    bad = [k for k, v in required.items() if out.get(k) != v]
    iid = str(out.get("interpretation_id") or "").strip()
    sem = str(out.get("interpretation_semantics_sha256") or "").lower()
    receipt = str(out.get("receipt_sha256") or "").lower()
    if not iid:
        bad.append("interpretation_id")
    if _SHA.fullmatch(sem) is None:
        bad.append("interpretation_semantics_sha256")
    if _SHA.fullmatch(receipt) is None:
        bad.append("receipt_sha256")
    if bad:
        return out, "COMPATIBILITY_RECEIPT_BINDING_INVALID:" + ",".join(
            sorted(set(bad))
        )
    return out, None


def _verify_distinctness(
    raw: Any,
    *,
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    verifier: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None,
) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(raw, Mapping) or not callable(verifier):
        return None, "DISTINCTNESS_RECEIPT_AND_VERIFIER_REQUIRED"
    out = verifier(deepcopy(dict(raw)))
    if not isinstance(out, Mapping):
        return None, "DISTINCTNESS_VERIFIER_RETURNED_NO_RECEIPT"
    out = deepcopy(dict(out))

    expected_pairs = {
        (
            str(left["interpretation_id"]),
            str(left["interpretation_semantics_sha256"]),
            str(right["interpretation_id"]),
            str(right["interpretation_semantics_sha256"]),
        ),
        (
            str(right["interpretation_id"]),
            str(right["interpretation_semantics_sha256"]),
            str(left["interpretation_id"]),
            str(left["interpretation_semantics_sha256"]),
        ),
    }
    observed = (
        str(out.get("left_interpretation_id") or ""),
        str(out.get("left_semantics_sha256") or ""),
        str(out.get("right_interpretation_id") or ""),
        str(out.get("right_semantics_sha256") or ""),
    )
    bad = []
    required = {
        "pass": True,
        "schema": DISTINCTNESS_SCHEMA,
        "semantically_distinct": True,
        "verification_authority_mutated": False,
    }
    bad.extend(k for k, v in required.items() if out.get(k) != v)
    if observed not in expected_pairs:
        bad.append("interpretation_pair_binding")
    if left["interpretation_id"] == right["interpretation_id"]:
        bad.append("interpretation_ids_not_distinct")
    if left["interpretation_semantics_sha256"] == right["interpretation_semantics_sha256"]:
        bad.append("interpretation_semantics_not_distinct")
    if _SHA.fullmatch(str(out.get("receipt_sha256") or "").lower()) is None:
        bad.append("receipt_sha256")
    if bad:
        return out, "DISTINCTNESS_RECEIPT_BINDING_INVALID:" + ",".join(
            sorted(set(bad))
        )
    return out, None


def prove(
    *,
    source_id: str,
    source_text: str,
    compatibility_receipts: Sequence[Mapping[str, Any]],
    compatibility_verifier: Callable[[Mapping[str, Any]], Mapping[str, Any] | None],
    distinctness_receipt: Mapping[str, Any],
    distinctness_verifier: Callable[[Mapping[str, Any]], Mapping[str, Any] | None],
) -> dict[str, Any]:
    try:
        source_id = str(source_id or "").strip()
        if not source_id:
            return _base("FAIL_CLOSED", reason="SOURCE_ID_REQUIRED")
        if not isinstance(source_text, str) or not source_text:
            return _base("FAIL_CLOSED", reason="SOURCE_TEXT_REQUIRED")
        if (
            not isinstance(compatibility_receipts, Sequence)
            or isinstance(compatibility_receipts, (str, bytes))
            or len(compatibility_receipts) != 2
        ):
            return _base(
                "FAIL_CLOSED",
                reason="EXACTLY_TWO_COMPATIBILITY_RECEIPTS_REQUIRED",
            )

        source_sha = sha256(source_text.encode("utf-8")).hexdigest()
        checked = []
        for i, raw in enumerate(compatibility_receipts):
            out, error = _verify_compatibility(
                raw,
                source_id=source_id,
                source_sha256=source_sha,
                verifier=compatibility_verifier,
            )
            if error is not None or out is None:
                return _base(
                    "FAIL_CLOSED",
                    reason="COMPATIBILITY_RECEIPT_INVALID:"
                    + str(i)
                    + ":"
                    + str(error),
                    compatibility_result=out,
                )
            checked.append(out)

        distinct, error = _verify_distinctness(
            distinctness_receipt,
            left=checked[0],
            right=checked[1],
            verifier=distinctness_verifier,
        )
        if error is not None or distinct is None:
            return _base(
                "FAIL_CLOSED",
                reason="DISTINCTNESS_RECEIPT_INVALID:" + str(error),
                distinctness_result=distinct,
            )

        return _base(
            "PASS__PAIRWISE_SEMANTIC_NONIDENTIFIABILITY_PROVED",
            passed=True,
            semantic_nonidentifiability_authority=True,
            source_id=source_id,
            source_sha256=source_sha,
            witness_interpretation_ids=[
                checked[0]["interpretation_id"],
                checked[1]["interpretation_id"],
            ],
            compatibility_results=checked,
            distinctness_result=distinct,
            at_least_two_distinct_source_compatible_interpretations=True,
            unique_semantic_identity_identifiable_from_source_alone=False,
            additional_information_required_for_unique_identity=True,
            proof_rule=(
                "TWO_INDEPENDENTLY_AUTHENTICATED_SOURCE_COMPATIBLE_AND_"
                "SEMANTICALLY_DISTINCT_INTERPRETATIONS_REFUTE_UNIQUE_IDENTITY__"
                "NO_EXHAUSTIVE_HYPOTHESIS_UNIVERSE_REQUIRED"
            ),
            boundary=(
                "NEGATIVE_IDENTITY_RESULT_ONLY__DOES_NOT_SELECT_TRUE_INTERPRETATION__"
                "DOES_NOT_PROVE_DECISION_UNDERDETERMINATION_OR_OPEN_WORLD_COMPLETENESS"
            ),
        )
    except Exception as exc:
        return _base("FAIL_CLOSED", reason=type(exc).__name__ + ":" + str(exc))
