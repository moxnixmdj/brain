#!/usr/bin/env python3
"""Measure whether the four verification gates are actually wired into the skill learn/apply path.

`rule_generalization_probe_v1` recorded a structural defect in its docstring:
    "Three of the four checks this session shipped were never called by the learn path at all --
     they existed and measured nothing. A check whose success case is 'I didn't look' is the same
     failure in a new place."

On `d677e54e`, four verification modules existed in `canonical/swe_kernel/` and `canonical/tools/`:
  1. `skill_recheck_v1`: re-executes a stored rule against its `provenance.taught_sources`.
     - Defect A: `crystallize_code_fix` used `ON CONFLICT(skill_id) DO UPDATE SET verified_hits=...,
       provenance_json=...` without updating `pattern_json`, silently dropping `taught_sources`
       whenever an existing `skill_id` was re-taught or taught on a second distinct example.
     - Defect B: `import_bundle` merged `provenance_json` and `INVALIDATED`, but dropped
       `provenance.taught_sources` when merging into an existing row.
     - Defect C: `recall_and_apply_verified` never called `skill_recheck_v1.recheck(rule)`, so a
       rule whose `recheck(rule)["verdict"] == "FAIL"` still fired at recall time.
     - Defect D: `canonical/astra_runtime/skills/VERIFIED_SKILLS_BUNDLE_V1.json` had `0/5`
       `taught_sources` (`auditability_report_v1` layer `skills`: `0/5 (0.0%)` checkable).
  2. `skill_precondition_presence_v1`: checks `defect_is_present` / `gate` (`PRESENT`, `ABSENT`,
     `REFUSED`, `UNOBSERVABLE`), had zero callers in `canonical/` and no test file.
  3. `skill_sequence_verify_v1`: detects 2-step reversions (`STEP_REVERTED_EARLIER_STATE`) and
     no-ops (`STEP_DID_NOTHING`), had zero callers in `VerifiedSkillStore`.
  4. `rule_generalization_probe_v1`: executes a learned rule against an oracle on probe inputs
     (`HOLDS`, `BREAKS`, `NOT_APPLICABLE`, `REFUSED`, `NO_RULE`), had zero callers in
     `VerifiedSkillStore`.

Authority: NONE. `truth.achieved` = False. Zero model calls.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sqlite3
import sys
import tempfile
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from canonical.swe_kernel import (
    skill_precondition_presence_v1 as P,
    skill_recheck_v1 as R,
    skill_sequence_verify_v1 as S,
)
from canonical.swe_kernel.verified_skill_crystallizer_v1 import (
    VerifiedSkillStore,
    _seed_bundle_path,
)
from canonical.tools import rule_generalization_probe_v1 as G

SCHEMA = "PROJECT_BRAIN_LEARN_PATH_VERIFICATION_WIRING_V1"


def probe_recheck_wiring() -> dict[str, Any]:
    """Verify `skill_recheck_v1` across multi-example teaching, bundle merge, stale recall, and shipped bundle."""
    with tempfile.TemporaryDirectory() as td:
        db = pathlib.Path(td) / "recheck.sqlite"
        store = VerifiedSkillStore(db_path=db, seed=False)
        r1 = store.crystallize_code_fix(
            before_snippet="def f(x):\n    return x <= 10\n",
            after_snippet="def f(x):\n    return x < 10\n",
            language="python",
            error_class="BOUNDARY",
        )
        r2 = store.crystallize_code_fix(
            before_snippet="def g(y):\n    return y <= 20\n",
            after_snippet="def g(y):\n    return y < 20\n",
            language="python",
            error_class="BOUNDARY",
        )
        rep = R.recheck_store(db)
        sources_checked = rep["rules"][0].get("sources_checked", 0)

        # Corrupt the stored taught_sources so `recheck(rule)` returns FAIL, and verify recall blocks it
        conn = sqlite3.connect(str(db))
        with conn:
            row = conn.execute("SELECT skill_id, pattern_json FROM crystallized_skills").fetchone()
            rule_obj = json.loads(row[1])
            rule_obj["provenance"]["taught_sources"][0]["after"] = "def f(x):\n    return False\n"
            conn.execute(
                "UPDATE crystallized_skills SET pattern_json = ? WHERE skill_id = ?",
                (json.dumps(rule_obj), row[0]),
            )
            conn.execute("UPDATE skill_store_meta SET generation = generation + 1 WHERE id=1")
        conn.close()

        stale_recheck = R.recheck_store(db)
        stale_recall = store.recall_and_apply_verified(
            source_text="def h(z):\n    return z <= 30\n",
            language="python",
            error_class="BOUNDARY",
            verifier=lambda c: "< 30" in c,
        )

        # Verify re-teaching a seeded sourceless rule attaches taught_sources (ON CONFLICT fix)
        seeded_db = pathlib.Path(td) / "seeded.sqlite"
        seeded_store = VerifiedSkillStore(db_path=seeded_db, seed=True)
        before_seed_recheck = R.recheck_store(seeded_db)
        seeded_store.crystallize_code_fix(
            before_snippet="def discount(price, pct):\n    return price + price * pct\n",
            after_snippet="def discount(price, pct):\n    return price - price * pct\n",
            language="python",
            error_class="python_test_repair",
        )
        after_seed_recheck = R.recheck_store(seeded_db)

    return {
        "same_skill_id_across_two_examples": r1["skill_id"] == r2["skill_id"],
        "sources_checked_after_second_example": sources_checked,
        "stale_rule_recheck_fails": stale_recheck["counts"].get(R.FAIL) == 1,
        "stale_rule_blocked_at_recall": stale_recall is None,
        "seeded_before_reteach_pass": before_seed_recheck.get("counts", {}).get(R.PASS),
        "seeded_after_reteach_pass": after_seed_recheck.get("counts", {}).get(R.PASS),
        "ok": (
            r1["skill_id"] == r2["skill_id"]
            and sources_checked == 2
            and stale_recheck["counts"].get(R.FAIL) == 1
            and stale_recall is None
            and before_seed_recheck.get("counts", {}).get(R.PASS) == 0
            and after_seed_recheck.get("counts", {}).get(R.PASS) == 1
        ),
    }


def probe_precondition_wiring() -> dict[str, Any]:
    """Verify `skill_precondition_presence_v1` gates both `crystallize_code_fix` and `recall_and_apply_verified`."""
    with tempfile.TemporaryDirectory() as td:
        db = pathlib.Path(td) / "precond.sqlite"
        store = VerifiedSkillStore(db_path=db, seed=False)
        # 1. Absent defect (comparison operator unchanged) is refused at learn time
        refused_absent = store.crystallize_code_fix(
            before_snippet="def f(x):\n    return x < 10\n",
            after_snippet="def f(x):\n    return x < 20\n",
            language="python",
            error_class="BOUNDARY",
            precondition_field="comparison_operator",
            precondition_accessor=P.comparison_operator,
        )
        # 2. Unobservable defect (accessor=None) is refused at learn time
        refused_unobservable = store.crystallize_code_fix(
            before_snippet="def f(x):\n    return x <= 10\n",
            after_snippet="def f(x):\n    return x < 10\n",
            language="python",
            error_class="BOUNDARY",
            precondition_field="comparison_operator",
            precondition_accessor=None,
        )
        # 3. Present defect (`<=` -> `<`) is accepted and recorded
        accepted = store.crystallize_code_fix(
            before_snippet="def f(x):\n    return x <= 10\n",
            after_snippet="def f(x):\n    return x < 10\n",
            language="python",
            error_class="BOUNDARY",
            precondition_field="comparison_operator",
            precondition_accessor=P.comparison_operator,
        )
        # 4. Recall with precondition_accessor applies when defect (`<=`) is present
        applied_hit = store.recall_and_apply_verified(
            source_text="def g(y):\n    return y <= 50\n",
            language="python",
            error_class="BOUNDARY",
            verifier=lambda c: "< 50" in c,
            precondition_accessor=P.comparison_operator,
        )
        # 5. Recall with raising accessor is refused
        def raising_acc(_s: str) -> Any:
            raise ValueError("unobservable")

        blocked_hit = store.recall_and_apply_verified(
            source_text="def g(y):\n    return y <= 50\n",
            language="python",
            error_class="BOUNDARY",
            verifier=lambda c: "< 50" in c,
            precondition_accessor=raising_acc,
        )

    return {
        "refused_absent_reason": refused_absent.get("reason"),
        "refused_unobservable_reason": refused_unobservable.get("reason"),
        "accepted_crystallized": bool(accepted.get("crystallized")),
        "applied_when_present": applied_hit is not None,
        "blocked_when_accessor_raises": blocked_hit is None,
        "ok": (
            refused_absent.get("crystallized") is False
            and refused_absent.get("reason") == "PRECONDITION_DEFECT_ABSENT"
            and refused_unobservable.get("crystallized") is False
            and refused_unobservable.get("reason") == "PRECONDITION_DEFECT_UNOBSERVABLE"
            and accepted.get("crystallized") is True
            and applied_hit is not None
            and blocked_hit is None
        ),
    }


def probe_sequence_wiring() -> dict[str, Any]:
    """Verify `skill_sequence_verify_v1` blocks 2-step reversions and detects interference in `VerifiedSkillStore`."""
    with tempfile.TemporaryDirectory() as td:
        db = pathlib.Path(td) / "seq.sqlite"
        store = VerifiedSkillStore(db_path=db, seed=False)
        store.crystallize_code_fix(
            before_snippet="def f(x):\n    return x <= 10\n",
            after_snippet="def f(x):\n    return x < 10\n",
            language="python",
            error_class="A",
        )
        store.crystallize_code_fix(
            before_snippet="def f(x):\n    return x < 10\n",
            after_snippet="def f(x):\n    return x <= 10\n",
            language="python",
            error_class="B",
        )
        start = "def f(x):\n    return x <= 10\n"
        interference = store.audit_sequence_interference(start, language="python")
        rules_a = store.lookup_rules("python", error_class="A")
        rules_b = store.lookup_rules("python", error_class="B")
        explicit_seq = store.apply_verified_sequence(
            source_text=start,
            language="python",
            verifier=lambda _c: True,
            rules=rules_a + rules_b,
        )
        # Step 1 succeeds (`<=` -> `<`), Step 2 with `prior_sources=[start]` must NOT revert to `start`
        step1 = store.recall_and_apply_verified(
            source_text=start,
            language="python",
            error_class="A",
            verifier=lambda c: "< 10" in c,
        )
        step2_revert = store.recall_and_apply_verified(
            source_text=step1["patched_source"],
            language="python",
            error_class="B",
            verifier=lambda _c: True,
            prior_sources=[start],
        )

    return {
        "interference_found": interference.get("interference_found"),
        "explicit_opposing_sequence_verdict": explicit_seq.get("verdict"),
        "explicit_opposing_sequence_verified": explicit_seq.get("verified"),
        "step2_revert_blocked_by_prior_sources": step2_revert is None,
        "ok": (
            interference.get("interference_found") is True
            and explicit_seq.get("verdict") == S.FAIL
            and explicit_seq.get("verified") is False
            and step2_revert is None
        ),
    }


def probe_oracle_generalization_wiring() -> dict[str, Any]:
    """Verify `rule_generalization_probe_v1` gates `crystallize_code_fix` and invalidates on held-out victim BREAKS."""
    strict_oracle = lambda _src, pt: pt < 100
    inclusive_50_oracle = lambda _src, pt: pt <= 50

    with tempfile.TemporaryDirectory() as td:
        db = pathlib.Path(td) / "oracle.sqlite"
        store = VerifiedSkillStore(db_path=db, seed=False)
        # 1. Wrong-direction edit (`<` -> `<=` under strict `< 100` oracle) is refused at learn time
        wrong_dir = store.crystallize_code_fix(
            before_snippet="def classify(x):\n    return x < 100\n",
            after_snippet="def classify(x):\n    return x <= 100\n",
            language="python",
            error_class="BOUNDARY",
            oracle=strict_oracle,
            probes=(0, 99, 100, 101),
        )
        # 2. Right-direction edit (`<=` -> `<` under strict `< 100` oracle) is accepted at learn time
        right_dir = store.crystallize_code_fix(
            before_snippet="def classify(x):\n    return x <= 100\n",
            after_snippet="def classify(x):\n    return x < 100\n",
            language="python",
            error_class="BOUNDARY",
            oracle=strict_oracle,
            probes=(0, 99, 100, 101),
        )
        sid = right_dir["skill_id"]
        # 3. Probing the stored rule on a held-out victim with a same-convention oracle HOLDS
        holds_probe = store.probe_skill_on_victim(
            sid,
            "def tier(a):\n    return a <= 100\n",
            oracle=strict_oracle,
            probes=(99, 100, 101),
        )
        # 4. Probing the stored rule on a held-out victim with an inclusive-50 convention BREAKS and invalidates
        breaks_probe = store.probe_skill_on_victim(
            sid,
            "def tier(a):\n    return a <= 50\n",
            oracle=inclusive_50_oracle,
            probes=(49, 50, 51),
            invalidate_on_break=True,
        )
        # 5. Once invalidated by the victim probe, recall no longer fires the rule
        post_invalidation_recall = store.recall_and_apply_verified(
            source_text="def tier(a):\n    return a <= 100\n",
            language="python",
            error_class="BOUNDARY",
            verifier=lambda _c: True,
        )

    return {
        "wrong_direction_refused_at_learn": wrong_dir.get("crystallized") is False,
        "wrong_direction_reason": wrong_dir.get("reason"),
        "right_direction_crystallized": right_dir.get("crystallized") is True,
        "victim_same_convention_verdict": holds_probe.get("verdict"),
        "victim_other_convention_verdict": breaks_probe.get("verdict"),
        "victim_break_invalidated_rule": breaks_probe.get("invalidated") is True,
        "post_invalidation_recall_blocked": post_invalidation_recall is None,
        "ok": (
            wrong_dir.get("crystallized") is False
            and "ORACLE_PROBE_BREAKS" in str(wrong_dir.get("reason"))
            and right_dir.get("crystallized") is True
            and holds_probe.get("verdict") == G.HOLDS
            and breaks_probe.get("verdict") == G.BREAKS
            and breaks_probe.get("invalidated") is True
            and post_invalidation_recall is None
        ),
    }


def run_all() -> dict[str, Any]:
    recheck_res = probe_recheck_wiring()
    precond_res = probe_precondition_wiring()
    seq_res = probe_sequence_wiring()
    oracle_res = probe_oracle_generalization_wiring()
    return {
        "schema": SCHEMA,
        "authority": "NONE",
        "truth_achieved": False,
        "recheck_wiring": recheck_res,
        "precondition_wiring": precond_res,
        "sequence_wiring": seq_res,
        "oracle_generalization_wiring": oracle_res,
        "all_ok": (
            recheck_res["ok"]
            and precond_res["ok"]
            and seq_res["ok"]
            and oracle_res["ok"]
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = run_all()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for k in ("recheck_wiring", "precondition_wiring", "sequence_wiring", "oracle_generalization_wiring"):
            print(f"{k:32} ok={report[k]['ok']}")
        print(f"all_ok={report['all_ok']}")
    return 0 if report["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
