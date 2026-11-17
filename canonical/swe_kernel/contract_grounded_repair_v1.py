"""Contract-grounded repair: derive the goal from the environment, then act.

WHY THIS EXISTS
---------------
Measured on this tree (2026-11-13 .. 2026-11-16), three independent refusals:

* ``INSUFFICIENCY_CERTIFICATE_20261113_V1.json`` -- when the causal observable
  (an executed function, a callee signature, a runtime traceback exception) is
  absent from the representation, ``unrepairable_by_repetition`` is True: no
  number of experiences can identify the rule.
* ``WHAT_ONE_DEMONSTRATION_BUYS_20261116_V1.md`` -- a demonstration transports
  the *shape* of an edit (1/20 held-out bugs) and almost none of its identity.
  The *goal* of the edit "transports to everything and is not an edit at all --
  nothing in the tree infers goals".
* ``WHAT_A_PASS_IS_WORTH_20261116_V1.md`` -- a verifier built from the shape of
  definitions rejects 0 of the 19 wrong candidates a real suite accepted.  The
  verdict's reach is the reach of the *knowledge inside it*, not of its laws.

Those are one gap seen from three sides.  What is missing is an executable,
falsifiable statement of the goal, derived at use time from the environment's
own declared contract -- the published failing test and its data -- over a
vocabulary that includes what actually executed.  This module derives it,
certifies that the vocabulary can separate success from failure, conditions the
edit space on the derived goal, and verifies every candidate against the
corpus's own test on a FRESH copy.

WHAT IT DOES NOT DO
-------------------
* No model, no pretrained weights, no network, no gradient, no spend.
* No learned knowledge.  Facts come from the environment at use time (instant
  knowledge); the only numbers retained are exact counts of *executed verdicts*
  -- a calculated prior over procedures, never a knowledge house.
* It does not accept its own verdict.  A candidate's in-process pass is a
  filter; only the corpus's own pytest, on a fresh copy, is a repair.
* It does not infer the goal from the answer key.  ``correct_python_programs``
  is asserted absent before every task.
* It does not claim correctness, sentience, benchmark standing, or terminal
  credit.  Authority NONE.

DESIGN LAW: the best part is no part.  It reuses
``canonical.runtime.applicability_v1.insufficiency_witness`` (the certificate),
``canonical.runtime.contrast_selection_v1.select_contrast`` (chosen contrasts),
and the existing QuixBugs harness's fresh-copy verdict.  It adds one organ: the
goal compiler.
"""
from __future__ import annotations

import ast
import copy
import difflib
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "BRAIN_CONTRACT_GROUNDED_REPAIR_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
ANSWER_KEY = "correct_python_programs"
MODEL_DEPENDENCY_COUNT = 0

# ---------------------------------------------------------------------------
# Task: the environment's own declared contract, read at use time.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Task:
    name: str
    root: pathlib.Path
    program_rel: str
    test_rel: str
    function_name: str
    cases: tuple[tuple[list[Any], Any], ...]
    program_sha256: str
    test_sha256: str

    @property
    def program_path(self) -> pathlib.Path:
        return self.root / self.program_rel

    @property
    def test_path(self) -> pathlib.Path:
        return self.root / self.test_rel


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_task(task_dir: pathlib.Path, name: str) -> Task:
    """Read a real published task. The answer key must not exist in this tree."""
    root = pathlib.Path(task_dir)
    if (root / ANSWER_KEY).exists():
        raise RuntimeError("ANSWER_KEY_REACHED_THE_SOLVER")
    program_rel = f"python_programs/{name}.py"
    test_rel = f"python_testcases/test_{name}.py"
    program_path, test_path = root / program_rel, root / test_rel
    if not program_path.is_file() or not test_path.is_file():
        raise RuntimeError("TASK_FILES_MISSING")
    test_text = test_path.read_text(encoding="utf-8")
    function_name = _asserted_function(test_text, name)
    cases_path = root / "json_testcases" / f"{function_name}.json"
    cases: list[tuple[list[Any], Any]] = []
    if cases_path.is_file():
        for line in cases_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                args, expected = json.loads(line)
                cases.append((list(args), expected))
    return Task(
        name=name, root=root, program_rel=program_rel, test_rel=test_rel,
        function_name=function_name, cases=tuple(cases),
        program_sha256=_sha(program_path.read_bytes()),
        test_sha256=_sha(test_path.read_bytes()),
    )


def _asserted_function(test_text: str, name: str) -> str:
    """The published test file names the function; do not guess it.

    The ``pytest.use_correct`` branch legitimately names the answer key, but it
    is never the contract this solver reads.  Only the ``python_programs``
    import is accepted; a missing one is a refusal, not an inference.
    """
    tree = ast.parse(test_text, filename="test_file")
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("python_programs"):
            for alias in node.names:
                return alias.asname or alias.name
    raise RuntimeError("TEST_FILE_DOES_NOT_NAME_A_SOLVABLE_FUNCTION")


# ---------------------------------------------------------------------------
# Observation: the causal observable vocabulary.  This is the organ whose
# absence the insufficiency certificate proves unrepairable by repetition.
# ---------------------------------------------------------------------------

_RUNNER = r'''
import importlib, json, shutil, signal, sys, tempfile, pathlib, os

class _Timeout(Exception): pass
def _alarm(_s, _f): raise _Timeout()
signal.signal(signal.SIGALRM, _alarm)

payload = json.load(sys.stdin)
sys.dont_write_bytecode = True  # a stale .pyc would silently replay an older variant
task_dir = pathlib.Path(payload["task_dir"])
scratch = pathlib.Path(tempfile.mkdtemp(prefix="contract_pkg_"))
shutil.copytree(task_dir / "python_programs", scratch / "python_programs")
# SCRATCH MUST WIN.  If the task dir comes first, every variant resolves to the
# untouched original and the whole measurement becomes a tautology.
sys.path.insert(0, str(task_dir))
sys.path.insert(0, str(scratch))
name = payload["name"]
target = scratch / "python_programs" / (name + ".py")
program_file = str(target)
cases = payload["cases"]
grid = payload["grid"]
relations = payload["relations"]
per_call = float(payload["per_call_timeout"])
trace_lines = set()

def _call(fn, args):
    signal.setitimer(signal.ITIMER_REAL, per_call)
    try:
        return fn(*args), None
    except BaseException as exc:  # noqa: BLE001 - the exception IS the observable
        return None, type(exc).__name__
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)

def _call_traced(fn, args):
    """One case, its own executed lines.  Sharing a trace across cases would
    fabricate a vocabulary that cannot separate them."""
    seen = set()
    def tr(frame, event, arg):
        if frame.f_code.co_filename == program_file and event == "line":
            seen.add(frame.f_lineno)
        return tr
    signal.setitimer(signal.ITIMER_REAL, per_call)
    try:
        sys.settrace(tr)
        return fn(*args), None, sorted(seen)
    except BaseException as exc:
        return None, type(exc).__name__, sorted(seen)
    finally:
        sys.settrace(None)
        signal.setitimer(signal.ITIMER_REAL, 0)

def _relation(kind, result, args):
    try:
        if kind == "LEN_MATCHES_INPUT":
            return len(result) == len(args[0])
        if kind == "SORTED_OUTPUT":
            return result == sorted(result)
        if kind == "PERMUTATION_OF_INPUT":
            return sorted(result) == sorted(args[0])
        if kind == "NONNEGATIVE":
            return result >= 0
        if kind == "BOOLEAN":
            return isinstance(result, bool)
        if kind == "TYPE_MATCH":
            return isinstance(result, (int, float, bool, str, list, tuple, dict, set, type(None)))
    except BaseException:
        return None
    return None

def _facts(index, args, expected, value, err, lines):
    facts = {"argcount.%d" % len(args), "executed." + payload["function_name"]}
    facts.add("expected.type." + type(expected).__name__)
    for i, a in enumerate(args):
        facts.add("arg%d.type.%s" % (i, type(a).__name__))
    if err:
        facts.add("traceback." + err)
    if value is not None:
        facts.add("result.type." + type(value).__name__)
        if isinstance(value, (int, float)) and isinstance(expected, (int, float)) \
                and not isinstance(value, bool) and not isinstance(expected, bool):
            try:
                delta = value - expected
                facts.add("delta." + ("positive" if delta > 0 else "negative" if delta < 0 else "zero"))
            except BaseException:
                pass
    for line in lines:
        facts.add("line.%d" % line)
    return sorted(facts)

out = []
for index, source in enumerate(payload["variants"]):
    target.write_text(source, encoding="utf-8")
    for key in [k for k in list(sys.modules) if k == "python_programs" or k.startswith("python_programs.")]:
        del sys.modules[key]
    importlib.invalidate_caches()
    try:
        module = importlib.import_module("python_programs." + name)
        fn = getattr(module, payload["function_name"])
        load_error = None
    except BaseException as exc:
        out.append({"index": index, "load_error": type(exc).__name__ + ": " + str(exc)[:200],
                    "passed": 0, "total": len(cases), "errors": list(range(len(cases))),
                    "grid_violations": [{"relation": "LOAD_FAILED"}], "trace_lines": [],
                    "facts": [], "exceptions": []})
        continue
    passed, errors, exceptions, facts = 0, [], [], []
    case_violations = []
    for c, (args, expected) in enumerate(cases):
        if index == 0:
            value, err, lines = _call_traced(fn, args)
            trace_lines.update(lines)  # union, for grounding candidate positions
        else:
            value, err = _call(fn, args)
            lines = []
        case_ok = False
        if err is not None:
            errors.append(c); exceptions.append(err)
        else:
            try:
                case_ok = (value == expected)
                if case_ok:
                    passed += 1
                else:
                    errors.append(c)
            except BaseException:
                errors.append(c)
        # A candidate that already fails one published case is dead.  Breaking
        # here is what keeps non-terminating defects from eating the budget.
        if index > 0 and not case_ok:
            break
        if index == 0:
            facts.append(_facts(c, args, expected, value, err, lines))
            if value is not None:
                for rel in relations:
                    verdict = _relation(rel, value, args)
                    if verdict is False:
                        case_violations.append({"case": c, "relation": rel,
                                                "passed_case": bool(case_ok)})
    grid_violations = []
    # The original program is always checked against the wider grid (that is
    # how a relation earns its teeth).  A later variant earns that cost only
    # once it already satisfies the published contract.
    if (index == 0 or passed == len(cases)) and relations:
        for g, args in enumerate(grid):
            value, err = _call(fn, args)
            if err is not None or value is None:
                continue
            for rel in relations:
                verdict = _relation(rel, value, args)
                if verdict is False:
                    grid_violations.append({"grid": g, "relation": rel})
    out.append({"index": index, "passed": passed, "total": len(cases), "errors": errors,
                "grid_violations": grid_violations, "case_violations": case_violations,
                "trace_lines": sorted(trace_lines), "facts": facts if index == 0 else [],
                "exceptions": exceptions[:8]})
shutil.rmtree(scratch, ignore_errors=True)
json.dump(out, sys.stdout)
'''


def _grid(cases: Sequence[tuple[list[Any], Any]], cap: int = 12) -> list[list[Any]]:
    """Wider inputs built ONLY from published inputs, never invented data."""
    out: list[list[Any]] = []
    seen: set[str] = set()

    def add(args: Iterable[Any]) -> None:
        row = list(args)
        try:
            key = json.dumps(row, sort_keys=True, default=repr)
        except (TypeError, ValueError):
            return
        if key not in seen:
            seen.add(key)
            out.append(row)

    for args, _ in cases:
        add(args)
        for pos, value in enumerate(args):
            if isinstance(value, int) and not isinstance(value, bool):
                for delta in (1, -1):
                    row = list(args)
                    row[pos] = value + delta
                    add(row)
            elif isinstance(value, (list, tuple)) and len(value) > 1:
                row = list(args)
                row[pos] = list(value[:-1])
                add(row)
        if len(out) >= cap:
            break
    return out[:cap]


def _derive_relations(cases: Sequence[tuple[list[Any], Any]]) -> list[str]:
    """Relations read off the ASSERTIONS' expected values, not off names.

    A relation is a generalisation of what the published test asserts into a
    law over a wider grid.  It is kept only if it holds for every published
    expected value (so it is a property of the specification, not a guess).
    """
    candidates: dict[str, bool] = {
        "LEN_MATCHES_INPUT": True, "SORTED_OUTPUT": True,
        "PERMUTATION_OF_INPUT": True, "NONNEGATIVE": True,
        "BOOLEAN": True, "TYPE_MATCH": True,
    }
    for args, expected in cases:
        first = args[0] if args else None
        try:
            candidates["LEN_MATCHES_INPUT"] &= (hasattr(expected, "__len__") and hasattr(first, "__len__")
                                                and len(expected) == len(first))
            candidates["SORTED_OUTPUT"] &= isinstance(expected, (list, tuple)) and expected == sorted(expected)
            candidates["PERMUTATION_OF_INPUT"] &= (isinstance(expected, (list, tuple))
                                                   and isinstance(first, (list, tuple))
                                                   and sorted(expected) == sorted(first))
        except (TypeError, ValueError):
            candidates["LEN_MATCHES_INPUT"] = candidates["SORTED_OUTPUT"] = candidates["PERMUTATION_OF_INPUT"] = False
        candidates["NONNEGATIVE"] &= (isinstance(expected, (int, float))
                                      and not isinstance(expected, bool) and expected >= 0)
        candidates["BOOLEAN"] &= isinstance(expected, bool)
        candidates["TYPE_MATCH"] &= isinstance(expected, (int, float, bool, str, list, tuple, dict, set, type(None)))
    return sorted(k for k, ok in candidates.items() if ok)


@dataclass
class Observation:
    verdict: str
    cases_total: int
    cases_passed: int
    failing_indices: tuple[int, ...]
    trace_lines: tuple[int, ...]
    exceptions: tuple[str, ...]
    per_case_facts: tuple[frozenset[str], ...]
    static_facts: frozenset[str]
    relations: tuple[str, ...]
    grid_size: int
    static_certificate: dict[str, Any] | None
    traced_certificate: dict[str, Any] | None
    contract_reach: int
    runner_seconds: float


def _payload(task: Task, sources: Sequence[str], relations: Sequence[str]) -> dict[str, Any]:
    return {
        "task_dir": str(task.root), "name": task.name,
        "function_name": task.function_name,
        "cases": [[a, e] for a, e in task.cases], "grid": _grid(task.cases),
        "relations": list(relations), "per_call_timeout": 0.15,
        "variants": list(sources),
    }


def _run_child(payload: dict[str, Any], timeout_s: float, cwd: pathlib.Path) -> list[dict[str, Any]]:
    with tempfile.TemporaryDirectory(prefix="contract_runner_") as tmp:
        runner = pathlib.Path(tmp) / "runner.py"
        runner.write_text(_RUNNER, encoding="utf-8")
        done = subprocess.run([sys.executable, str(runner)], input=json.dumps(payload),
                              text=True, capture_output=True, timeout=timeout_s, cwd=str(cwd))
        if done.returncode != 0:
            raise RuntimeError("CHILD_FAILED:" + done.stderr.strip()[:300])
        return json.loads(done.stdout)


def observe(task: Task, source: str, *, timeout_s: float = 25.0) -> tuple[Observation, list[str]]:
    """Execute the program on the published cases in a bounded child."""
    from canonical.runtime import applicability_v1 as APP

    relations = _derive_relations(task.cases)
    grid = _grid(task.cases)
    started = time.time()
    try:
        rows = _run_child(_payload(task, [source], relations), timeout_s, task.root)
        row = rows[0]
    except (subprocess.TimeoutExpired, RuntimeError, ValueError, IndexError) as exc:
        return _unmeasurable(task, relations, len(grid), time.time() - started,
                             reason="OBSERVATION_" + type(exc).__name__), relations

    passed = int(row["passed"])
    errors = [int(i) for i in row["errors"]]
    trace_lines = tuple(int(i) for i in row.get("trace_lines", []))
    exceptions = tuple(str(e) for e in row.get("exceptions", []))
    per_case_facts = tuple(frozenset(f) for f in row.get("facts", []))
    if len(per_case_facts) != len(task.cases):
        per_case_facts = tuple(frozenset({"executed." + task.function_name}) for _ in task.cases)

    # Two vocabularies, so the certificate's closure is MEASURED, not asserted.
    static_tree = ast.parse(source, filename=str(task.program_path))
    static_facts = frozenset(f"ast.{type(n).__name__}" for n in ast.walk(static_tree))
    static_evidence = tuple((static_facts, i not in set(errors)) for i in range(len(task.cases)))
    traced_evidence = tuple((facts, i not in set(errors)) for i, facts in enumerate(per_case_facts))
    static_cert = APP.insufficiency_witness(static_evidence)
    traced_cert = APP.insufficiency_witness(traced_evidence)

    # A relation is REFUTED if it fails on a case the program already passes:
    # then it is not a law of the specification.  It is VACUOUS if nothing can
    # violate it.  Only a relation that is neither, and that the buggy program
    # DOES violate somewhere (a failing case or the wider grid), has teeth and
    # is used as a check.  This is the REFUTED/VACUOUS discipline applied to
    # assertions instead of to function names.
    case_violations = row.get("case_violations", [])
    grid_violations = row.get("grid_violations", [])
    refuted = {v["relation"] for v in case_violations if v.get("passed_case")}
    teeth = {v["relation"] for v in case_violations if not v.get("passed_case")}
    teeth |= {v["relation"] for v in grid_violations}
    confirmed = [r for r in relations if r not in refuted and r in teeth]
    reach = len(confirmed)
    obs = Observation(
        verdict="OBSERVED", cases_total=len(task.cases), cases_passed=passed,
        failing_indices=tuple(errors), trace_lines=trace_lines, exceptions=exceptions,
        per_case_facts=per_case_facts, static_facts=static_facts,
        relations=tuple(confirmed), grid_size=len(grid),
        static_certificate=static_cert, traced_certificate=traced_cert,
        contract_reach=reach, runner_seconds=round(time.time() - started, 3),
    )
    return obs, confirmed


def _unmeasurable(task: Task, relations: Sequence[str], grid_size: int,
                  seconds: float, reason: str = "OBSERVATION_TIMEOUT") -> Observation:
    return Observation(
        verdict="UNMEASURABLE__" + reason, cases_total=len(task.cases), cases_passed=0,
        failing_indices=(), trace_lines=(), exceptions=(), per_case_facts=(),
        static_facts=frozenset(), relations=tuple(relations), grid_size=grid_size,
        static_certificate=None, traced_certificate=None, contract_reach=0,
        runner_seconds=round(seconds, 3),
    )


# ---------------------------------------------------------------------------
# Calculated prior: exact counts of EXECUTED VERDICTS.  No fitted parameter,
# no corpus, no gradient.  Every bit is computed from an outcome that ran.
# This is what "own weights from scratch, every bit calculated" means here.
# ---------------------------------------------------------------------------

COMPARISON_MIRROR = {"Lt": "LtE", "LtE": "Lt", "Gt": "GtE", "GtE": "Gt",
                     "Eq": "NotEq", "NotEq": "Eq", "Is": "IsNot", "IsNot": "Is",
                     "In": "NotIn", "NotIn": "In"}
BINARY_OPS = ["Add", "Sub", "Mult", "Div", "FloorDiv", "Mod", "Pow",
              "BitXor", "BitAnd", "BitOr", "LShift", "RShift"]
NAME_SWAPS = {"min": "max", "max": "min", "any": "all", "all": "any",
              "sum": "max", "len": "sum", "abs": "len"}
FAMILIES = ("COMPARISON_CLASS", "BINARY_OP", "AUG_ASSIGN_OP", "NAME_SWAP",
            "OFFSET", "CALL_ARG", "CONSTANT", "BOOL_OP", "GUARD_INSERT")
SIGNATURE_FAMILIES: dict[str, tuple[str, ...]] = {
    "OFF_BY_ONE": ("OFFSET", "CALL_ARG", "COMPARISON_CLASS", "CONSTANT"),
    "BOUNDARY": ("COMPARISON_CLASS", "OFFSET", "CONSTANT"),
    "EXCEPTION": ("GUARD_INSERT", "OFFSET", "CALL_ARG"),
    "COLLECTION_SHAPE": ("OFFSET", "CALL_ARG", "GUARD_INSERT", "CONSTANT"),
    "WRONG_VALUE": ("BINARY_OP", "AUG_ASSIGN_OP", "NAME_SWAP", "BOOL_OP", "CONSTANT"),
    "UNKNOWN": FAMILIES,
}


@dataclass
class Prior:
    """A calculated prior over edit families, keyed by the goal's signature."""
    tried: dict[str, int] = field(default_factory=dict)
    verified: dict[str, int] = field(default_factory=dict)
    signature: str = "UNKNOWN"

    def rank(self, families: Iterable[str]) -> list[str]:
        def score(family: str) -> tuple:
            t, v = self.tried.get(family, 0), self.verified.get(family, 0)
            # Exact Laplace rate over executed verdicts; no float learning rate.
            rate_num, rate_den = v + 1, t + 2
            match = 1 if family in SIGNATURE_FAMILIES.get(self.signature, ()) else 0
            return (match, rate_num / rate_den, -t)
        return sorted(dict.fromkeys(families), key=score, reverse=True)

    def record(self, family: str, ok: bool) -> None:
        self.tried[family] = self.tried.get(family, 0) + 1
        if ok:
            self.verified[family] = self.verified.get(family, 0) + 1

    def as_dict(self) -> dict[str, Any]:
        return {"signature": self.signature, "tried": dict(self.tried),
                "verified": dict(self.verified),
                "note": "EXACT_COUNTS_OF_EXECUTED_VERDICTS__NO_FITTED_PARAMETERS"}


def goal_signature(task: Task, obs: Observation) -> str:
    """Classify the discrepancy between the goal and the observed behaviour."""
    if any("Error" in e or "Exception" in e or e.startswith("traceback.") or e.startswith("trace:")
           for e in obs.exceptions):
        return "EXCEPTION"
    for i in obs.failing_indices:
        if i >= len(task.cases):
            continue
        args, expected = task.cases[i]
        if isinstance(expected, (list, tuple, dict, set, str)):
            return "COLLECTION_SHAPE"
        if isinstance(expected, bool):
            return "BOUNDARY"
        if isinstance(expected, (int, float)):
            return "OFF_BY_ONE" if abs(float(expected)) <= 2 else "WRONG_VALUE"
    return "UNKNOWN"


# ---------------------------------------------------------------------------
# Goal-conditioned synthesis: candidates are built ONLY on positions that
# actually executed on the failing path, in families the goal selects.
# ---------------------------------------------------------------------------


@dataclass
class Candidate:
    family: str
    source: str
    description: str
    position: int


def _positions(tree: ast.AST, executed_lines: set[int]) -> list[tuple[int, ast.AST, ast.AST, str]]:
    out: list[tuple[int, ast.AST, ast.AST, str]] = []
    for parent in ast.walk(tree):
        for field_name, value in ast.iter_fields(parent):
            children = value if isinstance(value, list) else [value]
            for index, node in enumerate(children):
                if not isinstance(node, ast.AST):
                    continue
                role = f"{field_name}[{index}]" if isinstance(value, list) else field_name
                line = getattr(node, "lineno", None) or getattr(parent, "lineno", None)
                if line is None or (executed_lines and int(line) not in executed_lines):
                    continue
                out.append((int(line), parent, node, role))
    return out


def _install(parent: ast.AST, role: str, new: ast.AST) -> None:
    if role.endswith("]"):
        field_name, index = role[:-1].split("[")
        getattr(parent, field_name)[int(index)] = new
    else:
        setattr(parent, role, new)


def _name(text: str) -> ast.Name:
    return ast.Name(id=text, ctx=ast.Load())


def _byte_offsets(source: str) -> list[int]:
    """Byte offsets of each line start.  ast line/col offsets are UTF-8 bytes."""
    offsets = [0]
    for line in source.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line.encode("utf-8")))
    return offsets


def _render_surgical(source: str, node: ast.AST, replacement: ast.AST) -> str | None:
    """Replace exactly ONE node's source span.  No whole-file reprint, no
    docstring churn, no cosmetic diff: the best part is no part."""
    try:
        new_text = ast.unparse(replacement)
    except (RecursionError, ValueError, TypeError, SyntaxError):
        return None
    lineno = getattr(node, "lineno", None)
    end_lineno = getattr(node, "end_lineno", None)
    if lineno is None or end_lineno is None:
        return None
    offsets = _byte_offsets(source)
    start = offsets[lineno - 1] + int(getattr(node, "col_offset", 0))
    finish = offsets[end_lineno - 1] + int(getattr(node, "end_col_offset", 0))
    raw = source.encode("utf-8")
    if not (0 <= start <= finish <= len(raw)):
        return None
    try:
        return (raw[:start] + new_text.encode("utf-8") + raw[finish:]).decode("utf-8")
    except UnicodeDecodeError:
        return None


def synthesize(task: Task, source: str, obs: Observation, prior: Prior,
               *, cap: int = 260) -> list[Candidate]:
    tree = ast.parse(source, filename=str(task.program_path))
    executed = set(obs.trace_lines)
    if not executed:
        return []
    positions = _positions(tree, executed)
    literals: list[Any] = []
    for args, expected in task.cases:
        for value in [*args, expected]:
            if isinstance(value, (int, float, str, bool)) and value not in literals:
                literals.append(value)
    ordered = prior.rank(FAMILIES)
    out: list[Candidate] = []
    seen: set[str] = {source}

    def emit(family: str, rendered: str | None, description: str, line: int) -> None:
        if not rendered or rendered in seen or rendered == source:
            return
        seen.add(rendered)
        out.append(Candidate(family=family, source=rendered,
                             description=description, position=line))

    # Genuine statement-insertion templates with an explicit precondition,
    # grounded in the published expected values.  Insertion is a candidate only.
    for literal, precondition in _guard_literals(task):
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                    or node.name != task.function_name or not node.args.args or not node.body:
                continue
            first = node.body[0]
            line_start = _byte_offsets(source)[first.lineno - 1]
            indent = " " * int(getattr(first, "col_offset", 0))
            param = node.args.args[0].arg
            guard = ast.If(test=precondition(param), body=[ast.Return(value=literal)], orelse=[])
            try:
                text = indent + ast.unparse(guard) + "\n"
            except (RecursionError, ValueError, TypeError, SyntaxError):
                break
            raw = source.encode("utf-8")
            rendered = (raw[:line_start] + text.encode("utf-8") + raw[line_start:]).decode("utf-8")
            emit("GUARD_INSERT", rendered, f"GUARD_INSERT@{node.name}", int(first.lineno))
            break

    for family in ordered:
        if family == "GUARD_INSERT":
            continue
        for line, parent, node, role in positions:
            for replacement in _replacements(family, node, literals):
                emit(family, _render_surgical(source, node, replacement),
                     f"{family}@{role}:{type(node).__name__}", line)
                if len(out) >= cap:
                    return out
    return out


def _guard_literals(task: Task) -> list[tuple[ast.AST, Any]]:
    """The only insertion preconditions this contract can justify."""
    out: list[tuple[ast.AST, Any]] = []
    seen: set[str] = set()
    for _args, expected in task.cases:
        literal: Any = None
        if isinstance(expected, (list, tuple, dict, str)) and not expected:
            literal = type(expected)()
        elif isinstance(expected, bool):
            literal = False
        elif isinstance(expected, (int, float)) and expected == 0:
            literal = 0
        if literal is None:
            continue
        key = repr(literal)
        if key in seen:
            continue
        seen.add(key)
        out.append((ast.Constant(value=literal), lambda param: ast.UnaryOp(
            op=ast.Not(), operand=_name(param))))
        out.append((ast.Constant(value=literal), lambda param: ast.Compare(
            left=_name(param), ops=[ast.Eq()], comparators=[ast.Constant(value=0)])))
    return out[:4]


def _replacements(family: str, node: ast.AST, literals: Sequence[Any]) -> list[ast.AST]:
    out: list[ast.AST] = []
    if family == "COMPARISON_CLASS" and isinstance(node, ast.Compare) and len(node.ops) == 1:
        for op_name in ("Lt", "LtE", "Gt", "GtE", "Eq", "NotEq"):
            if op_name != type(node.ops[0]).__name__:
                n = copy.deepcopy(node)
                n.ops = [getattr(ast, op_name)()]
                out.append(n)
    elif family == "BINARY_OP" and isinstance(node, ast.BinOp):
        for name in BINARY_OPS:
            if name != type(node.op).__name__:
                n = copy.deepcopy(node)
                n.op = getattr(ast, name)()
                out.append(n)
    elif family == "AUG_ASSIGN_OP" and isinstance(node, ast.AugAssign):
        for name in BINARY_OPS:
            if name != type(node.op).__name__:
                n = copy.deepcopy(node)
                n.op = getattr(ast, name)()
                out.append(n)
    elif family == "BOOL_OP" and isinstance(node, ast.BoolOp):
        for name in ("And", "Or"):
            if name != type(node.op).__name__:
                n = copy.deepcopy(node)
                n.op = getattr(ast, name)()
                out.append(n)
    elif family == "NAME_SWAP" and isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        target = NAME_SWAPS.get(node.func.id)
        if target:
            n = copy.deepcopy(node)
            n.func = _name(target)
            out.append(n)
    elif family == "OFFSET" and isinstance(node, (ast.Name, ast.Constant, ast.Call, ast.BinOp, ast.Subscript)):
        for delta in (1, -1):
            out.append(ast.BinOp(left=copy.deepcopy(node),
                                 op=ast.Add() if delta == 1 else ast.Sub(),
                                 right=ast.Constant(value=1)))
        out.append(ast.Call(func=_name("max"),
                            args=[ast.Constant(value=0), copy.deepcopy(node)], keywords=[]))
        if isinstance(node, (ast.Name, ast.Call)):
            out.append(ast.Subscript(value=copy.deepcopy(node),
                                     slice=ast.Slice(lower=ast.Constant(value=1)), ctx=ast.Load()))
    elif family == "CALL_ARG" and isinstance(node, ast.Call):
        for pos, arg in enumerate(node.args):
            if isinstance(arg, (ast.Name, ast.BinOp, ast.Constant)):
                for delta in (1, -1):
                    n = copy.deepcopy(node)
                    n.args[pos] = ast.BinOp(left=copy.deepcopy(arg),
                                            op=ast.Add() if delta == 1 else ast.Sub(),
                                            right=ast.Constant(value=1))
                    out.append(n)
    elif family == "CONSTANT" and isinstance(node, ast.Constant):
        for value in literals:
            if value != node.value and isinstance(value, (int, float, str, bool)):
                out.append(ast.Constant(value=value))
    return out


# ---------------------------------------------------------------------------
# Verification: a candidate's own pass is a filter, never a verdict.
# ---------------------------------------------------------------------------


def screen_variants(task: Task, obs: Observation, sources: Sequence[str],
                    *, timeout_s: float = 150.0) -> list[dict[str, Any]]:
    """Batch-execute candidates in ONE bounded child, on published cases + wider grid."""
    if not sources:
        return []
    try:
        return _run_child(_payload(task, sources, obs.relations), timeout_s, task.root)
    except (subprocess.TimeoutExpired, RuntimeError, ValueError):
        return [{"index": i, "passed": 0, "total": len(task.cases),
                 "errors": list(range(len(task.cases))),
                 "grid_violations": [{"relation": "SCREEN_TIMEOUT"}],
                 "load_error": "SCREEN_TIMEOUT"} for i in range(len(sources))]


def fresh_verdict(task: Task, source: str, *, timeout_s: int = 120) -> dict[str, Any]:
    """The corpus's OWN pytest, on a FRESH copy. This is the only repair verdict.

    Reuses ``canonical.tools.quixbugs_end_to_end_repair_measure_v1.run_pytest``
    so the harness, the environment and the integrity rules are not re-invented.
    """
    from canonical.tools import quixbugs_end_to_end_repair_measure_v1 as harness

    with tempfile.TemporaryDirectory(prefix="contract_fresh_") as tmp:
        fresh = pathlib.Path(tmp) / "task"
        shutil.copytree(task.root, fresh)
        if (fresh / ANSWER_KEY).exists():
            raise RuntimeError("ANSWER_KEY_REACHED_THE_FRESH_COPY")
        (fresh / task.program_rel).write_text(source, encoding="utf-8")
        if _sha((fresh / task.test_rel).read_bytes()) != task.test_sha256:
            raise RuntimeError("TEST_FILE_CHANGED")
        result = harness.run_pytest(fresh, task.test_rel, timeout=timeout_s)
        return {"returncode": int(result["returncode"]),
                "timed_out": bool(result["timed_out"]),
                "seconds": float(result["seconds"]),
                "tail": list(result["tail"])}


# ---------------------------------------------------------------------------
# One autonomous loop.
# ---------------------------------------------------------------------------


def solve(task: Task, *, candidate_cap: int = 260, fresh_cap: int = 3,
          timeout_s: float = 25.0) -> dict[str, Any]:
    """Derive the goal, certify the vocabulary, synthesize, verify, identify."""
    from canonical.runtime import applicability_v1 as APP
    from canonical.runtime import contrast_selection_v1 as CS

    started = time.time()
    if not task.cases:
        return _report(task, "UNMEASURABLE__NO_PUBLISHED_JSON_CASES", obs=None, candidates=0,
                       reason="THIS_TASK_HAS_NO_EXECUTABLE_PUBLISHED_CONTRACT_DATA", started=started)
    source = task.program_path.read_text(encoding="utf-8")
    obs, relations = observe(task, source, timeout_s=timeout_s)
    if obs.verdict != "OBSERVED":
        return _report(task, "REFUSED__" + obs.verdict, obs=obs, candidates=0,
                       reason="NO_EXECUTED_CONTRACT_OBSERVABLE", started=started)
    if not obs.failing_indices:
        return _report(task, "REFUSED__BASELINE_ALREADY_PASSES", obs=obs, candidates=0,
                       reason="NO_FAILING_CASE_TO_INFER_THE_GOAL_FROM", started=started)
    if not obs.trace_lines:
        return _report(task, "REFUSED__NO_EXECUTION_TRACE", obs=obs, candidates=0,
                       reason="GOAL_IS_NOT_GROUNDED_IN_AN_EXECUTED_POSITION", started=started)
    # The certificate bounds what can be LEARNED (identified as a permanent
    # rule), not what can be DONE (a candidate edit verified by an independent
    # oracle).  Conflating the two is the error this module exists to avoid:
    # a repair judged by the corpus's own test never needs a learned scope.
    # When both vocabularies are insufficient, the rule is NOT admitted; the
    # repair still proceeds and is labelled as such in the receipt.
    learn_refused = bool(obs.static_certificate and obs.traced_certificate
                         and obs.static_certificate.get("unrepairable_by_repetition")
                         and obs.traced_certificate.get("unrepairable_by_repetition"))
    signature = goal_signature(task, obs)
    prior = Prior(signature=signature)
    candidates = synthesize(task, source, obs, prior, cap=candidate_cap)
    if not candidates:
        return _report(task, "REFUSED__NO_GROUNDED_CANDIDATES", obs=obs, candidates=0,
                       reason="HYPOTHESIS_SPACE_EMPTY_ON_THE_EXECUTED_PATH", started=started,
                       prior=prior, learn_refused=learn_refused)

    rows = screen_variants(task, obs, [c.source for c in candidates])
    screen_by_index = {int(r["index"]): r for r in rows}
    evidence: list[tuple[list[str], bool]] = []
    accepted: list[tuple[int, Candidate]] = []
    passed_published_but_refused_by_contract = 0
    for index, candidate in enumerate(candidates):
        row = screen_by_index.get(index, {})
        all_cases = int(row.get("passed", 0)) == int(row.get("total", len(task.cases)))
        if all_cases and row.get("grid_violations") and not row.get("load_error"):
            passed_published_but_refused_by_contract += 1
        ok = all_cases and not row.get("grid_violations") and not row.get("load_error")
        prior.record(candidate.family, bool(ok))
        evidence.append(([f"family.{candidate.family}", f"position.{candidate.position}",
                          f"goal.{signature}"], bool(ok)))
        if ok and len(accepted) < fresh_cap:
            accepted.append((index, candidate))

    identified: dict[str, Any]
    contrast: dict[str, Any] | None = None
    try:
        learned = APP.learn(evidence)
        identified = {"status": learned.status,
                      "survivors": len(learned.survivors) if hasattr(learned, "survivors") else None}
        states = [frozenset(facts) for facts, _ in evidence]
        contrast = CS.select_contrast(evidence, states).as_row()
    except Exception as exc:  # a diagnostic failure is reported, never a pass
        identified = {"status": "IDENTIFICATION_INSTRUMENT_REFUSED", "reason": type(exc).__name__}

    verified: list[dict[str, Any]] = []
    for index, candidate in accepted:
        verdict = fresh_verdict(task, candidate.source)
        verified.append({"family": candidate.family, "description": candidate.description, **verdict})
        if verdict["returncode"] == 0 and not verdict["timed_out"]:
            return _report(task, "REPAIRED__CORPUS_TEST_PASSES", obs=obs,
                           candidates=len(candidates), prior=prior, identified=identified,
                           contrast=contrast, screened=len(rows), fresh_verdicts=verified,
                           winning_family=candidate.family, winning_index=index,
                           winning_diff="\n".join(difflib.unified_diff(
                               source.splitlines(), candidate.source.splitlines(),
                               fromfile="published_buggy", tofile="candidate", lineterm="")),
                           passed_published_but_refused_by_contract=passed_published_but_refused_by_contract,
                           learn_refused=learn_refused,
                           reason="FRESH_COPY_VERDICT_IS_THE_ONLY_EVIDENCE", started=started)
    return _report(task, "NOT_REPAIRED__NO_CANDIDATE_PASSED_THE_CORPUS_TEST", obs=obs,
                   candidates=len(candidates), prior=prior, identified=identified,
                   contrast=contrast, screened=len(rows), fresh_verdicts=verified,
                   passed_published_but_refused_by_contract=passed_published_but_refused_by_contract,
                   learn_refused=learn_refused,
                   reason="ALL_GROUNDED_CANDIDATES_FAILED_AN_INDEPENDENT_VERDICT",
                   started=started)


def _report(task: Task, status: str, *, obs: Observation | None, candidates: int,
            reason: str, started: float, prior: Prior | None = None,
            identified: dict | None = None, contrast: dict | None = None,
            screened: int = 0, fresh_verdicts: Sequence[dict] = (),
            winning_family: str | None = None, winning_index: int | None = None,
            winning_diff: str | None = None,
            passed_published_but_refused_by_contract: int = 0,
            learn_refused: bool = False) -> dict[str, Any]:
    def cert(c: dict | None) -> dict | None:
        if not c:
            return None
        return {k: c.get(k) for k in ("kind", "reason", "shared_facts",
                                      "unrepairable_by_repetition", "what_would_repair_it")}
    closure = "SEE_CERTIFICATES"
    if obs and obs.static_certificate and obs.static_certificate.get("unrepairable_by_repetition") \
            and not obs.traced_certificate:
        closure = "STATIC_INSUFFICIENT__EXECUTED_OBSERVABLES_RESTORE_SEPARATION"
    return {
        "schema": SCHEMA, "task": task.name, "status": status, "reason": reason,
        "authority": AUTHORITY, "model_dependency_count": MODEL_DEPENDENCY_COUNT,
        "program_sha256": task.program_sha256, "test_sha256": task.test_sha256,
        "answer_key_absent": not (task.root / ANSWER_KEY).exists(),
        "goal": {
            "cases_total": obs.cases_total if obs else 0,
            "cases_passed": obs.cases_passed if obs else 0,
            "failing_cases": len(obs.failing_indices) if obs else 0,
            "signature": prior.signature if prior else None,
            "relations": list(obs.relations) if obs else [],
            "grid_size": obs.grid_size if obs else 0,
            "contract_reach": obs.contract_reach if obs else 0,
            "trace_lines": list(obs.trace_lines)[:40] if obs else [],
            "exceptions": list(obs.exceptions) if obs else [],
        },
        "identifiability": {
            "static_certificate": cert(obs.static_certificate) if obs else None,
            "traced_certificate": cert(obs.traced_certificate) if obs else None,
            "closure": closure, "learn": identified, "chosen_contrast": contrast,
            "permanent_rule_admitted": bool(
                identified and identified.get("status") == "IDENTIFIED__ONE_CONSISTENT_REQUIREMENT"),
            "learn_refused_by_certificate": learn_refused,
        },
        "synthesis": {"candidates": candidates, "screened": screened,
                      "fresh_verdicts": list(fresh_verdicts),
                      "winning_family": winning_family, "winning_index": winning_index,
                      "winning_diff": winning_diff,
                      "passed_published_but_refused_by_contract": passed_published_but_refused_by_contract,
                      "prior": prior.as_dict() if prior else None},
        "seconds": round(time.time() - started, 2),
    }
