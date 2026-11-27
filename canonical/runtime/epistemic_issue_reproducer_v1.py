"""Zero-LLM, Zero-Weight Polyglot Epistemic Issue-to-Reproducer & Blind SWE Resolver (v1).

Solves the fundamental real-world SWE-bench / SWE-bench Pro bottleneck where an agent is given
ONLY a pre-fix repository `c_old` (whose existing tests all pass) and a natural-language /
code-augmented GitHub issue description `d_issue` — WITHOUT any hidden golden test `t_gold`.

Algorithm (model_calls == 0, parameters_stored == 0, stdlib-only):
  1. `scan_repo_symbols(repo_root)`:
     Scans Python ASTs / JS exports AND existing repository tests to harvest exact module import
     paths, exported symbols, exception classes, and proven test import conventions + pass2pass
     regression test files.
  2. `compile_issue_specs(issue_text, repo_index)`:
     Compiles executable reproducer test candidates from:
       - Fenced code blocks (`python`/`py`/`js`/`javascript`/`node`) & Python `>>>` doctests
       - Inline `# Expected:` / `// Expected:` / `# raises Exc` / `assert` specifications
       - Structured prose behavioral clauses (`sym(args)` returns X instead of Y / should return Y
         / should raise Exc / fails to raise Exc / crashes with Exc)
       - Contrastive passing examples (anti-overfit protection)
  3. `synthesize_verified_reproducer(repo_root, issue_text)`:
     Materializes candidate reproducer tests using proven repo imports and qualifies them live
     against `c_old` under the strict F->P Epistemic Gate:
       - Rejects tests that pass on `c_old` (rc == 0)
       - Rejects harness/import/syntax errors (ImportError/NameError/SyntaxError/ReferenceError)
       - Accepts ONLY tests that fail cleanly on `c_old` with a genuine behavioral failure.
  4. `solve_issue_from_description(repo_root, issue_text)`:
     End-to-end blind issue resolution:
       - Synthesizes & qualifies `t_gen` on `c_old` in an isolated workspace
       - Invokes `causal_angelic_swe_engine_v1` (Python) or `multilang_causal_swe_engine_v1` (JS/TS)
       - Removes `t_gen` and verifies the candidate patch against existing `pass2pass` regression tests
       - Emits a clean unified diff (`patch_diff`) ready for `git apply` / Harbor `model.patch`.
"""
from __future__ import annotations

import ast
import difflib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

SCHEMA = "BRAIN_EPISTEMIC_ISSUE_REPRODUCER_V1"
AUTHORITY = "NONE"

_SKIP_DIRS = frozenset({
    ".git", ".hg", ".svn", ".venv", "venv", "env", "node_modules", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox", "build", "dist",
    ".eggs", ".next", "out", "coverage",
})

_PY_HARNESS_ERRORS = (
    "SyntaxError:",
    "IndentationError:",
    "TabError:",
    "ImportError:",
    "ModuleNotFoundError:",
    "No module named ",
    "NameError:",
    "AttributeError: module ",
    "ERROR collecting ",
    "required positional argument",
    "positional argument but",
)

_PYTEST_AVAIL_CACHE: dict[str, bool] = {}


def _python_has_pytest(python_exe: str) -> bool:
    """Cached check whether `python_exe` has `pytest` importable."""
    if python_exe not in _PYTEST_AVAIL_CACHE:
        try:
            proc = subprocess.run(
                [python_exe, "-c", "import pytest"],
                capture_output=True,
                text=True,
                timeout=10.0,
            )
            _PYTEST_AVAIL_CACHE[python_exe] = proc.returncode == 0
        except Exception:
            _PYTEST_AVAIL_CACHE[python_exe] = False
    return _PYTEST_AVAIL_CACHE[python_exe]


_STDLIB_TEST_RUNNER_SNIPPET = r"""
import importlib.util, inspect, pathlib, sys, tempfile, traceback, unittest

failed = 0
ran = 0
for rel in sys.argv[1:]:
    p = pathlib.Path(rel).resolve()
    spec = importlib.util.spec_from_file_location(p.stem, p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    suite = unittest.defaultTestLoader.loadTestsFromModule(mod)
    if suite.countTestCases() > 0:
        res = unittest.TextTestRunner(verbosity=0).run(suite)
        ran += res.testsRun
        failed += len(res.failures) + len(res.errors)
    for name, obj in inspect.getmembers(mod, inspect.isfunction):
        if not name.startswith("test_") or obj.__module__ != mod.__name__:
            continue
        sig = inspect.signature(obj)
        kwargs = {}
        tmp_ctx = None
        if "tmp_path" in sig.parameters:
            tmp_ctx = tempfile.TemporaryDirectory()
            kwargs["tmp_path"] = pathlib.Path(tmp_ctx.name)
        elif any(p_.default is inspect.Parameter.empty for p_ in sig.parameters.values()):
            continue
        ran += 1
        try:
            obj(**kwargs)
        except Exception:
            failed += 1
            traceback.print_exc()
        finally:
            if tmp_ctx is not None:
                tmp_ctx.cleanup()
if ran == 0:
    print("ERROR collecting 0 runnable tests", file=sys.stderr)
    sys.exit(2)
sys.exit(1 if failed > 0 else 0)
"""

_JS_HARNESS_ERRORS = (
    "SyntaxError:",
    "ReferenceError:",
    "Cannot find module",
    "ERR_MODULE_NOT_FOUND",
    "ERR_INVALID_ARG_TYPE",
)


@dataclass
class SymbolEntry:
    name: str
    language: str
    rel_path: str
    module_path: str
    kind: str  # "function", "class", "exception", "export", "default_export"
    lineno: int = 1


@dataclass
class RepoSymbolIndex:
    repo_root: str
    language: str  # "python" | "javascript"
    python_src_root: str = ""
    package_name: str = ""
    package_main: str = ""
    js_is_esm: bool = False
    is_typescript_vitest: bool = False
    ts_entry_rel: str = ""
    symbols: dict[str, list[SymbolEntry]] = field(default_factory=dict)
    proven_imports: list[str] = field(default_factory=list)
    test_files: list[str] = field(default_factory=list)
    symbol_to_tests: dict[str, list[str]] = field(default_factory=dict)
    module_to_tests: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class CompiledReproSpec:
    kind: str  # "fenced_block" | "doctest" | "prose_return" | "prose_raises" | "prose_no_crash" | "prose_proto" | "existing_test_clone"
    language: str
    test_source: str
    referenced_symbols: list[str]
    expected_exception: str | None = None
    assertion_count: int = 1
    has_contrastive: bool = False
    description: str = ""
    test_subdir: str = ""
    source_test_file: str = ""


def _iter_repo_files(root: pathlib.Path, suffixes: tuple[str, ...]) -> list[pathlib.Path]:
    out: list[pathlib.Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in _SKIP_DIRS and not d.startswith("."))
        for fn in sorted(filenames):
            if fn.endswith(suffixes):
                out.append(pathlib.Path(dirpath) / fn)
    return out


def _is_test_rel(rel: str) -> bool:
    parts = pathlib.PurePosixPath(rel.replace("\\", "/")).parts
    low_parts = [p.lower() for p in parts]
    if any(p in ("test", "tests", "__tests__", "spec", "specs") for p in low_parts[:-1]):
        return True
    name = low_parts[-1] if low_parts else ""
    return (
        name.startswith("test_")
        or name.endswith("_test.py")
        or name.endswith(".test.js")
        or name.endswith(".spec.js")
        or name.endswith(".test.ts")
        or name.endswith(".spec.ts")
    )


def _detect_repo_language(root: pathlib.Path) -> str:
    has_pkg_json = (root / "package.json").is_file()
    has_py_meta = (
        (root / "pyproject.toml").is_file()
        or (root / "setup.py").is_file()
        or (root / "setup.cfg").is_file()
    )
    py_files = [p for p in _iter_repo_files(root, (".py",)) if not _is_test_rel(str(p.relative_to(root)))]
    js_files = [p for p in _iter_repo_files(root, (".js", ".mjs", ".cjs", ".ts")) if not _is_test_rel(str(p.relative_to(root)))]
    if has_py_meta and py_files and not (has_pkg_json and len(js_files) > len(py_files) * 2):
        return "python"
    if has_pkg_json and js_files:
        return "javascript"
    if len(py_files) >= len(js_files) and py_files:
        return "python"
    if js_files:
        return "javascript"
    return "python"


def _py_module_path(rel_posix: str, has_src_layout: bool) -> str:
    p = rel_posix
    if has_src_layout and p.startswith("src/"):
        p = p[4:]
    if p.endswith("/__init__.py"):
        p = p[:-12]
    elif p.endswith(".py"):
        p = p[:-3]
    return p.replace("/", ".").strip(".")


def scan_repo_symbols(repo_root: pathlib.Path) -> RepoSymbolIndex:
    """Deterministically scan source symbols and proven test import patterns in milliseconds."""
    root = pathlib.Path(repo_root).resolve()
    lang = _detect_repo_language(root)
    idx = RepoSymbolIndex(repo_root=str(root), language=lang)

    if lang == "python":
        has_src = (root / "src").is_dir() and any((root / "src").rglob("*.py"))
        idx.python_src_root = "src" if has_src else ""
        all_py = _iter_repo_files(root, (".py",))
        for fp in all_py:
            rel = fp.relative_to(root).as_posix()
            try:
                src_text = fp.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if _is_test_rel(rel):
                idx.test_files.append(rel)
                try:
                    t_tree = ast.parse(src_text)
                except SyntaxError:
                    continue
                for node in t_tree.body:
                    if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                        names = [a.name for a in node.names if a.name != "*"]
                        if names:
                            imp_line = f"from {node.module} import {', '.join(names)}"
                            if imp_line not in idx.proven_imports:
                                idx.proven_imports.append(imp_line)
                            idx.module_to_tests.setdefault(node.module, [])
                            if rel not in idx.module_to_tests[node.module]:
                                idx.module_to_tests[node.module].append(rel)
                            for nm in names:
                                idx.symbol_to_tests.setdefault(nm, [])
                                if rel not in idx.symbol_to_tests[nm]:
                                    idx.symbol_to_tests[nm].append(rel)
                    elif isinstance(node, ast.Import):
                        for a in node.names:
                            imp_line = f"import {a.name}" + (f" as {a.asname}" if a.asname else "")
                            if imp_line not in idx.proven_imports:
                                idx.proven_imports.append(imp_line)
                            idx.module_to_tests.setdefault(a.name, [])
                            if rel not in idx.module_to_tests[a.name]:
                                idx.module_to_tests[a.name].append(rel)
                continue

            # Source file
            if has_src and not rel.startswith("src/"):
                continue
            mod = _py_module_path(rel, has_src)
            if not mod:
                continue
            if not idx.package_name:
                idx.package_name = mod.split(".")[0]
            try:
                tree = ast.parse(src_text)
            except SyntaxError:
                continue
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    idx.symbols.setdefault(node.name, []).append(
                        SymbolEntry(node.name, "python", rel, mod, "function", getattr(node, "lineno", 1))
                    )
                elif isinstance(node, ast.ClassDef):
                    is_exc = any(
                        "Error" in ast.unparse(b) or "Exception" in ast.unparse(b) or "Warning" in ast.unparse(b)
                        for b in node.bases
                    )
                    kind = "exception" if is_exc else "class"
                    idx.symbols.setdefault(node.name, []).append(
                        SymbolEntry(node.name, "python", rel, mod, kind, getattr(node, "lineno", 1))
                    )
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and not item.name.startswith("__"):
                            qname = f"{node.name}.{item.name}"
                            idx.symbols.setdefault(qname, []).append(
                                SymbolEntry(qname, "python", rel, mod, "function", getattr(item, "lineno", 1))
                            )
            # Capture re-exported symbols from __init__.py
            if rel.endswith("/__init__.py"):
                for node in tree.body:
                    if isinstance(node, ast.ImportFrom):
                        for a in node.names:
                            nm = a.asname or a.name
                            if nm and nm != "*":
                                idx.symbols.setdefault(nm, []).insert(
                                    0, SymbolEntry(nm, "python", rel, mod, "export", getattr(node, "lineno", 1))
                                )
    else:
        # JavaScript / TypeScript
        pkg_json = root / "package.json"
        if pkg_json.is_file():
            try:
                pj = json.loads(pkg_json.read_text(encoding="utf-8"))
                idx.package_name = str(pj.get("name") or "").strip().split("/")[-1]
                idx.package_main = str(pj.get("main") or "index.js").strip()
                idx.js_is_esm = str(pj.get("type") or "").lower() == "module"
            except Exception:
                pass
        all_js = _iter_repo_files(root, (".js", ".mjs", ".cjs", ".ts"))
        for fp in all_js:
            rel = fp.relative_to(root).as_posix()
            try:
                src_text = fp.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if _is_test_rel(rel):
                idx.test_files.append(rel)
                for m_req in re.finditer(
                    r"^\s*(?:var|const|let)\s+([A-Za-z_$][\w${}\s,:]*)\s*=\s*require\(\s*['\"]([^'\"]+)['\"]\s*\)\s*;?",
                    src_text,
                    flags=re.MULTILINE,
                ):
                    line = m_req.group(0).strip()
                    if line not in idx.proven_imports:
                        idx.proven_imports.append(line)
                    mod_ref = m_req.group(2)
                    idx.module_to_tests.setdefault(mod_ref, [])
                    if rel not in idx.module_to_tests[mod_ref]:
                        idx.module_to_tests[mod_ref].append(rel)
                    for nm in re.findall(r"[A-Za-z_$]\w*", m_req.group(1)):
                        idx.symbol_to_tests.setdefault(nm, [])
                        if rel not in idx.symbol_to_tests[nm]:
                            idx.symbol_to_tests[nm].append(rel)
                continue

            # Source JS file: extract exports and named functions
            for m_exp in re.finditer(
                r"\b(?:module\.exports\s*=\s*\{([^}]+)\}|exports\.([A-Za-z_$]\w*)\s*=|export\s+(?:async\s+)?(?:function|const|let|var|class)\s+([A-Za-z_$]\w*))",
                src_text,
            ):
                if m_exp.group(1):
                    for key_m in re.finditer(r"([A-Za-z_$]\w*)\s*(?::|,|$)", m_exp.group(1)):
                        nm = key_m.group(1)
                        idx.symbols.setdefault(nm, []).append(SymbolEntry(nm, "javascript", rel, rel, "export"))
                else:
                    nm = m_exp.group(2) or m_exp.group(3)
                    if nm:
                        idx.symbols.setdefault(nm, []).append(SymbolEntry(nm, "javascript", rel, rel, "export"))
            for m_fn in re.finditer(
                r"\b(?:function\s+([A-Za-z_$]\w*)\s*\(|(?:var|const|let)\s+([A-Za-z_$]\w*)\s*=\s*function\b)",
                src_text,
            ):
                nm = m_fn.group(1) or m_fn.group(2)
                if nm:
                    idx.symbols.setdefault(nm, []).append(SymbolEntry(nm, "javascript", rel, rel, "function"))
            if idx.package_name:
                idx.symbols.setdefault(idx.package_name, []).append(
                    SymbolEntry(idx.package_name, "javascript", idx.package_main or "index.js", "./" + (idx.package_main or "index.js"), "default_export")
                )
        ts_src_files = [
            p.relative_to(root).as_posix()
            for p in all_js
            if p.suffix.lower() in (".ts", ".tsx", ".mts") and not _is_test_rel(p.relative_to(root).as_posix())
        ]
        if ts_src_files and (root / "node_modules" / ".bin" / "vitest").exists():
            idx.is_typescript_vitest = True
            idx.ts_entry_rel = "src/index.ts" if "src/index.ts" in ts_src_files else ts_src_files[0]

    return idx


def _extract_balanced_call(text: str, open_paren_idx: int) -> tuple[str, int] | None:
    """Return `(args_inside_parens, close_paren_idx)` respecting nested parens/brackets/quotes."""
    if open_paren_idx >= len(text) or text[open_paren_idx] != "(":
        return None
    depth = 0
    in_str: str | None = None
    esc = False
    for i in range(open_paren_idx, len(text)):
        ch = text[i]
        if esc:
            esc = False
            continue
        if in_str:
            if ch == "\\":
                esc = True
            elif ch == in_str:
                in_str = None
            continue
        if ch in ("'", '"', "`"):
            in_str = ch
        elif ch in ("(", "[", "{"):
            depth += 1
        elif ch in (")", "]", "}"):
            depth -= 1
            if depth == 0 and ch == ")":
                return text[open_paren_idx + 1 : i], i
    return None


def _build_python_imports(referenced: Sequence[str], repo_index: RepoSymbolIndex) -> list[str]:
    """Assemble exact working Python import lines from repo symbols + proven test imports."""
    imports: list[str] = []
    imported_names: set[str] = set()
    ref_set = set(referenced)
    # Also include dotted heads (e.g. `packaging.licenses` -> `packaging`)
    for r in list(ref_set):
        if "." in r:
            ref_set.add(r.split(".")[0])
            ref_set.add(r.split(".")[-1])

    # 1. Prefer top-level re-exports & exact symbol entries from source AST
    by_mod: dict[str, list[str]] = {}
    for sym in sorted(ref_set):
        entries = repo_index.symbols.get(sym)
        if not entries:
            continue
        # Prefer shorter module path (public package re-export over private submodule)
        best = min(entries, key=lambda e: (e.module_path.count("."), len(e.module_path)))
        if best.module_path and sym not in imported_names and "." not in sym:
            by_mod.setdefault(best.module_path, []).append(sym)
            imported_names.add(sym)

    for mod, names in sorted(by_mod.items()):
        imports.append(f"from {mod} import {', '.join(sorted(set(names)))}")

    # 2. If package root itself is referenced (e.g. `packaging.licenses...`), import it
    if repo_index.package_name and repo_index.package_name in ref_set and repo_index.package_name not in imported_names:
        imports.append(f"import {repo_index.package_name}")
        imported_names.add(repo_index.package_name)

    # 3. Pull any proven test imports matching referenced symbols not yet imported
    for imp_line in repo_index.proven_imports:
        if any(re.search(rf"\b{re.escape(s)}\b", imp_line) for s in ref_set - imported_names):
            if imp_line not in imports:
                imports.append(imp_line)

    return imports


def _build_js_imports(referenced: Sequence[str], repo_index: RepoSymbolIndex) -> list[str]:
    """Assemble working CommonJS/ESM/TypeScript-Vitest imports for a reproducer test at repo root."""
    pkg_var = re.sub(r"[^A-Za-z0-9_$]", "_", repo_index.package_name or "pkg")
    if not pkg_var or pkg_var[0].isdigit():
        pkg_var = "pkg"
    bare_exports: list[str] = []
    for sym in referenced:
        if sym == pkg_var or "." in sym:
            continue
        if sym in repo_index.symbols and sym not in bare_exports:
            bare_exports.append(sym)
    if repo_index.is_typescript_vitest:
        entry_rel = "./" + (repo_index.ts_entry_rel or "src/index.ts").lstrip("./")
        ts_exports = [
            nm for nm in bare_exports
            if any(e.kind == "export" for e in repo_index.symbols.get(nm, ()))
        ]
        lines = [
            "import { test, expect } from 'vitest';",
            "import assert from 'node:assert/strict';",
            f"import * as {pkg_var} from '{entry_rel}';",
        ]
        if ts_exports:
            lines.append(f"import {{ {', '.join(ts_exports)} }} from '{entry_rel}';")
        return lines

    main_rel = "./" + (repo_index.package_main or "index.js").lstrip("./")
    lines = [
        "const test = require('node:test');",
        "const assert = require('node:assert/strict');",
        f"const {pkg_var} = require('{main_rel}');",
    ]
    if bare_exports:
        for nm in bare_exports:
            lines.append(f"const {nm} = {pkg_var}.{nm};")
    return lines


def _extract_expected_literal_near(tail: str) -> str | None:
    """Extract a Python/JS literal or backticked value from prose immediately following a call."""
    patterns = [
        # "returns X instead of Y" / "produces X rather than Y" -> want Y!
        r"(?i)(?:instead\s+of|rather\s+than|not)\s+(?:returning\s+|producing\s+)?`([^`\n]+)`",
        r"(?i)(?:instead\s+of|rather\s+than)\s+(?:returning\s+|producing\s+)?(\{[^}\n]+\}|\[[^\]\n]+\]|'[^'\n]*'|\"[^\"\n]*\"|-?\d+(?:\.\d+)?|True|False|None|true|false|null|undefined)",
        # "should return Y" / "must return Y" / "expected Y" / "expected: Y"
        r"(?i)(?:should|must|expected\s+to)\s+(?:return|produce|output|yield|be|equal)\s+`([^`\n]+)`",
        r"(?i)(?:should|must|expected\s+to)\s+(?:return|produce|output|yield|be|equal)\s+(\{[^}\n]+\}|\[[^\]\n]+\]|'[^'\n]*'|\"[^\"\n]*\"|-?\d+(?:\.\d+)?|True|False|None|true|false|null|undefined)",
        r"(?i)expected(?:\s+output|\s+result|\s+value)?\s*[:=]\s*`([^`\n]+)`",
        r"(?i)expected(?:\s+output|\s+result|\s+value)?\s*[:=]\s*(\{[^}\n]+\}|\[[^\]\n]+\]|'[^'\n]*'|\"[^\"\n]*\"|-?\d+(?:\.\d+)?|True|False|None|true|false|null|undefined)",
        r"==+\s*`([^`\n]+)`",
        r"==+\s*(\{[^}\n]+\}|\[[^\]\n]+\]|'[^'\n]*'|\"[^\"\n]*\"|-?\d+(?:\.\d+)?|True|False|None|true|false|null|undefined)",
    ]
    for pat in patterns:
        m = re.search(pat, tail)
        if m:
            val = m.group(1).strip().rstrip(".,;")
            if val:
                return val
    return None


def _extract_expected_exception_near(tail: str, repo_index: RepoSymbolIndex) -> str | None:
    """Detect `should raise <Exc>` / `fails to raise <Exc>` / `should throw <Exc>`."""
    patterns = [
        r"(?i)(?:should|must|expected\s+to|fails?\s+to|does\s+not|doesn't|didn't)\s+(?:raise|throw)\s+`?([A-Z][A-Za-z0-9_]*(?:Error|Exception|Warning|Expression|Invalid[A-Za-z0-9_]*))`?",
        r"(?i)(?:instead\s+of\s+(?:raising|throwing)|reject(?:s|ing)?\b[^.\n]{0,40}\bwith)\s+`?([A-Z][A-Za-z0-9_]*(?:Error|Exception|Warning|Expression|Invalid[A-Za-z0-9_]*))`?",
        r"(?i)expected\s+`?([A-Z][A-Za-z0-9_]*(?:Error|Exception|Warning|Expression|Invalid[A-Za-z0-9_]*))`?",
    ]
    for pat in patterns:
        m = re.search(pat, tail)
        if m:
            exc = m.group(1).strip()
            if exc:
                return exc
    # Also check any repo-defined exception class mentioned near raise/reject/invalid
    if re.search(r"(?i)\b(?:raise|raises|throw|throws|reject|invalid)\b", tail):
        for sym, entries in repo_index.symbols.items():
            if any(e.kind == "exception" for e in entries) and re.search(rf"\b{re.escape(sym)}\b", tail):
                return sym
    return None


def _compile_fenced_blocks(issue_text: str, repo_index: RepoSymbolIndex) -> list[CompiledReproSpec]:
    specs: list[CompiledReproSpec] = []
    lang = repo_index.language
    fence_re = re.compile(r"```([A-Za-z0-9_+-]*)\n(.*?)```", flags=re.DOTALL)
    for m in fence_re.finditer(issue_text):
        tag = (m.group(1) or "").strip().lower()
        body = m.group(2).strip("\n")
        if not body.strip():
            continue
        if lang == "python" and tag not in ("", "py", "python", "python3", "pycon"):
            continue
        if lang == "javascript" and tag not in ("", "js", "javascript", "node", "ts", "typescript"):
            continue

        # Handle Python interactive `>>> ` doctest blocks inside fences
        if lang == "python" and ">>> " in body:
            specs.extend(_compile_doctest_block(body, issue_text[m.end() : m.end() + 400], repo_index))
            continue

        # Find referenced repo symbols in block
        refs = [s for s in repo_index.symbols if "." not in s and re.search(rf"\b{re.escape(s)}\b", body)]
        if lang == "python":
            spec = _wrap_python_snippet(body, issue_text[m.end() : m.end() + 400], refs, repo_index)
            if spec:
                specs.append(spec)
        else:
            spec = _wrap_js_snippet(body, issue_text[m.end() : m.end() + 400], refs, repo_index)
            if spec:
                specs.append(spec)
    return specs


def _compile_doctest_block(block: str, tail_prose: str, repo_index: RepoSymbolIndex) -> list[CompiledReproSpec]:
    """Convert `>>> ...` transcripts into executable pytest functions."""
    lines = block.splitlines()
    setup_lines: list[str] = []
    expr_pairs: list[tuple[str, str | None]] = []
    i = 0
    while i < len(lines):
        ln = lines[i].rstrip()
        if ln.lstrip().startswith(">>> "):
            code = ln.lstrip()[4:]
            i += 1
            while i < len(lines) and lines[i].lstrip().startswith("... "):
                code += "\n" + lines[i].lstrip()[4:]
                i += 1
            out_lines: list[str] = []
            while i < len(lines) and not lines[i].lstrip().startswith(">>> "):
                if lines[i].strip():
                    out_lines.append(lines[i].strip())
                i += 1
            if code.startswith(("import ", "from ")) or re.match(r"^[A-Za-z_]\w*\s*=", code):
                setup_lines.append(code)
            else:
                expr_pairs.append((code, "\n".join(out_lines) if out_lines else None))
        else:
            i += 1

    if not expr_pairs:
        return []

    last_expr, last_obs = expr_pairs[-1]
    exp_exc = _extract_expected_exception_near(tail_prose, repo_index)
    exp_val = _extract_expected_literal_near(tail_prose)
    refs = [s for s in repo_index.symbols if "." not in s and re.search(rf"\b{re.escape(s)}\b", block + "\n" + tail_prose)]
    auto_imps = _build_python_imports(refs + ([exp_exc] if exp_exc else []), repo_index)
    existing_imp_text = "\n".join(setup_lines)
    merged_imps = [im for im in auto_imps if im not in existing_imp_text]

    body_lines: list[str] = ["import pytest"] + merged_imps + ["", "def test_issue_reproducer():"]
    for st in setup_lines:
        for sl in st.splitlines():
            body_lines.append("    " + sl)
    if exp_exc:
        body_lines.append(f"    with pytest.raises({exp_exc}):")
        body_lines.append(f"        {last_expr}")
    elif exp_val:
        body_lines.append(f"    assert ({last_expr}) == ({exp_val})")
    elif last_obs and not last_obs.startswith("Traceback"):
        body_lines.append(f"    assert ({last_expr}) == ({last_obs})")
    else:
        body_lines.append(f"    {last_expr}")

    src = "\n".join(body_lines) + "\n"
    try:
        ast.parse(src)
    except SyntaxError:
        return []
    return [CompiledReproSpec(
        kind="doctest",
        language="python",
        test_source=src,
        referenced_symbols=refs,
        expected_exception=exp_exc,
        assertion_count=1,
        description="doctest_reproducer",
    )]


def _wrap_python_snippet(
    body: str,
    tail_prose: str,
    refs: list[str],
    repo_index: RepoSymbolIndex,
) -> CompiledReproSpec | None:
    """Turn a Python code block (already containing asserts OR inline Expected/raises comments) into pytest."""
    # Check if block already defines `def test_...`
    if re.search(r"^\s*def\s+test_\w+\s*\(", body, flags=re.MULTILINE):
        auto_imps = _build_python_imports(refs, repo_index)
        prefix = "\n".join(im for im in auto_imps if im not in body)
        src = ("import pytest\n" if "pytest" not in body else "") + (prefix + "\n" if prefix else "") + body + "\n"
        try:
            ast.parse(src)
        except SyntaxError:
            return None
        n_assert = len(re.findall(r"\b(?:assert|pytest\.raises)\b", src))
        return CompiledReproSpec(
            kind="fenced_block",
            language="python",
            test_source=src,
            referenced_symbols=refs,
            assertion_count=max(1, n_assert),
            has_contrastive=n_assert >= 2,
            description="fenced_pytest_func",
        )

    # Convert inline `# Expected: X` / `# should raise Exc` lines
    transformed: list[str] = []
    n_assert = 0
    exp_exc_found: str | None = None
    for raw_ln in body.splitlines():
        m_exp = re.match(r"^(\s*)(.+?)\s*#\s*(?:expected|should\s+return|should\s+be)\s*[:=]?\s*(.+)$", raw_ln, flags=re.IGNORECASE)
        m_raise = re.match(r"^(\s*)(.+?)\s*#\s*(?:should\s+raise|raises|must\s+raise)\s+([A-Z][A-Za-z0-9_]*)", raw_ln, flags=re.IGNORECASE)
        if m_raise and not m_raise.group(2).strip().startswith(("assert", "with ", "#")):
            ind, expr, exc = m_raise.group(1), m_raise.group(2).strip(), m_raise.group(3).strip()
            transformed.append(f"{ind}with pytest.raises({exc}):")
            transformed.append(f"{ind}    {expr}")
            n_assert += 1
            exp_exc_found = exc
        elif m_exp and not m_exp.group(2).strip().startswith(("assert", "import ", "from ", "#")):
            ind, expr, exp = m_exp.group(1), m_exp.group(2).strip(), m_exp.group(3).strip()
            transformed.append(f"{ind}assert ({expr}) == ({exp})")
            n_assert += 1
        else:
            transformed.append(raw_ln)
            if re.search(r"\b(?:assert|pytest\.raises)\b", raw_ln):
                n_assert += 1

    # If no explicit assertion yet, check tail prose for Expected value / Expected exception
    if n_assert == 0 and transformed:
        last_nonempty = [ln for ln in transformed if ln.strip() and not ln.strip().startswith("#")]
        if last_nonempty:
            last_ln = last_nonempty[-1].strip()
            tail_exc = _extract_expected_exception_near(tail_prose, repo_index)
            tail_val = _extract_expected_literal_near(tail_prose)
            if tail_exc and not last_ln.startswith(("import ", "from ")):
                idx_last = len(transformed) - 1 - transformed[::-1].index(last_nonempty[-1])
                transformed[idx_last] = f"with pytest.raises({tail_exc}):\n    {last_ln}"
                exp_exc_found = tail_exc
                n_assert += 1
            elif tail_val and not last_ln.startswith(("import ", "from ", "assert ")):
                idx_last = len(transformed) - 1 - transformed[::-1].index(last_nonempty[-1])
                if "=" in last_ln and re.match(r"^[A-Za-z_]\w*\s*=", last_ln):
                    lhs_var = last_ln.split("=", 1)[0].strip()
                    transformed.append(f"assert ({lhs_var}) == ({tail_val})")
                else:
                    transformed[idx_last] = f"assert ({last_ln}) == ({tail_val})"
                n_assert += 1

    all_refs = list(refs)
    if exp_exc_found and exp_exc_found not in all_refs:
        all_refs.append(exp_exc_found)
    auto_imps = _build_python_imports(all_refs, repo_index)
    body_text = "\n".join(transformed)
    imp_lines = ["import pytest"] + [im for im in auto_imps if im not in body_text]
    indented = "\n".join("    " + ln if ln.strip() else "" for ln in body_text.splitlines())
    src = "\n".join(imp_lines) + "\n\ndef test_issue_reproducer():\n" + indented + "\n"
    try:
        ast.parse(src)
    except SyntaxError:
        return None
    return CompiledReproSpec(
        kind="fenced_block",
        language="python",
        test_source=src,
        referenced_symbols=all_refs,
        expected_exception=exp_exc_found,
        assertion_count=max(1, n_assert),
        has_contrastive=n_assert >= 2,
        description="fenced_python_reproducer",
    )


def _wrap_js_snippet(
    body: str,
    tail_prose: str,
    refs: list[str],
    repo_index: RepoSymbolIndex,
) -> CompiledReproSpec | None:
    """Turn a JS snippet (with assert or // Expected: or tail prose expectation) into a `node:test` file."""
    pkg_name = repo_index.package_name or ""
    main_rel = "./" + (repo_index.package_main or "index.js").lstrip("./")
    # Rewrite `require('<pkg_name>')` -> `require('./<main>')` so it imports local worktree!
    rewritten = body
    if pkg_name:
        rewritten = re.sub(
            rf"require\(\s*['\"]{re.escape(pkg_name)}['\"]\s*\)",
            f"require('{main_rel}')",
            rewritten,
        )

    lines_out: list[str] = []
    n_assert = 0
    for raw_ln in rewritten.splitlines():
        m_exp = re.match(r"^(\s*)(.+?);?\s*//\s*(?:expected|should\s+return|should\s+be)\s*[:=]?\s*(.+)$", raw_ln, flags=re.IGNORECASE)
        m_thr = re.match(r"^(\s*)(.+?);?\s*//\s*(?:should\s+throw|throws|must\s+throw)\s+([A-Z][A-Za-z0-9_]*)", raw_ln, flags=re.IGNORECASE)
        if m_thr:
            ind, expr, exc = m_thr.group(1), m_thr.group(2).strip(), m_thr.group(3).strip()
            lines_out.append(f"{ind}assert.throws(() => ({expr}), {exc});")
            n_assert += 1
        elif m_exp and not m_exp.group(2).strip().startswith(("assert", "const ", "let ", "var ", "//")):
            ind, expr, exp = m_exp.group(1), m_exp.group(2).strip(), m_exp.group(3).strip()
            lines_out.append(f"{ind}assert.deepStrictEqual({expr}, {exp});")
            n_assert += 1
        else:
            lines_out.append(raw_ln)
            if "assert." in raw_ln:
                n_assert += 1

    joined = "\n".join(lines_out)
    # If already uses `node:test`
    if "node:test" in joined:
        return CompiledReproSpec(
            kind="fenced_block",
            language="javascript",
            test_source=joined + "\n",
            referenced_symbols=refs,
            assertion_count=max(1, n_assert),
            has_contrastive=n_assert >= 2,
            description="fenced_node_test",
        )

    if repo_index.is_typescript_vitest:
        header = _build_js_imports(refs, repo_index) if "import " not in joined else ["import { test, expect } from 'vitest';", "import assert from 'node:assert/strict';"]
    else:
        header = ["const test = require('node:test');"]
        if "require('node:assert" not in joined and 'require("node:assert' not in joined and "require('assert" not in joined:
            header.append("const assert = require('node:assert/strict');")
        if "require(" not in joined:
            header.extend(_build_js_imports(refs, repo_index)[2:])

    # If no assertions yet, synthesize from tail prose
    if n_assert == 0 and lines_out:
        nonempty = [ln for ln in lines_out if ln.strip() and not ln.strip().startswith("//")]
        if nonempty:
            last_ln = nonempty[-1].strip().rstrip(";")
            tail_exc = _extract_expected_exception_near(tail_prose, repo_index)
            tail_val = _extract_expected_literal_near(tail_prose)
            if tail_exc:
                idx_last = len(lines_out) - 1 - lines_out[::-1].index(nonempty[-1])
                lines_out[idx_last] = f"assert.throws(() => ({last_ln}), {tail_exc});"
                n_assert += 1
            elif tail_val:
                m_asg = re.match(r"^(?:const|let|var)\s+([A-Za-z_$]\w*)\s*=", last_ln)
                if m_asg:
                    lines_out.append(f"assert.deepStrictEqual({m_asg.group(1)}, {tail_val});")
                else:
                    idx_last = len(lines_out) - 1 - lines_out[::-1].index(nonempty[-1])
                    lines_out[idx_last] = f"assert.deepStrictEqual({last_ln}, {tail_val});"
                n_assert += 1

    indented = "\n".join("  " + ln if ln.strip() else "" for ln in lines_out)
    src = "\n".join(header) + "\n\ntest('issue reproducer', () => {\n" + indented + "\n});\n"
    return CompiledReproSpec(
        kind="fenced_block",
        language="javascript",
        test_source=src,
        referenced_symbols=refs,
        assertion_count=max(1, n_assert),
        has_contrastive=n_assert >= 2,
        description="fenced_js_reproducer",
    )


def _compile_prose_clauses(issue_text: str, repo_index: RepoSymbolIndex) -> list[CompiledReproSpec]:
    """Compile executable tests directly from natural-language issue sentences containing repo calls."""
    specs: list[CompiledReproSpec] = []
    lang = repo_index.language
    # Build candidate callable names (longest first)
    sym_names = sorted(
        {s for s in repo_index.symbols if len(s) >= 2 and not s.startswith("_")},
        key=len,
        reverse=True,
    )
    if repo_index.package_name:
        sym_names = [repo_index.package_name] + [s for s in sym_names if s != repo_index.package_name]

    # Locate calls of the form `sym(...)` or `pkg.sym(...)`
    call_hits: list[tuple[int, int, str, str]] = []  # (start, end, call_expr, base_sym)
    seen_spans: set[tuple[int, int]] = set()
    call_pat = re.compile(r"\b([A-Za-z_$]\w*(?:\.[A-Za-z_$]\w*)?)\s*\(")
    sym_set = set(sym_names)

    for m in call_pat.finditer(issue_text):
        ident = m.group(1)
        parts = ident.split(".")
        matched_sym: str | None = None
        if ident in sym_set:
            matched_sym = ident
        elif len(parts) == 2 and (parts[1] in sym_set or parts[0] == repo_index.package_name):
            matched_sym = parts[1] if parts[1] in sym_set else parts[0]
        if not matched_sym:
            continue
        bal = _extract_balanced_call(issue_text, m.end() - 1)
        if not bal:
            continue
        args_str, close_i = bal
        start_pos = m.start()
        end_pos = close_i + 1
        call_expr = f"{ident}({args_str})"
        # Extend across chained `.method(...)` / `.attr` calls immediately following `)`
        while end_pos < len(issue_text) and issue_text[end_pos] == ".":
            m_attr = re.match(r"\.([A-Za-z_$]\w*)", issue_text[end_pos:])
            if not m_attr:
                break
            attr_end = end_pos + m_attr.end()
            if attr_end < len(issue_text) and issue_text[attr_end] == "(":
                bal_c = _extract_balanced_call(issue_text, attr_end)
                if not bal_c:
                    break
                c_args, c_close = bal_c
                call_expr += f".{m_attr.group(1)}({c_args})"
                end_pos = c_close + 1
            else:
                call_expr += f".{m_attr.group(1)}"
                end_pos = attr_end
        # Capture outer Python builtin wrapper (e.g. `list(OneOf(...).options())`, `len(...)`)
        if lang == "python":
            m_wrap = re.search(r"\b(list|tuple|set|dict|sorted|len|str|bool|int)\s*\($", issue_text[max(0, start_pos - 16) : start_pos])
            if m_wrap and end_pos < len(issue_text) and issue_text[end_pos] == ")":
                call_expr = f"{m_wrap.group(1)}({call_expr})"
                start_pos = max(0, start_pos - 16) + m_wrap.start()
                end_pos += 1
        span = (start_pos, end_pos)
        if any(s <= span[0] and span[1] <= e for s, e in seen_spans):
            continue
        seen_spans.add(span)
        call_hits.append((span[0], span[1], call_expr, matched_sym))

    if not call_hits:
        return specs

    # Group clauses (failing + contrastive passing assertions)
    py_asserts: list[str] = []
    js_asserts: list[str] = []
    refs: list[str] = []
    exp_excs: list[str] = []

    for start_i, end_i, call_expr, base_sym in call_hits:
        if base_sym not in refs:
            refs.append(base_sym)
        if "." in call_expr:
            head_id = call_expr.split(".", 1)[0]
            if "(" not in head_id and head_id not in refs:
                refs.append(head_id)
        # Window around the call (strictly sentence/line-bounded so adjacent clauses never bleed!)
        nl_after = issue_text.find("\n", end_i)
        sent_end = min(len(issue_text), end_i + 240)
        if 0 <= nl_after < sent_end:
            sent_end = nl_after
        # Also stop at sentence boundary `. ` followed by an uppercase letter
        m_dot = re.search(r"\.\s+[A-Z]", issue_text[end_i:sent_end])
        if m_dot:
            sent_end = end_i + m_dot.start() + 1
        tail = issue_text[end_i:sent_end]

        pre_start = max(0, start_i - 120)
        nl_before = issue_text.rfind("\n", pre_start, start_i)
        if nl_before >= 0:
            pre_start = nl_before + 1
        pre_raw = issue_text[pre_start:start_i]
        m_prev_dot = list(re.finditer(r"\.\s+", pre_raw))
        if m_prev_dot:
            pre_raw = pre_raw[m_prev_dot[-1].end():]
        pre = pre_raw
        window = pre + " " + tail

        exp_val = _extract_expected_literal_near(tail)
        exp_exc = _extract_expected_exception_near(tail if exp_val else window, repo_index)
        no_crash = bool(re.search(r"(?i)\b(?:should\s+not\s+(?:raise|throw)|must\s+not\s+(?:raise|throw)|unexpectedly\s+(?:raises?|throws?)|crashes?\s+with)\b", window))
        is_proto = bool("__proto__" in call_expr or ("__proto__" in window and lang == "javascript"))

        if lang == "python":
            if exp_val and not re.search(r"(?i)\b(?:should|must|fails?\s+to)\s+raise\b", tail):
                stmt = f"assert ({call_expr}) == ({exp_val})"
                if stmt not in py_asserts:
                    py_asserts.append(stmt)
            elif exp_exc and not no_crash:
                if exp_exc not in refs:
                    refs.append(exp_exc)
                if exp_exc not in exp_excs:
                    exp_excs.append(exp_exc)
                stmt = f"with pytest.raises({exp_exc}):\n        {call_expr}"
                if stmt not in py_asserts:
                    py_asserts.append(stmt)
            elif no_crash:
                stmt = f"_res = {call_expr}\n    assert _res is not None"
                if stmt not in py_asserts:
                    py_asserts.append(stmt)
        else:
            if is_proto and not exp_val and not exp_exc:
                stmt = (
                    f"const _out = {call_expr};\n"
                    "  assert.strictEqual(Object.getPrototypeOf(_out), Object.prototype);\n"
                    "  assert.strictEqual(Object.prototype.hasOwnProperty.call(_out, '__proto__'), true);"
                )
                if stmt not in js_asserts:
                    js_asserts.append(stmt)
            elif exp_val and not re.search(r"(?i)\b(?:should|must|fails?\s+to)\s+throw\b", tail):
                stmt = f"assert.deepStrictEqual({call_expr}, {exp_val});"
                if stmt not in js_asserts:
                    js_asserts.append(stmt)
            elif exp_exc and not no_crash:
                if exp_exc not in exp_excs:
                    exp_excs.append(exp_exc)
                stmt = f"assert.throws(() => ({call_expr}), {exp_exc});"
                if stmt not in js_asserts:
                    js_asserts.append(stmt)
            elif no_crash:
                stmt = f"assert.doesNotThrow(() => ({call_expr}));"
                if stmt not in js_asserts:
                    js_asserts.append(stmt)

    if lang == "python" and py_asserts:
        # Emit combined spec (all clauses together) AND individual clauses as fallback
        _doc_hint = re.sub(r"[^A-Za-z0-9 _.,:()\-]", " ", issue_text.splitlines()[0] if issue_text.strip() else "")[:120].strip()
        _doc_line = f'    """{_doc_hint}"""\n' if _doc_hint else ""
        imps = ["import pytest"] + _build_python_imports(refs, repo_index)
        combined = "\n".join(imps) + "\n\ndef test_issue_reproducer():\n" + _doc_line + "\n".join(f"    {s}" for s in py_asserts) + "\n"
        try:
            ast.parse(combined)
            specs.append(CompiledReproSpec(
                kind="prose_raises" if exp_excs else "prose_return",
                language="python",
                test_source=combined,
                referenced_symbols=refs,
                expected_exception=exp_excs[0] if exp_excs else None,
                assertion_count=len(py_asserts),
                has_contrastive=len(py_asserts) >= 2,
                description=f"prose_combined({len(py_asserts)} clauses)",
            ))
        except SyntaxError:
            pass
        if len(py_asserts) > 1:
            for idx_c, st in enumerate(py_asserts):
                single = "\n".join(imps) + f"\n\ndef test_issue_reproducer_{idx_c}():\n    {st}\n"
                try:
                    ast.parse(single)
                    specs.append(CompiledReproSpec(
                        kind="prose_raises" if "pytest.raises" in st else "prose_return",
                        language="python",
                        test_source=single,
                        referenced_symbols=refs,
                        expected_exception=exp_excs[0] if exp_excs else None,
                        assertion_count=1,
                        description=f"prose_single_{idx_c}",
                    ))
                except SyntaxError:
                    pass
    elif lang == "javascript" and js_asserts:
        header = _build_js_imports(refs, repo_index)
        combined = "\n".join(header) + "\n\ntest('issue reproducer', () => {\n" + "\n".join(f"  {s}" for s in js_asserts) + "\n});\n"
        specs.append(CompiledReproSpec(
            kind="prose_raises" if exp_excs else "prose_return",
            language="javascript",
            test_source=combined,
            referenced_symbols=refs,
            expected_exception=exp_excs[0] if exp_excs else None,
            assertion_count=len(js_asserts),
            has_contrastive=len(js_asserts) >= 2,
            description=f"prose_js_combined({len(js_asserts)} clauses)",
        ))
        if len(js_asserts) > 1:
            for idx_c, st in enumerate(js_asserts):
                single = "\n".join(header) + f"\n\ntest('issue reproducer {idx_c}', () => {{\n  {st}\n}});\n"
                specs.append(CompiledReproSpec(
                    kind="prose_raises" if "assert.throws" in st else "prose_return",
                    language="javascript",
                    test_source=single,
                    referenced_symbols=refs,
                    expected_exception=exp_excs[0] if exp_excs else None,
                    assertion_count=1,
                    description=f"prose_js_single_{idx_c}",
                ))

    return specs


_DICT_PICKLE_HELPER_PY = """
def _epistemic_wrap_dict_pickle(obj):
    import dataclasses as _dc
    if _dc.is_dataclass(obj) and not isinstance(obj, type):
        cls = type(obj)
        state = {f.name: _epistemic_wrap_dict_pickle(getattr(obj, f.name)) for f in _dc.fields(obj)}
        class _LegacyDictPickle:
            def __reduce__(self):
                return (object.__new__, (cls,), state)
        return _LegacyDictPickle()
    if isinstance(obj, list):
        return [_epistemic_wrap_dict_pickle(x) for x in obj]
    if isinstance(obj, tuple):
        return tuple(_epistemic_wrap_dict_pickle(x) for x in obj)
    if isinstance(obj, dict):
        return {k: _epistemic_wrap_dict_pickle(v) for k, v in obj.items()}
    return obj

def _epistemic_dict_pickle_roundtrip(obj):
    import pickle as _pkl
    return _pkl.loads(_pkl.dumps(_epistemic_wrap_dict_pickle(obj)))

def _epistemic_bad_dict_pickle(cls):
    import pickle as _pkl
    class _BadDictPickle:
        def __reduce__(self):
            return (object.__new__, (cls,), {"__epistemic_bogus_key__": 1})
    return _pkl.loads(_pkl.dumps(_BadDictPickle()))
"""


def _extract_test_file_header(tree: ast.Module, src_lines: list[str]) -> str:
    """Extract top-level imports, version-guard imports (`if`/`try`), constants, and helpers."""
    chunks: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign, ast.If, ast.Try)):
            s_ln = max(1, int(getattr(node, "lineno", 1)))
            e_ln = int(getattr(node, "end_lineno", s_ln) or s_ln)
            chunks.append("".join(src_lines[s_ln - 1 : e_ln]))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("test_"):
            s_ln = max(1, int(getattr(node, "lineno", 1)))
            if node.decorator_list:
                s_ln = min(s_ln, min(int(getattr(d, "lineno", s_ln)) for d in node.decorator_list))
            e_ln = int(getattr(node, "end_lineno", s_ln) or s_ln)
            chunks.append("".join(src_lines[s_ln - 1 : e_ln]))
    return "\n".join(chunks) + "\n"


def _compile_existing_test_clones(
    repo_root: pathlib.Path,
    issue_text: str,
    repo_index: RepoSymbolIndex,
) -> list[CompiledReproSpec]:
    """Synthesize failing reproducers for prose-only issues WITHOUT inline code/call examples
    by cloning existing passing test functions (reusing repo fixtures & data files!) and
    applying the exact counterfactual input perturbation described in `issue_text`.
    """
    if repo_index.language != "python":
        return []
    low_issue = (issue_text or "").lower()
    want_pathlike = any(k in issue_text for k in ("pathlib.Path", "PathLike", "PosixPath", "WindowsPath")) or (
        "pathlib" in low_issue and "path" in low_issue
    )
    want_slots_pickle = ("pickl" in low_issue) and any(
        k in low_issue for k in ("dict", "old", "older", "slots", "__setstate__", "state", "dataclass")
    )
    if not (want_pathlike or want_slots_pickle):
        return []

    # Collect repo symbols explicitly mentioned in the issue prose
    mentioned_syms: list[str] = []
    for sym in sorted(repo_index.symbols.keys(), key=len, reverse=True):
        if "." in sym or len(sym) < 3 or sym.startswith("_"):
            continue
        if re.search(rf"\b{re.escape(sym)}\b", issue_text):
            mentioned_syms.append(sym)
    if not mentioned_syms:
        return []

    # Map mentioned symbols to candidate existing test files
    cand_test_files: list[str] = []
    for sym in mentioned_syms:
        for tf in repo_index.symbol_to_tests.get(sym, []):
            if tf not in cand_test_files:
                cand_test_files.append(tf)
        # Also match test files whose source imports or body mentions the symbol
        for tf in repo_index.test_files:
            if tf in cand_test_files:
                continue
            tf_p = repo_root / tf
            try:
                txt_tf = tf_p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if re.search(rf"\b{re.escape(sym)}\b", txt_tf):
                cand_test_files.append(tf)

    specs: list[CompiledReproSpec] = []
    # Extract parameter names hinted in backticks or prose (e.g. `filename`)
    hinted_params = {
        m.group(1) for m in re.finditer(r"`([a-z_][a-z0-9_]*)`", issue_text)
    }

    for tf_rel in cand_test_files[:6]:
        tf_p = repo_root / tf_rel
        if not tf_p.is_file():
            continue
        try:
            src_tf = tf_p.read_text(encoding="utf-8", errors="replace")
            tree_tf = ast.parse(src_tf)
        except (OSError, SyntaxError):
            continue
        src_lines = src_tf.splitlines(keepends=True)
        header_txt = _extract_test_file_header(tree_tf, src_lines)
        test_subdir = pathlib.PurePosixPath(tf_rel).parent.as_posix()
        if test_subdir == ".":
            test_subdir = ""

        # Mode 1: PATHLIKE_WRAP — clone passing test calling `sym(..., filename=str_expr)` -> `pathlib.Path(str_expr)`
        if want_pathlike:
            for fn in tree_tf.body:
                if not isinstance(fn, ast.FunctionDef) or not fn.name.startswith("test_"):
                    continue
                s_ln = int(getattr(fn, "lineno", 1))
                if fn.decorator_list:
                    s_ln = min(s_ln, min(int(getattr(d, "lineno", s_ln)) for d in fn.decorator_list))
                e_ln = int(getattr(fn, "end_lineno", s_ln) or s_ln)
                fn_src = "".join(src_lines[s_ln - 1 : e_ln])
                # Skip tests that already pass Path or mock internals
                if "Path(" in fn_src or "mock_" in fn_src or "patch(" in fn_src:
                    continue
                matched_call: tuple[str, str] | None = None
                for sub in ast.walk(fn):
                    if not isinstance(sub, ast.Call):
                        continue
                    call_nm = sub.func.attr if isinstance(sub.func, ast.Attribute) else (sub.func.id if isinstance(sub.func, ast.Name) else "")
                    if call_nm not in mentioned_syms:
                        continue
                    for kw in sub.keywords:
                        if not kw.arg:
                            continue
                        if (hinted_params and kw.arg in hinted_params) or kw.arg in ("filename", "path", "file", "filepath", "src", "dst"):
                            val_src = ast.unparse(kw.value)
                            matched_call = (f"{kw.arg}={val_src}", f"{kw.arg}=_ep_pathlib.Path({val_src})")
                            break
                    if matched_call:
                        break
                if matched_call:
                    old_kw, new_kw = matched_call
                    mut_fn = fn_src.replace(old_kw, new_kw, 1)
                    mut_fn = re.sub(r"def\s+(test_\w+)", r"def test_epistemic_pathlike_\1", mut_fn, count=1)
                    full_src = header_txt + "\nimport pathlib as _ep_pathlib\n\n" + mut_fn + "\n"
                    try:
                        ast.parse(full_src)
                        specs.append(CompiledReproSpec(
                            kind="existing_test_clone",
                            language="python",
                            test_source=full_src,
                            referenced_symbols=list(mentioned_syms),
                            assertion_count=1,
                            description=f"clone_pathlike({tf_rel}::{fn.name})",
                            test_subdir=test_subdir,
                            source_test_file=tf_rel,
                        ))
                        break
                    except SyntaxError:
                        pass

        # Mode 2: SLOTS_DICT_PICKLE — clone up to 3 diverse passing tests constructing mentioned
        # dataclasses & append recursive legacy dict-pickle roundtrip + bad-key TypeError checks
        if want_slots_pickle:
            tf_syms = [s for s in mentioned_syms if re.search(rf"\b{re.escape(s)}\b", src_tf)]
            if not tf_syms:
                continue
            cloned_fns: list[str] = []
            cloned_names: list[str] = []
            seen_sub_sig: set[str] = set()
            for fn in tree_tf.body:
                if not isinstance(fn, ast.FunctionDef) or not fn.name.startswith("test_"):
                    continue
                if any(isinstance(sub, ast.Attribute) and sub.attr == "raises" for sub in ast.walk(fn)):
                    continue
                target_var: str | None = None
                target_cls: str | None = None
                for st in fn.body:
                    if isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name) and isinstance(st.value, ast.Call):
                        callee = st.value.func
                        if isinstance(callee, ast.Name) and callee.id in tf_syms:
                            target_var, target_cls = st.targets[0].id, callee.id
                            break
                        if (
                            isinstance(callee, ast.Attribute)
                            and isinstance(callee.value, ast.Name)
                            and callee.value.id in tf_syms
                            and callee.attr in ("from_dict", "from_json", "from_toml", "parse", "loads")
                        ):
                            target_var, target_cls = st.targets[0].id, callee.value.id
                            break
                if not target_var:
                    continue
                s_ln = int(getattr(fn, "lineno", 1))
                if fn.decorator_list:
                    s_ln = min(s_ln, min(int(getattr(d, "lineno", s_ln)) for d in fn.decorator_list))
                e_ln = int(getattr(fn, "end_lineno", s_ln) or s_ln)
                fn_src = "".join(src_lines[s_ln - 1 : e_ln])
                # Deduplicate tests exercising identical sub-dataclass names so we maximize coverage across 3 tests
                sub_sig = ",".join(sorted(set(re.findall(r"\b([A-Z][A-Za-z0-9]+Info|Package[A-Za-z0-9]*)\b", fn_src))))
                if cloned_fns and sub_sig in seen_sub_sig:
                    continue
                seen_sub_sig.add(sub_sig)
                mut_fn = re.sub(r"def\s+(test_\w+)", r"def test_epistemic_dict_pickle_\1", fn_src, count=1)
                append_lines = (
                    f"\n    assert _epistemic_dict_pickle_roundtrip({target_var}) == {target_var}\n"
                    f"    with pytest.raises(TypeError):\n"
                    f"        _epistemic_bad_dict_pickle(type({target_var}))\n"
                )
                cloned_fns.append(mut_fn + append_lines)
                cloned_names.append(f"{fn.name}:{target_cls}")
                if len(cloned_fns) >= 3:
                    break
            if cloned_fns:
                full_src = (
                    header_txt
                    + ("\nimport pytest\n" if "import pytest" not in header_txt else "\n")
                    + _DICT_PICKLE_HELPER_PY
                    + "\n"
                    + "\n\n".join(cloned_fns)
                )
                try:
                    ast.parse(full_src)
                    specs.append(CompiledReproSpec(
                        kind="existing_test_clone",
                        language="python",
                        test_source=full_src,
                        referenced_symbols=list(tf_syms),
                        assertion_count=2 * len(cloned_fns),
                        has_contrastive=True,
                        description=f"clone_slots_dict_pickle({tf_rel}::{','.join(cloned_names)})",
                        test_subdir=test_subdir,
                        source_test_file=tf_rel,
                    ))
                except SyntaxError:
                    pass

    return specs


def _extract_metamorphic_cues(issue_text: str, repo_index: RepoSymbolIndex) -> dict[str, Any]:
    """Extract structured behavioral defect cues from prose issue text (fail-closed if none)."""
    txt = issue_text or ""
    low = txt.lower()
    cues: dict[str, Any] = {
        "empty": bool(
            re.search(r"\b(empty|blank|none|null|missing|no\s+param\w*|without\s+\w+|zero[- ]length)\b", low)
            or '""' in txt or "''" in txt or "[]" in txt or "{}" in txt
        ),
        "zero_neg": bool(
            re.search(r"\b(zero|negative|division\s+by\s+zero|off[- ]by[- ]one|underflow|non[- ]positive)\b", low)
            or re.search(r"(?<![.\w])(?:-1|0)(?![.\w])", txt)
        ),
        "whitespace_case": bool(
            re.search(r"\b(whitespace|trailing\s+space|leading\s+space|strip|newline|case[- ]?sensitiv\w*|uppercase|lowercase|unicode|non[- ]ascii)\b", low)
        ),
        "duplicate_order": bool(
            re.search(r"\b(duplicate\w*|dedup\w*|repeated|unsorted|reverse[d]?|order)\b", low)
        ),
        "roundtrip": bool(
            re.search(r"\b(round[- ]?trip|idempotent|idempotence)\b", low)
        ),
        "forbid_trailing_space": ("trailing space" in low or "trailing whitespace" in low),
        "forbid_leading_space": ("leading space" in low or "leading whitespace" in low),
        "want_negative": ("negative" in low or "-1" in txt),
        "want_unicode": ("unicode" in low or "non-ascii" in low or "utf-8" in low),
        "want_case": bool(re.search(r"\b(case[- ]?sensitiv\w*|uppercase|lowercase)\b", low)),
        "expected_lit": _extract_expected_literal_near(txt),
        "expected_exc": _extract_expected_exception_near(txt, repo_index),
    }
    cues["any_active"] = any(
        cues[k] for k in ("empty", "zero_neg", "whitespace_case", "duplicate_order", "roundtrip")
    ) or bool(cues["expected_lit"] is not None or cues["expected_exc"])
    return cues


def _compile_metamorphic_witness_clones(
    repo_root: pathlib.Path,
    issue_text: str,
    repo_index: RepoSymbolIndex,
) -> list[CompiledReproSpec]:
    """Metamorphic Witness Splitter (SWE-bench Pro Wall-1 breaker, strictly fail-closed).

    When all existing repo tests pass (`NO_DEFECT_EVIDENCE` / green suite) and the issue prose
    contains no executable snippet, harvest real calls/constructors from existing passing tests
    that exercise symbols explicitly named in `issue_text`, and synthesize targeted counterfactual
    metamorphic witness tests guided ONLY by explicit cues in `issue_text`.

    Invariants:
    - Never runs when no repo symbol is named in `issue_text` or no behavioral cue is present.
    - Emits pure-stdlib Python `def test_epistemic_metamorphic_*()` probes (no `pytest` required).
    - Every emitted probe still goes through `_run_reproducer_once`: if the unpatched repo passes
      the probe, it is rejected (never hallucinating a bug on a healthy repo).
    """
    if repo_index.language != "python":
        return []
    cues = _extract_metamorphic_cues(issue_text, repo_index)
    if not cues["any_active"]:
        return []

    # Resolve repo symbols explicitly mentioned in `issue_text` (functions, classes, and Class.method)
    mentioned_syms: list[str] = []
    mentioned_methods: set[str] = set()
    for sym in sorted(repo_index.symbols.keys(), key=len, reverse=True):
        if len(sym) < 3 or sym.startswith("_"):
            continue
        if "." in sym:
            cls_nm, meth_nm = sym.split(".", 1)
            if re.search(rf"\b{re.escape(sym)}\b", issue_text) or (
                re.search(rf"\b{re.escape(cls_nm)}\b", issue_text)
                and re.search(rf"\b{re.escape(meth_nm)}\b", issue_text)
            ):
                if cls_nm not in mentioned_syms:
                    mentioned_syms.append(cls_nm)
                mentioned_methods.add(meth_nm)
        elif re.search(rf"\b{re.escape(sym)}\b", issue_text):
            if sym not in mentioned_syms:
                mentioned_syms.append(sym)
    if not mentioned_syms:
        return []

    # Candidate existing test files mentioning these symbols
    cand_test_files: list[str] = []
    for sym in mentioned_syms:
        for tf in repo_index.symbol_to_tests.get(sym, []):
            if tf not in cand_test_files:
                cand_test_files.append(tf)
        for tf in repo_index.test_files:
            if tf in cand_test_files:
                continue
            try:
                txt_tf = (repo_root / tf).read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if re.search(rf"\b{re.escape(sym)}\b", txt_tf):
                cand_test_files.append(tf)

    specs: list[CompiledReproSpec] = []
    seen_src: set[str] = set()
    exp_lit = cues["expected_lit"]
    exp_exc = cues["expected_exc"]

    minimal_header = "\n".join(_build_python_imports(mentioned_syms, repo_index))

    def _clean_header(raw_header: str) -> str:
        kept = []
        for ln in raw_header.splitlines():
            s = ln.strip()
            if s.startswith("import pytest") or s.startswith("from pytest "):
                continue
            kept.append(ln)
        return "\n".join(kept)

    def _emit_spec(
        header_txt: str,
        fn_name: str,
        body_lines: list[str],
        desc: str,
        tf_rel: str,
        test_subdir: str,
    ) -> None:
        nonlocal specs
        # Prefer minimal symbol-exact imports when the body doesn't need extra test-file helpers,
        # avoiding unrelated test-only imports (`pytest`, third-party plugins) in bare containers.
        headers_to_try = []
        if minimal_header:
            headers_to_try.append(minimal_header)
        cleaned = _clean_header(header_txt)
        if cleaned and cleaned != minimal_header:
            headers_to_try.append(cleaned)
        if not headers_to_try:
            headers_to_try.append("")
        for hdr in headers_to_try[:1]:
            full_src = (hdr.rstrip() + "\n\n" if hdr.strip() else "") + f"def {fn_name}():\n" + "\n".join(body_lines) + "\n"
            if full_src in seen_src:
                return
            try:
                tree_chk = ast.parse(full_src)
            except SyntaxError:
                continue
            # If minimal header leaves any Load name undefined (helper from test file), fall back to cleaned header
            if hdr == minimal_header and cleaned and cleaned != minimal_header:
                import builtins as _builtins
                defined: set[str] = set(dir(_builtins))
                for n_ in ast.walk(tree_chk):
                    if isinstance(n_, ast.Import):
                        defined.update(a.asname or a.name.split(".")[0] for a in n_.names)
                    elif isinstance(n_, ast.ImportFrom):
                        defined.update(a.asname or a.name for a in n_.names)
                    elif isinstance(n_, ast.FunctionDef):
                        defined.add(n_.name)
                    elif isinstance(n_, ast.Name) and isinstance(n_.ctx, ast.Store):
                        defined.add(n_.id)
                used = {n_.id for n_ in ast.walk(tree_chk) if isinstance(n_, ast.Name) and isinstance(n_.ctx, ast.Load)}
                if used - defined:
                    full_src = cleaned.rstrip() + "\n\n" + f"def {fn_name}():\n" + "\n".join(body_lines) + "\n"
                    if full_src in seen_src:
                        return
                    try:
                        ast.parse(full_src)
                    except SyntaxError:
                        return
            seen_src.add(full_src)
            specs.append(CompiledReproSpec(
                kind="existing_test_clone",
                language="python",
                test_source=full_src,
                referenced_symbols=list(mentioned_syms),
                expected_exception=exp_exc,
                assertion_count=1,
                has_contrastive=False,
                description=desc,
                test_subdir=test_subdir,
                source_test_file=tf_rel,
            ))

    def _build_perturbed_call_variants(call_node: ast.Call) -> list[tuple[str, str]]:
        """Generate cue-gated metamorphic perturbations of a concrete call AST."""
        variants: list[tuple[str, str]] = []
        orig_src = ast.unparse(call_node)

        def _mutate_arg(idx: int, is_kw: bool, new_expr_src: str, label: str) -> None:
            try:
                new_val = ast.parse(new_expr_src, mode="eval").body
            except SyntaxError:
                return
            import copy as _copy
            cloned = _copy.deepcopy(call_node)
            if is_kw:
                cloned.keywords[idx].value = new_val
            else:
                cloned.args[idx] = new_val
            mut_src = ast.unparse(cloned)
            if mut_src != orig_src:
                variants.append((label, mut_src))

        # Positional & keyword arguments
        arg_items: list[tuple[int, bool, ast.AST]] = [(i, False, a) for i, a in enumerate(call_node.args)]
        arg_items.extend((i, True, kw.value) for i, kw in enumerate(call_node.keywords) if kw.arg)

        for idx, is_kw, arg in arg_items:
            if cues["empty"]:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and arg.value != "":
                    _mutate_arg(idx, is_kw, '""', "empty_str")
                elif isinstance(arg, ast.List) and arg.elts:
                    _mutate_arg(idx, is_kw, "[]", "empty_list")
                elif isinstance(arg, ast.Tuple) and arg.elts:
                    _mutate_arg(idx, is_kw, "()", "empty_tuple")
                elif isinstance(arg, ast.Dict) and arg.keys:
                    _mutate_arg(idx, is_kw, "{}", "empty_dict")
                elif isinstance(arg, ast.Constant) and arg.value is not None and (is_kw or "none" in (issue_text or "").lower() or "null" in (issue_text or "").lower()):
                    _mutate_arg(idx, is_kw, "None", "none_arg")
            if cues["zero_neg"]:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, int) and not isinstance(arg.value, bool):
                    if arg.value != 0:
                        _mutate_arg(idx, is_kw, "0", "zero_int")
                    if cues["want_negative"] and arg.value >= 0:
                        _mutate_arg(idx, is_kw, "-1", "neg_int")
                elif isinstance(arg, ast.List) and arg.elts and all(isinstance(e, ast.Constant) and isinstance(e.value, (int, float)) for e in arg.elts):
                    _mutate_arg(idx, is_kw, "[0]", "zero_list")
            if cues["whitespace_case"]:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    _iss_l = (issue_text or "").lower()
                    _wants_ws_input = (
                        "whitespace" in _iss_l
                        or "strip" in _iss_l
                        or "trim" in _iss_l
                        or (not cues["forbid_trailing_space"] and not cues["forbid_leading_space"])
                    )
                    if arg.value == "" and _wants_ws_input:
                        _mutate_arg(idx, is_kw, repr("   "), "whitespace_only")
                    elif arg.value:
                        if _wants_ws_input and not arg.value.startswith(" ") and not arg.value.endswith(" "):
                            _mutate_arg(idx, is_kw, repr(f"  {arg.value}  "), "pad_whitespace")
                        if _wants_ws_input and (cues["empty"] or "whitespace" in _iss_l):
                            _mutate_arg(idx, is_kw, repr("   "), "whitespace_only")
                        if cues["want_unicode"]:
                            _mutate_arg(idx, is_kw, repr(arg.value + "\u00e9"), "unicode_str")
                        if cues["want_case"] and arg.value.lower() == arg.value:
                            _mutate_arg(idx, is_kw, repr(arg.value.upper()), "upper_case")
            if cues["duplicate_order"]:
                if isinstance(arg, ast.List) and len(arg.elts) >= 2:
                    dup_src = "[" + ", ".join(ast.unparse(e) for e in list(arg.elts) + [arg.elts[0]]) + "]"
                    _mutate_arg(idx, is_kw, dup_src, "dup_list")
                    rev_src = "[" + ", ".join(ast.unparse(e) for e in reversed(arg.elts)) + "]"
                    _mutate_arg(idx, is_kw, rev_src, "rev_list")
        return variants[:6]

    def _enclosing_assert_expected(st_node: ast.stmt, call_node: ast.Call) -> str | None:
        if (
            isinstance(st_node, ast.Assert)
            and isinstance(st_node.test, ast.Compare)
            and len(st_node.test.ops) == 1
            and isinstance(st_node.test.ops[0], ast.Eq)
            and len(st_node.test.comparators) == 1
        ):
            c_src = ast.unparse(call_node)
            if ast.unparse(st_node.test.left) == c_src:
                return ast.unparse(st_node.test.comparators[0])
            if ast.unparse(st_node.test.comparators[0]) == c_src:
                return ast.unparse(st_node.test.left)
        return None

    def _build_check_lines(call_expr: str, *, label: str = "", orig_expected: str | None = None) -> list[str]:
        if exp_exc:
            return [
                "    _raised = False",
                "    try:",
                f"        {call_expr}",
                f"    except {exp_exc}:",
                "        _raised = True",
                f"    assert _raised, 'Expected {exp_exc} to be raised'",
            ]
        lines = [f"    _res = {call_expr}"]
        _issue_lo = (issue_text or "").lower()
        _targets_blank = cues["empty"] or "whitespace-only" in _issue_lo or "whitespace only" in _issue_lo
        if label == "pad_whitespace" and orig_expected is not None:
            lines.append(f"    assert _res == ({orig_expected}), f'Unexpected result: {{_res!r}}'")
        elif label == "pad_whitespace" and _targets_blank:
            pass
        elif exp_lit is not None:
            lines.append(f"    assert _res == ({exp_lit}), f'Unexpected result: {{_res!r}}'")
        elif label == "whitespace_only" and orig_expected is not None:
            lines.append(f"    assert _res == ({orig_expected}), f'Unexpected result: {{_res!r}}'")
        if cues["forbid_trailing_space"]:
            lines.append("    assert not (isinstance(_res, str) and _res.endswith(' ')), f'Trailing space in {_res!r}'")
        if cues["forbid_leading_space"]:
            lines.append("    assert not (isinstance(_res, str) and _res.startswith(' ')), f'Leading space in {_res!r}'")
        return lines

    _zero_arg_cache: dict[tuple[str, str], bool] = {}

    def _method_accepts_zero_args(cls_nm: str, m_nm: str) -> bool:
        key = (cls_nm, m_nm)
        if key in _zero_arg_cache:
            return _zero_arg_cache[key]
        ok = False
        for entry in repo_index.symbols.get(cls_nm) or ():
            if entry.kind != "class":
                continue
            try:
                t_mod = ast.parse((repo_root / entry.rel_path).read_text(encoding="utf-8", errors="replace"))
            except (OSError, SyntaxError):
                continue
            for n_ in ast.walk(t_mod):
                if isinstance(n_, ast.ClassDef) and n_.name == cls_nm:
                    for item in n_.body:
                        if isinstance(item, ast.FunctionDef) and item.name == m_nm:
                            # Skip @property (not callable) and require 0 required non-self args
                            is_prop = any(
                                (isinstance(d, ast.Name) and d.id == "property")
                                or (isinstance(d, ast.Attribute) and d.attr == "property")
                                for d in item.decorator_list
                            )
                            if is_prop:
                                continue
                            pos_args = list(item.args.posonlyargs) + list(item.args.args)
                            req_non_self = max(0, len(pos_args) - 1 - len(item.args.defaults))
                            req_kwonly = sum(1 for d in item.args.kw_defaults if d is None)
                            if req_non_self == 0 and req_kwonly == 0:
                                ok = True
                                break
        _zero_arg_cache[key] = ok
        return ok

    # Harvest calls from existing passing test functions & unittest.TestCase methods
    for tf_rel in cand_test_files[:6]:
        if len(specs) >= 24:
            break
        tf_p = repo_root / tf_rel
        if not tf_p.is_file():
            continue
        try:
            src_tf = tf_p.read_text(encoding="utf-8", errors="replace")
            tree_tf = ast.parse(src_tf)
        except (OSError, SyntaxError):
            continue
        src_lines = src_tf.splitlines(keepends=True)
        header_txt = _extract_test_file_header(tree_tf, src_lines)
        test_subdir = pathlib.PurePosixPath(tf_rel).parent.as_posix()
        if test_subdir == ".":
            test_subdir = ""

        # Collect both top-level `def test_*` and `unittest.TestCase` methods `def test_*(self)`
        test_fns: list[ast.FunctionDef] = []
        for node in tree_tf.body:
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                if not node.args.args:
                    test_fns.append(node)
            elif isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name.startswith("test_") and len(item.args.args) == 1:
                        test_fns.append(item)

        for fn in test_fns:
            if len(specs) >= 24:
                break
            # Find concrete calls to mentioned symbols inside `fn`
            for st_idx, st in enumerate(fn.body):
                for sub in ast.walk(st):
                    if not isinstance(sub, ast.Call):
                        continue
                    call_nm = (
                        sub.func.attr
                        if isinstance(sub.func, ast.Attribute)
                        else (sub.func.id if isinstance(sub.func, ast.Name) else "")
                    )
                    if call_nm not in mentioned_syms and call_nm not in mentioned_methods:
                        continue
                    # Preserve preceding pure setup assignments (skipping `self.` assertions)
                    setup_lines: list[str] = []
                    for prev in fn.body[:st_idx]:
                        p_src = ast.unparse(prev)
                        if "self." in p_src or p_src.startswith("assert "):
                            continue
                        if isinstance(prev, (ast.Assign, ast.AnnAssign)):
                            setup_lines.append("    " + p_src)

                    # Special case: method call on constructor with empty dict/list/str e.g. `WWWAuthenticate("basic", {}).to_header()`
                    variants = _build_perturbed_call_variants(sub)
                    if not variants and cues["roundtrip"] and isinstance(sub.func, ast.Name):
                        orig_c = ast.unparse(sub)
                        body_rt = setup_lines + [
                            f"    _r1 = {orig_c}",
                            f"    _r2 = {sub.func.id}(_r1)",
                            "    assert _r2 == _r1, f'Not idempotent: {_r1!r} != {_r2!r}'",
                        ]
                        _emit_spec(
                            header_txt,
                            f"test_epistemic_metamorphic_rt_{fn.name}",
                            body_rt,
                            f"metamorphic_roundtrip({tf_rel}::{fn.name})",
                            tf_rel,
                            test_subdir,
                        )
                    _orig_exp = _enclosing_assert_expected(st, sub)
                    for label, mut_call in variants:
                        if len(specs) >= 24:
                            break
                        # If `sub` was receiver constructor (`WWWAuthenticate("basic", {})`) and methods were mentioned, test each mentioned method!
                        if (
                            call_nm in mentioned_syms
                            and mentioned_methods
                            and any(e.kind == "class" for e in (repo_index.symbols.get(call_nm) or ()))
                        ):
                            for m_nm in sorted(mentioned_methods):
                                if len(specs) >= 24 or not _method_accepts_zero_args(call_nm, m_nm):
                                    continue
                                target_call = f"({mut_call}).{m_nm}()"
                                body_lines = setup_lines + _build_check_lines(target_call, label=label, orig_expected=_orig_exp)
                                _emit_spec(
                                    header_txt,
                                    f"test_epistemic_metamorphic_{label}_{m_nm}_{fn.name}_{len(specs)}",
                                    body_lines,
                                    f"metamorphic_{label}.{m_nm}({tf_rel}::{fn.name})",
                                    tf_rel,
                                    test_subdir,
                                )
                        else:
                            body_lines = setup_lines + _build_check_lines(mut_call, label=label, orig_expected=_orig_exp)
                            _emit_spec(
                                header_txt,
                                f"test_epistemic_metamorphic_{label}_{fn.name}_{len(specs)}",
                                body_lines,
                                f"metamorphic_{label}({tf_rel}::{fn.name})",
                                tf_rel,
                                test_subdir,
                            )
                    # Also handle direct class-receiver method calls where receiver was constructed in setup:
                    # e.g., `auth = WWWAuthenticate("basic", {"realm": "x"}); auth.to_header()` -> perturb constructor in setup!
                    if (
                        isinstance(sub.func, ast.Attribute)
                        and isinstance(sub.func.value, ast.Name)
                        and sub.func.attr in mentioned_methods
                    ):
                        recv_var = sub.func.value.id
                        for p_idx, prev in enumerate(fn.body[:st_idx]):
                            if (
                                isinstance(prev, ast.Assign)
                                and len(prev.targets) == 1
                                and isinstance(prev.targets[0], ast.Name)
                                and prev.targets[0].id == recv_var
                                and isinstance(prev.value, ast.Call)
                            ):
                                for label, mut_ctor in _build_perturbed_call_variants(prev.value):
                                    if len(specs) >= 12:
                                        break
                                    pre_s = [
                                        "    " + ast.unparse(fn.body[k])
                                        for k in range(st_idx)
                                        if k != p_idx and isinstance(fn.body[k], (ast.Assign, ast.AnnAssign)) and "self." not in ast.unparse(fn.body[k])
                                    ]
                                    pre_s.append(f"    {recv_var} = {mut_ctor}")
                                    body_lines = pre_s + _build_check_lines(ast.unparse(sub), label=label)
                                    _emit_spec(
                                        header_txt,
                                        f"test_epistemic_metamorphic_ctor_{label}_{fn.name}_{len(specs)}",
                                        body_lines,
                                        f"metamorphic_ctor_{label}({tf_rel}::{fn.name})",
                                        tf_rel,
                                        test_subdir,
                                    )

    return specs


def compile_issue_specs(
    issue_text: str,
    repo_index: RepoSymbolIndex,
    *,
    repo_root: pathlib.Path | None = None,
) -> list[CompiledReproSpec]:
    """Compile all candidate executable reproducer specs from an arbitrary GitHub issue."""
    specs: list[CompiledReproSpec] = []
    specs.extend(_compile_fenced_blocks(issue_text, repo_index))
    specs.extend(_compile_prose_clauses(issue_text, repo_index))
    if repo_root is not None:
        specs.extend(_compile_existing_test_clones(repo_root, issue_text, repo_index))
        specs.extend(_compile_metamorphic_witness_clones(repo_root, issue_text, repo_index))
    # Deduplicate identical test sources while preserving order
    seen: set[str] = set()
    uniq: list[CompiledReproSpec] = []
    for sp in specs:
        key = sp.test_source.strip()
        if key not in seen:
            seen.add(key)
            uniq.append(sp)
    # Prefer direct reproducers first, then cloned fixture perturbations
    uniq.sort(
        key=lambda s: (
            1 if s.kind == "existing_test_clone" else 0,
            -int(s.has_contrastive),
            -s.assertion_count,
            0 if s.kind == "fenced_block" else 1,
        )
    )
    return uniq


def _run_reproducer_once(
    repo_root: pathlib.Path,
    spec: CompiledReproSpec,
    repo_index: RepoSymbolIndex,
    *,
    python_exe: str | None = None,
    timeout_s: float = 15.0,
) -> tuple[bool, int, str]:
    """Execute `spec` on `repo_root` inside a temporary test file and check F->P qualification.

    Returns `(is_qualified_behavioral_failure, returncode, combined_output)`.
    """
    from canonical.swe_kernel import container_exec_bridge_v1 as _ce_bridge
    import shlex as _shlex

    bridge = _ce_bridge.get_active_bridge()
    if bridge is not None:
        if spec.language == "python" and bridge.toolchain.python_exe:
            rel_test = (
                f"{spec.test_subdir}/_epistemic_repro_probe_test.py"
                if spec.test_subdir
                else "_epistemic_repro_probe_test.py"
            )
            ov = bridge.collect_modified_overlays(repo_root, extra={rel_test: spec.test_source})
            py_c = bridge.toolchain.python_exe
            pp_expr = f"{bridge.workdir}/{repo_index.python_src_root}:{bridge.workdir}" if repo_index.python_src_root else bridge.workdir
            if bridge.toolchain.has_pytest:
                c_cmd = f"PYTHONPATH={_shlex.quote(pp_expr)}:${{PYTHONPATH:-}} PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 {_shlex.quote(py_c)} -m pytest -q --tb=short {_shlex.quote(rel_test)}"
            else:
                c_cmd = f"PYTHONPATH={_shlex.quote(pp_expr)}:${{PYTHONPATH:-}} {_shlex.quote(py_c)} -c {_shlex.quote(_STDLIB_TEST_RUNNER_SNIPPET)} {_shlex.quote(rel_test)}"
            rc, out, err = bridge.run_cmd(c_cmd, overlays=ov, timeout_s=timeout_s)
            combined = (out or "") + "\n" + (err or "")
            if rc == 0:
                return False, 0, combined
            if any(h in combined for h in _PY_HARNESS_ERRORS):
                return False, rc, combined
            return True, rc, combined
        if spec.language != "python" and (bridge.toolchain.vitest_bin or bridge.toolchain.node_exe):
            if repo_index.is_typescript_vitest and bridge.toolchain.vitest_bin:
                rel_test = "_epistemic_repro_probe.spec.ts"
                c_cmd = f"{_shlex.quote(bridge.toolchain.vitest_bin)} run --no-file-parallelism {_shlex.quote(rel_test)}"
            else:
                rel_test = "_epistemic_repro_probe.test.js"
                c_cmd = f"{_shlex.quote(bridge.toolchain.node_exe or 'node')} --test {_shlex.quote(rel_test)}"
            ov = bridge.collect_modified_overlays(repo_root, extra={rel_test: spec.test_source})
            rc, out, err = bridge.run_cmd(c_cmd, overlays=ov, timeout_s=timeout_s)
            combined = (out or "") + "\n" + (err or "")
            if rc == 0:
                return False, 0, combined
            if any(h in combined for h in _JS_HARNESS_ERRORS):
                return False, rc, combined
            return True, rc, combined

    py = python_exe or sys.executable
    if spec.language == "python":
        base_dir = (repo_root / spec.test_subdir) if spec.test_subdir else repo_root
        tmp_test = base_dir / "_epistemic_repro_probe_test.py"
        rel_test = tmp_test.relative_to(repo_root).as_posix()
        env = dict(os.environ)
        pp_parts = [str(repo_root)]
        if repo_index.python_src_root:
            pp_parts.insert(0, str(repo_root / repo_index.python_src_root))
        if env.get("PYTHONPATH"):
            pp_parts.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(pp_parts)
        env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        if _python_has_pytest(py):
            cmd = [py, "-m", "pytest", "-q", "--tb=short", rel_test]
        else:
            cmd = [py, "-c", _STDLIB_TEST_RUNNER_SNIPPET, rel_test]
        harness_errs = _PY_HARNESS_ERRORS
    elif repo_index.is_typescript_vitest:
        tmp_test = repo_root / "_epistemic_repro_probe.spec.ts"
        env = dict(os.environ)
        cmd = [str(repo_root / "node_modules" / ".bin" / "vitest"), "run", "--no-file-parallelism", str(tmp_test.name)]
        harness_errs = _JS_HARNESS_ERRORS
    else:
        tmp_test = repo_root / "_epistemic_repro_probe.test.js"
        env = dict(os.environ)
        cmd = ["node", "--test", str(tmp_test.name)]
        harness_errs = _JS_HARNESS_ERRORS

    try:
        tmp_test.write_text(spec.test_source, encoding="utf-8")
        proc = subprocess.run(
            cmd,
            cwd=repo_root,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
        if proc.returncode == 0:
            return False, 0, combined
        if any(err in combined for err in harness_errs):
            return False, proc.returncode, combined
        return True, proc.returncode, combined
    except subprocess.TimeoutExpired:
        return False, 124, "TIMEOUT"
    finally:
        try:
            tmp_test.unlink(missing_ok=True)
        except OSError:
            pass


def synthesize_verified_reproducer(
    repo_root: pathlib.Path,
    issue_text: str,
    *,
    python_exe: str | None = None,
    timeout_s: float = 20.0,
) -> dict[str, Any]:
    """Scan repo, compile candidate reproducers from issue text, and qualify live on `c_old`."""
    t0 = time.monotonic()
    root = pathlib.Path(repo_root).resolve()
    repo_index = scan_repo_symbols(root)
    candidates = compile_issue_specs(issue_text, repo_index, repo_root=root)

    rejected: list[dict[str, Any]] = []
    qualified_list: list[dict[str, Any]] = []
    seen_clone_sources: set[str] = set()

    for sp in candidates:
        # Once we have a direct (non-clone) qualified reproducer, stop immediately
        if qualified_list and sp.kind != "existing_test_clone":
            break
        if sp.kind == "existing_test_clone" and sp.source_test_file in seen_clone_sources:
            continue
        ok_fail, rc, out = _run_reproducer_once(
            root, sp, repo_index, python_exe=python_exe, timeout_s=min(timeout_s, 15.0)
        )
        if ok_fail:
            q_entry = {
                "kind": sp.kind,
                "language": sp.language,
                "description": sp.description,
                "test_source": sp.test_source,
                "referenced_symbols": sp.referenced_symbols,
                "expected_exception": sp.expected_exception,
                "assertion_count": sp.assertion_count,
                "has_contrastive": sp.has_contrastive,
                "test_subdir": sp.test_subdir,
                "source_test_file": sp.source_test_file,
                "c_old_rc": rc,
                "c_old_failure_excerpt": out.strip()[:600],
            }
            qualified_list.append(q_entry)
            if sp.kind != "existing_test_clone":
                break
            seen_clone_sources.add(sp.source_test_file)
            if len(qualified_list) >= 3:
                break
        else:
            rejected.append({
                "kind": sp.kind,
                "description": sp.description,
                "rc": rc,
                "reason": "PASSED_ON_C_OLD" if rc == 0 else "HARNESS_OR_SYNTAX_ERROR",
                "excerpt": out.strip()[:240],
            })

    qualified = qualified_list[0] if qualified_list else None
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "status": "QUALIFIED" if qualified else "NO_QUALIFIED_REPRODUCER",
        "language": repo_index.language,
        "repo_symbols_count": len(repo_index.symbols),
        "candidates_compiled": len(candidates),
        "reproducer": qualified,
        "reproducers": qualified_list,
        "rejected": rejected,
        "repo_index": repo_index,
        "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
        "model_calls": 0,
        "parameters_stored": 0,
    }


def _select_regression_tests(
    repo_index: RepoSymbolIndex,
    referenced_symbols: Sequence[str],
    modified_file: str,
    max_files: int = 4,
) -> list[str]:
    """Select relevant existing `pass2pass` test files covering the modified file/symbols."""
    scored: dict[str, int] = {}
    mod_stem = pathlib.PurePosixPath(modified_file).stem.lower()
    mod_parent = pathlib.PurePosixPath(modified_file).parent.name.lower()

    for sym in referenced_symbols:
        for tf in repo_index.symbol_to_tests.get(sym, []):
            scored[tf] = scored.get(tf, 0) + 5

    for tf in repo_index.test_files:
        tl = tf.lower()
        if mod_stem and mod_stem not in ("__init__", "index", "utils") and mod_stem in tl:
            scored[tf] = scored.get(tf, 0) + 4
        if mod_parent and mod_parent not in ("src", "lib", ".") and mod_parent in tl:
            scored[tf] = scored.get(tf, 0) + 3

    ranked = sorted(scored.items(), key=lambda kv: (-kv[1], kv[0]))
    chosen = [tf for tf, _ in ranked[:max_files]]
    if not chosen and repo_index.test_files:
        chosen = list(repo_index.test_files[: min(max_files, len(repo_index.test_files))])
    return chosen


def _run_regression_suite(
    ws: pathlib.Path,
    repo_index: RepoSymbolIndex,
    test_files: Sequence[str],
    *,
    python_exe: str | None = None,
    timeout_s: float = 45.0,
) -> tuple[bool, list[dict[str, Any]]]:
    """Run existing `pass2pass` tests in `ws` to prevent single-test overfitting."""
    if not test_files:
        return True, []
    from canonical.swe_kernel import container_exec_bridge_v1 as _ce_bridge
    import shlex as _shlex

    bridge = _ce_bridge.get_active_bridge()
    if bridge is not None:
        ov = bridge.collect_modified_overlays(ws)
        results_c: list[dict[str, Any]] = []
        if repo_index.language == "python" and bridge.toolchain.python_exe:
            py_c = bridge.toolchain.python_exe
            pp_expr = f"{bridge.workdir}/{repo_index.python_src_root}:{bridge.workdir}" if repo_index.python_src_root else bridge.workdir
            tf_args = " ".join(_shlex.quote(tf) for tf in test_files)
            if bridge.toolchain.has_pytest:
                c_cmd = f"PYTHONPATH={_shlex.quote(pp_expr)}:${{PYTHONPATH:-}} PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 {_shlex.quote(py_c)} -m pytest -q --tb=no {tf_args}"
            else:
                c_cmd = f"PYTHONPATH={_shlex.quote(pp_expr)}:${{PYTHONPATH:-}} {_shlex.quote(py_c)} -c {_shlex.quote(_STDLIB_TEST_RUNNER_SNIPPET)} {tf_args}"
            rc, out, _ = bridge.run_cmd(c_cmd, overlays=ov, timeout_s=timeout_s)
            results_c.append({
                "files": list(test_files),
                "rc": rc,
                "summary": (out or "").strip().splitlines()[-1] if (out or "").strip() else "",
                "via_container_bridge": True,
            })
            return rc == 0, results_c
        if repo_index.language != "python" and (bridge.toolchain.vitest_bin or bridge.toolchain.node_exe):
            all_ok_c = True
            for tf in test_files:
                tf_text = (ws / tf).read_text(encoding="utf-8", errors="replace")
                if repo_index.is_typescript_vitest and bridge.toolchain.vitest_bin:
                    if not re.search(r"\b(?:describe|it|test)\s*\(", tf_text):
                        continue
                    c_cmd = f"{_shlex.quote(bridge.toolchain.vitest_bin)} run --no-file-parallelism {_shlex.quote(tf)}"
                else:
                    nd = bridge.toolchain.node_exe or "node"
                    c_cmd = f"{_shlex.quote(nd)} --test {_shlex.quote(tf)}" if "node:test" in tf_text else f"{_shlex.quote(nd)} {_shlex.quote(tf)}"
                rc, out, _ = bridge.run_cmd(c_cmd, overlays=ov, timeout_s=timeout_s)
                if rc != 0:
                    all_ok_c = False
                results_c.append({
                    "file": tf,
                    "rc": rc,
                    "summary": (out or "").strip().splitlines()[-1] if (out or "").strip() else "",
                    "via_container_bridge": True,
                })
            return all_ok_c, results_c

    results: list[dict[str, Any]] = []
    all_ok = True
    py = python_exe or sys.executable

    if repo_index.language == "python":
        env = dict(os.environ)
        pp_parts = [str(ws)]
        if repo_index.python_src_root:
            pp_parts.insert(0, str(ws / repo_index.python_src_root))
        if env.get("PYTHONPATH"):
            pp_parts.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(pp_parts)
        env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        if _python_has_pytest(py):
            cmd = [py, "-m", "pytest", "-q", "--tb=no", *list(test_files)]
        else:
            cmd = [py, "-c", _STDLIB_TEST_RUNNER_SNIPPET, *list(test_files)]
        proc = subprocess.run(cmd, cwd=ws, env=env, capture_output=True, text=True, timeout=timeout_s)
        ok = proc.returncode == 0
        all_ok = ok
        results.append({
            "files": list(test_files),
            "rc": proc.returncode,
            "summary": (proc.stdout or "").strip().splitlines()[-1] if (proc.stdout or "").strip() else "",
        })
    elif repo_index.is_typescript_vitest:
        vitest_bin = str(ws / "node_modules" / ".bin" / "vitest")
        for tf in test_files:
            tf_text = (ws / tf).read_text(encoding="utf-8", errors="replace")
            if not re.search(r"\b(?:describe|it|test)\s*\(", tf_text):
                continue
            cmd = [vitest_bin, "run", "--no-file-parallelism", tf]
            proc = subprocess.run(cmd, cwd=ws, capture_output=True, text=True, timeout=timeout_s)
            ok = proc.returncode == 0
            if not ok:
                all_ok = False
            results.append({
                "file": tf,
                "rc": proc.returncode,
                "summary": (proc.stdout or "").strip().splitlines()[-1] if (proc.stdout or "").strip() else "",
            })
    else:
        for tf in test_files:
            # Prefer `node` directly for tape/custom harnesses; fall back to `node --test`
            tf_text = (ws / tf).read_text(encoding="utf-8", errors="replace")
            cmd = ["node", "--test", tf] if "node:test" in tf_text else ["node", tf]
            proc = subprocess.run(cmd, cwd=ws, capture_output=True, text=True, timeout=timeout_s)
            ok = proc.returncode == 0
            if not ok:
                all_ok = False
            results.append({
                "file": tf,
                "rc": proc.returncode,
                "summary": (proc.stdout or "").strip().splitlines()[-1] if (proc.stdout or "").strip() else "",
            })
    return all_ok, results


def _copy_workspace(src: pathlib.Path, dst: pathlib.Path) -> None:
    """Create a fast isolated working copy (symlinking node_modules if present)."""
    def _ignore(dirpath: str, names: list[str]) -> set[str]:
        return {n for n in names if n in (".git", "__pycache__", ".pytest_cache", "node_modules")}

    shutil.copytree(src, dst, ignore=_ignore)
    nm = src / "node_modules"
    if nm.exists() and not (dst / "node_modules").exists():
        (dst / "node_modules").symlink_to(nm.resolve())


def solve_issue_from_description(
    repo_root: pathlib.Path,
    issue_text: str,
    *,
    python_exe: str | None = None,
    timeout_s: float = 60.0,
    run_regression: bool = True,
    memory: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """End-to-end blind issue resolution: `(repo_root, issue_text) -> verified unified patch`.

    Never requires a pre-existing failing test file and never mutates `repo_root`.
    """
    t0 = time.monotonic()
    root = pathlib.Path(repo_root).resolve()
    py = python_exe or sys.executable

    synth = synthesize_verified_reproducer(root, issue_text, python_exe=py, timeout_s=min(20.0, timeout_s / 2.0))
    repo_index: RepoSymbolIndex = synth["repo_index"]
    repro = synth.get("reproducer")
    if not repro:
        return {
            "schema": SCHEMA,
            "authority": AUTHORITY,
            "status": "NO_QUALIFIED_REPRODUCER",
            "verified": False,
            "language": repo_index.language,
            "candidates_compiled": synth["candidates_compiled"],
            "rejected_reproducers": synth["rejected"],
            "elapsed_s": round(time.monotonic() - t0, 3),
            "model_calls": 0,
            "parameters_stored": 0,
        }

    with tempfile.TemporaryDirectory(prefix="brain_blind_issue_") as td:
        ws = pathlib.Path(td) / "repo"
        _copy_workspace(root, ws)

        repro_list = list(synth.get("reproducers") or ([repro] if repro else []))
        repro_rels: list[str] = []
        all_ref_syms: list[str] = []
        for idx_r, rp in enumerate(repro_list):
            for s in rp.get("referenced_symbols") or []:
                if s not in all_ref_syms:
                    all_ref_syms.append(s)
            if rp["language"] == "python":
                subdir = str(rp.get("test_subdir") or "").strip("/")
                fname = f"_epistemic_issue_repro_{idx_r}_test.py" if idx_r > 0 else "_epistemic_issue_repro_test.py"
                r_rel = f"{subdir}/{fname}" if subdir else fname
            elif repo_index.is_typescript_vitest:
                r_rel = f"_epistemic_issue_repro_{idx_r}.spec.ts" if idx_r > 0 else "_epistemic_issue_repro.spec.ts"
            else:
                r_rel = f"_epistemic_issue_repro_{idx_r}.test.js" if idx_r > 0 else "_epistemic_issue_repro.test.js"
            r_path = ws / r_rel
            r_path.parent.mkdir(parents=True, exist_ok=True)
            r_path.write_text(rp["test_source"], encoding="utf-8")
            repro_rels.append(r_rel)

        # Include top symbol-matched existing pass2pass test files during Python solve so
        # overfitted candidates are pruned immediately (anti-overfit gate, arXiv:2511.16858v3).
        pre_reg_tests = (
            _select_regression_tests(repo_index, all_ref_syms, "", max_files=2)
            if run_regression
            else []
        )

        if repro["language"] == "python":
            from canonical.swe_kernel import container_exec_bridge_v1 as _ce_bridge

            solve_targets = list(repro_rels) + [tf for tf in pre_reg_tests if tf not in repro_rels]
            rem_s = max(15.0, timeout_s - (time.monotonic() - t0))
            if _ce_bridge.get_active_bridge() is not None:
                from canonical.swe_kernel import container_swe_patch_solver_v1 as _ce_py_solver

                solve_res = _ce_py_solver.solve_python_with_container_bridge(
                    ws,
                    solve_targets,
                    python_src_root=repo_index.python_src_root or "",
                    referenced_symbols=all_ref_syms,
                    timeout_s=rem_s,
                )
            else:
                from canonical.runtime import causal_angelic_swe_engine_v1 as PY_SWE

                solve_res = PY_SWE.solve_repository(
                    ws,
                    solve_targets,
                    python_exe=py,
                    timeout_s=rem_s,
                )
        else:
            from canonical.runtime import multilang_causal_swe_engine_v1 as ML_SWE

            solve_res = ML_SWE.solve_js_repository(
                ws,
                repro_rels[:1],
                memory=memory,
                timeout_s=max(15.0, timeout_s - (time.monotonic() - t0)),
            )

        winner = solve_res.get("winner") or {}
        if not solve_res.get("verified") or not winner.get("file") or not winner.get("patched_source"):
            return {
                "schema": SCHEMA,
                "authority": AUTHORITY,
                "status": "UNSOLVED",
                "verified": False,
                "language": repro["language"],
                "reproducer": repro,
                "solver_status": solve_res.get("status"),
                "elapsed_s": round(time.monotonic() - t0, 3),
                "model_calls": 0,
                "parameters_stored": 0,
            }

        # Apply ALL winner patches (single-file OR multi-file `COMPOSED_ANGELIC_PROGRESS`!)
        mod_rel = str(winner["file"])
        patched_files: dict[str, str] = {}
        raw_pf = winner.get("patched_files")
        if isinstance(raw_pf, Mapping) and raw_pf:
            for pf_rel, pf_src in raw_pf.items():
                patched_files[str(pf_rel)] = str(pf_src)
        else:
            patched_files[mod_rel] = str(winner["patched_source"])
            extra_patches = winner.get("extra_patches") or ()
            if isinstance(extra_patches, Mapping):
                for ef, esrc in extra_patches.items():
                    patched_files[str(ef)] = str(esrc)
            else:
                for ef, esrc in extra_patches:
                    patched_files[str(ef)] = str(esrc)

        diff_chunks: list[str] = []
        for pf_rel, pf_src in patched_files.items():
            orig_text = (root / pf_rel).read_text(encoding="utf-8", errors="replace")
            (ws / pf_rel).write_text(pf_src, encoding="utf-8")
            diff_chunks.append("".join(difflib.unified_diff(
                orig_text.splitlines(keepends=True),
                pf_src.splitlines(keepends=True),
                fromfile=f"a/{pf_rel}",
                tofile=f"b/{pf_rel}",
            )))

        # Remove all temporary reproducers before running pass2pass regression suite
        for r_rel in repro_rels:
            (ws / r_rel).unlink(missing_ok=True)

        reg_ok = True
        reg_tests: list[str] = []
        reg_report: list[dict[str, Any]] = []
        if run_regression:
            reg_tests = _select_regression_tests(repo_index, all_ref_syms, mod_rel)
            reg_ok, reg_report = _run_regression_suite(ws, repo_index, reg_tests, python_exe=py)

        if not reg_ok:
            return {
                "schema": SCHEMA,
                "authority": AUTHORITY,
                "status": "REGRESSION_REJECTED",
                "verified": False,
                "language": repro["language"],
                "reproducer": repro,
                "winner": {
                    "file": mod_rel,
                    "lineno": winner.get("lineno"),
                    "tier": winner.get("tier"),
                    "description": winner.get("description"),
                },
                "regression_tests": reg_tests,
                "regression_report": reg_report,
                "elapsed_s": round(time.monotonic() - t0, 3),
                "model_calls": 0,
                "parameters_stored": 0,
            }

        return {
            "schema": SCHEMA,
            "authority": AUTHORITY,
            "status": "VERIFIED",
            "verified": True,
            "language": repro["language"],
            "reproducer": repro,
            "winner": {
                "file": mod_rel,
                "lineno": winner.get("lineno"),
                "tier": winner.get("tier"),
                "description": winner.get("description"),
            },
            "patch_diff": "".join(diff_chunks),
            "patched_files": patched_files,
            "regression_tests": reg_tests,
            "regression_report": reg_report,
            "elapsed_s": round(time.monotonic() - t0, 3),
            "model_calls": 0,
            "parameters_stored": 0,
        }
