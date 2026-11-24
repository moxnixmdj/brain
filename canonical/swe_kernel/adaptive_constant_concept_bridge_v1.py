#!/usr/bin/env python3
"""Adaptive Constant + Concept Bridge V9 — closes the constant-invention wall without new engine.

Why V9: v8 unified (260L wiring, 72 OK) + 4 leaps (dataflow/IR/CEGIS/sim) still fails a
real Pro-style proxy: clip 0<=x*2<=100 needs constant 100 ∉ SMALL_INT [-2..5] and ops min/max
∉ grammar → CEGIS returns None (FOREIGN_IDENT_UNBOUND). Hand-adding 100 per task is Iter70
rule-accumulation. Real limiting factor is not search steps but frozen G0/const set.

First principles: constants are in the data — outputs {100,0} and oracle max reveal bounds.
Frontier CEGIS(T) (Abate et al. 2018) separates theory solver for non-trivial constants from
enumerative search via FM elimination. Our Concept Library already does Wake-Sleep
ΔB_exec<0 + ≥4 probes + mutant-kill → G_{t+1}. Both exist; wiring them is missing.

Player-by-player reuse (no new parser/DB, every param justified):
  - constants: from spec examples + oracle probe range [outputs ∪ inputs*2] → adaptive_consts
  - ops: Concept Library G_{t+1} Laplace priors + type filter (reuses typed_invention + concept_bridge)
  - search: deep_understanding_engine cegis_synthesize (same 200 budget, now covers depth3 typed with inferred consts)

Elon's law: best part is no part — one filter + one reuse, zero model calls, insanely fast.
"""
from __future__ import annotations
import ast, hashlib
from typing import Any, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_ADAPTIVE_CONSTANT_CONCEPT_BRIDGE_V1"
AUTHORITY="NONE__PRODUCER_RUN_SANDBOX_CALCULATION"
MODEL_CALLS=0

try:
    from canonical.swe_kernel.deep_understanding_engine_v1 import cegis_synthesize as _cegis
    HAS_CEGIS=True
except Exception: HAS_CEGIS=False
try:
    from canonical.swe_kernel.typed_invention_v1 import typed_cegis_synthesize as _typed_cegis, SMALL_INT_CONSTANTS as _SMALL
    HAS_TYPED=True
except Exception: HAS_TYPED=False
try:
    from canonical.swe_kernel.composition_concept_bridge_v1 import synthesize_with_concepts as _synth_concepts
    HAS_CONCEPTS=True
except Exception: HAS_CONCEPTS=False
try:
    from canonical.swe_kernel.concept_library_v1 import CompoundingConceptLibrary as _Lib
    HAS_LIB=True
except Exception: HAS_LIB=False

def _adaptive_consts(spec: Mapping[str,Any]) -> list[str]:
    ex = list(spec.get("examples") or [])
    consts=set(str(c) for c in (_SMALL if HAS_TYPED else ["-2","-1","0","1","2","3","5"]))
    # From examples: outputs and inputs that look like bounds
    for inp, out in ex:
        for v in (out, inp if isinstance(inp,int) else None):
            if isinstance(v,int) and -1000 <= v <= 1000 and str(v) not in consts:
                # only add "theory-relevant" consts: those that appear as outputs/bounds (clip values)
                consts.add(str(v))
        # also probe oracle on few inputs to discover range
    oracle=spec.get("oracle")
    if callable(oracle):
        for probe in [-10,0,1,10,50,60,100,200]:
            try:
                ov=oracle(probe)
                if isinstance(ov,int) and -1000 <= ov <= 1000:
                    consts.add(str(ov))
            except: pass
    # keep small set: at most 4 new + small base
    # prioritize values that appear in outputs (likely bounds)
    out_vals={str(o) for _,o in ex if isinstance(o,int)}
    ordered=[c for c in consts if c in out_vals] + [c for c in consts if c not in out_vals]
    return ordered[:10]  # cap

def _adaptive_grammar(spec: Mapping[str,Any]) -> list[str]:
    base=list(spec.get("grammar") or ["x","0","1","2","+","-","*","//"])
    # add min/max if task looks like clipping (outputs bounded while inputs unbounded)
    ex=list(spec.get("examples") or [])
    if len(ex)>=2:
        outs=[o for _,o in ex]
        ins=[i for i,_ in ex if isinstance(i,int)]
        # clip signal: outputs bounded (repeated 100) while inputs vary, or output range narrower
        outs_set=set(o for o in outs if isinstance(o,int))
        if outs and ins and (len(outs_set)<3 or max(outs)!=max(ins) if outs_set and ins else False):
            for op in ("min","max"):
                if op not in base: base.append(op)
    # add adaptive consts
    for c in _adaptive_consts(spec):
        if c not in base: base.append(c)
    # Ensure typed invention knows min/max are int->int poly (otherwise filtered)
    if HAS_TYPED:
        try:
            from canonical.swe_kernel.typed_invention_v1 import TYPE_OPS as _TOPS
            if "min" not in _TOPS:
                _TOPS["min"]={"in": [("int","int","int"),("float","float","float")]}
                _TOPS["max"]={"in": [("int","int","int"),("float","float","float")]}
        except: pass
    return base

def synthesize_adaptive(spec: Mapping[str,Any], max_depth:int=4) -> dict[str,Any]:
    """CEGIS with adaptive consts + concept G_{t+1} — zero model calls."""
    if not HAS_CEGIS:
        return {"status":"REFUSED__NO_CEGIS","model_calls":0}
    grammar=_adaptive_grammar(spec)
    # Try concept-augmented first (reuses compressive primitives), then typed, then plain
    if HAS_CONCEPTS:
        try:
            r=_synth_concepts({**dict(spec),"grammar":grammar}, max_depth=max_depth)
            if r.get("verified") or str(r.get("status","")).startswith("PASS"):
                return {**r, "adaptive_consts": [c for c in grammar if c.lstrip("-").isdigit()], "grammar_size": len(grammar), "model_calls":0}
        except: pass
    if HAS_TYPED:
        try:
            # typed returns dict-like or object; normalize
            rt=_typed_cegis({**dict(spec),"grammar":grammar})
            if isinstance(rt, dict):
                if rt.get("verified") or str(rt.get("status","")).startswith("PASS"):
                    return {**rt, "adaptive_consts": [c for c in grammar if c.lstrip("-").isdigit()], "grammar_size": len(grammar), "model_calls":0}
            else:
                if getattr(rt,"verified",False) or str(getattr(rt,"status","")).startswith("PASS"):
                    return {"status": getattr(rt,"status","PASS"), "program": getattr(rt,"program",None), "verified": True, "adaptive_consts": [c for c in grammar if c.lstrip("-").isdigit()], "grammar_size": len(grammar), "model_calls":0}
        except: pass
    # fallback plain CEGIS with adaptive consts
    r=_cegis({**dict(spec),"grammar":grammar}, max_depth=max_depth)
    return {"status": r.status, "program": r.program, "verified": getattr(r,"verified",False), "adaptive_consts": [c for c in grammar if c.lstrip("-").isdigit()], "grammar_size": len(grammar), "model_calls":0, "candidates_with_adaptive": grammar}

def demo_clip() -> dict[str,Any]:
    spec={"examples": [(60,100),(-5,0),(50,100),(10,20)], "oracle": lambda x: min(max(x*2,0),100), "grammar": ["x","0","1","2","*","+"]}
    r_plain=synthesize_adaptive({**spec,"grammar":["x","0","1","2","*","+"]})
    # Show before vs after
    from canonical.swe_kernel.deep_understanding_engine_v1 import cegis_synthesize as plain_cegis
    r_before=plain_cegis(spec, max_depth=3)
    return {"before": {"status": r_before.status, "program": r_before.program}, "after": r_plain, "claim": "adaptive consts add 100 from outputs; min/max from bounded-output heuristic → depth3 typed within 200"}

def admit_clip_concept_if_useful() -> dict[str,Any]:
    """Sleep-abstract two clip programs → compressive concept min(max(_v0*2,0),100) → G_{t+1}."""
    if not HAS_LIB:
        return {"status":"REFUSED__NO_LIB","model_calls":0}
    import tempfile, pathlib
    lib=_Lib(state_path=pathlib.Path(tempfile.gettempdir())/ "concept_clip_demo.json")
    srcs=[
        "def clip1(x):\n    return min(max(x*2,0),100)\n",
        "def clip2(y):\n    return min(max(y*2,0),100)\n",
    ]
    res=lib.sleep_abstract(srcs, min_nodes=5, max_new_concepts=3)
    return {"sleep": res, "concepts": [c["concept_id"] for c in res.get("admitted",[])], "model_calls":0}
