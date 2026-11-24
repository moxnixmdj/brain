#!/usr/bin/env python3
"""Deterministically select a fresh HARD-51 subset from pinned SWE-bench Pro V2.

This runner-side selector reads only release metadata and per-task ``task.toml``
configuration. It does not read problem statements, solutions, tests, verifier
outputs or model trajectories. It copies selected task directories to a runner
temporary directory so Harbor can use them; no raw benchmark task is saved in
the Brain repository. The workflow separately replaces each unpinned image tag
with the immutable digest observed from the public GHCR image.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import tomllib
from typing import Any

SCHEMA = "BRAIN_SWE_PRO_V2_HARD51_FRESH_SELECTION_V1"
RELEASE_TAG = "v2.0.0"
RELEASE_SHA = "66f92766bba642462d4bbe5479e83f91f9211862"
EXPECTED = {
    "v2/SHA256SUMS": "9d84f8507c89241d42d8b3ef911600a1ec75dbbb32687ce9b45b93318502c0bd",
    "v2/hard51_ids.txt": "6e35e84708a26443e1746ae928940555a3188654c90f3a2eb691f4f699482bd1",
    "v2/tooling/patch_replay.py": "5c8b344de37164e9723f1724c2573013957fb644c3913a64c12c1718c737d876",
}
RELEASE_ASSET_DIGESTS = {
    "SHA256SUMS": "2377c1a2462a911cca428611494d2595a17bd9ddf5af2e476c77566b0b40ed9a",
    "swe-bench-pro-v2.0.0-tasks.zip": "1b4e97502e7c73c6c96d86fd72ae3b67cb081af1796784157fe3097b34406947",
}
IMAGE_PREFIX = "ghcr.io/scaleapi/swe-bench_pro-v2:"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: pathlib.Path) -> str:
    return sha256_bytes(path.read_bytes())


def _read_ids(path: pathlib.Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _task_config(root: pathlib.Path, task_id: str) -> dict[str, Any]:
    return tomllib.loads((root / "v2" / "tasks" / task_id / "task.toml").read_text(encoding="utf-8"))


def verify_tree(
    root: pathlib.Path,
    *,
    expected: dict[str, str] | None = None,
    task_count: int = 642,
    hard51_count: int = 51,
) -> dict[str, Any]:
    expected = EXPECTED if expected is None else expected
    v2 = root / "v2"
    ids_path = v2 / "hard51_ids.txt"
    tasks_path = v2 / "tasks"
    checksums = {
        rel: sha256_file(root / rel) for rel in expected
    }
    ids = _read_ids(ids_path)
    task_dirs = sorted(p.name for p in tasks_path.iterdir() if p.is_dir())
    checks = {
        "sha256sums_file_matches": checksums.get("v2/SHA256SUMS") == expected.get("v2/SHA256SUMS"),
        "hard51_ids_file_matches": checksums.get("v2/hard51_ids.txt") == expected.get("v2/hard51_ids.txt"),
        "patch_replay_file_matches": checksums.get("v2/tooling/patch_replay.py") == expected.get("v2/tooling/patch_replay.py"),
        "hard51_count": len(ids) == hard51_count,
        "task_count": len(task_dirs) == task_count,
        "hard51_ids_present": all((tasks_path / task_id).is_dir() for task_id in ids),
        "hard51_ids_unique": len(ids) == len(set(ids)),
    }
    metadata_checks = {
        "agent_no_network": True,
        "verifier_public_network": True,
        "docker_image_tag_exact": True,
        "agent_timeout_sec": True,
    }
    tags: dict[str, str] = {}
    for task_id in ids:
        config = _task_config(root, task_id)
        agent = config.get("agent") or {}
        verifier = config.get("verifier") or {}
        env = config.get("environment") or {}
        tag = str(env.get("docker_image") or "")
        tags[task_id] = tag
        metadata_checks["agent_no_network"] &= agent.get("network_mode") == "no-network"
        metadata_checks["verifier_public_network"] &= verifier.get("network_mode") == "public"
        metadata_checks["docker_image_tag_exact"] &= tag == IMAGE_PREFIX + task_id
        metadata_checks["agent_timeout_sec"] &= float(agent.get("timeout_sec") or 0) > 0
    checks.update(metadata_checks)
    failed = sorted(k for k, v in checks.items() if not v)
    if failed:
        raise SystemExit("SWE_PRO_V2_RELEASE_METADATA_CHECK_FAIL " + repr(failed))
    return {
        "checks": checks,
        "checksums": checksums,
        "hard51_count": len(ids),
        "task_count": len(task_dirs),
        "hard51_ids": ids,
        "image_tags": tags,
    }


def selection_key(run_id: str, task_id: str) -> str:
    return sha256_bytes(f"{run_id}:{task_id}".encode("utf-8"))


def build_selection(
    root: pathlib.Path,
    out_dir: pathlib.Path,
    run_id: str,
    count: int,
    *,
    expected: dict[str, str] | None = None,
    task_count: int = 642,
    hard51_count: int = 51,
) -> dict[str, Any]:
    if count <= 0 or count > hard51_count:
        raise SystemExit("SWE_PRO_V2_SELECTION_COUNT_OUT_OF_RANGE")
    verification = verify_tree(
        root,
        expected=expected,
        task_count=task_count,
        hard51_count=hard51_count,
    )
    ids = verification["hard51_ids"]
    ranked = sorted(ids, key=lambda task_id: (selection_key(run_id, task_id), task_id))
    selected = ranked[:count]
    out_dir.mkdir(parents=True, exist_ok=True)
    tasks_out = out_dir / "tasks"
    tasks_out.mkdir(parents=True, exist_ok=True)
    for task_id in selected:
        source = root / "v2" / "tasks" / task_id
        shutil.copytree(source, tasks_out / task_id, dirs_exist_ok=True)
    (out_dir / "task_ids.txt").write_text("\n".join(selected) + "\n", encoding="utf-8")
    (out_dir / "unpinned_tags.txt").write_text(
        "\n".join(verification["image_tags"][task_id] for task_id in selected) + "\n",
        encoding="utf-8",
    )
    rows = [
        {
            "task_id": task_id,
            "selection_sha256": selection_key(run_id, task_id),
            "image_tag": verification["image_tags"][task_id],
        }
        for task_id in selected
    ]
    selection = {
        "schema": SCHEMA,
        "release_tag": RELEASE_TAG,
        "release_sha": RELEASE_SHA,
        "release_asset_digests": RELEASE_ASSET_DIGESTS,
        "sha256sums_sha256": verification["checksums"].get("v2/SHA256SUMS"),
        "hard51_ids_sha256": verification["checksums"].get("v2/hard51_ids.txt"),
        "patch_replay_sha256": verification["checksums"].get("v2/tooling/patch_replay.py"),
        "run_id": run_id,
        "selection_seed": "sha256(run_id:task_id)",
        "selected_task_count": len(selected),
        "hard51_count": verification["hard51_count"],
        "task_count": verification["task_count"],
        "excluded_seen_task_ids": [],
        "checks": verification["checks"],
        "tasks": rows,
        "source_reads_instruction_content": False,
        "source_reads_solution_or_test_content": False,
        "task_specific_answers_in_repo": False,
        "raw_benchmark_tasks_saved_in_workspace": False,
        "model_calls": 0,
        "runtime_network_calls": 0,
        "hidden_test_reading": False,
        "borrowed_outputs": False,
        "note": "Freshness is a run-id-seeded choice from the pinned HARD-51 ID list, not a claim that task content was unseen or that a capability was acquired.",
    }
    (out_dir / "selection.json").write_text(
        json.dumps(selection, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return selection


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--swe-root", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--count", type=int, default=3)
    args = parser.parse_args()
    selection = build_selection(
        pathlib.Path(args.swe_root),
        pathlib.Path(args.out_dir),
        str(args.run_id),
        int(args.count),
    )
    print(
        "SWE_PRO_V2_HARD51_SELECTION_PASS",
        json.dumps(
            {
                "selected_task_count": selection["selected_task_count"],
                "task_ids": [row["task_id"] for row in selection["tasks"]],
                "release_sha": selection["release_sha"],
                "selection_seed": selection["selection_seed"],
            },
            sort_keys=True,
        ),
    )


if __name__ == "__main__":
    main()
