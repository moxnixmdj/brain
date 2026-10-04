#!/usr/bin/env python3
"""Exact synthetic pointwise-optimality audit for frozen active legacy-15 LiveBench.

For each public synthetic contract:
1. the runtime planner receives visible prompt text only and emits one candidate;
2. the exact pinned public checkers produce the candidate's boolean result vector;
3. only if the candidate is not full-score, every required next-cardinality
   checker subset is independently reclassified by the semantic UNSAT kernel;
4. the distribution-free pointwise certificate kernel verifies completeness.

A passing row proves the emitted candidate is score-optimal for that row without
using terminal frequencies or the Opus response. This audit is still synthetic
profile evidence, not terminal acceptance credit.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys
from typing import Any

from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as archetypes
from canonical.runtime import livebench_legacy15_end2end_exact_synthetic_audit_v2 as v2
from canonical.runtime import livebench_legacy15_end2end_witness_or_unsat_audit_v3 as v3
from canonical.runtime import livebench_legacy15_pointwise_candidate_planner_v1 as planner
from canonical.runtime import livebench_legacy15_slot_feasibility_v1 as feasibility
from canonical.runtime import livebench_pointwise_optimality_certificate_v1 as pointwise

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_POINTWISE_EXACT_SYNTHETIC_AUDIT_V4"


def exact_flags(
    response: str,
    records: list[dict[str, Any]],
    registry,
    solver_instruction_ids: list[str],
) -> tuple[list[bool], list[str]]:
    by_id: dict[str, bool] = {}
    errors: list[str] = []
    for record in records:
        iid = str(record["instruction_id"])
        inst = registry.INSTRUCTION_DICT[iid](iid)
        inst.build_description(**record["kwargs"])
        try:
            by_id[iid] = bool(inst.check_following(response))
        except Exception as exc:
            by_id[iid] = False
            errors.append(iid + ":EXCEPTION:" + type(exc).__name__)
    if set(by_id) != set(solver_instruction_ids):
        errors.append("SOLVER_ORACLE_ID_SET_MISMATCH")
    return [bool(by_id.get(iid, False)) for iid in solver_instruction_ids], errors


def semantically_verified_required_unsat_subsets(
    visible_constraints: list[dict[str, Any]],
    checker_flags: list[bool],
) -> tuple[list[tuple[int, ...]], list[dict[str, Any]]]:
    required = pointwise.required_next_cardinality_subsets(
        len(checker_flags), sum(bool(x) for x in checker_flags)
    )
    supplied: list[tuple[int, ...]] = []
    proofs: list[dict[str, Any]] = []
    for subset in required:
        rows = [visible_constraints[i] for i in subset]
        out = feasibility.classify_visible_contracts(rows)
        if out.get("status") == "PROVED_UNSAT":
            supplied.append(tuple(subset))
            proofs.append({
                "indices": list(subset),
                "instruction_ids": [str(visible_constraints[i]["instruction_id"]) for i in subset],
                "hard_unsat_reasons": list(out.get("hard_unsat_reasons") or []),
            })
    return supplied, proofs


def audit(livebench_root: Path, max_failures: int) -> dict[str, Any]:
    legacy = livebench_root / "livebench/if_runner/instruction_following_eval"
    assert v2.git_blob_sha(legacy / "instructions_registry.py") == v2.FROZEN_REGISTRY_BLOB
    assert v2.git_blob_sha(legacy / "instructions.py") == v2.FROZEN_INSTRUCTIONS_BLOB

    sys.path.insert(0, str(livebench_root / "livebench/if_runner"))
    from instruction_following_eval import instructions_registry as registry

    sets = archetypes.enumerate_compatible_sets()
    assert len(sets) == v2.EXPECTED_SET_COUNT

    total = 0
    planner_fail = 0
    full_score = 0
    pointwise_certified_nonfull = 0
    pointwise_fail = 0
    oracle_errors = 0
    failures: list[dict[str, Any]] = []
    by_archetype = defaultdict(Counter)
    by_profile = defaultdict(Counter)
    selected_size = Counter()
    candidate_g = Counter()
    missing_subset_count = Counter()
    unsat_reason_count = Counter()

    for ids in sets:
        arch = archetypes.archetype(ids)
        for profile in v3.PROFILES:
            for reverse in (False, True):
                total += 1
                prompt, records = v2.render_prompt(ids, profile, registry, reverse)
                out = planner.solve(prompt)
                ba = by_archetype[arch]
                bp = by_profile[profile["name"]]

                if out.get("status") != "PASS_POINTWISE_CANDIDATE_PLAN":
                    planner_fail += 1
                    ba["planner_fail"] += 1
                    bp["planner_fail"] += 1
                    if len(failures) < max_failures:
                        failures.append({
                            "ids": list(ids),
                            "profile": profile["name"],
                            "order": "reverse" if reverse else "forward",
                            "stage": "planner",
                            "reason": out.get("error") or out.get("status"),
                        })
                    continue

                visible = list(out["visible_constraints"])
                solver_ids = [str(c["instruction_id"]) for c in visible]
                flags, errors = exact_flags(str(out["response"]), records, registry, solver_ids)
                if errors:
                    oracle_errors += 1
                    ba["oracle_error"] += 1
                    bp["oracle_error"] += 1
                    if len(failures) < max_failures:
                        failures.append({
                            "ids": list(ids),
                            "profile": profile["name"],
                            "order": "reverse" if reverse else "forward",
                            "stage": "exact_oracle",
                            "errors": errors,
                        })
                    continue

                g = sum(flags)
                k = len(flags)
                selected_size[int(out["selected_constraint_count"])] += 1
                candidate_g[g] += 1

                if g == k:
                    full_score += 1
                    ba["full_score"] += 1
                    bp["full_score"] += 1
                    continue

                supplied, proofs = semantically_verified_required_unsat_subsets(visible, flags)
                for proof in proofs:
                    for reason in proof["hard_unsat_reasons"]:
                        unsat_reason_count[reason] += 1
                cert = pointwise.verify_pointwise_optimality_structure(flags, supplied)
                if cert.get("status") == "PASS__POINTWISE_OPTIMALITY_STRUCTURE_COMPLETE":
                    pointwise_certified_nonfull += 1
                    ba["pointwise_certified_nonfull"] += 1
                    bp["pointwise_certified_nonfull"] += 1
                else:
                    pointwise_fail += 1
                    missing = list(cert.get("missing_unsat_subsets") or [])
                    missing_subset_count[len(missing)] += 1
                    ba["pointwise_fail"] += 1
                    bp["pointwise_fail"] += 1
                    if len(failures) < max_failures:
                        failures.append({
                            "ids": list(ids),
                            "profile": profile["name"],
                            "order": "reverse" if reverse else "forward",
                            "stage": "pointwise_certificate",
                            "checker_flags": flags,
                            "selected_indices": out["selected_indices"],
                            "missing_unsat_subsets": missing,
                        })

    certified = full_score + pointwise_certified_nonfull
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__ALL_SYNTHETIC_CASES_POINTWISE_SCORE_OPTIMAL"
            if certified == total
            else "FAIL_CLOSED__POINTWISE_REPAIR_LEDGER_EMITTED"
        ),
        "bindings": {
            "livebench_commit": v2.FROZEN_LIVEBENCH_COMMIT,
            "registry_blob": v2.FROZEN_REGISTRY_BLOB,
            "instructions_blob": v2.FROZEN_INSTRUCTIONS_BLOB,
            "planner_schema": planner.SCHEMA,
            "semantic_unsat_schema": feasibility.SCHEMA,
            "pointwise_certificate_schema": pointwise.SCHEMA,
        },
        "scope": {
            "compatible_identity_sets": len(sets),
            "parameter_profiles": len(v3.PROFILES),
            "orders_per_profile": 2,
            "synthetic_cases": total,
            "terminal_rows_read": 0,
            "terminal_prompts_read": 0,
            "terminal_scores_read": 0,
            "terminal_frequency_inference": False,
        },
        "results": {
            "planner_fail": planner_fail,
            "full_score": full_score,
            "pointwise_certified_nonfull": pointwise_certified_nonfull,
            "pointwise_fail": pointwise_fail,
            "oracle_errors": oracle_errors,
            "pointwise_certified_total": certified,
            "pointwise_certified_fraction": certified / total,
        },
        "selected_constraint_count_distribution": dict(sorted(selected_size.items())),
        "candidate_true_checker_count_distribution": dict(sorted(candidate_g.items())),
        "missing_required_unsat_subset_count_distribution": dict(sorted(missing_subset_count.items())),
        "semantic_unsat_reason_counts": dict(unsat_reason_count.most_common()),
        "by_archetype": {k: dict(v) for k, v in sorted(by_archetype.items())},
        "by_profile": {k: dict(v) for k, v in sorted(by_profile.items())},
        "failure_samples": failures,
        "hard_nonclaims": [
            "SYNTHETIC_PUBLIC_PROFILE_EVIDENCE_ONLY",
            "SEVEN_PARAMETER_PROFILES_DO_NOT_PROVE_THE_ENTIRE_GENERATOR_SLOT_DOMAIN",
            "NO_TERMINAL_CASE_CONTENT_READ",
            "NO_TERMINAL_FREQUENCY_INFERENCE",
            "NO_LIVEBENCH_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--livebench-root", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--max-failures", type=int, default=250)
    ns = ap.parse_args()
    result = audit(Path(ns.livebench_root).resolve(), ns.max_failures)
    Path(ns.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], **result["results"]}, sort_keys=True))
    return 0 if result["status"].startswith("PASS__") else 1


if __name__ == "__main__":
    raise SystemExit(main())
