"""Formula-aware successor app policy overlay V5.

Adds only formula requests whose mapping to a spreadsheet formula is explicit or
mechanically determined from a supported aggregate + range. Execution is delegated
to the fixed set-and-read-back operation.
"""
from __future__ import annotations

import re
from typing import Any, Mapping

from canonical.runtime.osworld_v21_app_policy_overlay_v4 import (
    decide as base_decide,
)
from canonical.runtime.osworld_v21_app_policy_overlay_v3 import (
    _finish_or_candidate,
)
from canonical.runtime.osworld_v21_app_policy_overlay_v2 import (
    _active_app_name,
    _app,
    _app_op,
)

_AGG={"sum":"SUM","average":"AVERAGE","mean":"AVERAGE","min":"MIN","minimum":"MIN","max":"MAX","maximum":"MAX","count":"COUNT"}

def _formula(instruction:str):
    # Explicit formula syntax. Stop only at a sentence boundary after the formula.
    patterns=(
        r"\bset\s+(?:the\s+)?formula\s+(?:in|for)\s+([A-Z]{1,3}\d+)\s+(?:to|as)\s+(=[^\n;]+?)(?:\s*[.;]\s*$|$)",
        r"\bset\s+([A-Z]{1,3}\d+)\s+formula\s+(?:to|as)\s+(=[^\n;]+?)(?:\s*[.;]\s*$|$)",
    )
    for p in patterns:
        m=re.search(p,instruction,re.I)
        if m:
            formula=m.group(2).strip().rstrip(".")
            if formula.startswith("=") and len(formula)<=2000:
                return _app_op("libreoffice_calc","set_cell_formula_verified",{
                    "cell":m.group(1).upper(),"formula":formula
                })

    m=re.search(
        r"\bset\s+([A-Z]{1,3}\d+)\s+(?:to|as)\s+"
        r"(sum|average|mean|min|minimum|max|maximum|count)\s+"
        r"(?:of\s+)?([A-Z]{1,3}\d+:[A-Z]{1,3}\d+)\b",
        instruction,re.I,
    )
    if m:
        fn=_AGG[m.group(2).casefold()]
        formula=f"={fn}({m.group(3).upper()})"
        return _app_op("libreoffice_calc","set_cell_formula_verified",{
            "cell":m.group(1).upper(),"formula":formula
        })
    return None

def decide(state:Mapping[str,Any])->Mapping[str,Any]:
    instruction=state.get("instruction")
    if not isinstance(instruction,str) or not instruction.strip():
        return base_decide(state)
    active=_app(_active_app_name(state.get("a11y_tree")))
    if active=="libreoffice_calc":
        candidate=_formula(instruction)
        if candidate is not None:
            return _finish_or_candidate(state,candidate)
        if re.search(r"\bformula\b", instruction, re.I):
            return {
                "response":"formula request is not mechanically identified",
                "actions":[{"type":"WAIT"}],
                "_policy_receipt":{
                    "route":"FORMULA_REQUEST_FAIL_CLOSED",
                    "task_specific_policy_data":False,
                    "external_model_dependency":False,
                },
            }
    return base_decide(state)
