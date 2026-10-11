from __future__ import annotations

import math
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_AA_BRIEFCASE_DISPLAY_THRESHOLD_V1"
DISPLAY_THRESHOLD = 1822


class ThresholdError(ValueError):
    pass


def published_display_elo(raw_elo: float) -> int:
    if isinstance(raw_elo, bool) or not isinstance(raw_elo, (int, float)):
        raise ThresholdError("RAW_ELO_INVALID")
    x=float(raw_elo)
    if not math.isfinite(x):
        raise ThresholdError("RAW_ELO_INVALID")
    x=max(0.0,x)
    return int(math.floor(x+0.5))


def evaluate_score(score: float, representation: str) -> dict[str, Any]:
    if representation == "OWNER_DISPLAY_INTEGER":
        if isinstance(score,bool) or not isinstance(score,(int,float)):
            raise ThresholdError("DISPLAY_SCORE_INVALID")
        x=float(score)
        if not math.isfinite(x) or x != math.floor(x) or x < 0:
            raise ThresholdError("DISPLAY_SCORE_INVALID")
        display=int(x)
        raw=None
    elif representation == "RAW_FITTED_ELO":
        raw=float(score)
        display=published_display_elo(raw)
    else:
        raise ThresholdError("SCORE_REPRESENTATION_INVALID")

    return {
        "schema": SCHEMA,
        "status": "PASS_DISPLAY_THRESHOLD" if display >= DISPLAY_THRESHOLD else "FAIL_DISPLAY_THRESHOLD",
        "target_display_elo": DISPLAY_THRESHOLD,
        "score_representation": representation,
        "raw_fitted_elo": raw,
        "published_display_elo": display,
        "pass": display >= DISPLAY_THRESHOLD,
        "acceptance_credit_delta": 0,
        "terminal_authority": False,
    }


def verify_frozen_examples(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise ThresholdError("PAYLOAD_INVALID")
    examples=payload.get("examples")
    if not isinstance(examples,list) or not examples:
        raise ThresholdError("EXAMPLES_INVALID")
    bad=[]
    for row in examples:
        if not isinstance(row,Mapping):
            raise ThresholdError("EXAMPLE_INVALID")
        raw=row.get("raw")
        published=row.get("published")
        if isinstance(published,bool) or not isinstance(published,int):
            raise ThresholdError("PUBLISHED_INVALID")
        got=published_display_elo(raw)
        if got != published:
            bad.append({"raw":raw,"expected":published,"got":got})
    return {
        "schema": SCHEMA,
        "status":"PASS_FROZEN_DISPLAY_RULE" if not bad else "FAIL_FROZEN_DISPLAY_RULE",
        "verified":not bad,
        "example_count":len(examples),
        "mismatches":bad,
        "acceptance_credit_delta":0,
        "terminal_authority":False,
    }
