# PROJECT_BRAIN
"""software.diagnose_repair.v1 -- the engineering loop from the failure
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

import ast
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
from canonical.runtime import patch_inprocess_judge_v1 as judge_v1
from canonical.runtime import expression_synthesis_v1 as synth_v1
from canonical.runtime import hole_synthesis_v1 as hole_v1
from canonical.runtime.bound_capabilities import python_review_diff_mutation_gate as mutation_gate
from canonical.runtime.bound_capabilities import python_review_diff_type_gate as type_gate

SCHEMA = "PROJECT_BRAIN_SOFTWARE_DIAGNOSE_THEN_REPAIR_V1"
CAPABILITY_ID = "software.diagnose_repair.v1"   # no sequencing word ("then") in the id: the sentence door splits clauses on it
ADAPTER = "software_diagnose_then_repair_v1"
OWNED_MARKER = ".brain_owned_output_v1"
_SKIP = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "node_modules"}
_FRAME = re.compile(r"^(?P<path>[^\s:][^:\n]*\.py):(?P<line>\d+):")
_TESTNAME = lambda n: n.startswith("test_") or n.endswith("_test.py")  # noqa: E731


class _SpectrumSufficed(Exception):
    """Internal: the in-process spectrum named the target; the dynamic localizer is skipped."""


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
    if counts is not None and counts["failed"] + counts["error"] > 0:
        return counts["failed"] + counts["error"]      # fitness: how many still fail
    return 1000 + (rc if rc not in (None, 0) else 1)   # no verdict at all: worse than any failure count


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


def _overfit_signature(desc: dict[str, Any], nums: list[Any], strings: list[str]) -> bool:
    """A green edit that wrote one of the tests' own literals into the code (Tan et al.
    2016, anti-patterns in search-based repair): plausible, and the classic overfit."""
    kind, detail = str(desc.get("kind")), str(desc.get("detail"))
    if kind in ("CONSTANT_REPLACE", "STRING_REPLACE"):
        new = detail.split("->", 1)[-1]
        return any(repr(v) == new for v in [*nums, *strings] if v not in (0, 1, -1))
    if kind == "GUARD_INSERT":
        ret = detail.split("return ", 1)[-1]
        return any(repr(v) == ret for v in [*nums, *strings] if v not in (0, 1, -1))
    if kind in ("EXPR_SYNTH", "HOLE_SYNTH"):
        try:
            expr = ast.parse(detail.split("-> ", 1)[-1], mode="eval").body
        except SyntaxError:
            return False
        if isinstance(expr, ast.Constant):
            # a synthesized expression that is a bare constant reads no input at all:
            # the suite's expected value written into the code, whatever the value
            # (measured: `return 0` for a suite whose two expectations are both 0)
            return True
        literals = {n.value for n in ast.walk(expr) if isinstance(n, ast.Constant)}
        return any(v in literals for v in [*nums, *strings] if v not in (0, 1, -1))
    return False


def _replay(tree: pathlib.Path, target_rel: str, text: str, run_tests, scratch: pathlib.Path) -> list[int]:
    copy = scratch / "replay"
    shutil.rmtree(copy, ignore_errors=True)
    shutil.copytree(tree, copy, ignore=shutil.ignore_patterns(*_SKIP))
    try:
        out = []
        for _ in range(2):
            candidates_v1.write_candidate(copy, target_rel, text)
            out.append(run_tests(copy))
        return out
    finally:
        shutil.rmtree(copy, ignore_errors=True)


def _judge_batch(copy_root: pathlib.Path, target_rel: str, modules: list[dict[str, Any]], texts: list[str],
                 python_exe: str, confine: str, deadline: float, mode: str = "plain",
                 pytest_args: list[str] | None = None) -> dict[int, int]:
    """One judge process for ``texts`` in ``copy_root`` (confined when the host can)."""
    batch_rel = ".brain_diagnose/batch"
    out_rel = ".brain_diagnose/judge.json"
    bdir = copy_root / batch_rel
    shutil.rmtree(bdir, ignore_errors=True)
    bdir.mkdir(parents=True)
    for i, t in enumerate(texts):
        if isinstance(t, dict):      # a patch set spanning files
            (bdir / (str(i) + ".json")).write_text(json.dumps(t), encoding="utf-8")
        else:
            (bdir / (str(i) + ".py")).write_text(t, encoding="utf-8")
    out = copy_root / out_rel
    if out.exists():
        out.unlink()
    program = judge_v1.judge_program(target_rel, modules, batch_rel, len(texts), out_rel, mode=mode, pytest_args=pytest_args)
    timeout = max(5, int(deadline - time.monotonic()))
    ran = False
    if confine in ("auto", "required") and confine_v1.available():
        receipt = confine_v1.run("import os\nos.chdir('/project')\n" + program, str(copy_root), timeout=timeout,
                                 network=False, ro_binds=_site_dirs())
        ran = receipt.get("verdict") in ("OK", "TIMEOUT") or out.is_file()
    if not ran and confine != "required":
        try:
            subprocess.run([python_exe, "-c", program], cwd=copy_root, capture_output=True, timeout=timeout,
                           env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        except subprocess.TimeoutExpired:
            pass
    shutil.rmtree(bdir, ignore_errors=True)
    if not out.is_file():
        return {}
    try:
        data = json.loads(out.read_text(encoding="utf-8"))
    except ValueError:
        return {}
    out: dict[int, Any] = {}
    for k, v in data.items():
        if not str(k).lstrip("-").isdigit():
            continue                      # "_per_candidate_s": the measured budget, informational
        if isinstance(v, list) and len(v) == 2:
            out[int(k)] = (int(v[0]), float(v[1]))
        else:
            out[int(k)] = (int(v), float(int(v)))
    return out


def _spectrum(copy_root: pathlib.Path, modules: list[dict[str, Any]], python_exe: str, confine: str,
              deadline: float, mode: str = "plain", pytest_args: list[str] | None = None) -> dict[str, Any]:
    """One in-process run of the plain tests under a line tracer (confined when the host
    can): Ochiai-ranked (path, line) over the tree's non-test files."""
    out_rel = ".brain_diagnose/spectrum.json"
    out = copy_root / out_rel
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    program = judge_v1.spectrum_program(modules, out_rel, mode=mode, pytest_args=pytest_args)
    timeout = max(5, min(60, int(deadline - time.monotonic())))
    ran = False
    if confine in ("auto", "required") and confine_v1.available():
        receipt = confine_v1.run("import os\nos.chdir('/project')\n" + program, str(copy_root), timeout=timeout,
                                 network=False, ro_binds=_site_dirs())
        ran = receipt.get("verdict") in ("OK", "TIMEOUT") or out.is_file()
    if not ran and confine != "required":
        try:
            subprocess.run([python_exe, "-c", program], cwd=copy_root, capture_output=True, timeout=timeout,
                           env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        except subprocess.TimeoutExpired:
            pass
    if not out.is_file():
        return {"status": "SPECTRUM_NO_OUTPUT"}
    try:
        data = json.loads(out.read_text(encoding="utf-8"))
    except ValueError:
        return {"status": "SPECTRUM_UNREADABLE"}
    ranked = [r for r in data.get("ranked") or [] if r[2] > 0]
    return {"status": "SPECTRUM_INPROCESS" if ranked else "SPECTRUM_NO_SUSPICIOUS_LINE",
            "failing_test_count": data.get("failing"), "test_count": len(data.get("tests") or []),
            "ranked": ranked, "hit_lines": data.get("hit_lines") or {}}


def _assert_subjects(plain_mods: list[dict[str, Any]]) -> set[str]:
    """Callables the plain tests' `assert <expr> == <lit>` rows call: the subjects under test."""
    out: set[str] = set()
    for m in plain_mods:
        for sp in m.get("asserts") or []:
            try:
                node = ast.parse(str(sp.get("expr") or ""), mode="eval")
            except SyntaxError:
                continue
            for n in ast.walk(node):
                if isinstance(n, ast.Call):
                    f = n.func
                    if isinstance(f, ast.Name):
                        out.add(f.id)
                    elif isinstance(f, ast.Attribute):
                        out.add(f.attr)
    return out


def _dotted(tree: pathlib.Path, rel: str) -> tuple[str, str]:
    """Import name and sys.path entry for a tree file, the way pytest's prepend mode sees it."""
    p = tree / rel
    d = p.parent
    pkg: list[str] = []
    while (d / "__init__.py").is_file() and d != tree.parent:
        pkg.insert(0, d.name)
        d = d.parent
    return ".".join(pkg + [p.stem]), (d.relative_to(tree).as_posix() if d != tree else ".")


def _hole_synth(copy_root: pathlib.Path, target_rel: str, function: str, line: int,
                examples: list[tuple[list[Any], Any]], constants: list[Any], python_exe: str, confine: str,
                deadline: float, budget_s: float, cls: str | None = None, n_ctor: int = 0) -> dict[str, Any]:
    """One confined run of hole_synthesis_v1 for ``function``'s hole(s) on ``line``."""
    out_rel = ".brain_diagnose/hole.json"
    out = copy_root / out_rel
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    module, sys_path = _dotted(copy_root, target_rel)
    spec = {"module": module, "sys_path": sys_path, "target": target_rel, "function": function, "line": line,
            "examples": [[list(a), e] for a, e in examples], "constants": list(constants), "out": out_rel,
            "budget_s": budget_s, "max_found": 4, "class": cls, "n_ctor": n_ctor}
    program = hole_v1.program(spec, pathlib.Path(hole_v1.__file__).read_text(encoding="utf-8"))
    timeout = max(5, min(60, int(deadline - time.monotonic())))
    ran = False
    if confine in ("auto", "required") and confine_v1.available():
        receipt = confine_v1.run("import os\nos.chdir('/project')\n" + program, str(copy_root), timeout=timeout,
                                 network=False, ro_binds=_site_dirs())
        ran = receipt.get("verdict") in ("OK", "TIMEOUT") or out.is_file()
    if not ran and confine != "required":
        try:
            subprocess.run([python_exe, "-c", program], cwd=copy_root, capture_output=True, timeout=timeout,
                           env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        except subprocess.TimeoutExpired:
            pass
    if not out.is_file():
        return {"status": "HOLE_NO_OUTPUT"}
    try:
        return json.loads(out.read_text(encoding="utf-8"))
    except ValueError:
        return {"status": "HOLE_UNREADABLE"}


def _test_import_closure(tree: pathlib.Path, tests_rel: list[str]) -> list[str]:
    """Tree files (not tests, not __init__) the named test files import, in order of appearance."""
    import ast as _ast
    out: list[str] = []

    def add(mod: str) -> None:
        rel = mod.replace(".", "/")
        for cand in (rel + ".py", rel + "/__init__.py"):
            p = tree / cand
            if p.is_file() and not _TESTNAME(p.name) and cand not in out:
                out.append(cand)
                return

    for rel in tests_rel:
        try:
            t = _ast.parse((tree / rel).read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        for n in _ast.walk(t):
            if isinstance(n, _ast.Import):
                for a in n.names:
                    add(a.name)
            elif isinstance(n, _ast.ImportFrom) and n.module and not n.level:
                add(n.module)
                for a in n.names:            # from pkg import calc
                    add(n.module + "." + a.name)
    return [p for p in out if not p.endswith("/__init__.py")] or out


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


REVIEW_MAX_MUTANTS = 40


def _added_lines(diff_text: str) -> dict[str, set[int]]:
    """New-side line numbers of the `+` lines of a unified diff, per file (the hunk
    ranges the gate parses include context; the review wants the changed lines only)."""
    out: dict[str, set[int]] = {}
    rel, new_ln = "", 0
    for raw in diff_text.splitlines():
        if raw.startswith("+++ "):
            rel = raw[4:].strip()
            rel = rel[2:] if rel.startswith("b/") else rel
        elif raw.startswith("@@"):
            m = re.search(r"\+(\d+)", raw)
            new_ln = int(m.group(1)) if m else 0
        elif raw.startswith("-") and not raw.startswith("---"):
            continue
        elif raw.startswith("+") and not raw.startswith("+++"):
            out.setdefault(rel, set()).add(new_ln)
            new_ln += 1
        elif raw.startswith((" ", "")) and rel and new_ln:
            new_ln += 1
    return out


def _function_body_lines(text: str) -> set[int]:
    """Statement lines inside function bodies: the lines a per-test tracer can see
    (module-level statements run at import, before any test is traced)."""
    try:
        tree_ = ast.parse(text)
    except SyntaxError:
        return set()
    out: set[int] = set()
    for fn in ast.walk(tree_):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for n in ast.walk(fn):
                if isinstance(n, ast.stmt) and not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    out.add(n.lineno)
    return out


def _review(*, tree: pathlib.Path, repo: pathlib.Path, patched: dict[str, str], diff_text: str, diff_path: pathlib.Path,
            tests_tree: list[str], modules: list[dict[str, Any]], inproc: bool, mode: str, pytest_args: list[str],
            python_exe: str, confine: str, deadline: float, scratch_root: pathlib.Path) -> dict[str, Any]:
    """What the suite can SEE of the shipped patch, measured with Brain's own review
    gates on the patched tree: (1) mutation -- python.review.diff_mutation_gate.v1's
    line-confined mutants of the changed lines, each judged by the same in-process
    judge that ranked the candidates (a mutant that survives is a changed line the
    named tests execute but never observe); (2) coverage -- the traced spectrum of
    the patched tree: changed executable lines the named tests never executed;
    (3) types -- python.review.diff_type_gate.v1 (mypy when the interpreter has it,
    PASS_BASELINE_ONLY said loudly otherwise).  Evidence about the suite's grip on
    the patch, written to the ledger; it does not change the verdict."""
    t0 = time.monotonic()
    out: dict[str, Any] = {"step": "review"}
    copy = scratch_root / "review"
    shutil.rmtree(copy, ignore_errors=True)
    shutil.copytree(tree, copy, ignore=shutil.ignore_patterns(*_SKIP))
    try:
        for rel, text in patched.items():
            (copy / rel).write_text(text, encoding="utf-8")
        lines_by_file = {rel: lines for rel, lines in _added_lines(diff_text).items() if rel in patched}
        # 1. mutation: survivors are lines the tests do not pin
        mut: dict[str, Any] = {"status": "SKIPPED:NO_IN_PROCESS_JUDGE"}
        if inproc:
            sites: list[dict[str, Any]] = []
            texts: list[Any] = []
            for rel, lines in lines_by_file.items():
                for site in mutation_gate._mutants_for_text(rel, patched[rel], lines, REVIEW_MAX_MUTANTS - len(texts)):
                    texts.append({rel: mutation_gate._apply_splice(patched[rel], rel, site)})
                    sites.append(site.row(rel))
                    if len(texts) >= REVIEW_MAX_MUTANTS:
                        break
            if not texts:
                mut = {"status": "NO_MUTABLE_SITES", "mutants": 0}
            else:
                lead = next(iter(patched))
                verdicts = _judge_batch(copy, lead, modules, texts, python_exe, confine, min(deadline, time.monotonic() + 60),
                                        mode=mode, pytest_args=pytest_args)
                survivors = [sites[i] for i in range(len(texts)) if verdicts.get(i, (None,))[0] == 0]
                judged = [i for i in range(len(texts)) if i in verdicts]
                mut = {"status": "MEASURED" if len(judged) == len(texts) else "PARTIAL:" + str(len(judged)) + "/" + str(len(texts)),
                       "mutants": len(texts), "killed": len(judged) - len(survivors), "survived": len(survivors),
                       "kill_ratio": round((len(judged) - len(survivors)) / len(judged), 4) if judged else None,
                       "survivors": survivors[:20], "operators_from": "python.review.diff_mutation_gate.v1"}
        out["mutation"] = mut
        # 2. coverage: changed executable lines the named tests executed on the patched tree
        cov: dict[str, Any] = {"status": "SKIPPED:NO_IN_PROCESS_JUDGE"}
        if inproc:
            spec = _spectrum(copy, modules, python_exe, confine, min(deadline, time.monotonic() + 60), mode=mode, pytest_args=pytest_args)
            executed = {(path, int(ln)) for path, lns in (spec.get("hit_lines") or {}).items() for ln in lns}
            if not spec.get("test_count"):
                cov = {"status": "SKIPPED:" + str(spec.get("status"))}
            else:
                unc: list[dict[str, Any]] = []
                n_exec = 0
                for rel, lines in lines_by_file.items():
                    executable = _function_body_lines(patched[rel]) or set(lines)
                    for ln in sorted(lines & executable):
                        if (rel, ln) in executed:
                            n_exec += 1
                        else:
                            unc.append({"file": rel, "line": ln})
                cov = {"status": "MEASURED", "changed_executable_lines": n_exec + len(unc), "executed": n_exec, "uncovered": unc[:20]}
        out["coverage"] = cov
        # 3. types: the existing gate, on the patched copy
        try:
            tg = type_gate.run({"diff_path": _rel(repo, diff_path), "worktree_path": _rel(repo, copy),
                                "output_path": _rel(repo, scratch_root / "review_types.json"),
                                "python_executable": python_exe, "timeout_s": 60}, repo)
            out["types"] = {"gate": tg.get("gate"), "mypy_version": tg.get("mypy_version"),
                            "blocking": tg.get("blocking_count", tg.get("blocking")), "from": "python.review.diff_type_gate.v1"}
        except SystemExit as exc:
            try:
                reason = json.loads(str(exc.code)).get("reason")
            except Exception:  # noqa: BLE001
                reason = str(exc.code)
            out["types"] = {"gate": "REFUSED:" + str(reason)[:160], "from": "python.review.diff_type_gate.v1"}
        except Exception as exc:  # noqa: BLE001 - the review never breaks the verdict
            out["types"] = {"gate": "ERROR:" + type(exc).__name__, "from": "python.review.diff_type_gate.v1"}
    finally:
        shutil.rmtree(copy, ignore_errors=True)
    out["seconds"] = round(time.monotonic() - t0, 3)
    return out


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
    tie_policy = str(args.get("tie_policy") or "first")       # first | refuse
    if tie_policy not in ("first", "refuse"):
        raise DiagnoseRepairRefusal("TIE_POLICY_INVALID")
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
    target_files: list[str] = []
    gate: dict[str, Any] = {}
    diff_text = ""
    try:
        # 1. reproduce
        t0 = time.monotonic()
        trim = plugin_trim(tree, tests_tree)
        repro = _reproduce(tree, tests_tree, python_exe, min(remaining(), 300), confine, trim)
        steps.append({"step": "reproduce", "seconds": round(time.monotonic() - t0, 3), "plugin_trim": trim, **repro})

        # 2. diagnose: spectrum first (one in-process traced run, ~0.1 s) when the
        #    judge can run the suite; the dynamic dataflow localizer otherwise, bounded
        judge_mode = str(args.get("judge") or "auto")       # auto | pytest
        plain_ok, plain_why, plain_mods = (judge_v1.plain_tests(tree, tests_tree) if judge_mode == "auto"
                                           else (False, "JUDGE_PYTEST_REQUESTED", []))
        judge_mode_inproc = "plain"
        if not plain_ok and judge_mode == "auto":
            # not plain (fixtures, conftest hooks, classes ...): host pytest itself in the
            # long-lived judge process instead of one pytest process per candidate; the
            # traced spectrum run below is also the probe -- no output, and the old
            # per-candidate pytest path is used unchanged
            judge_mode_inproc = "pytest"
            plain_mods = judge_v1.hosted_modules(tree, tests_tree)
            plain_ok = True
            plain_why = "PYTEST_HOSTED:" + plain_why
        judge_row = {"in_process": plain_ok, "reason": plain_why}
        t0 = time.monotonic()
        loc_row: dict[str, Any] = {"step": "localize"}
        loc_top: list[str] = []
        loc_lines: dict[str, list[int]] = {}
        spectrum: dict[str, Any] = {"status": "NOT_PLAIN:" + plain_why} if not plain_ok else {}
        if plain_ok:
            spectrum = _spectrum(tree, plain_mods, python_exe, confine, deadline, mode=judge_mode_inproc, pytest_args=trim)
            if judge_mode_inproc == "pytest" and not spectrum.get("ranked"):
                # the hosted probe produced nothing (pytest not importable there, a
                # collection error, a hang): back to the per-candidate pytest path
                plain_ok, plain_mods = False, []
                plain_why = "PYTEST_HOSTED_FAILED:" + str(spectrum.get("status")) + ":" + plain_why.split(":", 1)[-1]
                judge_row = {"in_process": False, "reason": plain_why}
                spectrum = {"status": "NOT_PLAIN:" + plain_why}
        if plain_ok:
            # equal Ochiai score and call depth (every line the failing tests touched): the callable the
            # failing assertions name directly -- the subject under test -- comes first,
            # so `Rect(3, 4).area()` ranks area()'s lines ahead of __init__'s
            subjects = _assert_subjects(plain_mods)
            if subjects and spectrum.get("ranked"):
                owners: dict[str, dict[int, str]] = {}
                def _owner_name(path: str, line: int) -> str:
                    if path not in owners:
                        owners[path] = {}
                        try:
                            t_ = ast.parse((tree / path).read_text(encoding="utf-8"))
                            for n in ast.walk(t_):
                                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                    for ln_ in range(n.lineno, (n.end_lineno or n.lineno) + 1):
                                        owners[path][ln_] = n.name       # innermost wins (walk is outer-first)
                        except (OSError, SyntaxError, UnicodeDecodeError):
                            pass
                    return owners[path].get(line, "")
                spectrum["ranked"] = sorted(spectrum["ranked"],
                                            key=lambda r: (-r[2], -r[5], 0 if _owner_name(r[0], r[1]) in subjects else 1))
                spectrum["subjects"] = sorted(subjects)
            for path, line, score, ef, ep, _depth in spectrum.get("ranked") or []:
                if path.endswith(".py") and not _TESTNAME(pathlib.PurePosixPath(path).name):
                    loc_lines.setdefault(path, []).append(int(line))
                    if path not in loc_top:
                        loc_top.append(path)
            loc_row.update({"status": spectrum["status"], "failing_test_count": spectrum.get("failing_test_count"),
                            "ranked_files": loc_top[:10], "ranked_lines": (spectrum.get("ranked") or [])[:20]})
        try:
            if loc_top:
                raise _SpectrumSufficed()
            loc = localizer.run({"source_root": tree_rel,
                                 "test_paths": [tree_rel + "/" + t for t in tests_tree],
                                 "timeout_s": min(remaining(), int(args.get("localizer_timeout_s") or 20)),
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
        except _SpectrumSufficed:
            pass
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
            spectral = str(loc_row.get("status")) == "SPECTRUM_INPROCESS"
            if agreed:
                target_rel, basis = agreed[0], ("SPECTRUM_AND_TRACEBACK_AGREE" if spectral else "LOCALIZER_AND_TRACEBACK_AGREE")
            elif loc_top:
                target_rel, basis = loc_top[0], ("SPECTRUM_TOP" if spectral else "LOCALIZER_TOP")
            elif tb_files:
                target_rel, basis = tb_files[0], "TRACEBACK_TOP"
            else:
                # a wrong return value raises nothing inside the tree and the dynamic
                # localizer may not run this suite's shape (measured: parametrized
                # tests -> NO_FAILING_TEST); the files the failing tests import from
                # the tree are the last static witness before refusing
                imported = _test_import_closure(tree, tests_tree)
                loc_row["test_import_closure"] = imported[:10]
                if len(imported) == 1:
                    target_rel, basis = imported[0], "TEST_IMPORT_CLOSURE_UNIQUE"
                else:
                    raise DiagnoseRepairRefusal("NO_LOCALIZED_SOURCE" + (":AMBIGUOUS_IMPORTS:" + str(len(imported)) if imported else ""))
        loc_row.update({"target": target_rel, "target_basis": basis,
                        "seconds": round(time.monotonic() - t0, 3)})
        steps.append(loc_row)
        if not (tree / target_rel).is_file() or not target_rel.endswith(".py"):
            raise DiagnoseRepairRefusal("TARGET_NOT_PYTHON_FILE:" + target_rel)

        # 3. repair: fault-prioritized candidates, tested in parallel on per-worker
        #    copies of the scratch tree, each under the same pytest command (confined
        #    when the host can) that reproduced the failure.  The user's tree is
        #    never touched.  One file at a time in the spectrum's order; when no file
        #    alone has a green edit, pairs of hunks across lines and files (stage 3).
        t0 = time.monotonic()
        nums, strings = candidates_v1.test_literals([tree / t for t in tests_tree])
        per_run = max(5, min(remaining(), 300))
        run_tests = lambda copy: _candidate_verdict(copy, tests_tree, python_exe, per_run, confine, trim)  # noqa: E731
        green_budget = int(args.get("green_budget") or 4)
        witness_row: dict[str, Any] = {}

        def make_choose(target_rel: str, source_text: str, cands: list[tuple[dict[str, Any], Any]],
                        expected_rows: list[tuple[list[Any], Any]]):
            def choose(greens: list[tuple[int, Any]]) -> int:
                # several green patches: the one that changes behaviour least outside
                # the tests' own inputs (PATCH-SIM); ties and unavailability -> search order
                nonlocal witness_row
                if len(greens) == 1:
                    witness_row = {"status": "SINGLE_GREEN", "ranking": [{"index": greens[0][0]}]}
                    return greens[0][0]
                t0w = time.monotonic()
                first = greens[0][0]
                desc = next((d for i, (d, _) in enumerate(cands, 1) if i == first), {})
                witness_row = witness_v1.witness(
                    tree=tree, target_rel=target_rel, original_text=source_text, lineno=int(desc.get("lineno") or 1),
                    greens=greens, test_paths=[tree / t for t in tests_tree],
                    run_program=lambda copy, program, out_rel: _probe(copy, program, out_rel, python_exe,
                                                                       max(5, min(remaining(), 60)), confine),
                    scratch=scratch_root, expected=expected_rows,
                    property_examples=int(args.get("property_examples", witness_v1.PROPERTY_EXAMPLES)))
                witness_row["seconds"] = round(time.monotonic() - t0w, 3)
                return int(witness_row["ranking"][0]["index"])
            return choose

        def run_search(target_rel: str, cands: list[tuple[dict[str, Any], Any]], chooser) -> dict[str, Any]:
            def judge_batch(copy: pathlib.Path, texts: list[Any], dl: float) -> dict[int, int]:
                return _judge_batch(copy, target_rel, plain_mods, texts, python_exe, confine, dl,
                                    mode=judge_mode_inproc, pytest_args=trim)
            if plain_ok:
                return candidates_v1.evaluate_batch(
                    tree, target_rel, cands, judge_batch, run_tests,
                    workers=workers, deadline=deadline, max_candidates=max_candidates, scratch=scratch_root,
                    green_budget=green_budget, choose=chooser)
            return candidates_v1.evaluate(
                tree, target_rel, cands, run_tests,
                workers=workers, deadline=deadline, max_candidates=max_candidates, scratch=scratch_root,
                green_budget=green_budget, choose=chooser)

        def expected_for(source_text: str, priority: list[int]) -> list[tuple[list[Any], Any]]:
            if not (plain_mods and priority):
                return []
            w_owner = witness_v1.owning_callable(source_text, priority[0])
            w_specs = [sp for m in plain_mods for sp in (m.get("asserts") or [])]
            if w_owner["name"] and w_owner["class"]:
                return synth_v1.examples_for_method(w_owner["class"], w_owner["name"],
                                                    len(w_owner["ctor_params"] or []), len(w_owner["params"]), w_specs)
            if w_owner["name"]:
                return synth_v1.examples_for(w_owner["name"], w_owner["params"], w_specs)
            return []

        def search_file(target_rel: str) -> dict[str, Any]:
            source_text = (tree / target_rel).read_text(encoding="utf-8")
            priority: list[int] = []
            for ln in [*loc_lines.get(target_rel, []), *next((r["lines"] for r in repro["traceback_files"]
                                                               if r["path"] == target_rel), [])]:
                if ln not in priority:
                    priority.append(ln)
            candidates = candidates_v1.generate(source_text, nums, strings, priority)
            stmt_rows = candidates_v1.statement_candidates(source_text, priority)
            candidates = candidates_v1.merge_ranked(candidates, stmt_rows, priority)
            synth_row: dict[str, Any] = {"status": "NOT_ATTEMPTED"}
            if plain_ok and priority:
                # the tests pin the function's value on >= 2 inputs: the returned
                # expression is a hole, enumerate it (bounded) and let the judge decide
                owner = witness_v1.owning_callable(source_text, priority[0])
                fname, cls_name = owner["name"], owner["class"]
                if fname is None:
                    synth_row = {"status": "NO_FREE_FUNCTION:" + str(owner["why"])}
                else:
                    fn_node = hole_v1.find_def(ast.parse(source_text), fname, cls_name)
                    params = list(owner["params"])
                    n_ctor = len(owner["ctor_params"] or []) if cls_name else 0
                    specs = [sp for m in plain_mods for sp in (m.get("asserts") or [])]
                    if cls_name:
                        examples = synth_v1.examples_for_method(cls_name, fname, n_ctor, len(params), specs)
                    else:
                        examples = synth_v1.examples_for(fname, params, specs)
                    # constants come from the function's own body, never from the tests:
                    # a test literal in a synthesized expression is the overfit anti-pattern
                    own_consts = sorted({n.value for n in ast.walk(fn_node)
                                         if isinstance(n, ast.Constant) and type(n.value) in (int, float)})
                    if cls_name:
                        # a method's value depends on the instance: only the executing hole
                        # synthesizer (which sees self.<attr>) can propose it
                        synth = {"status": "METHOD:HOLE_ONLY", "expressions": []}
                    else:
                        synth = synth_v1.synthesize(params, examples, constants=own_consts,
                                                    budget_s=min(2.0, max(0.5, remaining() / 10)))
                    synth_row = {"function": fname, "class": cls_name, "examples": len(examples), **{k: v for k, v in synth.items()}}
                    if synth["expressions"]:
                        extra = candidates_v1.synthesized_candidates(source_text, priority[0], synth["expressions"])
                        candidates = candidates_v1.merge_ranked(candidates, extra, priority)
                        synth_row["candidates"] = len(extra)
                    if len(examples) >= 2 and remaining() > 10:
                        # the hole is any expression on the suspicious line (assignment,
                        # condition, return): run the function on the examples, confined,
                        # with each distinct expression spliced in; keep the ones that agree
                        fn_lines = set(range(fn_node.lineno, (fn_node.end_lineno or fn_node.lineno) + 1))
                        hole_rows: list[dict[str, Any]] = []
                        extra = []
                        t_h = time.monotonic()
                        budget_h = min(3.0, max(0.5, remaining() / 8))
                        def _worth(x: int) -> bool:
                            kinds = {st["kind"] for st in hole_v1.hole_sites(source_text, fname, x, cls_name)}
                            return bool(kinds) and not (synth["expressions"] and kinds == {"return"})
                        for ln in [x for x in priority if x in fn_lines and _worth(x)][:4]:
                            left = budget_h - (time.monotonic() - t_h)
                            if left < 0.3:
                                break
                            hole = _hole_synth(tree, target_rel, fname, ln, examples, own_consts, python_exe,
                                               confine, deadline, budget_s=min(1.5, left), cls=cls_name, n_ctor=n_ctor)
                            sites = [r for r in hole.get("sites") or []
                                     if not (synth["expressions"] and (r.get("site") or {}).get("kind") == "return")]
                            extra += candidates_v1.hole_candidates(source_text, sites)
                            hole_rows.append({"line": ln, "status": hole.get("status"), "names": hole.get("names"),
                                              "seconds": hole.get("seconds"),
                                              "sites": [{"kind": (r.get("site") or {}).get("kind"),
                                                         "original": (r.get("site") or {}).get("original"),
                                                         "distinct": r.get("distinct"), "tried": r.get("tried"),
                                                         "expressions": r.get("expressions"), "stop": r.get("stop")}
                                                        for r in hole.get("sites") or []]})
                        candidates = candidates_v1.merge_ranked(candidates, extra, priority)
                        synth_row["hole"] = {"lines": hole_rows, "candidates": len(extra),
                                             "seconds": round(time.monotonic() - t_h, 3)}
            expected_rows = expected_for(source_text, priority)
            search = run_search(target_rel, candidates, make_choose(target_rel, source_text, candidates, expected_rows))
            stage2: dict[str, Any] = {}
            suspicious = [i for i in search["green_indices"] if _overfit_signature(candidates[i - 1][0], nums, strings)]
            only_suspicious = bool(search["green_indices"]) and len(suspicious) == len(search["green_indices"])
            if search["winner"] and search["winner"]["index"] in suspicious and not only_suspicious:
                # the witness chose a green that carries the overfit signature while
                # clean greens exist (measured: mergesort -- `len(arr) < 2` with the test
                # literal 2, beside `len(arr) <= 1`): re-rank the clean ones alone
                clean = [(i, candidates[i - 1][1]) for i in search["green_indices"] if i not in suspicious]
                chosen = make_choose(target_rel, source_text, candidates, expected_rows)(clean) if len(clean) > 1 else clean[0][0]
                replay = _replay(tree, target_rel, candidates[chosen - 1][1], run_tests, scratch_root)
                if all(r == 0 for r in replay):
                    search = {**search, "winner": {"index": chosen, "mutation": candidates[chosen - 1][0],
                                                   "candidate": candidates[chosen - 1][1], "replay_returncodes": replay,
                                                   "rechosen_from": clean and [i for i, _ in clean]}}
            if (not search["winner"] or only_suspicious) and search["stop_reason"] in ("EXHAUSTED", "VERIFIED") \
                    and deadline - time.monotonic() > 10:
                # stage 2: no single edit is green -- or every green one carries an
                # overfitting signature (a test literal written into the code, Tan et
                # al. 2016 anti-patterns).  Compose pairs inside one statement, ordered
                # by the singles' fitness (fewest tests still failing, then search
                # order); bounded, same deadline, same runner, same witness.
                t1 = time.monotonic()
                # singles on the top-ranked line only (a two-edit fix inside one statement),
                # best fitness first; with one failing test fitness is flat and search
                # order (cheapest edits first) decides the window
                # ... on each of the top-ranked lines in turn, bounded by compose_limit
                # (the spectrum ties every line a failing test executes; measured:
                # mergesort's two-token fix `== 0` -> `<= 1` sits on the fourth-ranked line)
                top_lines: list[int] = []
                for d, _ in candidates:
                    if d.get("lineno") not in top_lines and d.get("lineno") is not None:
                        top_lines.append(d["lineno"])
                    if len(top_lines) >= 8:
                        break
                fit = sorted(search["attempts"], key=lambda a: (a["returncode"], a.get("distance", 1e9), a["index"]))
                pairs = []
                limit = int(args.get("compose_limit") or 200)
                for top_line in top_lines:
                    order = [a["index"] for a in fit if a["returncode"] < 1000
                             and a["mutation"].get("lineno") == top_line
                             and a["mutation"].get("kind") != "GUARD_INSERT"][:int(args.get("compose_from") or 24)]
                    pairs += candidates_v1.compose_pairs(source_text, candidates, order, limit=limit - len(pairs))
                    if len(pairs) >= limit:
                        break
                if pairs:
                    base = len(candidates)
                    s2 = run_search(target_rel, pairs, make_choose(target_rel, source_text, pairs, expected_rows))
                    for a in s2["attempts"]:
                        a["index"] += base
                        a["stage"] = "compose"
                    if s2["winner"]:
                        s2["winner"]["index"] += base
                    combined = candidates + pairs
                    greens_all = [(i, combined[i - 1][1]) for i in search["green_indices"]] + \
                                 [(i + base, combined[i + base - 1][1]) for i in s2["green_indices"]]
                    winner = search["winner"]
                    if greens_all:
                        chosen = make_choose(target_rel, source_text, combined, expected_rows)(greens_all) if len(greens_all) > 1 else greens_all[0][0]
                        if winner is None or winner["index"] != chosen:
                            if s2["winner"] and s2["winner"]["index"] == chosen:
                                winner = s2["winner"]
                            else:
                                text = combined[chosen - 1][1]
                                replay = _replay(tree, target_rel, text, run_tests, scratch_root)
                                winner = ({"index": chosen, "mutation": combined[chosen - 1][0], "candidate": text,
                                           "replay_returncodes": replay} if all(r == 0 for r in replay) else winner)
                    search = {**s2, "winner": winner, "attempts": search["attempts"] + s2["attempts"],
                              "tested_candidate_count": search["tested_candidate_count"] + s2["tested_candidate_count"],
                              "candidate_count": base + len(pairs),
                              "green_indices": search["green_indices"] + [i + base for i in s2["green_indices"]],
                              "stop_reason": "VERIFIED" if winner else s2["stop_reason"]}
                stage2 = {"reason": "ONLY_SUSPICIOUS_GREENS:" + str(suspicious) if only_suspicious else "NO_SINGLE_EDIT_GREEN",
                          "composed_from": order, "fitness_of_window": [(a["index"], a["returncode"], a.get("distance"))
                                                                        for a in fit[:len(order)]],
                          "pair_count": len(pairs), "seconds": round(time.monotonic() - t1, 3)}
            return {"target_rel": target_rel, "source_text": source_text, "priority": priority, "candidates": candidates,
                    "search": search, "stage2": stage2, "suspicious": suspicious, "synth_row": synth_row,
                    "witness_row": witness_row, "expected_rows": expected_rows}

        # files in the spectrum's order: the agreed/top target first, then the next
        # ranked files that own suspicious lines (bounded); a file is only searched
        # when the previous one had no verified, non-overfit edit
        file_order = [target_rel] + [p for p in loc_top if p != target_rel and loc_lines.get(p)
                                     and (tree / p).is_file() and p.endswith(".py")][:int(args.get("max_files") or 3) - 1]
        per_file: list[dict[str, Any]] = []
        for rel in file_order:
            witness_row = {}
            r = search_file(rel)
            r["seconds"] = round(time.monotonic() - t0 - sum(x["seconds"] for x in per_file), 3)
            per_file.append(r)
            s_ = r["search"]
            if s_["winner"] and s_["winner"]["index"] not in r["suspicious"]:
                break
            if s_["stop_reason"] == "DEADLINE" or remaining() < 15:
                break
        chosen_file = next((r for r in per_file if r["search"]["winner"] and r["search"]["winner"]["index"] not in r["suspicious"]),
                           per_file[0])
        stage3: dict[str, Any] = {}
        if not (chosen_file["search"]["winner"] and chosen_file["search"]["winner"]["index"] not in chosen_file["suspicious"]) \
                and all(r["search"]["stop_reason"] in ("EXHAUSTED", "VERIFIED") for r in per_file) and remaining() > 10:
            # stage 3: no file has a green edit on its own -- the fix may need two hunks:
            # two lines of one file, or one line in each of two files (a wrong value
            # computed in a callee and mishandled by its caller).  Pairs of the
            # best-fitness singles across the searched files, disjoint by construction,
            # judged as patch sets; the witness ranks greens as before.
            t3 = time.monotonic()
            pools = []
            window = int(args.get("compose_from") or 24)
            for r in per_file:
                fit = sorted(r["search"]["attempts"], key=lambda a: (a["returncode"], a.get("distance", 1e9), a["index"]))
                eligible = [a for a in fit if a["returncode"] < 1000 and a["index"] <= len(r["candidates"])
                            and a["mutation"].get("kind") not in ("GUARD_INSERT", "COMPOSE")]
                # the window is line-diverse: hunks pair edits on different lines, so no
                # one line's many equal-fitness singles may crowd the other line's out
                per_line: dict[Any, int] = {}
                order = []
                for a in eligible:
                    ln = a["mutation"].get("lineno")
                    if per_line.get(ln, 0) < max(2, window // 4):
                        order.append(a["index"])
                        per_line[ln] = per_line.get(ln, 0) + 1
                    if len(order) >= window:
                        break
                pools.append((r["target_rel"], r["candidates"], order))
            originals = {r["target_rel"]: r["source_text"] for r in per_file}
            hunks = candidates_v1.compose_hunks(originals, pools, limit=int(args.get("compose_limit") or 200))
            s3: dict[str, Any] = {}
            if hunks:
                lead = per_file[0]
                witness_row = {}
                s3 = run_search(lead["target_rel"], hunks, make_choose(lead["target_rel"], lead["source_text"], hunks, lead["expected_rows"]))
                for a in s3["attempts"]:
                    a["stage"] = "compose_hunks"
                sus3 = [i for i in s3["green_indices"]
                        if any(_overfit_signature(pt, nums, strings) for pt in hunks[i - 1][0]["parts"])]
                if s3["winner"] and s3["winner"]["index"] not in sus3:
                    chosen_file = {**lead, "search": s3, "candidates": hunks, "suspicious": sus3,
                                   "witness_row": witness_row, "stage2": lead["stage2"]}
                elif s3["green_indices"]:
                    chosen_file = {**chosen_file, "suspicious": sorted(set(chosen_file["suspicious"]) | set(sus3))}
            stage3 = {"reason": "NO_SINGLE_FILE_GREEN", "files": [r["target_rel"] for r in per_file],
                      "window_per_file": [{"file": rel, "singles": o} for rel, _, o in pools], "pair_count": len(hunks),
                      "tested": s3.get("tested_candidate_count", 0), "green_indices": s3.get("green_indices", []),
                      "stop_reason": s3.get("stop_reason"), "seconds": round(time.monotonic() - t3, 3)}
        search, candidates, suspicious = chosen_file["search"], chosen_file["candidates"], chosen_file["suspicious"]
        source_text, priority, target_rel = chosen_file["source_text"], chosen_file["priority"], chosen_file["target_rel"]
        synth_row, witness_row, stage2 = chosen_file["synth_row"], chosen_file["witness_row"], chosen_file["stage2"]
        tested_total = sum(r["search"]["tested_candidate_count"] for r in per_file) + int(stage3.get("tested") or 0)
        steps.append({"step": "patch_search", "seconds": round(time.monotonic() - t0, 3),
                      "candidate_count": search["candidate_count"], "tested_candidate_count": tested_total,
                      "workers": search["workers"], "stop_reason": search["stop_reason"],
                      "priority_lines": priority[:20], "compose": stage2, "compose_hunks": stage3, "judge": judge_row,
                      "synthesis": synth_row,
                      "files_searched": [{"file": r["target_rel"], "tested": r["search"]["tested_candidate_count"],
                                          "greens": r["search"]["green_indices"], "stop_reason": r["search"]["stop_reason"],
                                          "seconds": r["seconds"]} for r in per_file],
                      "winning_mutation": (search["winner"] or {}).get("mutation"),
                      "winning_index": (search["winner"] or {}).get("index"),
                      "green_indices": search["green_indices"], "witness": witness_row,
                      "overfit_signature_indices": suspicious,
                      "attempts": search["attempts"][:200]})
        if any(r["search"]["stop_reason"] == "DEADLINE" for r in per_file) or stage3.get("stop_reason") == "DEADLINE":
            raise DiagnoseRepairRefusal("DEADLINE_EXCEEDED:" + str(deadline_s) + "s:tested=" + str(tested_total))
        if not search["winner"]:
            raise DiagnoseRepairRefusal("OPEN:NO_VERIFIED_CANDIDATE:" + str(tested_total))
        if search["winner"]["index"] in suspicious:
            # the only way to make the suite green was to write its expected value into
            # the code; that is the suite's weakness, not a repair, and it is not shipped
            raise DiagnoseRepairRefusal("OPEN:ONLY_OVERFIT_SIGNATURE_GREENS:" + str(suspicious))
        if tie_policy == "refuse" and witness_row.get("tie_at_top"):
            # two different behaviours satisfy the suite, the contract and the probes
            # equally: the suite under-specifies; under tie_policy=refuse that is the
            # answer, with every tied alternative in the ledger, and nothing is shipped
            tied = [r["index"] for r in witness_row.get("ranking") or [] if r.get("tied_with_top")]
            raise DiagnoseRepairRefusal("OPEN:WITNESS_TIE:classes=" + str(witness_row.get("behaviour_classes"))
                                        + ":" + str(tied[:8]))
        patched = candidates_v1.candidate_files(target_rel, search["winner"]["candidate"])
        diff_text = ""
        for rel in sorted(patched):
            before = source_text if rel == target_rel else (tree / rel).read_text(encoding="utf-8")
            diff_text += "".join(difflib.unified_diff(before.splitlines(keepends=True), patched[rel].splitlines(keepends=True),
                                                      fromfile="a/" + rel, tofile="b/" + rel))
            if not diff_text.endswith("\n"):
                diff_text += "\n"
        target_files = sorted(patched)
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
        # 5. review: what the named tests can see of the shipped lines (mutation,
        #    coverage, types) -- evidence in the ledger, never a change of verdict
        if status == "VERIFIED_PATCH" and str(args.get("review") or "auto") != "off" and remaining() > 5:
            review_row = _review(tree=tree, repo=repo, patched=patched, diff_text=diff_text, diff_path=diff_out,
                                 tests_tree=tests_tree, modules=plain_mods, inproc=plain_ok, mode=judge_mode_inproc,
                                 pytest_args=trim, python_exe=python_exe, confine=confine, deadline=deadline,
                                 scratch_root=scratch_root)
            steps.append(review_row)
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
        "target_path": target_rel, "target_paths": target_files, "confined": confined, "deadline_s": deadline_s,
        "steps": steps, "gate": gate.get("gate"), "status": status, "verified": verified,
        "diff_path": _rel(repo, diff_out) if diff_text else None,
        "diff_sha256": _sha(diff_text.encode("utf-8")) if diff_text else None,
        "anchor_tree_sha256": anchor_before, "anchor_unchanged": anchor_after == anchor_before,
        "hard_nonclaims": ["BOUNDED_AST_REPAIR_AT_MOST_TWO_HUNKS_IN_AT_MOST_TWO_FILES", "FULL_SUITE_GREEN_IS_NOT_SEMANTIC_CORRECTNESS",
                           "PATCH_IS_PROPOSED_NEVER_APPLIED_TO_SOURCE_ROOT"],
        "model_dependency_count": 0, "incremental_spend_usd": 0,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(artifact, indent=2, sort_keys=True) + "\n").encode("utf-8")
    output.write_bytes(raw)
    rv = next((st for st in steps if st.get("step") == "review"), {})
    return {
        "adapter": ADAPTER, "status": status, "verified": verified, "target_path": target_rel, "target_paths": target_files,
        "confined": confined, "steps": [s.get("step") for s in steps],
        "review": {"mutation_kill_ratio": (rv.get("mutation") or {}).get("kill_ratio"),
                   "mutation_survivors": (rv.get("mutation") or {}).get("survived"),
                   "uncovered_changed_lines": len((rv.get("coverage") or {}).get("uncovered") or []) if (rv.get("coverage") or {}).get("status") == "MEASURED" else None,
                   "type_gate": (rv.get("types") or {}).get("gate")} if rv else None,
        "diff_path": artifact["diff_path"], "diff_sha256": artifact["diff_sha256"],
        "gate": gate.get("gate"), "tests_discovered": gate.get("tests_discovered"),
        "tests_failed": gate.get("tests_failed"), "seconds": round(time.monotonic() - started, 3),
        "output_path": _rel(repo, output), "output_sha256": _sha(raw),
        "output_verified": json.loads(raw) == artifact,
        "model_dependency_count": 0, "incremental_spend_usd": 0,
    }
