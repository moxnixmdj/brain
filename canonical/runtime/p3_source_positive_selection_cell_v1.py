"""P3 source-positive selection cell v1.

Deletes the overstrong requirement to enumerate a complete semantic/policy-world
partition for a reached capacity-binding context.

The selected Brain-owned policy is admitted only when:
1. its exact selected-claim policy is independently content-bound to the current
   P3 input;
2. the existing proof-carrying source-positive adequacy bridge certifies that
   same policy across every source-compatible interpretation of the current
   semantic state; and
3. the selected claims are grounded and realized through the existing P3
   realization cell.

No negative relevance inference and no complete world enumeration are used.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.effect_broker_receipt_resolver_v2 import resolve_receipt_bytes
from canonical.runtime.p3_required_claim_grounded_realization_cell_v3 import (
    evaluate as realize,
)
from canonical.runtime.source_positive_adequacy_db_admission_v1 import (
    evaluate as evaluate_positive,
)

SCHEMA="PROJECT_BRAIN_P3_SOURCE_POSITIVE_SELECTION_CELL_V1"
CONTRACT_SCHEMA="PROJECT_BRAIN_P3_SOURCE_POSITIVE_SELECTION_CONTRACT_V1"
RECEIPT_SCHEMA="PROJECT_BRAIN_P3_SOURCE_POSITIVE_SELECTION_BINDING_VERIFICATION_V1"
_FIELDS={
    "schema","selected_policy_id","selected_claim_ids",
    "positive_adequacy_payload","selection_binding_ref",
}


def _fail(reason:str, **detail:Any)->dict[str,Any]:
    out={
        "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
        "p3_contract_cell_authorized":False,
        "selected_policy_adequacy_verified":False,
        "interpretation_set_enumeration_required":False,
        "complete_world_partition_required":False,
        "source_authorization_verified":False,
        "policy_adequacy_authority":False,
        "db_admission_authority":False,
        "u_subtraction_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
    }
    if detail: out["detail"]=detail
    return out


def _digest(value:Any)->str:
    raw=json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    return "sha256:"+sha256(raw).hexdigest()


def _claim_surface(public:Mapping[str,Any])->tuple[list[str],set[str],int]:
    task=public.get("task")
    if not isinstance(task,Mapping):
        raise ValueError("TASK_REQUIRED")
    claims=task.get("claims")
    if not isinstance(claims,list) or not claims:
        raise ValueError("CLAIMS_REQUIRED")
    if "claim_order" in task:
        raise ValueError("CALLER_CLAIM_ORDER_FORBIDDEN")
    ids=[]; required=set()
    for row in claims:
        if not isinstance(row,Mapping):
            raise ValueError("CLAIM_ROW_INVALID")
        cid=row.get("claim_id"); req=row.get("required")
        if not isinstance(cid,str) or not cid or cid in ids:
            raise ValueError("CLAIM_ID_INVALID_OR_DUPLICATE")
        if req not in (True,False):
            raise ValueError("CLAIM_REQUIRED_FLAG_INVALID")
        if "include" in row:
            raise ValueError("CALLER_INCLUDE_FORBIDDEN")
        ids.append(cid)
        if req: required.add(cid)
    profile=task.get("audience_profile")
    constraints=profile.get("constraints") if isinstance(profile,Mapping) else None
    max_items=constraints.get("max_items") if isinstance(constraints,Mapping) else None
    if isinstance(max_items,bool) or not isinstance(max_items,int) or max_items<1:
        raise ValueError("MAX_ITEMS_INVALID")
    return ids,required,max_items


def evaluate(payload:Mapping[str,Any], *, repo_root:str|Path)->dict[str,Any]:
    try:
        if not isinstance(payload,Mapping):
            return _fail("PAYLOAD_MAPPING_REQUIRED")
        public=payload.get("v3_input")
        contract=payload.get("source_positive_selection_contract")
        if not isinstance(public,Mapping):
            return _fail("V3_INPUT_REQUIRED")
        if not isinstance(contract,Mapping):
            return _fail("SOURCE_POSITIVE_SELECTION_CONTRACT_REQUIRED")
        if set(contract)!=_FIELDS:
            return _fail(
                "SOURCE_POSITIVE_SELECTION_CONTRACT_FIELDS_INVALID",
                missing=sorted(_FIELDS-set(contract)),
                extra=sorted(set(contract)-_FIELDS),
            )
        if contract.get("schema")!=CONTRACT_SCHEMA:
            return _fail("SOURCE_POSITIVE_SELECTION_CONTRACT_SCHEMA_INVALID")

        claim_ids,required,max_items=_claim_surface(public)
        claim_set=set(claim_ids)
        policy_id=contract.get("selected_policy_id")
        selected=contract.get("selected_claim_ids")
        if not isinstance(policy_id,str) or not policy_id:
            return _fail("SELECTED_POLICY_ID_INVALID")
        if (
            not isinstance(selected,list) or not selected
            or len(set(selected))!=len(selected)
            or any(not isinstance(x,str) or x not in claim_set for x in selected)
        ):
            return _fail("SELECTED_CLAIM_IDS_INVALID")
        selected_set=set(selected)
        if not required.issubset(selected_set):
            return _fail("SELECTED_POLICY_OMITS_REQUIRED_CLAIM")
        if len(selected)>max_items:
            return _fail("SELECTED_POLICY_EXCEEDS_ITEM_BUDGET",selected_count=len(selected),max_items=max_items)
        if selected != [cid for cid in claim_ids if cid in selected_set]:
            return _fail("SELECTED_POLICY_ORDER_MUST_PRESERVE_CLAIM_ORDER")

        adequacy=contract.get("positive_adequacy_payload")
        if not isinstance(adequacy,Mapping):
            return _fail("POSITIVE_ADEQUACY_PAYLOAD_REQUIRED")
        if adequacy.get("selected_policy_id")!=policy_id:
            return _fail("POSITIVE_ADEQUACY_POLICY_ID_MISMATCH")
        bindings=adequacy.get("content_bindings")
        if not isinstance(bindings,Mapping):
            return _fail("POSITIVE_ADEQUACY_CONTENT_BINDINGS_REQUIRED")
        public_digest=_digest(public)
        selected_digest=_digest(selected)
        if bindings.get("p3_v3_input_sha256")!=public_digest:
            return _fail("POSITIVE_ADEQUACY_V3_INPUT_BINDING_MISMATCH")
        if bindings.get("selected_claim_ids_sha256")!=selected_digest:
            return _fail("POSITIVE_ADEQUACY_SELECTION_BINDING_MISMATCH")

        ref=contract.get("selection_binding_ref")
        if not isinstance(ref,Mapping):
            return _fail("SELECTION_BINDING_REF_REQUIRED")
        path=ref.get("path")
        if not isinstance(path,str) or not path.startswith("canonical/verification/"):
            return _fail("SELECTION_BINDING_MUST_BE_CANONICAL_VERIFICATION")
        bound=resolve_receipt_bytes(ref,repo_root=Path(repo_root))
        receipt=bound["document"]
        if receipt.get("schema")!=RECEIPT_SCHEMA:
            return _fail("SELECTION_BINDING_SCHEMA_INVALID")
        for field in (
            "independent_verified","exact_byte_bound",
            "selected_policy_binding_authenticated",
            "deployed_route_exactly_realizes_selected_claim_policy",
        ):
            if receipt.get(field) is not True:
                return _fail("SELECTION_BINDING_PREMISE_UNPROVED:"+field)
        if receipt.get("conclusion")!="success":
            return _fail("SELECTION_BINDING_NOT_SUCCESS")
        if receipt.get("selected_policy_id")!=policy_id:
            return _fail("SELECTION_BINDING_POLICY_ID_MISMATCH")
        if receipt.get("selected_claim_ids_sha256")!=selected_digest:
            return _fail("SELECTION_BINDING_SELECTED_CLAIMS_MISMATCH")
        if receipt.get("v3_input_sha256")!=public_digest:
            return _fail("SELECTION_BINDING_V3_INPUT_MISMATCH")
        if receipt.get("positive_adequacy_payload_sha256")!=_digest(adequacy):
            return _fail("SELECTION_BINDING_ADEQUACY_PAYLOAD_MISMATCH")

        positive=evaluate_positive(adequacy)
        if positive.get("pass") is not True or positive.get("db_admission_authorized") is not True:
            return _fail(
                "SOURCE_POSITIVE_ADEQUACY_NOT_CERTIFIED",
                positive_status=positive.get("status"),
                positive_reason=positive.get("reason"),
                positive_result=positive,
            )
        if positive.get("selected_policy_id")!=policy_id:
            return _fail("SOURCE_POSITIVE_ADEQUACY_SELECTED_POLICY_DRIFT")
        if positive.get("interpretation_set_enumeration_required") is not False:
            return _fail("SOURCE_POSITIVE_ADEQUACY_ENUMERATION_BOUNDARY_INVALID")
        if positive.get("exact_interpretation_set_completeness_required") is not False:
            return _fail("SOURCE_POSITIVE_ADEQUACY_COMPLETENESS_BOUNDARY_INVALID")

        compiled=deepcopy(dict(public))
        ctask=compiled["task"]
        rows=[]
        for row in ctask["claims"]:
            if row["claim_id"] not in selected_set:
                continue
            nr=dict(row); nr["required"]=True; nr.pop("include",None); rows.append(nr)
        ctask["claims"]=rows
        ctask.pop("claim_order",None)
        realized=realize({"v3_input":compiled})
        if realized.get("pass") is not True:
            return _fail("SELECTED_POLICY_GROUNDED_REALIZATION_FAILED",realization=realized)
        if any(
            realized.get(k) is not False
            for k in (
                "source_authorization_verified","policy_adequacy_authority",
                "db_admission_authority","u_subtraction_authority","terminal_authority",
            )
        ) or realized.get("terminal_credit_delta")!=0:
            return _fail("DOWNSTREAM_AUTHORITY_BOUNDARY_INVALID")

        return {
            "schema":SCHEMA,"pass":True,
            "status":"PASS__P3_SOURCE_POSITIVE_SELECTION_CELL",
            "selected_policy_id":policy_id,
            "selected_claim_ids":list(selected),
            "selected_policy_adequacy_verified":True,
            "semantic_overapproximation_used":True,
            "interpretation_set_enumeration_required":False,
            "complete_world_partition_required":False,
            "unused_semantic_dimensions_need_not_be_classified":True,
            "positive_adequacy_receipt":positive,
            "selection_binding_path":bound["path"],
            "selection_binding_git_blob_sha":bound["git_blob_sha"],
            "rendered_text":realized.get("rendered_text"),
            "render_trace":realized.get("render_trace"),
            "realization_receipt":realized,
            "p3_contract_cell_authorized":True,
            "source_authorization_verified":False,
            "policy_adequacy_authority":False,
            "db_admission_authority":False,
            "u_subtraction_authority":False,
            "terminal_authority":False,
            "terminal_credit_delta":0,
            "boundary":(
                "CURRENT_SOURCE_COMPATIBLE_SEMANTIC_OVERAPPROXIMATION_AND_EXACT_SELECTED_POLICY_ONLY;"
                "NO_COMPLETE_WORLD_PARTITION_NO_NEGATIVE_RELEVANCE_NO_GLOBAL_P3_CLOSURE"
            ),
        }
    except Exception as exc:
        return _fail("INVALID_INPUT",exception_type=type(exc).__name__,detail_text=str(exc)[:240])


def run(args:Mapping[str,Any]|None=None,root:Any=None)->dict[str,Any]:
    return evaluate(args or {},repo_root=root or Path(__file__).resolve().parents[2])
