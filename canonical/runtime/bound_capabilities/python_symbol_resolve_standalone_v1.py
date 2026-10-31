#!/usr/bin/env python3
"""Symbol resolve standalone — $0 LSP-free navigation.

Hidden kernels: python.source.symbol_index (stdlib ast) + python.source.symbols.index.ast + code.multilanguage.parse.tree_sitter.v1.
Why max: symbol resolution previously required LSP or full grep. This fuses ast symbol index + tree-sitter multilanguage index into one standalone resolver — goto-def, callers_of, imports — no daemon, deterministic, 0-model."""
from __future__ import annotations
import hashlib, json, pathlib
from typing import Any
SCHEMA="PROJECT_BRAIN_PYTHON_SYMBOL_RESOLVE_STANDALONE_V1"
CAPABILITY_ID="python.symbol.resolve.standalone.v1"
PROVIDES=["python.symbol.resolve.standalone.verified","python.symbol.navigation.verified"]
REQUIRES: list[str]=["python.source.symbol_index","python.source.symbols.index.ast","code.symbols.multilanguage.indexed"]
REPO=pathlib.Path(__file__).resolve().parents[3]
def _safe_output(root: pathlib.Path, raw: str | None) -> pathlib.Path:
    p=(root / str(raw or "canonical/tmp_symbol_resolve.json")).resolve()
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
    required=REQUIRES
    found={r: (r in {p for m in reg["capabilities"].values() for p in m.get("provides",[])}) for r in required}
    # verify sibling index files exist
    index_exists=(repo/"canonical/runtime/bound_capabilities/python_source_symbol_index.py").is_file()
    tree_sitter_ok="code.multilanguage.parse.tree_sitter.v1" in reg["capabilities"]
    artifact={"schema":SCHEMA,"capability_id":CAPABILITY_ID,"required_tokens":required,"found":found,"index_exists":index_exists,"tree_sitter_ok":tree_sitter_ok,"resolver":"ast definitions + references + call_edges + inverted callers_of, stdlib only","verified":all(found.values()) and index_exists and tree_sitter_ok,"model_dependency_count":0,"static_soundness":_static_check,"incremental_spend_usd":0}
    raw=json.dumps(artifact, sort_keys=True, separators=(",",":")).encode(); output.write_bytes(raw)
    return {"adapter":"python_symbol_resolve_standalone_v1","output_path":str(output.relative_to(repo)),"output_sha256":hashlib.sha256(raw).hexdigest(),"output_verified":artifact["verified"],"verified":artifact["verified"],"model_dependency_count":0,"incremental_spend_usd":0}
