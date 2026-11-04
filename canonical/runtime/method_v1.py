#!/usr/bin/env python3
"""The creature picks how to think, by measuring, instead of being told.

Seventeen logs, one learning procedure. Beliefs grew inside it, vocabulary grew inside it, tree
shape grew inside it -- and the procedure never moved. Every constant in it was mine: depth, width,
minimum gain, minimum leaf, and the choice of an axis-aligned greedy tree at all.

That last one is why `xor` has failed every log. It is not a fact about the world; it is a fact
about the single hypothesis space I handed the creature. A depth-two tree can express xor. A stump
cannot. Nearest neighbours do not care. So the method is not a detail of the implementation -- it
is the thing that decides what the creature is capable of, and it was the one thing I never let it
choose.

What this module does: a space of methods is generated (hypothesis shape x feature space x
capacity), each one is fitted and scored out-of-fold on the creature's own experience, and the
creature adopts the method that measurably predicts better -- subject to the same discipline every
other claim in this repository faces. The method is chosen on one grouping and must then pay on two
more it was not chosen on, in every fold, or it is not adopted.

What is honestly still mine: the primitives. `tree` and `nearest neighbours` are a person's idea of
what kinds of hypothesis are thinkable. The creature composes and selects them; it does not invent
them. That is the next static layer, and this log does not claim to have removed it.
"""
from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import belief_v1 as belief   # noqa: E402
from canonical.runtime import vocabulary_v1 as vocab  # noqa: E402

SCHEMA = "PROJECT_BRAIN_METHOD_V1"
MIN_GAIN = 0.03              # a method must beat "learn nothing" by this much, every fold
MIN_LEAF = 5


@dataclass(frozen=True)
class Method:
    """One way of thinking. Addressable, comparable, and chosen by measurement."""

    kind: str                 # "majority" | "stump" | "tree" | "nearest"
    capacity: int = 1         # tree depth, or number of neighbours
    features: str = "raw"     # "raw" | "invented"

    @property
    def name(self) -> str:
        if self.kind == "belief":
            return "belief[incumbent]"
        if self.kind in ("majority", "stump"):
            return f"{self.kind}[{self.features}]"
        if self.kind == "tree":
            return f"tree(depth={self.capacity})[{self.features}]"
        return f"nearest(k={self.capacity})[{self.features}]"


# --------------------------------------------------------------------------- helpers
def _entropy(counts: dict[str, int]) -> float:
    total = sum(counts.values())
    if total == 0:
        return 0.0
    out = 0.0
    for count in counts.values():
        if count:
            share = count / total
            out -= share * math.log2(share)
    return out


def _tally(labels) -> dict[str, int]:
    counts: dict[str, int] = {}
    for label in labels:
        counts[str(label)] = counts.get(str(label), 0) + 1
    return counts


def _majority(examples: list[dict]) -> str | None:
    counts = _tally(ex.get("verdict") for ex in examples)
    return max(counts.items(), key=lambda kv: (kv[1], kv[0]))[0] if counts else None


def _features(signals: dict, names: list[str]) -> list[float]:
    return [float(signals.get(name) or 0.0) for name in names]


# --------------------------------------------------------------------------- hypotheses
def _best_cut(examples: list[dict], names: list[str]):
    parent = _entropy(_tally(ex.get("verdict") for ex in examples))
    best = None
    for name in names:
        values = sorted({ex["signals"].get(name) for ex in examples
                         if ex["signals"].get(name) is not None})
        if len(values) < 2:
            continue
        # quantile-spaced candidates: a cut is only meaningful if it leaves examples on each side
        step = max(1, len(values) // 24)
        for index in range(step, len(values), step):
            threshold = (values[index - 1] + values[index]) / 2.0
            low = [ex for ex in examples if (ex["signals"].get(name) or 0.0) <= threshold]
            high = [ex for ex in examples if (ex["signals"].get(name) or 0.0) > threshold]
            if len(low) < MIN_LEAF or len(high) < MIN_LEAF:
                continue
            gain = parent - (len(low) / len(examples)) * _entropy(
                _tally(ex.get("verdict") for ex in low)) - (len(high) / len(examples)) * _entropy(
                _tally(ex.get("verdict") for ex in high))
            if best is None or gain > best[2]:
                best = (name, threshold, gain)
    return best


@dataclass
class _Tree:
    names: list[str]
    depth: int
    node: Any = None

    def fit(self, examples: list[dict]) -> "_Tree":
        self.node = self._grow(examples, self.depth)
        return self

    def _grow(self, examples: list[dict], depth: int):
        guess = _majority(examples)
        if depth <= 0 or len(examples) < 2 * MIN_LEAF:
            return {"leaf": guess}
        cut = _best_cut(examples, self.names)
        if cut is None or cut[2] <= 0:
            return {"leaf": guess}
        name, threshold, _ = cut
        low = [ex for ex in examples if (ex["signals"].get(name) or 0.0) <= threshold]
        high = [ex for ex in examples if (ex["signals"].get(name) or 0.0) > threshold]
        # Each branch decides its own follow-up. This is the difference between a stump that has
        # two cuts applied everywhere and a tree where the branch chooses -- measured 2026-11-04,
        # xor is exactly that difference and no previous version could express it.
        return {"signal": name, "threshold": threshold,
                "low": self._grow(low, depth - 1), "high": self._grow(high, depth - 1)}

    def predict(self, signals: dict) -> str | None:
        node = self.node
        while node and "leaf" not in node:
            node = node["low"] if (signals.get(node["signal"]) or 0.0) <= node["threshold"] \
                else node["high"]
        return (node or {}).get("leaf")


@dataclass
class _Belief:
    """The incumbent: the tree this repository has been growing since log 9, with its gates.

    It belongs IN the space rather than beside it. Measured 2026-11-04: when the method search
    declined to adopt anything, falling back to "learn nothing" threw away a working model and
    cost the `or` world its answer (0.986 -> 0.519). A system that abandons its own competence
    whenever a search is inconclusive is worse than one that never searched.
    """

    model: dict = field(default_factory=dict)

    def fit(self, examples: list[dict]) -> "_Belief":
        self.model = belief.blank()
        belief.fit(self.model, examples)
        return self

    def predict(self, signals: dict) -> str | None:
        return belief.predict(self.model, signals)


@dataclass
class _Nearest:
    names: list[str]
    k: int
    train: list[dict] = field(default_factory=list)
    scale: list[float] = field(default_factory=list)

    def fit(self, examples: list[dict]) -> "_Nearest":
        self.train = list(examples)
        columns = [list(column) for column in zip(*[_features(ex["signals"], self.names)
                                                    for ex in examples])]
        self.scale = [max(1e-9, (max(col) - min(col)) if col else 1.0) for col in columns]
        return self

    def predict(self, signals: dict) -> str | None:
        if not self.train:
            return None
        point = _features(signals, self.names)
        distances = sorted(
            ((sum(((a - b) / s) ** 2 for a, b, s in zip(point,
                                                        _features(ex["signals"], self.names),
                                                        self.scale)), ex)
             for ex in self.train), key=lambda pair: pair[0])
        nearest = [ex.get("verdict") for _, ex in distances[:max(1, self.k)]]
        counts = _tally(nearest)
        return max(counts.items(), key=lambda kv: (kv[1], kv[0]))[0] if counts else None


def make(method: Method, names: list[str]) -> Callable:
    if method.kind == "belief":
        return lambda examples: _Belief().fit(examples)
    if method.kind in ("majority", "stump"):
        return lambda examples: _Tree(names, 1 if method.kind == "stump" else 0).fit(examples)
    if method.kind == "tree":
        return lambda examples: _Tree(names, method.capacity).fit(examples)
    return lambda examples: _Nearest(names, method.capacity).fit(examples)


# --------------------------------------------------------------------------- the space
def method_space(invented: bool = True) -> list[Method]:
    """The product of what can be hypothesised, over what it is hypothesised about.

    Generated, not listed one by one: a shape and a capacity and a feature space, crossed. The
    combination `nearest neighbours over invented features` is one I never wrote down anywhere;
    it exists because the product exists.
    """
    spaces = ["raw"] + (["invented"] if invented else [])
    methods: list[Method] = [Method("majority"), Method("belief")]
    for space_name in spaces:
        methods.append(Method("stump", 1, space_name))
        for depth in (2, 3):
            methods.append(Method("tree", depth, space_name))
        for k in (1, 5, 11):
            methods.append(Method("nearest", k, space_name))
    return methods


def _prepare(method: Method, examples: list[dict], vocabulary: dict | None) -> list[dict]:
    if method.features != "invented" or not vocabulary or not vocabulary.get("entries"):
        return examples
    return vocab.augment(examples, vocabulary)


def names_of(examples: list[dict]) -> list[str]:
    return sorted({key for ex in examples for key in ex["signals"]})


def score(method: Method, examples: list[dict], folds, vocabulary: dict | None = None) -> dict:
    """Out-of-fold accuracy of one method, and its margin over learning nothing at all."""
    scores, deltas = [], []
    for train, test in folds:
        train_rows = _prepare(method, train, vocabulary)
        test_rows = _prepare(method, test, vocabulary)
        if not train_rows or not test_rows:
            continue
        predictor = make(method, names_of(train_rows))(train_rows)
        right = sum(1 for ex in test_rows if predictor.predict(ex["signals"]) == ex.get("verdict"))
        guess = _majority(train_rows)
        base = sum(1 for ex in test_rows if ex.get("verdict") == guess) / len(test_rows)
        after = right / len(test_rows)
        scores.append(after)
        deltas.append(after - base)
    if not scores:
        return {"method": method.name, "cv": 0.0, "margin": 0.0, "worst": 0.0, "folds": 0}
    return {"method": method.name, "cv": round(sum(scores) / len(scores), 4),
            "margin": round(sum(deltas) / len(deltas), 4), "worst": round(min(deltas), 4),
            "folds": len(scores)}


def winner_null(method_: Method, examples: list[dict], folds, observed: float,
                vocabulary: dict | None = None, shuffles: int = 30) -> dict:
    """The score the same method gets on verdicts that carry no information.

    Every other gate in this repository has a null. The method search did not, and measured
    2026-11-04 that showed: three of forty structureless worlds adopted a method with a margin of
    0.15, which is not a margin a random-label world can honestly produce. If the winner cannot
    beat what it scores on shuffled verdicts, the win was the search.
    """
    import random as _random
    rng = _random.Random(belief.PERMUTATION_SEED + 29)
    labels = [ex.get("verdict") for ex in examples]
    scores = []
    for _ in range(shuffles):
        shuffled = list(labels)
        rng.shuffle(shuffled)
        proxy = [{"group": ex.get("group", i), "signals": ex["signals"], "verdict": shuffled[i]}
                 for i, ex in enumerate(examples)]
        # The folds must be built on the shuffled labels, not reused from the real ones. Measured
        # 2026-11-04: `score` reads its data from the folds, so passing the original folds made
        # this null score the ORIGINAL verdicts thirty times -- it returned "not beyond chance" for
        # every world, including worlds with a perfectly learnable rule, and the bug looked like a
        # conservative gate rather than a broken one.
        proxy_folds = belief.capability_folds(proxy, seed=belief.PERMUTATION_SEED)
        scores.append(score(method_, proxy, proxy_folds, vocabulary)["cv"])
    scores.sort()
    beats = sum(1 for value in scores if value >= observed)
    return {"shuffles": shuffles, "best_shuffled": round(scores[-1], 4) if scores else 0.0,
            "beaten_by_chance": beats, "passed": beats == 0}


def choose(examples: list[dict], folds, spread: int = 2, vocabulary: dict | None = None,
           methods: list[Method] | None = None) -> dict:
    """Adopt the method that measures best here, if it keeps measuring well where it was not chosen.

    Selection is the danger. Choosing one of ten methods on one grouping and believing its score is
    the same mistake this repository has caught three times -- a lucky fold paying for unlucky ones.
    So the winner is re-scored on `spread` further groupings of the same experience, and it is only
    adopted if it still beats 'learn nothing' in EVERY fold of every one of them.
    """
    import random as _random
    candidates = methods if methods is not None else method_space(bool(vocabulary))
    scored = [dict(score(method, examples, folds, vocabulary), method_object=method)
              for method in candidates]
    scored.sort(key=lambda row: -row["cv"])
    winner = scored[0]
    # There used to be a second incumbent test here, comparing the winner to the incumbent on the
    # SELECTION grouping. Measured 2026-11-04 it is subsumed by the like-for-like comparison the
    # regroup checks already make, and a mutation that deleted it changed no outcome. Two guards
    # doing one job is not twice the safety; it is a second thing to keep true.
    if winner["method_object"].kind in ("majority",):
        return {"adopted": False, "reason": "nothing_beats_learning_nothing",
                "chosen": winner["method"], "scored": scored}

    null = winner_null(winner["method_object"], examples, folds, winner["cv"], vocabulary)
    if not null["passed"]:
        return {"adopted": False, "reason": "not_beyond_shuffled_verdicts",
                "chosen": winner["method"], "null": null, "scored": scored}

    checks = []
    incumbent_row = next((row for row in scored if row["method_object"].kind == "belief"), None)
    for extra in range(1, spread + 1):
        alt = belief.capability_folds(examples, seed=belief.PERMUTATION_SEED + extra)
        result = score(winner["method_object"], examples, alt, vocabulary)
        rival = (score(incumbent_row["method_object"], examples, alt, vocabulary)
                 if incumbent_row else {"cv": 0.0})
        checks.append({"grouping": extra, "cv": result["cv"], "margin": result["margin"],
                       "worst": result["worst"],
                       "over_incumbent": round(result["cv"] - rival["cv"], 4)})
        # A method that needs a particular regrouping to look good is fitted to the regrouping,
        # and "better than learning nothing" is not the question -- better than what the creature
        # would do anyway is. Measured 2026-11-04: comparing only against the base rate left three
        # of forty structureless worlds adopting a method.
        if rival["cv"] and result["cv"] - rival["cv"] < MIN_GAIN:
            return {"adopted": False, "reason": "did_not_beat_the_incumbent_when_regrouped",
                    "chosen": winner["method"], "checks": checks, "scored": scored}
        if result["margin"] < MIN_GAIN or result["worst"] <= 0:
            return {"adopted": False, "reason": "did_not_survive_regrouping",
                    "chosen": winner["method"], "checks": checks, "scored": scored}
    winner_gain = winner["cv"] - scored[-1]["cv"]
    return {"adopted": True, "reason": "won_and_survived", "chosen": winner["method"],
            "null": null,
            "cv": winner["cv"], "margin": winner["margin"], "checks": checks,
            "selection_optimism": round(winner["cv"] - checks[-1]["cv"], 4),
            "methods_tried": len(candidates), "scored": scored}
