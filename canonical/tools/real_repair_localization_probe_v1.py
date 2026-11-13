#!/usr/bin/env python3
"""Four pinned real historical repairs, and the difference between teaching a file and a lesson.

Everything here executes against `canonical/tests/fixtures/historical_repair_projects_v1`, which pins
real pre- and post-repair sources from boltons and more-itertools by sha256 and git blob sha, each
with its exact unchanged upstream test body. Nothing is constructed for the occasion and no source or
test snapshot is modified.

THE TWO ARMS
------------
Arm A teaches the way the tree's own curriculum worker teaches: `before_snippet` and `after_snippet`
are the two whole 1317-line files. Anti-unification yields 13 holes over 99 vs 99 tokens, so
`derive_operator_swap` returns None -- correctly, because it requires exactly ONE operator difference
and this pair differs in a docstring as well. The stored rule proposes **0 candidates on every real
source in the corpus**. One real experience buys a permanent no-op.

Arm B localizes the same real repair to the smallest statement covering the change
(`lesson_localization_v1`), which is `if abs_bytes <= next_size:` -> `if abs_bytes < next_size:`,
and derives `<=` -> `<`. That lesson, applied to a DIFFERENT real module in a different file,
contains that module's real upstream fix and the fix passes its own upstream tests.

Each corpus case is then judged by its OWN upstream tests through `ProjectTestOracle`, which copies
the project, writes the candidate, runs the suite and never patches the original.

WHAT THE NUMBERS ARE NOT
------------------------
Not a claim that the localized lesson is the right lesson for the corpus. Two of the four real bugs
are missing zero-guards, not operator boundaries, and localization refuses them by name; the skill
still fires on them (32 to 56 sites) and cannot repair them, which is a real failure recorded as
`FIRED_AND_NOT_REPAIRED_WITHIN_BUDGET` with the budget stated, never as a pass.
Not a claim about the scope law succeeding here. All four real targets already fail their own tests,
so `baseline.violates_own_spec` -- the requirement Round F identified on constructed fixtures -- is
present in every observation and discriminates nothing. The law says AMBIGUOUS, and that is reported
rather than dressed up.
Not independent verification. Authority NONE: producer-run measurement in one sandbox.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import tempfile
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import applicability_v1 as app  # noqa: E402
from canonical.swe_kernel import lesson_localization_v1 as loc  # noqa: E402
from canonical.swe_kernel import operator_generalization_v1 as gen  # noqa: E402
from canonical.swe_kernel import skill_scope_acquisition_v1 as acq  # noqa: E402
from canonical.swe_kernel import verified_skill_crystallizer_v1 as cry  # noqa: E402
from canonical.swe_kernel.skill_verification_contract_v1 import ProjectTestOracle  # noqa: E402
from canonical.swe_kernel.verified_skill_crystallizer_v1 import anti_unify_code_rule  # noqa: E402
from canonical.tests.historical_repair_curriculum_v1 import FIXTURES, build_case  # noqa: E402

SCHEMA = "PROJECT_BRAIN_REAL_REPAIR_LOCALIZATION_PROBE_V1"

#: The pinned real cases, in corpus order.
CASES = ("unit_boundary", "bits_capacity", "ichunked_zero", "chunked_even_zero")
#: Which real repair the lesson is taught from.
TEACH_FROM = "unit_boundary"
#: Candidates actually executed per target. Stated in every verdict that depends on it.
BUDGET = 12

REPAIRED = "REPAIRED"
NOT_REPAIRED = "FIRED_AND_NOT_REPAIRED_WITHIN_BUDGET"
DID_NOT_FIRE = "DID_NOT_FIRE__NOT_APPLICABLE"
UNVERIFIABLE = "UNVERIFIABLE__ITS_OWN_TESTS_DID_NOT_RUN"
ALREADY_CORRECT = "ALREADY_PASSES_ITS_OWN_TESTS"


def _oracle(repo: pathlib.Path, case: dict[str, Any]) -> ProjectTestOracle:
    project, target = case["project"], case["target"]
    setting = case["args"]["retained_learning"]
    return ProjectTestOracle(
        project, str(target.relative_to(project)),
        [str((repo / p).relative_to(project)) for p in case["args"]["test_paths"]],
        setting["contract"]["scope_id"], timeout_s=15)


def _verdict(oracle: ProjectTestOracle, before: str, rule: dict[str, Any],
             real_after: str) -> dict[str, Any]:
    """Judge one real target by its own upstream tests, before and after the skill is applied."""
    baseline = oracle(before)
    b_rc = baseline.evidence.get("returncode")
    b_tests = baseline.evidence.get("test_count")
    if not b_tests:
        # Zero tests ran. That is not a failure of the skill and not a pass of the target: it is no
        # observation at all, and treating it as a failure would fabricate evidence.
        return {"verdict": UNVERIFIABLE, "baseline_returncode": b_rc, "baseline_test_count": b_tests,
                "candidates_proposed": 0, "candidates_tried": 0, "passing_candidates": [],
                "real_fix_rank": None, "real_fix_passes": None}
    if b_rc == 0:
        return {"verdict": ALREADY_CORRECT, "baseline_returncode": b_rc, "baseline_test_count": b_tests,
                "candidates_proposed": 0, "candidates_tried": 0, "passing_candidates": [],
                "real_fix_rank": None, "real_fix_passes": None}

    candidates = list(gen.propose_operator_swaps(before, rule, language="python"))
    tried = candidates[:BUDGET]
    passing, rank = [], None
    for i, cand in enumerate(tried):
        if oracle(cand).evidence.get("returncode") == 0:
            passing.append(i + 1)
        if cand == real_after:
            rank = i + 1
    real_fix = oracle(real_after).evidence
    return {
        "verdict": REPAIRED if passing else (NOT_REPAIRED if tried else DID_NOT_FIRE),
        "baseline_returncode": b_rc, "baseline_test_count": b_tests,
        "candidates_proposed": len(candidates), "candidates_tried": len(tried),
        "budget": BUDGET, "passing_candidates": passing,
        "real_fix_rank": rank,
        "real_fix_proposed": rank is not None,
        "real_fix_passes": real_fix.get("returncode") == 0,
        "real_fix_test_count": real_fix.get("test_count"),
    }


def demonstration() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="real_repair_probe_") as td:
        repo = pathlib.Path(td)
        teach = build_case(repo, TEACH_FROM, "teaching")
        whole_before = teach["target"].read_text()
        whole_after = (FIXTURES / TEACH_FROM / "after.py").read_text()

        # ---- arm A: teach the whole file, the way the curriculum worker does
        whole_rule = anti_unify_code_rule(whole_before, whole_after, language="python",
                                          error_class="BOUNDARY")
        inert = {
            "holes": whole_rule.get("hole_count"),
            "pattern_tokens": len(whole_rule.get("pattern_tokens") or []),
            "replacement_tokens": len(whole_rule.get("replacement_tokens") or []),
            "derived_swap": gen.derive_operator_swap(whole_rule),
            "derived_family": [(s["from"], s["to"]) for s in gen.derive_swap_family(whole_rule)],
            "candidates_on_each_real_source": {
                cid: sum(1 for _ in gen.propose_operator_swaps(
                    (FIXTURES / cid / "before.py").read_text(), whole_rule, language="python"))
                for cid in CASES},
        }
        inert["total_candidates_on_the_corpus"] = sum(
            inert["candidates_on_each_real_source"].values())
        # error_class is not the cause; both values give identical tokens
        generic_rule = anti_unify_code_rule(whole_before, whole_after, language="python",
                                            error_class="GENERIC")
        inert["error_class_is_not_the_cause"] = (
            (generic_rule.get("pattern_tokens") == whole_rule.get("pattern_tokens"))
            and (generic_rule.get("replacement_tokens") == whole_rule.get("replacement_tokens")))

        # ---- arm B: localize the same real repair to the statement that changed
        localized = loc.localize_operator_lesson(whole_before, whole_after, language="python")
        chosen = localized.chosen
        rule = dict(chosen.rule) if chosen else {}
        rule.setdefault("language", "python")
        rule.setdefault("state", "ACTIVE")

        # the localized lesson also has to survive the production store, not just this probe
        stored: dict[str, Any] = {"attempted": bool(chosen)}
        if chosen:
            db = repo / "memory" / "localized.sqlite"
            db.parent.mkdir(parents=True, exist_ok=True)
            taught = cry.VerifiedSkillStore(db, seed=False).crystallize_code_fix(
                before_snippet=chosen.before_statement, after_snippet=chosen.after_statement,
                language="python", error_class="BOUNDARY")
            stored["crystallized"] = bool(taught.get("crystallized"))
            stored["reason"] = taught.get("reason")
            stored["swap_after_storing"] = gen.derive_operator_swap(
                (cry.VerifiedSkillStore(db, seed=False).lookup_rules("python", "BOUNDARY") or [{}])[0])

        # ---- apply the localized lesson to every real case, judged by its own upstream tests
        per_case: dict[str, Any] = {}
        for cid in CASES:
            case = build_case(repo, cid, "probe_" + cid)
            oracle = _oracle(repo, case)
            per_case[cid] = _verdict(oracle, case["target"].read_text(), rule,
                                     (FIXTURES / cid / "after.py").read_text())
            per_case[cid]["localization_of_its_own_repair"] = (
                loc.localize_operator_lesson(case["target"].read_text(),
                                             (FIXTURES / cid / "after.py").read_text()).status)

        # ---- the fact vocabulary, whole-file against site-relative, on the same real evidence
        rows_site, rows_whole = [], []
        facts_comparison: dict[str, Any] = {}
        for cid in CASES:
            src = (FIXTURES / cid / "before.py").read_text()
            verdict = per_case[cid]["verdict"]
            succeeded = verdict == REPAIRED
            usable = verdict in (REPAIRED, NOT_REPAIRED, DID_NOT_FIRE)
            site = acq.site_facts(src, rule, baseline_ok=False, language="python")
            whole = acq.observable_facts(src, baseline_ok=False, language="python")
            facts_comparison[cid] = {"firing_sites": site["firing_sites"],
                                     "unlocated_offsets": site["unlocated_offsets"],
                                     "whole_file_facts": len(whole),
                                     "site_relative_facts": len(site["state"])}
            if usable:
                rows_site.append((sorted(site["state"]), succeeded))
                rows_whole.append((sorted(whole), succeeded))

        law_site = app.learn(rows_site)
        law_whole = app.learn(rows_whole)
        # the degeneracy that forced site-relative facts, stated exactly
        ub_before = (FIXTURES / TEACH_FROM / "before.py").read_text()
        ub_after = (FIXTURES / TEACH_FROM / "after.py").read_text()
        degenerate = (acq.observable_facts(ub_before, baseline_ok=False)
                      == acq.observable_facts(ub_after, baseline_ok=False))

        return {
            "schema": SCHEMA,
            "authority": "NONE__PRODUCER_RUN_MEASUREMENT_IN_ONE_SANDBOX",
            "corpus": {
                "path": str(FIXTURES.relative_to(ROOT)),
                "pinned_by": "sha256 and git blob sha in PROVENANCE.json",
                "source_and_upstream_test_snapshots_unmodified": True,
                "network_required_at_test_time": False,
                "cases": list(CASES),
                "repositories": ["mahmoud/boltons", "more-itertools/more-itertools"]},
            "arm_a_teach_the_whole_file": inert,
            "arm_b_localize_the_lesson": {
                "status": localized.status,
                "regions_examined": localized.regions_examined,
                "regions_with_a_statement_pair": localized.regions_with_a_statement_pair,
                "operator_lessons_found": len(localized.lessons),
                "before_statement": (chosen.before_statement.strip() if chosen else None),
                "after_statement": (chosen.after_statement.strip() if chosen else None),
                "before_lines": (list(chosen.before_lines) if chosen else None),
                "swap": (dict(chosen.swap) if chosen else None),
                "family": ([(s["from"], s["to"]) for s in chosen.family] if chosen else []),
                "stored_through_the_production_path": stored},
            "transfer": per_case,
            "fact_vocabulary": {
                "whole_file_facts_cannot_distinguish_a_real_defect_from_its_own_repair": degenerate,
                "per_case": facts_comparison,
                "law_on_site_relative_facts": {
                    "status": law_site.status, "required": list(law_site.required or []),
                    "survivors": law_site.survivor_count,
                    "constant_facts": sorted(acq.constant_facts(rows_site))},
                "law_on_whole_file_facts": {
                    "status": law_whole.status, "required": list(law_whole.required or []),
                    "survivors": law_whole.survivor_count},
                "why_the_round_f_requirement_does_not_discriminate_here": (
                    "all four real targets already fail their own upstream tests, so "
                    "baseline.violates_own_spec is present in every observation and refuted by none")},
            "observations": {"site_relative_rows": len(rows_site), "whole_file_rows": len(rows_whole),
                             "budget_per_target": BUDGET},
        }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    doc = demonstration()
    if args.json:
        print(json.dumps(doc, indent=1, sort_keys=True))
        return 0

    a, b = doc["arm_a_teach_the_whole_file"], doc["arm_b_localize_the_lesson"]
    print("real repair localization probe: four pinned third-party repairs, executed\n")
    print(f"  corpus                {doc['corpus']['path']}")
    print(f"  repositories          {doc['corpus']['repositories']}")
    print(f"\n  ARM A -- teach the two whole files, as the curriculum worker does")
    print(f"    holes / tokens      {a['holes']} / {a['pattern_tokens']} vs {a['replacement_tokens']}")
    print(f"    derived swap        {a['derived_swap']}   family {a['derived_family']}")
    print(f"    error_class is not the cause: {a['error_class_is_not_the_cause']}")
    print(f"    candidates on the corpus      {a['candidates_on_each_real_source']}")
    print(f"    TOTAL                         {a['total_candidates_on_the_corpus']}  <-- inert")
    print(f"\n  ARM B -- localize the same real repair to one statement")
    print(f"    status              {b['status']}")
    print(f"    regions             {b['regions_examined']} examined, "
          f"{b['regions_with_a_statement_pair']} with a statement pair")
    print(f"    statement           {b['before_statement']!r} -> {b['after_statement']!r}")
    print(f"    lines               {b['before_lines']}")
    print(f"    swap                {b['swap']}   family {b['family']}")
    print(f"    stored in production {b['stored_through_the_production_path']}")
    print(f"\n  TRANSFER -- each real target judged by its OWN upstream tests (budget {BUDGET})")
    for cid, row in doc["transfer"].items():
        print(f"    {cid:18} {row['verdict']}")
        print(f"        baseline rc={row['baseline_returncode']} tests={row['baseline_test_count']}"
              f"  candidates {row['candidates_tried']}/{row['candidates_proposed']}"
              f"  passing={row['passing_candidates']}")
        print(f"        the real upstream fix: proposed={row['real_fix_rank']} "
              f"passes={row['real_fix_passes']} tests={row.get('real_fix_test_count')}")
        print(f"        its own repair localizes to: {row['localization_of_its_own_repair']}")
    fv = doc["fact_vocabulary"]
    print(f"\n  FACT VOCABULARY on the same real evidence")
    print(f"    whole-file facts cannot tell a real defect from its own repair: "
          f"{fv['whole_file_facts_cannot_distinguish_a_real_defect_from_its_own_repair']}")
    for cid, row in fv["per_case"].items():
        print(f"      {cid:18} sites={row['firing_sites']:3} unlocated={row['unlocated_offsets']:3} "
              f"whole_file_facts={row['whole_file_facts']:3} site_relative={row['site_relative_facts']:3}")
    site, whole = fv["law_on_site_relative_facts"], fv["law_on_whole_file_facts"]
    print(f"    law on site-relative facts: {site['status']} survivors={site['survivors']}")
    print(f"      constant in every observation: {site['constant_facts']}")
    print(f"    law on whole-file facts   : {whole['status']} survivors={whole['survivors']}")
    print(f"    {fv['why_the_round_f_requirement_does_not_discriminate_here']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
