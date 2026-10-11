from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image

from canonical.runtime.chartography_axis_calibration_v1 import infer_linear_axes
from canonical.runtime.chartography_fixed_x_boundary_v1 import solve_lowest_interior_boundary
from canonical.runtime.chartography_positioned_ocr_v1 import extract_words
from canonical.runtime.chartography_semantic_utils_v1 import (
    format_requested_rounding,
    prompt_numbers,
)
from canonical.runtime.chartography_series_intersection_v1 import solve as solve_series_intersection

SCHEMA = "PROJECT_BRAIN_CHARTOGRAPHY_PROFESSIONAL_SEMANTIC_ROUTER_V1"


class ProfessionalChartSemanticError(ValueError):
    pass


def solve(image_path: str | Path, prompt: str) -> dict[str, Any]:
    low = " ".join(str(prompt).lower().split())
    observation = extract_words(image_path, psm=11, min_confidence=0)
    words = observation["words"]

    if "precipitat" in low:
        image = Image.open(image_path)
        calibration = infer_linear_axes(words, image_width=image.width, image_height=image.height)
        x_ticks = [row["value"] for row in calibration["x"]["ticks"]]
        values = prompt_numbers(prompt, exclude_formatting=True)
        in_range = [value for value in values if min(x_ticks) <= value <= max(x_ticks)]
        if not in_range:
            raise ProfessionalChartSemanticError("COMPOSITION_OPERAND_NOT_IDENTIFIED")
        composition = min(in_range, key=abs)
        boundary = solve_lowest_interior_boundary(image_path, composition, words=words)
        value = float(boundary["boundary_value"])
        return {
            "schema": SCHEMA,
            "status": "PASS__SUPPORTED_PROFESSIONAL_CHART_SEMANTICS",
            "route": "PRECIPITATION_ON_COOLING_TO_LOWEST_INTERIOR_PHASE_BOUNDARY",
            "answer": format_requested_rounding(prompt, value),
            "raw_value": value,
            "observation": {
                "psm": observation["psm"],
                "word_count": observation["word_count"],
                "producer_cognition": False,
            },
            "evidence": boundary,
            "model_dependency_count": 0,
            "external_model_runtime_dependency_count": 0,
            "donor_runtime_dependency_count": 0,
            "producer_cognition": "BRAIN_OWNED_DETERMINISTIC_MECHANISM",
            "terminal_authority": False,
        }

    if "how long" in low or "what time" in low or "at what time" in low:
        result = solve_series_intersection(image_path, prompt, words=words)
        return {
            "schema": SCHEMA,
            "status": "PASS__SUPPORTED_PROFESSIONAL_CHART_SEMANTICS",
            "route": result["status"],
            "answer": result["answer"],
            "raw_value": result["raw_value"],
            "observation": {
                "psm": observation["psm"],
                "word_count": observation["word_count"],
                "producer_cognition": False,
            },
            "evidence": result,
            "model_dependency_count": 0,
            "external_model_runtime_dependency_count": 0,
            "donor_runtime_dependency_count": 0,
            "producer_cognition": "BRAIN_OWNED_DETERMINISTIC_MECHANISM",
            "terminal_authority": False,
        }

    raise ProfessionalChartSemanticError("UNSUPPORTED_PROFESSIONAL_CHART_SEMANTICS")
