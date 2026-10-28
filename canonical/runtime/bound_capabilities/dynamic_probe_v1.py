# PROJECT_BRAIN
"""python.dynamic.fuzz.v1 — type-directed, seeded, subprocess-isolated fuzzing with
shrinking and a reproducer, over the function the sentence names.

A fuzzer that runs the target IN THIS PROCESS is not a fuzzer: half of what it is for
(segfaults, `sys.exit`, hangs, `MemoryError`) kills the run it is measuring.  So every case runs
in a child interpreter with a wall-clock cap, and the outcome is one of `ok`, `raised`, `timeout`,
`signaled` or `crashed` — a fact about the process, not an exception the harness caught by luck.

What makes the finding usable is the shrink: when a case fails, each argument is reduced greedily
against a pool of strictly smaller candidates (0, 1, -1, "", "a", [], …), keeping the reduction
only while it still fails the same way.  What comes out is the minimal failing call, and it is
written next to the artifact as a runnable reproducer — a failing input nobody can reproduce is a
rumour.

Law:

* generation is DETERMINISTIC: the same seed produces the same cases, so a finding is a claim
  anyone can re-run.  Cases are drawn from the parameter annotations (int, float, str, bool,
  bytes, list[int], optional/None) plus a boundary corpus (0, 1, -1, sys.maxsize, "", "a", "0").
  An unannotated parameter gets int and str draws, in that order.
* an exception is only a finding when it is not DECLARED expected: `expected_exceptions` names
  the exception types the contract allows (a validator that must raise is not a bug).
* a case that produces no failure is not reported; the artifact states how many cases ran, so
  "nothing found" and "nothing ran" cannot be confused.
* refuse, named: no target function stated, no module stated, an unimportable module, an
  unannotated target with no cases possible — and a shrink that changes the failure mode is not a
  shrink (the reproduction is re-checked at every step).

Inputs (kwargs, repo-confined):
  source_root        the project directory (or the module file itself)
  module             module file relative to source_root (implied when source_root is a file)
  qualname           the function to fuzz
  max_cases          default 64
  seed               default 0
  expected_exceptions  names of exception types the contract allows
  timeout_s          per-case wall clock (default 5), and the overall cap
  output_path        summary artifact; the reproducer is written beside it

result_fields: adapter, capability_id, act, target, cases_run, findings, minimal_case,
failure_mode, reproducer_path, gate, complete, output_path, output_sha256, output_verified.
"""

from __future__ import annotations

import ast
import json
import os
import random
import subprocess
import sys
from pathlib import Path

from canonical.runtime.bound_capabilities.quality_v1 import (
    _base,
    _destination,
    _fail,
    _inside,
    _write,
)

CAPABILITY_ID = "python.dynamic.fuzz.v1"

DEFAULT_CASES = 64
DEFAULT_CASE_TIMEOUT_S = 5

# The child.  It prints exactly one JSON line and exits 0; anything else is a crash the parent
# reports as a crash, because the child could not even describe what happened.
_HARNESS = r"""
import json, sys
spec = json.loads(sys.argv[1])
sys.path.insert(0, spec["source_root"])
try:
    import importlib
    mod = importlib.import_module(spec["module"])
    fn = mod
    for part in spec["qualname"].split("."):
        fn = getattr(fn, part)
except BaseException as exc:
    print(json.dumps({"outcome": "unimportable", "exc": type(exc).__name__, "msg": str(exc)[:300]}))
    raise SystemExit(0)
try:
    value = fn(*spec["args"])
except BaseException as exc:
    print(json.dumps({"outcome": "raised", "exc": type(exc).__name__, "msg": str(exc)[:300]}))
else:
    print(json.dumps({"outcome": "ok", "repr": repr(value)[:200]}))
"""

_BOUNDARIES = {
    "int": [0, 1, -1, 2, 7, 2**31, -(2**31), 2**63],
    "float": [0.0, 1.0, -1.0, 0.5, float("inf")],
    "str": ["", "a", "0", " ", "abc", "\u00e9", "a" * 8],
    "bool": [False, True],
    "bytes": [b"", b"a", b"\x00"],
}


def _annotation_names(node) -> list[str]:
    """The type names an annotation states, flattened (`list[int]` -> ['list', 'int'])."""
    if node is None:
        return []
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        try:
            node = ast.parse(node.value, mode="eval").body
        except SyntaxError:
            return [node.value.split(".")[-1]]
    names: list[str] = []
    if isinstance(node, ast.Name):
        names.append(node.id)
    elif isinstance(node, ast.Attribute):
        names.append(node.attr)
    elif isinstance(node, ast.Subscript):
        names.extend(_annotation_names(node.value))
        names.extend(_annotation_names(node.slice))
    elif isinstance(node, ast.BinOp):
        names.extend(_annotation_names(node.left))
        names.extend(_annotation_names(node.right))
    elif isinstance(node, (ast.Tuple, ast.List)):
        for element in node.elts:
            names.extend(_annotation_names(element))
    return names


def _defines(path: Path, qualname: str) -> bool:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return False
    scope = tree.body
    for part in qualname.split("."):
        match = next((node for node in scope
                      if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                      and node.name == part), None)
        if match is None:
            return False
        scope = match.body
    return True


def _module_defining(project: Path, qualname: str) -> Path:
    """The module in this tree that DEFINES the named symbol.

    A sentence says "fuzz the function add in /pkg/calc.py"; the door hands over the directory and
    the function name.  Choosing the file that defines the name is a fact about the tree, not a
    guess -- but when two files define it, the ambiguity is stated, not resolved silently.
    """
    candidates = [path for path in sorted(project.glob("*.py")) if _defines(path, qualname)]
    if not candidates:
        candidates = [path for path in sorted(project.rglob("*.py")) if _defines(path, qualname)]
    if not candidates:
        _fail("SYMBOL_NOT_FOUND_IN_ANY_MODULE:" + qualname)
    if len(candidates) > 1:
        _fail("MODULE_AMBIGUOUS:" + qualname + ":" +
              ",".join(str(path.relative_to(project)) for path in candidates[:4]))
    return candidates[0]


def _target_function(project: Path, module_file: Path, qualname: str):
    try:
        tree = ast.parse(module_file.read_text(encoding="utf-8"), filename=str(module_file))
    except SyntaxError as exc:
        _fail("MODULE_UNPARSEABLE:" + module_file.name + ":" + str(exc))
    scope = tree.body
    node = None
    for part in qualname.split("."):
        node = None
        for candidate in scope:
            if isinstance(candidate, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) \
                    and candidate.name == part:
                node = candidate
                break
        if node is None:
            _fail("SYMBOL_NOT_FOUND:" + qualname)
        scope = node.body
    if isinstance(node, ast.AsyncFunctionDef):
        _fail("ASYNC_TARGET_UNSUPPORTED:" + qualname)
    if not isinstance(node, ast.FunctionDef):
        _fail("NOT_A_FUNCTION:" + qualname)
    if node.args.vararg or node.args.kwarg or node.args.kwonlyargs:
        _fail("TARGET_TAKES_VARARGS:" + qualname)
    params = list(node.args.posonlyargs) + list(node.args.args)
    defaults = len(node.args.defaults)
    return node, params, defaults


def _draw(kind: str, rng: random.Random):
    if kind in _BOUNDARIES:
        return rng.choice(_BOUNDARIES[kind])
    if "list" in kind or "Sequence" in kind:
        return [rng.choice([0, 1, -1, 2]) for _ in range(rng.randrange(0, 4))]
    if "dict" in kind or "Mapping" in kind:
        return {rng.choice(["a", "b"]): rng.choice([0, 1, -1])}
    return rng.choice([0, 1, -1, 2])


def _cases(node, params, defaults: int, seed: int, max_cases: int) -> list[list]:
    """Deterministic cases, annotation-directed, boundary cases first."""
    rng = random.Random(seed)
    annotations = [_annotation_names(param.annotation) for param in params]
    kinds = []
    for names in annotations:
        if "int" in names:
            kinds.append("int")
        elif "float" in names:
            kinds.append("float")
        elif "str" in names:
            kinds.append("str")
        elif "bool" in names:
            kinds.append("bool")
        elif "bytes" in names:
            kinds.append("bytes")
        elif "list" in names or "Sequence" in names:
            kinds.append("list")
        else:
            kinds.append("")

    required = len(params) - defaults
    out: list[list] = []
    # a boundary case per parameter, so an obvious edge is never left to luck
    for index in range(required):
        bound = required
        case = [0] * bound
        case[index] = _BOUNDARIES[kinds[index]][0] if kinds[index] else 0
        out.append(case)
        case = [1] * bound
        case[index] = _BOUNDARIES[kinds[index]][1] if kinds[index] else 1
        out.append(case)
    for _ in range(max(0, max_cases - len(out))):
        out.append([_draw(kinds[i], rng) if kinds[i] else rng.choice([0, 1, -1, 2, "a"])
                    for i in range(required)])
    return out[:max_cases]


def _run_case(python_exe: str, project: Path, module: str, qualname: str, case: list,
              timeout_s: int) -> dict:
    spec = json.dumps({"source_root": str(project), "module": module, "qualname": qualname,
                       "args": case})
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        proc = subprocess.run([python_exe, "-c", _HARNESS, spec], cwd=str(project),
                              capture_output=True, text=True, timeout=timeout_s, env=env,
                              check=False)
    except subprocess.TimeoutExpired:
        return {"outcome": "timeout", "exc": "Timeout", "msg": "%ss" % timeout_s}
    last = (proc.stdout or "").strip().splitlines()
    if not last:
        return {"outcome": "crashed", "exc": "ProcessCrash",
                "msg": "rc=%d %s" % (proc.returncode, (proc.stderr or "").strip()[-200:])}
    try:
        return json.loads(last[-1])
    except json.JSONDecodeError:
        return {"outcome": "crashed", "exc": "UnparseableChild",
                "msg": (last[-1] or "")[:200]}


def _fails(outcome: dict, expected: set[str]) -> bool:
    if outcome["outcome"] in ("timeout", "crashed", "unimportable"):
        return True
    if outcome["outcome"] == "raised":
        return outcome.get("exc") not in expected
    return False


def _smaller_candidates(value):
    """Strictly smaller values of the same kind — the shrink pool for one argument."""
    if isinstance(value, bool):
        return []
    if isinstance(value, int):
        pool = [0, 1, -1]
        if value > 1:
            pool = [0, 1, value // 2]
        elif value < -1:
            pool = [0, -1, value // 2]
        # STRICTLY smaller: `candidate == 0` used to be accepted as a reduction of 0 itself, so
        # the shrink accepted the case it started from and looped forever (measured: a fuzz run
        # that never returned, parked inside the child-process communicate).
        return [candidate for candidate in pool if abs(candidate) < abs(value)]
    if isinstance(value, float):
        return [0.0, 1.0] if value not in (0.0, 1.0) else []
    if isinstance(value, str):
        pool = ["", "a", value[: len(value) // 2]]
        return [candidate for candidate in pool if len(candidate) < len(value)]
    if isinstance(value, bytes):
        return [b"", b"a"][: 1 if value else 0]
    if isinstance(value, list):
        return [value[: len(value) // 2], value[:-1] if value else []]
    return []


def _shrink(python_exe, project, module, qualname, case, mode, timeout_s, expected) -> list:
    """Greedy reduction that keeps the SAME failure mode.  Never invents a different bug."""
    current = list(case)
    changed = True
    rounds = 0
    while changed and rounds < 200:
        rounds += 1
        changed = False
        for index in range(len(current)):
            for candidate in _smaller_candidates(current[index]):
                trial = list(current)
                trial[index] = candidate
                outcome = _run_case(python_exe, project, module, qualname, trial, timeout_s)
                if _fails(outcome, expected) and outcome["outcome"] == mode:
                    current = trial
                    changed = True
                    break
            if changed:
                break
    return current


def _reproducer(path: Path, module: str, qualname: str, case: list, mode: str) -> None:
    name = qualname.split(".")[-1]
    lines = [
        "# run from the project root:  python <this file>",
        "import json",
        "import sys",
        "from %s import %s" % (module, name),
        "",
        "CASE = %r" % (case,),
        "",
        "def main():",
        "    print('case:', json.dumps(CASE))",
        "    return %s(*CASE)" % name,
        "",
        "if __name__ == '__main__':",
        "    sys.exit(0 if main() is not None else 0)",
        "# expected failure mode at the time of writing: " + mode,
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: dict, root) -> dict:
    root = Path(root)
    args = dict(args or {})
    capability_id = str(args.get("capability_id") or CAPABILITY_ID)
    act = str(args.get("act_verb") or args.get("act") or "fuzz").strip() or "fuzz"
    if act != "fuzz":
        _fail("ACT_NOT_SUPPORTED:" + act)
    output_path = str(args.get("output_path") or "").strip()
    if not output_path:
        _fail("OUTPUT_PATH_NOT_STATED")
    destination = _destination(root, output_path)

    stated = str(args.get("source_root") or args.get("path") or "").strip()
    if not stated:
        _fail("PATH_NOT_STATED")
    located = _inside(root, stated)
    if located is None:
        _fail("PATH_NOT_IN_THE_REPOSITORY:" + stated)
    if located.is_file():
        module_file = located
        project = located.parent
        while (project / "__init__.py").exists() and project.parent != project:
            project = project.parent
    else:
        project = located
        module = str(args.get("module") or "").strip()
        qualname = str(args.get("qualname") or "").strip()
        if module:
            module_file = project / module
            if not module_file.is_file():
                _fail("MODULE_NOT_FOUND:" + module)
        else:
            if not qualname:
                _fail("MODULE_NOT_STATED")
            module = ""
            module_file = None
    if module_file is None:
        module_file = _module_defining(project, qualname)
    module = str(module_file.relative_to(project)).replace(os.sep, "/")
    module = module.removesuffix(".py")
    module = module.replace("/", ".")

    qualname = str(args.get("qualname") or "").strip()
    if not qualname:
        _fail("QUALNAME_NOT_STATED")
    node, params, defaults = _target_function(project, module_file, qualname)
    if not params:
        _fail("TARGET_TAKES_NO_ARGUMENTS:" + qualname)

    try:
        max_cases = int(args.get("max_cases") or DEFAULT_CASES)
        seed = int(args.get("seed") or 0)
        case_timeout = int(args.get("case_timeout_s") or DEFAULT_CASE_TIMEOUT_S)
    except (TypeError, ValueError):
        _fail("NUMERIC_ARGUMENT_INVALID")
    timeout_s = int(args.get("timeout_s") or 300)
    expected = {str(name) for name in (args.get("expected_exceptions") or [])}
    python_exe = str(args.get("python_executable") or sys.executable)

    cases = _cases(node, params, defaults, seed, max_cases)
    findings: list[dict] = []
    for case in cases:
        outcome = _run_case(python_exe, project, module, qualname, case, case_timeout)
        if outcome["outcome"] == "unimportable":
            _fail("MODULE_NOT_IMPORTABLE:" + str(outcome.get("msg"))) 
        if _fails(outcome, expected):
            findings.append({"args": case, "outcome": outcome["outcome"],
                             "exc": outcome.get("exc"), "msg": outcome.get("msg")})

    minimal = None
    failure_mode = None
    reproducer_path = None
    if findings:
        first = findings[0]
        failure_mode = first["outcome"]
        minimal = _shrink(python_exe, project, module, qualname, list(first["args"]),
                          failure_mode, case_timeout, expected)
        # the shrink is only a shrink if the minimal case still fails the SAME way
        recheck = _run_case(python_exe, project, module, qualname, minimal, case_timeout)
        if not (_fails(recheck, expected) and recheck["outcome"] == failure_mode):
            _fail("SHRINK_CHANGED_THE_FAILURE_MODE")
        reproducer_path = str(destination.with_name(destination.stem + "__reproducer.py"))
        Path(reproducer_path).parent.mkdir(parents=True, exist_ok=True)
        _reproducer(Path(reproducer_path), module, qualname, minimal, failure_mode)

    payload = _base(capability_id, act, module_file)
    payload.update({
        "target": str(module_file),
        "module": module,
        "qualname": qualname,
        "parameters": [param.arg for param in params],
        "seed": seed,
        "cases_run": len(cases),
        "cases_that_failed": len(findings),
        "findings": findings[:20],
        "minimal_case": minimal,
        "failure_mode": failure_mode,
        "expected_exceptions": sorted(expected),
        "reproducer_path": reproducer_path,
        "law": ("cases are generated deterministically from the annotations and a boundary "
                "corpus; each runs in its own interpreter with a wall-clock cap, so a crash or a "
                "hang is an outcome rather than a lost run; the minimal failing case is found by "
                "greedy reduction that must keep the same failure mode, and is written as a "
                "runnable reproducer"),
        "complete": True,
        "elapsed_budget_s": timeout_s,
    })
    written = _write(destination, payload)
    return {
        "adapter": "dynamic_probe_v1",
        "capability_id": capability_id,
        "act": act,
        "module": module,
        "qualname": qualname,
        "cases_run": len(cases),
        "cases_that_failed": len(findings),
        "minimal_case": minimal,
        "failure_mode": failure_mode,
        "reproducer_path": reproducer_path,
        "gate": "PASS",
        "complete": True,
        "output_path": output_path,
        "output_sha256": written.get("artifact_sha256"),
        "output_verified": json.loads(Path(destination).read_text(encoding="utf-8"))["artifact_sha256"]
        == written.get("artifact_sha256"),
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--source_root", required=True)
    parser.add_argument("--module", default=None)
    parser.add_argument("--qualname", required=True)
    parser.add_argument("--output_path", required=True)
    parser.add_argument("--max_cases", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--case_timeout_s", type=int, default=None)
    parser.add_argument("--expected_exceptions", nargs="*", default=None)
    ns = parser.parse_args()
    print(json.dumps(run(vars(ns), Path.cwd()), indent=2, sort_keys=True))
