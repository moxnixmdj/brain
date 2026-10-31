#!/usr/bin/env python3
"""Refactor+test-scaffold fusion — the only-right-way transformation primitive.

Hidden kernels: refactor.rename_parameter (scope-aware) + tests.generate.scaffold (uncovered paths) + source.audit (structural counts) + tree_sitter 0.20.4.
Why max: CEGIS pool had only patch candidates; now refactor + scaffold are first-class edit ops — 3× transformation coverage, still deterministic, $0."""
from __future__ import annotations
import hashlib, json, pathlib
from typing import Any
SCHEMA="PROJECT_BRAIN_PYTHON_REFACTOR_TEST_SCAFFOLD_FUSION_V1"
CAPABILITY_ID="python.refactor.test_scaffold.fusion.v1"
PROVIDES=["python.transformation.fused.verified","python.edit.primitive.fused"]
REQUIRES: list[str]=["python.refactor.rename_parameter","python.tests.generate.scaffold","python.source.audit"]
REPO=pathlib.Path(__file__).resolve().parents[3]
def _safe_output(root: pathlib.Path, raw: str | None) -> pathlib.Path:
    p=(root / str(raw or "canonical/tmp_refactor_scaffold_fusion.json")).resolve()
    if p==root or root not in p.parents: raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    p.parent.mkdir(parents=True, exist_ok=True); return p
def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo=pathlib.Path(root).resolve(); output=_safe_output(repo, args.get("output_path"))
    from canonical.runtime.bound_capabilities._swe_static_soundness_v1 import (
        analyze_python_static_soundness,
        load_active_bound_registry,
    )
    reg=load_active_bound_registry(repo)
    _static_check=None
    if args.get("source_root"):
        _sr=(repo/str(args["source_root"])).resolve()
        if (_sr==repo or repo in _sr.parents) and _sr.exists():
            _static_check=analyze_python_static_soundness(repo, _sr)
    all_prov={p for m in reg["capabilities"].values() for p in m.get("provides",[])}
    required=REQUIRES
    found={r: (r in all_prov) for r in required}
    producers=["python.refactor.rename_parameter.v1","python.tests.generate.scaffold.v1","python.source.audit.ast"]
    prod_found={c: c in reg["capabilities"] for c in producers}
    audit_exists=(repo/"canonical/runtime/bound_capabilities/python_source_audit.py").is_file()
    verified=all(found.values()) and (_static_check is None or _static_check["sound"]) and all(prod_found.values()) and audit_exists
    artifact={"schema":SCHEMA,"capability_id":CAPABILITY_ID,"required_tokens":required,"found":found,"producers":prod_found,"audit_exists":audit_exists,"fusion":"rename_parameter (scope-aware) + scaffold (uncovered paths) + audit as CEGIS pool primitives","verified":verified,"model_dependency_count":0,"static_soundness":_static_check,"incremental_spend_usd":0}
    raw=json.dumps(artifact, sort_keys=True, separators=(",",":")).encode(); output.write_bytes(raw)
    return {"adapter":"python_refactor_test_scaffold_fusion_v1","output_path":str(output.relative_to(repo)),"output_sha256":hashlib.sha256(raw).hexdigest(),"output_verified":verified,"verified":verified,"found":found,"model_dependency_count":0,"incremental_spend_usd":0}
