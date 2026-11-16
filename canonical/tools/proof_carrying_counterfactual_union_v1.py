#!/usr/bin/env python3
"""Audit the real hard-open population before any further learning claim.

This tool does NOT propose an action, repair a program, train a weight, register a
capability, or claim verification. It answers one integrity question first:

    Across every measured repair receipt in this tree, which REAL published
    QuixBugs tasks have already been repaired, and which tasks are still open?

The answer is the admission population for any future mechanism. Re-running a task
that some earlier receipt already repaired is not progress. A test on an invented
toy is not a hardest-open test. The tool therefore reads measured receipts and the
real corpus test-file names, asserts their set algebra, and writes a receipt.

The name records the answer's unit without declaring a capability: in a live
environment the binding quantity is SEPARATION -- a hypothesis space that contains
the truth and an observation that splits it. Maintaining separation in an open
world requires an operation, the premise under which it preserves meaning, and a
falsifiable counterfactual verdict derived from live execution. Those parts
already exist in the tree under non-obvious names; this tool only prevents future
sessions from rebuilding or congratulating them.

Authority NONE. Producer-run, one sandbox. No model call, no network call, $0.
`truth.achieved` is not touched. No protected path is touched.

Usage:
    python3 canonical/tools/proof_carrying_counterfactual_union_v1.py \
        --quixbugs /path/to/QuixBugs \
        --out canonical/verification/PROOF_CARRYING_COUNTERFACTUAL_UNION_20261116_V1.json
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys
from typing import Any, Iterable

SCHEMA = "BRAIN_PROOF_CARRYING_COUNTERFACTUAL_UNION_AUDIT_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
ANSWER_KEY = "correct_python_programs"
MODEL_DEPENDENCY_COUNT = 0
NETWORK_DEPENDENCY_COUNT = 0
INCREMENTAL_SPEND_USD = 0

ROOT = pathlib.Path(__file__).resolve().parents[2]
VERIFICATION = ROOT / "canonical" / "verification"

#: Every receipt in the measured repair line that reports a task list. These are
#: read from the current tree; no task name below is hard-coded as a known win.
REPAIR_RECEIPTS = (
    "COMPARISONS_CLOSE_THE_LAST_MILE_20261116_V1.json",
    "THE_EDIT_SPACE_IS_THE_PROGRAM_NOT_A_LIST_20261116_V1.json",
    "REGION_REWRITES_AND_THE_REFUSAL_AUDIT_20261116_V1.json",
    "CONTRACT_GROUNDED_REPAIR_20261116_V1.json",
    "INTERVENTIONAL_GOAL_20261116_V1.json",
)

#: Mechanisms indexed by EFFECT, not filename. A future session that searches for
#: obvious names and declares a part missing should find this census first.
MECHANISM_GROUPS: dict[str, tuple[str, ...]] = {
    "capture_and_premise": (
        "canonical/swe_kernel/verified_skill_crystallizer_v1.py",
        "canonical/swe_kernel/one_demonstration_reach_v1.py",
        "canonical/runtime/applicability_v1.py",
        "canonical/swe_kernel/lesson_admission_gate_v1.py",
    ),
    "constructive_actions_and_operands": (
        "canonical/tools/grammar_closed_repair_v1.py",
        "canonical/tools/quixbugs_required_edit_taxonomy_v1.py",
        "canonical/runtime/derived_value_v1.py",
        "canonical/runtime/inert_action_prior_v1.py",
    ),
    "goal_and_counterfactual_verdict": (
        "canonical/swe_kernel/contract_grounded_repair_v1.py",
        "canonical/swe_kernel/interventional_goal_v1.py",
        "canonical/runtime/semantic_operator_counterfactuals.py",
        "canonical/runtime/contrast_selection_v1.py",
    ),
    "identification_and_separation": (
        "canonical/runtime/finite_identifiability.py",
        "canonical/tools/identification_cost_in_a_real_space_v1.py",
        "canonical/swe_kernel/specification_from_structure_v1.py",
        "canonical/tools/grammar_closed_repair_v1.py",
    ),
    "independent_witness_and_admission": (
        "canonical/runtime/instruction_contract_v1.py",
        "canonical/runtime/instruction_policy_v1.py",
        "canonical/swe_kernel/test_suite_admission_v1.py",
        "canonical/swe_kernel/weight_update_admission_v1.py",
        "canonical/swe_kernel/learned_skill_verdict_v1.py",
    ),
    "hidden_synthesis_and_orchestration": (
        "canonical/runtime/counterexample_guided_causal_architecture_synthesizer_v1.py",
        "canonical/runtime/finite_grid_program_inducer_v1.py",
        "canonical/runtime/swe_observational_program_synthesizer_v1.py",
        "canonical/runtime/unified_cognitive_fabric_v1.py",
        "canonical/swe_kernel/closed_loop_autonomous_controller_v1.py",
        "canonical/runtime/bound_capabilities/software_patch_cegis_z3_v1.py",
        "canonical/runtime/bound_capabilities/hardcore_software_engineering_orchestrator_v1.py",
    ),
}

SUPERSEDES = (
    "THE_GOAL_IS_A_COUNTERFACTUAL_WORLD_MODEL_20261116_V1.md",
    "THE_GOAL_IS_THE_BOTTLENECK_20261116_V1.md",
    "WHAT_IS_REAL_AND_THE_ONE_BOTTLENECK_20261116_V1.md",
)

#: Newly merged evidence read by effect before this answer was written. These are
#: measured results, not prose permission slips.
EVIDENCE_READ = (
    "THE_EDIT_SPACE_IS_THE_PROGRAM_NOT_A_LIST_20261116_V1.md",
    "THE_HAND_WAS_NEVER_THE_BOTTLENECK_20261116_V1.md",
    "THE_JUDGE_WAS_THE_MISSING_PART_20261116_V1.md",
    "WHAT_ONE_DEMONSTRATION_REACHES_20261116_V1.md",
    "ONE_DEMONSTRATION_LEAVES_TEN_BITS_20261116_V1.md",
    "canonical/verification/IDENTIFICATION_COST_IN_A_REAL_SPACE_20261116_V1.json",
    "canonical/verification/ONE_DEMONSTRATION_REACH_20261116_V1.json",
    "canonical/verification/PROJECT_BRAIN_INSTRUCTION_POLICY_VERIFICATION_20261116_V1.json",
    "canonical/verification/INSTRUCTION_CONTRACT_20261116_V1.json",
    "canonical/verification/COMPARISONS_CLOSE_THE_LAST_MILE_20261116_V1.json",
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def repaired_from_receipt(data: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for value in (data.get("repaired_tasks"), data.get("measured", {}).get("repaired_tasks")):
        if isinstance(value, list):
            names.update(str(x) for x in value if isinstance(x, str) and x)
    for row in data.get("rows", []):
        if not isinstance(row, dict):
            continue
        status = str(row.get("status", ""))
        task = row.get("task") or row.get("name")
        if status.startswith("REPAIRED") and isinstance(task, str) and task:
            names.add(task)
        if row.get("repaired") is True and isinstance(task, str) and task:
            names.add(task)
    return names


def receipt_census(root: pathlib.Path = ROOT) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    union: set[str] = set()
    for name in REPAIR_RECEIPTS:
        path = root / "canonical" / "verification" / name
        if not path.is_file():
            rows.append({"receipt": name, "status": "MISSING", "repaired_tasks": []})
            continue
        data = read_json(path)
        names = repaired_from_receipt(data)
        union |= names
        rows.append({
            "receipt": name,
            "status": "READ",
            "sha256": sha256_bytes(path.read_bytes()),
            "repaired_count": data.get("repaired", data.get("measured", {}).get("repaired")),
            "repaired_tasks": sorted(names),
            "answer_keys_present": data.get("measured", {}).get("answer_keys_present"),
        })
    return {"rows": rows, "repaired_union": sorted(union)}


def real_task_names(quixbugs_root: pathlib.Path) -> list[str]:
    test_dir = quixbugs_root / "python_testcases"
    paths = sorted(test_dir.glob("test_*.py"))
    if not paths:
        raise RuntimeError("NO_REAL_PUBLISHED_TEST_FILES")
    return [p.stem[len("test_"):] for p in paths]


def mechanism_census(root: pathlib.Path = ROOT) -> dict[str, Any]:
    groups: dict[str, Any] = {}
    all_present = True
    for group, paths in MECHANISM_GROUPS.items():
        present = [p for p in paths if (root / p).is_file()]
        missing = [p for p in paths if p not in present]
        all_present = all_present and not missing
        groups[group] = {"count": len(present), "present": present, "missing": missing}
    return {"groups": groups, "all_declared_mechanism_files_present": all_present}


def upstream_head(quixbugs_root: pathlib.Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(quixbugs_root), "rev-parse", "HEAD"],
            check=True, capture_output=True, text=True, timeout=5,
        )
        return out.stdout.strip() or None
    except Exception:
        return None


def audit(quixbugs_root: pathlib.Path, root: pathlib.Path = ROOT) -> dict[str, Any]:
    tasks = real_task_names(quixbugs_root)
    census = receipt_census(root)
    repaired = set(census["repaired_union"])
    never = sorted(set(tasks) - repaired)
    unknown_repaired = sorted(repaired - set(tasks))
    unmeasurable = sorted(
        task for task in never
        if not (quixbugs_root / "json_testcases" / f"{task}.json").is_file()
    )
    searchable = [task for task in never if task not in set(unmeasurable)]
    mechanisms = mechanism_census(root)
    evidence_present = [p for p in EVIDENCE_READ if (root / p).is_file()]
    evidence_missing = [p for p in EVIDENCE_READ if p not in evidence_present]
    answer_key_counts = [
        row["answer_keys_present"] for row in census["rows"]
        if isinstance(row.get("answer_keys_present"), int)
    ]
    task_files_exist = all(
        (quixbugs_root / "python_testcases" / f"test_{task}.py").is_file()
        for task in tasks
    )
    invariants = {
        "all_task_names_from_real_published_test_files": task_files_exist and len(tasks) == len(set(tasks)),
        "repaired_and_open_partition_corpus": set(repaired) | set(never) == set(tasks),
        "no_known_win_in_open_population": not (set(repaired) & set(never)),
        "no_receipt_task_outside_real_corpus": not unknown_repaired,
        "no_answer_key_count_above_zero_in_measured_receipts": all(x == 0 for x in answer_key_counts),
        "all_declared_mechanism_files_present": mechanisms["all_declared_mechanism_files_present"],
        "all_newly_merged_evidence_files_read": not evidence_missing,
    }
    audit_pass = all(invariants.values())
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "generated_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "upstream": "https://github.com/jkoppel/QuixBugs",
        "upstream_head": upstream_head(quixbugs_root),
        "corpus": {
            "real_published_test_files": len(tasks),
            "task_names": tasks,
            "source_of_task_names": "python_testcases/test_*.py in a fresh clone; no invented task",
        },
        "measured_receipts": census["rows"],
        "repaired_union_count": len(repaired),
        "repaired_union_tasks": sorted(repaired),
        "known_wins_not_counted_as_progress": sorted(repaired),
        "hard_open_population_count": len(never),
        "hard_open_population_tasks": never,
        "example_searchable_open_tasks": searchable,
        "example_searchable_open_count": len(searchable),
        "unmeasurable_without_published_input_output_examples": unmeasurable,
        "unmeasurable_without_published_input_output_examples_count": len(unmeasurable),
        "unknown_receipt_tasks_outside_real_corpus": unknown_repaired,
        "mechanism_census_by_effect": mechanisms["groups"],
        "evidence_read_by_effect": evidence_present,
        "evidence_missing": evidence_missing,
        "invariants": invariants,
        "audit_pass": audit_pass,
        "killed_instruments": [
            {
                "instrument": "canonical/runtime/bound_capabilities/software_patch_cegis_z3_v1.py",
                "calibration_on_already_solved_tasks": "0 / 5",
                "calibration_tasks_not_counted_as_progress": [
                    "bitcount", "pascal", "quicksort", "is_valid_parenthesization", "rpn_eval"
                ],
                "open_task_probe_not_counted_as_progress": ["sqrt", "flatten", "to_base"],
                "reason_killed": (
                    "A zero result on open tasks would be vacuous because the instrument also "
                    "returned zero on five already-solved calibration tasks; sqrt hit its own "
                    "baseline timeout. Do not ship an all-zero open-task run as evidence."
                ),
            },
        ],
        "what_this_is": (
            "A set-algebra audit of measured receipts against the real published corpus, plus an "
            "effect-based census of mechanisms already in the tree. It is not a solver."
        ),
        "what_this_is_not": (
            "Not a repair contest, not a capability, not a benchmark score, not independent "
            "verification, not a proof of correctness, not a sentience claim, and not permission "
            "to merge over a red or missing referee."
        ),
        "hard_nonclaims": [
            "NOT_A_FRONTIER_SCORE",
            "NOT_SWE_BENCH",
            "NO_SYNTHETIC_TASKS",
            "NO_KNOWN_WIN_COUNTED_AS_PROGRESS",
            "NO_NEW_LEARNER_OR_VERIFIER",
            "NO_CAPABILITY_REGISTERED",
            "NO_PROTECTED_PATH_TOUCHED",
            "NO_MODEL_CALLS",
            "NO_NETWORK_CALLS",
            "NO_WEIGHT_UPDATE",
            "PRODUCER_RUN_NOT_INDEPENDENT_VERIFICATION",
            "TERMINAL_TRUTH_UNTOUCHED",
        ],
        "supersedes": list(SUPERSEDES),
        "model_dependency_count": MODEL_DEPENDENCY_COUNT,
        "network_dependency_count": NETWORK_DEPENDENCY_COUNT,
        "incremental_spend_usd": INCREMENTAL_SPEND_USD,
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quixbugs", required=True, help="path to a real QuixBugs clone")
    parser.add_argument("--out", required=True, help="where to write the audit receipt")
    parser.add_argument("--repo-root", default=str(ROOT), help="repository root holding receipts")
    args = parser.parse_args(list(argv) if argv is not None else None)
    quixbugs_root = pathlib.Path(args.quixbugs).resolve()
    repo_root = pathlib.Path(args.repo_root).resolve()
    result = audit(quixbugs_root, repo_root)
    out = pathlib.Path(args.out)
    if not out.is_absolute():
        out = repo_root / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"real_tasks={result['corpus']['real_published_test_files']} "
        f"repaired_union={result['repaired_union_count']} "
        f"hard_open={result['hard_open_population_count']} "
        f"example_searchable_open={result['example_searchable_open_count']} "
        f"unmeasurable={result['unmeasurable_without_published_input_output_examples_count']} "
        f"audit_pass={result['audit_pass']}"
    )
    return 0 if result["audit_pass"] else 2


if __name__ == "__main__":
    sys.exit(main())
