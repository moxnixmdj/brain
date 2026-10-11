"""Bound adapter for the verified general scientific raw-resource V2 pipeline.

The shared science pipeline accepts arbitrary local roots. This promoted adapter
intentionally narrows that interface to existing repository-local roots only.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime import general_scientific_raw_resource_pipeline_v2 as pipeline

SCHEMA="PROJECT_BRAIN_BOUND_GENERAL_SCIENTIFIC_RAW_RESOURCE_V2"
MAX_ROOTS=16


def _roots(repo:Path, raw:Any)->list[str]:
    if not isinstance(raw,Sequence) or isinstance(raw,(str,bytes)) or not raw or len(raw)>MAX_ROOTS:
        raise RuntimeError("SCIENCE_ROOTS_INVALID")
    repo=repo.resolve()
    out=[]
    for item in raw:
        if not isinstance(item,str) or not item.strip() or "\x00" in item:
            raise RuntimeError("SCIENCE_ROOT_INVALID")
        rel=Path(item)
        if rel.is_absolute():
            raise RuntimeError("ABSOLUTE_SCIENCE_ROOT_FORBIDDEN")
        p=(repo/rel).resolve()
        if p==repo or repo not in p.parents:
            raise RuntimeError("SCIENCE_ROOT_OUTSIDE_REPOSITORY")
        if not p.exists():
            raise RuntimeError("SCIENCE_ROOT_MISSING")
        s=str(p)
        if s not in out: out.append(s)
    return out


def run(args:Mapping[str,Any],root:Any)->dict[str,Any]:
    if not isinstance(args,Mapping):
        raise RuntimeError("ARGS_NOT_OBJECT")
    instruction=args.get("instruction")
    if not isinstance(instruction,str) or not instruction.strip() or len(instruction)>20000:
        raise RuntimeError("SCIENCE_INSTRUCTION_INVALID")
    repo=Path(root).resolve()
    roots=_roots(repo,args.get("roots"))
    out=pipeline.execute(instruction,roots)
    if out.get("verified") is not True:
        raise RuntimeError("SCIENCE_PIPELINE_NOT_VERIFIED:"+str(out.get("reason") or out.get("status")))
    return {
        "schema":SCHEMA,
        "adapter":"general_scientific_raw_resource_v2",
        "verified":True,
        "status":"PASS__BOUND_GENERAL_SCIENTIFIC_RAW_RESOURCE_V2",
        "family":out.get("family"),
        "receipt_sha256":out.get("receipt_sha256"),
        "scientific_result":out.get("scientific_result"),
        "compile_receipt_sha256":(out.get("compile_receipt") or {}).get("compile_receipt_sha256"),
        "model_dependency_count":0,
        "external_model_runtime_calls":0,
        "network_dependency_count":0,
        "input_root_count":len(roots),
        "terminal_authority":False,
    }
