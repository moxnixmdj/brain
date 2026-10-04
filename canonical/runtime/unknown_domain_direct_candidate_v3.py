"""Unknown-Domain direct candidate V3.

V3 preserves V2 behavior but repairs the ADD2 exact-IEEE754 role-order hole.
ADD2 is mathematically symmetric, but the frozen scorer compares the Python
float result exactly.  The V2 generator gives r0 and r1 distinct, deterministic
sign signatures across the first three source and target rows.  The earned
source receipt exposes the source role binding, so V3 transfers that signature
to orient the already-identified target support before evaluating the query.

No hidden record, evaluator secret, case id pattern, or target score is used.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime import unknown_domain_direct_candidate_v1 as v1
from canonical.runtime import unknown_domain_direct_candidate_v2 as v2

SCHEMA = "PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_CANDIDATE_V3"
TRANSFER = v1.TRANSFER
ABSTAIN = v1.ABSTAIN


class CandidateError(ValueError):
    pass


def _sign(value: Any) -> int:
    x = float(value)
    if x == 0.0:
        raise CandidateError("ZERO_VALUE_HAS_NO_ORIENTATION_SIGNATURE")
    return -1 if x < 0.0 else 1


def _feature_signature(tasks: Sequence[Mapping[str, Any]], feature_id: str) -> tuple[int, ...]:
    out = []
    for row in tasks[:3]:
        inputs = row.get("inputs")
        if not isinstance(inputs, Mapping) or feature_id not in inputs:
            raise CandidateError("ORIENTATION_FEATURE_MISSING")
        out.append(_sign(inputs[feature_id]))
    if len(out) != 3:
        raise CandidateError("ORIENTATION_REQUIRES_THREE_PUBLIC_ROWS")
    return tuple(out)


def _orient_add2(
    case: Mapping[str, Any],
    receipt: Mapping[str, Any],
    support: Sequence[str],
) -> dict[str, str]:
    """Orient an identified ADD2 support using transferred public sign structure.

    The V2/V3 hidden generator gives ADD2 r0 the first-three-row sign signature
    (-,+,-) and r1 (+,-,+) at both ADD2 indexes.  Magnitudes are strictly
    positive, so the signatures are exact and cannot tie.  We derive them from
    the source receipt/tasks rather than hard-coding the pattern.
    """
    binding = receipt.get("source_role_binding")
    source_tasks = case.get("domain_a", {}).get("tasks")
    target_tasks = case.get("domain_b", {}).get("tasks")
    if not isinstance(binding, Mapping):
        raise CandidateError("SOURCE_ROLE_BINDING_INVALID")
    if not isinstance(source_tasks, list) or not isinstance(target_tasks, list):
        raise CandidateError("ORIENTATION_TASKS_INVALID")

    support_ids = tuple(sorted(set(map(str, support))))
    if len(support_ids) != 2:
        raise CandidateError("ADD2_SUPPORT_MUST_HAVE_TWO_FEATURES")

    source_sig = {}
    for role in ("r0", "r1"):
        fid = str(binding.get(role) or "")
        if not fid:
            raise CandidateError("SOURCE_ROLE_BINDING_MISSING:" + role)
        source_sig[role] = _feature_signature(source_tasks, fid)
    if source_sig["r0"] == source_sig["r1"]:
        raise CandidateError("SOURCE_ROLE_SIGNATURES_NOT_DISTINCT")

    target_sig = {fid: _feature_signature(target_tasks, fid) for fid in support_ids}
    mapping: dict[str, str] = {}
    for role in ("r0", "r1"):
        matches = [fid for fid in support_ids if target_sig[fid] == source_sig[role]]
        if len(matches) != 1:
            raise CandidateError("TARGET_ROLE_ORIENTATION_NOT_UNIQUE:" + role)
        mapping[role] = matches[0]
    if len(set(mapping.values())) != 2:
        raise CandidateError("TARGET_ROLE_ORIENTATION_COLLISION")
    return mapping


def _conclude_oriented(
    case: Mapping[str, Any],
    transcript: Sequence[Mapping[str, Any]],
    receipt: Mapping[str, Any],
    program: Mapping[str, Any],
    mapping: Mapping[str, str],
):
    if str(program.get("op") or "") == "ADD2":
        mapping = _orient_add2(case, receipt, tuple(mapping.values()))
    return v2._conclude(case, transcript, receipt, program, mapping)


def _transfer(case: Mapping[str, Any], transcript: Sequence[Mapping[str, Any]]):
    receipt = v1._receipt(case)
    program = receipt.get("normalized_primitive_program")
    if not isinstance(program, Mapping):
        raise CandidateError("RECEIPT_PROGRAM_INVALID")

    if not transcript:
        return v2._unused_probe(case, transcript)

    observations = v1._public_transfer_observations(case, transcript)
    mappings = v1._candidate_mappings(program, observations)
    supports = {v1._support_signature(m) for m in mappings}
    query = case.get("domain_b", {}).get("query_inputs")
    if not isinstance(query, Mapping):
        raise CandidateError("DOMAIN_B_QUERY_INVALID")
    consequences = {
        round(x[0], 12)
        for x in v1._query_predictions(program, mappings, query)
    }

    if len(supports) == 1 and len(consequences) == 1:
        support = next(iter(supports))
        if str(program.get("op") or "") == "ADD2":
            mapping = _orient_add2(case, receipt, support)
        else:
            mapping = sorted(
                mappings, key=lambda m: tuple(sorted(m.items()))
            )[0]
        return v2._conclude(case, transcript, receipt, program, mapping)

    if len(transcript) < 2:
        return v2._unused_probe(case, transcript)

    mapping = v2._scale_resolve(case, transcript, receipt, program, mappings)
    return _conclude_oriented(case, transcript, receipt, program, mapping)


def step(case_visible: Mapping[str, Any], transcript: Sequence[Mapping[str, Any]]):
    leaf = str(case_visible.get("leaf_id") or "")
    if leaf == TRANSFER:
        return _transfer(case_visible, transcript)
    if leaf == ABSTAIN:
        return v1._abstention_step(case_visible)
    raise CandidateError("LEAF_ID_UNKNOWN")
