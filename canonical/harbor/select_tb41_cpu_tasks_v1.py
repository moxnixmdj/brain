#!/usr/bin/env python3
"""Select a fresh, CPU-only Terminal-Bench 4.1 subset without task answers.

This runner-side selector reads only pinned release metadata, ``dataset.toml``
and ``task.toml`` resource fields. It never reads instruction bodies, hidden
tests, solutions or verifier outputs. Selection is seeded by the GitHub run id,
excludes GPU tasks, excludes task names whose instruction text was already seen
during build-time research, and keeps only tasks with one pinned environment
image and one pinned verifier image and no compose sidecars.

It copies the selected task directories into a disposable runner directory and
rewrites only ``task.toml`` to use digest-pinned prebuilt image references. No
benchmark task, test, solution, answer or trajectory is written into this Git
repository.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import tomllib
from typing import Any

SCHEMA = "BRAIN_TB41_CPU_FRESH_SELECTION_V1"
EXPECTED_SOURCE_SHA = "4070d6cef56a7d20cb5dc98d5e10ada88a6b9440"
EXPECTED_RELEASE_TAG = "v4.1.0"
EXPECTED_TASK_COUNT = 66
EXPECTED_IMAGE_COUNT = 157
EXPECTED_MANIFEST_SHA256 = (
    "49a2b9ce70dbbb957f3eaf74c737ccb8c6d68b3167d4ccfb5c58762a9726b289"
)

# Names only. These instruction texts were fetched as build-time research in a
# previous pass; excluding them avoids presenting a previously seen prompt as
# fresh. No instruction text, answer, test or solution is stored here.
EXCLUDED_SEEN_INSTRUCTION_TASKS = frozenset(
    {
        "math-eval-grader",
        "html-js-filter",
        "bun-sourcemap-leak",
        "batched-eval-parity",
        "layout-config-recreation",
        "data-anonymization",
    }
)


def load_manifest(path: pathlib.Path) -> dict[str, Any]:
    data = path.read_bytes()
    observed = hashlib.sha256(data).hexdigest()
    if observed != EXPECTED_MANIFEST_SHA256:
        raise SystemExit(
            "PREBUILT_MANIFEST_SHA256_MISMATCH "
            + json.dumps({"expected": EXPECTED_MANIFEST_SHA256, "observed": observed})
        )
    manifest = json.loads(data)
    checks = {
        "schema_version": manifest.get("schema_version") == 1,
        "release_tag": manifest.get("release_tag") == EXPECTED_RELEASE_TAG,
        "task_count": manifest.get("task_count") == EXPECTED_TASK_COUNT,
        "image_count": manifest.get("image_count") == EXPECTED_IMAGE_COUNT,
        "tasks_present": len(manifest.get("tasks") or []) == EXPECTED_TASK_COUNT,
    }
    for row in manifest.get("tasks") or []:
        if row.get("source_sha") != EXPECTED_SOURCE_SHA:
            checks["source_sha"] = False
            break
    failed = sorted(key for key, value in checks.items() if not value)
    if failed:
        raise SystemExit("PREBUILT_MANIFEST_SCHEMA_FAIL " + repr(failed))
    return manifest


def _manifest_task_index(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in manifest.get("tasks") or []:
        name = str(row.get("task") or "")
        if not name:
            continue
        images = row.get("images") or []
        env = [i for i in images if i.get("kind") == "environment"]
        verifier = [i for i in images if i.get("kind") == "verifier"]
        other = [i for i in images if i.get("kind") not in {"environment", "verifier"}]
        if len(env) != 1 or len(verifier) != 1 or other:
            continue
        if any(i.get("compose_services") for i in images):
            continue
        if any(i.get("status") not in {"built", "cached"} for i in images):
            continue
        refs = [env[0].get("pinned_ref"), verifier[0].get("pinned_ref")]
        if not all(isinstance(ref, str) and ref.startswith("harborframework/terminal-bench:") and "@sha256:" in ref for ref in refs):
            continue
        out[name] = {
            "environment_image": env[0]["pinned_ref"],
            "environment_digest": env[0].get("digest"),
            "verifier_image": verifier[0]["pinned_ref"],
            "verifier_digest": verifier[0].get("digest"),
        }
    return out


def _cpu_task_names(tb_root: pathlib.Path) -> tuple[list[str], dict[str, str]]:
    dataset_path = tb_root / "tasks" / "dataset.toml"
    dataset = tomllib.loads(dataset_path.read_text(encoding="utf-8"))
    refs = dataset.get("tasks") or []
    names: list[str] = []
    checksums: dict[str, str] = {}
    for ref in refs:
        full = str(ref.get("name") or "")
        short = full.split("/", 1)[1] if "/" in full else full
        checksums[short] = str(ref.get("digest") or "")
        task_path = tb_root / "tasks" / short / "task.toml"
        if not task_path.is_file():
            continue
        cfg = tomllib.loads(task_path.read_text(encoding="utf-8"))
        env = cfg.get("environment") or {}
        if env.get("gpus") or env.get("gpu_types"):
            continue
        if short in EXCLUDED_SEEN_INSTRUCTION_TASKS:
            continue
        names.append(short)
    return sorted(names), checksums


def select_tasks(
    tb_root: pathlib.Path,
    manifest: dict[str, Any],
    run_id: str,
    count: int = 3,
    *,
    strict_cpu_count: bool = True,
) -> dict[str, Any]:
    if count < 1:
        raise SystemExit("TASK_COUNT_MUST_BE_POSITIVE")
    cpu_names, checksums = _cpu_task_names(tb_root)
    if strict_cpu_count and len(cpu_names) < 63 - len(EXCLUDED_SEEN_INSTRUCTION_TASKS):
        raise SystemExit(
            "CPU_TASK_COUNT_UNEXPECTED "
            + json.dumps({"observed": len(cpu_names), "expected_at_least": 63 - len(EXCLUDED_SEEN_INSTRUCTION_TASKS)})
        )
    index = _manifest_task_index(manifest)
    eligible = [name for name in cpu_names if name in index]
    if len(eligible) < count:
        raise SystemExit(
            "INSUFFICIENT_SAFE_CPU_TASKS "
            + json.dumps({"eligible": len(eligible), "requested": count}, sort_keys=True)
        )
    seeded = sorted(
        eligible,
        key=lambda name: (hashlib.sha256(f"{run_id}:{name}".encode("utf-8")).hexdigest(), name),
    )
    chosen = seeded[:count]
    tasks = []
    for name in chosen:
        row = dict(index[name])
        row.update(
            {
                "name": name,
                "task_checksum": checksums.get(name, ""),
                "selection_hash": hashlib.sha256(f"{run_id}:{name}".encode("utf-8")).hexdigest(),
            }
        )
        tasks.append(row)
    return {
        "schema": SCHEMA,
        "run_id": run_id,
        "selection_seed": "sha256(run_id:task_name)",
        "source_sha": EXPECTED_SOURCE_SHA,
        "release_tag": EXPECTED_RELEASE_TAG,
        "cpu_candidates": len(cpu_names),
        "eligible_pinned_no_sidecar_tasks": len(eligible),
        "excluded_seen_instruction_task_names": sorted(EXCLUDED_SEEN_INSTRUCTION_TASKS),
        "selected_task_count": len(tasks),
        "tasks": tasks,
    }


def _pin_task_toml(path: pathlib.Path, environment_image: str, verifier_image: str) -> None:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    out: list[str] = []
    inserted_environment = False
    inserted_verifier = False
    has_verifier_environment = False
    for line in lines:
        stripped = line.strip()
        out.append(line)
        if stripped == "[environment]" and not inserted_environment:
            out.append("docker_image = " + json.dumps(environment_image))
            inserted_environment = True
        elif stripped == "[verifier.environment]" and not inserted_verifier:
            out.append("docker_image = " + json.dumps(verifier_image))
            inserted_verifier = True
            has_verifier_environment = True
    if not inserted_environment:
        raise SystemExit("TASK_TOML_ENVIRONMENT_SECTION_MISSING " + str(path))
    if not has_verifier_environment:
        out.extend(["", "[verifier.environment]", "docker_image = " + json.dumps(verifier_image)])
    new_text = "\n".join(out) + "\n"
    parsed = tomllib.loads(new_text)
    env = parsed.get("environment") or {}
    verifier_env = ((parsed.get("verifier") or {}).get("environment") or {})
    if env.get("docker_image") != environment_image or verifier_env.get("docker_image") != verifier_image:
        raise SystemExit("TASK_TOML_IMAGE_PINNING_FAILED " + str(path))
    path.write_text(new_text, encoding="utf-8")


def prepare_dataset(tb_root: pathlib.Path, out_dir: pathlib.Path, selection: dict[str, Any]) -> None:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    for task in selection["tasks"]:
        name = task["name"]
        source = tb_root / "tasks" / name
        if not source.is_dir():
            raise SystemExit("SOURCE_TASK_DIR_MISSING " + str(source))
        target = out_dir / name
        shutil.copytree(source, target, symlinks=True)
        _pin_task_toml(
            target / "task.toml",
            task["environment_image"],
            task["verifier_image"],
        )
    (out_dir / "selection.json").write_text(
        json.dumps(selection, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    refs = []
    for task in selection["tasks"]:
        refs.extend([task["environment_image"], task["verifier_image"]])
    (out_dir / "pinned_refs.txt").write_text("\n".join(refs) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tb-root", required=True, type=pathlib.Path)
    parser.add_argument("--manifest", required=True, type=pathlib.Path)
    parser.add_argument("--out-dir", required=True, type=pathlib.Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--count", type=int, default=3)
    args = parser.parse_args()
    manifest = load_manifest(args.manifest)
    selection = select_tasks(args.tb_root, manifest, args.run_id, args.count)
    prepare_dataset(args.tb_root, args.out_dir, selection)
    print(
        "TB41_CPU_SELECTION_PASS "
        + json.dumps(
            {
                "selected": [row["name"] for row in selection["tasks"]],
                "cpu_candidates": selection["cpu_candidates"],
                "eligible": selection["eligible_pinned_no_sidecar_tasks"],
                "out_dir": str(args.out_dir),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
