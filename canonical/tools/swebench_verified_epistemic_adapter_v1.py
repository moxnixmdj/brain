"""Generate SWE-bench predictions.jsonl from Brain's open_model().solve().

This is a *producer* only. It never grades anything and never edits a score.
The official SWE-bench Docker harness grades the emitted patch strings.

What it deliberately does not do:
  * no network access, no `git clone`, no package installation;
  * no reading of the gold patch, test_patch or FAIL_TO_PASS from the task row;
  * no claim that a patch resolves an instance (only the harness can say that);
  * no special meaning invented for `mode="EPISTEMIC"`. The engine only
    special-cases RECALL and SOLVE_OR_LEARN; any other mode falls through to
    its ordinary routing. The requested string is forwarded verbatim and
    recorded in the sidecar report.

Usage (on a machine with the pre-cloned SWE-bench repos and the harness):

    python3 -m canonical.tools.swebench_verified_epistemic_adapter_v1 \\
        --dataset-path verified.jsonl \\
        --repos-root /data/swe_repos \\
        --output predictions.jsonl --report adapter_report.jsonl \\
        --limit 50 --run-id epistemic_smoke_50

    python -m swebench.harness.run_evaluation \\
        --dataset_name SWE-bench/SWE-bench_Verified \\
        --predictions_path predictions.jsonl \\
        --max_workers 6 --run_id epistemic_smoke_50
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from canonical.tools.swebench_issue_localizer_v1 import localize_issue

SCHEMA = "PROJECT_BRAIN_SWEBENCH_VERIFIED_EPISTEMIC_ADAPTER_V1"
DEFAULT_MODEL_NAME = "b81b2217-epistemic-v1"
DEFAULT_MODE = "EPISTEMIC"
MAX_PATCH_CHARS = 2_000_000
INSTANCE_RE = re.compile(r"^(?P<repo>[A-Za-z0-9_.-]+__[A-Za-z0-9_.-]+)-(?P<number>[0-9]+)$")
DIFF_HEADER_RE = re.compile(r"^diff --git ", re.MULTILINE)

SolveFn = Callable[..., dict[str, Any]]


class AdapterError(RuntimeError):
    """Fail-closed condition; the instance gets an empty patch and a reason."""


def mode_note(mode: str) -> str:
    """State exactly what the engine does with the requested mode string."""
    requested = str(mode or "AUTO").strip().upper()
    if requested in {"RECALL", "SOLVE_OR_LEARN"}:
        return "MODE_SPECIAL_CASED_BY_ENGINE:" + requested
    return (
        "MODE_NOT_SPECIAL_CASED_BY_ENGINE:"
        + requested
        + " (open_model().solve() only special-cases RECALL and SOLVE_OR_LEARN;"
        " all other strings use ordinary routing)"
    )


def repo_key(instance_id: str) -> str:
    match = INSTANCE_RE.match(str(instance_id or "").strip())
    if not match:
        raise AdapterError("INSTANCE_ID_INVALID:" + str(instance_id)[:120])
    return match.group("repo")


def load_instances(
    *,
    dataset_path: str | os.PathLike[str] | None = None,
    dataset_name: str | None = None,
    split: str = "test",
) -> list[dict[str, Any]]:
    """Read task rows from a local JSON/JSONL file or a Hugging Face dataset.

    Only the fields a solver is entitled to see are copied forward; gold and
    test fields are never passed to the model by this adapter.
    """
    if dataset_path and dataset_name:
        raise AdapterError("DATASET_SOURCE_AMBIGUOUS")
    if dataset_path:
        path = Path(dataset_path)
        if not path.is_file():
            raise AdapterError("DATASET_PATH_MISSING:" + str(path))
        raw = path.read_text(encoding="utf-8", errors="replace")
        stripped = raw.lstrip()
        if stripped.startswith("["):
            rows = json.loads(raw)
        elif stripped.startswith("{") and "\n" not in stripped.strip():
            rows = [json.loads(raw)]
        else:
            rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    elif dataset_name:
        try:
            from datasets import load_dataset  # type: ignore[import-not-found]
        except ImportError as exc:
            raise AdapterError("DATASETS_PACKAGE_MISSING") from exc
        rows = load_dataset(dataset_name, split=split)
    else:
        raise AdapterError("DATASET_SOURCE_REQUIRED")
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            raise AdapterError("DATASET_ROW_NOT_OBJECT")
        iid = str(row.get("instance_id") or "").strip()
        if not iid or iid in seen:
            raise AdapterError("DATASET_INSTANCE_ID_INVALID_OR_DUPLICATE:" + iid[:120])
        seen.add(iid)
        out.append(
            {
                "instance_id": iid,
                "problem_statement": str(row.get("problem_statement") or ""),
                "repo": str(row.get("repo") or ""),
                "base_commit": str(row.get("base_commit") or ""),
                "hints_text": str(row.get("hints_text") or ""),
            }
        )
    return out


def filter_instances(
    instances: Iterable[dict[str, Any]],
    *,
    limit: int | None = None,
    instance_ids: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    rows = list(instances)
    if instance_ids:
        wanted = set(instance_ids)
        rows = [row for row in rows if row["instance_id"] in wanted]
        missing = wanted - {row["instance_id"] for row in rows}
        if missing:
            raise AdapterError("INSTANCE_IDS_NOT_IN_DATASET:" + ",".join(sorted(missing)[:8]))
    if limit is not None:
        if limit < 0:
            raise AdapterError("LIMIT_INVALID")
        rows = rows[:limit]
    return rows


def render_goal(instance: Mapping[str, Any], *, include_hints: bool = False) -> str:
    """Build the only task text the solver is allowed to see.

    The gold patch, test_patch, FAIL_TO_PASS and PASS_TO_PASS fields are
    intentionally absent from the adapter's in-memory row.
    """
    iid = str(instance.get("instance_id") or "").strip()
    statement = str(instance.get("problem_statement") or "").strip()
    if not statement:
        raise AdapterError("PROBLEM_STATEMENT_EMPTY:" + iid)
    repo = str(instance.get("repo") or "").strip()
    base = str(instance.get("base_commit") or "").strip()
    parts = [
        "Fix the following real software issue in the supplied repository.",
        "Work only inside the checked-out repository passed as source_root/worktree_path.",
        "Return a source-level fix; do not edit tests and do not fetch anything from the network.",
        f"Instance: {iid}",
        (f"Repository: {repo}" if repo else ""),
        (f"Base commit: {base}" if base else ""),
        "",
        "Issue:",
        statement,
    ]
    if include_hints and str(instance.get("hints_text") or "").strip():
        parts += ["", "Additional issue discussion:", str(instance["hints_text"]).strip()]
    return "\n".join(part for part in parts if part is not None)


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
        check=False,
    )
    if check and proc.returncode != 0:
        raise AdapterError("GIT_FAILED:" + " ".join(args[:3]) + ":" + proc.stderr.strip()[-300:])
    return proc


def make_worktree(repos_root: Path, instance: Mapping[str, Any], workdir: Path) -> Path:
    """Create a detached local worktree at the instance's base commit."""
    iid = str(instance.get("instance_id") or "").strip()
    base = str(instance.get("base_commit") or "").strip()
    if not base or not re.fullmatch(r"[0-9a-fA-F]{7,40}", base):
        raise AdapterError("BASE_COMMIT_INVALID:" + iid)
    key = repo_key(iid)
    source = repos_root / key
    if not (source / ".git").exists() and not (source.is_file() and source.name == ".git"):
        raise AdapterError("REPO_NOT_PRECLONED:" + key)
    if _git(source, "cat-file", "-e", base + "^{commit}", check=False).returncode != 0:
        raise AdapterError("BASE_COMMIT_NOT_IN_LOCAL_REPO:" + iid + ":" + base)
    target = workdir / (iid.replace("/", "_") + "__worktree")
    if target.exists():
        raise AdapterError("WORKTREE_PATH_ALREADY_EXISTS:" + str(target))
    target.parent.mkdir(parents=True, exist_ok=True)
    _git(source, "worktree", "add", "--detach", str(target), base)
    return target


def remove_worktree(repos_root: Path, instance: Mapping[str, Any], worktree: Path, workdir: Path) -> None:
    """Remove only worktrees this adapter created underneath its own workdir."""
    try:
        resolved = worktree.resolve()
        root = workdir.resolve()
        if root not in resolved.parents or resolved == root:
            return
        key = repo_key(str(instance.get("instance_id") or ""))
        source = repos_root / key
        if source.is_dir():
            _git(source, "worktree", "remove", "--force", str(worktree), check=False)
        if worktree.exists():
            shutil.rmtree(worktree, ignore_errors=True)
    except (OSError, AdapterError):
        pass


def _diff_from_worktree(worktree: Path, *, include_untracked: bool) -> str:
    if include_untracked:
        untracked = _git(worktree, "ls-files", "--others", "--exclude-standard").stdout.splitlines()
        files = [line for line in untracked if line and "\x00" not in line]
        if files:
            _git(worktree, "add", "-N", "--", *files)
    diff = _git(worktree, "diff", "--binary", "--no-ext-diff", "HEAD").stdout
    return diff


def _looks_like_unified_diff(text: str) -> bool:
    return (
        isinstance(text, str)
        and 0 < len(text) <= MAX_PATCH_CHARS
        and bool(DIFF_HEADER_RE.search(text))
        and "--- " in text
        and "+++ " in text
        and "@@" in text
    )


def _patch_check(worktree: Path, patch: str) -> str:
    """Return the first git check that succeeds: forward or already-applied."""
    with tempfile.NamedTemporaryFile("w", suffix=".patch", delete=False, encoding="utf-8") as handle:
        handle.write(patch)
        name = handle.name
    try:
        for flag, label in (([], "APPLIES_CLEANLY"), (["--reverse"], "ALREADY_APPLIED")):
            proc = _git(worktree, "apply", "--check", *flag, name, check=False)
            if proc.returncode == 0:
                return label
        return "GIT_APPLY_CHECK_FAILED"
    finally:
        os.unlink(name)


def extract_patch(
    result: Mapping[str, Any] | None,
    worktree: Path | None,
    *,
    include_untracked: bool = False,
) -> tuple[str, str, str]:
    """Return (patch, source, reason). Never invents a patch."""
    candidate = ""
    source = "NONE"
    if isinstance(result, Mapping):
        for key in ("model_patch", "patch", "unified_diff", "git_diff"):
            value = result.get(key)
            if isinstance(value, str) and value.strip():
                candidate = value
                source = "MODEL_RESULT:" + key
                break
    if not candidate and worktree is not None:
        try:
            candidate = _diff_from_worktree(worktree, include_untracked=include_untracked)
        except AdapterError as exc:
            return "", "NONE", str(exc)
        source = "WORKTREE_DIFF"
    if not candidate.strip():
        return "", source, "NO_SOURCE_CHANGE"
    if not _looks_like_unified_diff(candidate):
        return "", source, "NOT_A_UNIFIED_DIFF"
    if worktree is not None:
        check = _patch_check(worktree, candidate)
        if check == "GIT_APPLY_CHECK_FAILED":
            return "", source, check
        return candidate, source, check
    return candidate, source, "UNCHECKED_NO_WORKTREE"


def prediction_row(instance_id: str, patch: str, model_name: str) -> dict[str, str]:
    """Official SWE-bench prediction shape: three string fields, one per line."""
    return {
        "instance_id": instance_id,
        "model_name_or_path": model_name,
        "model_patch": patch,
    }


def solve_one(
    instance: Mapping[str, Any],
    *,
    solve_fn: SolveFn,
    repos_root: Path,
    workdir: Path,
    model_name: str,
    mode: str,
    include_hints: bool = False,
    include_untracked: bool = False,
    keep_worktrees: bool = False,
    context_paths: Sequence[str] | None = None,
) -> tuple[dict[str, str], dict[str, Any]]:
    """Produce one prediction row and one fail-closed trace row."""
    iid = str(instance.get("instance_id") or "").strip()
    goal = ""
    trace: dict[str, Any] = {
        "schema": SCHEMA,
        "instance_id": iid,
        "model_name_or_path": model_name,
        "mode_requested": mode,
        "mode_semantics": mode_note(mode),
        "model_status": None,
        "model_reason": None,
        "patch_source": "NONE",
        "patch_check": "NOT_ATTEMPTED",
        "patch_chars": 0,
        "outcome": "NO_SOURCE_CHANGE",
    }
    worktree: Path | None = None
    try:
        goal = render_goal(instance, include_hints=include_hints)
        worktree = make_worktree(repos_root, instance, workdir)
        # Advisory only: do not put these values into the solver inputs or alter
        # routing/admission. Existing patch checks do not verify effect receipts.
        trace["issue_localization"] = localize_issue(
            str(instance.get("problem_statement") or ""), worktree
        )
        task_path = workdir / (iid.replace("/", "_") + "__task.txt")
        task_path.write_text(goal + "\n", encoding="utf-8")
        report_path = workdir / (iid.replace("/", "_") + "__model_result.json")
        inputs: dict[str, Any] = {
            "instance_id": iid,
            "source_root": str(worktree),
            "worktree_path": str(worktree),
            "repo": str(instance.get("repo") or ""),
            "base_commit": str(instance.get("base_commit") or ""),
            "task_path": str(task_path),
            "problem_statement_path": str(task_path),
            "request_spec": goal,
            "goal": goal,
            "output_path": str(report_path),
            "diff_path": str(workdir / (iid.replace("/", "_") + "__model.patch")),
            "python_executable": sys.executable,
            "synthesize_regression_test": False,
            "test_paths": [],
            "test_argv": [],
            "timeout_s": 600,
        }
        result = solve_fn(
            goal,
            inputs=inputs,
            mode=mode,
            instance_id=iid,
            context_paths=list(context_paths or [str(task_path)]),
            cwd=str(worktree),
        )
        if not isinstance(result, Mapping):
            raise AdapterError("SOLVE_RESULT_NOT_MAPPING")
        trace["model_status"] = str(result.get("status") or "")
        trace["model_reason"] = str(result.get("reason") or "")
        trace["model_pass"] = result.get("pass") is True
        trace["model_capability_id"] = str(result.get("capability_id") or "")
        patch, source, check = extract_patch(
            result, worktree, include_untracked=include_untracked
        )
        trace.update(
            {
                "patch_source": source,
                "patch_check": check,
                "patch_chars": len(patch),
                "outcome": "PATCH_EMITTED" if patch else check or "NO_SOURCE_CHANGE",
            }
        )
        return prediction_row(iid, patch, model_name), trace
    except Exception as exc:  # fail closed; keep the instance in predictions.jsonl
        trace["outcome"] = "ADAPTER_EXCEPTION:" + type(exc).__name__ + ":" + str(exc)[:300]
        return prediction_row(iid, "", model_name), trace
    finally:
        if worktree is not None and not keep_worktrees:
            remove_worktree(repos_root, instance, worktree, workdir)


def generate_predictions(
    instances: Iterable[Mapping[str, Any]],
    *,
    solve_fn: SolveFn,
    repos_root: Path,
    workdir: Path,
    output_path: Path,
    report_path: Path,
    model_name: str = DEFAULT_MODEL_NAME,
    mode: str = DEFAULT_MODE,
    include_hints: bool = False,
    include_untracked: bool = False,
    keep_worktrees: bool = False,
    skip_existing: bool = False,
    context_paths: Sequence[str] | None = None,
) -> dict[str, Any]:
    workdir.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, dict[str, Any]] = {}
    if skip_existing and output_path.exists():
        for line in output_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            existing[str(row.get("instance_id"))] = row
    counts: dict[str, int] = {"total": 0, "skipped": 0, "patched": 0, "empty": 0}
    with output_path.open("w", encoding="utf-8") as predictions, report_path.open(
        "w", encoding="utf-8"
    ) as report:
        for instance in instances:
            counts["total"] += 1
            iid = str(instance.get("instance_id") or "")
            if iid in existing:
                row = existing[iid]
                predictions.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
                counts["skipped"] += 1
                continue
            row, trace = solve_one(
                instance,
                solve_fn=solve_fn,
                repos_root=repos_root,
                workdir=workdir,
                model_name=model_name,
                mode=mode,
                include_hints=include_hints,
                include_untracked=include_untracked,
                keep_worktrees=keep_worktrees,
                context_paths=context_paths,
            )
            predictions.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            predictions.flush()
            report.write(json.dumps(trace, ensure_ascii=False, sort_keys=True) + "\n")
            report.flush()
            counts["patched" if row["model_patch"] else "empty"] += 1
    return {
        "schema": SCHEMA,
        "predictions_path": str(output_path),
        "report_path": str(report_path),
        "mode_requested": mode,
        "mode_semantics": mode_note(mode),
        "counts": counts,
        "claim": "PREDICTIONS_GENERATED_ONLY__RESOLUTION_SCORE_REQUIRES_OFFICIAL_HARNESS",
    }


def _engine_solver() -> SolveFn:
    from canonical.runtime.brain_unified_model_v1 import open_model

    model = open_model()

    def solve(goal: str, **kwargs: Any) -> dict[str, Any]:
        return model.solve(goal, **kwargs)

    return solve


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--dataset-path", help="local JSON or JSONL task rows")
    source.add_argument("--dataset-name", help="Hugging Face dataset, e.g. SWE-bench/SWE-bench_Verified")
    parser.add_argument("--split", default="test")
    parser.add_argument("--repos-root", required=True, type=Path, help="directory of pre-cloned <owner>__<repo> repos")
    parser.add_argument("--output", required=True, type=Path, help="predictions.jsonl")
    parser.add_argument("--report", required=True, type=Path, help="fail-closed sidecar trace")
    parser.add_argument("--workdir", type=Path, default=Path(tempfile.mkdtemp(prefix="brain_swe_")))
    parser.add_argument("--model-name", default=DEFAULT_MODEL_NAME)
    parser.add_argument("--mode", default=DEFAULT_MODE)
    parser.add_argument("--limit", type=int, default=None, help="smoke-test size, e.g. 50")
    parser.add_argument("--instance-ids", nargs="*", default=None)
    parser.add_argument("--include-hints", action="store_true")
    parser.add_argument("--include-untracked", action="store_true")
    parser.add_argument("--keep-worktrees", action="store_true")
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--run-id", default=None, help="recorded only; harness run_id is separate")
    args = parser.parse_args(argv)

    try:
        instances = load_instances(
            dataset_path=args.dataset_path, dataset_name=args.dataset_name, split=args.split
        )
        instances = filter_instances(instances, limit=args.limit, instance_ids=args.instance_ids)
        summary = generate_predictions(
            instances,
            solve_fn=_engine_solver(),
            repos_root=args.repos_root.resolve(),
            workdir=args.workdir.resolve(),
            output_path=args.output.resolve(),
            report_path=args.report.resolve(),
            model_name=args.model_name,
            mode=args.mode,
            include_hints=args.include_hints,
            include_untracked=args.include_untracked,
            keep_worktrees=args.keep_worktrees,
            skip_existing=args.skip_existing,
        )
        summary["run_id"] = args.run_id
        print(json.dumps(summary, sort_keys=True))
        return 0
    except AdapterError as exc:
        print(json.dumps({"error": str(exc), "schema": SCHEMA}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
