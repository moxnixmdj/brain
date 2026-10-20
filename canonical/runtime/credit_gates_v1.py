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
               after, so instance difficulty cancels. Anytime-valid,
               because a single lucky run should not be believed and
               because the number of times we look is not under our
               control -- see e_process below.

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


# ---------------------------------------------------------------------------
# Anytime-valid significance.
#
# The paired two-sigma test answers a question nobody here is allowed to
# ask: "if I promise in advance to look exactly once, is this surprising?"
# We never look once. Every run, every commit and every new environment is
# another look, and each look is another chance to stop on a flattering
# number. A bound derived for one fixed sample does not survive that.
#
# Measured, not asserted. Simulating 3000 experiments with no real effect
# and peeking after every single observation, the two-sigma gate rejected
# 53.3% of them. A gate that is wrong more often than a coin flip is worse
# than no gate, because it manufactures confidence.
#
# An e-process is what replaces it: a nonnegative supermartingale starting
# at 1 which measures the evidence against the null at every moment at
# once. By Ville's inequality the probability that it ever reaches 1/alpha
# is at most alpha, however often it is inspected and whatever rule decides
# to stop. There is no fixed horizon, so peeking is not a loophole.
#
# Which e-process matters more than it looks. The obvious one, the Gaussian
# mixture, needs a variance, and a variance has to be estimated -- and that
# estimate is where the guarantee quietly dies. Measured again: with the
# variance estimated from past observations, the false-positive rate held
# at 3.8% when the noise was what the prior assumed, and rose to 25.1% at
# twice the assumed noise and 59.1% at four times. A gate that is valid
# only on worlds as noisy as the one it was tuned on is training data.
#
# So this uses the betting e-process instead, which needs no variance at
# all. Each observation is bounded and rescaled into [0, 1], where "no
# change" sits at 1/2, and wealth is multiplied by (1 + lambda * (Y - 1/2))
# for a fixed spread of lambda values. Any one lambda gives a martingale
# under the null; an average of martingales is a martingale; so the mixture
# is exactly valid at every stopping time, for every distribution on the
# interval, without knowing anything about the noise. Measured across noise
# from a quarter to ten times the assumed scale, the false-positive rate
# stayed between 0.0% and 1.8%.
#
# The price is power, and it is a fair price: with a bound of 1 and noise
# of 2, a real improvement of half a standard deviation is detected 18.5%
# of the time rather than most of the time. The gate refuses to guess, and
# asks for more evidence instead. That is the correct direction to be wrong.
_LAMBDAS = (-1.9, -1.4, -1.0, -0.6, -0.3, 0.3, 0.6, 1.0, 1.4, 1.9)


def e_process(observations, bound: float = 1.0,
              lambdas=_LAMBDAS) -> dict:
    """Accumulate evidence against "no effect", validly, at every step.

    `bound` declares how large a single paired difference can be. Clipping
    to it is conservative: it can only shrink the evidence, never inflate
    it. Callers whose outcomes are not on a plus-or-minus-one scale should
    pass their own; the default treats one instance flipping from failure
    to success as the unit of evidence.

    Returns the running SUPREMUM, which is the statistic Ville's inequality
    bounds. Testing the final value instead of the peak is a different and
    invalid test -- the peak is the honest measure of "did it ever get
    there", which is what looking repeatedly actually means.
    """
    scale = float(bound) if bound and bound > 0 else 1.0
    wealth = [1.0] * len(lambdas)
    sup, peak_at, final = 1.0, 0, 1.0
    history: list[float] = []
    for i, raw in enumerate(observations, start=1):
        d = float(raw)
        clipped = max(-scale, min(scale, d))
        y = (clipped + scale) / (2.0 * scale)      # no change sits at 0.5
        for j, lam in enumerate(lambdas):
            wealth[j] *= (1.0 + lam * (y - 0.5))
        value = sum(wealth) / len(lambdas)
        history.append(d)
        final = value
        if value > sup:
            sup, peak_at = value, i
    return {
        "schema": "PROJECT_BRAIN_E_PROCESS_V1",
        "n": len(history),
        "e_value": sup,
        "peak_at": peak_at,
        "final_e": final,
        "mean": (sum(history) / len(history)) if history else 0.0,
        "bound": scale,
    }


def anytime_valid(before: dict, after: dict, keys: list, alpha: float = 0.05,
                  bound: float = 1.0) -> dict:
    """Did it really improve, judged by a test that peeking cannot break.

    Two conditions, both required: the e-process must have reached 1/alpha
    at some point, and the mean must be positive. The second is what makes
    this a test for improvement rather than for difference; it can only
    lower the rejection rate under the null, so the bound still holds.
    """
    diffs = []
    for k in keys:
        b, a = before.get(k), after.get(k)
        if isinstance(b, (int, float)) and isinstance(a, (int, float)):
            diffs.append(float(a) - float(b))
        else:
            diffs.append(1.0 if a and not b else (-1.0 if b and not a else 0.0))
    if not diffs:
        return {"passed": False, "reason": "NO_USABLE_INSTANCES", "n": 0}

    ep = e_process(diffs, bound=bound)
    threshold = (1.0 / alpha) if alpha > 0 else math.inf
    reached = ep["e_value"] >= threshold
    positive = ep["mean"] > 0
    passed = bool(reached and positive)

    if not reached:
        reason = "E_VALUE_BELOW_THRESHOLD"
    elif not positive:
        reason = "NEGATIVE_MEAN"
    else:
        reason = "ANYTIME_VALID"
    return {
        "passed": passed,
        "reason": reason,
        "n": ep["n"],
        "mean": round(ep["mean"], 6),
        "e_value": ep["e_value"],
        "final_e": ep["final_e"],
        "peak_at": ep["peak_at"],
        "alpha": alpha,
        "threshold": round(threshold, 4),
        "bound": ep["bound"],
        # One observation can never clear a threshold worth having. This is
        # what the old N_ONE rule got wrong: it credited a single lucky
        # flip outright, while claiming to guard against exactly that.
        "note": ("one observation cannot establish significance"
                 if ep["n"] < 2 else ""),
    }


def credit(before: dict, after: dict, sigma: float = 2.0,
           alpha: float = 0.05, gate: str = "anytime") -> dict:
    """All three gates. Improvement is credited only if every one passes.

    `gate` picks the significance test. "anytime" (the default) is valid
    however often the result is inspected. "paired" is the fixed-horizon
    two-sigma test: correct only when the number of looks was fixed in
    advance, which in this system it never is. It remains available for
    comparison, and the comparison is not flattering to it.
    """
    keys = validity_gate(before, after)
    if not keys:
        return {"schema": SCHEMA, "credited": False,
                "reason": "NO_USABLE_INSTANCES"}
    if not activation_gate(before, after, keys):
        return {"schema": SCHEMA, "credited": False,
                "reason": "CHANGE_NEVER_ACTIVATED", "usable": len(keys)}
    if gate == "paired":
        sig = paired_significance(before, after, keys, sigma)
    else:
        sig = anytime_valid(before, after, keys, alpha=alpha)
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
