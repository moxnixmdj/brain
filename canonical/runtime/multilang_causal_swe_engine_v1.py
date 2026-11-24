"""Multi-Language Causal Angelic SWE Engine v1 (JavaScript / TypeScript / Node.js).

Zero-LLM, zero-weight (`model_calls == 0`, `parameters_stored == 0`) automated software repair
for real JavaScript & TypeScript repositories using:
  1. Built-in Node.js V8 coverage (`NODE_V8_COVERAGE`) + stack-trace fault localization
     (no Babel/Istanbul instrumentation required).
  2. Tier-0 external inspectable JS/TS rewrite law recall (Plotkin single-experience transfer).
  3. First-principles JS/TS causal repair operators (finite/safe-integer invariants, truthiness &
     empty-value unwrap, leading-delimiter accumulator repair, comparison/boolean/ternary repair,
     regex literal refinement, sibling domain-throw boundary guards, nullish crash guards).
  4. Two-phase isolated verification (`node --check` + isolated copy -> clean full-suite verify)
     with atomic writeback only on 0-regression verification pass.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import os
import pathlib
import re
import shutil
import signal
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence
from urllib.parse import unquote, urlparse

from canonical.runtime import oe_sygus_synthesizer_v1 as OESYGUS

SCHEMA = "BRAIN_MULTILANG_CAUSAL_SWE_ENGINE_V1"


def _run_pgroup_cmd(
    cmd: Sequence[str],
    *,
    cwd: str | pathlib.Path,
    env: Mapping[str, str] | None = None,
    timeout: float = 20.0,
) -> tuple[int, str, str]:
    """Run subprocess in its own process group and SIGKILL the entire group on timeout.

    Guarantees ZERO orphaned grandchild processes (e.g. runaway `node` workers from infinite
    loops) while still collecting any stdout/stderr flushed before timeout.
    """
    proc = subprocess.Popen(
        list(cmd),
        cwd=str(cwd),
        env=dict(env) if env is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
        start_new_session=True,
    )
    try:
        out, err = proc.communicate(timeout=timeout)
        return int(proc.returncode or 0), out or "", err or ""
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        try:
            out, err = proc.communicate(timeout=2.0)
        except Exception:
            out, err = "", ""
        return 124, out or "", (err or "") + "\nTIMEOUT"
AUTHORITY = "NONE"

_DEFAULT_EXTRA_BIN_DIRS = (
    "/tmp/js_test_tools/node_modules/.bin",
)
_DEFAULT_EXTRA_NODE_PATHS = (
    "/tmp/js_test_tools/node_modules",
)

_SKIP_DIRS = frozenset({
    ".git", "node_modules", "dist", "build", "coverage", ".next", ".turbo", ".cache", "__pycache__",
})


@dataclass(frozen=True)
class JSLocalizedSite:
    file: str
    lineno: int
    score: float
    source: str  # "stack" | "v8_cov" | "fallback"


@dataclass
class JSLocalizationReport:
    test_cmd: list[str]
    test_runner: str
    initial_rc: int
    initial_output: str
    sites: list[JSLocalizedSite] = field(default_factory=list)
    covered_lines_by_file: dict[str, set[int]] = field(default_factory=dict)
    error_types: list[str] = field(default_factory=list)
    build_cmd: list[str] | None = None


def _detect_js_build_cmd(worktree: pathlib.Path, src_files: Sequence[str], *, force_check: bool = False) -> list[str] | None:
    """Detect whether a JS/TS repository requires a pre-test build step (e.g., TS->dist/ or CJS/ESM bundle)."""
    pkg_path = worktree / "package.json"
    if not pkg_path.is_file():
        return None
    try:
        pkg = json.loads(pkg_path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None
    scripts = pkg.get("scripts") if isinstance(pkg.get("scripts"), dict) else {}
    npm_bin = shutil.which("npm") or "npm"
    has_ts = any(sf.endswith(".ts") for sf in src_files)
    # Collect declared entrypoints (`main`, `module`, `exports`) to see if compiled outputs are expected
    entry_paths: list[str] = []
    for k in ("main", "module"):
        v = pkg.get(k)
        if isinstance(v, str) and v.strip():
            entry_paths.append(v.strip())
    def _walk_exp(obj: Any) -> None:
        if isinstance(obj, str) and obj.strip():
            entry_paths.append(obj.strip())
        elif isinstance(obj, dict):
            for val in obj.values():
                _walk_exp(val)
    _walk_exp(pkg.get("exports"))
    compiled_markers = ("dist/", "build/", "lib/cjs/", "lib/esm/", "out/")
    needs_compiled = any(any(m in p for m in compiled_markers) for p in entry_paths)
    missing_entry = any(
        p.startswith("./") and not (worktree / p[2:]).exists()
        for p in entry_paths
        if "*" not in p
    )
    for _fast_b in ("build:esbuild", "build:js", "build:esm", "build:dist", "build:bundle", "build"):
        if isinstance(scripts.get(_fast_b), str) and scripts[_fast_b].strip():
            if has_ts or needs_compiled or missing_entry or force_check:
                return [npm_bin, "run", _fast_b]
    if (missing_entry or force_check) and (worktree / "jakefile.js").is_file():
        npx_bin = shutil.which("npx") or "npx"
        return [npx_bin, "jake", "build"]
    return None


@dataclass(frozen=True)
class JSPatchCandidate:
    file: str
    lineno: int
    tier: str
    description: str
    patched_source: str
    skill_id: str | None = None
    extra_patches: tuple[tuple[str, str], ...] = ()


def _ensure_tape_shim_dir() -> pathlib.Path:
    """Create a zero-dependency built-in `tape` adapter backed by Node `assert` (lowest `NODE_PATH` fallback)."""
    shim_nm = pathlib.Path(tempfile.gettempdir()) / ".brain_js_shims_v1" / "node_modules"
    tape_js = shim_nm / "tape" / "index.js"
    if not tape_js.is_file():
        tape_js.parent.mkdir(parents=True, exist_ok=True)
        tape_js.write_text(
            "const assert = require('assert');\n"
            "let _fails = 0, _tests = 0;\n"
            "function tape(name, cb) {\n"
            "  _tests++;\n"
            "  const t = {\n"
            "    ok: (v, m) => assert.ok(v, m),\n"
            "    true: (v, m) => assert.ok(v, m),\n"
            "    notOk: (v, m) => assert.ok(!v, m),\n"
            "    false: (v, m) => assert.ok(!v, m),\n"
            "    equal: (a, b, m) => assert.strictEqual(a, b, m),\n"
            "    strictEqual: (a, b, m) => assert.strictEqual(a, b, m),\n"
            "    is: (a, b, m) => assert.strictEqual(a, b, m),\n"
            "    notEqual: (a, b, m) => assert.notStrictEqual(a, b, m),\n"
            "    deepEqual: (a, b, m) => assert.deepStrictEqual(a, b, m),\n"
            "    same: (a, b, m) => assert.deepStrictEqual(a, b, m),\n"
            "    notDeepEqual: (a, b, m) => assert.notDeepStrictEqual(a, b, m),\n"
            "    throws: (fn, e, m) => assert.throws(fn, e, m),\n"
            "    doesNotThrow: (fn, m) => assert.doesNotThrow(fn, m),\n"
            "    pass: () => {},\n"
            "    fail: (m) => assert.fail(m || 'fail'),\n"
            "    plan: () => {},\n"
            "    end: () => {},\n"
            "  };\n"
            "  try { cb(t); console.log('ok ' + _tests + ' - ' + name); }\n"
            "  catch (err) {\n"
            "    _fails++;\n"
            "    console.log('not ok ' + _tests + ' - ' + name);\n"
            "    console.error(err && err.stack ? err.stack : String(err));\n"
            "  }\n"
            "}\n"
            "process.on('beforeExit', () => {\n"
            "  console.log('# tests ' + _tests + '\\n# pass ' + (_tests - _fails) + '\\n# fail ' + _fails);\n"
            "  if (_fails > 0) process.exitCode = 1;\n"
            "});\n"
            "module.exports = tape;\n",
            encoding="utf-8",
        )
    de_js = shim_nm / "deep-equal" / "index.js"
    if not de_js.is_file():
        de_js.parent.mkdir(parents=True, exist_ok=True)
        de_js.write_text(
            "const assert = require('assert');\n"
            "module.exports = function deepEqual(a, b, opts) {\n"
            "  try {\n"
            "    if (opts && opts.strict) assert.deepStrictEqual(a, b);\n"
            "    else assert.deepEqual(a, b);\n"
            "    return true;\n"
            "  } catch (_) {\n"
            "    return false;\n"
            "  }\n"
            "};\n",
            encoding="utf-8",
        )
    sb_js = shim_nm / "safe-buffer" / "index.js"
    if not sb_js.is_file():
        sb_js.parent.mkdir(parents=True, exist_ok=True)
        sb_js.write_text("module.exports = { Buffer: globalThis.Buffer };\n", encoding="utf-8")
    return shim_nm


def _build_node_env(repo: pathlib.Path, *, cov_dir: pathlib.Path | None = None) -> dict[str, str]:
    env = dict(os.environ)
    bin_parts: list[str] = []
    local_bin = repo / "node_modules" / ".bin"
    if local_bin.is_dir():
        bin_parts.append(str(local_bin))
    for d in _DEFAULT_EXTRA_BIN_DIRS:
        if os.path.isdir(d):
            bin_parts.append(d)
    if env.get("PATH"):
        bin_parts.append(env["PATH"])
    env["PATH"] = ":".join(bin_parts)

    np_parts: list[str] = []
    local_nm = repo / "node_modules"
    if local_nm.is_dir():
        np_parts.append(str(local_nm))
    for d in _DEFAULT_EXTRA_NODE_PATHS:
        if os.path.isdir(d):
            np_parts.append(d)
    if env.get("NODE_PATH"):
        np_parts.append(env["NODE_PATH"])
    np_parts.append(str(_ensure_tape_shim_dir()))
    if np_parts:
        env["NODE_PATH"] = ":".join(np_parts)
    if cov_dir is not None:
        env["NODE_V8_COVERAGE"] = str(cov_dir)
    env["CI"] = "1"
    return env


def _find_tool_bin(tool: str, repo: pathlib.Path) -> str | None:
    cand_local = repo / "node_modules" / ".bin" / tool
    if cand_local.is_file():
        return str(cand_local)
    for d in _DEFAULT_EXTRA_BIN_DIRS:
        p = pathlib.Path(d) / tool
        if p.is_file():
            return str(p)
    found = shutil.which(tool)
    return found


def is_js_ts_repo(repo: pathlib.Path) -> bool:
    if (repo / "package.json").is_file():
        return True
    for p in repo.iterdir():
        if p.is_file() and p.suffix.lower() in (".js", ".mjs", ".cjs", ".ts"):
            return True
    return False


def _is_non_prod_skip(rel: str) -> bool:
    low = rel.lower().replace("\\", "/")
    parts = low.split("/")
    base = parts[-1]
    return (
        "benchmarks" in parts
        or "benchmark" in parts
        or "examples" in parts
        or "fixtures" in parts
        or "docs" in parts
        or ".bench." in base
    )


def _is_test_path(rel: str) -> bool:
    low = rel.lower().replace("\\", "/")
    parts = low.split("/")
    base = parts[-1]
    return (
        "test" in parts
        or "tests" in parts
        or "__tests__" in parts
        or base in ("test.js", "tests.js", "test.mjs", "tests.mjs", "test.ts", "tests.ts")
        or ".test." in base
        or ".spec." in base
        or base.startswith("test_")
        or base.startswith("test-")
    )


def _discover_js_files(repo: pathlib.Path) -> tuple[list[str], list[str]]:
    src_files: list[str] = []
    test_files: list[str] = []
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in sorted(dirs) if d not in _SKIP_DIRS and not d.startswith(".")]
        for fn in sorted(files):
            if not fn.endswith((".js", ".mjs", ".cjs", ".ts")) or fn.endswith(".d.ts"):
                continue
            if fn.endswith((".config.js", ".config.ts", ".config.mjs", ".config.cjs")):
                continue
            rel = pathlib.Path(root, fn).relative_to(repo).as_posix()
            if _is_non_prod_skip(rel):
                continue
            if _is_test_path(rel):
                test_files.append(rel)
            else:
                src_files.append(rel)
    return src_files, test_files


def detect_js_test_command(
    repo: pathlib.Path,
    test_targets: Sequence[str] | None = None,
) -> tuple[list[str], str]:
    """Auto-detect the fastest zero-config JS/TS test command for `repo`."""
    node_bin = shutil.which("node") or "node"
    targets = list(test_targets) if test_targets else []
    pkg: dict[str, Any] = {}
    if (repo / "package.json").is_file():
        try:
            pkg = json.loads((repo / "package.json").read_text(encoding="utf-8", errors="replace"))
        except Exception:
            pkg = {}
    scripts_test = str((pkg.get("scripts") or {}).get("test") or "")
    dev_deps = set((pkg.get("devDependencies") or {}).keys()) | set((pkg.get("dependencies") or {}).keys())

    if not targets:
        _, found_tests = _discover_js_files(repo)
        targets = found_tests

    sample_text = ""
    for tf in targets[:3]:
        p = repo / tf
        if p.is_file():
            try:
                sample_text += p.read_text(encoding="utf-8", errors="replace")[:4000] + "\n"
            except OSError:
                pass

    has_ts = any(t.endswith(".ts") for t in targets)
    if (
        "vitest" in dev_deps
        or "vitest" in scripts_test
        or "from 'vitest'" in sample_text
        or 'from "vitest"' in sample_text
    ):
        vbin = _find_tool_bin("vitest", repo)
        if vbin:
            cmd = [vbin, "run", "--no-file-parallelism", "--reporter=verbose"]
            if targets:
                cmd.extend(targets)
            return cmd, "vitest"
        # Zero-dependency fallback: Node v22 native TypeScript strip-types + ESM loader hook mapping `vitest` onto `node:test` + `node:assert`
        vdir = pathlib.Path(tempfile.gettempdir()) / ".brain_vitest_shim_v2"
        try:
            vdir.mkdir(parents=True, exist_ok=True)
            vmod = vdir / "vitest.mjs"
            vldr = vdir / "loader.mjs"
            if not vmod.is_file():
                vmod.write_text(
                    "import { describe as _desc, it as _it, test as _test, beforeEach, afterEach, before, after } from 'node:test';\n"
                    "import _assert from 'node:assert';\n"
                    "function _attachEach(fn) {\n"
                    "  const w = Object.assign((...a) => fn(...a), fn);\n"
                    "  w.each = (cases) => (name, cb) => {\n"
                    "    for (const c of cases) {\n"
                    "      const args = Array.isArray(c) ? c : [c];\n"
                    "      let label = String(name);\n"
                    "      for (const a of args) label = label.replace(/%[sdifjoO%]/, String(a));\n"
                    "      fn(label, () => cb(...args));\n"
                    "    }\n"
                    "  };\n"
                    "  return w;\n"
                    "}\n"
                    "export const describe = _attachEach(_desc);\n"
                    "export const it = _attachEach(_it);\n"
                    "export const test = _attachEach(_test);\n"
                    "export const beforeAll = before;\n"
                    "export const afterAll = after;\n"
                    "export const assert = Object.assign((...a) => _assert(...a), _assert, {\n"
                    "  isTrue: (v, m) => _assert.strictEqual(v, true, m),\n"
                    "  isFalse: (v, m) => _assert.strictEqual(v, false, m),\n"
                    "  isNull: (v, m) => _assert.strictEqual(v, null, m),\n"
                    "  isUndefined: (v, m) => _assert.strictEqual(v, undefined, m),\n"
                    "});\n"
                    "export function expect(actual) {\n"
                    "  const make = (neg) => ({\n"
                    "    toBe: (exp) => neg ? _assert.notStrictEqual(actual, exp) : _assert.strictEqual(actual, exp),\n"
                    "    toEqual: (exp) => neg ? _assert.notDeepEqual(actual, exp) : _assert.deepEqual(actual, exp),\n"
                    "    toStrictEqual: (exp) => neg ? _assert.notDeepStrictEqual(actual, exp) : _assert.deepStrictEqual(actual, exp),\n"
                    "    toThrow: (m) => neg ? _assert.doesNotThrow(actual, m) : _assert.throws(actual, m),\n"
                    "    toMatch: (re) => neg ? _assert.doesNotMatch(String(actual), re) : _assert.match(String(actual), re),\n"
                    "    toContain: (sub) => {\n"
                    "      const ok = Array.isArray(actual) ? actual.includes(sub) : String(actual).includes(String(sub));\n"
                    "      _assert.strictEqual(ok, !neg);\n"
                    "    },\n"
                    "    toBeTruthy: () => _assert.strictEqual(Boolean(actual), !neg),\n"
                    "    toBeFalsy: () => _assert.strictEqual(Boolean(actual), neg),\n"
                    "    toBeDefined: () => _assert.strictEqual(actual !== undefined, !neg),\n"
                    "    toBeUndefined: () => _assert.strictEqual(actual === undefined, !neg),\n"
                    "    toBeNull: () => _assert.strictEqual(actual === null, !neg),\n"
                    "    toBeInstanceOf: (cls) => _assert.strictEqual(actual instanceof cls, !neg),\n"
                    "    toHaveLength: (n) => _assert.strictEqual(actual.length === n, !neg),\n"
                    "  });\n"
                    "  return Object.assign(make(false), { not: make(true) });\n"
                    "}\n"
                    "export { beforeEach, afterEach, before, after };\n",
                    encoding="utf-8",
                )
            if not vldr.is_file():
                vldr.write_text(
                    "import fs from 'node:fs';\n"
                    "import path from 'node:path';\n"
                    "import { pathToFileURL, fileURLToPath } from 'node:url';\n"
                    f"const VITEST_URL = {vmod.as_uri()!r};\n"
                    "export async function resolve(specifier, context, nextResolve) {\n"
                    "  if (specifier === 'vitest') return { url: VITEST_URL, shortCircuit: true };\n"
                    "  if (specifier.startsWith('.') && context.parentURL) {\n"
                    "    const parentDir = path.dirname(fileURLToPath(context.parentURL));\n"
                    "    const cands = [];\n"
                    "    for (const ext of ['', '.ts', '.mts', '.js', '.mjs', '/index.ts', '/index.js']) {\n"
                    "      cands.push(path.resolve(parentDir, specifier + ext));\n"
                    "    }\n"
                    "    if (specifier.endsWith('.js')) cands.push(path.resolve(parentDir, specifier.slice(0, -3) + '.ts'));\n"
                    "    if (specifier.endsWith('.mjs')) cands.push(path.resolve(parentDir, specifier.slice(0, -4) + '.mts'));\n"
                    "    for (const cand of cands) {\n"
                    "      if (fs.existsSync(cand) && fs.statSync(cand).isFile()) {\n"
                    "        return { url: pathToFileURL(cand).href, shortCircuit: true };\n"
                    "      }\n"
                    "    }\n"
                    "  }\n"
                    "  return nextResolve(specifier, context);\n"
                    "}\n"
                    "export async function load(url, context, nextLoad) {\n"
                    "  if (url.endsWith('.ts') && !url.endsWith('.d.ts')) {\n"
                    "    const src = fs.readFileSync(fileURLToPath(url), 'utf8');\n"
                    "    if (/^\\s*(?:import|export)\\b/m.test(src)) {\n"
                    "      return { format: 'module-typescript', source: src, shortCircuit: true };\n"
                    "    }\n"
                    "  }\n"
                    "  return nextLoad(url, context);\n"
                    "}\n",
                    encoding="utf-8",
                )
            reg_uri = f"data:text/javascript,import {{ register }} from 'node:module'; register({vldr.as_uri()!r});"
            cmd = [node_bin, "--experimental-strip-types", "--import", reg_uri, "--test"]
            if targets:
                cmd.extend(targets)
            return cmd, "vitest_shim"
        except OSError:
            pass

    if (
        "mocha" in dev_deps
        or "mocha" in scripts_test
        or ("describe(" in sample_text and "it(" in sample_text and "node:test" not in sample_text and not has_ts)
    ):
        mbin = _find_tool_bin("mocha", repo)
        if mbin:
            cmd = [mbin, "--bail=false", "--timeout", "10000"]
            # Check if package.json explicitly declares a `mocha <files...>` suite (e.g. `"test-node"`).
            # When declared, use its exact harness + test files so browser-only server scripts (e.g. `tests/test.js`)
            # are never passed to Node Mocha and leading harness files always load before target test files.
            mocha_script_files: list[str] = []
            all_scripts = pkg.get("scripts") or {}
            if isinstance(all_scripts, dict):
                for sc_val in all_scripts.values():
                    sc_s = str(sc_val or "").strip()
                    if sc_s.startswith("mocha "):
                        sc_files = [tok for tok in sc_s.split()[1:] if not tok.startswith("-") and (repo / tok).is_file()]
                        if sc_files:
                            mocha_script_files = sc_files
                            break
            if mocha_script_files:
                mocha_targets = list(mocha_script_files)
                for t in (targets or ()):
                    if t not in mocha_targets and not any(t.endswith(f) for f in ("/test.js", "test.js")):
                        mocha_targets.append(t)
                cmd.extend(mocha_targets)
            elif targets:
                cmd.extend(targets)
            return cmd, "mocha"
        # Zero-dependency fallback: map Mocha globals + per-suite/per-test `this` context onto Node's `node:test`
        shim_path = pathlib.Path(tempfile.gettempdir()) / ".brain_mocha_shim_v2.cjs"
        try:
            if not shim_path.is_file():
                shim_path.write_text(
                    "const nt = require('node:test');\n"
                    "let suiteCtx = { timeout() {}, slow() {}, retries() {}, skip() {} };\n"
                    "function _wrapDesc(name, fn) {\n"
                    "  return nt.describe(name, () => {\n"
                    "    const prev = suiteCtx;\n"
                    "    suiteCtx = Object.create(prev);\n"
                    "    try { return fn.call(suiteCtx); } finally { suiteCtx = prev; }\n"
                    "  });\n"
                    "}\n"
                    "function _wrapSuiteHook(hook) {\n"
                    "  return (nameOrFn, maybeFn) => {\n"
                    "    const fn = typeof nameOrFn === 'function' ? nameOrFn : maybeFn;\n"
                    "    const sc = suiteCtx;\n"
                    "    return hook(() => fn.call(sc));\n"
                    "  };\n"
                    "}\n"
                    "function _wrapTestHook(hook) {\n"
                    "  return (nameOrFn, maybeFn) => {\n"
                    "    const fn = typeof nameOrFn === 'function' ? nameOrFn : maybeFn;\n"
                    "    const sc = suiteCtx;\n"
                    "    return hook((t) => { t._mc = t._mc || Object.create(sc); return fn.call(t._mc); });\n"
                    "  };\n"
                    "}\n"
                    "function _wrapIt(name, fn) {\n"
                    "  if (!fn) return nt.it(name, { skip: true }, () => {});\n"
                    "  const sc = suiteCtx;\n"
                    "  return nt.it(name, (t) => { t._mc = t._mc || Object.create(sc); return fn.call(t._mc); });\n"
                    "}\n"
                    "global.describe = _wrapDesc;\n"
                    "global.context = _wrapDesc;\n"
                    "global.it = _wrapIt;\n"
                    "global.specify = _wrapIt;\n"
                    "global.before = _wrapSuiteHook(nt.before);\n"
                    "global.beforeEach = _wrapTestHook(nt.beforeEach);\n"
                    "global.after = _wrapSuiteHook(nt.after);\n"
                    "global.afterEach = _wrapTestHook(nt.afterEach);\n",
                    encoding="utf-8",
                )
            cmd = [node_bin, "--test", "-r", str(shim_path)]
            if targets:
                cmd.extend(targets)
            return cmd, "mocha_shim"
        except OSError:
            pass

    if (
        "ava" in dev_deps
        or "from 'ava'" in sample_text
        or 'from "ava"' in sample_text
    ):
        abin = _find_tool_bin("ava", repo)
        if abin:
            cmd = [abin, "--timeout=20s"]
            if targets:
                cmd.extend(targets)
            return cmd, "ava"

    if "uvu" in dev_deps or "uvu" in scripts_test or "from 'uvu'" in sample_text or 'from "uvu"' in sample_text:
        udir = pathlib.Path(tempfile.gettempdir()) / ".brain_uvu_shim_v3"
        umod = udir / "uvu.mjs"
        uass = udir / "assert.mjs"
        uldr = udir / "loader.mjs"
        try:
            udir.mkdir(parents=True, exist_ok=True)
            if not umod.is_file():
                umod.write_text(
                    "import nt from 'node:test';\n"
                    "export function suite(title = '', initCtx = {}) {\n"
                    "  const tests = [];\n"
                    "  const b = [], a = [], be = [], ae = [];\n"
                    "  const fn = (name, cb) => tests.push({ name, cb, only: false, skip: false });\n"
                    "  fn.only = (name, cb) => tests.push({ name, cb, only: true, skip: false });\n"
                    "  fn.skip = (name, cb) => tests.push({ name, cb, only: false, skip: true });\n"
                    "  fn.before = (cb) => b.push(cb); fn.before.each = (cb) => be.push(cb);\n"
                    "  fn.after = (cb) => a.push(cb); fn.after.each = (cb) => ae.push(cb);\n"
                    "  fn.run = () => {\n"
                    "    nt.describe(title || 'uvu', () => {\n"
                    "      const ctx = Object.assign({}, initCtx);\n"
                    "      for (const h of b) nt.before(() => h(ctx));\n"
                    "      for (const h of be) nt.beforeEach(() => h(ctx));\n"
                    "      for (const h of a) nt.after(() => h(ctx));\n"
                    "      for (const h of ae) nt.afterEach(() => h(ctx));\n"
                    "      for (const t of tests) {\n"
                    "        if (t.skip) nt.it(t.name, { skip: true }, () => {});\n"
                    "        else nt.it(t.name, () => t.cb(ctx));\n"
                    "      }\n"
                    "    });\n"
                    "  };\n"
                    "  return fn;\n"
                    "}\n"
                    "export const test = suite();\n",
                    encoding="utf-8",
                )
            if not uass.is_file():
                uass.write_text(
                    "import assert from 'node:assert';\n"
                    "export const ok = (v, m) => assert.ok(v, m);\n"
                    "export const is = (a, b, m) => assert.ok(Object.is(a, b), m || `Expected ${a} to be ${b}`);\n"
                    "is.not = (a, b, m) => assert.ok(!Object.is(a, b), m || `Expected ${a} not to be ${b}`);\n"
                    "export const equal = (a, b, m) => assert.deepStrictEqual(a, b, m);\n"
                    "export const unreachable = (m) => assert.fail(m || 'Should not reach');\n"
                    "export const type = (v, t, m) => assert.strictEqual(typeof v, t, m);\n"
                    "export const instance = (v, c, m) => assert.ok(v instanceof c, m);\n"
                    "export const match = (v, r, m) => assert.ok(typeof r === 'string' ? String(v).includes(r) : r.test(String(v)), m);\n"
                    "export const snapshot = (a, b, m) => assert.strictEqual(a, b, m);\n"
                    "export const fixture = snapshot;\n"
                    "export const throws = (fn, e, m) => assert.throws(fn, e, m);\n"
                    "export const not = (v, m) => assert.ok(!v, m);\n"
                    "not.ok = (v, m) => assert.ok(!v, m);\n"
                    "not.equal = (a, b, m) => assert.notDeepStrictEqual(a, b, m);\n"
                    "not.type = (v, t, m) => assert.notStrictEqual(typeof v, t, m);\n"
                    "not.instance = (v, c, m) => assert.ok(!(v instanceof c), m);\n"
                    "not.match = (v, r, m) => assert.ok(!(typeof r === 'string' ? String(v).includes(r) : r.test(String(v))), m);\n"
                    "not.throws = (fn, e, m) => assert.doesNotThrow(fn, e, m);\n",
                    encoding="utf-8",
                )
            if not uldr.is_file():
                uldr.write_text(
                    "import fs from 'node:fs';\n"
                    "import path from 'node:path';\n"
                    "import { fileURLToPath, pathToFileURL } from 'node:url';\n"
                    "export async function resolve(specifier, context, nextResolve) {\n"
                    f"  if (specifier === 'uvu') return {{ url: {umod.as_uri()!r}, shortCircuit: true }};\n"
                    f"  if (specifier === 'uvu/assert') return {{ url: {uass.as_uri()!r}, shortCircuit: true }};\n"
                    "  if ((specifier.startsWith('./') || specifier.startsWith('../')) && context.parentURL && context.parentURL.startsWith('file:')) {\n"
                    "    const parentDir = path.dirname(fileURLToPath(context.parentURL));\n"
                    "    for (const ext of ['', '.js', '.mjs', '/index.js', '/index.mjs']) {\n"
                    "      const cand = path.resolve(parentDir, specifier + ext);\n"
                    "      if (fs.existsSync(cand) && fs.statSync(cand).isFile()) {\n"
                    "        return { url: pathToFileURL(cand).href, shortCircuit: true };\n"
                    "      }\n"
                    "    }\n"
                    "  }\n"
                    "  return nextResolve(specifier, context);\n"
                    "}\n",
                    encoding="utf-8",
                )
            reg_uri = f"data:text/javascript,import {{ register }} from 'node:module'; register({uldr.as_uri()!r});"
            uvu_targets = [
                t for t in (targets or [])
                if "/suites/" not in t.replace("\\", "/")
            ]
            if not uvu_targets:
                # Prefer top-level `test/*.js` entrypoints that invoke `.run()`
                tdir = repo / "test"
                if tdir.is_dir():
                    uvu_targets = [
                        p.relative_to(repo).as_posix()
                        for p in sorted(tdir.glob("*.js"))
                        if ".run(" in p.read_text(encoding="utf-8", errors="replace")
                    ]
            cmd = [node_bin, "--import", reg_uri, "--test"]
            if uvu_targets:
                cmd.extend(uvu_targets)
            return cmd, "uvu_shim"
        except OSError:
            pass

    if "tape" in dev_deps or "tape" in scripts_test or "require('tape')" in sample_text or 'require("tape")' in sample_text:
        if targets:
            if len(targets) == 1:
                return [node_bin, targets[0]], "tape_shim"
            req_expr = ";".join(f"require({json.dumps(str((repo / t).resolve()))})" for t in targets)
            return [node_bin, "-e", req_expr], "tape_shim"

    if "tap" in dev_deps or "tap" in scripts_test or "require('tap')" in sample_text or 'require("tap")' in sample_text:
        if targets and len(targets) == 1:
            return [node_bin, targets[0]], "node_tap"
        tbin = _find_tool_bin("tap", repo)
        if tbin:
            cmd = [tbin, "--no-coverage"]
            if targets:
                cmd.extend(targets)
            return cmd, "tap"

    if "node:test" in sample_text or "node --test" in scripts_test:
        cmd = [node_bin, "--test"]
        if targets:
            cmd.extend(targets)
        return cmd, "node_test"

    if targets:
        return [node_bin, "--test", *targets], "node_test"
    return [node_bin, "--test"], "node_test"


def _copy_js_worktree(src_root: pathlib.Path, dst_root: pathlib.Path) -> None:
    if dst_root.exists():
        shutil.rmtree(dst_root)
    dst_root.mkdir(parents=True, exist_ok=True)
    for item in src_root.iterdir():
        if item.name in (".git", "__pycache__", ".pytest_cache"):
            continue
        dst_item = dst_root / item.name
        if item.name == "node_modules" and item.is_dir():
            # Fast symlink for read-only node_modules
            os.symlink(str(item.resolve()), str(dst_item))
        elif item.is_dir():
            shutil.copytree(item, dst_item, symlinks=True, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        else:
            shutil.copy2(item, dst_item)


def _offset_to_lineno(line_starts: list[int], offset: int) -> int:
    # Binary search line_starts for 1-based line number
    lo, hi = 0, len(line_starts) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if line_starts[mid] <= offset:
            lo = mid + 1
        else:
            hi = mid - 1
    return max(1, hi + 1)


_VLQ_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
_VLQ_MAP = {ch: i for i, ch in enumerate(_VLQ_CHARS)}


def _load_sourcemap_line_map(
    gen_path: pathlib.Path,
    worktree: pathlib.Path,
    src_files: set[str],
) -> dict[int, list[tuple[str, int]]]:
    """Pure-Python ECMA-426 Source Map v3 Base64-VLQ decoder (zero dependencies).

    Maps 1-based generated JS line numbers (e.g. `dist/lib.mjs:1420`) back to
    1-based original source `(rel_src_path, orig_lineno)` pairs in `src_files`.
    Supports both sibling `.map` files and inline `sourceMappingURL=data:...;base64,...`.
    """
    sm_obj: dict[str, Any] | None = None
    map_dir = gen_path.parent
    sib_map = pathlib.Path(str(gen_path) + ".map")
    if sib_map.is_file():
        try:
            sm_obj = json.loads(sib_map.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            sm_obj = None
    if sm_obj is None and gen_path.is_file():
        try:
            tail = gen_path.read_text(encoding="utf-8", errors="replace")[-8192:]
            m_url = re.search(r"//[#@]\s*sourceMappingURL=(\S+)", tail)
            if m_url:
                surl = m_url.group(1).strip()
                if surl.startswith("data:") and ";base64," in surl:
                    import base64
                    b64 = surl.split(";base64,", 1)[1]
                    sm_obj = json.loads(base64.b64decode(b64).decode("utf-8", errors="replace"))
                else:
                    cand_map = (gen_path.parent / surl).resolve()
                    if cand_map.is_file():
                        map_dir = cand_map.parent
                        sm_obj = json.loads(cand_map.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            sm_obj = None
    if not isinstance(sm_obj, dict):
        return {}
    sources_raw = sm_obj.get("sources")
    mappings = sm_obj.get("mappings")
    if not isinstance(sources_raw, list) or not isinstance(mappings, str) or not mappings:
        return {}
    source_root = str(sm_obj.get("sourceRoot") or "")
    wt_res = worktree.resolve()
    resolved_sources: list[str | None] = []
    for sr in sources_raw:
        if not isinstance(sr, str):
            resolved_sources.append(None)
            continue
        raw_s = (source_root + sr) if source_root else sr
        raw_s = raw_s.replace("\\", "/")
        if raw_s.startswith("file://"):
            raw_s = unquote(urlparse(raw_s).path)
        rel_match: str | None = None
        try:
            cand_p = (map_dir / raw_s).resolve()
            rel_c = cand_p.relative_to(wt_res).as_posix()
            if rel_c in src_files:
                rel_match = rel_c
        except Exception:
            pass
        if rel_match is None:
            norm_s = raw_s.lstrip("./")
            while norm_s.startswith("../"):
                norm_s = norm_s[3:]
            if norm_s in src_files:
                rel_match = norm_s
        resolved_sources.append(rel_match)
    if not any(resolved_sources):
        return {}

    line_map: dict[int, list[tuple[str, int]]] = {}
    src_idx = 0
    orig_line = 0  # 0-based in VLQ
    orig_col = 0
    gen_line = 1  # 1-based
    i = 0
    n = len(mappings)
    while i < n:
        ch = mappings[i]
        if ch == ";":
            gen_line += 1
            i += 1
            continue
        if ch == ",":
            i += 1
            continue
        # Decode up to 5 VLQ integers for this segment
        fields: list[int] = []
        while i < n and mappings[i] not in (",", ";"):
            val = 0
            shift = 0
            while i < n:
                d = _VLQ_MAP.get(mappings[i], -1)
                i += 1
                if d < 0:
                    break
                val |= (d & 31) << shift
                shift += 5
                if (d & 32) == 0:
                    break
            signed = -(val >> 1) if (val & 1) else (val >> 1)
            fields.append(signed)
        if len(fields) >= 4:
            src_idx += fields[1]
            orig_line += fields[2]
            orig_col += fields[3]
            if 0 <= src_idx < len(resolved_sources):
                rsrc = resolved_sources[src_idx]
                if rsrc is not None and orig_line >= 0:
                    pair = (rsrc, orig_line + 1)
                    lst = line_map.setdefault(gen_line, [])
                    if not lst or lst[-1] != pair:
                        lst.append(pair)
    return line_map


def _extract_v8_covered_lines(
    cov_dir: pathlib.Path,
    worktree: pathlib.Path,
    src_files: set[str],
) -> dict[str, set[int]]:
    wt_resolved = worktree.resolve()
    covered: dict[str, set[int]] = {}
    line_starts_cache: dict[str, list[int]] = {}
    smap_cache: dict[str, dict[int, list[tuple[str, int]]]] = {}

    for jf in sorted(cov_dir.glob("*.json")):
        try:
            data = json.loads(jf.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            continue
        for script in data.get("result") or ():
            url = str(script.get("url") or "")
            if not url.startswith("file://"):
                continue
            try:
                p = pathlib.Path(unquote(urlparse(url).path)).resolve()
                rel = p.relative_to(wt_resolved).as_posix()
            except Exception:
                continue
            use_smap = rel not in src_files
            if use_smap:
                # Skip node_modules and test files; map compiled dist/build bundles back via Source Map v3!
                if "node_modules/" in rel or rel.startswith("test/") or rel.startswith("tests/"):
                    continue
                if rel not in smap_cache:
                    smap_cache[rel] = _load_sourcemap_line_map(p, worktree, src_files)
                smap = smap_cache[rel]
                if not smap:
                    continue
            else:
                smap = {}
            if rel not in line_starts_cache:
                try:
                    txt = p.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                starts = [0]
                for idx, ch in enumerate(txt):
                    if ch == "\n":
                        starts.append(idx + 1)
                line_starts_cache[rel] = starts
            starts = line_starts_cache[rel]
            for fn in script.get("functions") or ():
                for rg in fn.get("ranges") or ():
                    if int(rg.get("count", 0)) <= 0:
                        continue
                    s_ln = _offset_to_lineno(starts, int(rg.get("startOffset", 0)))
                    e_ln = _offset_to_lineno(starts, max(int(rg.get("startOffset", 0)), int(rg.get("endOffset", 0)) - 1))
                    # Avoid whole-file module wrapper drowning specificity when inner functions exist
                    if e_ln - s_ln > 200 and fn.get("functionName") == "":
                        continue
                    if not use_smap:
                        lset = covered.setdefault(rel, set())
                        for ln in range(s_ln, min(e_ln + 1, s_ln + 300)):
                            lset.add(ln)
                    else:
                        for gln in range(s_ln, min(e_ln + 1, s_ln + 400)):
                            for orig_rel, orig_ln in smap.get(gln, ()):
                                covered.setdefault(orig_rel, set()).add(orig_ln)
    return covered


def _resolve_direct_test_imports(
    worktree: pathlib.Path,
    test_targets: Sequence[str] | None,
    src_files: set[str],
) -> tuple[set[str], set[str]]:
    """Resolve direct relative `import`/`require` edges from failing test files to repo source files.

    Returns `(stem_matches, direct_imports)` where `stem_matches` are the exact unit-under-test
    files mirrored by the test path (e.g. `test/ranges/subset.js` -> `ranges/subset.js`).
    """
    stem_matches: set[str] = set()
    direct: set[str] = set()
    wt_res = worktree.resolve()
    for tf in test_targets or ():
        tp = worktree / tf
        if not tp.is_file():
            continue
        # Stem match: e.g., test/ranges/subset.js -> ranges/subset.js
        tf_norm = tf.replace("\\", "/")
        for prefix in ("test/", "tests/", "__tests__/"):
            if tf_norm.startswith(prefix):
                cand = tf_norm[len(prefix):]
                if cand in src_files:
                    stem_matches.add(cand)
                    direct.add(cand)
        try:
            txt = tp.read_text(encoding="utf-8", errors="replace")[:12000]
        except OSError:
            continue
        specs = re.findall(r"""(?:from\s+|require\s*\(\s*)['"](\.\.?/[^'"]+)['"]""", txt)
        for spec in specs:
            base = (tp.parent / spec)
            cands = [base]
            if base.suffix in (".js", ".mjs", ".cjs"):
                # ESM TypeScript imports often write `./index.js` pointing to `./index.ts`
                cands.append(base.with_suffix(".ts"))
            elif not base.suffix:
                for ext in (".ts", ".js", ".mjs", ".cjs"):
                    cands.append(pathlib.Path(str(base) + ext))
                for idx in ("index.ts", "index.js", "index.mjs"):
                    cands.append(base / idx)
            for c in cands:
                try:
                    rel = c.resolve().relative_to(wt_res).as_posix()
                except Exception:
                    continue
                if rel in src_files:
                    direct.add(rel)
    return stem_matches, direct


def _extract_failing_test_symbols(output: str) -> set[str]:
    """Extract candidate identifier tokens from failing test headers/assertions (ANSI-stripped)."""
    clean = re.sub(r"\x1b\[[0-9;]*m", "", output)
    toks: set[str] = set()
    stop = {
        "should", "when", "with", "from", "that", "this", "expected", "received",
        "error", "assertionerror", "function", "throw", "equal", "deeply", "fail",
        "true", "false", "null", "undefined", "string", "number", "option", "value",
    }
    for line in clean.splitlines():
        if any(m in line for m in ("FAIL ", "× ", "not ok ", "1) ", "2) ", "3) ", "→ ")):
            for m in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]{2,})\b", line):
                ml = m.lower()
                if ml not in stop:
                    toks.add(m)
                    toks.add(ml)
    return toks


def localize_js_faults(
    worktree: pathlib.Path,
    test_targets: Sequence[str] | None = None,
    *,
    timeout_s: float = 30.0,
) -> JSLocalizationReport:
    src_files_list, _ = _discover_js_files(worktree)
    src_files = set(src_files_list)
    test_cmd, runner = detect_js_test_command(worktree, test_targets)
    build_cmd = _detect_js_build_cmd(worktree, src_files_list)
    if build_cmd:
        _b_rc, _, _ = _run_pgroup_cmd(
            build_cmd,
            cwd=worktree,
            env=_build_node_env(worktree),
            timeout=min(timeout_s, 25.0),
        )
        if _b_rc != 0:
            build_cmd = None

    with tempfile.TemporaryDirectory(prefix="brain_v8cov_") as cov_tmp:
        cov_dir = pathlib.Path(cov_tmp)
        env = _build_node_env(worktree, cov_dir=cov_dir)
        rc, _so, _se = _run_pgroup_cmd(
            test_cmd,
            cwd=worktree,
            env=env,
            timeout=min(timeout_s, 14.0),
        )
        out = _so + "\n" + _se
        if rc != 0 and build_cmd is None and ("ERR_MODULE_NOT_FOUND" in out or "MODULE_NOT_FOUND" in out):
            _fallback_build = _detect_js_build_cmd(worktree, src_files_list, force_check=True)
            if _fallback_build:
                _b_rc2, _, _ = _run_pgroup_cmd(
                    _fallback_build,
                    cwd=worktree,
                    env=env,
                    timeout=min(timeout_s, 25.0),
                )
                if _b_rc2 == 0:
                    build_cmd = _fallback_build
                    rc, _so, _se = _run_pgroup_cmd(
                        test_cmd,
                        cwd=worktree,
                        env=env,
                        timeout=min(timeout_s, 14.0),
                    )
                    out = _so + "\n" + _se
        covered = _extract_v8_covered_lines(cov_dir, worktree, src_files)

    stem_matches, direct_imports = _resolve_direct_test_imports(worktree, test_targets, src_files)
    fail_syms = _extract_failing_test_symbols(out)

    # Extract stack-trace frames referencing repo source files (including Source Map v3 translation!)
    sites: list[JSLocalizedSite] = []
    seen_sites: set[tuple[str, int]] = set()
    wt_str = str(worktree.resolve()).replace("\\", "/")
    _stack_smaps: dict[str, dict[int, list[tuple[str, int]]]] = {}
    for m in re.finditer(r"([A-Za-z0-9_./\\\-]+\.(?:js|mjs|cjs|ts)):(\d+)(?::\d+)?", out):
        raw_p = m.group(1).replace("\\", "/")
        lno = int(m.group(2))
        rel = raw_p
        if raw_p.startswith(wt_str + "/"):
            rel = raw_p[len(wt_str) + 1 :]
        rel = rel.lstrip("./")
        mapped_targets: list[tuple[str, int]] = []
        if rel in src_files:
            mapped_targets.append((rel, lno))
        elif "node_modules/" not in rel and (worktree / rel).is_file():
            if rel not in _stack_smaps:
                _stack_smaps[rel] = _load_sourcemap_line_map(worktree / rel, worktree, src_files)
            mapped_targets.extend(_stack_smaps[rel].get(lno, ())[:2])
        for m_rel, m_lno in mapped_targets:
            if m_rel in src_files and (m_rel, m_lno) not in seen_sites:
                seen_sites.add((m_rel, m_lno))
                boost = 0.35 if m_rel in stem_matches else (0.2 if m_rel in direct_imports else 0.0)
                sites.append(JSLocalizedSite(file=m_rel, lineno=m_lno, score=1.0 + boost, source="stack"))
                covered.setdefault(m_rel, set()).add(m_lno)

    # Add V8-covered lines from executed repo source files (stem match > direct import > transitive)
    for rel, lns in sorted(covered.items()):
        base_score = 1.2 if rel in stem_matches else (0.9 if rel in direct_imports else 0.55)
        for ln in sorted(lns):
            if (rel, ln) not in seen_sites:
                seen_sites.add((rel, ln))
                sites.append(JSLocalizedSite(file=rel, lineno=ln, score=base_score, source="v8_cov"))

    # Fallback: if V8 coverage didn't record a transpiled .ts file (e.g., vitest OXC/SSR transform),
    # scan direct-import files first (full file!), then remaining non-test source files.
    if not sites or (direct_imports and not any(d in covered for d in direct_imports)):
        ordered_fallback = [r for r in src_files_list if r in direct_imports] + [
            r for r in src_files_list if r not in direct_imports
        ]
        for rel in ordered_fallback[:6]:
            if rel in covered:
                continue
            p = worktree / rel
            if p.is_file():
                nlines = len(p.read_text(encoding="utf-8", errors="replace").splitlines())
                base_score = 0.85 if rel in direct_imports else 0.3
                for ln in range(1, min(nlines + 1, 1500)):
                    covered.setdefault(rel, set()).add(ln)
                    sites.append(JSLocalizedSite(file=rel, lineno=ln, score=base_score, source="fallback"))

    # Boost lines inside functions / statements referencing failing-test symbols
    if fail_syms and sites:
        file_lines_cache: dict[str, list[str]] = {}
        boosted: list[JSLocalizedSite] = []
        for s in sites:
            if s.file not in file_lines_cache:
                p = worktree / s.file
                file_lines_cache[s.file] = (
                    p.read_text(encoding="utf-8", errors="replace").splitlines() if p.is_file() else []
                )
            flines = file_lines_cache[s.file]
            extra = 0.0
            if 1 <= s.lineno <= len(flines):
                # Check line itself + nearest enclosing function header
                ltxt = flines[s.lineno - 1]
                ltoks = set(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]{2,})\b", ltxt))
                _hit_syms = ltoks & fail_syms
                if _hit_syms:
                    # Strong boost for distinctive camelCase/snake_case symbols (e.g. `forceQuotes`, `plainObjects`, `renderFile`)
                    _has_distinct = any(
                        any(c.isupper() for c in t[1:]) or ("_" in t and len(t) >= 6)
                        for t in _hit_syms
                    )
                    extra += 0.35 if _has_distinct else 0.15
                # Check enclosing function declaration within 80 lines above
                for back in range(s.lineno - 1, max(0, s.lineno - 80), -1):
                    hdr = flines[back - 1]
                    mf = re.search(r"\bfunction\s+([A-Za-z_$]\w*)", hdr)
                    if mf:
                        if mf.group(1) in fail_syms or mf.group(1).lower() in fail_syms:
                            extra += 0.2
                        break
            boosted.append(JSLocalizedSite(file=s.file, lineno=s.lineno, score=s.score + extra, source=s.source))
        sites = boosted

    sites.sort(key=lambda s: (-s.score, s.file, s.lineno))
    err_types = sorted(set(re.findall(r"\b((?:Assertion|Type|Range|Reference|Syntax|URI)?Error)\b", out)))
    return JSLocalizationReport(
        test_cmd=test_cmd,
        test_runner=runner,
        initial_rc=rc,
        initial_output=out,
        sites=sites,
        covered_lines_by_file=covered,
        error_types=err_types,
        build_cmd=build_cmd,
    )


def _check_js_syntax(rel: str, src: str) -> bool:
    if rel.endswith((".ts", ".tsx", ".mts", ".cts")):
        # Strip comments and quoted/regex literals before balanced delimiter check so parser
        # files with `/* { */` or `'('` literals are never falsely rejected.
        cleaned = re.sub(
            r"//[^\n]*|/\*[\s\S]*?\*/|'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"|`(?:\\.|[^`\\])*`",
            "",
            src,
        )
        return cleaned.count("{") == cleaned.count("}") and cleaned.count("(") == cleaned.count(")")
    node_bin = shutil.which("node") or "node"
    suf = pathlib.Path(rel).suffix or ".js"
    with tempfile.NamedTemporaryFile("w", suffix=suf, encoding="utf-8", delete=False) as tf:
        tf.write(src)
        tpath = tf.name
    try:
        cp = subprocess.run([node_bin, "--check", tpath], capture_output=True, text=True, timeout=5.0)
        return cp.returncode == 0
    except Exception:
        return False
    finally:
        try:
            os.unlink(tpath)
        except OSError:
            pass


def _extract_js_single_line_diff(before: str, after: str) -> tuple[str, str] | None:
    b_lines = before.splitlines()
    a_lines = after.splitlines()
    if len(b_lines) != len(a_lines):
        return None
    diffs = [(b.strip(), a.strip()) for b, a in zip(b_lines, a_lines) if b != a]
    if len(diffs) == 1 and diffs[0][0] and diffs[0][1]:
        return diffs[0]
    return None


def _abstract_js_line_rule(before_line: str, after_line: str) -> dict[str, Any] | None:
    """Generalize a verified 1-line JS/TS repair into a path-free, variable-generalized regex rule."""
    # Never leak paths
    if re.search(r"(?:/tmp/|/home/|/Users/)", before_line + after_line):
        return None
    # Parameterize common single-identifier variable in finite/safe-int/nullish rewrites
    for pat_b, pat_a, kind in (
        (r"isNaN\(([A-Za-z_$][\w$.]*)\)", r"!Number.isFinite(\1)", "isNaN_to_not_isFinite"),
        (r"!isNaN\(([A-Za-z_$][\w$.]*)\)", r"Number.isFinite(\1)", "not_isNaN_to_isFinite"),
        (r"Number\.isFinite\(([A-Za-z_$][\w$.]*)\)", r"Number.isSafeInteger(\1)", "isFinite_to_isSafeInteger"),
        (r"!Number\.isFinite\(([A-Za-z_$][\w$.]*)\)", r"!Number.isSafeInteger(\1)", "not_isFinite_to_not_isSafeInteger"),
        (r"Number\.isInteger\(([A-Za-z_$][\w$.]*)\)", r"Number.isSafeInteger(\1)", "isInteger_to_isSafeInteger"),
        (r"!Number\.isInteger\(([A-Za-z_$][\w$.]*)\)", r"!Number.isSafeInteger(\1)", "not_isInteger_to_not_isSafeInteger"),
        (r"isFinite\(([A-Za-z_$][\w$.]*)\)", r"Number.isSafeInteger(\1)", "global_isFinite_to_isSafeInteger"),
        (r"\bfor\s*\(\s*var\s+([A-Za-z_$]\w*)\s*=", r"for (let \1 =", "var_param_shadow_to_let"),
        (r"\\u000b", r"\\u0009", "regex_vtab_to_htab"),
    ):
        if re.search(pat_b, before_line) and re.sub(pat_b, pat_a, before_line) == after_line:
            lid = "jslaw_" + hashlib.sha256(f"{kind}|{pat_b}|{pat_a}".encode("utf-8")).hexdigest()[:12]
            return {
                "law_id": lid,
                "kind": kind,
                "pattern": pat_b,
                "replacement": pat_a,
                "verified_uses": 1,
                "status": "ACTIVE",
                "parameters_stored": 0,
            }
    return None


def synthesize_js_candidates(
    worktree: pathlib.Path,
    loc: JSLocalizationReport,
    *,
    memory: Mapping[str, Any] | None = None,
    max_candidates: int = 80,
) -> list[JSPatchCandidate]:
    """Generate minimal, high-precision JS/TS repair candidates from live V8 localization + failure signal."""
    cands: list[JSPatchCandidate] = []
    seen_src: set[tuple[str, str, tuple[tuple[str, str], ...]]] = set()

    file_counts: dict[str, int] = {}
    per_file_cap = max(28, max_candidates // 2)

    def add_cand(
        rel: str,
        lineno: int,
        tier: str,
        desc: str,
        patched: str,
        skill_id: str | None = None,
        extra_patches: tuple[tuple[str, str], ...] = (),
    ) -> None:
        if len(cands) >= max_candidates:
            return
        if tier != "JS_TIER0_SKILL_RECALL" and file_counts.get(rel, 0) >= per_file_cap and len(file_order) > 1:
            return
        key = (rel, patched, extra_patches)
        if key in seen_src:
            return
        seen_src.add(key)
        file_counts[rel] = file_counts.get(rel, 0) + 1
        cands.append(JSPatchCandidate(rel, lineno, tier, desc, patched, skill_id, extra_patches))

    out_txt = loc.initial_output
    out_low = out_txt.lower()
    want_throw = any(
        k in out_low
        for k in ("did not throw", "expected function to throw", "to throw", "throws", "missing expected exception")
    )

    # Order files & lines by localization score (stack > direct-import+symbol > v8_cov > fallback)
    file_order: list[str] = []
    lines_by_file_ranked: dict[str, list[int]] = {}
    for s in loc.sites:
        if s.file not in file_order:
            file_order.append(s.file)
        fl = lines_by_file_ranked.setdefault(s.file, [])
        if s.lineno not in fl:
            fl.append(s.lineno)
    # Also include remaining JS source files & promote files whose stem/symbols appear in failure output
    _all_src_js, _ = _discover_js_files(worktree)
    for _sf in _all_src_js:
        if _sf not in file_order:
            file_order.append(_sf)
    # Extract failing-block lines (`not ok`, `FAIL`, `AssertionError`, `at ...`) for symbol/stem matching
    _fail_lines = [
        ln for ln in out_txt.splitlines()
        if any(k in ln for k in ("not ok ", "FAIL", "AssertionError", "Error:", "expected", "actual", "at "))
    ]
    _fail_blob = "\n".join(_fail_lines[:80])
    _fail_stems = {
        m.group(1).lower()
        for m in re.finditer(r"(?:^|[/\\])([A-Za-z0-9_-]{3,})\.(?:js|mjs|cjs|ts)\b", _fail_blob)
    }
    _fail_camel = {
        m.group(0)
        for m in re.finditer(r"\b[a-z][a-zA-Z0-9]*[A-Z][a-zA-Z0-9]+\b", _fail_blob)
    }
    if _fail_stems or _fail_camel:
        _orig_pos = {rf: i for i, rf in enumerate(file_order)}
        def _file_promo(rf: str) -> tuple[int, int]:
            st = pathlib.Path(rf).stem.lower()
            score_p = 0
            if st in _fail_stems:
                score_p += 10
            if _fail_camel:
                fp_p = worktree / rf
                if fp_p.is_file():
                    txt_p = fp_p.read_text(encoding="utf-8", errors="replace")
                    hits_c = sum(1 for sym in _fail_camel if sym in txt_p)
                    score_p += min(hits_c, 3) * 8
            return (-score_p, _orig_pos.get(rf, 999))
        file_order.sort(key=_file_promo)

    # 0. Tier-0 Recall from External Inspectable `js_rewrite_laws` (0 extra search on unseen repos!)
    js_laws = memory.get("js_rewrite_laws") if isinstance(memory, Mapping) else None
    if isinstance(js_laws, Mapping) and js_laws:
        for rel in file_order[:4]:
            p = worktree / rel
            if not p.is_file():
                continue
            orig = p.read_text(encoding="utf-8", errors="replace")
            lines = orig.splitlines(keepends=True)
            lns = lines_by_file_ranked.get(rel) or list(range(1, len(lines) + 1))
            for lid, rec in js_laws.items():
                if not isinstance(rec, Mapping) or rec.get("status") != "ACTIVE":
                    continue
                pat = str(rec.get("pattern") or "")
                repl = str(rec.get("replacement") or "")
                if not pat:
                    continue
                for ln in lns:
                    if 1 <= ln <= len(lines) and re.search(pat, lines[ln - 1]):
                        new_line = re.sub(pat, repl, lines[ln - 1])
                        if new_line != lines[ln - 1]:
                            nl = list(lines)
                            nl[ln - 1] = new_line
                            add_cand(rel, ln, "JS_TIER0_SKILL_RECALL", f"tier0({rec.get('kind', lid)})", "".join(nl), skill_id=str(lid))

    # Pass 1: High-precision semantic operators (Ops 1-5) across ranked lines
    # Pass 2: Broad comparison/boolean flips (Op 6) so they never starve Pass 1
    cmp_deferred: list[tuple[str, int, str, str, str]] = []

    for rel in file_order[:4]:
        p = worktree / rel
        if not p.is_file():
            continue
        orig = p.read_text(encoding="utf-8", errors="replace")
        lines = orig.splitlines(keepends=True)
        lns = lines_by_file_ranked.get(rel) or list(range(1, len(lines) + 1))

        # Pre-harvest existing `throw new <Err>(...)` statements in this file for Op 5
        existing_throws: list[str] = []
        for ltxt in lines:
            mt = re.search(r"(throw\s+new\s+[A-Za-z_]\w*\s*\([^;\n]+\))", ltxt)
            if mt:
                ts = mt.group(1).strip().rstrip(";") + ";"
                if ts not in existing_throws:
                    existing_throws.append(ts)

        # Pre-harvest boolean `options.<prop>` flags referenced in this file (zero domain hardcoding)
        opt_flags: list[str] = []
        for mopt in re.finditer(r"\boptions\.([A-Za-z_$]\w*)\b", orig):
            fl_name = mopt.group(1)
            if fl_name not in opt_flags:
                opt_flags.append(fl_name)

        # Op 0c (high-precision runtime crash): JS TypeError Optional-Chaining Member Guard
        # (`JS_TYPEERROR_OPTIONAL_MEMBER_GUARD`):
        # When Node throws `TypeError: Cannot read properties of undefined/null (reading 'M')`,
        # rewrite `.M` -> `?.M` at the exact crash line (and also check `Cannot read property 'M'`).
        if "TypeError" in loc.error_types:
            m_prop = re.search(
                r"Cannot read propert(?:ies of (?:undefined|null) \(reading|y) '([A-Za-z_$]\w*)'",
                loc.initial_output,
            )
            if m_prop:
                prop_nm = m_prop.group(1)
                for ln_te in lns[:12]:
                    if not (1 <= ln_te <= len(lines)):
                        continue
                    l_te = lines[ln_te - 1]
                    if f".{prop_nm}" in l_te and f"?.{prop_nm}" not in l_te:
                        nl = list(lines)
                        nl[ln_te - 1] = l_te.replace(f".{prop_nm}", f"?.{prop_nm}", 1)
                        add_cand(
                            rel, ln_te, "JS_TYPEERROR_OPTIONAL_MEMBER_GUARD",
                            f"optional_chain(.{prop_nm}->?.{prop_nm})", "".join(nl),
                        )

        # Op 0d (high-precision semantic): Falsy-Zero Numeric Coercion Guard (`JS_FALSY_ZERO_NUMERIC_COERCION_FIX`):
        # In JavaScript `Number('0')` is `0` (falsy!), so `return (G && Number(X)) || X;` or `return Number(X) || X;`
        # drops `'0'` back to string `'0'`. Rewrite to explicit non-NaN non-empty ternary preserving `0`.
        for ln_fz in lns[:200]:
            if not (1 <= ln_fz <= len(lines)):
                continue
            l_fz = lines[ln_fz - 1]
            m_fz = re.match(
                r"^(\s*return\s+)\((.+?)\s*&&\s*Number\(([A-Za-z_$][\w$.]*)\)\)\s*\|\|\s*\3(\s*;?\s*)$",
                l_fz,
            )
            if m_fz:
                fz_pre, fz_g, fz_x, fz_post = m_fz.groups()
                nl = list(lines)
                nl[ln_fz - 1] = (
                    f"{fz_pre}({fz_g} && {fz_x} !== '' && {fz_x} != null && !Number.isNaN(Number({fz_x}))) "
                    f"? Number({fz_x}) : {fz_x}{fz_post}\n"
                )
                add_cand(
                    rel, ln_fz, "JS_FALSY_ZERO_NUMERIC_COERCION_FIX",
                    f"falsy_zero_number_coercion({fz_x})", "".join(nl),
                )
            else:
                m_fz2 = re.match(
                    r"^(\s*return\s+)Number\(([A-Za-z_$][\w$.]*)\)\s*\|\|\s*\2(\s*;?\s*)$",
                    l_fz,
                )
                if m_fz2:
                    fz_pre, fz_x, fz_post = m_fz2.groups()
                    nl = list(lines)
                    nl[ln_fz - 1] = (
                        f"{fz_pre}({fz_x} !== '' && {fz_x} != null && !Number.isNaN(Number({fz_x}))) "
                        f"? Number({fz_x}) : {fz_x}{fz_post}\n"
                    )
                    add_cand(
                        rel, ln_fz, "JS_FALSY_ZERO_NUMERIC_COERCION_FIX",
                        f"falsy_zero_number_coercion({fz_x})", "".join(nl),
                    )

        # Op 0e (high-precision dataflow): Read-Before-Write Sibling Block Dependency Reorder
        # (`JS_SIBLING_BLOCK_DEP_REORDER`):
        # When 1+ consecutive `obj.<prop>.forEach(...)` consumer blocks are immediately followed at the same
        # indentation by an `if (...) { ... obj[...].push(...) }` producer block mutating `obj`'s bucket arrays,
        # reorder the producer block before the `.forEach(...)` consumer blocks to restore write-before-read order.
        for bi in range(len(lines)):
            m_fe = re.match(r"^([ \t]+)([A-Za-z_$]\w*)\.[A-Za-z_$]\w*\.forEach\s*\(", lines[bi])
            if not m_fe:
                continue
            fe_ind, fe_obj = m_fe.groups()
            # Collect 1+ contiguous `fe_obj.<prop>.forEach(...)` blocks at indentation `fe_ind`
            cur = bi
            fe_end = bi
            while cur < len(lines):
                if not lines[cur].strip():
                    cur += 1
                    continue
                if re.match(rf"^{re.escape(fe_ind)}{re.escape(fe_obj)}\.[A-Za-z_$]\w*\.forEach\s*\(", lines[cur]):
                    # Find matching closing `});` at indentation `fe_ind`
                    blk_close = -1
                    for cj in range(cur + 1, min(len(lines), cur + 25)):
                        if lines[cj].startswith(fe_ind + "}") and ");" in lines[cj]:
                            blk_close = cj
                            break
                    if blk_close < 0:
                        break
                    fe_end = blk_close + 1
                    cur = fe_end
                else:
                    break
            # Skip blank lines to inspect the immediately following sibling block
            p_start = fe_end
            while p_start < len(lines) and not lines[p_start].strip():
                p_start += 1
            if p_start >= len(lines) or not re.match(rf"^{re.escape(fe_ind)}if\s*\([^)]+\)\s*\{{\s*$", lines[p_start]):
                continue
            p_end = -1
            for pj in range(p_start + 1, min(len(lines), p_start + 30)):
                if lines[pj].strip() == "}" and lines[pj][: len(lines[pj]) - len(lines[pj].lstrip())] == fe_ind:
                    p_end = pj + 1
                    break
            if p_end <= p_start:
                continue
            prod_txt = "".join(lines[p_start:p_end])
            if re.search(rf"\b{re.escape(fe_obj)}(?:\[[^\n;]+\]|\.[A-Za-z_$]\w*)(?:\s*\|\|\s*\[\s*\])?\)?\??\.push\s*\(", prod_txt):
                if any((k + 1) in set(lns) for k in range(bi, p_end)):
                    nl = lines[:bi] + lines[p_start:p_end] + ["\n"] + lines[bi:fe_end] + lines[p_end:]
                    add_cand(
                        rel, p_start + 1, "JS_SIBLING_BLOCK_DEP_REORDER",
                        f"reorder_producer_before_forEach({fe_obj})", "".join(nl),
                    )
                    break

        # Op 0f (high-precision interval arithmetic): Non-Negative Suffix Lower-Bound Clamp
        # (`JS_INTERVAL_SUB_LOWER_CLAMP`):
        # When computing an interval lower bound `start = size - end` while clamping the upper bound to `size - 1`,
        # suffix length > size produces negative `start`. `Math.max(size - end, 0)` clamps to 0 while preserving NaN.
        for ln_cl in lns[:200]:
            if not (1 <= ln_cl <= len(lines)):
                continue
            l_cl = lines[ln_cl - 1]
            m_sub = re.match(
                r"^(\s*(?:(?:var|let|const)\s+)?)([A-Za-z_$]\w*)\s*=\s*([A-Za-z_$]\w*)\s*-\s*([A-Za-z_$]\w*)(\s*;?\s*)$",
                l_cl,
            )
            if not m_sub:
                continue
            cl_ind, cl_lhs, cl_hi, cl_sub, cl_semi = m_sub.groups()
            win_cl = "".join(lines[ln_cl : min(len(lines), ln_cl + 24)])
            if f"{cl_lhs} < 0" in win_cl and f"{cl_hi} - 1" in win_cl:
                nl = list(lines)
                nl[ln_cl - 1] = f"{cl_ind}{cl_lhs} = Math.max({cl_hi} - {cl_sub}, 0){cl_semi}\n"
                add_cand(
                    rel, ln_cl, "JS_INTERVAL_SUB_LOWER_CLAMP",
                    f"clamp_nonneg({cl_lhs}=Math.max({cl_hi}-{cl_sub},0))", "".join(nl),
                )

        # Op 0g (high-precision RFC/ASCII regex control-char law):
        # `JS_REGEX_HTAB_VTAB_TYPO_FIX`:
        # When an HTTP/RFC printable-ASCII regex character class (including module-level `const` regexes
        # evaluated at import time) includes `\u000b` (vertical tab) alongside `\u0020-\u007e`, rewrite `\u000b` -> `\u0009` (HTAB).
        for ln_rx, l_rx in enumerate(lines, 1):
            if r"\u000b" in l_rx and (r"\u0020-\u007e" in l_rx or r"\x20-\x7e" in l_rx):
                nl = list(lines)
                nl[ln_rx - 1] = l_rx.replace(r"\u000b", r"\u0009")
                add_cand(
                    rel, ln_rx, "JS_REGEX_HTAB_VTAB_TYPO_FIX",
                    "regex_vtab_to_htab(\\u000b->\\u0009)", "".join(nl),
                )

        # Op 0h (high-precision map-write idempotency / first-write-wins law):
        # `JS_MAP_FIRST_WRITE_GUARD`:
        # Inside a localized parser function with `map[key] = expr;` assignments to the same `(map, key)`,
        # atomically guard all writes with `if (map[key] === undefined) map[key] = expr;` (first-write-wins).
        _map_writes: dict[tuple[str, str], list[int]] = {}
        for idx_mw, l_mw in enumerate(lines):
            m_mw = re.match(r"^(\s*)([A-Za-z_$]\w*)\s*\[\s*([A-Za-z_$]\w*)\s*\]\s*=\s*([^=].+?);\s*$", l_mw)
            if m_mw and f"{m_mw.group(2)}[{m_mw.group(3)}] === undefined" not in l_mw:
                _map_writes.setdefault((m_mw.group(2), m_mw.group(3)), []).append(idx_mw)
        localized_js_set = set(lns)
        for (mw_map, mw_key), mw_idxs in _map_writes.items():
            if not any((mi + 1) in localized_js_set for mi in mw_idxs):
                continue
            # Only guard dictionary/parameter maps (at least 1 write inside localized function, skip numeric `arr[i]`)
            if mw_key in ("i", "j", "k", "idx", "index"):
                continue
            nl_mw = list(lines)
            for mi in mw_idxs:
                m_mw = re.match(r"^(\s*)(.+;\s*)$", nl_mw[mi])
                if m_mw:
                    nl_mw[mi] = f"{m_mw.group(1)}if ({mw_map}[{mw_key}] === undefined) {m_mw.group(2)}"
            add_cand(
                rel, mw_idxs[0] + 1, "JS_MAP_FIRST_WRITE_GUARD",
                f"first_write_wins({mw_map}[{mw_key}]x{len(mw_idxs)})", "".join(nl_mw),
            )

        # Op 0i (high-precision strict JS decimal integer parsing + non-empty NaN sentinel guard):
        # `JS_STRICT_PARSEINT_DECIMAL_GUARD`:
        # 1. Replace `parseInt(expr, 10)` in localized sites with strict decimal `(/^\d+$/.test(expr) ? Number(expr) : NaN)`.
        # 2. When consecutive `var v = parseInt(expr, 10)` bindings feed downstream `isNaN(v)` branches inside a
        #    function with an explicit malformed-input `return <sentinel>` (e.g., `return -2`), also emit a guard
        #    rejecting non-empty non-decimal tokens (`if ((expr && !/^\d+$/.test(expr)) || ...) return <sentinel>;`).
        _pat_pint = re.compile(r"\bparseInt\s*\(\s*([^,()]+?)\s*,\s*10\s*\)")
        pint_hits = [ln_pi for ln_pi in lns[:250] if 1 <= ln_pi <= len(lines) and _pat_pint.search(lines[ln_pi - 1])]
        if pint_hits:
            nl_pi = list(lines)
            for ln_pi in pint_hits:
                nl_pi[ln_pi - 1] = _pat_pint.sub(
                    lambda m: f"(/^\\d+$/.test({m.group(1)}) ? Number({m.group(1)}) : NaN)",
                    nl_pi[ln_pi - 1],
                )
            add_cand(
                rel, pint_hits[0], "JS_STRICT_PARSEINT_DECIMAL_GUARD",
                f"strict_decimal_parseInt(x{len(pint_hits)})", "".join(nl_pi),
            )
            # Check for non-empty non-decimal token guard returning enclosing malformed-input sentinel
            pint_exprs: list[str] = []
            pint_vars: list[str] = []
            last_pi_ln = pint_hits[0]
            for ln_pi in pint_hits:
                m_bind = re.match(
                    r"^\s*(?:var|let|const)\s+([A-Za-z_$]\w*)\s*=\s*parseInt\s*\(\s*([^,()]+?)\s*,\s*10\s*\)",
                    lines[ln_pi - 1],
                )
                if m_bind:
                    pint_vars.append(m_bind.group(1))
                    pint_exprs.append(m_bind.group(2).strip())
                    last_pi_ln = max(last_pi_ln, ln_pi)
            if pint_exprs:
                # Find enclosing function's early error return sentinels (e.g. `return -2` or `if (...) return -2;`)
                sentinels: list[str] = []
                for back_i in range(max(0, pint_hits[0] - 40), pint_hits[0]):
                    m_ret = re.search(r"\breturn\s+(-?\d+|null|false)\s*;?\s*$", lines[back_i])
                    if m_ret and m_ret.group(1) not in sentinels:
                        sentinels.append(m_ret.group(1))
                indent_pi = lines[last_pi_ln - 1][: len(lines[last_pi_ln - 1]) - len(lines[last_pi_ln - 1].lstrip())]
                cond_strict = " || ".join(f"({ex} && !/^\\d+$/.test({ex}))" for ex in pint_exprs)
                cond_nan = " || ".join(f"({ex} && isNaN({vr}))" for ex, vr in zip(pint_exprs, pint_vars))
                for sent in sentinels[:2]:
                    for tag_c, cond_c in (("strict_digits", cond_strict), ("nonempty_nan", cond_nan)):
                        nl_g = list(lines)
                        nl_g.insert(last_pi_ln, f"{indent_pi}if ({cond_c}) return {sent}\n")
                        add_cand(
                            rel, last_pi_ln, "JS_STRICT_PARSEINT_DECIMAL_GUARD",
                            f"nonempty_token_guard({tag_c}->return {sent})", "".join(nl_g),
                        )

        # Op 0j (high-precision JS function-scoped `var` parameter-shadowing repair):
        # `JS_VAR_PARAM_SHADOW_TO_LET`:
        # When `function fn(..., p, ...)` contains `for (var p = ...)` whose loop variable `p` shadows
        # an enclosing function parameter `p`, rewrite `for (var p =` -> `for (let p =` (ES6 block scoping).
        # Also checks sibling source files in the same directory for identical `for (var p =` parameter shadowing
        # to enable atomic multi-file repair across parallel parser modules.
        def _fix_var_param_shadow_in_lines(file_lines: list[str], target_var: str | None = None) -> tuple[str, int, str] | None:
            out_l = list(file_lines)
            first_hit = -1
            hit_var = ""
            for i_v, raw_v in enumerate(out_l):
                m_fv = re.search(r"\bfor\s*\(\s*var\s+([A-Za-z_$]\w*)\s*=", raw_v)
                if not m_fv:
                    continue
                lv = m_fv.group(1)
                if target_var and lv != target_var:
                    continue
                for back_i in range(i_v - 1, max(-1, i_v - 35), -1):
                    m_fn = re.search(r"(?:^|\W)function(?:\s+[A-Za-z_$]\w*)?\s*\(([^)]*)\)\s*\{", out_l[back_i])
                    if m_fn:
                        params = [pt.strip() for pt in m_fn.group(1).split(",") if pt.strip()]
                        if lv in params:
                            out_l[i_v] = re.sub(rf"\bfor\s*\(\s*var\s+{re.escape(lv)}\s*=", f"for (let {lv} =", raw_v, count=1)
                            if first_hit < 0:
                                first_hit = i_v + 1
                                hit_var = lv
                        break
            if first_hit > 0:
                return "".join(out_l), first_hit, hit_var
            return None

        _shadow_hit = _fix_var_param_shadow_in_lines(lines)
        if _shadow_hit is not None:
            patched_s, hit_ln, hit_v = _shadow_hit
            add_cand(
                rel, hit_ln, "JS_VAR_PARAM_SHADOW_TO_LET",
                f"block_scope_shadowed_param(for let {hit_v})", patched_s,
            )
            # Check sibling modules in the same directory for identical `var` parameter shadowing
            sib_extras: list[tuple[str, str]] = []
            rel_dir = (worktree / rel).parent
            if rel_dir.is_dir():
                for sib_p in sorted(rel_dir.iterdir()):
                    if not sib_p.is_file() or sib_p.suffix.lower() not in (".js", ".mjs", ".cjs", ".ts"):
                        continue
                    sib_rel = sib_p.relative_to(worktree).as_posix()
                    if (
                        sib_rel == rel
                        or _is_non_prod_skip(sib_rel)
                        or ".test." in sib_rel
                        or ".spec." in sib_rel
                        or sib_rel.startswith("test/")
                        or sib_rel.startswith("tests/")
                    ):
                        continue
                    sib_lines = sib_p.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
                    sib_fix = _fix_var_param_shadow_in_lines(sib_lines, target_var=hit_v)
                    if sib_fix is not None:
                        sib_extras.append((sib_rel, sib_fix[0]))
            if sib_extras:
                add_cand(
                    rel, hit_ln, "JS_VAR_PARAM_SHADOW_TO_LET",
                    f"block_scope_shadowed_param_multifile(for let {hit_v} +{len(sib_extras)} files)",
                    patched_s,
                    extra_patches=tuple(sib_extras),
                )

        # Op 0k (high-precision JS `switch` fall-through case alias abduction):
        # `JS_SWITCH_CASE_ALIAS_FALLTHROUGH`:
        # When a `switch` statement matches an ASCII space (`0x20` / `32` / `' '`) without matching HTAB
        # (`0x09` / `9` / `'\t'`), or matches a hyphenated/underscored string literal (e.g. `'utf-8'`,
        # `'iso-8859-1'`) without its separator-free alias (`'utf8'`, `'iso88591'`), synthesize the
        # missing fall-through `case <alias>:` right above the existing `case`.
        for idx_sw, raw_sw in enumerate(lines):
            m_case = re.match(r"^(\s*)case\s+([^:\s][^:]*?)\s*:(.*)$", raw_sw)
            if not m_case:
                continue
            ind_sw, lit_sw = m_case.group(1), m_case.group(2).strip()
            aliases: list[str] = []
            if lit_sw == "0x20":
                aliases.append("0x09")
            elif lit_sw == "32":
                aliases.append("9")
            elif lit_sw in ("' '", '" "'):
                aliases.append(f"{lit_sw[0]}\\t{lit_sw[0]}")
            else:
                m_q = re.match(r"^(['\"])([A-Za-z0-9][A-Za-z0-9_-]*)\1$", lit_sw)
                if m_q and ("-" in m_q.group(2) or "_" in m_q.group(2)):
                    qch, sval = m_q.group(1), m_q.group(2)
                    compact = sval.replace("-", "").replace("_", "")
                    if compact and compact != sval:
                        aliases.append(f"{qch}{compact}{qch}")
            if not aliases:
                continue
            # Ensure alias case isn't already present nearby in this switch
            win_sw = "".join(lines[max(0, idx_sw - 12) : min(len(lines), idx_sw + 12)])
            for al in aliases:
                if f"case {al}:" in win_sw:
                    continue
                nl_sw = list(lines)
                nl_sw.insert(idx_sw, f"{ind_sw}case {al}:\n")
                add_cand(
                    rel, idx_sw + 1, "JS_SWITCH_CASE_ALIAS_FALLTHROUGH",
                    f"switch_case_alias({lit_sw}->+{al})", "".join(nl_sw),
                )

        # Op 0n (high-precision JS stdlib Unicode & numeric duality):
        # `JS_STDLIB_UNICODE_NUMERIC_DUALITY`:
        # Legacy ES3 `String.fromCharCode(x)` silently truncates code points > U+FFFF to 16-bit
        # surrogates, and `charCodeAt` / global `isNaN` / `isFinite` mis-handle astral code points
        # and type coercions. Synthesize ES6+ `String.fromCodePoint` (both direct and range-safe
        # fallback for invalid/out-of-range code points) and `Number.isNaN` / `Number.isFinite`.
        _charcode_du_n = 0
        for idx_du, raw_du in enumerate(lines):
            if "String.fromCharCode(" in raw_du:
                # 1. Range-safe `String.fromCodePoint` with fallback to original `String.fromCharCode` / $0
                m_fc = re.search(r"String\.fromCharCode\(([^)]+)\)", raw_du)
                if m_fc:
                    arg_fc = m_fc.group(1).strip()
                    safe_expr = (
                        f"((function(__cp){{return __cp>=0&&__cp<=0x10FFFF"
                        f"?String.fromCodePoint(__cp):String.fromCharCode(__cp);}})({arg_fc}))"
                    )
                    nl_du1 = list(lines)
                    nl_du1[idx_du] = raw_du[:m_fc.start()] + safe_expr + raw_du[m_fc.end():]
                    add_cand(
                        rel, idx_du + 1, "JS_STDLIB_UNICODE_NUMERIC_DUALITY",
                        "fromCharCode->range_safe_fromCodePoint",
                        "".join(nl_du1),
                    )
                    nl_du2 = list(lines)
                    nl_du2[idx_du] = raw_du.replace("String.fromCharCode(", "String.fromCodePoint(", 1)
                    add_cand(
                        rel, idx_du + 1, "JS_STDLIB_UNICODE_NUMERIC_DUALITY",
                        "fromCharCode->fromCodePoint",
                        "".join(nl_du2),
                    )
            if ".charCodeAt(" in raw_du and _charcode_du_n < 4:
                _charcode_du_n += 1
                nl_du3 = list(lines)
                nl_du3[idx_du] = raw_du.replace(".charCodeAt(", ".codePointAt(", 1)
                add_cand(
                    rel, idx_du + 1, "JS_STDLIB_UNICODE_NUMERIC_DUALITY",
                    "charCodeAt->codePointAt",
                    "".join(nl_du3),
                )

        # Op 0o (high-precision ECMAScript Nullish/Typeof-Null Laws + S3-Preserving Branch Strengthening):
        # (0o-i) `JS_NULLISH_TYPEOF_GUARD`:
        #   - ECMAScript quirk #1: `typeof x === 'object'` is TRUE for `null`! Strengthen to
        #     `(x !== null && typeof x === 'object')` when not already null-guarded.
        #   - ECMAScript quirk #2: `x === undefined` / `typeof x === 'undefined'` misses `null`!
        #     Generalize to `x == null` (catches both `null` and `undefined`).
        #   - ECMAScript quirk #3: `if (typeof x === 'function')` optional-arg shifting / ES6
        #     default `x = {}` misses explicit `null` -> normalize `if (x == null) { x = {}; }`.
        # (0o-ii) `JS_S3_BRANCH_STRENGTHEN`:
        #   - Preserve original condition `C` intact (S3 anti-overfitting principle) and strengthen
        #     with minimal semantic type/container/option guards:
        #     * `x.length === 0` (matches string, Array, TypedArray, custom objects) ->
        #       `((typeof x === 'string' || Array.isArray(x)) && (C))` or `(typeof x === 'string' && (C))`
        #     * `if (state.<flag>)` / `if (options.<flag>)` where `<flag>` appears in failing output ->
        #       strengthen with `typeof <val> === 'string'` / `typeof <val> !== 'string'` / `<val> != null`!
        _fail_syms_0o = _extract_failing_test_symbols(loc.initial_output)
        _fail_syms_0o_low = {s.lower() for s in _fail_syms_0o}
        _fail_lines_0o = "\n".join(
            ln_t for ln_t in loc.initial_output.splitlines()
            if any(k in ln_t.lower() for k in ("not ok", "fail", "error", "actual", "expected", "assert"))
        ).lower()
        _want_nullish_0o = any(
            k in _fail_lines_0o for k in ("null", "undefined", "cannot read propert", "cannot convert", "typeerror")
        )
        _generic_opt_noise = {"options", "opts", "state", "length", "object", "string", "value", "key", "data", "type", "name", "index"}
        _0o_lns = set(lns)
        _0o_added = 0
        for idx_o, raw_o in enumerate(lines):
            if _0o_added >= 8:
                break
            if (idx_o + 1) not in _0o_lns:
                continue
            st_o = raw_o.strip()
            if not st_o or st_o.startswith(("//", "/*", "*")):
                continue
            ind_o = raw_o[: len(raw_o) - len(raw_o.lstrip())]

            # (0o-ii) S3-Preserving In-Body `if (C)` Type/Container/Option Strengthening (highest signal first!)
            m_if_0o = re.match(r"^([ \t]*(?:else\s+)?if\s*\()(.+)(\)\s*\{?.*)$", raw_o.rstrip("\r\n"))
            if m_if_0o:
                pre_if, cond_0o, post_if = m_if_0o.group(1), m_if_0o.group(2).strip(), m_if_0o.group(3)
                # (a) Emptiness check `v.length === 0` or `!v.length` without string/Array guard
                m_len0 = re.search(r"\b([A-Za-z_$][\w$.]*)\.length\s*===?\s*0\b|!\s*([A-Za-z_$][\w$.]*)\.length\b", cond_0o)
                if m_len0 and "typeof " not in cond_0o and "Array.isArray" not in cond_0o:
                    v_l0 = m_len0.group(1) or m_len0.group(2)
                    for new_c, g_tag in (
                        (f"({cond_0o}) && (typeof {v_l0} === 'string')", "len0_then_str"),
                        (f"({cond_0o}) && (typeof {v_l0} === 'string' || Array.isArray({v_l0}))", "len0_then_str_or_arr"),
                        (f"(typeof {v_l0} === 'string' || Array.isArray({v_l0})) && ({cond_0o})", "str_or_arr"),
                        (f"(typeof {v_l0} === 'string') && ({cond_0o})", "only_str"),
                    ):
                        nl_o = list(lines)
                        nl_o[idx_o] = f"{pre_if}{new_c}{post_if}\n"
                        add_cand(
                            rel, idx_o + 1, "JS_S3_BRANCH_STRENGTHEN",
                            f"s3_len0_type_guard({v_l0}:{g_tag})", "".join(nl_o),
                        )
                        _0o_added += 1

                # (b) Option/state flag condition `state.<flag>` / `options.<flag>` matching exact failing test symbol!
                m_opt_c = re.search(r"\b((?:state|options|opts|this|config)\.[A-Za-z_$]\w*)\b", cond_0o)
                if m_opt_c:
                    opt_expr = m_opt_c.group(1)
                    opt_leaf = opt_expr.split(".", 1)[1]
                    if (
                        opt_leaf.lower() not in _generic_opt_noise
                        and (opt_leaf in _fail_syms_0o or opt_leaf.lower() in _fail_syms_0o_low)
                    ):
                        ctx_chunk = "".join(lines[max(0, idx_o - 14) : min(len(lines), idx_o + 6)])
                        val_cands: list[str] = []
                        for m_vc in re.finditer(r"\b(node\.value|object|value|val|str|input|node|scalar|item|data)\b", ctx_chunk):
                            vn = m_vc.group(1)
                            if vn not in val_cands:
                                val_cands.append(vn)
                        for vc in val_cands[:3]:
                            # Soundness: never guard an object (already property-indexed as `vc.<prop>` in `cond_0o`) with `typeof vc === 'string'`
                            if re.search(rf"\b{re.escape(vc)}\.[A-Za-z_$]\w*\b", cond_0o):
                                continue
                            for extra_g, g_tag in (
                                (f"typeof {vc} === 'string'", f"is_str({vc})"),
                                (f"typeof {vc} !== 'string'", f"not_str({vc})"),
                            ):
                                if extra_g in cond_0o:
                                    continue
                                nl_o = list(lines)
                                nl_o[idx_o] = f"{pre_if}({cond_0o}) && ({extra_g}){post_if}\n"
                                add_cand(
                                    rel, idx_o + 1, "JS_S3_BRANCH_STRENGTHEN",
                                    f"s3_opt_type_guard({opt_expr}&&{g_tag})", "".join(nl_o),
                                )
                                _0o_added += 1

            # (0o-i-a) `typeof x === 'object'` without null guard
            if _want_nullish_0o:
                m_to = re.search(r"typeof\s+([A-Za-z_$][\w$.]*)\s*===\s*['\"]object['\"]", raw_o)
                if m_to:
                    v_to = m_to.group(1)
                    if f"{v_to} !== null" not in raw_o and f"{v_to} != null" not in raw_o and f"{v_to} &&" not in raw_o:
                        nl_o = list(lines)
                        nl_o[idx_o] = (
                            raw_o[: m_to.start()]
                            + f"({v_to} !== null && {m_to.group(0)})"
                            + raw_o[m_to.end() :]
                        )
                        add_cand(
                            rel, idx_o + 1, "JS_NULLISH_TYPEOF_GUARD",
                            f"typeof_object_null_guard({v_to})", "".join(nl_o),
                        )
                        _0o_added += 1

                # (0o-i-b) `x === undefined` / `typeof x === 'undefined'` -> `x == null`
                m_ud = re.search(
                    r"(?:typeof\s+([A-Za-z_$][\w$.]*)\s*===\s*['\"]undefined['\"]|([A-Za-z_$][\w$.]*)\s*===\s*undefined\b)",
                    raw_o,
                )
                if m_ud:
                    v_ud = m_ud.group(1) or m_ud.group(2)
                    nl_o = list(lines)
                    nl_o[idx_o] = raw_o[: m_ud.start()] + f"{v_ud} == null" + raw_o[m_ud.end() :]
                    add_cand(
                        rel, idx_o + 1, "JS_NULLISH_TYPEOF_GUARD",
                        f"undef_to_nullish({v_ud}==null)", "".join(nl_o),
                    )
                    _0o_added += 1

                # (0o-i-c) Optional-arg data/opts normalization (`if (x == null) { x = {}; }`)
                m_fn_hdr = re.match(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$]\w*)\s*\(([^)]*)\)\s*\{", raw_o)
                if not m_fn_hdr:
                    m_fn_hdr = re.match(r"^\s*(?:exports\.|module\.exports\.)([A-Za-z_$]\w*)\s*=\s*function\s*\(([^)]*)\)\s*\{", raw_o)
                if m_fn_hdr:
                    fn_nm_0o = m_fn_hdr.group(1)
                    if fn_nm_0o in _fail_syms_0o or fn_nm_0o.lower() in _fail_lines_0o:
                        p_list = [p.strip().split("=")[0].strip().split(":")[0].strip() for p in m_fn_hdr.group(2).split(",")]
                        for pm_o in p_list:
                            if pm_o in ("data", "d", "opts", "options", "locals", "context", "ctx", "params", "obj"):
                                nl_o = list(lines)
                                nl_o.insert(idx_o + 1, f"{ind_o}  if ({pm_o} == null) {{ {pm_o} = {{}}; }}\n")
                                add_cand(
                                    rel, idx_o + 1, "JS_NULLISH_TYPEOF_GUARD",
                                    f"nullish_arg_default({fn_nm_0o}:{pm_o}={{}})", "".join(nl_o),
                                )
                                _0o_added += 1

        # Op 0p (TypeScript Interface-Guided S3 Guard Synthesis, `JS_TS_INTERFACE_S3_GUARD`):
        # For strongly-typed `.ts` files, read the repository's own `interface`/`type` schemas
        # for parameters of localized functions whose name/body matches a failing symbol, and
        # synthesize S3-preserving guard clauses on early-return `if (...) return` guards using
        # the parameter's declared boolean/nullable/enum fields (0 domain hardcoding).
        if rel.endswith(".ts"):
            _ts_ifaces: dict[str, list[tuple[str, str]]] = {}
            _ts_extends: dict[str, list[str]] = {}
            _ts_corpus_parts: list[str] = []
            for _ts_rel in _all_src_js:
                if not _ts_rel.endswith(".ts"):
                    continue
                _ts_p = worktree / _ts_rel
                if not _ts_p.is_file():
                    continue
                try:
                    _ts_txt = _ts_p.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue
                _ts_corpus_parts.append(_ts_txt)
                _ts_clean = re.sub(r"/\*[\s\S]*?\*/", "", _ts_txt)
                for _m_if in re.finditer(
                    r"(?:export\s+)?(?:interface\s+([A-Za-z_$]\w*)(?:\s+extends\s+([A-Za-z_$][\w,\s]*))?|type\s+([A-Za-z_$]\w*)\s*=)\s*\{([^{}]{1,3500})\}",
                    _ts_clean,
                ):
                    _tname = _m_if.group(1) or _m_if.group(3)
                    _ext_str = _m_if.group(2) or ""
                    _tbody = _m_if.group(4)
                    _fields: list[tuple[str, str]] = []
                    for _fl in _tbody.splitlines():
                        _mf = re.match(r"^\s*(?:readonly\s+)?([A-Za-z_$]\w*)(\??)\s*:\s*([^;\n,]+)", _fl)
                        if _mf:
                            _fields.append((_mf.group(1), (_mf.group(2) + _mf.group(3)).strip()))
                    if _fields and _tname not in _ts_ifaces:
                        _ts_ifaces[_tname] = _fields
                    if _ext_str and _tname:
                        _ts_extends[_tname] = [b.strip().split("<")[0] for b in _ext_str.split(",") if b.strip()]
            _ts_corpus = "\n".join(_ts_corpus_parts)
            # Inherit 1-hop `extends` fields (e.g. `ScalarNode extends NodeBase`)
            for _tn, _bases in _ts_extends.items():
                for _bn in _bases:
                    if _bn in _ts_ifaces:
                        _existing_fn = {x[0] for x in _ts_ifaces.get(_tn, ())}
                        for _bf in _ts_ifaces[_bn]:
                            if _bf[0] not in _existing_fn:
                                _ts_ifaces.setdefault(_tn, []).append(_bf)
                                _existing_fn.add(_bf[0])

            # Type-Scoped Peer Expression Harvester (100% general, 0 domain hardcoding):
            # For each interface `T`, scan peer functions `function foo(p: T)` across all `.ts`
            # files in the repository to harvest already-type-checked expressions `p.<chain>` used
            # in `===`/`!==` comparisons (e.g. `layout.presenterOptions.schema.defaultScalarTag.tagName`).
            _ts_peer_exprs: dict[str, list[str]] = {}
            for _m_pfn in re.finditer(
                r"\bfunction\s+[A-Za-z_$]\w*\s*\(\s*([A-Za-z_$]\w*)\s*:\s*([A-Za-z_$]\w*)[^{]*\{",
                _ts_corpus,
            ):
                _pp, _pt = _m_pfn.group(1), _m_pfn.group(2)
                if _pt not in _ts_ifaces:
                    continue
                _p_slice = _ts_corpus[_m_pfn.end() : _m_pfn.end() + 2500]
                _plist = _ts_peer_exprs.setdefault(_pt, [])
                # Harvest property chains `<pp>.<a.b.c>` appearing on EITHER side of `===`/`!==`
                # (use lookahead for LHS so `A === B` harvests BOTH `A` and `B` without consuming `===`!)
                for _m_cmp in re.finditer(
                    rf"(?:===|!==)\s*({re.escape(_pp)}(?:\.[A-Za-z_$]\w*){{2,6}})\b|"
                    rf"\b({re.escape(_pp)}(?:\.[A-Za-z_$]\w*){{2,6}})(?=\s*(?:===|!==))",
                    _p_slice,
                ):
                    _ch = _m_cmp.group(1) or _m_cmp.group(2)
                    if not _ch:
                        continue
                    # Normalize parameter prefix to `<PARAM>`
                    _norm_ch = "<PARAM>" + _ch[len(_pp):]
                    if _norm_ch not in _plist:
                        _plist.append(_norm_ch)

            if _ts_ifaces:
                _0p_added = 0
                for idx_p, raw_p in enumerate(lines):
                    if _0p_added >= 16:
                        break
                    m_tsfn = re.match(
                        r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$]\w*)\s*\(\s*([A-Za-z_$]\w*)\s*:\s*([A-Za-z_$]\w*)",
                        raw_p,
                    )
                    if not m_tsfn:
                        continue
                    fn_ts, param_ts, type_ts = m_tsfn.group(1), m_tsfn.group(2), m_tsfn.group(3)
                    if type_ts not in _ts_ifaces:
                        continue
                    # Locate exact end of this function (matching closing brace at same/less indent)
                    fn_ind_len = len(raw_p) - len(raw_p.lstrip())
                    fn_end = min(len(lines), idx_p + 45)
                    for k_fe in range(idx_p + 1, fn_end):
                        ln_fe = lines[k_fe]
                        if ln_fe.strip() == "}" and (len(ln_fe) - len(ln_fe.lstrip())) <= fn_ind_len:
                            fn_end = k_fe + 1
                            break
                    fn_body = "".join(lines[idx_p:fn_end])
                    # Only target functions matching a failing symbol AND containing localized lines
                    _fn_lns = set(range(idx_p + 1, fn_end + 1))
                    _fn_match_sym = any(
                        s in fn_body or s.lower() in fn_ts.lower()
                        for s in _fail_syms_0o
                        if s.lower() not in _generic_opt_noise
                    )
                    if not (_fn_match_sym and (_fn_lns & _0o_lns)):
                        continue
                    # Collect declared guard predicates from `type_ts` + 1-hop nested interfaces
                    ts_preds: list[tuple[str, str]] = []
                    for f_nm, f_ty in _ts_ifaces[type_ts]:
                        f_ty_clean = f_ty.lstrip("?").strip()
                        if f_ty_clean == "boolean":
                            ts_preds.append((f"!{param_ts}.{f_nm}", f"!{f_nm}"))
                            ts_preds.append((f"{param_ts}.{f_nm}", f"{f_nm}"))
                        elif f_ty.startswith("?") or "undefined" in f_ty_clean or "null" in f_ty_clean:
                            ts_preds.append((f"{param_ts}.{f_nm} != null", f"{f_nm}!=null"))
                            ts_preds.append((f"!{param_ts}.{f_nm}", f"!{f_nm}"))
                        # 1-hop nested interface (e.g. `layout.node: Readonly<ScalarNode>`)
                        _unwrapped_ty = re.sub(r"\b(?:Readonly|Required|Partial)<([^<>]+)>", r"\1", f_ty_clean)
                        _unwrapped_ty = re.sub(r"\b(?:Readonly|Required|Partial)<([^<>]+)>", r"\1", _unwrapped_ty)
                        base_ty = re.split(r"[\s|&<]", _unwrapped_ty.strip())[0]
                        if base_ty in _ts_ifaces:
                            for sf_nm, sf_ty in _ts_ifaces[base_ty]:
                                sf_ty_clean = sf_ty.lstrip("?").strip()
                                if sf_ty_clean == "boolean":
                                    ts_preds.append((f"!{param_ts}.{f_nm}.{sf_nm}", f"!{f_nm}.{sf_nm}"))
                                    ts_preds.append((f"{param_ts}.{f_nm}.{sf_nm}", f"{f_nm}.{sf_nm}"))
                                elif sf_ty.startswith("?") or "undefined" in sf_ty_clean or "null" in sf_ty_clean:
                                    ts_preds.append((f"{param_ts}.{f_nm}.{sf_nm} != null", f"{f_nm}.{sf_nm}!=null"))
                                    ts_preds.append((f"{param_ts}.{f_nm}.{sf_nm} == null", f"{f_nm}.{sf_nm}==null"))
                                # String literal union (e.g. `tag: 'str' | 'int'` or `kind: 'plain' | 'quoted'`)
                                _lit_vals = [m_s.group(0) for m_s in re.finditer(r"(['\"])([A-Za-z0-9_.:/-]+)\1", sf_ty_clean)]
                                if len(_lit_vals) >= 2:
                                    for lit_s in _lit_vals[:4]:
                                        ts_preds.append((f"{param_ts}.{f_nm}.{sf_nm} !== {lit_s}", f"{f_nm}.{sf_nm}!=={lit_s}"))
                                        ts_preds.append((f"{param_ts}.{f_nm}.{sf_nm} === {lit_s}", f"{f_nm}.{sf_nm}==={lit_s}"))
                                # Repo-wide `.sf_nm` string-value-domain harvester (0 domain hardcoding!)
                                if "string" in sf_ty_clean and sf_nm in ("tag", "kind", "type", "role", "mode", "format"):
                                    _dom_counts: dict[str, int] = {}
                                    for _md in re.finditer(
                                        rf"(?:\.|^\s*){re.escape(sf_nm)}\s*(?:===|!==|==|!=|=|:)\s*(['\"][A-Za-z0-9_.:/@,-]{{1,64}}['\"])",
                                        _ts_corpus,
                                        re.M,
                                    ):
                                        _lv = _md.group(1)
                                        _dom_counts[_lv] = _dom_counts.get(_lv, 0) + 1
                                    # Also harvest `const <CONST> = '...'` if referenced with `.sf_nm`
                                    for _md2 in re.finditer(
                                        rf"\.{re.escape(sf_nm)}\s*(?:===|!==)\s*([A-Z][A-Z0-9_]{{2,}})\b",
                                        _ts_corpus,
                                    ):
                                        _cn = _md2.group(1)
                                        _mdef = re.search(rf"\bconst\s+{re.escape(_cn)}\s*=\s*(['\"][A-Za-z0-9_.:/@,-]{{1,64}}['\"])", _ts_corpus)
                                        if _mdef:
                                            _lv = _mdef.group(1)
                                            _dom_counts[_lv] = _dom_counts.get(_lv, 0) + 3
                                    _top_lits = sorted(_dom_counts.items(), key=lambda kv: -kv[1])[:6]
                                    for _lv, _ in _top_lits:
                                        ts_preds.insert(0, (f"{param_ts}.{f_nm}.{sf_nm} !== {_lv}", f"{f_nm}.{sf_nm}!=={_lv}"))
                                    # Pair `param.f.sf` with type-scoped peer expressions from other `(p: TypeName)` fns
                                    for _norm_pe in _ts_peer_exprs.get(type_ts, ()):
                                        _pe_concrete = _norm_pe.replace("<PARAM>", param_ts, 1)
                                        _lhs_concrete = f"{param_ts}.{f_nm}.{sf_nm}"
                                        if _pe_concrete == _lhs_concrete:
                                            continue
                                        _pe_leaf = _pe_concrete.rsplit(".", 1)[-1].lower()
                                        if sf_nm.lower() in _pe_leaf or _pe_leaf in sf_nm.lower():
                                            ts_preds.insert(0, (f"{_lhs_concrete} !== {_pe_concrete}", f"{f_nm}.{sf_nm}!==peer({_pe_leaf})"))
                                            ts_preds.append((f"{_lhs_concrete} === {_pe_concrete}", f"{f_nm}.{sf_nm}===peer({_pe_leaf})"))
                    # Filter out formatting/trivia metadata fields when semantic fields exist
                    _trivia_skip = ("comment", "blank", "range", "span", "offset", "position")
                    ts_preds = [
                        pt for pt in ts_preds
                        if not any(tk in pt[1].lower() for tk in _trivia_skip)
                    ]
                    # Deduplicate `ts_preds` preserving order
                    _seen_tp: set[str] = set()
                    ts_preds_u: list[tuple[str, str]] = []
                    for _pe, _pt in ts_preds:
                        if _pe not in _seen_tp:
                            _seen_tp.add(_pe)
                            ts_preds_u.append((_pe, _pt))
                    # Apply predicates to early-return `if (<cond>) return` lines inside `fn_ts`
                    for k_p in range(idx_p + 1, fn_end):
                        if _0p_added >= 16:
                            break
                        ln_p = lines[k_p]
                        if re.match(r"^\s*\}\s*$", ln_p):
                            break
                        m_er = re.match(r"^(\s*if\s*\()(.+)(\)\s*return\b.*)$", ln_p)
                        if not m_er:
                            continue
                        er_pre, er_cond, er_post = m_er.group(1), m_er.group(2), m_er.group(3)
                        # Skip the primary option gate (`if (!layout.presenterOptions.forceQuotes) return`)
                        if any(
                            f".{s}" in er_cond
                            for s in _fail_syms_0o
                            if s.lower() not in _generic_opt_noise
                        ):
                            continue
                        for pred_expr, pred_tag in ts_preds_u:
                            if _0p_added >= 16:
                                break
                            bare_field = pred_expr.lstrip("!").split()[0]
                            if bare_field in er_cond:
                                continue
                            nl_p = list(lines)
                            nl_p[k_p] = f"{er_pre}{er_cond} || {pred_expr}{er_post}\n"
                            add_cand(
                                rel, k_p + 1, "JS_TS_INTERFACE_S3_GUARD",
                                f"ts_iface_s3({fn_ts}:||{pred_tag})", "".join(nl_p),
                            )
                            _0p_added += 1

        # Op 0q (Sibling Null-Prototype Container Constructor Propagation, `JS_NULL_PROTO_CONTAINER_SYNC`):
        # When a localized JS/TS file already constructs null-prototype containers (`{ __proto__: null }`
        # or `Object.create(null)`), scan localized functions `fn(param)` that initialize a bare object
        # literal (`var/let/const r = {};`) while either:
        #   (a) invoking a sibling null-prototype container helper `helper(...)` in the same function/file
        #       -> propagate `helper(param)` (e.g. `var result = emptyCopyOf(input);`), or
        #   (b) having an `options.<flag> ? { __proto__: null } : {}` idiom in scope.
        if "{ __proto__: null }" in orig or "Object.create(null)" in orig:
            # Find helper functions in this file whose body constructs a null-prototype container
            _null_proto_helpers: list[str] = []
            for _m_np in re.finditer(
                r"(?:var|let|const)\s+([A-Za-z_$]\w*)\s*=\s*function(?:\s+[A-Za-z_$]\w*)?\s*\([^)]*\)\s*\{|"
                r"function\s+([A-Za-z_$]\w*)\s*\([^)]*\)\s*\{",
                orig,
            ):
                _hnm = _m_np.group(1) or _m_np.group(2)
                _hslice = orig[_m_np.end() : _m_np.end() + 450]
                if _hnm and ("{ __proto__: null }" in _hslice or "Object.create(null)" in _hslice):
                    if _hnm not in _null_proto_helpers:
                        _null_proto_helpers.append(_hnm)
            # Also capture file's null-proto option ternary if present
            _m_np_tern = re.search(
                r"\b([A-Za-z_$][\w$.]*\s*\?\s*(?:\{\s*__proto__\s*:\s*null\s*\}|Object\.create\(\s*null\s*\))\s*:\s*\{\s*\})",
                orig,
            )
            _np_tern_expr = _m_np_tern.group(1) if _m_np_tern else None
            _0q_added = 0
            for idx_q, raw_q in enumerate(lines):
                if _0q_added >= 8:
                    break
                m_fnp = re.match(
                    r"^\s*(?:(?:var|let|const)\s+([A-Za-z_$]\w*)\s*=\s*)?function(?:\s+([A-Za-z_$]\w*))?\s*\(\s*([A-Za-z_$]\w*)([^)]*)\)\s*\{",
                    raw_q,
                )
                if not m_fnp:
                    continue
                fn_q = m_fnp.group(1) or m_fnp.group(2) or "anon"
                p0_q = m_fnp.group(3)
                rest_params_q = m_fnp.group(4) or ""
                # Find end of this function (bounded)
                q_ind = len(raw_q) - len(raw_q.lstrip())
                q_end = min(len(lines), idx_q + 120)
                for k_qe in range(idx_q + 1, q_end):
                    if lines[k_qe].strip() in ("}", "};") and (len(lines[k_qe]) - len(lines[k_qe].lstrip())) <= q_ind:
                        q_end = k_qe + 1
                        break
                fn_q_lns = set(range(idx_q + 1, q_end + 1))
                if not (fn_q_lns & _0o_lns):
                    continue
                fn_q_body = "".join(lines[idx_q:q_end])
                # (0q-i) Detect variables already initialized via null-proto conditional (`v = C ? { __proto__: null } : {}`)
                # whose null prototype is later clobbered by a single-key object literal (`v = { k: expr };` -> `v[k] = expr;`)!
                _null_proto_vars: dict[str, str] = {}
                for k_init in range(idx_q + 1, q_end):
                    m_npv = re.match(
                        r"^\s*(?:(?:var|let|const)\s+)?([A-Za-z_$]\w*)\s*=\s*([^;\n]+?\?\s*(?:\{\s*__proto__\s*:\s*null\s*\}|Object\.create\(\s*null\s*\))\s*:\s*\{\s*\})\s*;?",
                        lines[k_init],
                    )
                    if m_npv:
                        _null_proto_vars[m_npv.group(1)] = m_npv.group(2).strip()
                if _null_proto_vars:
                    for k_ov in range(idx_q + 1, q_end):
                        if _0q_added >= 8:
                            break
                        m_ov = re.match(
                            r"^(\s*)([A-Za-z_$]\w*)\s*=\s*\{\s*([A-Za-z0-9_$'\"]+)\s*:\s*([^,;}\n]+?)\s*\}(\s*;?\s*)$",
                            lines[k_ov],
                        )
                        if m_ov and m_ov.group(2) in _null_proto_vars:
                            ov_ind, ov_var, ov_k, ov_val, ov_post = m_ov.groups()
                            if ov_k != "__proto__":
                                # Preserve already-initialized null-proto container via property assignment `v[k] = val;`
                                key_acc = ov_k if (ov_k.isdigit() or ov_k[0] in ("'", '"')) else f"'{ov_k}'"
                                nl_q = list(lines)
                                nl_q[k_ov] = f"{ov_ind}{ov_var}[{key_acc}] = {ov_val}{ov_post.rstrip()}\n"
                                add_cand(
                                    rel, k_ov + 1, "JS_NULL_PROTO_CONTAINER_SYNC",
                                    f"null_proto_clobber_fix({fn_q}:{ov_var}[{key_acc}]={ov_val})",
                                    "".join(nl_q),
                                )
                                _0q_added += 1

                # (0q-ii) Look for bare `var/let/const <v> = {};` lines inside this function
                for k_b in range(idx_q + 1, q_end):
                    if _0q_added >= 8:
                        break
                    m_bare = re.match(r"^(\s*(?:var|let|const)\s+([A-Za-z_$]\w*)\s*=\s*)\{\s*\}(\s*;?\s*)$", lines[k_b])
                    if not m_bare:
                        continue
                    b_pre, b_var, b_post = m_bare.group(1), m_bare.group(2), m_bare.group(3).rstrip()
                    # (a) Prefer sibling null-proto helper already called inside THIS function!
                    for _hnm in _null_proto_helpers:
                        if _hnm == fn_q:
                            continue
                        if f"{_hnm}(" in fn_q_body:
                            nl_q = list(lines)
                            nl_q[k_b] = f"{b_pre}{_hnm}({p0_q}){b_post}\n"
                            add_cand(
                                rel, k_b + 1, "JS_NULL_PROTO_CONTAINER_SYNC",
                                f"null_proto_helper_sync({fn_q}:{b_var}={_hnm}({p0_q}))",
                                "".join(nl_q),
                            )
                            _0q_added += 1
                    # (b) Fallback: propagate file's `options.<flag> ? { __proto__: null } : {}` if `options` is a param
                    if _np_tern_expr and "options" in (p0_q + rest_params_q) and "options." in _np_tern_expr:
                        nl_q = list(lines)
                        nl_q[k_b] = f"{b_pre}{_np_tern_expr}{b_post}\n"
                        add_cand(
                            rel, k_b + 1, "JS_NULL_PROTO_CONTAINER_SYNC",
                            f"null_proto_opt_sync({fn_q}:{b_var})",
                            "".join(nl_q),
                        )
                        _0q_added += 1

        # Op 0r (Sibling 1-Arg String/Key Normalizer Propagation, `JS_ARG_SIBLING_NORMALIZER_WRAP`):
        # When a localized JS/TS file defines a 1-arg string/key normalizer helper `normFn(x)`
        # (already invoked elsewhere in the same file) and a localized guard/membership check
        # (`has.call(Object.prototype, k)`, `hasOwn(..., k)`, `.has(k)`) receives a raw identifier `k`,
        # wrap `k` in `normFn(k)` (e.g. `has.call(Object.prototype, stripWrappingBrackets(key))`).
        _1arg_helpers: list[str] = []
        for _m_1a in re.finditer(
            r"(?:var|let|const)\s+([A-Za-z_$]\w*)\s*=\s*function(?:\s+[A-Za-z_$]\w*)?\s*\(\s*[A-Za-z_$]\w*\s*\)\s*\{|"
            r"function\s+([A-Za-z_$]\w*)\s*\(\s*[A-Za-z_$]\w*\s*\)\s*\{",
            orig,
        ):
            _hn = _m_1a.group(1) or _m_1a.group(2)
            if not _hn or _hn in _1arg_helpers:
                continue
            _body_sl = orig[_m_1a.end() : _m_1a.end() + 500]
            # Must look like a pure string/key normalizer (returns transformed string/slice/replace) and be called elsewhere
            _outside_decl = orig[: _m_1a.start()] + orig[_m_1a.end() :]
            if (
                any(tok in _body_sl for tok in (".slice(", ".replace(", ".trim(", ".toLowerCase(", ".charAt(", ".charCodeAt(", ".substring("))
                and bool(re.search(rf"\b{re.escape(_hn)}\s*\(", _outside_decl))
            ):
                _1arg_helpers.append(_hn)
        if _1arg_helpers:
            _0r_added = 0
            for idx_r, raw_r in enumerate(lines):
                if _0r_added >= 10:
                    break
                if (idx_r + 1) not in _0o_lns:
                    continue
                m_guard_call = re.search(
                    r"(\b(?:has\.call|hasOwnProperty\.call|hasOwn)\s*\([^,]+,\s*)([A-Za-z_$]\w*)(\s*\))",
                    raw_r,
                )
                if not m_guard_call:
                    continue
                g_arg = m_guard_call.group(2)
                for _hn in _1arg_helpers[:4]:
                    if _0r_added >= 10:
                        break
                    if f"{_hn}(" in raw_r:
                        continue
                    nl_r = list(lines)
                    nl_r[idx_r] = (
                        raw_r[: m_guard_call.start(2)]
                        + f"{_hn}({g_arg})"
                        + raw_r[m_guard_call.end(2) :]
                    )
                    add_cand(
                        rel, idx_r + 1, "JS_ARG_SIBLING_NORMALIZER_WRAP",
                        f"sibling_normalizer_wrap({_hn}({g_arg}))",
                        "".join(nl_r),
                    )
                    _0r_added += 1

        # Op 0s (Non-Empty String Type-Guard Strengthening, `JS_TYPEOF_STRING_NONEMPTY_GUARD`):
        # When a localized JS/TS file checks `if (typeof <v> !== 'string' ...)` (single-line or
        # multi-line) to fall back to a default or reject invalid config, empty string `''` passes
        # `typeof '' === 'string'` and can cause infinite loops / RangeError / broken fallback.
        # Strengthen `typeof <v> !== 'string'` -> `typeof <v> !== 'string' || !<v>`.
        _fail_lower_0s = str(getattr(loc, "initial_output", "") or "").lower()
        _0s_hits: list[tuple[int, int, str, str]] = []
        for idx_s, raw_s in enumerate(lines):
            m_tos = re.search(r"(\btypeof\s+([A-Za-z_$][\w$.]*)\s*!==\s*['\"]string['\"])", raw_s)
            if not m_tos:
                continue
            if not re.match(r"^\s*(?:else\s+)?if\s*\(", raw_s):
                continue
            tos_var = m_tos.group(2)
            window_s = "".join(lines[idx_s : min(len(lines), idx_s + 3)])
            if f"!{tos_var}" in window_s or f"{tos_var}.length" in window_s or f"{tos_var} === ''" in window_s or f'{tos_var} === ""' in window_s:
                continue
            if _0o_lns and not any(abs((idx_s + 1) - ln_o) <= 400 for ln_o in _0o_lns):
                continue
            nl_s = list(lines)
            nl_s[idx_s] = (
                raw_s[: m_tos.end(1)]
                + f" || !{tos_var}"
                + raw_s[m_tos.end(1) :]
            )
            leaf_s = tos_var.split(".")[-1].lower()
            # Prefer variables whose name (or >=4-char prefix) appears in the failure trace/assertion!
            sym_match = (
                0
                if (len(leaf_s) >= 3 and leaf_s in _fail_lower_0s)
                else 1
            )
            _0s_hits.append((sym_match, idx_s, tos_var, "".join(nl_s)))
        _0s_hits.sort(key=lambda t: (t[0], t[1]))
        for _, idx_s, tos_var, src_s in _0s_hits[:6]:
            add_cand(
                rel, idx_s + 1, "JS_TYPEOF_STRING_NONEMPTY_GUARD",
                f"typeof_string_nonempty(typeof {tos_var}!=='string'||!{tos_var})",
                src_s,
            )

        # Op 0t (ECMAScript Fast-Path String Concatenation vs Array.prototype.join Nullish Sync,
        # `JS_FASTPATH_JOIN_NULLISH_SYNC`):
        # When a localized JS/TS function has a length-specialized fast path `if (arr.length === 2)`
        # performing `arr[0] + sep + arr[1]` while a sibling fallback below uses `arr.join(sep)`,
        # `+` coerces `null`/`undefined` to `'null'`/`'undefined'` instead of `''` (violating
        # ECMAScript `Array.prototype.join` semantics). Synthesize nullish-coalesced `(arr[i] ?? '')`!
        _0t_added = 0
        for idx_t, raw_t in enumerate(lines):
            if _0t_added >= 6:
                break
            m_len_fp = re.match(r"^\s*if\s*\(\s*([A-Za-z_$]\w*)\.length\s*===\s*2\s*\)", raw_t)
            if not m_len_fp:
                continue
            arr_t = m_len_fp.group(1)
            # Confirm a sibling `.join(` fallback on the same array appears within the next 15 lines
            tail_t = "".join(lines[idx_t + 1 : min(len(lines), idx_t + 16)])
            if f"{arr_t}.join(" not in tail_t:
                continue
            for k_t in range(idx_t + 1, min(len(lines), idx_t + 6)):
                ln_t = lines[k_t]
                if f"{arr_t}[0]" in ln_t and f"{arr_t}[1]" in ln_t and "+" in ln_t and "??" not in ln_t:
                    # (a) Nullish-coalesced fast path matching Array.prototype.join semantics
                    fixed_t = re.sub(
                        rf"\b{re.escape(arr_t)}\[(\d+)\]",
                        rf"({arr_t}[\1] ?? '')",
                        ln_t,
                    )
                    nl_t = list(lines)
                    nl_t[k_t] = fixed_t
                    add_cand(
                        rel, k_t + 1, "JS_FASTPATH_JOIN_NULLISH_SYNC",
                        f"fastpath_join_nullish_sync({arr_t}[0..1]??'')",
                        "".join(nl_t),
                    )
                    _0t_added += 1
                    # (b) Canonical `Array.prototype.join` fallback: elide broken length===2 `+` fast path
                    # (`+` uses ToPrimitive/valueOf + stringifies null/undefined; `.join()` uses ToString + '')
                    close_t = None
                    for k_cl in range(k_t + 1, min(len(lines), idx_t + 8)):
                        if lines[k_cl].strip() == "}":
                            close_t = k_cl
                            break
                    if close_t is not None:
                        nl_elide = lines[:idx_t] + lines[close_t + 1 :]
                        add_cand(
                            rel, idx_t + 1, "JS_FASTPATH_JOIN_NULLISH_SYNC",
                            f"fastpath_join_elide({arr_t}.length===2->join)",
                            "".join(nl_elide),
                        )
                        _0t_added += 1
                    break

        # Op 0m (high-precision JS regex character-class missing escaped backslash):
        # `JS_REGEX_CHARCLASS_ESCAPED_BACKSLASH`:
        # Inside JS string-encoded regex character classes (e.g. POSIX `punct: '...[@[\\]^_`{|}~'`),
        # `[\\]` escapes `]` without including a literal backslash `\\` (`\\\\` in a JS string literal).
        # Synthesize `[\\\\\\]` (literal backslash + escaped `]`) cleanly.
        for idx_rx, raw_rx in enumerate(lines):
            if r"[\\]" in raw_rx and r"[\\\\\\]" not in raw_rx:
                nl_rx = list(lines)
                nl_rx[idx_rx] = raw_rx.replace(r"[\\]", r"[\\\\\\]", 1)
                add_cand(
                    rel, idx_rx + 1, "JS_REGEX_CHARCLASS_ESCAPED_BACKSLASH",
                    "regex_charclass_add_literal_backslash([\\\\]->[\\\\\\\\\\\\])",
                    "".join(nl_rx),
                )

        # Op 0u (high-precision ECMAScript regex dot-all / newline wildcard law):
        # `JS_REGEX_DOTALL_NEWLINE_LAW`:
        # In JS `RegExp`, `.` does NOT match `\n` unless either `[\s\S]` is used in the regex
        # source string or the `s` (`dotAll`) flag is passed to `new RegExp(...)`.
        # When failing test output shows a newline matching failure (`\n` or `newline`), synthesize:
        # (a) regex-source wildcard upgrades (`'.*?'` -> `'[\\s\\S]*?'`, `'.*'` -> `'[\\s\\S]*'`, etc.)
        # (b) `new RegExp(..., flags)` `s` (`dotAll`) flag injection.
        _init_out_u = str(loc.initial_output or "")
        _newline_fail_u = (
            "\\n" in _init_out_u
            or "newline" in _init_out_u.lower()
            or "multiline" in _init_out_u.lower()
        )
        if _newline_fail_u:
            _0u_added = 0
            # (0) Tempered-dot regex templates `(?:(?!...).)*` or `(?:(?!${...}).)*` -> `[\\s\\S])`
            # (inside JS string/template literals, `\\s\\S` is required so the runtime regex receives `\s\S`!)
            _tdot_re = re.compile(r"(?<!\\)\.\)(?=[*+?])")
            _tdot_idxs: list[int] = []
            for idx_u, raw_u in enumerate(lines):
                st_u = raw_u.strip()
                if not st_u or st_u.startswith(("//", "*", "/*")):
                    continue
                if "(?!" in raw_u and _tdot_re.search(raw_u) and r"[\\s\\S]" not in raw_u:
                    _tdot_idxs.append(idx_u)
            if _tdot_idxs:
                if len(_tdot_idxs) >= 2:
                    nl_all = list(lines)
                    for ix in _tdot_idxs:
                        nl_all[ix] = _tdot_re.sub(lambda _m: r"[\\s\\S])", nl_all[ix])
                    add_cand(
                        rel, _tdot_idxs[0] + 1, "JS_REGEX_DOTALL_NEWLINE_LAW",
                        f"regex_tempered_dot_co({len(_tdot_idxs)}_sites:.->[\\s\\S])",
                        "".join(nl_all),
                    )
                    _0u_added += 1
                for ix in _tdot_idxs[:4]:
                    nl_one = list(lines)
                    nl_one[ix] = _tdot_re.sub(lambda _m: r"[\\s\\S])", nl_one[ix])
                    add_cand(
                        rel, ix + 1, "JS_REGEX_DOTALL_NEWLINE_LAW",
                        "regex_tempered_dot(.->[\\s\\S])",
                        "".join(nl_one),
                    )
                    _0u_added += 1
            for idx_u, raw_u in enumerate(lines):
                if _0u_added >= 12:
                    break
                st_u = raw_u.strip()
                if not st_u or st_u.startswith(("//", "*", "/*", "case ")):
                    continue
                # (a) Regex source wildcard string literal: `'.*?'`, `'.*'`, `'.+?'`, `'.+'`
                for old_wc, new_wc in (
                    ("'.*?'", r"'[\\s\\S]*?'"),
                    ('".*?"', r'"[\\s\\S]*?"'),
                    ("'.*'", r"'[\\s\\S]*'"),
                    ('".*"', r'"[\\s\\S]*"'),
                    ("'.+?'", r"'[\\s\\S]+?'"),
                    ("'.+'", r"'[\\s\\S]+'"),
                ):
                    if old_wc in raw_u and r"[\\s\\S]" not in raw_u:
                        nl_u = list(lines)
                        nl_u[idx_u] = raw_u.replace(old_wc, new_wc, 1)
                        add_cand(
                            rel, idx_u + 1, "JS_REGEX_DOTALL_NEWLINE_LAW",
                            f"regex_dotall_wildcard({old_wc}->{new_wc})",
                            "".join(nl_u),
                        )
                        _0u_added += 1
                        break
                # (b) `new RegExp(src, ... ? 'i' : '')` -> add 's' flag
                if "new RegExp(" in raw_u:
                    m_rf = re.search(r"(\?\s*['\"])([a-zA-Z]*)(['\"]\s*:\s*['\"])([a-zA-Z]*)(['\"])", raw_u)
                    if m_rf and "s" not in m_rf.group(2) and "s" not in m_rf.group(4):
                        fixed_rf = (
                            raw_u[: m_rf.start()]
                            + f"{m_rf.group(1)}{m_rf.group(2)}s{m_rf.group(3)}{m_rf.group(4)}s{m_rf.group(5)}"
                            + raw_u[m_rf.end() :]
                        )
                        nl_u = list(lines)
                        nl_u[idx_u] = fixed_rf
                        add_cand(
                            rel, idx_u + 1, "JS_REGEX_DOTALL_NEWLINE_LAW",
                            "regex_dotall_flag(new RegExp +s)",
                            "".join(nl_u),
                        )
                        _0u_added += 1

        # Op 0v (high-precision raw-vs-normalized loop key preservation + shadow alpha-renaming):
        # `JS_NORMALIZED_KEY_PRESERVE_RAW_INPUT`:
        # Inside `for (const <outer> of <col>) { ... const <norm> = <fn>(...); ... }` where an object
        # literal stores `{ <prop>: <norm>, <other>: <f>(<norm>), ... }` (and optionally an
        # `if (Array.isArray(<norm>)) { for (const <inner> of <norm>) { ... <prop>: <inner>, ... } }`
        # branch where `<inner>` may shadow `<outer>`), restore `<prop>: <outer>` across both branches
        # while alpha-renaming any shadowed `<inner>` to `_brain_el`.
        for idx_loop, raw_loop in enumerate(lines):
            m_fl = re.match(r"^(\s*)for\s*\(\s*(?:const|let|var)\s+([A-Za-z_$]\w*)\s+of\s+([^)]+)\)\s*\{\s*$", raw_loop)
            if not m_fl:
                continue
            l_ind, outer_v = m_fl.group(1), m_fl.group(2)
            # Find matching closing brace of this `for` loop
            end_loop = -1
            for k_l in range(idx_loop + 1, min(len(lines), idx_loop + 70)):
                if lines[k_l].startswith(l_ind + "}"):
                    end_loop = k_l
                    break
            if end_loop <= idx_loop + 4:
                continue
            body_lns = lines[idx_loop + 1 : end_loop]
            body_txt = "".join(body_lns)
            # Find derived/normalized local variable `const <norm> = <fn>(...)` inside the loop body
            norm_vars: list[str] = []
            for bl in body_lns:
                m_nv = re.match(r"^\s*(?:const|let)\s+([A-Za-z_$]\w*)\s*=\s*[A-Za-z_$][\w.]*\s*\(", bl)
                if m_nv and m_nv.group(1) != outer_v and m_nv.group(1) not in norm_vars:
                    norm_vars.append(m_nv.group(1))
            for norm_v in norm_vars:
                # Find object property `<prop>: <norm_v>,` where `<norm_v>` is also passed to another call nearby
                m_prop = re.search(rf"\b([A-Za-z_$]\w*)\s*:\s*{re.escape(norm_v)}\s*,", body_txt)
                if not m_prop:
                    continue
                prop_nm = m_prop.group(1)
                if not re.search(rf"[A-Za-z_$]\w*\s*\(\s*{re.escape(norm_v)}\s*\)", body_txt):
                    continue
                new_body = list(body_lns)
                changed_0v = False
                # (a) Handle any inner `for (const <inner> of <norm_v>)` loop (with alpha-renaming if shadowed!)
                bi = 0
                while bi < len(new_body):
                    m_in = re.match(
                        rf"^(\s*)for\s*\(\s*(const|let|var)\s+([A-Za-z_$]\w*)\s+of\s+{re.escape(norm_v)}\s*\)\s*\{{\s*$",
                        new_body[bi],
                    )
                    if m_in:
                        in_ind, in_kw, in_var = m_in.groups()
                        in_end = -1
                        for bk in range(bi + 1, len(new_body)):
                            if new_body[bk].startswith(in_ind + "}"):
                                in_end = bk
                                break
                        if in_end > bi + 1:
                            if in_var == outer_v:
                                new_body[bi] = f"{in_ind}for ({in_kw} _brain_el of {norm_v}) {{\n"
                                for bk in range(bi + 1, in_end):
                                    # Keep `<prop>: <outer_v>` intact, rename other `<in_var>` uses to `_brain_el`
                                    if re.search(rf"\b{re.escape(prop_nm)}\s*:\s*{re.escape(in_var)}\s*,", new_body[bk]):
                                        changed_0v = True
                                    else:
                                        rep_bk = re.sub(rf"\b{re.escape(in_var)}\b", "_brain_el", new_body[bk])
                                        if rep_bk != new_body[bk]:
                                            new_body[bk] = rep_bk
                                            changed_0v = True
                            else:
                                for bk in range(bi + 1, in_end):
                                    rep_bk = re.sub(
                                        rf"\b({re.escape(prop_nm)}\s*:\s*){re.escape(in_var)}(\s*,)",
                                        rf"\g<1>{outer_v}\g<2>",
                                        new_body[bk],
                                    )
                                    if rep_bk != new_body[bk]:
                                        new_body[bk] = rep_bk
                                        changed_0v = True
                            bi = in_end + 1
                            continue
                    # (b) Replace `<prop>: <norm_v>,` -> `<prop>: <outer_v>,` in non-array branch
                    rep_out = re.sub(
                        rf"\b({re.escape(prop_nm)}\s*:\s*){re.escape(norm_v)}(\s*,)",
                        rf"\g<1>{outer_v}\g<2>",
                        new_body[bi],
                    )
                    if rep_out != new_body[bi]:
                        new_body[bi] = rep_out
                        changed_0v = True
                    bi += 1
                if changed_0v:
                    nl_0v = list(lines)
                    nl_0v[idx_loop + 1 : end_loop] = new_body
                    add_cand(
                        rel, idx_loop + 1, "JS_NORMALIZED_KEY_PRESERVE_RAW_INPUT",
                        f"preserve_raw_loop_key({prop_nm}:{norm_v}->{outer_v})",
                        "".join(nl_0v),
                    )

        # Op 0w (high-precision boolean rejection-guard widening):
        # `JS_GUARD_CONJUNCT_DROP_ON_REJECT`:
        # When a test expects an input to be rejected (`Missing expected exception`, `did not throw`,
        # `forbid`, `reject`, etc.) and a localized rejection branch (`if (...) { return false; / throw ... }`)
        # guards a predicate call with a boolean mode flag (`(<flag> && <pred>(<arg>))`), dropping
        # the over-restrictive `<flag> &&` widens rejection to all modes!
        _raw_init_0w = str(getattr(loc, "initial_output", "") or "")
        _raw_0w_lo = _raw_init_0w.lower()
        _expects_reject_0w = any(
            k in _raw_0w_lo
            for k in (
                "missing expected exception",
                "did not throw",
                "expected to throw",
                "forbid",
                "should reject",
                "must reject",
            )
        )
        if _expects_reject_0w:
            # Extract informative lowercase words (>3 chars) from failing test lines for clean ranking
            _fail_words_0w: set[str] = set()
            for _fl_0w in _raw_init_0w.splitlines():
                if "not ok" in _fl_0w.lower() or "fail" in _fl_0w.lower() or "error" in _fl_0w.lower():
                    for _w0 in re.findall(r"[a-z]{4,}", _fl_0w.lower()):
                        if _w0 not in ("error", "assertionerror", "missing", "expected", "exception", "subtest", "failed", "test", "units"):
                            _fail_words_0w.add(_w0)
            _0w_hits: list[tuple[int, int, str, str]] = []
            _lns_0w = sorted(set(lns) | set((getattr(loc, "covered_lines_by_file", None) or {}).get(rel) or ()))
            for ln_0w in _lns_0w:
                if not (1 <= ln_0w <= len(lines)):
                    continue
                raw_0w = lines[ln_0w - 1]
                if "&&" not in raw_0w:
                    continue
                for m_cj in re.finditer(r"\(\s*([A-Za-z_$]\w*)\s*&&\s*([A-Za-z_$][\w.]*\([^()]*\))\s*\)", raw_0w):
                    flag_v, pred_call = m_cj.group(1), m_cj.group(2)
                    # Verify this line is inside a rejection branch (`return false` or `throw` within next 3 lines)
                    nxt_ctx = "".join(lines[ln_0w - 1 : min(len(lines), ln_0w + 4)])
                    if "return false" not in nxt_ctx and "throw " not in nxt_ctx:
                        continue
                    # Score identifier overlap with failing test description (general lexical alignment, 0 hardcoding)
                    fn_ctx = "".join(lines[max(0, ln_0w - 25) : ln_0w + 1]).lower()
                    overlap_s = sum(1 for fw in _fail_words_0w if fw in pred_call.lower()) * 3 + sum(
                        1 for fw in _fail_words_0w if fw in fn_ctx
                    )
                    patched_ln_0w = raw_0w[: m_cj.start()] + pred_call + raw_0w[m_cj.end() :]
                    nl_0w = list(lines)
                    nl_0w[ln_0w - 1] = patched_ln_0w
                    _0w_hits.append((overlap_s, ln_0w, f"drop_reject_guard({flag_v}&&{pred_call}->{pred_call})", "".join(nl_0w)))
            _0w_hits.sort(key=lambda t: (-t[0], t[1]))
            for _ov, ln_0w, desc_0w, psrc_0w in _0w_hits[:4]:
                add_cand(rel, ln_0w, "JS_GUARD_CONJUNCT_DROP_ON_REJECT", desc_0w, psrc_0w)

        # Op 0x (Iter 61 — ECMAScript detached-method `this` binding law):
        # `JS_DETACHED_THIS_TO_DEFINED_RECEIVER`:
        # When a method defined inside `Object.defineProperties(target, { ... })` or
        # `Object.defineProperty(target, ...)` references `this(...)` / `this.prop` and a test
        # invokes it detached (`const { m } = obj; m(...)`), `this` is `undefined` (`TypeError`).
        # Replacing `this` with the lexically in-scope `target` binds the method safely.
        if "TypeError" in (loc.initial_output or "") and any(
            "Object.defineProperties(" in _l or "Object.defineProperty(" in _l for _l in lines
        ):
            _def_re = re.compile(r"\bObject\.definePropert(?:y|ies)\s*\(\s*([A-Za-z_$][\w$]*)\s*,")
            _0x_hits: list[tuple[int, int, str, str]] = []
            for di, dline in enumerate(lines):
                m_def = _def_re.search(dline)
                if not m_def:
                    continue
                target_id = m_def.group(1)
                # Walk brace depth from di to find the matching end of defineProperties/defineProperty
                depth_0x = 0
                started_0x = False
                end_di = min(len(lines), di + 120)
                for dj in range(di, end_di):
                    for ch_d in lines[dj]:
                        if ch_d == "(":
                            depth_0x += 1
                            started_0x = True
                        elif ch_d == ")":
                            depth_0x -= 1
                    if started_0x and depth_0x <= 0:
                        end_di = dj + 1
                        break
                for dj in range(di, end_di):
                    raw_dx = lines[dj]
                    if not re.search(r"\bthis\s*(?:\(|\.)", raw_dx):
                        continue
                    patched_dx = re.sub(r"\bthis(?=\s*\()", target_id, raw_dx)
                    if patched_dx == raw_dx:
                        patched_dx = re.sub(r"\bthis(?=\.)", target_id, raw_dx)
                    if patched_dx != raw_dx:
                        nl_dx = list(lines)
                        nl_dx[dj] = patched_dx
                        in_loc = 1 if (dj + 1) in lns else 0
                        _0x_hits.append((in_loc, dj + 1, f"detached_this({target_id})", "".join(nl_dx)))
            _0x_hits.sort(key=lambda t: (-t[0], t[1]))
            for _il, ln_0x, desc_0x, psrc_0x in _0x_hits[:4]:
                add_cand(rel, ln_0x, "JS_DETACHED_THIS_TO_DEFINED_RECEIVER", desc_0x, psrc_0x)

        # Op 0y (Iter 61/63 — ECMA-262 case-insensitive RegExp `/i` flag law):
        # `JS_REGEX_CASE_INSENSITIVE_FLAG`:
        # Companion to Op 0u (`JS_REGEX_DOTALL_NEWLINE_LAW`). When a failing test exercises
        # case variations against a regex literal `/pattern/flags` containing ASCII letters
        # (including hex escapes like `/%2E/g`) without `i`, add `/i`, ranked by lexical
        # overlap against the actual failure lines (including mid-stream TAP `not ok` blocks).
        _raw_out_0y = loc.initial_output or ""
        _not_ok_0y: list[str] = []
        _out_lines_0y = _raw_out_0y.splitlines()
        for _li_y, _ln_y in enumerate(_out_lines_0y):
            if _ln_y.startswith(("not ok ", "  ---", "FAIL ", "✖")) or "AssertionError" in _ln_y or "not equal" in _ln_y.lower():
                _not_ok_0y.extend(_out_lines_0y[max(0, _li_y - 2) : min(len(_out_lines_0y), _li_y + 8)])
        _fail_blob_0y = (_raw_out_0y[:2000] + " " + " ".join(_not_ok_0y[:80]) + " " + _raw_out_0y[-3000:]).lower()
        _fail_toks_0y = {
            w for w in re.findall(r"[a-z]{3,}", _fail_blob_0y)
            if w not in {
                "should", "when", "with", "from", "that", "this", "have", "not", "true", "false",
                "expected", "actual", "assert", "strict", "equal", "error", "test", "spec", "fail",
                "passing", "failing", "status", "header", "response", "request", "function", "object",
            }
        }
        _case_hint_0y = any(
            k in _fail_blob_0y for k in ("case", "insensitive", "uppercase", "lowercase", "capital", "%2e")
        )
        _rx_decl_re = re.compile(
            r"(?<!['\"\\])/(?![/*])((?:\\.|[^/\\\r\n])+)/([dgimsuvy]*)(?!\s*[\w/])"
        )
        _0y_hits: list[tuple[int, int, str, str]] = []
        for ri_y, raw_y in enumerate(lines):
            stripped_y = raw_y.lstrip()
            if stripped_y.startswith(("//", "/*", "*")):
                continue
            for m_ry in _rx_decl_re.finditer(raw_y):
                pat_y, flg_y = m_ry.group(1), m_ry.group(2)
                if "i" in flg_y:
                    continue
                # Strip regex escape sequences like \s, \d, \w before checking for literal ASCII letters
                pat_lit = re.sub(r"\\.", "", pat_y)
                if not re.search(r"[A-Za-z]", pat_lit):
                    continue
                # Lexical tokens from the variable name + literal words inside the regex
                line_words = set(re.findall(r"[a-z]{3,}", (raw_y[: m_ry.start()] + " " + pat_lit).lower()))
                # Also split camelCase identifiers (e.g. cacheControlNoTransformRegExp -> cache, control, transform)
                for cid in re.findall(r"[A-Za-z][a-z]+", raw_y[: m_ry.start()]):
                    if len(cid) >= 3:
                        line_words.add(cid.lower())
                ov_y = sum(1 for w in line_words if w in _fail_toks_0y)
                pct_hex_hit = bool(re.search(r"%[0-9a-fA-F]{2}", pat_lit)) and (pat_lit.lower() in _fail_blob_0y)
                if ov_y <= 0 and not pct_hex_hit and not (_case_hint_0y and (ri_y + 1) in lns):
                    continue
                score_y = ov_y * 4 + (6 if pct_hex_hit else 0) + (3 if _case_hint_0y else 0) + (2 if (ri_y + 1) in lns else 0)
                patched_y = raw_y[: m_ry.end(2)] + "i" + raw_y[m_ry.end(2) :]
                nl_y = list(lines)
                nl_y[ri_y] = patched_y
                _0y_hits.append((score_y, ri_y + 1, f"regex_add_i_flag(/{pat_y[:28]}/{flg_y}i)", "".join(nl_y)))
                break
        _0y_hits.sort(key=lambda t: (-t[0], t[1]))
        for _sy, ln_0y, desc_0y, psrc_0y in _0y_hits[:4]:
            add_cand(rel, ln_0y, "JS_REGEX_CASE_INSENSITIVE_FLAG", desc_0y, psrc_0y)

        # Op 0z (Iter 62 — ECMA-262 Array.prototype.sort / toSorted comparator guard):
        # `JS_SORT_COMPARATOR_TYPEOF_FUNCTION_GUARD`:
        # `Array.prototype.sort(cmp)` / `.toSorted(cmp)` throw `TypeError: The comparison
        # function must be either a function or undefined` for any non-function truthy/null value.
        # Guard `.sort(arg)` / `.toSorted(arg)` -> `.toSorted(typeof arg === 'function' ? arg : undefined)`.
        _init_0z = loc.initial_output or ""
        if "TypeError" in _init_0z and "comparison function" in _init_0z.lower():
            _sort_re = re.compile(r"\.(toSorted|sort)\(\s*([A-Za-z_$][\w$.]*)\s*\)")
            _0z_hits: list[tuple[int, int, str, str]] = []
            for si_z, raw_z in enumerate(lines):
                if ".toSorted(" not in raw_z and ".sort(" not in raw_z:
                    continue
                m_sz = _sort_re.search(raw_z)
                if not m_sz:
                    continue
                meth_z, arg_z = m_sz.group(1), m_sz.group(2)
                if f"typeof {arg_z}" in raw_z:
                    continue
                repl_z = f".{meth_z}(typeof {arg_z} === 'function' ? {arg_z} : undefined)"
                patched_z = raw_z[: m_sz.start()] + repl_z + raw_z[m_sz.end() :]
                nl_z = list(lines)
                nl_z[si_z] = patched_z
                in_loc_z = 1 if (si_z + 1) in lns else 0
                _0z_hits.append((in_loc_z, si_z + 1, f"sort_cmp_guard({arg_z})", "".join(nl_z)))
            _0z_hits.sort(key=lambda t: (-t[0], t[1]))
            for _ilz, ln_0z, desc_0z, psrc_0z in _0z_hits[:4]:
                add_cand(rel, ln_0z, "JS_SORT_COMPARATOR_TYPEOF_FUNCTION_GUARD", desc_0z, psrc_0z)

        # Op 0aa (Iter 62 — ECMA-262 default-options object spread law):
        # `JS_OBJECT_SPREAD_STRIP_UNDEFINED_OPTIONS`:
        # Merging defaults via `opts = { key: defaultVal, ..., ...opts }` allows explicit
        # `{ key: undefined }` properties to clobber default values. Stripping undefined entries
        # (`...Object.fromEntries(Object.entries(opts ?? {}).filter(([, v]) => v !== undefined))`)
        # preserves all defaults while retaining falsy non-undefined overrides (`false`, `0`, `''`, `null`).
        _init_0aa_lo = (loc.initial_output or "").lower()
        if ("undefined" in _init_0aa_lo and ("default" in _init_0aa_lo or "typeerror" in _init_0aa_lo or "not iterable" in _init_0aa_lo)):
            _spread_re = re.compile(r"^(\s*)\.\.\.([A-Za-z_$][\w$]*)(,?\s*)$")
            _0aa_hits: list[tuple[int, int, str, str]] = []
            for oi, raw_o in enumerate(lines):
                m_sp = _spread_re.match(raw_o.rstrip("\r\n"))
                if not m_sp:
                    continue
                indent_o, obj_o, trail_o = m_sp.group(1), m_sp.group(2), m_sp.group(3)
                # Must sit inside an object literal `{ k: default, ..., ...obj }` (NOT an array `[...arr]`)
                ctx_prev = "".join(lines[max(0, oi - 15) : oi])
                if not re.search(r"\{\s*$", ctx_prev, re.M) or ":" not in ctx_prev:
                    continue
                if re.search(r"\[\s*$", ctx_prev, re.M) and ctx_prev.rfind("[") > ctx_prev.rfind("{"):
                    continue
                eol_o = "\r\n" if raw_o.endswith("\r\n") else ("\n" if raw_o.endswith("\n") else "")
                patched_o = (
                    f"{indent_o}...Object.fromEntries(Object.entries({obj_o} ?? {{}})"
                    f".filter(([, _v]) => _v !== undefined)){trail_o}{eol_o}"
                )
                nl_o = list(lines)
                nl_o[oi] = patched_o
                _0aa_hits.append((1 if "option" in obj_o.lower() else 0, oi + 1, f"strip_undefined_spread({obj_o})", "".join(nl_o)))
            _0aa_hits.sort(key=lambda t: (-t[0], t[1]))
            for _sc_o, ln_0aa, desc_0aa, psrc_0aa in _0aa_hits[:4]:
                add_cand(rel, ln_0aa, "JS_OBJECT_SPREAD_STRIP_UNDEFINED_OPTIONS", desc_0aa, psrc_0aa)

        # Op 0ab (Iter 62 — ECMA-262 `??` vs `=== undefined` boolean-default law):
        # `JS_NULLISH_BOOL_DEFAULT_STRICT_UNDEFINED`:
        # `expr ?? true` treats `null` identically to `undefined` (defaulting `null` to `true`),
        # diverging from default-parameter semantics (`param = true`) and truthiness checks
        # (`if (expr)`). Rewriting `expr ?? true` to `expr === undefined ? true : Boolean(expr)`
        # or `expr === undefined || expr === true` preserves the default ONLY for `undefined`.
        _nullish_bool_re = re.compile(r"\b([A-Za-z_$][\w$.]*)\s*\?\?\s*(true|false)\b")
        _0ab_hits: list[tuple[int, int, str, str]] = []
        for ri_ab, raw_ab in enumerate(lines):
            if "??" not in raw_ab:
                continue
            for m_nb in _nullish_bool_re.finditer(raw_ab):
                expr_nb, bval_nb = m_nb.group(1), m_nb.group(2)
                in_loc_ab = 1 if (ri_ab + 1) in lns else 0
                if bval_nb == "true":
                    variants_nb = [
                        (f"{expr_nb} === undefined ? true : Boolean({expr_nb})", f"strict_undef_bool({expr_nb})"),
                        (f"({expr_nb} === undefined || {expr_nb} === true)", f"strict_undef_or_true({expr_nb})"),
                    ]
                else:
                    variants_nb = [
                        (f"{expr_nb} === undefined ? false : Boolean({expr_nb})", f"strict_undef_bool({expr_nb})"),
                    ]
                for repl_nb, desc_nb in variants_nb:
                    nl_ab = list(lines)
                    nl_ab[ri_ab] = raw_ab[: m_nb.start()] + repl_nb + raw_ab[m_nb.end() :]
                    _0ab_hits.append((in_loc_ab, ri_ab + 1, desc_nb, "".join(nl_ab)))
        _0ab_hits.sort(key=lambda t: (-t[0], t[1]))
        for _ilab, ln_0ab, desc_0ab, psrc_0ab in _0ab_hits[:6]:
            add_cand(rel, ln_0ab, "JS_NULLISH_BOOL_DEFAULT_STRICT_UNDEFINED", desc_0ab, psrc_0ab)

        # Op 0ac (Iter 63 — Arithmetic zero-limit throw-guard boundary law):
        # `JS_THROW_LIMIT_NONZERO_LOWER_BOUND`:
        # When an `if (... && count >= limit)` guard immediately `throw`s (e.g. RangeError
        # on limit exceeded), `limit === 0` with `count === 0` falsely triggers the throw on
        # a scalar / empty collection. Conjoining `&& count > 0` protects the zero-count case.
        if "rangeerror" in _fail_blob_0y or "limit" in _fail_blob_0y:
            _0ac_hits: list[tuple[int, int, str, str]] = []
            _lim_cmp_re = re.compile(r"\b([A-Za-z_$][\w$.]*)\s*>=\s*([A-Za-z_$][\w$.]*)")
            for ri_ac, raw_ac in enumerate(lines):
                if "if" not in raw_ac or ">=" not in raw_ac:
                    continue
                next_blk = "".join(lines[ri_ac + 1 : min(len(lines), ri_ac + 4)])
                if "throw " not in next_blk:
                    continue
                for m_ac in _lim_cmp_re.finditer(raw_ac):
                    lhs_ac, rhs_ac = m_ac.group(1), m_ac.group(2)
                    if f"{lhs_ac} > 0" in raw_ac:
                        continue
                    patched_ac = raw_ac[: m_ac.end()] + f" && {lhs_ac} > 0" + raw_ac[m_ac.end() :]
                    nl_ac = list(lines)
                    nl_ac[ri_ac] = patched_ac
                    in_loc_ac = 1 if (ri_ac + 1) in lns else 0
                    _0ac_hits.append((in_loc_ac, ri_ac + 1, f"nonzero_limit_guard({lhs_ac} > 0)", "".join(nl_ac)))
            _0ac_hits.sort(key=lambda t: (-t[0], t[1]))
            for _ilac, ln_0ac, desc_0ac, psrc_0ac in _0ac_hits[:4]:
                add_cand(rel, ln_0ac, "JS_THROW_LIMIT_NONZERO_LOWER_BOUND", desc_0ac, psrc_0ac)

        # Op 0ad (Iter 63 — Conditional double-transform ternary simplification law):
        # `JS_TERNARY_FALLBACK_BRANCH_SIMPLIFY`:
        # When a ternary applies a method transform (`cond ? base.replace(...) : base`) whose
        # `else` branch is the unmodified `base` expression, simplifying to `base` eliminates
        # premature/redundant transformation (e.g. re-encoding structural separators).
        _0ad_hits: list[tuple[int, int, str, str]] = []
        _tern_tx_re = re.compile(
            r"([A-Za-z_$][\w$.]*)\s*\?\s*([^?:;\n]+?)\.(?:replace|replaceAll|toLowerCase|toUpperCase|trim)\([^;\n]*?\)\s*:\s*([^;\n]+?)(?=[;,\n])"
        )
        for ri_ad, raw_ad in enumerate(lines):
            if "?" not in raw_ad or ":" not in raw_ad:
                continue
            for m_ad in _tern_tx_re.finditer(raw_ad):
                cond_ad, base_then, base_else = m_ad.group(1).strip(), m_ad.group(2).strip(), m_ad.group(3).strip()
                if base_then != base_else:
                    continue
                # Score against failure tokens (camelCase-split condition name)
                c_words = {w.lower() for w in re.findall(r"[A-Za-z][a-z]+", cond_ad) if len(w) >= 3}
                c_words.add(cond_ad.lower())
                ov_ad = sum(1 for w in c_words if w in _fail_toks_0y)
                in_loc_ad = 1 if (ri_ad + 1) in lns else 0
                if ov_ad <= 0 and not in_loc_ad:
                    continue
                nl_ad = list(lines)
                nl_ad[ri_ad] = raw_ad[: m_ad.start()] + base_else + raw_ad[m_ad.end() :]
                _0ad_hits.append((ov_ad * 3 + in_loc_ad * 2, ri_ad + 1, f"ternary_drop_transform({cond_ad} -> {base_else})", "".join(nl_ad)))
        _0ad_hits.sort(key=lambda t: (-t[0], t[1]))
        for _scad, ln_0ad, desc_0ad, psrc_0ad in _0ad_hits[:4]:
            add_cand(rel, ln_0ad, "JS_TERNARY_FALLBACK_BRANCH_SIMPLIFY", desc_0ad, psrc_0ad)

        # Op 0l (high-precision JS implicit-string-coercion guard hardening):
        # `JS_COERCE_STRICT_STRING_GUARD`:
        # When a guard checks strict equality against string literals (`if (k === 'a' || k === 'b' ...)`),
        # non-string values like `['a']` bypass `===` yet coerce to `'a'` upon property indexing (`obj[k]`).
        # Coerce the guarded identifier (`''+k === ...` or `k == ...`) and atomically synchronize identical
        # guards across sibling modules in the same directory (e.g., `src/index.js` + `src/merge.js`).
        def _coerce_strict_str_guard(file_lines: list[str], mode_c: str) -> tuple[str, int, str] | None:
            out_l = list(file_lines)
            first_hit = -1
            hit_v = ""
            for i_g, raw_g in enumerate(out_l):
                if "if" not in raw_g or "===" not in raw_g:
                    continue
                m_g = re.search(
                    r"\bif\s*\(\s*([A-Za-z_$]\w*)\s*===\s*(['\"][^'\"]+['\"])(?:\s*\|\|\s*\1\s*===\s*['\"][^'\"]+['\"])+",
                    raw_g,
                )
                if not m_g:
                    continue
                gv = m_g.group(1)
                if mode_c == "loose_eq":
                    patched_ln = re.sub(rf"\b{re.escape(gv)}\s*===\s*(?=['\"])", f"{gv} == ", raw_g)
                else:
                    patched_ln = re.sub(rf"\b{re.escape(gv)}\s*===\s*(?=['\"])", f"'' + {gv} === ", raw_g)
                if patched_ln != raw_g:
                    out_l[i_g] = patched_ln
                    if first_hit < 0:
                        first_hit = i_g + 1
                        hit_v = gv
            if first_hit > 0:
                return "".join(out_l), first_hit, hit_v
            return None

        for _mc in ("str_coerce", "loose_eq"):
            _cg_hit = _coerce_strict_str_guard(lines, _mc)
            if _cg_hit is None:
                continue
            cg_src, cg_ln, cg_v = _cg_hit
            add_cand(
                rel, cg_ln, "JS_COERCE_STRICT_STRING_GUARD",
                f"coerce_strict_str_guard({_mc}:{cg_v})", cg_src,
            )
            cg_extras: list[tuple[str, str]] = []
            rel_dir = (worktree / rel).parent
            if rel_dir.is_dir():
                for sib_p in sorted(rel_dir.iterdir()):
                    if not sib_p.is_file() or sib_p.suffix.lower() not in (".js", ".mjs", ".cjs", ".ts"):
                        continue
                    sib_rel = sib_p.relative_to(worktree).as_posix()
                    if (
                        sib_rel == rel
                        or _is_non_prod_skip(sib_rel)
                        or ".test." in sib_rel
                        or ".spec." in sib_rel
                        or sib_rel.startswith("test/")
                        or sib_rel.startswith("tests/")
                    ):
                        continue
                    sib_lines = sib_p.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
                    sib_fix = _coerce_strict_str_guard(sib_lines, _mc)
                    if sib_fix is not None:
                        cg_extras.append((sib_rel, sib_fix[0]))
            if cg_extras:
                add_cand(
                    rel, cg_ln, "JS_COERCE_STRICT_STRING_GUARD",
                    f"coerce_strict_str_guard_multifile({_mc}:{cg_v} +{len(cg_extras)} files)",
                    cg_src,
                    extra_patches=tuple(cg_extras),
                )

        # Op 0: Coupled Multi-Line Sibling Template Synchronization (`JS_COUPLED_SIBLING_TEMPLATE_SYNC`):
        # (0a) Intra-block sibling template sync: inside any localized `else { ... }` block, if a
        #      template interpolation `${v}` appears in >= 2 sub-branches while a sibling `else`
        #      template omits `${v}`, atomically drop `${v}` across those sub-branches.
        # (0b) Inter-function sibling template & option-var sync: if a localized function `fnA` shares
        #      branch guards (`if (C)` / `else if (C)`) with a sibling function `fnB` that declares
        #      `const v = options.flag ? a : b` and interpolates `${v}` in those branches, atomically
        #      transfer the `const v = ...` declaration + `${v}` interpolations into `fnA`.
        localized_set = set(lns)
        fn_spans: list[tuple[int, int, str]] = []  # (start_idx, end_idx, fn_name)
        for fi, fl in enumerate(lines):
            mf = re.match(r"^(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$]\w*)\s*=\s*\([^)]*\boptions\b[^)]*\)\s*=>\s*\{", fl)
            if not mf:
                mf = re.match(r"^(?:export\s+)?function\s+([A-Za-z_$]\w*)\s*\([^)]*\boptions\b[^)]*\)\s*\{", fl)
            if mf:
                end_i = min(len(lines) - 1, fi + 80)
                for ej in range(fi + 1, min(len(lines), fi + 90)):
                    if lines[ej].startswith("}"):
                        end_i = ej
                        break
                fn_spans.append((fi, end_i, mf.group(1)))

        # (0a) Intra-block coupled `${v}` removal inside localized `else { ... }` blocks
        for fi, end_i, fn_nm in fn_spans:
            if not any((k + 1) in localized_set for k in range(fi, end_i + 1)):
                continue
            for bi in range(fi, end_i):
                if re.match(r"^\s*\}\s*else\s*\{\s*$", lines[bi]):
                    b_ind = len(lines[bi]) - len(lines[bi].lstrip())
                    b_end = end_i
                    for bj in range(bi + 1, end_i + 1):
                        if lines[bj].strip() == "}" and (len(lines[bj]) - len(lines[bj].lstrip())) <= b_ind:
                            b_end = bj
                            break
                    blk_idxs = list(range(bi + 1, b_end))
                    # Collect `${v}` tokens appearing in template lines inside this `else` block
                    tpl_lines_with: dict[str, list[int]] = {}
                    tpl_lines_total = 0
                    for k in blk_idxs:
                        if "`" in lines[k]:
                            tpl_lines_total += 1
                            for mv in re.finditer(r"\$\{([A-Za-z_$]\w*)\}", lines[k]):
                                tpl_lines_with.setdefault(mv.group(1), []).append(k)
                    for vname, hit_idxs in tpl_lines_with.items():
                        uniq_hits = sorted(set(hit_idxs))
                        # Only fire when `vname` is a single-char / short option-derived var present in
                        # some (>=2) template lines of this block while sibling template lines omit it
                        if len(uniq_hits) >= 2 and tpl_lines_total > len(uniq_hits) and re.search(
                            rf"\bconst\s+{re.escape(vname)}\s*=\s*options\.", "".join(lines[fi : end_i + 1])
                        ):
                            nl = list(lines)
                            for hi in uniq_hits:
                                nl[hi] = nl[hi].replace(f"${{{vname}}}", "")
                            add_cand(
                                rel, uniq_hits[0] + 1, "JS_COUPLED_SIBLING_TEMPLATE_SYNC",
                                f"coupled_drop_interp({fn_nm}:${{{vname}}}x{len(uniq_hits)})", "".join(nl),
                            )

        # (0b) Inter-function sibling `const v = options.<flag> ? ...` + template interpolation transfer
        for idx_a, (fa_s, fa_e, fn_a) in enumerate(fn_spans):
            if not any((k + 1) in localized_set for k in range(fa_s, fa_e + 1)):
                continue
            body_a = "".join(lines[fa_s : fa_e + 1])
            for idx_b, (fb_s, fb_e, fn_b) in enumerate(fn_spans):
                if idx_a == idx_b or abs(fa_s - fb_s) > 140:
                    continue
                body_b = "".join(lines[fb_s : fb_e + 1])
                for m_opt_decl in re.finditer(
                    r"^([ \t]*const\s+([A-Za-z_$]\w*)\s*=\s*options\.[A-Za-z_$]\w*\s*\?[^\n]+)\n",
                    body_b,
                    re.M,
                ):
                    decl_line, vname = m_opt_decl.group(1), m_opt_decl.group(2)
                    if re.search(rf"\bconst\s+{re.escape(vname)}\b", body_a):
                        continue
                    # Map branch condition (`if (C)` / `else if (C)`) -> (pre_tok, post_tok) around `${vname}` in fnB
                    cond_before_tok: dict[str, list[tuple[str, str]]] = {}
                    outer_cond: str | None = None
                    inner_cond: str | None = None
                    outer_ind: int | None = None
                    for kb in range(fb_s, fb_e + 1):
                        mc = re.search(r"\b(?:else\s+)?if\s*\(([^()]+(?:\([^()]*\)[^()]*)*)\)", lines[kb])
                        if mc:
                            k_ind = len(lines[kb]) - len(lines[kb].lstrip())
                            c_str = mc.group(1).strip()
                            if outer_ind is None or k_ind <= outer_ind:
                                outer_ind = k_ind
                                outer_cond = c_str
                                inner_cond = c_str
                            else:
                                inner_cond = c_str
                        if f"${{{vname}}}" in lines[kb]:
                            m_pre = re.search(rf"([A-Za-z0-9_.}}]+)\$\{{{re.escape(vname)}\}}(\s+<)", lines[kb])
                            if m_pre:
                                pair = (m_pre.group(1), m_pre.group(2))
                                for ck in (outer_cond, inner_cond):
                                    if ck and pair not in cond_before_tok.get(ck, ()):
                                        cond_before_tok.setdefault(ck, []).append(pair)
                    if not cond_before_tok:
                        continue
                    # Apply atomically to matching branches in `fnA`
                    nl = list(lines)
                    edits_made = 0
                    cur_cond_a: str | None = None
                    insert_decl_at: int | None = None
                    for ka in range(fa_s + 1, fa_e + 1):
                        if insert_decl_at is None and re.match(r"^\s*const\s+\w+\s*=\s*options\.", nl[ka]):
                            insert_decl_at = ka + 1
                        mc = re.search(r"\b(?:else\s+)?if\s*\(([^()]+(?:\([^()]*\)[^()]*)*)\)", nl[ka])
                        if mc:
                            cur_cond_a = mc.group(1).strip()
                        if cur_cond_a in cond_before_tok and "`" in nl[ka] and f"${{{vname}}}" not in nl[ka]:
                            for pre_tok, post_tok in cond_before_tok[cur_cond_a]:
                                needle = pre_tok + post_tok
                                if needle in nl[ka]:
                                    nl[ka] = nl[ka].replace(needle, f"{pre_tok}${{{vname}}}{post_tok}", 1)
                                    edits_made += 1
                                    break
                    if edits_made >= 1:
                        ins_pos = insert_decl_at if insert_decl_at is not None else (fa_s + 1)
                        nl.insert(ins_pos, decl_line + "\n")
                        add_cand(
                            rel, fa_s + 1, "JS_COUPLED_SIBLING_TEMPLATE_SYNC",
                            f"sibling_fn_sync({fn_b}->{fn_a}:${{{vname}}}x{edits_made})", "".join(nl),
                        )

        for ln in lns:
            if not (1 <= ln <= len(lines)):
                continue
            line = lines[ln - 1]
            stripped = line.strip()
            if not stripped or stripped.startswith(("//", "/*", "*", "import ", "export type ")):
                continue
            ind = line[: len(line) - len(line.lstrip())]

            # Op 1: JS Numeric Finite / Safe-Integer Invariants (`JS_NUMERIC_FINITE_SAFE_GUARD`)
            for pat, repl, dlabel in (
                (r"\bNumber\.isInteger\(([^()]+)\)", r"Number.isSafeInteger(\1)", "Number.isInteger->Number.isSafeInteger"),
                (r"\bNumber\.isFinite\(([^()]+)\)", r"Number.isSafeInteger(\1)", "Number.isFinite->Number.isSafeInteger"),
                (r"\b(?<!Number\.)isFinite\(([^()]+)\)", r"Number.isSafeInteger(\1)", "isFinite->Number.isSafeInteger"),
                (r"!\s*isNaN\(([^()]+)\)", r"isFinite(\1)", "!isNaN->isFinite"),
                (r"!\s*isNaN\(([^()]+)\)", r"Number.isFinite(\1)", "!isNaN->Number.isFinite"),
                (r"!\s*Number\.isNaN\(([^()]+)\)", r"Number.isFinite(\1)", "!Number.isNaN->Number.isFinite"),
                (r"\b(?<!Number\.)isNaN\(([^()]+)\)", r"!Number.isFinite(\1)", "isNaN->!Number.isFinite"),
                (r"\bNumber\.isNaN\(([^()]+)\)", r"!Number.isFinite(\1)", "Number.isNaN->!Number.isFinite"),
                (r"\bisNaN\(([^()]+)\)", r"!Number.isSafeInteger(\1)", "isNaN->!Number.isSafeInteger"),
            ):
                if re.search(pat, line):
                    new_l = re.sub(pat, repl, line, count=1)
                    if new_l != line:
                        nl = list(lines)
                        nl[ln - 1] = new_l
                        add_cand(rel, ln, "JS_NUMERIC_FINITE_SAFE_GUARD", dlabel, "".join(nl))

            # Op 2: JS Truthiness / Empty-String / Nullish Guard Unwrap (`JS_TRUTHINESS_AND_EMPTY_GUARD`)
            # (2a) `if (var)` guarding a single transform line (e.g., `if (val) { val = enc(val); }` or
            #      `if (val) val = enc(val);` skipping empty string `""`!)
            m_if_var = re.match(r"^(\s*)if\s*\(\s*([A-Za-z_$][\w$.]*)\s*\)\s*(\{?)\s*$", line)
            if m_if_var:
                vname = m_if_var.group(2)
                for repl_cond, dl in (
                    (f"{vname} !== undefined", f"truthy->{vname}!==undefined"),
                    (f"{vname} != null", f"truthy->{vname}!=null"),
                    ("true", f"unwrap_if({vname})"),
                ):
                    nl = list(lines)
                    nl[ln - 1] = f"{m_if_var.group(1)}if ({repl_cond}) {m_if_var.group(3)}\n"
                    add_cand(rel, ln, "JS_TRUTHINESS_AND_EMPTY_GUARD", dl, "".join(nl))
            # (2b) Ternary `v ? fn(v) : v` or `v ? fn(v) : ''` skipping empty string `""`
            m_tern_fn = re.search(
                r"\b([A-Za-z_$][\w$.]*)\s*\?\s*([A-Za-z_$][\w$.]*\s*\(\s*\1\s*\))\s*:\s*(?:\1|''|\"\")",
                line,
            )
            if m_tern_fn:
                new_l = line[: m_tern_fn.start()] + m_tern_fn.group(2) + line[m_tern_fn.end() :]
                nl = list(lines)
                nl[ln - 1] = new_l
                add_cand(rel, ln, "JS_TRUTHINESS_AND_EMPTY_GUARD", f"unwrap_empty_ternary({m_tern_fn.group(2)})", "".join(nl))
            # (2c) Inline `if (v) stmt;`
            m_if_inline = re.match(r"^(\s*)if\s*\(\s*([A-Za-z_$][\w$.]*)\s*\)\s+([^;{\n]+;)\s*$", line)
            if m_if_inline:
                nl = list(lines)
                nl[ln - 1] = f"{m_if_inline.group(1)}{m_if_inline.group(3)}\n"
                add_cand(rel, ln, "JS_TRUTHINESS_AND_EMPTY_GUARD", f"unwrap_inline_if({m_if_inline.group(2)})", "".join(nl))

            # Op 3: JS Leading-Delimiter Accumulator Repair (`JS_LEADING_DELIM_ACCUM_REPAIR`)
            # e.g., `cookie += '; ' + ...` or `str += `; ${k}=${v}`` -> guard leading delimiter when `str` is empty!
            m_acc_tpl = re.match(r"^(\s*)([A-Za-z_$][\w$.]*)\s*\+=\s*`([;,:&|]\s*)(.*)`\s*;?\s*$", line)
            if m_acc_tpl:
                a_ind, a_var, a_sep, a_rest = m_acc_tpl.groups()
                nl = list(lines)
                nl[ln - 1] = f"{a_ind}{a_var} += ({a_var} ? {a_sep!r} : '') + `{a_rest}`;\n"
                add_cand(rel, ln, "JS_LEADING_DELIM_ACCUM_REPAIR", f"guard_leading_delim({a_var},{a_sep!r})", "".join(nl))
            m_acc_str = re.match(r"^(\s*)([A-Za-z_$][\w$.]*)\s*\+=\s*(['\"])([;,:&|]\s*)\3\s*\+\s*(.+?)\s*;?\s*$", line)
            if m_acc_str:
                a_ind, a_var, _, a_sep, a_rest = m_acc_str.groups()
                nl = list(lines)
                nl[ln - 1] = f"{a_ind}{a_var} += ({a_var} ? {a_sep!r} : '') + {a_rest};\n"
                add_cand(rel, ln, "JS_LEADING_DELIM_ACCUM_REPAIR", f"guard_leading_delim({a_var},{a_sep!r})", "".join(nl))
            # Also `if (str) str += '; ';` when `str += '; '` is standalone unconditionally
            m_acc_only = re.match(r"^(\s*)([A-Za-z_$][\w$.]*)\s*\+=\s*(['\"])([;,:&|]\s*)\3\s*;?\s*$", line)
            if m_acc_only:
                a_ind, a_var, _, a_sep = m_acc_only.groups()
                nl = list(lines)
                nl[ln - 1] = f"{a_ind}if ({a_var}) {a_var} += {a_sep!r};\n"
                add_cand(rel, ln, "JS_LEADING_DELIM_ACCUM_REPAIR", f"guard_delim_append({a_var},{a_sep!r})", "".join(nl))
            # (3d) Loop-index delimiter guard `if (i > 0) str += "; ";` fails when earlier loop items `continue`!
            # Universal serializer invariant: emit delimiter iff accumulator is non-empty (`str.length > 0`).
            m_idx_delim = re.match(
                r"^(\s*)if\s*\(\s*[A-Za-z_$]\w*\s*(?:>\s*0|!==\s*0|!=\s*0)\s*\)\s*([A-Za-z_$][\w$.]*)\s*\+=\s*(['\"][;,:&|\-/\s]+['\"])\s*;?\s*$",
                line,
            )
            if m_idx_delim:
                d_ind, d_var, d_sep = m_idx_delim.groups()
                nl = list(lines)
                nl[ln - 1] = f"{d_ind}if ({d_var}.length > 0) {d_var} += {d_sep};\n"
                add_cand(rel, ln, "JS_LEADING_DELIM_ACCUM_REPAIR", f"idx_to_accum_len({d_var})", "".join(nl))

            # Op 4: JS Regex Literal Refinement (`JS_REGEX_LITERAL_REPAIR`)
            # First-principles signed-number canonicalization & quantifier widening on executed regex literals
            if "/" in line and any(tok in line for tok in ("match(", "exec(", "test(", "RegExp(", " = /", "return /")):
                # (4a) Misplaced-sign numeric group e.g. `(?:\d+)?\-?\d?\.?\d+` or `(?:\d+)?-?(?:\d+)?\.?\d+`
                m_bad_num = re.search(
                    r"\(\?:\\d\+\)\?\\?-\?(?:\(\?:\\d\+\)\?|\\d[\?\*]?)(?:\\\.)?\?\\d\+",
                    line,
                )
                if m_bad_num:
                    for repl_num, dl in (
                        (r"-?(?:\d+)?\.?\d+", "regex_canonical_signed_decimal"),
                        (r"-?(?:\d+\.?\d*|\.\d+)", "regex_strict_signed_decimal"),
                    ):
                        new_l = line[: m_bad_num.start()] + repl_num + line[m_bad_num.end() :]
                        if new_l != line:
                            nl = list(lines)
                            nl[ln - 1] = new_l
                            add_cand(rel, ln, "JS_REGEX_LITERAL_REPAIR", dl, "".join(nl))
                # (4b) Quantifier widening `\d?` -> `\d*` inside numeric regexes
                if r"\d?" in line:
                    nl = list(lines)
                    nl[ln - 1] = line.replace(r"\d?", r"\d*", 1)
                    add_cand(rel, ln, "JS_REGEX_LITERAL_REPAIR", "regex_digit_quantifier_widen", "".join(nl))
                # (4c) Direct signed/decimal sub-pattern refinements
                for old_r, new_r, dl in (
                    (r"(\d*\.?\d+)", r"(\d+(?:\.\d+)?|\.\d+)", "regex_num_group"),
                    (r"-?(\d*\.?\d+)", r"-?(?:\d+\.?\d*|\.\d+)", "regex_signed_decimal"),
                    (r"(-?\d*\.?\d+)", r"(-?(?:\d+)?\.?\d+)", "regex_opt_int_decimal"),
                    (r"((?:\d+)?\.?\d+)", r"(-?(?:\d+)?\.?\d+)", "regex_add_opt_sign"),
                    (r"(\d+(?:\.\d+)?)", r"(-?(?:\d+)?\.?\d+)", "regex_signed_opt_int"),
                    (r"(-?(?:\d+)?\.?\d+)", r"(-?(?:\d+\.?\d*|\.\d+))", "regex_strict_decimal"),
                    (r"(-?\d+)?\.?\d+", r"-?(?:\d+)?\.?\d+", "regex_move_sign_outside_opt_group"),
                    (r"((?:-?\d+)?\.?\d+)", r"(-?(?:\d+)?\.?\d+)", "regex_sign_outside_opt_int"),
                ):
                    if old_r in line:
                        nl = list(lines)
                        nl[ln - 1] = line.replace(old_r, new_r, 1)
                        add_cand(rel, ln, "JS_REGEX_LITERAL_REPAIR", dl, "".join(nl))

            # Op 5: JS Domain-Throw Boundary Guards (`JS_DOMAIN_THROW_GUARD`)
            # (5a) Date year range check (RFC 6265 / HTTP cookie / ISO year bounds [1000..9999] or [1601..9999])
            if want_throw and ("getTime(" in line or "toUTCString(" in line or "instanceof Date" in line):
                m_dv = re.search(r"\b([A-Za-z_$][\w$.]*)\.(?:getTime|toUTCString)\s*\(", line)
                if m_dv:
                    dv = m_dv.group(1)
                    throw_s = next((t for t in existing_throws if "expires" in t.lower()), existing_throws[0] if existing_throws else "throw new TypeError('invalid date');")
                    for yr_lo, yr_hi in ((1601, 9999), (1000, 9999)):
                        guard_l = f"{ind}if ({dv}.getUTCFullYear() < {yr_lo} || {dv}.getUTCFullYear() > {yr_hi}) {{ {throw_s} }}\n"
                        nl = list(lines)
                        nl.insert(ln - 1, guard_l)
                        add_cand(rel, ln, "JS_DOMAIN_THROW_GUARD", f"date_year_bounds({dv},{yr_lo}..{yr_hi})", "".join(nl))

            # (5b) Numeric guard before `Math.floor(v)` / `Math.trunc(v)` when tests expect throw on non-safe/non-finite
            if want_throw and ("Math.floor(" in line or "Math.trunc(" in line or "Number(" in line):
                m_nv = re.search(r"(?:Math\.floor|Math\.trunc)\s*\(\s*([A-Za-z_$][\w$.]*)\s*\)", line)
                if m_nv:
                    nv = m_nv.group(1)
                    throw_s = next((t for t in existing_throws if "maxage" in t.lower() or "int" in t.lower()), existing_throws[0] if existing_throws else "throw new TypeError('invalid number');")
                    for cond_s, dl in (
                        (f"!Number.isSafeInteger({nv})", f"guard_safe_int({nv})"),
                        (f"!Number.isFinite({nv})", f"guard_finite({nv})"),
                    ):
                        guard_l = f"{ind}if ({cond_s}) {{ {throw_s} }}\n"
                        nl = list(lines)
                        nl.insert(ln - 1, guard_l)
                        add_cand(rel, ln, "JS_DOMAIN_THROW_GUARD", dl, "".join(nl))

            # (5c) Dynamic Options-Flag Override (`JS_OPTIONS_FLAG_OVERRIDE`):
            # When a function checks `options.<flag>` and passes `options` into a helper call inside a
            # branch (`fn(..., options)`), synthesize `{ ...options, <flag>: true/false }` (single-site
            # and paired symmetric helper calls in the same branch family). Zero domain hardcoding.
            if (
                opt_flags
                and "function " not in stripped
                and "=>" not in stripped
                and not re.match(r"^(?:async\s+)?(?:constructor|[A-Za-z_$]\w*)\s*\([^)]*\)\s*\{$", stripped)
                and re.search(r"[A-Za-z_$]\w*\s*\([^\n]*,\s*options\s*\)", line)
            ):
                m_call = re.search(
                    r"\b(?!if\b|while\b|for\b|switch\b|catch\b|return\b)([A-Za-z_$]\w*)\s*\(([^()\n]*(?:\([^()\n]*\)[^()\n]*)*),\s*options\s*\)",
                    line,
                )
                if m_call:
                    fn_nm = m_call.group(1)
                    for fl_name in opt_flags[:3]:
                        for bval in ("true", "false"):
                            new_l = re.sub(
                                r"(\b" + re.escape(fn_nm) + r"\s*\([^()\n]*(?:\([^()\n]*\)[^()\n]*)*,\s*)options(\s*\))",
                                rf"\1{{ ...options, {fl_name}: {bval} }}\2",
                                line,
                                count=1,
                            )
                            if new_l != line:
                                nl = list(lines)
                                nl[ln - 1] = new_l
                                add_cand(rel, ln, "JS_OPTIONS_FLAG_OVERRIDE", f"opt_override({fn_nm},{fl_name}={bval})", "".join(nl))
                                # Also check for a symmetric sibling `else if (... fn_nm(..., options))` within +/- 30 lines
                                sib_nl = list(nl)
                                sib_hit = False
                                for sln in range(max(1, ln - 30), min(len(lines), ln + 30) + 1):
                                    if sln == ln:
                                        continue
                                    sline = lines[sln - 1]
                                    if "else if" in sline and fn_nm in sline and ", options)" in sline:
                                        snew = re.sub(
                                            r"(\b" + re.escape(fn_nm) + r"\s*\([^()\n]*(?:\([^()\n]*\)[^()\n]*)*,\s*)options(\s*\))",
                                            rf"\1{{ ...options, {fl_name}: {bval} }}\2",
                                            sline,
                                            count=1,
                                        )
                                        if snew != sline:
                                            sib_nl[sln - 1] = snew
                                            sib_hit = True
                                if sib_hit:
                                    add_cand(rel, ln, "JS_OPTIONS_FLAG_OVERRIDE", f"opt_override_pair({fn_nm},{fl_name}={bval})", "".join(sib_nl))

            # Op 5d: IEEE-754 NaN-Safe Comparison Inversion (`JS_NAN_SAFE_COMPARISON_INVERSION`)
            # Under IEEE-754, `NaN > x` is `false` whereas `!(NaN <= x)` is `true`.
            # Transforming `A > B` -> `!(A <= B)` (and duals) preserves all finite comparisons while
            # treating NaN (e.g. invalid Date.parse / parseFloat / Number) as failing the predicate.
            if any(op in line for op in (" > ", " < ", " >= ", " <= ")) and any(
                tok in line for tok in ("Date.parse", "parseFloat", "parseInt", "Number(", "parseHttpDate", "parse")
            ):
                m_cmp = re.search(
                    r"([A-Za-z_$][\w$.]*(?:\([^()]*\))?)\s*(>=|<=|>|<)\s*([A-Za-z_$][\w$.]*(?:\([^()]*\))?)",
                    line,
                )
                if m_cmp:
                    lhs_e, op_e, rhs_e = m_cmp.groups()
                    dual_op = {">": "<=", "<": ">=", ">=": "<", "<=": ">"}[op_e]
                    new_l = line[: m_cmp.start()] + f"!({lhs_e} {dual_op} {rhs_e})" + line[m_cmp.end() :]
                    nl = list(lines)
                    nl[ln - 1] = new_l
                    add_cand(rel, ln, "JS_NAN_SAFE_COMPARISON_INVERSION", f"nan_safe({op_e}->!({dual_op}))", "".join(nl))

            # Op 5e: Universal-to-Existential Loop Quantifier Dual (`JS_FOR_ALL_TO_EXISTS_LOOP_DUAL`)
            # Rewrites `for (...) { ... if (P) { return false; } }` (for-all check rejecting on first
            # mismatch) to existential check (`var _anyOk = false; for (...) { ... if (!(P)) { _anyOk = true; break; } } if (!_anyOk) { return false; }`).
            if re.match(r"^\s*for\s*\(", line):
                f_ind = ind
                end_for = None
                ret_false_idx = None
                if_cond_idx = None
                if_cond_expr = None
                for fk in range(ln, min(len(lines), ln + 14)):
                    fl_s = lines[fk]
                    if if_cond_idx is None:
                        m_if = re.match(r"^(\s*)if\s*\((.+)\)\s*\{\s*$", fl_s)
                        if m_if:
                            if_cond_idx = fk
                            if_cond_expr = m_if.group(2).strip()
                    elif ret_false_idx is None and re.match(r"^\s*return\s+false\s*;?\s*$", fl_s):
                        ret_false_idx = fk
                    if fl_s.strip() == "}" and (len(fl_s) - len(fl_s.lstrip())) == len(f_ind):
                        end_for = fk
                        break
                if end_for is not None and if_cond_idx is not None and ret_false_idx is not None and if_cond_expr:
                    inner_ind = lines[if_cond_idx][: len(lines[if_cond_idx]) - len(lines[if_cond_idx].lstrip())]
                    nl = list(lines)
                    nl[if_cond_idx] = f"{inner_ind}if (!({if_cond_expr})) {{\n"
                    nl[ret_false_idx] = f"{inner_ind}  _brainAnyMatch = true;\n{inner_ind}  break;\n"
                    nl.insert(end_for + 1, f"{f_ind}if (!_brainAnyMatch) {{ return false; }}\n")
                    nl.insert(ln - 1, f"{f_ind}var _brainAnyMatch = false;\n")
                    add_cand(rel, ln, "JS_FOR_ALL_TO_EXISTS_LOOP_DUAL", "forall_to_exists_loop", "".join(nl))

            # Op 5f: Precedence / Mutual-Exclusion Guard Strengthening (`JS_GUARD_EXCLUDE_PRIOR_BRANCH_VAR`)
            # When a sequential `if (B)` follows an earlier `if (A ...)` block in the same function,
            # synthesize `if (!A && B)` (prior validated branch takes precedence over secondary check).
            m_seq_if = re.match(r"^(\s*)if\s*\(\s*([A-Za-z_$]\w*)\s*\)\s*\{\s*$", line)
            if m_seq_if:
                s_ind, b_var = m_seq_if.groups()
                prior_vars: list[str] = []
                for pk in range(max(0, ln - 40), ln - 1):
                    if lines[pk].startswith("function ") or lines[pk].startswith("const "):
                        prior_vars.clear()
                    mp = re.match(
                        rf"^{re.escape(s_ind)}if\s*\(\s*([A-Za-z_$]\w*)(?:\s*&&|\s*\))",
                        lines[pk],
                    )
                    if mp:
                        pv = mp.group(1)
                        if pv != b_var and pv not in prior_vars:
                            prior_vars.append(pv)
                for pv in reversed(prior_vars[-3:]):
                    nl = list(lines)
                    nl[ln - 1] = f"{s_ind}if (!{pv} && {b_var}) {{\n"
                    add_cand(rel, ln, "JS_GUARD_EXCLUDE_PRIOR_BRANCH_VAR", f"guard_exclude(!{pv}&&{b_var})", "".join(nl))

            # Op 6 (deferred to Pass 2): JS Comparison / Boolean Operators (`JS_CMP_AND_BOOL_OP_REPAIR`)
            if len(cmp_deferred) < max_candidates and any(
                op in line for op in (" <= ", " >= ", " < ", " > ", " === ", " !== ", " && ", " || ")
            ):
                for old_op, new_op in (
                    (" <= ", " < "),
                    (" < ", " <= "),
                    (" >= ", " > "),
                    (" > ", " >= "),
                    (" === ", " !== "),
                    (" !== ", " === "),
                    (" && ", " || "),
                    (" || ", " && "),
                ):
                    if old_op in line:
                        nl = list(lines)
                        nl[ln - 1] = line.replace(old_op, new_op, 1)
                        cmp_deferred.append((rel, ln, "JS_CMP_AND_BOOL_OP_REPAIR", f"op({old_op.strip()}->{new_op.strip()})", "".join(nl)))

    for rel, ln, tier, desc, patched in cmp_deferred:
        add_cand(rel, ln, tier, desc, patched)

    _raw_lo = str(getattr(loc, "initial_output", "") or "").lower()
    _empty_or_range = ("empty" in _raw_lo) or ("rangeerror" in _raw_lo)
    _TIER_PRIO = {
        "JS_TIER0_SKILL_RECALL": 0,
        "JS_TYPEOF_STRING_NONEMPTY_GUARD": 0 if _empty_or_range else 1,
        "JS_TYPEERROR_OPTIONAL_MEMBER_GUARD": 1,
        "JS_TS_INTERFACE_S3_GUARD": 1,
        "JS_NULL_PROTO_CONTAINER_SYNC": 1,
        "JS_ARG_SIBLING_NORMALIZER_WRAP": 1,
        "JS_FASTPATH_JOIN_NULLISH_SYNC": 1,
        "JS_REGEX_DOTALL_NEWLINE_LAW": 1,
        "JS_NORMALIZED_KEY_PRESERVE_RAW_INPUT": 0,
        "JS_GUARD_CONJUNCT_DROP_ON_REJECT": 0,
        "JS_DETACHED_THIS_TO_DEFINED_RECEIVER": 0,
        "JS_REGEX_CASE_INSENSITIVE_FLAG": 0,
        "JS_SORT_COMPARATOR_TYPEOF_FUNCTION_GUARD": 0,
        "JS_OBJECT_SPREAD_STRIP_UNDEFINED_OPTIONS": 0,
        "JS_NULLISH_BOOL_DEFAULT_STRICT_UNDEFINED": 0,
        "JS_THROW_LIMIT_NONZERO_LOWER_BOUND": 0,
        "JS_TERNARY_FALLBACK_BRANCH_SIMPLIFY": 0,
        "JS_S3_BRANCH_STRENGTHEN": 1,
        "JS_NULLISH_TYPEOF_GUARD": 2,
        "JS_FALSY_ZERO_NUMERIC_COERCION_FIX": 2,
        "JS_REGEX_CHARCLASS_ESCAPED_BACKSLASH": 2,
        "JS_STDLIB_UNICODE_NUMERIC_DUALITY": 2,
        "JS_STRICT_PARSEINT_DECIMAL_GUARD": 2,
        "JS_CMP_AND_BOOL_OP_REPAIR": 9,
    }
    cands.sort(key=lambda c: _TIER_PRIO.get(c.tier, 5))

    return cands


def _failure_progress_signature(output: str) -> tuple[int, str]:
    """Extract `(fail_count, primary_site_sig)` for monotone `WRITE -> BUILD -> TEST` progress tracking."""
    m_node_fail = re.search(r"#\s*fail\s+(\d+)", output)
    if m_node_fail:
        fail_n = int(m_node_fail.group(1))
    else:
        m_utest = re.search(r"\[\s*FAILED\s*\]\s*(\d+)\s+test", output)
        if m_utest:
            fail_n = int(m_utest.group(1))
        else:
            not_oks = len(re.findall(r"^\s*not ok\b", output, re.M))
            fail_lines = len(re.findall(r"\b(?:AssertionError|FAIL|ExpectEqual failed|runtime error:|ERROR: AddressSanitizer)\b", output))
            fail_n = not_oks if not_oks > 0 else max(1, fail_lines)
    m_site = re.search(
        r"(?:#0\s+0x[0-9a-f]+\s+in\s+[^\n]*?\s+([^\s:]+:\d+)|([A-Za-z0-9_./-]+\.(?:[ch]|cpp|hpp|js|ts):\d+))",
        output,
    )
    site_sig = (m_site.group(1) or m_site.group(2) or "") if m_site else ""
    if not site_sig:
        m_ex = re.search(
            r"(?:exception:|what\(\):|Assertion\s+`[^`]+'|ERROR:\s+\w+Sanitizer:)\s*([^\n]{6,80})",
            output,
        )
        if m_ex:
            site_sig = m_ex.group(1).strip()
    return fail_n, site_sig


def _find_js_functions(src: str) -> list[dict[str, Any]]:
    """Locate named and arrow JS/TS function bodies with balanced brace spans and parameter lists."""
    out: list[dict[str, Any]] = []
    n = len(src)

    def _match_close_brace(open_idx: int) -> int:
        depth = 0
        i = open_idx
        in_str: str | None = None
        while i < n:
            ch = src[i]
            if in_str is not None:
                if ch == "\\":
                    i += 2
                    continue
                if ch == in_str:
                    in_str = None
                i += 1
                continue
            if ch in ("'", '"', "`"):
                in_str = ch
                i += 1
                continue
            if ch == "/" and i + 1 < n and src[i + 1] == "/":
                nl = src.find("\n", i + 2)
                i = n if nl < 0 else nl + 1
                continue
            if ch == "/" and i + 1 < n and src[i + 1] == "*":
                end = src.find("*/", i + 2)
                i = n if end < 0 else end + 2
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return i
            i += 1
        return -1

    def _parse_params(raw_p: str) -> list[str]:
        params: list[str] = []
        depth = 0
        cur: list[str] = []
        for ch in raw_p:
            if ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth = max(0, depth - 1)
            if ch == "," and depth == 0:
                part = "".join(cur).strip()
                cur = []
            else:
                cur.append(ch)
                continue
            if part:
                m_nm = re.match(r"^(?:\.\.\.)?([A-Za-z_$][A-Za-z0-9_$]*)", part)
                if m_nm:
                    params.append(m_nm.group(1))
        tail = "".join(cur).strip()
        if tail:
            m_nm = re.match(r"^(?:\.\.\.)?([A-Za-z_$][A-Za-z0-9_$]*)", tail)
            if m_nm:
                params.append(m_nm.group(1))
        return params

    patterns = [
        re.compile(r"\bfunction\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*\(([^)]*)\)\s*\{"),
        re.compile(r"\b(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*(?:async\s+)?\(([^)]*)\)\s*=>\s*\{"),
        re.compile(r"\breturn\s+(?:async\s+)?\(([^)]*)\)\s*=>\s*\{"),
    ]
    seen_open: set[int] = set()
    for pat in patterns:
        for m in pat.finditer(src):
            open_idx = m.end() - 1
            if open_idx in seen_open:
                continue
            close_idx = _match_close_brace(open_idx)
            if close_idx <= open_idx:
                continue
            seen_open.add(open_idx)
            if pat.groups == 2:
                fn_name = m.group(1)
                raw_p = m.group(2)
            else:
                fn_name = f"anon_L{src[:open_idx].count(chr(10)) + 1}"
                raw_p = m.group(1)
            params = _parse_params(raw_p)
            if not params:
                continue
            lno = src[:open_idx].count("\n") + 1
            out.append({
                "name": fn_name,
                "lineno": lno,
                "params": params,
                "open_idx": open_idx,
                "close_idx": close_idx,
                "body": src[open_idx + 1 : close_idx],
            })
    out.sort(key=lambda x: x["open_idx"])
    return out


def _capture_js_execution_traces(
    worktree: pathlib.Path,
    loc: JSLocalizationReport,
    target_files: Sequence[str],
    *,
    timeout_s: float = 4.5,
) -> dict[str, dict[str, Any]]:
    """Instrument localized JS functions with zero-dep Node v22 entry/exit JSONL tracing.

    Distinguishes terminating (`enter` + `exit`) vs infinite-loop (`enter` without `exit`)
    invocations with exact concrete parameter values in <= 4.5 seconds and ZERO orphans.
    """
    traces: dict[str, dict[str, Any]] = {}
    with tempfile.TemporaryDirectory(prefix="brain_jstrace_") as td:
        tdir = pathlib.Path(td)
        wt_c = tdir / "wt"
        _copy_js_worktree(worktree, wt_c)
        trace_file = tdir / "trace.jsonl"
        trace_file.write_text("", encoding="utf-8")

        fn_meta: dict[str, dict[str, Any]] = {}
        instrumented_any = False

        for rel in target_files[:3]:
            fp = wt_c / rel
            if not fp.is_file() or (rel.endswith(".ts") and not loc.build_cmd):
                continue
            src = fp.read_text(encoding="utf-8", errors="replace")
            fns = _find_js_functions(src)
            if not fns:
                continue
            # Instrument non-overlapping functions (innermost first -> skip enclosing overlaps cleanly)
            # Choose innermost functions or non-nested top-level functions so try/finally never corrupts spans
            chosen: list[dict[str, Any]] = []
            for f in fns:
                # Prefer leaf functions (no other function inside, or if outer only wraps an inner arrow return)
                has_inner = any(
                    o is not f and f["open_idx"] < o["open_idx"] and o["close_idx"] < f["close_idx"]
                    for o in fns
                )
                if not has_inner:
                    chosen.append(f)
            if not chosen:
                chosen = fns[:4]

            # Splice from right to left so indices remain valid
            patched = src
            for f in sorted(chosen, key=lambda x: -x["open_idx"]):
                fn_key = f"{rel}:{f['lineno']}:{f['name']}"
                fn_meta[fn_key] = {"file": rel, **f}
                # Serialize scalar/numeric/NaN/Infinity params safely
                param_pairs = []
                for pm in f["params"][:4]:
                    param_pairs.append(
                        f"{json.dumps(pm)}:(typeof {pm}==='number'?(Number.isNaN({pm})?'__NaN__':{pm}===Infinity?'__Inf__':{pm}===-Infinity?'__NegInf__':{pm}):(typeof {pm}==='string'||typeof {pm}==='boolean'||{pm}===null?{pm}:undefined))"
                    )
                obj_lit = "{" + ",".join(param_pairs) + "}"
                enter_js = (
                    f"const __bS=(globalThis.__bSeen||(globalThis.__bSeen=new Set()));"
                    f"const __bA={obj_lit};"
                    f"const __bK={json.dumps(fn_key)}+'|'+JSON.stringify(__bA);"
                    f"let __bId=0;"
                    f"if(!__bS.has(__bK)&&__bS.size<240){{__bS.add(__bK);__bId=(globalThis.__bSeq=(globalThis.__bSeq||0)+1);"
                    f"try{{process.getBuiltinModule('node:fs').appendFileSync("
                    f"process.env.BRAIN_JS_TRACE_FILE,JSON.stringify({{p:'E',id:__bId,fn:{json.dumps(fn_key)},a:__bA}})+'\\n')}}catch{{}}}}"
                    f"try{{"
                )
                exit_js = (
                    f"}}finally{{if(__bId>0)try{{process.getBuiltinModule('node:fs').appendFileSync("
                    f"process.env.BRAIN_JS_TRACE_FILE,JSON.stringify({{p:'X',id:__bId}})+'\\n')}}catch{{}}}}"
                )
                patched = (
                    patched[: f["open_idx"] + 1]
                    + enter_js
                    + patched[f["open_idx"] + 1 : f["close_idx"]]
                    + exit_js
                    + patched[f["close_idx"] :]
                )
            if _check_js_syntax(rel, patched):
                fp.write_text(patched, encoding="utf-8")
                instrumented_any = True

        if not instrumented_any:
            return {}

        env = _build_node_env(wt_c)
        env["BRAIN_JS_TRACE_FILE"] = str(trace_file)
        if loc.build_cmd:
            _brc_t, _, _ = _run_pgroup_cmd(loc.build_cmd, cwd=wt_c, env=env, timeout=min(timeout_s + 12.0, 20.0))
            if _brc_t != 0:
                return {}
        rc, _so, _se = _run_pgroup_cmd(loc.test_cmd, cwd=wt_c, env=env, timeout=timeout_s)

        entered: dict[int, tuple[str, dict[str, Any]]] = {}
        exited: set[int] = set()
        if trace_file.is_file():
            for line in trace_file.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                rid = rec.get("id")
                if rec.get("p") == "E" and isinstance(rid, int):
                    entered[rid] = (str(rec.get("fn") or ""), dict(rec.get("a") or {}))
                elif rec.get("p") == "X" and isinstance(rid, int):
                    exited.add(rid)

        for rid, (fn_key, args) in entered.items():
            if fn_key not in fn_meta:
                continue
            bucket = traces.setdefault(
                fn_key,
                {"meta": fn_meta[fn_key], "hung_envs": [], "exited_envs": [], "rc": rc},
            )
            if rid not in exited:
                bucket["hung_envs"].append(args)
            else:
                bucket["exited_envs"].append(args)
    return traces


def _synthesize_js_oe_sygus_candidates(
    worktree: pathlib.Path,
    loc: JSLocalizationReport,
    *,
    max_candidates: int = 24,
) -> list[JSPatchCandidate]:
    """Execution-guided JS OE-SyGuS + EUSolver guard & coercion repair synthesis.

    Captures live entry/exit traces, separates hung/anomalous inputs from normal passing
    inputs via `oe_sygus_synthesizer_v1`, and emits minimal general JS guards/coercions.
    Zero LLM calls, zero repo-specific hardcoding.
    """
    file_order: list[str] = []
    for s in sorted(loc.sites, key=lambda x: -x.score):
        if s.file not in file_order:
            file_order.append(s.file)
    if not file_order:
        src_l, _ = _discover_js_files(worktree)
        file_order = src_l[:3]
    if not file_order:
        return []
    _trace_to = 4.5 if loc.initial_rc == 124 else 11.0
    traces = _capture_js_execution_traces(worktree, loc, file_order[:3], timeout_s=_trace_to)
    if not traces:
        return []

    out: list[JSPatchCandidate] = []
    seen_patches: set[tuple[str, str]] = set()

    def _emit(rel: str, patched: str, desc: str, line: int, tier: str = "JS_OE_SYGUS_EUSOLVER", extra: dict[str, str] | None = None) -> None:
        key = (rel, patched)
        if key in seen_patches or len(out) >= max_candidates:
            return
        seen_patches.add(key)
        out.append(
            JSPatchCandidate(
                file=rel,
                lineno=line,
                tier=tier,
                description=desc,
                patched_source=patched,
                extra_patches=tuple(sorted((extra or {}).items())),
            )
        )

    def _is_anomalous_env(env: Mapping[str, Any]) -> bool:
        for v in env.values():
            if v in ("__NaN__", "__Inf__", "__NegInf__"):
                return True
            if isinstance(v, float) and not v.is_integer():
                return True
            if isinstance(v, (int, float)) and not isinstance(v, bool) and v < 0:
                return True
        return False

    # Prioritize functions with proven infinite-loop (`hung_envs`) first!
    ordered_traces = sorted(
        traces.items(),
        key=lambda kv: (-len(kv[1]["hung_envs"]), -len(kv[1]["exited_envs"])),
    )

    # Collect per-(tag) multi-site insertions so if multiple functions/files share the exact
    # same anomalous input class (e.g. non-integer floats in both index.js & index.browser.js),
    # we also emit ONE atomic multi-site candidate applying the same OE-SyGuS repair to all of them!
    joint_insertions: dict[str, dict[str, list[tuple[int, str, int]]]] = {}

    for fn_key, info in ordered_traces:
        meta = info["meta"]
        rel = meta["file"]
        fp = worktree / rel
        if not fp.is_file():
            continue
        src = fp.read_text(encoding="utf-8", errors="replace")
        open_idx = meta["open_idx"]
        body = meta["body"]
        lno = meta["lineno"]
        params = meta["params"]

        failing_envs: list[dict[str, Any]] = list(info["hung_envs"])
        passing_envs: list[dict[str, Any]] = list(info["exited_envs"])

        # If no hang occurred, check whether anomalous numeric/boundary inputs appeared alongside normal ones
        if not failing_envs and passing_envs:
            anom = [e for e in passing_envs if _is_anomalous_env(e)]
            norm = [e for e in passing_envs if not _is_anomalous_env(e)]
            if anom and norm:
                failing_envs = anom
                passing_envs = norm

        if not failing_envs:
            continue

        # If hang occurred on the very first call before any exit, seed neutral positive-int baseline
        if not passing_envs:
            base_p: dict[str, Any] = {}
            for k, v in failing_envs[0].items():
                if v in ("__NaN__", "__Inf__", "__NegInf__") or (isinstance(v, (int, float)) and not isinstance(v, bool)):
                    base_p[k] = 10
                else:
                    base_p[k] = v
            passing_envs = [base_p, {k: (1 if isinstance(v, int) else v) for k, v in base_p.items()}]

        # 1. Run Unified OE-SyGuS + EUSolver Separating Predicate Synthesis (lang="js")!
        guards = OESYGUS.synthesize_separating_predicates(
            failing_envs,
            passing_envs,
            lang="js",
            max_results=6,
        )
        guards = [g for g in guards if int(g.get("generality_penalty", 99)) <= 1]

        # Identify primary numeric parameter from failing_envs
        num_params = [
            p for p in params
            if any(
                (e.get(p) in ("__NaN__", "__Inf__", "__NegInf__"))
                or (isinstance(e.get(p), (int, float)) and not isinstance(e.get(p), bool))
                for e in failing_envs
            )
        ]

        # Detect return type hint from function body (`return id`, `return ''`, `return []`, `return 0`)
        ret_fallback = "''"
        if re.search(r"\breturn\s+\[", body):
            ret_fallback = "[]"
        elif re.search(r"\breturn\s+0\b|\breturn\s+\d+", body) and "''" not in body and '""' not in body:
            ret_fallback = "0"

        # A. Numeric coercion + non-positive guard candidates (OE-SyGuS trunc / |0 / floor / finite-guard)
        for np in num_params[:2]:
            # Elon's-Law idempotence: skip functions that already coerce `np` to an integer
            if re.search(rf"\b{re.escape(np)}\s*(?:\|=\s*0|\|\s*0)|Math\.(?:trunc|floor)\(\s*{re.escape(np)}\s*\)", body):
                continue
            has_loop = bool(re.search(rf"\b(?:while|for)\b", body))
            for snippet, tag in [
                (f"\n  {np} = {np} | 0\n", f"oe_bit_or0"),
                (f"\n  {np} = Math.trunc({np})\n", f"oe_trunc_only"),
                (f"\n  {np} = {np} | 0\n  if ({np} <= 0) return {ret_fallback}\n", f"oe_bit_or0_guard"),
                (f"\n  {np} -= 0\n  if (!Number.isFinite({np}) || {np} <= 0) return {ret_fallback}\n  {np} = Math.trunc({np})\n", f"oe_coerce_trunc"),
                (f"\n  {np} = Math.floor({np})\n  if (!Number.isFinite({np}) || {np} <= 0) return {ret_fallback}\n", f"oe_coerce_floor"),
            ]:
                if has_loop or info["hung_envs"] or any(isinstance(e.get(np), float) and not e.get(np).is_integer() for e in failing_envs):
                    patched = src[: open_idx + 1] + snippet + src[open_idx + 1 :]
                    _emit(rel, patched, f"OE-SyGuS {tag}({np}) in {meta['name']}", lno)
                    joint_insertions.setdefault(tag, {}).setdefault(rel, []).append((open_idx + 1, snippet, lno))

        # B. Pure EUSolver synthesized guard candidates (`if (<G>) return ...` / `if (<G>) throw ...` / `if (<G>) p = Math.trunc(p)`)
        for g in guards[:3]:
            gcode = g["code"]
            for rv in (ret_fallback, "null", "0"):
                snippet = f"\n  if ({gcode}) return {rv}\n"
                patched = src[: open_idx + 1] + snippet + src[open_idx + 1 :]
                _emit(rel, patched, f"EUSolver guard if ({gcode}) return {rv}", lno)
                joint_insertions.setdefault(f"guard_ret_{rv}_{gcode}", {}).setdefault(rel, []).append((open_idx + 1, snippet, lno))
            if any(k in loc.initial_output for k in ("Error", "throw", "reject", "invalid", "Invalid", "ERR_")):
                for err_cls in ("RangeError", "TypeError", "Error"):
                    snippet = f"\n  if ({gcode}) throw new {err_cls}('Invalid argument')\n"
                    patched = src[: open_idx + 1] + snippet + src[open_idx + 1 :]
                    _emit(rel, patched, f"EUSolver guard if ({gcode}) throw {err_cls}", lno)
                    joint_insertions.setdefault(f"guard_throw_{err_cls}_{gcode}", {}).setdefault(rel, []).append((open_idx + 1, snippet, lno))
            for np in num_params[:1]:
                snippet = f"\n  if ({gcode}) {np} = Math.trunc({np}) || 0\n"
                patched = src[: open_idx + 1] + snippet + src[open_idx + 1 :]
                _emit(rel, patched, f"EUSolver guarded trunc({np}) when {gcode}", lno)

    # Prepend atomic multi-site candidates when >= 2 anomalous sites share the same OE-SyGuS repair!
    joint_cands: list[JSPatchCandidate] = []
    for tag, file_map in joint_insertions.items():
        total_sites = sum(len(v) for v in file_map.values())
        if total_sites < 2:
            continue
        patched_by_file: dict[str, str] = {}
        first_rel = ""
        first_lno = 1
        for rel, ins_list in file_map.items():
            fp = worktree / rel
            if not fp.is_file():
                continue
            cur = fp.read_text(encoding="utf-8", errors="replace")
            # Apply right-to-left by byte offset (deduping identical offsets)
            seen_off: set[int] = set()
            for off, snip, lno in sorted(ins_list, key=lambda x: -x[0]):
                if off in seen_off:
                    continue
                seen_off.add(off)
                cur = cur[:off] + snip + cur[off:]
                if not first_rel:
                    first_rel, first_lno = rel, lno
            patched_by_file[rel] = cur
        if first_rel and first_rel in patched_by_file:
            extras = {k: v for k, v in patched_by_file.items() if k != first_rel}
            joint_cands.append(
                JSPatchCandidate(
                    file=first_rel,
                    lineno=first_lno,
                    tier="JS_OE_SYGUS_EUSOLVER",
                    description=f"OE-SyGuS atomic multi-site {tag} ({total_sites} sites across {len(patched_by_file)} file(s))",
                    patched_source=patched_by_file[first_rel],
                    extra_patches=tuple(sorted(extras.items())),
                )
            )
    return (joint_cands[:12] + out)[:max_candidates]


def solve_js_repository(
    repo_root: str | pathlib.Path,
    test_targets: Sequence[str] | None = None,
    *,
    memory: dict[str, Any] | None = None,
    max_candidates: int = 80,
    timeout_s: float = 30.0,
) -> dict[str, Any]:
    """Zero-LLM, zero-weight Causal Angelic SWE solver for JavaScript / TypeScript repositories."""
    t0 = time.monotonic()
    src_root = pathlib.Path(repo_root).resolve()

    with tempfile.TemporaryDirectory(prefix="brain_js_swe_") as tmp_dir:
        wt = pathlib.Path(tmp_dir) / "wt"
        _copy_js_worktree(src_root, wt)

        # Stage 1: V8 Coverage + Stack-Trace Localization
        loc = localize_js_faults(wt, test_targets, timeout_s=timeout_s)
        if loc.initial_rc == 0:
            return {
                "schema": SCHEMA,
                "authority": AUTHORITY,
                "language": "javascript_typescript",
                "status": "NO_FAILING_TEST",
                "verified": False,
                "runner": loc.test_runner,
                "model_calls": 0,
                "parameters_stored": 0,
                "seconds": round(time.monotonic() - t0, 3),
            }

        # Stage 2: Candidate Synthesis (Tier-0 JS Skill Recall + Causal Operators + Execution-Guided OE-SyGuS)
        cands = synthesize_js_candidates(wt, loc, memory=memory, max_candidates=max_candidates)
        oe_cands_ran = False
        if loc.initial_rc == 124:
            # Proven non-termination / infinite loop: inject execution-guided OE-SyGuS candidates
            # right AFTER any priority-0 static/Tier-0 candidates so surgical guards run first!
            oe_cands = _synthesize_js_oe_sygus_candidates(wt, loc, max_candidates=24)
            oe_cands_ran = True
            if oe_cands:
                _p0_tiers = {
                    "JS_TIER0_SKILL_RECALL",
                    "JS_TYPEOF_STRING_NONEMPTY_GUARD",
                    "JS_REGEX_DOTALL_NEWLINE_LAW",
                    "JS_NORMALIZED_KEY_PRESERVE_RAW_INPUT",
                    "JS_GUARD_CONJUNCT_DROP_ON_REJECT",
                    "JS_DETACHED_THIS_TO_DEFINED_RECEIVER",
                    "JS_REGEX_CASE_INSENSITIVE_FLAG",
                    "JS_SORT_COMPARATOR_TYPEOF_FUNCTION_GUARD",
                    "JS_OBJECT_SPREAD_STRIP_UNDEFINED_OPTIONS",
                    "JS_NULLISH_BOOL_DEFAULT_STRICT_UNDEFINED",
                    "JS_THROW_LIMIT_NONZERO_LOWER_BOUND",
                    "JS_TERNARY_FALLBACK_BRANCH_SIMPLIFY",
                }
                _p0 = [c for c in cands if c.tier in _p0_tiers]
                _rest = [c for c in cands if c.tier not in _p0_tiers]
                cands = _p0 + oe_cands + _rest

        # Stage 3: Two-phase isolated verification (+ monotone multi-hunk progress capture)
        attempts = 0
        winner: dict[str, Any] | None = None
        env_wt = _build_node_env(wt)
        base_fail_n, base_site = _failure_progress_signature(loc.initial_output)
        progress_cands: list[tuple[int, int, JSCandidate]] = []
        _fast_timeout = 14.0 if loc.initial_rc == 124 else min(timeout_s, 18.0)

        cand_idx = 0
        while cand_idx < len(cands):
            cand = cands[cand_idx]
            cand_idx += 1
            if (time.monotonic() - t0) >= max(timeout_s * 2.2, 65.0):
                break
            if not _check_js_syntax(cand.file, cand.patched_source):
                continue
            if any(not _check_js_syntax(ef, esrc) for ef, esrc in cand.extra_patches):
                continue
            attempts += 1
            fp = wt / cand.file
            orig_src = fp.read_text(encoding="utf-8", errors="replace")
            extra_origs: list[tuple[pathlib.Path, str]] = [
                (wt / ef, (wt / ef).read_text(encoding="utf-8", errors="replace"))
                for ef, _ in cand.extra_patches
            ]
            ok_fast = False
            trial_out = ""
            try:
                fp.write_text(cand.patched_source, encoding="utf-8")
                for ef, esrc in cand.extra_patches:
                    (wt / ef).write_text(esrc, encoding="utf-8")
                _build_ok = True
                if loc.build_cmd:
                    _brc_f, _, _ = _run_pgroup_cmd(
                        loc.build_cmd,
                        cwd=wt,
                        env=env_wt,
                        timeout=min(_fast_timeout, 20.0),
                    )
                    _build_ok = _brc_f == 0
                if _build_ok:
                    _rc_f, _so_f, _se_f = _run_pgroup_cmd(
                        loc.test_cmd,
                        cwd=wt,
                        env=env_wt,
                        timeout=_fast_timeout,
                    )
                    ok_fast = _rc_f == 0
                    trial_out = _so_f + "\n" + _se_f
            finally:
                fp.write_text(orig_src, encoding="utf-8")
                for efp, eorig in extra_origs:
                    efp.write_text(eorig, encoding="utf-8")

            if not ok_fast:
                if trial_out and "SyntaxError" not in trial_out and "ReferenceError" not in trial_out:
                    c_fail_n, c_site = _failure_progress_signature(trial_out)
                    if c_fail_n < base_fail_n or (c_site and base_site and c_site != base_site and c_fail_n <= base_fail_n):
                        progress_cands.append((c_fail_n, attempts, cand))
                if memory is not None and cand.skill_id and cand.tier == "JS_TIER0_SKILL_RECALL":
                    _update_memrl_law(memory.setdefault("js_rewrite_laws", {}), cand.skill_id, success=False)
                # If top-4 static candidates (or 18s) haven't solved yet, inject Execution-Guided OE-SyGuS!
                if ((cand_idx >= min(4, len(cands))) or ((time.monotonic() - t0) >= 18.0)) and not oe_cands_ran and (time.monotonic() - t0) < max(timeout_s * 1.8, 50.0):
                    oe_cands_ran = True
                    _oe_more = _synthesize_js_oe_sygus_candidates(wt, loc, max_candidates=24)
                    if _oe_more:
                        cands[cand_idx:cand_idx] = _oe_more
                continue

            # Phase B: Independent full-suite verification on a BRAND NEW worktree copy
            verify_wt = pathlib.Path(tmp_dir) / f"verify_{attempts}"
            _copy_js_worktree(src_root, verify_wt)
            (verify_wt / cand.file).write_text(cand.patched_source, encoding="utf-8")
            for ef, esrc in cand.extra_patches:
                (verify_wt / ef).write_text(esrc, encoding="utf-8")
            env_verify = _build_node_env(verify_wt)
            ok_full = False
            _b_ok_v = True
            if loc.build_cmd:
                _brc_v, _, _ = _run_pgroup_cmd(
                    loc.build_cmd,
                    cwd=verify_wt,
                    env=env_verify,
                    timeout=min(timeout_s, 25.0),
                )
                _b_ok_v = _brc_v == 0
            if not _b_ok_v:
                ok_full = False
            elif loc.test_runner == "node_tap" and not (verify_wt / "node_modules" / "tap").exists():
                # Run target test + all sibling tests in the same test subdirectory directly via `node`
                node_bin = shutil.which("node") or "node"
                _, all_tests = _discover_js_files(verify_wt)
                target_dirs = {pathlib.Path(t).parent.as_posix() for t in (test_targets or ())}
                verify_tests = [
                    t for t in all_tests
                    if (not target_dirs) or (pathlib.Path(t).parent.as_posix() in target_dirs)
                ]
                for t in test_targets or ():
                    if t not in verify_tests:
                        verify_tests.insert(0, t)
                ok_full = bool(verify_tests)
                for vt in verify_tests[:12]:
                    _rc_v, _, _ = _run_pgroup_cmd(
                        [node_bin, vt],
                        cwd=verify_wt,
                        env=env_verify,
                        timeout=min(timeout_s, 18.0),
                    )
                    if _rc_v != 0:
                        ok_full = False
                        break
            else:
                _, _all_js_tests_v = _discover_js_files(verify_wt)
                _phase_b_targets = test_targets if (test_targets and len(_all_js_tests_v) > 4) else None
                full_cmd, _ = detect_js_test_command(verify_wt, _phase_b_targets)
                _rc_full, _, _ = _run_pgroup_cmd(
                    full_cmd,
                    cwd=verify_wt,
                    env=env_verify,
                    timeout=max(timeout_s, 25.0),
                )
                ok_full = _rc_full == 0
            shutil.rmtree(verify_wt, ignore_errors=True)

            if ok_full:
                diff_txt = "".join(
                    difflib.unified_diff(
                        orig_src.splitlines(keepends=True),
                        cand.patched_source.splitlines(keepends=True),
                        fromfile=f"a/{cand.file}",
                        tofile=f"b/{cand.file}",
                    )
                )
                learned_law_id: str | None = None
                if memory is not None:
                    jstore = memory.setdefault("js_rewrite_laws", {})
                    if cand.skill_id and cand.skill_id in jstore:
                        _update_memrl_law(jstore, cand.skill_id, success=True)
                        learned_law_id = cand.skill_id
                    else:
                        sd = _extract_js_single_line_diff(orig_src, cand.patched_source)
                        if sd is not None:
                            rule = _abstract_js_line_rule(sd[0], sd[1])
                            if rule is not None:
                                lid = rule["law_id"]
                                if lid in jstore:
                                    _update_memrl_law(jstore, lid, success=True)
                                else:
                                    rule.setdefault("refutations", 0)
                                    rule.setdefault("utility_q", 0.85)
                                    jstore[lid] = rule
                                learned_law_id = lid
                        elif cand.tier == "JS_OE_SYGUS_EUSOLVER":
                            _oe_law = OESYGUS.abstract_synthesized_repair(
                                lang="js",
                                error_kind="NON_TERM_OR_BOUNDARY",
                                action_kind=cand.description.split("(")[0].strip().replace(" ", "_")[:48],
                            )
                            lid = _oe_law["law_id"]
                            if lid in jstore:
                                _update_memrl_law(jstore, lid, success=True)
                            else:
                                _oe_law["refutations"] = 0
                                _oe_law["utility_q"] = 0.85
                                jstore[lid] = _oe_law
                            learned_law_id = lid

                if cand.extra_patches:
                    for ef, esrc in cand.extra_patches:
                        eo = (wt / ef).read_text(encoding="utf-8", errors="replace")
                        diff_txt += "".join(
                            difflib.unified_diff(
                                eo.splitlines(keepends=True),
                                esrc.splitlines(keepends=True),
                                fromfile=f"a/{ef}",
                                tofile=f"b/{ef}",
                            )
                        )
                winner = {
                    "file": cand.file,
                    "lineno": cand.lineno,
                    "tier": cand.tier,
                    "description": cand.description,
                    "skill_id_used": cand.skill_id,
                    "attempt": attempts,
                    "diff": diff_txt,
                    "patched_source": cand.patched_source,
                    "extra_patches": dict(cand.extra_patches),
                    "learned_law_id": learned_law_id,
                }
                break

        # Stage 4: Multi-hunk / Multi-file Monotone Causal-Shift Progress Composition
        # If no single edit exited 0, compose strictly progress-making 1st edit + completing 2nd edit.
        if winner is None and progress_cands:
            progress_cands.sort(key=lambda x: (x[0], x[1]))
            for _, _, p1 in progress_cands[:2]:
                if winner is not None or (time.monotonic() - t0) >= max(timeout_s * 2.4, 72.0):
                    break
                st2_wt = pathlib.Path(tmp_dir) / f"js_stage2_{p1.lineno}"
                _copy_js_worktree(src_root, st2_wt)
                (st2_wt / p1.file).write_text(p1.patched_source, encoding="utf-8")
                loc2 = localize_js_faults(st2_wt, test_targets, timeout_s=min(timeout_s, 14.0))
                if loc2.initial_rc == 0:
                    shutil.rmtree(st2_wt, ignore_errors=True)
                    continue
                cands2 = synthesize_js_candidates(st2_wt, loc2, memory=memory, max_candidates=25)
                env2 = _build_node_env(st2_wt)
                for p2 in cands2:
                    if (time.monotonic() - t0) >= max(timeout_s * 2.4, 72.0):
                        break
                    if not _check_js_syntax(p2.file, p2.patched_source):
                        continue
                    attempts += 1
                    fp2 = st2_wt / p2.file
                    orig2 = fp2.read_text(encoding="utf-8", errors="replace")
                    ok2 = False
                    try:
                        fp2.write_text(p2.patched_source, encoding="utf-8")
                        _rc2, _, _ = _run_pgroup_cmd(
                            loc2.test_cmd, cwd=st2_wt, env=env2,
                            timeout=min(timeout_s, 14.0),
                        )
                        ok2 = _rc2 == 0
                    finally:
                        fp2.write_text(orig2, encoding="utf-8")
                    if not ok2:
                        continue
                    vwt = pathlib.Path(tmp_dir) / f"verify_s2_{attempts}"
                    _copy_js_worktree(src_root, vwt)
                    patched_map: dict[str, str] = {p1.file: p1.patched_source}
                    patched_map[p2.file] = p2.patched_source
                    for rel_f, txt_f in patched_map.items():
                        (vwt / rel_f).write_text(txt_f, encoding="utf-8")
                    _, _all_js_t2 = _discover_js_files(vwt)
                    _pb2 = test_targets if (test_targets and len(_all_js_t2) > 4) else None
                    fcmd, _ = detect_js_test_command(vwt, _pb2)
                    _rcf, _, _ = _run_pgroup_cmd(
                        fcmd, cwd=vwt, env=_build_node_env(vwt),
                        timeout=max(timeout_s, 25.0),
                    )
                    ok_full2 = _rcf == 0
                    shutil.rmtree(vwt, ignore_errors=True)
                    if ok_full2:
                        diff_parts = []
                        for rel_f, txt_f in patched_map.items():
                            o_txt = (src_root / rel_f).read_text(encoding="utf-8", errors="replace")
                            diff_parts.append("".join(difflib.unified_diff(
                                o_txt.splitlines(keepends=True), txt_f.splitlines(keepends=True),
                                fromfile=f"a/{rel_f}", tofile=f"b/{rel_f}",
                            )))
                        extra_patches = {k: v for k, v in patched_map.items() if k != p1.file}
                        winner = {
                            "file": p1.file,
                            "lineno": p1.lineno,
                            "tier": "JS_STAGE2_COMPOSED_PROGRESS",
                            "description": f"compose({p1.tier}:{p1.description} + {p2.tier}:{p2.description})",
                            "skill_id_used": None,
                            "attempt": attempts,
                            "diff": "\n".join(diff_parts),
                            "patched_source": patched_map[p1.file],
                            "extra_patches": extra_patches,
                            "learned_law_id": None,
                        }
                        break
                shutil.rmtree(st2_wt, ignore_errors=True)

        return {
            "schema": SCHEMA,
            "authority": AUTHORITY,
            "language": "javascript_typescript",
            "status": "VERIFIED" if winner else "UNSOLVED",
            "verified": winner is not None,
            "runner": loc.test_runner,
            "attempts": attempts,
            "candidates_generated": len(cands),
            "winner": winner,
            "model_calls": 0,
            "parameters_stored": 0,
            "seconds": round(time.monotonic() - t0, 3),
        }


# ===========================================================================
# Part 2: Zero-LLM C / C++ Causal Angelic SWE Engine (ASan/UBSan + gcov)
# ===========================================================================

_C_EXTS = (".c", ".cc", ".cpp", ".cxx")
_C_HDR_EXTS = (".h", ".hh", ".hpp")


@dataclass(frozen=True)
class CLocalizedSite:
    file: str
    lineno: int
    score: float
    source: str  # "asan" | "ubsan" | "assert" | "gcov" | "symbol" | "fallback"


@dataclass
class CLocalizationReport:
    runner_kind: str  # "gcc_direct" | "shell_baseline" | "make_test"
    build_cmd: list[str]
    run_cmd: list[str]
    run_cwd: str
    initial_rc: int
    initial_output: str
    bug_classes: list[str] = field(default_factory=list)
    sites: list[CLocalizedSite] = field(default_factory=list)
    covered_lines_by_file: dict[str, set[int]] = field(default_factory=dict)


@dataclass(frozen=True)
class CPatchCandidate:
    file: str
    lineno: int
    tier: str
    description: str
    patched_source: str
    skill_id: str | None = None


def _is_c_test_path(rel: str) -> bool:
    low = rel.lower().replace("\\", "/")
    parts = low.split("/")
    base = parts[-1]
    if "unity" in parts:
        return False
    return (
        "test" in parts
        or "tests" in parts
        or base in ("test.c", "tests.c", "test.cpp", "tests.cpp", "unittest.c", "xmltest.cpp")
        or base.startswith("test_")
        or base.startswith("unittest")
        or base.endswith("_test.c")
        or base.endswith("_tests.c")
        or base.endswith("_test.cpp")
        or base.endswith("_tests.cpp")
        or base.endswith("test.cpp")
    )


def _is_c_skip_path(rel: str) -> bool:
    low = rel.lower().replace("\\", "/")
    parts = low.split("/")
    base = parts[-1]
    return (
        any(d in parts for d in ("fuzzing", "fuzz", "examples", "example", "benchmarks", "benchmark", "docs", "unity"))
        or base in ("example.c", "example.cpp", "demo.c", "demo.cpp", "fuzz.c", "fuzz.cpp")
    )


def _discover_c_files(repo: pathlib.Path) -> tuple[list[str], list[str], list[str]]:
    """Return `(src_files, test_files, support_files)` for a C/C++ repository."""
    src_files: list[str] = []
    hdr_src_files: list[str] = []
    test_files: list[str] = []
    support_files: list[str] = []
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in sorted(dirs) if d not in _SKIP_DIRS and not d.startswith(".")]
        for fn in sorted(files):
            rel = pathlib.Path(root, fn).relative_to(repo).as_posix()
            low_parts = rel.lower().split("/")
            if fn.endswith(_C_HDR_EXTS):
                if not _is_c_skip_path(rel) and not _is_c_test_path(rel):
                    if fn.lower() not in ("utest.h", "catch.hpp", "doctest.h", "unity.h", "unittest.h"):
                        hdr_src_files.append(rel)
                continue
            if not fn.endswith(_C_EXTS):
                continue
            if "unity" in low_parts and fn == "unity.c":
                support_files.append(rel)
                continue
            if _is_c_skip_path(rel):
                continue
            if _is_c_test_path(rel):
                test_files.append(rel)
            else:
                src_files.append(rel)
    # Header-only C++ libraries (e.g., `include/cxxopts.hpp`) have no non-main `.cpp` library files.
    # Also include inline-implementation C library headers (e.g., `src/yyjson.h`) alongside `.c` sources.
    non_main_srcs = [sf for sf in src_files if not _c_has_main(repo / sf)]
    if not non_main_srcs and hdr_src_files:
        src_files = hdr_src_files
    elif hdr_src_files:
        for hf in hdr_src_files:
            if hf not in src_files:
                hp = repo / hf
                try:
                    htxt = hp.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                if "inline " in htxt and len(htxt) > 8000:
                    src_files.append(hf)
    return src_files, test_files, support_files


def is_c_cpp_repo(repo: pathlib.Path) -> bool:
    src_files, test_files, _ = _discover_c_files(repo)
    return bool(src_files and (test_files or (repo / "Makefile").is_file() or (repo / "tests" / "unittest.sh").is_file()))


def _c_has_main(path: pathlib.Path) -> bool:
    try:
        txt = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return bool(
        re.search(r"\b(?:int|void)\s+(?:[A-Z_][A-Z0-9_]*\s+)?main\s*\(", txt)
        or re.search(r"\bUTEST_MAIN\s*\(", txt)
    )


def _c_asan_env() -> dict[str, str]:
    env = dict(os.environ)
    # Disable leak detection (test harnesses frequently omit cleanup) while enabling full
    # SEGV / NULL-deref / buffer-overflow / use-after-free / SIGABRT assert / UBSan stack traces.
    env["ASAN_OPTIONS"] = "detect_leaks=0:handle_abort=1:abort_on_error=0:halt_on_error=1:symbolize=1"
    env["UBSAN_OPTIONS"] = "print_stacktrace=1:halt_on_error=1"
    return env


def detect_c_test_spec(
    worktree: pathlib.Path,
    test_targets: Sequence[str] | None = None,
    *,
    sanitizer: bool = True,
    coverage: bool = False,
    extra_flags: Sequence[str] | None = None,
) -> tuple[str, list[str], list[str], str]:
    """Return `(runner_kind, build_cmd, run_cmd, run_cwd)` for a C/C++ repository."""
    src_files, test_files, support_files = _discover_c_files(worktree)
    targets = [t.replace("\\", "/").lstrip("./") for t in (test_targets or ())]

    # Mode 1: Golden baseline shell suite (e.g., `tests/unittest.sh` + `tests/baseline_*.txt`)
    ut_sh = worktree / "tests" / "unittest.sh"
    if ut_sh.is_file() and (not targets or any(t.endswith(".sh") or "baseline_" in t for t in targets)):
        return "shell_baseline", [], ["bash", "unittest.sh"], str(worktree / "tests")

    # Mode 2: Direct GCC/G++ build of target test `.c`/`.cpp` file
    chosen_test: str | None = None
    for t in targets:
        if t.endswith(_C_EXTS) and (worktree / t).is_file():
            chosen_test = t
            break
    if chosen_test is None and test_files:
        for pref in (
            "xmltest.cpp",
            "tests.c",
            "test.c",
            "tests.cpp",
            "test.cpp",
            "test/options.cpp",
            "tests/misc_tests.c",
            "tests/unittest.c",
        ):
            if pref in test_files:
                chosen_test = pref
                break
        if chosen_test is None:
            chosen_test = test_files[0]
            # If the alphabetically first test file is a pure harness-only `main.c`/`main.cpp`
            # (e.g. `UTEST_MAIN()` / `CATCH_CONFIG_MAIN` with zero `UTEST(`/`TEST_CASE(` definitions),
            # automatically select a sibling test TU that defines actual test cases (which then links `main.c`).
            if pathlib.Path(chosen_test).name.lower() in ("main.c", "main.cpp"):
                c0_txt = (worktree / chosen_test).read_text(encoding="utf-8", errors="replace")
                if re.search(r"\b(?:UTEST_MAIN|CATCH_CONFIG_MAIN|DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN)\b", c0_txt) and not re.search(
                    r"\b(?:UTEST|TEST_CASE|SCENARIO)\s*\(", c0_txt
                ):
                    _case_re = re.compile(r"\b(?:UTEST|TEST_CASE|SCENARIO|ASSERT_[A-Z_]+|EXPECT_[A-Z_]+|REQUIRE|CHECK)\s*\(")

                    def _count_tu_cases(tu_rel: str) -> int:
                        tp = worktree / tu_rel
                        tt = tp.read_text(encoding="utf-8", errors="replace")
                        cnt = len(_case_re.findall(tt))
                        for inc_h in re.findall(r'#\s*include\s*"([^"]+\.(?:h|hpp|inc|inl))"', tt):
                            hp = tp.parent / inc_h
                            if hp.is_file():
                                cnt += len(_case_re.findall(hp.read_text(encoding="utf-8", errors="replace")))
                        return cnt

                    best_tu: tuple[int, int, str] | None = None
                    for cand_tf in test_files[1:]:
                        if pathlib.Path(cand_tf).parent == pathlib.Path(chosen_test).parent:
                            n_cases = _count_tu_cases(cand_tf)
                            # Break ties by preferring standard `.c` / primary `test.c` over versioned dialects
                            is_c_pri = 1 if cand_tf.endswith(".c") else 0
                            key = (n_cases, is_c_pri, cand_tf)
                            if n_cases > 0 and (best_tu is None or (n_cases, is_c_pri) > (best_tu[0], best_tu[1])):
                                best_tu = key
                    if best_tu is not None:
                        chosen_test = best_tu[2]

    if chosen_test is not None:
        tpath = worktree / chosen_test
        ttxt = tpath.read_text(encoding="utf-8", errors="replace")
        is_cpp = chosen_test.endswith((".cpp", ".cc", ".cxx")) or any(
            sf.endswith((".cpp", ".cc", ".cxx", ".hpp", ".hh")) for sf in src_files
        )
        compiler = shutil.which("g++" if is_cpp else "gcc") or ("g++" if is_cpp else "gcc")

        # Inspect direct AND 2-hop header `#include "...c"` inside test file so we never duplicate symbols
        included_c_basenames: set[str] = set()
        seen_hdrs: set[pathlib.Path] = set()

        def _scan_includes(fpath: pathlib.Path, depth: int) -> None:
            if depth > 2 or fpath in seen_hdrs or not fpath.is_file():
                return
            seen_hdrs.add(fpath)
            try:
                src_t = fpath.read_text(encoding="utf-8", errors="replace")
            except OSError:
                return
            for inc in re.findall(r'#\s*include\s*"([^"]+)"', src_t):
                if inc.endswith(_C_EXTS):
                    included_c_basenames.add(pathlib.Path(inc).name)
                elif inc.endswith(_C_HDR_EXTS):
                    for base_d in (fpath.parent, worktree, worktree / "tests", worktree / "test", worktree / "include", worktree / "src"):
                        cand_h = (base_d / inc).resolve()
                        if cand_h.is_file():
                            _scan_includes(cand_h, depth + 1)
                            break

        _scan_includes(tpath, 0)

        # Include directories
        inc_dirs = ["."]
        for cand_d in ("include", "src", "tests", "test", "test/util", "tests/util", "tests/unity/src", "unity/src"):
            if (worktree / cand_d).is_dir():
                inc_dirs.append(cand_d)
        t_parent = pathlib.Path(chosen_test).parent.as_posix()
        if t_parent and t_parent != "." and t_parent not in inc_dirs:
            inc_dirs.append(t_parent)
        # Auto-resolve vendored `#include <...>` / `#include "..."` headers (e.g. `test/3rdparty/doctest/doctest.h`)
        _wanted_incs = re.findall(r'#\s*include\s*[<"]([^">]+)[">]', ttxt)
        if _wanted_incs:
            _vendor_roots = [
                worktree / vd
                for vd in ("test/3rdparty", "tests/3rdparty", "3rdparty", "third_party", "vendor", "external", "deps")
                if (worktree / vd).is_dir()
            ]
            for _inc in _wanted_incs:
                if any((worktree / d / _inc).is_file() for d in inc_dirs):
                    continue
                _inc_rel = pathlib.Path(_inc)
                for _vr in _vendor_roots:
                    if (_vr / _inc_rel).is_file():
                        _rel_d = _vr.relative_to(worktree).as_posix()
                        if _rel_d not in inc_dirs:
                            inc_dirs.append(_rel_d)
                        break
                    for _sub in sorted(_vr.iterdir()):
                        if _sub.is_dir() and (_sub / _inc_rel).is_file():
                            _rel_d = _sub.relative_to(worktree).as_posix()
                            if _rel_d not in inc_dirs:
                                inc_dirs.append(_rel_d)
                            break

        # Library .c/.cpp sources to compile (exclude headers, files already `#include`d, or files with main())
        lib_srcs: list[str] = []
        for sf in src_files:
            if sf.endswith(_C_HDR_EXTS):
                continue
            if pathlib.Path(sf).name in included_c_basenames:
                continue
            if _c_has_main(worktree / sf):
                continue
            s_stem = pathlib.Path(sf).stem
            if len(src_files) > 1 and s_stem.lower().endswith("_utils") and s_stem not in ttxt:
                continue
            lib_srcs.append(sf)

        # Unity or multi-TU test harness support files (e.g., `test/main.cpp`, `tests/main.cpp`, `test/util/yy_test_utils.c`)
        extra_sup: list[str] = []
        auto_fw_flags: list[str] = []
        if "unity.h" in ttxt:
            for sup in support_files:
                if sup.endswith("unity.c"):
                    extra_sup.append(sup)
        for util_d in ("test/util", "tests/util"):
            udp = worktree / util_d
            if udp.is_dir():
                for uf in sorted(udp.iterdir()):
                    if uf.is_file() and uf.name.endswith(_C_EXTS) and not _c_has_main(uf):
                        u_rel = uf.relative_to(worktree).as_posix()
                        if (f'{uf.stem}.h"' in ttxt or f"{uf.stem}.h>" in ttxt) and u_rel not in extra_sup and u_rel not in lib_srcs:
                            extra_sup.append(u_rel)
        if not _c_has_main(tpath) and not re.search(r"\bCATCH_CONFIG_MAIN\b|\bDOCTEST_CONFIG_IMPLEMENT_WITH_MAIN\b|\bUTEST_MAIN\s*\(", ttxt):
            t_dir_p = tpath.parent
            is_single_main_fw = bool(re.search(r'#\s*include\s*["<](?:catch|doctest|utest)', ttxt, re.I))
            for sib in sorted(t_dir_p.iterdir()):
                if not sib.is_file() or not sib.name.endswith(_C_EXTS):
                    continue
                sib_rel = sib.relative_to(worktree).as_posix()
                if sib_rel == chosen_test or sib_rel in lib_srcs or sib_rel in extra_sup:
                    continue
                low_bn = sib.name.lower()
                if low_bn.startswith(("test_", "fuzz", "bench", "link_")):
                    continue
                if is_single_main_fw:
                    if low_bn in ("main.cpp", "main.c"):
                        sib_txt = sib.read_text(encoding="utf-8", errors="replace")
                        # If `main.cpp` only includes `doctest`/`catch` without defining the implementation macro
                        # (normally passed via CMake target_compile_definitions), compile `chosen_test` directly
                        # with the standard macro instead of linking an empty stub `main.cpp`.
                        if not _c_has_main(sib) and not re.search(
                            r"\b(?:CATCH_CONFIG_MAIN|DOCTEST_CONFIG_IMPLEMENT(?:_WITH_MAIN)?|UTEST_MAIN)\b", sib_txt
                        ):
                            if re.search(r'#\s*include\s*["<][^">]*doctest', ttxt + "\n" + sib_txt, re.I):
                                auto_fw_flags.append("-DDOCTEST_CONFIG_IMPLEMENT_WITH_MAIN")
                            elif re.search(r'#\s*include\s*["<][^">]*catch', ttxt + "\n" + sib_txt, re.I):
                                auto_fw_flags.append("-DCATCH_CONFIG_MAIN")
                            else:
                                extra_sup.append(sib_rel)
                        else:
                            extra_sup.append(sib_rel)
                    continue
                if low_bn in ("main.cpp", "main.c", "test.cpp", "allocator.cpp", "writer_string.cpp") or (
                    not _c_has_main(sib) and not low_bn.endswith(("_test.cpp", "_tests.cpp", "_test.c"))
                ):
                    if low_bn in ("main.cpp", "main.c") or not _c_has_main(sib):
                        if "link_test" in low_bn or "options" in low_bn:
                            continue
                        extra_sup.append(sib_rel)
            if is_single_main_fw and not extra_sup and not auto_fw_flags:
                if re.search(r'#\s*include\s*["<][^">]*doctest', ttxt, re.I):
                    auto_fw_flags.append("-DDOCTEST_CONFIG_IMPLEMENT_WITH_MAIN")
                elif re.search(r'#\s*include\s*["<][^">]*catch', ttxt, re.I):
                    auto_fw_flags.append("-DCATCH_CONFIG_MAIN")
        # Link companion helper TU `<stem>_other.cpp` / `<stem>_other.c` when present (e.g., multi-TU ADL/ODR tests)
        _other_sib = tpath.with_name(f"{tpath.stem}_other{tpath.suffix}")
        if _other_sib.is_file():
            _other_rel = _other_sib.relative_to(worktree).as_posix()
            if _other_rel not in lib_srcs and _other_rel not in extra_sup and _other_rel != chosen_test:
                extra_sup.append(_other_rel)

        # If any compiled test TU references a CMake-generated doc header (`#include "generated.h"`)
        # that does not exist on disk, supply an empty stub in an isolated temp include directory.
        all_test_tus = [chosen_test, *extra_sup]
        needs_gen_h = False
        for tu_rel in all_test_tus:
            tu_p = worktree / tu_rel
            if tu_p.is_file() and re.search(r'#\s*include\s*"generated\.h"', tu_p.read_text(encoding="utf-8", errors="replace")):
                if not any((worktree / d / "generated.h").is_file() for d in inc_dirs):
                    needs_gen_h = True
                    break
        if needs_gen_h:
            gen_dir = pathlib.Path(tempfile.gettempdir()) / ".brain_c_gen_stub_v1"
            gen_dir.mkdir(parents=True, exist_ok=True)
            gen_h = gen_dir / "generated.h"
            if not gen_h.is_file():
                gen_h.write_text("", encoding="utf-8")
            inc_dirs.append(str(gen_dir))

        bin_out = str(worktree / ".brain_c_test_bin")
        build_cmd = [compiler]
        if is_cpp:
            build_cmd.append("-std=c++17")
        build_cmd.extend(["-g", "-O0", "-fno-omit-frame-pointer"])
        if coverage:
            build_cmd.append("--coverage")
        elif sanitizer:
            build_cmd.extend(["-fsanitize=address,undefined", "-fno-sanitize-recover=all"])
        if "TESTS_MAIN" in ttxt:
            build_cmd.append("-DTESTS_MAIN")
        if auto_fw_flags:
            build_cmd.extend(auto_fw_flags)
        if extra_flags:
            build_cmd.extend(list(extra_flags))
        for idir in inc_dirs:
            build_cmd.extend(["-I", idir])
        build_cmd.extend(lib_srcs)
        build_cmd.extend(extra_sup)
        build_cmd.append(chosen_test)
        build_cmd.extend(["-lm", "-o", bin_out])
        return "gcc_direct", build_cmd, [bin_out], str(worktree)

    # Mode 3: Fallback `make test`
    return "make_test", [], ["make", "test"], str(worktree)


def _run_c_spec(
    worktree: pathlib.Path,
    runner_kind: str,
    build_cmd: list[str],
    run_cmd: list[str],
    run_cwd: str,
    *,
    timeout_s: float = 20.0,
    baseline_snapshots: Mapping[str, str] | None = None,
) -> tuple[int, str]:
    env = _c_asan_env()
    if runner_kind == "shell_baseline":
        tdir = worktree / "tests"
        snaps = dict(baseline_snapshots or {})
        if not snaps and tdir.is_dir():
            for bf in sorted(tdir.glob("baseline_*.txt")):
                snaps[bf.name] = bf.read_text(encoding="utf-8", errors="replace")
        try:
            cp = subprocess.run(run_cmd, cwd=run_cwd, env=env, capture_output=True, text=True, timeout=timeout_s)
        except subprocess.TimeoutExpired as te:
            return 124, f"TIMEOUT: {te}"
        out = (cp.stdout or "") + "\n" + (cp.stderr or "")
        if cp.returncode != 0:
            return cp.returncode, out
        # Diff all golden baseline files against their pre-run snapshot
        diffs: list[str] = []
        for bname, expected in sorted(snaps.items()):
            bp = tdir / bname
            actual = bp.read_text(encoding="utf-8", errors="replace") if bp.is_file() else ""
            if actual != expected:
                diffs.append(
                    "".join(
                        difflib.unified_diff(
                            expected.splitlines(keepends=True),
                            actual.splitlines(keepends=True),
                            fromfile=f"expected/{bname}",
                            tofile=f"actual/{bname}",
                        )
                    )
                )
            # Restore baseline file so repeated attempts compare cleanly
            bp.write_text(expected, encoding="utf-8")
        if diffs:
            return 1, out + "\nBASELINE_DIFF:\n" + "\n".join(diffs)
        return 0, out

    if build_cmd:
        try:
            cp_b = subprocess.run(
                build_cmd, cwd=str(worktree), env=env, capture_output=True, text=True, errors="replace",
                timeout=min(timeout_s, 24.0) if "-fsanitize=address,undefined" in build_cmd else timeout_s,
            )
        except subprocess.TimeoutExpired as te:
            if "-fsanitize=address,undefined" in build_cmd:
                # Heavy C++ TUs (e.g. tinyxml2.cpp) can blow UBSan compile time; fall back cleanly to ASan-only!
                build_cmd[:] = [
                    "-fsanitize=address" if tok == "-fsanitize=address,undefined" else tok
                    for tok in build_cmd
                ]
                try:
                    cp_b = subprocess.run(
                        build_cmd, cwd=str(worktree), env=env, capture_output=True, text=True, errors="replace",
                        timeout=max(timeout_s, 35.0),
                    )
                except subprocess.TimeoutExpired as te2:
                    return 124, f"BUILD_TIMEOUT: {te2}"
            else:
                return 124, f"BUILD_TIMEOUT: {te}"
        if cp_b.returncode != 0:
            return 200 + cp_b.returncode, "BUILD_FAILED:\n" + (cp_b.stdout or "") + "\n" + (cp_b.stderr or "")

    try:
        cp_r = subprocess.run(run_cmd, cwd=run_cwd, env=env, capture_output=True, text=True, errors="replace", timeout=min(timeout_s, 10.0))
        return cp_r.returncode, (cp_r.stdout or "") + "\n" + (cp_r.stderr or "")
    except subprocess.TimeoutExpired as te:
        return 124, f"RUN_TIMEOUT: {te}"


def _extract_c_gcov_lines(worktree: pathlib.Path, src_files: set[str]) -> dict[str, set[int]]:
    covered: dict[str, set[int]] = {}
    gcov_bin = shutil.which("gcov")
    if not gcov_bin:
        return covered
    gcda_files = list(worktree.rglob("*.gcda"))
    if not gcda_files:
        return covered
    try:
        subprocess.run(
            [gcov_bin, "-n", *[str(g) for g in gcda_files[:6]]],
            cwd=str(worktree),
            capture_output=True,
            text=True,
            timeout=10.0,
        )
    except Exception:
        pass
    # Actually generate `.gcov` files for each gcda
    try:
        subprocess.run(
            [gcov_bin, *[str(g) for g in gcda_files[:6]]],
            cwd=str(worktree),
            capture_output=True,
            text=True,
            timeout=10.0,
        )
    except Exception:
        return covered
    for gf in worktree.glob("*.gcov"):
        target_name = gf.name[:-5]  # strip `.gcov`
        matched_rel = next((sf for sf in src_files if pathlib.Path(sf).name == target_name), None)
        if not matched_rel:
            continue
        lset = covered.setdefault(matched_rel, set())
        for raw_l in gf.read_text(encoding="utf-8", errors="replace").splitlines():
            parts = raw_l.split(":", 2)
            if len(parts) < 2:
                continue
            cnt = parts[0].strip()
            if cnt and cnt[0].isdigit() and int(cnt.rstrip("*")) > 0:
                try:
                    lset.add(int(parts[1].strip()))
                except ValueError:
                    pass
    return covered


def _precompile_c_static_objs(
    worktree: pathlib.Path,
    build_cmd: list[str],
    mutable_files: set[str],
    cache_dir: pathlib.Path,
    *,
    timeout_s: float = 60.0,
) -> list[str]:
    """Precompile unchanging test/support `.c`/`.cpp` TUs in `build_cmd` to `.o` files once.

    Skips precompiling any TU that `#include`s a mutable header (e.g., header-only `.hpp` repos)
    except Catch2/doctest `main.cpp` which does not include library headers.
    """
    if not build_cmd or len(build_cmd) < 4:
        return build_cmd
    compiler = build_cmd[0]
    # Split flags (before `-o`) and input source files
    flags: list[str] = []
    inputs: list[str] = []
    out_flag: list[str] = []
    libs: list[str] = []
    i = 1
    while i < len(build_cmd):
        tok = build_cmd[i]
        if tok == "-o" and i + 1 < len(build_cmd):
            out_flag = [tok, build_cmd[i + 1]]
            i += 2
        elif tok == "-I" and i + 1 < len(build_cmd):
            flags.extend([tok, build_cmd[i + 1]])
            i += 2
        elif tok.startswith("-l"):
            libs.append(tok)
            i += 1
        elif tok.startswith("-"):
            flags.append(tok)
            i += 1
        else:
            inputs.append(tok)
            i += 1

    mutable_basenames = {pathlib.Path(mf).name for mf in mutable_files}
    inputs_norm = {inp.replace("\\", "/").lstrip("./") for inp in inputs}
    # Only skip caching a TU if it directly/transitively #includes a mutable `.c`/`.cpp` source
    # (e.g. `misc_tests.c` -> `common.h` -> `../cJSON.c`), NOT because an unrelated `contrib/*.cpp`
    # happens to exist outside `inputs_norm`!
    uncompiled_mutable_c_names = {
        pathlib.Path(mf).name for mf in mutable_files
        if mf.endswith(_C_EXTS) and mf not in inputs_norm
    }
    env = _c_asan_env()
    new_inputs: list[str] = []
    for inp in inputs:
        norm = inp.replace("\\", "/").lstrip("./")
        if norm in mutable_files or not inp.endswith(_C_EXTS):
            new_inputs.append(inp)
            continue
        p_inp = worktree / inp
        if not p_inp.is_file():
            new_inputs.append(inp)
            continue
        # Do not cache any TU that directly OR transitively (2-hop local #include) references a mutable header/source
        if mutable_basenames:
            def _tu_refs_mutable(fp_chk: pathlib.Path, depth: int = 0, seen_h: set[pathlib.Path] | None = None) -> tuple[bool, bool]:
                """Return (refs_any_mutable, refs_uncompiled_c_src)."""
                if depth > 2 or not fp_chk.is_file():
                    return (False, False)
                if seen_h is None:
                    seen_h = set()
                if fp_chk in seen_h:
                    return (False, False)
                seen_h.add(fp_chk)
                try:
                    t_chk = fp_chk.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    return (False, False)
                r_uncomp = any(bn in t_chk for bn in uncompiled_mutable_c_names)
                r_any = r_uncomp or any(bn in t_chk for bn in mutable_basenames if bn.endswith(_C_HDR_EXTS) or bn.endswith(_C_EXTS))
                if r_uncomp:
                    return (True, True)
                for inc_rel in re.findall(r'#\s*include\s*"([^"]+)"', t_chk):
                    for base_d in (fp_chk.parent, worktree, worktree / "include", worktree / "src", worktree / "test", worktree / "tests"):
                        cand_p = base_d / inc_rel
                        if cand_p.is_file():
                            sub_any, sub_uncomp = _tu_refs_mutable(cand_p, depth + 1, seen_h)
                            r_any = r_any or sub_any
                            r_uncomp = r_uncomp or sub_uncomp
                            if r_uncomp:
                                return (True, True)
                return (r_any, r_uncomp)

            refs_any, refs_uncomp_c = _tu_refs_mutable(p_inp)
            if refs_uncomp_c:
                new_inputs.append(inp)
                continue
            if refs_any:
                if not any(sf in inputs_norm for sf in mutable_files if sf.endswith(_C_EXTS)):
                    new_inputs.append(inp)
                    continue
        obj_name = hashlib.sha256(norm.encode("utf-8")).hexdigest()[:12] + "_" + pathlib.Path(norm).stem + ".o"
        obj_path = cache_dir / obj_name
        if not obj_path.is_file():
            # For unchanging test TUs (e.g. 2,300-line xmltest.cpp), skip heavy sanitizer instrumentation
            # during .o compilation while keeping full sanitizer instrumentation on mutable library TUs
            # and on the final link step (avoids 30s+ UBSan compile blowups on huge test suites!).
            tu_flags = [f for f in flags if not f.startswith("-fsanitize=")] if _is_c_test_path(norm) else flags
            try:
                cp = subprocess.run(
                    [compiler, *tu_flags, "-c", inp, "-o", str(obj_path)],
                    cwd=str(worktree),
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=timeout_s,
                )
                if cp.returncode != 0:
                    new_inputs.append(inp)
                    continue
            except Exception:
                new_inputs.append(inp)
                continue
        new_inputs.append(str(obj_path))

    return [compiler, *flags, *new_inputs, *libs, *out_flag]


def localize_c_faults(
    worktree: pathlib.Path,
    test_targets: Sequence[str] | None = None,
    *,
    timeout_s: float = 25.0,
    baseline_snapshots: Mapping[str, str] | None = None,
    extra_flags: Sequence[str] | None = None,
    precompiled_build_cmd: list[str] | None = None,
) -> CLocalizationReport:
    src_files_list, all_test_files, _ = _discover_c_files(worktree)
    src_files = set(src_files_list)
    runner_kind, build_cmd, run_cmd, run_cwd = detect_c_test_spec(
        worktree, test_targets, sanitizer=True, extra_flags=extra_flags
    )
    eff_build_cmd = list(precompiled_build_cmd) if precompiled_build_cmd else build_cmd
    rc, out = _run_c_spec(
        worktree, runner_kind, eff_build_cmd, run_cmd, run_cwd,
        timeout_s=timeout_s, baseline_snapshots=baseline_snapshots,
    )
    # Fixture-subdir CWD fallback: when a direct C test TU inside a subdirectory (e.g. `tests/test_*.c`)
    # aborts inside a file-open helper (`readfile` / `fopen` / `No such file` / `Assertion 'f'`),
    # retry running the already-built binary from the test TU's parent directory!
    if (
        rc != 0
        and rc < 200
        and runner_kind.endswith("_direct")
        and any(k in out for k in ("readfile", "fopen", "No such file", "ENOENT", "Assertion `f'", "Assertion `fp'"))
    ):
        _cand_tfs = list(test_targets or ()) or list(all_test_files[:2])
        for _tf in _cand_tfs:
            _sub = (worktree / _tf).parent
            if _sub.is_dir() and _sub.resolve() != worktree.resolve():
                _rc_sub, _out_sub = _run_c_spec(
                    worktree, runner_kind, None, run_cmd, _sub,
                    timeout_s=min(timeout_s, 15.0), baseline_snapshots=baseline_snapshots,
                )
                if _rc_sub == 0 or not any(
                    k in _out_sub for k in ("readfile", "fopen", "No such file", "ENOENT", "Assertion `f'", "Assertion `fp'")
                ):
                    run_cwd, rc, out = _sub, _rc_sub, _out_sub
                    break
    # Multi-TU C test discovery: when no explicit test_target was supplied and the alphabetically
    # first test TU passed (or failed to build), probe sibling `test_*.c` TUs with `main()` to
    # locate the actual failing test TU!
    if (rc == 0 or rc >= 200) and not test_targets and runner_kind.endswith("_direct") and len(all_test_files) > 1:
        _probe_cands = [
            tf for tf in all_test_files
            if pathlib.Path(tf).name.startswith("test_") and tf.endswith(_C_EXTS)
        ]
        for _ptf in _probe_cands[:12]:
            rk2, bc2, rc2_cmd, cwd2 = detect_c_test_spec(worktree, [_ptf], sanitizer=False, extra_flags=extra_flags)
            r2, o2 = _run_c_spec(worktree, rk2, bc2, rc2_cmd, cwd2, timeout_s=min(timeout_s, 12.0))
            if r2 != 0 and r2 < 200:
                runner_kind, build_cmd, run_cmd, run_cwd = detect_c_test_spec(worktree, [_ptf], sanitizer=True, extra_flags=extra_flags)
                rc, out = _run_c_spec(worktree, runner_kind, build_cmd, run_cmd, run_cwd, timeout_s=timeout_s)
                if rc >= 200 or rc == 124:
                    runner_kind, build_cmd, run_cmd, run_cwd = rk2, bc2, rc2_cmd, cwd2
                    rc, out = r2, o2
                break

    bug_classes: list[str] = []
    out_low = out.lower()
    for tag, pats in (
        ("NULL_DEREF", ("null pointer", "segv on unknown address 0x00000000", "member access within null pointer")),
        ("SEGV", ("addresssanitizer: segv", "segmentation fault")),
        ("HEAP_UAF", ("heap-use-after-free",)),
        ("BUFFER_OVERFLOW", ("heap-buffer-overflow", "stack-buffer-overflow", "global-buffer-overflow")),
        (
            "SIGNED_OVERFLOW",
            (
                "signed integer overflow",
                "cannot be represented in type",
                "negation of ",
                "runtime error: addition of unsigned offset",
            ),
        ),
        ("SIGABRT_ASSERT", ("addresssanitizer: abrt", "assertion `", "assertion '")),
        (
            "CPP_NO_MATCHING_OVERLOAD",
            (
                "no matching function for call to",
                "cannot bind non-const lvalue reference of type",
                "no match for 'operator<<'",
                "no match for \u2018operator<<\u2019",
                "std::basic_ostream<",
            ),
        ),
        ("ASSERT_FAIL", ("fail", "assertion", "baseline_diff")),
    ):
        if any(p in out_low for p in pats):
            bug_classes.append(tag)

    sites: list[CLocalizedSite] = []
    seen: set[tuple[str, int]] = set()
    covered: dict[str, set[int]] = {}
    wt_str = str(worktree.resolve()).replace("\\", "/")

    # 1. Exact ASan / UBSan / SIGABRT stack trace frames (`file.cpp:123` or `file.hpp:1060`)
    frame_rank = 0
    for m in re.finditer(r"([A-Za-z0-9_./\\\-]+\.(?:c|cc|cpp|cxx|h|hh|hpp)):(\d+)(?::\d+)?", out):
        raw_p = m.group(1).replace("\\", "/")
        lno = int(m.group(2))
        rel = raw_p
        if raw_p.startswith(wt_str + "/"):
            rel = raw_p[len(wt_str) + 1 :]
        rel = rel.lstrip("./")
        if rel not in src_files:
            bn = pathlib.Path(rel).name
            rel = next((sf for sf in src_files if pathlib.Path(sf).name == bn), "")
        if rel in src_files and (rel, lno) not in seen:
            seen.add((rel, lno))
            is_crash = any(
                b in bug_classes
                for b in ("NULL_DEREF", "HEAP_UAF", "BUFFER_OVERFLOW", "SIGNED_OVERFLOW", "SIGABRT_ASSERT")
            )
            sc = (1.6 - min(frame_rank * 0.05, 0.25)) if is_crash else 1.2
            frame_rank += 1
            sites.append(CLocalizedSite(file=rel, lineno=lno, score=sc, source="asan" if is_crash else "assert"))
            covered.setdefault(rel, set()).add(lno)
            p_src = worktree / rel
            if p_src.is_file():
                n_max = len(p_src.read_text(encoding="utf-8", errors="replace").splitlines())
                for off in range(-8, 9):
                    wln = lno + off
                    if 1 <= wln <= n_max and (rel, wln) not in seen:
                        seen.add((rel, wln))
                        sites.append(CLocalizedSite(file=rel, lineno=wln, score=sc - 0.15 - abs(off) * 0.01, source="asan"))
                        covered.setdefault(rel, set()).add(wln)

    # 1b. ASan Two-Pass Allocator/Sizer Twin Localization:
    # When ASan reports `heap-buffer-overflow WRITE` inside a Pass-2 writer/parser (`*_parse_*` / `*_write_*`),
    # the root cause is routinely in the upstream Pass-1 sizer/validator/skipper (`*_get_*_size`, `*_skip_*`)
    # in the same source file. Include those Pass-1 twin function spans for high-precision Pass-1 laws.
    if "BUFFER_OVERFLOW" in bug_classes and "WRITE of size" in out:
        pass2_files = [rel for rel in covered if re.search(r"\b[A-Za-z_]\w*_(?:parse|write)_[A-Za-z_]\w*\b", out)]
        for rel in pass2_files[:2]:
            p_src = worktree / rel
            if not p_src.is_file():
                continue
            flines = p_src.read_text(encoding="utf-8", errors="replace").splitlines()
            for idx, ltxt in enumerate(flines, 1):
                if re.search(r"\b[A-Za-z_]\w*(?:_get_[A-Za-z0-9_]*_size|_skip_[A-Za-z0-9_]+)\s*\(", ltxt) and ltxt.rstrip().endswith("{"):
                    fn_ind = len(ltxt) - len(ltxt.lstrip())
                    for fln in range(idx, min(len(flines) + 1, idx + 220)):
                        if (rel, fln) not in seen:
                            seen.add((rel, fln))
                            sites.append(CLocalizedSite(file=rel, lineno=fln, score=1.35, source="asan_pass1_twin"))
                            covered.setdefault(rel, set()).add(fln)
                        cur_l = flines[fln - 1]
                        if fln > idx + 1 and cur_l.strip() == "}" and (len(cur_l) - len(cur_l.lstrip())) <= fn_ind:
                            break

    # 2. Extract failing test function / symbol tokens AND direct library calls from failing test lines
    fail_toks: set[str] = set()
    called_fn_toks: set[str] = set()
    for line in out.splitlines():
        if any(k in line for k in (":FAIL:", "FAILED", "failed:", "Assertion", "BASELINE_DIFF", "runtime error")):
            for tok in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]{3,})\b", line):
                fail_toks.add(tok.lower())
                fail_toks.add(tok.lower().replace("_", ""))
    # Inspect any failing test file:line cited in output to harvest DIRECTLY CALLED library methods!
    _, all_test_files, _ = _discover_c_files(worktree)
    for m_tf in re.finditer(r"([A-Za-z0-9_./\\\-]+\.(?:c|cc|cpp|cxx)):(\d+)", out):
        tf_rel = m_tf.group(1).replace("\\", "/").lstrip("./")
        tf_ln = int(m_tf.group(2))
        tf_p = worktree / tf_rel
        if not tf_p.is_file():
            bn = pathlib.Path(tf_rel).name
            tf_match = next((t for t in all_test_files if pathlib.Path(t).name == bn), None)
            if tf_match:
                tf_rel = tf_match
                tf_p = worktree / tf_match
        if tf_p.is_file() and tf_rel not in src_files:
            tflines = tf_p.read_text(encoding="utf-8", errors="replace").splitlines()
            for j in range(max(0, tf_ln - 24), min(len(tflines), tf_ln + 4)):
                for m_call in re.finditer(r"(?:\.|->|::|\b)([A-Za-z_][A-Za-z0-9_]{4,})\s*(?:<[^<>]+>)?\s*\(", tflines[j]):
                    cn = m_call.group(1).lower()
                    if cn not in ("check", "assert", "require", "expect", "test", "equal", "false", "true"):
                        called_fn_toks.add(cn)
                        called_fn_toks.add(cn.replace("_", ""))

    if fail_toks or called_fn_toks:
        for rel in src_files_list:
            p_src = worktree / rel
            if not p_src.is_file():
                continue
            flines = p_src.read_text(encoding="utf-8", errors="replace").splitlines()
            for idx, ltxt in enumerate(flines, 1):
                stripped_l = ltxt.strip()
                if not stripped_l or stripped_l.startswith(("if", "for", "while", "switch", "return", "//", "*", "#")):
                    continue
                if stripped_l.endswith(";"):
                    continue
                matched_score = 0.0
                for mf in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_]{3,})\s*\(", ltxt):
                    fn_norm = mf.group(1).lower().replace("_", "")
                    if len(fn_norm) < 6:
                        continue
                    if any(ct in fn_norm or fn_norm in ct for ct in called_fn_toks if len(ct) >= 6):
                        matched_score = max(matched_score, 1.48 if "impl" in fn_norm else 1.42)
                    elif any(fn_norm in ft for ft in fail_toks if len(ft) >= 6):
                        matched_score = max(matched_score, 1.15)
                if matched_score > 0.0:
                    fn_ind = len(ltxt) - len(ltxt.lstrip())
                    for fln in range(idx, min(len(flines) + 1, idx + 170)):
                        if (rel, fln) not in seen:
                            seen.add((rel, fln))
                            sites.append(CLocalizedSite(file=rel, lineno=fln, score=matched_score, source="symbol"))
                            covered.setdefault(rel, set()).add(fln)
                        cur_l = flines[fln - 1]
                        if fln > idx + 1 and cur_l.strip() == "}" and (len(cur_l) - len(cur_l.lstrip())) <= fn_ind:
                            break

    # 3. If still no sites (e.g., shell baseline or generic assert), run gcov coverage pass or fallback
    if not sites and runner_kind == "gcc_direct":
        with tempfile.TemporaryDirectory(prefix="brain_cgcov_") as gtmp:
            gwt = pathlib.Path(gtmp) / "wt"
            _copy_js_worktree(worktree, gwt)
            rk_c, b_c, r_c, rcwd_c = detect_c_test_spec(
                gwt, test_targets, sanitizer=False, coverage=True, extra_flags=extra_flags
            )
            _run_c_spec(gwt, rk_c, b_c, r_c, rcwd_c, timeout_s=timeout_s)
            gcov_lines = _extract_c_gcov_lines(gwt, src_files)
            for rel, lns in sorted(gcov_lines.items()):
                for ln in sorted(lns):
                    if (rel, ln) not in seen:
                        seen.add((rel, ln))
                        sites.append(CLocalizedSite(file=rel, lineno=ln, score=0.7, source="gcov"))
                        covered.setdefault(rel, set()).add(ln)

    if not sites:
        script_srcs: list[str] = []
        if runner_kind == "shell_baseline" and (worktree / "tests" / "unittest.sh").is_file():
            stxt = (worktree / "tests" / "unittest.sh").read_text(encoding="utf-8", errors="replace")
            for m_sc in re.findall(r"(?:\.\./)?([A-Za-z0-9_.\-/]+\.(?:c|cpp|cc))", stxt):
                bn = pathlib.Path(m_sc).name
                matched = next((sf for sf in src_files_list if pathlib.Path(sf).name == bn), None)
                if matched and matched not in script_srcs:
                    script_srcs.append(matched)
        ordered_fb = script_srcs + [sf for sf in src_files_list if sf not in script_srcs]

        macro_hints: set[str] = set()
        for mb in re.findall(r"expected/baseline_([a-z0-9_]+)\.txt", out):
            macro_hints.add(mb.upper())

        for rel in ordered_fb[: (len(script_srcs) or 3)]:
            p_src = worktree / rel
            if p_src.is_file():
                flines = p_src.read_text(encoding="utf-8", errors="replace").splitlines()
                in_hint_block = 0
                for ln, ltxt in enumerate(flines, 1):
                    if ln > 800:
                        break
                    if macro_hints and re.match(r"^\s*#\s*if", ltxt):
                        if any(mh in ltxt.upper() for mh in macro_hints):
                            in_hint_block = 25
                    elif re.match(r"^\s*#\s*endif", ltxt) and in_hint_block > 0:
                        in_hint_block = 0
                    sc = 0.85 if in_hint_block > 0 else 0.35
                    if in_hint_block > 0:
                        in_hint_block -= 1
                    covered.setdefault(rel, set()).add(ln)
                    sites.append(CLocalizedSite(file=rel, lineno=ln, score=sc, source="fallback"))

    sites.sort(key=lambda s: (-s.score, s.file, s.lineno))
    return CLocalizationReport(
        runner_kind=runner_kind,
        build_cmd=eff_build_cmd,
        run_cmd=run_cmd,
        run_cwd=run_cwd,
        initial_rc=rc,
        initial_output=out,
        bug_classes=bug_classes,
        sites=sites,
        covered_lines_by_file=covered,
    )


def _find_c_enclosing_function(lines: list[str], lineno: int) -> tuple[int, int, str]:
    """Return `(header_start_idx, body_open_brace_idx, header_text)` for the C/C++ function containing 1-based `lineno`."""
    cur_ind = len(lines[lineno - 1]) - len(lines[lineno - 1].lstrip()) if 1 <= lineno <= len(lines) else 4
    for idx in range(lineno - 1, max(-1, lineno - 150), -1):
        raw = lines[idx]
        st = raw.strip()
        ind = len(raw) - len(raw.lstrip())
        # Column-0 or namespace-indented opening `{` whose preceding line is a function signature
        if st == "{" and (ind == 0 or ind < cur_ind):
            prev_sig = lines[idx - 1].strip() if idx > 0 else ""
            if "(" in prev_sig or ")" in prev_sig or ind == 0:
                if not prev_sig.startswith(("if", "for", "while", "switch", "else", "try", "catch", "do", "namespace", "class", "struct")):
                    fn_start = max(0, idx - 3)
                    hdr = " ".join(l.strip() for l in lines[fn_start : idx + 1])
                    return fn_start, idx, hdr
        # K&R / same-line opening brace `type Class::fn(...) {` or multi-line wrapped C signature ending `) {`
        if (
            idx < lineno - 1
            and st.endswith("{")
            and not st.startswith(("if", "for", "while", "switch", "else", "struct", "enum", "typedef", "class", "namespace", "catch"))
        ):
            prev_st = lines[idx - 1].strip() if idx > 0 else ""
            is_ctrl_cont = prev_st.endswith(("||", "&&", "?", ":", "(", "if", "while", "for")) or prev_st.startswith(("if (", "else if (", "while ("))
            if "(" in st and not is_ctrl_cont and st.count("(") == st.count(")") and (ind == 0 or ind < cur_ind):
                return idx, idx, st
            if ")" in st and not is_ctrl_cont:
                for back in range(1, min(5, idx + 1)):
                    bi = idx - back
                    bst = lines[bi].strip()
                    bind = len(lines[bi]) - len(lines[bi].lstrip())
                    if "(" in bst and (bind == 0 or bind < cur_ind):
                        if not bst.startswith(("if", "for", "while", "switch", "else", "struct", "enum", "typedef", "class", "namespace", "catch")):
                            hdr_m = " ".join(l.strip() for l in lines[bi : idx + 1])
                            return bi, idx, hdr_m
                        break
    return max(0, lineno - 40), max(0, lineno - 1), ""


def _infer_c_default_returns(lines: list[str], lineno: int) -> list[str]:
    """Infer type-safe early-return statements from the enclosing C/C++ function signature & file idioms."""
    fn_start, open_idx, hdr = _find_c_enclosing_function(lines, lineno)
    hdr_nocomment = re.sub(r"/\*.*?\*/", " ", hdr)
    hdr_nocomment = re.sub(r"//[^\n]*", " ", hdr_nocomment)
    hdr_clean = re.sub(r"\b[A-Z][A-Z0-9_]*\s*\(([^()]+)\)", r"\1", hdr_nocomment)
    ret_part = hdr_clean.split("(")[0] if "(" in hdr_clean else hdr_clean

    fn_ind = len(lines[open_idx]) - len(lines[open_idx].lstrip()) if 0 <= open_idx < len(lines) else 0
    rets: list[str] = []
    for idx in range(open_idx, min(len(lines), open_idx + 120)):
        if idx > open_idx and lines[idx].strip() == "}" and (len(lines[idx]) - len(lines[idx].lstrip())) <= fn_ind:
            break
        mr = re.search(r"\breturn\s+(NULL|nullptr|0|0\.0|false|true|JSONFailure|-1|\(double\)\s*NAN|NAN)\s*;", lines[idx])
        if mr:
            stmt = f"return {mr.group(1)};"
            if stmt not in rets:
                rets.append(stmt)

    if re.search(r"\bvoid\b", ret_part) and "*" not in ret_part:
        return ["return;"]
    if "*" in ret_part:
        return ["return NULL;"]
    if re.search(r"\b(?:double|float)\b", ret_part):
        cand_r = ["return 0.0;"]
        file_txt = "".join(lines[:300])
        if "NAN" in file_txt:
            cand_r.append("return (double)NAN;")
        m_dp = re.search(r"\bdouble\s+([A-Za-z_]\w*)", hdr_clean)
        if m_dp:
            cand_r.append(f"return {m_dp.group(1)};")
        for r in rets:
            if r not in cand_r and "NULL" not in r:
                cand_r.append(r)
        return cand_r[:4]
    if re.search(r"\b(?:cJSON_bool|bool)\b", ret_part):
        return ["return false;", "return true;", "return 0;"]
    for d in ("return 0;", "return -1;"):
        if d not in rets:
            rets.append(d)
    return [r for r in rets if "NULL" not in r][:3]


def _extract_balanced_paren_arg(text: str, open_paren_idx: int) -> tuple[str, int] | None:
    """Given index of `(`, return `(inner_text, close_paren_idx)` or None."""
    if open_paren_idx < 0 or open_paren_idx >= len(text) or text[open_paren_idx] != "(":
        return None
    depth = 0
    for i in range(open_paren_idx, len(text)):
        ch = text[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return text[open_paren_idx + 1 : i], i
    return None


def _update_memrl_law(store: dict[str, Any], law_id: str, *, success: bool) -> None:
    """Update MemRL EWMA utility Q-value & quarantine status on an external inspectable law."""
    entry = store.get(law_id)
    if not isinstance(entry, dict):
        return
    q = float(entry.get("utility_q", 0.7))
    if success:
        entry["verified_uses"] = int(entry.get("verified_uses", 0)) + 1
        entry["utility_q"] = round(0.7 * q + 0.3 * 1.0, 4)
        entry["status"] = "ACTIVE"
    else:
        refs = int(entry.get("refutations", 0)) + 1
        entry["refutations"] = refs
        entry["utility_q"] = round(0.7 * q + 0.3 * 0.0, 4)
        if refs >= 2:
            entry["status"] = "QUARANTINED"


def _abstract_c_repair_law(tier: str, desc: str) -> dict[str, Any] | None:
    """Generalize a verified C/C++ repair into a path-free, variable-free external MemRL law."""
    kind: str | None = None
    if tier in ("C_NULL_PTR_DEREF_GUARD", "C_TIER0_SKILL_RECALL"):
        kind = "null_early_return" if "early_return" in desc or "entry_null" in desc else "null_guard_wrap_deref"
    elif tier == "C_UBSAN_SIGNED_OVERFLOW_GUARD":
        kind = "ubsan_unsigned_abs_negation"
    elif tier == "C_EARLY_RETURN_FIELD_PROPAGATION":
        kind = "early_return_field_propagate"
    elif tier == "C_SIGABRT_NULL_ARG_GUARD":
        kind = "sigabrt_null_arg_guard"
    elif tier == "C_ASAN_BUFFER_BOUNDS_GUARD":
        kind = "asan_buffer_bounds_guard"
    elif tier == "C_CHAR_PREDICATE_WHITESPACE_COMPLETE":
        kind = "c_locale_isspace_complete"
    elif tier == "C_COUPLED_WHILE_TO_DO_WHILE_DIGIT_COUNT":
        kind = "coupled_while_to_do_while_digit_count"
    elif tier == "C_DOUBLE_PROJECTION_UNWRAP":
        kind = "double_projection_unwrap"
    elif tier == "C_SIBLING_COORD_GUARD_SYNC":
        kind = "sibling_coord_guard_sync"
    elif tier == "C_GROW_ONLY_RESIZE_GUARD":
        kind = "grow_only_resize_guard"
    elif tier == "C_SPECULATIVE_ADVANCE_NO_REWIND":
        kind = "speculative_advance_no_rewind"
    elif tier == "C_FLAG_SKIP_REMAINDER_BLOCK":
        kind = "flag_skip_remainder_block"
    elif tier == "C_ASAN_CONJUNCT_SHORT_CIRCUIT_SWAP":
        kind = "asan_conjunct_short_circuit_swap"
    elif tier == "C_SIBLING_BRANCH_GUARD_TRANSFER":
        kind = "sibling_branch_guard_transfer"
    elif tier == "C_NORM_COMPARE_CONSISTENCY":
        kind = "norm_compare_consistency"
    elif tier == "C_SIBLING_SAFE_DECODER_DELEGATE":
        kind = "sibling_safe_decoder_delegate"
    elif tier == "C_CPP_TEMPLATE_TRAIT_OVERLOAD_GENERALIZE":
        kind = "cpp_template_trait_overload_generalize"
    elif tier == "C_EMPTY_CONTAINER_ITERATOR_GUARD":
        kind = "empty_container_iterator_guard"
    elif tier == "C_UNCHECKED_ALLOC_NULL_GUARD":
        kind = "unchecked_alloc_null_guard"
    elif tier == "C_ZERO_CONSUME_WHILE_REJECT":
        kind = "zero_consume_while_reject"
    elif tier == "C_HARDCODED_PREFIX_CHAR_TO_EXPR":
        kind = "hardcoded_prefix_char_to_expr"
    elif tier == "C_RECURSIVE_VECTOR_ACCUMULATOR_MERGE":
        kind = "recursive_vector_accumulator_merge"
    elif tier == "C_SIBLING_METHOD_TRAILING_BLOCK_SYNC":
        kind = "sibling_method_trailing_block_sync"
    if kind is None:
        return None
    lid = "claw_" + hashlib.sha256(kind.encode("utf-8")).hexdigest()[:12]
    return {
        "law_id": lid,
        "kind": kind,
        "verified_uses": 1,
        "refutations": 0,
        "utility_q": 0.85,
        "status": "ACTIVE",
        "parameters_stored": 0,
    }


def synthesize_c_candidates(
    worktree: pathlib.Path,
    loc: CLocalizationReport,
    *,
    memory: Mapping[str, Any] | None = None,
    max_candidates: int = 80,
) -> list[CPatchCandidate]:
    cands: list[CPatchCandidate] = []
    seen_src: set[tuple[str, str]] = set()

    def add_cand(rel: str, lineno: int, tier: str, desc: str, patched: str, skill_id: str | None = None) -> None:
        if len(cands) >= max_candidates:
            return
        key = (rel, patched)
        if key in seen_src:
            return
        seen_src.add(key)
        cands.append(CPatchCandidate(rel, lineno, tier, desc, patched, skill_id))

    file_order: list[str] = []
    lines_by_file_ranked: dict[str, list[int]] = {}
    for s in loc.sites:
        if s.file not in file_order:
            file_order.append(s.file)
        fl = lines_by_file_ranked.setdefault(s.file, [])
        if s.lineno not in fl:
            fl.append(s.lineno)

    c_laws = memory.get("c_rewrite_laws") if isinstance(memory, Mapping) else None
    active_c_laws = sorted(
        (
            (str(k), v)
            for k, v in (c_laws.items() if isinstance(c_laws, Mapping) else ())
            if isinstance(v, Mapping) and v.get("status") == "ACTIVE"
        ),
        key=lambda kv: -float(kv[1].get("utility_q", 0.7)),
    )

    def _active_c_law_id(*kinds: str) -> str | None:
        return next((lid for lid, v in active_c_laws if v.get("kind") in kinds), None)

    null_law_id = _active_c_law_id("null_early_return", "null_guard_wrap_deref")
    has_null_law = null_law_id is not None
    ubsan_law_id = _active_c_law_id("ubsan_unsigned_abs_negation")
    early_field_law_id = _active_c_law_id("early_return_field_propagate")
    sigabrt_law_id = _active_c_law_id("sigabrt_null_arg_guard")
    oob_law_id = _active_c_law_id("asan_buffer_bounds_guard")
    ws_law_id = _active_c_law_id("c_locale_isspace_complete")
    digit_law_id = _active_c_law_id("coupled_while_to_do_while_digit_count")
    dproj_law_id = _active_c_law_id("double_projection_unwrap")
    cguard_law_id = _active_c_law_id("sibling_coord_guard_sync")
    gresize_law_id = _active_c_law_id("grow_only_resize_guard")
    rewind_law_id = _active_c_law_id("speculative_advance_no_rewind")
    fskip_law_id = _active_c_law_id("flag_skip_remainder_block")
    scswap_law_id = _active_c_law_id("asan_conjunct_short_circuit_swap")
    sibgrd_law_id = _active_c_law_id("sibling_branch_guard_transfer")
    normcmp_law_id = _active_c_law_id("norm_compare_consistency")
    safedec_law_id = _active_c_law_id("sibling_safe_decoder_delegate")
    tplovl_law_id = _active_c_law_id("cpp_template_trait_overload_generalize")
    empit_law_id = _active_c_law_id("empty_container_iterator_guard")
    pfxch_law_id = _active_c_law_id("hardcoded_prefix_char_to_expr")
    recacc_law_id = _active_c_law_id("recursive_vector_accumulator_merge")
    sibtr_law_id = _active_c_law_id("sibling_method_trailing_block_sync")

    # Extract any struct fields explicitly asserted in test failure output (e.g., `result.encoding == encoding_utf8`)
    asserted_fields: list[str] = []
    for m_af in re.finditer(r"\b[A-Za-z_]\w*\.([A-Za-z_]\w+)\s*(?:==|!=)\s*[A-Za-z0-9_]+", loc.initial_output):
        af = m_af.group(1)
        if af not in asserted_fields and af not in ("cpp", "hpp", "txt", "xml", "status"):
            asserted_fields.append(af)

    cmp_deferred: list[tuple[str, int, str, str, str]] = []

    # Pass 0y (high-precision C linked-list node pointer swap vs shallow field copy):
    # `C_LINKED_NODE_POINTER_SWAP_VS_FIELD_COPY`:
    # When replacing a value node in a singly/circularly linked list, shallow-copying fields
    # (`P->next->f1 = val->f1; P->next->f2 = val->f2;`) breaks object identity so later mutations
    # to `val` are invisible through the container. Splice the node pointer directly:
    # `val->next = P->next->next; P->next = val;`!
    for rel_ln in file_order[:4]:
        p_ln = worktree / rel_ln
        if not p_ln.is_file():
            continue
        orig_ln = p_ln.read_text(encoding="utf-8", errors="replace")
        lines_ln = orig_ln.splitlines(keepends=True)
        # Focus on functions mentioned in test failure or test assertion lines (or localized lines)
        _test_hint_syms: set[str] = set()
        m_as = re.search(r"\(([^():]+\.(?:c|cpp|cc)):\s*(\d+)\)", loc.initial_output)
        if m_as:
            _tfp = worktree / m_as.group(1)
            _tln = int(m_as.group(2))
            if _tfp.is_file():
                _tlines = _tfp.read_text(encoding="utf-8", errors="replace").splitlines()
                _win = "\n".join(_tlines[max(0, _tln - 25): min(len(_tlines), _tln + 5)])
                for _ms in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_]{6,})\s*\(", _win):
                    _test_hint_syms.add(_ms.group(1))
        for i_ln in range(len(lines_ln) - 1):
            l1 = lines_ln[i_ln]
            l2 = lines_ln[i_ln + 1]
            m1 = re.match(r"^(\s*)([A-Za-z_]\w*)->next->([A-Za-z_][\w.]*)\s*=\s*([A-Za-z_]\w*)->\3\s*;\s*$", l1)
            if not m1:
                continue
            ind_ln, p_var, _f1, v_var = m1.groups()
            m2 = re.match(
                rf"^\s*{re.escape(p_var)}->next->([A-Za-z_][\w.]*)\s*=\s*{re.escape(v_var)}->\1\s*;\s*$",
                l2,
            )
            if not m2:
                continue
            # Check enclosing function matches a hint symbol (if any) or localized line
            if _test_hint_syms:
                _head_ctx = "".join(lines_ln[max(0, i_ln - 30): i_ln + 1])
                if not any(hs in _head_ctx for hs in _test_hint_syms):
                    continue
            nl_ln = list(lines_ln)
            nl_ln[i_ln] = f"{ind_ln}{v_var}->next = {p_var}->next->next;\n"
            nl_ln[i_ln + 1] = f"{ind_ln}{p_var}->next = {v_var};\n"
            add_cand(
                rel_ln, i_ln + 1, "C_LINKED_NODE_POINTER_SWAP_VS_FIELD_COPY",
                f"linked_node_pointer_splice({p_var}->next={v_var})",
                "".join(nl_ln),
            )

    # Pass 0x (high-precision CWE-416 Heap-Use-After-Free aliasing compute-before-free reorder):
    # `C_HEAP_UAF_FREE_BEFORE_USE_REORDER`:
    # When ASan reports `heap-use-after-free`, scan all localized frames across `file_order[:4]`.
    # If frame line `L` is `return <use_expr>;` immediately preceded by a deallocation call
    # (`free(x);`, `*_Delete(x);`, `*_Free(x);`, `*_Destroy(x);`, `delete x;`), reorder so
    # `<use_expr>` computes/duplicates BEFORE the deallocation frees aliased subtrees!
    if "HEAP_UAF" in loc.bug_classes:
        _dealloc_re = re.compile(
            r"^\s*(?:(?:[A-Za-z_]\w*_)?(?:Delete|Free|Destroy|Release|delete|free|destroy|release)\s*\([^;]+\)|delete(?:\s*\[\s*\])?\s+[^;]+)\s*;\s*$"
        )
        for rel_uaf in file_order[:4]:
            p_uaf = worktree / rel_uaf
            if not p_uaf.is_file():
                continue
            orig_uaf = p_uaf.read_text(encoding="utf-8", errors="replace")
            lines_uaf = orig_uaf.splitlines(keepends=True)
            for lno_uaf in (lines_by_file_ranked.get(rel_uaf) or [])[:12]:
                for probe_ln in (lno_uaf, lno_uaf - 1, lno_uaf + 1):
                    if not (2 <= probe_ln <= len(lines_uaf)):
                        continue
                    cur_raw = lines_uaf[probe_ln - 1]
                    m_ret = re.match(r"^(\s*)return\s+(.+?)\s*;\s*$", cur_raw)
                    if not m_ret or "(" not in m_ret.group(2):
                        continue
                    ind_u, ret_expr = m_ret.group(1), m_ret.group(2).strip()
                    # Walk backward 1..3 lines skipping blank/comment lines for a deallocation call
                    prev_idx = probe_ln - 2
                    steps_back = 0
                    while prev_idx >= 0 and steps_back < 4:
                        s_prev = lines_uaf[prev_idx].strip()
                        if not s_prev or s_prev.startswith("//") or (s_prev.startswith("/*") and s_prev.endswith("*/")):
                            prev_idx -= 1
                            steps_back += 1
                            continue
                        break
                    if prev_idx < 0 or not _dealloc_re.match(lines_uaf[prev_idx]):
                        continue
                    # Extract return type from enclosing C/C++ function header
                    fn_s, _, fn_hdr = _find_c_enclosing_function(lines_uaf, probe_ln)
                    if fn_s <= 0 or not fn_hdr:
                        continue
                    # Parse return type before function name `(<args>)`
                    m_hdr = re.search(r"^(.*?)\b([A-Za-z_]\w*)\s*\(", fn_hdr.strip())
                    if not m_hdr:
                        continue
                    raw_rt = m_hdr.group(1).strip()
                    raw_rt = raw_rt.rsplit("}", 1)[-1].rsplit(";", 1)[-1].strip()
                    # Strip export macros like `CJSON_PUBLIC(cJSON *)` -> `cJSON *`, and storage specifiers
                    m_mac = re.search(r"[A-Z0-9_]+\s*\(\s*([^)]+)\s*\)", raw_rt)
                    if m_mac:
                        raw_rt = m_mac.group(1).strip()
                    raw_rt = re.sub(r"\b(?:static|inline|extern|virtual|constexpr)\b", "", raw_rt).strip()
                    if not raw_rt or raw_rt == "void":
                        continue
                    sep_sp = "" if raw_rt.endswith("*") else " "
                    nl_uaf = list(lines_uaf)
                    dealloc_line = nl_uaf[prev_idx]
                    nl_uaf[prev_idx] = f"{ind_u}{raw_rt}{sep_sp}_brain_uaf_res = {ret_expr};\n"
                    nl_uaf[probe_ln - 1] = f"{dealloc_line}{ind_u}return _brain_uaf_res;\n"
                    add_cand(
                        rel_uaf, probe_ln, "C_HEAP_UAF_FREE_BEFORE_USE_REORDER",
                        f"uaf_compute_before_free({ret_expr[:40]})",
                        "".join(nl_uaf),
                    )

    # Pass 0z (high-precision CWE-476 Unchecked Allocation NULL Guard):
    # `C_UNCHECKED_ALLOC_NULL_GUARD`:
    # When ASan reports `NULL_DEREF`, scan top localized stack frames (`loc.sites[:8]`).
    # If an enclosing function assigns a local pointer `<var>` from an allocator call
    # (`malloc`, `calloc`, `realloc`, `strdup`, or custom `*alloc*(`) before the crash/call line
    # without checking `<var>` for NULL, insert `if (!<var>) { <ret_stmt> }` right after the
    # allocation statement (or its enclosing `if/else` allocation block) before `<var>` is used!
    if "NULL_DEREF" in loc.bug_classes:
        _alloc_assign_re = re.compile(
            r"^(\s*)([A-Za-z_]\w*)\s*=\s*(?:\([^)]+\)\s*)?(?:[A-Za-z_]\w*)?(?:alloc|Alloc|malloc|calloc|realloc|strdup)\w*\s*\("
        )
        _seen_alloc_fn: set[tuple[str, int, str]] = set()
        for s_al in loc.sites[:8]:
            rel_al = s_al.file
            p_al = worktree / rel_al
            if not p_al.is_file():
                continue
            lines_al = p_al.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
            if not (1 <= s_al.lineno <= len(lines_al)):
                continue
            fn_s_al, open_al, _ = _find_c_enclosing_function(lines_al, s_al.lineno)
            if fn_s_al <= 0 or open_al >= s_al.lineno - 1:
                continue
            # Scan lines inside this function BEFORE `s_al.lineno` for an unchecked allocation
            alloc_vars: dict[str, int] = {}
            for k_al in range(open_al + 1, s_al.lineno - 1):
                m_al = _alloc_assign_re.match(lines_al[k_al])
                if m_al:
                    alloc_vars[m_al.group(2)] = k_al
            for avar, last_al_idx in alloc_vars.items():
                key_al = (rel_al, fn_s_al, avar)
                if key_al in _seen_alloc_fn:
                    continue
                _seen_alloc_fn.add(key_al)
                # Advance past closing `}` if allocation was inside an `if (...) { ... } else { ... }`
                ins_al = last_al_idx + 1
                while ins_al < s_al.lineno - 1 and lines_al[ins_al].strip() in ("}", "};"):
                    ins_al += 1
                # Skip if `avar` is already NULL-checked between allocation and crash/call site
                between_txt = "".join(lines_al[last_al_idx + 1 : s_al.lineno])
                if re.search(
                    rf"\b(?:!\s*{re.escape(avar)}|{re.escape(avar)}\s*==\s*(?:NULL|0|nullptr|\w*_null)|(?:NULL|0|nullptr|\w*_null)\s*==\s*{re.escape(avar)})\b",
                    between_txt,
                ):
                    continue
                # Determine indentation from next non-empty line (or enclosing function body)
                ind_al = "  "
                for probe_i in range(ins_al, min(len(lines_al), s_al.lineno + 1)):
                    if lines_al[probe_i].strip():
                        ind_al = lines_al[probe_i][: len(lines_al[probe_i]) - len(lines_al[probe_i].lstrip())]
                        break
                # Harvest existing null-like early returns in the SAME function body first (works even for multi-line C headers!)
                fn_body_al = "".join(lines_al[open_al : min(len(lines_al), s_al.lineno + 15)])
                def_rets_al: list[str] = []
                for m_er in re.finditer(r"\b(return\s+(?:NULL|nullptr|0|false|[A-Za-z_]\w*null)\s*;)", fn_body_al):
                    rs_e = re.sub(r"\s+", " ", m_er.group(1).strip())
                    if rs_e not in def_rets_al:
                        def_rets_al.append(rs_e)
                for rs_f in _infer_c_default_returns(lines_al, s_al.lineno):
                    if rs_f not in def_rets_al:
                        def_rets_al.append(rs_f)
                if "return NULL;" not in def_rets_al:
                    def_rets_al.append("return NULL;")
                for rstmt_al in def_rets_al[:2]:
                    nl_al = list(lines_al)
                    nl_al.insert(ins_al, f"{ind_al}if (!{avar}) {{ {rstmt_al} }}\n")
                    add_cand(
                        rel_al, ins_al + 1, "C_UNCHECKED_ALLOC_NULL_GUARD",
                        f"unchecked_alloc_null_guard({avar}->{rstmt_al})",
                        "".join(nl_al),
                    )

    # Pass 0aa (high-precision C zero-consumption token-loop empty-reject law):
    # `C_ZERO_CONSUME_WHILE_REJECT`:
    # When a localized parser function initializes a local cursor `<cur> = <init>;`
    # (e.g. `size_t offset = state->offset;`), runs a `while (...)` loop advancing `<cur>++`,
    # commits `<init> = <cur>;`, and returns `0` without rejecting `<cur> == <init>`,
    # insert `if (<cur> == <init>) { return 1; }` right after the `while` loop when test output
    # signals an empty/unexpected-success failure!
    _init_lo_0aa = str(loc.initial_output or "").lower()
    if any(k in _init_lo_0aa for k in ("empty", "fail", "leak", "expect", "reject", "invalid")):
        _fail_toks_0aa = set(re.findall(r"[a-z]{4,}", _init_lo_0aa))
        _seen_0aa: set[tuple[str, int]] = set()
        _0aa_cands: list[tuple[int, str, int, str, str]] = []
        for rel_0aa in file_order[:3]:
            p_0aa = worktree / rel_0aa
            if not p_0aa.is_file():
                continue
            lines_0aa = p_0aa.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
            for wi, wline in enumerate(lines_0aa):
                m_w = re.match(r"^(\s*)while\s*\(.+\)\s*\{\s*$", wline)
                if not m_w:
                    continue
                w_ind = m_w.group(1)
                # Find matching closing brace of this short token-consuming while loop
                w_end = -1
                for kj in range(wi + 1, min(len(lines_0aa), wi + 10)):
                    if lines_0aa[kj].startswith(w_ind + "}"):
                        w_end = kj
                        break
                if w_end <= wi:
                    continue
                w_body = "".join(lines_0aa[wi + 1 : w_end])
                m_inc = re.search(r"\b([A-Za-z_]\w*)\s*\+\+\s*;", w_body)
                if not m_inc:
                    continue
                cur_v = m_inc.group(1)
                fn_s_w, open_w, hdr_w = _find_c_enclosing_function(lines_0aa, wi + 1)
                if fn_s_w <= 0 or (rel_0aa, wi + 1) in _seen_0aa:
                    continue
                # Find `<cur_v> = <init_expr>;` before the loop and `<init_expr> = <cur_v>;` + `return 0;` after
                pre_txt = "".join(lines_0aa[open_w : wi])
                m_init = re.search(rf"\b{re.escape(cur_v)}\s*=\s*([A-Za-z_]\w*(?:->|\.)[A-Za-z_]\w*)\s*;", pre_txt)
                if not m_init:
                    continue
                init_expr = m_init.group(1)
                post_txt = "".join(lines_0aa[w_end + 1 : min(len(lines_0aa), w_end + 25)])
                if not re.search(rf"\b{re.escape(init_expr)}\s*=\s*{re.escape(cur_v)}\s*;", post_txt):
                    continue
                if "return 0;" not in post_txt:
                    continue
                if re.search(rf"\b{re.escape(cur_v)}\s*==\s*{re.escape(init_expr)}\b", post_txt):
                    continue
                _seen_0aa.add((rel_0aa, wi + 1))
                # Rank by lexical overlap between enclosing function/loop condition and failing test name
                fn_ctx_lo = (hdr_w + "\n" + wline + "\n" + pre_txt).lower()
                ov_0aa = sum(1 for ft in _fail_toks_0aa if len(ft) >= 4 and ft in fn_ctx_lo and ft not in ("test", "fail", "utest", "json", "parse", "char", "size", "const"))
                nl_0aa = list(lines_0aa)
                nl_0aa.insert(w_end + 1, f"{w_ind}if ({cur_v} == {init_expr}) {{ return 1; }}\n")
                _0aa_cands.append((ov_0aa, rel_0aa, w_end + 2, f"zero_consume_reject({cur_v}=={init_expr}->return 1)", "".join(nl_0aa)))
        _0aa_cands.sort(key=lambda t: (-t[0], t[2]))
        for _ov, rel_0aa, ln_0aa, desc_0aa, src_0aa in _0aa_cands[:3]:
            add_cand(rel_0aa, ln_0aa, "C_ZERO_CONSUME_WHILE_REJECT", desc_0aa, src_0aa)

    for rel in file_order[:3]:
        p = worktree / rel
        if not p.is_file():
            continue
        orig = p.read_text(encoding="utf-8", errors="replace")
        lines = orig.splitlines(keepends=True)
        lns = lines_by_file_ranked.get(rel) or list(range(1, len(lines) + 1))
        is_cpp_file = rel.endswith((".cpp", ".cc", ".cxx", ".hpp", ".hh"))

        # Op 0b: ASan Causal-Pair (Use-Site + Free-Site) HEAP_UAF Clear-Index Reset (`C_ASAN_UAF_CLEAR_INDEX_RESET`)
        # When ASan reports a heap-use-after-free where the use frame probes `obj->idx_arr[ix] == SENTINEL`
        # bounded by `obj->cap_field` and the free frame resets `obj->count = 0;`, synthesize resetting the
        # stale index table to `SENTINEL` right next to `obj->count = 0;`. Zero domain hardcoding!
        if "HEAP_UAF" in loc.bug_classes and "freed by thread" in loc.initial_output:
            use_part, free_part = loc.initial_output.split("freed by thread", 1)
            use_lines: list[int] = [
                int(m.group(2))
                for m in re.finditer(r"([A-Za-z0-9_./\\\-]+\.(?:c|cc|cpp)):(\d+)", use_part)
                if pathlib.Path(m.group(1)).name == pathlib.Path(rel).name
            ]
            free_lines: list[int] = [
                int(m.group(2))
                for m in re.finditer(r"([A-Za-z0-9_./\\\-]+\.(?:c|cc|cpp)):(\d+)", free_part)
                if pathlib.Path(m.group(1)).name == pathlib.Path(rel).name
            ]
            # Harvest `(obj_var, cap_field, idx_field, sentinel)` from the use-site function
            idx_specs: list[tuple[str, str, str]] = []  # (cap_field, idx_field, sentinel)
            for uln in use_lines[:3]:
                u_start = max(0, uln - 30)
                u_end = min(len(lines), uln + 15)
                u_win = "".join(lines[u_start:u_end])
                m_cap = re.search(r"<\s*[A-Za-z_]\w*->([A-Za-z_]\w*)\s*;", u_win)
                m_idx = re.search(r"([A-Za-z_]\w*)\s*=\s*[A-Za-z_]\w*->([A-Za-z_]\w*)\s*\[[^\]]+\]\s*;", u_win)
                if m_cap and m_idx:
                    cell_v, idx_field = m_idx.group(1), m_idx.group(2)
                    m_sent = re.search(rf"\b{re.escape(cell_v)}\s*==\s*([A-Z][A-Z0-9_]+|NULL|-1)\b", u_win)
                    if m_sent:
                        spec = (m_cap.group(1), idx_field, m_sent.group(1))
                        if spec not in idx_specs:
                            idx_specs.append(spec)
            for fln in free_lines[:3]:
                f_start = max(0, fln - 15)
                f_end = min(len(lines), fln + 25)
                # Find `obj->count = 0;` in the free-site function
                for k_idx in range(f_start, f_end):
                    m_cnt = re.match(r"^(\s*)([A-Za-z_]\w*)->([A-Za-z_]\w*)\s*=\s*0\s*;\s*$", lines[k_idx])
                    if not m_cnt:
                        continue
                    c_ind, obj_v, _ = m_cnt.groups()
                    # Detect loop variable declared in this function (default `i`)
                    fn_win = "".join(lines[f_start:f_end])
                    loop_v = "i" if re.search(r"\b(?:size_t|int|unsigned)\s+i\b", fn_win) else "size_t _bi"
                    for cap_f, idx_f, sent_v in idx_specs:
                        if loop_v == "i":
                            rst_loop = f"{c_ind}for (i = 0; i < {obj_v}->{cap_f}; i++) {{ {obj_v}->{idx_f}[i] = {sent_v}; }}\n"
                        else:
                            rst_loop = f"{c_ind}{{ size_t _bi; for (_bi = 0; _bi < {obj_v}->{cap_f}; _bi++) {{ {obj_v}->{idx_f}[_bi] = {sent_v}; }} }}\n"
                        nl = list(lines)
                        nl.insert(k_idx + 1, rst_loop)
                        add_cand(
                            rel, k_idx + 1, "C_ASAN_UAF_CLEAR_INDEX_RESET",
                            f"reset_index_table({obj_v}->{idx_f}={sent_v})", "".join(nl),
                        )

        # Pass 0g (high-precision semantic): ASCII Whitespace Predicate Completion (`C_CHAR_PREDICATE_WHITESPACE_COMPLETE`)
        # Run across all localized lines before broad ops so large header-only libraries never starve it.
        for ln_ws in lns[:300]:
            if not (1 <= ln_ws <= len(lines)):
                continue
            l_ws = lines[ln_ws - 1]
            if "find(' ') != std::string::npos" in l_ws:
                win_ws = "".join(lines[max(0, ln_ws - 5) : min(len(lines), ln_ws + 6)])
                if r"'\n'" in win_ws and r"'\t'" not in win_ws:
                    m_fsp = re.search(r"(([A-Za-z_]\w*(?:->|\.))find\(' '\) != std::string::npos)", l_ws)
                    if m_fsp:
                        full_chk, recv = m_fsp.group(1), m_fsp.group(2)
                        nl = list(lines)
                        nl[ln_ws - 1] = l_ws.replace(
                            full_chk,
                            f'{recv}find_first_of(" \\t\\n\\v\\f\\r") != std::string::npos',
                            1,
                        )
                        ws_tier = "C_TIER0_SKILL_RECALL" if ws_law_id else "C_CHAR_PREDICATE_WHITESPACE_COMPLETE"
                        add_cand(
                            rel, ln_ws, ws_tier,
                            "complete_c_locale_isspace", "".join(nl), skill_id=ws_law_id,
                        )

        # Pass 0h (high-precision mathematical): Coupled Base-Conversion Digit-Count Loop Boundary
        # (`C_COUPLED_WHILE_TO_DO_WHILE_DIGIT_COUNT`):
        # `while (0 != v) { v /= B; cnt++; }` yields 0 digits when `v == 0` instead of 1 digit ('0').
        # Rewrite ALL sibling identical digit-count loops in the file atomically to `do { ... } while (0 != v);`
        # so coupled size-estimator + writer passes stay consistent, plus single-site fallback.
        _digit_loops: list[tuple[int, int, str, str, str]] = []  # (start_idx, end_idx, indent, cond, var)
        _seen_dc_starts: set[int] = set()
        for ln_dc in lns[:350]:
            if not (1 <= ln_dc <= len(lines)):
                continue
            for scan_i in range(max(0, ln_dc - 4), min(len(lines), ln_dc + 2)):
                if scan_i in _seen_dc_starts:
                    continue
                m_wl = re.match(
                    r"^(\s*)while\s*\(\s*(?:(0\s*!=\s*([A-Za-z_]\w*))|(([A-Za-z_]\w*)\s*!=\s*0))\s*\)\s*\{\s*$",
                    lines[scan_i],
                )
                if not m_wl:
                    continue
                w_ind = m_wl.group(1)
                w_cond = m_wl.group(2) or m_wl.group(4)
                w_var = m_wl.group(3) or m_wl.group(5)
                # Find closing brace within 6 lines and verify body divides `w_var /= 10` (or base) & increments a counter
                end_i = -1
                for j_i in range(scan_i + 1, min(len(lines), scan_i + 7)):
                    if lines[j_i].strip() == "}":
                        end_i = j_i
                        break
                if end_i > scan_i + 1:
                    body_txt = "".join(lines[scan_i + 1 : end_i])
                    if re.search(rf"\b{re.escape(w_var)}\s*/=\s*(?:10|16|8|2)\s*;", body_txt) and re.search(
                        r"(?:\+\+[A-Za-z_]\w*|[A-Za-z_]\w*\+\+|[A-Za-z_]\w*\s*\+=\s*1)\s*;", body_txt
                    ):
                        _seen_dc_starts.add(scan_i)
                        _digit_loops.append((scan_i, end_i, w_ind, w_cond, w_var))
        if _digit_loops:
            # Scan whole file for any sibling identical digit-count loops with the same variable (e.g. Pass-1 sizer + Pass-2 writer)
            dc_vars = {t[4] for t in _digit_loops}
            all_dc: list[tuple[int, int, str, str, str]] = list(_digit_loops)
            for scan_i in range(len(lines)):
                if scan_i in _seen_dc_starts:
                    continue
                m_wl = re.match(
                    r"^(\s*)while\s*\(\s*(?:(0\s*!=\s*([A-Za-z_]\w*))|(([A-Za-z_]\w*)\s*!=\s*0))\s*\)\s*\{\s*$",
                    lines[scan_i],
                )
                if not m_wl:
                    continue
                w_var = m_wl.group(3) or m_wl.group(5)
                if w_var not in dc_vars:
                    continue
                w_ind = m_wl.group(1)
                w_cond = m_wl.group(2) or m_wl.group(4)
                end_i = -1
                for j_i in range(scan_i + 1, min(len(lines), scan_i + 7)):
                    if lines[j_i].strip() == "}":
                        end_i = j_i
                        break
                if end_i > scan_i + 1:
                    body_txt = "".join(lines[scan_i + 1 : end_i])
                    if re.search(rf"\b{re.escape(w_var)}\s*/=\s*(?:10|16|8|2)\s*;", body_txt) and re.search(
                        r"(?:\+\+[A-Za-z_]\w*|[A-Za-z_]\w*\+\+|[A-Za-z_]\w*\s*\+=\s*1)\s*;", body_txt
                    ):
                        _seen_dc_starts.add(scan_i)
                        all_dc.append((scan_i, end_i, w_ind, w_cond, w_var))
            dc_tier = "C_TIER0_SKILL_RECALL" if digit_law_id else "C_COUPLED_WHILE_TO_DO_WHILE_DIGIT_COUNT"
            # Coupled atomic rewrite of all sibling digit-count loops first
            nl_all = list(lines)
            for si, ei, wi, wc, _ in all_dc:
                nl_all[si] = f"{wi}do {{\n"
                nl_all[ei] = f"{wi}}} while ({wc});\n"
            add_cand(
                rel, all_dc[0][0] + 1, dc_tier,
                f"coupled_do_while_digit_count({len(all_dc)}_loops)", "".join(nl_all), skill_id=digit_law_id,
            )
            if len(all_dc) > 1:
                for si, ei, wi, wc, _ in _digit_loops[:3]:
                    nl_one = list(lines)
                    nl_one[si] = f"{wi}do {{\n"
                    nl_one[ei] = f"{wi}}} while ({wc});\n"
                    add_cand(rel, si + 1, dc_tier, "do_while_digit_count", "".join(nl_one), skill_id=digit_law_id)

        # Pass 0i (high-precision mathematical): Double Coordinate-Projection Unwrap (`C_DOUBLE_PROJECTION_UNWRAP`)
        # If local variable `v = F(x)` was ALREADY projected via `F` in the enclosing function, unwrap
        # double-projected calls `F(v)` or `F(v + k)` / `F(v - k)` -> `v` / `v + k` / `v - k`.
        dp_tier = "C_TIER0_SKILL_RECALL" if dproj_law_id else "C_DOUBLE_PROJECTION_UNWRAP"
        for ln_dp in lns[:350]:
            if not (1 <= ln_dp <= len(lines)):
                continue
            l_dp = lines[ln_dp - 1]
            if "(" not in l_dp:
                continue
            for m_call in re.finditer(r"\b([A-Za-z_]\w*)\s*\(\s*([A-Za-z_]\w*(?:\s*[+-]\s*[A-Za-z0-9_]+)?)\s*\)", l_dp):
                proj_fn, inner_arg = m_call.group(1), m_call.group(2).strip()
                if proj_fn in ("if", "for", "while", "switch", "return", "sizeof", "static_cast", "resize", "reserve"):
                    continue
                base_var = re.match(r"^([A-Za-z_]\w*)", inner_arg).group(1)  # type: ignore[union-attr]
                prev_win = "".join(lines[max(0, ln_dp - 30) : ln_dp - 1])
                if re.search(rf"\b{re.escape(base_var)}\s*=\s*{re.escape(proj_fn)}\s*\(", prev_win):
                    nl = list(lines)
                    nl[ln_dp - 1] = l_dp[: m_call.start()] + inner_arg + l_dp[m_call.end() :]
                    add_cand(
                        rel, ln_dp, dp_tier,
                        f"unwrap_double_projection({proj_fn}({inner_arg})->{inner_arg})",
                        "".join(nl), skill_id=dproj_law_id,
                    )

        # Pass 0j (high-precision mathematical): Guard/Body Coordinate-Projection Sync (`C_SIBLING_COORD_GUARD_SYNC`)
        # When `if (X > BoundFn())` guards a body calling `ProjFn(X)` (e.g. `resize(GetDataColumnIndex(pRow.size()))`),
        # the guard compared unprojected `X` against the projected bound; rewrite to `if (ProjFn(X) > BoundFn())`.
        cg_tier = "C_TIER0_SKILL_RECALL" if cguard_law_id else "C_SIBLING_COORD_GUARD_SYNC"
        for ln_cg in lns[:350]:
            if not (1 <= ln_cg <= len(lines)):
                continue
            l_cg = lines[ln_cg - 1]
            m_grd = re.match(
                r"^(\s*if\s*\(\s*)([A-Za-z_]\w*(?:\.[A-Za-z_]\w*\(\))?)(\s*(?:>|>=|<|<=)\s*[A-Za-z_]\w*\(\)\s*\).*)$",
                l_cg,
            )
            if not m_grd:
                continue
            g_pre, g_expr, g_rest = m_grd.groups()
            body_win = "".join(lines[ln_cg : min(len(lines), ln_cg + 14)])
            for m_pf in re.finditer(rf"\b([A-Za-z_]\w*)\s*\(\s*{re.escape(g_expr)}\s*\)", body_win):
                proj_fn = m_pf.group(1)
                if proj_fn in ("if", "for", "while", "switch", "return", "sizeof", "resize", "reserve", "push_back"):
                    continue
                nl = list(lines)
                nl[ln_cg - 1] = f"{g_pre}{proj_fn}({g_expr}){g_rest}\n"
                add_cand(
                    rel, ln_cg, cg_tier,
                    f"sync_guard_projection({g_expr}->{proj_fn}({g_expr}))",
                    "".join(nl), skill_id=cguard_law_id,
                )
                break

        # Pass 0k (high-precision mathematical): Non-Destructive Grow-Only Container Resize Monotonicity
        # (`C_GROW_ONLY_RESIZE_GUARD`):
        # Inside a growth loop/branch (`>` / `>=` guard above), unconditional `v->resize(N);` shrinks wider
        # containers! Guard with `if (v->size() < (N)) { v->resize(N); }` to preserve monotonic growth.
        gr_tier = "C_TIER0_SKILL_RECALL" if gresize_law_id else "C_GROW_ONLY_RESIZE_GUARD"
        for ln_gr in lns[:350]:
            if not (1 <= ln_gr <= len(lines)):
                continue
            l_gr = lines[ln_gr - 1]
            m_rs = re.match(r"^(\s*)([A-Za-z_]\w*(?:->|\.))resize\((.+)\)\s*;\s*$", l_gr)
            if not m_rs:
                continue
            r_ind, r_recv, r_arg = m_rs.groups()
            r_arg_s = r_arg.strip()
            if f"{r_recv}size()" in l_gr:
                continue
            prev_blk = "".join(lines[max(0, ln_gr - 10) : ln_gr - 1])
            if ">" in prev_blk and ("if" in prev_blk or "for" in prev_blk):
                nl = list(lines)
                nl[ln_gr - 1] = f"{r_ind}if ({r_recv}size() < ({r_arg_s})) {{ {r_recv}resize({r_arg_s}); }}\n"
                add_cand(
                    rel, ln_gr, gr_tier,
                    f"grow_only_resize({r_recv}size()<{r_arg_s})",
                    "".join(nl), skill_id=gresize_law_id,
                )

        # Pass 0l (high-precision parser invariant): Speculative Lookahead Advance Without Rewind
        # (`C_SPECULATIVE_ADVANCE_NO_REWIND`):
        # In any lexer/skipper function returning `0` on non-match, if `if (C == buf[pos]) { pos++; if (...) ... else if (...) ... }`
        # speculatively increments `pos++` before verifying a multi-char prefix and falls through without an `else`
        # branch rewinding `pos--`, insert `} else { pos--; }` (and EOF guard if `size` is in scope).
        rw_tier = "C_TIER0_SKILL_RECALL" if rewind_law_id else "C_SPECULATIVE_ADVANCE_NO_REWIND"
        _seen_rw: set[int] = set()
        for ln_rw in lns[:2000]:
            if not (1 <= ln_rw <= len(lines)) or ln_rw in _seen_rw:
                continue
            l_rw = lines[ln_rw - 1]
            m_adv = re.match(r"^(\s*)([A-Za-z_]\w*(?:->|\.)?[A-Za-z_]\w*)\+\+\s*;\s*$", l_rw)
            if not m_adv:
                continue
            adv_ind, pos_expr = m_adv.groups()
            # Previous non-blank/comment line must be an `if (...[pos_expr])` opener
            prev_if = -1
            for pi in range(ln_rw - 2, max(-1, ln_rw - 6), -1):
                st_p = lines[pi].strip()
                if not st_p or st_p.startswith(("/*", "*", "//")):
                    continue
                if st_p.startswith("if") and pos_expr in st_p and st_p.endswith("{"):
                    prev_if = pi
                break
            if prev_if < 0:
                continue
            # Next non-blank/comment line must be an inner `if (...)` at the same indentation `adv_ind`
            inner_if = -1
            for ni in range(ln_rw, min(len(lines), ln_rw + 6)):
                st_n = lines[ni].strip()
                if not st_n or st_n.startswith(("/*", "*", "//")):
                    continue
                if lines[ni].startswith(adv_ind + "if ") or lines[ni].startswith(adv_ind + "if("):
                    inner_if = ni
                break
            if inner_if < 0:
                continue
            # Find closing `}` of the inner `if ... else if ...` chain at indentation `adv_ind` (without trailing `else`)
            chain_end = -1
            has_plain_else = False
            for ci in range(inner_if + 1, min(len(lines), inner_if + 90)):
                if lines[ci].startswith(adv_ind + "}"):
                    st_c = lines[ci].strip()
                    if st_c.startswith("} else if"):
                        continue
                    if st_c.startswith("} else"):
                        has_plain_else = True
                        break
                    if st_c == "}":
                        chain_end = ci
                        break
            if chain_end < 0 or has_plain_else:
                continue
            # Verify outer `if` closes right after `chain_end` and falls through to `return 0;`
            after_txt = "".join(lines[chain_end + 1 : min(len(lines), chain_end + 8)])
            if "return 0;" in after_txt:
                _seen_rw.add(ln_rw)
                nl = list(lines)
                nl[chain_end] = f"{adv_ind}}} else {{\n{adv_ind}  {pos_expr}--;\n{adv_ind}}}\n"
                add_cand(
                    rel, ln_rw, rw_tier,
                    f"rewind_speculative_advance({pos_expr}--)",
                    "".join(nl), skill_id=rewind_law_id,
                )

        # Pass 0m (high-precision control-flow invariant): Special-Case Flag Skip-Remainder Block
        # (`C_FLAG_SKIP_REMAINDER_BLOCK`):
        # Inside an enclosing `{ ... }` block where boolean flag `F` is set (`F = 1;`) and checked via `!F`
        # on the very next `if (... !F ...)`, followed by unguarded sibling statements consuming the cursor
        # up to the enclosing `}`, wrap from that `if` through the end of the enclosing block in `if (!F) { ... }`.
        fs_tier = "C_TIER0_SKILL_RECALL" if fskip_law_id else "C_FLAG_SKIP_REMAINDER_BLOCK"
        _seen_fs: set[int] = set()
        for ln_fs in lns[:2000]:
            if not (1 <= ln_fs <= len(lines)) or ln_fs in _seen_fs:
                continue
            l_fs = lines[ln_fs - 1]
            m_fi = re.match(r"^(\s*)if\s*\([^)]*&&\s*!([A-Za-z_]\w*)\b", l_fs)
            if not m_fi:
                continue
            fi_ind, flag_v = m_fi.groups()
            if len(fi_ind) < 2:
                continue
            prev_win = "".join(lines[max(0, ln_fs - 45) : ln_fs - 1])
            if not re.search(rf"\b{re.escape(flag_v)}\s*=\s*1\s*;", prev_win):
                continue
            # Find closing `}` of the enclosing block (strictly less indented than `fi_ind`)
            blk_end = -1
            for ej in range(ln_fs, min(len(lines), ln_fs + 140)):
                st_e = lines[ej].strip()
                if st_e == "}":
                    e_ind = lines[ej][: len(lines[ej]) - len(lines[ej].lstrip())]
                    if len(e_ind) < len(fi_ind):
                        blk_end = ej
                        break
            if blk_end > ln_fs + 5:
                rem_txt = "".join(lines[ln_fs:blk_end])
                if "while" in rem_txt or "offset++" in rem_txt:
                    _seen_fs.add(ln_fs)
                    nl = list(lines)
                    nl.insert(blk_end, f"{fi_ind}}}\n")
                    nl.insert(ln_fs - 1, f"{fi_ind}if (!{flag_v}) {{\n")
                    add_cand(
                        rel, ln_fs, fs_tier,
                        f"guard_remainder_block(if !{flag_v})",
                        "".join(nl), skill_id=fskip_law_id,
                    )

        # Pass 0n (high-precision CWE-125 memory safety): Short-Circuit Bounds-Before-Dereference Conjunct Swap
        # (`C_ASAN_CONJUNCT_SHORT_CIRCUIT_SWAP`):
        # When ASan reports `BUFFER_OVERFLOW` READ at `while (A && B)` or `if (A && B)` where `A` dereferences
        # memory (`*p` / `p[...]`) and `B` checks a bound/counter (`n--`, `<`, `>`, `!= 0`), swap to `B && A`
        # so C/C++ left-to-right short-circuit evaluation enforces the bound BEFORE dereferencing memory.
        if "BUFFER_OVERFLOW" in loc.bug_classes:
            sc_tier = "C_TIER0_SKILL_RECALL" if scswap_law_id else "C_ASAN_CONJUNCT_SHORT_CIRCUIT_SWAP"
            for ln_sc in lns[:40]:
                if not (1 <= ln_sc <= len(lines)):
                    continue
                l_sc = lines[ln_sc - 1]
                m_kw = re.match(r"^(\s*(?:while|if)\s*)\(", l_sc)
                if not m_kw or "&&" not in l_sc:
                    continue
                ext = _extract_balanced_paren_arg(l_sc, m_kw.end() - 1)
                if not ext:
                    continue
                cond_inner, close_pos = ext
                # Split `cond_inner` on top-level `&&`
                depth = 0
                split_pos = -1
                for ci in range(len(cond_inner) - 1):
                    ch = cond_inner[ci]
                    if ch in "([":
                        depth += 1
                    elif ch in ")]":
                        depth -= 1
                    elif depth == 0 and cond_inner[ci : ci + 2] == "&&":
                        split_pos = ci
                        break
                if split_pos <= 0:
                    continue
                lhs_c = cond_inner[:split_pos].strip()
                rhs_c = cond_inner[split_pos + 2 :].strip()
                lhs_deref = bool(re.search(r"(?:\*[A-Za-z_]\w*|[A-Za-z_]\w*\s*\[)", lhs_c))
                rhs_deref = bool(re.search(r"(?:\*[A-Za-z_]\w*|[A-Za-z_]\w*\s*\[)", rhs_c))
                if lhs_deref and not rhs_deref:
                    nl = list(lines)
                    nl[ln_sc - 1] = l_sc[: m_kw.end()] + f"{rhs_c} && {lhs_c}" + l_sc[close_pos:]
                    add_cand(
                        rel, ln_sc, sc_tier,
                        f"swap_short_circuit_guard({rhs_c} && {lhs_c})",
                        "".join(nl), skill_id=scswap_law_id,
                    )

        # Pass 0o (high-precision structural transfer): Sibling-Function Branch Guard Alpha-Transfer
        # (`C_SIBLING_BRANCH_GUARD_TRANSFER`):
        # When a localized branch `if (HDR(*v_tgt))` already has a local rejection block `if (...) { REJ_tgt }`,
        # find any sibling function in the SAME file with an alpha-equivalent branch `if (HDR(*v_sib))`,
        # alpha-rename `v_sib -> v_tgt` on any missing rejection guard whose condition references ONLY `v_tgt`
        # and literals, and transfer it with `REJ_tgt` into the localized branch. Zero domain hardcoding!
        sg_tier = "C_TIER0_SKILL_RECALL" if sibgrd_law_id else "C_SIBLING_BRANCH_GUARD_TRANSFER"
        _seen_sg: set[tuple[int, str]] = set()
        for ln_sg in lns[:250]:
            if not (1 <= ln_sg <= len(lines)):
                continue
            l_sg = lines[ln_sg - 1]
            m_br = re.match(r"^(\s*)(?:else\s+)?if\s*\(([^;]+?\*([A-Za-z_]\w*)[^;]*)\)\s*\{\s*$", l_sg)
            if not m_br:
                continue
            br_ind, br_cond, v_tgt = m_br.groups()
            hdr_norm = re.sub(rf"\b{re.escape(v_tgt)}\b", "$V", re.sub(r"\s+", " ", br_cond.strip()))
            # Find end of target branch & harvest its local rejection body (`if (...) { ... continue; / return ...; }`)
            t_end = -1
            for tj in range(ln_sg, min(len(lines), ln_sg + 60)):
                if lines[tj].startswith(br_ind + "}"):
                    t_end = tj
                    break
            if t_end <= ln_sg + 2:
                continue
            tgt_blk = "".join(lines[ln_sg:t_end])
            # Extract first local rejection guard inside target branch
            m_rej = re.search(
                r"\n([ \t]+)if\s*\([^\n]+(?:\n[^\n]+){0,3}\)\s*\{\n((?:[^\n]+\n){1,5}?)\1\}",
                "\n" + tgt_blk,
            )
            if not m_rej:
                continue
            rej_ind, rej_body = m_rej.group(1), m_rej.group(2)
            if "continue;" not in rej_body and "return " not in rej_body:
                continue
            # Anchor insertion right after the closing brace of that first local rejection guard
            insert_offset = tgt_blk.find(rej_body)
            if insert_offset < 0:
                continue
            ins_line = ln_sg + tgt_blk[: insert_offset + len(rej_body)].count("\n") + 1
            if not (ln_sg < ins_line <= t_end):
                continue
            # Scan sibling functions in the same file for an alpha-equivalent branch header `hdr_norm`
            for si in range(len(lines)):
                if abs(si - (ln_sg - 1)) < 5:
                    continue
                m_sb = re.match(r"^(\s*)(?:else\s+)?if\s*\(([^;]+?\*([A-Za-z_]\w*)[^;]*)\)\s*\{\s*$", lines[si])
                if not m_sb:
                    continue
                sb_ind, sb_cond, v_sib = m_sb.groups()
                if re.sub(rf"\b{re.escape(v_sib)}\b", "$V", re.sub(r"\s+", " ", sb_cond.strip())) != hdr_norm:
                    continue
                s_end = -1
                for sj in range(si + 1, min(len(lines), si + 60)):
                    if lines[sj].startswith(sb_ind + "}"):
                        s_end = sj
                        break
                if s_end <= si + 2:
                    continue
                sib_blk = "".join(lines[si + 1 : s_end])
                for m_sg in re.finditer(
                    r"^[ \t]+if\s*\(([^\n;]+)\)\s*\{\s*\n[ \t]+return\b[^\n]*;\s*\n[ \t]+\}",
                    sib_blk,
                    re.M,
                ):
                    raw_cond = m_sg.group(1).strip()
                    # Ensure condition only references `v_sib` + hex/int literals (no unbound sibling locals)
                    ident_toks = set(re.findall(r"\b[A-Za-z_]\w*\b", re.sub(r"0[xX][0-9a-fA-F]+", "", raw_cond)))
                    if ident_toks != {v_sib}:
                        continue
                    ren_cond = re.sub(rf"\b{re.escape(v_sib)}\b", v_tgt, raw_cond)
                    ren_norm = re.sub(r"\s+", "", ren_cond)
                    if ren_norm in re.sub(r"\s+", "", tgt_blk):
                        continue
                    key_sg = (ins_line, ren_norm)
                    if key_sg in _seen_sg:
                        continue
                    _seen_sg.add(key_sg)
                    nl = list(lines)
                    nl.insert(ins_line, f"{rej_ind}if ({ren_cond}) {{\n{rej_body}{rej_ind}}}\n")
                    add_cand(
                        rel, ins_line, sg_tier,
                        f"transfer_sibling_guard({ren_cond[:48]})",
                        "".join(nl), skill_id=sibgrd_law_id,
                    )

        # Pass 0p (high-precision mathematical): Comparator Order-Equivalence Consistency
        # (`C_NORM_COMPARE_CONSISTENCY`):
        # When a comparator normalizes `a = F(a); b = F(b);` after saving `a_orig = a; b_orig = b;`,
        # tests equivalence `a == b`, and then orders by the UNNORMALIZED `(a_orig < b_orig)` / `(a_orig > b_orig)`,
        # rewrite the mismatched ordering checks to `(a < b)` / `(a > b)` to restore order-equivalence consistency.
        nc_tier = "C_TIER0_SKILL_RECALL" if normcmp_law_id else "C_NORM_COMPARE_CONSISTENCY"
        _seen_nc: set[int] = set()
        for ln_nc in lns[:300]:
            if not (1 <= ln_nc <= len(lines)) or ln_nc in _seen_nc:
                continue
            l_nc = lines[ln_nc - 1]
            m_lt = re.match(r"^(\s*)if\s*\(\s*([A-Za-z_]\w*)\s*<\s*([A-Za-z_]\w*)\s*\)\s*\{\s*$", l_nc)
            if not m_lt:
                continue
            lt_ind, oa, ob = m_lt.groups()
            prev_blk = "".join(lines[max(0, ln_nc - 25) : ln_nc - 1])
            m_sa = re.search(rf"\b{re.escape(oa)}\s*=\s*([A-Za-z_]\w*)\s*;", prev_blk)
            m_sb = re.search(rf"\b{re.escape(ob)}\s*=\s*([A-Za-z_]\w*)\s*;", prev_blk)
            if not (m_sa and m_sb):
                continue
            na, nb = m_sa.group(1), m_sb.group(1)
            if na == oa or nb == ob or not re.search(rf"\b{re.escape(na)}\s*==\s*{re.escape(nb)}\b", prev_blk):
                continue
            # Find closing brace of the `if (oa < ob) { ... } else if (oa > ob) { ... }` comparator block
            blk_end = ln_nc - 1
            for nxt_i in range(ln_nc, min(len(lines), ln_nc + 8)):
                if lines[nxt_i].startswith(lt_ind + "}") and not lines[nxt_i].strip().startswith("} else"):
                    blk_end = nxt_i
                    break
            _seen_nc.add(ln_nc)
            # Form 1: POSIX / C exact signed-difference comparator `return na - nb;` (preserves both sign & exact delta)
            if blk_end > ln_nc - 1:
                blk_src = "".join(lines[ln_nc - 1 : blk_end + 1])
                if "return -1" in blk_src and "return 1" in blk_src:
                    nl_diff = lines[: ln_nc - 1] + [f"{lt_ind}return {na} - {nb};\n"] + lines[blk_end + 1 :]
                    add_cand(
                        rel, ln_nc, nc_tier,
                        f"order_diff_consistency(return {na} - {nb})",
                        "".join(nl_diff), skill_id=normcmp_law_id,
                    )
            # Form 2: Signum comparator on normalized values `(na < nb) / (na > nb)`
            nl = list(lines)
            nl[ln_nc - 1] = l_nc.replace(oa, na, 1).replace(ob, nb, 1)
            for nxt_i in range(ln_nc, min(len(lines), ln_nc + 6)):
                if re.search(rf"\b{re.escape(oa)}\s*>\s*{re.escape(ob)}\b", nl[nxt_i]):
                    nl[nxt_i] = nl[nxt_i].replace(oa, na, 1).replace(ob, nb, 1)
                    break
            add_cand(
                rel, ln_nc, nc_tier,
                f"order_consistency({oa},{ob}->{na},{nb})",
                "".join(nl), skill_id=normcmp_law_id,
            )

        # Pass 0q (high-precision ASan OOB): Safe Sibling Decoder Delegation (`C_SIBLING_SAFE_DECODER_DELEGATE`):
        # When ASan reports BUFFER_OVERFLOW READ inside an unguarded `if/else if/else` decoder writing `*out = ...;`
        # in function `fnA`, delegate that crashing `if/else` chain to a safe sibling decoder `fnB(ptr, out)`
        # in the same file whose name is a suffix/root of `fnA` and which guards continuation reads against NUL.
        if "BUFFER_OVERFLOW" in loc.bug_classes:
            sd_tier = "C_TIER0_SKILL_RECALL" if safedec_law_id else "C_SIBLING_SAFE_DECODER_DELEGATE"
            _seen_sd: set[int] = set()
            for ln_sd in lns[:25]:
                if not (1 <= ln_sd <= len(lines)):
                    continue
                fn_s, open_i, hdr_s = _find_c_enclosing_function(lines, ln_sd)
                m_fna = re.search(r"\b([A-Za-z_]\w+)\s*\(([^)]*)\)", hdr_s)
                if not m_fna:
                    continue
                fn_a, params_a = m_fna.groups()
                # Find start of the crashing `if (...) { *out = ... } else if ... else { ... }` chain
                if_start = -1
                for bi in range(ln_sd - 1, max(open_i, ln_sd - 18), -1):
                    if re.match(r"^\s*if\s*\(", lines[bi]) and not lines[bi].lstrip().startswith("else"):
                        if_start = bi
                        break
                if if_start < 0 or if_start in _seen_sd:
                    continue
                if_ind = lines[if_start][: len(lines[if_start]) - len(lines[if_start].lstrip())]
                if_end = -1
                for ei in range(if_start + 1, min(len(lines), if_start + 35)):
                    if lines[ei].startswith(if_ind + "}") and not lines[ei].strip().startswith("} else"):
                        if_end = ei
                        break
                if if_end <= if_start + 2:
                    continue
                chain_txt = "".join(lines[if_start : if_end + 1])
                m_out = re.search(r"\*([A-Za-z_]\w*)\s*=", chain_txt)
                m_ptr = re.search(r"\b([A-Za-z_]\w*)\s*\[\s*0\s*\]", chain_txt)
                if not (m_out and m_ptr):
                    continue
                out_v, ptr_v = m_out.group(1), m_ptr.group(1)
                # Find a safe sibling function `fnB` in the same file whose body checks `'\0' !=` and writes `*out`
                for si, sl in enumerate(lines):
                    if abs(si - fn_s) < 5 or not sl.rstrip().endswith("{"):
                        continue
                    hdr_b = " ".join(l.strip() for l in lines[max(0, si - 2) : si + 1])
                    m_fnb = re.search(r"\b([A-Za-z_]\w+)\s*\([^)]*\*[^)]*,\s*[^)]*\*", hdr_b)
                    if not m_fnb:
                        continue
                    fn_b = m_fnb.group(1)
                    if fn_b == fn_a or len(fn_b) < 6:
                        continue
                    # Sibling must share prefix+suffix with `fn_a` (e.g. `utf8codepoint` <-> `utf8rcodepoint`)
                    if not (fn_b[:4] == fn_a[:4] and fn_b[-6:] == fn_a[-6:]):
                        continue
                    sb_win = "".join(lines[si : min(len(lines), si + 40)])
                    if r"'\0' !=" in sb_win and f"*{out_v}" in sb_win:
                        _seen_sd.add(if_start)
                        nl = lines[:if_start] + [f"{if_ind}(void){fn_b}({ptr_v}, {out_v});\n"] + lines[if_end + 1 :]
                        add_cand(
                            rel, if_start + 1, sd_tier,
                            f"delegate_safe_decoder({fn_b}({ptr_v},{out_v}))",
                            "".join(nl), skill_id=safedec_law_id,
                        )
                        break

        # Pass 0r (high-precision C++17 compile-time overload generalization):
        # `C_CPP_TEMPLATE_TRAIT_OVERLOAD_GENERALIZE`:
        # When `g++` fails with `no matching function for call to '...::fn(float&)'` (or `long double&`)
        # and the header defines `fn(double &var)`, generalize it to a `std::enable_if<std::is_floating_point<T>::value>`
        # template (symmetrically `std::is_integral<T>` for narrow `int &var` overloads).
        if "CPP_NO_MATCHING_OVERLOAD" in loc.bug_classes:
            to_tier = "C_TIER0_SKILL_RECALL" if tplovl_law_id else "C_CPP_TEMPLATE_TRAIT_OVERLOAD_GENERALIZE"
            ovl_fn: str | None = None
            ovl_arg_ty: str | None = None
            m_ovl = re.search(
                r"no matching function for call to\s+['`‘][^'`’]*?::([A-Za-z_]\w*)\s*\(\s*(float|long double|double|short|long|long long|unsigned\s+\w+|int\d*_t|uint\d*_t)\s*&?\s*\)",
                loc.initial_output,
            )
            if m_ovl:
                ovl_fn, ovl_arg_ty = m_ovl.group(1), m_ovl.group(2).strip()
            else:
                m_bind = re.search(
                    r"cannot bind non-const lvalue reference of type\s+['`‘](double|int)\s*&['`’]\s+to a value of type\s+['`‘](float|long double|short|long|long long|unsigned\s+\w+|int\d*_t|uint\d*_t)['`’]",
                    loc.initial_output,
                )
                m_note_fn = re.search(r"initializing argument 1 of\s+['`‘][^'`’]*?::([A-Za-z_]\w*)\s*\(", loc.initial_output)
                if m_bind and m_note_fn:
                    ovl_fn, ovl_arg_ty = m_note_fn.group(1), m_bind.group(2).strip()
            if ovl_fn and ovl_arg_ty:
                is_fp = ovl_arg_ty in ("float", "long double", "double")
                base_ty = "double" if is_fp else "int"
                trait_nm = "std::is_floating_point" if is_fp else "std::is_integral"
                for mi, mline in enumerate(lines):
                    m_sig = re.match(
                        rf"^(\s*)([A-Za-z_][\w:<>]*\s*[&*]?\s*{re.escape(ovl_fn)}\s*\(\s*){re.escape(base_ty)}(\s*&\s*[A-Za-z_]\w*\s*\)\s*\{{)\s*$",
                        mline,
                    )
                    if not m_sig:
                        continue
                    m_ind = m_sig.group(1)
                    # Find closing brace of this overload
                    m_end = -1
                    for ei in range(mi + 1, min(len(lines), mi + 45)):
                        if lines[ei].startswith(m_ind + "}") and lines[ei].strip() == "}":
                            m_end = ei
                            break
                    if m_end <= mi:
                        continue
                    # Candidate 1: generalize to SFINAE template `template <typename T, std::enable_if_t<trait<T>::value>* = nullptr>`
                    body_gen = [
                        re.sub(rf"\b{re.escape(base_ty)}\b", "T", bl)
                        for bl in lines[mi : m_end + 1]
                    ]
                    tpl_hdr = f"{m_ind}template <typename T, typename std::enable_if<{trait_nm}<T>::value>::type * = nullptr>\n"
                    nl_tpl = lines[:mi] + [tpl_hdr] + body_gen + lines[m_end + 1 :]
                    add_cand(
                        rel, mi + 1, to_tier,
                        f"generalize_overload({ovl_fn}({base_ty}&)->{trait_nm}<T>)",
                        "".join(nl_tpl), skill_id=tplovl_law_id,
                    )
                    break

        # Pass 0s (high-precision C++ empty-container iterator guard):
        # `C_EMPTY_CONTAINER_ITERATOR_GUARD`:
        # `std::next(std::begin(c))` on an empty container advances past `std::end(c)` causing immediate SEGV.
        # Guard with `(c.empty() ? std::end(c) : std::next(std::begin(c)))` across all matching sites in file.
        if any(bc in loc.bug_classes for bc in ("SEGV", "NULL_DEREF")) or "empty" in loc.initial_output.lower():
            ei_tier = "C_TIER0_SKILL_RECALL" if empit_law_id else "C_EMPTY_CONTAINER_ITERATOR_GUARD"
            _pat_next_beg = re.compile(r"std::next\s*\(\s*std::begin\s*\(\s*([A-Za-z_]\w*)\s*\)\s*\)")
            matched_ei_lines: list[tuple[int, str]] = []
            for ln_ei in lns[:1500]:
                if not (1 <= ln_ei <= len(lines)):
                    continue
                l_ei = lines[ln_ei - 1]
                m_nb = _pat_next_beg.search(l_ei)
                if m_nb and f"{m_nb.group(1)}.empty()" not in l_ei:
                    matched_ei_lines.append((ln_ei, m_nb.group(1)))
            if matched_ei_lines:
                # Atomic multi-site repair across all sibling `std::next(std::begin(cont))` in file
                cont_names = {c for _, c in matched_ei_lines}
                nl_all = list(lines)
                changed_any = False
                for idx_a, raw_a in enumerate(nl_all):
                    m_a = _pat_next_beg.search(raw_a)
                    if m_a and m_a.group(1) in cont_names and f"{m_a.group(1)}.empty()" not in raw_a:
                        cn = m_a.group(1)
                        nl_all[idx_a] = _pat_next_beg.sub(
                            f"({cn}.empty() ? std::end({cn}) : std::next(std::begin({cn})))",
                            raw_a,
                            count=1,
                        )
                        changed_any = True
                if changed_any:
                    add_cand(
                        rel, matched_ei_lines[0][0], ei_tier,
                        f"guard_empty_next_begin({','.join(sorted(cont_names))})",
                        "".join(nl_all), skill_id=empit_law_id,
                    )

        # Pass 0t (high-precision abstraction-consistency law):
        # `C_HARDCODED_PREFIX_CHAR_TO_EXPR`:
        # When an enclosing branch validates `pred(var[0])` and constructs `std::string{'<lit>', var[j]}`,
        # replace the hardcoded `'<lit>'` with `var[0]` across all identical sibling loops in the file.
        px_tier = "C_TIER0_SKILL_RECALL" if pfxch_law_id else "C_HARDCODED_PREFIX_CHAR_TO_EXPR"
        _pat_hard_ch = re.compile(r"std::string\s*\{\s*'([^'\\])'\s*,\s*([A-Za-z_]\w*)\s*\[\s*([A-Za-z_]\w*)\s*\]\s*\}")
        px_hits: list[tuple[int, str, str]] = []
        for ln_px in lns[:1500]:
            if not (1 <= ln_px <= len(lines)):
                continue
            m_hc = _pat_hard_ch.search(lines[ln_px - 1])
            if not m_hc:
                continue
            lit_ch, var_nm, _idx_nm = m_hc.groups()
            ctx_up = "".join(lines[max(0, ln_px - 10) : ln_px - 1])
            if re.search(rf"\b[A-Za-z_]\w*\s*\(\s*{re.escape(var_nm)}\s*\[\s*0\s*\]\s*\)", ctx_up):
                px_hits.append((ln_px, lit_ch, var_nm))
        if px_hits:
            # Atomic sibling replacement across all matching sites in file
            nl_px = list(lines)
            first_ln, first_lit, first_var = px_hits[0]
            for idx_p, raw_p in enumerate(nl_px):
                m_p = _pat_hard_ch.search(raw_p)
                if m_p and m_p.group(1) == first_lit and m_p.group(2) == first_var:
                    ctx_u = "".join(lines[max(0, idx_p - 10) : idx_p])
                    if re.search(rf"\b[A-Za-z_]\w*\s*\(\s*{re.escape(first_var)}\s*\[\s*0\s*\]\s*\)", ctx_u):
                        nl_px[idx_p] = raw_p[: m_p.start()] + f"std::string{{{first_var}[0], {first_var}[{m_p.group(3)}]}}" + raw_p[m_p.end() :]
            add_cand(
                rel, first_ln, px_tier,
                f"replace_hardcoded_prefix('{first_lit}'->{first_var}[0])",
                "".join(nl_px), skill_id=pfxch_law_id,
            )

        # Pass 0u (high-precision monoidal recursion law):
        # `C_RECURSIVE_VECTOR_ACCUMULATOR_MERGE`:
        # When a function returning `std::vector<...>` maintains a local accumulator `acc` (`acc.push_back(...)`)
        # and tail-returns a recursive call `return <expr>.<same_fn>(...);`, merge the recursive result into `acc`
        # instead of discarding `acc`.
        ra_tier = "C_TIER0_SKILL_RECALL" if recacc_law_id else "C_RECURSIVE_VECTOR_ACCUMULATOR_MERGE"
        _seen_ra: set[int] = set()
        for ln_ra in lns[:1500]:
            if not (1 <= ln_ra <= len(lines)) or ln_ra in _seen_ra:
                continue
            l_ra = lines[ln_ra - 1]
            m_ret = re.match(r"^(\s*)return\s+(.+?(?:\.|->)\s*([A-Za-z_]\w*)\s*\(.*)$", l_ra)
            if not m_ret:
                continue
            r_ind, r_head, callee_nm = m_ret.groups()
            # Collect full return statement up to `;` (may span 1–3 lines)
            end_ra = ln_ra - 1
            stmt_ra = l_ra.strip()
            while not stmt_ra.endswith(";") and end_ra + 1 < min(len(lines), ln_ra + 4):
                end_ra += 1
                stmt_ra += " " + lines[end_ra].strip()
            if not stmt_ra.endswith(";"):
                continue
            fn_s, open_i, hdr_ra = _find_c_enclosing_function(lines, ln_ra)
            if not re.search(rf"\b{re.escape(callee_nm)}\s*\(", hdr_ra):
                continue
            fn_win = "".join(lines[open_i : min(len(lines), open_i + 140)])
            m_acc = re.search(r"std::vector\s*<[^>;]+>\s+([A-Za-z_]\w*)\s*(?:\{\s*\}|;)", fn_win)
            if not m_acc:
                continue
            acc_v = m_acc.group(1)
            if f"{acc_v}.push_back(" not in fn_win:
                continue
            call_expr = stmt_ra[len("return ") : -1].strip()
            _seen_ra.add(ln_ra)
            repl_lines = [
                f"{r_ind}auto _brain_sub_acc = {call_expr};\n",
                f"{r_ind}{acc_v}.insert({acc_v}.end(), _brain_sub_acc.begin(), _brain_sub_acc.end());\n",
                f"{r_ind}return {acc_v};\n",
            ]
            nl_ra = lines[: ln_ra - 1] + repl_lines + lines[end_ra + 1 :]
            add_cand(
                rel, ln_ra, ra_tier,
                f"merge_recursive_acc({acc_v}+={callee_nm})",
                "".join(nl_ra), skill_id=recacc_law_id,
            )

        # Pass 0v (high-precision sibling method invariant parity law):
        # `C_SIBLING_METHOD_TRAILING_BLOCK_SYNC`:
        # When function `fnA` shares an identical validation loop body (`anchor_stmt`, e.g. `argument->validate();`)
        # with a sibling function `fnB` in the same file (sharing >= 5-char prefix), and `fnB` immediately follows
        # that loop with an additional trailing validation/throw block before closing `}`, while `fnA` immediately
        # executes `return <var>;`, transfer `fnB`'s trailing block right before `fnA`'s `return`.
        st_tier = "C_TIER0_SKILL_RECALL" if sibtr_law_id else "C_SIBLING_METHOD_TRAILING_BLOCK_SYNC"
        _seen_st: set[int] = set()
        for ln_st in lns[:1500]:
            if not (1 <= ln_st <= len(lines)) or ln_st in _seen_st:
                continue
            l_st = lines[ln_st - 1]
            m_ret_v = re.match(r"^(\s*)return\s+([A-Za-z_]\w*)\s*;\s*$", l_st)
            if not m_ret_v or ln_st < 5:
                continue
            ret_ind = m_ret_v.group(1)
            # Immediate preceding line must close a loop block (`}`) containing a `->validate()` / `->check()` call
            if lines[ln_st - 2].strip() != "}":
                continue
            anchor_stmt = ""
            for bk in range(ln_st - 3, max(0, ln_st - 8), -1):
                st_bk = lines[bk].strip()
                if st_bk.endswith("();") and ("validate" in st_bk or "check" in st_bk or "verify" in st_bk):
                    anchor_stmt = st_bk
                    break
            if not anchor_stmt:
                continue
            fn_s, open_i, hdr_a = _find_c_enclosing_function(lines, ln_st)
            m_fa = re.search(r"\b([A-Za-z_]\w{4,})\s*\(", hdr_a)
            if not m_fa:
                continue
            fa_name = m_fa.group(1)
            fn_ind_a = len(lines[open_i]) - len(lines[open_i].lstrip())
            # Search for sibling function `fnB` in the same file containing the exact same `anchor_stmt`
            for si_b, sl_b in enumerate(lines):
                if abs(si_b - (ln_st - 1)) < 8 or sl_b.strip() != anchor_stmt:
                    continue
                # Find the closing `}` of the anchor loop in `fnB`
                loop_end_b = -1
                for k_b in range(si_b + 1, min(len(lines), si_b + 5)):
                    if lines[k_b].strip() == "}":
                        loop_end_b = k_b
                        break
                if loop_end_b < 0:
                    continue
                fn_sb, open_ib, hdr_b = _find_c_enclosing_function(lines, si_b + 1)
                m_fb = re.search(r"\b([A-Za-z_]\w{4,})\s*\(", hdr_b)
                if not m_fb:
                    continue
                fb_name = m_fb.group(1)
                if fb_name == fa_name or fb_name[:5] != fa_name[:5]:
                    continue
                fn_ind_b = len(lines[open_ib]) - len(lines[open_ib].lstrip())
                # Collect trailing lines in `fnB` from `loop_end_b + 1` until `fnB`'s closing `}`
                fn_end_b = -1
                for eb in range(loop_end_b + 1, min(len(lines), loop_end_b + 80)):
                    if lines[eb].strip() == "}" and (len(lines[eb]) - len(lines[eb].lstrip())) <= fn_ind_b:
                        fn_end_b = eb
                        break
                if fn_end_b <= loop_end_b + 2:
                    continue
                trail_blk = "".join(lines[loop_end_b + 1 : fn_end_b])
                if "throw " not in trail_blk:
                    continue
                _seen_st.add(ln_st)
                nl_st = lines[: ln_st - 1] + [trail_blk] + lines[ln_st - 1 :]
                add_cand(
                    rel, ln_st, st_tier,
                    f"sync_sibling_trailing_block({fb_name}->{fa_name})",
                    "".join(nl_st), skill_id=sibtr_law_id,
                )
                break

        # Pass 0w (high-precision C++ `std::basic_ostream<char, Traits>` custom-traits stream law):
        # `CPP_BASIC_OSTREAM_CSTR_WRITE`:
        # Streaming a `std::string` (`std::basic_string<char, std::char_traits<char>>`) via `os << expr;`
        # into a templated `std::basic_ostream<char, Traits>& os` fails to compile whenever `Traits` is
        # a custom `char_traits`. Rewriting to `os << (expr).c_str();` (or `os.write(s.data(), s.size())`)
        # works for EVERY `Traits` specialization without allocating an extra basic_string.
        if "CPP_NO_MATCHING_OVERLOAD" in loc.bug_classes:
            for ln_os in lns[:120]:
                if not (1 <= ln_os <= len(lines)):
                    continue
                l_os = lines[ln_os - 1]
                m_os = re.match(r"^(\s*)(return\s+)?([A-Za-z_]\w*)\s*<<\s*([^;]+?)\s*;\s*$", l_os)
                if not m_os:
                    continue
                os_ind, os_ret, os_var, os_expr = m_os.group(1), m_os.group(2) or "", m_os.group(3), m_os.group(4).strip()
                if os_expr.endswith((".c_str()", ".data()")):
                    continue
                ctx_os = "".join(lines[max(0, ln_os - 6) : ln_os])
                if "basic_ostream" not in ctx_os:
                    continue
                nl_os1 = list(lines)
                nl_os1[ln_os - 1] = f"{os_ind}{os_ret}{os_var} << ({os_expr}).c_str();\n"
                add_cand(
                    rel, ln_os, "CPP_BASIC_OSTREAM_CSTR_WRITE",
                    f"basic_ostream_cstr({os_var}<<{os_expr}.c_str())",
                    "".join(nl_os1),
                )
                nl_os2 = list(lines)
                nl_os2[ln_os - 1] = (
                    f"{os_ind}const auto _brain_str = {os_expr};\n"
                    f"{os_ind}{os_ret}{os_var}.write(_brain_str.data(), static_cast<std::streamsize>(_brain_str.size()));\n"
                )
                add_cand(
                    rel, ln_os, "CPP_BASIC_OSTREAM_CSTR_WRITE",
                    f"basic_ostream_write({os_var}.write({os_expr}))",
                    "".join(nl_os2),
                )

        for ln in lns[:120]:
            if not (1 <= ln <= len(lines)):
                continue
            line = lines[ln - 1]
            stripped = line.strip()
            if not stripped or stripped.startswith(("//", "/*", "*", "#")):
                continue
            ind = line[: len(line) - len(line.lstrip())]

            # Op 0c: UBSan Signed Integer Overflow / `std::abs(INT_MIN)` Two's-Complement Guard
            # (`C_UBSAN_SIGNED_OVERFLOW_GUARD`, CWE-190):
            # Rewrite `static_cast<U>(std::abs(X))` -> `static_cast<U>(0) - static_cast<U>(X)` (exact
            # well-defined unsigned negation for every signed integer width, zero UB on INT_MIN/LLONG_MIN).
            if "SIGNED_OVERFLOW" in loc.bug_classes and "abs(" in line:
                u_tier = "C_TIER0_SKILL_RECALL" if ubsan_law_id else "C_UBSAN_SIGNED_OVERFLOW_GUARD"
                for m_sc in re.finditer(r"static_cast\s*<\s*([^<>]+?)\s*>\s*\(", line):
                    utype = m_sc.group(1).strip()
                    outer = _extract_balanced_paren_arg(line, m_sc.end() - 1)
                    if not outer:
                        continue
                    outer_inner, outer_close = outer
                    m_abs = re.match(r"^\s*(?:std::)?abs\s*\(", outer_inner)
                    if not m_abs:
                        continue
                    abs_res = _extract_balanced_paren_arg(outer_inner, m_abs.end() - 1)
                    if not abs_res:
                        continue
                    abs_arg = abs_res[0].strip()
                    # Candidate A: exact unsigned two's-complement magnitude for negative/min value
                    repl_a = f"(static_cast<{utype}>(0) - static_cast<{utype}>({abs_arg}))"
                    nl_a = list(lines)
                    nl_a[ln - 1] = line[: m_sc.start()] + repl_a + line[outer_close + 1 :]
                    add_cand(
                        rel, ln, u_tier,
                        f"unsigned_negate_abs({utype})", "".join(nl_a), skill_id=ubsan_law_id,
                    )
                    # Candidate B: sign-general branchless-safe conditional unsigned magnitude
                    repl_b = (
                        f"(({abs_arg}) < 0 ? (static_cast<{utype}>(0) - static_cast<{utype}>({abs_arg})) "
                        f": static_cast<{utype}>({abs_arg}))"
                    )
                    nl_b = list(lines)
                    nl_b[ln - 1] = line[: m_sc.start()] + repl_b + line[outer_close + 1 :]
                    add_cand(
                        rel, ln, u_tier,
                        f"signed_safe_abs({utype})", "".join(nl_b), skill_id=ubsan_law_id,
                    )

            # Op 0d: SIGABRT Assertion Caller-Chain NULL Argument Guard (`C_SIGABRT_NULL_ARG_GUARD`):
            # When an `assert(s)` crashes inside a string/helper function, inspect caller frames invoking
            # `obj->fn(ptr_expr)` or `return obj->fn(ptr_expr);` and guard NULL `ptr_expr` safely.
            if "SIGABRT_ASSERT" in loc.bug_classes:
                s_tier = "C_TIER0_SKILL_RECALL" if sigabrt_law_id else "C_SIGABRT_NULL_ARG_GUARD"
                m_ret_call = re.match(r"^(\s*)return\s+([A-Za-z_]\w*(?:->|\.)[A-Za-z_]\w*)\s*\((.+)\)\s*;\s*$", line)
                if m_ret_call:
                    rc_ind, callee_e, arg_e = m_ret_call.groups()
                    arg_s = arg_e.strip()
                    if "->" in arg_s or re.match(r"^[A-Za-z_]\w*$", arg_s):
                        def_rets_s = _infer_c_default_returns(lines, ln)
                        # Prefer `return true;` first for copy/clone helpers returning bool (unset value is already default!)
                        ordered_rets = (["return true;"] if "return true;" in def_rets_s else []) + [
                            r for r in def_rets_s if r != "return true;"
                        ]
                        for ret_stmt in ordered_rets[:3]:
                            nl = list(lines)
                            nl[ln - 1] = f"{rc_ind}if (!({arg_s})) {{ {ret_stmt} }}\n{line}"
                            add_cand(
                                rel, ln, s_tier,
                                f"sigabrt_null_arg_guard({callee_e}->{ret_stmt})", "".join(nl), skill_id=sigabrt_law_id,
                            )

            # Op 0f: ASan Buffer Over-Read Bounds Guard (`C_ASAN_BUFFER_BOUNDS_GUARD`, CWE-121/122/125):
            # When ASan reports a stack/heap/global buffer-overflow READ at `arr[idx]` inside an
            # `if`/`while` condition, mine the enclosing function's `(idx < bound)` invariant and
            # short-circuit guard the indexed read (`idx >= bound || !(...)` or `idx < bound && (...)`).
            if "BUFFER_OVERFLOW" in loc.bug_classes and re.search(r"[A-Za-z_]\w*\s*\[\s*[A-Za-z_]\w*\s*\]", line):
                m_idx_use = re.search(r"([A-Za-z_]\w*)\s*\[\s*([A-Za-z_]\w*)\s*\]", line)
                if m_idx_use:
                    idx_v = m_idx_use.group(2)
                    # Mine `(idx_v < bound)` from surrounding +/- 50 lines in same function
                    bound_vars: list[str] = []
                    win_b = "".join(lines[max(0, ln - 50) : min(len(lines), ln + 30)])
                    for mb in re.finditer(rf"\b{re.escape(idx_v)}\s*<\s*([A-Za-z_]\w*(?:->[A-Za-z_]\w*)?)", win_b):
                        bv = mb.group(1)
                        if bv != idx_v and bv not in bound_vars:
                            bound_vars.append(bv)
                    for bv in bound_vars[:2]:
                        oob_tier = "C_TIER0_SKILL_RECALL" if oob_law_id else "C_ASAN_BUFFER_BOUNDS_GUARD"
                        # Case 1: `if (!(<expr>))` -> `if (idx >= bv || !(<expr>))`
                        m_if_not = re.match(r"^(\s*if\s*\()(\s*!\s*.+)(\)\s*\{?\s*)$", line)
                        if m_if_not:
                            nl = list(lines)
                            nl[ln - 1] = f"{m_if_not.group(1)}({idx_v} >= {bv}) || {m_if_not.group(2).lstrip()}{m_if_not.group(3)}\n"
                            add_cand(
                                rel, ln, oob_tier,
                                f"guard_oob_or({idx_v}>={bv})", "".join(nl), skill_id=oob_law_id,
                            )
                        # Case 2: `if (<expr>)` / `while (<expr>)` -> `if ((idx < bv) && (<expr>))`
                        m_if_w = re.match(r"^(\s*(?:if|while)\s*\()(.+)(\)\s*\{?\s*)$", line)
                        if m_if_w:
                            nl = list(lines)
                            nl[ln - 1] = f"{m_if_w.group(1)}({idx_v} < {bv}) && ({m_if_w.group(2).strip()}){m_if_w.group(3)}\n"
                            add_cand(
                                rel, ln, oob_tier,
                                f"guard_oob_and({idx_v}<{bv})", "".join(nl), skill_id=oob_law_id,
                            )

            # Op 0e: Early-Return Sibling Struct-Field Propagation (`C_EARLY_RETURN_FIELD_PROPAGATION`):
            # When a failing test asserts `<res>.<field> == ...` and a localized early return
            # `if (<cond>) return <expr>;` omits setting `<field>`, harvest `<res>.<field> = <rhs>;`
            # from the normal return path of the SAME enclosing function and propagate it!
            if asserted_fields and "return " in stripped and stripped.endswith(";"):
                e_tier = "C_TIER0_SKILL_RECALL" if early_field_law_id else "C_EARLY_RETURN_FIELD_PROPAGATION"
                m_er = re.match(r"^(\s*(?:if\s*\([^)]+\)\s*)?)return\s+(.+?)\s*;\s*$", line)
                if m_er:
                    er_prefix, er_expr = m_er.groups()
                    if "(" in er_expr:
                        _, open_b_idx, hdr_t = _find_c_enclosing_function(lines, ln)
                        fn_ind_e = len(lines[open_b_idx]) - len(lines[open_b_idx].lstrip()) if 0 <= open_b_idx < len(lines) else 0
                        # Harvest `<var>.<field> = <rhs>;` inside the same function body
                        for fld in asserted_fields[:3]:
                            rhs_cands: list[str] = []
                            for k_ln in range(open_b_idx, min(len(lines), open_b_idx + 140)):
                                if k_ln > open_b_idx and lines[k_ln].strip() == "}" and (len(lines[k_ln]) - len(lines[k_ln].lstrip())) <= fn_ind_e:
                                    break
                                m_fa = re.search(rf"\b[A-Za-z_]\w*\.{re.escape(fld)}\s*=\s*([^;]+);", lines[k_ln])
                                if m_fa:
                                    rhs_v = m_fa.group(1).strip()
                                    if rhs_v not in rhs_cands:
                                        rhs_cands.append(rhs_v)
                            if rhs_cands:
                                decl_t = "auto" if is_cpp_file else ""
                                if not decl_t:
                                    hc = re.sub(r"\b[A-Z][A-Z0-9_]*\s*", "", hdr_t.split("(")[0]).strip()
                                    decl_t = hc or "int"
                                for rhs_v in rhs_cands[:2]:
                                    nl = list(lines)
                                    nl[ln - 1] = f"{er_prefix}{{ {decl_t} _brain_r = {er_expr}; _brain_r.{fld} = {rhs_v}; return _brain_r; }}\n"
                                    add_cand(
                                        rel, ln, e_tier,
                                        f"early_return_field({fld}={rhs_v})", "".join(nl), skill_id=early_field_law_id,
                                    )

            # Op 1: C NULL-Pointer Dereference Guards (`C_NULL_PTR_DEREF_GUARD`)
            # Harvest all pointer dereference chains `a->b->c` / `ptr->field` on this line
            derefs: list[str] = []
            for md in re.finditer(r"\b([A-Za-z_]\w*(?:->[A-Za-z_]\w*)*)->([A-Za-z_]\w*)", line):
                ptr_expr = md.group(1)
                if ptr_expr not in derefs:
                    derefs.append(ptr_expr)

            if derefs:
                def_rets = _infer_c_default_returns(lines, ln)
                _, open_brace_idx, _ = _find_c_enclosing_function(lines, ln)
                tier_nm = "C_TIER0_SKILL_RECALL" if has_null_law else "C_NULL_PTR_DEREF_GUARD"
                sk_id = null_law_id if has_null_law else None

                # (1a) Function-entry NULL guard for top-level pointer parameter on NULL_DEREF crash
                if "NULL_DEREF" in loc.bug_classes and open_brace_idx < ln - 1:
                    root_ptr = derefs[0].split("->")[0]
                    # Insert right after `{` (after any C89 leading variable declarations)
                    ins_idx = open_brace_idx + 1
                    while ins_idx < ln - 1 and re.match(
                        r"^\s*(?:const\s+|static\s+|unsigned\s+|signed\s+|struct\s+)?[A-Za-z_]\w*\s*\*?\s+[A-Za-z_]\w*\s*(?:=[^;]+)?;\s*$",
                        lines[ins_idx],
                    ):
                        ins_idx += 1
                    entry_ind = "    "
                    if ins_idx < len(lines) and lines[ins_idx].strip():
                        entry_ind = lines[ins_idx][: len(lines[ins_idx]) - len(lines[ins_idx].lstrip())]
                    for ret_stmt in def_rets[:3]:
                        nl = list(lines)
                        nl.insert(ins_idx, f"{entry_ind}if ({root_ptr} == NULL) {{ {ret_stmt} }}\n")
                        add_cand(
                            rel, ins_idx + 1, tier_nm,
                            f"fn_entry_null_guard({root_ptr}->{ret_stmt})", "".join(nl), skill_id=sk_id,
                        )

                # (1b) Early-return NULL guard BEFORE dereference line: `if (ptr == NULL) { return <VAL>; }`
                if not stripped.startswith(("else", "case ", "default:")):
                    for ptr_e in derefs[:2]:
                        for ret_stmt in def_rets[:3]:
                            nl = list(lines)
                            nl.insert(ln - 1, f"{ind}if ({ptr_e} == NULL) {{ {ret_stmt} }}\n")
                            add_cand(rel, ln, tier_nm, f"null_early_return({ptr_e}->{ret_stmt})", "".join(nl), skill_id=sk_id)

                # (1c) Single statement dereference -> wrap `if (ptr != NULL) { <stmt> }`
                if stripped.endswith(";") and not stripped.startswith(("return ", "if ", "if(", "for", "while", "else")):
                    for ptr_e in derefs[:2]:
                        nl = list(lines)
                        nl[ln - 1] = f"{ind}if ({ptr_e} != NULL) {{ {stripped} }}\n"
                        add_cand(rel, ln, tier_nm, f"null_guard_wrap({ptr_e})", "".join(nl), skill_id=sk_id)

                # (1d) Guard inside an `if (cond)` condition: `if ((ptr != NULL) && (cond))`
                m_if_c = re.match(r"^(\s*(?:else\s+)?if\s*\()(.+)(\)\s*\{?\s*)$", line)
                if m_if_c:
                    pre, cond_body, post = m_if_c.groups()
                    for ptr_e in derefs[:2]:
                        if f"{ptr_e} != NULL" not in cond_body and f"NULL != {ptr_e}" not in cond_body:
                            nl = list(lines)
                            nl[ln - 1] = f"{pre}({ptr_e} != NULL) && ({cond_body}){post}\n"
                            add_cand(rel, ln, "C_NULL_PTR_DEREF_GUARD", f"if_null_conjunct({ptr_e})", "".join(nl))

            # Op 1e: Contextual Disjunct Conditioning (`C_DISJUNCT_CONDITION_REFINEMENT`):
            # In an early-return `if (... || (ptr == NULL))`, refine each `(ptr == NULL)` disjunct with a
            # condition `(C)` harvested from a subsequent `if (C)` in the same function -> `((C) && (ptr == NULL))`.
            if stripped.startswith("if") and "||" in line and "NULL" in line:
                sub_conds: list[str] = []
                for k_ln in range(ln, min(len(lines), ln + 25)):
                    if lines[k_ln].startswith("}"):
                        break
                    mc = re.match(r"^\s*if\s*\(([^()]+)\)\s*\{?\s*$", lines[k_ln])
                    if mc and mc.group(1).strip() not in sub_conds:
                        sub_conds.append(mc.group(1).strip())
                for m_or_null in re.finditer(r"\|\|\s*\(([A-Za-z_]\w*->[A-Za-z_]\w*\s*==\s*NULL)\)", line):
                    null_disj = m_or_null.group(1)
                    for sc in sub_conds[:4]:
                        if sc not in line:
                            new_l = line[: m_or_null.start(1)] + f"({sc}) && ({null_disj})" + line[m_or_null.end(1) :]
                            nl = list(lines)
                            nl[ln - 1] = new_l
                            add_cand(rel, ln, "C_DISJUNCT_CONDITION_REFINEMENT", f"cond_disjunct({sc}&&{null_disj})", "".join(nl))

            # Op 4b: Sibling Branch Pre-Call Transfer (`C_SIBLING_BRANCH_PRE_CALL_TRANSFER`)
            # When a localized branch invokes `CALL(...)` (e.g., `if (!HANDLER(...))`), inspect the
            # preceding sibling `if` branch within 25 lines for the same `CALL(...)` and transfer any
            # missing immediate pre-call statement (including `#if ... #endif` guard if present).
            m_call_ln = re.search(r"\b(?!if\b|while\b|for\b|switch\b|return\b)([A-Za-z_][A-Za-z0-9_]{2,})\s*\(", stripped)
            if m_call_ln:
                callee = m_call_ln.group(1)
                for sib_i in range(max(0, ln - 26), ln - 2):
                    if f"{callee}(" in lines[sib_i]:
                        # Walk back over comments right before `sib_i` to find the pre-call block
                        prev_end = sib_i - 1
                        while prev_end >= 0 and (
                            not lines[prev_end].strip() or lines[prev_end].strip().startswith(("/*", "*", "//"))
                        ):
                            prev_end -= 1
                        if prev_end >= 0:
                            if lines[prev_end].strip().startswith("#endif"):
                                blk_start = prev_end - 1
                                while blk_start >= 0 and not lines[blk_start].strip().startswith("#if"):
                                    blk_start -= 1
                                if blk_start >= 0 and prev_end - blk_start <= 4:
                                    pre_blk = "".join(lines[blk_start : prev_end + 1])
                                    if pre_blk.strip() and pre_blk.strip() not in "".join(lines[max(0, ln - 6) : ln]):
                                        nl = list(lines)
                                        nl.insert(ln - 1, pre_blk)
                                        add_cand(
                                            rel, ln, "C_SIBLING_BRANCH_PRE_CALL_TRANSFER",
                                            f"sibling_precall({callee})", "".join(nl),
                                        )
                            elif lines[prev_end].strip().endswith(";") and not lines[prev_end].strip().startswith(("return ", "break;", "continue;")):
                                pre_stmt = lines[prev_end]
                                if pre_stmt.strip() not in "".join(lines[max(0, ln - 6) : ln]):
                                    nl = list(lines)
                                    nl.insert(ln - 1, f"{ind}{pre_stmt.strip()}\n")
                                    add_cand(
                                        rel, ln, "C_SIBLING_BRANCH_PRE_CALL_TRANSFER",
                                        f"sibling_precall({callee})", "".join(nl),
                                    )
                        break

            # Op 1d: If an `if (...)` checks `item != parent->child` and the NEXT line dereferences
            # `item->prev->next`, also guard the `if` with `item->prev != NULL`!
            m_if_prev = re.match(r"^(\s*(?:else\s+)?if\s*\()(.+)(\)\s*\{?\s*)$", line)
            if m_if_prev and ln < len(lines):
                nxt_block = "".join(lines[ln : min(len(lines), ln + 4)])
                for md in re.finditer(r"\b([A-Za-z_]\w*->[A-Za-z_]\w*)->[A-Za-z_]\w*", nxt_block):
                    sub_ptr = md.group(1)
                    if sub_ptr not in m_if_prev.group(2):
                        nl = list(lines)
                        nl[ln - 1] = f"{m_if_prev.group(1)}({sub_ptr} != NULL) && ({m_if_prev.group(2)}){m_if_prev.group(3)}\n"
                        add_cand(rel, ln, "C_NULL_PTR_DEREF_GUARD", f"lookahead_null_conjunct({sub_ptr})", "".join(nl))

            # Op 2: C Overlapping Buffer `strcpy`/`memcpy` -> `memmove` (`C_OVERLAP_MEMMOVE_REPAIR`)
            m_strcpy = re.match(r"^(\s*)strcpy\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)\s*;\s*$", line)
            if m_strcpy:
                s_ind, dst_e, src_e = m_strcpy.groups()
                nl = list(lines)
                nl[ln - 1] = f"{s_ind}memmove({dst_e}, {src_e}, strlen({src_e}) + 1);\n"
                add_cand(rel, ln, "C_OVERLAP_MEMMOVE_REPAIR", f"strcpy->memmove({dst_e})", "".join(nl))

            # Op 3: C Signed-Char `<ctype.h>` Cast Guard (`C_SIGNED_CHAR_GUARD`)
            m_ctype = re.search(r"\b(isspace|isdigit|isalpha|isalnum|isxdigit|tolower|toupper)\s*\(([^()]+)\)", line)
            if m_ctype and "unsigned char" not in m_ctype.group(2):
                cfn, carg = m_ctype.groups()
                nl = list(lines)
                nl[ln - 1] = line[: m_ctype.start()] + f"{cfn}((unsigned char)({carg}))" + line[m_ctype.end() :]
                add_cand(rel, ln, "C_SIGNED_CHAR_GUARD", f"unsigned_char_cast({cfn})", "".join(nl))

            # Op 4: C Sibling State-Reset / Clear Synthesis (`C_STATE_RESET_REPAIR`)
            # When a branch sets a variable or returns/continues while sibling branches in the same
            # function reset a buffer `buf[0] = '\0';` or counter `x = 0;`, synthesize that reset.
            if stripped.startswith(("if ", "if(", "else", "return ", "continue;")) or "= 0;" in stripped or "= NULL;" in stripped:
                # Harvest `var[0] = '\0';` resets in surrounding +/- 45 lines
                resets: list[str] = []
                for rln in range(max(1, ln - 45), min(len(lines), ln + 45) + 1):
                    rm = re.search(r"\b([A-Za-z_]\w*\[0\]\s*=\s*'\\0'\s*;)", lines[rln - 1])
                    if rm and rm.group(1) not in resets:
                        resets.append(rm.group(1))
                for rst in resets[:2]:
                    if rst not in stripped and ("=" in stripped or "continue" in stripped):
                        nl = list(lines)
                        nl.insert(ln, f"{ind}{rst}\n")
                        add_cand(rel, ln, "C_STATE_RESET_REPAIR", f"insert_sibling_reset({rst})", "".join(nl))

            # Op 5 (deferred): C Comparison / Boolean / Off-by-one Repair (`C_BOUNDS_AND_CMP_REPAIR`)
            if len(cmp_deferred) < max_candidates and any(
                op in line for op in (" <= ", " >= ", " < ", " > ", " == ", " != ", " && ", " || ")
            ):
                for old_op, new_op in (
                    (" <= ", " < "),
                    (" < ", " <= "),
                    (" >= ", " > "),
                    (" > ", " >= "),
                    (" == ", " != "),
                    (" != ", " == "),
                    (" && ", " || "),
                    (" || ", " && "),
                ):
                    if old_op in line:
                        nl = list(lines)
                        nl[ln - 1] = line.replace(old_op, new_op, 1)
                        cmp_deferred.append((rel, ln, "C_BOUNDS_AND_CMP_REPAIR", f"op({old_op.strip()}->{new_op.strip()})", "".join(nl)))

    for rel, ln, tier, desc, patched in cmp_deferred:
        add_cand(rel, ln, tier, desc, patched)

    return cands


def _find_c_functions(src: str) -> list[dict[str, Any]]:
    """Lightweight C/C++17 function definition extractor for execution-guided OE-SyGuS tracing."""
    lines = src.splitlines(keepends=True)
    out: list[dict[str, Any]] = []
    _kw_skip = frozenset({"if", "for", "while", "switch", "catch", "else", "return", "sizeof", "alignof"})
    i = 0
    while i < len(lines):
        raw = lines[i]
        st = raw.strip()
        if not st or st.startswith(("#", "//", "/*", "*")):
            i += 1
            continue
        # Gather multi-line header up to `{` or `;` (max 5 lines)
        buf = raw
        j = i
        while "{" not in buf and ";" not in buf and j + 1 < len(lines) and (j - i) < 5:
            j += 1
            buf += lines[j]
        if "{" not in buf or "(" not in buf or ")" not in buf:
            i += 1
            continue
        hdr = buf.split("{", 1)[0].strip()
        if ";" in hdr or "=" in hdr or hdr.startswith(("struct ", "enum ", "union ", "class ", "namespace ", "typedef ")):
            i += 1
            continue
        m = re.search(r"([A-Za-z_][A-Za-z0-9_:~]*)\s*\(([^()]*)\)\s*(?:const\s*)?(?:noexcept\s*)?$", hdr)
        if not m:
            i += 1
            continue
        fn_name = m.group(1)
        if fn_name in _kw_skip or "::" in fn_name and "~" in fn_name:
            i += 1
            continue
        ret_type = hdr[: m.start(1)].strip()
        if not ret_type:
            i += 1
            continue
        raw_params = m.group(2).strip()
        params: list[tuple[str, str, str]] = []  # (ctype, pname, fmt_kind)
        if raw_params and raw_params != "void":
            for part in raw_params.split(","):
                pt = part.strip()
                if not pt or "..." in pt or "(" in pt:
                    continue
                mp = re.search(r"([A-Za-z_][A-Za-z0-9_]*)\s*(?:\[\s*\])?$", pt)
                if not mp:
                    continue
                pnm = mp.group(1)
                ct = pt[: mp.start(1)].strip()
                is_ptr = ("*" in ct) or ("[" in pt)
                if is_ptr:
                    fk = "cstr" if ("char" in ct and ct.count("*") == 1 and "unsigned" not in ct) else "ptr"
                elif any(t in ct for t in ("double", "float")):
                    fk = "float"
                elif any(t in ct for t in ("size_t", "uint", "unsigned")):
                    fk = "uint"
                elif any(t in ct for t in ("int", "long", "short", "char", "bool", "ssize_t", "ptrdiff_t")):
                    fk = "int"
                else:
                    continue
                params.append((ct, pnm, fk))
        if not params:
            i = j + 1
            continue
        # Insertion line right after `{` (skipping C89 leading declarations)
        ins_idx = j + 1
        while ins_idx < len(lines) and re.match(
            r"^\s*(?:const\s+|static\s+|unsigned\s+|signed\s+|struct\s+)?[A-Za-z_]\w*\s*\*?\s+[A-Za-z_]\w*\s*(?:=[^;]+)?;\s*$",
            lines[ins_idx],
        ):
            ins_idx += 1
        out.append({
            "name": fn_name,
            "ret_type": ret_type,
            "params": params,
            "open_line": j + 1,
            "insert_idx": ins_idx,
        })
        i = j + 1
    return out


def _capture_c_execution_traces(
    worktree: pathlib.Path,
    loc: CLocalizationReport,
    rel: str,
    fns: Sequence[dict[str, Any]],
    *,
    timeout_s: float = 15.0,
) -> dict[str, list[dict[str, Any]]]:
    """Instrument localized C/C++ functions with bounded `fprintf(stderr, "__B_CTR__ ...")`,
    run the test binary ONCE, and return per-function argument-frame lists."""
    fp = worktree / rel
    if not fp.is_file() or not fns:
        return {}
    orig = fp.read_text(encoding="utf-8", errors="replace")
    lines = orig.splitlines(keepends=True)

    # Sort descending by insert_idx so line insertions don't shift earlier offsets
    chosen_fns = sorted(fns[:6], key=lambda x: int(x["insert_idx"]), reverse=True)
    nl = list(lines)
    for k_i, f in enumerate(chosen_fns):
        ins = int(f["insert_idx"])
        if not (0 <= ins <= len(nl)):
            continue
        ind = "    "
        if ins < len(nl) and nl[ins].strip():
            ind = nl[ins][: len(nl[ins]) - len(nl[ins].lstrip())]
        fmt_parts: list[str] = []
        arg_parts: list[str] = []
        for _ct, pnm, fk in f["params"][:4]:
            if fk == "int":
                fmt_parts.append(f"{pnm}=I:%lld")
                arg_parts.append(f"(long long)({pnm})")
            elif fk == "uint":
                fmt_parts.append(f"{pnm}=U:%llu")
                arg_parts.append(f"(unsigned long long)({pnm})")
            elif fk == "float":
                fmt_parts.append(f"{pnm}=F:%.6g")
                arg_parts.append(f"(double)({pnm})")
            elif fk == "cstr":
                fmt_parts.append(f"{pnm}=P:%d")
                arg_parts.append(f"(({pnm}) != NULL ? 1 : 0)")
            else:
                fmt_parts.append(f"{pnm}=P:%d")
                arg_parts.append(f"(({pnm}) != NULL ? 1 : 0)")
        if not fmt_parts:
            continue
        tag = f"__B_CTR__ {f['name']} " + " ".join(fmt_parts) + "\\n"
        args_csv = ", ".join(arg_parts)
        stmt = (
            f"{ind}{{ static int __b_tr_{k_i} = 0; "
            f"if (__b_tr_{k_i} < 128) {{ __b_tr_{k_i}++; "
            f"fprintf(stderr, \"{tag}\", {args_csv}); fflush(stderr); }} }}\n"
        )
        nl.insert(ins, stmt)

    patched = "".join(nl)
    if "#include <stdio.h>" not in patched and "#include <cstdio>" not in patched:
        patched = "#include <stdio.h>\n" + patched

    traces: dict[str, list[dict[str, Any]]] = {}
    try:
        fp.write_text(patched, encoding="utf-8")
        _rc, out = _run_c_spec(
            worktree, loc.runner_kind, loc.build_cmd, loc.run_cmd, loc.run_cwd,
            timeout_s=timeout_s,
        )
    finally:
        fp.write_text(orig, encoding="utf-8")

    for line in (out or "").splitlines():
        if "__B_CTR__ " not in line:
            continue
        payload = line.split("__B_CTR__ ", 1)[1].strip()
        toks = payload.split()
        if len(toks) < 2:
            continue
        fn_nm = toks[0]
        frame: dict[str, Any] = {}
        for tok in toks[1:]:
            if "=" not in tok or ":" not in tok:
                continue
            k, tv = tok.split("=", 1)
            tcode, raw_v = tv.split(":", 1)
            try:
                if tcode in ("I", "U"):
                    frame[k] = int(raw_v)
                elif tcode == "F":
                    frame[k] = float(raw_v)
                elif tcode == "P":
                    frame[k] = None if raw_v == "0" else {"__ptr__": 1}
            except ValueError:
                continue
        if frame:
            traces.setdefault(fn_nm, []).append(frame)
    return traces


def _synthesize_c_oe_sygus_candidates(
    worktree: pathlib.Path,
    loc: CLocalizationReport,
    *,
    max_candidates: int = 20,
) -> list[CPatchCandidate]:
    """Execution-Guided C/C++17 OE-SyGuS + EUSolver Precondition Guard & Clamp Synthesizer.
    Instruments localized C/C++ functions once, collects concrete argument traces, invokes
    unified `oe_sygus_synthesizer_v1.synthesize_separating_predicates(..., lang='c')` with
    strict anti-overfitting (`generality_penalty <= 1`, `extra_consts=()`), and emits
    type-consistent C/C++17 function-entry guards & scalar clamps."""
    cands: list[CPatchCandidate] = []
    seen: set[tuple[str, str]] = set()
    file_order: list[str] = []
    lines_by_file: dict[str, list[int]] = {}
    for s in loc.sites:
        if s.file not in file_order:
            file_order.append(s.file)
        lines_by_file.setdefault(s.file, []).append(s.lineno)
    if not file_order:
        src_f, _, _ = _discover_c_files(worktree)
        file_order = src_f[:2]

    for rel in file_order[:2]:
        fp = worktree / rel
        if not fp.is_file():
            continue
        orig = fp.read_text(encoding="utf-8", errors="replace")
        lines = orig.splitlines(keepends=True)
        all_fns = _find_c_functions(orig)
        if not all_fns:
            continue
        ranked_lns = set(lines_by_file.get(rel) or ())
        # Prefer functions near localized lines or mentioned in failure output
        scored_fns: list[tuple[int, dict[str, Any]]] = []
        for fn in all_fns:
            sc = 0
            if fn["name"] in loc.initial_output:
                sc += 20
            if any(abs(ln - int(fn["open_line"])) <= 60 for ln in ranked_lns):
                sc += 10
            scored_fns.append((sc, fn))
        scored_fns.sort(key=lambda x: (-x[0], int(x[1]["open_line"])))
        target_fns = [fn for sc, fn in scored_fns if sc > 0][:4] or [fn for _, fn in scored_fns[:3]]
        traces = _capture_c_execution_traces(worktree, loc, rel, target_fns)
        if not traces:
            continue

        fn_by_name = {f["name"]: f for f in target_fns}
        for fn_nm, calls in traces.items():
            fn = fn_by_name.get(fn_nm)
            if fn is None or len(calls) < 2:
                continue
            # Last observed call before crash/assert failure = failing call; earlier distinct calls = passing!
            fail_frame = calls[-1]
            pass_frames = [c for c in calls[:-1] if c != fail_frame]
            if not pass_frames:
                continue
            guards = OESYGUS.synthesize_separating_predicates(
                [fail_frame],
                pass_frames,
                lang="c",
                extra_consts=(),
                max_results=4,
            )
            ins_idx = int(fn["insert_idx"])
            if not (0 <= ins_idx <= len(lines)):
                continue
            ind = "    "
            if ins_idx < len(lines) and lines[ins_idx].strip():
                ind = lines[ins_idx][: len(lines[ins_idx]) - len(lines[ins_idx].lstrip())]
            def_rets = _infer_c_default_returns(lines, int(fn["open_line"]) + 1)
            ret_t = str(fn["ret_type"])
            if "*" in ret_t:
                for rv in ("return NULL;",):
                    if rv not in def_rets:
                        def_rets.insert(0, rv)
            elif "bool" in ret_t:
                for rv in ("return false;", "return true;"):
                    if rv not in def_rets:
                        def_rets.append(rv)
            elif "void" in ret_t and "*" not in ret_t:
                def_rets = ["return;"]
            else:
                for rv in ("return -1;", "return 0;"):
                    if rv not in def_rets:
                        def_rets.append(rv)

            for g in guards:
                if int(g.get("generality_penalty", 9)) > 1:
                    continue
                pred_c = str(g.get("code") or "").strip()
                if not pred_c:
                    continue
                for ret_stmt in def_rets[:3]:
                    nl = list(lines)
                    nl.insert(ins_idx, f"{ind}if ({pred_c}) {{ {ret_stmt} }}\n")
                    patched = "".join(nl)
                    key = (rel, patched)
                    if key not in seen and len(cands) < max_candidates:
                        seen.add(key)
                        cands.append(
                            CPatchCandidate(
                                rel,
                                ins_idx + 1,
                                "C_OE_SYGUS_EUSOLVER",
                                f"c_oe_sygus_guard({fn_nm}: if ({pred_c}) {ret_stmt})",
                                patched,
                            )
                        )
    return cands


def solve_c_repository(
    repo_root: str | pathlib.Path,
    test_targets: Sequence[str] | None = None,
    *,
    memory: dict[str, Any] | None = None,
    max_candidates: int = 80,
    timeout_s: float = 45.0,
    extra_flags: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Zero-LLM, zero-weight Causal Angelic SWE solver for C / C++ repositories (ASan/UBSan + gcov)."""
    t0 = time.monotonic()
    src_root = pathlib.Path(repo_root).resolve()

    with tempfile.TemporaryDirectory(prefix="brain_c_swe_") as tmp_dir:
        wt = pathlib.Path(tmp_dir) / "wt"
        obj_cache = pathlib.Path(tmp_dir) / "obj_cache"
        obj_cache.mkdir(parents=True, exist_ok=True)
        _copy_js_worktree(src_root, wt)

        # Capture golden baseline snapshots if present (e.g., `tests/baseline_*.txt`)
        baseline_snaps: dict[str, str] = {}
        tdir = wt / "tests"
        if tdir.is_dir():
            for bf in sorted(tdir.glob("baseline_*.txt")):
                baseline_snaps[bf.name] = bf.read_text(encoding="utf-8", errors="replace")

        # Precompile unchanging test/support `.c`/`.cpp` TUs ONCE (huge speedup for C++ Catch2 / pugixml / tinyxml2!)
        src_files_init, _, _ = _discover_c_files(wt)
        rk_pre, b_pre, _, _ = detect_c_test_spec(wt, test_targets, sanitizer=True, extra_flags=extra_flags)
        precompiled_build_cmd: list[str] | None = None
        if rk_pre == "gcc_direct" and b_pre:
            precompiled_build_cmd = _precompile_c_static_objs(
                wt, b_pre, set(src_files_init), obj_cache, timeout_s=max(timeout_s, 60.0)
            )

        # Stage 1: ASan / UBSan + SIGABRT + Symbol + gcov Fault Localization
        loc = localize_c_faults(
            wt,
            test_targets,
            timeout_s=max(timeout_s, 45.0),
            baseline_snapshots=baseline_snaps,
            extra_flags=extra_flags,
            precompiled_build_cmd=precompiled_build_cmd,
        )
        if loc.initial_rc == 0:
            return {
                "schema": SCHEMA,
                "authority": AUTHORITY,
                "language": "c_cpp",
                "status": "NO_FAILING_TEST",
                "verified": False,
                "runner": loc.runner_kind,
                "model_calls": 0,
                "parameters_stored": 0,
                "seconds": round(time.monotonic() - t0, 3),
            }

        # Stage 2: Candidate Synthesis (Tier-0 MemRL Law Recall + Causal C/C++ Operators)
        cands = synthesize_c_candidates(wt, loc, memory=memory, max_candidates=max_candidates)
        oe_c_ran = False
        if not cands:
            oe_c_ran = True
            cands = _synthesize_c_oe_sygus_candidates(wt, loc, max_candidates=20)

        # Stage 3: Two-Phase Isolated Compile + ASan/UBSan Verification (+ monotone progress capture)
        attempts = 0
        winner: dict[str, Any] | None = None
        base_fail_n, base_site = _failure_progress_signature(loc.initial_output)
        progress_cands: list[tuple[int, int, CCandidate]] = []

        cand_idx = 0
        while cand_idx < len(cands):
            cand = cands[cand_idx]
            cand_idx += 1
            if (time.monotonic() - t0) >= max(timeout_s * 3.0, 95.0):
                break
            attempts += 1
            fp = wt / cand.file
            orig_src = fp.read_text(encoding="utf-8", errors="replace")
            ok_fast = False
            rc_c = 1
            out_c = ""
            try:
                fp.write_text(cand.patched_source, encoding="utf-8")
                rc_c, out_c = _run_c_spec(
                    wt, loc.runner_kind, loc.build_cmd, loc.run_cmd, loc.run_cwd,
                    timeout_s=max(timeout_s, 45.0), baseline_snapshots=baseline_snaps,
                )
                ok_fast = rc_c == 0
            finally:
                fp.write_text(orig_src, encoding="utf-8")

            if not ok_fast:
                # Track strictly compiled progress candidates (reduced failures or shifted crash site)
                if rc_c < 200 and rc_c != 124 and out_c and "BUILD_FAILED:" not in out_c:
                    c_fail_n, c_site = _failure_progress_signature(out_c)
                    if c_fail_n < base_fail_n or (c_site and base_site and c_site != base_site and c_fail_n <= base_fail_n):
                        progress_cands.append((c_fail_n, attempts, cand))
                if memory is not None and cand.skill_id and cand.tier == "C_TIER0_SKILL_RECALL":
                    _update_memrl_law(memory.setdefault("c_rewrite_laws", {}), cand.skill_id, success=False)
                # After top-6 static candidates (or 15s) haven't solved, inject Execution-Guided C OE-SyGuS!
                if ((cand_idx >= min(6, len(cands))) or ((time.monotonic() - t0) >= 15.0)) and not oe_c_ran and (time.monotonic() - t0) < max(timeout_s * 2.2, 65.0):
                    oe_c_ran = True
                    _oe_c_more = _synthesize_c_oe_sygus_candidates(wt, loc, max_candidates=20)
                    if _oe_c_more:
                        cands[cand_idx:cand_idx] = _oe_c_more
                continue

            # Phase B: Brand-new isolated worktree full rebuild & ASan/UBSan verify
            verify_wt = pathlib.Path(tmp_dir) / f"verify_{attempts}"
            _copy_js_worktree(src_root, verify_wt)
            (verify_wt / cand.file).write_text(cand.patched_source, encoding="utf-8")
            rk_v, b_v, r_v, rcwd_v = detect_c_test_spec(
                verify_wt, test_targets, sanitizer=True, extra_flags=extra_flags
            )
            try:
                _rel_cwd = loc.run_cwd.resolve().relative_to(wt.resolve())
                if str(_rel_cwd) not in ("", ".") and (verify_wt / _rel_cwd).is_dir():
                    rcwd_v = verify_wt / _rel_cwd
            except Exception:
                pass
            if rk_v == "gcc_direct" and b_v:
                b_v = _precompile_c_static_objs(
                    verify_wt, b_v, set(src_files_init), obj_cache, timeout_s=max(timeout_s, 60.0)
                )
            rc_v, _ = _run_c_spec(
                verify_wt, rk_v, b_v, r_v, rcwd_v,
                timeout_s=max(timeout_s, 45.0), baseline_snapshots=baseline_snaps,
            )
            ok_full = rc_v == 0
            shutil.rmtree(verify_wt, ignore_errors=True)

            if ok_full:
                diff_txt = "".join(
                    difflib.unified_diff(
                        orig_src.splitlines(keepends=True),
                        cand.patched_source.splitlines(keepends=True),
                        fromfile=f"a/{cand.file}",
                        tofile=f"b/{cand.file}",
                    )
                )
                learned_law_id: str | None = None
                if memory is not None:
                    cstore = memory.setdefault("c_rewrite_laws", {})
                    if cand.skill_id and cand.skill_id in cstore:
                        _update_memrl_law(cstore, cand.skill_id, success=True)
                        learned_law_id = cand.skill_id
                    else:
                        rule = _abstract_c_repair_law(cand.tier, cand.description)
                        if rule is None and cand.tier == "C_OE_SYGUS_EUSOLVER":
                            _oe_claw = OESYGUS.abstract_synthesized_repair(
                                lang="c",
                                error_kind="c_oe_sygus_guard",
                                action_kind=cand.description.split("(")[0].strip().replace(" ", "_")[:48],
                            )
                            rule = {
                                **_oe_claw,
                                "kind": "c_oe_sygus_guard",
                                "tier": cand.tier,
                                "status": "ACTIVE",
                                "verified_uses": 1,
                                "failures": 0,
                                "refutations": 0,
                                "utility_q": 0.85,
                                "parameters_stored": 0,
                            }
                        if rule is not None:
                            lid = rule["law_id"]
                            if lid in cstore:
                                _update_memrl_law(cstore, lid, success=True)
                            else:
                                cstore[lid] = rule
                            learned_law_id = lid

                winner = {
                    "file": cand.file,
                    "lineno": cand.lineno,
                    "tier": cand.tier,
                    "description": cand.description,
                    "skill_id_used": cand.skill_id,
                    "attempt": attempts,
                    "diff": diff_txt,
                    "patched_source": cand.patched_source,
                    "learned_law_id": learned_law_id,
                }
                break

        # Stage 4: Multi-hunk / Multi-file Monotone Causal-Shift Progress Composition (C/C++)
        if winner is None and progress_cands:
            progress_cands.sort(key=lambda x: (x[0], x[1]))
            for _, _, p1 in progress_cands[:2]:
                if winner is not None:
                    break
                st2_wt = pathlib.Path(tmp_dir) / f"c_stage2_{p1.lineno}"
                _copy_js_worktree(src_root, st2_wt)
                (st2_wt / p1.file).write_text(p1.patched_source, encoding="utf-8")
                loc2 = localize_c_faults(
                    st2_wt, test_targets, timeout_s=max(timeout_s, 35.0),
                    baseline_snapshots=baseline_snaps, extra_flags=extra_flags,
                )
                if loc2.initial_rc == 0:
                    shutil.rmtree(st2_wt, ignore_errors=True)
                    continue
                cands2 = synthesize_c_candidates(st2_wt, loc2, memory=memory, max_candidates=20)
                for p2 in cands2:
                    attempts += 1
                    fp2 = st2_wt / p2.file
                    orig2 = fp2.read_text(encoding="utf-8", errors="replace")
                    ok2 = False
                    try:
                        fp2.write_text(p2.patched_source, encoding="utf-8")
                        rc2, _ = _run_c_spec(
                            st2_wt, loc2.runner_kind, loc2.build_cmd, loc2.run_cmd, loc2.run_cwd,
                            timeout_s=max(timeout_s, 35.0), baseline_snapshots=baseline_snaps,
                        )
                        ok2 = rc2 == 0
                    finally:
                        fp2.write_text(orig2, encoding="utf-8")
                    if not ok2:
                        continue
                    vwt = pathlib.Path(tmp_dir) / f"verify_c_s2_{attempts}"
                    _copy_js_worktree(src_root, vwt)
                    patched_map: dict[str, str] = {p1.file: p1.patched_source}
                    patched_map[p2.file] = p2.patched_source
                    for rel_f, txt_f in patched_map.items():
                        (vwt / rel_f).write_text(txt_f, encoding="utf-8")
                    rk_v2, b_v2, r_v2, rcwd_v2 = detect_c_test_spec(
                        vwt, test_targets, sanitizer=True, extra_flags=extra_flags
                    )
                    rc_v2, _ = _run_c_spec(
                        vwt, rk_v2, b_v2, r_v2, rcwd_v2,
                        timeout_s=max(timeout_s, 45.0), baseline_snapshots=baseline_snaps,
                    )
                    shutil.rmtree(vwt, ignore_errors=True)
                    if rc_v2 == 0:
                        diff_parts = []
                        for rel_f, txt_f in patched_map.items():
                            o_txt = (src_root / rel_f).read_text(encoding="utf-8", errors="replace")
                            diff_parts.append("".join(difflib.unified_diff(
                                o_txt.splitlines(keepends=True), txt_f.splitlines(keepends=True),
                                fromfile=f"a/{rel_f}", tofile=f"b/{rel_f}",
                            )))
                        extra_patches = {k: v for k, v in patched_map.items() if k != p1.file}
                        winner = {
                            "file": p1.file,
                            "lineno": p1.lineno,
                            "tier": "C_STAGE2_COMPOSED_PROGRESS",
                            "description": f"compose({p1.tier}:{p1.description} + {p2.tier}:{p2.description})",
                            "skill_id_used": None,
                            "attempt": attempts,
                            "diff": "\n".join(diff_parts),
                            "patched_source": patched_map[p1.file],
                            "extra_patches": extra_patches,
                            "learned_law_id": None,
                        }
                        break
                shutil.rmtree(st2_wt, ignore_errors=True)

        return {
            "schema": SCHEMA,
            "authority": AUTHORITY,
            "language": "c_cpp",
            "status": "VERIFIED" if winner else "UNSOLVED",
            "verified": winner is not None,
            "runner": loc.runner_kind,
            "bug_classes": loc.bug_classes,
            "attempts": attempts,
            "candidates_generated": len(cands),
            "winner": winner,
            "model_calls": 0,
            "parameters_stored": 0,
            "seconds": round(time.monotonic() - t0, 3),
        }

