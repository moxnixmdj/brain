#!/usr/bin/env python3
"""BugsInPy blind-corpus run for software.diagnose_repair.v1 -- real projects, real
developer-fixed bugs, none of which shaped the repair templates.

BugsInPy (Widyasari et al. 2020, github.com/soarsmu/BugsInPy) is the Python analogue of
Defects4J: 501 bugs from 17 open-source projects, each with the buggy and fixed commit,
the developer's patch and the test(s) that fail on the bug and pass on the fix.  Unlike
QuixBugs, nothing here was used to derive the capability's templates: this is the blind
measurement.

Protocol per bug (every step is recorded, nothing is rounded up):

1. checkout -- the buggy commit is fetched shallowly from the project's GitHub repo;
   the project's import-time dependencies are installed once per project into a
   target directory (the corpus's pinned requirement files are for Python 3.6-3.8;
   this host runs whatever `python3` is, so a bug whose test cannot be reproduced
   here is NOT_APPLICABLE:ENV, counted and listed, never silently dropped);
2. oracle -- the corpus's failing test ids must FAIL on the buggy commit and PASS with
   the developer's patch applied, under THIS interpreter; other tests in the same
   test file(s) that fail even with the developer's patch are environment failures
   and are listed (the capability repairs whole test files, so such a bug is
   NOT_APPLICABLE:TEST_FILE_ENV_FAILURES until node-id selection exists);
3. repair -- software.diagnose_repair.v1 is given the project tree and the test
   file(s), nothing else (not the patch, not the failing test ids, not the fixed
   commit);
4. verdict -- the APR literature's: PLAUSIBLE when the capability's own gate passed;
   when the capability's full-suite gate failed, the gate's failing tests are re-run
   on the developer-fixed tree: failures that exist there too are environment
   failures and the verdict is PLAUSIBLE:GATE_FAILURES_PREEXISTING, said as such.
   CORRECT is judged against the developer's patch: SAME_LINES when the shipped
   `+`/`-` lines equal the developer's after whitespace normalisation, otherwise
   INSPECT (a semantically equivalent but textually different patch needs a human;
   the diff is in the row).  The scope filter (--max-changed-lines, default 4 --
   the capability's declared reach is at most two hunks) marks bigger developer
   patches OUT_OF_SCOPE; with --all they are attempted anyway.

Output: one JSON receipt with per-bug rows and a summary over ALL selected bugs, not
only the applicable ones.  The corpus is not vendored; pass its checkout with
--bugsinpy.  Network: github.com (project checkouts) and PyPI (dependencies).
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import shutil
import statistics
import subprocess
import sys
import time

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from canonical.runtime.bound_capabilities import software_diagnose_then_repair_v1 as dr  # noqa: E402

SCHEMA = "PROJECT_BRAIN_BUGSINPY_CORPUS_RUN_V1"

# import-time dependencies per project for the tests the corpus names (the corpus's own
# requirement files pin Python-3.6-era versions of everything including pytest)
PROJECT_DEPS: dict[str, list[str]] = {
    "thefuck": ["psutil", "pyte", "colorama", "six", "decorator", "mock", "pytest-mock", "pytest<8"],
    "youtube-dl": [],
    "tqdm": ["pynose"],
    "PySnooper": ["python_toolbox", "future"],
    "cookiecutter": ["jinja2", "click", "binaryornot", "pyyaml", "python-slugify", "requests", "jinja2-time", "poyo"],
    "httpie": ["requests", "pygments", "requests-toolbelt"],
}
TEST_ROOTS: dict[str, str] = {"youtube-dl": "test", "tqdm": "tqdm/tests"}


def _sh(cmd: list[str], cwd: pathlib.Path | None = None, timeout: int = 600, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)


def _read_info(path: pathlib.Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip('"')
    return out


def _test_ids(run_test: str, test_files: list[str]) -> list[str]:
    """pytest node ids from a BugsInPy run_test.sh (pytest or unittest spellings)."""
    ids: list[str] = []
    modules = {f[:-3].replace("/", "."): f for f in test_files if f.endswith(".py")}
    for line in run_test.splitlines():
        line = line.strip()
        if not line:
            continue
        toks = line.split()
        if "unittest" in toks:
            for t in toks[toks.index("unittest") + 1:]:
                if t.startswith("-"):
                    continue
                # test.test_utils.TestUtil.test_match_str -> test/test_utils.py::TestUtil::test_match_str
                mod = next((m for m in sorted(modules, key=len, reverse=True) if t == m or t.startswith(m + ".")), None)
                if mod:
                    rest = t[len(mod) + 1:]
                    ids.append(modules[mod] + ("::" + rest.replace(".", "::") if rest else ""))
                else:
                    parts = t.split(".")
                    ids.append("/".join(parts[:-2]) + ".py::" + "::".join(parts[-2:]))
        else:
            for t in toks[1:]:
                if "::" in t or t.endswith(".py"):
                    ids.append(t)
    return ids


def _patch_lines(diff_text: str) -> list[str]:
    return [re.sub(r"\s+", " ", ln[1:]).strip() for ln in diff_text.splitlines()
            if ln[:1] in "+-" and not ln.startswith(("+++", "---"))]


def _pytest_env(deps: list[pathlib.Path]) -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(str(d) for d in deps if d) + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = env.get("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "")
    return env


def _run_tests(tree: pathlib.Path, targets: list[str], env: dict[str, str], timeout: int = 300) -> dict:
    """pytest -q on targets; returns {rc, passed, failed:[ids], errors, summary}."""
    try:
        p = _sh([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-o", "addopts=", "--no-header", "-rfE", *targets],
                cwd=tree, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return {"rc": None, "failed": [], "timeout": True}
    failed = [ln.split(" ", 2)[1].split(" - ")[0] for ln in p.stdout.splitlines() if ln.startswith(("FAILED ", "ERROR "))]
    summary = next((ln for ln in reversed(p.stdout.splitlines()) if " in " in ln and ("passed" in ln or "failed" in ln or "error" in ln or "no tests" in ln)), "")
    return {"rc": p.returncode, "failed": failed, "summary": summary.strip("= "), "tail": (p.stdout + p.stderr)[-600:] if p.returncode != 0 else ""}


def _checkout(project_url: str, sha: str, dest: pathlib.Path, fixed_sha: str = "", test_files: list[str] | None = None) -> str | None:
    """Buggy commit, plus the fixed commit's versions of the named test files -- the
    corpus's own protocol (bugsinpy-checkout): the failing test is often added or
    changed by the fixing commit, so the buggy tree alone does not contain it."""
    shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True)
    cmds = [["git", "init", "-q"], ["git", "remote", "add", "origin", project_url],
            ["git", "fetch", "-q", "--depth", "1", "origin", sha], ["git", "checkout", "-q", "FETCH_HEAD"]]
    if fixed_sha and test_files:
        cmds += [["git", "fetch", "-q", "--depth", "1", "origin", fixed_sha],
                 ["git", "checkout", "-q", "FETCH_HEAD", "--", *test_files]]
    for cmd in cmds:
        p = _sh(cmd, cwd=dest, timeout=600)
        if p.returncode != 0:
            return (p.stderr or p.stdout)[-300:]
    p = _sh(["git", "add", "-A"], cwd=dest)
    return None


def _install_deps(project: str, target: pathlib.Path) -> str | None:
    pkgs = PROJECT_DEPS.get(project, [])
    if not pkgs or (target / ".done").exists():
        return None
    target.mkdir(parents=True, exist_ok=True)
    p = _sh([sys.executable, "-m", "pip", "install", "-q", "--target", str(target), *pkgs], timeout=900)
    if p.returncode != 0:
        return (p.stderr or p.stdout)[-400:]
    (target / ".done").write_text("ok")
    return None


def run_bug(project: str, bug: str, bip: pathlib.Path, work: pathlib.Path, deps: list[pathlib.Path], deadline: int,
            max_changed: int, attempt_all: bool, extra_args: dict, precheck_only: bool = False) -> dict:
    bdir = bip / "projects" / project / "bugs" / bug
    info = _read_info(bdir / "bug.info")
    pinfo = _read_info(bip / "projects" / project / "project.info")
    patch = (bdir / "bug_patch.txt").read_text(encoding="utf-8", errors="replace")
    corpus_test_files = [t.strip() for t in info.get("test_file", "").split(";") if t.strip()]
    test_ids = _test_ids((bdir / "run_test.sh").read_text(encoding="utf-8", errors="replace"), corpus_test_files)
    test_files = sorted({t.split("::", 1)[0] for t in test_ids})
    dev_lines = _patch_lines(patch)
    dev_files = sorted({ln[6:] for ln in patch.splitlines() if ln.startswith("+++ b/")})
    row: dict = {"project": project, "bug": bug, "buggy_commit": info.get("buggy_commit_id"), "test_ids": test_ids,
                 "test_files": test_files, "dev_patch_files": dev_files, "dev_patch_changed_lines": len(dev_lines),
                 "dev_patch": dev_lines[:12]}
    in_scope = len(dev_files) == 1 and len(dev_lines) <= max_changed
    row["in_scope"] = in_scope
    if not in_scope and not attempt_all:
        row["status"] = "OUT_OF_SCOPE:" + (str(len(dev_files)) + "_FILES" if len(dev_files) != 1 else str(len(dev_lines)) + "_CHANGED_LINES")
        return row
    root = work / project / bug
    shutil.rmtree(root, ignore_errors=True)
    tree = root / "proj"
    err = _checkout(pinfo.get("github_url", ""), info.get("buggy_commit_id", ""), tree,
                    fixed_sha=info.get("fixed_commit_id", ""), test_files=corpus_test_files)
    if err:
        row["status"] = "NOT_APPLICABLE:CHECKOUT:" + err.strip()[-120:]
        return row
    env = _pytest_env(deps)
    # oracle on this interpreter
    t0 = time.perf_counter()
    buggy = _run_tests(tree, test_ids, env)
    if not buggy["failed"]:
        row["status"] = "NOT_APPLICABLE:ENV:FAILING_TESTS_DO_NOT_FAIL_HERE"
        row["oracle"] = {"buggy": buggy}
        shutil.rmtree(root, ignore_errors=True)
        return row
    fixed = root / "fixed"
    shutil.copytree(tree, fixed, symlinks=True)
    (root / "dev.patch").write_text(patch, encoding="utf-8")
    ap = _sh(["git", "apply", str(root / "dev.patch")], cwd=fixed)
    if ap.returncode != 0:
        row["status"] = "NOT_APPLICABLE:DEV_PATCH_DOES_NOT_APPLY"
        shutil.rmtree(root, ignore_errors=True)
        return row
    fixed_named = _run_tests(fixed, test_ids, env)
    if fixed_named["failed"] or fixed_named.get("rc") not in (0,):
        row["status"] = "NOT_APPLICABLE:ENV:FAILING_TESTS_DO_NOT_PASS_WITH_DEV_FIX"
        row["oracle"] = {"buggy": buggy, "fixed_named": fixed_named}
        shutil.rmtree(root, ignore_errors=True)
        return row
    fixed_files = _run_tests(fixed, test_files, env)
    row["oracle"] = {"buggy_failing": buggy["failed"], "fixed_named": fixed_named["summary"],
                     "fixed_test_files": fixed_files["summary"], "env_failures_in_test_files": fixed_files["failed"][:10],
                     "seconds": round(time.perf_counter() - t0, 1)}
    if fixed_files["failed"]:
        row["status"] = "NOT_APPLICABLE:TEST_FILE_ENV_FAILURES:" + str(len(fixed_files["failed"]))
        shutil.rmtree(root, ignore_errors=True)
        return row
    if precheck_only:
        row["status"] = "APPLICABLE"
        shutil.rmtree(root, ignore_errors=True)
        return row
    # repair: the capability sees the tree and the test files only
    t0 = time.perf_counter()
    args = {"source_root": "proj", "test_paths": ["proj/" + t for t in test_files], "output_path": "out/dr.json",
            "python_executable": sys.executable, "deadline_s": deadline, "confine": "auto", **extra_args}
    saved = os.environ.get("PYTHONPATH")
    os.environ["PYTHONPATH"] = env["PYTHONPATH"]
    try:
        result = dr.run(args, root)
    except Exception as exc:  # noqa: BLE001 - a crash is a row, not the end of the run
        row["status"] = "RUNNER_EXCEPTION:" + type(exc).__name__ + ":" + str(exc)[:200]
        row["seconds"] = round(time.perf_counter() - t0, 1)
        return row
    finally:
        if saved is None:
            os.environ.pop("PYTHONPATH", None)
        else:
            os.environ["PYTHONPATH"] = saved
    row["seconds"] = round(time.perf_counter() - t0, 1)
    row["status"] = result["status"]
    row["review"] = result.get("review")
    try:
        art = json.loads((root / "out" / "dr.json").read_text(encoding="utf-8"))
        row["steps"] = [(s.get("step"), s.get("seconds")) for s in art["steps"]]
        search = next((s for s in art["steps"] if s.get("step") == "patch_search"), {})
        loc = next((s for s in art["steps"] if s.get("step") == "localize"), {})
        rep = next((s for s in art["steps"] if s.get("step") == "reproduce"), {})
        gate = next((s for s in art["steps"] if s.get("step") == "full_suite_gate"), {})
        row["reproduce"] = {k: rep.get(k) for k in ("failing_test_count", "failing_tests", "test_count") if k in rep}
        row["target_basis"] = loc.get("target_basis")
        row["target_path"] = result.get("target_path")
        row["target_is_dev_file"] = result.get("target_path") in dev_files
        row["judge"] = search.get("judge")
        row["tested_candidates"] = search.get("tested_candidate_count")
        row["winning_mutation"] = search.get("winning_mutation")
        row["stop_reason"] = search.get("stop_reason")
        row["gate"] = {k: gate.get(k) for k in ("gate", "tests_discovered", "tests_failed", "failing_tests") if k in gate}
    except Exception as exc:  # noqa: BLE001
        row["artifact_error"] = type(exc).__name__
    if result.get("diff_path"):
        diff = (root / result["diff_path"]).read_text(encoding="utf-8")
        row["diff"] = _patch_lines(diff)
        row["same_lines_as_dev"] = sorted(row["diff"]) == sorted(dev_lines)
    # verdict
    status = str(result["status"])
    if status == "VERIFIED_PATCH":
        row["verdict"] = "PLAUSIBLE"
    elif status.startswith("PATCH_FAILS_FULL_SUITE") and row.get("gate", {}).get("failing_tests"):
        again = _run_tests(fixed, row["gate"]["failing_tests"][:40], env)
        preexisting = set(again["failed"])
        novel = [t for t in row["gate"]["failing_tests"][:40] if t not in preexisting]
        row["gate_failures_on_dev_fixed_tree"] = sorted(preexisting)[:20]
        row["verdict"] = "PLAUSIBLE:GATE_FAILURES_PREEXISTING" if not novel else "NOT_PLAUSIBLE:REGRESSES:" + str(novel[:5])
    else:
        row["verdict"] = "NOT_PLAUSIBLE"
    if row["verdict"].startswith("PLAUSIBLE"):
        row["correctness"] = "SAME_LINES_AS_DEV" if row.get("same_lines_as_dev") else "INSPECT"
    keep = work / "artifacts"
    keep.mkdir(parents=True, exist_ok=True)
    if (root / "out" / "dr.json").is_file():
        shutil.copy2(root / "out" / "dr.json", keep / (project + "_" + bug + "_dr.json"))
    if os.environ.get("BIP_KEEP_TREES") and not row["verdict"].startswith("PLAUSIBLE"):
        return row
    shutil.rmtree(root, ignore_errors=True)
    return row


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--bugsinpy", required=True, help="path to a BugsInPy checkout")
    ap.add_argument("--projects", default="thefuck,youtube-dl,tqdm,PySnooper")
    ap.add_argument("--only", default="", help="comma-separated project:bug ids")
    ap.add_argument("--out", default=str(REPO / "canonical/astra_runtime/evidence/ASTRA-VERIFY-DIAGNOSE-REPAIR-001__BUGSINPY_CORPUS.json"))
    ap.add_argument("--work", default="/tmp/bugsinpy_work")
    ap.add_argument("--deadline", type=int, default=300)
    ap.add_argument("--max-changed-lines", type=int, default=4)
    ap.add_argument("--all", action="store_true", help="attempt out-of-scope bugs too")
    ap.add_argument("--precheck-only", action="store_true", help="oracle/env check only; no repair")
    ap.add_argument("--arg", action="append", default=[], help="extra capability arg as key=value (json value)")
    ns = ap.parse_args(argv)
    bip = pathlib.Path(ns.bugsinpy).resolve()
    work = pathlib.Path(ns.work).resolve()
    work.mkdir(parents=True, exist_ok=True)
    extra: dict = {}
    for kv in ns.arg:
        k, v = kv.split("=", 1)
        try:
            extra[k] = json.loads(v)
        except ValueError:
            extra[k] = v
    only = {x.strip() for x in ns.only.split(",") if x.strip()}
    brain_deps = pathlib.Path(os.environ.get("BRAIN_DEPS", "/tmp/brain-onboarding-deps"))
    rows: list[dict] = []
    t_all = time.perf_counter()
    for project in [p.strip() for p in ns.projects.split(",") if p.strip()]:
        bugs = sorted((bip / "projects" / project / "bugs").iterdir(), key=lambda p: int(p.name))
        dep_dir = work / project / "deps"
        err = _install_deps(project, dep_dir)
        if err:
            rows.append({"project": project, "status": "NOT_APPLICABLE:DEPS:" + err[-200:]})
            continue
        deps = [dep_dir] if PROJECT_DEPS.get(project) else []
        deps.append(brain_deps)
        for b in bugs:
            if only and (project + ":" + b.name) not in only:
                continue
            row = run_bug(project, b.name, bip, work, deps, ns.deadline, ns.max_changed_lines, ns.all, extra,
                          precheck_only=ns.precheck_only)
            rows.append(row)
            print(project, b.name, row.get("status"), row.get("verdict", ""), row.get("seconds", ""), flush=True)
    attempted = [r for r in rows if r.get("verdict")]
    plausible = [r for r in attempted if str(r["verdict"]).startswith("PLAUSIBLE")]
    by_status: dict[str, int] = {}
    for r in rows:
        key = str(r.get("status", "")).split(":")[0] if not str(r.get("status", "")).startswith(("NOT_APPLICABLE", "OUT_OF_SCOPE", "OPEN")) \
            else ":".join(str(r.get("status")).split(":")[:2])
        by_status[key] = by_status.get(key, 0) + 1
    secs = [r["seconds"] for r in attempted if r.get("seconds")]
    summary = {"bugs_selected": len(rows), "in_scope": sum(1 for r in rows if r.get("in_scope")),
               "attempted": len(attempted), "plausible": len(plausible),
               "plausible_gate_clean": sum(1 for r in plausible if r["verdict"] == "PLAUSIBLE"),
               "same_lines_as_dev": sum(1 for r in plausible if r.get("correctness") == "SAME_LINES_AS_DEV"),
               "inspect": sum(1 for r in plausible if r.get("correctness") == "INSPECT"),
               "by_status": dict(sorted(by_status.items())),
               "target_is_dev_file": sum(1 for r in attempted if r.get("target_is_dev_file")),
               "seconds_median": round(statistics.median(secs), 1) if secs else None, "seconds_max": max(secs) if secs else None,
               "seconds_total": round(time.perf_counter() - t_all, 1), "host_cpus": os.cpu_count(), "python": sys.version.split()[0],
               "corpus": "BugsInPy " + _git_head(bip), "capability": dr.CAPABILITY_ID,
               "blind": "no bug here was used to derive the capability's templates or synthesis",
               "verdict_law": "PLAUSIBLE = the capability's own gate passed (or its only gate failures also fail with the developer's fix: environment); CORRECT needs a human unless the changed lines equal the developer's; neither is proof"}
    receipt = {"schema": SCHEMA, "summary": summary, "bugs": rows}
    out = pathlib.Path(ns.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=1, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=1))
    return 0


def _git_head(path: pathlib.Path) -> str:
    p = _sh(["git", "rev-parse", "--short", "HEAD"], cwd=path)
    return p.stdout.strip() if p.returncode == 0 else "?"


if __name__ == "__main__":
    raise SystemExit(main())
