from __future__ import annotations

import hashlib
import pathlib
import re
import subprocess
import sys
from typing import Any, Mapping, Sequence

from canonical.runtime.goal_compiler import decompose_goal
from canonical.runtime.independent_acceptance_model import assess as assess_independence

CAPABILITY_ID = "python.software.acceptance.specification.v1"
SCHEMA = "PROJECT_BRAIN_PYTHON_SOFTWARE_ACCEPTANCE_SPECIFICATION_V1"

_PATH_RE = re.compile(r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+|[A-Za-z0-9_.-]+[.]py")
_QUOTED_RE = re.compile(r'["\']([^"\']+)["\']')


class SoftwareAcceptanceSpecError(ValueError):
    pass


def _safe_relative(raw: str) -> str:
    text = str(raw or "").strip().strip(chr(96)).replace("\\", "/")
    p = pathlib.PurePosixPath(text)
    if not text or p.is_absolute() or ".." in p.parts:
        raise SoftwareAcceptanceSpecError("UNSAFE_REPOSITORY_PATH:" + text)
    return str(p)


def _paths(text: str) -> list[str]:
    out: list[str] = []
    tick = chr(96)
    for token in re.findall(tick + r"([^" + tick + r"]+)" + tick, text):
        if "/" in token or "." in pathlib.PurePosixPath(token).name:
            try:
                p = _safe_relative(token)
            except SoftwareAcceptanceSpecError:
                continue
            if p not in out:
                out.append(p)
    for token in _PATH_RE.findall(text):
        try:
            p = _safe_relative(token.rstrip(".,;:!?)]}"))
        except SoftwareAcceptanceSpecError:
            continue
        if p not in out:
            out.append(p)
    return out


def _clauses(request: str) -> list[str]:
    text = " ".join(str(request or "").strip().split())
    if not text:
        raise SoftwareAcceptanceSpecError("REQUEST_REQUIRED")
    base = decompose_goal(text) or [text]
    out: list[str] = []
    splitter = re.compile(
        r"\s*(?:;|\n|\band\s+(?=(?:must\b|should\b|do\s+not\b|don't\b|"
        r"create\b|add\b|write\b|delete\b|remove\b|run\b|only\s+modify\b)))\s*",
        re.IGNORECASE,
    )
    for part in base:
        for item in splitter.split(part):
            item = item.strip(" .")
            if item:
                out.append(item)
    return out


def _sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _predicate(pid: str, clause: str, kind: str, verifier: Mapping[str, Any] | None, *, reason: str | None = None) -> dict[str, Any]:
    return {
        "predicate_id": pid,
        "clause": clause,
        "kind": kind,
        "critical": True,
        "bound": verifier is not None,
        "verifier": None if verifier is None else dict(verifier),
        "unbound_reason": reason,
    }


def compile_request(
    request: str,
    root: Any,
    *,
    max_scope_baseline_files: int = 2000,
) -> dict[str, Any]:
    base = pathlib.Path(root).resolve()
    clauses = _clauses(request)
    predicates: list[dict[str, Any]] = []

    for index, clause in enumerate(clauses):
        pid = f"R{index+1}"
        lower = clause.casefold()
        if "../" in clause or "..\\" in clause:
            predicates.append(_predicate(
                pid,
                clause,
                "UNSAFE_PATH_REFERENCE",
                None,
                reason="PATH_TRAVERSAL_REFERENCE_REJECTED",
            ))
            continue
        paths = _paths(clause)
        quoted = _QUOTED_RE.findall(clause)

        if re.search(r"\bonly\s+modify\b", lower):
            if not paths:
                predicates.append(_predicate(pid, clause, "SCOPE_UNCHANGED", None, reason="ALLOWED_PATHS_NOT_EXPLICIT"))
                continue
            allowed = sorted(set(paths))
            baseline: dict[str, str] = {}
            too_large = False
            for p in sorted(x for x in base.rglob("*") if x.is_file() and ".git" not in x.parts):
                rel = p.relative_to(base).as_posix()
                if any(rel == a or rel.startswith(a.rstrip("/") + "/") for a in allowed):
                    continue
                baseline[rel] = _sha256(p)
                if len(baseline) > int(max_scope_baseline_files):
                    too_large = True
                    break
            if too_large:
                predicates.append(_predicate(pid, clause, "SCOPE_UNCHANGED", None, reason="SCOPE_BASELINE_TOO_LARGE"))
                continue
            predicates.append(_predicate(pid, clause, "SCOPE_UNCHANGED", {
                "kind": "SCOPE_UNCHANGED",
                "allowed_paths": allowed,
                "baseline_sha256": baseline,
            }))
            continue

        if re.search(r"\b(?:do\s+not|don't)\s+modify\b", lower):
            if len(paths) != 1:
                predicates.append(_predicate(pid, clause, "FILE_UNCHANGED", None, reason="EXACT_PATH_REQUIRED"))
                continue
            p = (base / paths[0]).resolve()
            if not p.is_file() or base not in p.parents:
                predicates.append(_predicate(pid, clause, "FILE_UNCHANGED", None, reason="BASELINE_FILE_MISSING"))
                continue
            predicates.append(_predicate(pid, clause, "FILE_UNCHANGED", {
                "kind": "FILE_SHA256_EQUALS",
                "path": paths[0],
                "sha256": _sha256(p),
            }))
            continue

        if re.search(r"\bmust\s+not\s+(?:contain|include)\b", lower):
            if len(paths) != 1 or len(quoted) != 1:
                predicates.append(_predicate(pid, clause, "TEXT_ABSENT", None, reason="EXACT_PATH_AND_QUOTED_TEXT_REQUIRED"))
                continue
            predicates.append(_predicate(pid, clause, "TEXT_ABSENT", {
                "kind": "TEXT_ABSENT",
                "path": paths[0],
                "text": quoted[0],
            }))
            continue

        if re.search(r"\bmust\s+(?:contain|include)\b", lower):
            if len(paths) != 1 or len(quoted) != 1:
                predicates.append(_predicate(pid, clause, "TEXT_PRESENT", None, reason="EXACT_PATH_AND_QUOTED_TEXT_REQUIRED"))
                continue
            predicates.append(_predicate(pid, clause, "TEXT_PRESENT", {
                "kind": "TEXT_PRESENT",
                "path": paths[0],
                "text": quoted[0],
            }))
            continue

        if re.search(r"\b(?:create|add|write)\b", lower) and re.search(r"\bfile\b", lower):
            if len(paths) != 1:
                predicates.append(_predicate(pid, clause, "FILE_EXISTS", None, reason="EXACT_PATH_REQUIRED"))
                continue
            predicates.append(_predicate(pid, clause, "FILE_EXISTS", {"kind": "FILE_EXISTS", "path": paths[0]}))
            continue

        if re.search(r"\b(?:delete|remove)\b", lower) and (paths or "file" in lower):
            if len(paths) != 1:
                predicates.append(_predicate(pid, clause, "FILE_ABSENT", None, reason="EXACT_PATH_REQUIRED"))
                continue
            predicates.append(_predicate(pid, clause, "FILE_ABSENT", {"kind": "FILE_ABSENT", "path": paths[0]}))
            continue

        if re.search(r"\b(?:must\s+compile|compiles?\s+successfully|python\s+compile)\b", lower):
            py = [p for p in paths if p.endswith(".py")]
            if len(py) != 1:
                predicates.append(_predicate(pid, clause, "PYTHON_COMPILE", None, reason="EXACT_PYTHON_PATH_REQUIRED"))
                continue
            predicates.append(_predicate(pid, clause, "PYTHON_COMPILE", {"kind": "PYTHON_COMPILE", "path": py[0]}))
            continue

        if re.search(r"\b(?:tests?|unittest)\b", lower) and re.search(r"\b(?:pass|run|succeed)\b", lower):
            py = [p for p in paths if p.endswith(".py")]
            if len(py) != 1:
                predicates.append(_predicate(pid, clause, "PYTHON_TEST_PASS", None, reason="EXACT_TEST_PATH_REQUIRED"))
                continue
            predicates.append(_predicate(pid, clause, "PYTHON_TEST_PASS", {
                "kind": "PYTHON_TEST_FILE_PASS",
                "path": py[0],
                "timeout_s": 20,
            }))
            continue

        predicates.append(_predicate(
            pid,
            clause,
            "SEMANTIC_REQUIREMENT_UNBOUND",
            None,
            reason="NO_INDEPENDENT_EXECUTABLE_VERIFIER_DERIVED_FROM_EXPLICIT_REQUEST",
        ))

    return {
        "schema": SCHEMA,
        "capability_id": CAPABILITY_ID,
        "status": "COMPILED__FAIL_CLOSED_ON_UNBOUND_SEMANTICS",
        "request": str(request),
        "clauses": clauses,
        "predicates": predicates,
        "all_critical_bound": all(bool(x["bound"]) for x in predicates),
        "bound_predicate_count": sum(1 for x in predicates if x["bound"]),
        "unbound_predicate_count": sum(1 for x in predicates if not x["bound"]),
        "existing_tests_are_not_complete_request_semantics": True,
        "general_purpose_model_dependency_count": 0,
        "external_general_purpose_model_runtime_dependency_count": 0,
        "incremental_spend_usd": 0,
    }


def _resolve_file(base: pathlib.Path, rel: str) -> pathlib.Path:
    safe = _safe_relative(rel)
    p = (base / safe).resolve()
    if p == base or base not in p.parents:
        raise SoftwareAcceptanceSpecError("PATH_ESCAPES_REPOSITORY:" + safe)
    return p


def _run_verifier(spec: Mapping[str, Any], base: pathlib.Path) -> tuple[bool, str]:
    kind = str(spec.get("kind") or "")
    if kind == "FILE_EXISTS":
        p = _resolve_file(base, str(spec["path"]))
        return p.is_file(), "FILE_EXISTS"
    if kind == "FILE_ABSENT":
        p = _resolve_file(base, str(spec["path"]))
        return not p.exists(), "FILE_ABSENT"
    if kind == "FILE_SHA256_EQUALS":
        p = _resolve_file(base, str(spec["path"]))
        return p.is_file() and _sha256(p) == str(spec["sha256"]), "FILE_SHA256_EQUALS"
    if kind in {"TEXT_PRESENT", "TEXT_ABSENT"}:
        p = _resolve_file(base, str(spec["path"]))
        if not p.is_file():
            return False, "TEXT_SOURCE_MISSING"
        text = p.read_text(encoding="utf-8")
        present = str(spec["text"]) in text
        return (present if kind == "TEXT_PRESENT" else not present), kind
    if kind == "PYTHON_COMPILE":
        p = _resolve_file(base, str(spec["path"]))
        if not p.is_file():
            return False, "PYTHON_SOURCE_MISSING"
        try:
            compile(p.read_text(encoding="utf-8"), str(p), "exec")
        except (SyntaxError, UnicodeError):
            return False, "PYTHON_COMPILE"
        return True, "PYTHON_COMPILE"
    if kind == "PYTHON_TEST_FILE_PASS":
        p = _resolve_file(base, str(spec["path"]))
        if not p.is_file():
            return False, "TEST_FILE_MISSING"
        timeout = float(spec.get("timeout_s", 20))
        try:
            cp = subprocess.run(
                [sys.executable, "-m", "unittest", str(p.relative_to(base))],
                cwd=str(base),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=timeout,
                check=False,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )
        except subprocess.TimeoutExpired:
            return False, "PYTHON_TEST_TIMEOUT"
        return cp.returncode == 0, "PYTHON_TEST_FILE_PASS"
    if kind == "SCOPE_UNCHANGED":
        baseline = spec.get("baseline_sha256")
        allowed = [str(x) for x in (spec.get("allowed_paths") or [])]
        if not isinstance(baseline, Mapping):
            raise SoftwareAcceptanceSpecError("SCOPE_BASELINE_INVALID")
        for rel, expected in baseline.items():
            p = _resolve_file(base, str(rel))
            if not p.is_file() or _sha256(p) != str(expected):
                return False, "SCOPE_UNCHANGED"
        for p in (x for x in base.rglob("*") if x.is_file() and ".git" not in x.parts):
            rel = p.relative_to(base).as_posix()
            if rel in baseline:
                continue
            if any(rel == a or rel.startswith(a.rstrip("/") + "/") for a in allowed):
                continue
            return False, "SCOPE_UNCHANGED"
        return True, "SCOPE_UNCHANGED"
    raise SoftwareAcceptanceSpecError("VERIFIER_KIND_UNSUPPORTED:" + kind)


def verify_acceptance(plan: Mapping[str, Any], root: Any) -> dict[str, Any]:
    if not isinstance(plan, Mapping) or plan.get("schema") != SCHEMA:
        raise SoftwareAcceptanceSpecError("PLAN_SCHEMA_INVALID")
    predicates = plan.get("predicates")
    if not isinstance(predicates, Sequence) or isinstance(predicates, (str, bytes)):
        raise SoftwareAcceptanceSpecError("PREDICATES_INVALID")

    base = pathlib.Path(root).resolve()
    results: list[dict[str, Any]] = []
    iam_requirements: list[dict[str, Any]] = []
    iam_checks: list[dict[str, Any]] = []

    for row in predicates:
        if not isinstance(row, Mapping):
            raise SoftwareAcceptanceSpecError("PREDICATE_INVALID")
        pid = str(row.get("predicate_id") or "")
        if not pid:
            raise SoftwareAcceptanceSpecError("PREDICATE_ID_REQUIRED")
        bound = row.get("bound") is True and isinstance(row.get("verifier"), Mapping)
        if not bound:
            results.append({
                "predicate_id": pid,
                "bound": False,
                "pass": False,
                "status": "UNBOUND",
                "reason": row.get("unbound_reason"),
            })
            continue

        verifier = dict(row["verifier"])
        passed, observed = _run_verifier(verifier, base)
        failure_mode = "acceptance_predicate_violation:" + str(row.get("kind") or "UNKNOWN")
        iam_requirements.append({
            "id": pid,
            "critical": True,
            "must_detect_failure_modes": [failure_mode],
            "builder_dependencies": ["builder:software_change"],
        })
        iam_checks.append({
            "id": "CHECK_" + pid,
            "covers": [pid],
            "provenance": "independent_oracle",
            "dependencies": ["raw:repository_state", "oracle:" + str(verifier.get("kind") or "unknown")],
            "detects": [failure_mode],
            "derived_from_builder_output": False,
        })
        results.append({
            "predicate_id": pid,
            "bound": True,
            "pass": bool(passed),
            "status": "PASS" if passed else "FAIL",
            "verifier_kind": verifier.get("kind"),
            "observed": observed,
        })

    independent = assess_independence({
        "requirements": iam_requirements,
        "checks": iam_checks,
    }) if iam_requirements else {
        "schema": "BRAIN_INDEPENDENT_ACCEPTANCE_MODEL_RESULT_V1",
        "pass": False,
        "terminal_submission_authorized_by_this_gate": False,
        "failed_requirements": [],
        "requirements": [],
    }

    all_bound = len(results) == len(predicates) and all(x["bound"] for x in results)
    all_pass = bool(results) and all(x["pass"] for x in results)
    accepted = all_bound and all_pass and independent.get("pass") is True

    return {
        "schema": SCHEMA + "_RESULT",
        "capability_id": CAPABILITY_ID,
        "status": "PASS__ALL_EXPLICIT_ACCEPTANCE_PREDICATES_BOUND_AND_VERIFIED" if accepted else "FAIL_CLOSED__ACCEPTANCE_INCOMPLETE_OR_FAILED",
        "pass": accepted,
        "candidate_repair_acceptance_authorized": accepted,
        "merge_or_promotion_authority": False,
        "all_critical_bound": all_bound,
        "all_bound_checks_pass": all_pass,
        "predicate_results": results,
        "independent_acceptance_model": independent,
        "existing_test_pass_does_not_override_unbound_semantics": True,
        "general_purpose_model_dependency_count": 0,
        "external_general_purpose_model_runtime_dependency_count": 0,
        "incremental_spend_usd": 0,
        "hard_nonclaims": [
            "NO_ARBITRARY_NATURAL_LANGUAGE_SEMANTIC_COMPLETENESS",
            "NO_HIDDEN_REQUIREMENT_INFERENCE",
            "NO_GENERAL_MERGEABILITY_AUTHORITY",
            "NO_FRONTIERCODE_SCORE_CREDIT",
        ],
    }


def compile_and_verify(request: str, root: Any) -> dict[str, Any]:
    plan = compile_request(request, root)
    return {
        "plan": plan,
        "verification": verify_acceptance(plan, root),
    }
