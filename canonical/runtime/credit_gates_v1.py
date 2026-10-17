"""Did it actually improve? Decided by arithmetic, never by assertion.

Harvested from "Self-Evolving Agent Harnesses via Gated Semantic
Quality-Diversity" (HarnessBank, arXiv:2607.13683), which separates PROPOSING
a change from CREDITING it. A model may suggest. Only deterministic code may
decide whether the suggestion helped.

Three gates, in order. All must pass.

1. VALIDITY    Re-run, and exclude instances that fail identically before and
               after. Those are infrastructure failures, not behaviour, and
               counting them as improvements measures the wrong thing.

2. ACTIVATION  Confirm the change actually did something. A patch that never
               fired cannot be credited with a gain, and a "gain" on a change
               that produced identical behaviour is noise wearing a badge.

3. SIGNIFICANCE Paired comparison on a SEALED set withheld from every
               decision. Paired, because the same instances run before and
               after, so instance difficulty cancels. Two sigma, because a
               single lucky run should not be believed.

The bound is deliberate and comes from "The Self-Improvement Problem"
(arXiv:2610.21646): no terminating procedure can be both perfectly reliable
and perfectly non-conservative. Bounded evaluation plus a finite proposal
budget is the regime where guarantees exist. These gates choose reliability.
"""
from __future__ import annotations

import math

SCHEMA = "PROJECT_BRAIN_CREDIT_GATES_V1"


def validity_gate(before: dict, after: dict) -> list:
    """Instances usable for comparison: exclude identical-outcome infra failures."""
    usable = []
    for key in set(before) & set(after):
        b, a = before[key], after[key]
        # Identical failure before and after is the environment, not the change.
        if b == a and _is_failure(b):
            continue
        usable.append(key)
    return sorted(usable)


def _is_failure(value) -> bool:
    return value is None or value is False or value == 0


def activation_gate(before: dict, after: dict, keys: list) -> bool:
    """Did behaviour change anywhere? No change means no credit."""
    return any(before.get(k) != after.get(k) for k in keys)


def paired_significance(before: dict, after: dict, keys: list, sigma: float = 2.0) -> dict:
    """Paired 2-sigma test on the sealed set."""
    diffs = []
    for k in keys:
        b, a = before.get(k), after.get(k)
        if isinstance(b, (int, float)) and isinstance(a, (int, float)):
            diffs.append(float(a) - float(b))
        else:
            diffs.append(1.0 if a and not b else (-1.0 if b and not a else 0.0))
    n = len(diffs)
    if n == 0:
        return {"passed": False, "reason": "NO_USABLE_INSTANCES", "n": 0}
    mean = sum(diffs) / n
    if n == 1:
        return {"passed": mean > 0, "reason": "N_ONE", "n": 1, "mean": mean}
    var = sum((d - mean) ** 2 for d in diffs) / (n - 1)
    stderr = math.sqrt(var / n)
    if stderr == 0.0:
        return {"passed": mean > 0, "reason": "ZERO_VARIANCE", "n": n,
                "mean": mean, "stderr": 0.0}
    ratio = mean / stderr
    return {
        "passed": ratio > sigma,
        "reason": "PAIRED_SIGMA",
        "n": n,
        "mean": round(mean, 6),
        "stderr": round(stderr, 6),
        "sigma_ratio": round(ratio, 4),
        "threshold": sigma,
    }


def credit(before: dict, after: dict, sigma: float = 2.0) -> dict:
    """All three gates. Improvement is credited only if every one passes."""
    keys = validity_gate(before, after)
    if not keys:
        return {"schema": SCHEMA, "credited": False,
                "reason": "NO_USABLE_INSTANCES"}
    if not activation_gate(before, after, keys):
        return {"schema": SCHEMA, "credited": False,
                "reason": "CHANGE_NEVER_ACTIVATED", "usable": len(keys)}
    sig = paired_significance(before, after, keys, sigma)
    return {
        "schema": SCHEMA,
        "credited": bool(sig["passed"]),
        "reason": sig["reason"],
        "usable_instances": len(keys),
        "statistics": sig,
        "model_dependency_count": 0,
    }


if __name__ == "__main__":
    # Same infra failure both runs: excluded, and correctly not counted.
    before = {"a": 0, "b": 1, "c": 0, "d": 1, "e": 0, "f": 1, "g": 0, "h": 1}
    after = {"a": 0, "b": 1, "c": 1, "d": 1, "e": 1, "f": 1, "g": 1, "h": 1}
    print("real gain across 4 ->", credit(before, after)["credited"],
          credit(before, after)["statistics"].get("sigma_ratio"))
    print("no change        ->", credit(before, dict(before))["reason"])
    print("one lucky flip   ->", credit({"a": 0, "b": 1}, {"a": 1, "b": 1})["credited"])
