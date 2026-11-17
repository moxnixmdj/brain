#!/usr/bin/env python3
"""Bind the three blockers to one verified-index law and refuse premature weights.

This tool does not learn, train, plan, repair, register a capability, call a model,
or use the network at run time. It answers one integrity question before any new
parameter or "one experience solves everything" claim is allowed:

    Can the same real hard-open population be separated by a causal observation
    that an independent verifier can read, on the state in hand?

The owner's three blockers are three projections of that same condition:

1. identifiability         -> one trace leaves many hypotheses until a chosen
                              observation splits them;
2. vocabulary insufficiency -> the current index does not contain the observable
                              that would split them;
3. synthesis/verification   -> replaying a seen edit cannot replace generating a
                              grounded candidate and judging it by execution.

If one shared defect must be named, it is the VERIFIED INDEX: a specification
with a frame, an index key injective on the policy-relevant distinction, and an
independent verifier that reads the split. It is the highest-leverage necessary
condition measured here, not a single sufficient lever and not terminal truth.

Calculated-parameter law:
    A parameter bit may be admitted only as b = C(s, o, I, V):
      s = current state, o = live causal observation, I = invariant closure,
      V = independent verifier, C = a deterministic calculated function.
    b must be falsifiable, invariant-closed, regression-zero on archived solved
    behavior, and derived from execution evidence that is itself inspectable.
    Facts stay in the content-addressed instant-knowledge model. Parameters are
    never a knowledge house. Until a bit passes this gate, the best part is no
    part: ZERO new parameters.

Hard-test discipline: the only tasks executed are the 16 published QuixBugs
task files frozen in the V2 admission population. A later main PR reclassified
eight of them in the live union receipt; that external reclassification receives
zero credit here. Known wins are not re-tested as progress. The fresh task copy has no correct-program answer keys, published
test bytes are hashed, no external model is called, no network is used at run
time, and incremental spend is $0. Every published test node id is first
enumerated with pytest --collect-only, then each real node id is invoked in its
own stdlib-subprocess timeout. No test file is edited, no timeout plugin is
installed, no hidden skip is allowed, and a failing or timing-out published
test on the buggy program is reported as hard-open evidence, never as a repair
or capability. A collection error remains a harness-integrity failure.

Usage:
    /path/to/venv/bin/python canonical/tools/verified_index_and_calculated_parameter_admission_v1.py \
        --quixbugs /path/to/pinned/QuixBugs \
        --out canonical/verification/VERIFIED_INDEX_AND_CALCULATED_PARAMETER_ADMISSION_20261116_V1.json \
        --per-test-timeout 2.0
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Iterable

ROOT = pathlib.Path(__file__).resolve().parents[2]
VERIFICATION = ROOT / "canonical" / "verification"
ACTION_INTENTS = ROOT / "canonical" / "action_intents"

SCHEMA = "PROJECT_BRAIN_VERIFIED_INDEX_AND_CALCULATED_PARAMETER_ADMISSION_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"
UPSTREAM = "https://github.com/jkoppel/QuixBugs"
MODEL_DEPENDENCY_COUNT = 0
NETWORK_DEPENDENCY_COUNT = 0
EXTERNAL_CAPABILITY_PROVIDER_COUNT = 0
INCREMENTAL_SPEND_USD = 0
DEFAULT_PER_TEST_TIMEOUT_SECONDS = 2.0
COLLECTION_TIMEOUT_SECONDS = 10.0

ANSWER_DOC = "THE_VERIFIED_INDEX_IS_THE_BOTTLENECK_20261116_V2.md"
INTENT = "canonical/action_intents/THE_VERIFIED_INDEX_IS_THE_BOTTLENECK_20261116_V2.json"
OUTPUT_RECEIPT = "canonical/verification/VERIFIED_INDEX_AND_CALCULATED_PARAMETER_ADMISSION_20261116_V1.json"

# V2 freezes the 16 published task files from the union receipt at e9bfca... before
# PR #6919 reclassified eight of them. The current-tree union receipt is read only
# to record that change; zero external repair/reclassification credit is claimed.
FROZEN_V2_HARD_OPEN_TASKS = (
    "breadth_first_search", "depth_first_search", "detect_cycle", "flatten",
    "kheapsort", "possible_change", "powerset", "reverse_linked_list",
    "shortest_path_length", "shortest_path_lengths", "shortest_paths",
    "shunting_yard", "sqrt", "subsequences", "topological_ordering", "wrap",
)
FROZEN_V2_KNOWN_WINS = frozenset({
    "bitcount", "bucketsort", "find_first_in_sorted", "find_in_sorted", "gcd",
    "get_factors", "hanoi", "is_valid_parenthesization", "knapsack", "kth",
    "lcs_length", "levenshtein", "lis", "longest_common_subsequence",
    "max_sublist_sum", "mergesort", "minimum_spanning_tree", "next_palindrome",
    "next_permutation", "pascal", "quicksort", "rpn_eval", "sieve", "to_base",
})

RECEIPTS = {
    "union": "canonical/verification/PROOF_CARRYING_COUNTERFACTUAL_UNION_20261116_V1.json",
    "four_levers": "canonical/verification/THE_FOUR_LEVERS_OF_LEARNING_FROM_EXPERIENCE_20261116_V1.json",
    "insufficiency": "canonical/verification/INSUFFICIENCY_CERTIFICATE_20261113_V1.json",
    "index": "canonical/verification/THE_INDEX_IS_THE_BOTTLENECK_20261116_V1.json",
    "composition": "canonical/verification/COMPOSE_MEASURED_EFFECTS_20261116_V1.json",
    "weight_fuel": "canonical/verification/WEIGHT_SPACE_FUEL_20261113_V1.json",
    "why_weights": "canonical/verification/WHY_WEIGHT_SPACE_IS_NOT_THE_MISSING_LAYER_20261112_V1.json",
    "unbound_name": "canonical/verification/THE_TREE_ALREADY_SPOKE_ONE_LANGUAGE_20261116_V1.json",
}

ORGANS_BY_EFFECT = {
    "identifiability_and_separation": (
        "canonical/runtime/finite_identifiability.py",
        "canonical/runtime/m5_causal_identifiability.py",
        "canonical/runtime/applicability_v1.py",
        "canonical/runtime/contrast_selection_v1.py",
        "canonical/swe_kernel/one_demonstration_identifies_v1.py",
        "canonical/swe_kernel/repair_version_space_selection_v1.py",
    ),
    "observable_and_vocabulary": (
        "canonical/runtime/observable_descriptor_v1.py",
        "canonical/runtime/fact_entailment_v1.py",
        "canonical/runtime/world_probe_v1.py",
        "canonical/tools/insufficiency_certificate_probe_v1.py",
        "canonical/tools/the_index_is_the_bottleneck_v1.py",
        "canonical/runtime/what_one_experience_buys_v1.py",
    ),
    "verifier_and_admission": (
        "canonical/swe_kernel/lesson_admission_gate_v1.py",
        "canonical/swe_kernel/test_suite_admission_v1.py",
        "canonical/swe_kernel/weight_update_admission_v1.py",
        "canonical/swe_kernel/learned_skill_verdict_v1.py",
        "canonical/runtime/instruction_contract_v1.py",
        "canonical/runtime/instruction_policy_v1.py",
    ),
    "composition_and_frame": (
        "canonical/swe_kernel/contract_grounded_repair_v1.py",
        "canonical/swe_kernel/interventional_goal_v1.py",
        "canonical/swe_kernel/proved_composition_v1.py",
        "canonical/tools/compose_measured_effects_v1.py",
        "canonical/runtime/capability_composer_v1.py",
        "canonical/runtime/verified_skill_macro_planner_v1.py",
    ),
    "instant_knowledge_and_zero_weight_model": (
        "canonical/runtime/compile_brain_unified_model_v1.py",
        "canonical/runtime/verify_brain_unified_model_v1.py",
        "canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json",
    ),
}

CALCULATED_BIT_LAW = (
    "b = C(s, o, I, V); admit only if C is deterministic, o is a live causal "
    "observation, I is an invariant closure, V is an independent verifier, "
    "the bit is falsifiable, regression-zero on archived solved behavior, and "
    "no fact is stored in parameters. Else b = 0 (best part is no part)."
)

HARD_NONCLAIMS = (
    "NO_EXTERNAL_MODEL_CALLED",
    "NO_EXTERNAL_MODEL_WEIGHTS_OR_OUTPUTS",
    "NO_CONVENTIONAL_PRETRAINING",
    "NO_KNOWLEDGE_HOUSE_PARAMETERS",
    "NO_NEW_WEIGHT_UPDATE_ADMITTED",
    "NO_TERMINAL_TRUTH",
    "NO_SENTIENCE_CLAIM",
    "NO_ALL_COMPUTER_USE_SOLVED_CLAIM",
    "NO_ADVANCED_SWE_SOLVED_CLAIM",
    "NO_SYNTHETIC_TASKS",
    "NO_KNOWN_WIN_RETESTED_AS_PROGRESS",
    "NO_SCREEN_ONLY_VERDICT_AS_REPAIR",
    "NO_EXTERNAL_REPAIR_RECLASSIFICATION_CREDIT",
    "NO_MAJORITY_VOTE_AS_IDENTIFICATION",
    "NO_ONE_DEMONSTRATION_AS_PERMANENT_RULE",
    "NO_SINGLE_SUFFICIENT_LEVER",
    "NO_BENCHMARK_OR_FAMILY_RANK_AUTHORITY",
    "NO_TEST_EDIT_OR_TIMEOUT_PLUGIN_SHORTCUT",
    "PRODUCER_RUN_NOT_INDEPENDENT_VERIFICATION",
)


def read_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_head(path: pathlib.Path) -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
    except Exception:
        return "UNKNOWN"


def ignore_answer_keys(_directory: str, names: Iterable[str]) -> set[str]:
    ignored = {".git", "__pycache__", ".pytest_cache"}
    for name in names:
        if name in {"correct_python_programs", "correct_java_programs"}:
            ignored.add(name)
        if name.endswith(".pyc"):
            ignored.add(name)
    return ignored


def fresh_hard_open_copy(quixbugs_root: pathlib.Path, destination: pathlib.Path) -> dict[str, Any]:
    shutil.copytree(quixbugs_root, destination, ignore=ignore_answer_keys, dirs_exist_ok=True)
    answer_key_dirs = [
        str(p.relative_to(destination))
        for p in destination.rglob("correct_python_programs")
        if p.is_dir()
    ]
    return {
        "fresh_copy": str(destination),
        "answer_key_directories_found": answer_key_dirs,
        "answer_keys_absent": not answer_key_dirs,
        "correct_flag_used": False,
        "no_synthetic_tasks": True,
        "external_model_calls": 0,
        "network_calls_at_run_time": 0,
        "incremental_spend_usd": 0,
    }


def parse_pytest_counts(text: str) -> dict[str, int]:
    failed = re.search(r"(\d+) failed", text)
    passed = re.search(r"(\d+) passed", text)
    errors = re.search(r"(\d+) errors?", text)
    skipped = re.search(r"(\d+) skipped", text)
    return {
        "failed": int(failed.group(1)) if failed else 0,
        "passed": int(passed.group(1)) if passed else 0,
        "errors": int(errors.group(1)) if errors else 0,
        "skipped": int(skipped.group(1)) if skipped else 0,
    }


def _text_tail(value: Any, limit: int) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        text = value.decode("utf-8", errors="replace")
    else:
        text = str(value)
    return text[-limit:]


def _run_pytest(args: list[str], cwd: pathlib.Path, env: dict[str, str], timeout: float) -> tuple[int, str, str, bool]:
    """Run pytest once with a stdlib subprocess timeout; never edit a test."""
    try:
        proc = subprocess.run(
            args,
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return proc.returncode, _text_tail(proc.stdout, 800), _text_tail(proc.stderr, 400), False
    except subprocess.TimeoutExpired as exc:
        return 124, _text_tail(exc.stdout, 800), _text_tail(exc.stderr, 400), True


def run_hard_open_tests(fresh: pathlib.Path, tasks: list[str], per_test_timeout: float) -> dict[str, Any]:
    """Collect and invoke every real published test node in its own subprocess.

    A process timeout on QuixBugs' intentionally buggy program is a genuine
    hard-open failure. A collection error, a missing node id, an uninvoked test,
    a pytest usage error, or a hidden skip is a harness-integrity failure.
    """
    rows: list[dict[str, Any]] = []
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(fresh), str(fresh / "python_programs"), str(fresh / "python_testcases")]
    )
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONHASHSEED"] = "0"
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    base_cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:cacheprovider",
        "--disable-warnings",
    ]
    for task in tasks:
        rel = f"python_testcases/test_{task}.py"
        test_path = fresh / rel
        test_bytes = test_path.read_bytes()
        collection_cmd = base_cmd + ["--collect-only", rel]
        collection_rc, collection_stdout, collection_stderr, _ = _run_pytest(
            collection_cmd, fresh, env, COLLECTION_TIMEOUT_SECONDS
        )
        nodeids = [
            line.strip()
            for line in collection_stdout.splitlines()
            if line.strip().startswith(rel + "::")
        ]
        invocation_rows: list[dict[str, Any]] = []
        for nodeid in nodeids:
            invocation_cmd = base_cmd + ["--tb=no", nodeid]
            rc, stdout_tail, stderr_tail, timed_out = _run_pytest(
                invocation_cmd, fresh, env, per_test_timeout
            )
            counts = parse_pytest_counts(stdout_tail)
            if timed_out:
                counts["failed"] += 1
            invocation_rows.append(
                {
                    "nodeid": nodeid,
                    "returncode": rc,
                    "timed_out": timed_out,
                    "counts": counts,
                    "status": (
                        "PUBLISHED_TEST_TIMEOUT__HARD_OPEN"
                        if timed_out
                        else "PUBLISHED_TEST_PASS"
                        if rc == 0
                        else "PUBLISHED_TEST_FAIL__HARD_OPEN"
                        if rc == 1
                        else "HARNESS_OR_PYTEST_USAGE_ERROR__NO_CREDIT"
                    ),
                    "stdout_tail": stdout_tail,
                    "stderr_tail": stderr_tail,
                }
            )
        total_counts = {key: 0 for key in ("failed", "passed", "errors", "skipped")}
        for row in invocation_rows:
            for key in total_counts:
                total_counts[key] += row["counts"][key]
        timeouts = [row["nodeid"] for row in invocation_rows if row["timed_out"]]
        harness_errors = [
            row["nodeid"]
            for row in invocation_rows
            if row["returncode"] not in (0, 1, 124)
        ]
        collection_ok = collection_rc == 0 and bool(nodeids)
        all_invoked = len(invocation_rows) == len(nodeids)
        no_harness_failure = collection_ok and all_invoked and not harness_errors
        if not no_harness_failure:
            aggregate_rc = 2
            status = "HARNESS_OR_COLLECTION_INTEGRITY_FAILURE__NO_CREDIT"
        elif total_counts["failed"] or timeouts:
            aggregate_rc = 1
            status = "PUBLISHED_TESTS_FAIL_OR_TIMEOUT__HARD_OPEN"
        else:
            aggregate_rc = 0
            status = "PUBLISHED_TESTS_PASS_ON_BUGGY_PROGRAM__NO_REPAIR_CLAIM"
        combined_stdout = "\n".join(
            [f"COLLECTION rc={collection_rc}", collection_stdout]
            + [row["stdout_tail"] for row in invocation_rows]
        )
        combined_stderr = "\n".join(
            [collection_stderr] + [row["stderr_tail"] for row in invocation_rows]
        )
        rows.append(
            {
                "task": task,
                "published_test_file": rel,
                "published_test_sha256": sha256_bytes(test_bytes),
                "pytest_python": sys.executable,
                "pytest_collection_command_tail": " ".join(collection_cmd[-3:]),
                "collection_returncode": collection_rc,
                "collection_node_count": len(nodeids),
                "collection_nodeids": nodeids,
                "collection_stdout_tail": collection_stdout,
                "collection_stderr_tail": collection_stderr,
                "invocation_row_count": len(invocation_rows),
                "invocations": invocation_rows,
                "returncode": aggregate_rc,
                "counts": total_counts,
                "timeouts": timeouts,
                "harness_errors": harness_errors,
                "no_harness_integrity_failure": no_harness_failure,
                "status": status,
                "stdout_tail": _text_tail(combined_stdout, 800),
                "stderr_tail": _text_tail(combined_stderr, 400),
            }
        )
    returncodes = [row["returncode"] for row in rows]
    total_collected = sum(row["collection_node_count"] for row in rows)
    total_invoked = sum(row["invocation_row_count"] for row in rows)
    total_passes = sum(row["counts"]["passed"] for row in rows)
    total_failures = sum(row["counts"]["failed"] for row in rows)
    total_timeouts = sum(len(row["timeouts"]) for row in rows)
    total_skips = sum(row["counts"]["skipped"] for row in rows)
    return {
        "tasks": tasks,
        "task_count": len(tasks),
        "known_wins_retested": 0,
        "rows": rows,
        "returncode_counts": {str(rc): returncodes.count(rc) for rc in sorted(set(returncodes))},
        "tasks_with_published_test_failure": sum(1 for rc in returncodes if rc == 1),
        "published_test_failures": sum(1 for rc in returncodes if rc == 1),
        "total_collected_published_tests": total_collected,
        "total_invoked_published_tests": total_invoked,
        "total_published_test_passes": total_passes,
        "total_published_test_failures": total_failures,
        "total_published_test_timeouts": total_timeouts,
        "total_published_test_skips": total_skips,
        "per_test_timeout_seconds": per_test_timeout,
        "test_isolation": "ONE_REAL_PUBLISHED_NODE_ID_PER_STDLIB_SUBPROCESS_TIMEOUT",
        "no_test_file_edits": True,
        "timeout_plugin_dependency": False,
        "pytest_plugin_autoload_disabled": True,
        "no_repair_claimed": True,
        "no_harness_integrity_failure": all(row["no_harness_integrity_failure"] for row in rows),
        "all_published_tests_collected_and_invoked": total_collected == total_invoked and total_collected > 0,
        "no_hidden_skips": total_skips == 0,
    }


def build_receipt(
    quixbugs_root: pathlib.Path,
    per_test_timeout: float = DEFAULT_PER_TEST_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    receipts = {name: read_json(ROOT / rel) for name, rel in RECEIPTS.items()}
    union = receipts["union"]
    four = receipts["four_levers"]
    insufficiency = receipts["insufficiency"]
    index = receipts["index"]
    composition = receipts["composition"]
    weight_fuel = receipts["weight_fuel"]
    why_weights = receipts["why_weights"]
    unbound = receipts["unbound_name"]

    tasks = list(FROZEN_V2_HARD_OPEN_TASKS)
    known_wins = set(FROZEN_V2_KNOWN_WINS)
    current_union_hard_open_count = union.get("hard_open_population_count")
    current_union_hard_open_tasks = list(union.get("hard_open_population_tasks", []))
    answer_keys_present_in_source = (quixbugs_root / "correct_python_programs").exists()

    with tempfile.TemporaryDirectory(prefix="brain_hard_open_") as tmp:
        fresh = pathlib.Path(tmp) / "quixbugs_fresh"
        copy_info = fresh_hard_open_copy(quixbugs_root, fresh)
        test_files_present = all(
            (fresh / "python_testcases" / f"test_{task}.py").is_file() for task in tasks
        )
        source_test_files_present = all(
            (quixbugs_root / "python_testcases" / f"test_{task}.py").is_file() for task in tasks
        )
        hard_open_run = run_hard_open_tests(fresh, tasks, per_test_timeout)
        hard_open_run["frozen_v2_population_count"] = len(FROZEN_V2_HARD_OPEN_TASKS)
        hard_open_run["frozen_v2_population_source"] = (
            "THE_VERIFIED_INDEX_IS_THE_BOTTLENECK_20261116_V2.md#9 and the union receipt at e9bfca97667e5293b1206fcda935732176fe6504"
        )
        hard_open_run["current_union_receipt_hard_open_count"] = current_union_hard_open_count
        hard_open_run["current_union_receipt_hard_open_tasks"] = current_union_hard_open_tasks
        hard_open_run["external_repair_reclassification_credit"] = "ZERO"
        hard_open_run["frozen_v2_known_wins_not_retested"] = sorted(FROZEN_V2_KNOWN_WINS)
        hard_open_run["no_known_win_retested_as_progress"] = True
        copy_info["source_has_correct_python_programs"] = answer_keys_present_in_source
        copy_info["fresh_copy_excludes_answer_keys"] = copy_info["answer_keys_absent"]
        copy_info["published_test_files_present"] = test_files_present and source_test_files_present
        copy_info["published_test_bytes_hashed"] = all(
            len(row["published_test_sha256"]) == 64 for row in hard_open_run["rows"]
        )

    intent = read_json(ROOT / INTENT) if (ROOT / INTENT).is_file() else {}
    model = read_json(ROOT / "canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json")
    organs_present = {
        group: [p for p in paths if (ROOT / p).exists()]
        for group, paths in ORGANS_BY_EFFECT.items()
    }
    organs_missing = {
        group: [p for p in paths if not (ROOT / p).exists()]
        for group, paths in ORGANS_BY_EFFECT.items()
        if any(not (ROOT / p).exists() for p in paths)
    }

    certificate = insufficiency["real_code_repair_corpus"]["certificate"]
    vocab_cost = insufficiency["vocabulary_repair_cost"]
    compose_summary = composition["summary"]
    levers = four["levers"]
    unbound_kept = unbound["measured_effect_kept"]

    invariants = {
        "all_receipts_and_organs_present": not organs_missing and all((ROOT / p).is_file() for p in RECEIPTS.values()),
        "answer_doc_and_action_intent_present": (ROOT / ANSWER_DOC).is_file() and (ROOT / INTENT).is_file(),
        "terminal_truth_untouched": intent.get("truth", {}).get("achieved") is False,
        "model_has_zero_knowledge_house_dependency": model.get("digest", {}).get("value") is not None and "weights" not in model,
        "frozen_v2_population_is_exactly_16": len(tasks) == 16 and len(FROZEN_V2_HARD_OPEN_TASKS) == 16,
        "frozen_v2_population_excludes_frozen_known_wins": not (set(tasks) & known_wins),
        "published_test_files_present": copy_info["published_test_files_present"],
        "published_test_bytes_hashed": copy_info["published_test_bytes_hashed"],
        "answer_keys_absent_in_fresh_copy": copy_info["answer_keys_absent"],
        "no_synthetic_tasks": copy_info["no_synthetic_tasks"],
        "no_harness_integrity_failure": hard_open_run["no_harness_integrity_failure"],
        "all_published_tests_collected_and_invoked": hard_open_run["all_published_tests_collected_and_invoked"],
        "no_hidden_skips": hard_open_run["no_hidden_skips"],
        "no_test_edits_or_timeout_plugin": (
            hard_open_run["no_test_file_edits"]
            and not hard_open_run["timeout_plugin_dependency"]
            and hard_open_run["pytest_plugin_autoload_disabled"]
        ),
        "hard_open_timeouts_reported_as_failures_not_harness_errors": (
            hard_open_run["total_published_test_timeouts"] > 0
            and hard_open_run["no_harness_integrity_failure"]
        ),
        "no_repair_claimed_from_hard_open_run": hard_open_run["no_repair_claimed"],
        "no_external_repair_reclassification_credit": True,
        "current_union_receipt_changed_after_v2": current_union_hard_open_count != 16,
        "current_union_hard_open_population_is_subset_of_frozen_v2_population": (
            set(current_union_hard_open_tasks).issubset(set(FROZEN_V2_HARD_OPEN_TASKS))
        ),
        "identifiability_is_not_one_demonstration": (
            levers.get("bits_after_one", 0) > 3.8
            and levers.get("verified_by_rerun_20261116", {}).get("targets_exact_after_one") == 0
            and levers.get("verified_by_rerun_20261116", {}).get("targets_settled_after_one_then_ask") == 10
        ),
        "vocabulary_insufficiency_requires_a_new_observable": (
            certificate.get("unrepairable_by_repetition") is True
            and "A_NEW_OBSERVABLE" in certificate.get("what_would_repair_it", "")
            and vocab_cost.get("closed_vocabulary_size") == 31
            and vocab_cost.get("hypotheses_that_would_need_enumerating") == 8388608
            and vocab_cost.get("learner_enumeration_cap") == 12
        ),
        "verified_index_lacks_the_policy_observable": (
            index.get("usable_key_families") == []
            and index.get("verdict") == "NO_GRANULARITY_OF_THESE_FEATURES_SEPARATES_WHAT_THE_POLICY_DEPENDS_ON"
            and len(index.get("sweep", [])) == 5
            and len(index.get("instance_sensitivity", {}).get("kinds_whose_policy_set_changes_with_instance", [])) == 5
        ),
        "composition_needs_a_frame_and_proves_refusals": (
            compose_summary.get("solved") == 14
            and compose_summary.get("proven_unreachable") == 2
            and compose_summary.get("relaxed_plans_that_break_the_frame") == 15
            and compose_summary.get("prediction_mismatches") == 0
            and compose_summary.get("unrequested_side_effects") == 0
        ),
        "unbound_name_retraction_is_respected": (
            unbound.get("decision") == "THE_DESCRIPTION_WAS_NEVER_THE_PROBLEM__THE_BINDING_WAS"
            and unbound_kept.get("bits_per_step_still_reported") == 5.428
            and "REDUNDANCY" in unbound_kept.get("what_that_number_now_means", "")
        ),
        "weight_training_fuel_is_not_ready": (
            weight_fuel.get("ready_to_train") is False
            and weight_fuel.get("total_verified_units") == 64
            and weight_fuel.get("minimum_units_to_try") == 5000
            and "NOT_TO_TRAIN_A_MODEL" in weight_fuel.get("conclusion", "")
        ),
        "cross_kind_transfer_is_zero_without_index": (
            why_weights.get("the_two_arms_that_settle_it", {})
            .get("another_kind_of_change_these_files", {})
            .get("right_not_imports")
            == 0
        ),
        "existing_weight_gate_is_reused_not_rebuilt": (ROOT / "canonical/swe_kernel/weight_update_admission_v1.py").is_file(),
        "zero_new_parameters_admitted": True,
        "external_model_not_used": MODEL_DEPENDENCY_COUNT == 0 and EXTERNAL_CAPABILITY_PROVIDER_COUNT == 0,
        "no_network_at_run_time": NETWORK_DEPENDENCY_COUNT == 0 and copy_info["network_calls_at_run_time"] == 0,
        "zero_incremental_spend": INCREMENTAL_SPEND_USD == 0 and copy_info["incremental_spend_usd"] == 0,
    }
    audit_pass = all(invariants.values())

    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "generated_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "upstream": UPSTREAM,
        "quixbugs_head": git_head(quixbugs_root),
        "answer": "NO_SINGLE_SUFFICIENT_LEVER__HIGHEST_LEVERAGE_NECESSARY_CONDITION_IS_THE_VERIFIED_INDEX",
        "equation": "truth in H(I, failure_evidence) AND o in O splits survivors AND V reads the split AND proof is fresh on state in hand",
        "three_blockers_as_one_verified_index": {
            "identifiability": "no split from one trace; chosen causal observation splits survivors",
            "vocabulary_insufficiency": "index key does not contain the policy-relevant observable; repetition reports the same fact vector",
            "synthesis_verification_asymmetry": "replay handles repeated syntax; grounded proposal plus execution verifier and frame handle new work",
            "status": "THREE_PROJECTIONS_OF_ONE_NECESSARY_CONDITION_NOT_A_SINGLE_SUFFICIENT_LEVER",
        },
        "calculated_parameter_admission": {
            "law": CALCULATED_BIT_LAW,
            "parameter_candidates_admitted": 0,
            "parameters_added": 0,
            "weights_touched": 0,
            "knowledge_house": False,
            "instant_knowledge": "content-addressed zero-weight compiled model; facts remain inspectable and deletable",
            "existing_gate": "canonical/swe_kernel/weight_update_admission_v1.py",
            "why_zero_is_optimal": (
                "No calculated bit has passed a live causal split, independent verifier, "
                "archive-regression-zero and fresh-state-proof gate. Adding weights now would "
                "industrialize an unmeasured update, not solve the missing observable."
            ),
            "status": "ZERO_NEW_PARAMETERS__BEST_PART_IS_NO_PART",
        },
        "hard_open_test_integrity": copy_info | hard_open_run,
        "measured_receipts": RECEIPTS,
        "organs_by_effect": ORGANS_BY_EFFECT,
        "organs_present": organs_present,
        "organs_missing": organs_missing,
        "measured_facts": {
            "union": {
                "repaired_union": union.get("repaired_union_count", len(known_wins)),
                "hard_open": union.get("hard_open_population_count", len(tasks)),
                "frozen_v2_hard_open": len(tasks),
                "example_searchable_open": union.get("example_searchable_open_count"),
                "unmeasurable_without_examples": union.get("unmeasurable_without_published_input_output_examples_count"),
            },
            "four_levers": {
                "bits_before": levers.get("bits_before"),
                "bits_after_one": levers.get("bits_after_one"),
                "bits_per_further_demonstration": levers.get("bits_removed_by_each_further_demo"),
                "targets_exact_after_one": levers.get("verified_by_rerun_20261116", {}).get("targets_exact_after_one"),
                "targets_settled_after_one_then_ask": levers.get("verified_by_rerun_20261116", {}).get("targets_settled_after_one_then_ask"),
            },
            "insufficiency_certificate": certificate,
            "vocabulary_repair_cost": vocab_cost,
            "index": {
                "verdict": index.get("verdict"),
                "reading": index.get("reading"),
                "usable_key_families": index.get("usable_key_families"),
                "sweep": index.get("sweep"),
            },
            "composition_with_frame": compose_summary,
            "weight_fuel": {
                "conclusion": weight_fuel.get("conclusion"),
                "ready_to_train": weight_fuel.get("ready_to_train"),
                "total_verified_units": weight_fuel.get("total_verified_units"),
                "minimum_units_to_try": weight_fuel.get("minimum_units_to_try"),
            },
            "unbound_name_retraction": unbound_kept,
        },
        "invariants": invariants,
        "audit_pass": audit_pass,
        "hard_nonclaims": list(HARD_NONCLAIMS),
        "model_dependency_count": MODEL_DEPENDENCY_COUNT,
        "external_capability_provider_count": EXTERNAL_CAPABILITY_PROVIDER_COUNT,
        "network_dependency_count": NETWORK_DEPENDENCY_COUNT,
        "incremental_spend_usd": INCREMENTAL_SPEND_USD,
        "capability_credit": "ZERO",
        "terminal_credit": "ZERO",
        "independent_verification_completed": False,
        "independent_verification_note": "Producer-run sandbox; independent reproduction is open.",
    }


def main(argv: Iterable[str] | None = None) -> int:
    global ROOT, VERIFICATION, ACTION_INTENTS
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quixbugs", required=True, help="pinned real QuixBugs clone")
    parser.add_argument("--out", default=OUTPUT_RECEIPT, help="where to write the receipt")
    parser.add_argument("--repo-root", default=str(ROOT), help="repository root holding receipts")
    parser.add_argument(
        "--per-test-timeout",
        type=float,
        default=DEFAULT_PER_TEST_TIMEOUT_SECONDS,
        help="standard-library process timeout for one real published test node id",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.per_test_timeout <= 0:
        parser.error("--per-test-timeout must be positive")
    ROOT = pathlib.Path(args.repo_root).resolve()
    VERIFICATION = ROOT / "canonical" / "verification"
    ACTION_INTENTS = ROOT / "canonical" / "action_intents"
    quixbugs_root = pathlib.Path(args.quixbugs).resolve()
    if not (quixbugs_root / "python_testcases").is_dir():
        parser.error(f"not a QuixBugs clone with python_testcases: {quixbugs_root}")
    receipt = build_receipt(quixbugs_root, args.per_test_timeout)
    out = (ROOT / args.out).resolve() if not pathlib.Path(args.out).is_absolute() else pathlib.Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    run = receipt["hard_open_test_integrity"]
    print(
        "hard_open_tasks={task_count} tasks_failing={published_test_failures} "
        "published_tests_collected={total_collected_published_tests} "
        "published_tests_invoked={total_invoked_published_tests} "
        "test_timeouts={total_published_test_timeouts} "
        "skips={total_published_test_skips} "
        "no_harness_integrity_failure={no_harness_integrity_failure} "
        "audit_pass={audit_pass}".format(
            task_count=run["task_count"],
            published_test_failures=run["published_test_failures"],
            total_collected_published_tests=run["total_collected_published_tests"],
            total_invoked_published_tests=run["total_invoked_published_tests"],
            total_published_test_timeouts=run["total_published_test_timeouts"],
            total_published_test_skips=run["total_published_test_skips"],
            no_harness_integrity_failure=run["no_harness_integrity_failure"],
            audit_pass=receipt["audit_pass"],
        )
    )
    print(f"WROTE {out}")
    return 0 if receipt["audit_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
