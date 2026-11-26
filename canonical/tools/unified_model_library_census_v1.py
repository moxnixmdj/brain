"""Measure the unified model's library instead of trusting its declared count.

Three numbers the model has never reported about itself:

1. **How many capabilities are distinct.** The artifact declares 447 capabilities. Counting
   the *implementation* behind each id (sha256 of the module the capability's provenance
   names) collapses them to far fewer, because one adapter file is registered under many ids.

2. **How many can be asked for in words.** A capability whose only vocabulary is its own path
   can be addressed by name and by nothing else. Measured by looking for a declared
   natural-language phrase a caller could plausibly say.

3. **The routing recall curve.** Recall@1 as the library grows, measured without any labelled
   task set: hide a capability, restrict the index to a random subset of size k that contains
   it, and route a query built from its *declared trigger phrase*. Triggers are metadata the
   index was not built from (the index comes from provides/requires/id terms), so a hit is
   semantic overlap rather than the name restating itself.

Run: ``python3 -m canonical.tools.unified_model_library_census_v1``
"""
from __future__ import annotations

import argparse
import ast
import collections
import hashlib
import json
import pathlib
import random
import statistics
import sys
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

CLAUSE = (
    "A capability is only a capability if a person can ask for it. Counting ids measures the "
    "registry; counting distinct implementations measures the library; counting askable ids "
    "measures what the router can actually reach."
)


def _module_path(cid: str, rec: dict[str, Any]) -> str | None:
    provenance = rec.get("provenance") or {}
    path = provenance.get("source_path")
    if path:
        return str(path)
    if cid.startswith("canonical/"):
        return cid.split(".auto.v1")[0]
    return None


def askable_phrases(rec: dict[str, Any]) -> list[str]:
    """Declared trigger phrases a caller could plausibly say out loud.

    Slugs (``report.call_graph``), version markers (``v1``), bare numbers and shouting
    (``PASS__…``) are excluded: they are names, not requests.
    """
    out: list[str] = []
    for raw in rec.get("triggers") or []:
        text = str(raw).strip()
        if " " not in text or len(text) < 8:
            continue
        if text.isupper():
            continue
        if not any(ch.islower() for ch in text):
            continue
        if text.count(".") > 1:
            continue
        out.append(text)
    return out


def docstring_sentence(cid: str, rec: dict[str, Any], root: pathlib.Path) -> str | None:
    """First sentence of the module's own docstring, if it has one worth reading."""
    path = _module_path(cid, rec)
    if not path:
        return None
    target = root / path
    if not target.is_file():
        return None
    try:
        doc = ast.get_docstring(ast.parse(target.read_text(encoding="utf-8", errors="replace")))
    except SyntaxError:
        return None
    if not doc:
        return None
    flat = " ".join(doc.split())
    first = " ".join(flat.split(". ")[0].split())
    return first if len(first) >= 20 else None


def _self_locating(model: Any, caps: dict[str, Any]) -> dict[str, Any]:
    """Can a capability be found by describing what it does, using its own recorded description?

    This is the measure the artifact could not report before the compiler started carrying
    the module's docstring sentence: with no description stored, the numerator is zero by
    construction, whatever the router is capable of.
    """
    described = {cid: str(rec["described_as"]) for cid, rec in caps.items()
                 if isinstance(rec, dict) and rec.get("described_as")}
    if not described:
        return {"n": 0, "found": 0, "share": 0.0}
    found = 0
    for cid, sentence in described.items():
        routed = model.route(sentence, top_k=1)
        if (routed.get("best") or {}).get("id") == cid:
            found += 1
    return {"n": len(described), "found": found, "share": round(found / len(described), 4)}


def census(root: str | pathlib.Path = ".", *, sample: int = 200, trials: int = 24,
           seed: int = 20261124) -> dict[str, Any]:
    sys.path.insert(0, str(pathlib.Path(root).resolve()))
    from canonical.runtime.brain_unified_model_v1 import open_model

    base = pathlib.Path(root)
    model = open_model()
    caps: dict[str, Any] = model.capabilities

    # --- 1. declared vs distinct -------------------------------------------------------
    by_content: dict[str, list[str]] = collections.defaultdict(list)
    unresolved: list[str] = []
    for cid, rec in caps.items():
        path = _module_path(cid, rec)
        target = base / path if path else None
        if not target or not target.is_file():
            unresolved.append(cid)
            continue
        by_content[hashlib.sha256(target.read_bytes()).hexdigest()].append(cid)
    duplicate_groups = {d: ids for d, ids in by_content.items() if len(ids) > 1}
    largest = max(by_content.values(), key=len) if by_content else []
    collapsed = sum(len(ids) for ids in duplicate_groups.values())

    # --- 2. askable in words -----------------------------------------------------------
    askable = [cid for cid, rec in caps.items() if askable_phrases(rec)]
    with_doc = [cid for cid, rec in caps.items() if docstring_sentence(cid, rec, base)]
    doc_counts = collections.Counter(
        docstring_sentence(cid, caps[cid], base) for cid in with_doc
    )
    generic = sum(n for n in doc_counts.values() if n > 1)

    # --- 3. routing recall curve -------------------------------------------------------
    pool = sorted({cid for postings in model.index.values() for cid in postings} | set(caps))
    eligible = [cid for cid in pool if askable_phrases(caps.get(cid) or {})]
    rng = random.Random(seed)
    victims = rng.sample(eligible, min(sample, len(eligible)))
    saved_index, saved_caps = model.index, model.capabilities
    curve: list[dict[str, Any]] = []
    try:
        for k in (16, 32, 64, 128, 192, 256, 320, 384, len(pool)):
            per_victim: list[float] = []
            for victim in victims:
                phrases = askable_phrases(saved_caps.get(victim) or {})
                if not phrases:
                    continue
                hits = 0
                for _ in range(trials):
                    others = [c for c in pool if c != victim]
                    keep = set(rng.sample(others, min(k - 1, len(others)))) | {victim}
                    model.index = {
                        tok: {c: w for c, w in post.items() if c in keep}
                        for tok, post in saved_index.items()
                    }
                    model.index = {tok: p for tok, p in model.index.items() if p}
                    model.capabilities = {c: r for c, r in saved_caps.items() if c in keep}
                    routed = model.route(rng.choice(phrases), top_k=1)
                    if (routed.get("best") or {}).get("id") == victim:
                        hits += 1
                per_victim.append(hits / trials)
            if not per_victim:
                continue
            mean = statistics.fmean(per_victim)
            stderr = statistics.stdev(per_victim) / (len(per_victim) ** 0.5)
            curve.append({
                "library_size": k,
                "recall_at_1": round(mean, 4),
                "ci95": [round(mean - 1.96 * stderr, 4), round(mean + 1.96 * stderr, 4)],
                "victims": len(per_victim),
                "trials_per_victim": trials,
            })
    finally:
        model.index, model.capabilities = saved_index, saved_caps

    return {
        "schema": "PROJECT_BRAIN_UNIFIED_MODEL_LIBRARY_CENSUS_V1",
        "clause": CLAUSE,
        "root": str(base.resolve()),
        "declared_capabilities": len(caps),
        "distinct_implementations": len(by_content),
        "duplicate_capabilities": collapsed,
        "duplicate_share": round(collapsed / max(1, len(caps)), 4),
        "largest_duplicate_group": {
            "ids": len(largest),
            "example": largest[0] if largest else None,
        },
        "unresolved_module": len(unresolved),
        "askable_in_words": len(askable),
        "askable_share": round(len(askable) / max(1, len(caps)), 4),
        "described_as": sum(1 for rec in caps.values() if isinstance(rec, dict) and rec.get("described_as")),
        "self_locating": _self_locating(model, caps),
        "with_docstring": len(with_doc),
        "generic_docstrings": generic,
        "distinct_docstrings": len(doc_counts),
        "routing_pool": len(pool),
        "routable_victims": len(eligible),
        "recall_curve": curve,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--sample", type=int, default=200)
    parser.add_argument("--trials", type=int, default=24)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = census(args.root, sample=args.sample, trials=args.trials)
    if args.json:
        print(json.dumps(report, indent=1))
        return 0
    print(f"  {report['clause']}\n")
    print(f"  capabilities declared          : {report['declared_capabilities']}")
    print(f"  distinct implementations       : {report['distinct_implementations']}")
    print(f"  duplicate ids                  : {report['duplicate_capabilities']}"
          f"  ({report['duplicate_share'] * 100:.0f}%)")
    print(f"  largest duplicate group        : {report['largest_duplicate_group']['ids']} ids -> 1 file")
    print(f"  unresolved module              : {report['unresolved_module']}")
    print(f"  askable in words               : {report['askable_in_words']}"
          f"  ({report['askable_share'] * 100:.0f}%)")
    print(f"  carries a description          : {report['described_as']}"
          f"  (found by its own description: {report['self_locating']['found']}"
          f"/{report['self_locating']['n']} = {report['self_locating']['share'] * 100:.1f}%)")
    print(f"  has a docstring                : {report['with_docstring']}"
          f"  (generic: {report['generic_docstrings']}, distinct: {report['distinct_docstrings']})")
    print(f"\n  {'library size':>13s}  {'recall@1':>9s}  {'95% CI':>18s}  n")
    for row in report["recall_curve"]:
        lo, hi = row["ci95"]
        print(f"  {row['library_size']:13d}  {row['recall_at_1']:9.3f}  [{lo:.3f}, {hi:.3f}]  {row['victims']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
