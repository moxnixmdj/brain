"""R2 V45 residual-TOP authority coherence verifier.

Verifies the load-bearing current projection across:
- V25 direct-route activation,
- CURRENT_R2_DECISION_INTELLIGENCE,
- CURRENT_TERMINAL_AUTHORITY,
- V11 / fixed-point exact runtime blobs,
- residual producer/verifier/source-proof/parser blobs,
- the immutable V44 scheduler cut retained by V45,
- the sealed residual-TOP verification record.

This verifier grants no terminal credit. It checks coherence of declared authority
and exact bytes only.
"""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_R2_V45_RESIDUAL_TOP_AUTHORITY_COHERENCE_VERIFY_V1"
EXPECTED_ROUTE_ID="DIRECT_ADEQUACY::CROSS_DOCUMENT_RESIDUAL_EFFECT_FRONTIER_V1"

EXPECTED={
    "activation":"canonical/governance/R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_ACTIVATION_20261009_V25.json",
    "current_r2":"canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json",
    "terminal":"canonical/governance/CURRENT_TERMINAL_AUTHORITY.json",
    "scheduler":"canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V44.json",
    "runtime":"canonical/runtime/r2_direct_end_to_end_adequacy_v11.py",
    "fixed_point":"canonical/runtime/general_adequate_decision_fixed_point_v2.py",
    "fixed_point_test":"canonical/tests/test_general_adequate_decision_fixed_point_v2.py",
    "residual_route":"canonical/runtime/r2_cross_document_residual_effect_direct_adequacy_v1.py",
    "residual_producer":"canonical/runtime/cross_document_residual_effect_frontier_v1.py",
    "residual_verifier":"canonical/runtime/cross_document_residual_effect_frontier_verify_v1.py",
    "source_proof":"canonical/runtime/source_aligned_semantic_proof_v7.py",
    "scope_parser":"canonical/runtime/certified_effect_target_scope_v1.py",
    "inventory_parser":"canonical/runtime/certified_effect_id_inventory_v1.py",
    "verification":"canonical/verification/R2_CROSS_DOCUMENT_RESIDUAL_TOP_VERIFY_20261009_V1.json",
}

def _blob_sha(raw:bytes)->str:
    header=f"blob {len(raw)}\0".encode("ascii")
    return sha1(header+raw).hexdigest()

def _read(root:Path,rel:str)->bytes:
    path=(root/rel).resolve()
    if root not in path.parents:
        raise ValueError("PATH_OUTSIDE_ROOT:"+rel)
    if not path.is_file() or path.is_symlink():
        raise ValueError("FILE_REQUIRED:"+rel)
    return path.read_bytes()

def _json(root:Path,rel:str)->tuple[dict[str,Any],str]:
    raw=_read(root,rel)
    try:
        obj=json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise ValueError("JSON_INVALID:"+rel) from exc
    if not isinstance(obj,Mapping):
        raise ValueError("JSON_OBJECT_REQUIRED:"+rel)
    return dict(obj),_blob_sha(raw)

def _eq(errors:list[str],name:str,actual:Any,expected:Any)->None:
    if actual!=expected:
        errors.append(f"{name}:{actual!r}!={expected!r}")

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
    root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
    errors:list[str]=[]
    evidence:dict[str,Any]={}
    try:
        activation,activation_sha=_json(root,EXPECTED["activation"])
        current,current_sha=_json(root,EXPECTED["current_r2"])
        terminal,terminal_sha=_json(root,EXPECTED["terminal"])
        scheduler,_scheduler_sha=_json(root,EXPECTED["scheduler"])
        verification,verification_sha=_json(root,EXPECTED["verification"])

        actual_sha={key:_blob_sha(_read(root,rel)) for key,rel in EXPECTED.items()}
        evidence["actual_git_blob_sha"]=actual_sha
        evidence["current_r2_blob_sha"]=current_sha
        evidence["terminal_blob_sha"]=terminal_sha

        routes=activation.get("current_routes")
        if not isinstance(routes,list):
            errors.append("ACTIVATION_CURRENT_ROUTES_NOT_LIST")
            routes=[]
        route_rows=[
            x for x in routes
            if isinstance(x,Mapping) and x.get("route_id")==EXPECTED_ROUTE_ID
        ]
        if len(route_rows)!=1:
            errors.append("RESIDUAL_ROUTE_COUNT_NOT_ONE")
            route={}
        else:
            route=dict(route_rows[0])

        _eq(errors,"ACTIVATION_ROUTE_COUNT",activation.get("current_route_count"),31)
        _eq(errors,"ACTIVATION_ROUTE_LIST_COUNT",len(routes),31)
        _eq(errors,"ACTIVATION_EXACT_COUNT",activation.get("exact_cell_count"),3)
        _eq(errors,"ACTIVATION_BOUNDED_COUNT",activation.get("bounded_family_count"),28)
        _eq(
            errors,
            "ACTIVATION_COUNT_SUM",
            (activation.get("exact_cell_count") or 0)+(activation.get("bounded_family_count") or 0),
            31,
        )
        _eq(errors,"ACTIVATION_RUNTIME",activation.get("runtime"),EXPECTED["runtime"])
        _eq(
            errors,
            "ACTIVATION_RUNTIME_BINDING_PATH",
            (activation.get("runtime_binding") or {}).get("path"),
            EXPECTED["runtime"],
        )
        _eq(
            errors,
            "ACTIVATION_RUNTIME_BINDING_SHA",
            (activation.get("runtime_binding") or {}).get("git_blob_sha"),
            actual_sha["runtime"],
        )
        _eq(
            errors,
            "ACTIVATION_CONTROLLER_BINDING_SHA",
            (activation.get("controller_binding") or {}).get("git_blob_sha"),
            actual_sha["fixed_point"],
        )
        _eq(
            errors,
            "ACTIVATION_SUPERSEDES_V24",
            (activation.get("supersedes") or {}).get("path"),
            "canonical/governance/R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_ACTIVATION_20261009_V24.json",
        )

        route_bindings={
            "runtime_git_blob_sha":"residual_route",
            "producer_git_blob_sha":"residual_producer",
            "independent_verifier_git_blob_sha":"residual_verifier",
            "source_proof_git_blob_sha":"source_proof",
            "source_scope_parser_git_blob_sha":"scope_parser",
            "effect_id_inventory_parser_git_blob_sha":"inventory_parser",
        }
        for field,key in route_bindings.items():
            _eq(errors,"ROUTE_"+field.upper(),route.get(field),actual_sha[key])
        _eq(
            errors,
            "ROUTE_VERIFICATION_SHA",
            (route.get("verification") or {}).get("git_blob_sha"),
            actual_sha["verification"],
        )

        direct=current.get("direct_adequacy") or {}
        controller=current.get("controller") or {}
        _eq(errors,"CURRENT_R2_ACTIVATION_PATH",direct.get("activation_path"),EXPECTED["activation"])
        _eq(errors,"CURRENT_R2_ACTIVATION_SHA",direct.get("activation_git_blob_sha"),activation_sha)
        _eq(errors,"CURRENT_R2_ROUTE_COUNT",direct.get("current_route_count"),31)
        _eq(errors,"CURRENT_R2_EXACT_COUNT",direct.get("exact_cell_count"),3)
        _eq(errors,"CURRENT_R2_BOUNDED_COUNT",direct.get("bounded_family_count"),28)
        _eq(errors,"CURRENT_R2_RUNTIME_PATH",direct.get("direct_runtime_path"),EXPECTED["runtime"])
        _eq(errors,"CURRENT_R2_RUNTIME_SHA",direct.get("direct_runtime_git_blob_sha"),actual_sha["runtime"])
        _eq(errors,"CURRENT_R2_FIXED_POINT_SHA",controller.get("fixed_point_git_blob_sha"),actual_sha["fixed_point"])
        _eq(
            errors,
            "CURRENT_R2_FIXED_POINT_TEST_SHA",
            controller.get("fixed_point_regression_test_git_blob_sha"),
            actual_sha["fixed_point_test"],
        )
        _eq(
            errors,
            "CURRENT_R2_LATEST_VERIFY_PATH",
            direct.get("latest_verification_path"),
            EXPECTED["verification"],
        )
        _eq(
            errors,
            "CURRENT_R2_LATEST_VERIFY_SHA",
            direct.get("latest_verification_git_blob_sha"),
            verification_sha,
        )

        source=terminal.get("authoritative_sources") or {}
        source_r2=source.get("current_r2_decision_intelligence") or {}
        live=terminal.get("live_truth") or {}
        precedence=terminal.get("r2_scheduler_precedence") or {}
        recon=terminal.get("r2_v45_residual_top_reconciliation") or {}

        _eq(errors,"TERMINAL_CURRENT_R2_PATH",source_r2.get("path"),EXPECTED["current_r2"])
        _eq(errors,"TERMINAL_ROUTE_COUNT",live.get("r2_direct_adequacy_route_count"),31)
        _eq(errors,"TERMINAL_EXACT_COUNT",live.get("r2_direct_adequacy_exact_cell_count"),3)
        _eq(errors,"TERMINAL_BOUNDED_COUNT",live.get("r2_direct_adequacy_bounded_family_count"),28)
        _eq(errors,"TERMINAL_RESIDUAL_TOP_BOUND",live.get("r2_source_backed_cross_document_residual_top_bound"),True)
        _eq(
            errors,
            "TERMINAL_PROOF_OBLIGATIONS_BOUND",
            live.get("r2_cross_document_residual_top_proof_obligations_exposed_to_resolver"),
            True,
        )
        _eq(
            errors,
            "TERMINAL_SCHEDULER_PATH",
            precedence.get("current_scheduler_path"),
            EXPECTED["scheduler"],
        )
        _eq(
            errors,
            "TERMINAL_SCHEDULER_SHA",
            precedence.get("current_scheduler_git_blob_sha"),
            actual_sha["scheduler"],
        )
        _eq(errors,"TERMINAL_V45_ROUTE_COUNT",recon.get("route_count"),31)
        _eq(errors,"TERMINAL_V45_BOUNDED_COUNT",recon.get("bounded_family_count"),28)
        _eq(errors,"TERMINAL_V45_ACTIVATION_SHA",recon.get("direct_activation_git_blob_sha"),activation_sha)
        _eq(errors,"TERMINAL_V45_RUNTIME_SHA",recon.get("direct_runtime_git_blob_sha"),actual_sha["runtime"])
        _eq(errors,"TERMINAL_V45_FIXED_POINT_SHA",recon.get("fixed_point_controller_git_blob_sha"),actual_sha["fixed_point"])
        _eq(errors,"TERMINAL_V45_VERIFY_SHA",recon.get("verification_git_blob_sha"),verification_sha)
        _eq(errors,"TERMINAL_V45_CREDIT",recon.get("terminal_credit_delta"),0)
        _eq(errors,"TERMINAL_V45_TERMINAL_FALSE",recon.get("terminal_remains_false"),True)

        _eq(errors,"VERIFICATION_TOTAL_PASS",((verification.get("isolated_verification") or {}).get("total_passed")),77)
        _eq(errors,"VERIFICATION_TOTAL_FAIL",((verification.get("isolated_verification") or {}).get("total_failed")),0)
        _eq(errors,"VERIFICATION_TERMINAL_AUTHORITY",verification.get("terminal_authority"),False)

        if not (current.get("status") or "").startswith("ACTIVE_CURRENT_R2_AUTHORITY__V45__"):
            errors.append("CURRENT_R2_STATUS_NOT_V45")
        if source_r2.get("status")!=current.get("status"):
            errors.append("TERMINAL_CURRENT_R2_STATUS_PROJECTION_MISMATCH")
        if "THIRTY_ONE_DIRECT_ROUTES" not in str(precedence.get("rule") or ""):
            errors.append("TERMINAL_PRECEDENCE_RULE_ROUTE_COUNT_STALE")
        if "SOURCE_BACKED_RESIDUAL_TOP" not in str(precedence.get("rule") or ""):
            errors.append("TERMINAL_PRECEDENCE_RULE_RESIDUAL_TOP_MISSING")

        # The V44 scheduler remains intentionally unchanged. Verify its declared
        # schema/object is present rather than inventing a V45 scheduler cut.
        if not scheduler:
            errors.append("SCHEDULER_EMPTY")

    except Exception as exc:
        errors.append(type(exc).__name__+":"+str(exc))

    return {
        "schema":SCHEMA,
        "verified":not errors,
        "status":"PASS__R2_V45_RESIDUAL_TOP_AUTHORITY_COHERENT" if not errors else "FAIL_CLOSED",
        "errors":sorted(set(errors)),
        "evidence":evidence,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "boundary":"AUTHORITY_PROJECTION_AND_CONTENT_ADDRESS_COHERENCE_ONLY",
    }
