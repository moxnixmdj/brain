from __future__ import annotations

import ast
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
from typing import Any, Mapping, Sequence

from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract

SCHEMA = "PROJECT_BRAIN_PYTHON_REQUEST_ACCEPTANCE_MODEL_V1"
PLAN_SCHEMA = "PROJECT_BRAIN_PYTHON_REQUEST_ACCEPTANCE_PLAN_V1"
RESULT_SCHEMA = "PROJECT_BRAIN_PYTHON_REQUEST_ACCEPTANCE_RESULT_V1"


class RequestAcceptanceError(RuntimeError):
    pass


_QUOTED = r'["“]([^"”]+)["”]'
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canon(value).encode("utf-8")).hexdigest()


def _safe_rel(raw: Any) -> str:
    if not isinstance(raw, str) or not raw.strip() or "\x00" in raw:
        raise RequestAcceptanceError("PATH_INVALID")
    p = pathlib.PurePosixPath(raw.replace("\\", "/").strip())
    if p.is_absolute() or any(part in {"", ".", ".."} for part in p.parts):
        raise RequestAcceptanceError("PATH_INVALID")
    return p.as_posix()


def _safe_path(root: pathlib.Path, raw: Any, *, require_file: bool | None = None) -> pathlib.Path:
    rel = _safe_rel(raw)
    p = (root / rel).resolve()
    if p == root or root not in p.parents:
        raise RequestAcceptanceError("PATH_OUTSIDE_REPOSITORY")
    if p.exists() and p.is_symlink():
        raise RequestAcceptanceError("SYMLINK_REJECTED")
    if require_file is True and not p.is_file():
        raise RequestAcceptanceError("FILE_REQUIRED")
    if require_file is False and p.exists() and not p.is_dir():
        raise RequestAcceptanceError("DIRECTORY_REQUIRED")
    return p


def _classify(segment: str) -> dict[str, Any] | None:
    s = " ".join(segment.strip().split())

    # Order negative forms before positive forms.
    patterns: list[tuple[str, str]] = [
        ("FILE_NOT_CONTAINS", rf'(?i)^(?:the\s+)?file\s+{_QUOTED}\s+must\s+not\s+contain\s+{_QUOTED}[.!]?$'),
        ("FILE_CONTAINS", rf'(?i)^(?:the\s+)?file\s+{_QUOTED}\s+must\s+contain\s+{_QUOTED}[.!]?$'),
        ("FILE_ABSENT", rf'(?i)^(?:the\s+)?file\s+{_QUOTED}\s+must\s+not\s+exist[.!]?$'),
        ("FILE_EXISTS", rf'(?i)^(?:the\s+)?file\s+{_QUOTED}\s+must\s+exist[.!]?$'),
        ("PYTHON_AST_PARSE", rf'(?i)^python\s+file\s+{_QUOTED}\s+must\s+(?:parse|compile)[.!]?$'),
        ("PYTHON_TEST_FILE_PASS", rf'(?i)^(?:python\s+)?test\s+file\s+{_QUOTED}\s+must\s+pass[.!]?$'),
        ("PATH_UNCHANGED", rf'(?i)^(?:do\s+not\s+modify|must\s+not\s+modify)\s+{_QUOTED}[.!]?$'),
    ]
    for kind, pat in patterns:
        m = re.fullmatch(pat, s)
        if not m:
            continue
        groups = list(m.groups())
        if kind in {"FILE_CONTAINS", "FILE_NOT_CONTAINS"}:
            path, literal = groups[0], groups[1]
            return {"kind": kind, "path": _safe_rel(path), "literal": literal}
        return {"kind": kind, "path": _safe_rel(groups[0])}

    # Deliberately narrow scope grammar. It is mechanically checkable from the
    # candidate's changed-path set and therefore does not rely on semantic guesswork.
    m = re.fullmatch(rf'(?i)^only\s+modify\s+{_QUOTED}[.!]?$', s)
    if m:
        return {"kind": "CHANGED_PATHS_SUBSET", "allowed_paths": [_safe_rel(m.group(1))]}

    return None


def _predicate_row(obligation: Mapping[str, Any]) -> dict[str, Any]:
    raw_text = str(obligation.get("text") or "")
    verifier = _classify(raw_text)
    semantic = "BOUND_EXECUTABLE" if verifier is not None else "UNBOUND"
    return {
        "predicate_id": "ACCEPT:" + _sha({
            "obligation_id": obligation.get("obligation_id"),
            "segment_sha256": obligation.get("segment_sha256"),
            "verifier": verifier,
        }),
        "obligation_id": obligation.get("obligation_id"),
        "segment_index": obligation.get("segment_index"),
        "segment_sha256": obligation.get("segment_sha256"),
        "raw_text": raw_text,
        "predicate_class": (
            "NEGATIVE_REQUIREMENT"
            if verifier and verifier.get("kind") in {"FILE_NOT_CONTAINS", "FILE_ABSENT", "PATH_UNCHANGED"}
            else "SCOPE"
            if verifier and verifier.get("kind") == "CHANGED_PATHS_SUBSET"
            else "BEHAVIOR_OR_CONSTRAINT"
        ),
        "semantic_binding": semantic,
        "verifier": verifier,
        "unbound_reason": None if verifier is not None else "NO_SOUND_BOUNDED_EXECUTABLE_SEMANTIC_BINDING",
        "existing_test_evidence_may_self_bind_this_predicate": False,
    }


def compile_plan(
    request_text: str,
    *,
    source_id: str = "software_request",
    routing_target_effects: Sequence[str] = ("software.patch.correct",),
) -> dict[str, Any]:
    contract = compile_contract(
        request_text,
        source_id=source_id,
        routing_target_effects=list(routing_target_effects),
    )
    if contract.get("pass") is not True:
        return {
            "schema": PLAN_SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": list(contract.get("errors") or ["RAW_CONTRACT_FAILED"]),
            "model_dependency_count": 0,
            "external_capability_provider_count": 0,
            "incremental_spend_usd": 0,
        }

    obligations = contract["acceptance_contract"]["obligations"]
    predicates = [_predicate_row(row) for row in obligations]
    bound = [row for row in predicates if row["semantic_binding"] == "BOUND_EXECUTABLE"]
    unbound = [row for row in predicates if row["semantic_binding"] == "UNBOUND"]
    payload = {
        "task_contract_sha256": contract["task_contract_sha256"],
        "task_sha256": contract["task_sha256"],
        "predicates": [
            {
                "predicate_id": row["predicate_id"],
                "obligation_id": row["obligation_id"],
                "segment_sha256": row["segment_sha256"],
                "semantic_binding": row["semantic_binding"],
                "verifier": row["verifier"],
            }
            for row in predicates
        ],
    }
    return {
        "schema": PLAN_SCHEMA,
        "status": "COMPILED__ALL_RAW_OBLIGATIONS_EXECUTABLY_BOUND" if not unbound else "COMPILED__UNBOUND_ACCEPTANCE_PREDICATES_REMAIN",
        "pass": True,
        "task_contract": contract,
        "acceptance_predicates": predicates,
        "bound_predicate_count": len(bound),
        "unbound_predicate_count": len(unbound),
        "all_raw_obligations_semantically_bound": not unbound,
        "acceptance_plan_sha256": _sha(payload),
        "existing_test_evidence_is_request_semantics_authority": False,
        "repair_stop_authorized_at_compile_time": False,
        "model_dependency_count": 0,
        "external_capability_provider_count": 0,
        "incremental_spend_usd": 0,
        "hard_nonclaims": [
            "NO_ARBITRARY_NATURAL_LANGUAGE_SEMANTIC_COMPLETENESS",
            "NO_CLAIM_EXISTING_TEST_PASS_PROVES_UNBOUND_REQUEST_SEMANTICS",
            "NO_UNBOUND_PREDICATE_MAY_BE_SILENTLY_DROPPED",
            "NO_GENERAL_SOFTWARE_REPAIR_COMPLETENESS",
            "NO_FRONTIERCODE_SCORE_OR_ACCEPTANCE_CREDIT",
        ],
    }


def _run_verifier(
    verifier: Mapping[str, Any],
    *,
    root: pathlib.Path,
    changed_paths: set[str],
    timeout_s: int,
) -> tuple[bool, str, dict[str, Any]]:
    kind = str(verifier.get("kind") or "")
    details: dict[str, Any] = {"kind": kind}

    if kind == "CHANGED_PATHS_SUBSET":
        allowed = {_safe_rel(x) for x in verifier.get("allowed_paths") or []}
        ok = changed_paths <= allowed
        details.update({"allowed_paths": sorted(allowed), "changed_paths": sorted(changed_paths)})
        return ok, "CHANGED_PATHS_WITHIN_SCOPE" if ok else "CHANGED_PATH_OUTSIDE_SCOPE", details

    path = _safe_rel(verifier.get("path"))
    p = _safe_path(root, path)
    details["path"] = path

    if kind == "FILE_EXISTS":
        ok = p.is_file() and not p.is_symlink()
        return ok, "FILE_EXISTS" if ok else "FILE_MISSING", details

    if kind == "FILE_ABSENT":
        ok = not p.exists()
        return ok, "FILE_ABSENT" if ok else "FILE_PRESENT", details

    if kind == "PATH_UNCHANGED":
        ok = path not in changed_paths
        details["changed_paths"] = sorted(changed_paths)
        return ok, "PATH_UNCHANGED" if ok else "PATH_CHANGED", details

    if kind in {"FILE_CONTAINS", "FILE_NOT_CONTAINS"}:
        if not p.is_file() or p.is_symlink():
            return False, "FILE_MISSING", details
        data = p.read_bytes()
        if len(data) > 4_000_000:
            return False, "FILE_TOO_LARGE", details
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            return False, "FILE_NOT_UTF8", details
        literal = str(verifier.get("literal") or "")
        found = literal in text
        details["literal_sha256"] = hashlib.sha256(literal.encode("utf-8")).hexdigest()
        details["file_sha256"] = hashlib.sha256(data).hexdigest()
        ok = found if kind == "FILE_CONTAINS" else not found
        return ok, ("LITERAL_PRESENT" if found else "LITERAL_ABSENT"), details

    if kind == "PYTHON_AST_PARSE":
        if not p.is_file() or p.is_symlink() or p.suffix != ".py":
            return False, "PYTHON_FILE_INVALID", details
        try:
            ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
        except (SyntaxError, UnicodeDecodeError):
            return False, "PYTHON_PARSE_FAILED", details
        details["file_sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
        return True, "PYTHON_PARSE_PASS", details

    if kind == "PYTHON_TEST_FILE_PASS":
        if not p.is_file() or p.is_symlink() or p.suffix != ".py":
            return False, "TEST_FILE_INVALID", details
        try:
            proc = subprocess.run(
                [sys.executable, str(p)],
                cwd=root,
                text=True,
                capture_output=True,
                timeout=timeout_s,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )
        except subprocess.TimeoutExpired:
            return False, "TEST_TIMEOUT", details
        details.update({
            "returncode": proc.returncode,
            "stdout_sha256": hashlib.sha256(proc.stdout.encode("utf-8", "replace")).hexdigest(),
            "stderr_sha256": hashlib.sha256(proc.stderr.encode("utf-8", "replace")).hexdigest(),
            "test_file_sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
        })
        return proc.returncode == 0, "TEST_PASS" if proc.returncode == 0 else "TEST_FAIL", details

    return False, "UNKNOWN_VERIFIER_KIND", details


def evaluate_plan(
    plan: Mapping[str, Any],
    *,
    repo_root: str | os.PathLike[str],
    changed_paths: Sequence[str] = (),
    existing_test_evidence: Mapping[str, Any] | None = None,
    timeout_s: int = 20,
) -> dict[str, Any]:
    if not isinstance(plan, Mapping) or plan.get("schema") != PLAN_SCHEMA or plan.get("pass") is not True:
        raise RequestAcceptanceError("PLAN_INVALID")
    root = pathlib.Path(repo_root).resolve()
    if not root.is_dir() or root.is_symlink():
        raise RequestAcceptanceError("REPOSITORY_INVALID")
    timeout = max(1, min(int(timeout_s), 60))
    changed = {_safe_rel(x) for x in changed_paths}

    rows = []
    for pred in plan.get("acceptance_predicates") or []:
        if pred.get("semantic_binding") != "BOUND_EXECUTABLE" or not isinstance(pred.get("verifier"), Mapping):
            rows.append({
                "predicate_id": pred.get("predicate_id"),
                "obligation_id": pred.get("obligation_id"),
                "status": "UNBOUND",
                "pass": False,
                "reason": pred.get("unbound_reason") or "UNBOUND",
            })
            continue
        ok, reason, details = _run_verifier(
            pred["verifier"],
            root=root,
            changed_paths=changed,
            timeout_s=timeout,
        )
        rows.append({
            "predicate_id": pred.get("predicate_id"),
            "obligation_id": pred.get("obligation_id"),
            "status": "VERIFIED_PASS" if ok else "VERIFIED_FAIL",
            "pass": ok,
            "reason": reason,
            "details": details,
        })

    unbound = [r for r in rows if r["status"] == "UNBOUND"]
    failed = [r for r in rows if r["status"] == "VERIFIED_FAIL"]
    complete = bool(rows) and not unbound and not failed
    # Existing tests are deliberately informational here. They can be inputs to
    # a specific explicit "test file must pass" predicate, but they cannot erase
    # or auto-bind an unrelated raw request obligation.
    test_evidence = dict(existing_test_evidence or {})
    return {
        "schema": RESULT_SCHEMA,
        "status": "PASS__COMPLETE_BOUND_REQUEST_ACCEPTANCE" if complete else "OPEN__REQUEST_ACCEPTANCE_NOT_COMPLETE",
        "pass": complete,
        "acceptance_plan_sha256": plan.get("acceptance_plan_sha256"),
        "predicate_results": rows,
        "bound_verified_pass_count": sum(r["status"] == "VERIFIED_PASS" for r in rows),
        "bound_verified_fail_count": len(failed),
        "unbound_predicate_count": len(unbound),
        "all_raw_obligations_semantically_bound": not unbound,
        "all_bound_verifiers_pass": not failed,
        "existing_test_evidence": test_evidence,
        "existing_test_evidence_is_request_semantics_authority": False,
        "repair_stop_authorized_by_this_capability": complete,
        "model_dependency_count": 0,
        "external_capability_provider_count": 0,
        "incremental_spend_usd": 0,
        "hard_nonclaims": [
            "NO_ARBITRARY_NATURAL_LANGUAGE_SEMANTIC_COMPLETENESS",
            "NO_TEST_PASS_TO_UNBOUND_REQUEST_SEMANTICS_INFERENCE",
            "NO_REPAIR_STOP_WHILE_ANY_REQUEST_PREDICATE_IS_UNBOUND_OR_FAILING",
            "NO_GENERAL_MERGEABILITY_OR_FRONTIERCODE_SCORE_CLAIM",
        ],
    }


def run(args: Mapping[str, Any], root: str | os.PathLike[str]) -> dict[str, Any]:
    if not isinstance(args, Mapping):
        raise RequestAcceptanceError("ARGS_NOT_OBJECT")
    request_text = str(args.get("request_text") or "")
    plan = compile_plan(
        request_text,
        source_id=str(args.get("source_id") or "software_request"),
        routing_target_effects=tuple(args.get("routing_target_effects") or ("software.patch.correct",)),
    )
    if plan.get("pass") is not True:
        return plan
    if args.get("compile_only") is True:
        return plan
    return evaluate_plan(
        plan,
        repo_root=root,
        changed_paths=tuple(args.get("changed_paths") or ()),
        existing_test_evidence=args.get("existing_test_evidence") if isinstance(args.get("existing_test_evidence"), Mapping) else None,
        timeout_s=int(args.get("timeout_s", 20)),
    )
