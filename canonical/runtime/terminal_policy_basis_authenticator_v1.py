"""Authenticate a complete positive policy basis over the bound behavioral registry.

This gate composes existing structural contract/extension gates with exact-byte
independent adequacy receipts. It answers one narrow question:

  Does every behavior in the exact bound registry have at least one selected
  Brain-owned, resource-admissible, independently verified policy whose policy
  basis structurally covers the behavior contract and all current ABC extensions?

A pass authenticates the current registry's positive policy edges only. It does
not prove the registry exhausts the universal target trace, U is empty, D
finality, or terminal success.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from canonical.runtime.effect_broker_receipt_resolver_v2 import resolve_receipt_bytes
from canonical.runtime.adequacy_basis_structural_completeness_gate_v1 import verify_policy_manifest
from canonical.runtime.behavioral_contract_extension_gate_v1 import verify_abc_extension_admission

SCHEMA="PROJECT_BRAIN_TERMINAL_POLICY_BASIS_AUTHENTICATOR_V1"
RECEIPT_SCHEMA="PROJECT_BRAIN_SELECTED_POLICY_ADEQUACY_RECEIPT_V1"
RECEIPT_FIELDS={
    "schema","behavior_id","policy_id","policy_manifest_git_blob_sha",
    "registry_git_blob_sha","independent_verified","exact_byte_bound",
    "conclusion","policy_adequate_on_declared_scope",
    "policy_safe_on_declared_scope","brain_owned","resource_admissible",
}
CLOSURE_FIELDS={
    "behavior_id","selected_policy_id","policy_manifest_ref",
    "adequacy_receipt_ref","abc_extension_atom_ids",
}

def _base(**more:Any)->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "pass":False,
        "status":"FAIL_CLOSED",
        "all_current_registry_behavior_edges_authenticated":False,
        "u_empty_authorized":False,
        "abc_closed_authorized":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        **more,
    }

def _resolve(ref:Any, root:Path):
    if not isinstance(ref,Mapping):
        raise ValueError("REFERENCE_REQUIRED")
    return resolve_receipt_bytes(ref,repo_root=root)

def evaluate(payload:Mapping[str,Any], *, repo_root:str|Path)->dict[str,Any]:
    if not isinstance(payload,Mapping):
        return _base(reason="PAYLOAD_MAPPING_REQUIRED")
    try:
        root=Path(repo_root).resolve(strict=True)
        registry_bound=_resolve(payload.get("registry_ref"),root)
        schema_bound=_resolve(payload.get("contract_schema_ref"),root)
    except Exception as exc:
        return _base(reason="REGISTRY_OR_SCHEMA_BINDING_INVALID",
                     exception_type=type(exc).__name__,detail=str(exc)[:180])

    registry=registry_bound["document"]
    contract_schema=schema_bound["document"]
    contracts=registry.get("active_contracted_residuals")
    if not isinstance(contracts,Sequence) or isinstance(contracts,(str,bytes)) or not contracts:
        return _base(reason="REGISTRY_ACTIVE_CONTRACTS_INVALID")

    contract_by_id={}
    for i,c in enumerate(contracts):
        if not isinstance(c,Mapping):
            return _base(reason="REGISTRY_CONTRACT_INVALID",index=i)
        bid=c.get("behavior_id")
        if not isinstance(bid,str) or not bid or bid in contract_by_id:
            return _base(reason="REGISTRY_BEHAVIOR_ID_INVALID_OR_DUPLICATE",index=i)
        contract_by_id[bid]=c

    closures=payload.get("closures")
    if not isinstance(closures,Sequence) or isinstance(closures,(str,bytes)):
        return _base(reason="CLOSURES_INVALID")
    closure_by_id={}
    closure_field_errors=[]
    for i,row in enumerate(closures):
        if not isinstance(row,Mapping):
            closure_field_errors.append(f"CLOSURE_NOT_OBJECT:{i}")
            continue
        if set(row)!=CLOSURE_FIELDS:
            bid=str(row.get("behavior_id") or i)
            closure_field_errors.append(f"CLOSURE_FIELDS_INVALID:{bid}")
            continue
        bid=row.get("behavior_id")
        if not isinstance(bid,str) or not bid or bid in closure_by_id:
            closure_field_errors.append(f"CLOSURE_BEHAVIOR_ID_INVALID_OR_DUPLICATE:{i}")
            continue
        closure_by_id[bid]=row

    expected=set(contract_by_id)
    supplied=set(closure_by_id)
    missing=sorted(expected-supplied)
    extra=sorted(supplied-expected)
    if closure_field_errors or missing or extra:
        return _base(
            reason="CONTRACT_CLOSURE_DOMAIN_MISMATCH",
            errors=sorted(closure_field_errors),
            open_behavior_ids=missing,
            extra_behavior_ids=extra,
            authenticated_behavior_count=0,
            registry_behavior_count=len(expected),
            registry_git_blob_sha=registry_bound["git_blob_sha"],
            contract_schema_git_blob_sha=schema_bound["git_blob_sha"],
        )

    errors=[]
    authenticated=[]
    details=[]
    for bid in sorted(expected):
        row=closure_by_id[bid]
        contract=contract_by_id[bid]
        selected=row.get("selected_policy_id")
        if not isinstance(selected,str) or not selected:
            errors.append(f"SELECTED_POLICY_ID_INVALID:{bid}")
            continue

        try:
            manifest_bound=_resolve(row.get("policy_manifest_ref"),root)
        except Exception:
            errors.append(f"POLICY_MANIFEST_BINDING_INVALID:{bid}")
            continue
        manifest=manifest_bound["document"]
        structural=verify_policy_manifest(contract,contract_schema,manifest)
        if structural.get("pass") is not True:
            errors.append(f"POLICY_MANIFEST_STRUCTURAL_INCOMPLETE:{bid}")
            details.append({"behavior_id":bid,"structural_errors":structural.get("errors",[])})
            continue

        manifest_policies=manifest.get("policies") or []
        if selected not in {p.get("policy_id") for p in manifest_policies if isinstance(p,Mapping)}:
            errors.append(f"SELECTED_POLICY_NOT_IN_MANIFEST:{bid}")
            continue

        extension=verify_abc_extension_admission(contract,row.get("abc_extension_atom_ids"))
        if extension.get("pass") is not True:
            errors.append(f"ABC_EXTENSION_ADMISSION_INCOMPLETE:{bid}")
            details.append({"behavior_id":bid,"extension_errors":extension.get("errors",[])})
            continue

        try:
            receipt_bound=_resolve(row.get("adequacy_receipt_ref"),root)
        except Exception:
            errors.append(f"ADEQUACY_RECEIPT_BINDING_INVALID:{bid}")
            continue
        receipt=receipt_bound["document"]
        if set(receipt)!=RECEIPT_FIELDS:
            errors.append(f"ADEQUACY_RECEIPT_FIELDS_INVALID:{bid}")
            continue
        if receipt.get("schema")!=RECEIPT_SCHEMA:
            errors.append(f"ADEQUACY_RECEIPT_SCHEMA_INVALID:{bid}")
            continue
        if receipt.get("behavior_id")!=bid:
            errors.append(f"ADEQUACY_RECEIPT_BEHAVIOR_MISMATCH:{bid}")
            continue
        if receipt.get("policy_id")!=selected:
            errors.append(f"ADEQUACY_RECEIPT_POLICY_MISMATCH:{bid}")
            continue
        if receipt.get("policy_manifest_git_blob_sha")!=manifest_bound["git_blob_sha"]:
            errors.append(f"ADEQUACY_RECEIPT_MANIFEST_MISMATCH:{bid}")
            continue
        if receipt.get("registry_git_blob_sha")!=registry_bound["git_blob_sha"]:
            errors.append(f"ADEQUACY_RECEIPT_REGISTRY_MISMATCH:{bid}")
            continue

        required_true=(
            "independent_verified","exact_byte_bound",
            "policy_adequate_on_declared_scope","policy_safe_on_declared_scope",
            "brain_owned","resource_admissible",
        )
        if receipt.get("conclusion")!="success" or any(receipt.get(k) is not True for k in required_true):
            errors.append(f"ADEQUACY_RECEIPT_CLAIMS_UNSATISFIED:{bid}")
            continue

        authenticated.append(bid)
        details.append({
            "behavior_id":bid,
            "selected_policy_id":selected,
            "policy_manifest_git_blob_sha":manifest_bound["git_blob_sha"],
            "adequacy_receipt_git_blob_sha":receipt_bound["git_blob_sha"],
            "abc_extension_atom_count":len(row.get("abc_extension_atom_ids") or []),
        })

    open_ids=sorted(expected-set(authenticated))
    if errors:
        return _base(
            reason="ONE_OR_MORE_POLICY_EDGES_UNAUTHENTICATED",
            errors=sorted(set(errors)),
            open_behavior_ids=open_ids,
            authenticated_behavior_ids=sorted(authenticated),
            authenticated_behavior_count=len(authenticated),
            registry_behavior_count=len(expected),
            registry_git_blob_sha=registry_bound["git_blob_sha"],
            contract_schema_git_blob_sha=schema_bound["git_blob_sha"],
            behavior_results=details,
        )

    return {
        "schema":SCHEMA,
        "pass":True,
        "status":"PASS__ALL_BOUND_REGISTRY_BEHAVIORS_HAVE_AUTHENTICATED_POSITIVE_POLICY_EDGES",
        "registry_git_blob_sha":registry_bound["git_blob_sha"],
        "contract_schema_git_blob_sha":schema_bound["git_blob_sha"],
        "registry_behavior_count":len(expected),
        "authenticated_behavior_count":len(authenticated),
        "authenticated_behavior_ids":sorted(authenticated),
        "open_behavior_ids":[],
        "behavior_results":details,
        "all_current_registry_behavior_edges_authenticated":True,
        "scope_boundary":"EXACT_BOUND_BEHAVIORAL_REGISTRY_ONLY__UNIVERSAL_TARGET_TRACE_COVERAGE_AND_SELECTED_DISCRIMINATOR_TOTALITY_REMAIN_SEPARATE",
        "u_empty_authorized":False,
        "abc_closed_authorized":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
    }
