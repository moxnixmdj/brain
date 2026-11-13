#!/usr/bin/env python3
"""When can evidence not teach, and what does the tree do about it?

WHY THIS EXISTS
---------------
`applicability_v1.learn` refuses to invent a requirement and answers INCONSISTENT. That refusal is
correct, and until now it was unexplained on real code: `vocabulary_gap`, the instrument built to
witness insufficiency, fires only when two observations have EQUAL fact sets, and the pinned real
code-repair corpus is not shaped that way. So the tree could say "nothing can be learned here" and
simultaneously "nothing is wrong with the vocabulary", and two rounds read the label rather than the
proof.

`insufficiency_witness` is the general proof. With A = the intersection of all successes' fact sets,
a consistent conjunction exists iff A is not a subset of any failure's fact set, because A is the
largest candidate and excludes a failure exactly by not being contained in it. That is decidable in
|evidence| set comparisons, where `learn` decides it by enumerating 2^|A| subsets -- so the witness
also decides cases where `learn` must answer BOUNDED.

THIS PROBE MEASURES THREE THINGS, ALL EXECUTED
----------------------------------------------
1. The real code-repair corpus, where the older witness is blind and the new one is not, and where
   the outcomes come from each pinned target's OWN upstream test suite.
2. A live vocabulary defect on main, before and after repair: `python.test.corpus` was decided by the
   substring "test" against the whole relative path, which credited 54 files on this tree that are
   not test modules and made `canonical/tools` sense as IDENTICAL to `canonical/tests`. That is the
   equal-facts wall, and it left `canonical/tests/test_real_input_space_census_v1.py` red. Narrowing
   the sensor to the `test_` filename prefix removes it, and the census identifies its requirement.
3. What a vocabulary repair for case 1 would cost: closing the fact vocabulary to kinds and emitting
   absence removes the obstruction but pushes the shared literal set past the learner's own
   enumeration cap, so the obstacle moves from representation to combinatorics.

Authority NONE -- producer-run measurement in one sandbox, not independent verification.
$0, no model in any result-bearing path, nothing written, no network.
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

SCHEMA = "PROJECT_BRAIN_INSUFFICIENCY_CERTIFICATE_PROBE_V1"

from canonical.runtime import applicability_v1 as app  # noqa: E402
from canonical.runtime import fact_entailment_v1 as fe  # noqa: E402
from canonical.runtime import world_probe_v1 as wp  # noqa: E402
from canonical.swe_kernel import skill_scope_acquisition_v1 as acq  # noqa: E402
from canonical.tests.historical_repair_curriculum_v1 import FIXTURES  # noqa: E402
from canonical.tools import real_repair_localization_probe_v1 as repair  # noqa: E402

EFFECTS = ["python.source.available", "python.test.corpus.available",
           "json.available", "markdown.available"]
CENSUS_DIRS = {
    "canonical/tests": True, "canonical/runtime": True,
    "canonical/runtime/bound_capabilities": True, "canonical/verification": True,
    "canonical/tools": False, "canonical/analysis": False,
}
RULE = {"language": "python", "state": "ACTIVE",
        "pattern_tokens": [["op", "<="]], "replacement_tokens": [["op", "<"]]}


def _old_loose_corpus_facts(root: pathlib.Path) -> bool:
    """The pre-repair rule, recomputed: any .py whose RELATIVE PATH contains "test"."""
    skip = {".git", "node_modules", "__pycache__", ".venv", ".pytest_cache", ".ruff_cache"}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip]
        for name in filenames:
            if not name.endswith(".py"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, name), ROOT).lower()
            if "test" in rel:
                return True
    return False


def measure_theorem() -> dict:
    """The equivalence, exhaustively, over every evidence set on a three-fact vocabulary."""
    vocab = ("a", "b", "c")
    states = [frozenset(s) for k in range(len(vocab) + 1)
              for s in itertools.combinations(vocab, k)]
    combos = [(s, o) for s in states for o in (True, False)]
    checked = disagreements = subsumption_checks = subsumption_misses = 0
    for size in range(5):
        for evidence in itertools.combinations(combos, size):
            evidence = list(evidence)
            checked += 1
            w = app.insufficiency_witness(evidence)
            fires = w is not None and w["kind"] in app.UNREPAIRABLE_BY_REPETITION
            if fires != (app.learn(evidence).status == app.INCONSISTENT):
                disagreements += 1
            if app.vocabulary_gap(evidence) is not None:
                subsumption_checks += 1
                if not (w is not None and w["kind"] == app.WITNESS_SAME_STATE):
                    subsumption_misses += 1
    return {"evidence_sets_checked": checked, "equivalence_counterexamples": disagreements,
            "equal_facts_cases_checked": subsumption_checks,
            "subsumption_counterexamples": subsumption_misses}


def measure_real_corpus() -> dict:
    """The four pinned real repairs, outcomes from their own upstream suites."""
    doc = repair.demonstration()
    rows, evidence = [], []
    for cid in repair.CASES:
        src = (FIXTURES / cid / "before.py").read_text()
        sf = acq.site_facts(src, RULE, baseline_ok=False)
        ok = doc["transfer"][cid]["verdict"] == repair.REPAIRED
        evidence.append((sf["state"], ok))
        rows.append({"case": cid, "verdict": doc["transfer"][cid]["verdict"],
                     "succeeded": ok, "site_facts": len(sf["state"]),
                     # distinct numbers, reported as themselves: a site is where the rule fires,
                     # a candidate is an edit it proposes. Conflating them was a mislabel here.
                     "firing_sites": sf["firing_sites"],
                     "candidates_proposed": doc["transfer"][cid]["candidates_proposed"]})
    b = app.learn(evidence)
    w = app.insufficiency_witness(evidence)
    return {
        "rows": rows, "evidence": [(sorted(f), o) for f, o in evidence],
        "learn_status": b.status, "learn_survivors": b.survivor_count,
        "learn_reason": b.reason,
        "older_witness_vocabulary_gap": app.vocabulary_gap(evidence),
        "certificate": w,
        "constant_facts": sorted(acq.constant_facts(evidence)),
        "correction_no_success_is_a_subset_of_a_failure":
            not any(s <= f for s, so in evidence if so for f, fo in evidence if not fo),
    }


def measure_sensor_defect() -> dict:
    """The live vocabulary defect, before and after, on the census the tree already ships."""
    before, after = [], []
    for d, pinned in CENSUS_DIRS.items():
        root = ROOT / d
        facts_now = tuple(wp.established_facts(EFFECTS, root=str(root)))
        loose = _old_loose_corpus_facts(root)
        # the pre-repair fact set differs only in the corpus fact, which the loose rule over-credited
        facts_old = tuple(sorted(set(facts_now) | ({"python.test.corpus.available"} if loose else set())))
        before.append((facts_old, pinned))
        after.append((facts_now, pinned))
    genuine = {d: sorted(p.name for p in (ROOT / d).rglob("test_*.py"))[:3]
               for d in CENSUS_DIRS}
    b_old, b_new = app.learn(before), app.learn(after)
    w_old, w_new = app.insufficiency_witness(before), app.insufficiency_witness(after)
    old_by_dir = dict(zip(CENSUS_DIRS, before))
    tools_old = old_by_dir["canonical/tools"][0]
    return {
        "pinned_outcomes": CENSUS_DIRS,
        "genuine_test_modules_found": {d: v for d, v in genuine.items()},
        "before_repair": {
            "learn": b_old.status, "survivors": b_old.survivor_count,
            "certificate": (w_old or {}).get("kind"),
            "older_witness": "FIRES" if app.vocabulary_gap(before) else None,
            # which directories the loose rule made INDISTINGUISHABLE from canonical/tools
            "sensed_identical_to_canonical_tools": sorted(
                d for d in CENSUS_DIRS if old_by_dir[d][0] == tools_old),
        },
        "after_repair": {
            "learn": b_new.status, "survivors": b_new.survivor_count,
            "identified_requirement": list(b_new.most_general),
            "certificate": (w_new or {}).get("kind"),
            "admits_every_success_and_refuses_every_failure": all(
                (set(b_new.most_general) <= set(f)) == o for f, o in after),
        },
        "entailment_still_correct": {
            "known_facts": len(fe.known_facts()),
            "implication_pairs": sum(len(v) for v in fe.as_row()["implications"].values()),
            "corpus_implies_source": fe.implies("python.test.corpus.available",
                                                "python.source.available"),
            "source_implies_corpus": fe.implies("python.source.available",
                                                "python.test.corpus.available"),
            "they_are_equivalent": fe.equivalent("python.test.corpus.available",
                                                 "python.source.available"),
        },
    }


def measure_file_counts() -> dict:
    """How many files the substring rule credited that are not test modules."""
    skip = {".git", "node_modules", "__pycache__", ".venv", ".pytest_cache", ".ruff_cache",
            "dist", "build", ".cache", ".arena"}
    loose, genuine = [], []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in skip]
        for name in filenames:
            if not name.endswith(".py"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, name), ROOT)
            if "test" in rel.lower():
                loose.append(rel)
            if name.startswith("test_"):
                genuine.append(rel)
    only_loose = sorted(set(loose) - set(genuine))
    return {"substring_rule_files": len(loose), "genuine_test_modules": len(genuine),
            "credited_but_not_a_test": len(only_loose),
            "via_a_directory_component": sum(
                1 for r in only_loose if "test" not in os.path.basename(r).lower()),
            "via_the_filename": sum(
                1 for r in only_loose if "test" in os.path.basename(r).lower()),
            "examples": only_loose[:6]}


def measure_repair_cost(real: dict) -> dict:
    """What closing the vocabulary with absence facts would cost, measured not proposed."""
    evidence = [(frozenset(f), o) for f, o in real["evidence"]]

    def kind(fact: str) -> str:
        parts = fact.split(".")
        return ".".join(parts[:2]) if parts[0] == "left_operand" else fact

    vocab = sorted({kind(f) for facts, _ in evidence for f in facts})
    closed = []
    for facts, ok in evidence:
        k = {kind(f) for f in facts}
        closed.append((frozenset(k | {f"absent.{v}" for v in vocab if v not in k}), ok))
    shared = set.intersection(*[set(f) for f, o in closed if o])
    return {"closed_vocabulary_size": len(vocab),
            "shared_literals_after_closing": len(shared),
            "hypotheses_that_would_need_enumerating": 2 ** len(shared),
            "learner_enumeration_cap": app.MAX_CANDIDATE_FACTS,
            "certificate_after_closing": (app.insufficiency_witness(closed) or {}).get("kind"),
            "learn_after_closing": app.learn(closed).status,
            "reading": ("absence removes the separation obstruction but not the enumeration bound, "
                        "so the obstacle moves from representation to combinatorics")}


def demonstration() -> dict:
    real = measure_real_corpus()
    return {
        "schema": SCHEMA,
        "authority": "NONE__PRODUCER_RUN_MEASUREMENT_IN_ONE_SANDBOX",
        "theorem": measure_theorem(),
        "real_code_repair_corpus": real,
        "sensor_defect_before_and_after": measure_sensor_defect(),
        "file_counts": measure_file_counts(),
        "vocabulary_repair_cost": measure_repair_cost(real),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true", help="emit the measurement as JSON")
    args = parser.parse_args(argv)
    doc = demonstration()
    if args.json:
        print(json.dumps(doc, indent=1, sort_keys=True))
        return 0

    t, r, s, f, c = (doc["theorem"], doc["real_code_repair_corpus"],
                     doc["sensor_defect_before_and_after"], doc["file_counts"],
                     doc["vocabulary_repair_cost"])
    print(f"{SCHEMA}   authority {doc['authority']}\n")
    print("  1. THE CERTIFICATE IS THE LEARNER'S OWN VERDICT, EXHAUSTIVELY")
    print(f"     evidence sets checked      {t['evidence_sets_checked']}")
    print(f"     equivalence violations     {t['equivalence_counterexamples']}")
    print(f"     equal-facts cases checked  {t['equal_facts_cases_checked']}")
    print(f"     subsumption violations     {t['subsumption_counterexamples']}")
    print("\n  2. THE REAL CODE-REPAIR CORPUS, WHERE THE OLDER WITNESS IS BLIND")
    for row in r["rows"]:
        print(f"     {row['case']:18} {row['verdict']:44} facts={row['site_facts']:3}"
              f" sites={row['firing_sites']:3} candidates={row['candidates_proposed']}")
    print(f"     learn                      {r['learn_status']}  survivors {r['learn_survivors']}")
    print(f"     vocabulary_gap (older)     {r['older_witness_vocabulary_gap']}")
    print(f"     certificate (new)          {(r['certificate'] or {}).get('kind')}")
    print(f"     the facts all successes share {(r['certificate'] or {}).get('shared_facts')}")
    print(f"     ...are exactly the constants   {r['constant_facts']}")
    print(f"     CORRECTION  no success is a subset of a failure: {r['correction_no_success_is_a_subset_of_a_failure']}")
    print("\n  3. A LIVE VOCABULARY DEFECT ON MAIN, BEFORE AND AFTER REPAIR")
    print(f"     files the substring rule credited that are not tests  {f['credited_but_not_a_test']}")
    print(f"       of {f['substring_rule_files']} matched vs {f['genuine_test_modules']} genuine"
          f"  ({f['via_a_directory_component']} via a directory, {f['via_the_filename']} via a filename)")
    for e in f["examples"][:4]:
        print(f"         {e}")
    b, a = s["before_repair"], s["after_repair"]
    print(f"     BEFORE  learn {b['learn']:52} survivors {b['survivors']}")
    print(f"             certificate {b['certificate']}   older witness {b['older_witness']}")
    print(f"             canonical/tools sensed identical to {b['sensed_identical_to_canonical_tools']}")
    print(f"     AFTER   learn {a['learn']}  survivors {a['survivors']}")
    print(f"             identified requirement {a['identified_requirement']}")
    print(f"             certificate {a['certificate']}")
    print(f"             admits every success, refuses every failure: {a['admits_every_success_and_refuses_every_failure']}")
    e = s["entailment_still_correct"]
    print(f"     entailment  known {e['known_facts']}  pairs {e['implication_pairs']}"
          f"  corpus=>source {e['corpus_implies_source']}  source=>corpus {e['source_implies_corpus']}"
          f"  equivalent {e['they_are_equivalent']}")
    print("\n  4. WHAT A VOCABULARY REPAIR FOR CASE 2 WOULD COST")
    print(f"     closed kind vocabulary     {c['closed_vocabulary_size']}")
    print(f"     shared literals after      {c['shared_literals_after_closing']}")
    print(f"     hypotheses to enumerate    {c['hypotheses_that_would_need_enumerating']}  (cap {c['learner_enumeration_cap']})")
    print(f"     certificate after closing  {c['certificate_after_closing']}")
    print(f"     learn after closing        {c['learn_after_closing']}")
    print(f"     {c['reading']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
