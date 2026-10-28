# PROJECT_BRAIN
"""software.diagnose_then_repair.v1 -- the engineering loop from the failure
forward, wired from parts the Brain already owned.

Measured before this adapter (2026-10-28): the registry had a dynamic fault
localizer, a test-guided patch search and an anchored full-suite gate, and no
capability that connected them.  Repair started at "fix"; nothing took a
failing test as its input, reproduced it, decided WHERE to look, and verified
the result against the whole tree.  This does, in order, each step evidence
for the next:

  1. REPRODUCE   run the failing tests once in a scratch copy of the tree --
                 confined (user+mount namespace, chroot, no network) when the
                 host can confine, and the receipt says which.  A suite that
                 passes here is a refusal: there is nothing to repair.
  2. DIAGNOSE    parse the failing tracebacks (frames under the tree, test
                 files excluded) and run python.fault.localize.dynamic.dataflow.v1
                 (Ochiai over call traces); the target file is the caller's
                 ``source_path`` or the top-ranked file both witnesses agree on,
                 else the top localized file, else the top traceback file.
                 No witness -> NO_LOCALIZED_SOURCE, no guessing.
  3. REPAIR      patch_candidate_search_v1: template edits (operator, compare,
                 bool, operand-order, not-toggle, constant and string
                 replacements) ordered spectrum-first by the lines the
                 localizer and the traceback named, tested in parallel on
                 per-worker copies of the scratch tree under the same pytest
                 command (confined when the host can) that reproduced the
                 failure; the first green candidate is replayed twice.  The
                 user's tree is never touched.  No verified candidate -> OPEN,
                 the ledger says how many were tried and why it stopped.
  4. VERIFY      re-anchor the diff to the tree and run
                 python.repo.diff_apply_full_testgate.v1: scratch copy, git
                 apply --check, the WHOLE discovered suite under pytest.  Only
                 gate PASS makes ``verified`` true.

Budget: ``deadline_s`` (default 600) is end-to-end; every step inherits the
remaining time.  Laws: fail closed on every missing input and every step
refusal; the anchor tree is hashed before and after and any drift fails the
run; artifacts carry no wall-clock fields except measured step seconds.

Inputs (repo-confined):
  source_root        tree to repair (read-only; patches are proposed, not applied)
  test_paths         failing test files, repo-relative (>= 1)
  source_path        optional: the file to patch (skips the target decision)
  output_path        ledger artifact
  diff_path          optional: where the verified diff is written
                     (default <output>.diff)
  python_executable  interpreter for pytest (default: this one)
  deadline_s         end-to-end budget in seconds (default 600)
  max_candidates     patch-search bound (default 2000)
  workers            parallel candidate workers (default: cpu count, max 8)
  confine            "auto" (default) | "required" | "off"

result_fields: adapter, status, verified, target_path, confined, steps,
diff_path, diff_sha256, gate, tests_discovered, tests_failed, seconds,
output_path, output_sha256, output_verified.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time
from typing import Any

from canonical.runtime import confine_v1
from canonical.runtime.bound_capabilities import python_dynamic_fault_localizer_v1 as localizer
from canonical.runtime.bound_capabilities import python_repo_diff_apply_full_testgate as full_gate
from canonical.runtime import patch_candidate_search_v1 as candidates_v1
from canonical.runtime import patch_differential_witness_v1 as witness_v1

SCHEMA = "PROJECT_BRAIN_SOFTWARE_DIAGNOSE_THEN_REPAIR_V1"
CAPABILITY_ID = "software.diagnose_then_repair.v1"
ADAPTER = "software_diagnose_then_repair_v1"
OWNED_MARKER = ".brain_owned_output_v1"
_SKIP = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "node_modules"}
_FRAME = re.compile(r"^(?P<path>[^\s:][^:\n]*\.py):(?P<line>\d+):")
_TESTNAME = lambda n: n.startswith("test_") or n.endswith("_test.py")  # noqa: E731


class DiagnoseRepairRefusal(RuntimeError):
    pass


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _safe(repo: pathlib.Path, rel: str, must_exist: bool = False) -> pathlib.Path:
    if not isinstance(rel, str) or not rel.strip():
        raise DiagnoseRepairRefusal("MISSING_OR_INVALID_PATH_ARGUMENT")
    p = (repo / rel).resolve()
    if p != repo and repo not in p.parents:
        raise DiagnoseRepairRefusal("PATH_ESCAPE:" + rel)
    if must_exist and not p.exists():
        raise DiagnoseRepairRefusal("PATH_MISSING:" + rel)
    return p


def _rel(repo: pathlib.Path, p: pathlib.Path) -> str:
    return p.relative_to(repo).as_posix()


def _tree_hash(root: pathlib.Path) -> str:
    rows = []
    for p in sorted(root.rglob("*")):
        if p.is_file() and not any(part in _SKIP for part in p.relative_to(root).parts):
            rows.append([p.relative_to(root).as_posix(), _sha(p.read_bytes())])
    return _sha(json.dumps(rows, separators=(",", ":")).encode("utf-8"))


def _owned_scratch(repo: pathlib.Path, where: pathlib.Path) -> pathlib.Path:
    """(Re)create a scratch dir only if it is ours; never delete foreign files."""
    if where.exists():
        if not (where / OWNED_MARKER).is_file():
            raise DiagnoseRepairRefusal("SCRATCH_DIR_NOT_OWNED_BY_BRAIN:" + _rel(repo, where))
        shutil.rmtree(where)
    where.mkdir(parents=True)
    (where / OWNED_MARKER).write_text(CAPABILITY_ID + "\n", encoding="utf-8")
    return where


def _copy_tree(src: pathlib.Path, dst: pathlib.Path) -> None:
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(*_SKIP), dirs_exist_ok=True)


def _site_dirs() -> tuple[str, ...]:
    out = []
    for d in sys.path:
        if d and os.path.isdir(d) and not d.startswith(("/usr", "/bin", "/lib")):
            out.append(os.path.realpath(d))
    for extra in (os.environ.get("PYTHONPATH") or "").split(os.pathsep):
        if extra and os.path.isdir(extra):
            out.append(os.path.realpath(extra))
    return tuple(sorted(set(out)))


_SUMMARY = re.compile(r"^(?:=+ )?(?P<body>(?:\d+ (?:failed|errors?|passed|skipped|xfailed|xpassed|warnings?|deselected)(?:, )?)+) in [0-9.]+s(?: \([^)]*\))?(?: =+)?$")


def _summary_counts(log: str) -> dict[str, int] | None:
    """Counts from pytest's final summary line; None when pytest never got there."""
    for line in reversed(log.splitlines()):
        m = _SUMMARY.match(line.strip())
        if not m:
            continue
        out = {"failed": 0, "error": 0, "passed": 0}
        for n, word in re.findall(r"(\d+) (failed|errors?|passed)", m.group("body")):
            out["error" if word.startswith("error") else word] += int(n)
        return out
    return None


def plugin_trim(tree: pathlib.Path, tests_rel: list[str]) -> list[str]:
    """pytest ``-p no:<plugin>`` flags for plugins the named tests provably do not use.

    Measured (pytest 9.2, 2-cpu host): a one-test file takes 0.20 s to run and
    0.75 s with the Hypothesis plugin autoloaded -- 0.55 s per candidate, paid
    thousands of times in a search, by tests that never import it.  A plugin is
    trimmed only when NO test file named and NO conftest.py in the tree mentions
    its import name; anything else keeps the default plugin set.
    """
    texts = []
    for rel in tests_rel:
        try:
            texts.append((tree / rel).read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            return []
    for conf in tree.rglob("conftest.py"):
        if not any(part in _SKIP for part in conf.relative_to(tree).parts):
            try:
                texts.append(conf.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError):
                return []
    for ini in ("pytest.ini", "pyproject.toml", "setup.cfg", "tox.ini"):
        if (tree / ini).is_file():
            try:
                texts.append((tree / ini).read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError):
                return []
    blob = "\n".join(texts)
    flags: list[str] = []
    for module, plugin in (("hypothesis", "hypothesispytest"),):
        if module not in blob:
            flags += ["-p", "no:" + plugin]
    return flags


def _pytest(tree: pathlib.Path, tests_rel: list[str], python_exe: str, timeout_s: int,
            confine: str, tb: str = "long", trim: list[str] | None = None) -> tuple[int | None, str, bool]:
    """Run pytest on ``tests_rel`` inside ``tree``; prefer confinement; report which happened.

    Returns (rc, log, confined).  rc None means no verdict came back at all."""
    log_rel = ".brain_diagnose/pytest.txt"
    (tree / ".brain_diagnose").mkdir(exist_ok=True)
    argv = ["-m", "pytest", "-q", "-p", "no:cacheprovider", *(trim or []), "--tb=" + tb, *tests_rel]
    program = (
        "import os, subprocess, sys\n"
        "os.chdir('/project')\n"
        "env = dict(os.environ); env['PYTHONDONTWRITEBYTECODE'] = '1'\n"
        # the chroot has no /tmp: the temp dir lives in the scratch tree
        "os.makedirs('/project/.brain_diagnose/tmp', exist_ok=True); env['TMPDIR'] = '/project/.brain_diagnose/tmp'\n"
        "r = subprocess.run([sys.executable, *" + repr(argv) + "], capture_output=True, text=True, env=env)\n"
        "open(" + repr("/project/" + log_rel) + ", 'w', encoding='utf-8').write(r.stdout + '\\n' + r.stderr)\n"
        "print('BRAIN_RC=' + str(r.returncode))\n"
        "sys.exit(0)\n"
    )
    confined = False
    rc = None
    if confine in ("auto", "required") and confine_v1.available():
        receipt = confine_v1.run(program, str(tree), timeout=timeout_s, network=False,
                                 ro_binds=_site_dirs())
        if receipt.get("verdict") == "OK":
            confined = True
            m = re.search(r"BRAIN_RC=(-?\d+)", receipt.get("output") or "")
            rc = int(m.group(1)) if m else None
        elif confine == "required":
            raise DiagnoseRepairRefusal("CONFINEMENT_FAILED:" + str(receipt.get("verdict")))
    if confine == "required" and not confined:
        raise DiagnoseRepairRefusal("CONFINEMENT_UNAVAILABLE")
    if not confined:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        try:
            proc = subprocess.run([python_exe, *argv], cwd=tree, capture_output=True,
                                  text=True, timeout=timeout_s, env=env)
        except subprocess.TimeoutExpired:
            raise DiagnoseRepairRefusal("REPRODUCE_TIMEOUT")
        (tree / log_rel).write_text(proc.stdout + "\n" + proc.stderr, encoding="utf-8")
        rc = proc.returncode
    log = (tree / log_rel).read_text(encoding="utf-8", errors="replace") if (tree / log_rel).is_file() else ""
    return rc, log, confined


def _candidate_verdict(copy_root: pathlib.Path, tests_rel: list[str], python_exe: str, timeout_s: int,
                       confine: str, trim: list[str] | None = None) -> int:
    """pytest verdict for one candidate copy: 0 only when the summary line says nothing failed."""
    try:
        rc, log, _ = _pytest(copy_root, tests_rel, python_exe, timeout_s, confine, tb="no", trim=trim)
    except DiagnoseRepairRefusal:
        return 2
    counts = _summary_counts(log)
    if rc == 0 and counts is not None and counts["failed"] + counts["error"] == 0 and counts["passed"] > 0:
        return 0
    return rc if rc not in (None, 0) else 1


def _probe(copy_root: pathlib.Path, program: str, out_rel: str, python_exe: str, timeout_s: int,
           confine: str) -> list[Any] | None:
    """Run a witness probe inside ``copy_root`` (confined when the host can); return its rows."""
    out = copy_root / out_rel
    out.parent.mkdir(exist_ok=True)
    if out.exists():
        out.unlink()
    ran = False
    if confine in ("auto", "required") and confine_v1.available():
        receipt = confine_v1.run("import os\nos.chdir('/project')\n" + program, str(copy_root), timeout=timeout_s,
                                 network=False, ro_binds=_site_dirs())
        ran = receipt.get("verdict") == "OK"
    if not ran and confine != "required":
        try:
            subprocess.run([python_exe, "-c", program], cwd=copy_root, capture_output=True, timeout=timeout_s,
                           env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
            ran = True
        except subprocess.TimeoutExpired:
            ran = False
    if not ran or not out.is_file():
        return None
    try:
        return json.loads(out.read_text(encoding="utf-8"))
    except ValueError:
        return None


def _reproduce(tree: pathlib.Path, tests_rel: list[str], python_exe: str, timeout_s: int,
               confine: str, trim: list[str] | None = None) -> dict[str, Any]:
    """Run the failing tests once; the verdict is the summary line, never the exit code."""
    rc, log, confined = _pytest(tree, tests_rel, python_exe, timeout_s, confine, trim=trim)
    if rc is None:
        raise DiagnoseRepairRefusal("REPRODUCE_NO_VERDICT")
    if rc == 5:
        raise DiagnoseRepairRefusal("REPRODUCE_COLLECTED_NO_TESTS")
    # The verdict is the summary line, never the exit code alone: a harness that
    # crashes before collecting (rc 1, 3, 4) looks exactly like a failing test to
    # anyone reading rc, and a "repair" of a crash is a lie.
    counts = _summary_counts(log)
    if counts is None:
        raise DiagnoseRepairRefusal("REPRODUCE_HARNESS_ERROR:rc=" + str(rc))
    if counts["failed"] + counts["error"] == 0:
        raise DiagnoseRepairRefusal("NOTHING_TO_REPAIR:FAILING_TESTS_PASS")
    frames: dict[str, int] = {}
    frame_lines: dict[str, list[int]] = {}
    for line in log.splitlines():
        m = _FRAME.match(line.strip())
        if not m:
            continue
        raw = m.group("path")
        p = pathlib.Path(raw)
        p = p if p.is_absolute() else tree / p
        try:
            p = p.resolve()
            rel = p.relative_to(tree).as_posix()
        except ValueError:
            continue
        if not p.is_file() or _TESTNAME(p.name) or rel.startswith(".brain_diagnose/"):
            continue
        frames[rel] = frames.get(rel, 0) + 1
        ln = int(m.group("line"))
        if ln not in frame_lines.setdefault(rel, []):
            frame_lines[rel].append(ln)
    ranked = sorted(frames.items(), key=lambda kv: (-kv[1], kv[0]))
    return {"confined": confined, "returncode": rc, "log_sha256": _sha(log.encode("utf-8")),
            "failed": counts["failed"], "errors": counts["error"], "passed": counts["passed"],
            "traceback_files": [{"path": p, "frames": n, "lines": frame_lines.get(p, [])} for p, n in ranked]}


def run(args: dict[str, Any], root: str | os.PathLike[str]) -> dict[str, Any]:
    started = time.monotonic()
    repo = pathlib.Path(root).resolve()
    args = dict(args or {})
    deadline_s = max(5, int(args.get("deadline_s") or 600))
    deadline = started + deadline_s

    def remaining() -> int:
        left = int(deadline - time.monotonic())
        if left <= 0:
            raise DiagnoseRepairRefusal("DEADLINE_EXCEEDED:" + str(deadline_s) + "s")
        return left

    source_root = _safe(repo, str(args.get("source_root") or ""), must_exist=True)
    if not source_root.is_dir():
        raise DiagnoseRepairRefusal("SOURCE_ROOT_NOT_DIRECTORY")
    tests_raw = args.get("test_paths") or []
    if not isinstance(tests_raw, list) or not tests_raw:
        raise DiagnoseRepairRefusal("TEST_PATHS_REQUIRED")
    tests_abs = [_safe(repo, str(t), must_exist=True) for t in tests_raw]
    for t in tests_abs:
        if source_root not in t.parents:
            raise DiagnoseRepairRefusal("TEST_OUTSIDE_SOURCE_ROOT:" + _rel(repo, t))
    tests_tree = [t.relative_to(source_root).as_posix() for t in tests_abs]
    output = _safe(repo, str(args.get("output_path") or ""))
    if output == repo or source_root == output or source_root in output.parents:
        raise DiagnoseRepairRefusal("OUTPUT_INSIDE_SOURCE_ROOT")
    diff_out = _safe(repo, str(args.get("diff_path") or (_rel(repo, output) + ".diff")))
    python_exe = str(args.get("python_executable") or sys.executable)
    confine = str(args.get("confine") or "auto")
    if confine not in ("auto", "required", "off"):
        raise DiagnoseRepairRefusal("CONFINE_MODE_INVALID")
    max_candidates = int(args.get("max_candidates") or 2000)
    workers = int(args.get("workers") or candidates_v1.default_workers())
    caller_target = args.get("source_path")

    anchor_before = _tree_hash(source_root)
    scratch_root = _owned_scratch(repo, output.parent / (output.stem + ".scratch"))
    tree = scratch_root / "tree"
    _copy_tree(source_root, tree)
    tree_rel = _rel(repo, tree)
    steps: list[dict[str, Any]] = []
    status = ""
    target_rel: str | None = None
    gate: dict[str, Any] = {}
    diff_text = ""
    try:
        # 1. reproduce
        t0 = time.monotonic()
        trim = plugin_trim(tree, tests_tree)
        repro = _reproduce(tree, tests_tree, python_exe, min(remaining(), 300), confine, trim)
        steps.append({"step": "reproduce", "seconds": round(time.monotonic() - t0, 3), "plugin_trim": trim, **repro})

        # 2. diagnose
        t0 = time.monotonic()
        loc_row: dict[str, Any] = {"step": "localize"}
        loc_top: list[str] = []
        loc_lines: dict[str, list[int]] = {}
        try:
            loc = localizer.run({"source_root": tree_rel,
                                 "test_paths": [tree_rel + "/" + t for t in tests_tree],
                                 "timeout_s": min(remaining(), 120),
                                 "output_path": _rel(repo, scratch_root / "localize.json")}, repo)
            seen: list[str] = []
            for row in loc.get("ranked_lines") or []:
                p = str(row.get("path") or "")
                if p.startswith(tree_rel + "/"):
                    p = p[len(tree_rel) + 1:]
                if row.get("line") is not None:
                    loc_lines.setdefault(p, []).append(int(row["line"]))
            for sym in loc.get("ranked_symbols") or []:
                p = str(sym.get("path") or "")
                if p.startswith(tree_rel + "/"):
                    p = p[len(tree_rel) + 1:]
                if p and p not in seen:
                    seen.append(p)
            loc_top = seen
            loc_row.update({"status": loc.get("status"), "failing_test_count": loc.get("failing_test_count"),
                            "ranked_files": seen[:10], "output_sha256": loc.get("output_sha256")})
        except BaseException as exc:  # noqa: BLE001 - a localizer refusal is evidence, not a crash
            loc_row.update({"status": "LOCALIZER_REFUSED:" + type(exc).__name__ + ":" + str(exc)[:160]})
        tb_files = [r["path"] for r in repro["traceback_files"]]
        if isinstance(caller_target, str) and caller_target.strip():
            t_abs = _safe(repo, caller_target, must_exist=True)
            if source_root not in t_abs.parents:
                raise DiagnoseRepairRefusal("SOURCE_PATH_OUTSIDE_SOURCE_ROOT")
            target_rel, basis = t_abs.relative_to(source_root).as_posix(), "CALLER_STATED"
        else:
            agreed = [p for p in loc_top if p in tb_files]
            if agreed:
                target_rel, basis = agreed[0], "LOCALIZER_AND_TRACEBACK_AGREE"
            elif loc_top:
                target_rel, basis = loc_top[0], "LOCALIZER_TOP"
            elif tb_files:
                target_rel, basis = tb_files[0], "TRACEBACK_TOP"
            else:
                raise DiagnoseRepairRefusal("NO_LOCALIZED_SOURCE")
        loc_row.update({"target": target_rel, "target_basis": basis,
                        "seconds": round(time.monotonic() - t0, 3)})
        steps.append(loc_row)
        if not (tree / target_rel).is_file() or not target_rel.endswith(".py"):
            raise DiagnoseRepairRefusal("TARGET_NOT_PYTHON_FILE:" + target_rel)

        # 3. repair: fault-prioritized candidates, tested in parallel on per-worker
        #    copies of the scratch tree, each under the same pytest command (confined
        #    when the host can) that reproduced the failure.  The user's tree is
        #    never touched.
        t0 = time.monotonic()
        source_text = (tree / target_rel).read_text(encoding="utf-8")
        nums, strings = candidates_v1.test_literals([tree / t for t in tests_tree])
        priority: list[int] = []
        for ln in [*loc_lines.get(target_rel, []), *next((r["lines"] for r in repro["traceback_files"]
                                                           if r["path"] == target_rel), [])]:
            if ln not in priority:
                priority.append(ln)
        candidates = candidates_v1.generate(source_text, nums, strings, priority)
        per_run = max(5, min(remaining(), 300))
        witness_row: dict[str, Any] = {}

        def choose(greens: list[tuple[int, str]]) -> int:
            # several green patches: the one that changes behaviour least outside
            # the tests' own inputs (PATCH-SIM); ties and unavailability -> search order
            nonlocal witness_row
            if len(greens) == 1:
                witness_row = {"status": "SINGLE_GREEN", "ranking": [{"index": greens[0][0]}]}
                return greens[0][0]
            t0w = time.monotonic()
            first = greens[0][0]
            desc = next((d for i, (d, _) in enumerate(candidates, 1) if i == first), {})
            witness_row = witness_v1.witness(
                tree=tree, target_rel=target_rel, original_text=source_text, lineno=int(desc.get("lineno") or 1),
                greens=greens, test_paths=[tree / t for t in tests_tree],
                run_program=lambda copy, program, out_rel: _probe(copy, program, out_rel, python_exe,
                                                                   max(5, min(remaining(), 60)), confine),
                scratch=scratch_root)
            witness_row["seconds"] = round(time.monotonic() - t0w, 3)
            return int(witness_row["ranking"][0]["index"])

        search = candidates_v1.evaluate(
            tree, target_rel, candidates,
            lambda copy: _candidate_verdict(copy, tests_tree, python_exe, per_run, confine, trim),
            workers=workers, deadline=deadline, max_candidates=max_candidates, scratch=scratch_root,
            green_budget=int(args.get("green_budget") or 4), choose=choose)
        steps.append({"step": "patch_search", "seconds": round(time.monotonic() - t0, 3),
                      "candidate_count": search["candidate_count"], "tested_candidate_count": search["tested_candidate_count"],
                      "workers": search["workers"], "stop_reason": search["stop_reason"],
                      "priority_lines": priority[:20],
                      "winning_mutation": (search["winner"] or {}).get("mutation"),
                      "winning_index": (search["winner"] or {}).get("index"),
                      "green_indices": search["green_indices"], "witness": witness_row,
                      "attempts": search["attempts"][:200]})
        if search["stop_reason"] == "DEADLINE":
            raise DiagnoseRepairRefusal("DEADLINE_EXCEEDED:" + str(deadline_s) + "s:tested=" + str(search["tested_candidate_count"]))
        if not search["winner"]:
            raise DiagnoseRepairRefusal("OPEN:NO_VERIFIED_CANDIDATE:" + str(search["tested_candidate_count"]))
        diff_text = "".join(difflib.unified_diff(
            source_text.splitlines(keepends=True), search["winner"]["candidate"].splitlines(keepends=True),
            fromfile="a/" + target_rel, tofile="b/" + target_rel))
        if not diff_text.endswith("\n"):
            diff_text += "\n"
        diff_out.parent.mkdir(parents=True, exist_ok=True)
        diff_out.write_text(diff_text, encoding="utf-8")

        # 4. verify against the whole tree
        t0 = time.monotonic()
        gate_out = scratch_root / "gate.json"
        try:
            g = full_gate.run({"anchor_path": _rel(repo, source_root), "diff_path": _rel(repo, diff_out),
                               "output_path": _rel(repo, gate_out), "python_executable": python_exe,
                               "timeout_s": min(remaining(), 600)}, repo)
            gate = {"gate": g.get("gate"), "tests_discovered": g.get("tests_discovered"),
                    "tests_failed": g.get("tests_failed"), "output_sha256": g.get("output_sha256")}
        except SystemExit as exc:
            try:
                reason = json.loads(str(exc.code)).get("reason")
            except Exception:  # noqa: BLE001
                reason = str(exc.code)
            gate = {"gate": "REFUSED:" + str(reason)[:160]}
        steps.append({"step": "full_suite_gate", "seconds": round(time.monotonic() - t0, 3), **gate})
        status = "VERIFIED_PATCH" if gate.get("gate") == "PASS" else "PATCH_FAILS_FULL_SUITE:" + str(gate.get("gate"))
    except DiagnoseRepairRefusal as exc:
        status = str(exc)
    finally:
        shutil.rmtree(scratch_root, ignore_errors=True)

    anchor_after = _tree_hash(source_root)
    if anchor_after != anchor_before:
        status = "SOURCE_ROOT_MUTATED_DURING_RUN"
    verified = status == "VERIFIED_PATCH" and anchor_after == anchor_before
    confined = bool(steps and steps[0].get("step") == "reproduce" and steps[0].get("confined"))
    artifact = {
        "schema": SCHEMA, "capability_id": CAPABILITY_ID,
        "source_root": _rel(repo, source_root), "test_paths": [_rel(repo, t) for t in tests_abs],
        "target_path": target_rel, "confined": confined, "deadline_s": deadline_s,
        "steps": steps, "gate": gate.get("gate"), "status": status, "verified": verified,
        "diff_path": _rel(repo, diff_out) if diff_text else None,
        "diff_sha256": _sha(diff_text.encode("utf-8")) if diff_text else None,
        "anchor_tree_sha256": anchor_before, "anchor_unchanged": anchor_after == anchor_before,
        "hard_nonclaims": ["BOUNDED_SINGLE_FILE_AST_REPAIR_ONLY", "FULL_SUITE_GREEN_IS_NOT_SEMANTIC_CORRECTNESS",
                           "PATCH_IS_PROPOSED_NEVER_APPLIED_TO_SOURCE_ROOT"],
        "model_dependency_count": 0, "incremental_spend_usd": 0,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(artifact, indent=2, sort_keys=True) + "\n").encode("utf-8")
    output.write_bytes(raw)
    return {
        "adapter": ADAPTER, "status": status, "verified": verified, "target_path": target_rel,
        "confined": confined, "steps": [s.get("step") for s in steps],
        "diff_path": artifact["diff_path"], "diff_sha256": artifact["diff_sha256"],
        "gate": gate.get("gate"), "tests_discovered": gate.get("tests_discovered"),
        "tests_failed": gate.get("tests_failed"), "seconds": round(time.monotonic() - started, 3),
        "output_path": _rel(repo, output), "output_sha256": _sha(raw),
        "output_verified": json.loads(raw) == artifact,
        "model_dependency_count": 0, "incremental_spend_usd": 0,
    }
