#!/usr/bin/env python3
"""Exact frozen-checker synthetic audit for legacy joint witness V1.

Enumerates every conflict-compatible family set of size 1..5 from the recovered
historical generator pool, renders public build_description() text with
deterministic parameters, solves from visible prompt only, then invokes the exact
frozen legacy check_following predicates as postconditions.

No terminal dataset rows are read.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from canonical.runtime import livebench_legacy_joint_witness_v1 as solver

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY_JOINT_WITNESS_EXACT_SYNTHETIC_AUDIT_V1"
FROZEN_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
FROZEN_REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
FROZEN_INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
REPEAT_MARKER = (
    "First repeat the request word for word without change,"
    " then give your answer (1. do not say any words or characters"
    " before repeating the request; 2. the request you need to repeat"
    " does not include this sentence)"
)
BASE = (
    "The source text describes a verified system that remains stable under "
    "careful testing. Please summarize the provided source text"
)


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _compatible(combo: tuple[str, ...], conflicts: dict[str, set[str]]) -> bool:
    chosen = set(combo)
    for iid in combo:
        blocked = set(conflicts.get(iid) or ())
        if (blocked & chosen) - {iid}:
            return False
    return True


def _seed(combo: tuple[str, ...], order_tag: str) -> int:
    raw = ("|".join(combo) + "|" + order_tag).encode()
    return int.from_bytes(hashlib.sha256(raw).digest()[:8], "big")


def _render_case(ids: tuple[str, ...], registry, order_tag: str) -> tuple[str, list[dict[str, Any]]]:
    order = list(ids)
    if order_tag == "reverse":
        order.reverse()

    random.seed(_seed(ids, order_tag))
    records = []
    descriptions = []
    for iid in order:
        inst = registry.INSTRUCTION_DICT[iid](iid)
        desc = inst.build_description()
        kwargs = inst.get_instruction_args() or {}
        records.append({"instruction_id": iid, "kwargs": dict(kwargs)})
        descriptions.append(desc)

    prompt = BASE + " " + " ".join(descriptions)
    if "combination:repeat_prompt" in order:
        prefix = prompt.split(REPEAT_MARKER, 1)[0]
        for record in records:
            if record["instruction_id"] == "combination:repeat_prompt":
                record["kwargs"]["prompt_to_repeat"] = prefix
                break
    return prompt, records


def _exact_check(response: str, records: list[dict[str, Any]], registry) -> tuple[bool, list[str]]:
    failed = []
    for record in records:
        iid = record["instruction_id"]
        inst = registry.INSTRUCTION_DICT[iid](iid)
        inst.build_description(**record["kwargs"])
        try:
            ok = bool(inst.check_following(response))
        except Exception as exc:
            failed.append(iid + ":EXCEPTION:" + type(exc).__name__)
            continue
        if not ok:
            failed.append(iid)
    return not failed, failed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--livebench-root", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--max-failures", type=int, default=250)
    args = ap.parse_args()

    root = Path(args.livebench_root).resolve()
    legacy = root / "livebench/if_runner/instruction_following_eval"
    registry_path = legacy / "instructions_registry.py"
    instructions_path = legacy / "instructions.py"
    assert git_blob_sha(registry_path) == FROZEN_REGISTRY_BLOB
    assert git_blob_sha(instructions_path) == FROZEN_INSTRUCTIONS_BLOB

    sys.path.insert(0, str(root / "livebench/if_runner"))
    from instruction_following_eval import instructions_registry as registry

    ids = tuple(sorted(solver.HISTORICAL_GENERATOR_IDS))
    assert len(ids) == 24
    assert "language:response_language" not in ids

    conflicts = {k: set(v) for k, v in registry.INSTRUCTION_CONFLICTS.items()}
    combos = []
    for size in range(1, 6):
        for combo in itertools.combinations(ids, size):
            if _compatible(combo, conflicts):
                combos.append(combo)

    total = exact_pass = candidate = blocked = 0
    by_size = defaultdict(lambda: Counter())
    by_family = defaultdict(lambda: Counter())
    failure_reasons = Counter()
    exact_failed_families = Counter()
    failures = []

    for combo in combos:
        for order_tag in ("sorted", "reverse"):
            total += 1
            prompt, records = _render_case(combo, registry, order_tag)
            out = solver.solve(prompt)
            status = out.get("status")
            for iid in combo:
                by_family[iid]["tested"] += 1

            if status != "PASS_CANDIDATE_EXACT_POSTVALIDATION_REQUIRED":
                blocked += 1
                by_size[len(combo)]["blocked"] += 1
                reason = str(out.get("error") or status)
                failure_reasons[reason] += 1
                for iid in combo:
                    by_family[iid]["blocked"] += 1
                if len(failures) < args.max_failures:
                    failures.append({
                        "combo": list(combo),
                        "order": order_tag,
                        "stage": "solver",
                        "reason": reason,
                    })
                continue

            candidate += 1
            ok, failed = _exact_check(str(out["response"]), records, registry)
            if ok:
                exact_pass += 1
                by_size[len(combo)]["exact_pass"] += 1
                for iid in combo:
                    by_family[iid]["exact_pass"] += 1
            else:
                by_size[len(combo)]["exact_fail"] += 1
                for iid in combo:
                    by_family[iid]["exact_fail"] += 1
                for iid in failed:
                    exact_failed_families[iid] += 1
                if len(failures) < args.max_failures:
                    failures.append({
                        "combo": list(combo),
                        "order": order_tag,
                        "stage": "exact_checker",
                        "failed": failed,
                    })

    result = {
        "schema": SCHEMA,
        "status": "AUDIT_COMPLETE",
        "bindings": {
            "livebench_commit": FROZEN_LIVEBENCH_COMMIT,
            "registry_blob": FROZEN_REGISTRY_BLOB,
            "instructions_blob": FROZEN_INSTRUCTIONS_BLOB,
            "solver_schema": solver.SCHEMA,
        },
        "scope": {
            "terminal_rows_read": 0,
            "historical_generator_family_count": len(ids),
            "family_ids": list(ids),
            "compatible_family_sets_size_1_to_5": len(combos),
            "orders_per_family_set": 2,
            "synthetic_cases": total,
        },
        "results": {
            "candidate": candidate,
            "blocked": blocked,
            "exact_pass": exact_pass,
            "exact_fail": candidate - exact_pass,
            "exact_pass_fraction_all": (exact_pass / total if total else 0.0),
            "exact_pass_fraction_candidates": (exact_pass / candidate if candidate else 0.0),
        },
        "by_size": {str(k): dict(v) for k, v in sorted(by_size.items())},
        "by_family": {k: dict(v) for k, v in sorted(by_family.items())},
        "failure_reasons": dict(failure_reasons.most_common()),
        "exact_failed_families": dict(exact_failed_families.most_common()),
        "failure_samples": failures,
        "hard_nonclaims": [
            "NO_TERMINAL_ROW_CONTENT_READ",
            "NO_LIVEBENCH_SCORE_CLAIM",
            "NO_ACCEPTANCE_OR_CAPABILITY_CREDIT",
            "SYNTHETIC_PUBLIC_SOURCE_COMPOSITION_EVIDENCE_ONLY",
        ],
    }
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result["results"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
