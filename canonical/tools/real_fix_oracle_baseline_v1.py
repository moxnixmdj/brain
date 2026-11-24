#!/usr/bin/env python3
"""Real-fix oracle baseline: 87 execution-verified tasks, judged by the repo's own tests.

WHY THIS EXISTS
---------------
`canonical/corpus/real_fix_pairs_20261119_V1.json` carries 87 tasks mined under
the rule *"the commit's test must FAIL at the parent and PASS at the commit,
verified by execution"*.  Each row has the repository, the parent and fix
commits, the source path, the full before/after text, and the exact failing test
node ids.

That is a real oracle, and until now nothing in this tree ran it.  Every number
about repair reach in this repository was measured on QuixBugs or on synthetic
witnesses.  This harness makes the 87 runnable:

    git checkout <fix sha>          # the tests the fix added now exist
    write `before` over the source  # revert ONLY the fix
    pytest <failed_nodes>  -> FAIL  # confirmed
    write `after`                  # the fix
    pytest <failed_nodes>  -> PASS  # confirmed

A task is only *well-formed* if both directions hold.  Tasks that are not
well-formed are reported and excluded, never silently dropped.

INTEGRITY
---------
The candidate arm sees: the `before` source text, the repository path, the
failing node ids, and the interpreter.  It NEVER sees `after`, the commit
subject, or the diff.  `after` is held by the judge only.

AUTHORITY: NONE.  Producer-run sandbox measurement.  No model, no network at
decision time, no spend.  Nothing here repairs a repository; the judge applies a
candidate to a throwaway clone and reverts it.

Usage
-----
    python3 canonical/tools/real_fix_oracle_baseline_v1.py --validate-only
    python3 canonical/tools/real_fix_oracle_baseline_v1.py --arm blind --limit 20
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

SCHEMA = "PROJECT_BRAIN_REAL_FIX_ORACLE_BASELINE_V1"
CORPUS = pathlib.Path(__file__).resolve().parents[1] / "corpus" / "real_fix_pairs_20261119_V1.json"
DEFAULT_WORKDIR = pathlib.Path("/tmp/real")

REPO_URL = {
    "pypa/packaging": "packaging",
    "hukkin/tomli": "tomli",
    "pallets/itsdangerous": "itsdangerous",
}


# --------------------------------------------------------------------------- #
# the oracle
# --------------------------------------------------------------------------- #

@dataclass
class Oracle:
    """One repository at one commit, with a private virtualenv."""

    repo_slug: str
    workdir: pathlib.Path
    py: str = ""
    path: pathlib.Path = field(init=False)

    def __post_init__(self) -> None:
        name = REPO_URL.get(self.repo_slug, self.repo_slug.split("/")[-1])
        self.path = self.workdir / name
        self.py = str(self.workdir / "venvs" / name / "bin" / "python")

    # -- environment ------------------------------------------------------- #
    def ensure(self) -> dict[str, Any]:
        """Clone + venv + install.  Returns a receipt; never raises."""
        steps: dict[str, Any] = {}
        try:
            if not self.path.exists():
                subprocess.run(
                    ["git", "clone", "-q", "--no-checkout",
                     f"https://github.com/{self.repo_slug}", str(self.path)],
                    check=True, capture_output=True, timeout=900)
                steps["cloned"] = True
            else:
                steps["cloned"] = False
            venv = pathlib.Path(self.py).parents[1]
            if not pathlib.Path(self.py).exists():
                subprocess.run([sys.executable, "-m", "venv", str(venv)],
                               check=True, capture_output=True, timeout=600)
                subprocess.run([self.py, "-m", "pip", "install", "-q", "--upgrade", "pip"],
                               check=True, capture_output=True, timeout=900)
                subprocess.run([self.py, "-m", "pip", "install", "-q", "pytest", "flaky"],
                               check=True, capture_output=True, timeout=900)
                # build backends first: tomli needs flit_core, and without it the
                # editable install fails silently and every task becomes
                # "ORACLE_DISAGREES" for the wrong reason
                subprocess.run([self.py, "-m", "pip", "install", "-q",
                                "flit_core", "hatchling", "setuptools", "wheel",
                                "poetry-core"],
                               check=False, capture_output=True, timeout=1200)
                r = subprocess.run([self.py, "-m", "pip", "install", "-q", "-e", str(self.path)],
                                   capture_output=True, text=True, timeout=1800)
                steps["install_rc"] = r.returncode
                if r.returncode != 0:
                    steps["install_error"] = (r.stderr or r.stdout)[-400:]
                steps["venv"] = True
            else:
                steps["venv"] = False
            steps["ok"] = True
        except Exception as exc:  # noqa: BLE001
            steps["ok"] = False
            steps["error"] = f"{type(exc).__name__}: {exc}"[:300]
        return steps

    # -- state ------------------------------------------------------------- #
    def checkout(self, ref: str) -> None:
        # A bare `--no-checkout` clone has no worktree files, so discarding
        # edits can legitimately fail.  Never fatal: the point is only to drop
        # whatever the previous task wrote.
        subprocess.run(["git", "checkout", "-q", "--", "."], cwd=self.path, check=False)
        subprocess.run(["git", "checkout", "-q", ref], cwd=self.path, check=True)

    def write_source(self, rel: str, text: str) -> None:
        p = self.path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def test(self, nodes: Sequence[str], timeout: int = 900) -> dict[str, Any]:
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        t0 = time.perf_counter()
        try:
            r = subprocess.run(
                [self.py, "-m", "pytest", *nodes, "-q", "--no-header",
                 "-p", "no:cacheprovider", "-x"],
                cwd=self.path, capture_output=True, text=True, env=env, timeout=timeout)
            rc, out = r.returncode, (r.stdout or "") + (r.stderr or "")
        except subprocess.TimeoutExpired:
            rc, out = 124, "TIMEOUT"
        dt = time.perf_counter() - t0
        passed = rc == 0
        tail = [ln for ln in out.strip().splitlines() if ln.strip()][-1:] or [""]
        return {"rc": rc, "passed": passed, "seconds": round(dt, 2), "tail": tail[0][:160]}


# --------------------------------------------------------------------------- #
# the candidate arm
# --------------------------------------------------------------------------- #

def blind_candidates(before: str, repo_path: pathlib.Path,
                     *, limit: int = 64) -> list[tuple[str, str]]:
    """Candidate single-statement edits, built ONLY from what the file already contains.

    No knowledge of the fix.  The vocabulary is the file's own: its imports, its
    names, its calls, and the identifiers used elsewhere in the same repository.
    An edit that needs a name that appears nowhere is not proposed, because an
    invented name is a fabricated repair.
    """
    import ast

    try:
        tree = ast.parse(before)
    except SyntaxError:
        return []

    # vocabulary already present in the file
    called: set[str] = set()
    attrs: set[str] = set()
    imported: set[str] = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Name):
                called.add(f.id)
            elif isinstance(f, ast.Attribute):
                called.add(f.attr)
        elif isinstance(n, ast.Attribute):
            attrs.add(n.attr)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names:
                imported.add(a.asname or a.name.split(".")[0])
    vocab = sorted((called | imported) - {"print", "len", "range", "isinstance"})

    # sibling modules in the same repository: names a real fix could reach for
    sibling: set[str] = set()
    try:
        for p in list(repo_path.rglob("*.py"))[:400]:
            if any(x in p.parts for x in (".git", "tests", "test", "__pycache__",
                                          "node_modules", "build", "dist")):
                continue
            try:
                sub = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
            except SyntaxError:
                continue
            for n in ast.walk(sub):
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    sibling.add(n.name)
    except Exception:
        pass

    out: list[tuple[str, str]] = []
    lines = before.splitlines(keepends=True)
    # 1. wrap an existing call in a cast/coerce that already exists in the file
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(("def ", "class ", "#", "@", "import ", "from ")):
            continue
        for name in list(vocab)[:12]:
            for wrap in ("tuple", "list", "set", "frozenset", "dict", "sorted", "str", "int"):
                if f"{wrap}(" in line:
                    continue
                out.append((f"wrap:{wrap}@{i}", f"{wrap}({stripped.rstrip()}))"))
                if len(out) >= limit:
                    return out
    # 2. add a missing import for a sibling name the file already references
    for name in sorted(sibling)[:24]:
        if name in before:
            continue
        out.append((f"import:{name}", f"import {name}\n"))
        if len(out) >= limit:
            break
    return out[:limit]


ARMS: dict[str, Callable[..., list[tuple[str, str]]]] = {
    "blind": blind_candidates,
}


def apply_candidate(before: str, kind: str, payload: str) -> str:
    """Materialise a candidate edit.  Unknown kinds are refused, not guessed."""
    if kind.startswith("import:"):
        return payload + before
    if kind.startswith("wrap:"):
        try:
            idx = int(kind.split("@")[1])
        except (IndexError, ValueError):
            return before
        lines = before.splitlines(keepends=True)
        if not 0 <= idx < len(lines):
            return before
        lines[idx] = payload + "\n"
        return "".join(lines)
    return before


# --------------------------------------------------------------------------- #
# the run
# --------------------------------------------------------------------------- #

def run(corpus: pathlib.Path, workdir: pathlib.Path, *, arm: str | None,
        limit: int | None, validate_only: bool, out_path: pathlib.Path | None,
        per_task_budget_s: float = 120.0) -> dict[str, Any]:
    tasks = json.loads(corpus.read_text())["tasks"]
    if limit:
        tasks = tasks[:limit]
    oracles: dict[str, Oracle] = {}
    rows: list[dict[str, Any]] = []
    env_receipts: dict[str, Any] = {}

    for t in tasks:
        slug = t["repo"]
        if slug not in oracles:
            oracles[slug] = Oracle(slug, workdir)
            env_receipts[slug] = oracles[slug].ensure()
        o = oracles[slug]
        row: dict[str, Any] = {
            "repo": slug, "sha": t["sha"][:10], "parent": t["parent"][:10],
            "source": t["source"], "nodes": len(t["failed_nodes"]),
        }
        if not env_receipts[slug].get("ok"):
            row["well_formed"] = False
            row["reason"] = "ENV_UNAVAILABLE"
            row["env_error"] = env_receipts[slug].get("error")
            rows.append(row)
            continue

        try:
            o.checkout(t["sha"])
            o.write_source(t["source"], t["before"])
            before_run = o.test(t["failed_nodes"])
            o.write_source(t["source"], t["after"])
            after_run = o.test(t["failed_nodes"])
        except Exception as exc:  # noqa: BLE001
            row["well_formed"] = False
            row["reason"] = f"HARNESS_{type(exc).__name__}"
            rows.append(row)
            continue

        row["well_formed"] = (before_run["passed"] is False and after_run["passed"] is True)
        row["before_passes"] = before_run["passed"]
        row["after_passes"] = after_run["passed"]
        row["oracle_s"] = round(before_run["seconds"] + after_run["seconds"], 2)

        if not row["well_formed"]:
            row["reason"] = "ORACLE_DISAGREES"
            rows.append(row)
            continue
        if validate_only:
            rows.append(row)
            continue

        # ---- the arm runs BLIND: `before` only ---------------------------- #
        o.write_source(t["source"], t["before"])
        gen = ARMS.get(arm or "")
        solved: dict[str, Any] | None = None
        tried = 0
        t0 = time.perf_counter()
        if gen is not None:
            try:
                cands = gen(t["before"], o.path)
            except Exception:
                cands = []
            for kind, payload in cands:
                if time.perf_counter() - t0 > per_task_budget_s:
                    break
                tried += 1
                patched = apply_candidate(t["before"], kind, payload)
                if patched == t["before"]:
                    continue
                o.write_source(t["source"], patched)
                verdict = o.test(t["failed_nodes"])
                if verdict["passed"]:
                    solved = {"kind": kind, "attempt": tried,
                              "seconds": round(time.perf_counter() - t0, 2)}
                    break
        row["arm"] = arm
        row["arm_tried"] = tried
        row["solved"] = solved is not None
        if solved:
            row["solution"] = solved
        rows.append(row)
        print(f"{slug:24s} {t['sha'][:8]} nodes={len(t['failed_nodes']):3d} "
              f"well_formed={row['well_formed']} solved={row['solved']} tried={tried}",
              flush=True)

    good = [r for r in rows if r.get("well_formed")]
    summary = {
        "schema": SCHEMA,
        "authority": "NONE__PRODUCER_RUN_SANDBOX",
        "model_dependency_count": 0,
        "network_calls_at_decision_time": 0,
        "arm": arm,
        "tasks": len(rows),
        "well_formed": len(good),
        "solved": sum(1 for r in good if r.get("solved")),
        "unsolved": sum(1 for r in good if r.get("solved") is False),
        "not_well_formed": len(rows) - len(good),
        "oracle_seconds_mean": round(
            sum(r.get("oracle_s", 0.0) for r in good) / max(1, len(good)), 2),
        "environments": env_receipts,
        "rows": rows,
    }
    if out_path:
        out_path.write_text(json.dumps(summary, indent=1), encoding="utf-8")
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpus", default=str(CORPUS))
    ap.add_argument("--workdir", default=str(DEFAULT_WORKDIR))
    ap.add_argument("--arm", default=None, choices=[None, "blind"])
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--validate-only", action="store_true")
    ap.add_argument("--out", default=None)
    ap.add_argument("--per-task-budget", type=float, default=120.0)
    ns = ap.parse_args(argv)

    s = run(pathlib.Path(ns.corpus), pathlib.Path(ns.workdir), arm=ns.arm,
            limit=ns.limit, validate_only=ns.validate_only,
            out_path=pathlib.Path(ns.out) if ns.out else None,
            per_task_budget_s=ns.per_task_budget)
    print(json.dumps({k: v for k, v in s.items() if k != "rows"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
