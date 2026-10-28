"""The analysers a Python engineer actually runs: ruff, mypy, bandit.

The inventory's second-ranked gap was static analysis.  It was not a missing algorithm -- ruff,
mypy and bandit are installed in this repository's own environment -- it was that nothing called
them.  Measured before this module existed, over the 43-act probe:

    "Lint the python source <R>/pkg and report it to <O>"       -> python.source.audit.ast, PASS
    "Type check the python source <R>/pkg and report it to <O>" -> python.source.audit.ast, PASS
    "Audit the dependencies in <R> for vulnerabilities"         -> python.source.audit.ast, PASS

An AST walker answered all three with a credible artifact and a PASS: the worst shape a report
can take, because a lint report that never ran a linter is indistinguishable from a clean one.

What this module refuses to do is as important as what it does.  An analyser that is not
installed is a REFUSAL (`TOOL_NOT_INSTALLED:<tool>`), not an empty finding list, because "no
issues" and "never ran" must never be reported the same way.  Every tool is resolved from the
interpreter that is running this code first (`sys.executable`'s directory) and then from PATH,
so the analyser is the one belonging to this environment rather than whichever binary a shell
happens to find.

Each verb writes the artifact the front door promised, and every artifact is re-derivable: the
digest covers the document with the digest field blanked, so `verify_artifact` can reproduce it.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

DEFAULT_TIMEOUT_S = 300

# ruff's own rule families, named so the artifact says which contract it measured.
_RUFF_LINT_SELECT = "E,F,W,I,B,UP,SIM,C4,RUF"
_RUFF_DEAD_CODE_SELECT = "F401,F811,F841"
_RUFF_COMPLEXITY_SELECT = "C901"
_COMPLEXITY_THRESHOLD = 10


class ToolchainError(RuntimeError):
    """A refusal the caller can act on: the request did not meet the verb's contract."""


def _fail(reason: str) -> None:
    raise ToolchainError(reason)


# --------------------------------------------------------------------------- resolution


def _inside(repo: Path, path: str) -> Path | None:
    """The file or directory a stated path names, stated the way the front layer states it.

    The binder states paths relative to the root it was given; a tool run inside a worktree (or
    here, inside the repository root) needs them relative to that.  Both name the same entry, so
    the prefix is found inside the stated path rather than the path being refused.  Nothing is
    invented: a path that names nothing is still refused.
    """
    stated = Path(path)
    if stated.is_absolute() and stated.exists():
        return stated
    if not stated.is_absolute():
        # A path the sentence stated ABSOLUTELY can reach here with its separator stripped
        # ("home/u/x.py" for "/home/u/x.py"), and joining that onto the root fabricates a
        # mirror that never exists.  The absolute reading wins when it is the one that names
        # something real.
        absolute_like = Path("/") / stated
        if absolute_like.exists():
            return absolute_like
        if (repo / stated).exists():
            return repo / stated
    parts = stated.parts[1:] if stated.is_absolute() else stated.parts
    for start in range(1, len(parts)):
        candidate = Path(*parts[start:])
        if (repo / candidate).exists():
            return repo / candidate
    return None


def _resolve_tool(name: str) -> str:
    """The analyser belonging to THIS interpreter, or its PATH entry, or a refusal."""
    beside_python = Path(sys.executable).parent / name
    if beside_python.is_file() and os.access(beside_python, os.X_OK):
        return str(beside_python)
    found = shutil.which(name)
    if found:
        return found
    _fail("TOOL_NOT_INSTALLED:" + name)


def _run(argv: list[str], cwd: Path, timeout_s: int) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            argv, cwd=str(cwd), capture_output=True, text=True, timeout=timeout_s
        )
    except subprocess.TimeoutExpired:
        _fail("TOOL_TIMED_OUT:" + " ".join(argv[:2]))
    except OSError as exc:
        _fail("TOOL_NOT_EXECUTABLE:" + " ".join(argv[:2]) + ":" + str(exc)[:120])


# --------------------------------------------------------------------------- artifact


def _canonical(payload: dict) -> str:
    body = dict(payload)
    body["artifact_sha256"] = ""
    return json.dumps(body, indent=1, sort_keys=True) + "\n"


def verify_artifact(output_path: Path) -> str:
    """Re-derive a written artifact's digest from its own bytes. Raises on mismatch."""
    loaded = json.loads(Path(output_path).read_text(encoding="utf-8"))
    recorded = str(loaded.get("artifact_sha256") or "")
    derived = hashlib.sha256(_canonical(loaded).encode("utf-8")).hexdigest()
    if not recorded or recorded != derived:
        _fail("ARTIFACT_DIGEST_MISMATCH:" + str(recorded)[:16])
    return derived


def _write(output_path: Path, payload: dict) -> dict:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload["artifact_path"] = str(output_path)
    payload["artifact_sha256"] = ""
    payload["artifact_sha256"] = hashlib.sha256(
        _canonical(payload).encode("utf-8")
    ).hexdigest()
    output_path.write_text(
        json.dumps(payload, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    verify_artifact(output_path)
    return payload


def _base(capability_id: str, tool: str, target: Path) -> dict[str, Any]:
    return {
        "adapter": "toolchain_v1",
        "capability_id": capability_id,
        "tool": tool,
        "target": str(target),
        "gate": "PASS",
        "model_dependency_count": 0,
    }


# --------------------------------------------------------------------------- verbs


def _ruff_json(
    tool: str, argv: list[str], cwd: Path, timeout_s: int
) -> tuple[list[dict], str]:
    """ruff's findings, and whatever it printed that is not a finding."""
    proc = _run(argv, cwd, timeout_s)
    # ruff exits 1 when it HAS findings and 2+ when it could not do its job.  A finding is the
    # answer to the question that was asked; a failure to run is not.
    if proc.returncode >= 2:
        _fail(
            "TOOL_FAILED:%s:%s"
            % (tool, (proc.stderr or proc.stdout or "").strip()[:200])
        )
    try:
        findings = json.loads(proc.stdout or "[]")
    except ValueError:
        _fail("TOOL_OUTPUT_UNPARSEABLE:" + tool)
    if not isinstance(findings, list):
        _fail("TOOL_OUTPUT_UNPARSEABLE:" + tool)
    return findings, (proc.stderr or "").strip()


def _rel(repo: Path, filename: str) -> str:
    try:
        return str(Path(filename).resolve().relative_to(repo.resolve()))
    except (ValueError, OSError):
        return str(filename)


def _lint(args, target: Path, cap: str) -> dict:
    tool = _resolve_tool("ruff")
    timeout_s = int(args.get("timeout_s") or DEFAULT_TIMEOUT_S)
    select = str(args.get("select") or _RUFF_LINT_SELECT)
    findings, stderr = _ruff_json(
        tool,
        [
            tool,
            "check",
            "--output-format",
            "json",
            "--select",
            select,
            "--no-cache",
            str(target),
        ],
        Path.cwd(),
        timeout_s,
    )
    rows = [
        {
            "code": str(f.get("code") or ""),
            "message": str(f.get("message") or "")[:200],
            "path": _rel(
                target.parent, str((f.get("location") or {}).get("path") or "")
            ),
            "line": int(((f.get("location") or {}).get("row") or 0)),
            "fix_available": bool(f.get("fix")),
        }
        for f in findings
    ]
    codes: dict[str, int] = {}
    for row in rows:
        codes[row["code"]] = codes.get(row["code"], 0) + 1
    return {
        **_base(cap, "ruff", target),
        "rule_families": select,
        "issue_count": len(rows),
        "issues": rows,
        "issue_codes": codes,
        "clean": not rows,
        "tool_stderr": stderr,
    }


def _format(args, target: Path, cap: str) -> dict:
    tool = _resolve_tool("ruff")
    timeout_s = int(args.get("timeout_s") or DEFAULT_TIMEOUT_S)
    check_only = bool(args.get("check_only", False))
    argv = (
        [tool, "format", "--no-cache"]
        + (["--check", "--diff"] if check_only else [])
        + [str(target)]
    )
    proc = _run(argv, Path.cwd(), timeout_s)
    if proc.returncode not in (0, 1):
        _fail("TOOL_FAILED:ruff:" + (proc.stderr or proc.stdout or "").strip()[:200])
    touched = (
        [
            line.split("Would reformat:", 1)[1].strip()
            for line in (proc.stdout or "").splitlines()
            if line.startswith("Would reformat:")
        ]
        if check_only
        else []
    )
    if not check_only:
        touched = [
            line.split("Reformatted", 1)[1].strip()
            for line in (proc.stderr or "").splitlines()
            if line.startswith("Reformatted")
        ]
    return {
        **_base(cap, "ruff", target),
        "check_only": check_only,
        "changed_files": touched,
        "changed_count": len(touched),
        "reformatted": bool(touched),
        "unformatted": proc.returncode == 1 if check_only else bool(touched),
    }


def _type_check(args, target: Path, cap: str) -> dict:
    tool = _resolve_tool("mypy")
    timeout_s = int(args.get("timeout_s") or DEFAULT_TIMEOUT_S)
    proc = _run(
        [
            tool,
            "--no-error-summary",
            "--show-error-codes",
            "--no-color-output",
            # `--explicit-package-bases` because an ordinary package directory imports the same
            # file under two module names ("bound_capabilities.x" and
            # "canonical.runtime.bound_capabilities.x") and mypy refuses that as a duplicate
            # source -- measured on this repository's own adapters, where the refusal was
            # reported as TOOL_FAILED instead of as the type result it is.
            "--explicit-package-bases",
            "--ignore-missing-imports",
            str(target),
        ],
        Path.cwd(),
        timeout_s,
    )
    if proc.returncode not in (0, 1):
        _fail("TOOL_FAILED:mypy:" + (proc.stderr or proc.stdout or "").strip()[:200])
    errors, notes = [], []
    for line in (proc.stdout or "").splitlines():
        parts = line.split(":", 4)
        if len(parts) >= 5 and parts[4].strip().startswith(("error:", "note:")):
            kind, message = parts[4].strip().split(":", 1)
            row = {
                "path": parts[0],
                "line": parts[1].strip(),
                "column": parts[2].strip(),
                "message": message.strip()[:200],
            }
            (errors if kind == "error" else notes).append(row)
    return {
        **_base(cap, "mypy", target),
        "error_count": len(errors),
        "errors": errors,
        "note_count": len(notes),
        "clean": not errors,
        "mypy_exit": proc.returncode,
    }


def _complexity(args, target: Path, cap: str) -> dict:
    tool = _resolve_tool("ruff")
    timeout_s = int(args.get("timeout_s") or DEFAULT_TIMEOUT_S)
    threshold = int(args.get("threshold") or _COMPLEXITY_THRESHOLD)
    select = str(args.get("select") or _RUFF_COMPLEXITY_SELECT)
    findings, stderr = _ruff_json(
        tool,
        [
            tool,
            "check",
            "--output-format",
            "json",
            "--select",
            select,
            "--no-cache",
            str(target),
        ],
        Path.cwd(),
        timeout_s,
    )
    rows = [
        {
            "path": _rel(
                target.parent, str((f.get("location") or {}).get("path") or "")
            ),
            "line": int(((f.get("location") or {}).get("row") or 0)),
            "message": str(f.get("message") or "")[:200],
        }
        for f in findings
    ]
    # ruff's C901 message ends "is too complex (N > M)"; the number is the measurement.
    measured = []
    for row in rows:
        text = row["message"]
        value = 0
        if "(" in text and ")" in text:
            inner = text[text.rindex("(") + 1 : text.rindex(")")]
            head = inner.split(">", 1)[0].strip()
            value = int(head) if head.isdigit() else 0
        measured.append({**row, "cyclomatic_complexity": value})
    over = [m for m in measured if m["cyclomatic_complexity"] > threshold]
    return {
        **_base(cap, "ruff", target),
        "threshold": threshold,
        "functions": measured,
        "over_threshold_count": len(over),
        "max_complexity": max(
            [m["cyclomatic_complexity"] for m in measured], default=0
        ),
        "within_threshold": not over,
        "tool_stderr": stderr,
    }


def _dead_code(args, target: Path, cap: str) -> dict:
    tool = _resolve_tool("ruff")
    timeout_s = int(args.get("timeout_s") or DEFAULT_TIMEOUT_S)
    select = str(args.get("select") or _RUFF_DEAD_CODE_SELECT)
    findings, stderr = _ruff_json(
        tool,
        [
            tool,
            "check",
            "--output-format",
            "json",
            "--select",
            select,
            "--no-cache",
            str(target),
        ],
        Path.cwd(),
        timeout_s,
    )
    rows = [
        {
            "code": str(f.get("code") or ""),
            "path": _rel(
                target.parent, str((f.get("location") or {}).get("path") or "")
            ),
            "line": int(((f.get("location") or {}).get("row") or 0)),
            "message": str(f.get("message") or "")[:200],
        }
        for f in findings
    ]
    return {
        **_base(cap, "ruff", target),
        "unused_count": len(rows),
        "unused": rows,
        "rules": select,
        "clean": not rows,
        "tool_stderr": stderr,
    }


def _security(args, target: Path, cap: str) -> dict:
    """bandit, run through THIS interpreter so the analyser and its policy travel together."""
    timeout_s = int(args.get("timeout_s") or DEFAULT_TIMEOUT_S)
    proc = _run(
        [sys.executable, "-m", "bandit", "-r", "-f", "json", "-q", str(target)],
        Path.cwd(),
        timeout_s,
    )
    if proc.returncode not in (0, 1):
        detail = (proc.stderr or proc.stdout or "").strip()
        if "No module named bandit" in detail:
            _fail("TOOL_NOT_INSTALLED:bandit")
        _fail("TOOL_FAILED:bandit:" + detail[:200])
    try:
        report = json.loads(proc.stdout or "{}")
    except ValueError:
        _fail("TOOL_OUTPUT_UNPARSEABLE:bandit")
    rows = [
        {
            "test_id": str(r.get("test_id") or ""),
            "test_name": str(r.get("test_name") or ""),
            "severity": str(r.get("issue_severity") or "").lower(),
            "confidence": str(r.get("issue_confidence") or "").lower(),
            "path": _rel(target.parent, str(r.get("filename") or "")),
            "line": int(r.get("line_number") or 0),
            "message": str(r.get("issue_text") or "")[:200],
        }
        for r in (report.get("results") or [])
    ]
    severities: dict[str, int] = {}
    for row in rows:
        severities[row["severity"]] = severities.get(row["severity"], 0) + 1
    return {
        **_base(cap, "bandit", target),
        "issue_count": len(rows),
        "issues": rows,
        "severity_counts": severities,
        "files_scanned": len(report.get("metrics", {}) or {}),
        "clean": not rows,
    }


_HANDLERS = {
    "lint": _lint,
    "format": _format,
    "type_check": _type_check,
    "complexity": _complexity,
    "dead_code": _dead_code,
    "security": _security,
}


def run(args: dict, root: Path) -> dict:
    """The one entrypoint every analyser capability uses.  Keys come from the action template."""
    args = dict(args or {})
    root = Path(root)
    verb = str(args.get("tool_verb") or "").strip()
    capability_id = str(args.get("capability_id") or "")
    output_path = str(args.get("output_path") or "").strip()
    if not output_path:
        _fail("OUTPUT_PATH_NOT_STATED")
    destination = Path(output_path)
    if not destination.is_absolute():
        # Same separator problem, one layer out: a DESTINATION does not exist yet, so the
        # decision is made from the parent that does.
        absolute_like = Path("/") / output_path
        joined = root / destination
        if not joined.parent.exists() and absolute_like.parent.exists():
            destination = absolute_like
        else:
            destination = joined
    try:
        if verb not in _HANDLERS:
            _fail("TOOL_VERB_NOT_SUPPORTED:" + (verb or "<none>"))
        stated = str(args.get("source_root") or args.get("path") or "").strip()
        if not stated:
            _fail("PATH_NOT_STATED")
        target = _inside(root, stated)
        if target is None:
            _fail("PATH_NOT_IN_THE_REPOSITORY:" + stated)
        payload = _HANDLERS[verb](args, target, capability_id)
    except ToolchainError as exc:
        refusal = {
            "adapter": "toolchain_v1",
            "capability_id": capability_id,
            "tool": verb,
            "gate": "FAIL",
            "reason": str(exc),
        }
        _write(destination, refusal)
        raise
    return _write(destination, payload)
