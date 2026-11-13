"""End-to-end tests for causal localization sufficiency, dynamic execution-locus
candidate filtering, pre-write contrast admission, and cross-module callee
dependency preservation.

Every test executes real code, real `pytest` subprocesses or traced frames, and
real SQLite stores; nothing is mocked, monkeypatched, or stubbed.
"""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import textwrap

import pytest

from canonical.swe_kernel import (
    lesson_admission_gate_v1 as adm,
    operator_generalization_v1 as gen,
    repair_input_dependency_gate_v1 as dep_gate,
    skill_recheck_v1 as recheck_mod,
    verified_lesson_pipeline_v1 as pipeline,
    verified_skill_crystallizer_v1 as cry,
)
from canonical.swe_kernel.skill_verification_contract_v1 import ProjectTestOracle
from canonical.tests.historical_repair_curriculum_v1 import (
    FIXTURES,
    build_case,
)


ROOT = Path(__file__).resolve().parents[2]
VERIFICATION_JSON = (
    ROOT
    / "canonical"
    / "verification"
    / "CAUSAL_LOCALIZATION_AND_DEPENDENCY_ADMISSION_20261113_V1.json"
)


def test_whole_file_unit_boundary_requires_localization_and_verifies_causal_sufficiency(
    tmp_path: Path,
) -> None:
    case = build_case(tmp_path / "repo", "unit_boundary", "ub")
    rel_target = case["target"].relative_to(case["project"]).as_posix()
    rel_tests = [
        p.relative_to(case["project"]).as_posix()
        for p in sorted(case["project"].glob("test_*.py"))
    ]

    whole_before = (FIXTURES / "unit_boundary" / "before.py").read_text(encoding="utf-8")
    whole_after = (FIXTURES / "unit_boundary" / "after.py").read_text(encoding="utf-8")

    # 1. Without `localize_lesson=True`, whole-file anti-unification crystallizes
    #    an inert 13-hole whole-file rule that passes self-witness ONLY on its own
    #    1,317-line file and generates ZERO operator-swap candidates on every other
    #    target (`bits_capacity`, `ichunked_zero`, `chunked_even_zero`).
    unlocalized_db = tmp_path / "unlocalized.sqlite"
    oracle_unloc = ProjectTestOracle(
        case["project"],
        rel_target,
        rel_tests,
        case["args"]["retained_learning"]["contract"]["scope_id"],
    )
    unloc = cry.VerifiedSkillStore(unlocalized_db, seed=False).crystallize_code_fix(
        before_snippet=whole_before,
        after_snippet=whole_after,
        language="python",
        error_class="BOUNDARY",
        contract=case["args"]["retained_learning"]["contract"],
        training_verifier=oracle_unloc,
        localize_lesson=False,
    )
    assert unloc["crystallized"] is True
    unloc_rule = cry._load_rules(unlocalized_db, "python")[0]
    bits_before = (FIXTURES / "bits_capacity" / "before.py").read_text(encoding="utf-8")
    assert list(gen.propose_operator_swaps(bits_before, unloc_rule, language="python")) == []

    # 2. With `localize_lesson=True`, the incidental docstring region is stripped,
    #    counterfactual causal sufficiency executes the localized single-hunk
    #    rewrite against the real `ProjectTestOracle`, and admission rejects a
    #    harmful inclusive contrast victim BEFORE writing any SQLite row.
    unseen_defective = adm.Victim(
        victim_id="unseen_exclusive_tier_defect",
        source=(
            "def scale_tier(val):\n"
            "    tier = 0\n"
            "    for bound in (10, 100):\n"
            "        if val <= bound:\n"
            "            break\n"
            "        tier += 1\n"
            "    return tier\n"
        ),
        oracle=lambda _src, pt: 0 if pt < 10 else (1 if pt < 100 else 2),
        probes=(9, 10, 11),
    )
    already_correct_inclusive = adm.Victim(
        victim_id="already_correct_inclusive_quota",
        source=(
            "def inclusive_tier(val):\n"
            "    tier = 0\n"
            "    for cap in (10, 100):\n"
            "        if val <= cap:\n"
            "            break\n"
            "        tier += 1\n"
            "    return tier\n"
        ),
        oracle=lambda _src, pt: 0 if pt <= 10 else (1 if pt <= 100 else 2),
        probes=(9, 10, 11),
    )
    already_correct_preserved = adm.Victim(
        victim_id="already_correct_idempotent_clamp",
        source=(
            "def clamp_at_ten(val):\n"
            "    best = 10\n"
            "    for cap in (10,):\n"
            "        if val <= cap:\n"
            "            break\n"
            "        best = cap\n"
            "    return val if val < best else best\n"
        ),
        oracle=lambda _src, pt: pt if pt <= 10 else 10,
        probes=(9, 10, 11),
    )

    rejected_db = tmp_path / "rejected.sqlite"
    oracle_reject = ProjectTestOracle(
        case["project"],
        rel_target,
        rel_tests,
        case["args"]["retained_learning"]["contract"]["scope_id"],
    )
    rejected = cry.VerifiedSkillStore(rejected_db, seed=False).crystallize_code_fix(
        before_snippet=whole_before,
        after_snippet=whole_after,
        language="python",
        error_class="BOUNDARY",
        contract=case["args"]["retained_learning"]["contract"],
        training_verifier=oracle_reject,
        localize_lesson=True,
        admission_victims=(unseen_defective, already_correct_inclusive),
    )
    assert rejected["crystallized"] is False
    assert (
        rejected["reason"]
        == "ADMISSION_REJECT:BROKE_CORRECT_PROGRAM:already_correct_inclusive_quota"
    )
    assert cry._load_rules(rejected_db, "python") == []

    # 3. With a preserved contrast victim, crystallization succeeds, persists
    #    localization + causal_sufficiency provenance, and passes recheck + witness.
    admitted_db = tmp_path / "admitted.sqlite"
    oracle_admit = ProjectTestOracle(
        case["project"],
        rel_target,
        rel_tests,
        case["args"]["retained_learning"]["contract"]["scope_id"],
    )
    admitted = cry.VerifiedSkillStore(admitted_db, seed=False).crystallize_code_fix(
        before_snippet=whole_before,
        after_snippet=whole_after,
        language="python",
        error_class="BOUNDARY",
        contract=case["args"]["retained_learning"]["contract"],
        training_verifier=oracle_admit,
        localize_lesson=True,
        admission_victims=(unseen_defective, already_correct_preserved),
    )
    assert admitted["crystallized"] is True
    assert admitted["causal_sufficiency"]["verified"] is True
    assert admitted["causal_sufficiency"]["incidental_edits_stripped"] is True
    assert admitted["localization"]["before_lines"] == [565, 566]
    assert admitted["localization"]["incidental_regions_ignored"] == 1

    rules = cry._load_rules(admitted_db, "python")
    assert len(rules) == 1
    rule = rules[0]
    assert rule["admission"]["verdict"] == "ADMIT"
    assert rule["causal_sufficiency"]["verified"] is True
    assert rule["localization"]["swap"] == {"from": "<=", "to": "<"}
    assert recheck_mod.recheck(rule)["verdict"] == "PASS"
    assert recheck_mod.self_witness(rule)["verdict"] == "PASS"


def test_counterfactual_causal_sufficiency_rejects_spurious_localized_operator_swap(
    tmp_path: Path,
) -> None:
    """Adversarial test: a multi-hunk commit contains BOTH (a) an incidental
    single-operator edit (`<= -> <`) in an unexecuted/irrelevant helper AND
    (b) a multi-statement structural fix that actually repairs the failing test.

    Static AST localization (`localize_operator_lesson`) picks hunk (a) because
    hunk (b) is not a single-operator swap. Without counterfactual causal
    sufficiency, hunk (a) would be crystallized as a bogus "verified" skill!
    Our counterfactual gate applies ONLY hunk (a) to `before_snippet`, runs the
    real `ProjectTestOracle`, sees the test still fail, and refuses admission.
    """
    proj = tmp_path / "spurious_proj"
    pkg = proj / "pkg"
    tests = proj / "tests"
    pkg.mkdir(parents=True)
    tests.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")

    before_code = textwrap.dedent(
        """\
        def unused_helper(x, cap):
            if x <= cap:
                return "ok"
            return "over"


        def compute_total(items):
            # Real bug: returns 0 instead of summing items
            total = 0
            return total
        """
    )
    after_code = textwrap.dedent(
        """\
        def unused_helper(x, cap):
            if x < cap:
                return "ok"
            return "over"


        def compute_total(items):
            total = 0
            for val in items:
                total += val
            return total
        """
    )
    (pkg / "calc.py").write_text(before_code, encoding="utf-8")
    (tests / "test_calc.py").write_text(
        textwrap.dedent(
            """\
            from pkg.calc import compute_total


            def test_compute_total():
                assert compute_total([2, 3, 5]) == 10
            """
        ),
        encoding="utf-8",
    )

    contract = {
        "schema_version": 1,
        "scope_id": "spurious_proj:pkg/calc.py",
        "verification_kind": "TEST_SUITE",
    }
    oracle = ProjectTestOracle(
        proj, "pkg/calc.py", ["tests/test_calc.py"], contract["scope_id"]
    )
    db_path = tmp_path / "spurious.sqlite"
    res = cry.VerifiedSkillStore(db_path, seed=False).crystallize_code_fix(
        before_snippet=before_code,
        after_snippet=after_code,
        language="python",
        error_class="BOUNDARY",
        contract=contract,
        training_verifier=oracle,
        localize_lesson=True,
    )
    assert res["crystallized"] is False
    assert res["reason"] == "LOCALIZED_LESSON_NOT_CAUSALLY_SUFFICIENT"
    assert res["localization"]["status"] == "LOCALIZED__ONE_OPERATOR_LESSON"
    assert cry._load_rules(db_path, "python") == []


def test_execution_locus_reaches_innocent_guard_without_false_repair_claim(
    tmp_path: Path,
) -> None:
    """Honest limit test: `executed_locus.syntax_valid_site` proves dynamic
    reachability on the failing trace, NOT root-cause sufficiency.

    When an innocent `if x <= 10:` guard executes before an unrelated arithmetic
    defect (`return x + 99`), `executed_locus.syntax_valid_site` is True (1 locus
    candidate), and `evaluate_rule_in_executed_locus` executes the `ProjectTestOracle`
    once and honestly reports `STILL_BROKEN` rather than claiming repair.
    """
    # Teach a real `if ?id0 <= ?id1: break` rule on a minimal temp store.
    db_path = tmp_path / "rule.sqlite"
    store = cry.VerifiedSkillStore(db_path, seed=False)
    taught = store.crystallize_code_fix(
        before_snippet="for b in (10,):\n    if x <= b:\n        break\n",
        after_snippet="for b in (10,):\n    if x < b:\n        break\n",
        language="python",
        error_class="BOUNDARY",
    )
    assert taught["crystallized"] is True
    rule = cry._load_rules(db_path, "python")[0]

    proj = tmp_path / "innocent_guard_proj"
    (proj / "mod").mkdir(parents=True)
    (proj / "tests").mkdir(parents=True)
    (proj / "mod" / "__init__.py").write_text("", encoding="utf-8")
    target = proj / "mod" / "core.py"
    target.write_text(
        textwrap.dedent(
            """\
            def unexecuted_branch(z):
                for b in (10,):
                    if z <= b:
                        break
                return z


            def buggy_fn(x):
                for b in (10,):
                    if x <= b:
                        break
                return x + 99
            """
        ),
        encoding="utf-8",
    )
    test_file = proj / "tests" / "test_core.py"
    test_file.write_text(
        textwrap.dedent(
            """\
            from mod.core import buggy_fn


            def test_buggy_fn():
                assert buggy_fn(5) == 5
            """
        ),
        encoding="utf-8",
    )

    trace = pipeline.trace_project_target(proj, "mod/core.py", ["tests/test_core.py"])
    assert trace["verifiable"] is True
    assert trace["returncode"] != 0
    oracle = ProjectTestOracle(proj, "mod/core.py", ["tests/test_core.py"], "innocent_guard_proj:mod/core.py")
    ev = pipeline.apply_localized_skill_with_locus(
        oracle,
        target.read_text(encoding="utf-8"),
        rule,
        returncode=trace["returncode"],
        test_count=trace["test_count"],
        executed_lines=trace["executed_lines"],
    )
    # 2 static `<=` sites exist (`unexecuted_branch` + `buggy_fn`),
    # dynamic tracing prunes the unexecuted function (2 -> 1), and the oracle
    # catches that flipping the executed guard does NOT fix `x + 99`.
    assert ev["raw_candidates"] == 2
    assert ev["locus_candidates"] == 1
    assert ev["oracle_calls"] == 1
    assert ev["verdict"] == "NOT_REPAIRED"


def test_real_historical_execution_locus_pipeline_and_scope_identification() -> None:
    report = pipeline.measure_real_historical_pipeline()
    assert report["authority"] == "NONE"
    assert report["truth_achieved"] is False
    assert report["incremental_spend_usd"] == 0
    assert report["model_dependency_count"] == 0

    red = report["candidate_reduction_on_4_real_defects"]
    assert red["static_raw_candidates_total"] == 77
    assert red["execution_locus_candidates_total"] == 2
    assert red["static_probe_oracle_calls_total"] == 26
    assert red["execution_locus_oracle_calls_total"] == 2
    assert red["reduction_ratio"] > 0.97

    assert report["per_case"]["bits_capacity"]["verdict"] == "REPAIRED"
    assert report["per_case"]["bits_capacity"]["matches_exact_upstream_fix"] is True
    assert report["per_case"]["bits_capacity"]["passing_locus_ranks"] == [1]
    assert report["per_case"]["ichunked_zero"]["verdict"] == "DID_NOT_FIRE_IN_EXECUTED_LOCUS"
    assert report["per_case"]["ichunked_zero"]["oracle_calls"] == 0
    assert report["per_case"]["chunked_even_zero"]["verdict"] == "DID_NOT_FIRE_IN_EXECUTED_LOCUS"
    assert report["per_case"]["chunked_even_zero"]["oracle_calls"] == 0

    sc = report["scope_comparison"]
    assert sc["static_site_union_status"] == "INCONSISTENT__NO_REQUIREMENT_EXPLAINS_THE_EVIDENCE"
    assert sc["static_site_union_survivors"] == 0
    assert sc["execution_locus_with_green_control_status"] == "IDENTIFIED__ONE_CONSISTENT_REQUIREMENT"
    assert sc["execution_locus_with_green_control_survivors"] == 1
    assert sc["execution_locus_identified_required_facts"] == [
        "baseline.violates_own_spec",
        "executed_locus.syntax_valid_site",
    ]
    assert report["green_control_bits_capacity_after"]["verdict_under_learned_scope"] == "ALREADY_CORRECT"
    assert report["green_control_bits_capacity_after"]["oracle_calls_under_learned_scope"] == 0

    # Verify committed JSON receipt matches live pipeline invariants.
    assert VERIFICATION_JSON.is_file()
    committed = json.loads(VERIFICATION_JSON.read_text(encoding="utf-8"))
    assert committed == report


def test_imported_callee_dependency_gate_distinguishes_bypass_from_legitimate_edits() -> None:
    before_direct = textwrap.dedent(
        """\
        from billing.discounts import apply_discount, apply_tiered_discount


        def compute_invoice(items, disc):
            total = 0.0
            for i in range(len(items) - 1):
                total += apply_discount(items[i], disc)
            return round(total, 2)
        """
    )

    # 1. Dropping the non-stdlib imported dependency (`apply_discount`) to hardcode
    #    `(sum(items) - disc)` is REJECTED.
    bypass = textwrap.dedent(
        """\
        from billing.discounts import apply_discount, apply_tiered_discount


        def compute_invoice(items, disc):
            return (sum(items) - disc)
        """
    )
    r_bypass = dep_gate.gate(before_direct, bypass)
    assert r_bypass["status"] == "REFUSED"
    assert r_bypass["reason"] == "PATCH_STOPPED_CALLING_IMPORTED_DEPENDENCY: compute_invoice(apply_discount)"
    assert r_bypass["lost_callees"][0]["function"] == "compute_invoice"
    assert r_bypass["lost_callees"][0]["callee"] == "apply_discount"

    # 2. Replacing `apply_discount(...)` with sibling non-stdlib helper
    #    `apply_tiered_discount(...)` is PERMITTED (imported callee module stays used).
    sibling_swap = textwrap.dedent(
        """\
        from billing.discounts import apply_discount, apply_tiered_discount


        def compute_invoice(items, disc):
            total = 0.0
            for i in range(len(items)):
                total += apply_tiered_discount(items[i], disc)
            return round(total, 2)
        """
    )
    assert dep_gate.gate(before_direct, sibling_swap)["status"] == "PASS"

    # 3. Module-qualified non-stdlib import (`from billing import discounts; discounts.apply(...)`)
    #    is ALSO protected when bypassed.
    before_mod = textwrap.dedent(
        """\
        from billing import discounts


        def compute_invoice(items, disc):
            return sum(discounts.apply_discount(x, disc) for x in items[:-1])
        """
    )
    bypass_mod = textwrap.dedent(
        """\
        from billing import discounts


        def compute_invoice(items, disc):
            return sum(items) - disc
        """
    )
    r_mod = dep_gate.gate(before_mod, bypass_mod)
    assert r_mod["status"] == "REFUSED"
    assert r_mod["reason"] == "PATCH_STOPPED_CALLING_IMPORTED_DEPENDENCY: compute_invoice(discounts.apply_discount)"

    # 4. Dropping a stdlib helper (`math.floor(x)` -> `int(x)`) is PERMITTED.
    before_stdlib = "import math\n\ndef snap(x):\n    return math.floor(x)\n"
    after_stdlib = "import math\n\ndef snap(x):\n    return int(x)\n"
    assert dep_gate.gate(before_stdlib, after_stdlib)["status"] == "PASS"

    # 5. Shadowed parameter name does not masquerade as an imported module call.
    before_shadow = textwrap.dedent(
        """\
        from billing.discounts import apply_discount


        def run_custom(x, apply_discount):
            return apply_discount(x)
        """
    )
    after_shadow = textwrap.dedent(
        """\
        from billing.discounts import apply_discount


        def run_custom(x, apply_discount):
            return x
        """
    )
    # Parameter `apply_discount` is caught by `PATCH_STOPPED_READING_ITS_INPUTS`,
    # and NOT misattributed to `lost_callees`.
    r_shadow = dep_gate.gate(before_shadow, after_shadow)
    assert r_shadow["lost_callees"] == []
    assert r_shadow["status"] == "REFUSED"
    assert r_shadow["reason"] == "PATCH_STOPPED_READING_ITS_INPUTS: run_custom(apply_discount)"
