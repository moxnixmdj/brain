"""Deterministic task-contract extraction for zero-model scientific execution.

Extracts only explicit source facts from the task instruction. It does not infer
missing semantics and does not call any learned model or network service.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

SCHEMA = "PROJECT_BRAIN_SCIENCE_ZERO_MODEL_CONTRACT_V1"
_ABS_PATH_RE = re.compile(r"(?<![A-Za-z0-9_.-])(/(?:data|app|results)/[A-Za-z0-9_./-]+)")
_FENCE_RE = re.compile(r"```(?P<lang>[A-Za-z0-9_-]*)\n(?P<body>.*?)```", re.S)


def _uniq(items):
    out=[]
    for x in items:
        if x not in out:
            out.append(x)
    return out


def extract_explicit_contract(instruction: str) -> dict[str, Any]:
    if not isinstance(instruction, str) or not instruction.strip():
        raise ValueError("SCIENCE_INSTRUCTION_REQUIRED")
    paths=_uniq(m.group(1).rstrip(".,;:)") for m in _ABS_PATH_RE.finditer(instruction))
    inputs=[p for p in paths if p.startswith(("/data/","/app/"))]
    outputs=[p for p in paths if p.startswith("/results/")]

    json_templates=[]
    text_blocks=[]
    for m in _FENCE_RE.finditer(instruction):
        lang=m.group("lang").strip().lower()
        body=m.group("body").strip()
        if lang=="json" or (not lang and body.startswith("{")):
            try:
                obj=json.loads(body)
            except Exception:
                continue
            if isinstance(obj, dict):
                json_templates.append(obj)
        elif lang in {"text","txt","csv"}:
            text_blocks.append(body)

    low=instruction.lower()
    lexical={
        "radial_velocity": ("radial velocity" in low or "radial-velocity" in low or re.search(r"\brv\b",low) is not None),
        "astrometry": "astrometr" in low,
        "orbit": any(x in low for x in ("orbit","kepler","eccentricity","inclination")),
        "ode": any(x in low for x in ("ordinary differential equation"," ode ","dynamical system","vector-field","vector field")),
        "time_series": any(x in low for x in ("time series","trajectory","time grid")),
    }
    if lexical["radial_velocity"] and lexical["astrometry"]:
        capability="JOINT_RV_ASTROMETRY_FIT"
    elif lexical["ode"]:
        capability="SYMBOLIC_ODE_DISCOVERY"
    else:
        capability="UNRESOLVED"

    return {
        "schema":SCHEMA,
        "status":"EXPLICIT_CONTRACT_EXTRACTED",
        "input_paths":inputs,
        "output_paths":outputs,
        "json_templates":json_templates,
        "text_blocks":text_blocks,
        "lexical_evidence":lexical,
        "capability_class":capability,
        "semantic_completeness_claim":False,
        "external_model_calls":0,
        "network_calls":0,
        "terminal_authority":False,
    }
