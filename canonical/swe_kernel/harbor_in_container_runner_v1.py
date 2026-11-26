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
import zlib
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
    scan_deadline = time.perf_counter() + 12.0

    for root_dir, dirs, files in os.walk(repo_root):
        if time.perf_counter() >= scan_deadline:
            break
        dirs[:] = [
            d for d in dirs
            if not d.startswith(".") and d not in {"node_modules", "__pycache__", "build", "dist", "venv", ".venv"}
        ]
        for fname in files:
            if time.perf_counter() >= scan_deadline:
                break
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
        "instruction": instruction,
        "instruction_chars": len(instruction),
        "discover_wall_s": round(time.perf_counter() - t0, 3),
        "model_calls": 0,
    }
    STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    _reap_children()
    return {
        "schema": state["schema"],
        "repo_root": state["repo_root"],
        "python_exe": state["python_exe"],
        "ecosystems": state["ecosystems"],
        "ranked_tests": ranked_tests[:6],
        "instruction_chars": len(instruction),
        "discover_wall_s": state["discover_wall_s"],
        "model_calls": 0,
    }


def _list_untracked(repo_root: pathlib.Path) -> set[str]:
    try:
        st = subprocess.run(
            ["git", "-C", str(repo_root), "status", "--porcelain", "-uall"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if st.returncode == 0:
            return {
                ln[3:].strip()
                for ln in st.stdout.splitlines()
                if ln.startswith("?? ") and ln[3:].strip()
            }
    except Exception:
        pass
    return set()


def _clean_untracked_in_repo(
    repo_root: pathlib.Path,
    *,
    revert_tracked: bool = False,
    pre_untracked: set[str] | None = None,
) -> None:
    """Restore tracked files when no repair verified and remove only newly created untracked entries."""
    try:
        if revert_tracked:
            subprocess.run(
                ["git", "-C", str(repo_root), "checkout", "--", "."],
                capture_output=True,
                timeout=20,
            )
        cur_untracked = _list_untracked(repo_root)
        baseline = pre_untracked if pre_untracked is not None else set()
        for rel in sorted(cur_untracked):
            if pre_untracked is not None and rel in baseline:
                continue
            if pre_untracked is None and not (
                "__pycache__" in rel or ".pytest_cache" in rel or rel.endswith(".pyc")
            ):
                continue
            target = (repo_root / rel).resolve()
            if repo_root in target.parents:
                if target.is_dir():
                    shutil.rmtree(target, ignore_errors=True)
                else:
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


def synthesize_metamorphic_green_witness(
    instruction: str,
    repo_root: pathlib.Path,
    py_exe: str,
    *,
    out_path: pathlib.Path = WITNESS_TEST_PATH,
) -> dict[str, Any]:
    """Active Counterfactual Metamorphic Witness Splitter (Wall 1: 100%-green parent suite).

    When `instruction` contains only prose (no doctest / fenced repro) and existing tests are
    100% green, scan non-test modules matching identifiers in `instruction` and execute three
    active counterfactual algebraic probes in an isolated child process:
      1. `ACTIVE_RETURN_ALIAS_INDEPENDENCE`: mutating one returned mutable container (`list`/`dict`/`set`)
         of a composite return tuple must not corrupt sibling returned iterables/values.
      2. `PREDICATE_CANONICALIZER_FIXED_POINT`: when `is_<X>(g)` agrees with `canonicalize_<X>(g) == g`
         across baseline valid strings, any string `p` with `is_<X>(p) is True` must satisfy `canonicalize_<X>(p) == p`.
      3. `FALSY_CALLABLE_KEY_EQUIVALENCE`: optional `key=None` callable parameters must treat a
         `__bool__() == False` callable identically to an equivalent truthy callable.
    """
    from canonical.swe_kernel.causal_swe_repair_v1 import _clean_env, run_pytest_verdicts

    out_path.unlink(missing_ok=True)
    if not instruction.strip():
        return {"compiled": False, "reason": "empty_instruction"}

    tokens = {
        tok
        for tok in re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,40}", instruction)
        if tok.lower() not in {"the", "and", "for", "with", "when", "fix", "make", "that", "from", "this", "none", "true", "false"}
    }
    if not tokens:
        return {"compiled": False, "reason": "no_identifier_tokens"}

    src_base = repo_root / "src" if (repo_root / "src").is_dir() else repo_root
    cand_targets: list[tuple[str, str, str | None]] = []
    scan_dl = time.perf_counter() + 2.5
    for idx_f, py_p in enumerate(src_base.rglob("*.py")):
        if idx_f >= 400 or time.perf_counter() >= scan_dl:
            break
        rel_src = py_p.relative_to(src_base).as_posix()
        if any(p.startswith(("test", ".")) for p in rel_src.split("/")):
            continue
        if py_p.stat().st_size > 220_000:
            continue
        try:
            tree = ast.parse(py_p.read_text(encoding="utf-8", errors="ignore"))
        except SyntaxError:
            continue
        fn_defs = {
            st.name: st for st in tree.body if isinstance(st, ast.FunctionDef) and not st.name.startswith("_")
        }
        if not fn_defs:
            continue
        mod_dotted = rel_src.removesuffix(".py").replace("/", ".")
        if mod_dotted.endswith(".__init__"):
            mod_dotted = mod_dotted.removesuffix(".__init__")
        for fn_nm in sorted(fn_defs):
            matched_tok = (fn_nm in tokens) or (py_p.stem in {t.lower() for t in tokens} and fn_nm.startswith("is_"))
            if not matched_tok:
                continue
            sib_canon: str | None = None
            if fn_nm.startswith("is_"):
                for c_nm in fn_defs:
                    if c_nm.startswith(("canonicalize_", "normalize_")):
                        sib_canon = c_nm
                        break
            cand_targets.append((mod_dotted, fn_nm, sib_canon))
            if len(cand_targets) >= 6:
                break
        if len(cand_targets) >= 6:
            break

    if not cand_targets:
        return {"compiled": False, "reason": "no_matching_repo_functions"}

    probe_script = textwrap.dedent(
        """
        import copy, importlib, inspect, json, sys

        targets = json.loads(sys.argv[1])
        out_witness = None

        for mod_name, fn_name, sib_canon in targets:
            try:
                mod = importlib.import_module(mod_name)
                fn = getattr(mod, fn_name)
            except Exception:
                continue

            # Probe 1: Predicate-Canonicalizer Fixed-Point Commutativity (`is_X` vs `canonicalize_X`)
            if sib_canon and hasattr(mod, sib_canon):
                canon_fn = getattr(mod, sib_canon)
                green_seeds = ["alpha", "alpha-beta", "pkg1", "simple-name"]
                verified_green = []
                law_holds_on_green = True
                for g in green_seeds:
                    try:
                        if fn(g) is True:
                            if canon_fn(g) == g:
                                verified_green.append(g)
                            else:
                                law_holds_on_green = False
                    except Exception:
                        pass
                if law_holds_on_green and len(verified_green) >= 2:
                    for p in ("a--b", "a__b", "a..b", "a---b"):
                        try:
                            if fn(p) is True and canon_fn(p) != p:
                                out_witness = {
                                    "relation": "PREDICATE_CANONICALIZER_FIXED_POINT",
                                    "target": f"{mod_name}.{fn_name}",
                                    "code": (
                                        "import unittest\\n"
                                        f"from {mod_name} import {fn_name}, {sib_canon}\\n\\n"
                                        "class TestMetamorphicWitness(unittest.TestCase):\\n"
                                        "    def test_metamorphic_fixed_point_violation(self):\\n"
                                        f"        self.assertNotEqual({sib_canon}({p!r}), {p!r})\\n"
                                        f"        self.assertFalse({fn_name}({p!r}))\\n\\n"
                                        "    def test_metamorphic_valid_controls(self):\\n"
                                        f"        self.assertTrue({fn_name}({verified_green[0]!r}))\\n"
                                        f"        self.assertTrue({fn_name}({verified_green[1]!r}))\\n"
                                        f"        self.assertFalse({fn_name}('Invalid_Upper'))\\n"
                                    ),
                                }
                                break
                        except Exception:
                            pass
                if out_witness:
                    break

            # Probe 2: Active Return-Alias Independence (`r1, r2 = fn(seed)` -> mutating `r1` must not corrupt `r2`)
            try:
                sig = inspect.signature(fn)
                req_pos = [
                    p for p in sig.parameters.values()
                    if p.default is inspect.Parameter.empty
                    and p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
                ]
                seed_arg_sets = []
                if len(req_pos) <= 1:
                    seed_arg_sets.append(([10, 20, 30, 40],))
                    seed_arg_sets.append(([10, 20, 30, 40], 2))
                elif len(req_pos) == 2:
                    seed_arg_sets.append(([10, 20, 30, 40], 2))
                for s_args in seed_arg_sets:
                    try:
                        r_clean = fn(*copy.deepcopy(s_args))
                    except Exception:
                        continue
                    if not isinstance(r_clean, tuple) or len(r_clean) != 2:
                        continue
                    if isinstance(r_clean[0], list) and len(r_clean[0]) >= 1 and hasattr(r_clean[1], "__iter__"):
                        clean_head = list(r_clean[0])
                        clean_seq = list(r_clean[1])
                        r_mut = fn(*copy.deepcopy(s_args))
                        r_mut[0][0] = "__BRAIN_MUTATED_HEAD__"
                        mut_seq = list(r_mut[1])
                        if mut_seq != clean_seq:
                            out_witness = {
                                "relation": "ACTIVE_RETURN_ALIAS_INDEPENDENCE",
                                "target": f"{mod_name}.{fn_name}",
                                "code": (
                                    "import unittest\\n"
                                    f"from {mod_name} import {fn_name}\\n\\n"
                                    "class TestMetamorphicWitness(unittest.TestCase):\\n"
                                    "    def test_metamorphic_return_alias_isolation(self):\\n"
                                    f"        head, it_out = {fn_name}(*{s_args!r})\\n"
                                    "        head[0] = '__BRAIN_MUTATED_HEAD__'\\n"
                                    f"        self.assertEqual(list(it_out), {clean_seq!r})\\n\\n"
                                    "    def test_metamorphic_unmutated_control(self):\\n"
                                    f"        head, it_out = {fn_name}(*{s_args!r})\\n"
                                    f"        self.assertEqual(head, {clean_head!r})\\n"
                                    f"        self.assertEqual(list(it_out), {clean_seq!r})\\n"
                                ),
                            }
                            break
                if out_witness:
                    break
            except Exception:
                pass

            # Probe 3: Falsy-Callable `key` Parameter Equivalence
            try:
                sig = inspect.signature(fn)
                if "key" in sig.parameters:
                    class _FalsyKey:
                        def __bool__(self):
                            return False
                        def __call__(self, x):
                            return x % 2
                    req_n = sum(
                        1 for p in sig.parameters.values()
                        if p.default is inspect.Parameter.empty
                        and p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
                    )
                    pos_call = ([1, 2, 3, 4],) if req_n <= 1 else ([1, 2, 3, 4], 2)
                    truthy_out = list(fn(*copy.deepcopy(pos_call), key=lambda x: x % 2))
                    falsy_out = list(fn(*copy.deepcopy(pos_call), key=_FalsyKey()))
                    if falsy_out != truthy_out:
                        out_witness = {
                            "relation": "FALSY_CALLABLE_KEY_EQUIVALENCE",
                            "target": f"{mod_name}.{fn_name}",
                            "code": (
                                "import unittest\\n"
                                f"from {mod_name} import {fn_name}\\n\\n"
                                "class _FalsyKey:\\n"
                                "    def __bool__(self): return False\\n"
                                "    def __call__(self, x): return x % 2\\n\\n"
                                "class TestMetamorphicWitness(unittest.TestCase):\\n"
                                "    def test_metamorphic_falsy_key_callable(self):\\n"
                                f"        self.assertEqual(list({fn_name}(*{pos_call!r}, key=_FalsyKey())), {truthy_out!r})\\n\\n"
                                "    def test_metamorphic_truthy_key_control(self):\\n"
                                f"        self.assertEqual(list({fn_name}(*{pos_call!r}, key=lambda x: x % 2)), {truthy_out!r})\\n"
                            ),
                        }
                        break
            except Exception:
                pass

            # Probe 4: Disabled Optional Dunder Protocol Equivalence (`__reversed__ = None`)
            # In Python's data model, setting an optional protocol attribute (`__reversed__`) to `None`
            # explicitly disables that protocol and MUST behave identically to omitting it (`__iter__` fallback)!
            try:
                class _PlainIterOnly:
                    def __init__(self, data):
                        self._data = list(data)
                    def __iter__(self):
                        return iter(self._data)

                class _DisabledReversedIter:
                    __reversed__ = None
                    def __init__(self, data):
                        self._data = list(data)
                    def __iter__(self):
                        return iter(self._data)

                plain_val = fn(_PlainIterOnly([1, 2, 3]))
                if hasattr(plain_val, "__iter__") and not isinstance(plain_val, (str, bytes, list, tuple, dict, set)):
                    plain_val = list(plain_val)
                if isinstance(plain_val, (int, float, str, bytes, bool, list, tuple)):
                    crashed_or_diff = False
                    try:
                        dis_val = fn(_DisabledReversedIter([1, 2, 3]))
                        if hasattr(dis_val, "__iter__") and not isinstance(dis_val, (str, bytes, list, tuple, dict, set)):
                            dis_val = list(dis_val)
                        crashed_or_diff = (dis_val != plain_val)
                    except Exception:
                        crashed_or_diff = True
                    if crashed_or_diff:
                        wrap_call = f"list({fn_name}(x))" if isinstance(plain_val, list) else f"{fn_name}(x)"
                        out_witness = {
                            "relation": "DISABLED_DUNDER_FALLBACK_EQUIVALENCE",
                            "target": f"{mod_name}.{fn_name}",
                            "code": (
                                "import unittest\\n"
                                f"from {mod_name} import {fn_name}\\n\\n"
                                "class _PlainIterOnly:\\n"
                                "    def __init__(self, d): self._d = list(d)\\n"
                                "    def __iter__(self): return iter(self._d)\\n\\n"
                                "class _DisabledReversedIter:\\n"
                                "    __reversed__ = None\\n"
                                "    def __init__(self, d): self._d = list(d)\\n"
                                "    def __iter__(self): return iter(self._d)\\n\\n"
                                "class TestMetamorphicWitness(unittest.TestCase):\\n"
                                "    def test_metamorphic_disabled_reversed_protocol(self):\\n"
                                "        x = _DisabledReversedIter([1, 2, 3])\\n"
                                f"        self.assertEqual({wrap_call}, {plain_val!r})\\n\\n"
                                "    def test_metamorphic_plain_iter_control(self):\\n"
                                "        x = _PlainIterOnly([1, 2, 3])\\n"
                                f"        self.assertEqual({wrap_call}, {plain_val!r})\\n"
                            ),
                        }
                        break
            except Exception:
                pass

            # Probe 5: Bidirectional Codec / Serializer Round-Trip Equivalence (`dec(enc(x)) == x`)
            try:
                inv_pairs = [
                    ("encode", "decode"), ("escape", "unescape"),
                    ("quote", "unquote"), ("format", "parse"), ("dumps", "loads"),
                ]
                sibling_dec = None
                enc_fn_obj = None
                dec_fn_obj = None
                enc_nm = ""
                dec_nm = ""
                for p_enc, p_dec in inv_pairs:
                    if fn_name == p_enc or fn_name.startswith(p_enc + "_"):
                        suf = fn_name[len(p_enc):]
                        cand_d = getattr(mod, p_dec + suf, None)
                        if callable(cand_d):
                            enc_fn_obj, dec_fn_obj, enc_nm, dec_nm = fn, cand_d, fn_name, p_dec + suf
                            break
                    elif fn_name == p_dec or fn_name.startswith(p_dec + "_"):
                        suf = fn_name[len(p_dec):]
                        cand_e = getattr(mod, p_enc + suf, None)
                        if callable(cand_e):
                            enc_fn_obj, dec_fn_obj, enc_nm, dec_nm = cand_e, fn, p_enc + suf, fn_name
                            break
                if enc_fn_obj is not None and dec_fn_obj is not None:
                    ctrl_ok = (dec_fn_obj(enc_fn_obj("abc")) == "abc")
                    if ctrl_ok:
                        for w_rt in ('a"b', r"a\\b", 'a\\"b', "a\\nb", "a%25b", "a=b&c=d", ""):
                            try:
                                enc_w = enc_fn_obj(w_rt)
                                rt_val = dec_fn_obj(enc_w)
                                broke = (rt_val != w_rt)
                                non_id_line = (
                                    f"        self.assertNotEqual({enc_nm}({w_rt!r}), {w_rt!r})\\n"
                                    if enc_w != w_rt
                                    else ""
                                )
                            except Exception:
                                broke = True
                                non_id_line = ""
                            if broke:
                                out_witness = {
                                    "relation": "BIDIRECTIONAL_CODEC_ROUNDTRIP_EQUIVALENCE",
                                    "target": f"{mod_name}.{enc_nm}/{dec_nm}",
                                    "code": (
                                        "import unittest\\n"
                                        f"from {mod_name} import {enc_nm}, {dec_nm}\\n\\n"
                                        "class TestMetamorphicWitness(unittest.TestCase):\\n"
                                        "    def test_metamorphic_roundtrip_boundary(self):\\n"
                                        f"{non_id_line}"
                                        f"        self.assertEqual({dec_nm}({enc_nm}({w_rt!r})), {w_rt!r})\\n\\n"
                                        "    def test_metamorphic_roundtrip_control(self):\\n"
                                        f"        self.assertEqual({dec_nm}({enc_nm}('abc')), 'abc')\\n"
                                    ),
                                }
                                break
                if out_witness:
                    break
            except Exception:
                pass

        print(json.dumps(out_witness or {}))
        """
    ).strip()

    try:
        done = subprocess.run(
            [py_exe, "-c", probe_script, json.dumps(cand_targets)],
            cwd=str(repo_root),
            env=_clean_env(repo_root),
            capture_output=True,
            text=True,
            timeout=10.0,
        )
        if done.returncode != 0 or not done.stdout.strip():
            return {"compiled": False, "reason": "probe_no_violation"}
        res_obj = json.loads(done.stdout.strip().splitlines()[-1])
        if not res_obj or not res_obj.get("code"):
            return {"compiled": False, "reason": "no_metamorphic_violation_detected"}
        out_path.write_text(str(res_obj["code"]), encoding="utf-8")
        verd = run_pytest_verdicts(repo_root, str(out_path), python_exe=py_exe, timeout_s=10.0)
        if not verd.get("failing") or not verd.get("passing"):
            out_path.unlink(missing_ok=True)
            return {"compiled": False, "reason": "metamorphic_witness_did_not_separate"}
        return {
            "compiled": True,
            "relation": res_obj.get("relation"),
            "target": res_obj.get("target"),
            "witness_path": str(out_path),
            "failing_nodes": list(verd.get("failing") or []),
        }
    except Exception:
        out_path.unlink(missing_ok=True)
        return {"compiled": False, "reason": "probe_exception"}


def phase_repair(timeout_s: float) -> dict[str, Any]:
    t0 = time.perf_counter()
    if not STATE_PATH.is_file():
        return {"status": "SKIPPED__NO_DISCOVERY_STATE", "pass": False, "model_calls": 0}
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    repo_root = pathlib.Path(state["repo_root"])
    py_exe = str(state["python_exe"])
    ranked_tests: list[str] = list(state.get("ranked_tests") or [])
    pre_untracked = _list_untracked(repo_root)

    if not state.get("ecosystems", {}).get("python"):
        _clean_untracked_in_repo(repo_root, pre_untracked=pre_untracked)
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
        _regression_check,
    )
    from canonical.swe_kernel.petri_cow_splicing_engine_v1 import AdmissionFilteredSkillStore

    import signal

    def _alarm_handler(_signum: int, _frame: Any) -> None:
        raise TimeoutError("HARBOR_REPAIR_WATCHDOG_EXPIRED")

    prev_handler = signal.signal(signal.SIGALRM, _alarm_handler)
    signal.alarm(max(20, int(timeout_s) + 15))
    try:
        failing_target: str | list[str] | None = None
        witness_info: dict[str, Any] = {"compiled": False}
        originals_checked: dict[str, dict] = {}
        for cand_t in ranked_tests[:4]:
            if time.perf_counter() - t0 > timeout_s * 0.30:
                break
            verd = run_pytest_verdicts(repo_root, cand_t, python_exe=py_exe, timeout_s=15.0)
            originals_checked[cand_t] = verd
            if verd.get("returncode") == 1 and verd.get("failing"):
                failing_target = cand_t
                break

        if failing_target is None:
            witness_info = compile_issue_witness_test(
                str(state.get("instruction") or ""),
                repo_root,
                py_exe,
            )
            if not witness_info.get("compiled"):
                witness_info = synthesize_metamorphic_green_witness(
                    str(state.get("instruction") or ""),
                    repo_root,
                    py_exe,
                )
            if witness_info.get("compiled"):
                failing_target = str(witness_info["witness_path"])

        probed = [{"target": name, "exit": v.get("returncode"), "timeout": bool(v.get("timeout")),
                   "passing": len(v['passing']), "failing": len(v['failing'])}
                  for name, v in originals_checked.items()]
        if failing_target is None:
            _clean_untracked_in_repo(repo_root, revert_tracked=True, pre_untracked=pre_untracked)
            _reap_children()
            return {
                "status": ("OPEN__NO_FAILING_WITNESS_OBSERVED" if any(v["ok"] for v in originals_checked.values())
                           else "OPEN__NO_USABLE_NATIVE_TEST_RESULT_OR_WITNESS"),
                "probed_tests": list(originals_checked), "probe_outcomes": probed,
                "witness_compiler": witness_info,
                "pass": False,
                "wall_s": round(time.perf_counter() - t0, 3),
                "model_calls": 0,
            }

        rem_budget = min(38.0, max(12.0, timeout_s - (time.perf_counter() - t0) - 15.0))
        mem = SWERepairMemory(MEM_PATH)
        skill_store = AdmissionFilteredSkillStore(SKILL_PATH, mode="generalized")
        outcome = repair_worktree(
            repo_root,
            failing_target,
            python_exe=py_exe,
            memory=mem,
            skill_store=skill_store,
            budget_s=rem_budget,
            admit_skills=not witness_info.get("compiled"),  # a deleted /tmp test cannot revalidate a skill
        )
        # If repaired against a synthesized `/tmp` witness, also verify existing ranked unit test file!
        if outcome.get("pass") and witness_info.get("compiled") and ranked_tests:
            reg_chk = run_pytest_verdicts(repo_root, ranked_tests[0], python_exe=py_exe, timeout_s=15.0)
            reason = _regression_check(originals_checked.get(ranked_tests[0], {}), reg_chk)
            if reason:
                outcome = {
                    **outcome,
                    "status": reason + "__AFTER_WITNESS_REPAIR",
                    "pass": False,
                }
        WITNESS_TEST_PATH.unlink(missing_ok=True)
        if witness_info.get("witness_path"):
            pathlib.Path(str(witness_info["witness_path"])).unlink(missing_ok=True)
        _clean_untracked_in_repo(
            repo_root,
            revert_tracked=not bool(outcome.get("pass")),
            pre_untracked=pre_untracked,
        )
        reaped = _reap_children()
        return {
            "status": outcome.get("status"),
            "pass": bool(outcome.get("pass")),
            "failing_target": failing_target,
            "winning_mechanism": outcome.get("winning_mechanism"),
            "learned_skill_id": outcome.get("learned_skill_id"),
            "reused_skill_id": outcome.get("reused_skill_id"),
            "subtree_admission": outcome.get("subtree_admission"),
            "probe_outcomes": probed,
            "repaired_file": outcome.get("repaired_file"),
            "repaired_line": outcome.get("repaired_line"),
            "reaped_children": reaped,
            "wall_s": round(time.perf_counter() - t0, 3),
            "model_calls": 0,
        }
    except BaseException as exc:
        WITNESS_TEST_PATH.unlink(missing_ok=True)
        if isinstance(locals().get("witness_info"), dict) and witness_info.get("witness_path"):
            pathlib.Path(str(witness_info["witness_path"])).unlink(missing_ok=True)
        _clean_untracked_in_repo(repo_root, revert_tracked=True, pre_untracked=pre_untracked)
        reaped = _reap_children()
        return {
            "status": "OPEN__WATCHDOG_OR_CONTAINER_ABORT",
            "reason": f"{type(exc).__name__}:{str(exc)[:120]}",
            "pass": False,
            "reaped_children": reaped,
            "wall_s": round(time.perf_counter() - t0, 3),
            "model_calls": 0,
        }
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, prev_handler)


def _instruction_text(body: str, *, compressed: bool) -> str:
    data = base64.b64decode(body, validate=True)
    limit = 64_000
    if compressed:
        obj = zlib.decompressobj()
        data = obj.decompress(data, limit + 1)
        if not obj.eof or obj.unused_data:
            raise ValueError('INCOMPLETE_OR_OVERSIZED_INSTRUCTION')
    if len(data) > limit:
        raise ValueError('INSTRUCTION_TOO_LARGE')
    return data.decode('utf-8')


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("discover", "repair"), required=True)
    payload = parser.add_mutually_exclusive_group()
    payload.add_argument("--instruction-b64", default="")
    payload.add_argument("--instruction-zlib-b64", default="")
    parser.add_argument("--timeout-s", type=float, default=120.0)
    args = parser.parse_args()

    # Keep runner stderr strictly empty so `observations[*]["stderr"]` never inflates
    # Harbor's 64 KB `MAX_WORKER_REQUEST_BYTES` budget on multi-cycle large-instruction tasks.
    devnull = open(os.devnull, "w", encoding="utf-8")
    sys.stderr = devnull
    try:
        if args.phase == "discover":
            instr = _instruction_text(args.instruction_zlib_b64 or args.instruction_b64,
                                      compressed=bool(args.instruction_zlib_b64))
            out = phase_discover(instr)
        else:
            out = phase_repair(args.timeout_s)
    finally:
        sys.stderr = sys.__stderr__
        devnull.close()
    print(json.dumps(out, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
