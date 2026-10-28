# PROJECT_BRAIN
"""python.review.diff_type_gate.v1 — the type-soundness gate on the diff.

Static triage (python.review.diff_static_triage.v1, ruff F/E/W) catches
undefined names and syntax classes.  It cannot see a type lie: an `int`
bound to a `str`, an unsupported operand pair, a wrong-arity call.  A
senior engineer blocks those on review — this adapter runs mypy's native
JSON output on the diff's touched files and blocks on error-severity
findings INTERSECTED with the new-side changed line ranges.

* BASELINE (always runs, stdlib): every touched ``.py`` parsed with
  ``ast`` — syntax errors are blocking findings with file:line evidence.
* MYPY (PyPI tool, probed live): ``mypy -O json --no-incremental
  --follow-imports=silent --ignore-missing-imports`` on the touched
  files inside the named worktree.  severity=="error" rows on changed
  lines are BLOCKING; notes/warnings are ADVISORY.
* tool-absent is reported ``UNAVAILABLE`` and the gate becomes
  ``PASS_BASELINE_ONLY`` — loudly partial, never pretending the type
  sweep ran.

Laws:
* changed-lines-only filtering: pre-existing findings outside the diff's
  new-side ranges are advisory context (``out_of_scope``), never blockers.
* determinism: findings sorted by (file, line, code); no incremental
  cache (``--no-incremental``), no bytecode writes; byte-identical
  artifacts on rerun (pin-proven).
* fail closed: path escapes, empty diff, missing touched files,
  malformed mypy rows — all refuse with named reasons.
* zero repo mutation: reads only; nothing writes into source trees.

Inputs (kwargs, repo-confined):
  diff_path          unified diff artifact under review
  worktree_path      tree holding the NEW-side bytes of the touched files
  output_path        summary artifact (registry result_fields mirror)
  python_executable  interpreter used to probe/run mypy (default: this one)
  timeout_s          wall-clock cap for the mypy call (default 120)

result_fields: adapter, diff_sha256, files_touched, blocking_findings,
advisory_findings, syntax_errors, mypy, gate, complete, output_path,
output_sha256, output_verified, verified.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from canonical.runtime.bound_capabilities.review_gate_input_safety_v1 import guard_inputs

from canonical.runtime.bound_capabilities.python_review_diff_static_triage import (
    _parse_diff_ranges,
)

SCHEMA = "PROJECT_BRAIN_DIFF_TYPE_GATE_V1"


def _fail(reason: str) -> dict:
    return {
        "error": True,
        "capability": "python.review.diff_type_gate.v1",
        "reason": reason,
    }


def _safe_path(repo: Path, rel: str, must_exist: bool = False) -> Path | dict:
    if not rel or not isinstance(rel, str):
        return _fail("MISSING_OR_INVALID_PATH_ARGUMENT")
    p = (repo / rel).resolve()
    if p != repo and repo not in p.parents:
        return _fail("PATH_ESCAPE:" + rel)
    if must_exist and not p.exists():
        return _fail("PATH_MISSING:" + rel)
    return p


def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _in_ranges(ranges, lineno: int) -> bool:
    return any(start <= lineno <= end for start, end in ranges)


def run(args, root):
    repo = Path(root).resolve()
    args = dict(args or {})
    diff_rel = str(args.get("diff_path") or "")
    diff_abs = _safe_path(repo, diff_rel, must_exist=True)
    if isinstance(diff_abs, dict): return diff_abs
    diff_text = diff_abs.read_text(encoding="utf-8", errors="replace")
    if not diff_text.strip():
        return _fail("DIFF_EMPTY")
    changed, created = _parse_diff_ranges(diff_text)
    py_changed = {p: r for p, r in changed.items() if p.endswith(".py")}

    worktree_rel = str(args.get("worktree_path") or "")
    worktree_abs = _safe_path(repo, worktree_rel, must_exist=True)
    if isinstance(worktree_abs, dict): return worktree_abs
    if not worktree_abs.is_dir():
        return _fail("WORKTREE_NOT_DIRECTORY")
    out_abs = _safe_path(repo, str(args.get("output_path") or ""))
    if isinstance(out_abs, dict): return out_abs
    guard_result = guard_inputs(worktree_abs, diff_abs, out_abs, py_changed, _fail)
    if isinstance(guard_result, dict):
        return guard_result
    timeout_s = int(args.get("timeout_s") or 120)
    python_exe = str(args.get("python_executable") or sys.executable)

    # -- stage 1: baseline parse of every touched .py ---------------------
    syntax_errors = []
    files_on_disk = {}
    for rel in sorted(py_changed):
        target = worktree_abs / rel
        if not target.is_file():
            return _fail("TOUCHED_FILE_MISSING_IN_WORKTREE:" + rel)
        files_on_disk[rel] = target
        try:
            ast.parse(target.read_text(encoding="utf-8"), filename=rel)
        except SyntaxError as exc:
            syntax_errors.append({"file": rel, "line": exc.lineno, "msg": str(exc.msg)})

    # -- stage 2: mypy json rows, filtered to the changed line ranges ------
    mypy_version = None
    blocking, advisory = [], []
    probe = subprocess.run([python_exe, "-m", "mypy", "--version"],
                           capture_output=True, text=True, timeout=min(timeout_s, 30))
    if probe.returncode == 0 and probe.stdout.strip().startswith("mypy"):
        mypy_version = probe.stdout.strip().split(" (")[0]
        touched = sorted(files_on_disk)
        if touched and not syntax_errors:
            proc = subprocess.run(
                [python_exe, "-m", "mypy", "-O", "json", "--no-incremental", "--cache-dir", os.devnull,
                 "--follow-imports=silent", "--ignore-missing-imports",
                 "--no-color-output", "--"] + touched,
                cwd=worktree_abs, capture_output=True, text=True, timeout=timeout_s)
            if proc.returncode not in (0, 1):
                _fail("MYPY_INVOCATION_FAILED:rc=" + str(proc.returncode) + ":" +
                      (proc.stderr.strip().splitlines() or ["<empty>"])[0][:200])
            rows = []
            for line in proc.stdout.splitlines():
                line = line.strip()
                if not line or not line.startswith("{"):
                    continue  # tolerate the plaintext summary line
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    return _fail("MYPY_OUTPUT_ROW_NOT_JSON")
            if ((proc.returncode == 1 and not rows)
                    or any(not isinstance(row, dict) or not isinstance(row.get("file"), str)
                           or not row["file"] or not isinstance(row.get("line"), int)
                           or row["line"] <= 0 or row.get("severity") not in ("error", "note", "warning")
                           for row in rows)):
                return _fail("MYPY_OUTPUT_INCOMPLETE")
            for row in sorted(rows, key=lambda r: (str(r.get("file")),
                                                   int(r.get("line") or 0),
                                                   str(r.get("code")))):
                fname = str(row.get("file") or "").replace("\\", "/")
                for rel in files_on_disk:
                    if fname.endswith("/" + rel) or fname == rel:
                        item = {"file": rel,
                                "line": int(row.get("line") or 0),
                                "code": str(row.get("code") or "untyped"),
                                "severity": str(row.get("severity") or "error"),
                                "message": str(row.get("message") or "")[:300]}
                        if _in_ranges(changed[rel], item["line"]):
                            if item["severity"] == "error":
                                blocking.append(item)
                            else:
                                advisory.append(item)
                        else:
                            advisory.append({**item, "out_of_scope": "preexisting"})
    elif probe.returncode != 0 or "mypy" not in probe.stdout.strip().lower():
        mypy_version = None

    if not py_changed:
        gate = "NO_PYTHON_CHANGES"
    elif mypy_version is None:
        gate = "FAIL" if syntax_errors else "PASS_BASELINE_ONLY"
    elif syntax_errors or blocking:
        gate = "FAIL"
    else:
        gate = "PASS"
    complete = True
    verified = gate == "PASS"

    artifact = {
        "schema": SCHEMA,
        "diff_path": diff_rel,
        "diff_sha256": _sha256(diff_text.encode("utf-8")),
        "files_touched": len(py_changed),
        "created_files": created,
        "syntax_errors": syntax_errors,
        "mypy": mypy_version or "UNAVAILABLE",
        "blocking_findings": blocking,
        "advisory_findings": advisory,
        "blocking_count": len(blocking),
        "advisory_count": len(advisory),
        "gate": gate,
        "gate_law": ("PASS needs zero syntax errors AND zero mypy error-severity "
                     "rows on changed lines with mypy actually running; "
                     "PASS_BASELINE_ONLY is recorded loudly when the tool is absent; "
                     "pre-existing findings outside the changed ranges are advisory "
                     "context, never blockers"),
        "complete": complete,
    }
    out_abs.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(artifact, indent=2, ensure_ascii=False) + "\n"
    out_abs.write_text(text, encoding="utf-8")
    out_verified = json.loads(out_abs.read_text(encoding="utf-8")) == artifact

    return {
        "adapter": "python_review_diff_type_gate",
        "diff_sha256": artifact["diff_sha256"],
        "files_touched": len(py_changed),
        "blocking_findings": len(blocking),
        "advisory_findings": len(advisory),
        "syntax_errors": len(syntax_errors),
        "mypy": mypy_version or "UNAVAILABLE",
        "gate": gate,
        "complete": complete,
        "output_path": str(args.get("output_path")),
        "output_sha256": _sha256(text.encode("utf-8")),
        "output_verified": out_verified,
        "verified": bool(verified),
    }


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--diff_path", required=True)
    p.add_argument("--worktree_path", required=True)
    p.add_argument("--output_path", required=True)
    p.add_argument("--python_executable", default=None)
    p.add_argument("--timeout_s", type=int, default=120)
    ns = p.parse_args()
    print(json.dumps(run(vars(ns), Path.cwd()), indent=2, sort_keys=True))
