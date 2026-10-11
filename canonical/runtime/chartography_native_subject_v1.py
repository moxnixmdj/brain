from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image

from canonical.runtime.chartography_axis_calibration_v1 import infer_linear_axes
from canonical.runtime.chartography_fixed_x_boundary_v1 import solve_lowest_interior_boundary
from canonical.runtime.chartography_positioned_ocr_v1 import extract_words
from canonical.runtime.chartography_semantic_utils_v1 import format_requested_rounding, prompt_numbers
from canonical.runtime.chartography_series_intersection_v1 import solve as solve_series

SCHEMA="PROJECT_BRAIN_CHARTOGRAPHY_NATIVE_SUBJECT_V1"

class ChartographyNativeSubjectError(ValueError):
    pass

def solve(image_path:str|Path,prompt:str)->dict[str,Any]:
    low=" ".join(str(prompt).lower().split())
    observation=extract_words(image_path,psm=11,min_confidence=0)
    words=observation["words"]

    if "how long" in low:
        result=solve_series(image_path,prompt,words=words)
        answer=result["answer"]; raw=float(result["raw_value"])
        route="CALIBRATED_SERIES_INTERSECTION"
        evidence=result
    elif "at what temperature" in low and ("wt %" in low or "wt%" in low):
        image=Image.open(image_path)
        cal=infer_linear_axes(words,image_width=image.width,image_height=image.height)
        xvals=[row["value"] for row in cal["x"]["ticks"]]
        nums=prompt_numbers(prompt,exclude_formatting=True)
        candidates=[v for v in nums if min(xvals)<=v<=max(xvals)]
        if not candidates:
            raise ChartographyNativeSubjectError("FIXED_X_OPERAND_NOT_IDENTIFIED")
        xvalue=min(candidates,key=abs)
        evidence=solve_lowest_interior_boundary(image_path,xvalue,words=words)
        raw=float(evidence["boundary_value"])
        answer=format_requested_rounding(prompt,raw)
        route="LOWEST_INTERIOR_BOUNDARY_AT_FIXED_X"
    else:
        raise ChartographyNativeSubjectError("UNSUPPORTED_QUERY_CLASS")

    return {
        "schema":SCHEMA,
        "status":"PASS__BRAIN_NATIVE_SUPPORTED_SCOPE",
        "route":route,
        "answer":answer,
        "raw_value":raw,
        "ocr_modes":observation.get("psm_values",[observation.get("psm")]),
        "evidence":evidence,
        "model_dependency_count":0,
        "external_model_runtime_dependency_count":0,
        "donor_runtime_dependency_count":0,
        "producer_cognition":"BRAIN_OWNED_NATIVE_MECHANISM",
        "terminal_authority":False,
    }
