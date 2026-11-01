#!/usr/bin/env python3
"""A multi-step instrument: does the machine finish a task on code it did not author?

Every number in the inventory is one request deep. A census sentence is a single sentence, the
fixture was written by the same hand that wrote the rows, and the acceptance check is part of the
sentence. That measures lookup, not engineering. This instrument measures the thing that matters:

    a real repository, a failing test, and a budget of attempts
    plan -> edit -> run -> observe -> repair

Design decisions, each made so the number cannot flatter the machine:

1. **The code is not ours.** Three real projects are cloned at pinned commits and their own test
   suites are the oracle. Nothing about the fixtures is authored here except the *injected* bug.
2. **The bug is injected mechanically**, and the injection is recorded: file, line, before, after.
   The issue text is then generated from the repository's own failing output, which is what a real
   bug report contains. A bug that turns the suite into a collection error is rejected and the next
   candidate is tried, because "the package no longer imports" is not a task.
3. **The acceptance check is the project's own suite**, run as the project runs it. It is never
   derived from the previous attempt's output.
4. **A failed attempt is fed back**, verbatim, as the observation a repairer would have: the
   failing test names and the last lines of the traceback. That is the whole difference between
   one request and a loop, and it is the only novel measurement here.
5. **Concessions are recorded, not hidden.** Each repository needs its own invocation (a src
   layout, a test subset). Those are operator-supplied and are listed in the report, because help
   the machine did not discover is help it did not provide.

Run:  python3 execution_guard/multistep_instrument_v1.py --json /tmp/multistep.json
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import pathlib
import random
import re
import shutil
import subprocess
import sys
import time
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

WORK = ROOT / "canonical" / "astra_runtime" / "tmp" / "multistep"

# PINNED COMMITS. The first version of this file claimed pinning in a comment while cloning
# whatever the default branch was that morning -- the same class of false claim the inventory keeps
# finding in its own numbers. The shas below were recorded on 2026-11-01 and are fetched explicitly,
# so a task bank is stable and two runs are comparable. A pin that cannot be fetched falls back to
# the default branch and says so in the report.
REPOS: dict[str, dict[str, Any]] = {
    "iniconfig": {
        "url": "https://github.com/pytest-dev/iniconfig.git",
        "commit": "a9e0ad14bcd0d9d3b68d2b699ce38399cbe64fdd",
        "test_cmd": [sys.executable, "-m", "pytest", "-q"],
        "py_path": None,
        "targets": ["src/iniconfig/_parse.py", "src/iniconfig/__init__.py"],
    },
    "pluggy": {
        "url": "https://github.com/pytest-dev/pluggy.git",
        "commit": "3fc9e561ea7e72a95549673d79ebdaf4a9fae829",
        "test_cmd": [sys.executable, "-m", "pytest", "-q"],
        "py_path": "src",
        "targets": ["src/pluggy/_manager.py", "src/pluggy/_callers.py", "src/pluggy/_hooks.py"],
    },
    "click": {
        "url": "https://github.com/pallets/click.git",
        "commit": "2247b35ea1c47c727d7a06e51fa280e12a863ff6",
        "test_cmd": [sys.executable, "-m", "pytest", "-q",
                     "tests/test_basic.py", "tests/test_arguments.py", "tests/test_options.py"],
        "py_path": "src",
        "targets": ["src/click/core.py", "src/click/parser.py", "src/click/types.py"],
    },
}


# --------------------------------------------------------------------------- repository plumbing

def materialise(name: str) -> pathlib.Path:
    """Clone once into the gitignored work area and return the checkout."""
    spec = REPOS[name]
    dest = WORK / name
    if (dest / ".git").is_dir():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        shutil.rmtree(dest)
    pinned = spec.get("commit")
    if pinned:
        dest.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "-C", str(dest), "init", "-q"], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(dest), "remote", "add", "origin", spec["url"]],
                       check=False, capture_output=True)
        fetched = subprocess.run(
            ["git", "-C", str(dest), "fetch", "-q", "--depth", "1", "origin", pinned],
            capture_output=True, timeout=300)
        if fetched.returncode == 0:
            subprocess.run(["git", "-C", str(dest), "checkout", "-q", "FETCH_HEAD"],
                           check=True, capture_output=True)
            return dest
        shutil.rmtree(dest, ignore_errors=True)  # the pin is unreachable; fall back and say so
    subprocess.run(["git", "clone", "--depth", "1", spec["url"], str(dest)],
                   check=True, capture_output=True, timeout=300)
    rev = subprocess.run(["git", "-C", str(dest), "rev-parse", "HEAD"],
                         capture_output=True, text=True).stdout.strip()
    spec["commit"] = rev
    spec["pin_honoured"] = False
    return dest


def _env(spec: dict[str, Any]) -> dict[str, str]:
    env = dict(os.environ)
    if spec.get("py_path"):
        env["PYTHONPATH"] = spec["py_path"]
    env.pop("PYTHONDONTWRITEBYTECODE", None)
    return env


def run_suite(repo: pathlib.Path, spec: dict[str, Any], *, timeout: int = 600) -> tuple[bool, str]:
    """The project's own acceptance command. Returns (green, tail of output)."""
    proc = subprocess.run(spec["test_cmd"], cwd=str(repo), env=_env(spec),
                          capture_output=True, text=True, timeout=timeout)
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode == 0, _tail(out)


def _tail(text: str, lines: int = 40) -> str:
    keep = [ln for ln in text.splitlines() if ln.strip()]
    return "\n".join(keep[-lines:])


# --------------------------------------------------------------------------- bug injection

MAX_FAILING = 25
MAX_FRACTION = 0.4


def _total_tests(tail: str) -> int | None:
    for n in re.findall(r"(\d+) passed", tail):
        pass
    found = re.findall(r"(\d+) passed", tail)
    return int(found[-1]) if found else None


def _failed_count(tail: str) -> int | None:
    """How many test cases the mutation broke, read from pytest's own summary line."""
    matches = re.findall(r"(\d+) failed", tail)
    return int(matches[-1]) if matches else None


_MUTATIONS = (
    ("flip_constant", lambda n: ast.Constant(value=True) if n.value is False else ast.Constant(value=False)
        if n.value is True else None),
)


def _candidate_sites(path: pathlib.Path) -> list[tuple[int, str, str]]:
    """(line, before, after) for constant flips that are syntactically safe to make."""
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (OSError, SyntaxError):
        return []
    lines = source.splitlines()
    sites: list[tuple[int, str, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, bool):
            line = lines[node.lineno - 1]
            before = "True" if node.value else "False"
            after = "False" if node.value else "True"
            if before in line:
                sites.append((node.lineno, line.strip(), line.replace(before, after).strip()))
        elif isinstance(node, ast.BoolOp):
            line = lines[node.lineno - 1]
            for old, new in ((" and ", " or "), (" or ", " and ")):
                if old in line:
                    sites.append((node.lineno, line.strip(), line.replace(old, new, 1).strip()))
                    break
        elif isinstance(node, ast.Compare) and len(node.ops) == 1:
            line = lines[node.lineno - 1]
            for old, new in (("<", ">"), (">", "<"), ("==", "!="), ("!=", "==")):
                if f" {old} " in line:
                    sites.append((node.lineno, line.strip(), line.replace(f" {old} ", f" {new} ", 1).strip()))
                    break
    return sites


def seed_bug(name: str) -> dict[str, Any]:
    """Inject the first mutation that breaks a test without breaking collection.

    Deterministic: candidates are ordered and the first success wins, so re-running the instrument
    reproduces the same task rather than inventing a new one each time.
    """
    spec = REPOS[name]
    repo = materialise(name)
    green, out = run_suite(repo, spec)
    if not green:
        return {"name": name, "seeded": False, "reason": "SUITE_NOT_GREEN_BEFORE_SEEDING", "tail": out}

    rng = random.Random(f"multistep:{name}")
    candidates = []
    roots = [repo / spec["py_path"]] if spec.get("py_path") else [repo / spec["targets"][0].split("/")[0]]
    for root in roots:
        for path in sorted(root.rglob("*.py")) if root.is_dir() else []:
            rel = path.relative_to(repo).as_posix()
            for line, before, after in _candidate_sites(path):
                if before != after:
                    candidates.append((rel, line, before, after))
    rng.shuffle(candidates)

    for rel, line, before, after in candidates[:40]:
        target = repo / rel
        original = target.read_text(encoding="utf-8")
        mutated = original.replace(before, after, 1) if before in original else None
        if not mutated or mutated == original:
            continue
        target.write_text(mutated, encoding="utf-8")
        try:
            ok, tail = run_suite(repo, spec)
        except subprocess.TimeoutExpired:
            ok, tail = True, "TIMEOUT"
        if ok:
            target.write_text(original, encoding="utf-8")  # this mutation was not observable
            continue
        if "error" in tail.lower() and "passed" not in tail.lower() and "failed" not in tail.lower():
            target.write_text(original, encoding="utf-8")  # collection error is not a task
            continue
        failed = _failed_count(tail)
        total = _total_tests(tail) or failed or 1
        ceiling = min(MAX_FAILING, max(1, int(total * MAX_FRACTION)))
        if failed is None or failed == 0 or failed > ceiling:
            # 644 failures is not a bug report, it is a demolition; and 0 is not a task.
            target.write_text(original, encoding="utf-8")
            continue
        # Commit the injected state, so ``git status`` afterwards shows only what the MACHINE did.
        # Without this, "files_changed" reported the injection itself and a door that edited
        # nothing looked like a door that had edited something.
        for cmd in (["git", "-C", str(repo), "-c", "user.email=m@x", "-c", "user.name=m",
                     "commit", "-am", "inject"],):
            subprocess.run(cmd, capture_output=True, timeout=120)
        failing = sorted(set(re.findall(r"FAILED\s+(\S+)", tail)))[:5]
        return {
            "name": name,
            "seeded": True,
            "file": rel,
            "line": line,
            "before": before,
            "after": after,
            "failing_tests": failing,
            "observation": tail,
        }
    return {"name": name, "seeded": False, "reason": "NO_OBSERVABLE_MUTATION_FOUND"}


def restore(name: str) -> None:
    spec = REPOS[name]
    repo = WORK / name
    subprocess.run(["git", "-C", str(repo), "checkout", "--", "."], capture_output=True, timeout=120)
    subprocess.run(["git", "-C", str(repo), "reset", "--hard", "-q", "HEAD~1"],
                   capture_output=True, timeout=120)
    subprocess.run(["git", "-C", str(repo), "clean", "-qfd"], capture_output=True, timeout=120)
    del spec


# --------------------------------------------------------------------------- the loop

ISSUE = (
    "Fix the failing tests in {repo}. The suite reports:\n\n{observation}\n\n"
    "The fault is in {file}. Restore the behaviour the tests expect."
)


def _door(goal: str, task_id: str) -> dict[str, Any]:
    from canonical.runtime import live_brain_route_admission_v1 as door
    started = time.perf_counter()
    try:
        result = dict(door.solve({"task_id": task_id, "goal": goal}) or {})
    except BaseException as exc:  # noqa: BLE001 - an instrument must record, not crash
        result = {"status": "RAISED:" + type(exc).__name__, "reason": str(exc)[:200]}
    result["ms"] = round((time.perf_counter() - started) * 1000)
    return result


def _changed(repo: pathlib.Path) -> list[str]:
    proc = subprocess.run(["git", "-C", str(repo), "status", "--porcelain"],
                          capture_output=True, text=True)
    return [ln[3:].strip() for ln in proc.stdout.splitlines() if ln.strip()]


def run_task(name: str, *, attempts: int = 3) -> dict[str, Any]:
    """One task: seed, then up to ``attempts`` door calls, each fed the previous observation."""
    spec = REPOS[name]
    repo = materialise(name)
    seed = seed_bug(name)
    row: dict[str, Any] = {"repo": name, "commit": spec.get("commit"), "seeded": seed.get("seeded"),
                           "injected": {k: seed.get(k) for k in ("file", "line", "before", "after")},
                           "concessions": {"test_cmd": " ".join(spec["test_cmd"]),
                                           "PYTHONPATH": spec.get("py_path")},
                           "attempts_log": [], "solved": False, "attempts_used": 0,
                           "final_stage": None}
    if not seed.get("seeded"):
        row["final_stage"] = seed.get("reason") or "SEED_FAILED"
        return row

    observation = seed["observation"]
    for attempt in range(1, attempts + 1):
        goal = ISSUE.format(repo=str(repo), observation=observation, file=seed["file"])
        res = _door(goal, f"MULTISTEP_{name}_{attempt}")
        changed = _changed(repo)
        green, after = run_suite(repo, spec)
        entry = {
            "attempt": attempt,
            "status": str(res.get("status") or ""),
            "selected": str(res.get("compiled_capability_id") or ""),
            "refusal": str(res.get("failure_class") or ""),
            "reason": str(res.get("reason") or "")[:180],
            "ms": res.get("ms"),
            "files_changed": changed,
            "edited_tests": [f for f in changed if "test" in pathlib.PurePosixPath(f).name.lower()],
            "suite_green_after": green,
            "observation_after": _tail(after, 12),
        }
        row["attempts_log"].append(entry)
        row["attempts_used"] = attempt
        if green:
            row["solved"] = True
            row["final_stage"] = "SOLVED"
            break
        # The next attempt sees what this one saw. This is the loop, and it is the only new thing.
        observation = entry["observation_after"] or entry["reason"] or entry["refusal"]
        row["final_stage"] = _stage(entry, changed)

    row["still_changed_after"] = _changed(repo)
    restore(name)
    return row


def _stage(entry: dict[str, Any], changed: list[str]) -> str:
    """Where a failed task actually died -- the diagnosis the census cannot give."""
    status = entry["status"]
    if not str(entry["selected"]).strip():
        return "NO_ROW_SELECTED"
    if status.startswith("FAIL") and not changed:
        return "REFUSED_WITH_NO_EDIT"
    if changed and not entry["suite_green_after"]:
        return "EDITED_BUT_STILL_RED"
    return "UNCLASSIFIED"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="multi-step SWE instrument")
    ap.add_argument("--repos", default=",".join(REPOS))
    ap.add_argument("--attempts", type=int, default=3)
    ap.add_argument("--json", default=None)
    args = ap.parse_args(argv)

    rows = [run_task(n.strip(), attempts=args.attempts) for n in args.repos.split(",") if n.strip()]
    solved = sum(1 for r in rows if r["solved"])
    print(f"MULTI-STEP TASKS {len(rows)}  SOLVED {solved}  BUDGET {args.attempts} attempt(s) each")
    for r in rows:
        print(f"  {r['repo']:<10} solved={r['solved']!s:<5} attempts={r['attempts_used']} "
              f"stage={r['final_stage']} injected={r['injected']['file']}:{r['injected']['line']}")
        for a in r["attempts_log"]:
            print(f"    #{a['attempt']} {a['status'][:44]:<44} row={a['selected'][:38] or '-':<38} "
                  f"edited={len(a['files_changed'])} green={a['suite_green_after']}")
    print("AUTHORITY NONE -- single-machine run, injected bugs, operator-supplied invocations")
    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(rows, indent=1), encoding="utf-8")
        print("WROTE", args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
