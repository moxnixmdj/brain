#!/usr/bin/env python3
"""Causal Whole-File Lesson Localization, Execution-Locus Filtering & Held-Out Admission.

WHY THIS EXISTS
---------------
Three separate pieces already existed in `canonical/swe_kernel/`:

1. `lesson_localization_v1` isolates a single-operator statement change from a real whole-file
   repair (e.g., 1,317-line `boltons/strutils.py` where both a docstring and `<=` -> `<` changed),
   turning a 13-hole inert whole-file rule (`0` candidates on every file) into a 1-operator rule.
2. `skill_scope_acquisition_v1` + `applicability_v1.learn` attempt to learn where that operator
   rule applies from static AST facts unioned across all firing offsets in a target file. On the
   pinned real historical corpus (`boltons` + `more-itertools`), static file-unioned facts return
   `INCONSISTENT__NO_REQUIREMENT_EXPLAINS_THE_EVIDENCE` (`0` survivors) and propose `77` raw
   candidates (`32` each on `more_itertools/more.py`), because a 175 KB module contains dozens of
   unexecuted bystander comparisons whose AST facts form a strict superset of the smaller repaired
   modules, plus token-level splices into `->` return annotations and `>>` shifts.
3. `lesson_admission_gate_v1` evaluates a candidate rule on held-out contrast programs (`>= 1`
   `REPAIRED`, `>= 1` `PRESERVED`, `0` `BROKEN`) before persistence.

WHAT THIS MODULE ADDS
---------------------
1. **Dynamic Causal Execution-Cone Tracing (`trace_project_target`)**:
   Runs a project's own unmodified test suite once in an isolated copy under `sys.settrace` on the
   pre-repair target alone (`before.py`, zero access to `after.py`), recording `(returncode,
   test_count, executed_lines)` and failing closed on zero-test runs (`UNVERIFIABLE`).
2. **Execution-Locus Candidate Filtering (`propose_execution_locus_candidates`)**:
   Restricts `operator_generalization_v1.propose_operator_swaps` to edits that (a) parse cleanly
   (`ast.parse`, eliminating `->=` and `>=>` token-splice syntax errors) and (b) touch a line
   inside `executed_lines` (the causal cone of the failing baseline test: a line never executed
   during a failing run cannot cause that run to pass).
   Measured on the four pinned real historical defects (`unit_boundary`, `bits_capacity`,
   `ichunked_zero`, `chunked_even_zero`): raw static proposals drop from `77` (`9 + 4 + 32 + 32`,
   `26` subprocess oracle evaluations) to `2` (`1 + 1 + 0 + 0`, `2` oracle evaluations total, rank-1
   exact upstream fix on both `boltons` issues, `0` wasted oracle runs on `more-itertools`).
3. **Execution-Grounded Scope Identification (`execution_locus_facts`, `learn_execution_locus_scope`)**:
   Computes AST context facts strictly over syntax-valid sites inside `executed_lines`. Across the
   four real broken targets plus one real already-passing target (`bits_capacity/after.py`, where
   `>=` still fires on an executed line), `applicability_v1.learn` moves from `INCONSISTENT` (`0`
   survivors) to `IDENTIFIED__ONE_CONSISTENT_REQUIREMENT` (`survivor_count == 1`, required facts
   `('baseline.violates_own_spec', 'executed_locus.syntax_valid_site')`).
4. **Honest Boundary**:
   `executed_locus.syntax_valid_site` is a necessary causal reachability precondition, NOT a proof
   that an executed comparison is the defect (an innocent guard on the failing path also satisfies
   it). Every candidate and stored skill therefore remains gated by `ProjectTestOracle` and
   held-out `lesson_admission_gate_v1` (`0` broken programs).

Authority: NONE. `truth.achieved` stays `false`; zero model calls (`$0`).
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import PurePosixPath
from typing import Any, Callable, Iterator, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import applicability_v1 as app  # noqa: E402
from canonical.swe_kernel import lesson_admission_gate_v1 as adm  # noqa: E402
from canonical.swe_kernel import lesson_localization_v1 as loc  # noqa: E402
from canonical.swe_kernel import operator_generalization_v1 as gen  # noqa: E402
from canonical.swe_kernel import skill_recheck_v1 as recheck_mod  # noqa: E402
from canonical.swe_kernel import skill_scope_acquisition_v1 as acq  # noqa: E402
from canonical.swe_kernel import verified_skill_crystallizer_v1 as cry  # noqa: E402
from canonical.swe_kernel.skill_verification_contract_v1 import (  # noqa: E402
    ProjectTestOracle,
    source_sha256,
)

SCHEMA = "PROJECT_BRAIN_VERIFIED_LESSON_PIPELINE_V1"

REPAIRED = "REPAIRED"
NOT_REPAIRED = "NOT_REPAIRED"
DID_NOT_FIRE = "DID_NOT_FIRE_IN_EXECUTED_LOCUS"
ALREADY_CORRECT = "ALREADY_CORRECT"
SCOPE_REFUSED = "SCOPE_REFUSED"
UNVERIFIABLE = "UNVERIFIABLE"

EXECUTED_VALID_SITE = "executed_locus.syntax_valid_site"

_TRACE_RUNNER_CODE = r"""
import json, os, pathlib, sys

proj_root = pathlib.Path(sys.argv[1]).resolve()
target_file = (proj_root / sys.argv[2]).resolve()
test_rels = sys.argv[3:]
target_str = str(target_file)

sys.path.insert(0, str(proj_root))
for sub in ("src", "pkg", "lib"):
    cand = proj_root / sub
    if cand.is_dir() and not (cand / "__init__.py").exists():
        sys.path.insert(0, str(cand))

executed_lines = set()

def _tracer(frame, event, arg):
    if event == "line":
        fn = frame.f_code.co_filename
        if fn == target_str or os.path.abspath(fn) == target_str:
            executed_lines.add(frame.f_lineno)
    return _tracer

test_paths = [str((proj_root / rel).resolve()) for rel in test_rels]

try:
    import pytest
    class _Counter:
        def __init__(self):
            self.ran = 0
            self.failed = 0
            self.collect_errors = 0
        def pytest_runtest_logreport(self, report):
            if report.when == "call":
                self.ran += 1
                if report.failed:
                    self.failed += 1
            elif report.when == "setup" and report.failed:
                self.ran += 1
                self.failed += 1
        def pytest_collectreport(self, report):
            if report.failed:
                self.collect_errors += 1

    cnt = _Counter()
    sys.settrace(_tracer)
    try:
        rc = int(pytest.main(["-q", "-p", "no:cacheprovider", "--tb=no", *test_paths], plugins=[cnt]))
    finally:
        sys.settrace(None)
    test_count = 0 if cnt.collect_errors > 0 and cnt.ran == 0 else cnt.ran
    if rc == 5:
        test_count = 0
except ImportError:
    import unittest
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    for tp in test_paths:
        p = pathlib.Path(tp)
        suite.addTests(loader.discover(str(p.parent), pattern=p.name, top_level_dir=str(proj_root)))
    runner = unittest.TextTestRunner(stream=open(os.devnull, "w"))
    sys.settrace(_tracer)
    try:
        res = runner.run(suite)
    finally:
        sys.settrace(None)
    test_count = int(res.testsRun)
    rc = 0 if (res.wasSuccessful() and test_count > 0) else 1

sys.stdout.write("\nBRAIN_LOCUS_TRACE:" + json.dumps({
    "returncode": rc,
    "test_count": test_count,
    "executed_lines": sorted(executed_lines),
}) + "\n")
"""


def _copy_project_clean(src: pathlib.Path, dst: pathlib.Path) -> None:
    def _ignore(_dir: str, names: list[str]) -> set[str]:
        return {n for n in names if n in {"__pycache__", ".pytest_cache", ".git", ".mypy_cache"}}

    shutil.copytree(src, dst, ignore=_ignore)


def trace_project_target(
    project_root: pathlib.Path | str,
    target_path: str,
    test_paths: Sequence[str],
    *,
    source_override: str | None = None,
    timeout_s: float = 25.0,
) -> dict[str, Any]:
    """Execute `test_paths` once in a disposable copy under `sys.settrace` to record `executed_lines`.

    Never mutates `project_root`. Reports `test_count == 0` as `verifiable: False` so a vacuous
    suite is never mistaken for either a pass or a contrasting failure.
    """
    root = pathlib.Path(project_root).resolve()
    rel_target = PurePosixPath(target_path)
    if rel_target.is_absolute() or ".." in rel_target.parts or not target_path.endswith(".py"):
        raise ValueError("INVALID_TRACE_TARGET")
    if not test_paths:
        raise ValueError("TEST_PATHS_REQUIRED")

    with tempfile.TemporaryDirectory(prefix="brain_locus_trace_") as td:
        copied = pathlib.Path(td) / "project"
        _copy_project_clean(root, copied)
        if source_override is not None:
            (copied / str(rel_target)).write_text(source_override, encoding="utf-8")

        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONNOUSERSITE"] = "1"
        try:
            proc = subprocess.run(
                [sys.executable, "-B", "-c", _TRACE_RUNNER_CODE, str(copied), str(rel_target), *test_paths],
                cwd=str(copied),
                capture_output=True,
                text=True,
                env=env,
                timeout=timeout_s,
            )
        except subprocess.TimeoutExpired:
            return {
                "verifiable": False,
                "returncode": 124,
                "test_count": 0,
                "executed_lines": frozenset(),
                "error": "TIMEOUT",
            }

    marker = [ln for ln in (proc.stdout or "").splitlines() if ln.startswith("BRAIN_LOCUS_TRACE:")]
    if not marker:
        return {
            "verifiable": False,
            "returncode": int(proc.returncode),
            "test_count": 0,
            "executed_lines": frozenset(),
            "error": "TRACE_MARKER_ABSENT",
        }
    payload = json.loads(marker[-1].split("BRAIN_LOCUS_TRACE:", 1)[1])
    t_count = int(payload.get("test_count") or 0)
    rc = int(payload.get("returncode") or 0)
    lines = frozenset(int(x) for x in (payload.get("executed_lines") or []))
    return {
        "verifiable": t_count > 0,
        "returncode": rc,
        "test_count": t_count,
        "executed_lines": lines,
        "error": None,
    }


def _first_diff_offset_and_line(before: str, after: str) -> tuple[int, int]:
    off = next((i for i, (a, b) in enumerate(zip(before, after)) if a != b), min(len(before), len(after)))
    lineno = before[:off].count("\n") + 1
    return off, lineno


def propose_execution_locus_candidates(
    source_text: str,
    rule: Mapping[str, Any],
    executed_lines: set[int] | frozenset[int],
    *,
    language: str = "python",
    limit: int = gen.MAX_CANDIDATES,
) -> Iterator[dict[str, Any]]:
    """Yield syntax-valid operator-swap candidates whose changed line was actually executed."""
    is_py = language.lower() == "python"
    emitted = 0
    for raw_idx, cand in enumerate(gen.propose_operator_swaps(source_text, rule, language=language, limit=limit)):
        if is_py:
            try:
                ast.parse(cand)
            except SyntaxError:
                continue
        off, lineno = _first_diff_offset_and_line(source_text, cand)
        if lineno not in executed_lines:
            continue
        emitted += 1
        yield {
            "candidate": cand,
            "raw_index": raw_idx,
            "locus_rank": emitted,
            "lineno": lineno,
            "offset": off,
        }


def execution_locus_facts(
    source_text: str,
    rule: Mapping[str, Any],
    *,
    returncode: int,
    test_count: int,
    executed_lines: set[int] | frozenset[int],
    language: str = "python",
) -> dict[str, Any]:
    """Observable causal-cone facts for `(source_text, rule)` from a baseline test trace.

    Facts are extracted ONLY at syntax-valid candidate sites that lie on `executed_lines`, so
    unexecuted bystander comparisons in large multi-function files never pollute the target's
    fact state.
    """
    is_py = language.lower() == "python"
    raw_cands = list(gen.propose_operator_swaps(source_text, rule, language=language))
    syntax_valid_count = 0
    executed_valid_offsets: list[int] = []

    for cand in raw_cands:
        if is_py:
            try:
                ast.parse(cand)
            except SyntaxError:
                continue
        syntax_valid_count += 1
        off, lineno = _first_diff_offset_and_line(source_text, cand)
        if lineno in executed_lines:
            executed_valid_offsets.append(off)

    facts: set[str] = set()
    if test_count > 0 and returncode != 0:
        facts.add(acq.BASELINE_VIOLATES)
    if executed_valid_offsets:
        facts.add(EXECUTED_VALID_SITE)
        for off in executed_valid_offsets:
            for f in acq.facts_at_offset(source_text, off):
                facts.add(f"executed_locus.{f}")

    return {
        "schema": SCHEMA,
        "verifiable": test_count > 0,
        "raw_candidates": len(raw_cands),
        "syntax_valid_candidates": syntax_valid_count,
        "executed_valid_candidates": len(executed_valid_offsets),
        "state": frozenset(facts),
    }


def learn_execution_locus_scope(
    observations: Sequence[tuple[Sequence[str] | frozenset[str], bool]],
) -> dict[str, Any]:
    """Run `applicability_v1.learn` over `(execution_locus_facts, succeeded)` rows."""
    normalized = [(sorted(set(facts)), bool(ok)) for facts, ok in observations]
    boundary = app.learn(normalized)
    all_facts = set().union(*(set(f) for f, _ in normalized)) if normalized else set()
    constant_facts = sorted(
        f for f in all_facts if all(f in set(fs) for fs, _ in normalized)
    )
    return {
        "schema": boundary.schema,
        "status": boundary.status,
        "required": list(boundary.required) if boundary.required is not None else None,
        "most_general": list(boundary.most_general) if boundary.most_general is not None else None,
        "most_specific": list(boundary.most_specific) if boundary.most_specific is not None else None,
        "survivor_count": boundary.survivor_count,
        "successes": boundary.successes,
        "failures": boundary.failures,
        "constant_facts": constant_facts,
        "reason": boundary.reason,
    }


def apply_localized_skill_with_locus(
    oracle: Callable[[str], Any],
    source_text: str,
    rule: Mapping[str, Any],
    *,
    returncode: int,
    test_count: int,
    executed_lines: set[int] | frozenset[int],
    required_facts: Sequence[str] | None = None,
    budget: int = 12,
    language: str = "python",
) -> dict[str, Any]:
    """Apply `rule` restricted to `executed_lines` and optional learned `required_facts`."""
    if test_count <= 0:
        return {
            "verdict": UNVERIFIABLE,
            "oracle_calls": 0,
            "raw_candidates": 0,
            "locus_candidates": 0,
            "candidates_tried": 0,
            "passing_locus_ranks": [],
            "patched_source": None,
        }

    locus_info = execution_locus_facts(
        source_text,
        rule,
        returncode=returncode,
        test_count=test_count,
        executed_lines=executed_lines,
        language=language,
    )
    if required_facts is not None and not set(required_facts).issubset(locus_info["state"]):
        return {
            "verdict": ALREADY_CORRECT if returncode == 0 else SCOPE_REFUSED,
            "oracle_calls": 0,
            "raw_candidates": locus_info["raw_candidates"],
            "locus_candidates": locus_info["executed_valid_candidates"],
            "candidates_tried": 0,
            "passing_locus_ranks": [],
            "patched_source": None,
        }

    if returncode == 0:
        return {
            "verdict": ALREADY_CORRECT,
            "oracle_calls": 0,
            "raw_candidates": locus_info["raw_candidates"],
            "locus_candidates": locus_info["executed_valid_candidates"],
            "candidates_tried": 0,
            "passing_locus_ranks": [],
            "patched_source": None,
        }

    locus_stream = list(
        propose_execution_locus_candidates(source_text, rule, executed_lines, language=language)
    )
    if not locus_stream:
        return {
            "verdict": DID_NOT_FIRE,
            "oracle_calls": 0,
            "raw_candidates": locus_info["raw_candidates"],
            "locus_candidates": 0,
            "candidates_tried": 0,
            "passing_locus_ranks": [],
            "patched_source": None,
        }

    tried = locus_stream[:budget]
    passing_ranks: list[int] = []
    winning_source: str | None = None
    calls = 0
    for item in tried:
        calls += 1
        res = oracle(item["candidate"])
        ev = getattr(res, "evidence", {}) or {}
        passed = bool(getattr(res, "passed", False)) and int(ev.get("test_count") or 0) > 0
        if passed:
            passing_ranks.append(int(item["locus_rank"]))
            if winning_source is None:
                winning_source = str(item["candidate"])
            break

    return {
        "verdict": REPAIRED if winning_source is not None else NOT_REPAIRED,
        "oracle_calls": calls,
        "raw_candidates": locus_info["raw_candidates"],
        "locus_candidates": len(locus_stream),
        "candidates_tried": len(tried),
        "passing_locus_ranks": passing_ranks,
        "patched_source": winning_source,
    }


def measure_real_historical_pipeline() -> dict[str, Any]:
    """End-to-end deterministic measurement on pinned `boltons` and `more-itertools` commits."""
    from canonical.tests.historical_repair_curriculum_v1 import FAMILIES, FIXTURES, build_case

    cases = ("unit_boundary", "bits_capacity", "ichunked_zero", "chunked_even_zero")
    with tempfile.TemporaryDirectory(prefix="verified_lesson_pipeline_") as td:
        repo = pathlib.Path(td)

        # 1. Teach `unit_boundary` whole-file repair via `localize_lesson=True` + causal sufficiency
        teach_case = build_case(repo, "unit_boundary", "teach_ub")
        whole_before = teach_case["target"].read_text(encoding="utf-8")
        whole_after = (FIXTURES / "unit_boundary" / "after.py").read_text(encoding="utf-8")
        teach_rel_target = teach_case["target"].relative_to(teach_case["project"]).as_posix()
        teach_rel_tests = [
            p.relative_to(teach_case["project"]).as_posix()
            for p in sorted(teach_case["project"].glob("test_*.py"))
        ]
        teach_oracle = ProjectTestOracle(
            teach_case["project"],
            teach_rel_target,
            teach_rel_tests,
            teach_case["args"]["retained_learning"]["contract"]["scope_id"],
        )

        # Held-out contrast victims for pre-write admission (`lesson_admission_gate_v1`):
        # 1. `unseen_exclusive_tier_defect`: `DEFECT_PRESENT` -> `REPAIRED`
        # 2. `already_correct_inclusive_quota`: `ALREADY_CORRECT` -> `BROKEN` (proving blind
        #    unguarded rewrite is rejected before touching SQLite: `ADMISSION_REJECT`)
        # 3. `already_correct_idempotent_clamp`: `ALREADY_CORRECT` -> `PRESERVED` (touched at
        #    boundary `10` without changing output, satisfying FGSE non-regression `ADMIT`).
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

        db_rejected = repo / "memory" / "rejected.sqlite"
        db_rejected.parent.mkdir(parents=True, exist_ok=True)
        ungated_collision_attempt = cry.VerifiedSkillStore(db_rejected, seed=False).crystallize_code_fix(
            before_snippet=whole_before,
            after_snippet=whole_after,
            language="python",
            error_class="BOUNDARY",
            contract=teach_case["args"]["retained_learning"]["contract"],
            training_verifier=teach_oracle,
            localize_lesson=True,
            admission_victims=(unseen_defective, already_correct_inclusive),
        )

        db_admitted = repo / "memory" / "admitted.sqlite"
        teach_oracle_2 = ProjectTestOracle(
            teach_case["project"],
            teach_rel_target,
            teach_rel_tests,
            teach_case["args"]["retained_learning"]["contract"]["scope_id"],
        )
        crystallized = cry.VerifiedSkillStore(db_admitted, seed=False).crystallize_code_fix(
            before_snippet=whole_before,
            after_snippet=whole_after,
            language="python",
            error_class="BOUNDARY",
            contract=teach_case["args"]["retained_learning"]["contract"],
            training_verifier=teach_oracle_2,
            localize_lesson=True,
            admission_victims=(unseen_defective, already_correct_preserved),
        )
        stored_rules = cry.VerifiedSkillStore(db_admitted, seed=False).lookup_rules("python", "BOUNDARY")
        stored_rule = dict(stored_rules[0])
        recheck_verdict = recheck_mod.recheck(stored_rule)
        witness_verdict = recheck_mod.self_witness(stored_rule)

        # 2. Trace & evaluate across all 4 real historical broken targets + 1 real green target (`bits_capacity/after.py`)
        per_case: dict[str, Any] = {}
        locus_rows: list[tuple[frozenset[str], bool]] = []
        static_site_rows: list[tuple[list[str], bool]] = []
        total_raw_candidates = 0
        total_locus_candidates = 0
        total_locus_oracle_calls = 0

        for cid in cases:
            c_proj = build_case(repo, cid, "eval_" + cid)
            rel_t = c_proj["target"].relative_to(c_proj["project"]).as_posix()
            rel_tests = [
                p.relative_to(c_proj["project"]).as_posix()
                for p in sorted(c_proj["project"].glob("test_*.py"))
            ]
            src_before = c_proj["target"].read_text(encoding="utf-8")
            src_after = (FIXTURES / cid / "after.py").read_text(encoding="utf-8")

            tr = trace_project_target(c_proj["project"], rel_t, rel_tests)
            lf = execution_locus_facts(
                src_before,
                stored_rule,
                returncode=tr["returncode"],
                test_count=tr["test_count"],
                executed_lines=tr["executed_lines"],
            )
            oracle_c = ProjectTestOracle(
                c_proj["project"],
                rel_t,
                rel_tests,
                c_proj["args"]["retained_learning"]["contract"]["scope_id"],
            )
            applied = apply_localized_skill_with_locus(
                oracle_c,
                src_before,
                stored_rule,
                returncode=tr["returncode"],
                test_count=tr["test_count"],
                executed_lines=tr["executed_lines"],
            )
            matches_pinned_upstream = (
                applied["patched_source"] is not None
                and source_sha256(applied["patched_source"]) == source_sha256(src_after)
            )
            per_case[cid] = {
                "baseline_returncode": tr["returncode"],
                "baseline_test_count": tr["test_count"],
                "executed_line_count": len(tr["executed_lines"]),
                "raw_candidates": applied["raw_candidates"],
                "locus_candidates": applied["locus_candidates"],
                "oracle_calls": applied["oracle_calls"],
                "verdict": applied["verdict"],
                "passing_locus_ranks": applied["passing_locus_ranks"],
                "matches_exact_upstream_fix": matches_pinned_upstream,
                "locus_facts": sorted(lf["state"]),
            }
            total_raw_candidates += int(applied["raw_candidates"])
            total_locus_candidates += int(applied["locus_candidates"])
            total_locus_oracle_calls += int(applied["oracle_calls"])

            succeeded = applied["verdict"] == REPAIRED
            locus_rows.append((lf["state"], succeeded))
            static_sf = acq.site_facts(src_before, stored_rule, baseline_ok=False, language="python")
            static_site_rows.append((sorted(static_sf["state"]), succeeded))

        # Real already-green control: sha256-pinned `bits_capacity/after.py`
        green_proj = build_case(repo, "bits_capacity", "eval_bits_green")
        green_after_src = (FIXTURES / "bits_capacity" / "after.py").read_text(encoding="utf-8")
        green_proj["target"].write_text(green_after_src, encoding="utf-8")
        green_rel_t = green_proj["target"].relative_to(green_proj["project"]).as_posix()
        green_rel_tests = [
            p.relative_to(green_proj["project"]).as_posix()
            for p in sorted(green_proj["project"].glob("test_*.py"))
        ]
        green_tr = trace_project_target(green_proj["project"], green_rel_t, green_rel_tests)
        green_lf = execution_locus_facts(
            green_after_src,
            stored_rule,
            returncode=green_tr["returncode"],
            test_count=green_tr["test_count"],
            executed_lines=green_tr["executed_lines"],
        )
        locus_rows_with_green = list(locus_rows) + [(green_lf["state"], False)]

        scope_broken_only = learn_execution_locus_scope(locus_rows)
        scope_with_green = learn_execution_locus_scope(locus_rows_with_green)
        static_scope = app.learn(static_site_rows)

        # Verify learned scope preserves `bits_capacity/after.py` with 0 oracle calls and 0 broken edits
        green_oracle = ProjectTestOracle(
            green_proj["project"],
            green_rel_t,
            green_rel_tests,
            green_proj["args"]["retained_learning"]["contract"]["scope_id"],
        )
        green_applied = apply_localized_skill_with_locus(
            green_oracle,
            green_after_src,
            stored_rule,
            returncode=green_tr["returncode"],
            test_count=green_tr["test_count"],
            executed_lines=green_tr["executed_lines"],
            required_facts=scope_with_green["required"],
        )

        return {
            "schema": SCHEMA,
            "authority": "NONE",
            "truth_achieved": False,
            "model_dependency_count": 0,
            "incremental_spend_usd": 0,
            "teaching": {
                "source_case": "unit_boundary",
                "crystallized": bool(crystallized.get("crystallized")),
                "skill_id": stored_rule.get("skill_id"),
                "localization": stored_rule.get("localization"),
                "causal_sufficiency": {
                    "verified": bool((stored_rule.get("causal_sufficiency") or {}).get("verified")),
                    "incidental_edits_stripped": bool(
                        (stored_rule.get("causal_sufficiency") or {}).get("incidental_edits_stripped")
                    ),
                    "minimal_candidate_sha256": (stored_rule.get("causal_sufficiency") or {}).get(
                        "minimal_candidate_sha256"
                    ),
                },
                "admission_verdict": (stored_rule.get("admission") or {}).get("verdict"),
                "admission_counts": (stored_rule.get("admission") or {}).get("counts"),
                "recheck_verdict": recheck_verdict.get("verdict"),
                "self_witness_verdict": witness_verdict.get("verdict"),
                "ungated_collision_rejected_by_admission_gate": {
                    "crystallized": bool(ungated_collision_attempt.get("crystallized")),
                    "reason": ungated_collision_attempt.get("reason"),
                    "counts": ((ungated_collision_attempt.get("admission") or {}).get("counts")),
                },
            },
            "candidate_reduction_on_4_real_defects": {
                "static_raw_candidates_total": total_raw_candidates,
                "execution_locus_candidates_total": total_locus_candidates,
                "reduction_ratio": round(
                    1.0 - (total_locus_candidates / max(1, total_raw_candidates)), 6
                ),
                "static_probe_oracle_calls_total": 26,
                "execution_locus_oracle_calls_total": total_locus_oracle_calls,
            },
            "per_case": per_case,
            "green_control_bits_capacity_after": {
                "baseline_returncode": green_tr["returncode"],
                "baseline_test_count": green_tr["test_count"],
                "locus_facts": sorted(green_lf["state"]),
                "verdict_under_learned_scope": green_applied["verdict"],
                "oracle_calls_under_learned_scope": green_applied["oracle_calls"],
            },
            "scope_comparison": {
                "static_site_union_status": static_scope.status,
                "static_site_union_survivors": static_scope.survivor_count,
                "execution_locus_broken_only_status": scope_broken_only["status"],
                "execution_locus_broken_only_survivors": scope_broken_only["survivor_count"],
                "execution_locus_with_green_control_status": scope_with_green["status"],
                "execution_locus_with_green_control_survivors": scope_with_green["survivor_count"],
                "execution_locus_identified_required_facts": scope_with_green["required"],
            },
            "provenance_cases": sorted(c for pair in FAMILIES.values() for c in pair),
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", type=pathlib.Path, default=None,
                        help="optional path to write deterministic JSON report")
    args = parser.parse_args(argv)
    report = measure_real_historical_pipeline()
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.write is not None:
        args.write.parent.mkdir(parents=True, exist_ok=True)
        args.write.write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
