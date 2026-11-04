#!/usr/bin/env python3
"""Which declared effects can a sentence actually reach?

Why this exists
---------------
The registry declares 141 capabilities and 259 distinct effects. Nothing in the tree says how
many of them a real sentence can *bind*, and the one figure that was quoted -- "443 rows, 11
ever reached" -- is from a superseded document and does not match the current tree at all.

A lesson learned by any other mechanism lives INSIDE a registry row. If the door does not route
a sentence to that row, the lesson is never consulted, however many times it was taught. Reach
is therefore a hard ceiling on every learning gain measured elsewhere in this repository, which
makes it the cheapest thing worth measuring and the most expensive thing to keep guessing.

What is measured, and what this is NOT
-------------------------------------
Each capability is addressed **three ways**, because the first two attempts at this census
were each wrong in a way the next one exposed:

  DECLARED_VOCABULARY  a bag of the capability's own declared keywords and effects
  NATURAL              a plain sentence built from its id and declared words
  NATURAL_WITH_INPUT   the same sentence naming a real path in this repository

The third exists because the second produced `GOAL_INPUT_BINDING_REQUIRED` for 133 of 141
capabilities. That error does not mean "unreachable"; it means the capability's declared
template demands inputs the sentence did not supply. Reporting those as unreachable would have
been the same error as reporting a test suite that never ran as a passing one.

It also produced **exactly the same result as NATURAL** -- 8 self-reached, 133 unreached, the
same rows -- which is itself the finding: the blocker is not the absence of a path token, it is
that these templates demand *role-shaped* inputs (`op`, `repo_root`, `rev`, `staged`, ...) that
no prose sentence names. `git.repository.operate.v1`, for instance, declares nine of them.

Measured 2026-11-02 on the same rows: `python.source.symbols.index.ast` was UNREACHED by its
declared vocabulary and SELF-REACHED by "Index the symbols in every python source file in
src"; `python.refactor.rename_symbol` was the reverse. So neither address is an upper bound,
neither is a lower bound, and quoting either alone would misstate the thing being measured.

Reach here is therefore **"self-reached by at least one of three templated addresses"**, and
that is the exact claim -- no more. A row recorded UNREACHED is *not* proven unreachable: a
real user sentence may bind it, and two of the three addresses presented here are crude
templates. What the UNREACHED rows do carry is a named cause, and the dominant cause is a
declaration fact rather than a phrasing fact:

    COMPILER_RAISED:GOAL_INPUT_BINDING_REQUIRED   the template demands inputs the sentence
                                                  never states -- measured 38 of 141

That is the same defect class an earlier action intent fixed for the test-scaffold row
("dropped as unbindable for five inputs no sentence states"), and it is actionable in a way
that "reach is low" never was.

What WOULD settle reach is a corpus of real user sentences rather than templates. This tool
does not have one, and does not pretend that its templates are one.

Three outcomes are recorded per address:

  SELF_REACHED     the sentence routes to the capability that declared it
  REACHED_BY_ANOTHER  the sentence routes somewhere else (a collision, not a gap)
  UNREACHED        the sentence routes nowhere -- no selection, or a refused compilation

The distinction matters because the three have different fixes. A collision is a scoring
problem; UNREACHED is a declaration problem; and a refusal that names its own cause is a
capability gap the machine has already diagnosed for us.

This census cannot run a capability and does not claim any capability worked. It measures
ROUTING only, and reports zero credit of every other kind.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "PROJECT_BRAIN_ROUTE_REACH_CENSUS_V1"

# This tool measures a DIAGNOSTIC, not a reach denominator. Measured 2026-11-02: the same
# capability can be unreached by all three templated addresses and reachable by one ordinary
# English sentence, and a different capability can be the other way round. A fraction computed
# from templates is therefore not a fraction of anything a user experiences, and it may never
# be quoted as "N of M capabilities are reachable".
NO_DENOMINATOR_CLAIM = (
    "TEMPLATED_ADDRESSES_ONLY__NOT_A_REACH_DENOMINATOR__UNREACHED_DOES_NOT_MEAN_UNREACHABLE")

SELF_REACHED = "SELF_REACHED"
REACHED_BY_ANOTHER = "REACHED_BY_ANOTHER"
UNREACHED = "UNREACHED"


def load_registry() -> dict:
    return json.loads(
        (ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text()
    )["capabilities"]


def declared_effects(registry: dict) -> dict[str, list[str]]:
    effects: dict[str, list[str]] = {}
    for cid, entry in registry.items():
        for effect in (entry.get("provides") or []):
            effects.setdefault(str(effect), []).append(cid)
    return effects


def natural_for(capability_id: str, entry: dict) -> str:
    """A plain sentence, built from the id and the declared words.

    Deliberately naive: it is a template, not a language model, and it says so. Its purpose is
    to be a SECOND address so that the census does not rest on one phrasing.
    """
    words = [w for w in str(capability_id).replace(".", " ").replace("_", " ").split()
             if len(w) > 1]
    seen: set[str] = set()
    ordered: list[str] = []
    for word in words:
        low = word.lower()
        if low not in seen:
            seen.add(low)
            ordered.append(low)
    extra = [str(k).lower() for k in (entry.get("keywords") or [])][:3]
    return "Please " + " ".join(ordered + extra)


def natural_with_input(capability_id: str, entry: dict, root: Path) -> str:
    """The natural sentence plus a real path, because most capabilities operate on files."""
    candidates = ["canonical", "canonical/runtime", "README.md"]
    present = [c for c in candidates if (root / c).exists()]
    target = present[0] if present else "."
    return natural_for(capability_id, entry) + f" in {target}"


def sentence_for(entry: dict) -> str:
    """The most generous address a capability can have: its own declared words."""
    words: list[str] = []
    for key in ("keywords", "provides"):
        for value in (entry.get(key) or []):
            words.extend(str(value).replace(".", " ").replace("_", " ").split())
    seen: set[str] = set()
    ordered: list[str] = []
    for word in words:
        low = word.lower()
        if len(low) < 2 or low in seen:
            continue
        seen.add(low)
        ordered.append(low)
    return " ".join(ordered)


def census(registry: dict | None = None, *, limit: int | None = None) -> dict:
    from canonical.runtime import goal_front_compiler_v1 as front

    registry = registry or load_registry()
    rows: list[dict] = []
    started = time.time()

    for index, (cid, entry) in enumerate(sorted(registry.items())):
        if limit is not None and index >= limit:
            break
        row: dict = {
            "capability_id": cid,
            "declares_effects": len(entry.get("provides") or []),
            "addresses": {},
            "outcome": UNREACHED,
            "reason": None,
        }
        best = UNREACHED
        for mode, goal in (("DECLARED_VOCABULARY", sentence_for(entry)),
                           ("NATURAL", natural_for(cid, entry)),
                           ("NATURAL_WITH_INPUT", natural_with_input(cid, entry, ROOT))):
            record = {"sentence": goal, "selected": None,
                      "compiler_mode": None, "outcome": UNREACHED, "reason": None}
            try:
                compiled = front.compile_goal(goal, registry, ROOT)
            except Exception as exc:                               # noqa: BLE001
                record["reason"] = f"COMPILER_RAISED:{getattr(exc, 'code', type(exc).__name__)}"
            else:
                selected = compiled.get("selected_capability")
                record["selected"] = selected
                record["compiler_mode"] = compiled.get("compiler_mode")
                if selected == cid:
                    record["outcome"] = SELF_REACHED
                elif selected:
                    record["outcome"] = REACHED_BY_ANOTHER
                    record["reason"] = f"ROUTED_TO:{selected}"
                else:
                    record["reason"] = "NO_SELECTION"
            row["addresses"][mode] = record
            if record["outcome"] == SELF_REACHED:
                best = SELF_REACHED
            elif record["outcome"] == REACHED_BY_ANOTHER and best == UNREACHED:
                best = REACHED_BY_ANOTHER
                row["reason"] = record["reason"]
            elif best == UNREACHED and record["reason"]:
                row["reason"] = record["reason"]
        row["outcome"] = best
        rows.append(row)

    by_outcome: dict[str, int] = {}
    for row in rows:
        by_outcome[row["outcome"]] = by_outcome.get(row["outcome"], 0) + 1

    per_address: dict[str, dict[str, int]] = {}
    for row in rows:
        for mode, record in row["addresses"].items():
            bucket = per_address.setdefault(mode, {})
            bucket[record["outcome"]] = bucket.get(record["outcome"], 0) + 1

    effects = declared_effects(registry)
    covered_effects = {
        str(effect)
        for effect, owners in effects.items()
        if any(r["capability_id"] in owners and r["outcome"] == SELF_REACHED for r in rows)
    }
    collisions = {
        str(effect): owners for effect, owners in effects.items() if len(owners) > 1
    }
    return {
        "schema": SCHEMA,
        "authority": "NO_CAPABILITY_CREDIT_ROUTING_MEASUREMENT_ONLY",
        "reach_denominator_claim": NO_DENOMINATOR_CLAIM,
        "measured_at_unix": int(started),
        "duration_s": round(time.time() - started, 2),
        "capabilities": len(rows),
        "declared_effects": len(effects),
        "effects_reached_by_their_own_owner": len(covered_effects),
        "effects_with_colliding_owners": len(collisions),
        "outcomes": by_outcome,
        "outcomes_per_address": per_address,
        "rows": rows,
    }


# --------------------------------------------------------------------------- real sentences
REAL_CORPUS_PROBE = "execution_guard/swe_advanced_probe_v1.py"


def real_sentence_corpus() -> list[dict]:
    """The repository's OWN hand-written advanced-SWE sentences, not a template of its ids.

    Why this is a different instrument from the templated addresses above
    --------------------------------------------------------------------
    The templated census measured its own phrasings and produced a diagnostic, not a reach
    denominator. This reuses sentences a person wrote as requests -- 49 of them, across
    polyglot, build, CI, performance, concurrency, test authoring, debugging, refactoring and
    design -- which is the corpus the diagnostic said it could not manufacture.

    It only ROUTES: it compiles each sentence and records which capability the front door
    picks. It does not execute anything, so a reach figure from this is about the door, not
    about whether the capability would then have worked.
    """
    import importlib.util

    path = ROOT / REAL_CORPUS_PROBE
    spec = importlib.util.spec_from_file_location("_brain_real_swe_probe", path)
    if spec is None or spec.loader is None:
        return []
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception:                                           # noqa: BLE001
        return []

    base = ".brain_reach_scratch"
    paths = {rel: f"{base}/{rel}" for rel in getattr(module, "FILES", {})}
    paths.update(pkg=f"{base}/pkg", tests=f"{base}/tests",
                 src=f"{base}/src", root=base)
    sentences: list[dict] = []
    for axis, template, allow in getattr(module, "PROBES", []):
        try:
            goal = template.format(**paths)
        except (KeyError, IndexError):
            continue
        sentences.append({"axis": axis, "goal": goal, "authorised_files": list(allow)})
    return sentences


def reach_over_real_sentences(registry: dict | None = None) -> dict:
    """How many capabilities and effects do REAL sentences actually reach?"""
    from canonical.runtime import goal_front_compiler_v1 as front

    registry = registry or load_registry()
    sentences = real_sentence_corpus()
    rows: list[dict] = []
    for item in sentences:
        row = dict(item, selected=None, compiler_mode=None, reason=None)
        try:
            compiled = front.compile_goal(item["goal"], registry, ROOT)
        except Exception as exc:                                # noqa: BLE001
            row["reason"] = f"COMPILER_RAISED:{getattr(exc, 'code', type(exc).__name__)}"
        else:
            row["selected"] = compiled.get("selected_capability")
            row["compiler_mode"] = compiled.get("compiler_mode")
            if not row["selected"]:
                row["reason"] = "NO_SELECTION"
        rows.append(row)

    reached = sorted({r["selected"] for r in rows if r["selected"]})
    effects = declared_effects(registry)
    reached_effects = sorted({
        str(effect) for effect, owners in effects.items()
        if any(o in reached for o in owners)
    })
    counts: dict[str, int] = {}
    for row in rows:
        if row["selected"]:
            counts[row["selected"]] = counts.get(row["selected"], 0) + 1
    served = sum(1 for r in rows if r["selected"])
    return {
        "schema": SCHEMA,
        "instrument": "REAL_SENTENCES_ROUTING_ONLY",
        "corpus": REAL_CORPUS_PROBE,
        "authority": "NO_CAPABILITY_CREDIT_ROUTING_MEASUREMENT_ONLY",
        "sentences": len(rows),
        "sentences_routed": served,
        "capabilities_total": len(registry),
        "capabilities_reached": len(reached),
        "declared_effects_total": len(effects),
        "declared_effects_reached": len(reached_effects),
        "reach_magnets": sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:12],
        "rows": rows,
    }


def main(argv: list[str]) -> int:
    limit = None
    if "--limit" in argv:
        limit = int(argv[argv.index("--limit") + 1])

    if "--real" in argv:
        real = reach_over_real_sentences()
        print(f"corpus                      : {real['corpus']}")
        print(f"sentences                   : {real['sentences']}")
        print(f"sentences routed somewhere  : {real['sentences_routed']}")
        print(f"capabilities reached        : {real['capabilities_reached']}"
              f" / {real['capabilities_total']}")
        print(f"declared effects reached    : {real['declared_effects_reached']}"
              f" / {real['declared_effects_total']}")
        print()
        print("rows doing the most work (a magnet is a routing concentration, not a win):")
        for cid, n in real["reach_magnets"]:
            print(f"  {n:3} sentences  {cid}")
        print()
        out = ROOT / "canonical/verification/ROUTE_REACH_REAL_SENTENCES_V1.json"
        out.write_text(json.dumps(real, indent=1, sort_keys=True) + "\n")
        print(f"written: {out.relative_to(ROOT)}")
        return 0

    report = census(limit=limit)
    print(f"capabilities                : {report['capabilities']}")
    print(f"declared effects            : {report['declared_effects']}")
    print(f"effects reached by owner    : {report['effects_reached_by_their_own_owner']}")
    print(f"effects with colliding owners: {report['effects_with_colliding_owners']}")
    print(f"duration                    : {report['duration_s']}s")
    print()
    for name in (SELF_REACHED, REACHED_BY_ANOTHER, UNREACHED):
        print(f"  {name:20} {report['outcomes'].get(name, 0)}")
    print()
    print("per address (this is why one address is not enough):")
    for mode, bucket in report["outcomes_per_address"].items():
        print(f"  {mode:20} " + "  ".join(f"{k}={v}" for k, v in sorted(bucket.items())))
    print()
    print("UNREACHED rows, with the reason each names:")
    for row in report["rows"]:
        if row["outcome"] == UNREACHED:
            print(f"  {row['capability_id']:52} {row['reason']}")
    print()
    out = ROOT / "canonical/verification/ROUTE_REACH_CENSUS_V1.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print(f"written: {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
