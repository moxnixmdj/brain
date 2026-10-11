from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from canonical.runtime.chartography_deterministic_geometry_v1 import (
    bar_height_ratio,
    count_components_left_of_x,
    grouped_bar_winner_group,
    line_left_to_right_trend,
    line_right_higher_color,
    read_bmp_rgb,
    tallest_bar_color,
    vertical_divider_x,
)

SCHEMA = "PROJECT_BRAIN_CHARTOGRAPHY_DETERMINISTIC_RELATION_ROUTER_V1"

COLORS: dict[str, tuple[int, int, int]] = {
    "RED": (255, 0, 0),
    "GREEN": (0, 180, 0),
    "BLUE": (0, 80, 255),
    "CYAN": (0, 190, 190),
    "YELLOW": (240, 190, 0),
    "PURPLE": (145, 70, 200),
    "ORANGE": (240, 120, 20),
}


class ChartographyRelationRouterError(ValueError):
    pass


def _mentioned_colors(prompt: str) -> list[str]:
    upper = prompt.upper()
    hits: list[tuple[int, str]] = []
    for name in COLORS:
        m = re.search(r"\b" + re.escape(name) + r"\b", upper)
        if m:
            hits.append((m.start(), name))
    return [name for _, name in sorted(hits)]


def _require_colors(colors: list[str], n: int, route: str) -> list[str]:
    if len(colors) != n:
        raise ChartographyRelationRouterError(
            f"{route}_REQUIRES_EXACTLY_{n}_MENTIONED_COLORS"
        )
    return colors


def _format_ratio(value: float) -> str:
    nearest = round(value)
    if abs(value - nearest) < 1e-9:
        return str(int(nearest))
    return format(value, ".6g")


def solve_supported_relation(
    image_path: str | Path,
    prompt: str,
) -> dict[str, Any]:
    if not isinstance(prompt, str) or not prompt.strip():
        raise ChartographyRelationRouterError("PROMPT_REQUIRED")

    p = " ".join(prompt.lower().split())
    colors = _mentioned_colors(prompt)
    image = read_bmp_rgb(image_path)

    route: str
    answer: str

    if (
        "how many" in p
        and ("data point" in p or "points" in p)
        and ("left of" in p or "to the left of" in p)
        and "divider" in p
    ):
        color = _require_colors(colors, 1, "SCATTER_COUNT")[0]
        answer = str(
            count_components_left_of_x(
                image,
                COLORS[color],
                vertical_divider_x(image),
            )
        )
        route = "SCATTER_COUNT"

    elif (
        "how many times" in p
        and ("tall" in p or "height" in p)
        and ("bar" in p or "bars" in p)
    ):
        first, second = _require_colors(colors, 2, "BAR_RATIO")
        answer = _format_ratio(
            bar_height_ratio(image, COLORS[first], COLORS[second])
        )
        route = "BAR_RATIO"

    elif (
        ("left to right" in p or "from left to right" in p)
        and "line" in p
        and "increase" in p
        and "decrease" in p
    ):
        color = _require_colors(colors, 1, "LINE_TREND")[0]
        answer = line_left_to_right_trend(image, COLORS[color])
        route = "LINE_TREND"

    elif (
        "line" in p
        and ("right side" in p or "right-hand side" in p or "far right" in p)
        and ("higher" in p or "above" in p)
    ):
        c1, c2 = _require_colors(colors, 2, "LINE_RIGHT_ORDER")
        answer = line_right_higher_color(
            image,
            {c1: COLORS[c1], c2: COLORS[c2]},
        )
        route = "LINE_RIGHT_ORDER"

    elif (
        ("two groups" in p or "which group" in p)
        and ("bar" in p or "bars" in p)
        and ("taller than" in p or "higher than" in p)
        and "left" in p
        and "right" in p
    ):
        first, second = _require_colors(colors, 2, "GROUPED_BAR_COMPARISON")
        answer = grouped_bar_winner_group(
            image,
            COLORS[first],
            COLORS[second],
        )
        route = "GROUPED_BAR_COMPARISON"

    elif (
        ("bar" in p or "bars" in p)
        and ("tallest" in p or "highest" in p)
        and len(colors) >= 2
    ):
        answer = tallest_bar_color(
            image,
            {name: COLORS[name] for name in colors},
        )
        route = "BAR_ORDERING"

    else:
        raise ChartographyRelationRouterError(
            "UNSUPPORTED_OR_AMBIGUOUS_RELATION_PROMPT"
        )

    return {
        "schema": SCHEMA,
        "status": "PASS__SUPPORTED_DETERMINISTIC_RELATION",
        "route": route,
        "answer": answer,
        "mentioned_colors": colors,
        "scope": (
            "SIMPLE_EXACT_COLOR_CODED_BMP_CHART_RELATIONS_ONLY__"
            "FAIL_CLOSED_OUTSIDE_DECLARED_GRAMMAR"
        ),
        "model_interpretation_required": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "acceptance_credit_delta": 0,
        "terminal_credit_delta": 0,
    }
