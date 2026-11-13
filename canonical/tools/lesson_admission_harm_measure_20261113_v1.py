#!/usr/bin/env python3
"""What the live learn path executes before it grants permanence. Measured, both ways.

THE ONE QUESTION
----------------
When `VerifiedSkillStore.crystallize_code_fix` returns `crystallized: True`, how many programs the
lesson was NOT taught on has it run? Before this gate: zero, even with its strongest option
(`oracle=` + `probes=`), because the learn path hands the probe the taught snippet as the victim.

This tool runs the same boundary lesson through the real store three times and reports what each
path executed and what the persisted rule then did to two unseen programs with their own specs.

Run it:  python3 canonical/tools/lesson_admission_harm_measure_20261113_v1.py --json

Authority: NONE. Sandbox measurement on a temporary database. No receipt, no capability, no
claim about programs outside the victims named here.
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

from canonical.swe_kernel import lesson_admission_gate_v1 as G  # noqa: E402
from canonical.swe_kernel.verified_skill_crystallizer_v1 import (  # noqa: E402
    VerifiedSkillStore,
    _load_rules,
    apply_crystallized_code_rule,
)
from canonical.tools.rule_generalization_probe_v1 import run_snippet  # noqa: E402

SCHEMA = "PROJECT_BRAIN_LESSON_ADMISSION_HARM_MEASURE_20261113_V1"

STRICT_VICTIM = "def bucket(z):\n    return z <= 100\n"
INCLUSIVE_VICTIM = "def cap(n):\n    return n <= 100\n"
#: `<=` appears only where n > 1000, and there BOTH predicates are False, so the edit cannot
#: change this program's answer at any integer. The probe points cover both branches.
GUARDED_VICTIM = ("def guarded(n):\n    if n > 1000:\n        return n <= 100\n"
                  "    return n < 100\n")
GUARDED_POINTS = (0, 99, 100, 101, 1001, 5000)


def _outcome(victim: str, spec: Any, points: Any, rule: Any) -> str:
    edited = apply_crystallized_code_rule(victim, rule)
    if edited is None:
        return G.NOT_APPLICABLE
    before_ok = all(run_snippet(victim, (p,)) == spec(victim, p) for p in points)
    after_ok = all(run_snippet(edited, (p,)) == spec(victim, p) for p in points)
    if before_ok and not after_ok:
        return G.BROKEN
    if not before_ok and after_ok:
        return G.REPAIRED
    return G.PRESERVED if after_ok else G.STILL_WRONG


def transfer_victim() -> G.Victim:
    return G.Victim("strict_bucket", STRICT_VICTIM, G.strict_spec, G.POINTS)


def falsification_victim() -> G.Victim:
    """Already correct, the rule FIRES on it, and it stays correct on both branches."""
    return G.Victim("guarded_strict", GUARDED_VICTIM, G.strict_spec, GUARDED_POINTS)


def harmful_victim() -> G.Victim:
    """Already correct under its OWN inclusive contract; the lesson breaks it at 100."""
    return G.Victim("inclusive_cap", INCLUSIVE_VICTIM, G.inclusive_spec, G.POINTS)


def measure() -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        db = pathlib.Path(tmp) / "skills.sqlite"
        store = VerifiedSkillStore(db_path=db, seed=False)

        # 1. The live path as shipped: strongest available option, no held-out victims.
        legacy = store.crystallize_code_fix(
            before_snippet=G.BEFORE, after_snippet=G.AFTER, language="python",
            error_class="BOUNDARY", oracle=G.strict_spec, probes=G.POINTS,
        )
        legacy_rule = _load_rules(db, "python")[0]
        legacy_after = {
            "strict_bucket": _outcome(STRICT_VICTIM, G.strict_spec, G.POINTS, legacy_rule),
            "inclusive_cap": _outcome(INCLUSIVE_VICTIM, G.inclusive_spec, G.POINTS, legacy_rule),
        }
        legacy_report = {
            "crystallized": legacy.get("crystallized"),
            "state": legacy.get("state"),
            "recorded_oracle_probe": legacy_rule.get("oracle_probe"),
            "recorded_admission_verdict": (legacy_rule.get("admission") or {}).get("verdict"),
            "held_out_programs_executed_before_write":
                (legacy_rule.get("oracle_probe") or {}).get("held_out_programs_executed"),
            "what_the_active_rule_then_did": legacy_after,
            "rows_in_store": len(_load_rules(db, "python")),
        }

        # 2. The same lesson, same store, with the victims the gate asks for.
        gated_db = pathlib.Path(tmp) / "gated.sqlite"
        gated_store = VerifiedSkillStore(db_path=gated_db, seed=False)
        refused = gated_store.crystallize_code_fix(
            before_snippet=G.BEFORE, after_snippet=G.AFTER, language="python",
            error_class="BOUNDARY", oracle=G.strict_spec, probes=G.POINTS,
            admission_victims=[transfer_victim(), harmful_victim()],
        )
        gated_report = {
            "crystallized": refused.get("crystallized"),
            "reason": refused.get("reason"),
            "verdict": (refused.get("admission") or {}).get("verdict"),
            "counts": (refused.get("admission") or {}).get("counts"),
            "rows_in_store": len(_load_rules(gated_db, "python")),
        }

        # 3. A suite where the falsification program is touched and survives.
        safe_db = pathlib.Path(tmp) / "safe.sqlite"
        safe_store = VerifiedSkillStore(db_path=safe_db, seed=False)
        admitted = safe_store.crystallize_code_fix(
            before_snippet=G.BEFORE, after_snippet=G.AFTER, language="python",
            error_class="BOUNDARY", oracle=G.strict_spec, probes=G.POINTS,
            admission_victims=[transfer_victim(), falsification_victim()],
        )
        safe_rows = _load_rules(safe_db, "python")
        safe_report = {
            "crystallized": admitted.get("crystallized"),
            "reason": admitted.get("reason"),
            "rows_in_store": len(safe_rows),
            "recorded_admission": (safe_rows[0].get("admission") if safe_rows else None),
        }

    return {
        "schema": SCHEMA,
        "lesson": {"before": G.BEFORE, "after": G.AFTER, "probes": list(G.POINTS)},
        "live_path_without_victims": legacy_report,
        "live_path_with_gate_and_harmful_victim": gated_report,
        "live_path_with_gate_and_safe_suite": safe_report,
        "authority": "NONE",
        "whole_task_correctness_proved": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = measure()
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        legacy = report["live_path_without_victims"]
        gated = report["live_path_with_gate_and_harmful_victim"]
        safe = report["live_path_with_gate_and_safe_suite"]
        print(f"without victims : crystallized={legacy['crystallized']} state={legacy['state']} "
              f"held_out_programs_executed={legacy['held_out_programs_executed_before_write']} "
              f"admission={legacy['recorded_admission_verdict']}")
        for name, outcome in legacy["what_the_active_rule_then_did"].items():
            print(f"    {name}: {outcome}")
        print(f"with the gate   : crystallized={gated['crystallized']} rows={gated['rows_in_store']} "
              f"{gated['reason']}")
        print(f"safe suite      : crystallized={safe['crystallized']} rows={safe['rows_in_store']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
