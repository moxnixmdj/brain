#!/usr/bin/env python3
"""A learned ranking that lives outside the weights, and survives the process that learned it.

The previous receipt established exactly one transferable object: **four floats** over four
computed features, fitted on 13 items, which solved 7 of 13 held-out items through the
benchmark's own hidden tests. It also established that feature *selection* scored by rank is
not the win, and that one feature gets 5/13 rather than 7/13.

This file is the smallest thing that makes that object real:

  * the features are pure functions of (dotted name, problem text, docstring, stub name) --
    computed, never stored, no world facts;
  * the weights are four floats in plain JSON outside the repo's code, inspectable, editable,
    and deletable without retraining anything;
  * `fit` derives the weights by grid search over outcomes;
  * `rank` applies them.

The claim under test is not "this is a good ranker". It is the user's instant-knowledge
claim, narrowed to something measurable: *knowledge acquired in one session, externalised
as data, reproduces the same behaviour in a later process without being re-learned.*

Authority: NONE. Computed mechanism only. Zero model calls.
"""
from __future__ import annotations

import json
import pathlib
import re
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "BRAIN_LEARNED_RANKING_STORE_V1"
DEFAULT_STORE = pathlib.Path("canonical/astra_runtime/state/LEARNED_RANKING_V1.json")

# Words that carry no purpose. Function words only -- not domain facts.
STOP = frozenset(
    "write function custom returns return takes should uses using compute computes calculate "
    "create new named call called given input value values the a an of to is are in for and "
    "or that this with by on as be it its if not from".split()
)

FEATURES = ("coverage", "doc_overlap", "stub_hit", "depth")


def words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]{3,}", (text or "").lower()) if w not in STOP}


def name_words(dotted: str) -> set[str]:
    base = dotted.rsplit(".", 1)[-1]
    parts = re.split(r"[_.]", re.sub(r"([A-Z])", r"_\1", base).lower())
    return {p for p in parts if len(p) >= 3}


def features(dotted: str, problem: str, doc: str, stub: str) -> dict[str, float]:
    """The four computed features. No weights, no thresholds, nothing stored."""
    nw, q = name_words(dotted), words(problem)
    return {
        "coverage": (len(nw & q) / len(nw)) if nw else 0.0,
        "doc_overlap": len(q & words(doc)) / max(len(q), 1),
        "stub_hit": 1.0 if (name_words(stub) & nw) else 0.0,
        "depth": -0.05 * dotted.count("."),
    }


def score(dotted: str, problem: str, doc: str, stub: str,
          weights: Mapping[str, float]) -> float:
    f = features(dotted, problem, doc, stub)
    return sum(float(weights.get(k, 0.0)) * f[k] for k in FEATURES)


def rank(corpus: Mapping[str, str], problem: str, stub: str,
         weights: Mapping[str, float], *, limit: int = 10) -> list[dict]:
    scored = []
    for dotted, doc in corpus.items():
        s = score(dotted, problem, doc, stub, weights)
        if s > 0:
            scored.append({"name": dotted, "score": round(s, 6),
                           "features": features(dotted, problem, doc, stub)})
    scored.sort(key=lambda r: (-r["score"], r["name"]))
    return scored[:limit]


# ---------------------------------------------------------------------------
# The store: plain JSON, outside the weights, editable and deletable.
# ---------------------------------------------------------------------------

def load(path: str | pathlib.Path | None = None) -> dict[str, Any]:
    target = pathlib.Path(path) if path is not None else DEFAULT_STORE
    if not target.exists():
        return {"schema": SCHEMA, "version": 1, "entries": {}}
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema": SCHEMA, "version": 1, "entries": {}}
    if not isinstance(data, dict):
        return {"schema": SCHEMA, "version": 1, "entries": {}}
    data.setdefault("entries", {})
    return data


def save(store: Mapping[str, Any], path: str | pathlib.Path | None = None) -> pathlib.Path:
    target = pathlib.Path(path) if path is not None else DEFAULT_STORE
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(dict(store), indent=1, sort_keys=True), encoding="utf-8")
    return target


def put_weights(store: dict[str, Any], weights: Mapping[str, float], *,
                learned_from: Sequence[str] = (), note: str = "") -> dict[str, Any]:
    store.setdefault("entries", {})["weights"] = {
        "features": list(FEATURES),
        "weights": {k: float(weights.get(k, 0.0)) for k in FEATURES},
        "learned_from": list(learned_from),
        "note": note,
    }
    return store


def get_weights(store: Mapping[str, Any]) -> dict[str, float]:
    entry = (store.get("entries") or {}).get("weights") or {}
    w = entry.get("weights") or {}
    return {k: float(w.get(k, 0.0)) for k in FEATURES}


def delete(store: dict[str, Any]) -> bool:
    entries = store.setdefault("entries", {})
    had = "weights" in entries
    entries.pop("weights", None)
    return had


# ---------------------------------------------------------------------------
# Fit: derive the weights from outcomes. No gradient descent, no training corpus.
# ---------------------------------------------------------------------------

GRID = tuple(
    (a, b, c, d)
    for a in (0.0, 1.0, 2.0, 4.0, 6.0)
    for b in (0.0, 1.0, 2.0, 4.0, 6.0)
    for c in (0.0, 3.0)
    for d in (1.0,)
)


def fit(examples: Sequence[Mapping[str, Any]], *, corpus: Mapping[str, str],
        hit_depth: int = 10) -> dict[str, Any]:
    """Choose the weights that put the most required names inside `hit_depth`.

    `examples` are (problem, stub, wanted_symbol). Scoring is by rank, which the receipt
    showed is NOT the same as by execution -- so this fit is a ranking fit, not a solve fit,
    and the receipt's 5/13-vs-7/13 result says the two disagree on two items.
    """
    best = None
    for w in GRID:
        weights = dict(zip(FEATURES, w))
        hits = 0
        for ex in examples:
            ranked = rank(corpus, ex["problem"], ex["stub"], weights, limit=hit_depth)
            if any(r["name"].rsplit(".", 1)[-1] == ex["wanted"] for r in ranked):
                hits += 1
        if best is None or hits > best[0]:
            best = (hits, weights)
    hits, weights = best
    return {"weights": weights, "hits": hits, "of": len(examples),
            "hit_depth": hit_depth}


def main(argv: Iterable[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--store", default=None)
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--delete", action="store_true")
    args = ap.parse_args(list(argv) if argv is not None else None)

    store = load(args.store)
    if args.delete:
        print(json.dumps({"deleted": delete(store), "store": str(args.store or DEFAULT_STORE)}))
        save(store, args.store)
        return 0
    payload = {"schema": SCHEMA, "store": str(args.store or DEFAULT_STORE),
               "weights": get_weights(store),
               "learned_from": ((store.get("entries") or {}).get("weights") or {}).get("learned_from", [])}
    print(json.dumps(payload, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
