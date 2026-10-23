"""Build / check MODULE_INVOCATION_EVIDENCE_V1.json: which inventory functions are invocable live.

Every function of every inventory module is considered.  A module is loadable when it imports
inside the guarded child (brain_module_invoke_runner_v1: audit hook refusing writes, deletes,
subprocesses and sockets, memory/CPU limits); an import that tries any of those is refused.

Each public function of a loadable module then gets exactly one tier, judged PER TEST CASE from
JUnit XML of a real pytest run (a failing test about some OTHER function no longer blocks it):

  TEST_EVIDENCED       >= 1 passing test case names it, and no failing test case names it
  READ_ONLY_UNTESTED   no test case names it; callable read-only, every result says so
  (refused)            a failing test case names it -> listed under ``refused`` as backlog

The module and every test file holding its passing evidence are pinned by sha256;
``brain_module_invoke_v1`` re-checks the pins on every call.

Usage:
  python3 -m canonical.runtime.module_invocation_evidence_v1 --list-tests > tests.txt
  python3 -m pytest -c /dev/null --rootdir . --junitxml run.xml $(cat tests.txt)
  python3 -m canonical.runtime.module_invocation_evidence_v1 --write --junit run.xml
  python3 -m canonical.runtime.module_invocation_evidence_v1 --register
  python3 -m canonical.runtime.module_invocation_evidence_v1 --check      # fast, no test rerun
"""
from __future__ import annotations

import argparse
import ast
import collections
import concurrent.futures as cf
import hashlib
import json
import pathlib
import platform
import re
import sys
import xml.etree.ElementTree as ET
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime.bound_capabilities import brain_module_invoke_v1 as invoker  # noqa: E402

INVENTORY_REL = "canonical/runtime/AUTONOMOUS_CAPABILITY_EXTENDED_REGISTRY_V1.json"
EVIDENCE_REL = invoker.EVIDENCE_REL
SCHEMA = "PROJECT_BRAIN_MODULE_INVOCATION_EVIDENCE_V1"
TESTED, UNTESTED = invoker.TIER_TESTED, invoker.TIER_UNTESTED
_SKIP_PARTS = {".git", "tmp", "__pycache__", "node_modules"}
# The invoker's own tests use admitted modules as samples; they are not evidence FOR those modules
# (and counting them would make the evidence depend on a test that pins the evidence).
NOT_EVIDENCE_TESTS = frozenset({"canonical/tests/test_brain_module_invoke_v1.py",
                                "canonical/tests/test_brain_module_solve_v1.py"})
_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory_paths(root: pathlib.Path = ROOT) -> list[str]:
    caps = json.loads((root / INVENTORY_REL).read_text(encoding="utf-8"))["capabilities"]
    return sorted({v["source"]["path"] for v in caps.values()
                   if v.get("status") != "VERIFIED_BOUND_CAPABILITY" and (v.get("source") or {}).get("path")})


def _is_test(rel: str) -> bool:
    name = pathlib.PurePosixPath(rel).name
    return "/tests/" in rel or name.startswith("test_") or name.endswith("_test.py") or name == "conftest.py"


def test_files(root: pathlib.Path = ROOT) -> dict[str, str]:
    out = {}
    for p in sorted(root.rglob("test_*.py")):
        rel = p.relative_to(root)
        if _SKIP_PARTS & set(rel.parts) or rel.as_posix() in NOT_EVIDENCE_TESTS:
            continue
        out[rel.as_posix()] = p.read_text(encoding="utf-8", errors="ignore")
    return out


def _first_line(doc: str | None) -> str:
    return (doc or "").strip().splitlines()[0][:200] if (doc or "").strip() else ""


def _signature(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, Any]:
    a = fn.args
    positional = a.posonlyargs + a.args
    n_req = len(positional) - len(a.defaults)
    required = [x.arg for x in positional[:n_req]] + [x.arg for x, d in zip(a.kwonlyargs, a.kw_defaults) if d is None]
    return {"params": [x.arg for x in positional + a.kwonlyargs], "required": required, "var_kw": a.kwarg is not None}


def static_module(root: pathlib.Path, rel: str) -> tuple[str | None, dict[str, Any]]:
    """(exclusion reason or None, {"doc", "functions": {name: {signature, doc}}}) without importing."""
    if _is_test(rel):
        return "IS_A_TEST", {}
    try:
        tree = ast.parse((root / rel).read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError, ValueError):
        return "UNPARSEABLE_OR_MISSING", {}
    funcs = {n.name: {"signature": _signature(n), "doc": _first_line(ast.get_docstring(n))}
             for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and not n.name.startswith("_")}
    if not funcs:
        return "NO_PUBLIC_FUNCTION", {}
    return None, {"doc": _first_line(ast.get_docstring(tree)), "functions": funcs}


class TestIndex:
    """Inverted word index over test files so reference lookup is not O(modules x tests)."""

    def __init__(self, tests: dict[str, str]):
        self.tests = tests
        self.by_word: dict[str, set[str]] = collections.defaultdict(set)
        for t, s in tests.items():
            for w in set(_WORD.findall(s)):
                self.by_word[w].add(t)

    def referencing(self, rel: str) -> list[str]:
        stem = pathlib.PurePosixPath(rel).stem
        dotted = rel[:-3].replace("/", ".")
        imp = re.compile(r"\b(?:import|from)\s+[\w.]*\b%s\b" % re.escape(stem))
        quoted = ('"%s"' % stem, "'%s'" % stem, '"%s.py"' % stem, "'%s.py'" % stem)
        out = []
        for t in self.by_word.get(stem, ()):
            s = self.tests[t]
            if dotted in s or rel in s or imp.search(s) or any(q in s for q in quoted):
                out.append(t)
        return sorted(out)


def case_references(source: str) -> dict[tuple[str | None, str], set[str]]:
    """{(class or None, test function): identifiers it uses, incl. its class setUp and its fixtures}."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}

    def names(node: ast.AST) -> set[str]:
        out = set()
        for x in ast.walk(node):
            if isinstance(x, ast.Name):
                out.add(x.id)
            elif isinstance(x, ast.Attribute):
                out.add(x.attr)
            elif isinstance(x, ast.Constant) and isinstance(x.value, str) and x.value.isidentifier():
                out.add(x.value)
        return out

    module_funcs = {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    refs: dict[tuple[str | None, str], set[str]] = {}

    def with_fixtures(fn) -> set[str]:
        got = names(fn)
        for arg in fn.args.args:
            if arg.arg in module_funcs and module_funcs[arg.arg] is not fn:
                got |= names(module_funcs[arg.arg])
        return got

    for name, fn in module_funcs.items():
        if name.startswith("test"):
            refs[(None, name)] = with_fixtures(fn)
    for cls in (n for n in tree.body if isinstance(n, ast.ClassDef)):
        methods = {m.name: m for m in cls.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))}
        shared = set().union(*(names(methods[m]) for m in ("setUp", "setUpClass", "setup_method") if m in methods))
        for mname, m in methods.items():
            if mname.startswith("test"):
                refs[(cls.name, mname)] = with_fixtures(m) | shared
    return refs


def _file_of(classname: str, file_attr: str | None, root: pathlib.Path) -> tuple[str | None, str | None]:
    parts = classname.split(".")
    for n in range(len(parts), 0, -1):
        rel = "/".join(parts[:n]) + ".py"
        if (root / rel).is_file():
            return rel, (parts[n] if n < len(parts) else None)
    return (pathlib.PurePosixPath(file_attr).as_posix() if file_attr else None), None


def junit_cases(paths: list[str], root: pathlib.Path = ROOT) -> dict[str, list[tuple[str | None, str, str]]]:
    """{test file: [(class, test name, PASS|FAIL|SKIP)]}.  When several runs cover a file the LATER run wins."""
    per: dict[str, list[tuple[str | None, str, str]]] = {}
    for xml in paths:
        this: dict[str, list] = collections.defaultdict(list)
        for case in ET.parse(xml).getroot().iter("testcase"):
            rel, cls = _file_of(case.get("classname", ""), case.get("file"), root)
            if rel is None:
                continue
            kinds = {child.tag for child in case}
            state = "FAIL" if kinds & {"failure", "error"} else "SKIP" if "skipped" in kinds else "PASS"
            this[rel].append((cls, re.sub(r"\[.*\]$", "", case.get("name", "")), state))
        per.update(this)
    return per


def statics(root: pathlib.Path = ROOT) -> tuple[dict[str, dict[str, Any]], collections.Counter]:
    reasons: collections.Counter = collections.Counter()
    out = {}
    for rel in inventory_paths(root):
        reason, info = static_module(root, rel)
        if reason:
            reasons[reason] += 1
        else:
            out[rel] = info
    return out, reasons


def build(junit: list[str], root: pathlib.Path = ROOT) -> dict[str, Any]:
    mods, reasons = statics(root)
    index = TestIndex(test_files(root))
    cases = junit_cases(junit, root)
    refs_cache: dict[str, dict] = {}

    def probe(rel: str):
        try:
            return rel, invoker.probe_import(root, rel), None
        except invoker.ModuleInvokeRefused as exc:
            return rel, None, str(exc)

    with cf.ThreadPoolExecutor(4) as ex:
        probes = list(ex.map(probe, sorted(mods)))
    modules: dict[str, Any] = {}
    refused: dict[str, dict[str, str]] = {}
    import_refusals: dict[str, str] = {}
    tier_count: collections.Counter = collections.Counter()
    for rel, loaded, error in probes:
        if loaded is None:
            kind = "IMPORT_REFUSED_BY_READ_ONLY_GUARD" if "READ_ONLY" in (error or "") else "IMPORT_FAILED"
            reasons[kind] += 1
            import_refusals[rel] = (error or "")[:160]
            continue
        info = mods[rel]
        names = [f for f in info["functions"] if f in loaded]
        if not names:
            reasons["NO_PUBLIC_FUNCTION_AFTER_IMPORT"] += 1
            continue
        evidence_files: set[str] = set()
        functions = {}
        for f in names:
            passing = failing = 0
            files = set()
            for t in index.referencing(rel):
                if t not in refs_cache:
                    refs_cache[t] = case_references(index.tests[t])
                for cls, name, state in cases.get(t, []):
                    used = refs_cache[t].get((cls, name)) or refs_cache[t].get((None, name)) or set()
                    if f in used:
                        if state == "PASS":
                            passing += 1
                            files.add(t)
                        elif state == "FAIL":
                            failing += 1
            if failing:
                refused.setdefault(rel, {})[f] = "FAILING_TEST_CASES:%d" % failing
                tier_count["REFUSED_FAILING_TEST_CASE"] += 1
                continue
            tier = TESTED if passing else UNTESTED
            tier_count[tier] += 1
            evidence_files |= files
            functions[f] = {"tier": tier, "passing_cases": passing, **info["functions"][f]}
        if functions:
            modules[rel] = {"sha256": _sha(root / rel), "doc": info["doc"], "functions": functions,
                            "tests": {t: _sha(root / t) for t in sorted(evidence_files)}}
    return {
        "schema": SCHEMA,
        "authority": "NONE__SANDBOX_MEASUREMENT_OF_EXISTING_TESTS_NOT_A_TRUE_CAPABILITY_RECEIPT",
        "generated_by": "canonical/runtime/module_invocation_evidence_v1.py",
        "admission_rule": [
            "module imports inside the guarded child (no write, delete, subprocess, socket at import)",
            "TEST_EVIDENCED: >=1 passing test case names the function and no failing case names it",
            "READ_ONLY_UNTESTED: no test case names it; callable read-only and every result says so",
            "a function named by a failing test case is refused and listed under 'refused'",
            "module and evidence test files pinned by sha256; any drift refuses the call",
        ],
        "measured_platform": platform.system().lower(),
        "measured_python": "%d.%d" % sys.version_info[:2],
        "junit_cases": sum(len(v) for v in cases.values()),
        "summary": {
            "inventory_modules": len(inventory_paths(root)),
            "invocable_modules": len(modules),
            "invocable_functions": sum(len(m["functions"]) for m in modules.values()),
            "functions_by_tier": dict(sorted(tier_count.items())),
            "modules_excluded": dict(sorted(reasons.items())),
        },
        "modules": modules,
        "refused": refused,
        "import_refusals": import_refusals,
    }


def check(root: pathlib.Path = ROOT) -> list[str]:
    data = json.loads((root / EVIDENCE_REL).read_text(encoding="utf-8"))
    errors = []
    if data.get("schema") != SCHEMA:
        return ["SCHEMA"]
    for rel, row in data["modules"].items():
        if not (root / rel).is_file() or _sha(root / rel) != row["sha256"]:
            errors.append("MODULE_DRIFT:" + rel)
            continue
        _, info = static_module(root, rel)
        if set(row["functions"]) - set(info.get("functions", {})):
            errors.append("FUNCTION_GONE:" + rel)
        for t, sha in row["tests"].items():
            if not (root / t).is_file() or _sha(root / t) != sha:
                errors.append("TEST_DRIFT:%s:%s" % (rel, t))
    s = data["summary"]
    tiers = collections.Counter(f["tier"] for m in data["modules"].values() for f in m["functions"].values())
    if s["invocable_modules"] != len(data["modules"]) or s["invocable_functions"] != sum(tiers.values()) \
            or any(s["functions_by_tier"].get(k) != v for k, v in tiers.items()):
        errors.append("SUMMARY_MISMATCH")
    return errors


def drifted_modules(data: dict[str, Any], root: pathlib.Path = ROOT) -> list[str]:
    """Every module whose pins no longer match, by exactly the rule `check()` uses.

    A module is drifted when its own sha256 moved, or when any test file it cites as evidence
    moved. Both mean the same thing: the pin that proves "the function that runs is the
    function that was tested" no longer proves it, so `brain_module_invoke_v1.admitted` refuses
    every call into that module.
    """
    out: list[str] = []
    for rel, row in data["modules"].items():
        if not (root / rel).is_file() or _sha(root / rel) != row.get("sha256"):
            out.append(rel)
            continue
        for t, sha in (row.get("tests") or {}).items():
            if not (root / t).is_file() or _sha(root / t) != sha:
                out.append(rel)
                break
    return sorted(set(out))


def remeasure(junit: list[str], only: list[str] | None = None,
              root: pathlib.Path = ROOT) -> tuple[dict[str, Any], list[str], list[tuple[str, str]]]:
    """Refresh ONLY the drifted rows, from a real test run, leaving the rest byte-identical.

    Why this exists. `--write` calls `build()`, which rebuilds the whole document from the
    junit it is given. Feeding it a partial run therefore does not partially update anything:
    every function not named by the supplied cases silently loses TEST_EVIDENCED and is
    re-tiered READ_ONLY_UNTESTED. Measured on this repository that is 2678 test-evidenced
    functions, so the partial re-measurement this document's own `remeasurement.why` field
    describes -- "re-measured from a real pytest run of every test file that references them"
    -- could not actually be performed by the tool that wrote the field. It had to be done by
    hand, which is how 26 modules came to sit stale and refuse every call into them.

    This does the documented thing for real, and it fails closed rather than re-stamping:

    * a module with no supplied junit for ANY test that references it is REFUSED, not
      re-pinned. Re-stamping a sha256 without a run behind it would forge the proof that the
      function which runs is the function which was tested -- the one thing this document
      exists to establish.
    * only rows in `drifted_modules` are touched; every other row is left exactly as it was.
    * a function named by a failing case is dropped from the row and listed under `refused`,
      exactly as `build()` does.
    """
    data = json.loads((root / EVIDENCE_REL).read_text(encoding="utf-8"))
    targets = drifted_modules(data, root)
    if only:
        wanted = set(only)
        targets = [r for r in targets if r in wanted]
    if not targets:
        return data, [], []

    mods, _ = statics(root)
    index = TestIndex(test_files(root))
    cases = junit_cases(junit, root)
    refs_cache: dict[str, dict] = {}
    updated: list[str] = []
    refused: list[tuple[str, str]] = []

    for rel in targets:
        if rel not in mods:
            refused.append((rel, "NOT_IN_STATIC_INVENTORY"))
            continue
        covering = sorted(index.referencing(rel))
        if not any(cases.get(t) for t in covering):
            refused.append((rel, "NO_TEST_RUN_SUPPLIED_FOR_ANY_REFERENCING_TEST"))
            continue
        try:
            loaded = invoker.probe_import(root, rel)
        except invoker.ModuleInvokeRefused as exc:
            refused.append((rel, "IMPORT_REFUSED:" + str(exc)[:120]))
            continue
        info = mods[rel]
        names = [f for f in info["functions"] if f in loaded]
        if not names:
            refused.append((rel, "NO_PUBLIC_FUNCTION_AFTER_IMPORT"))
            continue
        evidence_files: set[str] = set()
        functions: dict[str, Any] = {}
        failing_names: dict[str, str] = {}
        for f in names:
            passing = failing = 0
            files: set[str] = set()
            for t in covering:
                if t not in refs_cache:
                    refs_cache[t] = case_references(index.tests[t])
                for cls, name, state in cases.get(t, []):
                    used = refs_cache[t].get((cls, name)) or refs_cache[t].get((None, name)) or set()
                    if f in used:
                        if state == "PASS":
                            passing += 1
                            files.add(t)
                        elif state == "FAIL":
                            failing += 1
            if failing:
                failing_names[f] = "FAILING_TEST_CASES:%d" % failing
                continue
            tier = TESTED if passing else UNTESTED
            evidence_files |= files
            functions[f] = {"tier": tier, "passing_cases": passing, **info["functions"][f]}
        if not functions:
            refused.append((rel, "NO_ADMITTABLE_FUNCTION"))
            continue
        data["modules"][rel] = {
            "sha256": _sha(root / rel), "doc": info["doc"], "functions": functions,
            "tests": {t: _sha(root / t) for t in sorted(evidence_files)}}
        if failing_names:
            data.setdefault("refused", {})[rel] = failing_names
        else:
            (data.get("refused") or {}).pop(rel, None)
        updated.append(rel)

    if updated:
        tiers = collections.Counter(
            f["tier"] for m in data["modules"].values() for f in m["functions"].values())
        data["summary"]["invocable_modules"] = len(data["modules"])
        data["summary"]["invocable_functions"] = sum(tiers.values())
        data["summary"]["functions_by_tier"] = dict(sorted(tiers.items()))
        data["remeasurement"] = {
            "authority": "NONE__SANDBOX_MEASUREMENT_OF_EXISTING_TESTS_NOT_A_TRUE_CAPABILITY_RECEIPT",
            "junit_cases_observed": sum(len(v) for v in cases.values()),
            "measured_platform": platform.system().lower(),
            "measured_python": "%d.%d" % sys.version_info[:2],
            "modules": sorted(updated),
            "refused": [{"module": r, "why": w} for r, w in sorted(refused)],
            "tool": "canonical/runtime/module_invocation_evidence_v1.py --remeasure",
            "why": ("These modules drifted: their own bytes or a test file they cite as evidence "
                    "changed, so the sha256 pins no longer proved that the function which runs is "
                    "the function which was tested, and every call into them was refused. They were "
                    "re-measured from a real pytest run of the test files that reference them. Every "
                    "other row in this document is byte-identical to before, and a drifted module "
                    "with no supplied run is listed under refused rather than re-stamped."),
        }
    return data, updated, refused


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--list-tests", action="store_true")
    g.add_argument("--write", action="store_true")
    g.add_argument("--check", action="store_true")
    g.add_argument("--register", action="store_true")
    g.add_argument("--remeasure", action="store_true")
    ap.add_argument("--junit", action="append", default=[])
    ap.add_argument("--module", action="append", default=[])
    ns = ap.parse_args(argv)
    if ns.list_tests:
        mods, _ = statics()
        index = TestIndex(test_files())
        print("\n".join(sorted({t for rel in mods for t in index.referencing(rel)})))
        return 0
    if ns.write:
        if not ns.junit:
            ap.error("--write needs --junit from a real pytest run")
        data = build(ns.junit)
        (ROOT / EVIDENCE_REL).write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(data["summary"], indent=1))
        return 0
    if ns.remeasure:
        if not ns.junit:
            ap.error("--remeasure needs --junit from a real pytest run; re-stamping a sha256 "
                     "with no run behind it would forge the proof this document exists to hold")
        data, updated, refused = remeasure(ns.junit, ns.module or None)
        (ROOT / EVIDENCE_REL).write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"updated": updated,
                          "refused": [{"module": r, "why": w} for r, w in refused]}, indent=1))
        return 0
    if ns.register:
        entries = register()
        for cid, entry in entries.items():
            r = entry["verification"]["report"]
            print(cid, entry["status"], json.dumps({k: v for k, v in r.items() if k not in ("guard", "cases")}, default=str)[:1500])
        return 0 if all(e["status"] == "VERIFIED_BOUND_CAPABILITY" for e in entries.values()) else 1
    errors = check()
    print("MODULE_INVOCATION_EVIDENCE_" + ("OK" if not errors else "DRIFT"), *errors[:20], sep="\n ")
    return 1 if errors else 0


# ---------------------------------------------------------------------------------------------
# Self-verification of the invoker and registration of brain.module.function.invoke
# ---------------------------------------------------------------------------------------------
CAPABILITY_ID = invoker.CAPABILITY_ID
PROBE_DIR_REL = "tmp/module_invoke_probe"

_PROBES = {
    "write": ("def go():\n    open(%r, 'w').write('x')\n    return 1\n", True),
    "pathlib_write": ("import pathlib\ndef go():\n    pathlib.Path(%r).write_text('x')\n    return 1\n", True),
    "delete": ("import os\ndef go():\n    os.remove(%r)\n    return 1\n", True),
    "rmtree": ("import shutil\ndef go():\n    shutil.rmtree(%r)\n    return 1\n", True),
    "subprocess": ("import subprocess\ndef go():\n    subprocess.run(['touch', %r])\n    return 1\n", True),
    "os_system": ("import os\ndef go():\n    os.system('touch ' + %r)\n    return 1\n", True),
    "socket": ("import socket\ndef go():\n    socket.create_connection(('127.0.0.1', 9))\n    return %r\n", True),
    "mkdir": ("import os\ndef go():\n    os.mkdir(%r)\n    return 1\n", True),
}

# Oracle child: an independent read-only hook plus import BY DOTTED NAME (not the loader), so it
# shares neither the runner's binding code nor its loading path.
_ORACLE_CHILD = r'''
import json, os, sys, importlib
req = json.loads(sys.stdin.read()); sys.path.insert(0, req["root"]); sys.dont_write_bytecode = True
W = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC
def hook(ev, a):
    if ev == "open" and ((isinstance(a[1], str) and any(c in a[1] for c in "wax+")) or (isinstance(a[2], int) and a[2] & W)):
        raise PermissionError("oracle read-only")
    if ev.startswith(("os.remove", "os.unlink", "os.rmdir", "os.rename", "os.replace", "os.mkdir", "os.system",
                      "os.exec", "os.spawn", "os.posix_spawn", "os.fork", "shutil.", "subprocess.", "socket.")):
        raise PermissionError("oracle refused " + ev)
sys.addaudithook(hook)
import contextlib, io
with contextlib.redirect_stdout(io.StringIO()):
    fn = getattr(importlib.import_module(req["dotted"]), req["function"])
    out = fn()
sys.__stdout__.write("\x00ORACLE\x00" + json.dumps(out, sort_keys=True, allow_nan=False, default=lambda o: o.as_posix() if hasattr(o, "as_posix") else (_ for _ in ()).throw(TypeError("x"))))
'''


_GUARD_TEXT = re.compile(r"PermissionError:(?:BRAIN_MODULE_INVOKE_READ_ONLY|oracle (?:refused|read-only))[^\"]*")


def _canon(value: Any) -> str:
    """Canonical JSON; the two guards' refusal messages (caught and reported by a function) compare equal."""
    return _GUARD_TEXT.sub("PermissionError:<READ_ONLY_GUARD>", json.dumps(value, sort_keys=True))


def _oracle_direct(root: pathlib.Path, rel: str, function: str) -> Any:
    import subprocess
    req = json.dumps({"root": str(root), "dotted": rel[:-3].replace("/", "."), "function": function})
    proc = subprocess.run([sys.executable, "-I", "-c", _ORACLE_CHILD], input=req, capture_output=True, text=True,
                          timeout=invoker.TIMEOUT_S, cwd=str(root))
    if "\x00ORACLE\x00" not in proc.stdout:
        raise RuntimeError("ORACLE_CALL_FAILED")
    return json.loads(proc.stdout.split("\x00ORACLE\x00", 1)[1])


def _probe_guard(root: pathlib.Path) -> dict[str, Any]:
    import shutil
    probe_dir = root / PROBE_DIR_REL
    shutil.rmtree(probe_dir, ignore_errors=True)
    probe_dir.mkdir(parents=True)
    refused, escaped = [], []
    try:
        for name, (template, _) in sorted(_PROBES.items()):
            target = probe_dir / ("sentinel_" + name)
            if name == "delete":
                target.write_text("keep")
            elif name == "rmtree":
                target.mkdir()
            src = probe_dir / ("probe_%s.py" % name)
            src.write_text(template % str(target), encoding="utf-8")
            try:
                invoker.invoke(root, src.relative_to(root).as_posix(), "go", {})
                escaped.append(name)
            except invoker.ModuleInvokeRefused as exc:
                if "READ_ONLY" not in str(exc):
                    escaped.append(name + ":" + str(exc)[:80])
                    continue
                untouched = (target.exists() if name in ("delete", "rmtree") else not target.exists())
                (refused if untouched else escaped).append(name)
        effects = probe_dir / "probe_import_effects.py"
        effects.write_text("open(%r, 'w').write('x')\ndef go():\n    return 1\n" % str(probe_dir / "sentinel_import"), encoding="utf-8")
        try:
            invoker.invoke(root, effects.relative_to(root).as_posix(), "go", {})
            escaped.append("import_effects")
        except invoker.ModuleInvokeRefused:
            (refused if not (probe_dir / "sentinel_import").exists() else escaped).append("import_effects")
        binder = probe_dir / "probe_binding.py"
        binder.write_text("def f(a, b=2):\n    return [a, b]\ndef z():\n    return 'z'\ndef r(root, k):\n    return [str(root) != '', k]\n", encoding="utf-8")
        brel = binder.relative_to(root).as_posix()
        binding = {
            "kwargs": invoker.invoke(root, brel, "f", {"a": 1, "b": 3}) == [1, 3],
            "kwargs_default": invoker.invoke(root, brel, "f", {"a": 1}) == [1, 2],
            "positional": invoker.invoke(root, brel, "f", 7) == [7, 2],
            "zero_args": invoker.invoke(root, brel, "z", {}) == "z",
            "root_filled": invoker.invoke(root, brel, "r", {"k": 5}) == [True, 5],
        }
        binding["unmatched_dict_is_the_single_argument"] = invoker.invoke(root, brel, "f", {"zz": 1}) == [{"zz": 1}, 2]
        for fn_name, bad in (("f", {}), ("r", {"zz": 1}), ("r", 3)):
            try:
                invoker.invoke(root, brel, fn_name, bad)
                binding["refuses_%s_%s" % (fn_name, json.dumps(bad))] = False
            except invoker.ModuleInvokeRefused as exc:
                binding["refuses_%s_%s" % (fn_name, json.dumps(bad))] = "SIGNATURE" in str(exc) or "MISSING" in str(exc)
    finally:
        shutil.rmtree(probe_dir, ignore_errors=True)
    return {"refused": refused, "escaped": escaped, "binding": binding}


def _probe_admission(root: pathlib.Path, evidence: dict[str, Any]) -> dict[str, bool]:
    tested = sorted((rel, f) for rel, row in evidence["modules"].items() for f, fn in row["functions"].items()
                    if fn["tier"] == TESTED and row["tests"])
    rel, fname = tested[0]
    out = {}

    def refused(ev: dict[str, Any], module: str, function: str, code: str) -> bool:
        try:
            invoker.admitted(root, module, function, ev)
            return False
        except invoker.ModuleInvokeRefused as exc:
            return str(exc).startswith(code)

    out["admitted_row_passes"] = bool(invoker.admitted(root, rel, fname, evidence))
    out["unlisted_module"] = refused(evidence, "canonical/tests/test_brain_module_invoke_v1.py", "test_x", "MODULE_NOT_ADMITTED")
    out["unlisted_function"] = refused(evidence, rel, "__definitely_not_admitted__", "FUNCTION_NOT_ADMITTED")
    stale = json.loads(json.dumps(evidence))
    stale["modules"][rel]["sha256"] = "0" * 64
    out["module_sha_drift"] = refused(stale, rel, fname, "MODULE_EVIDENCE_STALE")
    stale = json.loads(json.dumps(evidence))
    first_test = sorted(stale["modules"][rel]["tests"])[0]
    stale["modules"][rel]["tests"][first_test] = "0" * 64
    out["test_sha_drift"] = refused(stale, rel, fname, "TEST_EVIDENCE_STALE")
    bad_rel, bad_fns = next(iter(sorted((evidence.get("refused") or {}).items())))
    out["own_failing_test_refuses"] = refused(evidence, bad_rel, sorted(bad_fns)[0], "FUNCTION_REFUSED_BY_ITS_OWN_FAILING_TEST")
    return out


def _probe_selection(evidence: dict[str, Any]) -> dict[str, Any]:
    """Self-retrieval: describe each TEST_EVIDENCED function by its own docstring (or name) and give
    a payload made of its own parameter names.  The selector must return it, its own family, or fail
    closed; a silent pick from another family is counted as WRONG."""
    from canonical.runtime.bound_capabilities import brain_module_solve_v1 as solver
    counts: collections.Counter = collections.Counter()
    wrong = []
    for rel, row in sorted(evidence["modules"].items()):
        for fname, fn in sorted(row["functions"].items()):
            sig = fn.get("signature") or {}
            if fn["tier"] != TESTED or len(sig.get("params") or []) < 2 or sig.get("var_kw"):
                continue
            payload = {p: 0 for p in sig["params"]}
            task = fn.get("doc") or fname.replace("_", " ")
            try:
                top, _ = solver.select(task, payload, evidence)
            except invoker.ModuleInvokeRefused as exc:
                counts["FAILED_CLOSED:" + str(exc).split(":")[0].split(" ")[0][:40]] += 1
                continue
            if (top["source_path"], top["function"]) == (rel, fname):
                counts["EXACT"] += 1
            elif top["family"] == solver.family(rel) and top["function"] == fname:
                counts["SAME_FAMILY_OTHER_VERSION"] += 1
            else:
                counts["WRONG"] += 1
                wrong.append("%s:%s -> %s:%s" % (rel, fname, top["source_path"], top["function"]))
    return {"counts": dict(sorted(counts.items())), "wrong": wrong[:50]}


def self_verify(root: pathlib.Path = ROOT, differential_limit: int | None = None) -> dict[str, Any]:
    import concurrent.futures as cf
    evidence = invoker.load_evidence(root)
    jobs = [(m, f) for m, r in sorted(evidence["modules"].items()) for f in r["functions"]]

    def call(job):
        m, f = job
        try:
            return m, f, "OK", invoker.invoke(root, m, f, {})
        except invoker.ModuleInvokeRefused as exc:
            return m, f, "REFUSED", str(exc)[:160]

    with cf.ThreadPoolExecutor(4) as ex:
        calls = list(ex.map(call, jobs))
    returned = [c for c in calls if c[2] == "OK"]
    compared = agreed = 0
    disagreements, nondeterministic, oracle_failed = [], [], 0
    for m, f, _, value in returned[:differential_limit]:
        try:
            again = invoker.invoke(root, m, f, {})
        except invoker.ModuleInvokeRefused:
            again = None
        if _canon(again) != _canon(value):
            nondeterministic.append("%s:%s" % (m, f))  # e.g. self-reported timings; not comparable
            continue
        try:
            expected = _oracle_direct(root, m, f)
        except Exception:
            oracle_failed += 1
            continue
        compared += 1
        if _canon(expected) == _canon(value):
            agreed += 1
        else:
            disagreements.append("%s:%s" % (m, f))
    return {
        "functions_called": len(calls),
        "returned_json_on_empty_payload": len(returned),
        "refused_on_empty_payload": collections.Counter(
            ("READ_ONLY_GUARD" if "READ_ONLY" in c[3] else "SIGNATURE_NEEDS_PAYLOAD" if ("SIGNATURE" in c[3] or "MISSING_REQUIRED" in c[3]) else "RAISED")
            for c in calls if c[2] == "REFUSED"),
        "differential_compared": compared,
        "differential_agreed": agreed,
        "differential_disagreements": disagreements,
        "differential_oracle_could_not_run": oracle_failed,
        "nondeterministic_excluded_from_differential": nondeterministic,
        "guard": _probe_guard(root),
        "admission": _probe_admission(root, evidence),
    }


def _base_entry(root: pathlib.Path, cid: str, adapter: str, ok: bool, report: dict[str, Any], method: str, claim: str) -> dict[str, Any]:
    ev = invoker.load_evidence(root)
    sm = ev["summary"]
    return {
        "status": "VERIFIED_BOUND_CAPABILITY" if ok else "VERIFICATION_FAILED",
        "incremental_spend_usd": 0,
        "cost": 1,
        "adapter_module": adapter,
        "entrypoint": "run",
        "platforms": ["linux"],
        "limitations": [
            "Only the %d modules / %d functions in %s (%d TEST_EVIDENCED, %d READ_ONLY_UNTESTED); everything else is refused." % (
                sm["invocable_modules"], sm["invocable_functions"], EVIDENCE_REL,
                sm["functions_by_tier"].get(TESTED, 0), sm["functions_by_tier"].get(UNTESTED, 0)),
            "Result correctness is NOT independently verified per call: TEST_EVIDENCED rests on the module's own passing tests, READ_ONLY_UNTESTED on nothing but faithful execution. Every result says which.",
            "Read-only: functions that write files, delete, start processes or open sockets are refused at runtime.",
            "The payload must match the function signature; arguments are never guessed.",
        ],
        "source": {
            "type": "brain_native_deterministic",
            "modules": ["hashlib", "inspect", "json", "math", "pathlib", "re", "subprocess", "sys"],
            "adapter_path": "canonical/runtime/bound_capabilities/%s.py" % adapter,
            "runner_path": invoker.RUNNER_REL,
            "evidence_path": EVIDENCE_REL,
        },
        "verification": {
            "verified": ok,
            "method": method,
            "claim": claim,
            "report": report,
            "adapter_sha256": _sha(root / ("canonical/runtime/bound_capabilities/%s.py" % adapter)),
            "invoker_sha256": _sha(root / "canonical/runtime/bound_capabilities/brain_module_invoke_v1.py"),
            "runner_sha256": _sha(root / invoker.RUNNER_REL),
            "evidence_sha256": _sha(root / EVIDENCE_REL),
            "measured_platform": platform.system().lower(),
            "measured_python": "%d.%d" % sys.version_info[:2],
            "model_dependency_count": 0,
        },
    }


def registry_entries(root: pathlib.Path, report: dict[str, Any], selection: dict[str, Any]) -> dict[str, dict[str, Any]]:
    from canonical.runtime.bound_capabilities import brain_module_solve_v1 as solver
    g = report["guard"]
    invoke_ok = (not g["escaped"] and len(g["refused"]) == len(_PROBES) + 1 and all(g["binding"].values())
                 and all(report["admission"].values()) and report["differential_compared"] > 0
                 and report["differential_agreed"] == report["differential_compared"])
    solve_ok = invoke_ok and selection["counts"].get("WRONG", 0) == 0 and selection["counts"].get("EXACT", 0) > 0
    invoke = _base_entry(root, CAPABILITY_ID, "brain_module_invoke_v1", invoke_ok, report,
                         "MODULE_INVOCATION_EVIDENCE_V1_SELF_VERIFY",
                         "Faithful read-only invocation of a NAMED admitted function; not per-result correctness.")
    invoke.update({
        "requires": ["python.source_file.available", "json.payload.available"],
        "provides": ["python.module.function.result"],
        "result_fields": ["status", "source_path", "function", "tier", "result_type", "output_path", "output_sha256", "output_verified"],
        "keywords": ["invoke", "function", "module"],
        "action_template": {
            "type": "invoke_capability",
            "args": {"capability_id": CAPABILITY_ID, "source_path": "${input.source_path}", "function": "${input.function}",
                     "json_path": "${input.json_path}", "output_path": "${input.output_path}"},
            "expect": {"type": "field_equals", "field": "output_verified", "value": True},
        },
    })
    solve = _base_entry(root, solver.CAPABILITY_ID, "brain_module_solve_v1", solve_ok,
                        {"selection_self_retrieval": selection, "invoker": "see brain.module.function.invoke"},
                        "MODULE_INVOCATION_EVIDENCE_V1_SELECTION_SELF_RETRIEVAL",
                        "Chooses the admitted function whose signature fits the payload and whose description fits the task, "
                        "fails closed on cross-family ambiguity, then invokes it read-only.")
    solve.update({
        "requires": ["json.payload.available", "task.description.available"],
        "provides": ["python.module.function.result"],
        "result_fields": ["status", "selected", "source_path", "function", "tier", "result_type", "output_path", "output_sha256", "output_verified"],
        "keywords": ["task", "payload"],
        "action_template": {
            "type": "invoke_capability",
            "args": {"capability_id": solver.CAPABILITY_ID, "task": "${input.task}",
                     "json_path": "${input.json_path}", "output_path": "${input.output_path}"},
            "expect": {"type": "field_equals", "field": "output_verified", "value": True},
        },
    })
    return {CAPABILITY_ID: invoke, solver.CAPABILITY_ID: solve}


def register(root: pathlib.Path = ROOT) -> dict[str, dict[str, Any]]:
    report = self_verify(root)
    selection = _probe_selection(invoker.load_evidence(root))
    entries = registry_entries(root, report, selection)
    path = root / INVENTORY_REL
    data = json.loads(path.read_text(encoding="utf-8"))
    data["capabilities"].update(entries)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return entries


if __name__ == "__main__":
    raise SystemExit(main())
