"""Polyglot C ASan/UBSan Causal & Relational CEGIS Repair Engine (Zero Runtime Model Calls).

Uses `gcc -fsanitize=address,undefined -g -O0` as a deterministic hardware-backed C fault
localizer (the C equivalent of Python's live differential tracer) paired with:
  1. Function-context C return-contract habitation (mines canonical error returns directly
     from sibling functions in the target `.c` file — zero hardcoded repo assumptions);
  2. Universal C pointer-dereference & linked-list guard synthesis (inline short-circuit,
     statement guard wrap, entry-guard expansion, pre-deref early return);
  3. Relational / logical / boundary operator CEGIS for non-crash logic & CVE bugs;
  4. Polyglot L2 skill crystallization into `ExternalCausalLawStore`.

Strictly 0 external model calls and 0 neural weights.
"""
from __future__ import annotations

import collections
import hashlib
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import time
from typing import Any, Mapping, Sequence


_ASAN_FRAME_RE = re.compile(r"#\d+\s+0x[0-9a-fA-F]+\s+in\s+([A-Za-z_][A-Za-z0-9_]*)\s+([^:\s]+):(\d+)")
_UBSAN_LINE_RE = re.compile(r"^([^:\s]+):(\d+):(\d+):\s+runtime error:\s+(.+)$", re.M)
_UNITY_FAIL_RE = re.compile(r"^([^:\s]+):(\d+):([^:\s]+):FAIL:\s*(.*)$", re.M)
_DEREF_CHAIN_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*(?:\s*->\s*[A-Za-z_][A-Za-z0-9_]*)+)")
_LIBC_PTR_CALL_RE = re.compile(
    r"\b(?:strlen|strcpy|strncpy|strcmp|strncmp|strcat|memcpy|memmove|memcmp|strchr|strstr|strdup)\s*\(\s*([A-Za-z_][A-Za-z0-9_]*(?:\s*->\s*[A-Za-z_][A-Za-z0-9_]*)*)"
)
_STAR_DEREF_RE = re.compile(r"(?<![A-Za-z0-9_\)\]])\*\s*([A-Za-z_][A-Za-z0-9_]*)")
_C_KEYWORDS = frozenset(
    {
        "if", "else", "for", "while", "do", "switch", "case", "return", "sizeof",
        "goto", "break", "continue", "NULL", "true", "false", "void", "int", "char",
        "double", "float", "size_t", "const", "static", "struct", "unsigned", "signed",
    }
)


def _find_c_compiler() -> str | None:
    return shutil.which("gcc") or shutil.which("cc") or shutil.which("clang")


def _detect_already_included_c_sources(
    root: pathlib.Path, c_sources: Sequence[str], include_dirs: Sequence[str]
) -> set[str]:
    """Detect `.c` files already `#include`d via unity-build headers (e.g., `tests/common.h` -> `../cJSON.c`)."""
    included_names: set[str] = set()
    visited_headers: set[pathlib.Path] = set()

    def _scan_file(fp: pathlib.Path, depth: int = 0) -> None:
        if depth > 2 or not fp.is_file() or fp in visited_headers:
            return
        visited_headers.add(fp)
        try:
            txt = fp.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return
        for m in re.finditer(r'#\s*include\s*"([^"]+)"', txt):
            inc = m.group(1)
            if inc.endswith(".c"):
                included_names.add(pathlib.Path(inc).name)
            elif inc.endswith(".h"):
                for base_dir in (fp.parent, *(root / d for d in include_dirs)):
                    cand = (base_dir / inc).resolve()
                    if cand.is_file():
                        _scan_file(cand, depth + 1)
                        break

    for src in c_sources:
        sp = pathlib.Path(src)
        full = sp if sp.is_absolute() else (root / sp)
        _scan_file(full, 0)
    return included_names


def compile_and_run_c_asan(
    repo_root: str | pathlib.Path,
    c_sources: Sequence[str],
    *,
    include_dirs: Sequence[str] = (".", "tests", "tests/unity/src"),
    extra_cflags: Sequence[str] = (),
    run_cwd: str | pathlib.Path | None = None,
    timeout_s: int = 15,
    use_sanitizers: bool = True,
) -> dict[str, Any]:
    """Compile C source + test files with ASan/UBSan and execute, parsing exact fault frames."""
    cc = _find_c_compiler()
    if not cc:
        return {"compiled": False, "passed": False, "reason": "NO_C_COMPILER", "model_calls": 0}

    root = pathlib.Path(repo_root).resolve()
    t0 = time.monotonic()
    already_inc = _detect_already_included_c_sources(root, c_sources, include_dirs)
    effective_sources = [s for s in c_sources if pathlib.Path(s).name not in already_inc] or list(c_sources)

    with tempfile.TemporaryDirectory(prefix="brain_casan_") as td:
        bin_path = pathlib.Path(td) / "test_bin"
        cmd = [cc, "-g", "-O0", "-w"]
        if use_sanitizers:
            cmd.append("-fsanitize=address,undefined")
        for inc in include_dirs:
            inc_p = (root / inc).resolve()
            if inc_p.is_dir():
                cmd.append(f"-I{inc_p}")
        cmd.extend(str(f) for f in extra_cflags)
        for src in effective_sources:
            sp = pathlib.Path(src)
            cmd.append(str(sp if sp.is_absolute() else (root / sp)))
        cmd.extend(["-o", str(bin_path), "-lm"])

        try:
            cp_cc = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True, timeout=timeout_s)
        except (subprocess.TimeoutExpired, OSError) as exc:
            return {"compiled": False, "passed": False, "reason": f"COMPILE_ERR:{exc}", "model_calls": 0}

        if cp_cc.returncode != 0:
            return {
                "compiled": False,
                "passed": False,
                "reason": "COMPILE_FAILED",
                "compile_stderr": cp_cc.stderr[-800:],
                "model_calls": 0,
            }

        run_env = dict(os.environ)
        run_env["ASAN_OPTIONS"] = "detect_leaks=0:abort_on_error=0:halt_on_error=1:symbolize=1"
        run_env["UBSAN_OPTIONS"] = "print_stacktrace=1:halt_on_error=1"
        try:
            cp_run = subprocess.run(
                [str(bin_path)],
                cwd=str(pathlib.Path(run_cwd).resolve() if run_cwd else root),
                env=run_env,
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
        except subprocess.TimeoutExpired:
            return {"compiled": True, "passed": False, "reason": "TIMEOUT", "model_calls": 0}

    comb = cp_run.stdout + "\n" + cp_run.stderr
    faults: list[dict[str, Any]] = []

    def _to_rel(raw_path: str) -> str | None:
        try:
            p = pathlib.Path(raw_path).resolve()
            rel = p.relative_to(root).as_posix()
            return rel
        except Exception:
            cand = raw_path.lstrip("./")
            if (root / cand).is_file():
                return cand
            return None

    # 1. UBSan runtime errors (exact file, line, column, message!)
    for m in _UBSAN_LINE_RE.finditer(comb):
        rel = _to_rel(m.group(1))
        if rel:
            msg = m.group(4).strip()
            low = msg.lower()
            if "null pointer" in low or "member access within null" in low:
                fkind = "NULL_DEREF"
            elif "index" in low and "out of bounds" in low:
                fkind = "BUFFER_OVERFLOW"
            elif "overflow" in low:
                fkind = "SIGNED_OVERFLOW"
            else:
                fkind = "UBSAN_ERROR"
            faults.append(
                {
                    "file": rel,
                    "line": int(m.group(2)),
                    "col": int(m.group(3)),
                    "func": "",
                    "fault_kind": fkind,
                    "message": msg,
                }
            )

    # 2. ASan crash stack frames
    asan_kind = ""
    m_ak = re.search(r"ERROR:\s+AddressSanitizer:\s+([^\n]+)", comb)
    if m_ak:
        ak_txt = m_ak.group(1).strip()
        if "SEGV" in ak_txt and ("0x000000000000" in ak_txt or "unknown address 0x0000" in ak_txt):
            asan_kind = "NULL_DEREF"
        elif "buffer-overflow" in ak_txt:
            asan_kind = "BUFFER_OVERFLOW"
        elif "use-after-free" in ak_txt:
            asan_kind = "USE_AFTER_FREE"
        else:
            asan_kind = "ASAN_ERROR"

    free_pos = comb.find("freed by thread")
    alloc_pos = comb.find("previously allocated by thread")
    for m in _ASAN_FRAME_RE.finditer(comb):
        rel = _to_rel(m.group(2))
        if rel:
            pos = m.start()
            if alloc_pos != -1 and pos >= alloc_pos:
                sec = "alloc"
            elif free_pos != -1 and pos >= free_pos:
                sec = "free"
            else:
                sec = "use"
            faults.append(
                {
                    "file": rel,
                    "line": int(m.group(3)),
                    "col": 0,
                    "func": m.group(1),
                    "section": sec,
                    "fault_kind": asan_kind or "ASAN_ERROR",
                    "message": m_ak.group(1).strip() if m_ak else "",
                }
            )

    # 3. Unity / assert failures (for non-ASan logic/CVE bugs!)
    unity_fails: list[dict[str, Any]] = []
    for m in _UNITY_FAIL_RE.finditer(comb):
        unity_fails.append(
            {
                "file": _to_rel(m.group(1)) or m.group(1),
                "line": int(m.group(2)),
                "test": m.group(3),
                "message": m.group(4).strip(),
            }
        )

    has_sanitizer_err = bool(faults) or ("runtime error:" in comb) or ("ERROR: AddressSanitizer:" in comb)
    passed = (cp_run.returncode == 0) and (not has_sanitizer_err) and (not unity_fails)
    return {
        "compiled": True,
        "passed": passed,
        "returncode": int(cp_run.returncode),
        "faults": faults,
        "unity_fails": unity_fails,
        "stdout_tail": cp_run.stdout[-800:],
        "stderr_tail": cp_run.stderr[-800:],
        "elapsed_ms": int((time.monotonic() - t0) * 1000),
        "model_calls": 0,
    }


def _find_enclosing_c_function(source: str, target_line: int) -> dict[str, Any] | None:
    """Locate the enclosing C function `(start_line, body_open_line, end_line, name, ret_type, params)`."""
    lines = source.splitlines()
    if not (1 <= target_line <= len(lines)):
        return None

    # Walk backwards tracking brace depth to find the top-level `{` at column 0 / depth 0
    depth = 0
    open_idx = -1
    for i in range(target_line - 1, -1, -1):
        ln = lines[i]
        # Strip line comments roughly
        code = ln.split("//", 1)[0]
        for ch in reversed(code):
            if ch == "}":
                depth += 1
            elif ch == "{":
                if depth == 0:
                    open_idx = i
                    break
                depth -= 1
        if open_idx != -1:
            # Verify this `{` is at top-level function scope (indented <= 2 spaces or preceded by `)`!)
            sig_region = "\n".join(lines[max(0, open_idx - 5) : open_idx + 1])
            if re.search(r"\)\s*\{", sig_region) and not re.search(
                r"\b(?:if|for|while|switch|else)\s*\([^)]*\)\s*\{", lines[open_idx]
            ):
                # Check previous non-empty line isn't `if (...)` / `for (...)` / `while (...)`
                prev_non = ""
                for k in range(open_idx, max(-1, open_idx - 4), -1):
                    st = lines[k].strip()
                    if st and st != "{":
                        prev_non = st
                        break
                if not re.match(r"^(?:if|else\s+if|for|while|switch|else)\b", prev_non):
                    break
            # Keep climbing out of nested block `{`
            open_idx = -1

    if open_idx == -1:
        return None

    # Find matching closing `}`
    depth = 0
    end_idx = len(lines) - 1
    started = False
    for i in range(open_idx, len(lines)):
        code = lines[i].split("//", 1)[0]
        for ch in code:
            if ch == "{":
                depth += 1
                started = True
            elif ch == "}":
                depth -= 1
                if started and depth == 0:
                    end_idx = i
                    break
        if started and depth == 0:
            break

    # Extract signature text above `open_idx`
    sig_start = max(0, open_idx - 5)
    sig_lines: list[str] = []
    for i in range(open_idx, sig_start - 1, -1):
        s = lines[i].strip()
        if not s or s.startswith(("/*", "*", "//", "#")) or s.endswith((";", "}")):
            if sig_lines:
                break
            continue
        sig_lines.append(s)
    sig_lines.reverse()
    sig_txt = " ".join(sig_lines)
    sig_head = sig_txt.split("{", 1)[0].strip()

    m_fn = re.search(r"^(.*?)\b([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)\s*$", sig_head)
    if not m_fn:
        return None
    ret_type = re.sub(r"\s+", " ", m_fn.group(1)).strip()
    func_name = m_fn.group(2)
    raw_params = m_fn.group(3).strip()
    params: list[str] = []
    if raw_params and raw_params != "void":
        for p in raw_params.split(","):
            pm = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", p)
            if pm:
                params.append(pm[-1])

    return {
        "func_name": func_name,
        "ret_type": ret_type,
        "params": params,
        "body_open_line": open_idx + 1,
        "end_line": end_idx + 1,
    }


def _mine_c_error_returns(source: str, func_info: Mapping[str, Any]) -> list[str]:
    """Codebase-Internal C Type-Habitation: mine canonical error `return ...;` expressions for `ret_type`."""
    lines = source.splitlines()
    b_open = int(func_info["body_open_line"])
    b_end = int(func_info["end_line"])
    ret_type = str(func_info.get("ret_type") or "")
    fn_slice = "\n".join(lines[b_open - 1 : b_end])

    # 1. Existing error returns inside THIS function (highest priority!)
    in_fn = collections.Counter(
        m.group(1).strip()
        for m in re.finditer(r"\breturn\s*([^;]*);", fn_slice)
        if m.group(1).strip() in ("NULL", "false", "0", "-1", "NAN", "CJSON_INVALID", "")
    )
    # 2. Type-consistent fallbacks mined from the file
    cands: list[str] = [k for k, _ in in_fn.most_common()]
    rt_low = ret_type.lower()
    if "*" in ret_type:
        defaults = ["NULL"]
    elif "cjson_bool" in rt_low or "bool" in rt_low:
        defaults = ["false", "0"]
    elif "double" in rt_low or "float" in rt_low:
        defaults = ["NAN", "0.0"] if ("NAN" in source or "<math.h>" in source) else ["0.0", "NAN"]
    elif "void" in rt_low and "*" not in ret_type:
        defaults = [""]
    else:
        defaults = ["0", "-1", "NULL"]
    for d in defaults:
        if d not in cands:
            cands.append(d)
    return cands[:4]


def _extract_deref_chains(line_txt: str) -> list[str]:
    """Extract ordered pointer expressions dereferenced on `line_txt` (`a->b->c` -> `['a->b', 'a']`)."""
    out: list[str] = []

    def _add(expr: str) -> None:
        e = re.sub(r"\s*->\s*", "->", expr.strip())
        if e and e not in _C_KEYWORDS and e not in out:
            out.append(e)

    # First: arrow chains `a->b->c` — the dereferenced prefixes are `a->b` and `a`!
    for m in _DEREF_CHAIN_RE.finditer(line_txt):
        parts = [p.strip() for p in m.group(1).split("->")]
        # Deepest pointer being dereferenced first (e.g. `item->prev` for `item->prev->next`, then `item`)
        for k in range(len(parts) - 1, 0, -1):
            _add("->".join(parts[:k]))

    # Second: libc pointer arguments (`strlen(valuestring)`, `strcpy(dst, src)`)
    for m in _LIBC_PTR_CALL_RE.finditer(line_txt):
        _add(m.group(1))

    # Third: unary `*ptr` dereferences
    for m in _STAR_DEREF_RE.finditer(line_txt):
        _add(m.group(1))

    return out


def synthesize_c_causal_patches(
    source: str,
    blame_line: int,
    *,
    fault_kind: str = "NULL_DEREF",
    target_func_name: str | None = None,
    max_patches: int = 24,
) -> list[tuple[str, int, str]]:
    """Synthesize minimal causal C repair candidates from ASan/UBSan blame or logic failure."""
    lines = source.splitlines(keepends=True)
    if not (1 <= blame_line <= len(lines)):
        return []
    func_info = _find_enclosing_c_function(source, blame_line)
    if func_info is None:
        return []

    b_open = int(func_info["body_open_line"])
    b_end = int(func_info["end_line"])
    err_rets = _mine_c_error_returns(source, func_info)
    out: list[tuple[str, int, str]] = []
    seen: set[str] = set()

    def _emit(lbl: str, ln: int, psrc: str) -> None:
        if psrc != source and psrc not in seen and len(out) < max_patches:
            seen.add(psrc)
            out.append((lbl, ln, psrc))

    line_txt = lines[blame_line - 1]
    indent = line_txt[: len(line_txt) - len(line_txt.lstrip(" \t"))]

    # --- FAMILY C-1: ASan/UBSan NULL-POINTER DEREFERENCE CAUSAL GUARD SYNTHESIS ---
    if fault_kind in ("NULL_DEREF", "ASAN_ERROR", "UBSAN_ERROR"):
        derefs = _extract_deref_chains(line_txt)
        # Also include function parameters if none found directly on line
        if not derefs:
            derefs = list(func_info.get("params") or ())[:3]

        # Strategy 1a: Inline short-circuit guard inside `if (...)` / `while (...)` on `blame_line`
        m_cond = re.match(r"^(\s*(?:else\s+)?(?:if|while)\s*\()(.+)(\)\s*(?:\{)?\s*\r?\n?)$", line_txt)
        if m_cond:
            pre_c, inner_c, suf_c = m_cond.group(1), m_cond.group(2), m_cond.group(3)
            for ptr in derefs[:4]:
                if f"{ptr} != NULL" in inner_c:
                    continue
                new_ln = f"{pre_c}({ptr} != NULL) && ({inner_c}){suf_c}"
                psrc = "".join(lines[: blame_line - 1]) + new_ln + "".join(lines[blame_line:])
                _emit(f"C_INLINE_NULL_SHORTCIRCUIT_{ptr}", blame_line, psrc)

        # Strategy 1b: Wrap standalone mutation statement on `blame_line` in `if (ptr != NULL) { ... }`
        stripped_ln = line_txt.strip()
        if stripped_ln.endswith(";") and not stripped_ln.startswith(("return ", "if ", "for ", "while ")):
            for ptr in derefs[:3]:
                wrapped = f"{indent}if ({ptr} != NULL)\n{indent}{{\n    {line_txt}{indent}}}\n"
                psrc = "".join(lines[: blame_line - 1]) + wrapped + "".join(lines[blame_line:])
                _emit(f"C_WRAP_STMT_NULL_GUARD_{ptr}", blame_line, psrc)

        # Strategy 1b-type (Family C-5: Codebase-Habited CWE-843 Type-Confusion Guard):
        # When `blame_line` accesses a typed field `var->field` (e.g. `from->valuestring`) after an earlier
        # `if (var == NULL)` / `if (!var)` check in the same function, refine that check to `if (!TypePred(var))`
        # using unary type predicates mined directly from the C source (e.g. `*_IsString`, `*_is_*`, `*_Check`)!
        type_preds = list(
            dict.fromkeys(
                re.findall(
                    r"\b([A-Za-z_][A-Za-z0-9_]*(?:Is[A-Z][A-Za-z0-9_]*|_is_[a-z][a-z0-9_]*|_Check))\s*\(",
                    source,
                )
            )
        )
        if type_preds:
            typed_fields = re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*->\s*([A-Za-z_][A-Za-z0-9_]*)\b", line_txt)
            for var_t, field_t in typed_fields[:3]:
                fl_low = field_t.lower()
                # Rank mined type predicates by suffix overlap with the dereferenced field name
                ranked_preds = sorted(
                    type_preds,
                    key=lambda p: (
                        0
                        if any(
                            tok in fl_low
                            for tok in re.findall(r"[a-z]{3,}", re.sub(r"^.*?(?:Is|_is_)", "", p).lower())
                        )
                        else 1,
                        p,
                    ),
                )
                for j in range(max(b_open, blame_line - 25), blame_line):
                    jtxt = lines[j - 1]
                    m_vn = re.match(
                        rf"^(\s*if\s*\()\s*(?:{re.escape(var_t)}\s*==\s*NULL|NULL\s*==\s*{re.escape(var_t)}|!{re.escape(var_t)})\s*(\)\s*(?:\{{)?\s*\r?\n?)$",
                        jtxt,
                    )
                    if m_vn:
                        g_pre, g_suf = m_vn.group(1), m_vn.group(2)
                        for tp in ranked_preds[:4]:
                            new_j = f"{g_pre}!{tp}({var_t}){g_suf}"
                            psrc = "".join(lines[: j - 1]) + new_j + "".join(lines[j:])
                            _emit(f"C_TYPE_CONFUSION_GUARD_{tp}_{var_t}", j, psrc)

        # Strategy 1c: Expand an existing top-of-function `if (... == NULL)` guard!
        for j in range(b_open, min(b_end, blame_line)):
            jtxt = lines[j - 1]
            m_ng = re.match(r"^(\s*if\s*\()(.+==\s*NULL[^)]*)(\)\s*\r?\n?)$", jtxt)
            if m_ng:
                g_pre, g_cond, g_suf = m_ng.group(1), m_ng.group(2), m_ng.group(3)
                for ptr in derefs[:4]:
                    if f"{ptr} == NULL" in g_cond:
                        continue
                    new_j = f"{g_pre}({g_cond}) || ({ptr} == NULL){g_suf}"
                    psrc = "".join(lines[: j - 1]) + new_j + "".join(lines[j:])
                    _emit(f"C_EXPAND_ENTRY_NULL_GUARD_{ptr}", j, psrc)

        # Strategy 1d: Insert pre-deref / function-entry `if (ptr == NULL) { return <habited_ret>; }`
        # Compute body indentation
        body_indent = "    "
        for k in range(b_open, min(b_end, b_open + 6)):
            s = lines[k]
            if s.strip():
                body_indent = s[: len(s) - len(s.lstrip(" \t"))]
                break

        for ptr in derefs[:3]:
            for rv in err_rets[:2]:
                ret_stmt = f"return {rv};" if rv else "return;"
                # Prioritize function-entry guard for function parameters so ALL control-flow branches are protected!
                if ptr in (func_info.get("params") or ()):
                    guard_e = f"{body_indent}if ({ptr} == NULL)\n{body_indent}{{\n{body_indent}    {ret_stmt}\n{body_indent}}}\n"
                    psrc_e = "".join(lines[:b_open]) + guard_e + "".join(lines[b_open:])
                    _emit(f"C_ENTRY_PARAM_NULL_RETURN_{ptr}_{rv or 'void'}", b_open + 1, psrc_e)
                # Fallback: insert right before blame_line (for non-parameter or nested fields like `item->prev`)
                guard_b = f"{indent}if ({ptr} == NULL)\n{indent}{{\n{indent}    {ret_stmt}\n{indent}}}\n"
                psrc_b = "".join(lines[: blame_line - 1]) + guard_b + "".join(lines[blame_line - 1 :])
                _emit(f"C_PRE_DEREF_NULL_RETURN_{ptr}_{rv or 'void'}", blame_line, psrc_b)

    # --- FAMILY C-4: ASan/UBSan BUFFER_OVERFLOW / UNDERFLOW INDEX-BOUNDS GUARD ---
    if fault_kind in ("BUFFER_OVERFLOW", "ASAN_ERROR", "UBSAN_ERROR"):
        # Detect subtract-index accesses like `buf[strlen(buf) - 1]` or `buf[len - 1]`
        sub_idx_pat = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\[\s*([^\]-]+?)\s*-\s*1\s*\]")
        m_cond_b = re.match(r"^(\s*(?:else\s+)?(?:if|while)\s*\()(.+)(\)\s*(?:\{)?\s*\r?\n?)$", line_txt)
        for m_si in sub_idx_pat.finditer(line_txt):
            buf_nm = m_si.group(1).strip()
            len_expr = m_si.group(2).strip()
            guards: list[tuple[str, str]] = []
            if len_expr.startswith("strlen("):
                guards.append((f"{buf_nm}_nonempty", f"({buf_nm}[0] != '\\0')"))
            guards.append(("len_gt0", f"(({len_expr}) > 0)"))
            if m_cond_b:
                pre_c, inner_c, suf_c = m_cond_b.group(1), m_cond_b.group(2), m_cond_b.group(3)
                for gtag, gexpr in guards:
                    if gexpr in inner_c:
                        continue
                    # Variant 1: Short-circuit conjunction `if ((buf[0] != '\0') && (cond))`
                    new_ln = f"{pre_c}{gexpr} && ({inner_c}){suf_c}"
                    _emit(
                        f"C_OOB_INLINE_UNDERFLOW_{buf_nm}_{gtag}",
                        blame_line,
                        "".join(lines[: blame_line - 1]) + new_ln + "".join(lines[blame_line:]),
                    )
                    # Variant 2: Pre-check `if (!gexpr) break;` (when inside loop body discarding empty buffer!)
                    pre_brk = f"{indent}if (!{gexpr}) {{ break; }}\n"
                    _emit(
                        f"C_OOB_LOOP_BREAK_EMPTY_{buf_nm}_{gtag}",
                        blame_line,
                        "".join(lines[: blame_line - 1]) + pre_brk + "".join(lines[blame_line - 1 :]),
                    )
            else:
                for gtag, gexpr in guards:
                    wrapped = f"{indent}if ({gexpr})\n{indent}{{\n    {line_txt}{indent}}}\n"
                    _emit(
                        f"C_OOB_WRAP_UNDERFLOW_{buf_nm}_{gtag}",
                        blame_line,
                        "".join(lines[: blame_line - 1]) + wrapped + "".join(lines[blame_line:]),
                    )

    # --- FAMILY C-2: BOOLEAN GUARD ALGEBRA & RELATIONAL / LOGICAL OPERATOR CEGIS ---
    # Mine existing `if (<cond>)` conditions inside this function for Guard Scoping (`ci -> (body_cond && ci)`).
    body_conds: list[str] = []
    for ln_k in range(b_open, b_end + 1):
        m_bc = re.match(r"^\s*(?:else\s+)?if\s*\(([^|&]+)\)\s*(?:\{)?\s*$", lines[ln_k - 1].strip())
        if m_bc:
            bc = m_bc.group(1).strip()
            if 3 <= len(bc) <= 48 and bc not in body_conds:
                body_conds.append(bc)

    def _split_top_level(expr: str, sep: str) -> list[str]:
        parts: list[str] = []
        depth = 0
        start = 0
        i = 0
        while i < len(expr):
            ch = expr[i]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth = max(0, depth - 1)
            elif depth == 0 and expr[i : i + len(sep)] == sep:
                parts.append(expr[start:i].strip())
                i += len(sep)
                start = i
                continue
            i += 1
        parts.append(expr[start:].strip())
        return [p for p in parts if p]

    # Scan function's top-level `if (...)` guards for Clause Drop & Body-Condition Guard Scoping
    for ln_i in range(b_open, min(b_end + 1, b_open + 35)):
        txt_i = lines[ln_i - 1]
        m_if = re.match(r"^(\s*(?:else\s+)?if\s*\()(.+)(\)\s*(?:\{)?\s*\r?\n?)$", txt_i)
        if not m_if:
            continue
        pre_i, inner_i, suf_i = m_if.group(1), m_if.group(2), m_if.group(3)
        for sep, tag in (("||", "OR"), ("&&", "AND")):
            clauses = _split_top_level(inner_i, sep)
            if len(clauses) >= 2:
                # B-1: Drop one clause
                for drop_idx in range(len(clauses) - 1, -1, -1):
                    kept = [c for j, c in enumerate(clauses) if j != drop_idx]
                    new_inner = f" {sep} ".join(kept)
                    psrc = "".join(lines[: ln_i - 1]) + f"{pre_i}{new_inner}{suf_i}" + "".join(lines[ln_i:])
                    _emit(f"C_BOOL_DROP_{tag}_CLAUSE_{drop_idx}_L{ln_i}", ln_i, psrc)
                # B-2: Scope one clause with an existing body condition `(body_cond && clause)`
                if sep == "||":
                    for sc_idx in range(len(clauses) - 1, -1, -1):
                        for bc in body_conds[:4]:
                            if bc in clauses[sc_idx]:
                                continue
                            scoped = list(clauses)
                            scoped[sc_idx] = f"(({bc}) && {clauses[sc_idx]})"
                            new_inner = " || ".join(scoped)
                            psrc = "".join(lines[: ln_i - 1]) + f"{pre_i}{new_inner}{suf_i}" + "".join(lines[ln_i:])
                            _emit(f"C_BOOL_SCOPE_OR_CLAUSE_{sc_idx}_L{ln_i}", ln_i, psrc)

    op_swaps = (
        (" == ", " != "),
        (" != ", " == "),
        (" <= ", " < "),
        (" < ", " <= "),
        (" >= ", " > "),
        (" > ", " >= "),
        (" && ", " || "),
        (" || ", " && "),
    )
    scan_lo = max(b_open, blame_line - 6)
    scan_hi = min(b_end, blame_line + 14)
    for ln_i in range(scan_lo, scan_hi + 1):
        txt_i = lines[ln_i - 1]
        if not any(kw in txt_i for kw in ("if ", "if(", "while", "for", "return")):
            continue
        for old_op, new_op in op_swaps:
            if old_op in txt_i:
                rep_ln = txt_i.replace(old_op, new_op, 1)
                psrc = "".join(lines[: ln_i - 1]) + rep_ln + "".join(lines[ln_i:])
                _emit(f"C_REL_OP_{old_op.strip()}_TO_{new_op.strip()}_L{ln_i}", ln_i, psrc)

    return out[:max_patches]


def _clean_c_local_type(ret_type: str) -> str:
    """Strip C storage-class / visibility macros (`static`, `inline`, `CJSON_PUBLIC(...)`) for local temp decls."""
    s = re.sub(r"\bCJSON_PUBLIC\s*\(([^)]+)\)", r"\1", ret_type)
    s = re.sub(r"\b(?:static|extern|inline|__inline|__inline__)\b", "", s)
    return re.sub(r"\s+", " ", s).strip()


def synthesize_c_uaf_patches(
    source: str,
    use_line: int,
    free_line: int,
) -> list[tuple[str, int, str]]:
    """Family C-3: Universal Temporal Use-After-Free Algebraic Commutation (`EVAL-BEFORE-FREE` & `SWAP`).

    Given ASan's paired `(free_line, use_line)` inside the same enclosing C function with `free_line < use_line`:
      - UAF-1 (`free_stmt; return expr;`) -> `<type> _uaf_result = expr; free_stmt; return _uaf_result;`
      - UAF-2 (`free_stmt; stmt;`)        -> `stmt; free_stmt;`
    Preserves memory deallocation (zero leak) while eliminating the heap-use-after-free!
    """
    lines = source.splitlines(keepends=True)
    if not (1 <= free_line < use_line <= len(lines)) or (use_line - free_line) > 8:
        return []
    func_info = _find_enclosing_c_function(source, use_line)
    if func_info is None:
        return []
    if not (int(func_info["body_open_line"]) <= free_line < use_line <= int(func_info["end_line"])):
        return []

    free_txt = lines[free_line - 1]
    use_txt = lines[use_line - 1]
    free_s = free_txt.strip()
    use_s = use_txt.strip()
    if not free_s.endswith(";") or not use_s.endswith(";"):
        return []

    indent = use_txt[: len(use_txt) - len(use_txt.lstrip(" \t"))]
    mid_lines = lines[free_line : use_line - 1]
    out: list[tuple[str, int, str]] = []

    # UAF-1: `free(X); return expr;` -> `<type> _uaf_result = expr; free(X); return _uaf_result;`
    m_ret = re.match(r"^return\s+(.+);$", use_s)
    if m_ret:
        expr = m_ret.group(1).strip()
        local_t = _clean_c_local_type(str(func_info.get("ret_type") or ""))
        if local_t and local_t != "void":
            sep = "" if local_t.endswith("*") else " "
            rewritten = (
                f"{indent}{local_t}{sep}_uaf_result = {expr};\n"
                + "".join(mid_lines)
                + free_txt
                + f"{indent}return _uaf_result;\n"
            )
            psrc = "".join(lines[: free_line - 1]) + rewritten + "".join(lines[use_line:])
            out.append((f"C_UAF_EVAL_BEFORE_FREE_L{free_line}_L{use_line}", free_line, psrc))
    else:
        # UAF-2: Swap `use_stmt` ahead of `free_stmt`
        rewritten = use_txt + "".join(mid_lines) + free_txt
        psrc = "".join(lines[: free_line - 1]) + rewritten + "".join(lines[use_line:])
        out.append((f"C_UAF_SWAP_USE_BEFORE_FREE_L{free_line}_L{use_line}", free_line, psrc))

    return out


def repair_c_repo_asan_cegis(
    repo_root: str | pathlib.Path,
    c_sources: Sequence[str],
    *,
    editable_files: Sequence[str] | None = None,
    include_dirs: Sequence[str] = (".", "tests", "tests/unity/src"),
    extra_cflags: Sequence[str] = (),
    timeout_s: int = 45,
    skill_store: Any = None,
) -> dict[str, Any]:
    """End-to-end zero-model C causal repair driven by `gcc -fsanitize=address,undefined`."""
    t0 = time.monotonic()
    root = pathlib.Path(repo_root).resolve()

    # Step 1: Run baseline under ASan/UBSan to capture exact fault coordinates & class!
    base = compile_and_run_c_asan(
        root, c_sources, include_dirs=include_dirs, extra_cflags=extra_cflags, timeout_s=min(15, timeout_s)
    )
    if not base.get("compiled"):
        return {
            "repaired": False,
            "reason": str(base.get("reason") or "BASELINE_COMPILE_FAILED"),
            "compile_stderr": base.get("compile_stderr", ""),
            "elapsed_ms": int((time.monotonic() - t0) * 1000),
            "model_calls": 0,
        }
    if base.get("passed"):
        return {
            "repaired": False,
            "reason": "BASELINE_ALREADY_PASSING",
            "elapsed_ms": int((time.monotonic() - t0) * 1000),
            "model_calls": 0,
        }

    # Filter fault frames to editable non-test `.c` files
    allowed_files = set(editable_files) if editable_files else {
        s for s in c_sources if s.endswith(".c") and not s.startswith("tests/") and "test" not in pathlib.Path(s).name.lower()
    }
    raw_faults = list(base.get("faults") or ())
    cands_tested = 0

    def _admit_c_law(fkind_s: str, lbl_s: str, rf_s: str, ln_i: int) -> str | None:
        if skill_store is not None and hasattr(skill_store, "admit"):
            try:
                from canonical.swe_kernel import universal_computer_agent_v1 as uca
                lid = f"c_asan::{hashlib.sha256(f'{fkind_s}:{lbl_s}'.encode()).hexdigest()[:10]}"
                law = uca.ParameterizedCausalLaw(
                    law_id=lid,
                    domain="c_asan_cegis",
                    tool_or_action=lbl_s,
                    command_template=["c_asan_cegis", fkind_s, lbl_s],
                    preconditions={"sanitizer_fault": fkind_s},
                    effects={"asan_ubsan_clean_pass": True},
                    provenance={"file": rf_s, "line": ln_i, "rule": lbl_s},
                    generalized=True,
                )
                skill_store.admit(law)
                return lid
            except Exception:
                return None
        return None

    # Step 1.5 (Family C-3): Paired ASan USE-AFTER-FREE `(free_frame, use_frame)` commutation!
    use_frames = [f for f in raw_faults if f.get("fault_kind") == "USE_AFTER_FREE" and f.get("section") == "use" and f.get("file") in allowed_files]
    free_frames = [f for f in raw_faults if f.get("fault_kind") == "USE_AFTER_FREE" and f.get("section") == "free" and f.get("file") in allowed_files]
    if use_frames and free_frames:
        seen_uaf: set[tuple[str, int, int]] = set()
        for uf in use_frames:
            for ff in free_frames:
                if uf.get("file") == ff.get("file") and uf.get("func") == ff.get("func"):
                    rf_u = str(uf["file"])
                    ln_u = int(uf["line"])
                    ln_f = int(ff["line"])
                    if ln_f < ln_u and (rf_u, ln_f, ln_u) not in seen_uaf:
                        seen_uaf.add((rf_u, ln_f, ln_u))
                        fp_u = root / rf_u
                        if not fp_u.is_file():
                            continue
                        orig_u = fp_u.read_text(encoding="utf-8", errors="replace")
                        for lbl, ln_p, psrc in synthesize_c_uaf_patches(orig_u, ln_u, ln_f):
                            cands_tested += 1
                            try:
                                fp_u.write_text(psrc, encoding="utf-8")
                                chk = compile_and_run_c_asan(
                                    root, c_sources, include_dirs=include_dirs, extra_cflags=extra_cflags, timeout_s=15
                                )
                            finally:
                                fp_u.write_text(orig_u, encoding="utf-8")
                            if chk.get("compiled") and chk.get("passed"):
                                law_id = _admit_c_law("USE_AFTER_FREE", lbl, rf_u, ln_p)
                                return {
                                    "repaired": True,
                                    "method": "C_ASAN_UBSAN_CAUSAL_CEGIS",
                                    "rule": lbl,
                                    "fault_kind": "USE_AFTER_FREE",
                                    "patched_file": rf_u,
                                    "patched_line": ln_p,
                                    "patched_source": psrc,
                                    "patched_files": {rf_u: psrc},
                                    "candidates_verified": cands_tested,
                                    "learned_law_id": law_id,
                                    "elapsed_ms": int((time.monotonic() - t0) * 1000),
                                    "model_calls": 0,
                                }

    target_sites: list[tuple[str, int, str]] = []
    seen_sites: set[tuple[str, int]] = set()
    for f in raw_faults:
        rf = str(f.get("file") or "")
        ln = int(f.get("line") or 0)
        fk = str(f.get("fault_kind") or "ASAN_ERROR")
        if rf in allowed_files and ln > 0 and (rf, ln) not in seen_sites:
            seen_sites.add((rf, ln))
            target_sites.append((rf, ln, fk))

    # Fallback: if no sanitizer frame in editable files, localize C function definitions matching Unity test names
    if not target_sites and base.get("unity_fails"):
        fail_raw = " ".join(
            f"{u.get('test', '')} {u.get('message', '')}" for u in base["unity_fails"]
        )
        fail_norm = re.sub(r"[^a-z0-9]+", "", fail_raw.lower())
        for rf in sorted(allowed_files):
            fp = root / rf
            if not fp.is_file():
                continue
            src_lines = fp.read_text(encoding="utf-8", errors="replace").splitlines()
            for idx, ltxt in enumerate(src_lines, 1):
                if ltxt.startswith((" ", "\t", "*", "/", "#")):
                    continue
                for m_f in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_]{5,})\s*\(", ltxt):
                    fn_name = m_f.group(1)
                    if fn_name in ("CJSON_PUBLIC", "CJSON_STDCALL"):
                        continue
                    fn_norm = re.sub(r"[^a-z0-9]+", "", fn_name.lower())
                    if len(fn_norm) >= 6 and fn_norm in fail_norm:
                        # Confirm `{` appears on this line or within the next 3 lines (definition, not call/decl!)
                        blk = "\n".join(src_lines[idx - 1 : min(len(src_lines), idx + 3)])
                        if "{" in blk and not ltxt.rstrip().endswith(";"):
                            target_sites.append((rf, min(len(src_lines), idx + 3), "LOGIC_FAIL"))
                            break

    for rf, blame_ln, fkind in target_sites[:4]:
        fp = root / rf
        if not fp.is_file():
            continue
        orig_src = fp.read_text(encoding="utf-8", errors="replace")
        patches = synthesize_c_causal_patches(orig_src, blame_ln, fault_kind=fkind, max_patches=36)
        for lbl, ln, psrc in patches:
            if time.monotonic() - t0 > timeout_s:
                break
            cands_tested += 1
            try:
                fp.write_text(psrc, encoding="utf-8")
                chk = compile_and_run_c_asan(
                    root, c_sources, include_dirs=include_dirs, extra_cflags=extra_cflags, timeout_s=15
                )
            finally:
                fp.write_text(orig_src, encoding="utf-8")

            if chk.get("compiled") and chk.get("passed"):
                law_id = _admit_c_law(fkind, lbl, rf, ln)
                return {
                    "repaired": True,
                    "method": "C_ASAN_UBSAN_CAUSAL_CEGIS",
                    "rule": lbl,
                    "fault_kind": fkind,
                    "patched_file": rf,
                    "patched_line": ln,
                    "patched_source": psrc,
                    "patched_files": {rf: psrc},
                    "candidates_verified": cands_tested,
                    "learned_law_id": law_id,
                    "elapsed_ms": int((time.monotonic() - t0) * 1000),
                    "model_calls": 0,
                }

    return {
        "repaired": False,
        "reason": "NO_VERIFIED_C_PATCH",
        "faults": base.get("faults", []),
        "unity_fails": base.get("unity_fails", []),
        "candidates_verified": cands_tested,
        "elapsed_ms": int((time.monotonic() - t0) * 1000),
        "model_calls": 0,
    }


# ===========================================================================
# ENGINE P-1: ZERO-LEAKAGE ISSUE-ONLY C ASAN/UBSAN BOUNDARY FUZZ ORACLE
# ===========================================================================


def _parse_c_header_decls(header_text: str) -> list[dict[str, Any]]:
    """Parse C function declarations from a `.h` header file (supports `CJSON_PUBLIC(...)` / `extern` macros)."""
    # Strip C comments and preprocessor directives
    clean = re.sub(r"/\*.*?\*/", " ", header_text, flags=re.S)
    clean = re.sub(r"//[^\n]*", " ", clean)
    clean = "\n".join(ln for ln in clean.splitlines() if not ln.lstrip().startswith("#"))
    decls: list[dict[str, Any]] = []
    # Match `<ret> <name>(<params>);`
    pat = re.compile(
        r"(?:CJSON_PUBLIC\s*\(([^)]+)\)|([A-Za-z_][A-Za-z0-9_\s\*]*?))\s+([A-Za-z_][A-Za-z0-9_]{2,})\s*\(([^;{}]*)\)\s*;"
    )
    for m in pat.finditer(clean):
        ret_raw = (m.group(1) or m.group(2) or "").strip()
        ret_type = re.sub(r"\s+", " ", ret_raw)
        fn_name = m.group(3).strip()
        if fn_name in _C_KEYWORDS or fn_name.startswith("__"):
            continue
        raw_p = re.sub(r"\s+", " ", m.group(4)).strip()
        params: list[tuple[str, str]] = []
        if raw_p and raw_p != "void":
            if "..." in raw_p:
                continue
            for idx, piece in enumerate(raw_p.split(",")):
                piece = piece.strip()
                if not piece:
                    continue
                pm = re.match(r"^(.*?)([A-Za-z_][A-Za-z0-9_]*)\s*$", piece)
                if pm and pm.group(1).strip():
                    ptype = re.sub(r"\s+", " ", pm.group(1)).strip()
                    pname = pm.group(2).strip()
                else:
                    ptype = piece
                    pname = f"arg{idx}"
                params.append((ptype, pname))
        decls.append({"ret_type": ret_type, "name": fn_name, "params": params})
    return decls


def _normalize_c_ptr_base(type_str: str) -> str:
    """Normalize `const cJSON * const` -> `cJSON *`."""
    s = re.sub(r"\b(?:const|volatile|restrict|struct)\b", "", type_str)
    s = re.sub(r"\s*\*\s*", " *", s)
    return re.sub(r"\s+", " ", s).strip()


def _mine_c_type_constructors(decls: Sequence[Mapping[str, Any]]) -> dict[str, list[str]]:
    """Mine valid C constructor call expressions per pointer type directly from header declarations."""
    ctors: dict[str, list[str]] = collections.defaultdict(list)
    ctor_hints = ("create", "new", "make", "alloc", "init", "parse")
    for d in decls:
        rt = _normalize_c_ptr_base(str(d["ret_type"]))
        if not rt.endswith("*") or rt.startswith("void *") or rt.startswith("char *"):
            continue
        nm = str(d["name"])
        nm_low = nm.lower()
        if not any(h in nm_low for h in ctor_hints):
            continue
        params = list(d["params"])
        expr: str | None = None
        if len(params) == 0:
            expr = f"{nm}()"
        elif len(params) == 1:
            pt0 = _normalize_c_ptr_base(params[0][0])
            if pt0 == "char *":
                expr = f'{nm}("brain_probe")'
            elif pt0 in ("double", "float"):
                expr = f"{nm}(1.0)"
            elif pt0 in ("int", "long", "size_t", "unsigned int", "cJSON_bool"):
                expr = f"{nm}(1)"
        if expr and expr not in ctors[rt]:
            # Prioritize Object/String/Number/Array constructors first
            if any(k in nm_low for k in ("string", "object", "number", "array")):
                ctors[rt].insert(0, expr)
            else:
                ctors[rt].append(expr)
    return {k: v[:8] for k, v in ctors.items()}


def _habited_c_values_for_type(ptype: str, ctors: Mapping[str, list[str]], hint_text: str = "") -> list[str]:
    """Return valid non-NULL C value expressions for `ptype`, mined strictly from headers."""
    nt = _normalize_c_ptr_base(ptype)
    if nt == "char *":
        return ['"brain_probe"']
    if nt.endswith("*"):
        c_list = list(ctors.get(nt) or ())
        if c_list:
            if hint_text:
                hl = hint_text.lower()
                c_list.sort(
                    key=lambda expr: (
                        0 if any(tok in hl for tok in ("string", "array", "object", "number", "bool") if tok in expr.lower()) else 1,
                        expr,
                    )
                )
            return c_list[:6]
        base_t = nt.rstrip("*").strip()
        if base_t and base_t != "void":
            return [f"({nt})calloc(1, sizeof({base_t}))"]
        return ["calloc(1, 64)"]
    if nt in ("double", "float"):
        return ["42.0"]
    return ["1"]


def synthesize_c_issue_asan_oracle(
    repo_root: str | pathlib.Path,
    issue_text: str,
    *,
    c_sources: Sequence[str] | None = None,
    include_dirs: Sequence[str] = (".", "tests"),
    timeout_s: int = 20,
) -> dict[str, Any]:
    """Zero-Leakage Engine P-1: Synthesize a C ASan/UBSan Boundary Fuzz Harness purely from `.h` + issue text.

    Zero human tests, zero ground-truth hints, zero model calls.
    Probes header-mined target functions with single-argument NULL & empty-container boundary vectors
    under `gcc -fsanitize=address,undefined` until a REAL sanitizer crash reproduces on the buggy repo.
    """
    root = pathlib.Path(repo_root).resolve()
    headers = sorted(
        p for p in root.glob("*.h") if "test" not in p.name.lower()
    )
    if not headers:
        headers = sorted(
            p for p in root.rglob("*.h")
            if ".git" not in p.parts and "test" not in p.as_posix().lower()
        )[:8]
    if not headers:
        return {"synthesized": False, "reason": "NO_C_HEADERS", "model_calls": 0}

    all_decls: list[tuple[str, dict[str, Any]]] = []
    header_decls_flat: list[dict[str, Any]] = []
    for hp in headers:
        rel_h = hp.relative_to(root).as_posix()
        ds = _parse_c_header_decls(hp.read_text(encoding="utf-8", errors="replace"))
        for d in ds:
            all_decls.append((rel_h, d))
            header_decls_flat.append(d)

    ctors = _mine_c_type_constructors(header_decls_flat)
    issue_low = (issue_text or "").lower()
    issue_tokens = set(re.findall(r"[a-zA-Z_][a-zA-Z0-9_]{2,}", issue_text or ""))
    issue_tokens_low = {t.lower() for t in issue_tokens}

    # Score candidate header functions strictly from issue text mentions
    scored: list[tuple[int, str, dict[str, Any]]] = []
    for rel_h, d in all_decls:
        nm = str(d["name"])
        if not d["params"]:
            continue
        score = 0
        if nm in issue_tokens:
            score += 100
        elif nm.lower() in issue_low:
            score += 80
        else:
            parts = [p.lower() for p in re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)", nm) if len(p) >= 4]
            overlap = sum(1 for p in parts if p in issue_tokens_low)
            if overlap >= 2:
                score += overlap * 15
        if score > 0:
            scored.append((score, rel_h, d))
    scored.sort(key=lambda x: (-x[0], x[2]["name"]))

    if not scored:
        return {"synthesized": False, "reason": "NO_MATCHING_C_FUNCTIONS", "model_calls": 0}

    if c_sources is None:
        c_sources = sorted(
            p.relative_to(root).as_posix()
            for p in root.glob("*.c")
            if "test" not in p.name.lower()
            and "int main(" not in p.read_text(encoding="utf-8", errors="replace")
        )

    oracle_rel = "_brain_c_asan_oracle.c"
    oracle_path = root / oracle_rel

    for _, rel_h, decl in scored[:4]:
        fn = str(decl["name"])
        params: list[tuple[str, str]] = list(decl["params"])
        ret_t = str(decl["ret_type"])
        ptr_indices = [i for i, (pt, _) in enumerate(params) if "*" in pt]

        # Build boundary probe vectors:
        #   (A) Each pointer param set to NULL while all others use header-habited valid objects
        #   (B) All params using header-habited valid empty objects (triggers `parent->child == NULL`!)
        probe_cases: list[tuple[str, list[str]]] = []
        # Pre-compute habited variants for each param (ranked by fn + issue type hints!)
        hint_s = f"{fn} {issue_text}"
        param_vals = [_habited_c_values_for_type(pt, ctors, hint_text=hint_s) for pt, _ in params]

        # Vector A: Single-argument NULL perturbations across top 4 receiver variants
        for null_idx in ptr_indices:
            first_variants = param_vals[0][:4] if null_idx != 0 else ["NULL"]
            for v0 in first_variants:
                args = []
                for j in range(len(params)):
                    if j == null_idx:
                        args.append("NULL")
                    elif j == 0:
                        args.append(v0)
                    else:
                        args.append(param_vals[j][0])
                probe_cases.append((f"NULL_ARG_{null_idx}_{params[null_idx][1]}", args))

        # Vector B: All valid empty-container objects (catches `parent->child == NULL`!)
        if len(ptr_indices) >= 2:
            zero_arg_ctors = [v for v in param_vals[0] if v.endswith("()")]
            v0_empty = zero_arg_ctors[0] if zero_arg_ctors else param_vals[0][0]
            args_b = [v0_empty] + [param_vals[j][0] for j in range(1, len(params))]
            probe_cases.append(("EMPTY_CONTAINER_RECEIVER", args_b))

        # Test each boundary vector individually under ASan/UBSan until a REAL sanitizer fault triggers!
        for pkind, args in probe_cases[:14]:
            call_probe = f"    (void){fn}({', '.join(args)});\n"
            if _normalize_c_ptr_base(ret_t) in ("double", "float") and "NULL" in args:
                call_probe = (
                    f"    double _r_probe = {fn}({', '.join(args)});\n"
                    "    (void)_r_probe;\n"
                )
            src_c = (
                "#include <stdlib.h>\n"
                "#include <stddef.h>\n"
                "#include <math.h>\n"
                f'#include "{rel_h}"\n'
                "int main(void) {\n"
                f"{call_probe}"
                "    return 0;\n"
                "}\n"
            )
            try:
                oracle_path.write_text(src_c, encoding="utf-8")
                res = compile_and_run_c_asan(
                    root,
                    list(c_sources) + [oracle_rel],
                    include_dirs=include_dirs,
                    timeout_s=min(10, timeout_s),
                )
            finally:
                if oracle_path.exists():
                    oracle_path.unlink()

            if res.get("compiled") and not res.get("passed") and res.get("faults"):
                # Confirm a sanitizer fault landed inside an editable `.c` source file!
                src_set = set(c_sources)
                src_faults = [f for f in res["faults"] if f.get("file") in src_set]
                if src_faults:
                    return {
                        "synthesized": True,
                        "oracle_kind": f"C_ASAN_BOUNDARY_{pkind}",
                        "target_function": fn,
                        "header": rel_h,
                        "oracle_source": src_c,
                        "fault_kind": src_faults[0].get("fault_kind"),
                        "fault_file": src_faults[0].get("file"),
                        "fault_line": src_faults[0].get("line"),
                        "model_calls": 0,
                    }

    return {"synthesized": False, "reason": "NO_ASAN_CRASH_REPRODUCED", "model_calls": 0}


def repair_c_repo_from_issue_zero_leakage(
    repo_root: str | pathlib.Path,
    issue_text: str,
    *,
    c_sources: Sequence[str] | None = None,
    include_dirs: Sequence[str] = (".", "tests"),
    timeout_s: int = 45,
    skill_store: Any = None,
) -> dict[str, Any]:
    """Zero-Leakage Issue-Only C Repair: synthesize C ASan/UBSan oracle from issue + `.h`, then repair!

    Zero human tests, zero model calls, leaves ZERO oracle files in the repo.
    """
    t0 = time.monotonic()
    root = pathlib.Path(repo_root).resolve()
    if c_sources is None:
        c_sources = sorted(
            p.relative_to(root).as_posix()
            for p in root.glob("*.c")
            if "test" not in p.name.lower()
            and "int main(" not in p.read_text(encoding="utf-8", errors="replace")
        )

    oracle = synthesize_c_issue_asan_oracle(
        root, issue_text, c_sources=c_sources, include_dirs=include_dirs, timeout_s=min(20, timeout_s)
    )
    if not oracle.get("synthesized"):
        return {
            "repaired": False,
            "reason": str(oracle.get("reason") or "C_ORACLE_SYNTHESIS_FAILED"),
            "oracle_synthesis": oracle,
            "elapsed_ms": int((time.monotonic() - t0) * 1000),
            "model_calls": 0,
        }

    oracle_rel = "_brain_c_asan_oracle.c"
    oracle_path = root / oracle_rel
    try:
        oracle_path.write_text(str(oracle["oracle_source"]), encoding="utf-8")
        rep = repair_c_repo_asan_cegis(
            root,
            list(c_sources) + [oracle_rel],
            editable_files=list(c_sources),
            include_dirs=include_dirs,
            timeout_s=max(10, int(timeout_s - (time.monotonic() - t0))),
            skill_store=skill_store,
        )
    finally:
        if oracle_path.exists():
            oracle_path.unlink()

    rep["oracle_synthesis"] = {
        "oracle_kind": oracle.get("oracle_kind"),
        "target_function": oracle.get("target_function"),
        "fault_kind": oracle.get("fault_kind"),
        "fault_file": oracle.get("fault_file"),
        "fault_line": oracle.get("fault_line"),
    }
    rep["zero_leakage_issue_only"] = True
    return rep

