#!/usr/bin/env python3
"""In-container epistemic tomography & non-LLM SWE repair worker for Harbor tasks.

Authority: PROJECT_BRAIN_HARBOR_IN_CONTAINER_RUNNER_V1
Constraints:
  - `model_calls == 0`, `parameters_stored == 0`
  - Zero network access, zero package installs, zero writes under `/opt/brain-ro`
  - Zero untracked scratch files left inside `/app` or `/testbed`
  - All CoW child PIDs reaped before exit (`NO_NEW_VISIBLE_PROCESSES`)
"""
from __future__ import annotations

import argparse
import ast
import base64
import doctest
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import textwrap
import time
from typing import Any

BRAIN_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(BRAIN_ROOT) not in sys.path:
    sys.path.insert(0, str(BRAIN_ROOT))

STATE_PATH = pathlib.Path("/tmp/brain_harbor_epistemic_state_v1.json")
MEM_PATH = pathlib.Path("/tmp/brain_harbor_swe_memory_v1.json")
SKILL_PATH = pathlib.Path("/tmp/brain_harbor_skill_store_v1.json")
WITNESS_TEST_PATH = pathlib.Path("/tmp/brain_issue_witness_test.py")


def _reap_children() -> int:
    reaped = 0
    while True:
        try:
            pid, _ = os.waitpid(-1, os.WNOHANG)
            if pid <= 0:
                break
            reaped += 1
        except ChildProcessError:
            break
    return reaped


def _detect_repo_root() -> pathlib.Path:
    for cand in ("/app", "/testbed", os.getcwd()):
        p = pathlib.Path(cand)
        if p.is_dir() and (p / ".git").exists():
            return p.resolve()
    for cand in ("/app", "/testbed", os.getcwd()):
        p = pathlib.Path(cand)
        if p.is_dir():
            return p.resolve()
    return pathlib.Path.cwd().resolve()


def _detect_task_python(repo_root: pathlib.Path) -> str:
    candidates = [
        "/opt/miniconda3/envs/testbed/bin/python",
        "/opt/conda/envs/testbed/bin/python",
        str(repo_root / ".venv" / "bin" / "python"),
        str(repo_root / "venv" / "bin" / "python"),
        "/usr/local/bin/python3",
        "/usr/local/bin/python",
        shutil.which("python3") or "",
        sys.executable,
    ]
    seen: set[str] = set()
    best_fallback: str = sys.executable
    for raw in candidates:
        if not raw or raw in seen or not os.path.isfile(raw) or not os.access(raw, os.X_OK):
            continue
        seen.add(raw)
        if best_fallback == sys.executable:
            best_fallback = raw
        try:
            chk = subprocess.run(
                [raw, "-c", "import pytest; print(pytest.__file__)"],
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                timeout=8,
            )
            if chk.returncode == 0:
                return raw
        except Exception:
            continue
    return best_fallback


def _extract_instruction_clues(instruction: str) -> dict[str, list[str]]:
    py_paths = sorted(
        set(re.findall(r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+\.py", instruction))
    )
    identifiers = []
    for tok in re.findall(r"\b[A-Za-z_][A-Za-z0-9_]{3,48}\b", instruction):
        if tok.lower() in {
            "this", "that", "with", "from", "when", "where", "should", "would",
            "could", "return", "returns", "error", "issue", "python", "true",
            "false", "none", "class", "function", "method", "file", "test", "tests",
        }:
            continue
        if tok not in identifiers:
            identifiers.append(tok)
        if len(identifiers) >= 24:
            break
    return {"py_paths": py_paths[:12], "identifiers": identifiers}


def _rank_candidate_tests(repo_root: pathlib.Path, clues: dict[str, list[str]]) -> list[str]:
    explicit_tests: list[str] = []
    src_clues: list[str] = []
    for rel in clues.get("py_paths", ()):
        if (repo_root / rel).is_file():
            if "test" in pathlib.Path(rel).name.lower() or rel.startswith(("tests/", "test/")):
                explicit_tests.append(rel)
            else:
                src_clues.append(rel)

    test_files: list[tuple[int, str]] = []
    idents = set(clues.get("identifiers", ())[:16])
    src_stems = {pathlib.Path(s).stem.removeprefix("_") for s in src_clues}

    for root_dir, dirs, files in os.walk(repo_root):
        dirs[:] = [
            d for d in dirs
            if not d.startswith(".") and d not in {"node_modules", "__pycache__", "build", "dist", "venv", ".venv"}
        ]
        for fname in files:
            if not (fname.startswith("test_") and fname.endswith(".py")) and not fname.endswith("_test.py"):
                continue
            fpath = pathlib.Path(root_dir) / fname
            rel_p = fpath.relative_to(repo_root).as_posix()
            score = 0
            stem = fpath.stem.removeprefix("test_").removesuffix("_test")
            if stem in src_stems:
                score += 20
            try:
                if fpath.stat().st_size <= 200_000:
                    txt = fpath.read_text(encoding="utf-8", errors="ignore")
                    for ident in idents:
                        if ident in txt:
                            score += 3
            except OSError:
                pass
            if score > 0 or len(test_files) < 8:
                test_files.append((score, rel_p))

    test_files.sort(key=lambda item: (-item[0], item[1]))
    ranked = list(explicit_tests)
    for _, rp in test_files[:8]:
        if rp not in ranked:
            ranked.append(rp)
    return ranked[:6]


def phase_discover(instruction: str) -> dict[str, Any]:
    t0 = time.perf_counter()
    repo_root = _detect_repo_root()
    py_exe = _detect_task_python(repo_root)
    clues = _extract_instruction_clues(instruction)
    ranked_tests = _rank_candidate_tests(repo_root, clues)

    # detect primary ecosystem
    has_py = bool(ranked_tests) or (repo_root / "pyproject.toml").is_file() or (repo_root / "setup.py").is_file()
    has_go = (repo_root / "go.mod").is_file()
    has_node = (repo_root / "package.json").is_file()
    has_rust = (repo_root / "Cargo.toml").is_file()

    state = {
        "schema": "PROJECT_BRAIN_HARBOR_IN_CONTAINER_RUNNER_V1",
        "repo_root": str(repo_root),
        "python_exe": py_exe,
        "ecosystems": {
            "python": has_py,
            "go": has_go,
            "node": has_node,
            "rust": has_rust,
        },
        "clues": clues,
        "ranked_tests": ranked_tests,
        "instruction": instruction[:20000],
        "instruction_chars": len(instruction),
        "discover_wall_s": round(time.perf_counter() - t0, 3),
        "model_calls": 0,
    }
    STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    _reap_children()
    return state


def _clean_untracked_in_repo(repo_root: pathlib.Path) -> None:
    """Remove any `.pytest_cache` or `__pycache__` artifacts if unignored so git capture stays clean."""
    try:
        st = subprocess.run(
            ["git", "-C", str(repo_root), "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if st.returncode == 0:
            for line in st.stdout.splitlines():
                if line.startswith("?? "):
                    rel = line[3:].strip()
                    target = (repo_root / rel).resolve()
                    if repo_root in target.parents and (
                        "__pycache__" in rel or ".pytest_cache" in rel or rel.endswith(".pyc")
                    ):
                        if target.is_dir():
                            shutil.rmtree(target, ignore_errors=True)
                        elif target.is_file():
                            target.unlink(missing_ok=True)
    except Exception:
        pass


def _repo_top_packages(repo_root: pathlib.Path) -> set[str]:
    pkgs: set[str] = set()
    for base in (repo_root, repo_root / "src"):
        if not base.is_dir():
            continue
        for child in base.iterdir():
            if child.is_dir() and (child / "__init__.py").is_file() and not child.name.startswith((".", "test")):
                pkgs.add(child.name)
            elif child.is_file() and child.suffix == ".py" and not child.name.startswith(("test_", "setup", "conftest")):
                pkgs.add(child.stem)
    return pkgs


def compile_issue_witness_test(
    instruction: str,
    repo_root: pathlib.Path,
    py_exe: str,
    *,
    out_path: pathlib.Path = WITNESS_TEST_PATH,
) -> dict[str, Any]:
    """Compile executable doctests & fenced Python repro blocks from `instruction` into `/tmp`."""
    from canonical.swe_kernel.causal_swe_repair_v1 import run_pytest_verdicts

    out_path.unlink(missing_ok=True)
    if not instruction.strip():
        return {"compiled": False, "reason": "empty_instruction"}

    top_pkgs = _repo_top_packages(repo_root)
    test_funcs: list[str] = []

    # 1. Extract stdlib doctest `>>>` blocks that specify concrete expected output (and aren't prose tracebacks of broken pseudocode)
    try:
        examples = doctest.DocTestParser().get_examples(instruction)
    except Exception:
        examples = []
    if examples and any(ex.want.strip() and "Traceback" not in ex.want for ex in examples):
        src_lines: list[str] = []
        has_assert = False
        for ex in examples:
            s_clean = ex.source.rstrip("\n")
            want_clean = ex.want.strip()
            if want_clean and "Traceback" not in want_clean and "\n" not in s_clean and not s_clean.lstrip().startswith((
                "import ", "from ", "def ", "class ", "for ", "while ", "if ", "with ", "try:", "@"
            )):
                # Check if `s_clean` is an expression vs assignment/statement
                try:
                    ast.parse(s_clean, mode="eval")
                    ast.parse(want_clean, mode="eval")
                    src_lines.append(f"assert ({s_clean}) == ({want_clean})")
                    has_assert = True
                    continue
                except SyntaxError:
                    pass
            src_lines.append(s_clean)
        cand_block = "\n".join(src_lines)
        try:
            tree_dt = ast.parse(cand_block)
            imported_roots = {
                (n.module.split(".")[0] if isinstance(n, ast.ImportFrom) and n.module else "")
                for n in ast.walk(tree_dt)
            } | {
                alias.name.split(".")[0]
                for n in ast.walk(tree_dt)
                if isinstance(n, ast.Import)
                for alias in n.names
            }
            if has_assert and (not top_pkgs or (imported_roots & top_pkgs)):
                body = textwrap.indent(cand_block, "        ")
                test_funcs.append(f"    def test_issue_doctest_witness(self):\n{body}\n")
        except SyntaxError:
            pass

    # 2. Extract fenced ```python / ```py reproduction blocks
    fence_re = re.compile(r"```(?:python|py)\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)
    for idx, match in enumerate(fence_re.finditer(instruction)):
        raw_code = textwrap.dedent(match.group(1)).strip()
        if not raw_code or len(raw_code) > 4000:
            continue
        try:
            b_tree = ast.parse(raw_code)
        except SyntaxError:
            continue
        imported_roots = set()
        has_assert_or_raises = False
        for node in ast.walk(b_tree):
            if isinstance(node, ast.Import):
                for al in node.names:
                    imported_roots.add(al.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".")[0])
            elif isinstance(node, ast.Assert):
                has_assert_or_raises = True
            elif isinstance(node, ast.Attribute) and node.attr in ("raises", "assertRaises", "assertEqual"):
                has_assert_or_raises = True
        if top_pkgs and not (imported_roots & top_pkgs):
            continue
        indented = textwrap.indent(raw_code, "        ")
        if any(isinstance(st, ast.FunctionDef) and st.name.startswith("test_") for st in b_tree.body):
            calls = "\n".join(
                f"        {st.name}()"
                for st in b_tree.body
                if isinstance(st, ast.FunctionDef) and st.name.startswith("test_") and len(st.args.args) == 0
            )
            if calls:
                test_funcs.append(f"    def test_issue_fenced_{idx}(self):\n{indented}\n{calls}\n")
        elif has_assert_or_raises or len(b_tree.body) >= 2:
            test_funcs.append(f"    def test_issue_fenced_{idx}(self):\n{indented}\n")

    if not test_funcs:
        return {"compiled": False, "reason": "no_executable_witness_in_instruction"}

    full_witness_src = "import unittest\n\n\nclass TestBrainIssueWitness(unittest.TestCase):\n" + "\n".join(test_funcs)
    out_path.write_text(full_witness_src, encoding="utf-8")
    verd = run_pytest_verdicts(repo_root, str(out_path), python_exe=py_exe, timeout_s=15.0)
    out_txt = verd.get("output", "")
    # Reject incomplete snippets that fail due to missing imports / undefined placeholder names
    invalid_markers = ("ModuleNotFoundError:", "ImportError:", "NameError:", "SyntaxError:", "IndentationError:")
    if not verd.get("failing") or any(m in out_txt for m in invalid_markers):
        out_path.unlink(missing_ok=True)
        return {
            "compiled": False,
            "reason": "witness_did_not_reproduce_clean_failure",
            "failing_count": len(verd.get("failing") or []),
        }
    return {
        "compiled": True,
        "witness_path": str(out_path),
        "failing_nodes": list(verd.get("failing") or []),
    }


def phase_repair(timeout_s: float) -> dict[str, Any]:
    t0 = time.perf_counter()
    if not STATE_PATH.is_file():
        return {"status": "SKIPPED__NO_DISCOVERY_STATE", "pass": False, "model_calls": 0}
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    repo_root = pathlib.Path(state["repo_root"])
    py_exe = str(state["python_exe"])
    ranked_tests: list[str] = list(state.get("ranked_tests") or [])

    if not state.get("ecosystems", {}).get("python"):
        _clean_untracked_in_repo(repo_root)
        _reap_children()
        return {
            "status": "OPEN__NO_PYTHON_FAILING_TARGET_IDENTIFIED",
            "ecosystems": state.get("ecosystems"),
            "pass": False,
            "wall_s": round(time.perf_counter() - t0, 3),
            "model_calls": 0,
        }

    from canonical.swe_kernel.causal_swe_repair_v1 import (
        SWERepairMemory,
        repair_worktree,
        run_pytest_verdicts,
    )
    from canonical.swe_kernel.petri_cow_splicing_engine_v1 import AdmissionFilteredSkillStore

    failing_target: str | list[str] | None = None
    witness_info: dict[str, Any] = {"compiled": False}
    for cand_t in ranked_tests[:4]:
        if time.perf_counter() - t0 > timeout_s * 0.30:
            break
        verd = run_pytest_verdicts(repo_root, cand_t, python_exe=py_exe, timeout_s=20.0)
        if verd.get("failing"):
            failing_target = cand_t
            break

    if failing_target is None:
        witness_info = compile_issue_witness_test(
            str(state.get("instruction") or ""),
            repo_root,
            py_exe,
        )
        if witness_info.get("compiled"):
            failing_target = str(witness_info["witness_path"])

    if failing_target is None:
        _clean_untracked_in_repo(repo_root)
        _reap_children()
        return {
            "status": "OPEN__NO_PRE_EXISTING_FAILING_TEST_IN_WORKTREE",
            "probed_tests": ranked_tests[:4],
            "witness_compiler": witness_info,
            "pass": False,
            "wall_s": round(time.perf_counter() - t0, 3),
            "model_calls": 0,
        }

    rem_budget = max(15.0, timeout_s - (time.perf_counter() - t0) - 5.0)
    mem = SWERepairMemory(MEM_PATH)
    skill_store = AdmissionFilteredSkillStore(SKILL_PATH, mode="generalized")
    outcome = repair_worktree(
        repo_root,
        failing_target,
        python_exe=py_exe,
        memory=mem,
        skill_store=skill_store,
        budget_s=rem_budget,
    )
    WITNESS_TEST_PATH.unlink(missing_ok=True)
    if not outcome.get("pass"):
        try:
            subprocess.run(
                ["git", "-C", str(repo_root), "checkout", "--", "."],
                capture_output=True,
                timeout=15,
            )
        except Exception:
            pass
    _clean_untracked_in_repo(repo_root)
    reaped = _reap_children()
    return {
        "status": outcome.get("status"),
        "pass": bool(outcome.get("pass")),
        "failing_target": failing_target,
        "winning_mechanism": outcome.get("winning_mechanism"),
        "learned_skill_id": outcome.get("learned_skill_id"),
        "repaired_file": outcome.get("repaired_file"),
        "repaired_line": outcome.get("repaired_line"),
        "reaped_children": reaped,
        "wall_s": round(time.perf_counter() - t0, 3),
        "model_calls": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("discover", "repair"), required=True)
    parser.add_argument("--instruction-b64", default="")
    parser.add_argument("--timeout-s", type=float, default=120.0)
    args = parser.parse_args()

    if args.phase == "discover":
        instr = base64.b64decode(args.instruction_b64.encode("ascii")).decode("utf-8", errors="replace") if args.instruction_b64 else ""
        out = phase_discover(instr)
    else:
        out = phase_repair(args.timeout_s)
    print(json.dumps(out, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
