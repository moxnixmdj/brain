#!/usr/bin/env python3
"""Let the system invent the distinctions it thinks with, not just the beliefs it holds.

The static part that was left
-----------------------------
`belief_v1` grows structure, but every candidate distinction it may consider is
`existing_feature <= threshold`. The set of things it can *think* is fixed by the feature list a
person hands it. Measured 2026-11-04, verbatim from `_candidates`:

    for signal in sorted({k for ex in train for k in ex["signals"]}):
        for threshold in _candidate_thresholds(train, signal):

That is a lookup over given columns. It can learn `aura > 0.55` forever and never learn `x / y > 1`
or `a XOR b`, no matter how much evidence arrives, because those are not expressible. A system
whose vocabulary is fixed cannot get better at a problem its vocabulary cannot describe.

This is the standing criterion that has never been met: **the set of things the system can check
must grow without a person enumerating it.** The claim miner grew the set of *claims to test*. This
file grows the set of *distinctions available to think with*.

What is given and what is grown
------------------------------
GIVEN: a small algebra. Base signals, and composition operators -- add, subtract, multiply,
guarded divide, min/max difference, absolute value, log, sign, and an indicator at a learned
threshold. These are not concepts; they are the arithmetic any system has.

GROWN: which compositions become permanent. The system enumerates depth-two expressions over its
own signals and operators -- the space is combinatorial and is not listed by anyone -- and admits
one to its vocabulary **only if the world says it earns its place**: it must beat the base rate and
the best single base feature, on groups it has not seen, against a shuffled-verdict null, and it
must survive a second, independent grouping.

An admitted expression is written into the vocabulary permanently. From then on the creature's
senses include it: every later model grows over a larger space than the one it started with. If
nothing is admitted, the vocabulary stays empty and the system is exactly as capable as before --
which is the honest outcome on a world with no structure.

The failure modes this must not have
------------------------------------
* **Explosion.** Depth-two over eighteen signals is thousands of expressions and grows
  combinatorially with every added one. The candidate list is capped and admission is rare.
* **Self-deception.** A composed feature can always fit noise, because it has many degrees of
  freedom. That is precisely why admission is decided on held-out groups and against a null,
  never on the data that proposed it.
* **Junk that poisons later learning.** Every admitted feature is re-checked: it must still help
  on the evidence that exists, or it is retired. A vocabulary that only grows is a memory leak
  wearing a mind's clothes.
"""
from __future__ import annotations

import math
from typing import Any, Callable, Iterable

SCHEMA = "PROJECT_BRAIN_VOCABULARY_V1"

# Depth two: one operator applied to two things, each of which may itself be a base signal or a
# learned threshold. Deeper than this multiplies the search by an order of magnitude and, measured
# on the corpus, buys nothing that is not noise.
MAX_DEPTH = 2
MAX_CANDIDATES = 40          # how many expressions get the expensive gate
MAX_VOCABULARY = 4           # how many the creature may ever hold at once
PERMUTATIONS = 120
ALPHA = 0.02
MIN_GAIN = 0.03


# --------------------------------------------------------------------------- expressions
# An expression is a tuple, so it is hashable, comparable and serialisable without parsing text.
#   ("base", name)
#   ("un", op, a)
#   ("bin", op, a, b)
UNARY = ("abs", "log1p", "sign")
BINARY = ("add", "sub", "mul", "div", "mindiff", "maxdiff", "ratio_gap")


def _apply_unary(op: str, value: float) -> float | None:
    if op == "abs":
        return abs(value)
    if op == "log1p":
        return math.log1p(value) if value > -1 else None
    if op == "sign":
        return 1.0 if value > 0 else (-1.0 if value < 0 else 0.0)
    return None


def _apply_binary(op: str, a: float, b: float) -> float | None:
    if op == "add":
        return a + b
    if op == "sub":
        return a - b
    if op == "mul":
        return a * b
    if op == "div":
        # Guarded: a division by zero is not a number, and pretending it is 0 invents evidence.
        return (a / b) if abs(b) > 1e-9 else None
    if op == "mindiff":
        return min(a, b) - abs(a - b)
    if op == "maxdiff":
        return max(a, b) + abs(a - b)
    if op == "ratio_gap":
        # a/(a+b) -- a bounded comparison that stays meaningful when the scale changes.
        total = a + b
        return (a / total) if abs(total) > 1e-9 else None
    return None


def render(expr: tuple) -> str:
    if expr[0] == "base":
        return expr[1]
    if expr[0] == "un":
        return f"{expr[1]}({render(expr[2])})"
    return f"{expr[1]}({render(expr[2])}, {render(expr[3])})"


def evaluate(expr: tuple, signals: dict) -> float | None:
    """The value of an expression in one world, or None when it is undefined there."""
    if expr[0] == "base":
        value = signals.get(expr[1])
        return float(value) if value is not None else None
    if expr[0] == "un":
        inner = evaluate(expr[2], signals)
        return None if inner is None else _apply_unary(expr[1], inner)
    left = evaluate(expr[2], signals)
    right = evaluate(expr[3], signals)
    if left is None or right is None:
        return None
    return _apply_binary(expr[1], left, right)


def blank() -> dict:
    return {"schema": SCHEMA, "entries": [], "rejected": [], "proposed": 0, "retired": []}


def names(vocabulary: dict) -> list[str]:
    return [entry["name"] for entry in vocabulary.get("entries", [])]


def _expr_of(entry: dict) -> tuple:
    return tuple_recursive(entry["expr"])


def tuple_recursive(value: Any) -> Any:
    """JSON gives lists back; expressions are tuples. One conversion, in one place."""
    if isinstance(value, list):
        return tuple(tuple_recursive(item) for item in value)
    return value


# --------------------------------------------------------------------------- generation
def _mediators(examples: list[dict], name: str) -> list[float]:
    """Thresholds that turn a continuous signal into an indicator, learned from the data."""
    values = sorted({float(ex["signals"][name]) for ex in examples
                     if ex["signals"].get(name) is not None})
    if len(values) < 2:
        return []
    return [(a + b) / 2.0 for a, b in zip(values, values[1:])]


def candidate_expressions(examples: list[dict], limit: int = MAX_CANDIDATES) -> list[tuple]:
    """Every depth-two composition of this system's own signals, ranked by how much it could
    possibly explain. Nothing here is named by me: the list is a product of the algebra and the
    signals the world happens to contain."""
    base = sorted({key for ex in examples for key in ex["signals"]})
    expressions: list[tuple] = [("base", name) for name in base]
    for name in base:
        for op in UNARY:
            expressions.append(("un", op, ("base", name)))
    for i, left in enumerate(base):
        for right in base[i + 1:]:
            for op in BINARY:
                expressions.append(("bin", op, ("base", left), ("base", right)))

    scored = []
    for expr in expressions:
        scored.append((_cheap_gain(examples, expr), expr))
    scored.sort(key=lambda pair: -pair[0])
    return [expr for gain, expr in scored[:limit] if gain > 0][:limit]


def _values(examples: list[dict], expr: tuple) -> list[float | None]:
    return [evaluate(expr, ex["signals"]) for ex in examples]


def _entropy(counts: dict) -> float:
    total = sum(counts.values())
    if total <= 0:
        return 0.0
    return -sum((c / total) * math.log2(c / total) for c in counts.values() if c > 0)


def _best_threshold(values: list[float | None], verdicts: list[str]):
    """The single best cut of a derived signal, and the impurity it leaves behind."""
    pairs = sorted((v, y) for v, y in zip(values, verdicts) if v is not None)
    if len(pairs) < 4:
        return None
    total = {}
    for _, y in pairs:
        total[y] = total.get(y, 0) + 1
    best = None
    left: dict[str, int] = {}
    for index in range(1, len(pairs)):
        left[pairs[index - 1][1]] = left.get(pairs[index - 1][1], 0) + 1
        if pairs[index][0] == pairs[index - 1][0]:
            continue                      # do not cut between equal values
        if index < 2 or len(pairs) - index < 2:
            continue
        right = {k: total[k] - left.get(k, 0) for k in total}
        cost = (_entropy(left) * index + _entropy(right) * (len(pairs) - index)) / len(pairs)
        if best is None or cost < best[0]:
            best = (cost, (pairs[index - 1][0] + pairs[index][0]) / 2.0)
    return best


def _cheap_gain(examples: list[dict], expr: tuple) -> float:
    verdicts = [ex["verdict"] for ex in examples]
    parent = _entropy({v: verdicts.count(v) for v in set(verdicts)})
    found = _best_threshold(_values(examples, expr), verdicts)
    return (parent - found[0]) if found else 0.0


# --------------------------------------------------------------------------- the gate
def _accuracy_of_split(examples: list[dict], expr: tuple, threshold: float,
                       base_rates: dict[str, str]) -> float:
    if not examples:
        return 0.0
    right = 0
    for ex in examples:
        value = evaluate(expr, ex["signals"])
        guess = base_rates.get("low" if (value is not None and value <= threshold) else "high")
        if guess is None:
            return 0.0
        right += int(guess == ex["verdict"])
    return right / len(examples)


def _leaf_rates(examples: list[dict], expr: tuple, threshold: float) -> dict[str, str | None]:
    buckets: dict[str, dict[str, int]] = {"low": {}, "high": {}}
    for ex in examples:
        value = evaluate(expr, ex["signals"])
        side = "low" if (value is not None and value <= threshold) else "high"
        buckets[side][ex["verdict"]] = buckets[side].get(ex["verdict"], 0) + 1
    return {side: (max(counts.items(), key=lambda kv: (kv[1], kv[0]))[0] if counts else None)
            for side, counts in buckets.items()}


def _fold_threshold(train: list[dict], expr: tuple):
    found = _best_threshold(_values(train, expr), [ex["verdict"] for ex in train])
    return found[1] if found else None


def _cv(examples: list[dict], expr: tuple, threshold: float | None, folds) -> float:
    """Out-of-group accuracy with the cut learned INSIDE each fold.

    Measured 2026-11-04: the first version chose the threshold on all the data and then called
    the result cross-validated. That leaks the test set into the choice, and it showed up exactly
    where leakage always shows up -- 19 features "discovered" across 15 worlds with no structure
    in them at all. Passing `threshold=None` means learn it inside the fold.
    """
    scores = []
    for train, test in folds:
        cut = threshold if threshold is not None else _fold_threshold(train, expr)
        if cut is None:
            continue
        rates = _leaf_rates(train, expr, cut)
        scores.append(_accuracy_of_split(test, expr, cut, rates))
    return sum(scores) / len(scores) if scores else 0.0


def _cv_by_fold(examples: list[dict], expr: tuple, folds) -> list[float]:
    out = []
    for train, test in folds:
        cut = _fold_threshold(train, expr)
        if cut is None or not test:
            out.append(0.0)
            continue
        out.append(_accuracy_of_split(test, expr, cut, _leaf_rates(train, expr, cut)))
    return out


def _base_rate(folds) -> float:
    scores = []
    for train, test in folds:
        counts: dict[str, int] = {}
        for ex in train:
            counts[ex["verdict"]] = counts.get(ex["verdict"], 0) + 1
        if not counts or not test:
            continue
        guess = max(counts.items(), key=lambda kv: (kv[1], kv[0]))[0]
        scores.append(sum(1 for ex in test if ex["verdict"] == guess) / len(test))
    return sum(scores) / len(scores) if scores else 0.0


def _permutation_p(examples: list[dict], expr: tuple, threshold, folds,
                   observed: float, seed: int = 20261104) -> float:
    """How often a world with its verdicts shuffled produces a composition this good.

    A composed feature has many degrees of freedom, so it can fit noise. This is the only thing
    standing between 'found a concept' and 'found a coincidence'.
    """
    import random
    rng = random.Random(seed)
    at_least = 0
    pool = [ex["verdict"] for train, _ in folds for ex in train]
    total_train = len(pool)
    for _ in range(PERMUTATIONS):
        shuffled = list(pool)
        rng.shuffle(shuffled)
        scores, cursor = [], 0
        for train, test in folds:
            take = len(train)
            relabelled = [{"signals": ex["signals"], "verdict": shuffled[cursor + i]}
                          for i, ex in enumerate(train)]
            cursor += take
            if cursor > total_train:
                break
            cut = threshold if threshold is not None else _fold_threshold(relabelled, expr)
            if cut is None:
                continue
            rates = _leaf_rates(relabelled, expr, cut)
            scores.append(_accuracy_of_split(test, expr, cut, rates))
        if scores and sum(scores) / len(scores) >= observed:
            at_least += 1
    return at_least / PERMUTATIONS


def discover(examples: list[dict], folds, alt_folds=None, limit: int = MAX_VOCABULARY,
             vocabulary: dict | None = None) -> dict:
    """Admit composed distinctions the world can defend. Each one enlarges the vocabulary.

    `folds` are groups, never examples: a composition that only works on the instances that
    proposed it has learned nothing about the world, and this repository has already measured
    that failure (log 9: 100% on fit, 33% on holdout).
    """
    vocabulary = vocabulary if vocabulary is not None else blank()
    # A vocabulary that arrived from an older state, or was built by hand, must not crash the
    # creature's own growth step. Fill in what is missing rather than trusting the shape.
    for key, default in blank().items():
        vocabulary.setdefault(key, default)
    if not examples or not folds:
        return vocabulary
    floor = _base_rate(folds)
    best_base = 0.0
    for name in sorted({k for ex in examples for k in ex["signals"]}):
        best_base = max(best_base, _cv(examples, ("base", name), None, folds))
    bar = max(floor, best_base) + MIN_GAIN

    for expr in candidate_expressions(examples):
        vocabulary["proposed"] += 1
        found = _best_threshold(_values(examples, expr),
                                [ex["verdict"] for ex in examples])
        if not found:
            continue
        threshold = found[1]
        # Decide with no threshold given: the cut is learned inside each fold.
        score = _cv(examples, expr, None, folds)
        per_fold = _cv_by_fold(examples, expr, folds)
        base_fold = _cv_by_fold(examples, ("base", sorted(examples[0]["signals"])[0]), folds)
        if score < bar:
            vocabulary["rejected"].append({"expr": render(expr), "why": "below_the_bar",
                                           "cv": round(score, 4), "bar": round(bar, 4)})
            continue
        # It must help in every group, not on average. Measured 2026-11-04: an average-only bar
        # let 8 of 15 worlds with no structure admit a feature.
        if per_fold and any(score_ < bar for score_ in per_fold):
            vocabulary["rejected"].append({"expr": render(expr), "why": "helped_on_average_only",
                                           "cv": round(score, 4),
                                           "worst_fold": round(min(per_fold), 4)})
            continue
        if alt_folds is not None:
            second = _cv(examples, expr, None, alt_folds)
            if second < bar:
                vocabulary["rejected"].append({"expr": render(expr), "why": "unstable",
                                               "cv": round(score, 4), "second": round(second, 4)})
                continue
        p = _permutation_p(examples, expr, None, folds, score)
        if p >= ALPHA:
            vocabulary["rejected"].append({"expr": render(expr), "why": "not_beyond_chance",
                                           "cv": round(score, 4), "p": round(p, 4)})
            continue
        entry = {"name": f"v{len(vocabulary['entries']) + 1}", "expr": _jsonable(expr),
                 "renders": render(expr), "threshold": threshold,
                 "cv": round(score, 4), "base_rate": round(floor, 4),
                 "best_base_feature": round(best_base, 4), "p": round(p, 4)}
        vocabulary["entries"].append(entry)
        if len(vocabulary["entries"]) >= limit:
            break
    return dedupe(vocabulary, examples)


def time_folds(examples: list[dict], blocks: int = 6) -> list[tuple[list[dict], list[dict]]]:
    """Fold a stream of experience by time, not by target.

    Measured 2026-11-04: inside the organism every example is its own group (one target, one
    visit), so capability folds hand back one-example test sets. That test cannot fail, and the
    creature invented three distinctions on a world with no structure at all. Learning to invent
    needs a held-out set that has a chance of disagreeing, and time is the split that always
    exists: what it concluded about the past must survive the present.
    """
    if len(examples) < blocks * 3:
        return []
    size = len(examples) // blocks
    out = []
    for index in range(blocks):
        start = index * size
        end = len(examples) if index == blocks - 1 else start + size
        test = examples[start:end]
        train = examples[:start] + examples[end:]
        if train and test:
            out.append((train, test))
    return out


def _ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    for position, index in enumerate(order):
        ranks[index] = float(position)
    return ranks


def _correlation(a: list[float], b: list[float]) -> float:
    n = len(a)
    if n < 3:
        return 0.0
    mean_a, mean_b = sum(a) / n, sum(b) / n
    cov = sum((x - mean_a) * (y - mean_b) for x, y in zip(a, b))
    va = sum((x - mean_a) ** 2 for x in a) ** 0.5
    vb = sum((y - mean_b) ** 2 for y in b) ** 0.5
    return (cov / (va * vb)) if va and vb else 0.0


def dedupe(vocabulary: dict, examples: list[dict]) -> dict:
    """Keep one of a set of distinctions that all say the same thing.

    Measured 2026-11-04: `sub(a, b)`, `div(a, b)` and `ratio_gap(a, b)` are monotone equivalents
    on positive data, and admitting all three made the learner WORSE than having none -- 0.883
    down to 0.533 -- because three redundant columns raise the multiple-comparison bar until the
    real split is rejected, and the one that survives can have a cut sitting in an outlier.
    Redundancy is not extra information; it is extra cost.
    """
    entries = vocabulary.get("entries") or []
    if len(entries) < 2:
        return vocabulary
    entries = sorted(entries, key=lambda e: -e["cv"])
    kept: list[dict] = []
    kept_values: list[list[float]] = []
    for entry in entries:
        values = []
        for example in examples:
            value = evaluate(_expr_of(entry), example["signals"])
            if value is None:
                values.append(0.0)
            else:
                values.append(float(value))
        if any(abs(_correlation(_ranks(values), _ranks(other))) >= 0.98 for other in kept_values):
            vocabulary.setdefault("rejected", []).append(
                {"expr": entry["renders"], "why": "redundant_with_an_admitted_feature"})
            continue
        kept.append(entry)
        kept_values.append(values)
    for position, entry in enumerate(kept):
        entry["name"] = f"v{position + 1}"
    vocabulary["entries"] = kept
    return vocabulary


def _jsonable(expr: tuple) -> Any:
    return [expr[0]] + [_jsonable(x) if isinstance(x, tuple) else x for x in expr[1:]]


# --------------------------------------------------------------------------- use
def augment(examples: list[dict], vocabulary: dict) -> list[dict]:
    """Add the invented distinctions to every example. From here on the model grows over a
    space that is larger than the one it was given -- because it built the extra dimensions."""
    entries = vocabulary.get("entries") or []
    if not entries:
        return examples
    expanded = []
    for example in examples:
        signals = dict(example["signals"])
        for entry in entries:
            value = evaluate(_expr_of(entry), example["signals"])
            signals[entry["name"]] = value if value is not None else 0.0
        expanded.append({**example, "signals": signals})
    return expanded


def check_still_earning(vocabulary: dict, examples: list[dict], folds) -> dict:
    """Re-check every admitted feature against the evidence that now exists.

    A vocabulary that only grows is a memory leak wearing a mind's clothes. An entry that no
    longer beats the base rate is retired, and the retirement is recorded rather than hidden."""
    if not vocabulary.get("entries"):
        return vocabulary
    floor = _base_rate(folds)
    kept = []
    for entry in vocabulary["entries"]:
        expr = _expr_of(entry)
        score = _cv(examples, expr, None, folds)
        if score < floor + MIN_GAIN * 0.5:
            vocabulary["retired"].append({"name": entry["name"], "cv": round(score, 4),
                                          "why": "no_longer_earns_its_place"})
            continue
        entry["cv_now"] = round(score, 4)
        kept.append(entry)
    vocabulary["entries"] = kept
    return vocabulary


def describe(vocabulary: dict) -> dict:
    return {
        "schema": SCHEMA,
        "vocabulary": [{"name": e["name"], "renders": e["renders"],
                        "cv": e["cv"], "p": e["p"]} for e in vocabulary.get("entries", [])],
        "proposed": vocabulary.get("proposed", 0),
        "admitted": len(vocabulary.get("entries", [])),
        "retired": vocabulary.get("retired", []),
        "rejected_why": _tally(r.get("why") for r in vocabulary.get("rejected", [])),
        "non_claims": [
            "THE_ALGEBRA_IS_GIVEN_THE_SELECTION_OF_COMPOSITIONS_IS_NOT",
            "A_COMPOSED_FEATURE_CAN_FIT_NOISE_THATS_WHY_ADMISSION_IS_HELD_OUT",
            "AN_EMPTY_VOCABULARY_IS_THE_HONEST_RESULT_ON_A_WORLD_WITH_NO_STRUCTURE",
        ],
    }


def _tally(values: Iterable[Any]) -> dict[str, int]:
    out: dict[str, int] = {}
    for value in values:
        out[str(value)] = out.get(str(value), 0) + 1
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))
