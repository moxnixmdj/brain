"""Build / check MODULE_INVOCATION_EVIDENCE_V1.json: which inventory modules may be invoked live.

A module from the non-executing inventory is admitted for ``brain.module.function.invoke`` only if
  1. it parses, is not a test, and passes the loader's no-import-time-effects screen;
  2. at least one repository test file references it (by dotted name, path, or import);
  3. EVERY referencing test file ran on the current tree with >= 1 passed case and 0 failures or
     errors (measured from JUnit XML produced by an actual pytest run);
  4. at least one of its public top-level functions is called or named by those test files.
Admitted functions are exactly those named functions.  The module and every evidence test file are
pinned by sha256; ``brain_module_invoke_v1`` re-checks the pins on every call.

Usage:
  python3 -m canonical.runtime.module_invocation_evidence_v1 --list-tests > tests.txt
  python3 -m pytest -c /dev/null --rootdir . --junitxml run.xml $(cat tests.txt)
  python3 -m canonical.runtime.module_invocation_evidence_v1 --write --junit run.xml
  python3 -m canonical.runtime.module_invocation_evidence_v1 --check      # fast, no test rerun
"""
from __future__ import annotations

import argparse
import ast
import collections
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
from canonical.runtime.bound_capabilities import research_tool_loader_v1 as loader  # noqa: E402

INVENTORY_REL = "canonical/runtime/AUTONOMOUS_CAPABILITY_EXTENDED_REGISTRY_V1.json"
EVIDENCE_REL = invoker.EVIDENCE_REL
SCHEMA = "PROJECT_BRAIN_MODULE_INVOCATION_EVIDENCE_V1"
_SKIP_PARTS = {".git", "tmp", "__pycache__", "node_modules"}
# The invoker's own tests use admitted modules as samples; they are not evidence FOR those modules
# (and counting them would make the evidence depend on a test that pins the evidence).
NOT_EVIDENCE_TESTS = frozenset({"canonical/tests/test_brain_module_invoke_v1.py"})


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


def screen(root: pathlib.Path, rel: str) -> tuple[str | None, list[str]]:
    """(exclusion reason or None, public top-level function names)."""
    if _is_test(rel):
        return "IS_A_TEST", []
    try:
        tree = ast.parse((root / rel).read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError, ValueError):
        return "UNPARSEABLE_OR_MISSING", []
    if loader.import_time_effects(tree):
        return "IMPORT_TIME_EFFECTS", []
    public = [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and not n.name.startswith("_")]
    if not public:
        return "NO_PUBLIC_FUNCTION", []
    return None, public


def referencing_tests(rel: str, tests: dict[str, str]) -> list[str]:
    stem = pathlib.PurePosixPath(rel).stem
    dotted = rel[:-3].replace("/", ".")
    imp = re.compile(r"\b(?:import|from)\s+[\w.]*\b%s\b" % re.escape(stem))
    quoted = ('"%s"' % stem, "'%s'" % stem, '"%s.py"' % stem, "'%s.py'" % stem)
    return sorted(t for t, s in tests.items() if dotted in s or rel in s or imp.search(s) or any(q in s for q in quoted))


def named_functions(public: list[str], texts: list[str]) -> list[str]:
    joined = "\n".join(texts)
    return [f for f in public if re.search(r"(?:\b|\.)%s\s*\(|[\"']%s[\"']|\.%s\b" % ((re.escape(f),) * 3), joined)]


def candidates(root: pathlib.Path = ROOT) -> tuple[dict[str, dict[str, Any]], collections.Counter]:
    tests = test_files(root)
    reasons: collections.Counter = collections.Counter()
    out: dict[str, dict[str, Any]] = {}
    for rel in inventory_paths(root):
        reason, public = screen(root, rel)
        if reason:
            reasons[reason] += 1
            continue
        refs = referencing_tests(rel, tests)
        if not refs:
            reasons["NO_TEST_REFERENCES_IT"] += 1
            continue
        funcs = named_functions(public, [tests[t] for t in refs])
        if not funcs:
            reasons["NO_PUBLIC_FUNCTION_NAMED_BY_ITS_TESTS"] += 1
            continue
        out[rel] = {"tests": refs, "functions": funcs}
    return out, reasons


def _file_of(classname: str, file_attr: str | None, root: pathlib.Path) -> str | None:
    if file_attr:
        return pathlib.PurePosixPath(file_attr).as_posix()
    parts = classname.split(".")
    for n in range(len(parts), 0, -1):
        rel = "/".join(parts[:n]) + ".py"
        if (root / rel).is_file():
            return rel
    return None


def junit_by_file(paths: list[str], root: pathlib.Path = ROOT) -> dict[str, collections.Counter]:
    """Per test file case counts.  When several runs cover the same file, the LATER run wins."""
    per: dict[str, collections.Counter] = {}
    for xml in paths:
        this: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
        for case in ET.parse(xml).getroot().iter("testcase"):
            rel = _file_of(case.get("classname", ""), case.get("file"), root)
            if rel is None:
                continue
            kinds = {child.tag for child in case}
            if kinds & {"failure", "error"}:
                this[rel]["failed"] += 1
            elif "skipped" in kinds:
                this[rel]["skipped"] += 1
            else:
                this[rel]["passed"] += 1
        per.update(this)
    return per


def build(junit: list[str], root: pathlib.Path = ROOT) -> dict[str, Any]:
    cands, reasons = candidates(root)
    per = junit_by_file(junit, root)
    modules: dict[str, Any] = {}
    for rel, info in sorted(cands.items()):
        runs = [per.get(t) for t in info["tests"]]
        if any(r is None for r in runs):
            reasons["A_REFERENCING_TEST_FILE_DID_NOT_RUN"] += 1
            continue
        if any(r["failed"] for r in runs):
            reasons["A_REFERENCING_TEST_FILE_FAILS_ON_THIS_TREE"] += 1
            continue
        if any(not r["passed"] for r in runs):
            reasons["A_REFERENCING_TEST_FILE_HAS_NO_PASSING_CASE"] += 1
            continue
        modules[rel] = {
            "sha256": _sha(root / rel),
            "functions": info["functions"],
            "tests": {t: _sha(root / t) for t in info["tests"]},
            "test_cases_passed": sum(r["passed"] for r in runs),
            "measured": "MEASURED_SANDBOX",
        }
    total_cases = sum(sum(c.values()) for c in per.values())
    return {
        "schema": SCHEMA,
        "authority": "NONE__SANDBOX_MEASUREMENT_OF_EXISTING_TESTS_NOT_A_TRUE_CAPABILITY_RECEIPT",
        "generated_by": "canonical/runtime/module_invocation_evidence_v1.py",
        "admission_rule": [
            "parses, not a test, passes research_tool_loader_v1.import_time_effects",
            "every repository test file that references it ran with >=1 passed and 0 failed/error cases",
            "only public functions named by those test files are admitted",
            "module and test files pinned by sha256; any drift refuses the call",
        ],
        "measured_platform": platform.system().lower(),
        "measured_python": "%d.%d" % sys.version_info[:2],
        "junit_cases": total_cases,
        "summary": {
            "inventory_modules": len(inventory_paths(root)),
            "admitted_modules": len(modules),
            "admitted_functions": sum(len(m["functions"]) for m in modules.values()),
            "excluded": dict(sorted(reasons.items())),
        },
        "modules": modules,
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
        reason, public = screen(root, rel)
        if reason:
            errors.append("SCREEN_FAILS:%s:%s" % (rel, reason))
        if set(row["functions"]) - set(public):
            errors.append("FUNCTION_GONE:" + rel)
        for t, sha in row["tests"].items():
            if not (root / t).is_file() or _sha(root / t) != sha:
                errors.append("TEST_DRIFT:%s:%s" % (rel, t))
    s = data["summary"]
    if s["admitted_modules"] != len(data["modules"]) or s["admitted_functions"] != sum(len(m["functions"]) for m in data["modules"].values()):
        errors.append("SUMMARY_MISMATCH")
    return errors


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--list-tests", action="store_true")
    g.add_argument("--write", action="store_true")
    g.add_argument("--check", action="store_true")
    g.add_argument("--register", action="store_true")
    ap.add_argument("--junit", action="append", default=[])
    ns = ap.parse_args(argv)
    if ns.list_tests:
        cands, _ = candidates()
        print("\n".join(sorted({t for c in cands.values() for t in c["tests"]})))
        return 0
    if ns.write:
        if not ns.junit:
            ap.error("--write needs --junit from a real pytest run")
        data = build(ns.junit)
        (ROOT / EVIDENCE_REL).write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(data["summary"], indent=1))
        return 0
    if ns.register:
        entry = register()
        r = entry["verification"]["report"]
        print(entry["status"], json.dumps({k: r[k] for k in r if k != "guard"}, default=str, indent=1), json.dumps(r["guard"], indent=1))
        return 0 if entry["status"] == "VERIFIED_BOUND_CAPABILITY" else 1
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
    rel = next(iter(sorted(evidence["modules"])))
    row = evidence["modules"][rel]
    out = {}

    def refused(ev: dict[str, Any], module: str, function: str, code: str) -> bool:
        try:
            invoker.admitted(root, module, function, ev)
            return False
        except invoker.ModuleInvokeRefused as exc:
            return str(exc).startswith(code)

    out["admitted_row_passes"] = bool(invoker.admitted(root, rel, row["functions"][0], evidence))
    out["unlisted_module"] = refused(evidence, "canonical/runtime/goal_compiler.py", "compile_goal", "MODULE_NOT_ADMITTED")
    out["unlisted_function"] = refused(evidence, rel, "__definitely_not_admitted__", "FUNCTION_NOT_ADMITTED")
    stale = json.loads(json.dumps(evidence))
    stale["modules"][rel]["sha256"] = "0" * 64
    out["module_sha_drift"] = refused(stale, rel, row["functions"][0], "MODULE_EVIDENCE_STALE")
    stale = json.loads(json.dumps(evidence))
    first_test = sorted(stale["modules"][rel]["tests"])[0]
    stale["modules"][rel]["tests"][first_test] = "0" * 64
    out["test_sha_drift"] = refused(stale, rel, row["functions"][0], "TEST_EVIDENCE_STALE")
    return out


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


def registry_entry(root: pathlib.Path, report: dict[str, Any]) -> dict[str, Any]:
    g = report["guard"]
    ok = (not g["escaped"] and len(g["refused"]) == len(_PROBES) + 1 and all(g["binding"].values())
          and all(report["admission"].values()) and report["differential_compared"] > 0
          and report["differential_agreed"] == report["differential_compared"])
    ev = invoker.load_evidence(root)
    return {
        "status": "VERIFIED_BOUND_CAPABILITY" if ok else "VERIFICATION_FAILED",
        "incremental_spend_usd": 0,
        "cost": 1,
        "requires": ["python.source_file.available", "json.payload.available"],
        "provides": ["python.module.function.result"],
        "result_fields": ["status", "source_path", "function", "result_type", "output_path", "output_sha256", "output_verified"],
        "keywords": ["invoke", "function", "module"],
        "action_template": {
            "type": "invoke_capability",
            "args": {"capability_id": CAPABILITY_ID, "source_path": "${input.source_path}", "function": "${input.function}",
                     "json_path": "${input.json_path}", "output_path": "${input.output_path}"},
            "expect": {"type": "field_equals", "field": "output_verified", "value": True},
        },
        "adapter_module": "brain_module_invoke_v1",
        "entrypoint": "run",
        "platforms": ["linux"],
        "limitations": [
            "Only the %d modules / %d functions in %s; everything else is refused." % (
                ev["summary"]["admitted_modules"], ev["summary"]["admitted_functions"], EVIDENCE_REL),
            "Result correctness is NOT independently verified per call; evidence is the module's own passing tests at the pinned sha256.",
            "Read-only: functions that write files, delete, start processes or open sockets are refused at runtime.",
            "The payload must match the function signature; arguments are never guessed.",
        ],
        "source": {
            "type": "brain_native_deterministic",
            "modules": ["hashlib", "inspect", "json", "pathlib", "subprocess", "sys"],
            "adapter_path": "canonical/runtime/bound_capabilities/brain_module_invoke_v1.py",
            "runner_path": invoker.RUNNER_REL,
            "evidence_path": EVIDENCE_REL,
        },
        "verification": {
            "verified": ok,
            "method": "MODULE_INVOCATION_EVIDENCE_V1_SELF_VERIFY",
            "claim": "Faithful read-only invocation of admitted functions; not per-result correctness.",
            "oracle": "canonical/runtime/module_invocation_evidence_v1.py:_oracle_direct (import by dotted name, own audit hook)",
            "report": report,
            "adapter_sha256": _sha(root / "canonical/runtime/bound_capabilities/brain_module_invoke_v1.py"),
            "runner_sha256": _sha(root / invoker.RUNNER_REL),
            "evidence_sha256": _sha(root / EVIDENCE_REL),
            "measured_platform": platform.system().lower(),
            "measured_python": "%d.%d" % sys.version_info[:2],
            "model_dependency_count": 0,
        },
    }


def register(root: pathlib.Path = ROOT) -> dict[str, Any]:
    report = self_verify(root)
    entry = registry_entry(root, report)
    path = root / INVENTORY_REL
    data = json.loads(path.read_text(encoding="utf-8"))
    data["capabilities"][CAPABILITY_ID] = entry
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return entry


if __name__ == "__main__":
    raise SystemExit(main())
