#!/usr/bin/env python3
"""Fail-closed weighted bound reducer for the frozen Finance & Accounting Index.

This module never invents component evidence. It only combines externally verified,
comparable normalized component intervals under the published 30/30/20/10/5/5 weights.
Missing components remain [0, 100].
"""
from itertools import combinations

WEIGHTS = {
    "BUSINESS_KNOWLEDGE": 0.30,
    "AGENTIC_KNOWLEDGE_WORK": 0.30,
    "REASONING": 0.20,
    "AGENTIC_TOOL_USE": 0.10,
    "LONG_CONTEXT": 0.05,
    "NON_HALLUCINATION": 0.05,
}
TARGET = 61.0

def _interval(v):
    if isinstance(v, (int, float)):
        lo = hi = float(v)
    else:
        if not isinstance(v, (list, tuple)) or len(v) != 2:
            raise ValueError("component bound must be scalar or [lower, upper]")
        lo, hi = map(float, v)
    if not (0.0 <= lo <= hi <= 100.0):
        raise ValueError("component bounds must satisfy 0 <= lower <= upper <= 100")
    return lo, hi

def aggregate_interval(component_bounds):
    unknown = set(component_bounds) - set(WEIGHTS)
    if unknown:
        raise ValueError(f"unknown components: {sorted(unknown)}")
    lower = 0.0
    upper = 0.0
    for k, w in WEIGHTS.items():
        lo, hi = _interval(component_bounds[k]) if k in component_bounds else (0.0, 100.0)
        lower += w * lo
        upper += w * hi
    return lower, upper

def classify(component_bounds, target=TARGET):
    lower, upper = aggregate_interval(component_bounds)
    if lower >= target:
        return {"state": "PROVED", "lower": lower, "upper": upper, "target": target}
    if upper < target:
        return {"state": "IMPOSSIBLE_ON_BOUND_INPUTS", "lower": lower, "upper": upper, "target": target}
    return {"state": "OPEN", "lower": lower, "upper": upper, "target": target, "residual": target-lower}

def minimum_additional_component_sets(component_bounds, target=TARGET):
    """Scheduling only: smallest missing-component sets whose ceiling could close target."""
    state = classify(component_bounds, target)
    if state["state"] != "OPEN":
        return []
    missing = [k for k in WEIGHTS if k not in component_bounds]
    base_lower = aggregate_interval(component_bounds)[0]
    for n in range(1, len(missing)+1):
        out = []
        for subset in combinations(missing, n):
            possible = base_lower + sum(WEIGHTS[k]*100.0 for k in subset)
            if possible >= target:
                out.append({"components": list(subset), "ceiling_with_base_lower": possible})
        if out:
            return out
    return []
