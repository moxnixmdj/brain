"""Why the significance gate had to change -- measured, not asserted.

The claim is easy to make and worth nothing until it is checked: a
fixed-horizon test, inspected repeatedly, does not hold the error rate it
promises. This module checks it, so the number is a measurement on this
machine rather than a quotation.

It runs three experiments over many simulated campaigns in which nothing
has really improved, and in which the result is inspected after every
single observation -- which is what this system actually does, since every
run, every commit and every new environment is another look.

    1. paired two-sigma, peeked continuously
    2. Gaussian-mixture e-process with the variance estimated from past
       observations -- the obvious fix, and the one that fails
    3. the betting e-process shipped in credit_gates_v1

The second is the instructive one. It is not wrong by accident. It is
valid on worlds exactly as noisy as the one its prior assumes, and it
degrades to 25% and then 59% false positives as the world gets noisier --
because the guarantee lives in a variance it has to guess. A gate that is
only valid on the planet it was tuned on is training data wearing the
vocabulary of a guarantee.

Run it directly to reproduce the table.
"""
from __future__ import annotations

import math
import random

SCHEMA = "PROJECT_BRAIN_ANYTIME_VALIDITY_V1"

ALPHA = 0.05
_LAMBDAS = (-1.9, -1.4, -1.0, -0.6, -0.3, 0.3, 0.6, 1.0, 1.4, 1.9)


def paired_two_sigma(diffs: list[float]) -> bool:
    """The fixed-horizon gate, answered right now, as often as you like."""
    n = len(diffs)
    if n == 0:
        return False
    mean = sum(diffs) / n
    if n == 1:
        return mean > 0                      # the old N_ONE rule: one flip wins
    var = sum((d - mean) ** 2 for d in diffs) / (n - 1)
    stderr = math.sqrt(var / n)
    if stderr == 0.0:
        return mean > 0
    return (mean / stderr) > 2.0


def gaussian_mixture(diffs: list[float], prior_var: float = 1.0,
                     floor_fraction: float = 0.25) -> float:
    """Mixture e-process with the variance guessed from the past.

    Kept here as the counter-example, not for use.
    """
    a = b = 0.0
    history: list[float] = []
    sup = 1.0
    for x in diffs:
        floor = floor_fraction * prior_var
        if len(history) < 2:
            var = max(prior_var, floor)
        else:
            mean = sum(history) / len(history)
            var = max(sum((h - mean) ** 2 for h in history) / (len(history) - 1), floor)
        a += x / var
        b += 1.0 / var
        history.append(x)
        wealth = (1.0 + b) ** -0.5 * math.exp(a * a / (2.0 * (1.0 + b)))
        if wealth > sup:
            sup = wealth
    return sup


def betting(diffs: list[float], bound: float = 1.0) -> float:
    """The shipped gate. No variance, no scale assumption, no guessing."""
    scale = float(bound) if bound and bound > 0 else 1.0
    wealth = [1.0] * len(_LAMBDAS)
    sup = 1.0
    for d in diffs:
        clipped = max(-scale, min(scale, float(d)))
        y = (clipped + scale) / (2.0 * scale)
        for j, lam in enumerate(_LAMBDAS):
            wealth[j] *= (1.0 + lam * (y - 0.5))
        value = sum(wealth) / len(wealth)
        if value > sup:
            sup = value
    return sup


def campaign(gate, true_sd: float, effect: float, max_n: int,
             rng: random.Random) -> bool:
    """One simulated programme of work, inspected after every observation."""
    diffs: list[float] = []
    for _ in range(max_n):
        diffs.append(rng.gauss(effect, true_sd))
        value = gate(diffs)
        if value is True or value >= (1.0 / ALPHA):
            if sum(diffs) / len(diffs) > 0:
                return True
    return False


def false_positive_rate(gate, true_sd: float, trials: int = 2000,
                        max_n: int = 50, seed: int = 7) -> float:
    rng = random.Random(seed)
    hits = sum(campaign(gate, true_sd, 0.0, max_n, rng) for _ in range(trials))
    return hits / trials


def detection_rate(gate, true_sd: float, effect: float, trials: int = 2000,
                   max_n: int = 50, seed: int = 7) -> float:
    rng = random.Random(seed)
    hits = sum(campaign(gate, true_sd, effect, max_n, rng) for _ in range(trials))
    return hits / trials


def main() -> int:
    trials = 2000
    print("%s\n" % SCHEMA)
    print("FALSE POSITIVES with no real improvement, peeking after every"
          " observation. Promised: <= %.0f%%\n" % (ALPHA * 100))

    paired = false_positive_rate(lambda d: paired_two_sigma(d), 1.0, trials)
    print("  paired two-sigma, peeked        %6.1f%%   <-- the old gate"
          % (paired * 100))
    print()
    print("  true noise   gaussian-mixture   betting (shipped)")
    worst_mixture = 0.0
    worst_betting = 0.0
    for sd in (0.25, 0.5, 1.0, 2.0, 4.0, 10.0):
        m = false_positive_rate(lambda d: gaussian_mixture(d), sd, trials)
        b = false_positive_rate(lambda d: betting(d), sd, trials)
        worst_mixture = max(worst_mixture, m)
        worst_betting = max(worst_betting, b)
        print("    %5.2fx        %6.1f%%          %6.1f%%"
              % (sd, m * 100, b * 100))
    print()
    print("  worst case over all noise levels: mixture %.1f%%, betting %.1f%%"
          % (worst_mixture * 100, worst_betting * 100))

    print("\nDETECTION of a real improvement of half a standard deviation\n")
    print("  true noise   betting (shipped)")
    for sd in (0.5, 1.0, 2.0):
        print("    %5.2fx           %6.1f%%" % (sd, detection_rate(
            lambda d: betting(d), sd, 0.5, trials) * 100))

    ok = worst_betting <= ALPHA
    print("\n%s: betting e-process %s its promise at every noise level"
          % ("PASS" if ok else "FAIL",
             "holds" if ok else "BREAKS"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
