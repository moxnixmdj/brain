#!/usr/bin/env python3
"""A model that can be wrong about something it has never seen.

Why this file exists
--------------------
The organism of log 11 predicts each target from *that target's* record. That is not a model.
It is a lookup table: `effect::archive_of_plain_repository_files` learned `INPUTS_IGNORED_SILENTLY`
at tick 35 and that knowledge was bound to a string. Presented with a second capability that
silently drops inputs, it would be surprised all over again, from zero. A system with the
expressive power of a lookup table cannot get better at anything it has not already done -- it
can only remember. That is the definition of static code with a scheduler attached.

So the organism needs one structure that serves every target at once: a thing that takes what it
can see *before* acting and says what it expects, where an observation about one instance
changes its expectations about every instance that looks similar.

The three properties this has to have, in order of importance
-------------------------------------------------------------
1. **It must be falsifiable.** It predicts, the world answers, and the answer can be "no".
   A model that is never wrong is a model of nothing.
2. **It must transfer.** Its accuracy on instances it has never seen has to be measured against
   a stated baseline, because a majority-class guess also has accuracy and the difference is
   the only thing that is real.
3. **Its structure must grow without a person enumerating it.** It starts as a single leaf -- one
   undifferentiated expectation -- and *adds distinctions* when the world rewards them. The
   candidate distinctions are generated from the signals it can see; which ones survive is
   decided by held-out error, not by me. Adding a distinction is the only way a system's idea
   space ever gets bigger.

The boundary, stated plainly
----------------------------
The *senses* are given: a finite set of numeric signals a body can read cheaply. That is not a
concession, it is what a body is -- every mind's primitives come from its sensorium. The claim
here is narrower and true: the space of **ideas over those senses** is generated and grown by
the system, not listed by hand. A person provides eyes; the creature decides what to believe
about what it sees. Anything stronger than that would be a lie about what has been built.

The overfitting guard
---------------------
A split is proposed on `train` and kept only if it improves accuracy on `validation`, which was
not used to propose it. Without that gate the structure grows until it has memorised the
training set and learned nothing -- the failure mode this repository has measured before (log 9:
100% on fit, 33% on holdout).
"""
from __future__ import annotations

SCHEMA = "PROJECT_BRAIN_BELIEF_V1"

# A leaf may not be split on fewer than this many examples: below it, any two buckets "improve"
# accuracy by accident, and the split is noise wearing a structure's clothes.
MIN_EXAMPLES_FOR_SPLIT = 3
MAX_DEPTH = 4
# A distinction must beat a chance null, not merely a fixed margin. Measured 2026-11-04: a 2%
# margin let a pure-noise world accept 27 splits in 20 trials, because on 60 examples a random
# split moves accuracy by 2% all the time. The null is now built, not assumed: the validation
# verdicts are shuffled and the split has to beat what shuffling produces.
PERMUTATIONS = 200
PERMUTATION_ALPHA = 0.01
PERMUTATION_SEED = 20261104
MIN_VALIDATION_GAIN = 0.03


# --------------------------------------------------------------------------- structure
def leaf() -> dict:
    return {"kind": "leaf", "counts": {}}


def blank() -> dict:
    """One undifferentiated expectation about the world. Every model starts here."""
    return {
        "schema": SCHEMA,
        "root": leaf(),
        "seen": 0,
        "splits_accepted": 0,
        "splits_proposed": 0,
        "depth_reached": 0,
        "rejected": [],
    }


def _walk(node: dict, signals: dict) -> dict:
    while node.get("kind") == "split":
        value = signals.get(node["signal"])
        if value is None:
            return node.get("otherwise") or leaf()      # a signal it cannot read is not evidence
        node = node["low"] if float(value) <= float(node["threshold"]) else node["high"]
    return node


def _counts(node: dict) -> dict:
    return dict(node.get("counts") or {})


def predict(model: dict, signals: dict) -> str | None:
    """What this model expects, given only what is visible before acting. None = no opinion.

    None is not a default answer: it is the model saying it has nothing to go on. Counting
    that as a correct prediction would let the system report accuracy for questions it
    declined to answer, which is the exact failure `AGENTS.md` exists to stop.
    """
    counts = _counts(_walk(model["root"], signals))
    if not counts:
        return None
    return max(counts.items(), key=lambda kv: (kv[1], kv[0]))[0]


def confidence(model: dict, signals: dict) -> float:
    """Share of the leaf's evidence that agrees with its own answer. 0.0 when there is none."""
    counts = _counts(_walk(model["root"], signals))
    total = sum(counts.values())
    if not total:
        return 0.0
    return max(counts.values()) / total


def observe(model: dict, signals: dict, verdict: str) -> dict:
    """One experience, written into the leaf it falls in. This is how one instance teaches many."""
    node = _walk(model["root"], signals)
    counts = node.setdefault("counts", {})
    counts[str(verdict)] = int(counts.get(str(verdict), 0)) + 1
    model["seen"] = int(model.get("seen", 0)) + 1
    return model


# --------------------------------------------------------------------------- measurement
def accuracy(model: dict, examples: list[dict]) -> tuple[float, int]:
    """(share correct, number actually answered). Unanswered examples are not correct."""
    right = answered = 0
    for ex in examples:
        guess = predict(model, ex["signals"])
        if guess is None:
            continue
        answered += 1
        right += int(guess == ex["verdict"])
    return (right / answered if answered else 0.0), answered


def majority_baseline(examples: list[dict]) -> float:
    """The guess a system that had learned nothing about signals would make. The number to beat."""
    counts: dict[str, int] = {}
    for ex in examples:
        counts[ex["verdict"]] = counts.get(ex["verdict"], 0) + 1
    total = sum(counts.values())
    return (max(counts.values()) / total) if total else 0.0


# --------------------------------------------------------------------------- growth
def _candidate_thresholds(examples: list[dict], signal: str) -> list[float]:
    values = sorted({float(ex["signals"][signal]) for ex in examples
                     if ex["signals"].get(signal) is not None})
    return [(a + b) / 2.0 for a, b in zip(values, values[1:])]


def _entropy(counts: dict) -> float:
    import math
    total = sum(counts.values())
    if total <= 0:
        return 0.0
    return -sum((c / total) * math.log2(c / total) for c in counts.values() if c > 0)


def _side(ex: dict, signal: str, threshold: float) -> str | None:
    value = ex["signals"].get(signal)
    if value is None:
        return None
    return "low" if float(value) <= threshold else "high"


def _split_examples(examples: list[dict], signal: str, threshold: float):
    low, high = [], []
    for ex in examples:
        side = _side(ex, signal, threshold)
        if side == "low":
            low.append(ex)
        elif side == "high":
            high.append(ex)
        # an unreadable signal belongs to neither bucket: it is not evidence
    return low, high


def _leaf_from(examples: list[dict]) -> dict:
    counts: dict[str, int] = {}
    for ex in examples:
        counts[ex["verdict"]] = counts.get(ex["verdict"], 0) + 1
    return {"kind": "leaf", "counts": counts}


def _weighted_entropy(examples: list[dict]) -> float:
    return _entropy(_leaf_from(examples)["counts"]) * len(examples)


def _split_node(node: dict, signal: str, threshold: float, low: dict, high: dict) -> dict:
    """`otherwise` keeps what was known before the split for any signal it cannot read."""
    return {"kind": "split", "signal": signal, "threshold": threshold,
            "low": low, "high": high, "otherwise": node}


def _node_accuracy(node: dict, examples: list[dict]) -> float:
    if not examples:
        return 0.0
    right = 0
    for ex in examples:
        counts = _counts(_walk(node, ex["signals"]))
        if counts and ex["verdict"] == max(counts.items(), key=lambda kv: (kv[1], kv[0]))[0]:
            right += 1
    return right / len(examples)


DEEPEST_PER_SIGNAL = 8


def _candidates(train: list[dict], limit: int = 12):
    """One candidate per signal -- the best cut of each -- ranked by how much it explains.

    Measured 2026-11-04: this used to return the global top-k over every (signal, threshold)
    pair. That made the system WORSE when it gained new senses: three invented columns pushed
    the one base feature that already predicted the verdict out of the top six, so the learner
    rejected everything and fell back to the majority class -- 0.883 down to 0.533 on a world it
    had been solving. A ranking is not a filter. Every signal gets exactly one shot, so gaining a
    dimension can never take a shot away from an existing one.
    """
    per_signal: dict[str, list[tuple[float, float]]] = {}
    for signal in sorted({k for ex in train for k in ex["signals"]}):
        cuts = []
        for threshold in _candidate_thresholds(train, signal):
            low, high = _split_examples(train, signal, threshold)
            if not low or not high:
                continue
            gain = (_weighted_entropy(train)
                    - _weighted_entropy(low) - _weighted_entropy(high))
            if gain > 0:
                cuts.append((gain, threshold))
        if cuts:
            cuts.sort(key=lambda c: -c[0])
            per_signal[signal] = cuts[:DEEPEST_PER_SIGNAL]
    """Quotas, not a cap -- and the difference was measured twice.

    2026-11-04, crowding: the old rule ranked every (signal, threshold) pair together and kept
    the top twelve, so three invented columns pushed the base feature that already worked out of
    the list and the learner fell to the base rate. Gaining a dimension must never cost an
    existing one its shot.

    2026-11-04, the opposite mistake: keeping only ONE candidate per signal cost the `ratio`
    world 0.883 -> 0.533, because a diagonal boundary can only be approximated by a tree if the
    tree has a dense ladder of cuts on one axis (1, 2 and 4 shots all gave 0.533; 8 restored
    0.883). So each signal keeps a full ladder, and every signal is guaranteed at least its best
    cut. Redundancy across signals is handled later, by `vocabulary_v1.dedupe`.
    """
    scored = []
    guaranteed = []
    for signal, cuts in per_signal.items():
        guaranteed.append((cuts[0][0], signal, cuts[0][1]))
        scored.extend((gain, signal, threshold) for gain, threshold in cuts)
    # Guarantee every sense its best cut, then rank by gain only. The guarantee is what stops an
    # invented column from crowding out a base sense (see the crowding test). The ORDER is not
    # load bearing: measured 2026-11-04, putting guaranteed cuts at the head gave `ratio` 0.617 and
    # gain-only ranking gave 0.617, so both are kept simple. An earlier reading of 0.883 on the
    # same world could not be reproduced and is not attributed to anything.
    merged = {c: None for c in guaranteed}
    for candidate in scored:
        merged.setdefault(candidate, None)
    ranked = sorted(merged, key=lambda c: -c[0])
    keep = set(guaranteed) | set(ranked[:max(limit, len(per_signal))])
    return [c for c in ranked if c in keep]


# --------------------------------------------------------------------------- cross-validation
def capability_folds(examples: list[dict], k: int = 4, seed: int = PERMUTATION_SEED):
    """Split BY GROUP, never by example.

    Measured 2026-11-04: a single 75/25 split of capabilities gave eight validation capabilities
    whose verdicts were so unrepresentative that an undifferentiated leaf scored 0.903 there and
    0.484 on the real holdout. Selection on that slice rejected every distinction, including the
    ones that are plainly real (`missing_module_imports > 0` -> CRASHED, 43 of 48). Folds over
    groups are the smallest honest fix: every group is tested, and no group is in both sides.
    """
    import random
    groups: dict[str, list[dict]] = {}
    for ex in examples:
        groups.setdefault(str(ex.get("group", ex.get("capability"))), []).append(ex)
    keys = sorted(groups)
    random.Random(seed).shuffle(keys)
    folds = []
    for i in range(k):
        held = set(keys[i::k])
        train = [ex for key in keys if key not in held for ex in groups[key]]
        test = [ex for key in keys if key in held for ex in groups[key]]
        if train and test:
            folds.append((train, test))
    return folds


def _cv_scores(folds, build) -> list[float]:
    return [_node_accuracy(build(train), test) for train, test in folds]


def _cv_accuracy(folds, build) -> float:
    scores = _cv_scores(folds, build)
    return sum(scores) / len(scores) if scores else 0.0


def _cv_p(before_node: dict, signal: str, threshold: float, folds, observed: float,
          shuffles: int = PERMUTATIONS) -> float:
    """Probability that a shuffled world gives a distinction this good.

    The null is the honest one: if this distinction were noise, the verdicts attached to these
    examples would be exchangeable. Verdicts are shuffled WITHIN each fold's training data,
    the same distinction is rebuilt, and the same out-of-group accuracy is recomputed.

    Measured 2026-11-04: the first version of this drew from one shared shuffled list with a
    cursor that ran past its end by the third fold, emptied a bucket, and returned p=1.0 for a
    distinction that scored 1.000 against a 0.000 baseline. A test that fails open is worse than
    no test, so this one is written to fail closed (see the guard below).
    """
    import random
    rng = random.Random(PERMUTATION_SEED)
    at_least = 0
    for _ in range(shuffles):
        scored = []
        for fold_train, fold_test in folds:
            verdicts = [ex["verdict"] for ex in fold_train]
            rng.shuffle(verdicts)
            shuffled = [{"signals": ex["signals"], "verdict": v}
                        for ex, v in zip(fold_train, verdicts)]
            low, high = _split_examples(shuffled, signal, threshold)
            if not low or not high:
                scored.append(0.0)                 # fail closed, never open
                continue
            node = _split_node(before_node, signal, threshold,
                               _leaf_from(low), _leaf_from(high))
            scored.append(_node_accuracy(node, fold_test))
        if scored and sum(scored) / len(scored) >= observed:
            at_least += 1
    return at_least / shuffles


def _verdict(node: dict, signal: str, threshold: float, folds):
    """(mean cv accuracy, worst fold delta) for one candidate under one grouping."""
    def build(tr):
        low, high = _split_examples(tr, signal, threshold)
        if not low or not high:
            return node
        return _split_node(node, signal, threshold, _leaf_from(low), _leaf_from(high))
    before_scores = _cv_scores(folds, lambda tr: node)
    after_scores = _cv_scores(folds, build)
    mean_after = sum(after_scores) / len(after_scores) if after_scores else 0.0
    mean_before = sum(before_scores) / len(before_scores) if before_scores else 0.0
    # after minus before. Measured 2026-11-04: written the other way round it reported a
    # +0.69 improvement on every fold as -0.69 of harm, and a perfectly learnable world was
    # rejected as if it were noise.
    deltas = [after - before for before, after in zip(before_scores, after_scores)]
    return mean_before, mean_after, (min(deltas) if deltas else 0.0)


def _accepts(node: dict, signal: str, threshold: float, folds, index: int,
             require_every_fold: bool = True):
    """Does this distinction survive ONE independent grouping? Returns (ok, attempt record)."""
    before, after, worst = _verdict(node, signal, threshold, folds)
    record = {"signal": signal, "threshold": round(threshold, 4),
              "cv_before": round(before, 4), "cv_after": round(after, 4),
              "worst_fold_delta": round(worst, 4)}
    if after - before < MIN_VALIDATION_GAIN:
        record["reason"] = "no_out_of_group_improvement"
        return False, record
    if require_every_fold and worst < 0:
        record["reason"] = "helped_on_average_but_hurt_a_group"
        return False, record
    p = _cv_p(node, signal, threshold, folds, after)
    bar = PERMUTATION_ALPHA / (index + 1)      # Holm-style: many tries must clear a higher bar
    record["p"] = round(p, 4)
    record["bar"] = round(bar, 4)
    if p >= bar:
        record["reason"] = "not_beyond_chance"
        return False, record
    return True, record


def grow(node: dict, train: list[dict], folds, depth: int = 0, log: list | None = None,
         alt_folds=None) -> dict:
    """Add the best distinction that survives out-of-group testing, or none.

    Candidates come from information gain on the training data. Whether one is kept is decided
    by folds of *unseen capabilities* and a shuffled-verdict null. Nothing about the final
    holdout is visible here.
    """
    if log is None:
        log = []
    if depth >= MAX_DEPTH or len(train) < MIN_EXAMPLES_FOR_SPLIT or not folds:
        return node

    attempts = []
    chosen = None
    for index, (_, signal, threshold) in enumerate(_candidates(train)):
        ok, record = _accepts(node, signal, threshold, folds, index)
        if ok and alt_folds:
            # Stability: the same distinction has to survive a DIFFERENT grouping of the same
            # data. Measured 2026-11-04: one grouping plus a permutation test still accepted
            # splits in seven of twenty pure-noise worlds. Noise is not stable; a rule about
            # the world does not depend on how the groups happen to be cut.
            ok, second = _accepts(node, signal, threshold, alt_folds, index,
                                  require_every_fold=False)
            record["second_grouping"] = second
        attempts.append(record)
        if ok:
            chosen = (signal, threshold, record.get("cv_after"))
            break

    if chosen is None:
        log.append({"depth": depth, "accepted": False, "attempts": attempts})
        return node

    signal, threshold, score = chosen
    log.append({"depth": depth, "accepted": True, "signal": signal,
                "threshold": round(threshold, 4), "cv_after": score, "attempts": attempts})
    low_all, high_all = _split_examples(train, signal, threshold)
    low_folds, high_folds = [], []
    for fold_train, fold_test in folds:
        low_test = [ex for ex in fold_test if _side(ex, signal, threshold) == "low"]
        high_test = [ex for ex in fold_test if _side(ex, signal, threshold) == "high"]
        low_train, high_train = _split_examples(fold_train, signal, threshold)
        if low_train and low_test:
            low_folds.append((low_train, low_test))
        if high_train and high_test:
            high_folds.append((high_train, high_test))
    return _split_node(
        node, signal, threshold,
        grow(_leaf_from(low_all), low_all, low_folds, depth + 1, log),
        grow(_leaf_from(high_all), high_all, high_folds, depth + 1, log))


def fit(model: dict, train: list[dict], validation: list[dict] | None = None) -> dict:
    """Grow the model against out-of-group folds and record what it accepted and refused.

    `validation`, when given, is appended as further evidence inside the folds rather than used
    as a single slice -- one slice is what failed on 2026-11-04.
    """
    everything = list(train) + list(validation or [])
    folds = capability_folds(everything, seed=PERMUTATION_SEED)
    alt_folds = capability_folds(everything, seed=PERMUTATION_SEED + 1)
    log: list = []
    # Start from the base rate, not from an empty leaf. Measured 2026-11-04: growing from an
    # empty leaf made the baseline score 0.000, so EVERY candidate looked like a large
    # improvement and the gate had nothing to compare against -- twenty pure-noise worlds
    # produced ten accepted splits. A model always has a prior; the question is whether a
    # distinction beats it.
    model["root"] = grow(_leaf_from(everything), everything, folds, 0, log, alt_folds)
    if not _counts(model["root"]):
        model["root"]["counts"] = _leaf_from(everything)["counts"]
    model["splits_proposed"] = int(model.get("splits_proposed", 0)) + len(log)
    model["splits_accepted"] = sum(1 for e in log if e["accepted"])
    model["accepted"] = [e for e in log if e["accepted"]]
    model["rejected"] = [e for e in log if not e["accepted"]]
    depth = 0
    node = model["root"]
    while node.get("kind") == "split":
        depth += 1
        node = node["low"]
    model["depth_reached"] = depth
    model["seen"] = sum(sum(_counts(n).values()) for n in _leaves(model["root"]))
    return model


def _leaves(node: dict) -> list[dict]:
    if node.get("kind") != "split":
        return [node]
    return _leaves(node["low"]) + _leaves(node["high"])


def describe(model: dict) -> dict:
    """A readable account of what it believes and what it refused to believe."""
    def walk(node):
        if node.get("kind") != "split":
            return {"leaf": dict(node.get("counts") or {})}
        return {"split_on": node["signal"], "at": node["threshold"],
                "low": walk(node["low"]), "high": walk(node["high"])}
    return {
        "schema": SCHEMA,
        "structure": walk(model["root"]),
        "seen": model.get("seen", 0),
        "splits_accepted": model.get("splits_accepted", 0),
        "splits_proposed": model.get("splits_proposed", 0),
        "accepted": list(model.get("accepted") or []),
        "rejected": list(model.get("rejected") or [])[-8:],
        "non_claims": [
            "SIGNALS_ARE_SENSES_GIVEN_BY_THE_BODY_NOT_IDEAS_INVENTED",
            "THE_IDEA_SPACE_OVER_THOSE_SENSES_IS_GROWN_AND_VALIDATED_HERE",
            "ACCURACY_IS_MEANINGLESS_WITHOUT_THE_BASELINE_IT_IS_COMPARED_TO",
        ],
    }
