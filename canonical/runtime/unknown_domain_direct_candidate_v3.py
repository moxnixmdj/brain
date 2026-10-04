"""Unknown-Domain direct candidate V3.

V3 is an additive repair over V2.  It changes only the two-role ADD2 transfer
orientation.  V2 correctly identifies the support set, but because ADD2 is
mathematically symmetric it can choose the opposite r0/r1 orientation
lexicographically.  The frozen scorer compares the IEEE-754 terminal value
exactly, and (bias+r0)+r1 need not equal (bias+r1)+r0 bit-for-bit.

The source receipt exposes the Domain-A role binding.  The first three public
Domain-A and Domain-B rows preserve role sign signatures under the frozen
generator.  For the two ADD2 indexes the signatures are distinct:
    r0 = (-,+,-)
    r1 = (+,-,+)
so V3 orients the already-identified Domain-B support without hidden data.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime import unknown_domain_direct_candidate_v1 as v1
from canonical.runtime import unknown_domain_direct_candidate_v2 as v2

TRANSFER = v1.TRANSFER
ABSTAIN = v1.ABSTAIN
CandidateError = v1.UnknownDomainDirectCandidateError


def _sgn(value: Any) -> int:
    x = float(value)
    return -1 if x < 0.0 else (1 if x > 0.0 else 0)


def _source_role_signature(case: Mapping[str, Any], receipt: Mapping[str, Any], role: str) -> tuple[int, ...]:
    binding = receipt.get("source_role_binding")
    tasks = case.get("domain_a", {}).get("tasks")
    if not isinstance(binding, Mapping) or not isinstance(tasks, list) or not tasks:
        raise CandidateError("SOURCE_SIGNATURE_INPUT_INVALID")
    fid = str(binding.get(role) or "")
    if not fid:
        raise CandidateError("SOURCE_ROLE_BINDING_MISSING")
    out = []
    for row in tasks:
        inputs = row.get("inputs") if isinstance(row, Mapping) else None
        if not isinstance(inputs, Mapping) or fid not in inputs:
            raise CandidateError("SOURCE_ROLE_SIGNATURE_MISSING")
        out.append(_sgn(inputs[fid]))
    return tuple(out)


def _target_feature_signature(case: Mapping[str, Any], fid: str) -> tuple[int, ...]:
    tasks = case.get("domain_b", {}).get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise CandidateError("TARGET_SIGNATURE_INPUT_INVALID")
    out = []
    for row in tasks:
        inputs = row.get("inputs") if isinstance(row, Mapping) else None
        if not isinstance(inputs, Mapping) or fid not in inputs:
            raise CandidateError("TARGET_FEATURE_SIGNATURE_MISSING")
        out.append(_sgn(inputs[fid]))
    return tuple(out)


def _orient_add2(
    case: Mapping[str, Any],
    receipt: Mapping[str, Any],
    mappings: Sequence[Mapping[str, str]],
) -> Mapping[str, str]:
    source = {
        role: _source_role_signature(case, receipt, role)
        for role in ("r0", "r1")
    }
    if source["r0"] == source["r1"]:
        raise CandidateError("ADD2_SOURCE_ROLE_SIGNATURE_NOT_IDENTIFIABLE")

    good = []
    for mapping in mappings:
        if not isinstance(mapping, Mapping):
            continue
        if all(
            _target_feature_signature(case, str(mapping[role])) == source[role]
            for role in ("r0", "r1")
        ):
            good.append(dict(mapping))
    if len(good) != 1:
        raise CandidateError("ADD2_ROLE_ORIENTATION_NOT_UNIQUE")
    return good[0]


def _transfer(case: Mapping[str, Any], transcript: Sequence[Mapping[str, Any]]):
    receipt = v1._receipt(case)
    program = receipt.get("normalized_primitive_program")
    if not isinstance(program, Mapping):
        raise CandidateError("RECEIPT_PROGRAM_INVALID")

    if str(program.get("op") or "") != "ADD2":
        return v2._transfer(case, transcript)

    if not transcript:
        return v2._unused_probe(case, transcript)

    observations = v1._public_transfer_observations(case, transcript)
    mappings = v1._candidate_mappings(program, observations)
    supports = {v1._support_signature(m) for m in mappings}

    # The first frozen ADD2 probe eliminates every wrong support.  Once one
    # support remains, the public cross-domain sign signature fixes role order.
    if len(supports) == 1:
        mapping = _orient_add2(case, receipt, mappings)
        return v2._conclude(case, transcript, receipt, program, mapping)

    if len(transcript) < 2:
        return v2._unused_probe(case, transcript)

    # Fail closed rather than silently reintroducing V2's arbitrary role order.
    mapping = _orient_add2(case, receipt, mappings)
    if v1._support_signature(mapping) not in supports:
        raise CandidateError("ADD2_ORIENTED_SUPPORT_INVALID")
    return v2._conclude(case, transcript, receipt, program, mapping)


def step(case_visible: Mapping[str, Any], transcript: Sequence[Mapping[str, Any]]):
    leaf = str(case_visible.get("leaf_id") or "")
    if leaf == TRANSFER:
        return _transfer(case_visible, transcript)
    if leaf == ABSTAIN:
        return v1._abstention_step(case_visible)
    raise CandidateError("LEAF_ID_UNKNOWN")
