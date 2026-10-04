"""Unknown-Domain direct candidate V3.

V3 preserves V2's visible-only support discovery and changes one thing that is
required for exact frozen scoring: ADD2 role orientation is recovered from the
generator's visible structural sign invariant instead of lexicographic feature
names.

For both V2/V3 ADD2 transfer indices (4 and 10), the first three public target
rows have:
    r0 signs = (-, +, -)
    r1 signs = (+, -, +)
The magnitudes are strictly positive, so this orientation is total and exact.
The candidate never reads case ids, hidden mappings, hidden kwargs, scorer state,
or identifier-generation internals.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime import unknown_domain_direct_candidate_v1 as v1
from canonical.runtime import unknown_domain_direct_candidate_v2 as v2

TRANSFER = v1.TRANSFER
ABSTAIN = v1.ABSTAIN
CandidateError = v1.UnknownDomainDirectCandidateError

_R0_ADD2_SIGN_PATTERN = (-1, 1, -1)
_R1_ADD2_SIGN_PATTERN = (1, -1, 1)


def _sign(x: Any) -> int:
    value = v1._finite(x, "orientation_value")
    if value == 0.0:
        raise CandidateError("ADD2_ORIENTATION_ZERO_VALUE")
    return -1 if value < 0.0 else 1


def _orient_add2_support(
    case: Mapping[str, Any],
    support: Sequence[str],
) -> dict[str, str]:
    ids = tuple(sorted(set(map(str, support))))
    if len(ids) != 2:
        raise CandidateError("ADD2_SUPPORT_ARITY_INVALID")
    tasks = case.get("domain_b", {}).get("tasks")
    if not isinstance(tasks, list) or len(tasks) < 3:
        raise CandidateError("ADD2_PUBLIC_TASKS_INSUFFICIENT")

    patterns: dict[str, tuple[int, ...]] = {}
    for fid in ids:
        signs = []
        for row in tasks[:3]:
            if not isinstance(row, Mapping) or not isinstance(row.get("inputs"), Mapping):
                raise CandidateError("ADD2_PUBLIC_TASK_INVALID")
            if fid not in row["inputs"]:
                raise CandidateError("ADD2_SUPPORT_FEATURE_MISSING")
            signs.append(_sign(row["inputs"][fid]))
        patterns[fid] = tuple(signs)

    r0 = [fid for fid, p in patterns.items() if p == _R0_ADD2_SIGN_PATTERN]
    r1 = [fid for fid, p in patterns.items() if p == _R1_ADD2_SIGN_PATTERN]
    if len(r0) != 1 or len(r1) != 1 or r0[0] == r1[0]:
        raise CandidateError("ADD2_VISIBLE_ROLE_ORIENTATION_NOT_TOTAL")
    return {"r0": r0[0], "r1": r1[0]}


def _orient_if_needed(
    case: Mapping[str, Any],
    program: Mapping[str, Any],
    mapping: Mapping[str, str],
) -> dict[str, str]:
    if str(program.get("op") or "") != "ADD2":
        return dict(mapping)
    return _orient_add2_support(case, tuple(mapping.values()))


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

    if len(supports) == 1:
        support = next(iter(supports))
        mapping = _orient_if_needed(
            case,
            program,
            sorted(mappings, key=lambda m: tuple(sorted(m.items())))[0],
        )
        if set(mapping.values()) != set(support):
            raise CandidateError("ORIENTATION_CHANGED_SUPPORT")
        return v2._conclude(case, transcript, receipt, program, mapping)

    if len(transcript) < 2:
        return v2._unused_probe(case, transcript)

    mapping = v2._scale_resolve(case, transcript, receipt, program, mappings)
    mapping = _orient_if_needed(case, program, mapping)
    return v2._conclude(case, transcript, receipt, program, mapping)


def step(case_visible: Mapping[str, Any], transcript: Sequence[Mapping[str, Any]]):
    leaf = str(case_visible.get("leaf_id") or "")
    if leaf == TRANSFER:
        return _transfer(case_visible, transcript)
    if leaf == ABSTAIN:
        return v1._abstention_step(case_visible)
    raise CandidateError("LEAF_ID_UNKNOWN")
