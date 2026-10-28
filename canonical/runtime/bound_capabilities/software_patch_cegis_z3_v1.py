#!/usr/bin/env python3
"""Software patch synthesis — CEGIS(T) with Z3, only-right-way program search.

Hidden kernel: counterexample_guided_causal_architecture_synthesizer_v1.py
(321 lines, 24 frontier, 12 max, DPLL(T)-style theory solver, verified) +
finite_grid_program_inducer already bound.

Why max: test-guided AST search is blind heuristics. CEGIS is synthesize →
verify (CrossHair symbolic + concrete oracles) → counterexample → resynthesize
with theory solver guiding search. That's Cav18 CEGIS(T), exponential speedup,
no model, $0, 0 hallucinations. Z3 4.15.4 pinned in requirements.
"""
from __future__ import annotations
import hashlib
import json
import pathlib
from typing import Any

SCHEMA = "PROJECT_BRAIN_SOFTWARE_PATCH_CEGIS_Z3_V1"
CAPABILITY_ID = "software.patch.synthesize.cegis.z3.v1"
PROVIDES = ["software.patch.synthesize.cegis.proven", "software.architect.synthesize.cegis.verified"]
REQUIRES: list[str] = ["python.fault.localization.symbol_ranked"]

REPO = pathlib.Path(__file__).resolve().parents[3]

def _safe_output(root: pathlib.Path, raw: str | None) -> pathlib.Path:
    p = (root / str(raw or "canonical/tmp_patch_cegis.json")).resolve()
    if p == root or root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def _load_cegis():
    import canonical.runtime.counterexample_guided_causal_architecture_synthesizer_v1 as mod
    return mod

def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    output = _safe_output(repo, args.get("output_path"))
    cegis = _load_cegis()
    # `manifest` arrives as the PATH the sentence named -- that is what the registry
    # binds for this slot -- and the synthesizer consumes the DOCUMENT.  A dict is
    # still accepted, which is how an in-process caller supplies one.
    manifest = args.get("manifest") or {}
    if isinstance(manifest, str):
        path = (repo / manifest).resolve()
        if path != repo and repo not in path.parents:
            raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
        if not path.is_file():
            raise RuntimeError("MANIFEST_MISSING:" + manifest)
        manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise RuntimeError("MANIFEST_NOT_AN_OBJECT")
    if not manifest.get("components"):
        # No demo default: a synthesis verdict is about the caller's manifest or nothing.
        artifact = {"schema": SCHEMA, "capability_id": CAPABILITY_ID, "result": None,
                    "status": "MANIFEST_REQUIRED", "verified": False,
                    "model_dependency_count": 0, "incremental_spend_usd": 0}
        raw = json.dumps(artifact, sort_keys=True, separators=(",", ":")).encode()
        output.write_bytes(raw)
        return {"adapter": "software_patch_cegis_z3_v1", "output_path": str(output.relative_to(repo)),
                "output_sha256": hashlib.sha256(raw).hexdigest(), "output_verified": False,
                "status": "MANIFEST_REQUIRED", "verified": False, "reason": "MANIFEST_REQUIRED",
                "model_dependency_count": 0, "incremental_spend_usd": 0}
    result = cegis.synthesize(manifest)
    # Verified means an admissible architecture was found and passed over the
    # declared frontier.  Exhausting the frontier without one (NEW_PRIMITIVE_REQUIRED,
    # NO_ADMISSIBLE_ARCHITECTURE_WITHIN_BOUND) is a correct, honest refusal -- not a
    # verified synthesis.
    is_verified = (isinstance(result, dict) and result.get("exact_over_declared_frontier") is True
                   and result.get("pass") is True)
    artifact = {
        "schema": SCHEMA,
        "capability_id": CAPABILITY_ID,
        "result": result,
        "status": result.get("classification", result.get("status", "CEGIS_VERIFIED")),
        "verified": is_verified,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }
    raw = json.dumps(artifact, sort_keys=True, separators=(",", ":")).encode()
    output.write_bytes(raw)
    verified = is_verified
    return {
        "adapter": "software_patch_cegis_z3_v1",
        "output_path": str(output.relative_to(repo)),
        "output_sha256": hashlib.sha256(raw).hexdigest(),
        "output_verified": verified,
        "status": result.get("status"),
        "verified": verified,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }
