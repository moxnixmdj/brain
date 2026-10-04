"""Zero-learned Unknown-Domain direct candidate V3.

V3 preserves V2's probe policy and structural mapping search, but evaluates the
primitive with the canonical V3 semantics.  In particular ADD2 is exactly
permutation-invariant, so an unobservable r0/r1 swap can no longer change the
terminal consequence by one IEEE-754 bit.
"""
from __future__ import annotations

import itertools
from typing import Any, Mapping, Sequence

from canonical.runtime import unknown_domain_direct_candidate_v1 as v1
from canonical.runtime import unknown_domain_direct_candidate_v2 as v2
from canonical.runtime import unknown_domain_direct_v3_semantics_v1 as sem

TRANSFER = v1.TRANSFER
ABSTAIN = v1.ABSTAIN
CandidateError = v1.UnknownDomainDirectCandidateError
SCHEMA = "PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_CANDIDATE_V3"


def _candidate_mappings(program: Mapping[str, Any], observations):
    roles = [str(x) for x in program.get("roles", [])]
    if roles not in (["r0"], ["r0", "r1"]):
        raise CandidateError("PROGRAM_ROLES_UNSUPPORTED")

    keys = None
    for inputs, _, _ in observations:
        current = set(map(str, inputs.keys()))
        keys = current if keys is None else keys & current
    if not keys or len(keys) < len(roles):
        raise CandidateError("DOMAIN_B_FEATURE_SET_TOO_SMALL")

    out = []
    for chosen in itertools.permutations(sorted(keys), len(roles)):
        mapping = dict(zip(roles, chosen))
        ok = True
        for inputs, target, _ in observations:
            try:
                values = {
                    role: v1._finite(inputs[fid], fid)
                    for role, fid in mapping.items()
                }
                pred = sem.eval_program(program, values)
            except (KeyError, ValueError):
                ok = False
                break
            if not v1._close(pred, target):
                ok = False
                break
        if ok:
            out.append(mapping)
    if not out:
        raise CandidateError("NO_STRUCTURAL_MAPPING_SURVIVES_PUBLIC_EVIDENCE")
    return out


def _query_predictions(program, mappings, query_inputs):
    rows = []
    for mapping in mappings:
        values = {
            role: v1._finite(query_inputs[fid], fid)
            for role, fid in mapping.items()
        }
        rows.append((
            sem.eval_program(program, values),
            v1._support_signature(mapping),
            mapping,
        ))
    return rows


def _conclude(case, transcript, receipt, program, mapping):
    query = case.get("domain_b", {}).get("query_inputs")
    if not isinstance(query, Mapping):
        raise CandidateError("DOMAIN_B_QUERY_INVALID")
    values = {role: float(query[fid]) for role, fid in mapping.items()}
    consequence = sem.eval_program(program, values)
    support = set(mapping.values())
    rejected = v1._all_visible_feature_ids(case, transcript) - support
    rid = str(receipt["receipt_id"])
    return {
        "type": "CONCLUDE",
        "terminal_consequence": consequence,
        "domain_a_source_receipt_ids": [rid],
        "transferred_primitive_fingerprint": str(receipt["primitive_fingerprint"]),
        "support_feature_ids": sorted(support),
        "negative_transfer_rejected_feature_ids": sorted(rejected),
        "mapping_basis": v1.MAPPING_BASIS,
        "evidence_provenance": v1._provenance(rid, support, rejected),
        "persistent_learned_bytes": 0,
        "external_frontier_model_calls": 0,
        "external_learned_capability_calls": 0,
    }


def _transfer(case: Mapping[str, Any], transcript: Sequence[Mapping[str, Any]]):
    receipt = v1._receipt(case)
    program = receipt.get("normalized_primitive_program")
    if not isinstance(program, Mapping):
        raise CandidateError("RECEIPT_PROGRAM_INVALID")

    if not transcript:
        return v2._unused_probe(case, transcript)

    observations = v1._public_transfer_observations(case, transcript)
    mappings = _candidate_mappings(program, observations)
    supports = {v1._support_signature(m) for m in mappings}

    query = case.get("domain_b", {}).get("query_inputs")
    if not isinstance(query, Mapping):
        raise CandidateError("DOMAIN_B_QUERY_INVALID")

    predictions = _query_predictions(program, mappings, query)
    consequences = {x[0] for x in predictions}
    if len(supports) == 1 and len(consequences) == 1:
        mapping = sorted(
            mappings,
            key=lambda m: tuple(sorted(m.items())),
        )[0]
        return _conclude(case, transcript, receipt, program, mapping)

    if len(transcript) < 2:
        return v2._unused_probe(case, transcript)

    mapping = v2._scale_resolve(case, transcript, receipt, program, mappings)
    return _conclude(case, transcript, receipt, program, mapping)


def step(case_visible: Mapping[str, Any], transcript: Sequence[Mapping[str, Any]]):
    leaf = str(case_visible.get("leaf_id") or "")
    if leaf == TRANSFER:
        return _transfer(case_visible, transcript)
    if leaf == ABSTAIN:
        return v1._abstention_step(case_visible)
    raise CandidateError("LEAF_ID_UNKNOWN")
