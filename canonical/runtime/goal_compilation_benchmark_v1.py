#!/usr/bin/env python3
"""Fixed, measured benchmark for plain-goal -> executable-plan compilation.

Why this exists
---------------
`goal_compiler.compile_goal` selects the correct live capability for ordinary
natural-language goals (measured: top-1 correct on every benchmark goal), but
then discards the candidate inside `_bind_inputs` with
``GOAL_INPUT_BINDING_REQUIRED:<arg>`` whenever the goal does not literally name
every input and output file. The result is
``GOAL_COMPILATION_NO_VERIFIED_CAPABILITY_MATCH`` for goals the registry can
actually satisfy.

This module measures that gap honestly. It reports, per goal:
  * whether compilation succeeded,
  * the failure cause when it did not,
  * the best-ranked capability that reached input binding (the near-miss),
  * which placeholder could not be bound.

Nothing here executes anything. It is a read-only measurement so that any
change to selection or binding is judged against a fixed, versioned set of
goals rather than against a hand-picked example.

Zero external model. Zero spend. Fails closed by reporting, never by guessing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]

SCHEMA = "GOAL_COMPILATION_BENCHMARK_V1"
AUTHORITY = "NONE"

# Each goal is ordinary phrasing an owner would actually type. ``expected`` is
# the live capability identity that must be reachable; it is asserted against
# the registry so the benchmark cannot rot silently when a capability is
# renamed or deleted.
BENCHMARK_GOALS: List[Dict[str, Any]] = [
    {
        "id": "BENCH_TAR_GZ_CREATE_AND_VERIFY",
        "goal": (
            "Create a tar.gz archive from a manifest and verify the archive "
            "against that manifest."
        ),
        "expected": [
            "archive.tar_gz.create_from_manifest",
            "archive.verify.tar_gz.gnu",
        ],
    },
    {
        "id": "BENCH_PDF_EXTRACT_TEXT",
        "goal": "Read a PDF and extract its text.",
        "expected": ["pdf.extract.text.pypdf"],
    },
    {
        "id": "BENCH_SQLITE_CREATE_INSERT_QUERY",
        "goal": (
            "Create a sqlite table with a schema, then insert records, then "
            "query the records back."
        ),
        "expected": ["sqlite.table.create_from_json_records"],
    },
    {
        "id": "BENCH_GROUNDING_AND_VERIFY",
        "goal": (
            "Compile a plain goal into a bound capability and verify the "
            "grounding."
        ),
        "expected": [
            "plain_goal.bound_capability.grounding.stdlib",
            "plain_goal.bound_capability.grounding.verify.stdlib",
        ],
    },
    {
        "id": "BENCH_SOURCE_AUDIT_WRITE_JSON",
        "goal": "Audit python source structure and write the audit to a JSON file.",
        "expected": ["python.source.audit.ast"],
    },
    {
        "id": "BENCH_EVIDENCE_RANK_BIND",
        "goal": (
            "Extract evidence from a source, then rank it, then bind it to a claim."
        ),
        "expected": ["source.evidence.extract.objective_grounded.stdlib"],
    },
    {
        "id": "BENCH_JSON_FETCH_CONSISTENCY",
        "goal": "Fetch a JSON document and assess its internal consistency.",
        "expected": ["knowledge.consistency.assess"],
    },
    {
        "id": "BENCH_UNITTEST_PASS_RATE",
        "goal": "Run the unittest corpus and produce a pass rate report.",
        "expected": ["python.tests.audit.unittest"],
    },
    {
        "id": "BENCH_MARKDOWN_TO_DECISION",
        "goal": "Summarize a markdown document into a decision record.",
        "expected": ["decision.synthesis.typed.stdlib"],
    },
]


# Goals that COMPILE but select a capability that merely shares vocabulary with
# the goal. Both have the SAME root cause, measured rather than guessed:
#
#   THE BEST-MATCHING CAPABILITY IS UNBINDABLE, SO THE COMPILER SUBSTITUTES THE
#   BEST CAPABLE ONE -- however weakly it matches -- and reports success.
#
#   BENCH_JSON_FETCH_CONSISTENCY  (pre-existing: also wrong at base 9554215)
#     knowledge.json.fetch.external    score 12  UNBINDABLE
#     knowledge.consistency.assess     score  8  UNBINDABLE
#     terminal.kstar.root.assess.stdlib score 2  bindable  <-- selected
#     Score 2 beat 12 and 8 purely because it was the only callable candidate.
#     It matches on the single word "assess" inside its own capability id.
#
#   BENCH_MARKDOWN_TO_DECISION
#     decision.synthesis.typed.stdlib  score 14  UNBINDABLE
#       (requires structured.decision_evidence.available; none exists)
#     document.convert.markdown_pdf.pandoc_weasyprint  <-- selected, a CONVERTER
#     that then reports success for a summary it never performed.
#
# Both scoring-level fixes were MEASURED AND REVERTED, which is why this file
# documents the gap instead of papering over it:
#
#   1. Require the goal's head verb to appear in the capability's declared
#      surface -> benchmark 5/9 fell to 2/9 and four existing tests broke,
#      because most capabilities do not literally contain the caller's verb.
#   2. Refuse any match scoring below a minimum (MIN_MATCH_SCORE=4) -> correctly
#      rejected the score-2 candidate, but the same goal then selected
#      docx.document.create_from_json_record at score 25. One wrong capability
#      swapped for another; no measured gain.
#
# The real fix is not in the scorer. It is to REFUSE when the best-matching
# capability exists but cannot be bound, instead of silently downgrading to the
# best callable one.
KNOWN_SELECTION_GAPS = {
    "BENCH_JSON_FETCH_CONSISTENCY": (
        "BEST_MATCHES_UNBINDABLE__knowledge.json.fetch.external_SCORE_12_AND_"
        "knowledge.consistency.assess_SCORE_8__SELECTED_terminal.kstar.root.assess.stdlib_"
        "SCORE_2_ON_ONE_IDENTITY_TOKEN__PRE_EXISTING_AT_BASE_9554215"
    ),
    "BENCH_MARKDOWN_TO_DECISION": (
        "BEST_MATCH_UNBINDABLE__decision.synthesis.typed.stdlib_SCORE_14_REQUIRES_"
        "structured.decision_evidence.available__SELECTED_A_MARKDOWN_TO_PDF_CONVERTER"
    ),
}

# A separate, real COVERAGE gap. Not a wrong selection -- this goal's expected
# first capability IS selected correctly -- so it is recorded apart from
# KNOWN_SELECTION_GAPS to keep the two failure modes from being conflated.
#
# No capability in the 363-capability live registry declares "insert" in its
# identity, provides, or keywords (measured: 0 of 363), so the "insert records"
# clause of BENCH_SQLITE_CREATE_INSERT_QUERY has nothing correct to select and
# the compiler maps it to sqlite.table.verify_against_json_records instead. The
# third clause is fine: that capability legitimately declares "query".
KNOWN_COVERAGE_GAPS = {
    "BENCH_SQLITE_CREATE_INSERT_QUERY": (
        "NO_CAPABILITY_IN_THE_LIVE_REGISTRY_DECLARES_INSERT__0_OF_363__"
        "THE_INSERT_CLAUSE_HAS_NOTHING_CORRECT_TO_SELECT"
    ),
}


def benchmark_digest(goals: List[Mapping[str, Any]]) -> str:
    """Content address of the benchmark goal set itself."""
    canon = json.dumps(
        [{"id": g["id"], "goal": g["goal"], "expected": g["expected"]} for g in goals],
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def _ensure_repo_root() -> None:
    """Make `canonical` importable when run as a plain script from any cwd."""
    import sys

    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))


def _registry() -> Dict[str, Any]:
    _ensure_repo_root()
    from canonical.runtime import live_integrated_brain_v1 as lb

    return dict(lb.load_verified_registry())


def _parse_cause(exc: BaseException) -> Dict[str, Any]:
    text = str(exc)
    if ":" in text:
        head, _, payload = text.partition(":")
        try:
            detail = json.loads(payload)
            return {"cause": head, "detail": detail}
        except Exception:
            return {"cause": head, "detail": payload[:200]}
    return {"cause": text[:120] or type(exc).__name__, "detail": None}


def _near_miss(goal: str, registry: Mapping[str, Any]) -> Dict[str, Any]:
    """Best-ranked capability that reached binding, and why it was dropped."""
    _ensure_repo_root()
    from canonical.runtime import goal_compiler as gc

    scored: List[Any] = []
    for cid, entry in registry.items():
        if not isinstance(entry, dict):
            continue
        if entry.get("status") != "VERIFIED_BOUND_CAPABILITY":
            continue
        if not isinstance(entry.get("action_template"), dict):
            continue
        try:
            score, spec, _ev = gc._score(goal, cid, entry)
        except Exception:
            continue
        if score <= 0:
            continue
        try:
            gc._bind_inputs(goal, str(REPO_ROOT), entry, context_paths=None, future_clauses=None)
            return {"capability_id": cid, "score": score, "drop_reason": None}
        except Exception as exc:
            scored.append((score, spec, cid, str(exc)))
    scored.sort(key=lambda row: (-row[0], -row[1]))
    if not scored:
        return {"capability_id": None, "score": None, "drop_reason": "NO_LEXICAL_MATCH"}
    score, _spec, cid, message = scored[0]
    return {"capability_id": cid, "score": score, "drop_reason": message[:120]}


def run(goals: List[Mapping[str, Any]] | None = None) -> Dict[str, Any]:
    """Measure compile success for the fixed benchmark. Never raises for a goal."""
    _ensure_repo_root()
    from canonical.runtime.goal_compiler import compile_goal

    goals = list(goals if goals is not None else BENCHMARK_GOALS)
    registry = _registry()
    rows: List[Dict[str, Any]] = []
    for spec in goals:
        goal = str(spec["goal"])
        row: Dict[str, Any] = {
            "id": spec["id"],
            "goal": goal,
            "expected": list(spec["expected"]),
            "expected_present_in_registry": [
                cid for cid in spec["expected"] if cid in registry
            ],
        }
        try:
            plan = compile_goal(goal, registry, str(REPO_ROOT))
            row["compiled"] = True
            row["compiler_mode"] = (
                plan.get("compiler_mode") if isinstance(plan, dict) else None
            )
            row["failure"] = None
            row["near_miss"] = None
            # COMPILING IS NOT SELECTING CORRECTLY. A plan can compile against a
            # capability that merely shares vocabulary with the goal, so the
            # selected identities are recorded and checked against the expected
            # chain separately. Reporting only "compiled" would overstate the
            # gain, which is exactly the kind of claim this repo forbids.
            selected: List[str] = []
            if isinstance(plan, dict):
                for part in plan.get("compiled_parts") or []:
                    cid = (part or {}).get("selected_capability")
                    if cid:
                        selected.append(str(cid))
                if not selected and plan.get("selected_capability"):
                    selected.append(str(plan["selected_capability"]))
            row["selected"] = selected
            row["expected_first_selected"] = bool(
                spec["expected"] and selected and spec["expected"][0] in selected
            )
            row["expected_all_selected"] = all(
                cid in selected for cid in spec["expected"]
            )
            row["binding_source"] = (
                plan.get("binding_source") if isinstance(plan, dict) else None
            )
            # A goal that compiles against the wrong capability is worse than one
            # that refuses, so it is labelled rather than counted as a success.
            row["known_selection_gap"] = (
                KNOWN_SELECTION_GAPS.get(spec["id"])
                if not row["expected_first_selected"]
                else None
            )
        except Exception as exc:  # measurement must survive every failure mode
            row["compiled"] = False
            row["compiler_mode"] = None
            row["failure"] = _parse_cause(exc)
            row["near_miss"] = _near_miss(goal, registry)
            row["selected"] = []
            row["expected_first_selected"] = False
            row["expected_all_selected"] = False
            row["binding_source"] = None
            row["known_selection_gap"] = None
        rows.append(row)

    compiled = [r for r in rows if r["compiled"]]
    first_ok = [r for r in rows if r["expected_first_selected"]]
    all_ok = [r for r in rows if r["expected_all_selected"]]
    # Compiled, but against a capability that only shares vocabulary with the
    # goal. Counted separately so a rising compile rate cannot mask it.
    gapped = [r for r in rows if r["compiled"] and not r["expected_first_selected"]]
    causes = Counter(
        (r["failure"] or {}).get("cause") for r in rows if not r["compiled"]
    )
    dropped = Counter(
        ((r["near_miss"] or {}).get("drop_reason") or "")
        .split(":")[0]
        for r in rows
        if not r["compiled"] and r["near_miss"]
    )
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "benchmark_sha256": benchmark_digest(goals),
        "totals": {
            "goals": len(rows),
            "compiled": len(compiled),
            "failed": len(rows) - len(compiled),
            "compile_rate": round(len(compiled) / len(rows), 4) if rows else 0.0,
            # Reported alongside, never instead of, the compile rate.
            "expected_first_capability_selected": len(first_ok),
            "expected_full_chain_selected": len(all_ok),
            "expected_first_rate": round(len(first_ok) / len(rows), 4) if rows else 0.0,
            "compiled_against_wrong_capability": len(gapped),
        },
        "known_selection_gaps": {
            r["id"]: r["known_selection_gap"] for r in gapped
        },
        "failure_causes": dict(causes),
        "near_miss_drop_reasons": dict(dropped),
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", help="write the full measurement to this path")
    parser.add_argument("--quiet", action="store_true", help="summary only")
    args = parser.parse_args()

    report = run()
    totals = report["totals"]
    print(f"GOAL COMPILATION BENCHMARK {report['benchmark_sha256'][:16]}")
    print(
        "compiled {compiled}/{goals} ({rate:.1%})".format(
            compiled=totals["compiled"], goals=totals["goals"], rate=totals["compile_rate"]
        )
    )
    print(
        "expected capability selected {first}/{goals} ({rate:.1%}) -- compiling is not selecting correctly".format(
            first=totals["expected_first_capability_selected"],
            goals=totals["goals"],
            rate=totals["expected_first_rate"],
        )
    )
    if totals["compiled_against_wrong_capability"]:
        print(
            "compiled against the WRONG capability: {n} (see known_selection_gaps)".format(
                n=totals["compiled_against_wrong_capability"]
            )
        )
    if report["failure_causes"]:
        print("failure causes:", json.dumps(report["failure_causes"], sort_keys=True))
    if report["near_miss_drop_reasons"]:
        print("near-miss drops:", json.dumps(report["near_miss_drop_reasons"], sort_keys=True))
    if not args.quiet:
        for row in report["rows"]:
            mark = "OK  " if row["compiled"] else "FAIL"
            extra = ""
            if not row["compiled"]:
                extra = " <- " + str((row["failure"] or {}).get("cause"))
                near = row["near_miss"] or {}
                if near.get("capability_id"):
                    extra += f" | near-miss {near['capability_id']} ({near.get('drop_reason')})"
            print(f"  {mark} {row['id']}{extra}")
    if args.json:
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(report, indent=1, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
