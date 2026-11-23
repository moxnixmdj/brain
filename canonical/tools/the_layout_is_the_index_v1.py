#!/usr/bin/env python3
"""The artifact's module layout is the index; the guide is the key. Measured, not asserted.

WHAT THIS FILE ESTABLISHES, AND WHAT IT REPLACES
------------------------------------------------
`documentation_is_the_source_v1` closed the network half of instant knowledge and then stalled at
4/7 realistic goals, with five candidate-selection rules all scoring 8/94 on the organic corpus.
That result is in `which_rule_on_a_real_corpus_v1`. The five rules shared one assumption:

    the unit of meaning is a NAME, and names are ranked by word overlap with the goal.

Measured, that assumption is false. On 94 rows whose truth was set by the projects' own test
imports, a bag-of-words ranker over names scored **8/94 (8.5%)**, and `inspect` was the top hit
for every rich row. Word overlap between a goal sentence and a docstring is pattern matching.

The artifact states a second index that is not word overlap at all: **its module layout.** A
library that splits `rich/align.py`, `rich/table.py`, `rich/panel.py` is stating that the things
in `align.py` belong together. The project's own test names state the same grouping from the
other side (`test_align.py` imports `Align, Measurement, VerticalCenter`). So:

    goal word  ->  the module whose own name states it  ->  the units in that module

Measured on 94 organic rows: **42/94 (44.7%)**, against 8/94 for every word-overlap rule. A
5.3x difference from removing an assumption, not from adding a weight.

THE LEAKAGE CHECK, WHICH SHRINKS THE RESULT BY 3.7x
---------------------------------------------------
A test file called `test_align.py` importing from `rich/align.py` makes "match the goal word to
the module name" nearly a tautology: the goal IS the module name. So the 94 rows were split by
whether the goal word is also a module name in the library:

    goal word IS a module name       37/60 = 61.7%   <- near-tautological
    goal word is NOT a module name    4/34 = 11.8%   <- the genuine number

**So the honest capability is 11.8%, not 43.6%.** It is above the 8.5% word-overlap baseline on
the same rows, and it is far below anything that would justify calling this solved. The headline
number is reported below only because deleting it would hide the leakage, not because it is the
result. Every plan built on this must use the 11.8%.

WHERE IT FAILS, AND WHY THAT IS RECORDED RATHER THAN PATCHED
------------------------------------------------------------
  rich      56.5%  68 modules, one concept each -- the layout IS the index
  attrs     33.3%  12 modules, mostly one public name per module
  click      0.0%  15 modules, and the public names live in ONE of them (`core.py`)
  tabulate   0.0%   1 module  -- a flat library has no layout to read

So the rule is a CONDITIONAL statement about the artifact, not a universal one: it works when the
library's own organization is a partition of its concepts, and it degrades to nothing when the
library is flat. The 0% rows are not failures to hide; they are the boundary of the mechanism,
and a flat library must fall back to a different index (word overlap, which is what the 8.5%
figure describes). Reporting 44.7% as a headline without this table would be the same class of
error as the earlier "35 was really 36".

WHAT IS COMPUTED
----------------
  * module_of      the dotted name's own parent, from the source tree. No table.
  * module_index   goal words ∩ module tail words, computed per unit set.
  * units_in       the artifact's own members of the winning module.
Nothing stored, nothing fitted, no model call, and the network is the same two hosts as
`documentation_is_the_source_v1`.

Schema BRAIN_THE_LAYOUT_IS_THE_INDEX_V1. Authority NONE__PRODUCER_RUN_SANDBOX.
"""
from __future__ import annotations

import json
import pathlib
import sys
from collections import Counter
from typing import Any, Mapping, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import documentation_is_the_source_v1 as D  # noqa: E402
import learned_ranking_store_v1 as L  # noqa: E402
import which_rule_on_a_real_corpus_v1 as W  # noqa: E402

SCHEMA = "BRAIN_THE_LAYOUT_IS_THE_INDEX_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"


def module_of(dotted: str) -> str:
    """The parent of a dotted name, computed from the name itself."""
    return dotted.rsplit(".", 1)[0] if "." in dotted else dotted


def module_index(units: Sequence[Mapping[str, Any]], goal: str) -> list[str]:
    """Order names by the module whose own name states the goal, best module first.

    A module is scored by how many of the goal's words appear in its tail AND in its full
    dotted path, because `rich.table` and `rich._table` state the same thing to a reader and a
    different thing to a parser. Ties are broken by the module path so the order is total and
    reproducible.
    """
    gw = L.words(goal)
    by_mod: dict[str, list[str]] = {}
    for u in units:
        by_mod.setdefault(module_of(u["dotted"]), []).append(u["name"])
    scored: list[tuple[int, int, str]] = []
    for mod in by_mod:
        tail_words = L.words(mod.rsplit(".", 1)[-1])
        path_words = L.words(mod.replace(".", " "))
        score = 2 * len(gw & tail_words) + len(gw & path_words)
        scored.append((-score, len(mod), mod))
    scored.sort()
    out: list[str] = []
    for _, _n, mod in scored:
        out.extend(sorted(by_mod[mod]))
    return out


def leakage_split() -> dict[str, Any]:
    """The 43.6% split into the part that is a tautology and the part that is capability."""
    taut = taut_hit = other = other_hit = 0
    for pkg, (repo, srcpath, testpath) in W.SPECS.items():
        try:
            src = D.fetch_source(repo, srcpath)
        except Exception:
            continue
        units = D.units_from_source(src, pkg)
        mods = {module_of(u["dotted"]).rsplit(".", 1)[-1] for u in units}
        rows = W.test_rows(repo, testpath, {u["name"] for u in units})
        for row in rows:
            gw = row["goal"].replace(" ", "_")
            is_taut = any(gw == m or gw in m.split("_") for m in mods)
            order = module_index(units, row["goal"])
            pos = [order.index(t) + 1 for t in row["truth"] if t in order]
            first = bool(pos and min(pos) == 1)
            if is_taut:
                taut += 1
                taut_hit += first
            else:
                other += 1
                other_hit += first
    return {
        "tautological": {"n": taut, "top1": taut_hit,
                         "rate": round(taut_hit / max(taut, 1), 3)},
        "genuine": {"n": other, "top1": other_hit,
                    "rate": round(other_hit / max(other, 1), 3)},
    }


def evaluate(verbose: bool = True) -> dict[str, Any]:
    """The same 94 organic rows, scored by the layout rule and by each word-overlap rule."""
    per_pkg: dict[str, dict[str, Any]] = {}
    layout_first = layout_mrr_n = 0
    layout_mrr = 0.0
    overlap_first = 0
    total = 0

    for pkg, (repo, srcpath, testpath) in W.SPECS.items():
        try:
            src = D.fetch_source(repo, srcpath)
        except Exception:
            continue
        units = D.units_from_source(src, pkg)
        surface = D.declared_surface(src, pkg)
        guide = D.readme_of(repo)
        taught = D.taught_names(guide) if guide else {}
        public = {u["name"] for u in units}
        rows = W.test_rows(repo, testpath, public)
        if not rows:
            continue
        mods = Counter(module_of(u["dotted"]) for u in units)
        hit_l = hit_o = 0
        for row in rows:
            order = module_index(units, row["goal"])
            pos = [order.index(t) + 1 for t in row["truth"] if t in order]
            if pos:
                layout_mrr_n += 1
                layout_mrr += 1.0 / min(pos)
                if min(pos) == 1:
                    hit_l += 1
                    layout_first += 1
            oorder = W.rule_scores(units, row["goal"], surface, taught, "A_whole_library")
            opos = [oorder.index(t) + 1 for t in row["truth"] if t in oorder]
            if opos and min(opos) == 1:
                hit_o += 1
                overlap_first += 1
        total += len(rows)
        per_pkg[pkg] = {"rows": len(rows), "units": len(units), "modules": len(mods),
                        "layout_top1": hit_l, "overlap_top1": hit_o,
                        "layout_rate": round(hit_l / len(rows), 3),
                        "flat": len(mods) <= 1}
        if verbose:
            print(f"  {pkg:9s} rows={len(rows):3d} modules={len(mods):3d} "
                  f"layout={hit_l:3d} ({per_pkg[pkg]['layout_rate']*100:5.1f}%)  "
                  f"overlap={hit_o:3d}  {'FLAT' if per_pkg[pkg]['flat'] else ''}")

    return {
        "leakage": leakage_split(),
        "schema": SCHEMA, "authority": AUTHORITY, "rows": total,
        "packages": per_pkg,
        "layout": {"top1": layout_first, "rate": round(layout_first / max(total, 1), 3),
                   "mrr": round(layout_mrr / max(layout_mrr_n, 1), 3)},
        "overlap": {"top1": overlap_first, "rate": round(overlap_first / max(total, 1), 3)},
        "ratio": round((layout_first / max(total, 1)) / max(overlap_first / max(total, 1), 1e-9), 2),
    }


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    print("the same organic rows, scored by layout instead of word overlap ...")
    res = evaluate()
    lk = res["leakage"]
    print(f"  leakage split: tautological {lk['tautological']['top1']}/{lk['tautological']['n']} "
          f"({lk['tautological']['rate']*100:.1f}%)   GENUINE "
          f"{lk['genuine']['top1']}/{lk['genuine']['n']} ({lk['genuine']['rate']*100:.1f}%)")
    print(f"\nrows {res['rows']}  layout {res['layout']['top1']} "
          f"({res['layout']['rate']*100:.1f}%)  overlap {res['overlap']['top1']} "
          f"({res['overlap']['rate']*100:.1f}%)  MRR {res['layout']['mrr']:.3f}  "
          f"ratio {res['ratio']}x")
    if "--out" in argv:
        p = pathlib.Path(argv[argv.index("--out") + 1])
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(res, indent=2, sort_keys=True))
        print(f"wrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
