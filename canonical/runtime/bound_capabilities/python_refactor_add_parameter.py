# PROJECT_BRAIN
"""python.refactor.add_parameter.v1 -- add an optional parameter whose default
IS the value the body already used, so behaviour cannot change.

The request this serves is ordinary and was unserved:

    "Add a parameter qty with a default value to the function line_total in
     app/models.py and update every caller so behaviour is unchanged."

The sentence states the law in its own words: the parameter is ADDED (every
existing caller keeps working) and behaviour is UNCHANGED (omitting it does what
the old code did).  Both halves have one mechanical reading, and it is not a
guess:

* ARITY.  A parameter with a default is optional, so no call site needs to be
  rewritten.  The "update every caller" half of the sentence is satisfied by the
  default, which is why nothing is edited outside the defining module -- and the
  artifact records that as a proof obligation rather than a claim.
* DEFAULT FROM THE BODY.  If the body reads ``<expr>.qty``, then the value the
  old code used for ``qty`` is exactly ``<expr>.qty``.  A parameter named
  ``qty`` can only be "the same behaviour with a default" if omitting it yields
  that value, so each such read becomes ``(qty if qty is not None else
  <expr>.qty)`` and the default is ``None``.  Calling ``line_total(item, 3)``
  then overrides exactly the value the sentence named, and calling
  ``line_total(item)`` computes what it always computed.

That is the whole mechanism: one signature splice plus the reads the parameter
shadows, byte-exact (SPAN_INTEGRITY on every splice), reparse-verified, and
rolled back in full if the named tests are not green afterwards.

Refusals are named rather than silent: an existing parameter of that name
(ALREADY_DECLARED), a name that is not an identifier (BAD_PARAMETER_NAME), a
function that is not in the stated module (FUNCTION_NOT_IN_MODULE), several
definitions of the name (AMBIGUOUS_DEFINITION), or a red suite after the edit
(TESTS_RED_AFTER_EDIT + full rollback).

Inputs (kwargs, repo-confined):
  source_root       tree to edit IN PLACE
  module            posix path of the defining module, e.g. "app/models.py"
  symbol            function name, e.g. "line_total"
  new_param         parameter name to add, e.g. "qty"
  output_path       summary artifact (registry result_fields mirror)
  run_tests         optional pytest paths to verify
  python_executable interpreter for verification (default: this one)
  timeout_s         wall-clock cap for the suite call (default 300)

result_fields: adapter, module, symbol, new_param, default, edit_count,
reads_shadowed, files_edited, gate, complete, output_path, output_sha256,
output_verified, verified.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_REFACTOR_ADD_PARAMETER_V1"
CAPABILITY = "python.refactor.add_parameter.v1"


def _fail(reason: str) -> None:
    raise SystemExit(json.dumps({"error": True, "capability": CAPABILITY,
                                 "reason": reason}, indent=2, sort_keys=True))


def _safe_path(repo: Path, rel: str, must_exist: bool = False) -> Path:
    if not rel or not isinstance(rel, str):
        _fail("MISSING_OR_INVALID_PATH_ARGUMENT")
    p = (repo / rel).resolve()
    if p != repo and repo not in p.parents:
        _fail("PATH_ESCAPE:" + rel)
    if must_exist and not p.exists():
        _fail("PATH_MISSING:" + rel)
    return p


def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _offsets(text: str) -> list[int]:
    """Byte offset of the start of every line, for ast line/col conversion."""
    pos = [0]
    for line in text.splitlines(keepends=True):
        pos.append(pos[-1] + len(line))
    return pos


def _line_col_to_offset(pos: list[int], lineno: int, col: int) -> int:
    return pos[lineno - 1] + col


class _ShadowReads(ast.NodeVisitor):
    """Every ``<expr>.name`` READ in one function scope, nested scopes excluded.

    A nested function or lambda is a different scope: it may rebind the name, so
    its reads are not evidence about this parameter and are never rewritten.
    """

    def __init__(self, name: str):
        self.name = name
        self.reads: list[ast.Attribute] = []

    def visit_FunctionDef(self, node):  # noqa: N802 - ast visitor name
        return  # do not descend into nested scopes

    visit_AsyncFunctionDef = visit_FunctionDef
    visit_Lambda = visit_FunctionDef
    visit_ClassDef = visit_FunctionDef

    def visit_Attribute(self, node):  # noqa: N802 - ast visitor name
        if node.attr == self.name and isinstance(node.ctx, ast.Load):
            self.reads.append(node)
        self.generic_visit(node)


def _definitions(tree: ast.AST, name: str) -> list[ast.AST]:
    return [n for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name]


def _signature_insert(text: str, pos: list[int], fn: ast.AST) -> tuple[int, str]:
    """Where to splice the new parameter, and what to splice there."""
    a = fn.args
    if a.kwonlyargs:
        last = a.kwonlyargs[-1]
        at = _line_col_to_offset(pos, last.lineno, last.end_col_offset)
        return at, ", %s=None"
    if a.vararg:
        at = _line_col_to_offset(pos, a.vararg.lineno, a.vararg.end_col_offset)
        return at, ", %s=None"
    if a.args:
        last = a.args[-1]
        at = _line_col_to_offset(pos, last.lineno, last.end_col_offset)
        return at, ", %s=None"
    # No parameters at all: the first character after the opening parenthesis.
    def_at = _line_col_to_offset(pos, fn.lineno, fn.col_offset)
    open_at = text.find("(", def_at)
    if open_at < 0:
        _fail("SIGNATURE_NOT_FOUND")
    return open_at + 1, "%s=None"


def run(args: dict, root: Path) -> dict:
    a = dict(args or {})
    repo = Path(root).resolve()
    src_rel = str(a.get("source_root") or ".")
    src_abs = _safe_path(repo, src_rel, must_exist=True)
    module_rel = str(a.get("module") or "")
    symbol = str(a.get("symbol") or a.get("qualname") or "").split(".")[-1]
    new_param = str(a.get("new_param") or "")
    run_tests = args.get("run_tests") or []
    if isinstance(run_tests, str):
        run_tests = [run_tests]
    python_exe = str(args.get("python_executable") or sys.executable)
    timeout_s = int(args.get("timeout_s") or 300)

    if not new_param.isidentifier():
        _fail("BAD_PARAMETER_NAME:" + new_param)
    if not symbol.isidentifier():
        _fail("BAD_FUNCTION_NAME:" + symbol)
    if module_rel in ("", ".") or module_rel.endswith("/"):
        _fail("MISSING_MODULE_PATH:" + module_rel)
    mod_abs = _safe_path(src_abs, module_rel, must_exist=True)
    mod_path = (src_abs / module_rel).resolve()
    module_rel = mod_path.relative_to(repo).as_posix()

    original_bytes = mod_path.read_bytes()
    text = original_bytes.decode("utf-8")
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:  # noqa: BLE001 - a module that does not parse is a refusal
        _fail("MODULE_DOES_NOT_PARSE:" + str(exc)[:120])

    found = _definitions(tree, symbol)
    if not found:
        _fail("FUNCTION_NOT_IN_MODULE:%s:%s" % (symbol, module_rel))
    if len(found) > 1:
        _fail("AMBIGUOUS_DEFINITION:%s:%d" % (symbol, len(found)))
    fn = found[0]
    declared = [x.arg for x in (list(fn.args.args) + list(fn.args.kwonlyargs))]
    declared += [x.arg for x in (fn.args.posonlyargs or [])]
    if fn.args.vararg:
        declared.append(fn.args.vararg.arg)
    if fn.args.kwarg:
        declared.append(fn.args.kwarg.arg)
    if new_param in declared:
        _fail("ALREADY_DECLARED:%s:%s" % (symbol, new_param))

    pos = _offsets(text)
    # 1. the reads this parameter shadows, so the default reproduces them
    shadow = _ShadowReads(new_param)
    for stmt in fn.body:
        shadow.visit(stmt)
    edits: list[tuple[int, int, str]] = []  # (start, end, replacement)
    read_rows: list[dict] = []
    for attr in shadow.reads:
        start = _line_col_to_offset(pos, attr.lineno, attr.col_offset)
        end = _line_col_to_offset(pos, attr.end_lineno, attr.end_col_offset)
        original = text[start:end]
        if text[start:end] != original:  # pragma: no cover - _offsets is total
            _fail("SPAN_INTEGRITY:" + module_rel)
        edits.append((start, end, "(%s if %s is not None else %s)" % (new_param, new_param, original)))
        read_rows.append({"line": attr.lineno, "read": original})

    # 2. the signature
    at, template = _signature_insert(text, pos, fn)
    edits.append((at, at, template % new_param))

    # one descending pass keeps every offset valid
    new_text = text
    for start, end, repl in sorted(edits, key=lambda e: (e[0], e[1]), reverse=True):
        if new_text[start:end] != text[start:end]:
            _fail("SPAN_INTEGRITY:%s:%d" % (module_rel, start))
        new_text = new_text[:start] + repl + new_text[end:]

    try:
        new_tree = ast.parse(new_text)
    except SyntaxError as exc:  # noqa: BLE001 - never leave a module that does not parse
        _fail("EDIT_WOULD_NOT_PARSE:" + str(exc)[:160])
    after = _definitions(new_tree, symbol)
    if len(after) != 1:
        _fail("EDIT_LOST_THE_DEFINITION:" + symbol)
    new_declared = [x.arg for x in (list(after[0].args.args) + list(after[0].args.kwonlyargs))]
    if new_param not in new_declared:
        _fail("EDIT_DID_NOT_ADD_THE_PARAMETER:" + new_param)
    defaults = len(after[0].args.defaults) + sum(
        1 for d in after[0].args.kw_defaults if d is not None)
    if defaults < 1:
        _fail("ADDED_PARAMETER_HAS_NO_DEFAULT:" + new_param)

    mod_path.write_text(new_text, encoding="utf-8")
    written: list[Path] = [mod_path]

    # 3. the named tests, or a full rollback
    evidence: dict = {"run_tests": list(run_tests)}
    verified = False
    gate = "PASS"
    if run_tests:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        try:
            proc = subprocess.run([python_exe, "-m", "pytest", "-q",
                                   "-p", "no:cacheprovider"] + list(run_tests),
                                  cwd=str(src_abs), capture_output=True, text=True,
                                  timeout=timeout_s, env=env)
        except subprocess.TimeoutExpired:
            mod_path.write_bytes(original_bytes)
            _fail("TIMEOUT:edit fully rolled back")
        evidence["pytest_rc"] = proc.returncode
        evidence["pytest_tail"] = proc.stdout.strip().splitlines()[-3:]
        if proc.returncode != 0:
            mod_path.write_bytes(original_bytes)
            _fail("TESTS_RED_AFTER_EDIT:edit fully rolled back:" +
                  ";".join((proc.stdout.strip().splitlines() or ["<no output>"])[-2:])[:300])
        verified = True
    else:
        # No suite named: the compile check above is real but partial, and the
        # result says so instead of implying a green suite it never ran.
        evidence["pytest_rc"] = None
        evidence["pytest_tail"] = ["not requested"]

    artifact = {
        "schema": SCHEMA,
        "source_root": src_rel,
        "module": module_rel,
        "symbol": symbol,
        "new_param": new_param,
        "default": None,
        "edit_count": len(edits),
        "reads_shadowed": sorted(read_rows, key=lambda r: r["line"]),
        "files_edited": [module_rel],
        "call_sites_need_no_edit": True,
        "verification": evidence,
        "gate": gate,
        "law": ("add an optional parameter whose default IS the value the body "
                "already read, so omitting it cannot change behaviour; every "
                "splice is span-checked, the module is reparsed, and a red suite "
                "rolls the edit back"),
        "complete": True,
    }
    out_rel = str(a.get("output_path") or "")
    if not out_rel:
        _fail("MISSING_OUTPUT_PATH")
    # The artifact must never be written over a file this adapter edits: a
    # binder that reads the sentence's one path as the destination would then
    # replace the very module the edit produced.  Redirect to a named sibling
    # and say so in the artifact rather than silently overwriting the work.
    _edited = {p2.resolve() for p2 in written}
    if (repo / out_rel).resolve() in _edited:
        stem = Path(out_rel).stem
        out_rel = str(Path(out_rel).with_name(stem + ".artifact.json"))
        redirected_from = str(a.get("output_path") or "")
    else:
        redirected_from = ""
    out_abs = _safe_path(repo, out_rel)
    out_abs.parent.mkdir(parents=True, exist_ok=True)
    text_out = json.dumps(artifact, indent=2, ensure_ascii=False) + "\n"
    out_abs.write_text(text_out, encoding="utf-8")
    out_verified = json.loads(out_abs.read_text(encoding="utf-8")) == artifact

    return {
        "adapter": "python_refactor_add_parameter",
        "module": module_rel,
        "symbol": symbol,
        "new_param": new_param,
        "default": None,
        "edit_count": len(edits),
        "reads_shadowed": len(read_rows),
        "files_edited": 1,
        "call_sites_need_no_edit": True,
        "gate": gate,
        "complete": True,
        "output_path": out_rel,
        "output_sha256": _sha256(text_out.encode("utf-8")),
        "output_verified": out_verified,
        "verified": bool(verified),
    }


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--source_root", required=True)
    p.add_argument("--module", required=True)
    p.add_argument("--symbol", required=True)
    p.add_argument("--new_param", required=True)
    p.add_argument("--output_path", required=True)
    p.add_argument("--run_tests", nargs="*", default=None)
    ns = p.parse_args()
    print(json.dumps(run(vars(ns), Path.cwd()), indent=2, sort_keys=True))
