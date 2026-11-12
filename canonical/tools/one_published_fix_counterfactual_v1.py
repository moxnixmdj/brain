#!/usr/bin/env python3
"""One preselected QuixBugs fix, empty/forward/reverse memories, actual upstream tests.

A bounded diagnostic, not a new solver or held-out benchmark claim. These bugs were studied in
this repository before. Correct target programs calibrate/check the oracle but are never passed
into candidate generation. Test execution uses the existing ProjectTestOracle, not a stand-in.
Run only on trusted upstream code: the oracle copies projects but is not an OS security sandbox.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from canonical.runtime import edit_kind_learning_v1 as kinds  # noqa: E402
from canonical.tools import quixbugs_one_fix_transfer_measure_v1 as bench  # noqa: E402

PIN = "4257f44b0ff1181dedaedee6a447e133219fcebf"
BUDGET = 10
TIMEOUT_S = 8
ARMS = ("empty", "forward", "reverse")


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def generate(bundle: dict, arm: str) -> dict:
    if arm not in ARMS:
        raise ValueError("UNKNOWN_ARM")
    memory = kinds.Lessons()
    if arm != "empty":
        before, after = bundle["teacher"]["before"], bundle["teacher"]["after"]
        if arm == "reverse":
            before, after = after, before
        memory.learn("one-published-fix", before, after)
    # Freeze memory: do not learn from candidate checks or any target's reference fix.
    candidates = {name: [row["source"] for row in memory.proposals(source, limit=BUDGET)]
                  for name, source in sorted(bundle["sources"].items())}
    return {"arm": arm, "lesson_count": len(memory.lessons),
            "operator_count": len(memory.operators), "candidates": candidates}


def fresh_generation(bundle_path: pathlib.Path, arm: str) -> dict:
    proc = subprocess.run([sys.executable, "-B", str(pathlib.Path(__file__).resolve()),
                           "--generate", str(bundle_path), "--arm", arm],
                          capture_output=True, text=True, timeout=60, check=True)
    return json.loads(proc.stdout)


def select(oracle, candidates: list[str], reference: str) -> dict:
    tried = 0
    for rank, source in enumerate(candidates, 1):
        tried += 1
        first = bench.verdict(oracle(source))
        if first["passed"]:
            # Every oracle call uses a new copied project and fresh subprocess.
            confirmation = bench.verdict(oracle(source))
            return {"candidate_count": len(candidates), "candidate_tests": tried,
                    "confirmation_tests": 1, "rank": rank,
                    "accepted": confirmation["passed"],
                    "published_fix_match": confirmation["passed"] and kinds.same_program(source, reference),
                    "candidate_sha256": hashlib.sha256(source.encode()).hexdigest(),
                    "first": first, "confirmation": confirmation}
    return {"candidate_count": len(candidates), "candidate_tests": tried,
            "confirmation_tests": 0, "rank": None, "accepted": False,
            "published_fix_match": False}


def counts(rows: dict) -> dict:
    return {arm: {"targets": len(rows),
                  "accepted": sum(row["arms"][arm]["accepted"] for row in rows.values()),
                  "published_fix_matches": sum(row["arms"][arm]["published_fix_match"] for row in rows.values()),
                  "candidates_tested": sum(row["arms"][arm]["candidate_tests"] for row in rows.values()),
                  "confirmations": sum(row["arms"][arm]["confirmation_tests"] for row in rows.values())}
            for arm in ARMS}


def measure(upstream: pathlib.Path, work: pathlib.Path) -> dict:
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=upstream, text=True).strip()
    if revision != PIN:
        raise ValueError("UPSTREAM_REVISION_MISMATCH")
    if subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=all"], cwd=upstream).strip():
        raise ValueError("UPSTREAM_TREE_DIRTY")
    names = sorted(bench.program_names(upstream))
    if len(names) != 40:
        raise ValueError("EXPECTED_40_PROGRAMS")
    teacher, targets = names[0], names[1:]  # fixed alphabetical choice; never try alternate teachers
    sources = {name: (upstream / "python_programs" / f"{name}.py").read_text() for name in names}
    correct = (upstream / "correct_python_programs" / f"{teacher}.py").read_text()
    fixed_teacher = bench.reference_fix(sources[teacher], correct)["fixed_source"]
    work.mkdir(parents=True, exist_ok=True)
    bundle = {"teacher": {"name": teacher, "before": sources[teacher], "after": fixed_teacher},
              "sources": sources}
    bundle_path = work / "generation_inputs.json"
    bundle_path.write_text(json.dumps(bundle))
    generated, restart = {}, {}
    for arm in ARMS:
        generated[arm] = fresh_generation(bundle_path, arm)
        restart[arm] = generated[arm] == fresh_generation(bundle_path, arm)
    if not all(restart.values()):
        raise ValueError("FRESH_PROCESS_GENERATION_DIFFERS")

    project = bench.build_project(upstream, teacher, work / "projects")
    oracle = bench.oracle_for(project, teacher, timeout_s=TIMEOUT_S)
    teacher_check = {"buggy": bench.verdict(oracle(sources[teacher])),
                     "reference": bench.verdict(oracle(fixed_teacher))}
    if teacher_check["buggy"]["passed"] or not teacher_check["reference"]["passed"]:
        raise ValueError("TEACHER_ORACLE_NOT_CALIBRATED")
    same_bug = {arm: select(oracle, generated[arm]["candidates"][teacher], fixed_teacher) for arm in ARMS}

    rows, excluded, data_hashes = {}, {}, {}
    for name in names:
        # Hash the whole bounded project as supplied by the existing upstream loader.
        project = bench.build_project(upstream, name, work / "projects")
        data_hashes[name] = {str(path.relative_to(project)): hashlib.sha256(path.read_bytes()).hexdigest()
                             for path in sorted(project.rglob("*")) if path.is_file()}
        if name == teacher:
            continue
        oracle = bench.oracle_for(project, name, timeout_s=TIMEOUT_S)
        reference = bench.reference_fix(sources[name],
            (upstream / "correct_python_programs" / f"{name}.py").read_text())["fixed_source"]
        baseline, fixed = bench.verdict(oracle(sources[name])), bench.verdict(oracle(reference))
        calibration = {"buggy": baseline, "reference": fixed}
        # Timeouts/errors on buggy sources are retained explicitly; a passing reference is required.
        if baseline["passed"] or not fixed["passed"] or not (fixed["test_count"] or 0) > 0:
            excluded[name] = calibration
            print(f"{name}: excluded by oracle calibration", file=sys.stderr, flush=True)
            continue
        rows[name] = {"calibration": calibration,
                      "arms": {arm: select(oracle, generated[arm]["candidates"][name], reference) for arm in ARMS}}
        print(f"{name}: " + ", ".join(f"{arm}={rows[name]['arms'][arm]['accepted']}" for arm in ARMS),
              file=sys.stderr, flush=True)

    return {"schema": "BRAIN_ONE_PUBLISHED_FIX_COUNTERFACTUAL_V1", "authority": "NONE",
            "upstream": {"url": "https://github.com/jkoppel/QuixBugs", "commit": PIN,
                         "bounded_project_file_sha256": data_hashes},
            "protocol": {"teacher_selection": "first alphabetically of all 40 programs", "teacher": teacher,
                         "target_names": targets, "candidate_budget_per_arm_per_target": BUDGET,
                         "oracle_timeout_s": TIMEOUT_S, "updates_on_targets": 0,
                         "target_reference_visible_to_generator": False,
                         "restart_means": "new process re-derives operators from the same saved lesson; not serialized runtime memory"},
            "generation_bundle_sha256": digest(bundle),
            "fresh_process_matches": restart,
            "generation": {arm: {"lessons": generated[arm]["lesson_count"],
                                 "operators": generated[arm]["operator_count"],
                                 "sha256": digest(generated[arm])} for arm in ARMS},
            "teacher_calibration": teacher_check, "same_bug_control": same_bug,
            "summary": counts(rows), "excluded": excluded, "per_target": rows,
            "code_sha256": {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in (
                "canonical/tools/one_published_fix_counterfactual_v1.py", "canonical/runtime/edit_kind_learning_v1.py",
                "canonical/tools/quixbugs_one_fix_transfer_measure_v1.py", "canonical/swe_kernel/skill_verification_contract_v1.py",
                "canonical/runtime/bound_capabilities/python_repository_acceptance_measurement_v1.py")},
            "limits": ["Previously studied benchmark, not genuinely unseen tasks or advanced SWE",
                       "One deterministic teacher, not a representative estimate of all one-shot learning",
                       "Empty arm is the same candidate learner without lessons, not the full cold repair solver",
                       "Reverse lesson controls direction, not all structural information in a demonstration",
                       "Maximum candidate budgets equal; spent budgets and wall-clock costs need not be equal",
                       "Fresh processes re-derive from saved examples; no arbitrary environment mastery established",
                       "Two passing calls are local checks, not independent verification or a correctness proof",
                       "Published AST match is a strict secondary check, not semantic equivalence or extra-input evaluation"],
            "model_calls": 0, "incremental_spend_usd": 0}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generate", type=pathlib.Path)
    parser.add_argument("--arm", choices=ARMS)
    parser.add_argument("--upstream", type=pathlib.Path)
    parser.add_argument("--out", type=pathlib.Path)
    args = parser.parse_args()
    if args.generate:
        if args.arm is None:
            parser.error("--generate requires --arm")
        print(json.dumps(generate(json.loads(args.generate.read_text()), args.arm), sort_keys=True))
        return 0
    if not args.upstream or not args.out:
        parser.error("--upstream and --out required")
    with tempfile.TemporaryDirectory(prefix="one-published-fix-") as scratch:
        report = measure(args.upstream.resolve(), pathlib.Path(scratch))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print(json.dumps(report["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
