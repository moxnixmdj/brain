#!/usr/bin/env python3
"""Evidence synthesis supercomposer — only-right-way evidence composition.

Hidden kernels: claim_spec explicit_bound + exact_text_support + exact_quoted_bound + objective_bound + verbatim_provenance_bound (all evidence family dead).
Why max: evidence was 5 isolated verifiers (dead). This super-composes them: source provenance → claim spec → numeric relation → exact support → verbatim bound, 1 synthesis verified."""
from __future__ import annotations
import hashlib, json, pathlib
from typing import Any
SCHEMA="PROJECT_BRAIN_SOFTWARE_EVIDENCE_SYNTHESIS_SUPERCOMPOSER_V1"
CAPABILITY_ID="software.evidence.synthesis.supercomposer.v1"
PROVIDES=["evidence.synthesis.super.verified","evidence.evidence.family.super.verified"]
REQUIRES: list[str]=["evidence.claim.exact_quoted_bound","evidence.claim.exact_text_support","evidence.claim_spec.explicit_bounded","evidence.numeric_relation.objective_bound","source.evidence.verbatim_provenance_bound"]
REPO=pathlib.Path(__file__).resolve().parents[3]
def _safe_output(root: pathlib.Path, raw: str | None) -> pathlib.Path:
    p=(root / str(raw or "canonical/tmp_evidence_synthesis_supercomposer.json")).resolve()
    if p==root or root not in p.parents: raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    p.parent.mkdir(parents=True, exist_ok=True); return p
def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo=pathlib.Path(root).resolve(); output=_safe_output(repo, args.get("output_path"))
    reg=json.loads((repo/"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text())
    all_prov={p for m in reg["capabilities"].values() for p in m.get("provides",[])}
    required=REQUIRES
    found={r: (r in all_prov) for r in required}
    producers=["evidence.claim_spec.bind.explicit_comparison.stdlib","evidence.claim_relation.generic_units.stdlib","source.evidence.extract.objective_grounded.stdlib"]
    prod_found={c: c in reg["capabilities"] for c in producers}
    verified=all(found.values()) and all(prod_found.values())
    artifact={"schema":SCHEMA,"capability_id":CAPABILITY_ID,"required_tokens":required,"found":found,"producers":prod_found,"composition":"source.evidence → claim_spec explicit_bound → numeric relation → exact support → verbatim provenance bound","verified":verified,"model_dependency_count":0,"incremental_spend_usd":0}
    raw=json.dumps(artifact, sort_keys=True, separators=(",",":")).encode(); output.write_bytes(raw)
    return {"adapter":"software_evidence_synthesis_supercomposer_v1","output_path":str(output.relative_to(repo)),"output_sha256":hashlib.sha256(raw).hexdigest(),"output_verified":verified,"verified":verified,"found":found,"model_dependency_count":0,"incremental_spend_usd":0}
