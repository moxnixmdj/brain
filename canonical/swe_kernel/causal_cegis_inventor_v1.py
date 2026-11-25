#!/usr/bin/env python3
"""Causal Angelic Abduction + Counterexample-Guided Observational E-Graph Synthesis (COGS)
+ Zero-Copy CoW Executable Mental Model + Polyglot Multi-File Beam Repair Engine.

Zero runtime model calls (`model_calls = 0`), zero memorized world-fact weights.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
import difflib
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any

try:
    import z3
except ImportError:
    z3 = None  # type: ignore[assignment]

from canonical.swe_kernel.cow_impact_repair_engine_v1 import (
    cow_write_text,
    create_zero_copy_cow_workspace,
)
from canonical.swe_kernel.cow_lens_fuzz_and_negative_space_v1 import (
    DEFAULT_NEGATIVE_STORE_PATH,
    NegativeSpaceInvariantStore,
    verify_cow_boundary_invariance,
)
from canonical.swe_kernel.repo_component_petri_v1 import (
    extract_candidate_repro_tests_from_issue,
    extract_test_called_symbols_and_literals,
    extract_test_spec_literals,
    synthesize_repo_petri_repairs,
)
from canonical.swe_kernel.universal_semantic_ir_v1 import (
    DEFAULT_LAW_STORE_PATH,
    IGNORED_DIRS,
    InterproceduralCausalGraph,
    SemanticCausalLaw,
    SemanticCausalLawStore,
    lift_verified_diff_to_semantic_law,
    lower_source_to_uir,
)
try:
    from canonical.swe_kernel import whitebox_introspector_and_trace_synthesizer_v1 as wb_synth
    from canonical.swe_kernel.multistep_repo_closed_loop_solver_v1 import _surgical_span_mutations
except Exception:
    wb_synth = None  # type: ignore[assignment]
    _surgical_span_mutations = None  # type: ignore[assignment]


def merge_orthogonal_file_patches(
    repo_root: pathlib.Path,
    patch_a: dict[str, str],
    patch_b: dict[str, str],
) -> dict[str, str] | None:
    """Compose two partial patches across disjoint files OR non-overlapping line hunks
    inside the SAME file (`Same-File Multi-Hunk Orthogonal Patch Algebra`).
    Returns `None` if two hunks touch overlapping line ranges or fail syntax validation.
    """
    merged: dict[str, str] = {}
    all_rels = sorted(set(patch_a.keys()) | set(patch_b.keys()))
    for rel in all_rels:
        in_a = rel in patch_a
        in_b = rel in patch_b
        if in_a and not in_b:
            merged[rel] = patch_a[rel]
            continue
        if in_b and not in_a:
            merged[rel] = patch_b[rel]
            continue
        if patch_a[rel] == patch_b[rel]:
            return None
        orig_p = repo_root / rel
        if not orig_p.is_file():
            return None
        orig_lines = orig_p.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
        a_lines = patch_a[rel].splitlines(keepends=True)
        b_lines = patch_b[rel].splitlines(keepends=True)

        def _extract_hunks(mod_lines: list[str]) -> list[tuple[int, int, list[str]]]:
            sm = difflib.SequenceMatcher(None, orig_lines, mod_lines, autojunk=False)
            hunks: list[tuple[int, int, list[str]]] = []
            for tag, i1, i2, j1, j2 in sm.get_opcodes():
                if tag != "equal":
                    hunks.append((i1, i2, mod_lines[j1:j2]))
            return hunks

        hunks_a = _extract_hunks(a_lines)
        hunks_b = _extract_hunks(b_lines)
        if not hunks_a or not hunks_b:
            return None
        for ia1, ia2, _ in hunks_a:
            for ib1, ib2, _ in hunks_b:
                # Overlap check (including same zero-length insertion point)
                if ia1 == ia2 and ib1 == ib2 and ia1 == ib1:
                    return None
                if max(ia1, ib1) < min(ia2, ib2):
                    return None

        combined_hunks = sorted(hunks_a + hunks_b, key=lambda h: h[0], reverse=True)
        out_lines = list(orig_lines)
        for i1, i2, repl in combined_hunks:
            out_lines[i1:i2] = repl
        merged_txt = "".join(out_lines)
        if rel.endswith(".py"):
            try:
                ast.parse(merged_txt)
            except SyntaxError:
                return None
        merged[rel] = merged_txt
    return merged


def synthesize_dual_program_splice(
    *,
    orig_src: str,
    cand_src: str,
    fail_samples_by_line: dict[int, list[dict[str, Any]]],
    reg_samples_by_line: dict[int, list[dict[str, Any]]],
) -> list[tuple[str, str]]:
    """Counterexample-Partitioned Dual-Program Splicing (`if G: P_cand else: P_orig`).

    Triggered when `cand_src` solves `baseline.failing_tests` (`quick_ok == True`) while
    breaking a passing test `T_reg` that `orig_src` passed. Computes separating predicates `G`
    such that `G(fail) == True` and `G(reg) == False` at the modified statement line.
    """
    orig_lines = orig_src.splitlines(keepends=True)
    cand_lines = cand_src.splitlines(keepends=True)
    if len(orig_lines) != len(cand_lines):
        return []
    diff_idxs = [i for i, (ol, cl) in enumerate(zip(orig_lines, cand_lines)) if ol != cl]
    if len(diff_idxs) != 1:
        return []
    idx = diff_idxs[0]
    line_no = idx + 1
    ol = orig_lines[idx]
    cl = cand_lines[idx]
    ol_strip = ol.strip()
    cl_strip = cl.strip()
    # Only splice single-line executable statements (Assign / AnnAssign / Return / Expr), not compound headers
    if ol_strip.endswith(":") or cl_strip.endswith(":") or not ol_strip or not cl_strip:
        return []
    indent = ol[: len(ol) - len(ol.lstrip())]
    f_smps = fail_samples_by_line.get(line_no, [])
    r_smps = reg_samples_by_line.get(line_no, [])
    if not f_smps or not r_smps:
        return []

    cand_guards: list[str] = []
    # Collect local variables & 1-hop attributes present in both fail and regression samples
    var_names = sorted(
        set().union(*(set((s.get("locals") or {}).keys()) for s in (f_smps + r_smps)))
        - {"self", "cls"}
    )
    probe_exprs: list[str] = []
    for v in var_names[:14]:
        probe_exprs.extend([f"{v} is None", f"{v} is not None", f"not {v}", f"bool({v})", f"isinstance({v}, (list, tuple))", f"isinstance({v}, str)"])
        for s in f_smps[:2]:
            attrs = ((s.get("locals") or {}).get(v) or {}).get("attrs") or {}
            for ak in list(attrs.keys())[:6]:
                probe_exprs.extend([f"{v}.{ak} is None", f"{v}.{ak} is not None", f"not {v}.{ak}", f"bool({v}.{ak})"])

    for g in probe_exprs:
        try:
            f_vals = [bool(_eval_snapshot_expr(g, s)) for s in f_smps]
            r_vals = [bool(_eval_snapshot_expr(g, s)) for s in r_smps]
        except Exception:
            continue
        if all(f_vals) and not any(r_vals):
            clean_g = g[5:-1] if g.startswith("bool(") and g.endswith(")") else g
            if clean_g not in cand_guards:
                cand_guards.append(clean_g)

    out: list[tuple[str, str]] = []
    for g in cand_guards[:4]:
        spliced_block = (
            f"{indent}if {g}:\n"
            f"{indent}    {cl_strip}\n"
            f"{indent}else:\n"
            f"{indent}    {ol_strip}\n"
        )
        new_lines = list(orig_lines)
        new_lines[idx] = spliced_block
        spliced_src = "".join(new_lines)
        try:
            ast.parse(spliced_src)
            out.append((spliced_src, f"Dual-program counterexample splice at L{line_no} guarded by `{g}`"))
        except SyntaxError:
            continue
    return out


def compute_workspace_digest(root: pathlib.Path) -> str:
    h = hashlib.sha256()
    root = pathlib.Path(root).resolve()
    for cur_dir, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in IGNORED_DIRS)
        for fn in sorted(filenames):
            if fn.endswith((".pyc", ".pyo")):
                continue
            fp = pathlib.Path(cur_dir) / fn
            if fp.is_symlink() or not fp.is_file():
                continue
            rel = fp.relative_to(root).as_posix()
            h.update(rel.encode("utf-8") + b"\x00")
            try:
                h.update(hashlib.sha256(fp.read_bytes()).digest())
            except OSError:
                pass
    return h.hexdigest()

INVENTOR_SCHEMA = "BRAIN_CAUSAL_CEGIS_INVENTOR_V1"

_PYTEST_VERDICT_AFTER = re.compile(
    r"^(\S+::.+?)\s+(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)(?:\s+\[\s*\d+%\])?$"
)
_PYTEST_VERDICT_BEFORE = re.compile(
    r"^(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)\s+(\S+::.+?)(?:\s+-\s+.*)?$"
)
_ASAN_FRAME_RE = re.compile(r"#\d+\s+0x[0-9a-fA-F]+\s+in\s+(\w+)\s+([^\s:]+):(\d+)")
_JS_FRAME_RE = re.compile(r"at\s+(?:(\S+)\s+\()?([^\s():]+):(\d+):(\d+)\)?")


@dataclass
class TestRunVerdict:
    passed: bool
    returncode: int
    outcomes: dict[str, str]
    failing_tests: list[str]
    passing_tests: list[str]
    output: str
    elapsed_ms: float


@dataclass
class InventedRepairResult:
    solved: bool
    stage: str
    mechanism: str
    modified_files: dict[str, str]
    unified_diff: str
    sabotage_verified: bool
    overfit_falsifier_passed: bool
    neighbor_impact_passed: bool
    crystallized_law_id: str | None
    candidates_evaluated_in_memory: int
    candidates_executed_in_sandbox: int
    source_tree_unchanged: bool
    elapsed_ms: float
    diagnostics: dict[str, Any] = field(default_factory=dict)


_ZYGOTE_PYTEST_SERVER_SCRIPT = r'''
import contextlib, importlib, io, json, os, signal, sys, time
import pytest

for raw in sys.stdin:
    raw = raw.strip()
    if not raw:
        continue
    req = json.loads(raw)
    args = req["args"]
    t_lim = float(req.get("timeout", 4.5))
    importlib.invalidate_caches()
    r_fd, w_fd = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(r_fd)
        buf = io.StringIO()
        rc = 1
        try:
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
                rc = int(pytest.main(args))
        except SystemExit as se:
            rc = int(se.code) if isinstance(se.code, int) else 1
        except BaseException:
            rc = 2
        try:
            payload = json.dumps({"rc": rc, "stdout": buf.getvalue()}).encode("utf-8", errors="replace")
            os.write(w_fd, payload)
        except BaseException:
            pass
        finally:
            os.close(w_fd)
            os._exit(0)
    os.close(w_fd)
    deadline = time.monotonic() + t_lim
    timed_out = False
    while True:
        wpid, _ = os.waitpid(pid, os.WNOHANG)
        if wpid == pid:
            break
        if time.monotonic() >= deadline:
            timed_out = True
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
            try:
                os.waitpid(pid, 0)
            except OSError:
                pass
            break
        time.sleep(0.004)
    chunks = []
    while True:
        b = os.read(r_fd, 16384)
        if not b:
            break
        chunks.append(b)
    os.close(r_fd)
    if timed_out:
        sys.stdout.write(json.dumps({"timeout": True, "rc": 124, "stdout": ""}) + "\n")
    else:
        raw_out = b"".join(chunks).decode("utf-8", errors="replace")
        sys.stdout.write((raw_out if raw_out else json.dumps({"rc": 2, "stdout": ""})) + "\n")
    sys.stdout.flush()
'''


def _resolve_repo_python_executable(repo_root: pathlib.Path) -> str:
    """Resolve the repository/container Python interpreter carrying `pytest` and project deps."""
    candidates = [
        str(repo_root / ".venv" / "bin" / "python"),
        str(repo_root / "venv" / "bin" / "python"),
        "/opt/miniconda3/envs/testbed/bin/python",
        "/opt/conda/envs/testbed/bin/python",
        "/opt/venv/bin/python",
        "/venv/bin/python",
        sys.executable,
        "/opt/conda/bin/python",
        "/usr/local/bin/python3",
    ]
    seen: set[str] = set()
    for cand in candidates:
        if not cand or cand in seen or not os.path.isfile(cand) or not os.access(cand, os.X_OK):
            continue
        seen.add(cand)
        if cand == sys.executable:
            try:
                import pytest  # noqa: F401
                return cand
            except ImportError:
                pass
        try:
            r = subprocess.run(
                [cand, "-c", "import pytest"],
                capture_output=True,
                stdin=subprocess.DEVNULL,
                timeout=3.0,
            )
            if r.returncode == 0:
                return cand
        except Exception:
            continue
    return sys.executable


class ExecutableMentalModel:
    """Zero-copy hardlink CoW execution sandbox with bytecode isolation and impact-cone checking."""

    def __init__(
        self,
        repo_root: pathlib.Path,
        *,
        language: str = "python",
        test_target: str | None = None,
        custom_test_cmd: list[str] | None = None,
        timeout_sec: float = 20.0,
    ) -> None:
        self.source_repo = pathlib.Path(repo_root).resolve()
        self.language = "cpp" if language in {"c", "cpp", "c++"} else language
        self.test_target = test_target
        self.custom_test_cmd = custom_test_cmd
        self.timeout_sec = timeout_sec
        self.py_exe = _resolve_repo_python_executable(self.source_repo) if self.language == "python" else sys.executable
        self.initial_source_digest = compute_workspace_digest(self.source_repo)
        self._tmp_ctx = tempfile.TemporaryDirectory(prefix="brain_mental_cow_", ignore_cleanup_errors=True)
        self.cow_root = pathlib.Path(self._tmp_ctx.name) / "ws"
        self.pycache_dir = pathlib.Path(self._tmp_ctx.name) / "pycache"
        self.pycache_dir.mkdir(parents=True, exist_ok=True)
        create_zero_copy_cow_workspace(self.source_repo, self.cow_root)
        for cache in self.cow_root.rglob("__pycache__"):
            shutil.rmtree(cache, ignore_errors=True)
        self._originals: dict[str, bytes] = {}
        self.simulations_run = 0
        self._mtime_bump = 2
        self._zygote_proc: subprocess.Popen[str] | None = None

    def close(self) -> None:
        if self._zygote_proc is not None:
            try:
                if self._zygote_proc.stdin:
                    self._zygote_proc.stdin.close()
                self._zygote_proc.terminate()
                self._zygote_proc.wait(timeout=1.5)
            except Exception:
                try:
                    self._zygote_proc.kill()
                    self._zygote_proc.wait(timeout=1.5)
                except Exception:
                    pass
            self._zygote_proc = None
        self._tmp_ctx.cleanup()

    def _ensure_zygote(self) -> subprocess.Popen[str] | None:
        if not hasattr(os, "fork"):
            return None
        if self._zygote_proc is not None and self._zygote_proc.poll() is None:
            return self._zygote_proc
        try:
            self._zygote_proc = subprocess.Popen(
                [self.py_exe, "-u", "-c", _ZYGOTE_PYTEST_SERVER_SCRIPT],
                cwd=self.cow_root,
                env=self._python_env(),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            return self._zygote_proc
        except Exception:
            self._zygote_proc = None
            return None

    def __enter__(self) -> ExecutableMentalModel:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def verify_source_untouched(self) -> bool:
        return compute_workspace_digest(self.source_repo) == self.initial_source_digest

    def _bump_file_mtime(self, target: pathlib.Path) -> None:
        """Advance mtime by >= 2 whole seconds on every write so CPython NEVER reuses a
        stale `.pyc` for the edited file while keeping `.pyc` warm for pytest/stdlib."""
        self._mtime_bump += 2
        ts = time.time() + self._mtime_bump
        try:
            os.utime(target, (ts, ts))
        except OSError:
            pass

    def _python_env(self) -> dict[str, str]:
        py_paths = []
        if (self.cow_root / "src").is_dir():
            py_paths.append(str(self.cow_root / "src"))
        py_paths.append(str(self.cow_root))
        existing = os.environ.get("PYTHONPATH", "")
        if existing:
            py_paths.append(existing)
        return {
            **os.environ,
            "PYTHONPATH": os.pathsep.join(py_paths),
            "PYTHONPYCACHEPREFIX": str(self.pycache_dir),
        }

    def apply_overrides(self, file_contents: dict[str, str | bytes]) -> None:
        for rel_path, content in file_contents.items():
            target = self.cow_root / rel_path
            if rel_path not in self._originals and target.exists():
                self._originals[rel_path] = target.read_bytes()
            if isinstance(content, bytes):
                if target.exists() or target.is_symlink():
                    target.unlink()
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
            else:
                cow_write_text(target, content)
            self._bump_file_mtime(target)

    def restore_originals(self, rel_paths: list[str] | None = None) -> None:
        keys = list(self._originals.keys()) if rel_paths is None else rel_paths
        for rel_path in keys:
            if rel_path in self._originals:
                target = self.cow_root / rel_path
                if target.exists() or target.is_symlink():
                    target.unlink()
                target.write_bytes(self._originals[rel_path])
                self._bump_file_mtime(target)

    def run_fast_gate(
        self,
        *,
        specific_target: str | None = None,
        specific_targets: list[str] | None = None,
        modified_rels: list[str],
        timeout_sec: float = 6.0,
    ) -> tuple[bool, TestRunVerdict | None]:
        """Fast targeted test gate reusing warm `PYTHONPYCACHEPREFIX` while running ONLY
        the failing nodeids (`1..10` tests instead of an entire 150-test suite)."""
        targets = [t for t in (specific_targets or ([specific_target] if specific_target else [])) if t and not t.startswith("<")]
        if self.language != "python" or self.custom_test_cmd is not None or not targets:
            v = self.run_oracle(specific_target=specific_target, timeout_sec=timeout_sec)
            return v.passed, v

        t0 = time.perf_counter()
        self.simulations_run += 1
        multi = len(targets) > 1
        pytest_args = [
            *targets[:10],
            "-v" if multi else "-q",
            "--tb=no",
            "-p",
            "no:cacheprovider",
            "-W",
            "ignore",
        ]
        zproc = self._ensure_zygote()
        if zproc is not None and zproc.stdin is not None and zproc.stdout is not None:
            try:
                zproc.stdin.write(
                    json.dumps({"args": pytest_args, "timeout": float(timeout_sec)}) + "\n"
                )
                zproc.stdin.flush()
                resp_line = zproc.stdout.readline()
                if resp_line:
                    resp = json.loads(resp_line)
                    if resp.get("timeout"):
                        return False, None
                    rc = int(resp.get("rc", 1))
                    out_txt = str(resp.get("stdout") or "")
                    if not multi:
                        return rc == 0, None
                    outcomes_z: dict[str, str] = {}
                    for line in out_txt.splitlines():
                        s = line.strip()
                        m1 = _PYTEST_VERDICT_AFTER.match(s)
                        if m1:
                            outcomes_z[m1.group(1)] = m1.group(2)
                            continue
                        m2 = _PYTEST_VERDICT_BEFORE.match(s)
                        if m2:
                            outcomes_z.setdefault(m2.group(2), m2.group(1))
                    failing_z = [k for k, v in outcomes_z.items() if v in {"FAILED", "ERROR", "TIMEOUT"}]
                    passing_z = [k for k, v in outcomes_z.items() if v == "PASSED"]
                    passed_z = rc == 0 and len(failing_z) == 0 and len(passing_z) > 0
                    return passed_z, TestRunVerdict(
                        passed=passed_z,
                        returncode=rc,
                        outcomes=outcomes_z,
                        failing_tests=failing_z,
                        passing_tests=passing_z,
                        output=out_txt[-2000:],
                        elapsed_ms=round((time.perf_counter() - t0) * 1000.0, 2),
                    )
            except Exception:
                pass

        cmd = [self.py_exe, "-m", "pytest", *pytest_args]
        try:
            proc = subprocess.run(
                cmd,
                cwd=self.cow_root,
                env=self._python_env(),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                stdin=subprocess.DEVNULL,
                timeout=timeout_sec,
            )
            if not multi:
                return proc.returncode == 0, None
            outcomes: dict[str, str] = {}
            for line in (proc.stdout or "").splitlines():
                s = line.strip()
                m1 = _PYTEST_VERDICT_AFTER.match(s)
                if m1:
                    outcomes[m1.group(1)] = m1.group(2)
                    continue
                m2 = _PYTEST_VERDICT_BEFORE.match(s)
                if m2:
                    outcomes.setdefault(m2.group(2), m2.group(1))
            failing = [k for k, v in outcomes.items() if v in {"FAILED", "ERROR", "TIMEOUT"}]
            passing = [k for k, v in outcomes.items() if v == "PASSED"]
            passed = proc.returncode == 0 and len(failing) == 0 and len(passing) > 0
            verdict = TestRunVerdict(
                passed=passed,
                returncode=proc.returncode,
                outcomes=outcomes,
                failing_tests=failing,
                passing_tests=passing,
                output=((proc.stdout or "") + "\n" + (proc.stderr or ""))[-2000:],
                elapsed_ms=round((time.perf_counter() - t0) * 1000.0, 2),
            )
            return passed, verdict
        except subprocess.TimeoutExpired:
            return False, None

    def run_oracle(
        self,
        *,
        specific_target: str | None = None,
        timeout_sec: float | None = None,
    ) -> TestRunVerdict:
        t0 = time.perf_counter()
        self.simulations_run += 1
        t_limit = timeout_sec or self.timeout_sec

        if self.custom_test_cmd is not None and specific_target is None:
            cmd = list(self.custom_test_cmd)
            env = self._python_env() if self.language == "python" else dict(os.environ)
        elif self.language == "python":
            tgt = specific_target or self.test_target or "tests"
            cmd = [
                self.py_exe,
                "-m",
                "pytest",
                tgt,
                "-v",
                "--tb=line",
                "-p",
                "no:cacheprovider",
                "-W",
                "ignore",
            ]
            env = self._python_env()
        elif self.language in {"javascript", "typescript"}:
            tgt = specific_target or self.test_target or "test.js"
            cmd = ["node", "--test", tgt] if ".test." in tgt or ".spec." in tgt else ["node", tgt]
            env = dict(os.environ)
        else:
            cmd = list(self.custom_test_cmd or ["ctest", "--output-on-failure"])
            env = dict(os.environ)
            env.setdefault("UBSAN_OPTIONS", "print_stacktrace=1:halt_on_error=1")

        import signal

        p_obj = subprocess.Popen(
            cmd,
            cwd=self.cow_root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
        try:
            p_out, p_err = p_obj.communicate(timeout=t_limit)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(p_obj.pid, signal.SIGKILL)
            except OSError:
                p_obj.kill()
            p_obj.communicate()
            return TestRunVerdict(
                passed=False,
                returncode=124,
                outcomes={"<timeout>": "TIMEOUT"},
                failing_tests=["<timeout>"],
                passing_tests=[],
                output="TIMEOUT",
                elapsed_ms=round((time.perf_counter() - t0) * 1000.0, 2),
            )

        combined = (p_out or "") + "\n" + (p_err or "")
        outcomes: dict[str, str] = {}
        if self.language == "python":
            for line in (p_out or "").splitlines():
                s = line.strip()
                m1 = _PYTEST_VERDICT_AFTER.match(s)
                if m1:
                    outcomes[m1.group(1)] = m1.group(2)
                    continue
                m2 = _PYTEST_VERDICT_BEFORE.match(s)
                if m2:
                    outcomes.setdefault(m2.group(2), m2.group(1))

        failing = [k for k, v in outcomes.items() if v in {"FAILED", "ERROR", "TIMEOUT"}]
        passing = [k for k, v in outcomes.items() if v == "PASSED"]
        if not outcomes:
            if p_obj.returncode == 0:
                outcomes["<suite>"] = "PASSED"
                passing = ["<suite>"]
            else:
                outcomes["<suite>"] = "FAILED"
                failing = ["<suite>"]

        passed = p_obj.returncode == 0 and len(failing) == 0 and len(passing) > 0
        return TestRunVerdict(
            passed=passed,
            returncode=p_obj.returncode,
            outcomes=outcomes,
            failing_tests=failing,
            passing_tests=passing,
            output=combined[-4000:],
            elapsed_ms=round((time.perf_counter() - t0) * 1000.0, 2),
        )


# ---------------------------------------------------------------------------
# Lightweight Child-Process Python Causal Tracer (runs ONLY inside CoW clone)
# ---------------------------------------------------------------------------

_CHILD_TRACER_SCRIPT = r'''
import collections.abc
import json
import os
import pathlib
import sys

import pytest

cfg = json.loads(sys.argv[1])
cow_root = pathlib.Path(cfg["cow_root"]).resolve()
cow_prefix = str(cow_root) + os.sep
test_file = cfg["test_file"]
fail_ids = set(cfg["fail_ids"])
pass_ids = set(cfg["pass_ids"])
wanted_ids = fail_ids | pass_ids
out_path = pathlib.Path(cfg["out_path"])
max_events_per_test = int(cfg.get("max_events", 35000))

_file_cache = {}
traces_by_id = {}

def _is_repo_file(filename):
    if not filename or filename[0] == "<":
        return None
    if filename in _file_cache:
        return _file_cache[filename]
    if not filename.startswith(cow_prefix):
        _file_cache[filename] = None
        return None
    rel = filename[len(cow_prefix):].replace(os.sep, "/")
    base = rel.rsplit("/", 1)[-1]
    if (
        rel.startswith(".brain")
        or rel.startswith("tests/")
        or "/tests/" in ("/" + rel)
        or base.startswith("test_")
        or base.endswith("_test.py")
    ):
        _file_cache[filename] = None
        return None
    _file_cache[filename] = rel
    return rel

def _summarize_val(v, depth=0):
    tname = type(v).__name__
    is_iter_only = isinstance(v, collections.abc.Iterator) and not isinstance(v, (collections.abc.Sequence, collections.abc.Mapping, str, bytes))
    info = {
        "type": tname,
        "is_none": v is None,
        "truthy": None,
        "repr": None,
        "len": None,
        "is_single_pass_iter": is_iter_only,
        "id": id(v),
    }
    try:
        info["truthy"] = bool(v)
    except Exception:
        info["truthy"] = None
    if isinstance(v, (bool, int, float, str, bytes)):
        r = repr(v)
        if len(r) <= 120:
            info["repr"] = r
    elif v is None:
        info["repr"] = "None"
    elif isinstance(v, (tuple, list, set, frozenset, dict)):
        info["len"] = len(v)
        if len(v) <= 6 and all(isinstance(x, (bool, int, float, str, type(None))) for x in (v.values() if isinstance(v, dict) else v)):
            r = repr(v)
            if len(r) <= 120:
                info["repr"] = r
    if depth == 0 and not isinstance(v, (bool, int, float, str, bytes, tuple, list, set, dict, type(None))):
        attrs = {}
        try:
            d = getattr(v, "__dict__", None)
            if isinstance(d, dict):
                for ak, av in list(d.items())[:22]:
                    if isinstance(ak, str) and not ak.startswith("__"):
                        attrs[ak] = _summarize_val(av, depth=1)
            for ak in ("name", "default", "required", "envvar", "show_envvar", "options_metavar", "on_setattr", "converter", "type", "opts", "secondary_opts", "multiple", "nargs", "is_flag", "flag_value"):
                if ak not in attrs and hasattr(v, ak):
                    try:
                        attrs[ak] = _summarize_val(getattr(v, ak), depth=1)
                    except Exception:
                        pass
        except Exception:
            pass
        if attrs:
            info["attrs"] = attrs
    return info

class _BrainTracePlugin:
    def pytest_collection_modifyitems(self, items):
        if wanted_ids and not any(w.startswith("<") for w in wanted_ids):
            kept = [it for it in items if it.nodeid in wanted_ids]
            if kept:
                items[:] = kept

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_call(self, item):
        nid = item.nodeid
        trace_all = (not wanted_ids) or any(w.startswith("<") for w in wanted_ids)
        if not trace_all and nid not in wanted_ids:
            yield
            return
        line_hits = {}
        last_seq = {}
        frame_samples = {}
        prev_line_in_frame = {}
        producer_lines = {}
        exceptions_seen = []
        events = [0]
        aborted_loop = [False]

        def _tracer(frame, event, arg):
            if events[0] >= max_events_per_test:
                aborted_loop[0] = True
                raise TimeoutError("COGS_INFINITE_LOOP_TRACE_LIMIT")
            rel = _is_repo_file(frame.f_code.co_filename)
            if rel is None:
                return None
            events[0] += 1
            lineno = frame.f_lineno
            key = f"{rel}:{lineno}"
            line_hits[key] = line_hits.get(key, 0) + 1
            last_seq[key] = events[0]
            fid = id(frame)
            prev_ln = prev_line_in_frame.get(fid)
            prev_line_in_frame[fid] = lineno
            if event in ("line", "exception"):
                samples = frame_samples.setdefault(key, [])
                if len(samples) < 6:
                    snap = {}
                    for k, v in list(frame.f_locals.items())[:22]:
                        if isinstance(k, str) and not k.startswith("__"):
                            sv = _summarize_val(v, depth=0)
                            snap[k] = sv
                            if sv.get("is_single_pass_iter") and prev_ln is not None:
                                producer_lines[f"{rel}:{prev_ln}"] = k
                    sentinels = {}
                    for gk, gv in list(frame.f_globals.items())[:60]:
                        if isinstance(gk, str) and not gk.startswith("_"):
                            try:
                                mod_dict = getattr(gv, "__dict__", None)
                                if isinstance(mod_dict, dict):
                                    for mk, mv in list(mod_dict.items())[:25]:
                                        if isinstance(mk, str) and mk.isupper():
                                            sentinels[f"{gk}.{mk}"] = id(mv)
                            except Exception:
                                pass
                    samples.append({"locals": snap, "sentinels": sentinels})
            if event == "exception" and len(exceptions_seen) < 35:
                exc_type, exc_val, _ = arg
                exceptions_seen.append({
                    "rel_path": rel,
                    "lineno": lineno,
                    "func": frame.f_code.co_name,
                    "exc_type": getattr(exc_type, "__name__", str(exc_type)),
                    "exc_msg": str(exc_val)[:200],
                })
            return _tracer

        sys.settrace(_tracer)
        call_failed = False
        try:
            outcome = yield
            call_failed = getattr(outcome, "excinfo", None) is not None
        finally:
            sys.settrace(None)
            traces_by_id[nid] = {
                "line_hits": line_hits,
                "last_seq": last_seq,
                "frame_samples": frame_samples,
                "producer_lines": producer_lines,
                "exceptions_seen": exceptions_seen,
                "call_failed": bool(call_failed or aborted_loop[0]),
            }

target_args = cfg.get("target_nodeids") or [test_file]
try:
    pytest.main(
        [*target_args, "-q", "--tb=no", "-p", "no:cacheprovider", "-W", "ignore"],
        plugins=[_BrainTracePlugin()],
    )
except BaseException:
    pass
finally:
    out_path.write_text(json.dumps(traces_by_id), encoding="utf-8")
'''


def _collect_python_traces(
    mental: ExecutableMentalModel,
    failing_tests: list[str],
    passing_tests: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    tracer_file = mental.pycache_dir / "_brain_child_tracer.py"
    tracer_file.write_text(_CHILD_TRACER_SCRIPT, encoding="utf-8")
    out_json = mental.pycache_dir / "traces_combined.json"
    if out_json.exists():
        out_json.unlink()
    test_file = mental.test_target or (failing_tests[0].split("::")[0] if failing_tests and not failing_tests[0].startswith("<") else "tests")
    sel_fail = failing_tests[:4]
    sel_pass = passing_tests[:6]
    explicit_ids = [nid for nid in (sel_fail + sel_pass) if nid and not nid.startswith("<")]
    cfg = json.dumps(
        {
            "cow_root": str(mental.cow_root),
            "test_file": test_file,
            "target_nodeids": explicit_ids if explicit_ids else [test_file],
            "fail_ids": sel_fail,
            "pass_ids": sel_pass,
            "out_path": str(out_json),
            "max_events": 35000,
        }
    )
    try:
        subprocess.run(
            [mental.py_exe, str(tracer_file), cfg],
            cwd=mental.cow_root,
            env=mental._python_env(),
            capture_output=True,
            text=True,
            timeout=18.0,
            stdin=subprocess.DEVNULL,
        )
        if out_json.exists():
            combined = json.loads(out_json.read_text(encoding="utf-8"))
            if any(x.startswith("<") for x in sel_fail):
                disc_fail = [k for k, v in combined.items() if v.get("call_failed")]
                disc_pass = [k for k, v in combined.items() if not v.get("call_failed")]
                if disc_fail:
                    failing_tests[:] = disc_fail
                    passing_tests[:] = disc_pass
                    sel_fail = disc_fail[:4]
                    sel_pass = disc_pass[:6]
            fail_traces = [combined[k] for k in sel_fail if k in combined]
            pass_traces = [combined[k] for k in sel_pass if k in combined]
            return fail_traces, pass_traces
    except Exception:
        pass
    return [], []


def _is_auxiliary_harness(rel_path: str, test_target: str | None) -> bool:
    if not rel_path.endswith("/testing.py"):
        return False
    if test_target and "testing" in pathlib.Path(test_target).stem.lower():
        return False
    return True


def _compute_ochiai_suspiciousness(
    fail_traces: list[dict[str, Any]],
    pass_traces: list[dict[str, Any]],
    test_target: str | None = None,
) -> list[tuple[str, int, float]]:
    total_fail = max(len(fail_traces), 1)
    ef: dict[str, int] = {}
    ep: dict[str, int] = {}
    max_seq: dict[str, int] = {}
    for ft in fail_traces:
        lseq = ft.get("last_seq") or {}
        for key in ft.get("line_hits", {}):
            ef[key] = ef.get(key + "", 0) + 1
            if lseq.get(key, 0) > max_seq.get(key, 0):
                max_seq[key] = lseq[key]
    for pt in pass_traces:
        for key in pt.get("line_hits", {}):
            ep[key] = ep.get(key, 0) + 1

    scored: list[tuple[str, int, float, int]] = []
    for key, f_cnt in ef.items():
        rel, ln_s = key.rsplit(":", 1)
        harness_penalty = 0.25 if _is_auxiliary_harness(rel, test_target) else 0.0
        p_cnt = ep.get(key, 0)
        denom = (total_fail * (f_cnt + p_cnt)) ** 0.5
        score = max(0.0, (f_cnt / denom if denom > 0 else 0.0) - harness_penalty)
        scored.append((rel, int(ln_s), round(score, 4), max_seq.get(key, 0)))
    ranked = sorted(scored, key=lambda x: (-x[2], -x[3], x[0], x[1]))
    return [(r, l, s) for r, l, s, _ in ranked]


# ---------------------------------------------------------------------------
# Counterexample-Guided Observational Equivalence Graph (ObsEGraph)
# ---------------------------------------------------------------------------


def _eval_snapshot_expr(expr_code: str, sample: dict[str, Any]) -> Any:
    """Safely evaluate a candidate expression over a recorded frame snapshot to build
    its Observational Equivalence Signature without spawning subprocesses."""
    locs = sample.get("locals") or {}
    sentinels = sample.get("sentinels") or {}

    class _ProxyObj:
        def __init__(self, summary: dict[str, Any]) -> None:
            self._s = summary

        def __bool__(self) -> bool:
            t = self._s.get("truthy")
            return bool(t) if t is not None else not bool(self._s.get("is_none"))

        def __eq__(self, other: object) -> bool:
            if isinstance(other, tuple) and len(other) == 2 and other[0] == "__ID__":
                return self._s.get("id") is not None and self._s.get("id") == other[1]
            if isinstance(other, _ProxyObj):
                return self._s.get("id") is not None and self._s.get("id") == other._s.get("id")
            return False

        def __getattr__(self, item: str) -> Any:
            attrs = self._s.get("attrs") or {}
            if item in attrs:
                return _rehydrate(attrs[item])
            raise AttributeError(item)

    class _SentinelNamespace:
        def __init__(self, prefix: str) -> None:
            self._prefix = prefix

        def __getattr__(self, item: str) -> Any:
            full = f"{self._prefix}.{item}"
            if full in sentinels:
                return ("__ID__", sentinels[full])
            raise AttributeError(item)

    def _rehydrate(summary: dict[str, Any]) -> Any:
        if summary.get("is_none"):
            return None
        rep = summary.get("repr")
        if rep is not None:
            try:
                return ast.literal_eval(rep)
            except Exception:
                pass
        tp = summary.get("type")
        if tp == "str":
            return "__NONEMPTY_STR__" if summary.get("truthy") else ""
        if tp == "bool":
            return bool(summary.get("truthy"))
        if summary.get("attrs"):
            return _ProxyObj(summary)
        return _ProxyObj(summary)

    env: dict[str, Any] = {
        "__builtins__": {
            "len": len,
            "bool": bool,
            "isinstance": isinstance,
            "str": str,
            "int": int,
            "float": float,
            "list": list,
            "tuple": tuple,
            "dict": dict,
            "set": set,
        }
    }
    for k, v in locs.items():
        env[k] = _rehydrate(v)
    for sk in sentinels:
        mod_name = sk.split(".", 1)[0]
        if mod_name not in env:
            env[mod_name] = _SentinelNamespace(mod_name)

    # Translate `x is not mod.SENT` -> `x != mod.SENT` only for tuple-ID proxies
    try:
        val = eval(expr_code, env, {})  # noqa: S307 - restricted builtins on own snapshot dict
        return val
    except Exception as exc:
        return ("__EXC__", type(exc).__name__)


def _extract_proximity_atoms(
    source_text: str,
    target_line: int,
    fail_samples: list[dict[str, Any]],
    *,
    parsed_tree: ast.AST | None = None,
) -> dict[str, list[str]]:
    """Collect candidate variables, 1-hop attributes, module sentinels, and module lexical
    literals strictly from the target function/class/module (Lexical & Type Alphabet Closure)."""
    attr_exprs: list[str] = []
    var_exprs: list[str] = []
    str_literals: list[str] = []
    sentinel_exprs: list[str] = []

    if parsed_tree is not None:
        tree = parsed_tree
    else:
        try:
            tree = ast.parse(source_text)
        except SyntaxError:
            return {"attrs": [], "vars": [], "literals": [], "sentinels": []}

    enclosing_fn = None
    enclosing_if = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.lineno <= target_line <= getattr(node, "end_lineno", node.lineno):
                enclosing_fn = node
        if isinstance(node, (ast.If, ast.While)):
            if node.test.lineno <= target_line <= getattr(node.test, "end_lineno", node.test.lineno):
                if enclosing_if is None or node.test.lineno >= enclosing_if.test.lineno:
                    enclosing_if = node

    # Ring 1: guarded body first (highest causal signal!), then Ring 2: enclosing function
    search_scopes = []
    if enclosing_if is not None:
        search_scopes.extend(enclosing_if.body)
        search_scopes.extend(enclosing_if.orelse)
    if enclosing_fn is not None:
        search_scopes.append(enclosing_fn)

    seen_a: set[str] = set()
    seen_v: set[str] = set()
    seen_lit: set[str] = set()

    for scope in search_scopes:
        for sub in ast.walk(scope):
            if isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Name):
                chain = f"{sub.value.id}.{sub.attr}"
                if chain not in seen_a and not sub.attr.startswith("__"):
                    seen_a.add(chain)
                    attr_exprs.append(chain)
            elif isinstance(sub, ast.Name) and not sub.id.startswith("__"):
                if sub.id not in {"self", "cls", "True", "False", "None"} and sub.id not in seen_v:
                    seen_v.add(sub.id)
                    var_exprs.append(sub.id)
            elif isinstance(sub, ast.Constant) and isinstance(sub.value, str) and len(sub.value) <= 40:
                if sub.value not in seen_lit:
                    seen_lit.add(sub.value)
                    str_literals.append(sub.value)

    # Also collect protocol/dunder string constants in the file if the site itself tests a dunder name
    for sub in ast.walk(tree):
        if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
            if sub.value.startswith("__") and sub.value.endswith("__") and sub.value not in seen_lit:
                seen_lit.add(sub.value)
                str_literals.append(sub.value)

    # Also add live 1-hop attributes & module sentinels observed in frame snapshots
    for smp in fail_samples:
        for s_key in (smp.get("sentinels") or {}):
            if s_key not in sentinel_exprs:
                sentinel_exprs.append(s_key)
        for loc_name, loc_info in (smp.get("locals") or {}).items():
            for ak in (loc_info.get("attrs") or {}):
                chain = f"{loc_name}.{ak}"
                if chain not in seen_a:
                    seen_a.add(chain)
                    attr_exprs.append(chain)

    return {
        "attrs": attr_exprs[:24],
        "vars": var_exprs[:20],
        "literals": str_literals[:16],
        "sentinels": sentinel_exprs[:16],
    }


def _z3_is_contingent_branch_formula(
    emit_src: str,
    old_src: str,
    all_samples: list[dict[str, Any]],
) -> bool:
    """Use Z3 to prove that `emit_src` is logically contingent (neither a Boolean/None
    tautology like `exc is None or exc is not None` nor a contradiction like
    `exception is not None and not exception` on always-truthy types) and non-equivalent to `old_src`."""
    try:
        new_ast = ast.parse(emit_src, mode="eval").body
        old_ast = ast.parse(old_src, mode="eval").body
    except SyntaxError:
        return False
    if z3 is None:
        return ast.dump(new_ast) != ast.dump(old_ast)

    always_truthy_when_non_none: set[str] = set()
    falsy_seen_or_builtin: set[str] = set()
    builtin_falsy_capable = {
        "bool", "int", "float", "complex", "str", "bytes", "bytearray",
        "list", "tuple", "dict", "set", "frozenset", "range", "NoneType",
    }
    for smp in all_samples:
        for k, inf in (smp.get("locals") or {}).items():
            tp = str((inf or {}).get("type") or "")
            if tp in builtin_falsy_capable or (inf or {}).get("truthy") is False:
                falsy_seen_or_builtin.add(k)
            elif tp and not inf.get("is_none") and inf.get("truthy") is True:
                always_truthy_when_non_none.add(k)
            for ak, ainf in ((inf or {}).get("attrs") or {}).items():
                atp = str((ainf or {}).get("type") or "")
                ak_key = f"{k}.{ak}"
                if atp in builtin_falsy_capable or (ainf or {}).get("truthy") is False:
                    falsy_seen_or_builtin.add(ak_key)
                elif atp and not ainf.get("is_none") and ainf.get("truthy") is True:
                    always_truthy_when_non_none.add(ak_key)
    always_truthy_when_non_none -= falsy_seen_or_builtin

    sym_none: dict[str, z3.BoolRef] = {}
    sym_truthy: dict[str, z3.BoolRef] = {}
    sym_str: dict[str, z3.BoolRef] = {}
    sym_opaque: dict[str, z3.BoolRef] = {}
    axioms: list[z3.BoolRef] = []

    def _term_vars(term_key: str) -> tuple[z3.BoolRef, z3.BoolRef, z3.BoolRef]:
        if term_key not in sym_none:
            n_v = z3.Bool(f"none_{term_key}")
            t_v = z3.Bool(f"truthy_{term_key}")
            s_v = z3.Bool(f"str_{term_key}")
            sym_none[term_key] = n_v
            sym_truthy[term_key] = t_v
            sym_str[term_key] = s_v
            axioms.append(z3.Implies(n_v, z3.Not(t_v)))
            axioms.append(z3.Implies(n_v, z3.Not(s_v)))
            if term_key in always_truthy_when_non_none:
                axioms.append(z3.Implies(z3.Not(n_v), t_v))
        return sym_none[term_key], sym_truthy[term_key], sym_str[term_key]

    def _encode(node: ast.expr) -> z3.BoolRef:
        if isinstance(node, ast.BoolOp):
            subs = [_encode(v) for v in node.values]
            return z3.And(*subs) if isinstance(node.op, ast.And) else z3.Or(*subs)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return z3.Not(_encode(node.operand))
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and len(node.comparators) == 1:
            op = node.ops[0]
            comp = node.comparators[0]
            lhs_k = ast.unparse(node.left).strip()
            if isinstance(comp, ast.Constant) and comp.value is None and isinstance(op, (ast.Is, ast.IsNot)):
                n_v, _, _ = _term_vars(lhs_k)
                return n_v if isinstance(op, ast.Is) else z3.Not(n_v)
            if isinstance(comp, ast.Constant) and comp.value is not None and isinstance(op, ast.Eq):
                n_v, t_v, _ = _term_vars(lhs_k)
                eq_sym = sym_opaque.setdefault(ast.unparse(node).strip(), z3.Bool(f"op_{len(sym_opaque)}"))
                axioms.append(z3.Implies(eq_sym, z3.Not(n_v)))
                axioms.append(z3.Implies(eq_sym, t_v if bool(comp.value) else z3.Not(t_v)))
                return eq_sym
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "isinstance" and len(node.args) == 2:
            arg0 = ast.unparse(node.args[0]).strip()
            arg1 = ast.unparse(node.args[1]).strip()
            if arg1 == "str":
                _, _, s_v = _term_vars(arg0)
                return s_v
        if isinstance(node, (ast.Name, ast.Attribute)):
            tk = ast.unparse(node).strip()
            _, t_v, _ = _term_vars(tk)
            return t_v
        canon = ast.unparse(node).strip()
        if canon not in sym_opaque:
            sym_opaque[canon] = z3.Bool(f"op_{len(sym_opaque)}")
        return sym_opaque[canon]

    f_new = _encode(new_ast)
    f_old = _encode(old_ast)

    s_sat = z3.Solver()
    s_sat.add(*axioms, f_new)
    if s_sat.check() != z3.sat:
        return False

    s_fal = z3.Solver()
    s_fal.add(*axioms, z3.Not(f_new))
    if s_fal.check() != z3.sat:
        return False

    s_diff = z3.Solver()
    s_diff.add(*axioms, f_new != f_old)
    return s_diff.check() == z3.sat


def synthesize_obsegraph_branch_repairs(
    *,
    source_text: str,
    line_no: int,
    pass_samples: list[dict[str, Any]],
    fail_samples: list[dict[str, Any]],
    parsed_tree: ast.AST | None = None,
    crashed_at_line: bool = False,
) -> tuple[list[tuple[str, str]], int]:
    """Counterexample-Guided Observational E-Graph over branch/ternary conditions at `line_no`.
    Collapses candidate predicates by their Boolean truth-vector across `(pass_samples, fail_samples)`
    and returns `(patched_source, description)` sorted by minimal AST complexity."""
    if parsed_tree is not None:
        tree = parsed_tree
    else:
        try:
            tree = ast.parse(source_text)
        except SyntaxError:
            return [], 0

    lines = source_text.splitlines(keepends=True)
    if not (1 <= line_no <= len(lines)):
        return [], 0

    cond_nodes: list[ast.expr] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.If, ast.IfExp)):
            if node.test.lineno <= line_no <= getattr(node.test, "end_lineno", node.test.lineno):
                cond_nodes.append(node.test)
    if not cond_nodes:
        return [], 0

    target_cond = min(
        cond_nodes,
        key=lambda n: (getattr(n, "end_lineno", n.lineno) - n.lineno, getattr(n, "end_col_offset", 0) - n.col_offset),
    )
    if target_cond.lineno != getattr(target_cond, "end_lineno", target_cond.lineno):
        return [], 0

    old_cond_src = lines[target_cond.lineno - 1][target_cond.col_offset : target_cond.end_col_offset]
    atoms = _extract_proximity_atoms(source_text, line_no, fail_samples, parsed_tree=tree)

    old_stripped = old_cond_src.strip()
    # Ring-0 subjects literally inside `target_cond`, followed by Ring-1/2 attrs and vars
    cond_subjects: list[str] = []
    for sub in ast.walk(target_cond):
        if isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Name):
            ch = f"{sub.value.id}.{sub.attr}"
            if ch not in cond_subjects:
                cond_subjects.append(ch)
        elif isinstance(sub, ast.Name) and sub.id not in {"self", "cls", "True", "False", "None"}:
            if sub.id not in cond_subjects:
                cond_subjects.append(sub.id)

    terms: list[str] = []
    for cand_t in cond_subjects + atoms["attrs"][:14] + atoms["vars"][:10]:
        if cand_t not in terms:
            terms.append(cand_t)

    # Atomic separating predicates constructed strictly from the module's lexical & type alphabet
    atomic_preds: list[str] = []
    type_guard_preds: list[str] = []
    compares_to_str = isinstance(target_cond, ast.Compare) and any(
        isinstance(c, ast.Constant) and isinstance(c.value, str) for c in target_cond.comparators
    )
    for t in terms[:22]:
        # Type-guard synthesis ONLY when `target_cond` compares against a `str` OR `t` was observed as `str` in `pass_samples`
        seen_as_str_in_pass = any(
            ((ps.get("locals") or {}).get(t.split(".")[0]) or {}).get("type") == "str"
            for ps in pass_samples
        )
        if compares_to_str or (crashed_at_line and seen_as_str_in_pass):
            for smp in fail_samples:
                base = t.split(".")[0]
                linfo = (smp.get("locals") or {}).get(base)
                if linfo and not linfo.get("is_none") and linfo.get("type") not in {"str", "bool"}:
                    tg = f"isinstance({t}, str)"
                    if tg not in type_guard_preds:
                        type_guard_preds.append(tg)
        if t != old_stripped:
            atomic_preds.append(f"{t} is not None")
            atomic_preds.append(f"not {t}")
            atomic_preds.append(f"{t}")
            atomic_preds.append(f"{t} is None")
    atomic_preds = (type_guard_preds + atomic_preds) if (crashed_at_line or compares_to_str) else atomic_preds

    # Sentinel disambiguation (e.g. `a.on_setattr is not setters.NO_OP`)
    for t in atoms["attrs"][:12]:
        for sent in atoms["sentinels"][:10]:
            atomic_preds.append(f"{t} != {sent}")  # evaluated in ObsEGraph; emitted as `is not`

    # Set/tuple membership extension when `old_cond` compares against a string literal
    # (disabled when crashed_at_line=True because `lhs in (...)` still invokes `lhs.__eq__` unguarded)
    if not crashed_at_line and isinstance(target_cond, ast.Compare) and len(target_cond.ops) == 1 and len(target_cond.comparators) == 1:
        lhs_src = ast.unparse(target_cond.left)
        comp = target_cond.comparators[0]
        if isinstance(comp, ast.Constant) and isinstance(comp.value, str):
            existing_lit = comp.value
            for lit in atoms["literals"]:
                if lit != existing_lit:
                    if isinstance(target_cond.ops[0], ast.NotEq):
                        atomic_preds.append(f"__SET_NOT_IN__:{lhs_src}:{existing_lit!r}:{lit!r}")
                    elif isinstance(target_cond.ops[0], ast.Eq):
                        atomic_preds.append(f"__SET_IN__:{lhs_src}:{existing_lit!r}:{lit!r}")

    def _is_non_bool_falsey_in_fail(expr_s: str) -> bool:
        for smp in fail_samples:
            locs = smp.get("locals") or {}
            if "." in expr_s:
                b_n, a_n = expr_s.split(".", 1)
                inf = ((locs.get(b_n) or {}).get("attrs") or {}).get(a_n)
            else:
                inf = locs.get(expr_s)
            if inf and not inf.get("is_none") and inf.get("truthy") is False and inf.get("type") != "bool":
                return True
        return False

    # Build full candidate boolean formulas in causal proximity order (Ring 1 guarded body first!)
    candidate_formulas: list[tuple[str, str]] = []  # (eval_formula, emit_source)
    if re.match(r"^[A-Za-z_][\w\.]*$", old_stripped) and _is_non_bool_falsey_in_fail(old_stripped):
        candidate_formulas.append((f"({old_cond_src}) is not None", f"{old_cond_src} is not None"))
    if (
        isinstance(target_cond, ast.Compare)
        and len(target_cond.ops) == 1
        and len(target_cond.comparators) == 1
        and isinstance(target_cond.comparators[0], ast.Constant)
        and target_cond.comparators[0].value is None
    ):
        lhs_none_s = ast.unparse(target_cond.left).strip()
        if _is_non_bool_falsey_in_fail(lhs_none_s):
            if isinstance(target_cond.ops[0], ast.IsNot):
                candidate_formulas.append((f"bool({lhs_none_s})", lhs_none_s))
            elif isinstance(target_cond.ops[0], ast.Is):
                candidate_formulas.append((f"not ({lhs_none_s})", f"not {lhs_none_s}"))
    if isinstance(target_cond, ast.BoolOp) and isinstance(target_cond.op, ast.And):
        for idx, sub_v in enumerate(target_cond.values):
            sub_s = ast.unparse(sub_v)
            if re.match(r"^[A-Za-z_][\w\.]*$", sub_s) and _is_non_bool_falsey_in_fail(sub_s):
                rebuilt = " and ".join(
                    (f"({sub_s} is not None)" if j == idx else ast.unparse(v))
                    for j, v in enumerate(target_cond.values)
                )
                candidate_formulas.append((rebuilt, rebuilt))

    for p in atomic_preds:
        if p.startswith("__SET_NOT_IN__:"):
            _, lhs_s, l1, l2 = p.split(":", 3)
            expr_s = f"{lhs_s} not in ({l1}, {l2})"
            candidate_formulas.append((expr_s, expr_s))
            continue
        if p.startswith("__SET_IN__:"):
            _, lhs_s, l1, l2 = p.split(":", 3)
            expr_s = f"{lhs_s} in ({l1}, {l2})"
            candidate_formulas.append((expr_s, expr_s))
            continue
        emit_p = p
        if " != " in p and any(p.endswith(s) for s in atoms["sentinels"]):
            emit_p = p.replace(" != ", " is not ")
        # Direct replacement ONLY on Ternary (`a if cond else b`), never deleting an `if` guard's subject
        if isinstance(target_cond, ast.IfExp) and not p.startswith("not ") and "is None" not in p:
            if emit_p != old_stripped:
                candidate_formulas.append((p, emit_p))
        if pass_samples or crashed_at_line or "is not " in emit_p:
            candidate_formulas.append(
                (
                    f"({p}) and ({old_cond_src})",
                    f"{emit_p} and {old_cond_src}"
                    if (crashed_at_line or p.startswith("isinstance"))
                    else f"{old_cond_src} and {emit_p}",
                )
            )
        if not crashed_at_line:
            candidate_formulas.append((f"({old_cond_src}) or ({p})", f"{old_cond_src} or {emit_p}"))

    # Observational Equivalence Collapse across `(pass_samples, fail_samples)`
    eclasses: dict[tuple[Any, ...], tuple[str, str]] = {}
    evaluated_count = 0
    all_samples = pass_samples + fail_samples
    n_pass = len(pass_samples)
    if all_samples:
        pass_old = tuple(bool(_eval_snapshot_expr(old_cond_src, s)) for s in pass_samples)
        fail_old = (
            tuple("__CRASH__" for _ in fail_samples)
            if crashed_at_line
            else tuple(bool(_eval_snapshot_expr(old_cond_src, s)) for s in fail_samples)
        )
        old_vec: tuple[Any, ...] = pass_old + fail_old
    else:
        old_vec = ()

    for ord_idx, (eval_f, emit_s) in enumerate(candidate_formulas):
        evaluated_count += 1
        if not all_samples:
            sig: tuple[Any, ...] = (emit_s,)
            eclasses.setdefault(sig, (eval_f, emit_s))
            continue
        vec = tuple(bool(_eval_snapshot_expr(eval_f, s)) for s in all_samples)
        if vec == old_vec:
            continue
        if n_pass > 0 and vec[:n_pass] != old_vec[:n_pass]:
            continue
        if len(fail_samples) > 0 and vec[-1] == old_vec[-1]:
            continue
        if not _z3_is_contingent_branch_formula(emit_s, old_cond_src, all_samples):
            continue
        sig = vec if n_pass >= 2 else (vec, ord_idx)
        if sig not in eclasses:
            eclasses[sig] = (eval_f, emit_s)

    out_patches: list[tuple[str, str]] = []
    ln_idx = target_cond.lineno - 1
    orig_line = lines[ln_idx]
    for _, (_, emit_s) in list(eclasses.items())[:8]:
        new_line = orig_line[: target_cond.col_offset] + emit_s + orig_line[target_cond.end_col_offset :]
        cand_lines = list(lines)
        cand_lines[ln_idx] = new_line
        patched_src = "".join(cand_lines)
        try:
            ast.parse(patched_src)
        except SyntaxError:
            continue
        out_patches.append((patched_src, f"ObsEGraph branch synthesis L{line_no}: `{old_cond_src}` -> `{emit_s}`"))

    return out_patches, evaluated_count


def synthesize_obsegraph_statement_and_value_repairs(
    *,
    source_text: str,
    line_no: int,
    pass_samples: list[dict[str, Any]],
    fail_samples: list[dict[str, Any]],
    escaping_exceptions: list[dict[str, Any]],
    parsed_tree: ast.AST | None = None,
    allow_iter_materialize: bool = False,
) -> tuple[list[tuple[str, str]], int]:
    """Synthesize multi-case value projections (STUN), return/call-arg substitutions,
    exception boundary extensions, and iterator/alias isolations at `line_no`."""
    if parsed_tree is not None:
        tree = parsed_tree
    else:
        try:
            tree = ast.parse(source_text)
        except SyntaxError:
            return [], 0

    lines = source_text.splitlines(keepends=True)
    if not (1 <= line_no <= len(lines)):
        return [], 0

    out: list[tuple[str, str]] = []
    eval_cnt = 0
    atoms = _extract_proximity_atoms(source_text, line_no, fail_samples, parsed_tree=tree)

    for node in ast.walk(tree):
        # 1. Exception handler tuple extension if an uncaught exception escaped inside this `try`
        if isinstance(node, ast.Try) and node.lineno <= line_no <= getattr(node, "end_lineno", node.lineno):
            for handler in node.handlers:
                if handler.type is not None and handler.lineno == handler.type.lineno:
                    h_line = lines[handler.type.lineno - 1]
                    old_exc_src = h_line[handler.type.col_offset : handler.type.end_col_offset]
                    for exc_rec in escaping_exceptions:
                        exc_name = str(exc_rec.get("exc_type") or "")
                        if (
                            exc_name
                            and exc_name.endswith("Error")
                            and exc_name not in {"AssertionError", "SyntaxError", "NameError", "AttributeError"}
                            and exc_name not in old_exc_src
                        ):
                            eval_cnt += 1
                            if old_exc_src.startswith("(") and old_exc_src.endswith(")"):
                                new_exc_src = old_exc_src[:-1] + f", {exc_name})"
                            else:
                                new_exc_src = f"({old_exc_src}, {exc_name})"
                            cand_lines = list(lines)
                            cand_lines[handler.type.lineno - 1] = (
                                h_line[: handler.type.col_offset] + new_exc_src + h_line[handler.type.end_col_offset :]
                            )
                            patched = "".join(cand_lines)
                            try:
                                ast.parse(patched)
                                out.append((patched, f"Causal exception boundary L{handler.lineno}: `{old_exc_src}` -> `{new_exc_src}`"))
                            except SyntaxError:
                                pass

        # 2. Assignment right-hand sides on `line_no`
        if isinstance(node, ast.Assign) and node.lineno == line_no == getattr(node, "end_lineno", node.lineno):
            rhs = node.value
            orig_line = lines[line_no - 1]
            rhs_src = orig_line[rhs.col_offset : rhs.end_col_offset]

            # 2a. STUN Conditional Collection Wrapping: `rv = [x]` -> `rv = [x] if x else []`
            if isinstance(rhs, ast.List) and len(rhs.elts) == 1:
                elt_src = ast.unparse(rhs.elts[0])
                eval_cnt += 1
                fail_falsey = any(not bool(_eval_snapshot_expr(elt_src, s)) for s in fail_samples) if fail_samples else True
                pass_truthy = all(bool(_eval_snapshot_expr(elt_src, s)) for s in pass_samples) if pass_samples else True
                if fail_falsey and pass_truthy:
                    stun_src = f"[{elt_src}] if {elt_src} else []"
                    cand_lines = list(lines)
                    cand_lines[line_no - 1] = orig_line[: rhs.col_offset] + stun_src + orig_line[rhs.end_col_offset :]
                    patched = "".join(cand_lines)
                    try:
                        ast.parse(patched)
                        out.append((patched, f"STUN conditional projection L{line_no}: `{rhs_src}` -> `{stun_src}`"))
                    except SyntaxError:
                        pass

            # 2b. Single-pass generator/iterator materialization ONLY when runtime or U-IR detected single-pass iterator!
            if allow_iter_materialize and isinstance(rhs, ast.Call):
                cname = ast.unparse(rhs.func)
                if cname not in {"tuple", "list", "set", "dict"}:
                    eval_cnt += 1
                    new_rhs = f"tuple({rhs_src})"
                    cand_lines = list(lines)
                    cand_lines[line_no - 1] = orig_line[: rhs.col_offset] + new_rhs + orig_line[rhs.end_col_offset :]
                    patched = "".join(cand_lines)
                    try:
                        ast.parse(patched)
                        out.append((patched, f"Iterator materialization L{line_no}: `{rhs_src}` -> `{new_rhs}`"))
                    except SyntaxError:
                        pass

        # 3. Return statement expressions / tuple slots / call argument forwarding
        if isinstance(node, ast.Return) and node.value is not None and node.lineno <= line_no <= getattr(node, "end_lineno", node.lineno):
            ret_val = node.value
            # 3a. Tuple return slot substitution & mutable-alias isolation (`return cmd_name, cmd, ...` -> `return cmd.name, ...` or `head.copy()`)
            if isinstance(ret_val, ast.Tuple) and ret_val.lineno == getattr(ret_val, "end_lineno", ret_val.lineno):
                r_line = lines[ret_val.lineno - 1]
                for elt in ret_val.elts:
                    if isinstance(elt, ast.Name):
                        old_name = elt.id
                        # Check 1-hop attributes on sibling tuple elements (`cmd.name`) or `.copy()`
                        for sib in ret_val.elts:
                            if sib is not elt and isinstance(sib, ast.Name):
                                for ak in ("name", "value", "id", "key"):
                                    cand_attr = f"{sib.id}.{ak}"
                                    if cand_attr in atoms["attrs"] or old_name.endswith(f"_{ak}") or old_name == ak:
                                        eval_cnt += 1
                                        cand_lines = list(lines)
                                        cand_lines[ret_val.lineno - 1] = (
                                            r_line[: elt.col_offset] + cand_attr + r_line[elt.end_col_offset :]
                                        )
                                        patched = "".join(cand_lines)
                                        try:
                                            ast.parse(patched)
                                            out.append((patched, f"ObsEGraph return-slot lineage L{ret_val.lineno}: `{old_name}` -> `{cand_attr}`"))
                                        except SyntaxError:
                                            pass
                        # Mutable alias `.copy()` if another tuple slot references `old_name`
                        other_refs = any(
                            any(isinstance(n, ast.Name) and n.id == old_name for n in ast.walk(sib))
                            for sib in ret_val.elts
                            if sib is not elt
                        )
                        if other_refs:
                            eval_cnt += 1
                            copy_expr = f"{old_name}.copy()"
                            cand_lines = list(lines)
                            cand_lines[ret_val.lineno - 1] = (
                                r_line[: elt.col_offset] + copy_expr + r_line[elt.end_col_offset :]
                            )
                            patched = "".join(cand_lines)
                            try:
                                ast.parse(patched)
                                out.append((patched, f"Alias escape isolation L{ret_val.lineno}: `{old_name}` -> `{copy_expr}`"))
                            except SyntaxError:
                                pass

    return out, eval_cnt


# ---------------------------------------------------------------------------
# Polyglot C/C++ & JS Z3 Bound / Null / Coupled Multi-File Synthesis
# ---------------------------------------------------------------------------


def _z3_proves_inclusive_bound_oob() -> bool:
    """Formal Z3 proof that `0 <= cursor <= n` indexing an `n`-element buffer `[0, n)`
    admits an out-of-bounds counterexample `cursor == n`, while `0 <= cursor < n` is safe."""
    if z3 is None:
        return True
    cursor = z3.Int("cursor")
    n = z3.Int("n")
    s_buggy = z3.Solver()
    s_buggy.add(n >= 0, cursor >= 0, cursor <= n, z3.Not(cursor < n))
    has_oob = s_buggy.check() == z3.sat

    s_fixed = z3.Solver()
    s_fixed.add(n >= 0, cursor >= 0, cursor < n, z3.Not(cursor < n))
    fixed_safe = s_fixed.check() == z3.unsat
    return has_oob and fixed_safe


def _extract_native_crash_progress(out: str, repo_root: pathlib.Path) -> tuple[int, str, str, int] | None:
    """Extract monotonic native crash progress `(pass_count, rel_path, fn_name, line_no)`
    from ASAN/UBSAN/Unity output; returns `None` on compiler failure or timeout."""
    if not out or out == "TIMEOUT":
        return None
    has_sanitizer_or_unity = (
        "AddressSanitizer" in out
        or "runtime error:" in out
        or ":FAIL" in out
        or ":PASS" in out
    )
    if ("error:" in out or "ld returned 1 exit status" in out) and not has_sanitizer_or_unity:
        return None
    pass_cnt = len(re.findall(r":PASS\b", out))
    for m_fr in re.finditer(r"#\d+\s+0x[0-9a-fA-F]+\s+in\s+([A-Za-z_]\w*)\s+([^\s:]+):(\d+)", out):
        fn_nm, fpath, ln_s = m_fr.group(1), m_fr.group(2), int(m_fr.group(3))
        if any(tok in fpath for tok in ("asan", "sanitizer", "/usr/", "libc", "unity.c")):
            continue
        base_nm = pathlib.Path(fpath).name
        if "test" in base_nm.lower():
            continue
        rel_match = base_nm
        for cand_p in repo_root.rglob(base_nm):
            rel_match = cand_p.relative_to(repo_root).as_posix()
            break
        return (pass_cnt, rel_match, fn_nm, ln_s)
    for m_ub in re.finditer(r"([^\s:]+):(\d+):\d+:\s+runtime error:", out):
        fpath, ln_s = m_ub.group(1), int(m_ub.group(2))
        base_nm = pathlib.Path(fpath).name
        if "test" not in base_nm.lower():
            return (pass_cnt, base_nm, "", ln_s)
    return (pass_cnt, "", "", 0)


def synthesize_polyglot_uir_z3_repairs(
    *,
    source_bytes: bytes,
    language: str,
    rel_path: str,
    target_func_name: str | None = None,
    cached_u_fns: list[UIRFunction] | None = None,
    hot_line: int | None = None,
) -> list[tuple[bytes, str]]:
    """First-principles cold-start synthesis (with zero stored laws!) over U-IR + Z3."""
    norm_lang = "cpp" if language in {"c", "cpp", "c++"} else language
    u_fns = cached_u_fns if cached_u_fns is not None else lower_source_to_uir(source_bytes, norm_lang, rel_path=rel_path)
    lines = source_bytes.decode("utf-8", errors="replace").splitlines(keepends=True)
    candidates: list[tuple[bytes, str]] = []

    for ufn in u_fns:
        if target_func_name and ufn.name != target_func_name:
            continue
        # Locate function body entry line (first line inside `{` for C/JS/Rust, or first statement for Python)
        body_entry_idx = max(0, ufn.start_line - 1)
        body_indent = "    "
        fn_body_txt = "".join(lines[max(0, ufn.start_line - 1) : min(len(lines), ufn.end_line)])
        cleanup_labels = list(dict.fromkeys(re.findall(r"\bgoto\s+([A-Za-z_]\w*)\s*;", fn_body_txt)))
        if norm_lang != "python":
            for scan_i in range(max(0, ufn.start_line - 1), min(len(lines), ufn.end_line)):
                if "{" in lines[scan_i]:
                    body_entry_idx = min(len(lines), scan_i + 1)
                    while body_entry_idx < min(len(lines), ufn.end_line):
                        dl = lines[body_entry_idx].strip()
                        if not dl or dl.startswith(("/*", "*", "//")):
                            body_entry_idx += 1
                            continue
                        if (
                            norm_lang == "cpp"
                            and dl.endswith(";")
                            and "->" not in dl
                            and not dl.startswith(("return", "if", "for", "while", "switch", "goto"))
                            and re.match(r"^(?:const\s+|unsigned\s+|signed\s+|struct\s+)*[A-Za-z_]\w*[\s\*]+[A-Za-z_]\w*\s*(?:=\s*[^;]+)?;$", dl)
                        ):
                            body_entry_idx += 1
                            continue
                        break
                    if body_entry_idx < len(lines):
                        m_ind = re.match(r"^\s*", lines[body_entry_idx])
                        if m_ind and m_ind.group(0).strip("\r\n"):
                            body_indent = m_ind.group(0)
                    break
        emitted_param_guards: set[str] = set()
        emitted_deref_sites: set[tuple[str, int]] = set()
        ordered_nodes = (
            sorted(ufn.nodes, key=lambda nd: abs(nd.start_line - hot_line))
            if hot_line is not None
            else list(ufn.nodes)
        )

        for node in ordered_nodes:
            # 1. Z3-backed loop-bound off-by-one repair across C/Python/JS/Rust/Go
            if (
                node.kind == "UIR_ITER_BOUNDED"
                and node.roles.get("bound_polarity") == "INCLUSIVE_LE"
                and node.roles.get("body_derefs_cursor") is True
                and _z3_proves_inclusive_bound_oob()
            ):
                old_span = source_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="replace")
                new_span = old_span
                if norm_lang == "python" and "range" in old_span:
                    new_span = re.sub(r"\+\s*1\b", "", old_span)
                elif norm_lang == "rust" and "..=" in old_span:
                    new_span = old_span.replace("..=", "..", 1)
                elif "<=" in old_span:
                    new_span = old_span.replace("<=", "<", 1)
                if new_span != old_span:
                    patched = source_bytes[: node.start_byte] + new_span.encode("utf-8") + source_bytes[node.end_byte :]
                    candidates.append((patched, f"Z3+UIR bound clamp in `{ufn.name}`: `{old_span}` -> `{new_span}`"))

            # 2. Dominating Null/Existence pre-guard invention across C/Python/JS
            if node.kind == "UIR_DEREF_LOAD" and not node.roles.get("dominated_by_null_guard"):
                base_var = str(node.roles.get("base_var") or "")
                deref_op = str(node.roles.get("deref_op") or "")
                if base_var and (base_var in ufn.params or norm_lang == "cpp"):
                    ret_expr = str(node.roles.get("default_return") or ufn.return_hint)
                    is_param = base_var in ufn.params
                    if is_param and base_var in emitted_param_guards:
                        continue
                    if is_param:
                        emitted_param_guards.add(base_var)
                    line_idx = body_entry_idx if (is_param and norm_lang != "python") else (node.start_line - 1)
                    if (base_var, line_idx) in emitted_deref_sites:
                        continue
                    emitted_deref_sites.add((base_var, line_idx))
                    if 0 <= line_idx < len(lines):
                        indent = body_indent if (is_param and norm_lang != "python") else re.match(r"^\s*", lines[line_idx]).group(0)
                        if norm_lang == "cpp":
                            if deref_op == "CHAINED_ARROW" or ("->" in base_var and not lines[line_idx].lstrip().startswith("return")):
                                stmt_s = lines[line_idx].strip()
                                if stmt_s.endswith(";"):
                                    wrapped = list(lines)
                                    wrapped[line_idx] = f"{indent}if ({base_var} != NULL) {{ {stmt_s} }}\n"
                                    candidates.append(("".join(wrapped).encode("utf-8"), f"Causal conditional null guard in `{ufn.name}` on `{base_var}`"))
                            for lbl in cleanup_labels[:1]:
                                if not is_param:
                                    g_goto = list(lines)
                                    g_goto.insert(line_idx, f"{indent}if ({base_var} == NULL) {{ goto {lbl}; }}\n")
                                    candidates.append(("".join(g_goto).encode("utf-8"), f"Causal cleanup-goto null guard in `{ufn.name}` on `{base_var}`"))
                            ret_cands = [ret_expr]
                            if "nan" in ret_expr.lower() or "0.0" in ret_expr:
                                for extra_rc in ["(double)0", "0"] + [p for p in ufn.params if p != base_var][:1]:
                                    if extra_rc not in ret_cands:
                                        ret_cands.append(extra_rc)
                            for rc in ret_cands:
                                ret_stmt = f"return {rc};" if rc != "" else "return;"
                                guard = f"{indent}if ({base_var} == NULL) {{ {ret_stmt} }}\n"
                                new_lines = list(lines)
                                new_lines.insert(line_idx, guard)
                                candidates.append(("".join(new_lines).encode("utf-8"), f"Causal null-deref guard in `{ufn.name}` on `{base_var}`"))
                            guard = ""
                        elif norm_lang == "python":
                            guard = f"{indent}if {base_var} is None:\n{indent}    return {ret_expr}\n"
                        elif norm_lang in {"javascript", "typescript"}:
                            guard = f"{indent}if ({base_var} === null || {base_var} === undefined) {{ return {ret_expr}; }}\n"
                        else:
                            guard = ""
                        if guard:
                            new_lines = list(lines)
                            new_lines.insert(line_idx, guard)
                            candidates.append(("".join(new_lines).encode("utf-8"), f"Causal null-deref guard in `{ufn.name}` on `{base_var}`"))

            # 3. Dominating Zero-Divisor guard invention
            if node.kind == "UIR_DIV_OP" and not node.roles.get("dominated_by_nonzero_guard"):
                div_var = str(node.roles.get("divisor_var") or "")
                ret_expr = str(node.roles.get("default_return") or ufn.return_hint)
                line_idx = node.start_line - 1
                if div_var and 0 <= line_idx < len(lines):
                    indent = re.match(r"^\s*", lines[line_idx]).group(0)
                    if norm_lang == "cpp":
                        ret_stmt = f"return {ret_expr};" if ret_expr != "" else "return;"
                        guard = f"{indent}if ({div_var} == 0) {{ {ret_stmt} }}\n"
                    elif norm_lang == "python":
                        for div_ret in (["0", ret_expr] if ret_expr != "0" else ["0"]):
                            g_py = f"{indent}if {div_var} == 0:\n{indent}    return {div_ret}\n"
                            new_lines = list(lines)
                            new_lines.insert(line_idx, g_py)
                            candidates.append(("".join(new_lines).encode("utf-8"), f"Causal zero-divisor guard in `{ufn.name}` on `{div_var}`"))
                        guard = ""
                    elif norm_lang in {"javascript", "typescript"}:
                        guard = f"{indent}if ({div_var} === 0) {{ return {ret_expr}; }}\n"
                    else:
                        guard = ""
                    if guard:
                        new_lines = list(lines)
                        new_lines.insert(line_idx, guard)
                        candidates.append(("".join(new_lines).encode("utf-8"), f"Causal zero-divisor guard in `{ufn.name}` on `{div_var}`"))

    return candidates


def _counterfactual_alpha_rename_python_test(test_source: str, failing_node_id: str) -> str | None:
    """Alpha-rename local dummy class/variable names inside the failing test function
    to falsify patches that overfit to test-specific dummy identifiers (e.g. `class C:`)."""
    fn_name = failing_node_id.split("::")[-1].split("[")[0]
    try:
        tree = ast.parse(test_source)
    except SyntaxError:
        return None

    lines = test_source.splitlines(keepends=True)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == fn_name:
            # Find any inner `class Dummy:` defined inside the test body
            for sub in ast.walk(node):
                if isinstance(sub, ast.ClassDef) and len(sub.name) <= 4:
                    old_cls = sub.name
                    new_cls = f"{old_cls}_AlphaProbe"
                    st = node.lineno - 1
                    en = getattr(node, "end_lineno", len(lines))
                    segment = "".join(lines[st:en])
                    renamed_seg = re.sub(rf"\b{re.escape(old_cls)}\b", new_cls, segment)
                    if renamed_seg != segment:
                        cand = "".join(lines[:st]) + renamed_seg + "".join(lines[en:])
                        try:
                            ast.parse(cand)
                            return cand
                        except SyntaxError:
                            return None
    return None


def _build_unified_diff(originals: dict[str, str], modified: dict[str, str]) -> str:
    chunks: list[str] = []
    for rel_path in sorted(modified):
        before = originals.get(rel_path, "").splitlines(keepends=True)
        after = modified[rel_path].splitlines(keepends=True)
        chunks.extend(
            difflib.unified_diff(before, after, fromfile=f"a/{rel_path}", tofile=f"b/{rel_path}")
        )
    return "".join(chunks)


def _extract_changed_hunk_and_fn(orig_txt: str, cand_txt: str) -> tuple[str, str, str]:
    orig_lines = orig_txt.splitlines()
    cand_lines = cand_txt.splitlines()
    sm = difflib.SequenceMatcher(a=orig_lines, b=cand_lines, autojunk=False)
    changed = [op for op in sm.get_opcodes() if op[0] != "equal"]
    if not changed:
        return "", "", ""
    i1, i2 = changed[0][1], changed[-1][2]
    j1, j2 = changed[0][3], changed[-1][4]
    orig_hunk = "\n".join(orig_lines[i1:i2]).strip()
    cand_hunk = "\n".join(cand_lines[j1:j2]).strip()
    fn_name = ""
    try:
        tree = ast.parse(orig_txt)
        probe_ln = max(1, i1 + 1)
        for nd in ast.walk(tree):
            if isinstance(nd, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if nd.lineno <= probe_ln <= getattr(nd, "end_lineno", nd.lineno):
                    fn_name = nd.name
    except SyntaxError:
        pass
    return orig_hunk, cand_hunk, fn_name


class CausalCEGISInventor:
    """Unified multi-file, polyglot (Python / C / C++ / JS) Causal Repair & Invention Engine."""

    def __init__(
        self,
        *,
        law_store_path: pathlib.Path | None = None,
        negative_store_path: pathlib.Path | None = None,
        enable_law_crystallization: bool = True,
        sandbox_budget: int = 36,
    ) -> None:
        resolved_law = law_store_path or DEFAULT_LAW_STORE_PATH
        resolved_neg = negative_store_path or (
            resolved_law.parent / "NEGATIVE_SPACE_INVARIANTS_V1.json"
            if law_store_path is not None
            else DEFAULT_NEGATIVE_STORE_PATH
        )
        self.law_store = SemanticCausalLawStore(resolved_law)
        self.negative_store = NegativeSpaceInvariantStore(resolved_neg)
        self.enable_law_crystallization = enable_law_crystallization
        self.sandbox_budget = sandbox_budget

    def solve_repository(
        self,
        repo_root: pathlib.Path,
        *,
        language: str = "python",
        test_target: str | None = None,
        custom_test_cmd: list[str] | None = None,
        problem_statement: str | None = None,
        timeout_sec: float = 25.0,
    ) -> InventedRepairResult:
        t0 = time.perf_counter()
        norm_lang = "cpp" if language in {"c", "cpp", "c++"} else language
        repo_root = pathlib.Path(repo_root).resolve()

        with ExecutableMentalModel(
            repo_root,
            language=norm_lang,
            test_target=test_target,
            custom_test_cmd=custom_test_cmd,
            timeout_sec=timeout_sec,
        ) as mental:
            abduced_repro_rel = "_cogs_abduced_issue_repro_test.py"
            baseline: TestRunVerdict | None = None

            def _try_abduce_from_issue() -> TestRunVerdict | None:
                if norm_lang != "python" or not problem_statement:
                    return None
                for cand_repro in extract_candidate_repro_tests_from_issue(repo_root, problem_statement):
                    repro_path = mental.cow_root / abduced_repro_rel
                    repro_path.write_text(cand_repro, encoding="utf-8")
                    mental.test_target = abduced_repro_rel
                    v_try = mental.run_oracle(
                        specific_target=abduced_repro_rel,
                        timeout_sec=min(8.0, timeout_sec),
                    )
                    bad_frag = any(
                        err_tok in v_try.output
                        for err_tok in ("SyntaxError", "IndentationError", "ModuleNotFoundError", "ImportError")
                    )
                    has_real_signal = ("AssertionError" in v_try.output) or any(
                        abduced_repro_rel not in m.group(1) and "pytest" not in m.group(1)
                        for m in re.finditer(r'File "([^"]+)", line \d+', v_try.output)
                    )
                    if not v_try.passed and v_try.failing_tests and not bad_frag and has_real_signal:
                        return v_try
                    if repro_path.exists():
                        repro_path.unlink()
                    mental.test_target = test_target
                return None

            if test_target is None and custom_test_cmd is None and problem_statement and norm_lang == "python":
                baseline = _try_abduce_from_issue()

            if baseline is None:
                baseline = mental.run_oracle()
                if (baseline.passed or not baseline.failing_tests) and problem_statement and norm_lang == "python":
                    ab_v = _try_abduce_from_issue()
                    if ab_v is not None:
                        baseline = ab_v

            if baseline.passed or not baseline.failing_tests:
                return InventedRepairResult(
                    solved=False,
                    stage="NO_FAILING_ORACLE_AT_BASELINE",
                    mechanism="NONE",
                    modified_files={},
                    unified_diff="",
                    sabotage_verified=False,
                    overfit_falsifier_passed=False,
                    neighbor_impact_passed=False,
                    crystallized_law_id=None,
                    candidates_evaluated_in_memory=0,
                    candidates_executed_in_sandbox=mental.simulations_run,
                    source_tree_unchanged=mental.verify_source_untouched(),
                    elapsed_ms=round((time.perf_counter() - t0) * 1000.0, 2),
                )

            causal_graph = InterproceduralCausalGraph(repo_root)

            # Fast static + traceback anchor extraction BEFORE paying for dynamic trace instrumentation
            fast_anchors: list[tuple[str, int]] = []
            for m_py in re.finditer(r'File "([^"]+)", line (\d+)', baseline.output):
                fpath = pathlib.Path(m_py.group(1))
                for known_rel in causal_graph.functions_by_file:
                    if m_py.group(1).endswith(known_rel) or known_rel == fpath.name:
                        fast_anchors.append((known_rel, int(m_py.group(2))))
            for m_ub in re.finditer(r"([^\s:]+):(\d+):\d+:\s+runtime error:", baseline.output):
                fpath = pathlib.Path(m_ub.group(1))
                for known_rel in causal_graph.functions_by_file:
                    if known_rel.endswith(fpath.name):
                        fast_anchors.append((known_rel, int(m_ub.group(2))))
            for m in _ASAN_FRAME_RE.finditer(baseline.output):
                fpath = pathlib.Path(m.group(2))
                for known_rel in causal_graph.functions_by_file:
                    if known_rel.endswith(fpath.name):
                        fast_anchors.append((known_rel, int(m.group(3))))
            for m_un in re.finditer(r"([^\s:]+):(\d+):[A-Za-z_]\w*:FAIL\b", baseline.output):
                fpath = pathlib.Path(m_un.group(1))
                for known_rel in causal_graph.functions_by_file:
                    if known_rel.endswith(fpath.name):
                        fast_anchors.append((known_rel, int(m_un.group(2))))
            for m in _JS_FRAME_RE.finditer(baseline.output):
                fpath = pathlib.Path(m.group(2))
                for known_rel in causal_graph.functions_by_file:
                    if known_rel.endswith(fpath.name):
                        fast_anchors.append((known_rel, int(m.group(3))))
            if not fast_anchors and test_target and test_target in causal_graph.file_imports:
                fast_anchors.append((test_target, 1))

            fast_cuts = causal_graph.trace_backward_causal_slice(fast_anchors[:12], max_hops=3)
            fast_recall_files: list[str] = []
            for cut in fast_cuts:
                if cut.rel_path not in fast_recall_files:
                    fast_recall_files.append(cut.rel_path)
            if not fast_recall_files:
                for rel in causal_graph.functions_by_file:
                    if not rel.startswith("test") and "/tests/" not in ("/" + rel):
                        fast_recall_files.append(rel)

            mem_eval_total = 0

            # ------------------------------------------------------------------
            # PHASE 1: Zero-Trace 1-Shot Universal Semantic Law Store Recall
            # ------------------------------------------------------------------
            if self.law_store.laws:
                phase1_hint: dict[str, Any] = {}
                if norm_lang == "python":
                    phase1_hint["assertion_literals"] = extract_test_spec_literals(
                        mental.cow_root, baseline.failing_tests
                    )
                phase1_targets: list[tuple[str, str | None]] = []
                for cut in fast_cuts[:4]:
                    if (cut.rel_path, cut.func_name) not in phase1_targets:
                        phase1_targets.append((cut.rel_path, cut.func_name))
                for rel_path in fast_recall_files[:8]:
                    if len(causal_graph.functions_by_file.get(rel_path, ())) <= 12:
                        if (rel_path, None) not in phase1_targets:
                            phase1_targets.append((rel_path, None))
                phase1_sim_cap = max(8, self.sandbox_budget // 3)
                for rel_path, tgt_fn_p1 in phase1_targets:
                    if mental.simulations_run >= phase1_sim_cap:
                        break
                    full_p = repo_root / rel_path
                    if not full_p.is_file():
                        continue
                    orig_bytes = full_p.read_bytes()
                    law_cands = self.law_store.match_and_compile_candidates(
                        orig_bytes,
                        norm_lang,
                        rel_path=rel_path,
                        target_func_name=tgt_fn_p1,
                        runtime_hint=phase1_hint,
                    )
                    for law, patched_bytes, desc in law_cands:
                        if mental.simulations_run >= phase1_sim_cap:
                            break
                        mem_eval_total += 1
                        verdict_res = self._verify_and_finalize_patch(
                            mental=mental,
                            causal_graph=causal_graph,
                            repo_root=repo_root,
                            baseline=baseline,
                            file_patches={rel_path: patched_bytes.decode("utf-8", errors="replace")},
                            mechanism=f"SEMANTIC_LAW_RECALL:{law.law_id}",
                            description=desc,
                            norm_lang=norm_lang,
                            mem_eval_total=mem_eval_total,
                            t0=t0,
                            already_law_id=law.law_id,
                        )
                        if verdict_res is not None:
                            return verdict_res

            # ------------------------------------------------------------------
            # PHASE 2: Dynamic Causal Spectrum + ObsEGraph + Z3 Cold Invention
            # ------------------------------------------------------------------
            anchors: list[tuple[str, int]] = list(fast_anchors)
            fail_traces: list[dict[str, Any]] = []
            pass_traces: list[dict[str, Any]] = []
            ochiai_ranked: list[tuple[str, int, float]] = []

            if norm_lang == "python":
                fail_traces, pass_traces = _collect_python_traces(
                    mental, baseline.failing_tests, baseline.passing_tests
                )
                ochiai_ranked = _compute_ochiai_suspiciousness(
                    fail_traces, pass_traces, test_target=test_target
                )
                for rel, ln, _ in ochiai_ranked[:18]:
                    anchors.append((rel, ln))
            elif not anchors:
                for rel, ufns in causal_graph.functions_by_file.items():
                    if not rel.startswith("test") and "test" not in rel:
                        for ufn in ufns:
                            anchors.append((rel, ufn.start_line))

            causal_cuts = causal_graph.trace_backward_causal_slice(anchors[:16], max_hops=3)
            if not causal_cuts:
                for rel, ufns in causal_graph.functions_by_file.items():
                    if not rel.startswith("test") and "/tests/" not in ("/" + rel):
                        for ufn in ufns:
                            causal_cuts.append(
                                type(
                                    "_FallbackCut",
                                    (),
                                    {"rel_path": rel, "func_name": ufn.name},
                                )()
                            )
            candidate_files_ordered: list[str] = []
            for cut in causal_cuts:
                if cut.rel_path not in candidate_files_ordered:
                    candidate_files_ordered.append(cut.rel_path)
            for rel, _, _ in ochiai_ranked[:20]:
                if rel not in candidate_files_ordered:
                    candidate_files_ordered.append(rel)
            single_file_Queue: list[tuple[dict[str, str], str, str]] = []

            if norm_lang == "python":
                # Aggregate samples per `rel:line`
                fail_samples_by_key: dict[str, list[dict[str, Any]]] = {}
                pass_samples_by_key: dict[str, list[dict[str, Any]]] = {}
                all_escaping_excs: list[dict[str, Any]] = []
                iter_producer_keys: set[str] = set()
                pass_iter_producer_keys: set[str] = set()
                for ft in fail_traces:
                    all_escaping_excs.extend(ft.get("exceptions_seen") or [])
                    iter_producer_keys.update((ft.get("producer_lines") or {}).keys())
                    for k, smps in (ft.get("frame_samples") or {}).items():
                        fail_samples_by_key.setdefault(k, []).extend(smps)
                for pt in pass_traces:
                    pass_iter_producer_keys.update((pt.get("producer_lines") or {}).keys())
                    for k, smps in (pt.get("frame_samples") or {}).items():
                        pass_samples_by_key.setdefault(k, []).extend(smps)

                src_cache: dict[str, tuple[str, ast.AST | None]] = {}
                iter_disagreement_lines: list[tuple[str, int, float]] = []
                for pk in sorted(iter_producer_keys - pass_iter_producer_keys):
                    rel_i, ln_i = pk.rsplit(":", 1)
                    iter_disagreement_lines.append((rel_i, int(ln_i), 1.20))

                exc_anchor_lines: list[tuple[str, int, float]] = []
                distinct_exc_sites: list[tuple[str, int]] = []
                for exc_rec in reversed(all_escaping_excs):
                    if exc_rec.get("exc_type") in {"GeneratorExit", "SystemExit", "StopIteration"}:
                        continue
                    erel = exc_rec.get("rel_path")
                    eln = exc_rec.get("lineno")
                    if erel and not _is_auxiliary_harness(erel, test_target) and isinstance(eln, int):
                        if (erel, eln) not in distinct_exc_sites:
                            distinct_exc_sites.append((erel, eln))
                        if len(distinct_exc_sites) >= 4:
                            break
                for erel, eln in distinct_exc_sites:
                    for delta in (0, -1):
                        if eln + delta >= 1:
                            exc_anchor_lines.append((erel, eln + delta, 1.10))

                # Daikon-style State-Invariant Disagreement Ranking: surface lines where an
                # expression literally written on that source line satisfies a 100% invariant
                # across >=2 passing samples (truthiness / non-None / runtime type) that is
                # violated on the failing sample — rescuing shared-execution lines (e.g. Rank #491)!
                state_disagreement_lines: list[tuple[str, int, float]] = []
                file_lines_cache: dict[str, list[str]] = {}
                for k, f_smps in fail_samples_by_key.items():
                    p_smps = pass_samples_by_key.get(k, [])
                    if len(p_smps) < 2 or not f_smps:
                        continue
                    rel_d, ln_d_s = k.rsplit(":", 1)
                    if _is_auxiliary_harness(rel_d, test_target):
                        continue
                    ln_d = int(ln_d_s)
                    if rel_d not in file_lines_cache:
                        fp_d = repo_root / rel_d
                        file_lines_cache[rel_d] = (
                            fp_d.read_text(encoding="utf-8", errors="replace").splitlines()
                            if fp_d.is_file()
                            else []
                        )
                    flines = file_lines_cache[rel_d]
                    if not (1 <= ln_d <= len(flines)):
                        continue
                    ltxt = flines[ln_d - 1]
                    # Extract `obj.attr` and `var` tokens literally appearing on `ltxt`
                    tokens = re.findall(r"\b([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)?)\b", ltxt)
                    for tok in tokens:
                        if tok in {"if", "elif", "else", "return", "and", "or", "not", "is", "in", "None", "True", "False", "self", "cls"}:
                            continue
                        p_summaries = []
                        f_summaries = []
                        for s in p_smps:
                            locs = s.get("locals") or {}
                            if "." in tok:
                                b_n, a_n = tok.split(".", 1)
                                inf = ((locs.get(b_n) or {}).get("attrs") or {}).get(a_n)
                            else:
                                inf = locs.get(tok)
                            if inf is not None:
                                p_summaries.append(inf)
                        for s in f_smps:
                            locs = s.get("locals") or {}
                            if "." in tok:
                                b_n, a_n = tok.split(".", 1)
                                inf = ((locs.get(b_n) or {}).get("attrs") or {}).get(a_n)
                            else:
                                inf = locs.get(tok)
                            if inf is not None:
                                f_summaries.append(inf)
                        if len(p_summaries) >= 2 and f_summaries:
                            p_truths = {ps.get("truthy") for ps in p_summaries}
                            f_truths = {fs.get("truthy") for fs in f_summaries}
                            p_types = {ps.get("type") for ps in p_summaries}
                            f_types = {fs.get("type") for fs in f_summaries}
                            if (len(p_truths) == 1 and not (f_truths <= p_truths)) or (
                                len(p_types) == 1 and not (f_types <= p_types)
                            ):
                                state_disagreement_lines.append((rel_d, ln_d, 1.15))
                                break

                for erel, _, _ in exc_anchor_lines:
                    if erel not in candidate_files_ordered:
                        candidate_files_ordered.insert(0, erel)

                called_symbols, spec_literals = extract_test_called_symbols_and_literals(
                    mental.cow_root, baseline.failing_tests
                )
                called_symbols_lower = {s.lower() for s in called_symbols}

                # Surface executed lines inside functions directly named/called by the failing test
                called_target_lines: list[tuple[str, int, float]] = []
                fn_spans_by_file: dict[str, list[tuple[int, int, str]]] = {}
                for k_exec in fail_samples_by_key:
                    r_ex, l_ex_s = k_exec.rsplit(":", 1)
                    if _is_auxiliary_harness(r_ex, test_target):
                        continue
                    l_ex = int(l_ex_s)
                    if r_ex not in fn_spans_by_file:
                        fp_ex = repo_root / r_ex
                        spans: list[tuple[int, int, str]] = []
                        if fp_ex.is_file():
                            st_ex = fp_ex.read_text(encoding="utf-8", errors="replace")
                            try:
                                tr_ex = ast.parse(st_ex)
                                src_cache[r_ex] = (st_ex, tr_ex)
                                for nd_ex in ast.walk(tr_ex):
                                    if isinstance(nd_ex, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                        spans.append(
                                            (nd_ex.lineno, getattr(nd_ex, "end_lineno", nd_ex.lineno), nd_ex.name)
                                        )
                            except SyntaxError:
                                src_cache[r_ex] = (st_ex, None)
                        fn_spans_by_file[r_ex] = spans
                    for s_ln, e_ln, fn_nm in fn_spans_by_file[r_ex]:
                        if s_ln <= l_ex <= e_ln:
                            fn_low = fn_nm.lower()
                            if fn_nm in called_symbols or fn_low in called_symbols_lower or any(
                                len(cs) >= 5 and cs in fn_low for cs in called_symbols_lower
                            ):
                                called_target_lines.append((r_ex, l_ex, 1.25))
                                break

                iter_site_set = {(r, l) for r, l, _ in iter_disagreement_lines}
                called_site_set = {(r, l) for r, l, _ in called_target_lines}
                combined_ranked = (
                    called_target_lines
                    + iter_disagreement_lines
                    + state_disagreement_lines
                    + exc_anchor_lines
                    + ochiai_ranked
                )
                visited_sites: set[tuple[str, int]] = set()
                per_site_buckets: list[list[tuple[dict[str, str], str, str]]] = []

                # Collect top localized functions `(rel_path, fn_name, firstlineno)` and hot lines
                loc_fns_ordered: list[tuple[str, str, int]] = []
                loc_fn_hot_lines: dict[tuple[str, str, int], list[int]] = {}
                for r_lk, l_lk, _ in combined_ranked[:80]:
                    if r_lk not in fn_spans_by_file and (repo_root / r_lk).is_file():
                        st_lk = (repo_root / r_lk).read_text(encoding="utf-8", errors="replace")
                        spans_lk: list[tuple[int, int, str]] = []
                        try:
                            tr_lk = ast.parse(st_lk)
                            src_cache[r_lk] = (st_lk, tr_lk)
                            for nd_lk in ast.walk(tr_lk):
                                if isinstance(nd_lk, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                    spans_lk.append(
                                        (nd_lk.lineno, getattr(nd_lk, "end_lineno", nd_lk.lineno), nd_lk.name)
                                    )
                        except SyntaxError:
                            src_cache[r_lk] = (st_lk, None)
                        fn_spans_by_file[r_lk] = spans_lk
                    # Pick innermost enclosing function span
                    enclosing = [
                        (s_ln, e_ln, fn_nm)
                        for s_ln, e_ln, fn_nm in fn_spans_by_file.get(r_lk, [])
                        if s_ln <= l_lk <= e_ln
                    ]
                    if enclosing:
                        s_ln, _, fn_nm = min(enclosing, key=lambda x: x[1] - x[0])
                        fkey = (r_lk, fn_nm, s_ln)
                        if fkey not in loc_fn_hot_lines:
                            loc_fns_ordered.append(fkey)
                            loc_fn_hot_lines[fkey] = []
                        if l_lk not in loc_fn_hot_lines[fkey]:
                            loc_fn_hot_lines[fkey].append(l_lk)

                test_file_paths = sorted(
                    {
                        mental.cow_root / t.split("::")[0]
                        for t in baseline.failing_tests
                        if t and not t.startswith("<") and (mental.cow_root / t.split("::")[0]).is_file()
                    }
                )
                if not test_file_paths and mental.test_target and (mental.cow_root / mental.test_target).is_file():
                    test_file_paths = [mental.cow_root / mental.test_target]
                for p_extra in sorted(mental.cow_root.glob("test_*.py"))[:3]:
                    if p_extra not in test_file_paths:
                        test_file_paths.append(p_extra)

                for r_fn, fn_nm, fl_no in loc_fns_ordered[:6]:
                    fp_fn = repo_root / r_fn
                    if not fp_fn.is_file():
                        continue
                    orig_b_fn = fp_fn.read_bytes()
                    orig_s_fn = orig_b_fn.decode("utf-8", errors="replace")
                    if self.law_store.laws:
                        for law, patched_b_fn, desc_fn in self.law_store.match_and_compile_candidates(
                            orig_b_fn,
                            norm_lang,
                            rel_path=r_fn,
                            target_func_name=fn_nm,
                            runtime_hint={"assertion_literals": spec_literals},
                        ):
                            mem_eval_total += 1
                            v_fn_res = self._verify_and_finalize_patch(
                                mental=mental,
                                causal_graph=causal_graph,
                                repo_root=repo_root,
                                baseline=baseline,
                                file_patches={r_fn: patched_b_fn.decode("utf-8", errors="replace")},
                                mechanism=f"SEMANTIC_LAW_RECALL:{law.law_id}",
                                description=desc_fn,
                                norm_lang=norm_lang,
                                mem_eval_total=mem_eval_total,
                                t0=t0,
                            )
                            if v_fn_res is not None:
                                return v_fn_res

                    fn_bucket: list[tuple[dict[str, str], str, str]] = []
                    hot_lns = loc_fn_hot_lines[(r_fn, fn_nm, fl_no)]
                    if wb_synth is not None:
                        if test_file_paths:
                            for tag, c_src in wb_synth.test_driven_precondition_guard_candidates(
                                orig_s_fn, test_file_paths, allowed_functions={fn_nm}, max_candidates=5
                            ):
                                mem_eval_total += 1
                                fn_bucket.append(({r_fn: c_src}, "COGS_REVERSE_PRECONDITION_SYNTHESIS", f"Entry guard `{tag}` in `{fn_nm}`"))
                        for tag, c_src in wb_synth.algebraic_dual_span_candidates(
                            orig_s_fn, allowed_functions={fn_nm}, hot_lines=hot_lns, max_candidates=6
                        ):
                            mem_eval_total += 1
                            fn_bucket.append(({r_fn: c_src}, "COGS_ALGEBRAIC_DUAL_MORPHISM", f"Algebraic dual `{tag}` in `{fn_nm}`"))
                    if _surgical_span_mutations is not None:
                        for tag, c_src in _surgical_span_mutations(
                            orig_s_fn, fn_nm, hot_lns, firstlineno=fl_no
                        )[:10]:
                            mem_eval_total += 1
                            fn_bucket.append(({r_fn: c_src}, "COGS_RELATIONAL_BOUNDARY_SYNTHESIS", f"Boundary `{tag}` in `{fn_nm}`"))
                    if fn_bucket:
                        fn_prio = -1 if (fn_nm in called_symbols or fn_nm.lower() in called_symbols_lower) else 1
                        per_site_buckets.append((fn_prio, fn_bucket))  # type: ignore[arg-type]

                for rel_path, line_no, _ in combined_ranked[:110]:
                    if (rel_path, line_no) in visited_sites:
                        continue
                    visited_sites.add((rel_path, line_no))
                    full_p = repo_root / rel_path
                    if not full_p.is_file():
                        continue
                    if rel_path not in src_cache:
                        stxt = full_p.read_text(encoding="utf-8", errors="replace")
                        try:
                            ptree = ast.parse(stxt)
                        except SyntaxError:
                            ptree = None
                        src_cache[rel_path] = (stxt, ptree)
                    src_txt, parsed_tree = src_cache[rel_path]
                    if parsed_tree is None:
                        continue
                    key = f"{rel_path}:{line_no}"
                    f_smps = fail_samples_by_key.get(key, [])
                    p_smps = pass_samples_by_key.get(key, [])

                    site_cands: list[tuple[dict[str, str], str, str]] = []
                    stmt_patches, c1 = synthesize_obsegraph_statement_and_value_repairs(
                        source_text=src_txt,
                        line_no=line_no,
                        pass_samples=p_smps,
                        fail_samples=f_smps,
                        escaping_exceptions=all_escaping_excs,
                        parsed_tree=parsed_tree,
                        allow_iter_materialize=(rel_path, line_no) in iter_site_set,
                    )
                    mem_eval_total += c1
                    for p_src, desc in stmt_patches:
                        site_cands.append(({rel_path: p_src}, "COGS_OBSEGRAPH_VALUE_OR_BOUNDARY", desc))

                    petri_patches, c_petri = synthesize_repo_petri_repairs(
                        repo_root=repo_root,
                        rel_path=rel_path,
                        source_text=src_txt,
                        line_no=line_no,
                        pass_samples=p_smps,
                        fail_samples=f_smps,
                        escaping_exceptions=all_escaping_excs,
                        spec_literals=spec_literals,
                        called_symbols=called_symbols,
                        parsed_tree=parsed_tree,
                    )
                    mem_eval_total += c_petri
                    for p_src, desc in petri_patches:
                        site_cands.append(({rel_path: p_src}, "COGS_REPO_COMPONENT_PETRI_NET", desc))

                    crashed_here = any(
                        e.get("rel_path") == rel_path and e.get("lineno") == line_no
                        for e in all_escaping_excs
                    )
                    br_patches, c2 = synthesize_obsegraph_branch_repairs(
                        source_text=src_txt,
                        line_no=line_no,
                        pass_samples=p_smps,
                        fail_samples=f_smps,
                        parsed_tree=parsed_tree,
                        crashed_at_line=crashed_here,
                    )
                    mem_eval_total += c2
                    for p_src, desc in br_patches:
                        site_cands.append(({rel_path: p_src}, "COGS_OBSEGRAPH_GUARD_SYNTHESIS", desc))

                    if site_cands:
                        top_desc = site_cands[0][2]
                        in_called_fn = (rel_path, line_no) in called_site_set
                        bucket_prio = (
                            -1
                            if in_called_fn
                            else (
                                0
                                if crashed_here or "Exception-handler Petri widening" in top_desc
                                else (
                                    1
                                    if (
                                        "is not None" in top_desc
                                        or "STUN" in top_desc
                                        or "materialization" in top_desc
                                        or "Alias" in top_desc
                                        or "Repo-component" in top_desc
                                    )
                                    else 2
                                )
                            )
                        )
                        per_site_buckets.append((bucket_prio, site_cands))  # type: ignore[arg-type]

                ordered_buckets = [b for _, b in sorted(per_site_buckets, key=lambda pair: pair[0])]  # type: ignore[misc]
                max_depth = max((len(b) for b in ordered_buckets), default=0)
                for d_idx in range(max_depth):
                    for bucket in ordered_buckets:
                        if d_idx < len(bucket):
                            single_file_Queue.append(bucket[d_idx])

            base_native_prog = (
                _extract_native_crash_progress(baseline.output, repo_root)
                if norm_lang != "python"
                else None
            )
            native_horizon_seeds: list[tuple[dict[str, str], tuple[int, str, str, int], str]] = []

            # Polyglot U-IR + Z3 cold-start synthesis across all causal cut files
            for cut in causal_cuts[:10]:
                full_p = repo_root / cut.rel_path
                if not full_p.is_file():
                    continue
                orig_b = full_p.read_bytes()
                cut_hot_ln = (
                    base_native_prog[3]
                    if (
                        base_native_prog is not None
                        and base_native_prog[1] == cut.rel_path
                        and base_native_prog[2] == cut.func_name
                        and base_native_prog[3] > 0
                    )
                    else None
                )
                poly_cands = synthesize_polyglot_uir_z3_repairs(
                    source_bytes=orig_b,
                    language=norm_lang,
                    rel_path=cut.rel_path,
                    target_func_name=cut.func_name,
                    cached_u_fns=causal_graph.functions_by_file.get(cut.rel_path),
                    hot_line=cut_hot_ln,
                )
                for patched_b, desc in poly_cands:
                    mem_eval_total += 1
                    single_file_Queue.append(
                        ({cut.rel_path: patched_b.decode("utf-8", errors="replace")}, "COGS_UIR_Z3_INVENTION", desc)
                    )

            # Deduplicate candidates and evaluate inside ExecutableMentalModel;
            # retain partial-progress patches for Phase 3 Coupled Multi-File / Multi-Hunk Beam!
            seen_patch_hashes: set[str] = set()
            partial_progress_beam: list[tuple[dict[str, str], int, list[str], str]] = []
            base_fail_cnt = len(baseline.failing_tests)
            py_fast_targets = (
                [t for t in baseline.failing_tests[:10] if not t.startswith("<")]
                if norm_lang == "python"
                else None
            )

            single_hunk_cap = (
                max(12, self.sandbox_budget - max(6, self.sandbox_budget // 5))
                if self.sandbox_budget >= 20
                else self.sandbox_budget + 2
            )
            for file_patches, mech, desc in single_file_Queue:
                if mental.simulations_run >= single_hunk_cap:
                    break
                phash = hashlib.sha256(
                    json.dumps(file_patches, sort_keys=True).encode("utf-8")
                ).hexdigest()[:16]
                if phash in seen_patch_hashes:
                    continue
                seen_patch_hashes.add(phash)

                # L3 Negative-Space Refutation Filter (~microseconds, 0 subprocess spawns)
                if norm_lang == "python" and len(file_patches) == 1:
                    rel_chk, cand_chk = next(iter(file_patches.items()))
                    orig_chk = (repo_root / rel_chk).read_text(encoding="utf-8", errors="replace")
                    o_hk, c_hk, fn_chk = _extract_changed_hunk_and_fn(orig_chk, cand_chk)
                    if o_hk and c_hk:
                        ctx_tag = f"FN:{fn_chk}" if fn_chk else "GENERAL"
                        if self.negative_store.is_refuted(o_hk, c_hk, context_tag=ctx_tag) is not None:
                            continue

                mental.apply_overrides(file_patches)
                quick_ok, quick_v = mental.run_fast_gate(
                    specific_targets=py_fast_targets,
                    modified_rels=list(file_patches.keys()),
                    timeout_sec=min(4.5, timeout_sec) if norm_lang == "python" else timeout_sec,
                )
                mental.restore_originals(list(file_patches.keys()))

                if quick_ok:
                    verdict_res = self._verify_and_finalize_patch(
                        mental=mental,
                        causal_graph=causal_graph,
                        repo_root=repo_root,
                        baseline=baseline,
                        file_patches=file_patches,
                        mechanism=mech,
                        description=desc,
                        norm_lang=norm_lang,
                        mem_eval_total=mem_eval_total,
                        t0=t0,
                    )
                    if verdict_res is not None:
                        return verdict_res
                    # Counterexample-Partitioned Dual-Program Splicing (`if G: P_cand else: P_orig`):
                    # `file_patches` solved `baseline.failing_tests` (`quick_ok=True`) yet broke a passing test!
                    if (
                        norm_lang == "python"
                        and len(file_patches) == 1
                        and mental.simulations_run < self.sandbox_budget + 6
                    ):
                        rel_only, cand_only = next(iter(file_patches.items()))
                        orig_only = (repo_root / rel_only).read_text(encoding="utf-8", errors="replace")
                        mental.apply_overrides(file_patches)
                        reg_check = mental.run_oracle(timeout_sec=min(8.0, timeout_sec))
                        mental.restore_originals([rel_only])
                        reg_tests = [
                            rt for rt in reg_check.failing_tests if rt in set(baseline.passing_tests)
                        ][:2]
                        if reg_tests:
                            f_tr_s, r_tr_s = _collect_python_traces(
                                mental, baseline.failing_tests[:2], reg_tests
                            )
                            f_by_ln: dict[int, list[dict[str, Any]]] = {}
                            r_by_ln: dict[int, list[dict[str, Any]]] = {}
                            for tr in f_tr_s:
                                for k_s, sm_s in (tr.get("frame_samples") or {}).items():
                                    if k_s.startswith(f"{rel_only}:"):
                                        f_by_ln.setdefault(int(k_s.rsplit(":", 1)[1]), []).extend(sm_s)
                            for tr in r_tr_s:
                                for k_s, sm_s in (tr.get("frame_samples") or {}).items():
                                    if k_s.startswith(f"{rel_only}:"):
                                        r_by_ln.setdefault(int(k_s.rsplit(":", 1)[1]), []).extend(sm_s)
                            for sp_src, sp_desc in synthesize_dual_program_splice(
                                orig_src=orig_only,
                                cand_src=cand_only,
                                fail_samples_by_line=f_by_ln,
                                reg_samples_by_line=r_by_ln,
                            )[:2]:
                                sp_res = self._verify_and_finalize_patch(
                                    mental=mental,
                                    causal_graph=causal_graph,
                                    repo_root=repo_root,
                                    baseline=baseline,
                                    file_patches={rel_only: sp_src},
                                    mechanism="COGS_DUAL_PROGRAM_COUNTEREXAMPLE_SPLICE",
                                    description=f"{desc} -> {sp_desc}",
                                    norm_lang=norm_lang,
                                    mem_eval_total=mem_eval_total,
                                    t0=t0,
                                )
                                if sp_res is not None:
                                    return sp_res
                elif quick_v is not None:
                    if 0 < len(quick_v.failing_tests) < base_fail_cnt:
                        partial_progress_beam.append(
                            (file_patches, len(quick_v.failing_tests), list(quick_v.failing_tests), desc)
                        )
                    elif norm_lang != "python" and base_native_prog is not None:
                        cand_prog = _extract_native_crash_progress(quick_v.output, repo_root)
                        if cand_prog is not None and (
                            cand_prog[0] > base_native_prog[0]
                            or (cand_prog[2] and cand_prog[2] != base_native_prog[2])
                            or (
                                cand_prog[2] == base_native_prog[2]
                                and cand_prog[3] > base_native_prog[3] + 2
                            )
                        ):
                            partial_progress_beam.append(
                                (file_patches, -cand_prog[0], list(quick_v.failing_tests), desc)
                            )
                            native_horizon_seeds.append((file_patches, cand_prog, desc))

            # ------------------------------------------------------------------
            # PHASE 3: Coupled Multi-File & Same-File Orthogonal Multi-Hunk Beam
            # ------------------------------------------------------------------
            if norm_lang != "python" and native_horizon_seeds:
                native_horizon_seeds.sort(key=lambda s: (-s[1][0], -s[1][3]))
                curr_p, curr_prog, curr_d = native_horizon_seeds[0]
                for _chain_step in range(5):
                    if mental.simulations_run >= self.sandbox_budget + 12 or not curr_prog[1]:
                        break
                    nxt_rel, nxt_fn, nxt_ln = curr_prog[1], curr_prog[2], curr_prog[3]
                    base_src_b = (
                        curr_p[nxt_rel].encode("utf-8")
                        if nxt_rel in curr_p
                        else (repo_root / nxt_rel).read_bytes()
                    )
                    nxt_cands = synthesize_polyglot_uir_z3_repairs(
                        source_bytes=base_src_b,
                        language=norm_lang,
                        rel_path=nxt_rel,
                        target_func_name=nxt_fn or None,
                        hot_line=nxt_ln if nxt_ln > 0 else None,
                    )
                    advanced_this_step = False
                    for nxt_b, nxt_desc in nxt_cands[:10]:
                        if mental.simulations_run >= self.sandbox_budget + 12:
                            break
                        chained = dict(curr_p)
                        chained[nxt_rel] = nxt_b.decode("utf-8", errors="replace")
                        ch_hash = hashlib.sha256(
                            json.dumps(chained, sort_keys=True).encode("utf-8")
                        ).hexdigest()[:16]
                        if ch_hash in seen_patch_hashes:
                            continue
                        seen_patch_hashes.add(ch_hash)
                        mental.apply_overrides(chained)
                        qn_ok, qn_v = mental.run_fast_gate(
                            modified_rels=list(chained.keys()),
                            timeout_sec=timeout_sec,
                        )
                        mental.restore_originals(list(chained.keys()))
                        if qn_ok:
                            v_ch = self._verify_and_finalize_patch(
                                mental=mental,
                                causal_graph=causal_graph,
                                repo_root=repo_root,
                                baseline=baseline,
                                file_patches=chained,
                                mechanism="COGS_COUPLED_MULTIFILE_INVENTION",
                                description=f"{curr_d} + {nxt_desc}",
                                norm_lang=norm_lang,
                                mem_eval_total=mem_eval_total,
                                t0=t0,
                            )
                            if v_ch is not None:
                                return v_ch
                        elif qn_v is not None:
                            nxt_prog = _extract_native_crash_progress(qn_v.output, repo_root)
                            if nxt_prog is not None and (
                                nxt_prog[0] > curr_prog[0]
                                or (nxt_prog[2] and nxt_prog[2] != curr_prog[2])
                                or (nxt_prog[2] == curr_prog[2] and nxt_prog[3] > curr_prog[3] + 2)
                            ):
                                curr_p, curr_prog, curr_d = chained, nxt_prog, f"{curr_d} + {nxt_desc}"
                                advanced_this_step = True
                                break
                    if not advanced_this_step:
                        break

            partial_progress_beam.sort(key=lambda item: item[1])
            for step1_patches, _, rem_fails, step1_desc in partial_progress_beam[:3]:
                # 3a. Compose orthogonal hunks across `partial_progress_beam` + `single_file_Queue`
                partner_pool = [(p, d) for p, _, _, d in partial_progress_beam[:6]] + [
                    (p, d) for p, _, d in single_file_Queue[:18]
                ]
                for file2_patches, step2_desc in partner_pool:
                    if mental.simulations_run >= self.sandbox_budget + 10:
                        break
                    combined_patches = merge_orthogonal_file_patches(
                        repo_root, step1_patches, file2_patches
                    )
                    if combined_patches is None:
                        continue
                    c_hash = hashlib.sha256(
                        json.dumps(combined_patches, sort_keys=True).encode("utf-8")
                    ).hexdigest()[:16]
                    if c_hash in seen_patch_hashes:
                        continue
                    seen_patch_hashes.add(c_hash)
                    mental.apply_overrides(combined_patches)
                    q2_ok, _ = mental.run_fast_gate(
                        specific_targets=py_fast_targets,
                        modified_rels=list(combined_patches.keys()),
                        timeout_sec=min(4.5, timeout_sec) if norm_lang == "python" else timeout_sec,
                    )
                    mental.restore_originals(list(combined_patches.keys()))
                    if q2_ok:
                        verdict_res = self._verify_and_finalize_patch(
                            mental=mental,
                            causal_graph=causal_graph,
                            repo_root=repo_root,
                            baseline=baseline,
                            file_patches=combined_patches,
                            mechanism="COGS_COUPLED_MULTIFILE_BEAM",
                            description=f"{step1_desc} + {step2_desc}",
                            norm_lang=norm_lang,
                            mem_eval_total=mem_eval_total,
                            t0=t0,
                        )
                        if verdict_res is not None:
                            return verdict_res

                # 3b. Residual Failing-Test Re-Tracing: apply `step1_patches` in CoW, trace ONLY
                # the residual failing tests `rem_fails`, synthesize Step-2 hunks, and compose!
                if (
                    norm_lang == "python"
                    and rem_fails
                    and mental.simulations_run < self.sandbox_budget + 10
                ):
                    mental.apply_overrides(step1_patches)
                    res_f_tr, res_p_tr = _collect_python_traces(
                        mental, rem_fails[:3], baseline.passing_tests[:5]
                    )
                    mental.restore_originals(list(step1_patches.keys()))
                    res_ochiai = _compute_ochiai_suspiciousness(res_f_tr, res_p_tr)
                    res_f_smps: dict[str, list[dict[str, Any]]] = {}
                    res_p_smps: dict[str, list[dict[str, Any]]] = {}
                    res_excs: list[dict[str, Any]] = []
                    for ft_r in res_f_tr:
                        res_excs.extend(ft_r.get("exceptions_seen") or [])
                        for k_r, sm_r in (ft_r.get("frame_samples") or {}).items():
                            res_f_smps.setdefault(k_r, []).extend(sm_r)
                    for pt_r in res_p_tr:
                        for k_r, sm_r in (pt_r.get("frame_samples") or {}).items():
                            res_p_smps.setdefault(k_r, []).extend(sm_r)
                    res_spec_lits = extract_test_spec_literals(repo_root, rem_fails)
                    for rel_r, ln_r, _ in res_ochiai[:18]:
                        fp_r = repo_root / rel_r
                        if not fp_r.is_file():
                            continue
                        orig_r_txt = fp_r.read_text(encoding="utf-8", errors="replace")
                        try:
                            ptree_r = ast.parse(orig_r_txt)
                        except SyntaxError:
                            continue
                        key_r = f"{rel_r}:{ln_r}"
                        s_p1, _ = synthesize_obsegraph_statement_and_value_repairs(
                            source_text=orig_r_txt,
                            line_no=ln_r,
                            pass_samples=res_p_smps.get(key_r, []),
                            fail_samples=res_f_smps.get(key_r, []),
                            escaping_exceptions=res_excs,
                            parsed_tree=ptree_r,
                        )
                        s_p2, _ = synthesize_repo_petri_repairs(
                            repo_root=repo_root,
                            rel_path=rel_r,
                            source_text=orig_r_txt,
                            line_no=ln_r,
                            pass_samples=res_p_smps.get(key_r, []),
                            fail_samples=res_f_smps.get(key_r, []),
                            escaping_exceptions=res_excs,
                            spec_literals=res_spec_lits,
                            parsed_tree=ptree_r,
                        )
                        s_p3, _ = synthesize_obsegraph_branch_repairs(
                            source_text=orig_r_txt,
                            line_no=ln_r,
                            pass_samples=res_p_smps.get(key_r, []),
                            fail_samples=res_f_smps.get(key_r, []),
                            parsed_tree=ptree_r,
                        )
                        for p2_txt, p2_desc in (s_p1 + s_p2 + s_p3)[:6]:
                            if mental.simulations_run >= self.sandbox_budget + 12:
                                break
                            comb2 = merge_orthogonal_file_patches(
                                repo_root, step1_patches, {rel_r: p2_txt}
                            )
                            if comb2 is None:
                                continue
                            ch2 = hashlib.sha256(
                                json.dumps(comb2, sort_keys=True).encode("utf-8")
                            ).hexdigest()[:16]
                            if ch2 in seen_patch_hashes:
                                continue
                            seen_patch_hashes.add(ch2)
                            mental.apply_overrides(comb2)
                            ok_r, _ = mental.run_fast_gate(
                                specific_targets=py_fast_targets,
                                modified_rels=list(comb2.keys()),
                                timeout_sec=min(4.5, timeout_sec),
                            )
                            mental.restore_originals(list(comb2.keys()))
                            if ok_r:
                                v_r = self._verify_and_finalize_patch(
                                    mental=mental,
                                    causal_graph=causal_graph,
                                    repo_root=repo_root,
                                    baseline=baseline,
                                    file_patches=comb2,
                                    mechanism="COGS_RESIDUAL_MULTIHUNK_BEAM",
                                    description=f"{step1_desc} + {p2_desc}",
                                    norm_lang=norm_lang,
                                    mem_eval_total=mem_eval_total,
                                    t0=t0,
                                )
                                if v_r is not None:
                                    return v_r

            return InventedRepairResult(
                solved=False,
                stage="UNSOLVED_WITHIN_BUDGET",
                mechanism="NONE",
                modified_files={},
                unified_diff="",
                sabotage_verified=False,
                overfit_falsifier_passed=False,
                neighbor_impact_passed=False,
                crystallized_law_id=None,
                candidates_evaluated_in_memory=mem_eval_total,
                candidates_executed_in_sandbox=mental.simulations_run,
                source_tree_unchanged=mental.verify_source_untouched(),
                elapsed_ms=round((time.perf_counter() - t0) * 1000.0, 2),
                diagnostics={
                    "baseline_failing": baseline.failing_tests[:5],
                    "candidate_files": candidate_files_ordered[:6],
                    "queued_candidates": len(single_file_Queue),
                },
            )

    def _verify_and_finalize_patch(
        self,
        *,
        mental: ExecutableMentalModel,
        causal_graph: InterproceduralCausalGraph,
        repo_root: pathlib.Path,
        baseline: TestRunVerdict,
        file_patches: dict[str, str],
        mechanism: str,
        description: str,
        norm_lang: str,
        mem_eval_total: int,
        t0: float,
        already_law_id: str | None = None,
    ) -> InventedRepairResult | None:
        modified_rels = list(file_patches.keys())
        try:
            mental.apply_overrides(file_patches)
            # Gate 1: Full target test file must pass (every failing test flips green, 0 passing break)
            full_v = mental.run_oracle()
            if not full_v.passed:
                return None
            for p_name in baseline.passing_tests:
                if full_v.outcomes.get(p_name) == "FAILED":
                    return None

            # Gate 1.5: 64-Vector 1ms os.fork() CoW Differential Boundary Invariance
            if norm_lang == "python" and len(file_patches) == 1:
                rel_b, cand_b = next(iter(file_patches.items()))
                orig_b_txt = (repo_root / rel_b).read_text(encoding="utf-8", errors="replace")
                o_hk, c_hk, fn_b = _extract_changed_hunk_and_fn(orig_b_txt, cand_b)
                if fn_b:
                    bfuzz = verify_cow_boundary_invariance(
                        orig_b_txt.encode("utf-8"),
                        cand_b.encode("utf-8"),
                        fn_b,
                    )
                    if not bfuzz.passed:
                        if self.enable_law_crystallization and o_hk and c_hk:
                            cex_msg = bfuzz.counterexamples[0]["exception"] if bfuzz.counterexamples else ""
                            self.negative_store.record_refutation(
                                orig_snippet=o_hk,
                                cand_snippet=c_hk,
                                refutation_reason="COW_64_BOUNDARY_REGRESSION",
                                counterexample_summary=cex_msg,
                                context_tag=f"FN:{fn_b}",
                            )
                        return None

            # Gate 2: Neighbor Impact-Cone Regression Tests across the repository
            neighbor_passed = True
            if norm_lang == "python" and mental.custom_test_cmd is None:
                impact_tests = causal_graph.compute_test_impact_cone(modified_rels, max_tests=2)
                for imp_test in impact_tests:
                    if imp_test == mental.test_target:
                        continue
                    # Only enforce neighbor tests that already pass on the unmodified baseline!
                    mental.restore_originals(modified_rels)
                    base_imp = mental.run_oracle(specific_target=imp_test, timeout_sec=10.0)
                    mental.apply_overrides(file_patches)
                    if base_imp.passed:
                        cand_imp = mental.run_oracle(specific_target=imp_test, timeout_sec=10.0)
                        if not cand_imp.passed:
                            neighbor_passed = False
                            break
            if not neighbor_passed:
                if self.enable_law_crystallization and norm_lang == "python" and len(file_patches) == 1:
                    rel_n, cand_n = next(iter(file_patches.items()))
                    orig_n_txt = (repo_root / rel_n).read_text(encoding="utf-8", errors="replace")
                    o_hk, c_hk, fn_n = _extract_changed_hunk_and_fn(orig_n_txt, cand_n)
                    if o_hk and c_hk and fn_n:
                        self.negative_store.record_refutation(
                            orig_snippet=o_hk,
                            cand_snippet=c_hk,
                            refutation_reason="NEIGHBOR_IMPACT_REGRESSION",
                            context_tag=f"FN:{fn_n}",
                        )
                return None

            # Gate 3: Counterfactual Test-Input Alpha-Renaming Overfit Falsifier
            overfit_ok = True
            if norm_lang == "python" and mental.test_target and (repo_root / mental.test_target).is_file():
                orig_test_txt = (repo_root / mental.test_target).read_text(encoding="utf-8", errors="replace")
                mutated_test_txt = _counterfactual_alpha_rename_python_test(
                    orig_test_txt, baseline.failing_tests[0]
                )
                if mutated_test_txt is not None:
                    mental.apply_overrides({mental.test_target: mutated_test_txt})
                    alpha_v = mental.run_oracle(
                        specific_target=baseline.failing_tests[0], timeout_sec=10.0
                    )
                    mental.restore_originals([mental.test_target])
                    if not alpha_v.passed:
                        overfit_ok = False
            if not overfit_ok:
                return None

            # Gate 4: Mandatory Sabotage Negative Control (reverting MUST fail again!)
            mental.restore_originals(modified_rels)
            sabotage_v = mental.run_oracle(
                specific_target=baseline.failing_tests[0]
                if (norm_lang == "python" and not baseline.failing_tests[0].startswith("<"))
                else None,
                timeout_sec=10.0,
            )
            sabotage_ok = not sabotage_v.passed
            if not sabotage_ok:
                return None
        finally:
            mental.restore_originals(modified_rels)

        originals_map = {
            rel: (repo_root / rel).read_text(encoding="utf-8", errors="replace")
            for rel in modified_rels
        }
        diff_txt = _build_unified_diff(originals_map, file_patches)

        # Crystallize newly invented single-file or multi-file U-IR law if generalized
        law_id = already_law_id
        if law_id is None and self.enable_law_crystallization:
            for rel, new_txt in file_patches.items():
                old_b = originals_map[rel].encode("utf-8")
                new_b = new_txt.encode("utf-8")
                lifted = lift_verified_diff_to_semantic_law(
                    before_bytes=old_b,
                    after_bytes=new_b,
                    language=norm_lang,
                    rel_path=rel,
                    sabotage_verified=True,
                    contrast_verified=True,
                )
                if lifted is not None and self.law_store.admit_law(lifted):
                    law_id = lifted.law_id
                    break

        return InventedRepairResult(
            solved=True,
            stage="VERIFIED_CAUSAL_REPAIR",
            mechanism=mechanism,
            modified_files=file_patches,
            unified_diff=diff_txt,
            sabotage_verified=True,
            overfit_falsifier_passed=True,
            neighbor_impact_passed=True,
            crystallized_law_id=law_id,
            candidates_evaluated_in_memory=mem_eval_total,
            candidates_executed_in_sandbox=mental.simulations_run,
            source_tree_unchanged=mental.verify_source_untouched(),
            elapsed_ms=round((time.perf_counter() - t0) * 1000.0, 2),
            diagnostics={"description": description},
        )
