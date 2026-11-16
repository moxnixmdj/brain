#!/usr/bin/env python3
"""Buy scope for the shipped skill bundle and write it, with a receipt, in one run.

`VERIFIED_SKILLS_BUNDLE_V1` shipped counts; `skill_scope_ledger_v1` measured `5/5
EXACT_MATCH_ONLY` because no rule carried a state. This tool runs
`skill_scope_bundle_v1.attach_scopes` over the bundle, writes the scoped bundle in place (or to
`--output`), and writes a receipt recording, per rule, the status bought, the observations spent,
and -- for every rule with an identified scope -- BOTH NUMBERS MOVING on its paired victims:
repairs kept, breakages refused. A scope that does not move both numbers is decoration and the
receipt says so by showing the counts.

Authority: NONE. Producer-run measurement; every verdict comes from executing a victim against
its own specification. Zero model dependency.

Usage:
    python canonical/tools/attach_shipped_skill_scopes_v1.py \
        [--bundle PATH] [--output PATH] [--receipt PATH] [--print-report]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import skill_scope_acquisition_v1 as acq  # noqa: E402
from canonical.swe_kernel import skill_scope_bundle_v1 as ssb  # noqa: E402

DEFAULT_BUNDLE = ROOT / "canonical" / "astra_runtime" / "skills" / "VERIFIED_SKILLS_BUNDLE_V1.json"
DEFAULT_RECEIPT = ROOT / "canonical" / "astra_runtime" / "skills" / "SKILL_SCOPE_ATTACHMENT_RECEIPT_V1.json"


def _both_numbers(bundle_before: dict[str, Any], bundle_after: dict[str, Any]) -> dict[str, Any]:
    """For every identified rule: unscoped breakage on its paired victims vs gated refusal."""
    before_by_id = {e.get("skill_id"): e for e in bundle_before.get("rules") or ()}
    per_rule: list[dict[str, Any]] = []
    totals = {"repaired_unscoped": 0, "broke_correct_unscoped": 0,
              "gated_admitted_defective": 0, "gated_refused_correct": 0}
    for entry in bundle_after.get("rules") or ():
        rule = entry.get("rule") or {}
        scope = rule.get("scope") or {}
        if not str(scope.get("status") or "").startswith("IDENTIFIED"):
            continue
        sid = entry.get("skill_id")
        original_rule = (before_by_id.get(sid) or {}).get("rule") or rule
        victims, not_bought = ssb.paired_victims(original_rule)
        if not_bought or not victims:
            continue
        repaired = broke = admitted_defective = refused_correct = 0
        for victim in victims:
            verdict = acq.observe(original_rule, victim["source"], victim["spec"])["verdict"]
            if verdict == acq.REPAIRED:
                repaired += 1
            elif verdict == acq.BROKE_CORRECT:
                broke += 1
            faithful = (lambda s, spec=victim["spec"]: ssb._exec_ok(s, spec))
            gate = ssb.admit(rule, victim["source"], language=str(rule.get("language") or "python"),
                             verifier=faithful)
            defective = verdict == acq.REPAIRED
            if gate["admitted"] and defective:
                admitted_defective += 1
            if (not gate["admitted"]) and verdict == acq.BROKE_CORRECT:
                refused_correct += 1
        totals["repaired_unscoped"] += repaired
        totals["broke_correct_unscoped"] += broke
        totals["gated_admitted_defective"] += admitted_defective
        totals["gated_refused_correct"] += refused_correct
        per_rule.append({
            "skill_id": sid,
            "repaired_unscoped": repaired,
            "broke_correct_unscoped": broke,
            "gated_admitted_defective": admitted_defective,
            "gated_refused_correct": refused_correct,
            "both_numbers_moved": admitted_defective == repaired and refused_correct == broke,
        })
    return {"per_rule": per_rule, "totals": totals,
            "all_identified_rules_moved_both_numbers": all(
                r["both_numbers_moved"] for r in per_rule) if per_rule else None}


def run(bundle_path: pathlib.Path, output_path: pathlib.Path,
        receipt_path: pathlib.Path) -> dict[str, Any]:
    bundle_before = ssb.load_bundle(bundle_path)
    scoped, report = ssb.attach_scopes(bundle_before)
    both = _both_numbers(bundle_before, scoped)
    ssb.save_bundle(scoped, output_path)
    receipt = {
        "schema": ssb.SCHEMA + "__RECEIPT",
        "authority": ssb.AUTHORITY,
        "bundle": str(bundle_path),
        "output": str(output_path),
        "report": report,
        "both_numbers": both,
        "whole_task_correctness_proved": False,
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=1, sort_keys=True), encoding="utf-8")
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=pathlib.Path, default=DEFAULT_BUNDLE)
    parser.add_argument("--output", type=pathlib.Path, default=None,
                        help="defaults to --bundle (in place)")
    parser.add_argument("--receipt", type=pathlib.Path, default=DEFAULT_RECEIPT)
    parser.add_argument("--print-report", action="store_true")
    args = parser.parse_args(argv)
    output = args.output or args.bundle
    receipt = run(args.bundle, output, args.receipt)
    if args.print_report:
        print(json.dumps(receipt, indent=1, sort_keys=True))
    else:
        rep = receipt["report"]
        both = receipt["both_numbers"]
        print(f"rules={rep['rule_count']} identified={rep['identified']} "
              f"not_bought={rep['not_bought']} receipt={args.receipt}")
        for entry in rep["entries"]:
            print(f"  {entry['skill_id']} {entry.get('language')}: {entry['status']}")
        if both["per_rule"]:
            print(f"both_numbers_moved={both['all_identified_rules_moved_both_numbers']} "
                  f"totals={both['totals']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
