# PROJECT_BRAIN
"""python.review.diff_security_gate.v1 — security triage on changed lines.

Lint proves name hygiene, types prove soundness, coverage proves
execution, perf proves speed — none of them can see ``shell=True`` on a
changed line, an ``eval`` of external input, or a hardcoded password.
This adapter runs bandit's JSON report on the diff's touched files and
intersects findings with the new-side changed line ranges.

* BASELINE (always runs, stdlib): touched ``.py`` parsed with ``ast``.
* BANDIT (PyPI tool, probed live): ``bandit -f json --quiet`` per
  touched file.  Blocking policy (stated in the artifact, as a senior
  would apply it): severity HIGH blocks; severity MEDIUM blocks when
  confidence is HIGH; everything else is ADVISORY evidence.
* tool-absent -> gate ``PASS_BASELINE_ONLY``, loudly partial, verified
  stays False.  rc>1 (invocation failure) is a named refusal, never a
  silent clean report.

Laws:
* changed-lines-only: pre-existing findings outside the diff's new-side
  ranges are advisory context (``out_of_scope``), never blockers.
* determinism: findings sorted by (file, line, test_id); byte-identical
  artifacts on rerun (pin-proven).
* fail closed on PATH_*, DIFF_EMPTY, TOUCHED_FILE_MISSING_IN_WORKTREE,
  BANDIT_OUTPUT_NOT_JSON, BANDIT_INVOCATION_FAILED.
* zero repo mutation: reads only.

Inputs (kwargs, repo-confined):
  diff_path          unified diff artifact under review
  worktree_path      tree holding the NEW-side bytes of the touched files
  output_path        summary artifact (registry result_fields mirror)
  python_executable  interpreter used to probe/run bandit (default: this one)
  timeout_s          wall-clock cap per bandit call (default 120)

result_fields: adapter, diff_sha256, files_touched, blocking_findings,
advisory_findings, syntax_errors, bandit, gate, complete, output_path,
output_sha256, output_verified, verified.
"""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from canonical.runtime.bound_capabilities.review_gate_input_safety_v1 import guard_inputs

from canonical.runtime.bound_capabilities.python_review_diff_static_triage import (
    _parse_diff_ranges,
)

SCHEMA = "PROJECT_BRAIN_DIFF_SECURITY_GATE_V1"


def _fail(reason: str) -> dict:
    return {
        "error": True,
        "capability": "python.review.diff_security_gate.v1",
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


# hardcoded-secret family blocks regardless of bandit's LOW severity label:
# a senior blocks a real password in a diff every time.
_SECRET_FAMILY = {"B104", "B105", "B106", "B107"}


def _is_blocking(severity: str, confidence: str, test_id: str) -> bool:
    if test_id in _SECRET_FAMILY:
        return True
    if severity == "HIGH":
        return True
    return severity == "MEDIUM" and confidence == "HIGH"


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

    # -- stage 1: syntax baseline ----------------------------------------
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

    # -- stage 2: bandit json over touched files --------------------------
    bandit_version = None
    blocking, advisory = [], []
    probe = subprocess.run([python_exe, "-c",
                            "import bandit; print('bandit', bandit.__version__)"],
                           capture_output=True, text=True, timeout=min(timeout_s, 30))
    if probe.returncode == 0 and probe.stdout.strip().startswith("bandit"):
        bandit_version = (probe.stdout.strip().splitlines() or ["bandit"])[0]
        if not syntax_errors:
            for rel in sorted(files_on_disk):
                proc = subprocess.run(
                    [python_exe, "-m", "bandit", "-f", "json", "--quiet", "--", rel],
                    cwd=worktree_abs, capture_output=True, text=True,
                    timeout=timeout_s)
                if proc.returncode not in (0, 1):
                    return _fail("BANDIT_INVOCATION_FAILED:rc=" + str(proc.returncode) + ":" +
                          (proc.stderr.strip().splitlines() or ["<empty>"])[0][:200])
                try:
                    doc = json.loads(proc.stdout)
                except json.JSONDecodeError:
                    return _fail("BANDIT_OUTPUT_NOT_JSON")
                if not isinstance(doc, dict) or not isinstance(doc.get("errors"), list):
                    return _fail("BANDIT_OUTPUT_SHAPE_UNEXPECTED")
                if doc["errors"]:
                    return _fail("BANDIT_SCAN_INCOMPLETE")
                rows = doc.get("results")
                if (not isinstance(rows, list) or (proc.returncode == 1 and not rows)
                        or (proc.returncode == 0 and rows)
                        or any(not isinstance(row, dict) or not isinstance(row.get("filename"), str)
                               or not isinstance(row.get("line_number"), int)
                               or row["line_number"] <= 0 or not isinstance(row.get("test_id"), str)
                               or row.get("issue_severity") not in ("LOW", "MEDIUM", "HIGH")
                               or row.get("issue_confidence") not in ("LOW", "MEDIUM", "HIGH")
                               for row in rows)):
                    return _fail("BANDIT_OUTPUT_SHAPE_UNEXPECTED")
                for row in sorted(rows, key=lambda r: (str(r.get("filename")),
                                                       int(r.get("line_number") or 0),
                                                       str(r.get("test_id")))):
                    fname = str(row.get("filename") or "").replace("\\", "/").lstrip("./")
                    line = int(row.get("line_number") or 0)
                    item = {"file": rel,
                            "line": line,
                            "test_id": str(row.get("test_id") or ""),
                            "severity": str(row.get("issue_severity") or ""),
                            "confidence": str(row.get("issue_confidence") or ""),
                            "message": str(row.get("issue_text") or "")[:300]}
                    if _in_ranges(changed[rel], line):
                        (blocking if _is_blocking(item["severity"], item["confidence"],
                                                  item["test_id"])
                         else advisory).append(item)
                    else:
                        advisory.append({**item, "out_of_scope": "preexisting"})

    if not py_changed:
        gate = "NO_PYTHON_CHANGES"
    elif bandit_version is None:
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
        "bandit": bandit_version or "UNAVAILABLE",
        "blocking_findings": blocking,
        "advisory_findings": advisory,
        "blocking_count": len(blocking),
        "advisory_count": len(advisory),
        "gate": gate,
        "gate_law": ("PASS needs zero syntax errors AND zero blocking security rows "
                     "on changed lines with bandit actually running; HIGH severity "
                     "blocks, MEDIUM blocks at HIGH confidence, LOW is advisory; "
                     "PASS_BASELINE_ONLY is recorded loudly when the tool is absent; "
                     "pre-existing findings outside the diff's ranges are context, "
                     "never blockers"),
        "complete": complete,
    }
    out_abs.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(artifact, indent=2, ensure_ascii=False) + "\n"
    out_abs.write_text(text, encoding="utf-8")
    out_verified = json.loads(out_abs.read_text(encoding="utf-8")) == artifact

    return {
        "adapter": "python_review_diff_security_gate",
        "diff_sha256": artifact["diff_sha256"],
        "files_touched": len(py_changed),
        "blocking_findings": len(blocking),
        "advisory_findings": len(advisory),
        "syntax_errors": len(syntax_errors),
        "bandit": bandit_version or "UNAVAILABLE",
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
