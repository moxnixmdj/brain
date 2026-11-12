#!/usr/bin/env python3
"""Teach a lesson on one machine, ship it, land it on another, and try to show it wrong there.

The owner's sentence, taken literally:

    "After he does them at least once, he would learn all of those permanently."

"Permanently" is a claim about transport, and transport is the part that had never been
measured end to end here. The SQLite store is gitignored generated state: it does not travel.
The bundle is what travels (`canonical/astra_runtime/skills/VERIFIED_SKILLS_BUNDLE_V1.json`).
So the only sense in which a lesson is learned permanently is the sense in which a machine that
never saw the demonstration still holds it, and can still be contradicted by it.

This probe measures exactly that, in four steps, with no model and no network:

    A  teach one lesson through the ordinary path (`crystallize_code_fix`)
    B  ship it (`export_to_file`)
    C  land it on a store that has never learned anything (`import_bundle`)
    D  re-check it there, both ways: against the demonstration, and against the rule's own
       denotation (`skill_recheck_v1.self_witness`)

It then does the same for the five rules the repository ships, which is what a fresh clone
actually wakes up with.

Exit status: 0 when the lesson survives the round trip re-checkable, 1 when it does not,
2 when the measurement could not be run.

Authority: NONE. A PASS here means "the stored rule still reproduces the stored rewrite". That
is transport, not correctness, and it is not independent verification. Nothing is registered,
no family flips, `truth.achieved` stays false. $0, zero model dependency.

Usage:
    python3 skill_transport_roundtrip_probe_20261112.py [--json] [--keep]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import skill_recheck_v1 as R                      # noqa: E402
from canonical.swe_kernel.verified_skill_crystallizer_v1 import (           # noqa: E402
    VerifiedSkillStore,
    _seed_bundle_path,
)

SCHEMA = "PROJECT_BRAIN_SKILL_TRANSPORT_ROUNDTRIP_PROBE_V1"

BEFORE = "def total(prices):\n    return prices <= 0\n"
AFTER = "def total(prices):\n    return prices < 0\n"


def _counts(report: dict) -> dict:
    return {k: int((report.get("counts") or {}).get(k, 0)) for k in (R.PASS, R.FAIL, R.ABSENT)}


def measure(workdir: pathlib.Path) -> dict:
    """Run the round trip in a directory that is thrown away afterwards."""
    workdir.mkdir(parents=True, exist_ok=True)
    db_a = workdir / "machine_a.sqlite"
    db_b = workdir / "machine_b.sqlite"
    bundle = workdir / "SHIPPED.json"

    # --- A: learn it once, the ordinary way -------------------------------------------
    store_a = VerifiedSkillStore(db_path=db_a, seed=False)
    taught = store_a.crystallize_code_fix(
        before_snippet=BEFORE, after_snippet=AFTER, language="python",
        error_class="BOUNDARY", twin_oracle=lambda cand: "<=" not in cand,
    )
    on_a = R.recheck_store(db_a)

    # --- B: ship it --------------------------------------------------------------------
    exported = store_a.export_to_file(bundle)
    payload = json.loads(bundle.read_text(encoding="utf-8"))
    carries_source = any(
        isinstance(entry.get("rule"), dict)
        and isinstance((entry["rule"].get("provenance") or {}), dict)
        and (entry["rule"]["provenance"].get("taught_sources"))
        for entry in payload.get("rules") or [])

    # --- C: land it on a machine that has never learned anything -----------------------
    assert not db_b.exists()
    store_b = VerifiedSkillStore(db_path=db_b, seed=False)
    imported = store_b.import_bundle(bundle)

    # --- D: try to show it wrong there -------------------------------------------------
    on_b = R.recheck_store(db_b)

    # --- and what a fresh clone actually wakes up with ---------------------------------
    db_fresh = workdir / "fresh_clone.sqlite"
    assert not db_fresh.exists()
    seeded = VerifiedSkillStore(db_path=db_fresh)      # seeds itself from the shipped bundle
    shipped = R.recheck_store(db_fresh)
    shipped_bundle = R.recheck_bundle(_seed_bundle_path())

    return {
        "schema": SCHEMA,
        "authority": "NONE",
        "incremental_spend_usd": 0,
        "model_dependency_count": 0,
        "taught_on_a": bool(taught.get("crystallized")),
        "teach_refusal": taught.get("reason"),
        "recheck_on_a": _counts(on_a),
        "rules_exported": exported,
        "bundle_carries_the_demonstration": carries_source,
        "imported_on_b": {k: imported.get(k) for k in ("accepted", "merged", "refused")},
        "recheck_on_b": _counts(on_b),
        "self_witness_on_b": _counts({"counts": on_b.get("self_witness_counts")}),
        "recheckable_on_b_by_either": on_b.get("recheckable_any"),
        "fresh_clone_seeded_rules": seeded.count(),
        "fresh_clone_seed_refusals": (seeded.seed_result or {}).get("refused"),
        "shipped_store_recheck": _counts(shipped),
        "shipped_store_self_witness": _counts({"counts": shipped.get("self_witness_counts")}),
        "shipped_bundle_self_witness": _counts(shipped_bundle),
        "shipped_bundle_recheckable": shipped_bundle.get("recheckable"),
        "shipped_bundle_total": shipped_bundle.get("total"),
        "shipped_bundle_error": shipped_bundle.get("error"),
    }


def verdict(m: dict) -> tuple[bool, list[str]]:
    """What must hold for "learned once, permanently, on another machine" to be true here."""
    failures = []
    if not m["taught_on_a"]:
        failures.append(f"the lesson was never learned on A: {m['teach_refusal']}")
    if m["recheck_on_a"][R.PASS] != 1:
        failures.append("A could not re-check its own lesson against the demonstration")
    if not m["bundle_carries_the_demonstration"]:
        failures.append("the shipped bundle carries the rule but not the text it was taught on")
    if (m["imported_on_b"] or {}).get("accepted") != 1:
        failures.append(f"B refused the lesson: {m['imported_on_b']}")
    if m["recheck_on_b"][R.PASS] != 1:
        failures.append("B holds the rule but cannot re-check it: the lesson did not survive "
                        "the transport as a checkable lesson")
    if m["recheckable_on_b_by_either"] != 1:
        failures.append("B has no way to contradict the lesson it was given")
    if (m["shipped_bundle_total"] or 0) < 1:
        failures.append(f"the repository ships no lessons: {m['shipped_bundle_error']}")
    elif m["shipped_bundle_recheckable"] != m["shipped_bundle_total"]:
        failures.append("the repository ships lessons that cannot be shown wrong on a new machine")
    return (not failures), failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--keep", default=None, help="keep the scratch directory here")
    args = parser.parse_args(argv)

    workdir = pathlib.Path(args.keep) if args.keep else pathlib.Path(
        tempfile.mkdtemp(prefix="skill_transport_"))
    workdir.mkdir(parents=True, exist_ok=True)
    try:
        result = measure(workdir)
    except Exception as exc:
        print(f"cannot measure: {type(exc).__name__}:{exc}"[:200])
        return 2
    ok, failures = verdict(result)
    result["verdict"] = "SURVIVED" if ok else "BROKEN"
    result["failures"] = failures
    result["workdir"] = str(workdir)

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("skill transport round trip  --  authority NONE, $0, zero model\n")
        print(f"  teach on machine A                       {result['taught_on_a']}")
        print(f"  A can re-check it against the demo       {result['recheck_on_a']}")
        print(f"  rules shipped in the bundle              {result['rules_exported']}")
        print(f"  bundle carries the demonstration text    {result['bundle_carries_the_demonstration']}")
        print(f"  imported on machine B (never learned)    {result['imported_on_b']}")
        print(f"  B can re-check it against the demo       {result['recheck_on_b']}")
        print(f"  B can re-check it by self-witness        {result['self_witness_on_b']}")
        print(f"  B can contradict it by either            {result['recheckable_on_b_by_either']}/1")
        print()
        print(f"  a fresh clone seeds                      {result['fresh_clone_seeded_rules']} rules"
              f"  (refused {result['fresh_clone_seed_refusals']})")
        print(f"  shipped rules re-checkable by demo       "
              f"{result['shipped_store_recheck'][R.PASS]}/{result['shipped_bundle_total']}")
        print(f"  shipped rules re-checkable by witness    "
              f"{result['shipped_bundle_recheckable']}/{result['shipped_bundle_total']}")
        print()
        print(f"  VERDICT: {result['verdict']}")
        for line in failures:
            print(f"    - {line}")
        print("\nA lesson that survives as a RULE but not as a CHECK is history, not ability.")

    if args.keep is None and not ok:
        shutil.rmtree(workdir, ignore_errors=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
