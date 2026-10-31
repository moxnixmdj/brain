# PROJECT_BRAIN
"""python.source.add_function.v1 -- write the function the sentence states,
wire it into the package, and prove it with a test that is green.

The request this serves was unserved, and it is the plainest kind of software
work there is:

    "Add a function total_cents(item) to app/models.py that returns
     price_cents * qty, export it from app/__init__.py, and add a test for it
     in tests/test_total.py"

Everything the machine needs is IN that sentence: the name, the parameter list,
the expression the function returns, the module it goes into, the module that
re-exports it and the file the test belongs in.  Nothing here is invented --
the one inference is forced by the sentence's own vocabulary and is proved
against the module's own AST:

* FREE NAMES ARE THE PARAMETER'S ATTRIBUTES.  ``price_cents`` and ``qty`` are
  not parameters, not builtins and not globals of the module; they are the
  attributes the module's class assigns to itself.  The body therefore reads
  them off the parameter that the stated signature supplies -- and if a free
  name is NOT an attribute of exactly one class in that module, the adapter
  refuses rather than writing a function that would raise at call time.
* THE TEST IS DERIVED FROM THE SPEC, NOT FROM THE IMPLEMENTATION.  Sample
  values are bound to the same names and the stated expression is evaluated
  with them; the emitted assertion is that literal.  A test that called the new
  function and compared it to itself would be the "output_verified without an
  observed effect" defect in test form.
* THE SUITE DECIDES.  After the three writes the stated test directory is run
  with ``unittest discover``; a red suite restores every byte of every file and
  refuses TESTS_RED_AFTER_EDIT.

Refusals are named: UNSUPPORTED_CONSTRUCTOR, UNRESOLVED_FREE_NAME,
AMBIGUOUS_ATTRIBUTE_OWNER, FUNCTION_ALREADY_DEFINED, BAD_EXPRESSION,
NO_TEST_PATH_STATED, TESTS_RED_AFTER_EDIT (+full rollback).

Inputs (kwargs, repo-confined):
  source_root     tree to edit IN PLACE
  module          posix path of the module that receives the function
  symbol          function name, e.g. "total_cents"
  params          list of parameter names, e.g. ["item"]
  body            the returned expression, verbatim, e.g. "price_cents * qty"
  export_module   package __init__ the sentence says to export it from
  test_paths      the test file(s) the sentence names
  output_path     summary artifact (registry result_fields mirror)
  python_executable / timeout_s

result_fields: adapter, module, symbol, params, body, export_module, test_path,
free_names_resolved, gate, complete, suite_rc, output_path, output_sha256,
output_verified, verified.
"""

from __future__ import annotations

import ast
import builtins
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_SOURCE_ADD_FUNCTION_V1"
CAPABILITY = "python.source.add_function.v1"
_SAMPLES = [2, 3, 5, 7, 11, 13, 17, 19]


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


def _resolve_under(repo: Path, src_abs: Path, rel: str, must_exist: bool = False) -> Path:
    """Resolve a stated path under the tree root, then under source_root.

    Two conventions arrive here and both are evidence: a slot derived from the
    sentence is repository-relative ("app/models.py" beside source_root "app"),
    while a caller that already confined itself to a tree passes it
    source-relative.  Whichever file EXISTS wins; a file that does not exist yet
    (the test this capability is asked to create) is placed beside the module the
    sentence named, never guessed into a second tree.
    """
    candidates = []
    for base in (repo, src_abs):
        candidate = (base / rel).resolve()
        if repo not in candidate.parents and candidate != repo:
            continue
        if candidate.exists():
            return candidate
        candidates.append(candidate)
    # A path that does not exist yet is placed where its own directory already
    # exists -- repository-relative first, because that is the form a derived
    # slot arrives in.
    for candidate in candidates:
        if candidate.parent.is_dir():
            return candidate
    return candidates[0] if candidates else (repo / rel).resolve()


def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _class_attributes(tree: ast.AST) -> dict[str, dict[str, str]]:
    """{class: {attribute: constructor-parameter-that-assigns-it}} for the module.

    ``self.price_cents = price_cents`` in ``__init__`` is the module saying which
    name supplies the attribute; an attribute assigned from anything else maps to
    "" and can only be set after construction.
    """
    out: dict[str, dict[str, str]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        attrs: dict[str, str] = {}
        for fn in node.body:
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            first = fn.args.args[0].arg if fn.args.args else ""
            for sub in ast.walk(fn):
                if not isinstance(sub, ast.Assign):
                    continue
                if not (isinstance(sub.value, ast.Name) and sub.value.id in
                        [a.arg for a in fn.args.args]):
                    continue
                for target in sub.targets:
                    if (isinstance(target, ast.Attribute)
                            and isinstance(target.value, ast.Name)
                            and target.value.id == first):
                        attrs[target.attr] = sub.value.id
        out[node.name] = attrs
    return out


def _ctor_parameters(tree: ast.AST, class_name: str) -> list[tuple[str, bool]]:
    """(parameter, has_default) in declaration order for the class's __init__."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for fn in node.body:
                if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) and fn.name == "__init__":
                    args = [a for a in fn.args.args if a.arg != "self"]
                    required = len(args) - len(fn.args.defaults)
                    return [(a.arg, i >= required) for i, a in enumerate(args)]
    return []


def run(args: dict, root: Path) -> dict:
    a = dict(args or {})
    repo = Path(root).resolve()
    src_rel = str(a.get("source_root") or ".")
    src_abs = _safe_path(repo, src_rel, must_exist=True)
    module_rel = str(a.get("module") or "")
    export_rel = str(a.get("export_module") or "")
    symbol = str(a.get("symbol") or a.get("function_name") or "")
    params = a.get("params") or []
    if isinstance(params, str):
        params = [p.strip() for p in params.split(",") if p.strip()]
    params = [str(p) for p in params]
    body = str(a.get("body") or a.get("expression") or "").strip().rstrip(".")
    tests = a.get("test_paths") or []
    if isinstance(tests, str):
        tests = [tests]
    python_exe = str(args.get("python_executable") or sys.executable)
    timeout_s = int(args.get("timeout_s") or 300)

    if not symbol.isidentifier():
        _fail("BAD_FUNCTION_NAME:" + symbol)
    if not params or not all(p.isidentifier() for p in params):
        _fail("BAD_SIGNATURE:" + repr(params))
    if not body:
        _fail("MISSING_BODY")
    try:
        expr = ast.parse(body, mode="eval").body
    except SyntaxError as exc:  # noqa: BLE001
        _fail("BAD_EXPRESSION:%s" % str(exc)[:120])
    if not tests:
        _fail("NO_TEST_PATH_STATED")
    mod_path = _resolve_under(repo, src_abs, module_rel)
    if not mod_path.exists():
        _fail("PATH_MISSING:" + module_rel)
    module_rel = mod_path.relative_to(repo).as_posix()
    test_rel = str(tests[0])
    test_path = _resolve_under(repo, src_abs, test_rel)
    # THE TREE THE SUITE RUNS IN, and the module's name inside it.  A name spelled
    # against the repository does not import from the fixture root, and a test
    # that cannot import what it tests is a rollback, not a feature.
    base = Path(os.path.commonpath([str(mod_path.parent), str(test_path.parent)]))
    import_target = ".".join(mod_path.relative_to(base).with_suffix("").parts)
    package = ".".join(mod_path.relative_to(base).parent.parts)
    text = mod_path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    if any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == symbol
           for n in ast.walk(tree)):
        _fail("FUNCTION_ALREADY_DEFINED:" + symbol)

    attrs_by_class = _class_attributes(tree)
    free = sorted({n.id for n in ast.walk(expr) if isinstance(n, ast.Name)}
                  - set(params) - set(dir(builtins)) - {"True", "False", "None"})
    owners: dict[str, list[str]] = {}
    for name in free:
        owners[name] = [cls for cls, attrs in attrs_by_class.items() if name in attrs]
    unresolved = [n for n in free if not owners[n]]
    if unresolved:
        _fail("UNRESOLVED_FREE_NAME:" + ",".join(unresolved))
    ambiguous = [n for n in free if len(owners[n]) > 1]
    if ambiguous:
        _fail("AMBIGUOUS_ATTRIBUTE_OWNER:" + ",".join(ambiguous))
    owner = owners[free[0]][0] if free else ""
    if free and any(owners[n][0] != owner for n in free):
        _fail("ATTRIBUTES_SPAN_TWO_CLASSES")
    if len(params) != 1:
        _fail("UNSUPPORTED_CONSTRUCTOR:the sentence names %d parameters" % len(params))
    param = params[0]

    # the body the sentence states, with each free name read off the parameter
    rendered = ast.unparse(expr)
    for name in sorted(free, key=len, reverse=True):
        rendered = _replace_name(rendered, name, "%s.%s" % (param, name))

    # ---- the three writes, byte-exact and reversible -----------------------
    originals: dict[Path, bytes | None] = {mod_path: mod_path.read_bytes()}
    fn_text = "\n\ndef %s(%s):\n    return %s\n" % (symbol, ", ".join(params), rendered)
    if not text.endswith("\n"):
        fn_text = "\n" + fn_text
    mod_path.write_text(text + fn_text, encoding="utf-8")

    written: list[Path] = [mod_path]
    if export_rel:
        exp_path = _resolve_under(repo, src_abs, export_rel)
        exp_orig = exp_path.read_bytes() if exp_path.exists() else None
        originals[exp_path] = exp_orig
        exp_text = exp_orig.decode("utf-8") if exp_orig is not None else ""
        stem = mod_path.stem
        line = "from %s.%s import %s\n" % (package, stem, symbol) if package \
            else "from %s import %s\n" % (stem, symbol)
        if line.strip() not in exp_text:
            exp_path.parent.mkdir(parents=True, exist_ok=True)
            exp_path.write_text(exp_text + line, encoding="utf-8")
            written.append(exp_path)

    # sample values, and the expectation the SENTENCE states under them
    samples = {n: _SAMPLES[i % len(_SAMPLES)] for i, n in enumerate(free)}
    expected = eval(compile(ast.Expression(expr), "<stated>", "eval"),  # noqa: S307 - literals
                    {"__builtins__": {}}, dict(samples))
    # CONSTRUCTION.  The sentence states which attributes the function reads and
    # nothing about the class's other constructor arguments -- so supplying made
    # up values for them (a name, an id) would be inventing an input the caller
    # never gave.  An instance is therefore made without running __init__ and
    # given exactly the attributes the specification names; if the class refuses
    # that (slots, read-only properties), the adapter says so instead of guessing.
    test_orig = test_path.read_bytes() if test_path.exists() else None
    originals[test_path] = test_orig
    body_lines = ["        item = object.__new__(%s)" % owner]
    body_lines += ["        item.%s = %r" % (n, samples[n]) for n in free]
    body_lines.append("        self.assertEqual(%s(item), %r)" % (symbol, expected))
    test_text = (
        "import unittest\n\n"
        "from %s import %s\n\n\n"
        "class Test%s(unittest.TestCase):\n"
        "    def test_%s_returns_what_the_specification_states(self):\n%s\n"
    ) % (import_target, ", ".join([n for n in (owner, symbol) if n]),
         symbol.title().replace("_", ""), symbol, "\n".join(body_lines))
    if test_orig is not None:
        test_text = test_orig.decode("utf-8").rstrip("\n") + "\n\n\n" + test_text
    test_path.parent.mkdir(parents=True, exist_ok=True)
    test_path.write_text(test_text, encoding="utf-8")
    written.append(test_path)

    # ---- the verdict: run the stated suite, and call the function ----------
    tests_dir = test_path.parent.name
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(base))
    evidence: dict = {"suite": [], "call": None}
    ok = True
    cp = subprocess.run([python_exe, "-m", "unittest", "discover", "-s", tests_dir, "-t", "."],
                        cwd=str(base), capture_output=True, text=True, timeout=timeout_s, env=env)
    evidence["suite"] = [cp.returncode, (cp.stdout + cp.stderr).strip().splitlines()[-2:]]
    ok = ok and cp.returncode == 0
    probe_code = ("import json\nfrom %s import %s\n"
                  "print(json.dumps(%s(type('I',(),%r)())))\n"
                  % (import_target, symbol, symbol, dict(samples)))
    cp2 = subprocess.run([python_exe, "-c", probe_code], cwd=str(base),
                         capture_output=True, text=True, timeout=timeout_s, env=env)
    evidence["call"] = [cp2.returncode, cp2.stdout.strip()[-40:], cp2.stderr.strip()[-120:]]
    ok = ok and cp2.returncode == 0 and cp2.stdout.strip() == json.dumps(expected)
    if not ok:
        for path, original in originals.items():
            if original is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(original)
        _fail("TESTS_RED_AFTER_EDIT:all writes rolled back:%s" % json.dumps(evidence)[:300])

    artifact = {
        "schema": SCHEMA,
        "source_root": src_rel,
        "module": module_rel,
        "symbol": symbol,
        "params": params,
        "body": rendered,
        "export_module": export_rel,
        "test_path": test_rel,
        "free_names_resolved": {n: "%s.%s" % (owner, n) for n in free},
        "expected_under_samples": expected,
        "verification": evidence,
        "gate": "PASS",
        "law": ("the stated signature and expression are written verbatim; free "
                "names are proved to be the owning class's attributes; the test's "
                "expectation is the stated expression evaluated on sample values; "
                "a red suite rolls every write back"),
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
    payload = json.dumps(artifact, indent=2, ensure_ascii=False) + "\n"
    out_abs.write_text(payload, encoding="utf-8")
    out_verified = json.loads(out_abs.read_text(encoding="utf-8")) == artifact

    return {
        "adapter": "python_source_add_function",
        "module": module_rel,
        "symbol": symbol,
        "params": len(params),
        "body": rendered,
        "export_module": export_rel,
        "test_path": test_rel,
        "free_names_resolved": len(free),
        "suite_rc": evidence["suite"][0],
        "gate": "PASS",
        "complete": True,
        "output_path": out_rel,
        "output_sha256": _sha256(payload.encode("utf-8")),
        "output_verified": out_verified,
        "verified": True,
    }


def _replace_name(source: str, name: str, replacement: str) -> str:
    """Replace a bare identifier, never a substring of a longer one."""
    out, i = [], 0
    while True:
        j = source.find(name, i)
        if j < 0:
            out.append(source[i:])
            return "".join(out)
        before = source[j - 1] if j else ""
        after = source[j + len(name)] if j + len(name) < len(source) else ""
        if (before.isalnum() or before == "_" or before == ".") or (after.isalnum() or after == "_"):
            out.append(source[i:j + len(name)])
        else:
            out.append(source[i:j] + replacement)
        i = j + len(name)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--source_root", required=True)
    p.add_argument("--module", required=True)
    p.add_argument("--symbol", required=True)
    p.add_argument("--params", nargs="*", default=[])
    p.add_argument("--body", required=True)
    p.add_argument("--export_module", default="")
    p.add_argument("--test_paths", nargs="*", default=[])
    p.add_argument("--output_path", required=True)
    ns = p.parse_args()
    print(json.dumps(run(vars(ns), Path.cwd()), indent=2, sort_keys=True))
