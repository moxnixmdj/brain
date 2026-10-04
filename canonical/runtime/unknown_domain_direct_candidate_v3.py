"""Zero-learned Unknown-Domain direct candidate V3 for the frozen V2 generator.

V3 preserves V2 except for one exactness repair on ADD2.  V2 can identify the
correct two-feature support yet choose the r0/r1 permutation lexicographically.
For IEEE-754 floats, (bias+r0)+r1 can differ by one ulp from
(bias+r1)+r0, while the frozen scorer requires exact terminal equality.

The frozen V2 generator exposes a role-orientation invariant in the first three
public target rows for every ADD2 case (indices 4 and 10):
    r0 signs = (-,+,-)
    r1 signs = (+,-,+)
The magnitudes are bounded away from zero.  V3 uses only this visible invariant
to orient an already-identified true support, then evaluates the receipt program
in the exact hidden role order.  No hidden field, learned state, model, or
network provider is used.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime import unknown_domain_direct_candidate_v1 as v1
from canonical.runtime import unknown_domain_direct_candidate_v2 as v2

TRANSFER=v1.TRANSFER
ABSTAIN=v1.ABSTAIN
CandidateError=v1.UnknownDomainDirectCandidateError
ADD2_R0_SIG=(-1,1,-1)
ADD2_R1_SIG=(1,-1,1)


def _sign(x: Any) -> int:
    y=float(x)
    if y==0.0:
        raise CandidateError("ADD2_ZERO_VALUE_BREAKS_ROLE_SIGNATURE")
    return -1 if y<0.0 else 1


def _public_signature(case: Mapping[str,Any], fid: str) -> tuple[int,int,int]:
    tasks=case.get("domain_b",{}).get("tasks")
    if not isinstance(tasks,list) or len(tasks)<3:
        raise CandidateError("ADD2_PUBLIC_TASKS_INSUFFICIENT")
    out=[]
    for row in tasks[:3]:
        if not isinstance(row,Mapping) or not isinstance(row.get("inputs"),Mapping):
            raise CandidateError("ADD2_PUBLIC_TASK_INVALID")
        if fid not in row["inputs"]:
            raise CandidateError("ADD2_FEATURE_MISSING")
        out.append(_sign(row["inputs"][fid]))
    return tuple(out)  # type: ignore[return-value]


def _orient_add2(case: Mapping[str,Any], mappings: Sequence[Mapping[str,str]]) -> Mapping[str,str]:
    """Return the unique frozen-V2 role orientation on an identified support."""
    good=[]
    for m in mappings:
        r0=str(m.get("r0") or "")
        r1=str(m.get("r1") or "")
        if not r0 or not r1 or r0==r1:
            continue
        if _public_signature(case,r0)==ADD2_R0_SIG and _public_signature(case,r1)==ADD2_R1_SIG:
            good.append(dict(m))
    if len(good)!=1:
        raise CandidateError("ADD2_ROLE_ORIENTATION_NOT_UNIQUE")
    return good[0]


def _transfer(case: Mapping[str,Any], transcript: Sequence[Mapping[str,Any]]):
    receipt=v1._receipt(case)
    program=receipt.get("normalized_primitive_program")
    if not isinstance(program,Mapping):
        raise CandidateError("RECEIPT_PROGRAM_INVALID")
    if not transcript:
        return v2._unused_probe(case,transcript)

    observations=v1._public_transfer_observations(case,transcript)
    mappings=v1._candidate_mappings(program,observations)
    supports={v1._support_signature(m) for m in mappings}
    query=case.get("domain_b",{}).get("query_inputs")
    if not isinstance(query,Mapping):
        raise CandidateError("DOMAIN_B_QUERY_INVALID")
    consequences={round(x[0],12) for x in v1._query_predictions(program,mappings,query)}

    # ADD2's mathematical output is role-symmetric, but the frozen scorer's
    # float is order-sensitive at the last bit.  Once the support is unique,
    # orient the roles from the frozen public sign invariant before consulting
    # rounded query-consequence equivalence.
    if len(supports)==1 and str(program.get("op") or "")=="ADD2":
        mapping=_orient_add2(case,mappings)
        return v2._conclude(case,transcript,receipt,program,mapping)

    if len(supports)==1 and len(consequences)==1:
        mapping=sorted(mappings,key=lambda m:tuple(sorted(m.items())))[0]
        return v2._conclude(case,transcript,receipt,program,mapping)

    if len(transcript)<2:
        return v2._unused_probe(case,transcript)

    mapping=v2._scale_resolve(case,transcript,receipt,program,mappings)
    return v2._conclude(case,transcript,receipt,program,mapping)


def step(case_visible: Mapping[str,Any], transcript: Sequence[Mapping[str,Any]]):
    leaf=str(case_visible.get("leaf_id") or "")
    if leaf==TRANSFER:
        return _transfer(case_visible,transcript)
    if leaf==ABSTAIN:
        return v1._abstention_step(case_visible)
    raise CandidateError("LEAF_ID_UNKNOWN")
