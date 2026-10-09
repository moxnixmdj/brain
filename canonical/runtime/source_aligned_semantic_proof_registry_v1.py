"""Brain-owned source-aligned semantic proof registry V1.

Combines non-recursive source proof families without allowing one verifier to
self-certify another.

V1 sources:
  - source_aligned_semantic_proof_v10
  - source_aligned_participial_disposition_proof_v1

Claims are partitioned by kind before verification. A rejected claim from one
family cannot be silently accepted by another unless it was explicitly routed
to that family's proof kind.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from canonical.runtime.source_aligned_semantic_proof_v10 import (
    verify_proof as verify_v10,
)
from canonical.runtime.source_aligned_participial_disposition_proof_v1 import (
    KIND as PARTICIPIAL_KIND,
    verify_proof as verify_participial,
)

SCHEMA="BRAIN_SOURCE_ALIGNED_SEMANTIC_PROOF_REGISTRY_V1"


def verify_proof(
    source_text:str,
    *,
    source_id:str,
    claims:Sequence[Mapping[str,Any]],
    typed_context:Mapping[str,Any]|None=None,
    expected_typed_context_sha256:str|None=None,
    fact_source:str|bytes|None=None,
    fact_source_id:str|None=None,
)->dict[str,Any]:
    if not isinstance(claims,Sequence) or isinstance(claims,(str,bytes)):
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED",
            "errors":["CLAIMS_INVALID"],"terminal_authority":False,
        }

    seen=set()
    base_claims=[]
    participial_claims=[]
    for i,claim in enumerate(claims):
        if not isinstance(claim,Mapping):
            return {
                "schema":SCHEMA,"status":"FAIL_CLOSED",
                "errors":[f"CLAIM_NOT_OBJECT:{i}"],
                "terminal_authority":False,
            }
        cid=str(claim.get("claim_id") or "").strip()
        if not cid:
            return {
                "schema":SCHEMA,"status":"FAIL_CLOSED",
                "errors":[f"CLAIM_ID_MISSING:{i}"],
                "terminal_authority":False,
            }
        if cid in seen:
            return {
                "schema":SCHEMA,"status":"FAIL_CLOSED",
                "errors":["CLAIM_ID_DUPLICATE:"+cid],
                "terminal_authority":False,
            }
        seen.add(cid)
        if claim.get("kind")==PARTICIPIAL_KIND:
            participial_claims.append(deepcopy(dict(claim)))
        else:
            base_claims.append(deepcopy(dict(claim)))

    base=verify_v10(
        source_text,
        source_id=source_id,
        claims=base_claims,
        typed_context=typed_context,
        expected_typed_context_sha256=expected_typed_context_sha256,
        fact_source=fact_source,
        fact_source_id=fact_source_id,
    )
    if base.get("status")=="FAIL_CLOSED":
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED",
            "errors":["V10_PROOF_FAIL_CLOSED"],
            "base_proof":base,"terminal_authority":False,
        }

    part=verify_participial(
        source_text,
        source_id=source_id,
        claims=participial_claims,
    )
    if part.get("status")=="FAIL_CLOSED":
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED",
            "errors":["PARTICIPIAL_PROOF_FAIL_CLOSED"],
            "participial_proof":part,"terminal_authority":False,
        }

    accepted=list(base.get("accepted_claims") or [])+list(
        part.get("accepted_claims") or []
    )
    rejected=list(base.get("rejected_claims") or [])+list(
        part.get("rejected_claims") or []
    )
    proved=list(base.get("proved_constraints") or [])+list(
        part.get("proved_constraints") or []
    )

    return {
        "schema":SCHEMA,
        "status":"PROOF_CHECKED" if not rejected else "PROOF_CHECKED_WITH_REJECTIONS",
        "source_id":source_id,
        "accepted_claims":accepted,
        "rejected_claims":rejected,
        "proved_constraints":proved,
        "proof_families":{
            "v10":base.get("status"),
            "participial_disposition":part.get("status"),
        },
        "terminal_authority":False,
        "boundary":(
            "REGISTRY_COMBINES_ONLY_INDEPENDENTLY_VERIFIED_NONRECURSIVE_SOURCE_"
            "PROOF_FAMILIES__UNSUPPORTED_CLAIMS_REMAIN_REJECTED"
        ),
    }
