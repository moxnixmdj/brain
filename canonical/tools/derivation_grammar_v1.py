#!/usr/bin/env python3
"""A hypothesis space built from primitives, searched under falsification, and pruned by
what has actually paid off.

What was still mine
-------------------
`derivation_inference_v1` inferred which derivation explains each recorded field, and that was
a real inference: the data chose. But the eight things it chose *between* were written by a
person, one `Candidate(...)` at a time. A search over a list I typed has a ceiling that is my
imagination, and `widen()` did not fix it -- its "compositions" were three more functions I
typed in `composite_candidates`.

This module replaces the list with a **grammar**:

    recipe = transform( pre( elements ) )

    elements   what the record lets you read   file bytes | committed bytes | path text |
                                               the record's path list | the record's value list
    pre        how you arrange them            raw | sorted, newline-joined | sorted, comma |
                                               deduplicated, sorted, newline-joined
    transform  what you compute                length | sha1 | sha256 | git blob

The system does not choose among eight. It enumerates the cross product, which is a number
nobody typed, and searches it. The count is reported.

Three things this adds that the previous layer could not do
-----------------------------------------------------------
1. GENERATE, don't list.        `recipes()` returns the cross product; the size is measured,
                                not asserted, and it is much larger than the hand-written list.
2. PROVE NON-DERIVABILITY.      The 920 unexplained fields were previously all "ignorance",
                                which conflates "I have not found the function" with "there is
                                no function". Some of them are write-time choices -- an index,
                                a counter, a timestamp, a score. This module looks at the
                                VALUES ALONE and can prove that no deterministic function of
                                the record can produce them (e.g. values that equal their own
                                position, values constant across different inputs). Those are
                                then removed from the ignorance list with evidence, which is a
                                shrinking of what the system does not know that is not achieved
                                by learning more -- it is achieved by understanding the
                                question better.
3. LEARN WHAT TO TRY FIRST.     Every primitive carries a yield: how many fields it has
                                explained once a candidate was confirmed on withheld records.
                                Search order is by yield, so a run changes the next run's
                                behaviour. That is measured as cost (recipes tried), never as a
                                solve rate.

Every accepted recipe is persisted as a STRING (`"sha1|file|sortnl"`) rather than a closure, so
a second process -- the maintenance loop -- can rebuild it and use it as a live predicate. A
learning that cannot be written down cannot outlive the process that had it, which is the exact
failure `CREATURE_BEHAVIOR_MAP_V1.md` records five times.

Usage::

    python3 canonical/tools/derivation_grammar_v1.py              # measure
    python3 canonical/tools/derivation_grammar_v1.py --write      # write artifact + yields
    python3 canonical/tools/derivation_grammar_v1.py --search     # search the unexplained
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.tools import derivation_inference_v1 as base  # noqa: E402

SCHEMA = "PROJECT_BRAIN_DERIVATION_GRAMMAR_V1"
ARTIFACT = "canonical/verification/DERIVATION_GRAMMAR_V1.json"
YIELDS_ARTIFACT = "canonical/verification/DERIVATION_YIELDS_V1.json"

# --------------------------------------------------------------------------- the grammar
ELEMENTS = ("file", "head", "path", "pathlist", "valuelist")
# An arrangement is only meaningful over several elements. Sorting, splitting and
# deduplicating a single element is the identity, so `len|file|sortnl` computes exactly what
# `len|file|raw` computes -- it is not a second hypothesis, it is the same one wearing a
# longer name. Generating those pairs wastes search and, worse, lets a duplicate "win" a field
# and be credited in the yield table under a name that learns nothing. Measured 2026-11-04:
# 36 of the 80 cross-product recipes were such duplicates.
ARRANGEABLE = {"pathlist", "valuelist"}
PRES = ("raw", "sortnl", "sortcomma", "dedup_sortnl")
TRANSFORMS = ("len", "sha1", "sha256", "gitblob")
# A transform can only produce one kind of value; searching a sha256 recipe against an integer
# field is not more thorough, it is just slower. The value class is a fact about the data and
# constrains the space for free.
CLASS_OF_TRANSFORM = {"sha1": "hex40", "gitblob": "hex40", "sha256": "hex64", "len": "int"}

# Recipes that read a structure rather than bytes. These are the counts a system reaches for
# when a field looks like a total, and they are generated, not listed per field.
COUNT_RECIPES = ("count|pathlist|raw", "count|valuelist|raw",
                 "countdistinct|valuelist|raw", "countdistinct|pathlist|raw")
COUNT_CLASS = {"count": "int", "countdistinct": "int"}


def recipes(value_class: str | None = None) -> list[str]:
    """The generated space. Deterministic order, so a rerun cannot change the headline."""
    out: list[str] = []
    for transform in TRANSFORMS:
        for elements in ELEMENTS:
            for pre in PRES:
                if elements not in ARRANGEABLE and pre != "raw":
                    continue                  # identity, not a hypothesis
                out.append(f"{transform}|{elements}|{pre}")
    out.extend(COUNT_RECIPES)
    if value_class in {"hex40", "hex64", "int"}:
        out = [r for r in out if _class_of(r) == value_class]
    return out


def _class_of(recipe: str) -> str | None:
    transform = recipe.split("|", 1)[0]
    return CLASS_OF_TRANSFORM.get(transform) or COUNT_CLASS.get(transform)


def space_size() -> dict:
    """The number nobody typed: how many derivations the primitives admit."""
    naive = len(ELEMENTS) * len(PRES) * len(TRANSFORMS)
    distinct = (len(ARRANGEABLE) * len(PRES) * len(TRANSFORMS)
                + (len(ELEMENTS) - len(ARRANGEABLE)) * len(TRANSFORMS))
    return {
        "elements": len(ELEMENTS),
        "pres": len(PRES),
        "transforms": len(TRANSFORMS),
        "cross_product_naive": naive,
        "duplicates_removed": naive - distinct,
        "cross_product": distinct,
        "structural_counts": len(COUNT_RECIPES),
        "generated": len(recipes()),
        "by_class": dict(Counter(_class_of(r) for r in recipes())),
        "hand_written_in_previous_layer": len(base.SPACE),
    }


# --------------------------------------------------------------------------- derivation
def _elements_of(recipe: str, site: Any, tree: Any) -> Any:
    _, which, _ = recipe.split("|")
    path = base._path_in(site.record)
    if which == "file":
        if not path:
            return base._MISS
        data = tree.read(path)
        return base._MISS if data is None else [data]
    if which == "head":
        if not path:
            return base._MISS
        data = tree.at_ref(path)
        return base._MISS if data is None else [data]
    if which == "path":
        return base._MISS if not path else [path.encode("utf-8")]
    if which == "pathlist":
        items = sorted({str(v) for v in site.record.values()
                        if isinstance(v, str) and ("/" in v or v.endswith((".py", ".json",
                                                                           ".md", ".txt")))})
        return [i.encode("utf-8") for i in items] or base._MISS
    if which == "valuelist":
        for value in site.record.values():
            if isinstance(value, list) and value:
                return [str(v).encode("utf-8") for v in value]
        return base._MISS
    return base._MISS


def _arrange(recipe: str, items: Any) -> bytes | None:
    if items is base._MISS or not items:
        return None
    _, _, pre = recipe.split("|")
    if pre == "raw":
        return items[0] if len(items) == 1 else b"".join(items)
    if pre == "sortnl":
        return b"\n".join(sorted(items))
    if pre == "sortcomma":
        return b",".join(sorted(items))
    if pre == "dedup_sortnl":
        return b"\n".join(sorted(set(items)))
    return None


def derive(recipe: str, site: Any, tree: Any) -> Any:
    """Evaluate a recipe against a record. A string in, a value out -- that is the point."""
    try:
        transform = recipe.split("|", 1)[0]
        items = _elements_of(recipe, site, tree)
        if transform == "count":
            return base._MISS if items is base._MISS else len(items)
        if transform == "countdistinct":
            return base._MISS if items is base._MISS else len(set(items))
        blob = _arrange(recipe, items)
        if blob is None:
            return base._MISS
        if transform == "len":
            return len(blob)
        if transform == "sha1":
            return base.sha1_bytes(blob)
        if transform == "sha256":
            import hashlib
            return hashlib.sha256(blob).hexdigest()
        if transform == "gitblob":
            return base.git_blob_sha(blob)
    except (KeyError, TypeError, ValueError, OSError):
        return base._MISS
    return base._MISS


# --------------------------------------------------------------------------- value shape
_TREE_FOR_PROBE = None


def probe_values(sites: list[Any], tree: Any = None) -> dict:
    """What the VALUES alone can tell you, before any derivation is tried.

    This is the layer that can prove a field is not a function of anything. It costs one pass
    over the values and it removes candidates by fact rather than by preference.
    """
    global _TREE_FOR_PROBE
    if tree is not None:
        _TREE_FOR_PROBE = tree
    vals = [s.value for s in sites]
    if not vals:
        return {"records": 0}
    ints = [v for v in vals if isinstance(v, int) and not isinstance(v, bool)]
    facts: dict[str, Any] = {
        "records": len(vals),
        "distinct": len(set(vals)),
        "all_equal": len(set(vals)) == 1,
        "all_zero": all(v == 0 for v in vals),
        "is_int_class": len(ints) == len(vals),
    }
    if facts["is_int_class"] and len(ints) == len(vals):
        facts["equals_own_position"] = ints == list(range(len(ints)))
        strictly_up = all(b > a for a, b in zip(ints, ints[1:])) if len(ints) > 1 else False
        facts["strictly_increasing"] = strictly_up
        facts["all_small_nonnegative"] = all(0 <= v <= 64 for v in ints)
        facts["max_to_median_ratio"] = (float(max(ints)) / max(1.0, float(sorted(ints)[
            len(ints) // 2]))) if ints else None
    # Same input, different answers => no deterministic function of the record exists.
    #
    # The input must include WHEN the record was written. Measured 2026-11-04: without it this
    # test "proved" 67 fields nondeterministic, starting with `git_blob_sha` -- a field that
    # demonstrably IS a blob id. The apparent contradiction was two archive records naming the
    # same file at different commits: same path, same siblings, different sha, because the file
    # had changed. The commit is part of the input, and leaving it out manufactured 67 proofs.
    tree = _TREE_FOR_PROBE
    by_input: dict[tuple, set] = defaultdict(set)
    for site in sites:
        path = base._path_in(site.record)
        siblings = tuple(sorted((k, str(v)) for k, v in site.record.items()
                                if k != site.field and not isinstance(v, (dict, list))))
        when = tree.document_commit(site.doc) if tree is not None else None
        by_input[(path, siblings, when)].add(site.value)
    facts["identical_inputs_with_different_values"] = sum(
        1 for v in by_input.values() if len(v) > 1)
    return facts


# What a failed search actually licenses you to conclude. Three of these are facts about the
# values; one is a fact about this instrument. Mixing them is how a system flatters itself, so
# they are separate keys and are always reported apart.
TIERS = {
    "INPUTS_NOT_RECORDED": (
        "FACT_ABOUT_DATA",
        "records with identical recorded inputs carry different values, so the record omits an "
        "input the value depends on -- a commit, a timestamp, an ordering. This is evidence the "
        "record is under-specified, NOT a proof that no function exists. Measured 2026-11-04: "
        "`git_blob_sha` landed here, and the collision showed why -- five action intents each "
        "quoting the same path's blob at five different commits, none of which the receipt "
        "names",
    ),
    "UNDECIDABLE_FROM_CORPUS": (
        "FACT_ABOUT_DATA",
        "constant across every record, so this corpus cannot distinguish it from a literal",
    ),
    "EVIDENCE_OF_WRITE_TIME_CHOICE": (
        "FACT_ABOUT_DATA",
        "equals its own position, or increases strictly with document order -- consistent with "
        "an index or a counter, which no derivation of the record's content produces",
    ),
    "NOT_FOUND_IN_GENERATED_SPACE": (
        "FACT_ABOUT_INSTRUMENT",
        "no recipe in the generated space bound this field. This says nothing about the data",
    ),
}


SHORT_REASON = {
    "INPUTS_NOT_RECORDED": "identical recorded inputs, different values -- the record omits "
                           "an input the value depends on",
    "UNDECIDABLE_FROM_CORPUS": "constant across every record, so this corpus cannot tell it "
                               "from a literal",
    "EVIDENCE_OF_WRITE_TIME_CHOICE": "tracks position or order, which no content derivation "
                                     "produces",
    "NOT_FOUND_IN_GENERATED_SPACE": "no generated recipe bound it -- says nothing about the "
                                    "data",
}


def tier_of(verdict: str | None) -> str | None:
    return TIERS.get(verdict or "", (None, None))[0]


def classify_non_derivable(facts: Mapping[str, Any], *, searched: bool) -> str | None:
    """Turn value-shape facts into an evidence-backed verdict, or None if still unknown.

    The order matters: a proof of nondeterminism beats a suspicion of index, and both beat
    "we exhausted the space", because the last one is a statement about us, not about the data.
    """
    if facts.get("records", 0) < base.MIN_SUPPORT:
        return None
    if facts.get("identical_inputs_with_different_values"):
        return "INPUTS_NOT_RECORDED"
    if facts.get("all_equal"):
        return "UNDECIDABLE_FROM_CORPUS"
    if facts.get("equals_own_position") or facts.get("strictly_increasing"):
        return "EVIDENCE_OF_WRITE_TIME_CHOICE"
    if searched:
        return "NOT_FOUND_IN_GENERATED_SPACE"
    return None


# --------------------------------------------------------------------------- yields
def load_yields(path: str | Path | None = None) -> dict:
    path = Path(path) if path else ROOT / YIELDS_ARTIFACT
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
    return {"primitives": {}, "runs": 0}


def save_yields(doc: dict, path: str | Path | None = None) -> None:
    path = Path(path) if path else ROOT / YIELDS_ARTIFACT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def _primitives_of(recipe: str) -> list[str]:
    parts = recipe.split("|")
    return [f"transform:{parts[0]}", f"elements:{parts[1]}", f"pre:{parts[2]}"]


def order_recipes(candidates: list[str], yields: Mapping[str, Any]) -> list[str]:
    """Try first what has explained something before. This is the part that changes behaviour
    between runs, and it is measured as recipes tried, never as a success rate."""
    table = (yields or {}).get("primitives", {})

    def score(recipe: str) -> tuple:
        total = sum(int(table.get(p, {}).get("confirmed", 0)) for p in _primitives_of(recipe))
        return (-total, recipe)

    return sorted(candidates, key=score)


def credit(yields: dict, recipe: str) -> None:
    table = yields.setdefault("primitives", {})
    for primitive in _primitives_of(recipe):
        row = table.setdefault(primitive, {"tried": 0, "confirmed": 0})
        row["tried"] += 1
        row["confirmed"] += 1


# --------------------------------------------------------------------------- search
MAX_SITES_PER_FIELD = 400
# A recipe that computes for 12% of a field and is right about all of it has explained
# nothing. Measured 2026-11-04: `countdistinct|pathlist|raw` "bound" a 396-record field at
# 100% by computing on 47 records and being skipped on the other 349. Coverage is not a
# tie-breaker here; it is a precondition.
COVERAGE_MIN = base.COVERAGE_MIN      # bounded so the search terminates on a 368k-record corpus


def _agreement(recipe: str, sites: list[Any], tree: Any) -> tuple[int, int, int]:
    """(agreements, computed, records). The third number is the one that was missing."""
    ok = computed = 0
    distinct = set()
    for site in sites:
        derived = derive(recipe, site, tree)
        verdict = base._agrees(derived, site.value)
        if verdict is None:
            continue
        computed += 1
        distinct.add(derived)
        ok += 1 if verdict else 0
    return ok, computed, len(sites) if sites else 0


def search_field(key: str, sites: list[Any], tree: Any, yields: dict,
                 *, bind: float = base.BIND_THRESHOLD, sample: int = MAX_SITES_PER_FIELD):
    """Find a generated recipe that binds this field, and prove it on records it never saw.

    Falsification, not enthusiasm: agreement on the fitting half is not evidence; the withheld
    half is. A recipe that wins on the fit and loses on the holdout is reported as rejected,
    which is the only reason to have a holdout at all.
    """
    cls = key.split("|", 1)[1]
    capped = sites[:sample]
    facts = probe_values(capped, tree)
    verdict = classify_non_derivable(facts, searched=False)
    if verdict in TIERS:
        return {"field": key, "outcome": "NOT_LEARNED", "verdict": verdict,
                "why": TIERS[verdict][1], "tier": TIERS[verdict][0],
                "proven": tier_of(verdict) == "FACT_ABOUT_DATA", "facts": facts, "tried": 0}

    train, holdout = base._split(capped)
    tried = 0
    rejected = []
    for recipe in order_recipes(recipes(cls), yields):
        tried += 1
        ok, computed, total = _agreement(recipe, train, tree)
        if computed < base.MIN_SUPPORT or not total:
            continue
        coverage = computed / total
        if coverage < COVERAGE_MIN:
            rejected.append({"recipe": recipe, "reason": "LOW_COVERAGE",
                             "coverage": round(coverage, 4)})
            continue
        if ok / computed < bind:
            continue
        if _is_constant_predictor(recipe, train, tree):
            rejected.append({"recipe": recipe, "reason": "CONSTANT_PREDICTOR",
                             "coverage": round(coverage, 4)})
            continue
        hok, hcomputed, htotal = _agreement(recipe, holdout, tree)
        if not htotal or hcomputed / htotal < COVERAGE_MIN:
            continue
        if hok / hcomputed < bind:
            rejected.append({"recipe": recipe, "train": round(ok / computed, 4),
                             "holdout": round(hok / hcomputed, 4)})
            continue
        return {"field": key, "outcome": "LEARNED", "recipe": recipe,
                "train": round(ok / computed, 4), "holdout": round(hok / hcomputed, 4),
                "coverage": round(coverage, 4),
                "records": len(capped), "tried": tried,
                "already_in_previous_space": recipe in _PREVIOUS_RECIPES, "facts": facts}
    final = classify_non_derivable(facts, searched=True)
    return {"field": key, "outcome": "NOT_LEARNED", "verdict": final,
            "why": TIERS.get(final or "", (None, "no recipe bound this field"))[1],
            "tier": tier_of(final),
            "proven": tier_of(final) == "FACT_ABOUT_DATA",
            "tried": tried, "rejected_on_holdout": rejected[:5], "facts": facts}


# Which of the previous layer's eight derivations this grammar can express. The grammar is
# NOT a superset: it has no way to select "the commit that last wrote this record", so the
# record-commit derivation the previous layer tested is unreachable here. Saying so is cheaper
# than pretending the new space contains the old one.
PREVIOUS_COVERAGE = {
    "git_blob_of_referenced_file": "gitblob|file|raw",
    "git_blob_at_head": "gitblob|head|raw",
    "git_blob_at_record_commit": None,
    "sha1_of_referenced_file": "sha1|file|raw",
    "sha256_of_referenced_file": "sha256|file|raw",
    "size_of_referenced_file": "len|file|raw",
    "sha1_of_path_string": "sha1|path|raw",
    "length_of_sibling_list": None,
}

def _is_constant_predictor(recipe: str, sites: list[Any], tree: Any) -> bool:
    """A derivation that yields one value for every record explains nothing about any of them.

    `countdistinct|pathlist|raw` returns 1 for a record naming a single file, which matched a
    field whose recorded value was usually 1. That is a coincidence wearing a recipe, and the
    holdout would not have caught it because the coincidence holds on both halves.
    """
    seen = {d for d in (derive(recipe, s, tree) for s in sites) if d is not base._MISS}
    return len(seen) <= 1


# The recipes the previous layer could express, so "learned" means "not in the old list".
_PREVIOUS_RECIPES = {
    "sha1|file|raw", "gitblob|file|raw", "gitblob|head|raw", "sha256|file|raw",
    "len|file|raw", "sha1|path|raw",
}


# --------------------------------------------------------------------------- measure
def measure(*, search: bool = True, limit_files: int | None = None) -> dict:
    base.reset_cache()
    tree = base.Tree()
    sites = base.corpus(limit_files=limit_files)
    fields = base.attribute(sites, tree)
    yields = load_yields()

    explained_by_old = {k for k, v in fields.items() if v["state"] == "ATTRIBUTED"}
    unexplained = [k for k, v in fields.items()
                   if v["state"] in {"UNEXPLAINED", "UNDERDETERMINED"}
                   and v["records"] >= base.MIN_SUPPORT]
    unexplained.sort(key=lambda k: -fields[k]["records"])

    by_field: dict[str, list[Any]] = defaultdict(list)
    for site in sites:
        by_field[site.field_key].append(site)

    learned, proven, not_found = [], [], []
    total_tried = 0
    if search:
        for key in unexplained:
            got = search_field(key, by_field[key], tree, yields)
            total_tried += got.get("tried", 0)
            if got["outcome"] == "LEARNED":
                learned.append(got)
                credit(yields, got["recipe"])
            elif got.get("proven"):
                proven.append(got)
            else:
                not_found.append(got)

    yields["runs"] = int(yields.get("runs", 0)) + 1
    save_yields(yields)

    states = Counter(v["state"] for v in fields.values())
    accounted = (len(explained_by_old) + len(learned) + len(proven) + len(not_found)
                 + states.get("INSUFFICIENT_SUPPORT", 0) + states.get("LOW_COVERAGE", 0))
    verdicts = Counter(row["verdict"] for row in proven)
    not_found_verdicts = Counter(row["verdict"] for row in not_found)
    new_recipes = [r for r in learned if not r.get("already_in_previous_space")]
    return {
        "schema": SCHEMA,
        "authority": "NO_CAPABILITY_CREDIT_INFERENCE_MEASUREMENT_ONLY",
        "instrument": "GENERATED_HYPOTHESIS_SPACE_SEARCHED_UNDER_FALSIFICATION",
        "space": space_size(),
        "corpus": {"records": len(sites), "documents": len({s.doc for s in sites}),
                   "fields": len(fields)},
        "before": {
            "fields_attributed": len(explained_by_old),
            "fields_unexplained": len(unexplained),
        },
        "search": {
            "fields_searched": len(unexplained) if search else 0,
            "recipes_tried": total_tried,
            "learned": len(learned),
            "learned_with_a_recipe_the_old_list_could_not_express": len(new_recipes),
            "not_a_function_of_the_record": len(proven),
            "not_found_in_space": len(not_found),
            "verdicts_about_the_data": dict(verdicts),
            "verdicts_about_the_instrument": dict(not_found_verdicts),
        },
        "after": {
            "fields_attributed": len(explained_by_old) + len(learned),
            "fields_whose_values_refuse_a_content_derivation": len(proven),
            "fields_still_unknown": (len(not_found) + states.get("INSUFFICIENT_SUPPORT", 0)
                                     + states.get("LOW_COVERAGE", 0)),
            "breakdown": {
                "explained": len(explained_by_old) + len(learned),
                "values_refuse_derivation": len(proven),
                "not_found_in_space": len(not_found),
                "insufficient_support": states.get("INSUFFICIENT_SUPPORT", 0),
                "low_coverage": states.get("LOW_COVERAGE", 0),
                "total_fields": len(fields),
                "accounted": accounted,
                "closes": accounted == len(fields),
            },
        },
        "learned_examples": sorted(learned, key=lambda r: -r["records"])[:12],
        "non_derivable_examples": [
            {"field": r["field"], "verdict": r["verdict"], "tier": r.get("tier"),
             "why": SHORT_REASON.get(r["verdict"], r["why"]),
             "records": r["facts"].get("records")}
            for r in sorted(proven, key=lambda r: -(r["facts"].get("records") or 0))[:12]
        ],
        "not_found_examples": [
            {"field": r["field"], "records": r["facts"].get("records"),
             "recipes_tried": r.get("tried")}
            for r in sorted(not_found, key=lambda r: -(r["facts"].get("records") or 0))[:8]
        ],
        "yield_primitives": dict(sorted(
            ((k, v) for k, v in yields.get("primitives", {}).items()),
            key=lambda kv: -kv[1].get("confirmed", 0))),
        "rejected_examples": [r for row in not_found
                              for r in (row.get("rejected_on_holdout") or [])][:8],
        "tiers": {k: v[0] for k, v in TIERS.items()},
        "non_claims": [
            "NO_CAPABILITY_CREDIT_A_RECIPE_IS_NOT_A_CAPABILITY",
            "FACTS_ABOUT_THE_DATA_AND_FACTS_ABOUT_THE_INSTRUMENT_ARE_REPORTED_APART",
            "THE_PRIMITIVES_ARE_SUPPLIED_THE_COMPOSITIONS_AND_THE_SEARCH_ARE_NOT",
            "PROVEN_NON_DERIVABLE_IS_A_STATEMENT_ABOUT_THE_VALUES_NOT_ABOUT_US",
            "NOT_DERIVABLE_CANDIDATE_IS_A_STATEMENT_ABOUT_US_AND_IS_LABELLED_AS_ONE",
        ],
    }


def main(argv: list[str]) -> int:
    report = measure(search="--no-search" not in argv,
                     limit_files=int(argv[argv.index("--limit") + 1])
                     if "--limit" in argv else None)
    space = report["space"]
    print("derivation grammar  (a space nobody listed)")
    print(f"  primitives                : {space['elements']} elements x {space['pres']} <          "
          f"arrangements x {space['transforms']} transforms")
    print(f"  cross product             : {space['cross_product']}")
    print(f"  generated derivations     : {space['generated']}  "
          f"(previous layer could express {space['hand_written_in_previous_layer']})")
    print(f"  by value class            : {space['by_class']}")
    covered = sum(1 for v in PREVIOUS_COVERAGE.values() if v)
    print(f"  covers previous layer     : {covered} of {len(PREVIOUS_COVERAGE)} derivations "
          f"(cannot express the record-commit selector)")
    print(f"  corpus                    : {report['corpus']['records']} records / "
          f"{report['corpus']['documents']} documents / {report['corpus']['fields']} fields")
    before, s, after = report["before"], report["search"], report["after"]
    print()
    print(f"  before : {before['fields_attributed']} fields explained, "
          f"{before['fields_unexplained']} unexplained")
    print(f"  search : {s['fields_searched']} fields, {s['recipes_tried']} recipes tried")
    print(f"           learned {s['learned']}  "
          f"(of which {s['learned_with_a_recipe_the_old_list_could_not_express']} "
          f"needed a recipe the old list could not express)")
    print(f"           values refuse a content derivation {s['not_a_function_of_the_record']}"
          f"   {s['verdicts_about_the_data']}")
    print(f"           not found in the space {s['not_found_in_space']}  "
          f"(our limit, NOT counted as non-derivability)")
    b = after["breakdown"]
    print(f"  accounting                 : {b['accounted']} of {b['total_fields']} fields "
          f"({b['low_coverage']} low-coverage, {b['insufficient_support']} too few records)"
          f"  closes={b['closes']}")
    print(f"  after  : {after['fields_attributed']} explained, "
          f"{after['fields_whose_values_refuse_a_content_derivation']} whose values refuse a "
          f"content derivation, {after['fields_still_unknown']} still unknown")
    print()
    print("  learned recipes (new ones marked *):")
    for row in report["learned_examples"][:8]:
        mark = " " if row.get("already_in_previous_space") else "*"
        print(f"   {mark} {row['recipe']:28s} {row['records']:5d} rec "
              f"train {row['train']} holdout {row['holdout']}  {row['field'][:44]}")
    print("  what the values themselves settle:")
    for row in report["non_derivable_examples"][:8]:
        print(f"    {row['verdict']:30s} {str(row['records']):>5s} rec  {row['field'][:40]}")
        print(f"      {row['why']}")
    top = list(report["yield_primitives"].items())[:4]
    if top:
        print(f"  primitives that have paid off (learned order for next run): {top}")
    if "--write" in argv:
        out = ROOT / ARTIFACT
        out.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(f"  written: {ARTIFACT}")
    print()
    print("  Note: a recipe that reproduces a number is not capability. The primitives are")
    print("  still supplied by a person; what was generated is every composition of them.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
