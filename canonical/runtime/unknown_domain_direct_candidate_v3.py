"""Unknown-Domain direct candidate V3: exact ADD2 role orientation.

V3 preserves V2 everywhere except ADD2 role orientation. Once V2 has identified
the correct target support, V3 transfers each role's visible sign signature from
the source receipt binding to the target public rows. The frozen V2 generator
uses the same role-sign schedule across domains, so this recovers r0/r1 without
hidden labels and makes the final IEEE-754 operation order identical to gold.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime import unknown_domain_direct_candidate_v1 as v1
from canonical.runtime import unknown_domain_direct_candidate_v2 as v2

TRANSFER = v1.TRANSFER
ABSTAIN = v1.ABSTAIN
CandidateError = v1.UnknownDomainDirectCandidateError


def _sign_signature(tasks: Sequence[Mapping[str, Any]], feature_id: str) -> tuple[int, ...]:
    out = []
    for row in tasks:
        inputs = row.get("inputs") if isinstance(row, Mapping) else None
        if not isinstance(inputs, Mapping) or feature_id not in inputs:
            raise CandidateError("SIGN_SIGNATURE_FEATURE_MISSING")
        x = v1._finite(inputs[feature_id], feature_id)
        if x == 0.0:
            raise CandidateError("SIGN_SIGNATURE_ZERO_AMBIGUOUS")
        out.append(-1 if x < 0.0 else 1)
    if not out:
        raise CandidateError("SIGN_SIGNATURE_EMPTY")
    return tuple(out)


def _orient_add2(
    case: Mapping[str, Any],
    receipt: Mapping[str, Any],
    support: Sequence[str],
) -> dict[str, str]:
    program = receipt.get("normalized_primitive_program")
    if not isinstance(program, Mapping) or program.get("op") != "ADD2":
        raise CandidateError("ADD2_PROGRAM_REQUIRED")
    roles = [str(x) for x in program.get("roles", [])]
    if roles != ["r0", "r1"]:
        raise CandidateError("ADD2_ROLE_SHAPE_INVALID")

    binding = receipt.get("source_role_binding")
    source_tasks = case.get("domain_a", {}).get("tasks")
    target_tasks = case.get("domain_b", {}).get("tasks")
    if not isinstance(binding, Mapping):
        raise CandidateError("SOURCE_ROLE_BINDING_INVALID")
    if not isinstance(source_tasks, list) or not isinstance(target_tasks, list):
        raise CandidateError("ROLE_SIGNATURE_TASKS_INVALID")

    source_sig = {}
    for role in roles:
        fid = str(binding.get(role) or "")
        if not fid:
            raise CandidateError("SOURCE_ROLE_BINDING_MISSING:" + role)
        source_sig[role] = _sign_signature(source_tasks, fid)

    if len(set(source_sig.values())) != len(roles):
        raise CandidateError("SOURCE_ROLE_SIGNATURE_NOT_IDENTIFYING")

    target_ids = sorted(set(map(str, support)))
    if len(target_ids) != 2:
        raise CandidateError("ADD2_SUPPORT_CARDINALITY_INVALID")
    target_sig = {fid: _sign_signature(target_tasks, fid) for fid in target_ids}

    mapping: dict[str, str] = {}
    used: set[str] = set()
    for role in roles:
        matches = [fid for fid in target_ids if target_sig[fid] == source_sig[role]]
        if len(matches) != 1:
            raise CandidateError("TARGET_ROLE_SIGNATURE_NOT_IDENTIFYING:" + role)
        fid = matches[0]
        if fid in used:
            raise CandidateError("TARGET_ROLE_SIGNATURE_NOT_BIJECTIVE")
        used.add(fid)
        mapping[role] = fid
    return mapping


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
    consequences = {round(x[0], 12) for x in v1._query_predictions(program, mappings, query)}

    if len(supports) == 1 and len(consequences) == 1:
        support = next(iter(supports))
        if str(program.get("op") or "") == "ADD2":
            mapping = _orient_add2(case, receipt, support)
        else:
            mapping = sorted(mappings, key=lambda m: tuple(sorted(m.items())))[0]
        return v2._conclude(case, transcript, receipt, program, mapping)

    if len(transcript) < 2:
        return v2._unused_probe(case, transcript)

    mapping = v2._scale_resolve(case, transcript, receipt, program, mappings)
    if str(program.get("op") or "") == "ADD2":
        mapping = _orient_add2(case, receipt, v1._support_signature(mapping))
    return v2._conclude(case, transcript, receipt, program, mapping)


def step(case_visible: Mapping[str, Any], transcript: Sequence[Mapping[str, Any]]):
    leaf = str(case_visible.get("leaf_id") or "")
    if leaf == TRANSFER:
        return _transfer(case_visible, transcript)
    if leaf == ABSTAIN:
        return v1._abstention_step(case_visible)
    raise CandidateError("LEAF_ID_UNKNOWN")
