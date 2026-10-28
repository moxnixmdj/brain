# PROJECT_BRAIN
"""python.review.diff_static_triage.v1 — the review gate on the produced diff.

A senior engineer never opens a PR before static triage *on the changed
lines* — whole-repo lint noise hides the signal.  This adapter diffs a
unified-diff artifact (e.g. the issue→PR crown's output) against the tree
it targets and runs two honest gates:

* BASELINE (always runs, stdlib): every touched ``.py`` must compile
  (``ast.parse`` in-process) — syntax errors are blocking findings with
  file:line evidence.
* RUFF (PyPI tool, probed live): ``ruff check --output-format json
  --no-cache --isolated`` on the touched files inside the named worktree,
  findings INTERSECTED with the new-side changed line ranges of the diff.
  - F* and E9* are BLOCKING on changed lines (undefined names, syntax
    classes) — the classes a real reviewer blocks a PR on.
  - everything else is ADVISORY — listed, never blocking.
  - tool-absent is reported ``UNAVAILABLE`` and the gate becomes
    ``PASS_SYNTAX_ONLY`` — loudly partial, never pretending the full sweep
    ran.

Laws:
* changed-lines-only filtering: pre-existing findings elsewhere in a
  touched file cannot fail a PR that did not touch those lines.
* determinism: findings sorted; byte-identical artifacts on rerun with the
  same inputs (pin-proven).
* fail closed: path escapes, unreadable diff, missing touched files,
  malformed ruff JSON output — all refuse with named reasons.
* zero repo mutation: the triage reads; nothing writes into source trees.

Inputs (kwargs, repo-confined):
  diff_path        unified diff artifact under review
  worktree_path    tree holding the NEW-side bytes of the touched files
  output_path      summary artifact (registry result_fields mirror)
  python_executable interpreter used to probe/run ruff (default: this one)
  timeout_s        wall-clock cap for the ruff call (default 60)

result_fields: adapter, diff_sha256, files_touched, blocking_findings,
advisory_findings, syntax_errors, ruff, gate, complete, output_path,
output_sha256, output_verified, verified.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

from canonical.runtime.bound_capabilities.review_gate_input_safety_v1 import guard_inputs

SCHEMA = "PROJECT_BRAIN_DIFF_STATIC_TRIAGE_V1"
BLOCKING_PREFIXES = ("F", "E9")
_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def _fail(reason: str) -> dict:
    return {
        "error": True,
        "capability": "python.review.diff_static_triage.v1",
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


def _parse_diff_ranges(text: str) -> tuple[dict, list[str]]:
    """{path: [(start,end)...]} of new-side ranges; created files → [(1, None)].
    Only touchable file kinds retained; deletions are evidence-less rows."""
    changed: dict[str, list] = {}
    created: list[str] = []
    cur = None
    cur_created = False
    for line in text.splitlines():
        if line.startswith("--- "):
            cur = None
            cur_created = False
            if line.strip() == "--- /dev/null":
                cur_created = True
        elif line.startswith("+++ "):
            if cur_created:
                cur = line[4:].strip()
                if cur.startswith("b/"):
                    cur = cur[2:]
                created.append(cur)
                changed.setdefault(cur, [])
                cur_created = False
            else:
                path = line[4:].strip()
                if path == "/dev/null":
                    cur = None
                    continue
                if path.startswith("b/"):
                    path = path[2:]
                cur = path
                changed.setdefault(cur, [])
        elif line.startswith("@@") and cur is not None:
            m = _HUNK.match(line)
            if m:
                start = int(m.group(1))
                count = int(m.group(2) or "1")
                changed[cur].append((start, start + max(count, 1) - 1))
    # created files: whole file is "changed" (range 1..inf)
    for path in created:
        changed[path] = [(1, 10 ** 9)]
    return {k: v for k, v in changed.items() if v}, sorted(created)


def _in_ranges(ranges: list, lineno: int) -> bool:
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
    timeout_s = int(args.get("timeout_s") or 60)
    python_exe = str(args.get("python_executable") or sys.executable)

    # -- stage 1: baseline compile of every touched .py -------------------
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

    # -- stage 2: ruff, filtered to the changed line ranges ---------------
    ruff_version = None
    blocking, advisory = [], []
    probe = subprocess.run([python_exe, "-m", "ruff", "--version"],
                           capture_output=True, text=True, timeout=min(timeout_s, 30))
    if probe.returncode == 0 and probe.stdout.strip().startswith("ruff"):
        ruff_version = probe.stdout.strip()
        touched = sorted(files_on_disk)
        if touched:
            proc = subprocess.run(
                [python_exe, "-m", "ruff", "check", "--output-format", "json",
                 "--no-cache", "--isolated", "--select", "E,F,W", "--"] + touched,
                cwd=worktree_abs, capture_output=True, text=True, timeout=timeout_s)
            if proc.returncode not in (0, 1):
                _fail("RUFF_INVOCATION_FAILED:rc=" + str(proc.returncode))
            try:
                rows = json.loads(proc.stdout)
            except json.JSONDecodeError:
                return _fail("RUFF_OUTPUT_NOT_JSON")
            if (not isinstance(rows, list) or (proc.returncode == 1 and not rows)
                    or (proc.returncode == 0 and rows)
                    or any(not isinstance(row, dict) or not isinstance(row.get("filename"), str)
                           or not isinstance(row.get("location"), dict)
                           or not isinstance(row["location"].get("row"), int)
                           or row["location"]["row"] <= 0 or not isinstance(row.get("code"), str)
                           for row in rows)):
                return _fail("RUFF_OUTPUT_SHAPE_UNEXPECTED")
            for row in sorted(rows, key=lambda r: (str(r.get("filename")),
                                                   int(r.get("location", {}).get("row", 0)),
                                                   str(r.get("code")))):
                fname = str(row.get("filename") or "")
                # normalize to repo/worktree-relative
                for rel in files_on_disk:
                    if fname.endswith("/" + rel) or fname == rel:
                        lineno = int(row.get("location", {}).get("row", 0))
                        code = str(row.get("code") or "")
                        msg = str(row.get("message") or "")
                        item = {"file": rel, "line": lineno, "code": code,
                                "message": msg[:200]}
                        if _in_ranges(changed[rel], lineno):
                            if code.startswith(BLOCKING_PREFIXES):
                                blocking.append(item)
                            else:
                                advisory.append(item)
                        # findings outside the changed ranges are pre-existing:
                        # visible in the artifact as context, never blocking.
                        else:
                            row_class = "preexisting"
                            advisory.append({**item, "out_of_scope": row_class})

    gate = "FAIL"
    if not py_changed:
        gate = "NO_PYTHON_CHANGES"
    elif ruff_version is None:
        gate = "FAIL" if syntax_errors else "PASS_SYNTAX_ONLY"
    elif ruff_version and not syntax_errors and not blocking:
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
        "ruff": ruff_version or "UNAVAILABLE",
        "blocking_findings": blocking,
        "advisory_findings": advisory,
        "blocking_count": len(blocking),
        "advisory_count": len(advisory),
        "gate": gate,
        "gate_law": ("PASS needs zero syntax errors AND zero F*/E9* findings on "
                     "changed lines with ruff actually running; PASS_SYNTAX_ONLY is "
                     "recorded loudly when the tool is absent; pre-existing findings "
                     "outside the changed ranges are advisory context, never blockers"),
        "complete": complete,
    }
    out_abs.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(artifact, indent=2, ensure_ascii=False) + "\n"
    out_abs.write_text(text, encoding="utf-8")
    out_verified = json.loads(out_abs.read_text(encoding="utf-8")) == artifact

    return {
        "adapter": "python_review_diff_static_triage",
        "diff_sha256": artifact["diff_sha256"],
        "files_touched": len(py_changed),
        "blocking_findings": len(blocking),
        "advisory_findings": len(advisory),
        "syntax_errors": len(syntax_errors),
        "ruff": ruff_version or "UNAVAILABLE",
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
    p.add_argument("--timeout_s", type=int, default=60)
    ns = p.parse_args()
    print(json.dumps(run(vars(ns), Path.cwd()), indent=2, sort_keys=True))
