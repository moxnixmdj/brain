"""Unknown-Domain direct candidate V3: exact role-order-safe transfer.

V3 removes V2's arbitrary lexicographic role tie-break. When multiple ordered
mappings share one support and one rounded query consequence, it resolves role
identity from visible cross-domain sign signatures carried by the independently
verified Domain-A receipt and the public Domain-A/Domain-B task rows.

If visible role identity is still ambiguous, V3 fails closed rather than
inventing an ordering. No hidden generator/scorer import, model, network, or
persistent learned bytes are used.
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


def _source_role_signatures(
    case: Mapping[str, Any],
    receipt: Mapping[str, Any],
    roles: list[str],
) -> dict[str, tuple[int, ...]]:
    binding = receipt.get("source_role_binding")
    tasks = case.get("domain_a", {}).get("tasks")
    if not isinstance(binding, Mapping) or not isinstance(tasks, list) or not tasks:
        raise CandidateError("SOURCE_ROLE_SIGNATURE_INPUT_INVALID")
    out: dict[str, tuple[int, ...]] = {}
    for role in roles:
        fid = str(binding.get(role) or "")
        if not fid:
            raise CandidateError("SOURCE_ROLE_BINDING_MISSING")
        signs = []
        for row in tasks:
            inputs = row.get("inputs") if isinstance(row, Mapping) else None
            if not isinstance(inputs, Mapping) or fid not in inputs:
                raise CandidateError("SOURCE_ROLE_SIGNATURE_ROW_INVALID")
            signs.append(_sgn(inputs[fid]))
        out[role] = tuple(signs)
    return out


def _target_feature_signature(case: Mapping[str, Any], fid: str) -> tuple[int, ...]:
    tasks = case.get("domain_b", {}).get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise CandidateError("TARGET_ROLE_SIGNATURE_INPUT_INVALID")
    signs = []
    for row in tasks:
        inputs = row.get("inputs") if isinstance(row, Mapping) else None
        if not isinstance(inputs, Mapping) or fid not in inputs:
            raise CandidateError("TARGET_ROLE_SIGNATURE_ROW_INVALID")
        signs.append(_sgn(inputs[fid]))
    return tuple(signs)


def _resolve_role_order(
    case: Mapping[str, Any],
    receipt: Mapping[str, Any],
    program: Mapping[str, Any],
    mappings: list[Mapping[str, str]],
) -> Mapping[str, str]:
    if len(mappings) == 1:
        return mappings[0]
    roles = [str(x) for x in program.get("roles", [])]
    source = _source_role_signatures(case, receipt, roles)
    survivors = []
    for mapping in mappings:
        if all(
            _target_feature_signature(case, str(mapping[role])) == source[role]
            for role in roles
        ):
            survivors.append(mapping)
    if len(survivors) != 1:
        raise CandidateError("VISIBLE_ROLE_ORDER_NOT_UNIQUELY_IDENTIFIED")
    return survivors[0]


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
    predictions = v1._query_predictions(program, mappings, query)
    consequences = {round(x[0], 12) for x in predictions}

    if len(supports) == 1 and len(consequences) == 1:
        mapping = _resolve_role_order(case, receipt, program, mappings)
        return v2._conclude(case, transcript, receipt, program, mapping)

    if len(transcript) < 2:
        return v2._unused_probe(case, transcript)

    # Retain V2's scale fallback only when support itself is not yet unique.
    # If it cannot select uniquely it already fails closed.
    mapping = v2._scale_resolve(case, transcript, receipt, program, mappings)
    return v2._conclude(case, transcript, receipt, program, mapping)


def step(case_visible: Mapping[str, Any], transcript: Sequence[Mapping[str, Any]]):
    leaf = str(case_visible.get("leaf_id") or "")
    if leaf == TRANSFER:
        return _transfer(case_visible, transcript)
    if leaf == ABSTAIN:
        return v1._abstention_step(case_visible)
    raise CandidateError("LEAF_ID_UNKNOWN")
