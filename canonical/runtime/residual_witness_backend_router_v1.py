#!/usr/bin/env python3
"""Execution router for residual-to-witness retrieval actions.

The retrieval compiler decides what information to seek next. This router binds
that action to a concrete backend while preserving authority separation:

- backends may discover candidates;
- backends may report independently verified completeness only with a receipt;
- backends may never self-declare a candidate sufficient for acceptance;
- backend failure never becomes evidence of nonexistence.

Built-in zero-cost/model-independent adapters reuse the Brain's existing
package-registry and open-web discovery primitives. Other surfaces are injected
by the host through the same narrow provider contract.
"""
from __future__ import annotations

import copy
import importlib.util
import pathlib
from typing import Any, Callable, Mapping

from canonical.runtime import residual_witness_retrieval_compiler_v1 as core

SCHEMA="PROJECT_BRAIN_RESIDUAL_WITNESS_BACKEND_ROUTER_V1"
_PROVIDER_REGISTRY: dict[str, Callable[[Mapping[str, Any]], Mapping[str, Any]]] = {}

class RetrievalBackendError(RuntimeError):
    pass


def set_external_provider(surface: str, provider: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None) -> None:
    surface=str(surface or "").strip()
    if surface not in core.SURFACES:
        raise ValueError("BACKEND_SURFACE_INVALID")
    if provider is None:
        _PROVIDER_REGISTRY.pop(surface,None)
        return
    if not callable(provider):
        raise ValueError("BACKEND_PROVIDER_NOT_CALLABLE")
    _PROVIDER_REGISTRY[surface]=provider


def clear_external_providers() -> None:
    _PROVIDER_REGISTRY.clear()


def _load_bound(name: str):
    root=pathlib.Path(__file__).resolve().parent/"bound_capabilities"
    path=root/name
    spec=importlib.util.spec_from_file_location("project_brain_backend_"+name.replace(".","_"),path)
    if spec is None or spec.loader is None:
        raise RetrievalBackendError("BACKEND_MODULE_LOAD_FAILED:"+name)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _package_registry_provider(action: Mapping[str, Any]) -> Mapping[str, Any]:
    from canonical.runtime import capability_discovery
    result=capability_discovery.search_all(str(action.get("query") or ""),limit_per_source=12)
    candidates=result.get("candidates") or []
    return {
        "backend_id":"BRAIN_FEDERATED_PACKAGE_DISCOVERY_V1",
        "candidates":candidates,
        "complete":False,
        "independently_complete":False,
        "raw_status":result.get("schema"),
    }


def _open_web_provider(action: Mapping[str, Any]) -> Mapping[str, Any]:
    module=_load_bound("open_web_source_candidate_discovery.py")
    query=str(action.get("query") or "")
    result=module.discover(query,limit=20,timeout=15,query_override=query)
    return {
        "backend_id":"BRAIN_OPEN_WEB_DISCOVERY_V1",
        "candidates":result.get("candidates") or [],
        "complete":False,
        "independently_complete":False,
        "raw_status":result.get("status"),
        "backend_errors":result.get("backend_errors") or [],
    }


def _scholarly_provider(action: Mapping[str, Any]) -> Mapping[str, Any]:
    module=_load_bound("open_web_source_candidate_discovery.py")
    query=str(action.get("query") or "")
    candidates,trace=module._crossref(query,20,15)
    return {
        "backend_id":"BRAIN_CROSSREF_DISCOVERY_V1",
        "candidates":candidates,
        "complete":False,
        "independently_complete":False,
        "raw_status":trace,
    }


def _github_public_provider(action: Mapping[str, Any]) -> Mapping[str, Any]:
    from canonical.runtime import github_public_retrieval_provider_v1
    return github_public_retrieval_provider_v1.search(action,limit=20)


def default_providers() -> dict[str, Callable[[Mapping[str, Any]], Mapping[str, Any]]]:
    providers={
        "PACKAGE_REGISTRY":_package_registry_provider,
        "OPEN_WEB":_open_web_provider,
        "DOCUMENTATION":_open_web_provider,
        "SCHOLARLY":_scholarly_provider,
    }
    for surface in (
        "REPOSITORY_METADATA",
        "CODE_CONTENT",
        "SYMBOLS",
        "MANIFESTS",
        "TESTS_EXAMPLES",
        "ISSUES_PRS",
        "COMMITS_RELEASES_BRANCHES_TAGS",
    ):
        providers[surface]=_github_public_provider
    return providers


def _candidate_id(candidate: Mapping[str, Any], index: int) -> str:
    for key in ("candidate_id","url","repository","project","name","tool_id"):
        value=str(candidate.get(key) or "").strip()
        if value:
            return value
    return f"ANONYMOUS_CANDIDATE_{index:04d}"


def _normalize_result(
    action: Mapping[str, Any],
    raw: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(raw,Mapping):
        raise RetrievalBackendError("BACKEND_RESULT_MAPPING_REQUIRED")
    forbidden=(
        "verified_sufficient",
        "acceptance_credit",
        "family_credit",
        "capability_credit",
        "verified_witness",
    )
    if any(raw.get(key) not in (None,False,0,[],{}) for key in forbidden):
        raise RetrievalBackendError("BACKEND_AUTHORITY_VIOLATION")

    raw_candidates=raw.get("candidates") or []
    if not isinstance(raw_candidates,list):
        raise RetrievalBackendError("BACKEND_CANDIDATES_LIST_REQUIRED")
    candidates=[]
    for index,item in enumerate(raw_candidates):
        if not isinstance(item,Mapping):
            raise RetrievalBackendError("BACKEND_CANDIDATE_MAPPING_REQUIRED")
        if item.get("verified_sufficient") is True or item.get("acceptance_credit"):
            raise RetrievalBackendError("BACKEND_CANDIDATE_SELF_VERIFICATION")
        x=dict(item)
        x["candidate_id"]=_candidate_id(x,index)
        x["retrieval_surface"]=action["surface"]
        x["query_id"]=action["query_id"]
        x["query"]=action["query"]
        x["sufficiency_status"]="UNVERIFIED"
        candidates.append(x)

    complete=raw.get("complete") is True
    independently_complete=raw.get("independently_complete") is True
    completeness_receipt=str(raw.get("completeness_receipt") or "").strip()
    completeness_admitted=bool(complete and independently_complete and completeness_receipt)

    return {
        "schema":SCHEMA,
        "status":"BACKEND_RESULT_NORMALIZED",
        "backend_id":str(raw.get("backend_id") or "EXTERNAL_BACKEND"),
        "surface":action["surface"],
        "query_id":action["query_id"],
        "query":action["query"],
        "candidates":candidates,
        "candidate_count":len(candidates),
        "complete_asserted":complete,
        "independently_complete_asserted":independently_complete,
        "completeness_receipt":completeness_receipt or None,
        "completeness_admitted":completeness_admitted,
        "acceptance_credit":0,
    }


def _append_candidates(state: Mapping[str, Any], normalized: Mapping[str, Any]) -> dict[str, Any]:
    out=copy.deepcopy(dict(state))
    seen={
        (
            str(x.get("retrieval_surface") or ""),
            str(x.get("query_id") or ""),
            str(x.get("candidate_id") or ""),
        )
        for x in out.get("observed_candidates") or []
        if isinstance(x,Mapping)
    }
    bucket=out.setdefault("observed_candidates",[])
    for candidate in normalized.get("candidates") or []:
        key=(
            str(candidate.get("retrieval_surface") or ""),
            str(candidate.get("query_id") or ""),
            str(candidate.get("candidate_id") or ""),
        )
        if key not in seen:
            bucket.append(copy.deepcopy(candidate))
            seen.add(key)
    return out


def execute_action(
    program: Mapping[str, Any],
    state: Mapping[str, Any],
    action: Mapping[str, Any],
    provider: Callable[[Mapping[str, Any]], Mapping[str, Any]],
) -> dict[str, Any]:
    if action.get("action")!="QUERY":
        raise ValueError("QUERY_ACTION_REQUIRED")
    if action.get("surface") not in core.SURFACES:
        raise ValueError("QUERY_SURFACE_INVALID")
    try:
        raw=provider(dict(action))
        normalized=_normalize_result(action,raw)
    except RetrievalBackendError as exc:
        failed=core.update_cell(
            state,
            query_id=str(action["query_id"]),
            surface=str(action["surface"]),
            cell_state="FAILED_PERMANENT",
        )
        return {
            "schema":SCHEMA,
            "status":"BACKEND_REJECTED_PERMANENT",
            "error_class":type(exc).__name__,
            "error":str(exc)[:1000],
            "state":failed,
            "action":dict(action),
            "acceptance_credit":0,
        }
    except Exception as exc:
        failed=core.update_cell(
            state,
            query_id=str(action["query_id"]),
            surface=str(action["surface"]),
            cell_state="FAILED_TRANSIENT",
        )
        return {
            "schema":SCHEMA,
            "status":"BACKEND_FAILED_TRANSIENT",
            "error_class":type(exc).__name__,
            "error":str(exc)[:1000],
            "state":failed,
            "action":dict(action),
            "acceptance_credit":0,
        }

    with_candidates=_append_candidates(state,normalized)
    if normalized["candidate_count"]>0:
        cell_state="QUERIED_CANDIDATE"
        independent=False
    elif normalized["completeness_admitted"]:
        cell_state="EXHAUSTIVELY_CLOSED"
        independent=True
    else:
        cell_state="QUERIED_NO_CANDIDATE"
        independent=False

    updated=core.update_cell(
        with_candidates,
        query_id=str(action["query_id"]),
        surface=str(action["surface"]),
        cell_state=cell_state,
        candidate_count=normalized["candidate_count"],
        independently_complete=independent,
    )
    return {
        "schema":SCHEMA,
        "status":"BACKEND_EXECUTED",
        "result":normalized,
        "state":updated,
        "terminal":core.terminal_status(updated),
        "next_action":core.next_action(program,updated),
        "acceptance_credit":0,
    }


def execute_next(
    program: Mapping[str, Any],
    state: Mapping[str, Any],
    providers: Mapping[str, Callable[[Mapping[str, Any]], Mapping[str, Any]]] | None=None,
) -> dict[str, Any]:
    action=core.next_action(program,state)
    if action.get("action")!="QUERY":
        return {
            "schema":SCHEMA,
            "status":"NO_BACKEND_QUERY_REQUIRED",
            "action":action,
            "state":copy.deepcopy(dict(state)),
            "terminal":core.terminal_status(state),
            "acceptance_credit":0,
        }
    surface=str(action["surface"])
    merged=default_providers()
    merged.update(_PROVIDER_REGISTRY)
    if providers:
        merged.update(dict(providers))
    provider=merged.get(surface)
    if not callable(provider):
        failed=core.update_cell(
            state,
            query_id=str(action["query_id"]),
            surface=surface,
            cell_state="FAILED_PERMANENT",
        )
        return {
            "schema":SCHEMA,
            "status":"BACKEND_UNBOUND",
            "surface":surface,
            "action":action,
            "state":failed,
            "terminal":core.terminal_status(failed),
            "next_action":core.next_action(program,failed),
            "acceptance_credit":0,
        }
    return execute_action(program,state,action,provider)


def accept_independent_witness(
    state: Mapping[str, Any],
    *,
    witness_id: str,
    residual_id: str,
    source_surface: str,
    independent_receipt: str,
) -> dict[str, Any]:
    return core.add_verified_witness(
        state,
        witness_id=witness_id,
        residual_id=residual_id,
        source_surface=source_surface,
        independent_receipt=independent_receipt,
    )
