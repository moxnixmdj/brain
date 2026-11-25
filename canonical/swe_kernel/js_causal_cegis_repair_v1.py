"""Polyglot JavaScript / Node.js Causal CEGIS Repair Engine (Zero Runtime Model Calls).

Uses native Node.js (`node` + V8 stack traces + `NODE_V8_COVERAGE` bytecode coverage) for
deterministic fault localization, paired with:
  1. JS Null/Undefined Guard & Optional-Chaining synthesis (`TypeError` causal repair);
  2. Universal JS Boolean-Guard, Operator, Boundary & Scope-Option Habitation CEGIS;
  3. Bidirectional FST Lens synthesis (reusing `reverse_tomography_algebra_v1`);
  4. Polyglot L2 skill crystallization into `ExternalCausalLawStore`.

Strictly 0 external model calls and 0 external npm dependencies required.
"""
from __future__ import annotations

import collections
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import time
from typing import Any, Mapping, Sequence


_V8_FRAME_RE = re.compile(r"at\s+(?:([A-Za-z0-9_$.<>]+)\s+)?\(?([^\s():]+?\.[cm]?js):(\d+):(\d+)\)?")
_REQUIRE_RE = re.compile(r"""require\(\s*['"]([^'"]+)['"]\s*\)""")
_TYPEERR_PROP_RE = re.compile(r"Cannot read propert(?:y|ies) of (null|undefined)\s*\(reading ['\"]([^'\"]+)['\"]\)")

# Minimal zero-dependency CommonJS `tap` test shim used ONLY when `node_modules/tap` is absent!
_TAP_SHIM_JS = r"""'use strict'
const assert = require('assert')
let _failures = 0
let _total = 0

function makeT(prefix) {
  const t = {
    equal(a, b, msg) {
      _total++
      try { assert.strictEqual(a, b, msg) }
      catch (e) { _failures++; console.error('TAP_FAIL:', prefix, msg || '', 'actual=', a, 'expected=', b); }
    },
    strictEqual(a, b, msg) { t.equal(a, b, msg) },
    not(a, b, msg) {
      _total++
      try { assert.notStrictEqual(a, b, msg) }
      catch (e) { _failures++; console.error('TAP_FAIL:', prefix, msg || '', 'unexpected=', a); }
    },
    same(a, b, msg) {
      _total++
      try { assert.deepStrictEqual(a, b, msg) }
      catch (e) { _failures++; console.error('TAP_FAIL:', prefix, msg || '', 'actual=', a, 'expected=', b); }
    },
    strictSame(a, b, msg) { t.same(a, b, msg) },
    ok(v, msg) {
      _total++
      if (!v) { _failures++; console.error('TAP_FAIL:', prefix, msg || '', 'expected truthy, got=', v); }
    },
    notOk(v, msg) {
      _total++
      if (v) { _failures++; console.error('TAP_FAIL:', prefix, msg || '', 'expected falsy, got=', v); }
    },
    throws(fn, err, msg) {
      _total++
      try {
        if (typeof err === 'string' && msg === undefined) { assert.throws(fn) }
        else { assert.throws(fn, err, msg) }
      }
      catch (e) { _failures++; console.error('TAP_FAIL:', prefix, msg || '', 'did not throw'); }
    },
    doesNotThrow(fn, msg) {
      _total++
      try { assert.doesNotThrow(fn, msg) }
      catch (e) { _failures++; console.error('TAP_FAIL:', prefix, msg || '', 'threw:', e && e.message); }
    },
    match(found, wanted, msg) {
      _total++
      try {
        if (wanted instanceof RegExp) { assert.match(String(found), wanted, msg) }
        else if (wanted && typeof wanted === 'object' && found && typeof found === 'object') {
          for (const k of Object.keys(wanted)) {
            if (wanted[k] instanceof RegExp) assert.match(String(found[k]), wanted[k], msg)
            else assert.deepStrictEqual(found[k], wanted[k], msg)
          }
        } else { assert.strictEqual(found, wanted, msg) }
      } catch (e) { _failures++; console.error('TAP_FAIL:', prefix, msg || '', 'match failed'); }
    },
    plan() {},
    end() {},
    comment() {},
    test(name, opts, fn) {
      if (typeof opts === 'function') { fn = opts; }
      if (typeof fn !== 'function') return Promise.resolve()
      const sub = makeT((prefix ? prefix + ' > ' : '') + name)
      try {
        const r = fn(sub)
        if (r && typeof r.then === 'function') {
          return r.catch(err => { _failures++; console.error('TAP_ERR:', name, err && err.stack || err) })
        }
      } catch (err) {
        _failures++
        console.error('TAP_ERR:', name, err && err.stack || err)
      }
      return Promise.resolve()
    },
  }
  return t
}

const rootT = makeT('')
process.on('beforeExit', () => {
  if (_failures > 0) {
    console.error('TAP_SUMMARY: total=' + _total + ' failures=' + _failures)
    process.exitCode = 1
  }
})
module.exports = rootT
"""


def _find_node() -> str | None:
    return shutil.which("node")


def _ensure_tap_shim_dir() -> pathlib.Path:
    d = pathlib.Path(tempfile.gettempdir()) / "_brain_js_node_path"
    tap_dir = d / "tap"
    tap_idx = tap_dir / "index.js"
    if not tap_idx.is_file() or tap_idx.read_text(encoding="utf-8", errors="replace") != _TAP_SHIM_JS:
        tap_dir.mkdir(parents=True, exist_ok=True)
        tap_idx.write_text(_TAP_SHIM_JS, encoding="utf-8")
    return d


def run_js_test(
    repo_root: str | pathlib.Path,
    test_file: str,
    *,
    timeout_s: int = 12,
    collect_v8_coverage: bool = False,
) -> dict[str, Any]:
    """Run a JS/Node.js test file and parse V8 stack frames, error class, and optional V8 line coverage."""
    node = _find_node()
    if not node:
        return {"passed": False, "reason": "NO_NODE_RUNTIME", "model_calls": 0}

    root = pathlib.Path(repo_root).resolve()
    t0 = time.monotonic()
    env = dict(os.environ)
    if not (root / "node_modules" / "tap").exists():
        shim_dir = str(_ensure_tap_shim_dir())
        prev_np = env.get("NODE_PATH", "")
        env["NODE_PATH"] = f"{prev_np}{os.pathsep}{shim_dir}" if prev_np else shim_dir

    cov_td = tempfile.TemporaryDirectory(prefix="brain_v8cov_") if collect_v8_coverage else None
    if cov_td is not None:
        env["NODE_V8_COVERAGE"] = cov_td.name

    try:
        test_path = (root / test_file).resolve()
        use_node_test = False
        try:
            txt = test_path.read_text(encoding="utf-8", errors="replace")
            use_node_test = ("node:test" in txt) or ("require('node:test')" in txt)
        except OSError:
            pass
        cmd = [node, "--test", test_file] if use_node_test else [node, test_file]
        try:
            cp = subprocess.run(cmd, cwd=str(root), env=env, capture_output=True, text=True, timeout=timeout_s)
        except subprocess.TimeoutExpired:
            return {"passed": False, "returncode": 124, "reason": "TIMEOUT", "frames": [], "executed_lines": {}, "model_calls": 0}

        comb = cp.stdout + "\n" + cp.stderr
        frames: list[dict[str, Any]] = []
        for m in _V8_FRAME_RE.finditer(comb):
            raw_f = m.group(2)
            try:
                rel = pathlib.Path(raw_f).resolve().relative_to(root).as_posix()
            except Exception:
                continue
            frames.append(
                {"func": m.group(1) or "", "file": rel, "line": int(m.group(3)), "col": int(m.group(4))}
            )

        err_kind = ""
        err_prop = ""
        m_te = _TYPEERR_PROP_RE.search(comb)
        if m_te:
            err_kind = "NULL_PROP_DEREF"
            err_prop = m_te.group(2)
        elif "TypeError:" in comb:
            err_kind = "TYPE_ERROR"
        elif "RangeError:" in comb:
            err_kind = "RANGE_ERROR"
        elif "ReferenceError:" in comb:
            err_kind = "REFERENCE_ERROR"
        elif "TAP_FAIL:" in comb or "AssertionError" in comb:
            err_kind = "ASSERTION_FAIL"

        # Parse V8 bytecode coverage -> executed line numbers per repo `.js` file
        executed_lines: dict[str, set[int]] = {}
        if cov_td is not None:
            for jf in pathlib.Path(cov_td.name).glob("*.json"):
                try:
                    data = json.loads(jf.read_text(encoding="utf-8"))
                except Exception:
                    continue
                for res in data.get("result") or ():
                    url = str(res.get("url") or "")
                    if not url.startswith("file://"):
                        continue
                    fp = pathlib.Path(url[len("file://") :])
                    try:
                        rel = fp.resolve().relative_to(root).as_posix()
                    except Exception:
                        continue
                    if rel.startswith("node_modules/") or rel == test_file:
                        continue
                    try:
                        src = fp.read_text(encoding="utf-8", errors="replace")
                    except OSError:
                        continue
                    # Precompute newline offsets
                    nl_pos = [0]
                    idx = 0
                    while True:
                        ni = src.find("\n", idx)
                        if ni == -1:
                            break
                        nl_pos.append(ni + 1)
                        idx = ni + 1
                    import bisect
                    hit_lines = executed_lines.setdefault(rel, set())
                    for fn_cov in res.get("functions") or ():
                        for rng in fn_cov.get("ranges") or ():
                            if int(rng.get("count") or 0) <= 0:
                                continue
                            s_off = int(rng.get("startOffset") or 0)
                            e_off = int(rng.get("endOffset") or s_off)
                            ln_s = bisect.bisect_right(nl_pos, s_off)
                            ln_e = bisect.bisect_right(nl_pos, max(s_off, e_off - 1))
                            for ln_i in range(ln_s, min(ln_e + 1, len(nl_pos) + 1)):
                                hit_lines.add(ln_i)

        tap_fails = [
            ln for ln in comb.splitlines()
            if "TAP_FAIL:" in ln or "TAP_ERR:" in ln or re.match(r"^\s*not ok\s+\d+", ln)
        ]
        m_sum = re.search(r"TAP_SUMMARY:\s+total=(\d+)\s+failures=(\d+)", comb)
        m_tape = re.search(r"^#\s+fail\s+(\d+)", comb, re.M)
        if m_sum:
            failure_count = int(m_sum.group(2))
        elif m_tape:
            failure_count = int(m_tape.group(1))
        else:
            failure_count = len(tap_fails) if tap_fails else (0 if cp.returncode == 0 else 1)
        if not err_kind and failure_count > 0:
            err_kind = "ASSERTION_FAIL"
        passed = (cp.returncode == 0) and (failure_count == 0) and ("AssertionError" not in comb)
        return {
            "passed": passed,
            "returncode": int(cp.returncode),
            "failure_count": failure_count,
            "err_kind": err_kind,
            "err_prop": err_prop,
            "frames": frames,
            "tap_fails": tap_fails[:12],
            "executed_lines": {k: sorted(v) for k, v in executed_lines.items()},
            "stdout_tail": cp.stdout[-600:],
            "stderr_tail": cp.stderr[-600:],
            "elapsed_ms": int((time.monotonic() - t0) * 1000),
            "model_calls": 0,
        }
    finally:
        if cov_td is not None:
            cov_td.cleanup()


def _discover_js_target_files(
    root: pathlib.Path, test_file: str, base: Mapping[str, Any]
) -> list[str]:
    """Order candidate editable `.js` source files by V8 crash frames -> stem match -> direct `require()` -> V8 coverage."""
    crash_ordered: list[str] = []
    other_ordered: list[str] = []

    def _valid(rel: str) -> bool:
        p = root / rel
        if not p.is_file():
            return False
        if rel == test_file or rel.startswith(("test/", "tests/", "node_modules/")):
            return False
        return True

    # 1. V8 crash stack frames (highest precision!)
    for fr in base.get("frames") or ():
        rel = str(fr.get("file") or "")
        if _valid(rel) and rel not in crash_ordered:
            crash_ordered.append(rel)

    def _add_other(rel: str) -> None:
        if _valid(rel) and rel not in crash_ordered and rel not in other_ordered:
            other_ordered.append(rel)

    # 2. Direct relative `require(...)` from `test_file`
    tf_p = root / test_file
    if tf_p.is_file():
        txt = tf_p.read_text(encoding="utf-8", errors="replace")
        for m in _REQUIRE_RE.finditer(txt):
            spec = m.group(1)
            if not spec.startswith("."):
                continue
            cand_base = (tf_p.parent / spec).resolve()
            for cand in (cand_base, cand_base.with_suffix(".js"), cand_base / "index.js"):
                if cand.is_file():
                    try:
                        _add_other(cand.relative_to(root).as_posix())
                    except Exception:
                        pass
                    break

    # 3. Remaining files executed in V8 coverage
    for rel in sorted((base.get("executed_lines") or {}).keys()):
        _add_other(rel)

    # Prioritize exact filename-stem matches with `test_file` (e.g. `test/parse.js` -> `lib/parse.js`)
    # ahead of auxiliary utilities directly imported by the test harness!
    test_stem = pathlib.Path(test_file).stem.lower().replace(".test", "").replace(".spec", "")
    other_ordered.sort(key=lambda rel: (0 if pathlib.Path(rel).stem.lower() == test_stem else 1))

    return crash_ordered + other_ordered


def _mine_repo_js_bool_methods(root: pathlib.Path) -> list[str]:
    """Codebase-Internal JS Type-Habitation: mine frequent 1-arg boolean predicate methods in repo `.js` files."""
    counts: collections.Counter[str] = collections.Counter()
    skip_m = {"log", "error", "warn", "push", "pop", "join", "split", "map", "forEach", "slice", "replace", "match"}
    for fp in sorted(root.rglob("*.js")):
        rel = fp.relative_to(root).as_posix()
        if rel.startswith(("test/", "tests/", "node_modules/", ".git/")):
            continue
        try:
            txt = fp.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for m in re.finditer(r"(?:if\s*\([^)]*|&&\s*|\|\|\s*)!?[A-Za-z0-9_$\[\]\)\.]+\.([a-z][A-Za-z0-9_]{2,})\([^,()]{1,40}\)", txt):
            meth = m.group(1)
            if meth not in skip_m:
                counts[meth] += 1
    return [m for m, _ in counts.most_common(4)]


def synthesize_js_causal_patches(
    source: str,
    candidate_lines: Sequence[int],
    *,
    err_kind: str = "",
    err_prop: str = "",
    habited_bool_methods: Sequence[str] = (),
    max_patches: int = 160,
) -> list[tuple[str, int, str]]:
    """Synthesize minimal first-principles JS causal repair candidates on `candidate_lines`."""
    lines = source.splitlines(keepends=True)
    out: list[tuple[str, int, str]] = []
    seen: set[str] = set()

    def _emit(lbl: str, ln: int, psrc: str) -> None:
        if psrc != source and psrc not in seen and len(out) < max_patches:
            seen.add(psrc)
            out.append((lbl, ln, psrc))

    # Mine scope boolean option properties (`options.foo` / `opts.foo`) from the file for habitation
    opt_flags = sorted(
        set(re.findall(r"\b(?:options|opts)\.(include[A-Za-z0-9_]+|[a-z][A-Za-z0-9_]{3,})\b", source))
    )[:4]

    # Collect high-priority repo-native wrapper-to-method reduction matches across candidate lines first!
    # Pattern: `fn(arg0, String(obj), ...)` -> `obj.<habited_bool_method>(arg0)` (plus symmetric multi-site batch!)
    wrap_pat = re.compile(r"\b([A-Za-z_$][A-Za-z0-9_$]*)\(\s*([^,()]+?)\s*,\s*String\(\s*([A-Za-z_$][A-Za-z0-9_$.]*)\s*\)(?:\s*,\s*[^()]+)?\)")
    for meth in habited_bool_methods[:3]:
        batch_lines = list(lines)
        batch_hits: list[int] = []
        single_cands: list[tuple[str, int, str]] = []
        for ln in candidate_lines:
            if not (1 <= ln <= len(lines)):
                continue
            txt = lines[ln - 1]
            m_w = wrap_pat.search(txt)
            if m_w:
                arg0, recv = m_w.group(2).strip(), m_w.group(3).strip()
                rep = txt[: m_w.start()] + f"{recv}.{meth}({arg0})" + txt[m_w.end() :]
                single_cands.append((f"JS_HABITED_METHOD_{meth}_L{ln}", ln, "".join(lines[: ln - 1]) + rep + "".join(lines[ln:])))
                batch_lines[ln - 1] = rep
                batch_hits.append(ln)
        if len(batch_hits) >= 2:
            _emit(f"JS_HABITED_METHOD_{meth}_SYMMETRIC_{len(batch_hits)}SITES", batch_hits[0], "".join(batch_lines))
        for sc in single_cands:
            _emit(*sc)

    # Prioritize Template-Interpolation Ablation (`${ident}` -> `""` inside template strings!)
    for ln in candidate_lines:
        if not (1 <= ln <= len(lines)):
            continue
        txt = lines[ln - 1]
        if "${" in txt and ("`" in txt or (ln > 1 and "`" in lines[ln - 2])):
            for m_tpl in re.finditer(r"\$\{[A-Za-z_$][A-Za-z0-9_$.]*\}", txt):
                rep = txt[: m_tpl.start()] + txt[m_tpl.end() :]
                _emit(f"JS_TPL_ABLATE_{m_tpl.group(0)[2:-1]}_L{ln}", ln, "".join(lines[: ln - 1]) + rep + "".join(lines[ln:]))

    # Prioritize JS Regex Flag Algebra (`/pat/g` -> `/pat/gi`), Copy-Before-Mutate (`.sort(` -> `.slice().sort(`),
    # Def-Use Defensive Array Alias Decoupling (`isArray(rhs)` -> `lhs = rhs.slice()` + rebind downstream `rhs -> lhs`),
    # and JS Length-Polymorphism Type Guards (`x.length === 0 && (typeof x === 'string' || Array.isArray(x))`)!
    regex_lit_re = re.compile(r"(/[^/\n]{1,48}/)([a-z]*)")
    mut_call_re = re.compile(r"\b([A-Za-z_$][A-Za-z0-9_$.]*)\.(sort|reverse|splice)\(")
    len_zero_re = re.compile(r"\b([A-Za-z_$][A-Za-z0-9_$.]*)\.length\s*===\s*0\b")
    is_arr_guard_re = re.compile(r"\b(?:Array\.)?isArray\(\s*([A-Za-z_$][A-Za-z0-9_$.]*)\s*\)")
    alias_assign_re = re.compile(r"^(\s*(?:(?:var|let|const)\s+)?)([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*([A-Za-z_$][A-Za-z0-9_$.]*)\s*;(\s*\r?\n?)$")
    for ln in candidate_lines:
        if not (1 <= ln <= len(lines)):
            continue
        txt = lines[ln - 1]
        st_l = txt.strip()
        if not st_l or st_l.startswith(("//", "/*", "*")):
            continue
        # 1. Regex flag algebra (add `i` case-insensitive flag to regex literals without `i`)
        if "/" in txt and ("replace" in txt or "match" in txt or "test" in txt or "split" in txt or "=" in txt):
            for m_rx in regex_lit_re.finditer(txt):
                pat_s, flags_s = m_rx.group(1), m_rx.group(2)
                if "i" not in flags_s and not pat_s.startswith("//"):
                    rep = txt[: m_rx.start()] + f"{pat_s}{flags_s}i" + txt[m_rx.end() :]
                    _emit(f"JS_REGEX_ADD_FLAG_i_L{ln}", ln, "".join(lines[: ln - 1]) + rep + "".join(lines[ln:]))
        # 2a. Def-Use Defensive Array Copy + Alias Decoupling on `isArray(rhs)` -> `lhs = rhs;`
        m_aa = alias_assign_re.match(txt)
        if m_aa:
            pre_a, lhs_a, rhs_a, suf_a = m_aa.group(1), m_aa.group(2), m_aa.group(3), m_aa.group(4)
            ctx_window = "".join(lines[max(0, ln - 3) : ln])
            if any(mg.group(1) == rhs_a for mg in is_arr_guard_re.finditer(ctx_window)):
                copied_ln = f"{pre_a}{lhs_a} = {rhs_a}.slice();{suf_a}"
                _emit(f"JS_DEFENSIVE_SLICE_{lhs_a}_L{ln}", ln, "".join(lines[: ln - 1]) + copied_ln + "".join(lines[ln:]))
                # Def-Use Alias Decoupling: rebind downstream read occurrences of `rhs_a` in the same function to `lhs_a`!
                if "." in rhs_a:
                    rhs_word_re = re.compile(rf"(?<![A-Za-z0-9_$.]){re.escape(rhs_a)}(?![A-Za-z0-9_$.])")
                    decoupled = list(lines)
                    decoupled[ln - 1] = copied_ln
                    rebound_cnt = 0
                    for j_ln in range(ln, len(lines)):
                        lj = lines[j_ln]
                        if j_ln > ln and (lj.startswith("};") or lj.startswith("}") or lj.startswith("function ") or lj.startswith("module.exports")):
                            break
                        if rhs_a in lj and not re.search(rf"{re.escape(rhs_a)}\s*=(?!=)", lj):
                            new_lj = rhs_word_re.sub(lhs_a, lj)
                            if new_lj != lj:
                                decoupled[j_ln] = new_lj
                                rebound_cnt += 1
                    if rebound_cnt > 0:
                        _emit(f"JS_DEFENSIVE_SLICE_DECOUPLE_{lhs_a}_L{ln}", ln, "".join(decoupled))
        # 2b. Copy-before-mutate isolation (`arr.sort(...)` -> `arr.slice().sort(...)` AND `arr = arr.slice();`)
        for m_mc in mut_call_re.finditer(txt):
            recv, meth = m_mc.group(1), m_mc.group(2)
            rep = txt[: m_mc.start()] + f"{recv}.slice().{meth}(" + txt[m_mc.end() :]
            _emit(f"JS_COPY_BEFORE_{meth.upper()}_{recv}_L{ln}", ln, "".join(lines[: ln - 1]) + rep + "".join(lines[ln:]))
            ind_l = txt[: len(txt) - len(txt.lstrip(" \t"))]
            rep_pre = f"{ind_l}{recv} = {recv}.slice();\n{txt}"
            _emit(f"JS_REBIND_SLICE_BEFORE_{meth.upper()}_{recv}_L{ln}", ln, "".join(lines[: ln - 1]) + rep_pre + "".join(lines[ln:]))
        # 3. Length-polymorphism guard (preserving short-circuit throwing contract `P && T` BEFORE `T && P`!)
        m_lz = len_zero_re.search(txt)
        if m_lz and "typeof " not in txt:
            xv = m_lz.group(1)
            for tag_g, guard_g in (
                ("POST_STR_OR_ARR", f"{xv}.length === 0 && (typeof {xv} === 'string' || Array.isArray({xv}))"),
                ("POST_STR_ONLY", f"{xv}.length === 0 && typeof {xv} === 'string'"),
                ("PRE_STR_OR_ARR", f"(typeof {xv} === 'string' || Array.isArray({xv})) && {xv}.length === 0"),
            ):
                rep = txt[: m_lz.start()] + guard_g + txt[m_lz.end() :]
                _emit(f"JS_LEN_TYPE_GUARD_{tag_g}_{xv}_L{ln}", ln, "".join(lines[: ln - 1]) + rep + "".join(lines[ln:]))

    for ln in candidate_lines:
        if not (1 <= ln <= len(lines)):
            continue
        txt = lines[ln - 1]
        st = txt.strip()
        if not st or st.startswith(("//", "/*", "*", "const ", "let ", "var ")) and err_kind != "NULL_PROP_DEREF" and "=" not in st:
            continue
        indent = txt[: len(txt) - len(txt.lstrip(" \t"))]

        # --- FAMILY JS-1: NULL / UNDEFINED DEREF (`TypeError: Cannot read properties of null/undefined`) ---
        if err_kind == "NULL_PROP_DEREF" and err_prop:
            # Optional chaining `obj.prop` -> `obj?.prop`
            m_dot = re.search(rf"\b([A-Za-z_$][A-Za-z0-9_$.]*)\.{re.escape(err_prop)}\b", txt)
            if m_dot:
                recv = m_dot.group(1)
                rep = txt[: m_dot.start()] + f"{recv}?.{err_prop}" + txt[m_dot.end() :]
                psrc = "".join(lines[: ln - 1]) + rep + "".join(lines[ln:])
                _emit(f"JS_OPTIONAL_CHAIN_{recv}_{err_prop}", ln, psrc)
                # Early-return null guard before line
                for rv in ("null", "undefined", "false", "''", "0"):
                    g = f"{indent}if ({recv} == null) return {rv}\n"
                    psrc_g = "".join(lines[: ln - 1]) + g + "".join(lines[ln - 1 :])
                    _emit(f"JS_NULL_GUARD_RET_{rv}_L{ln}", ln, psrc_g)

        # --- FAMILY JS-2: JS RELATIONAL / EQUALITY / LOGICAL / BOOLEAN / STRING DUALS ---
        op_swaps = (
            (" === ", " !== "),
            (" !== ", " === "),
            (" <= ", " < "),
            (" < ", " <= "),
            (" >= ", " > "),
            (" > ", " >= "),
            (" && ", " || "),
            (" || ", " && "),
            (".replace(", ".replaceAll("),
            (".trim()", ".trimEnd()"),
            (".trimEnd()", ".trim()"),
        )
        for old_op, new_op in op_swaps:
            if old_op in txt:
                rep = txt.replace(old_op, new_op, 1)
                psrc = "".join(lines[: ln - 1]) + rep + "".join(lines[ln:])
                _emit(f"JS_OP_{old_op.strip()}_TO_{new_op.strip()}_L{ln}", ln, psrc)

        # Boolean return flip (`return true` <-> `return false`)
        if re.match(r"^\s*return\s+true\b", txt):
            rep = re.sub(r"\breturn\s+true\b", "return false", txt, count=1)
            _emit(f"JS_RET_TRUE_TO_FALSE_L{ln}", ln, "".join(lines[: ln - 1]) + rep + "".join(lines[ln:]))
        elif re.match(r"^\s*return\s+false\b", txt):
            rep = re.sub(r"\breturn\s+false\b", "return true", txt, count=1)
            _emit(f"JS_RET_FALSE_TO_TRUE_L{ln}", ln, "".join(lines[: ln - 1]) + rep + "".join(lines[ln:]))

        # Boolean clause drop / scope-flag refinement on `if (...)`
        m_if = re.match(r"^(\s*(?:else\s+)?if\s*\()(.+)(\)\s*(?:\{)?\s*\r?\n?)$", txt)
        if m_if:
            pre_i, inner_i, suf_i = m_if.group(1), m_if.group(2), m_if.group(3)
            # Negate entire condition
            if inner_i.startswith("!"):
                _emit(f"JS_UNNEG_IF_L{ln}", ln, "".join(lines[: ln - 1]) + f"{pre_i}{inner_i[1:].strip()}{suf_i}" + "".join(lines[ln:]))
            else:
                _emit(f"JS_NEG_IF_L{ln}", ln, "".join(lines[: ln - 1]) + f"{pre_i}!({inner_i}){suf_i}" + "".join(lines[ln:]))
            # Clause drop on top-level `&&` or `||`
            for sep, tag in ((" && ", "AND"), (" || ", "OR")):
                if sep in inner_i:
                    parts = inner_i.split(sep)
                    for di in range(len(parts) - 1, -1, -1):
                        kept = sep.join(p for j, p in enumerate(parts) if j != di)
                        if kept.strip():
                            _emit(f"JS_DROP_{tag}_{di}_L{ln}", ln, "".join(lines[: ln - 1]) + f"{pre_i}{kept}{suf_i}" + "".join(lines[ln:]))
            # Codebase-habited scope-option conjunction (`!options.flag && (...)` / `options.flag || (...)`)
            for flag in opt_flags[:2]:
                opt_var = "options" if f"options.{flag}" in source else "opts"
                if flag not in inner_i:
                    _emit(
                        f"JS_GUARD_NOT_{flag}_L{ln}",
                        ln,
                        "".join(lines[: ln - 1]) + f"{pre_i}!{opt_var}.{flag} && ({inner_i}){suf_i}" + "".join(lines[ln:]),
                    )
                    _emit(
                        f"JS_GUARD_OR_{flag}_L{ln}",
                        ln,
                        "".join(lines[: ln - 1]) + f"{pre_i}{opt_var}.{flag} || ({inner_i}){suf_i}" + "".join(lines[ln:]),
                    )

        # Call-argument option forwarding (`fn(a, b)` -> `fn(a, b, options)` if `options` is in file)
        if "options" in source and "options" not in txt:
            m_call = re.search(r"\b([A-Za-z_$][A-Za-z0-9_$.]*)\(([^()]+)\)", txt)
            if m_call and not m_call.group(1).endswith(("if", "for", "while", "switch", "catch")):
                fn_c, args_c = m_call.group(1), m_call.group(2).strip()
                if args_c and not args_c.endswith(","):
                    rep = txt[: m_call.start()] + f"{fn_c}({args_c}, options)" + txt[m_call.end() :]
                    _emit(f"JS_FORWARD_OPTIONS_{fn_c}_L{ln}", ln, "".join(lines[: ln - 1]) + rep + "".join(lines[ln:]))

    return out[:max_patches]


def repair_js_repo_causal_cegis(
    repo_root: str | pathlib.Path,
    test_file: str,
    *,
    editable_files: Sequence[str] | None = None,
    timeout_s: int = 45,
    skill_store: Any = None,
) -> dict[str, Any]:
    """End-to-end zero-model JavaScript / Node.js causal repair using V8 coverage & CEGIS."""
    t0 = time.monotonic()
    root = pathlib.Path(repo_root).resolve()

    base = run_js_test(root, test_file, timeout_s=min(12, timeout_s), collect_v8_coverage=True)
    if base.get("passed"):
        return {
            "repaired": False,
            "reason": "BASELINE_ALREADY_PASSING",
            "elapsed_ms": int((time.monotonic() - t0) * 1000),
            "model_calls": 0,
        }
    if base.get("reason") == "NO_NODE_RUNTIME":
        return {"repaired": False, "reason": "NO_NODE_RUNTIME", "elapsed_ms": 0, "model_calls": 0}

    targets = list(editable_files) if editable_files else _discover_js_target_files(root, test_file, base)
    err_kind = str(base.get("err_kind") or "")
    err_prop = str(base.get("err_prop") or "")
    exec_map = dict(base.get("executed_lines") or {})
    base_failures = max(1, int(base.get("failure_count") or 1))
    habited_methods = _mine_repo_js_bool_methods(root)

    def _admit_js_law(lbl_s: str, rf_s: str, ln_i: int) -> str | None:
        if skill_store is not None and hasattr(skill_store, "admit"):
            try:
                from canonical.swe_kernel import universal_computer_agent_v1 as uca
                lid = f"js_cegis::{hashlib.sha256(f'{err_kind}:{lbl_s}'.encode()).hexdigest()[:10]}"
                law = uca.ParameterizedCausalLaw(
                    law_id=lid,
                    domain="js_causal_cegis",
                    tool_or_action=lbl_s,
                    command_template=["js_causal_cegis", err_kind or "ASSERTION_FAIL", lbl_s],
                    preconditions={"js_error": err_kind or "ASSERTION_FAIL"},
                    effects={"node_test_pass": True},
                    provenance={"file": rf_s, "line": ln_i, "rule": lbl_s},
                    generalized=True,
                )
                skill_store.admit(law)
                return lid
            except Exception:
                return None
        return None

    cands_tested = 0
    for rf in targets[:4]:
        fp = root / rf
        if not fp.is_file():
            continue
        orig_src = fp.read_text(encoding="utf-8", errors="replace")
        orig_lines = orig_src.splitlines(keepends=True)
        # Prioritize exact V8 crash stack lines first, then executed lines from V8 coverage!
        cand_lines: list[int] = []
        for fr in base.get("frames") or ():
            if fr.get("file") == rf and int(fr.get("line") or 0) > 0:
                ln = int(fr["line"])
                if ln not in cand_lines:
                    cand_lines.append(ln)
        for ln in exec_map.get(rf) or ():
            if ln not in cand_lines:
                cand_lines.append(int(ln))
        if not cand_lines:
            cand_lines = list(range(1, len(orig_lines) + 1))

        patches = synthesize_js_causal_patches(
            orig_src,
            cand_lines,
            err_kind=err_kind,
            err_prop=err_prop,
            habited_bool_methods=habited_methods,
            max_patches=180,
        )
        # Track strictly-improving single-line edits (`failure_count < base_failures`) for O(N) multi-site composition!
        improving_by_line: dict[int, tuple[int, str, str]] = {}

        for lbl, ln, psrc in patches:
            if time.monotonic() - t0 > timeout_s:
                break
            cands_tested += 1
            try:
                fp.write_text(psrc, encoding="utf-8")
                chk = run_js_test(root, test_file, timeout_s=10, collect_v8_coverage=False)
            finally:
                fp.write_text(orig_src, encoding="utf-8")

            if chk.get("passed"):
                law_id = _admit_js_law(lbl, rf, ln)
                return {
                    "repaired": True,
                    "method": "JS_V8_CAUSAL_CEGIS",
                    "rule": lbl,
                    "err_kind": err_kind,
                    "patched_file": rf,
                    "patched_line": ln,
                    "patched_source": psrc,
                    "patched_files": {rf: psrc},
                    "candidates_verified": cands_tested,
                    "learned_law_id": law_id,
                    "elapsed_ms": int((time.monotonic() - t0) * 1000),
                    "model_calls": 0,
                }

            # Multi-Assertion Coordinate-Descent: record single-line patches that strictly lower failure_count!
            fc = int(chk.get("failure_count") or base_failures)
            if 0 < fc < base_failures:
                p_lines = psrc.splitlines(keepends=True)
                if len(p_lines) == len(orig_lines):
                    diff_idxs = [i for i in range(len(orig_lines)) if p_lines[i] != orig_lines[i]]
                    if len(diff_idxs) == 1:
                        di = diff_idxs[0]
                        prev = improving_by_line.get(di)
                        if prev is None or fc < prev[0]:
                            improving_by_line[di] = (fc, lbl, p_lines[di])
                        # Compose disjoint improving edits immediately once >= 2 sites improve!
                        if len(improving_by_line) >= 2:
                            comp_lines = list(orig_lines)
                            comp_lbls: list[str] = []
                            for idx_k, (_, l_k, new_l_k) in sorted(improving_by_line.items()):
                                comp_lines[idx_k] = new_l_k
                                comp_lbls.append(l_k)
                            comp_src = "".join(comp_lines)
                            cands_tested += 1
                            try:
                                fp.write_text(comp_src, encoding="utf-8")
                                chk_c = run_js_test(root, test_file, timeout_s=10, collect_v8_coverage=False)
                            finally:
                                fp.write_text(orig_src, encoding="utf-8")
                            if chk_c.get("passed"):
                                comb_rule = "COORDINATE_DESCENT(" + "+".join(comp_lbls[:4]) + ")"
                                first_ln = min(improving_by_line.keys()) + 1
                                law_id = _admit_js_law(comb_rule, rf, first_ln)
                                return {
                                    "repaired": True,
                                    "method": "JS_V8_COORDINATE_DESCENT_CEGIS",
                                    "rule": comb_rule,
                                    "err_kind": err_kind,
                                    "patched_file": rf,
                                    "patched_line": first_ln,
                                    "patched_source": comp_src,
                                    "patched_files": {rf: comp_src},
                                    "candidates_verified": cands_tested,
                                    "learned_law_id": law_id,
                                    "elapsed_ms": int((time.monotonic() - t0) * 1000),
                                    "model_calls": 0,
                                }

    return {
        "repaired": False,
        "reason": "NO_VERIFIED_JS_PATCH",
        "err_kind": err_kind,
        "targets_tried": targets[:4],
        "candidates_verified": cands_tested,
        "elapsed_ms": int((time.monotonic() - t0) * 1000),
        "model_calls": 0,
    }
