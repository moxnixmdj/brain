# PROJECT_BRAIN
"""python.refactor.extract_function.v1 — scope-aware statement-block
extraction with named-parameter inference and a test referee.

Second semantic editing verb (after rename_parameter).  A marked region of
statements inside a function is lifted into a new module-level function, the
region replaced by a call, byte-exact (ast span law: every splice point is
integrity-checked; comments, formatting and all untouched lines survive
byte-identically).

Inference law (senior reviewer rules, not heuristics):

* inputs   = names LOADED in the region that are bound earlier in the
             enclosing function scope (parameters, assignments, loop /
             comprehension / except targets at lines < region start).
             Module-level names never become parameters (new function sits
             in the same module where they still resolve).
             `self` is just a parameter — method regions extract with an
             explicit `self` parameter.
* outputs  = names STORED in the region that are LOADED after it
             (downstream in the same function).  Dead writes (never read
             after the region) are dropped — the call result is only
             assigned when later code observes it.  0 outputs -> bare call;
             1 output -> `x = new(...)`; >=2 -> `a, b = new(...)`.
* refuse   = misaligned regions (partial statements), control-flow escapes
             (return/break/continue/yield inside the region), nested
             def/class/lambda-*binding* complications, name collision of
             the new function, and ANY `global`/`nonlocal` on a name the
             region touches.

Verification law: the named suite runs after the bytes are rewritten; red
=> every byte restored and TESTS_RED_AFTER_EDIT; no tests => verified
stays false loudly.

Inputs (kwargs, repo-confined):
  source_root, module, qualname      function coordinate
  new_name                           identifier for the extracted function
  start_line, end_line               1-based inclusive region bounds
  output_path                        summary artifact (registry mirrors)
  run_tests                          list of pytest args (default [])
  python_executable, timeout_s

result_fields: adapter, complete, edit_count, files_edited, inputs, outputs,
extracted_name, output_path, output_sha256, output_verified, verified.
"""

from __future__ import annotations

import ast
import json
import keyword
import subprocess
import sys
from pathlib import Path

from canonical.runtime.bound_capabilities.python_refactor_rename_parameter import (
    _safe_path,
    _sha256,
)  # shared splice/safety law, harvested unchanged (white-box reuse)


def _fail(reason: str) -> None:
    raise SystemExit(json.dumps({"error": True,
                                 "capability": "python.refactor.extract_function.v1",
                                 "reason": reason}, indent=2, sort_keys=True))

SCHEMA = "PROJECT_BRAIN_REFACTOR_EXTRACT_FUNCTION_V1"

_CEXC = SystemExit  # shared refusal channel (rename_parameter._fail)


def _fn_lookup(tree: ast.Module, parts: list[str]):
    """Resolve qualname to its FunctionDef node; refuse loudly outside."""
    nodes = tree.body
    cursor = list(parts)
    fn = None
    while cursor:
        head, cursor = cursor[0], cursor[1:]
        hit = [n for n in nodes
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
               and getattr(n, "name", None) == head]
        if not hit:
            _fail("SYMBOL_NOT_FOUND:" + ".".join(parts))
        if len(hit) > 1:
            _fail("MULTI_DEFINITION:" + ".".join(parts))
        fn = hit[0]
        nodes = fn.body
    if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
        _fail("SYMBOL_NOT_FOUND:" + ".".join(parts))
    return fn


def _scope_names(fn) -> tuple[set, dict]:
    """(parameter names, {stmt-level assigned name -> first line})."""
    args = fn.args
    params = {a.arg for a in args.posonlyargs + args.args + args.kwonlyargs}
    for a in (args.vararg, args.kwarg):
        if a:
            params.add(a.arg)
    assigned: dict[str, int] = {}
    for name, line in _stores_of(fn):
        assigned.setdefault(name, line)
    return params, assigned


def _stores_of(node) -> list[tuple[str, int]]:
    """All Store-context Name bindings owned by a subtree — including names
    bound inside compound statements (if/for/while/with/try arms) — but
    NEVER names bound inside a nested def/class/lambda scope."""
    out: list[tuple[str, int]] = []

    def visit(t):
        if isinstance(t, ast.Name) and isinstance(t.ctx, (ast.Store, ast.Del)):
            out.append((t.id, t.lineno))
        elif isinstance(t, (ast.Tuple, ast.List)):
            for e in t.elts:
                visit(e)
        elif isinstance(t, ast.Starred):
            visit(t.value)

    def scan(n, top):
        if not top and isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef,
                                      ast.ClassDef, ast.Lambda)):
            return                                  # a different scope
        if isinstance(n, ast.Assign):
            for t in n.targets:
                visit(t)
        elif isinstance(n, (ast.AnnAssign, ast.AugAssign)) and n.target is not None:
            visit(n.target)
        elif isinstance(n, (ast.For, ast.AsyncFor)):
            visit(n.target)
        elif isinstance(n, (ast.With, ast.AsyncWith)):
            for item in n.items:
                if item.optional_vars is not None:
                    visit(item.optional_vars)
        elif isinstance(n, ast.ExceptHandler) and n.name:
            out.append((n.name, n.lineno))          # bare str name in 3.11+
        elif isinstance(n, ast.comprehension):
            visit(n.target)
        for c in ast.iter_child_nodes(n):
            scan(c, False)

    scan(node, True)
    return out


def _loads_of(node) -> list[tuple[str, int]]:
    out = []
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load):
            out.append((sub.id, sub.lineno))
        if isinstance(sub, ast.comprehension):
            # comprehension iterables load in the enclosing scope
            pass
    return out


def _has_blocking_cf(stmt) -> str | None:
    for n in ast.walk(stmt):
        if isinstance(n, ast.Return):
            return "RETURN_IN_REGION"
        if isinstance(n, (ast.Break, ast.Continue)):
            return "LOOP_ESCAPE_IN_REGION"
        if isinstance(n, (ast.Yield, ast.YieldFrom)):
            return "YIELD_IN_REGION"
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            return "NESTED_DEF_IN_REGION"
    return None


def _check_nonlocal_global(fn, names: set[str]):
    for n in ast.walk(fn):
        if isinstance(n, (ast.Global, ast.Nonlocal)):
            for nm in n.names:
                if nm in names:
                    _fail("REFUSE_NONLOCAL_OR_GLOBAL:" + nm)


def run(args, root):
    repo = Path(root).resolve()
    args = dict(args or {})
    src_rel = str(args.get("source_root") or "")
    src_abs = _safe_path(repo, src_rel, must_exist=True)
    if not src_abs.is_dir():
        _fail("SOURCE_ROOT_NOT_DIRECTORY")
    module_rel = str(args.get("module") or "")
    if not module_rel.endswith(".py"):
        _fail("MODULE_MUST_BE_PY")
    module_abs = _safe_path(src_abs, module_rel, must_exist=True)
    qualname = str(args.get("qualname") or "")
    raw_new_name = args.get("new_name")
    new_name = str(raw_new_name if raw_new_name is not None else "")
    new_name_was_defaulted = new_name in ("", "_extracted_helper")
    if new_name == "":
        new_name = "_extracted_helper"
    if not new_name.isidentifier() or keyword.iskeyword(new_name):
        _fail("INVALID_IDENTIFIER:new_name")
    raw_start = args.get("start_line")
    raw_end = args.get("end_line")
    region_was_defaulted = raw_start in (None, "", 0, "0") and raw_end in (None, "", 0, "0")
    try:
        start = 0 if region_was_defaulted else int(args.get("start_line"))
        end = 0 if region_was_defaulted else int(args.get("end_line"))
    except (TypeError, ValueError):
        _fail("REGION_INVALID")
    if not region_was_defaulted and not (start >= 1 and end >= start):
        _fail("REGION_INVALID")
    out_rel = str(args.get("output_path") or "")
    out_abs = _safe_path(repo, out_rel)
    python_exe = str(args.get("python_executable") or sys.executable)
    timeout_s = int(args.get("timeout_s") or 300)
    run_tests = list(args.get("run_tests") or [])
    # A caller that names pytest args gets pytest; a corpus this module
    # derived itself is run through the loader instead.
    verify_argv = [python_exe, "-m", "pytest", "-q",
                   "-p", "no:cacheprovider"] + run_tests
    if run_tests:
        import importlib.util as _ilu
        if _ilu.find_spec("pytest") is None and all(str(x).endswith(".py") for x in run_tests):
            from canonical.runtime.bound_capabilities.python_test_guided_patch_search_v1 import (
                suite_argv as _suite_argv_explicit,
            )
            resolved_explicit = [
                str((src_abs / str(x)).resolve()) if not Path(str(x)).is_absolute() else str(x)
                for x in run_tests
            ]
            verify_argv = _suite_argv_explicit(python_exe, *resolved_explicit)
    if not run_tests and ("run_tests" not in args or args.get("capability_id")):
        # The verification law below is the adapter's own: "the named suite runs
        # after the bytes are rewritten; red => every byte restored and
        # TESTS_RED_AFTER_EDIT; no tests => verified stays false loudly."  That
        # honesty is right, but the registry template hardcodes run_tests to [],
        # so the capability could NEVER vouch for its own edit -- it rewrote the
        # caller's source, reported verified False, and the acceptance layer
        # refused it with STEP_NOT_VERIFIED_BY_ITS_PRODUCER.  Measured on
        # dac97dc, a correct extract-function refactoring was performed and then
        # rejected for want of a suite nobody had named.
        #
        # The corpus is a fact about the tree, not a guess, and the module that
        # states it is already shared with the eleven capabilities that refuse
        # TEST_PATHS_REQUIRED.  A tree with no tests still yields nothing here,
        # and verified still stays false loudly -- exactly as the law requires.
        try:
            # discover_test_files, not discover_test_paths: the suite runs with
            # cwd=src_abs, so a repository-relative path would not resolve from
            # there and the runner would fail on a corpus that exists.
            from canonical.runtime.bound_capabilities.python_test_corpus_discovery_v1 import (
                discover_test_files as _discover_test_files,
            )
            from canonical.runtime.bound_capabilities.python_test_guided_patch_search_v1 import (
                suite_argv as _suite_argv,
            )
            try:
                discovered = [str(x) for x in _discover_test_files(src_abs)]
            except FileNotFoundError:
                discovered = []
            if (not discovered
                    and bool(str(args.get("goal") or "").strip())
                    and (src_abs / "__init__.py").is_file()
                    and (src_abs.parent == repo or repo in src_abs.parent.parents)
                    and (src_abs.parent / "tests").is_dir()):
                discovered = [str(x) for x in _discover_test_files(src_abs.parent / "tests")]
            if discovered:
                run_tests = discovered
                # Not pytest.  suite_argv collects through unittest's loader and
                # falls back to runpy, so the verification does not depend on a
                # third-party package being installed -- measured on dac97dc, the
                # hardcoded `python -m pytest` answered "No module named pytest"
                # and the capability rolled back a correct refactoring because
                # its verifier could not start.  A capability that names pytest
                # in its own args still gets pytest below.
                verify_argv = _suite_argv(python_exe, *discovered)
        except Exception:
            run_tests = []

    original_bytes = module_abs.read_bytes()
    text = original_bytes.decode("utf-8")
    lines = text.splitlines(keepends=True)
    try:
        tree = ast.parse(text, filename=module_rel)
    except SyntaxError as exc:
        _fail("SYNTAX_ERROR_IN_FILE:" + module_rel + ":" + str(exc))

    fn = _fn_lookup(tree, qualname.split("."))

    if new_name_was_defaulted:
        existing_top = {
            getattr(n, "name", "")
            for n in tree.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        }
        cand = f"_{fn.name}_extracted"
        idx = 2
        while cand in existing_top or cand == fn.name:
            cand = f"_{fn.name}_extracted_{idx}"
            idx += 1
        new_name = cand

    if region_was_defaulted or (start == 0 and end == 0):
        # Deterministic control-flow-free body slicing: find the longest contiguous
        # statement run in fn.body (excluding docstring) without return/yield/loop-escape.
        body_stmts = list(fn.body)
        if (body_stmts
                and isinstance(body_stmts[0], ast.Expr)
                and isinstance(getattr(body_stmts[0], "value", None), ast.Constant)
                and isinstance(body_stmts[0].value.value, str)):
            body_stmts = body_stmts[1:]
        best_run: list[ast.stmt] = []
        cur_run: list[ast.stmt] = []
        for stmt in body_stmts:
            if _has_blocking_cf(stmt) is None:
                cur_run.append(stmt)
                if len(cur_run) > len(best_run):
                    best_run = list(cur_run)
            else:
                cur_run = []
        if not best_run:
            _fail("NO_EXTRACTABLE_REGION:" + qualname)
        start = best_run[0].lineno
        end = getattr(best_run[-1], "end_lineno", best_run[-1].lineno)

    # region must be a contiguous run of complete statements at exactly ONE
    # statement-chain level.  Descend ONLY through same-scope block-stmts —
    # a region inside a nested def/lambda belongs to another function.
    def stmt_chains(body):
        yield body
        for s in body:
            if isinstance(s, (ast.If, ast.For, ast.AsyncFor, ast.While)):
                yield from stmt_chains(s.body)
                yield from stmt_chains(s.orelse)
            elif isinstance(s, (ast.With, ast.AsyncWith)):
                yield from stmt_chains(s.body)
            elif isinstance(s, ast.Try):
                yield from stmt_chains(s.body)
                yield from stmt_chains(s.orelse)
                yield from stmt_chains(s.finalbody)
                for h in s.handlers:
                    yield from stmt_chains(h.body)
            # def/class bodies: a different function's scope — never searched

    def _child_blocks(s):
        """Child statement-lists a block-stmt owns (each its own chain)."""
        blocks = []
        if isinstance(s, (ast.If, ast.For, ast.AsyncFor, ast.While)):
            blocks += [s.body, s.orelse]
        elif isinstance(s, (ast.With, ast.AsyncWith)):
            blocks.append(s.body)
        elif isinstance(s, ast.Try):
            blocks += [s.body, s.orelse, s.finalbody]
            blocks += [h.body for h in s.handlers]
        return [b for b in blocks if b]

    region: list[ast.stmt] = []
    owner_chain: list[ast.stmt] = []
    for chain in stmt_chains(fn.body):
        touching = [s for s in chain
                    if not (s.end_lineno < start or s.lineno > end)]
        if not touching:
            continue
        fully = [s for s in touching
                 if start <= s.lineno and s.end_lineno <= end]
        if fully != touching:
            # partial containment is legal ONLY when the region descends
            # wholly into exactly one child block of the one partial stmt;
            # touching a header or straddling blocks is misalignment.
            partials = [s for s in touching if s not in fully]
            descend_ok = False
            if not fully and len(partials) == 1:
                for block in _child_blocks(partials[0]):
                    if block[0].lineno <= start and end <= block[-1].end_lineno:
                        descend_ok = True
                        break
            if not descend_ok:
                _fail("REGION_NOT_STATEMENT_ALIGNED")
            continue
        # full claim: the statements must tile [start, end] exactly
        if touching[0].lineno != start or touching[-1].end_lineno != end:
            _fail("REGION_NOT_STATEMENT_ALIGNED")
        idxs = [chain.index(s) for s in touching]
        if idxs != list(range(idxs[0], idxs[-1] + 1)):
            _fail("REGION_NOT_STATEMENT_ALIGNED")   # contiguous only
        region = touching
        owner_chain = chain
        break
    if not region:
        _fail("REGION_NOT_STATEMENT_ALIGNED")

    # control-flow laws
    for s in region:
        cf = _has_blocking_cf(s)
        if cf:
            _fail(cf)

    params, assigned_before = _scope_names(fn)
    outside_bound = set(params) | {k for k, ln in assigned_before.items() if ln < start}

    # shadow analysis: loads bound inside the region are internal, not inputs.
    # Module-level names are NEVER parameters (name resolves at module scope).
    internal: set[str] = set()
    inputs: list[str] = []
    for s in region:
        for name, ln in _loads_of(s):
            if name in internal or name not in outside_bound:
                continue
            if name not in inputs:
                inputs.append(name)
        for name, ln in _stores_of(s):
            internal.add(name)

    # outputs = region writes that are READ later in the enclosing function
    # (siblings after the region, or anything deeper inside enclosing blocks).
    reads_after: set[str] = set()
    for sub in ast.walk(fn):
        if isinstance(sub, ast.stmt) and sub.lineno > end:
            reads_after |= {nm for nm, _ in _loads_of(sub)}
    for s in owner_chain:
        if s.lineno > end:
            reads_after |= {nm for nm, _ in _loads_of(s)}

    outputs: list[str] = []
    for s in region:
        for name, ln in _stores_of(s):
            if name in reads_after and name not in outputs:
                outputs.append(name)

    any_touched = set(inputs) | set(outputs)
    _check_nonlocal_global(fn, any_touched)


    # new name must not collide at module level
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Assign)):
            if getattr(n, "name", None) == new_name:
                _fail("NEW_NAME_COLLIDES:" + new_name)
            if isinstance(n, ast.Assign):
                for nm, _ in _stores_of(n):
                    if nm == new_name:
                        _fail("NEW_NAME_COLLIDES:" + new_name)

    indent = region[0].col_offset
    if indent < 4:
        _fail("REGION_INDENT_LT_4")
    dedent = indent - 4

    region_lines = lines[start - 1:end]
    body_lines = []
    for ln in region_lines:
        s_start = ln[dedent:] if ln[:dedent].strip() == "" else None
        if s_start is None:
            _fail("REGION_INDENT_INCONSISTENT")
        body_lines.append(s_start)
    body_text = "".join(body_lines)
    # validate extraction-compiled parse BEFORE touching the file
    param_text = ", ".join(inputs)
    if outputs:
        ret = "    return " + (outputs[0] if len(outputs) == 1 else ", ".join(outputs)) + "\n"
    else:
        ret = ""
    new_def = f"def {new_name}({param_text}):\n" + body_text + ret
    try:
        ast.parse(new_def)
    except SyntaxError:
        _fail("EXTRACTED_BLOCK_UNPARSEABLE")

    call_lhs = ""
    if len(outputs) == 1:
        call_lhs = outputs[0] + " = "
    elif len(outputs) >= 2:
        call_lhs = ", ".join(outputs) + " = "
    call_line = " " * indent + f"{call_lhs}{new_name}({param_text})\n"

    # where does the new module-level def go? immediately before the OUTERMOST
    # owning module-level def (before its decorators if any)
    owner_top = tree.body
    top_owner = None
    for n in owner_top:
        if n.lineno <= fn.lineno <= (n.end_lineno or fn.lineno) and \
                isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            top_owner = n
            break
    if top_owner is None:
        _fail("SYMBOL_NOT_FOUND:" + qualname)
    insert_at = min([top_owner.lineno] + [dec.lineno for dec in getattr(top_owner, "decorator_list", [])])

    rebuilt = lines[:start - 1] + [call_line] + lines[end:]
    rebuilt = rebuilt[:insert_at - 1] + [new_def + "\n", "\n"] + rebuilt[insert_at - 1:]
    new_text = "".join(rebuilt)
    try:
        ast.parse(new_text)
    except SyntaxError:
        _fail("SPAN_INTEGRITY:rebuilt_module_unparseable")

    module_abs.write_text(new_text, encoding="utf-8")

    evidence = {"run_tests": run_tests}
    gate = "PASS"
    if run_tests:
        import os
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        py_roots = [str(src_abs)]
        if (src_abs / "__init__.py").is_file() and (src_abs.parent == repo or repo in src_abs.parent.parents):
            py_roots.insert(0, str(src_abs.parent))
        if env.get("PYTHONPATH"):
            py_roots.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(py_roots)
        try:
            proc = subprocess.run(verify_argv,
                                  cwd=src_abs, capture_output=True, text=True,
                                  timeout=timeout_s, env=env)
        except subprocess.TimeoutExpired:
            module_abs.write_bytes(original_bytes)
            _fail("TIMEOUT:extraction fully rolled back")
        evidence["pytest_rc"] = proc.returncode
        evidence["pytest_tail"] = proc.stdout.strip().splitlines()[-3:]
        if proc.returncode != 0:
            module_abs.write_bytes(original_bytes)
            _fail("TESTS_RED_AFTER_EDIT:extraction fully rolled back:" +
                  ";".join((proc.stdout.strip().splitlines() or ["<no output>"])[-2:])[:300])
        verified = True
    else:
        verified = False

    artifact = {
        "schema": SCHEMA,
        "source_root": src_rel,
        "module": module_rel,
        "qualname": qualname,
        "extracted_name": new_name,
        "start_line": start,
        "end_line": end,
        "inputs": inputs,
        "outputs": outputs,
        "edit_count": 1,
        "files_edited": [module_rel],
        "verification": evidence,
        "gate": gate,
        "law": ("region lifts to a module-level def with inferred params/outs; "
                "call replaces the region at identical indent; new def inserted "
                "before the owning module-level statement (decorators included); "
                "named tests run post-edit and a red suite rolls back every byte"),
        "complete": True,
    }
    out_abs.parent.mkdir(parents=True, exist_ok=True)
    text_out = json.dumps(artifact, indent=2, ensure_ascii=False) + "\n"
    out_abs.write_text(text_out, encoding="utf-8")
    return {
        "adapter": "python_refactor_extract_function",
        "extracted_name": new_name,
        "inputs": inputs,
        "outputs": outputs,
        "edit_count": 1,
        "files_edited": [module_rel],
        "gate": gate,
        "complete": True,
        "output_path": out_rel,
        "output_sha256": _sha256(text_out.encode("utf-8")),
        "output_verified": json.loads(out_abs.read_text(encoding="utf-8")) == artifact,
        "verified": verified,
    }


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--source_root", required=True)
    p.add_argument("--module", required=True)
    p.add_argument("--qualname", required=True)
    p.add_argument("--new_name", required=True)
    p.add_argument("--start_line", type=int, required=True)
    p.add_argument("--end_line", type=int, required=True)
    p.add_argument("--output_path", required=True)
    p.add_argument("--run_tests", nargs="*", default=None)
    p.add_argument("--timeout_s", type=int, default=300)
    ns = p.parse_args()
    print(json.dumps(run(vars(ns), Path.cwd()), indent=2, sort_keys=True))
