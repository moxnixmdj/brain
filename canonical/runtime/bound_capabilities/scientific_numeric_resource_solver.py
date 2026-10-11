"""Bound-capability adapter for the verified scientific numeric resource pipeline."""
from __future__ import annotations

import pathlib
from typing import Any

from canonical.runtime import scientific_numeric_resource_pipeline_v1 as science

SCHEMA="PROJECT_BRAIN_BOUND_SCIENTIFIC_NUMERIC_RESOURCE_SOLVER_V1"


def _safe_existing_file(root:pathlib.Path,raw:Any)->pathlib.Path:
    value=str(raw or "").strip()
    if not value:
        raise ValueError("INPUT_PATH_REQUIRED")
    p=(root/value).resolve() if not pathlib.Path(value).is_absolute() else pathlib.Path(value).resolve()
    if p==root or root not in p.parents or not p.is_file():
        raise ValueError("INPUT_PATH_OUTSIDE_REPOSITORY_OR_MISSING")
    return p


def run(args,root):
    root=pathlib.Path(root).resolve()
    goal=str((args or {}).get("goal") or "").strip()
    if not goal:
        raise ValueError("GOAL_REQUIRED")
    input_path=_safe_existing_file(root,(args or {}).get("input_path"))
    result=science.execute(goal,[input_path])
    verified=result.get("verified") is True
    binding=result.get("resource_binding") if isinstance(result,dict) else {}
    inner=result.get("scientific_pipeline") if isinstance(result,dict) else {}
    return {
        "schema":SCHEMA,
        "status":"PASS__BOUND_SCIENTIFIC_NUMERIC_RESOURCE_SOLVED" if verified else "FAIL_CLOSED",
        "verified":bool(verified),
        "reason":None if verified else str(result.get("reason") or result.get("status") or "SCIENTIFIC_PIPELINE_NOT_VERIFIED"),
        "family":inner.get("family") if isinstance(inner,dict) else None,
        "selected_path":binding.get("selected_path") if isinstance(binding,dict) else None,
        "input_path":str(input_path.relative_to(root)).replace("\\","/"),
        "pipeline_receipt":result,
        "pipeline_receipt_sha256":result.get("receipt_sha256") if isinstance(result,dict) else None,
        "model_dependency_count":0,
        "external_model_runtime_calls":0,
        "network_dependency_count":0,
        "terminal_authority":False,
    }
