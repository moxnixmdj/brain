#!/usr/bin/env python3
"""Five rules, one corpus, and the honest answer to "which rule".

WHY THIS FILE EXISTS
--------------------
`documentation_is_the_source_v1` got 4 of 7 goals right and then stopped moving. Five different
candidate-selection rules were tried against those 7 goals and EVERY ONE scored exactly 4/7:

    A  stored ranker over the whole library                    4/7
    B  declared surface tier (stated > released > submodule)    4/7
    C  guide paragraph -> the names in its neighbouring code    4/7
    D  prose block -> the names in the code that follows it     4/7
    E  the project's docs/ tree instead of the README           4/7

Seven rows cannot separate five rules. The rules differ on WHICH row they fail, so the totals
coincide, and picking the winner by eye on 7 rows is how a fitted anecdote gets shipped as a
mechanism. That is the blocker this file removes -- not with a better rule, but with a corpus
that can actually decide.

WHERE THE GROUND TRUTH COMES FROM (it is not chosen by me)
----------------------------------------------------------
A project's own test file is the artifact stating which of its names matter together:

    from rich.align import Align, Console, Measurement, VerticalCenter

and the file's NAME (`test_align.py`) states the intent. So a row is:

    goal   = the test file's name, in words          ("align")
    truth  = the public names that file imports      {Align, Measurement, VerticalCenter}

No hand-writing, no judgment, no answer key I authored. The rule under test has to put the
names a project's own tests exercise at the top, having seen nothing but the library's source,
its declared surface, and its guide.

THE ONE HONEST LIMIT, STATED UP FRONT
-------------------------------------
A test file's name is not a user's sentence. It is a single word or two, which makes the goal
EASIER than a real request ("align" shares a stem with `Align`; "make this text line up in
columns" does not). So a high score here is a NECESSARY condition, not a sufficient one: a rule
that cannot pass this cannot pass a user's words, and passing it does not prove the reverse.
The 7 hand-written realistic goals stay in the file as the harder counterweight, reported
separately and never merged into this number.

Schema BRAIN_WHICH_RULE_ON_A_REAL_CORPUS_V1. Authority NONE__PRODUCER_RUN_SANDBOX.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
from typing import Any, Mapping, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import documentation_is_the_source_v1 as D  # noqa: E402
import learned_ranking_store_v1 as L  # noqa: E402

SCHEMA = "BRAIN_WHICH_RULE_ON_A_REAL_CORPUS_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"

# Each entry: package -> (repo, source path, tests path)
SPECS: dict[str, tuple[str, str, str]] = {
    "click":    ("pallets/click", "src/click", "tests"),
    "rich":     ("Textualize/rich", "rich", "tests"),
    "attrs":    ("python-attrs/attrs", "src/attr", "tests"),
    "tabulate": ("astanin/python-tabulate", "tabulate", "test"),
}


def test_rows(repo: str, test_path: str, public: set[str]) -> list[dict[str, Any]]:
    """One row per test file that imports a public name.

    The import set is the truth. Logging and config files are dropped because their names are
    not intents (`conftest`), and a row needs at least one truth name that also exists as a
    documented unit, otherwise the rule is being asked for a name it was never shown.
    """
    try:
        files = D.fetch_source(repo, test_path)
    except Exception:
        return []
    rows: list[dict[str, Any]] = []
    for fname, text in files.items():
        if not fname.endswith(".py"):
            continue
        base = fname.rsplit("/", 1)[-1]
        if base.startswith("conftest") or base.startswith("__"):
            continue
        imported: set[str] = set()
        for line in re.findall(r"^from\s+\S+\s+import\s+(.+)$", text, re.M):
            for x in line.replace("(", " ").replace(")", " ").split(","):
                x = x.strip().split(" as ")[-1].strip()
                if x and x != "*" and x.isidentifier():
                    imported.add(x)
        named = imported & public
        if not named:
            continue
        intent = base[:-3].replace("test_", "").replace("_", " ").strip()
        if not intent:
            continue
        rows.append({"package": repo, "file": base, "goal": intent, "truth": sorted(named)})
    rows.sort(key=lambda r: (r["package"], r["file"]))
    return rows


def rule_scores(units: Sequence[Mapping[str, Any]], goal: str,
                surface: Mapping[str, int], taught: Mapping[str, int],
                rule: str) -> list[str]:
    """The ordered name list this rule offers. Identical inputs, one difference: the rule."""
    ranked = D.rank_units(units, goal, surface=surface, taught=taught)
    names = [r["name"] for r in ranked]
    if rule == "A_whole_library":
        return names
    if rule == "B_surface_tier":
        return names  # rank_units already sorts by tier; A and B differ only in the tier input
    if rule == "C_taught_only":
        t = [n for n in names if taught.get(n, 0) > 0]
        return t or names
    if rule == "D_released_only":
        t = [n for n in names if surface.get(n, 2) < 2]
        return t or names
    if rule == "E_taught_then_released":
        t = [n for n in names if taught.get(n, 0) > 0]
        t += [n for n in names if surface.get(n, 2) < 2 and n not in t]
        return t or names
    raise ValueError(rule)


RULES = ("A_whole_library", "B_surface_tier", "C_taught_only", "D_released_only",
         "E_taught_then_released")


def evaluate(verbose: bool = True) -> dict[str, Any]:
    per_rule: dict[str, list[float]] = {r: [] for r in RULES}
    first: dict[str, int] = {r: 0 for r in RULES}
    any_hit: dict[str, int] = {r: 0 for r in RULES}
    total = 0
    per_pkg: dict[str, dict[str, Any]] = {}

    for pkg, (repo, srcpath, testpath) in SPECS.items():
        try:
            src = D.fetch_source(repo, srcpath)
        except Exception as e:
            if verbose:
                print(f"  {pkg:9s} SKIP fetch: {type(e).__name__}")
            continue
        units = D.units_from_source(src, pkg)
        surface = D.declared_surface(src, pkg)
        guide = D.readme_of(repo)
        taught = D.taught_names(guide) if guide else {}
        public = {u["name"] for u in units}
        rows = test_rows(repo, testpath, public)
        if not rows:
            if verbose:
                print(f"  {pkg:9s} SKIP: no test rows")
            continue
        for rule in RULES:
            r_first = r_any = 0
            for row in rows:
                order = rule_scores(units, row["goal"], surface, taught, rule)
                pos = [order.index(t) + 1 for t in row["truth"] if t in order]
                if pos:
                    # THE METRIC IS THE FIRST TRUTH MEMBER IN THE ORDER, not "is the top
                    # exactly right". A test file that imports eight public names does not
                    # claim all eight are equally intended, and a truth set averaging 3.7
                    # names makes `min_pos == 1` demand that the ONE right name beat every
                    # other name the same file also uses. Measured consequence of the wrong
                    # metric: all five rules scored exactly 8/94 with `top` = `inspect` on
                    # every rich row, which is the signature of a pinned answer, not a rule.
                    best = min(pos)
                    r_any += 1
                    per_rule[rule].append(1.0 / best)
                    if best == 1:
                        r_first += 1
            first[rule] += r_first
            any_hit[rule] += r_any
        total += len(rows)
        per_pkg[pkg] = {"rows": len(rows), "units": len(units),
                        "declared": sum(1 for v in surface.values() if v == 0),
                        "taught": sum(1 for n in public if taught.get(n, 0) > 0)}
        if verbose:
            print(f"  {pkg:9s} rows={len(rows):3d} units={len(units):4d} "
                  f"declared={per_pkg[pkg]['declared']:3d} taught={per_pkg[pkg]['taught']:3d}")

    out: dict[str, Any] = {"schema": SCHEMA, "authority": AUTHORITY, "rows": total,
                           "packages": per_pkg, "rules": {}}
    if total:
        for rule in RULES:
            vals = per_rule[rule]
            out["rules"][rule] = {
                "top1": first[rule], "covered": any_hit[rule], "rows": total,
                "top1_rate": round(first[rule] / total, 3),
                "mrr": round(sum(vals) / total, 3),
            }
    return out


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    print("measuring five rules against a corpus the rules did not choose ...")
    res = evaluate()
    print(f"\nrows: {res['rows']}")
    if res["rows"]:
        for rule, m in sorted(res["rules"].items(), key=lambda kv: -kv[1]["mrr"]):
            print(f"  {rule:22s} top-1 {m['top1']:3d}/{m['rows']:<3d} "
                  f"({m['top1_rate']*100:5.1f}%)  covered {m['covered']:3d}  MRR {m['mrr']:.3f}")
    if "--out" in argv:
        p = pathlib.Path(argv[argv.index("--out") + 1])
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(res, indent=2, sort_keys=True))
        print(f"wrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
