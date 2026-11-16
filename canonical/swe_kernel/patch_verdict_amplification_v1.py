#!/usr/bin/env python3
"""A pass is evidence only if something could have failed it. This measures what a pass is
worth, on this repository's own test suites, and adds whatever a confirmed law can add.

WHY THIS EXISTS
---------------
The last measurement in this tree built a verifier that needs no test file: laws are proposed
from a module's structure and confirmed by executing the program as it stands
(`specification_from_structure_v1`). On this repository's own code it rejected **8 of 89**
behaviourally-altered variants, and **58 of 89** were invisible to it. That is a real oracle and
a weak one.

But real work does not arrive with no oracle at all. It arrives with a *test suite* -- and the
2026 field says that is the weaker half of the problem, not the stronger one: 26 of the 500
SWE-bench Verified tasks had tests that **accepted wrong patches** after expert screening, and
*All Smoke, No Alarm* (arXiv:2606.18168) found weak or absent oracle signals in **80.2%** of
86,156 agent-authored test patches. So the question a learning loop actually faces is:

    the candidate passes the tests -- how much is that pass worth?

This module answers it for one candidate without asking anybody. It puts the candidate through
two independent gates and reports which one spoke:

    THE TEST SUITE     the real test file, run against the candidate by injecting it into the
                       module's own import name in a child process. Nothing is mocked and no
                       test is edited.
    A CONFIRMED LAW    the laws derived from the *pristine* module and confirmed on it by
                       execution -- never derived from the candidate, because a candidate that
                       supplies its own law is marking its own exam.

VERDICTS
--------
    REJECTED_BY_THE_TEST_SUITE        the tests caught it
    REJECTED_BY_A_CONFIRMED_LAW       the tests passed it and a law confirmed on the code as it
                                      stands did not -- with the exact call and both values
    ACCEPTED_BY_BOTH                  nothing available here falsified it. This is **not** a
                                      proof: it is the residual, and it is reported as a number
    UNVERIFIABLE                      the suite could not be run (missing dependency, timeout)

WHY THE INJECTION IS THE HONEST WAY TO DO IT
--------------------------------------------
The alternative is to copy the module somewhere and run the suite there, which changes what the
suite imports and turns the measurement into a measurement of the copy. Here the suite runs as
it is, from the repository, with the candidate installed under the module's own dotted name in a
fresh interpreter, so every other import resolves exactly as it does in the real run.

WHAT THIS IS NOT
----------------
Not a capability, not a correctness proof, not a replacement for a test. A law can only speak
about what its vocabulary can express; a candidate it is silent about is unmeasured, not
approved. Authority: NONE. `$0`. No model. No network. Nothing is written outside a temporary
directory.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
from typing import Any, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import specification_from_structure_v1 as spec  # noqa: E402

SCHEMA = "PROJECT_BRAIN_PATCH_VERDICT_AMPLIFICATION_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"

REJECTED_BY_TESTS = "REJECTED_BY_THE_TEST_SUITE"
REJECTED_BY_LAW = "REJECTED_BY_A_CONFIRMED_LAW"
ACCEPTED_BY_BOTH = "ACCEPTED_BY_BOTH"
UNVERIFIABLE = "UNVERIFIABLE"

#: The plugin is what makes the candidate the module, in the suite's own process, before
#: collection happens. It is generated into a temporary directory and loaded with `-p`; it never
#: touches the repository and it is not a `conftest.py`, so it cannot change what the suite does
#: beyond which object answers to the module's name.
_INJECTION_PLUGIN = '''
import importlib, importlib.util, os, sys

dotted = os.environ.get("BRAIN_INJECT_DOTTED")
path = os.environ.get("BRAIN_INJECT_PATH")
if dotted and path:
    spec = importlib.util.spec_from_file_location(dotted, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[dotted] = module
    try:
        spec.loader.exec_module(module)
    except BaseException as exc:
        sys.stderr.write("BRAIN_INJECT_FAILED:" + type(exc).__name__ + "\\n")
        raise
    parent, _, name = dotted.rpartition(".")
    if parent:
        setattr(importlib.import_module(parent), name, module)
'''


def _executable(python_executable: str | None, repo: pathlib.Path) -> str:
    """A relative interpreter path is relative to the repository, not to the child's directory."""
    if not python_executable:
        return sys.executable
    candidate = pathlib.Path(python_executable)
    if candidate.is_absolute():
        return str(candidate)
    # Deliberately not `.resolve()`: a virtualenv's `bin/python` is a symlink to the base
    # interpreter, and resolving it discards the `pyvenv.cfg` that makes its packages importable.
    resolved = repo / candidate
    if resolved.exists():
        return str(resolved)
    return str(candidate)


def module_dotted_name(module_path: str) -> str:
    """`canonical/swe_kernel/x.py` -> `canonical.swe_kernel.x`."""
    return module_path.replace("\\", "/").removesuffix(".py").replace("/", ".")


def run_tests(
    *,
    module_path: str,
    test_path: str,
    candidate_source: str,
    repo_root: pathlib.Path | str = ROOT,
    python_executable: str | None = None,
    timeout_s: float = 180.0,
) -> dict[str, Any]:
    """Run the module's own test file against `candidate_source`.

    Returns `PASS`, `FAIL`, or `UNRUNNABLE` with the reason. `FAIL` is any non-zero exit; the
    reason is in the tail so a collection error is never confused with a caught defect.
    """
    repo = pathlib.Path(repo_root).resolve()
    executable = _executable(python_executable, repo)
    dotted = module_dotted_name(module_path)
    with tempfile.TemporaryDirectory(prefix="brain_amplify_") as workdir:
        work = pathlib.Path(workdir)
        (work / "brain_mutant_inject.py").write_text(_INJECTION_PLUGIN, encoding="utf-8")
        candidate = work / "candidate.py"
        candidate.write_text(candidate_source, encoding="utf-8")
        env = {
            "PATH": "/usr/bin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": f"{work}{':'}{repo}",
            "BRAIN_INJECT_DOTTED": dotted,
            "BRAIN_INJECT_PATH": str(candidate),
            "PYTHONHASHSEED": "0",
        }
        try:
            process = subprocess.run(
                [executable, "-B", "-m", "pytest", str((repo / test_path).resolve()),
                 "-q", "--no-header", "-p", "brain_mutant_inject", "-x"],
                capture_output=True, text=True, timeout=timeout_s, cwd=work, env=env,
            )
        except subprocess.TimeoutExpired:
            return {"outcome": "UNRUNNABLE", "why": "TIMEOUT", "tail": []}
        except FileNotFoundError:
            return {"outcome": "UNRUNNABLE", "why": "INTERPRETER_NOT_FOUND", "tail": []}
    stdout = process.stdout or ""
    tail = [line for line in stdout.strip().splitlines() if line.strip()][-4:]
    if "No module named pytest" in (process.stderr or ""):
        return {"outcome": "UNRUNNABLE", "why": "PYTEST_MISSING", "tail": tail}
    if "BRAIN_INJECT_FAILED" in (process.stderr or ""):
        return {"outcome": "FAIL", "why": "CANDIDATE_DOES_NOT_IMPORT",
                "tail": tail, "returncode": process.returncode}
    if process.returncode == 0:
        return {"outcome": "PASS", "why": "TESTS_PASSED", "tail": tail, "returncode": 0}
    return {"outcome": "FAIL", "why": "TESTS_FAILED", "tail": tail,
            "returncode": process.returncode}


def prepare_laws(
    *,
    module_path: str,
    repo_root: pathlib.Path | str = ROOT,
    extra_pools: Mapping[str, Sequence[Any]] | None = None,
    grids: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Derive the laws from the pristine module once, so many candidates can be judged by them.

    `grids` replaces the invented argument grid. It exists because a law about a function that
    nothing can call is a law about nothing: pass the arguments reality already used.
    """
    repo = pathlib.Path(repo_root).resolve()
    pristine = (repo / module_path).read_text(encoding="utf-8")
    derived = spec.derive(pristine, pathlib.Path(module_path).stem)
    names = [entry["name"] for entry in derived["functions"]]
    return {
        "module_path": module_path,
        "derived": derived,
        "names": names,
        "baseline_source": spec.reduce_module(pristine, names) if names else "",
        "extra_pools": extra_pools,
        "grids": dict(grids) if grids is not None else None,
        "grid_source": "RECORDED_FROM_A_REAL_SUITE" if grids is not None else "INVENTED",
    }


def laws_against_prepared(
    prepared: Mapping[str, Any],
    *,
    candidate_source: str,
    call_timeout_s: float = 0.5,
) -> dict[str, Any]:
    if not prepared["names"]:
        return {"confirmed": 0, "broken": [], "verdict": ACCEPTED_BY_BOTH,
                "why": "NO_CALLABLE_FUNCTION", "counterexample": None,
                "vacuous": 0, "not_applicable": 0, "refuted": 0, "proposed": 0}
    payload = spec.child_payload(
        module_name=pathlib.Path(str(prepared["module_path"])).stem,
        baseline_source=prepared["baseline_source"],
        derived=prepared["derived"],
        variants=[{
            "variant_id": "candidate",
            "operator": "CANDIDATE",
            "function": None,
            "source": spec.reduce_module(candidate_source, prepared["names"]),
        }],
        call_timeout_s=call_timeout_s,
        extra_pools=prepared.get("extra_pools"),
        grids=prepared.get("grids"),
    )
    outcome = spec.run_child(payload)
    census: dict[str, dict[str, int]] = {}
    for row in outcome["confirmations"]:
        bucket = census.setdefault(row["kind"], {"proposed": 0, "confirmed": 0, "vacuous": 0,
                                                 "not_applicable": 0, "refuted": 0})
        bucket["proposed"] += 1
        if row["verdict"] == spec.CONFIRMED:
            bucket["confirmed"] += 1
        elif row["verdict"] == spec.VACUOUS:
            bucket["vacuous"] += 1
        elif row["verdict"] == spec.NOT_APPLICABLE:
            bucket["not_applicable"] += 1
        elif row["verdict"] == spec.REFUTED:
            bucket["refuted"] += 1
    confirmed = [row for row in outcome["confirmations"]
                 if row["verdict"] == spec.CONFIRMED and row["kind"] != "TOTALITY"]
    judgement = outcome["judgements"][0]
    broken = judgement["killed_by"]
    if broken == ["IMPORT_FAILED"]:
        # The candidate's changed definition could not be defined in the reduction. That is not a
        # law speaking and it is not a pass either; the law gate simply could not look.
        return {
            "confirmed": len(confirmed),
            "broken": [],
            "counterexample": None,
            "verdict": UNVERIFIABLE,
            "why": "CANDIDATE_NOT_LOADABLE_UNDER_REDUCTION",
            "laws_available": len(confirmed) > 0,
            "proposed": len(outcome["confirmations"]),
            "vacuous": sum(1 for row in outcome["confirmations"]
                           if row["verdict"] == spec.VACUOUS),
            "not_applicable": sum(1 for row in outcome["confirmations"]
                                  if row["verdict"] == spec.NOT_APPLICABLE),
            "refuted": sum(1 for row in outcome["confirmations"]
                           if row["verdict"] == spec.REFUTED),
            "census_by_kind": census,
            "killed_by": [],
            "laws_brought_to_bear": 0,
        }
    return {
        "confirmed": len(confirmed),
        "broken": broken,
        "counterexample": judgement.get("counterexample"),
        "verdict": REJECTED_BY_LAW if broken else ACCEPTED_BY_BOTH,
        "why": "LAW_SPOKE" if broken else "NO_LAW_SPOKE",
        "laws_available": len(confirmed) > 0,
        "proposed": len(outcome["confirmations"]),
        "vacuous": sum(1 for row in outcome["confirmations"]
                       if row["verdict"] == spec.VACUOUS),
        "not_applicable": sum(1 for row in outcome["confirmations"]
                              if row["verdict"] == spec.NOT_APPLICABLE),
        "refuted": sum(1 for row in outcome["confirmations"]
                       if row["verdict"] == spec.REFUTED),
        "census_by_kind": census,
        "killed_by": broken,
        # How many confirmed laws were *pointed at the mutated function*. Zero here means the law
        # never got the chance to disagree, which is a different fact from disagreeing and losing.
        "laws_brought_to_bear": int(judgement.get("laws_brought_to_bear") or 0),
    }


def laws_against(
    *,
    module_path: str,
    candidate_source: str,
    repo_root: pathlib.Path | str = ROOT,
    extra_pools: Mapping[str, Sequence[Any]] | None = None,
    call_timeout_s: float = 0.5,
) -> dict[str, Any]:
    """Confirm the laws on the pristine module, then let only those judge one candidate."""
    prepared = prepare_laws(module_path=module_path, repo_root=repo_root, extra_pools=extra_pools)
    return laws_against_prepared(prepared, candidate_source=candidate_source,
                                 call_timeout_s=call_timeout_s)


def amplify(
    *,
    module_path: str,
    test_path: str,
    candidate_source: str,
    repo_root: pathlib.Path | str = ROOT,
    python_executable: str | None = None,
    test_timeout_s: float = 180.0,
    extra_pools: Mapping[str, Sequence[Any]] | None = None,
) -> dict[str, Any]:
    """Two gates, one verdict, and the reason only one of them spoke."""
    tests = run_tests(
        module_path=module_path, test_path=test_path, candidate_source=candidate_source,
        repo_root=repo_root, python_executable=python_executable, timeout_s=test_timeout_s,
    )
    if tests["outcome"] == "UNRUNNABLE":
        return {
            "schema": SCHEMA, "authority": AUTHORITY,
            "verdict": UNVERIFIABLE, "tests": tests, "laws": None,
            "trust_the_pass": None,
            "why": "NOTHING_RAN:" + str(tests.get("why")),
        }
    if tests["outcome"] == "FAIL":
        return {
            "schema": SCHEMA, "authority": AUTHORITY,
            "verdict": REJECTED_BY_TESTS, "tests": tests, "laws": None,
            "trust_the_pass": None,
            "why": "THE_SUITE_FALSIFIED_IT",
        }
    laws = laws_against(
        module_path=module_path, candidate_source=candidate_source, repo_root=repo_root,
        extra_pools=extra_pools,
    )
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "verdict": laws["verdict"] if laws["verdict"] == REJECTED_BY_LAW else ACCEPTED_BY_BOTH,
        "tests": tests,
        "laws": laws,
        # A pass is trusted only in the sense that nothing available here falsified it. The key
        # is deliberately not called `correct`.
        "trust_the_pass": laws["verdict"] != REJECTED_BY_LAW,
        "why": laws["why"],
    }


# --------------------------------------------------------------------------- #
# The grid a real suite already built: the arguments its own executions passed
# --------------------------------------------------------------------------- #
#: Most functions in real code cannot be called with an invented argument: they want a parsed
#: record, a spec dict, a repository root. An invented grid reports NOT_APPLICABLE on exactly
#: those functions, which is why a structure-only verifier reached 6% of this tree's functions.
#: A test suite, by contrast, already knows how to call them -- it does it whenever it runs.
#: So the grid is *recorded* from the suite's own executions instead of guessed.
_ARGUMENT_TRACE_PLUGIN = '''
import json, os, pickle, sys

_target_suffix = os.environ.get("BRAIN_TRACE_SUFFIX") or ""
_out = os.environ.get("BRAIN_TRACE_OUT") or ""
_limit = int(os.environ.get("BRAIN_TRACE_LIMIT") or "200")
_records = []
_seen = set()


def _json_safe(value):
    try:
        text = json.dumps(value)
    except (TypeError, ValueError):
        return False
    try:
        return json.loads(text) == value
    except (TypeError, ValueError):
        return False


def _tracer(frame, event, arg):
    if event != "call":
        return _tracer
    code = frame.f_code
    if _target_suffix and not code.co_filename.replace("\\\\", "/").endswith(_target_suffix):
        return _tracer
    if len(_records) >= _limit:
        return _tracer
    names = code.co_varnames[: code.co_argcount]
    values = []
    for name in names:
        if name in ("self", "cls"):
            return _tracer
        if name not in frame.f_locals:
            return _tracer
        values.append(frame.f_locals[name])
    if not all(_json_safe(value) for value in values):
        return _tracer
    key = (code.co_name, json.dumps(values, sort_keys=True))
    if key in _seen:
        return _tracer
    _seen.add(key)
    _records.append({"function": code.co_name, "args": values})
    return _tracer


def _dump(exitstatus):
    if not _out:
        return
    with open(_out, "wb") as handle:
        pickle.dump({"records": _records, "exitstatus": int(exitstatus)}, handle)


def pytest_sessionfinish(session, exitstatus):
    _dump(exitstatus)


def pytest_configure(config):
    sys.settrace(_tracer)
    try:
        import threading
        threading.settrace(_tracer)
    except Exception:
        pass


def pytest_unconfigure(config):
    sys.settrace(None)
    if _out and not os.path.exists(_out):
        _dump(-1)
'''


def trace_suite_calls(
    *,
    module_path: str,
    test_path: str,
    repo_root: pathlib.Path | str = ROOT,
    python_executable: str | None = None,
    timeout_s: float = 180.0,
    limit: int = 200,
) -> dict[str, Any]:
    """Record the arguments the suite itself passes into `module_path`, as it runs.

    Only calls whose arguments survive a JSON round trip unchanged are kept, because the grid
    crosses a process boundary; the number dropped is reported rather than hidden. On the
    other side of that boundary the arguments are reconstructed exactly, so a law confirmed on
    them is confirmed on what the suite actually did.
    """
    import pickle

    repo = pathlib.Path(repo_root).resolve()
    executable = _executable(python_executable, repo)
    with tempfile.TemporaryDirectory(prefix="brain_trace_") as workdir:
        work = pathlib.Path(workdir)
        (work / "brain_argument_trace.py").write_text(_ARGUMENT_TRACE_PLUGIN, encoding="utf-8")
        capture = work / "calls.pickle"
        env = {
            "PATH": "/usr/bin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": f"{work}{':'}{repo}",
            "PYTHONHASHSEED": "0",
            "BRAIN_TRACE_SUFFIX": module_path.replace("\\", "/"),
            "BRAIN_TRACE_OUT": str(capture),
            "BRAIN_TRACE_LIMIT": str(limit),
        }
        try:
            process = subprocess.run(
                [executable, "-B", "-m", "pytest", str((repo / test_path).resolve()),
                 "-q", "--no-header", "-p", "brain_argument_trace", "-p", "no:cacheprovider"],
                capture_output=True, text=True, timeout=timeout_s, cwd=work, env=env,
            )
        except subprocess.TimeoutExpired:
            return {"records": [], "why": "TIMEOUT"}
        except FileNotFoundError:
            return {"records": [], "why": "INTERPRETER_NOT_FOUND"}
        if not capture.is_file():
            return {"records": [], "why": "NO_TRACE_FILE",
                    "stderr": (process.stderr or "")[-200:]}
        with capture.open("rb") as handle:
            payload = pickle.load(handle)
    records = payload.get("records") or []
    by_function: dict[str, int] = {}
    for record in records:
        by_function[record["function"]] = by_function.get(record["function"], 0) + 1
    return {
        "records": records,
        "functions": by_function,
        "suite_exit_status": payload.get("exitstatus"),
        "why": "TRACED",
    }


def recorded_grids(records: Sequence[Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Turn traced calls into the grid format `child_payload` expects, one pool per function."""
    pools: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        name = str(record.get("function") or "")
        args = record.get("args")
        if not name or not isinstance(args, list):
            continue
        pool = pools.setdefault(name, [])
        entry = {"args": args}
        if entry not in pool:
            pool.append(entry)
    return pools
