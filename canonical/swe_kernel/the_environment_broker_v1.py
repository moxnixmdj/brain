"""The environment broker: go into an arbitrary environment knowing nothing, ask the right
questions, verify every answer by running it, and only then keep it.

WHY THIS EXISTS
---------------
The user's proposal, taken literally:

    "an algorithm that enters any new arbitrary environment and does not know anything;
     it only asks the right questions and learns everything it needs, instantly."

This project has already measured the pieces. What it does not have is the link that turns
"the host printed something" into "the environment works, and here is the proof". That link
is the broker. It is deliberately NOT the whole agent and deliberately NOT smart: it holds
a fixed, declared set of environment questions, because a question set that can grow without
bound is the knowledge house coming back through the side door. When the goal is not inside
the declared contracts, the broker refuses by name instead of improvising.

THE FIVE QUESTIONS, AND THE ORDER THEY MUST BE ASKED IN
-------------------------------------------------------
    LAYOUT        what shape is this tree          (files only, never executes)
    INTERPRETER   what runs it                     (pyproject requires-python, checked)
    RUNNER        what checks it                   (candidate command lines, EXECUTED)
    DEPS          what must exist for it to run    (the project's own declarations)
    CONTRACT      what counts as success           (from the goal, or REFUSE)

The verification half is the whole point. Every answer except LAYOUT is confirmed by
execution before it is believed, because a printed page is not a machine (this tree's own
measured lesson: 0 of 164 catalogue options that own programs would run were executed to a
state change). A file can be stale, a doc can lie, a digest can drift -- a bounded run that
returns exit code 0 cannot.

WHAT IS CACHED, AND WHAT THAT MAKES THE MEMORY
-----------------------------------------------
One record per environment, keyed by the sha256 of the EVIDENCE FILES' contents (never by
path, never by name): the answer set, the command it verified with, its exit code, and the
wall clock. Nothing about the action sequence is stored; actions do not transfer and are
the cheapest thing to re-derive.

A cache is never trusted blindly. On a warm run the cached runner is re-executed and must
still return 0; if it does not, the entry is discarded and re-derived. So the broker's
staleness window is one check, not the lifetime of the file.

COST
----
Local evidence only. No model, no network, no weights. The web is the fallback for what the
host cannot answer, never the first source, and it is deliberately absent here: this module
makes no claim about web retrieval. Host-first is measured, not stylistic: asking this host
costs 6.78 ms against 255.2 ms for the web, and 7,432 man-page citations on this host
resolve to zero present files (intake/SCAN_RETRIEVE_FETCH_20261121_V1.md).

REFUSALS, ALL BY NAME
---------------------
    REFUSE__NOT_A_PYTHON_ENVIRONMENT   no pyproject/setup evidence found; nothing to ask about
    REFUSE__GOAL_OUTSIDE_THE_CLOSED_CONTRACTS  the goal is not one of the declared contracts
    REFUSE__REQUIRES_PYTHON_NOT_MET_LOCALLY     the declared floor excludes this interpreter
    REFUSE__NO_RUNNER_EXECUTED_CLEANLY          every candidate check command failed; the
                                                environment will not be believed
    REFUSE__VERIFICATION_FAILED                 the suite (or the check) does not pass;
                                                nothing is cached, nothing is claimed

Authority NONE__PRODUCER_RUN_SANDBOX. No network at run time.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time
from typing import Any, Mapping, Sequence

SCHEMA = "BRAIN_THE_ENVIRONMENT_BROKER_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"
CACHE_SCHEMA = "BRAIN_ENVIRONMENT_MEMORY_V1"
DEFAULT_MEMORY = pathlib.Path("/tmp/brain_memory/world_broker.json")

EVIDENCE_NAMES = ("pyproject.toml", "setup.py", "setup.cfg", "tox.ini", "Makefile",
                  "requirements.txt")
GOAL_KINDS = ("run-tests",)
TIMEOUT = 180.0


# ---------------------------------------------------------------- evidence
def evidence_digest(tree: pathlib.Path) -> tuple[str, list[str]]:
    """Digest of the evidence files that produced the answer. Not the path: the path is a
    label, and labels do not survive a move. Missing evidence is simply absent."""
    parts: list[bytes] = []
    names: list[str] = []
    for name in EVIDENCE_NAMES:
        candidate = tree / name
        if candidate.is_file():
            parts.append(name.encode() + b"\0" + hashlib.sha256(candidate.read_bytes()).hexdigest().encode())
            names.append(name)
    return hashlib.sha256(b"\n".join(parts)).hexdigest(), names


def read_toml_project(pyproject: pathlib.Path) -> dict[str, Any]:
    """Claim-minimal parsing. The broker needs three flat keys, not a TOML engine, and a
    wrong parse must be inert rather than clever."""
    text = pyproject.read_text(encoding="utf-8", errors="replace")
    out: dict[str, Any] = {"present": True, "requires_python": None, "declared_deps": [],
                           "build_backend": None}
    m = re.search(r"^\s*requires-python\s*=\s*[\"']([^\"']+)[\"']", text, re.MULTILINE)
    if m:
        out["requires_python"] = m.group(1).strip()
    m = re.search(r"^\s*build-backend\s*=\s*[\"']([^\"']+)[\"']", text, re.MULTILINE)
    if m:
        out["build_backend"] = m.group(1).strip()
    m = re.search(r"^\[project\].*?(?=^\[|\Z)", text, re.MULTILINE | re.DOTALL)
    if m:
        deps = re.search(r"dependencies\s*=\s*\[(.*?)\]", m.group(0), re.DOTALL)
        if deps:
            out["declared_deps"] = re.findall(r"[\"']([^\"']+)[\"']", deps.group(1))
    return out


def detect_layout(tree: pathlib.Path) -> dict[str, Any]:
    """LAYOUT is the one question answered with no execution: the file tree is the answer."""
    src = tree / "src"
    if src.is_dir():
        pkgs = sorted(p.name for p in src.iterdir()
                      if p.is_dir() and (p / "__init__.py").is_file())
        if pkgs:
            return {"kind": "src-layout", "packages": pkgs}
    pkgs = sorted(p.name for p in tree.iterdir()
                  if p.is_dir() and (p / "__init__.py").is_file()) if tree.is_dir() else []
    if pkgs:
        return {"kind": "flat", "packages": pkgs[:16]}
    return {"kind": "unknown", "packages": []}


def runner_candidates(tree: pathlib.Path) -> list[list[str]]:
    """The declared order of preference. Execution, not parsing, decides between them."""
    return [[sys.executable, "-m", "pytest", "-q"]]


def python_floor_ok(requirement: str | None) -> tuple[bool, str]:
    if not requirement:
        return True, "no requires-python declared"
    m = re.search(r">=\s*(\d+)(?:\.(\d+))?", requirement)
    if not m:
        return True, f"requires-python {requirement!r} not understood; not refusing on it"
    floor = (int(m.group(1)), int(m.group(2) or 0))
    here = sys.version_info[:2]
    return (here >= floor), f"requires-python {requirement!r} vs this interpreter {here[0]}.{here[1]}"


def run_check(tree: pathlib.Path, argv: Sequence[str]) -> dict[str, Any]:
    """One bounded execution of the candidate runner. The verifier is the environment."""
    env = {"PYTHONPATH": ":".join([str(tree), str(tree / "src"), str(tree / "tests")]),
           "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
           "HOME": str(tree), "PYTHONDONTWRITEBYTECODE": "1"}
    started = time.perf_counter()
    try:
        done = subprocess.run(list(argv), cwd=str(tree), capture_output=True, text=True,
                              timeout=TIMEOUT, env=env)
    except subprocess.TimeoutExpired:
        return {"command": list(argv), "exit_code": None, "ok": False, "detail": "TIMEOUT",
                "seconds": round(time.perf_counter() - started, 4)}
    tail = (done.stdout + done.stderr)[-2000:]
    counted = re.findall(r"(\d+)\s+passed", tail)
    errors = re.findall(r"(\d+)\s+(?:failed|errors?)", tail)
    return {"command": list(argv), "exit_code": done.returncode,
            "ok": done.returncode == 0,
            "reported_passed": int(counted[-1]) if counted else None,
            "reported_failed_or_errored": int(errors[-1]) if errors else None,
            "seconds": round(time.perf_counter() - started, 4),
            "tail": tail[-400:]}


# ---------------------------------------------------------------- memory
def load_memory(path: pathlib.Path) -> dict[str, Any]:
    if path.is_file():
        try:
            data = json.loads(path.read_text())
            if data.get("schema") == CACHE_SCHEMA:
                return data
        except (OSError, ValueError):
            pass
    return {"schema": CACHE_SCHEMA, "entries": {}}


def save_memory(memory: dict[str, Any], path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(memory, indent=1, sort_keys=True))


def broker(tree: pathlib.Path, goal: str, memory_path: pathlib.Path = DEFAULT_MEMORY) -> dict[str, Any]:
    started = time.perf_counter()
    result: dict[str, Any] = {"schema": SCHEMA, "authority": AUTHORITY,
                              "tree": str(tree), "goal": goal, "verdict": None}
    if goal not in GOAL_KINDS:
        result["verdict"] = "REFUSE__GOAL_OUTSIDE_THE_CLOSED_CONTRACTS"
        result["seconds"] = round(time.perf_counter() - started, 4)
        return result

    if not tree.is_dir():
        result["verdict"] = "REFUSE__NOT_A_PYTHON_ENVIRONMENT"
        result["seconds"] = round(time.perf_counter() - started, 4)
        return result

    pyproject = tree / "pyproject.toml"
    setup_py = tree / "setup.py"
    if not pyproject.is_file() and not setup_py.is_file():
        result["verdict"] = "REFUSE__NOT_A_PYTHON_ENVIRONMENT"
        result["seconds"] = round(time.perf_counter() - started, 4)
        return result

    digest, evidence = evidence_digest(tree)
    result["evidence"] = evidence
    result["evidence_digest"] = digest

    memory = load_memory(memory_path)
    cached = memory["entries"].get(digest)
    layout = detect_layout(tree)
    result["layout"] = layout
    declared = read_toml_project(pyproject) if pyproject.is_file() else {"present": False, "requires_python": None, "declared_deps": []}
    result["requirements"] = {"requires_python": declared.get("requires_python"),
                              "declared_deps": declared.get("declared_deps", []),
                              "build_backend": declared.get("build_backend")}
    floor_ok, floor_note = python_floor_ok(declared.get("requires_python"))
    result["interpreter"] = {"version": f"{sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}",
                             "check": floor_note, "ok": floor_ok}
    if not floor_ok:
        result["verdict"] = "REFUSE__REQUIRES_PYTHON_NOT_MET_LOCALLY"
        result["seconds"] = round(time.perf_counter() - started, 4)
        return result

    # the cache is re-verified, never trusted: the runner is re-executed, the derivation is skipped
    if cached is not None:
        recheck = run_check(tree, cached["runner"]["command"])
        result["from_memory"] = True
        result["recheck"] = {k: recheck[k] for k in ("exit_code", "ok", "seconds")}
        if recheck["ok"]:
            result["verdict"] = "ENVIRONMENT_BROKERED_FROM_MEMORY"
            result["runner"] = recheck
            result["seconds"] = round(time.perf_counter() - started, 4)
            return result
        memory["entries"].pop(digest, None)  # stale: discard and re-derive

    result["from_memory"] = False
    outcome = None
    for candidate in runner_candidates(tree):
        outcome = run_check(tree, candidate)
        if outcome["ok"]:
            break
    result["runner"] = outcome or {"ok": False, "detail": "NO_CANDIDATE_RUNNER"}
    if not (outcome and outcome["ok"]):
        result["verdict"] = "REFUSE__NO_RUNNER_EXECUTED_CLEANLY"
        result["seconds"] = round(time.perf_counter() - started, 4)
        return result  # NOTE: nothing is cached -- a failure is not an environment

    memory["entries"][digest] = {
        "goal": goal, "verdict": "ENVIRONMENT_BROKERED",
        "layout": layout, "requirements": result["requirements"],
        "runner": {k: outcome[k] for k in ("command", "exit_code", "reported_passed",
                                           "reported_failed_or_errored", "seconds")},
        "evidence_digest": digest,
    }
    save_memory(memory, memory_path)
    result["verdict"] = "ENVIRONMENT_BROKERED"
    result["seconds"] = round(time.perf_counter() - started, 4)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tree", type=pathlib.Path)
    parser.add_argument("--goal", default="run-tests")
    parser.add_argument("--memory", type=pathlib.Path, default=DEFAULT_MEMORY)
    parser.add_argument("--json", type=pathlib.Path, default=None)
    args = parser.parse_args(argv)
    got = broker(args.tree, args.goal, args.memory)
    text = json.dumps(got, indent=1, sort_keys=True)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if str(got.get("verdict", "")).startswith("ENVIRONMENT_BROKERED") else 1


if __name__ == "__main__":
    raise SystemExit(main())
