"""Atomic frontier transaction guard for Project Brain.

This guard prevents wall-clock loss from treating every advancing main SHA as
semantic staleness. A transaction remains reusable across a moving main when:
1) its authority epoch is unchanged, and
2) intervening main changes do not overlap its declared mutation/dependency
   paths.

It never grants execution, promotion, acceptance, or terminal authority.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any, Sequence

from canonical.runtime.authority_epoch_guard_v1 import epoch_for_ref

ROOT = Path(__file__).resolve().parents[2]


class AtomicFrontierTransactionError(RuntimeError):
    pass


def _s(value: Any) -> str:
    return str(value or "").strip()


def _normalize_path(value: str) -> str:
    value = _s(value).replace("\\", "/")
    while value.startswith("./"):
        value = value[2:]
    return value.rstrip("/")


def paths_overlap(a: str, b: str) -> bool:
    """Return True when repository paths are equal or ancestor/descendant."""
    a = _normalize_path(a)
    b = _normalize_path(b)
    if not a or not b:
        return False
    return a == b or a.startswith(b + "/") or b.startswith(a + "/")


def classify_snapshot(
    *,
    base_sha: str,
    current_sha: str,
    expected_authority_epoch: str,
    base_authority_epoch: str,
    current_authority_epoch: str,
    intervening_paths: Sequence[str],
    mutation_paths: Sequence[str],
    dependency_paths: Sequence[str] = (),
) -> dict[str, Any]:
    """Pure decision kernel used by the CLI and unit tests."""
    errors: list[str] = []
    base_sha = _s(base_sha)
    current_sha = _s(current_sha)
    expected_authority_epoch = _s(expected_authority_epoch)
    base_authority_epoch = _s(base_authority_epoch)
    current_authority_epoch = _s(current_authority_epoch)

    if not all((base_sha, current_sha, expected_authority_epoch, base_authority_epoch, current_authority_epoch)):
        errors.append("MISSING_TRANSACTION_BINDING")

    if expected_authority_epoch != base_authority_epoch:
        errors.append("START_EPOCH_BINDING_MISMATCH")

    if current_authority_epoch != expected_authority_epoch:
        errors.append("AUTHORITY_EPOCH_CHANGED")

    declared = tuple(
        sorted(
            {
                _normalize_path(p)
                for p in [*mutation_paths, *dependency_paths]
                if _normalize_path(p)
            }
        )
    )
    changed = tuple(sorted({_normalize_path(p) for p in intervening_paths if _normalize_path(p)}))
    conflicts = tuple(
        sorted(
            c
            for c in changed
            if any(paths_overlap(c, d) for d in declared)
        )
    )
    if conflicts:
        errors.append("INTERVENING_PATH_CONFLICT")

    exact = base_sha == current_sha
    passed = not errors
    if passed and exact:
        status = "PASS__EXACT_CURRENT"
        integration_mode = "LAND_ATOMICALLY_ON_EXACT_CURRENT_BASE"
    elif passed:
        status = "PASS__SEMANTICALLY_CURRENT__NONCONFLICTING_MAIN_ADVANCE"
        integration_mode = "REBIND_ON_CURRENT_MAIN__PRESERVE_UNCHANGED_VERIFICATION"
    else:
        status = "FAIL_CLOSED__TRANSACTION_STALE_OR_CONFLICTING"
        integration_mode = "RECOMPUTE_ONLY_INVALIDATED_DELTA"

    return {
        "schema": "PROJECT_BRAIN_ATOMIC_FRONTIER_TRANSACTION_GUARD_V1",
        "pass": passed,
        "status": status,
        "base_sha": base_sha,
        "current_sha": current_sha,
        "main_advanced": not exact,
        "expected_authority_epoch": expected_authority_epoch,
        "base_authority_epoch": base_authority_epoch,
        "current_authority_epoch": current_authority_epoch,
        "declared_paths": list(declared),
        "intervening_paths": list(changed),
        "conflicting_paths": list(conflicts),
        "integration_mode": integration_mode,
        "verification_reuse_allowed": bool(passed and not exact),
        "execution_authority": False,
        "promotion_authority": False,
        "acceptance_credit_delta": 0,
        "terminal_credit_delta": 0,
        "errors": errors,
        "rule": (
            "MAIN_SHA_DRIFT_ALONE_DOES_NOT_INVALIDATE_VERIFIED_WORK__"
            "AUTHORITY_EPOCH_OR_DECLARED_PATH_CONFLICT_DOES__"
            "REVERIFY_ONLY_INVALIDATED_DELTA"
        ),
    }


def _git(root: Path, *args: str) -> str:
    p = subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if p.returncode != 0:
        raise AtomicFrontierTransactionError(
            "GIT_FAILED:" + " ".join(args) + ":" + p.stderr.strip()
        )
    return p.stdout.strip()


def _ref_sha(root: Path, ref: str) -> str:
    out = _git(root, "rev-parse", ref)
    if len(out) != 40:
        raise AtomicFrontierTransactionError("INVALID_REF_SHA:" + ref + ":" + out)
    return out


def _is_ancestor(root: Path, base_ref: str, current_ref: str) -> bool:
    p = subprocess.run(
        ["git", "merge-base", "--is-ancestor", base_ref, current_ref],
        cwd=root,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if p.returncode == 0:
        return True
    if p.returncode == 1:
        return False
    raise AtomicFrontierTransactionError(
        "GIT_FAILED:merge-base --is-ancestor:" + p.stderr.strip()
    )


def _changed_paths(root: Path, base_ref: str, current_ref: str) -> tuple[str, ...]:
    out = _git(root, "diff", "--name-only", f"{base_ref}..{current_ref}")
    return tuple(x for x in out.splitlines() if _s(x))


def evaluate_transaction(
    *,
    root: Path,
    base_ref: str,
    current_ref: str,
    expected_authority_epoch: str,
    mutation_paths: Sequence[str],
    dependency_paths: Sequence[str] = (),
) -> dict[str, Any]:
    root = root.resolve()
    base_sha = _ref_sha(root, base_ref)
    current_sha = _ref_sha(root, current_ref)
    if not _is_ancestor(root, base_ref, current_ref):
        return {
            "schema": "PROJECT_BRAIN_ATOMIC_FRONTIER_TRANSACTION_GUARD_V1",
            "pass": False,
            "status": "FAIL_CLOSED__BASE_NOT_ANCESTOR_OF_CURRENT",
            "base_sha": base_sha,
            "current_sha": current_sha,
            "integration_mode": "REBASE_OR_REBUILD_FROM_CURRENT_MAIN",
            "verification_reuse_allowed": False,
            "execution_authority": False,
            "promotion_authority": False,
            "acceptance_credit_delta": 0,
            "terminal_credit_delta": 0,
            "errors": ["BASE_NOT_ANCESTOR_OF_CURRENT"],
        }

    base_epoch = epoch_for_ref(base_ref)["epoch_sha256"]
    current_epoch = epoch_for_ref(current_ref)["epoch_sha256"]
    return classify_snapshot(
        base_sha=base_sha,
        current_sha=current_sha,
        expected_authority_epoch=expected_authority_epoch,
        base_authority_epoch=base_epoch,
        current_authority_epoch=current_epoch,
        intervening_paths=_changed_paths(root, base_ref, current_ref),
        mutation_paths=mutation_paths,
        dependency_paths=dependency_paths,
    )


def start_transaction(
    *,
    root: Path,
    base_ref: str,
    mutation_paths: Sequence[str],
    dependency_paths: Sequence[str] = (),
) -> dict[str, Any]:
    root = root.resolve()
    epoch = epoch_for_ref(base_ref)
    return {
        "schema": "PROJECT_BRAIN_ATOMIC_FRONTIER_TRANSACTION_START_V1",
        "status": "BOUND",
        "base_ref": base_ref,
        "base_sha": _ref_sha(root, base_ref),
        "authority_epoch_sha256": epoch["epoch_sha256"],
        "authority_epoch_components": epoch["components"],
        "mutation_paths": sorted({_normalize_path(p) for p in mutation_paths if _normalize_path(p)}),
        "dependency_paths": sorted({_normalize_path(p) for p in dependency_paths if _normalize_path(p)}),
        "execution_authority": False,
        "promotion_authority": False,
        "rule": "RECHECK_THIS_EPOCH_AND_DECLARED_PATH_SET_IMMEDIATELY_BEFORE_CANONICAL_INTEGRATION",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--mode", choices=("start", "finalize"), required=True)
    ap.add_argument("--base-ref", required=True)
    ap.add_argument("--current-ref", default="HEAD")
    ap.add_argument("--expected-authority-epoch")
    ap.add_argument("--mutation-path", action="append", default=[])
    ap.add_argument("--dependency-path", action="append", default=[])
    ns = ap.parse_args()

    try:
        if ns.mode == "start":
            out = start_transaction(
                root=ns.root,
                base_ref=ns.base_ref,
                mutation_paths=ns.mutation_path,
                dependency_paths=ns.dependency_path,
            )
        else:
            if not ns.expected_authority_epoch:
                raise AtomicFrontierTransactionError(
                    "EXPECTED_AUTHORITY_EPOCH_REQUIRED_FOR_FINALIZE"
                )
            out = evaluate_transaction(
                root=ns.root,
                base_ref=ns.base_ref,
                current_ref=ns.current_ref,
                expected_authority_epoch=ns.expected_authority_epoch,
                mutation_paths=ns.mutation_path,
                dependency_paths=ns.dependency_path,
            )
    except Exception as exc:
        out = {
            "schema": "PROJECT_BRAIN_ATOMIC_FRONTIER_TRANSACTION_GUARD_V1",
            "pass": False,
            "status": "FAIL_CLOSED__TRANSACTION_GUARD_ERROR",
            "error": type(exc).__name__ + ":" + str(exc),
            "execution_authority": False,
            "promotion_authority": False,
        }

    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get("pass", ns.mode == "start") else 42


if __name__ == "__main__":
    raise SystemExit(main())
