"""Unknown-Domain direct candidate V3.

V3 preserves V2 except for the exact ADD2 role-orientation hole falsified by
the 2026-10-05 universal-promotion revocation.  ADD2 role order is resolved
from a visible cross-domain sign signature: the independently earned Domain-A
receipt names r0/r1, and the public Domain-A/Domain-B task sequences expose the
same role-specific sign pattern while keeping target feature identities opaque.

No hidden record, generator secret, beacon, terminal score, or evaluator-only
identifier is read.
"""
from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

from canonical.runtime import unknown_domain_direct_candidate_v1 as v1
from canonical.runtime import unknown_domain_direct_candidate_v2 as v2

TRANSFER=v1.TRANSFER
ABSTAIN=v1.ABSTAIN
CandidateError=v1.UnknownDomainDirectCandidateError


def _sign(x: Any) -> int:
    y=float(x)
    if not math.isfinite(y):
        raise CandidateError("ROLE_SIGNATURE_NONFINITE")
    if y > 0.0:
        return 1
    if y < 0.0:
        return -1
    return 0


def _source_role_signatures(
    case: Mapping[str,Any],
    receipt: Mapping[str,Any],
    roles: list[str],
) -> dict[str,tuple[int,...]]:
    binding=receipt.get("source_role_binding")
    tasks=case.get("domain_a",{}).get("tasks")
    if not isinstance(binding,Mapping) or not isinstance(tasks,list) or not tasks:
        raise CandidateError("SOURCE_ROLE_SIGNATURE_INPUT_INVALID")
    out={}
    for role in roles:
        fid=str(binding.get(role) or "")
        if not fid:
            raise CandidateError("SOURCE_ROLE_BINDING_MISSING")
        vals=[]
        for row in tasks:
            if not isinstance(row,Mapping) or not isinstance(row.get("inputs"),Mapping) or fid not in row["inputs"]:
                raise CandidateError("SOURCE_ROLE_SIGNATURE_ROW_INVALID")
            vals.append(_sign(row["inputs"][fid]))
        out[role]=tuple(vals)
    if len(set(out.values())) != len(out):
        raise CandidateError("SOURCE_ROLE_SIGNATURE_NOT_IDENTIFYING")
    return out


def _target_feature_signature(case: Mapping[str,Any], fid: str) -> tuple[int,...]:
    tasks=case.get("domain_b",{}).get("tasks")
    if not isinstance(tasks,list) or not tasks:
        raise CandidateError("TARGET_ROLE_SIGNATURE_INPUT_INVALID")
    vals=[]
    for row in tasks:
        if not isinstance(row,Mapping) or not isinstance(row.get("inputs"),Mapping) or fid not in row["inputs"]:
            raise CandidateError("TARGET_ROLE_SIGNATURE_ROW_INVALID")
        vals.append(_sign(row["inputs"][fid]))
    return tuple(vals)


def _resolve_add2_role_orientation(
    case: Mapping[str,Any],
    receipt: Mapping[str,Any],
    program: Mapping[str,Any],
    mappings: Sequence[Mapping[str,str]],
) -> dict[str,str]:
    roles=[str(x) for x in program.get("roles",[])]
    if str(program.get("op") or "")!="ADD2" or roles!=["r0","r1"]:
        raise CandidateError("ADD2_ROLE_SIGNATURE_PROGRAM_INVALID")
    source=_source_role_signatures(case,receipt,roles)
    survivors=[]
    for raw in mappings:
        m=dict(raw)
        if all(_target_feature_signature(case,str(m[role])) == source[role] for role in roles):
            survivors.append(m)
    if len(survivors)!=1:
        raise CandidateError("ADD2_ROLE_SIGNATURE_NOT_UNIQUE")
    return survivors[0]


def _transfer(case:Mapping[str,Any], transcript:Sequence[Mapping[str,Any]]):
    receipt=v1._receipt(case)
    program=receipt.get("normalized_primitive_program")
    if not isinstance(program,Mapping):
        raise CandidateError("RECEIPT_PROGRAM_INVALID")

    # Preserve V2's information discipline: at least one allowed probe is
    # requested before concluding transfer, which breaks the public-task
    # distractor mimicry without hidden access.
    if not transcript:
        return v2._unused_probe(case,transcript)

    observations=v1._public_transfer_observations(case,transcript)
    mappings=v1._candidate_mappings(program,observations)

    if str(program.get("op") or "")=="ADD2":
        mapping=_resolve_add2_role_orientation(case,receipt,program,mappings)
        return v2._conclude(case,transcript,receipt,program,mapping)

    supports={v1._support_signature(m) for m in mappings}
    query=case.get("domain_b",{}).get("query_inputs")
    if not isinstance(query,Mapping):
        raise CandidateError("DOMAIN_B_QUERY_INVALID")
    consequences={round(x[0],12) for x in v1._query_predictions(program,mappings,query)}
    if len(supports)==1 and len(consequences)==1:
        mapping=sorted(mappings,key=lambda m:tuple(sorted(m.items())))[0]
        return v2._conclude(case,transcript,receipt,program,mapping)
    if len(transcript)<2:
        return v2._unused_probe(case,transcript)
    mapping=v2._scale_resolve(case,transcript,receipt,program,mappings)
    return v2._conclude(case,transcript,receipt,program,mapping)


def step(case_visible:Mapping[str,Any], transcript:Sequence[Mapping[str,Any]]):
    leaf=str(case_visible.get("leaf_id") or "")
    if leaf==TRANSFER:
        return _transfer(case_visible,transcript)
    if leaf==ABSTAIN:
        return v1._abstention_step(case_visible)
    raise CandidateError("LEAF_ID_UNKNOWN")
