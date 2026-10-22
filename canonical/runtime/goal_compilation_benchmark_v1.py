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
# THREE fixes were implemented, MEASURED, AND REVERTED. They are recorded here
# so the next reader does not repeat them, and because the third one disproves
# the obvious conclusion:
#
#   1. Require the goal's head verb to appear in the capability's declared
#      surface -> benchmark 5/9 fell to 2/9 and four existing tests broke,
#      because most capabilities do not literally contain the caller's verb.
#   2. Refuse any match scoring below a minimum (MIN_MATCH_SCORE=4) -> correctly
#      rejected the score-2 candidate, but the same goal then selected
#      docx.document.create_from_json_record at score 25. One wrong capability
#      swapped for another; no measured gain.
#   3. Refuse when the highest-scoring capability is not the selected one
#      (GOAL_COMPILATION_BEST_MATCH_NOT_SELECTED) -> did fix three wrong
#      selections, and broke three existing tests.
#
# WHY 3 FAILED, AND WHY IT IS NOT A TUNING PROBLEM.
#
# The counterexample is the QR goal in test_goal_compiler:
#
#     image.code.decode.zbarimg      score 22   a DECODER
#     image.qr.generate.qrencode     score 21   the GENERATOR the goal asks for
#
# The generator is CORRECT and is selected, but only because the decoder cannot
# be bound. So a correct selection can sit one point BELOW the best match, while
# a wrong one sat twenty-three points below it. Score rank and correctness are
# independent, so no threshold separates them. A cut tuned to clear both cases
# would be fitted to this 23-goal sample, not derived from anything.
#
# Note the trap in reading the numbers above: on these 23 goals every correct
# single-capability selection had a gap of exactly 0, which looks like clean
# separability. It was an artefact of the sample. The existing suite, which this
# benchmark does not contain, held the counterexample the whole time.
#
# WHAT WOULD ACTUALLY WORK, MEASURED RATHER THAN GUESSED.
#
# First, a correction to an earlier reading of this file. These five goals are
# NOT compound: every one of them expects exactly one capability. A compound
# planner would fix none of them.
#
# The real mechanism is precondition gating, not argument binding. Three of the
# correct capabilities declare ZERO inputs and are gated on an effect instead:
#
#     knowledge.consistency.assess      requires knowledge.observation.available
#     decision.synthesis.typed.stdlib   requires structured.decision_evidence.available
#     json.query.jq                     requires json.file.available
#
# So "unbindable" here means precondition-gated, which is a different failure
# from the one world_binding_v1 closes. That is why wiring that binder in never
# reached these goals.
#
# TWO OF THE THREE ARE UNEXECUTABLE, NOT MERELY UNBOUND. Searching every
# `provides` declaration across all 363 capabilities:
#
#     structured.decision_evidence.available  -> NO PRODUCER
#     json.file.available                     -> NO PRODUCER
#     knowledge.observation.available         -> knowledge.json.fetch.external
#
# For BENCH_MARKDOWN_TO_DECISION and EXT_JQ_TABLE the expected capability cannot
# run at all, because nothing in the registry produces what it requires.
# Selecting it would be WORSE than the current wrong selection: it would compile
# and then fail at execution. The honest fix for those two is to add a capability
# that produces the missing effect, not to change the compiler.
#
# A fourth attempt was made and measured on this basis, and is also a dead end.
# compile_goal reaches _compile_single_goal without a proposal binder, so
# _rank_bindable_candidates skips every capability declaring an effect_result
# binding before it is scored. Passing the binder in is correct but MEASURED AS
# A NO-OP: rankings are byte-identical with and without it, and the benchmark is
# unchanged at 17/23. The binder now runs and fails closed with
# PROPOSAL_EFFECT_PROVIDER_MISSING, because no upstream step produced the effect.
# The skip was hiding nothing.
#
# What is left, and none of it is a scoring change:
#   1. EXT_QR_GENERATE needs a semantic direction signal, distinguishing
#      "generate a QR code" from "decode a barcode". Lexical overlap cannot
#      carry it, which is why all three scoring attempts failed alike.
#   2. BENCH_MARKDOWN_TO_DECISION and EXT_JQ_TABLE need a capability that
#      produces structured.decision_evidence.available and json.file.available.
#      This is a capability gap, and it is the honest bottleneck for both.
#   3. The remaining two need the goal to ground a resource it never names.
#      "Query a JSON table" does not say which table, so refusing is arguably
#      the correct outcome; an invented input is an unverifiable act.
# BENCH_JSON_FETCH_CONSISTENCY used to belong here, recorded as
# BEST_MATCHES_UNBINDABLE because knowledge.json.fetch.external and
# knowledge.consistency.assess could not be called and the catch-all won on one
# identity token at score 2. That diagnosis was accurate and is now closed:
# both capabilities declare an effect_result input, and once the producer map
# derived from the registry's own `provides` is supplied they bind, so the
# better-scoring chained plan (knowledge.consistency.assess, score 22) is kept
# over the grounded catch-all (score 2). It is removed rather than re-labelled
# because the goal now selects correctly.
# Was 2, then 1, now 0. Each closure is recorded because the reason matters more
# than the count.
#
#   BENCH_JSON_FETCH_CONSISTENCY  closed by supplying the effect_result producer
#       map and keeping the better-scoring plan.
#   BENCH_MARKDOWN_TO_DECISION    closed by two measurements, not by a threshold.
#       The chained grounded pass tied `decision.synthesis.verify.stdlib` against
#       `decision.synthesis.typed.stdlib` at score 14 and specificity 1, raised
#       GOAL_COMPILATION_AMBIGUOUS, and the compiler fell back to the world-bound
#       markdown-to-PDF converter. The tie is now broken by an edge the registry
#       already declares -- the verifier's `requires` names the effect the
#       synthesizer `provides`, so the verifier is downstream and a request that
#       has produced no decision cannot be asking for the check on one. With the
#       tie resolved, a plan whose slots were all accounted for beats a plan that
#       filled `markdown_path` by picking AGENTS.md off the filesystem.
#
# The remaining wrong selection is EXT_JQ_TABLE, in the EXTENDED tier, tracked in
# test_front_door_selection_parity_v1. It is not listed here because this dict is
# compared against the PRIMARY tier's own report.
KNOWN_SELECTION_GAPS = {}

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


EXTENDED_BENCHMARK_GOALS: List[Dict[str, Any]] = [
    {
        "id": "EXT_QR_GENERATE",
        "goal": "Generate a QR code image for the text PROJECT BRAIN.",
        "expected": ["image.qr.generate.qrencode"],
    },
    {
        "id": "EXT_BARCODE_DECODE",
        "goal": "Decode the barcode in an image.",
        "expected": ["image.code.decode.zbarimg"],
    },
    {
        "id": "EXT_OCR_SCANNED_IMAGE",
        "goal": "Extract text from a scanned image with OCR.",
        "expected": ["image.extract.ocr.tesseract"],
    },
    {
        "id": "EXT_TAR_VERIFY",
        "goal": "Verify a tar.gz archive against its manifest.",
        "expected": ["archive.verify.tar_gz.gnu"],
    },
    {
        "id": "EXT_XLSX_CREATE",
        "goal": "Create an xlsx table from JSON records.",
        "expected": ["xlsx.table.create_from_json_records"],
    },
    {
        "id": "EXT_DOCX_VERIFY",
        "goal": "Verify a docx document against its intent.",
        "expected": ["docx.document.verify.intent_ooxml"],
    },
    {
        "id": "EXT_EVIDENCE_RANK",
        "goal": "Rank source evidence by relevance to the objective.",
        "expected": ["source.objective_relevance.rank.bm25"],
    },
    {
        "id": "EXT_CLAIM_BIND",
        "goal": "Bind evidence claims to an explicit comparison.",
        "expected": ["evidence.claim_spec.bind.explicit_comparison.stdlib"],
    },
    {
        "id": "EXT_KNOWLEDGE_CONSISTENCY",
        "goal": "Assess the consistency of knowledge observations.",
        "expected": ["knowledge.consistency.assess"],
    },
    {
        "id": "EXT_JQ_TABLE",
        "goal": "Query a JSON table and produce a markdown table.",
        "expected": ["json.query.jq"],
    },
    {
        "id": "EXT_AST_AUDIT",
        "goal": "Audit the python source tree with an AST.",
        "expected": ["python.source.audit.ast"],
    },
    {
        "id": "EXT_SQLITE_VERIFY",
        "goal": "Verify a sqlite table against JSON records.",
        "expected": ["sqlite.table.verify_against_json_records"],
    },
    {
        "id": "EXT_DECISION_VERIFY",
        "goal": "Verify a typed decision synthesis.",
        "expected": ["decision.synthesis.verify.stdlib"],
    },
    {
        "id": "EXT_MD_TO_PDF",
        "goal": "Convert a markdown document to PDF.",
        "expected": ["document.convert.markdown_pdf.pandoc_weasyprint"],
    },
]

# Measured, not asserted. Both tiers were run against the same registry with
# `canonical/runtime/goal_compiler.py` checked out at each revision, so the
# comparison holds the registry constant and varies only the compiler.
#
#   git checkout 9554215 -- canonical/runtime/goal_compiler.py   -> baseline
#   git checkout HEAD    -- canonical/runtime/goal_compiler.py   -> current
#
# The extended tier was added precisely because a nine-goal sample is too small
# to generalise from, and it turned out to be the PESSIMISTIC sample: the gain
# is larger on fourteen ordinary goals than on the original nine.
BASELINE_MEASURED_AT_BASE_9554215 = {
    "PRIMARY": {"goals": 9, "compiled": 1, "expected_first_selected": 0},
    "EXTENDED": {"goals": 14, "compiled": 4, "expected_first_selected": 0},
}

# A measured, PRE-EXISTING defect worth recording because it explains most of
# the remaining wrong selections in both tiers.
#
# `terminal.kstar.root.assess.stdlib` carries a 27-keyword list of governance
# vocabulary -- proof, evidence, capability, semantic, composition, context,
# reuse, universal, adequacy, discriminator, generator, and so on -- which
# overlaps ordinary technical prose on at least one token almost always. It was
# selected for FOUR unrelated goals at base (QR generate, evidence rank, claim
# bind, knowledge consistency) and is still selected for three of them now. It
# binds easily, so once the better-matching capabilities prove unbindable it is
# the candidate that survives.
#
# Adding repository-self-referential tokens to GENERIC_MATCH_TOKENS reduced this
# from four goals to three; it did not eliminate it, and the two scoring-level
# attempts described above both failed to either.
KNOWN_OVERMATCHING_CAPABILITY = "terminal.kstar.root.assess.stdlib"


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


def run_all() -> Dict[str, Any]:
    """Measure both tiers, with the base-9554215 baseline shown alongside."""
    _ensure_repo_root()
    primary = run(BENCHMARK_GOALS)
    extended = run(EXTENDED_BENCHMARK_GOALS)
    combined_goals = primary["totals"]["goals"] + extended["totals"]["goals"]
    combined_compiled = primary["totals"]["compiled"] + extended["totals"]["compiled"]
    combined_first = (
        primary["totals"]["expected_first_capability_selected"]
        + extended["totals"]["expected_first_capability_selected"]
    )
    base = BASELINE_MEASURED_AT_BASE_9554215
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "primary": primary,
        "extended": extended,
        "combined": {
            "goals": combined_goals,
            "compiled": combined_compiled,
            "expected_first_selected": combined_first,
            "baseline_compiled": base["PRIMARY"]["compiled"] + base["EXTENDED"]["compiled"],
            "baseline_expected_first_selected": (
                base["PRIMARY"]["expected_first_selected"]
                + base["EXTENDED"]["expected_first_selected"]
            ),
        },
    }


def _print_tier(label: str, report: Dict[str, Any], baseline: Dict[str, int]) -> None:
    totals = report["totals"]
    print(
        "{label}: compiled {compiled}/{goals} ({rate:.1%})  [base 9554215: {bc}/{bg}]".format(
            label=label,
            compiled=totals["compiled"],
            goals=totals["goals"],
            rate=totals["compile_rate"],
            bc=baseline["compiled"],
            bg=baseline["goals"],
        )
    )
    print(
        "    expected capability selected {first}/{goals}  [base 9554215: {bf}/{bg}]"
        " -- compiling is not selecting correctly".format(
            first=totals["expected_first_capability_selected"],
            goals=totals["goals"],
            bf=baseline["expected_first_selected"],
            bg=baseline["goals"],
        )
    )
    if totals["compiled_against_wrong_capability"]:
        print(
            "    compiled against the WRONG capability: {n}".format(
                n=totals["compiled_against_wrong_capability"]
            )
        )
    if report["failure_causes"]:
        print("    failure causes:", json.dumps(report["failure_causes"], sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", help="write the full measurement to this path")
    parser.add_argument(
        "--primary-only",
        action="store_true",
        help="measure only the original nine-goal tier",
    )
    parser.add_argument("--quiet", action="store_true", help="summary only")
    args = parser.parse_args()

    report = run()
    totals = report["totals"]
    print(f"GOAL COMPILATION BENCHMARK {report['benchmark_sha256'][:16]}")
    _print_tier("PRIMARY", report, BASELINE_MEASURED_AT_BASE_9554215["PRIMARY"])
    if not args.primary_only:
        extended = run(EXTENDED_BENCHMARK_GOALS)
        _print_tier("EXTENDED", extended, BASELINE_MEASURED_AT_BASE_9554215["EXTENDED"])
        pg = totals["goals"] + extended["totals"]["goals"]
        pc = totals["compiled"] + extended["totals"]["compiled"]
        pf = (
            totals["expected_first_capability_selected"]
            + extended["totals"]["expected_first_capability_selected"]
        )
        base = BASELINE_MEASURED_AT_BASE_9554215
        bc = base["PRIMARY"]["compiled"] + base["EXTENDED"]["compiled"]
        bf = (
            base["PRIMARY"]["expected_first_selected"]
            + base["EXTENDED"]["expected_first_selected"]
        )
        print(f"COMBINED: compiled {pc}/{pg}  [base 9554215: {bc}/{pg}]")
        print(f"          expected capability selected {pf}/{pg}  [base 9554215: {bf}/{pg}]")
        report = {
            "schema": SCHEMA,
            "authority": AUTHORITY,
            "primary": report,
            "extended": extended,
        }
    else:
        print(
            "compiled {compiled}/{goals} ({rate:.1%})".format(
                compiled=totals["compiled"], goals=totals["goals"], rate=totals["compile_rate"]
            )
        )
        print(
            "expected capability selected {first}/{goals} ({rate:.1%})".format(
                first=totals["expected_first_capability_selected"],
                goals=totals["goals"],
                rate=totals["expected_first_rate"],
            )
        )
    if isinstance(report, dict) and "totals" in report:
        if report["near_miss_drop_reasons"]:
            print("near-miss drops:", json.dumps(report["near_miss_drop_reasons"], sort_keys=True))
    if not args.quiet:
        # `report` is a two-tier envelope unless --primary-only, so rows are
        # read from the tier objects rather than from the envelope.
        tiers = (
            [("PRIMARY", report)]
            if "rows" in report
            else [("PRIMARY", report["primary"]), ("EXTENDED", report["extended"])]
        )
        for tier_name, tier in tiers:
            print(f"-- {tier_name} --")
            for row in tier["rows"]:
                mark = "OK  " if row["compiled"] else "FAIL"
                extra = ""
                if not row["compiled"]:
                    extra = " <- " + str((row["failure"] or {}).get("cause"))
                    near = row["near_miss"] or {}
                    if near.get("capability_id"):
                        extra += f" | near-miss {near['capability_id']} ({near.get('drop_reason')})"
                elif not row["expected_first_selected"]:
                    extra = " -> " + ",".join(row["selected"][:2]) + "  WRONG-CAPABILITY"
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
