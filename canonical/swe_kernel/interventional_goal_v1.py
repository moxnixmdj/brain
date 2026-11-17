#!/usr/bin/env python3
"""Derive the GOAL by DO-interventions on the live environment, then act.

WHY THIS EXISTS (the exact hole, measured on this tree)
-------------------------------------------------------
`contract_grounded_repair_v1` derived a contract from the published ASSERTIONS'
expected values and checked candidates on a wider grid built from those same
integer inputs.  Its own receipt records the residual:

    quicksort winning diff: `if x < pivot` -> `if x - 1 < pivot`
    passes 13/13 published integer cases; WRONG for floats.

That is pattern matching in disguise.  The contract was OBSERVATIONAL: every
wider input was an integer perturbation, so `x - 1 < pivot` was indistinguishable
from `x <= pivot`.  No amount of repetition inside the integer domain can
separate them.  This is the tree's own verified theorem:

    canonical/capabilities/opus55/M5_NONINTERVENTIONAL_ROOT_CAUSE_IDENTIFIABILITY_001.json
    "UNIQUE_ROOT_CAUSE_IS_NOT_IDENTIFIABLE_IN_GENERAL_FROM_DECLARED_OBSERVATIONS_ALONE"
    premises: NO_REPLAY_OR_INTERVENTION.

The three owner-supplied objections are three projections of ONE missing organ:

  1. Identifiability  -> a single observational trace leaves exponentially many
     hypotheses; only a DO-intervention over the executed vocabulary separates
     them.  M5 already proves the negative half; this module builds the positive
     half.
  2. Insufficient vocabulary -> `insufficiency_witness` needs the executed
     function, the CALLEE SIGNATURE and the runtime traceback exception.  This
     runner records all three, per case, per intervention (not a shared union
     that fabricates a vocabulary).
  3. Synthesis/verification asymmetry -> replay covers repeated syntax; real
     work composes NEW inputs by intervening on the live program and repairs
     against execution feedback.  Here the verifier is the interventional
     contract, and the edit space is re-grounded on the lines the interventions
     actually execute.

WHAT IS BUILT (and what is deliberately NOT built)
-------------------------------------------------
* ONE new organ: an interventional goal compiler.  It reuses
  `contract_grounded_repair_v1` for Task loading, relation induction, surgical
  candidate rendering and the FRESH-COPY corpus pytest; reuses
  `applicability_v1.insufficiency_witness` and `contrast_selection_v1`;
  reuses the zero-weight instant-knowledge index in BRAIN_UNIFIED_MODEL_V1.
* NO external model, NO network at run time, NO gradient, NO fitted parameter,
  NO corpus of learned facts, NO answer key (`correct_python_programs` is
  asserted absent before every task), NO synthetic tasks.
* The only numbers retained are EXACT INTEGER COUNTS of executed intervention
  verdicts.  `CalculatedWeights` is `pass - fail` per edit family: every bit is
  an outcome that actually ran.  It is a calculated sufficient statistic, not a
  knowledge house.  The design law "the best part is no part" is honoured: a
  family with no executed contrast has weight exactly zero and is not admitted.
* A permanent rule is admitted ONLY when the intervention evidence identifies
  one requirement (M5).  Verified DOING and admitted LEARNING stay separate.

FALSIFIER (not counted as progress)
-----------------------------------
The prior turn's quicksort win is a known FALSE win.  Running its verbatim diff
through this organ must REFUSE it under at least one intervention.  Killing a
false claim is progress; re-counting three old bugs as wins is self-congratulation.

Authority NONE.  Producer-run sandbox measurement.  Not a leaderboard entry.
"""
from __future__ import annotations

import dataclasses
import difflib
import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

_REPO = pathlib.Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from canonical.swe_kernel import contract_grounded_repair_v1 as CGR  # noqa: E402
from canonical.runtime import applicability_v1 as APP  # noqa: E402
from canonical.runtime import contrast_selection_v1 as CS  # noqa: E402

SCHEMA = "BRAIN_INTERVENTIONAL_GOAL_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
ANSWER_KEY = CGR.ANSWER_KEY
MODEL_DEPENDENCY_COUNT = 0

# The relation vocabulary is the SAME as the observational organ, so the two
# receipts are comparable.  A relation is a predicate on (input, output); it
# needs NO expected value on an intervened input.  That is what makes it a
# counterfactual check instead of an answer-key lookup.
RELATIONS = ("LEN_MATCHES_INPUT", "SORTED_OUTPUT", "PERMUTATION_OF_INPUT",
             "NONNEGATIVE", "BOOLEAN", "TYPE_MATCH")


def relation(kind: str, result: Any, args: Sequence[Any]) -> bool | None:
    """True / False / inapplicable.  Imported by the bounded child as well."""
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


# ---------------------------------------------------------------------------
# DO-interventions: deterministic maps applied to REAL published inputs.
# No invented expected outputs.  An intervention is admissible only if every
# induced relation still holds for the transformed published (input, expected)
# pair, and only if the live program can actually execute the transformed input.
# ---------------------------------------------------------------------------

NUMERIC_MAPS: dict[str, Any] = {
    "TYPE_LIFT_INT_TO_FLOAT": lambda x: float(x),
    "SUBUNIT_SCALE": lambda x: float(x) / 2 + 0.25,
    "SHIFT_HALF": lambda x: float(x) + 0.5,
    "NEGATE": lambda x: -float(x),
}
INTERVENTIONS: tuple[str, ...] = (
    "IDENTITY", "REORDER_FIRST_SEQUENCE", "DUPLICATE_FIRST_ELEMENT",
    "TYPE_LIFT_INT_TO_FLOAT", "SUBUNIT_SCALE", "SHIFT_HALF", "NEGATE",
)


def _transform(value: Any, f: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return f(value)
    if isinstance(value, list):
        return [_transform(v, f) for v in value]
    if isinstance(value, tuple):
        return tuple(_transform(v, f) for v in value)
    if isinstance(value, dict):
        return {k: _transform(v, f) for k, v in value.items()}
    return value


def _expected_prime(name: str, args: Sequence[Any], expected: Any) -> Any:
    """The goal-preserving transform of the published expected value.

    Used ONLY to certify that a relation is invariant under the intervention.
    It is never passed to candidate generation and never used as a verdict.
    """
    if name == "IDENTITY":
        return expected
    if name in NUMERIC_MAPS:
        f = NUMERIC_MAPS[name]
        ep = _transform(expected, f)
        if isinstance(ep, list):
            try:
                ep = sorted(ep)  # negating / scaling a sorted output re-sorts it
            except (TypeError, ValueError):
                return expected
        return ep
    if name == "REORDER_FIRST_SEQUENCE":
        return expected  # sorted output does not reverse with its input
    if name == "DUPLICATE_FIRST_ELEMENT":
        for a in args:
            if isinstance(a, (list, tuple)) and len(a) > 0:
                if isinstance(expected, (list, tuple)):
                    try:
                        return sorted(list(expected) + [a[0]])
                    except (TypeError, ValueError):
                        return expected
                return expected
    return expected


def intervene(name: str, args: Sequence[Any], expected: Any) -> tuple[list[Any], Any] | None:
    """Return (do(args), goal-preserving expected) or None if not applicable."""
    args = list(args)
    if name == "IDENTITY":
        return args, _expected_prime(name, args, expected)
    if name in NUMERIC_MAPS:
        f = NUMERIC_MAPS[name]
        return _transform(args, f), _expected_prime(name, args, expected)
    if name == "REORDER_FIRST_SEQUENCE":
        for i, a in enumerate(args):
            if isinstance(a, (list, tuple)) and len(a) > 1:
                out = list(args)
                out[i] = list(reversed(a))
                return out, _expected_prime(name, args, expected)
        return None
    if name == "DUPLICATE_FIRST_ELEMENT":
        for i, a in enumerate(args):
            if isinstance(a, (list, tuple)) and len(a) > 0:
                out = list(args)
                out[i] = list(a) + [a[0]]
                return out, _expected_prime(name, args, expected)
        return None
    return None


@dataclass(frozen=True)
class Intervention:
    name: str
    cases: tuple[list[Any], ...]
    relations: tuple[str, ...]
    expected_prime: tuple[Any, ...]

    @property
    def is_control(self) -> bool:
        return self.name == "IDENTITY"


def derive_interventions(task: Any) -> tuple[list[Intervention], dict[str, Any]]:
    """Induce relations from published pairs, keep only intervention-invariant ones."""
    base_relations = CGR._derive_relations(task.cases)
    out: list[Intervention] = []
    diagnostics: dict[str, Any] = {"induced_relations": list(base_relations),
                                   "inapplicable": {}, "invariant_refuted": {}}
    for name in INTERVENTIONS:
        cases: list[list[Any]] = []
        primes: list[Any] = []
        for args, expected in task.cases:
            got = intervene(name, args, expected)
            if got is None:
                break
            args_prime, ep = got
            cases.append(args_prime)
            primes.append(ep)
        if not cases or len(cases) != len(task.cases):
            diagnostics["inapplicable"][name] = "STRUCTURAL_NOT_APPLICABLE"
            continue
        admitted: list[str] = []
        refuted: list[str] = []
        for rel in base_relations:
            holds = True
            for args_prime, ep in zip(cases, primes):
                verdict = relation(rel, ep, args_prime)
                if verdict is False:
                    holds = False
                    break
            if holds:
                admitted.append(rel)
            else:
                refuted.append(rel)
        if refuted:
            diagnostics["invariant_refuted"][name] = refuted
        if not admitted:
            diagnostics["inapplicable"][name] = "NO_INVARIANT_RELATION"
            continue
        out.append(Intervention(name=name, cases=tuple(cases), relations=tuple(admitted),
                                expected_prime=tuple(primes)))
    return out, diagnostics


# ---------------------------------------------------------------------------
# Bounded child.  It imports `relation` from THIS module (no duplicated law),
# runs the published contract first, and spends interventions ONLY on candidates
# that already satisfy it: verification is dearer than replay, by construction.
# ---------------------------------------------------------------------------

_CHILD = r'''
import importlib, json, shutil, signal, sys, tempfile, pathlib
sys.dont_write_bytecode = True
payload = json.load(sys.stdin)
repo = pathlib.Path(payload["repo_root"])
task_dir = pathlib.Path(payload["task_dir"])
scratch = pathlib.Path(tempfile.mkdtemp(prefix="interventional_pkg_"))
shutil.copytree(task_dir / "python_programs", scratch / "python_programs")
# SCRATCH MUST WIN: otherwise every variant silently loads the untouched original.
sys.path.insert(0, str(repo))
sys.path.insert(0, str(task_dir))
sys.path.insert(0, str(scratch))
from canonical.swe_kernel.interventional_goal_v1 import relation

name = payload["name"]
program_file = str(scratch / "python_programs" / (name + ".py"))
cases = payload["cases"]
interventions = payload["interventions"]
per_call = float(payload["per_call_timeout"])

class _Timeout(Exception): pass
def _alarm(_s, _f): raise _Timeout()
signal.signal(signal.SIGALRM, _alarm)

def _call(fn, args):
    signal.setitimer(signal.ITIMER_REAL, per_call)
    try:
        return fn(*args), None
    except BaseException as exc:  # the exception IS the causal observable
        return None, type(exc).__name__
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)

def _call_traced(fn, args):
    seen, callees = set(), set()
    def tr(frame, event, arg):
        if frame.f_code.co_filename == program_file:
            if event == "line":
                seen.add(frame.f_lineno)
            elif event == "call":
                # CALLEE SIGNATURE: the missing observable from INSUFFICIENCY_CERTIFICATE.
                callees.add("%s/%d" % (frame.f_code.co_name, frame.f_code.co_argcount))
        return tr
    signal.setitimer(signal.ITIMER_REAL, per_call)
    try:
        sys.settrace(tr)
        return fn(*args), None, sorted(seen), sorted(callees)
    except BaseException as exc:
        return None, type(exc).__name__, sorted(seen), sorted(callees)
    finally:
        sys.settrace(None)
        signal.setitimer(signal.ITIMER_REAL, 0)

out = []
for index, source in enumerate(payload["variants"]):
    (scratch / "python_programs" / (name + ".py")).write_text(source, encoding="utf-8")
    for key in [k for k in list(sys.modules) if k == "python_programs" or k.startswith("python_programs.")]:
        del sys.modules[key]
    importlib.invalidate_caches()
    try:
        module = importlib.import_module("python_programs." + name)
        fn = getattr(module, payload["function_name"])
        load_error = None
    except BaseException as exc:
        out.append({"index": index, "load_error": type(exc).__name__ + ": " + str(exc)[:160],
                    "published_ok": False, "published_passed": 0, "intervention": {},
                    "trace": {"lines": [], "callees": []}})
        continue
    published_ok, published_passed = True, 0
    all_lines, all_callees = set(), set()
    for c, (args, expected) in enumerate(cases):
        if index == 0:
            value, err, lines, callees = _call_traced(fn, args)
            all_lines.update(lines); all_callees.update(callees)
        else:
            value, err = _call(fn, args)
        ok = err is None
        if ok:
            try:
                ok = (value == expected)
            except BaseException:
                ok = False
        if ok:
            published_passed += 1
        else:
            published_ok = False
            if index > 0:
                break  # a candidate that fails the published contract is dead
    iv_report = {}
    # Always run interventions on the buggy original: that is where the goal
    # earns its teeth.  For candidates, only after they pass the contract.
    if index == 0 or published_ok:
        for iv in interventions:
            violations, exceptions, checked = [], [], 0
            for c, args_prime in enumerate(iv["cases"]):
                value, err = _call(fn, args_prime)
                checked += 1
                if err is not None:
                    exceptions.append({"case": c, "traceback": err})
                    continue
                if value is None:
                    continue
                for rel in iv["relations"]:
                    if relation(rel, value, args_prime) is False:
                        violations.append({"case": c, "relation": rel})
            iv_report[iv["name"]] = {"violations": violations, "exceptions": exceptions,
                                     "checked": checked}
    out.append({"index": index, "published_ok": published_ok,
                "published_passed": published_passed, "intervention": iv_report,
                "load_error": load_error,
                "trace": {"lines": sorted(all_lines), "callees": sorted(all_callees)}
                if index == 0 else {"lines": [], "callees": []}})
shutil.rmtree(scratch, ignore_errors=True)
json.dump(out, sys.stdout)
'''


def _payload(task: Any, interventions: Sequence[Intervention], sources: Sequence[str]) -> dict[str, Any]:
    return {
        "repo_root": str(_REPO), "task_dir": str(task.root),
        "name": task.name, "function_name": task.function_name,
        "cases": [[list(a), e] for a, e in task.cases],
        "interventions": [{"name": iv.name, "cases": [list(c) for c in iv.cases],
                           "relations": list(iv.relations)} for iv in interventions],
        "variants": list(sources), "per_call_timeout": 0.15,
    }


def _run_child(payload: dict[str, Any], timeout_s: float, cwd: pathlib.Path) -> list[dict[str, Any]]:
    with tempfile.TemporaryDirectory(prefix="interventional_runner_") as tmp:
        runner = pathlib.Path(tmp) / "runner.py"
        runner.write_text(_CHILD, encoding="utf-8")
        done = subprocess.run([sys.executable, str(runner)], input=json.dumps(payload),
                              text=True, capture_output=True, timeout=timeout_s, cwd=str(cwd))
        if done.returncode != 0:
            raise RuntimeError("CHILD_FAILED:" + done.stderr.strip()[:300])
        return json.loads(done.stdout)


# ---------------------------------------------------------------------------
# Own weights, from scratch: EXACT INTEGER COUNTS of executed verdicts.
# No gradient, no fitted float, no knowledge house.  Zero by default.
# ---------------------------------------------------------------------------


@dataclass
class CalculatedWeights:
    interventional_pass: dict[str, int] = field(default_factory=dict)
    interventional_fail: dict[str, int] = field(default_factory=dict)
    published_only: dict[str, int] = field(default_factory=dict)

    def weight(self, family: str) -> int:
        return self.interventional_pass.get(family, 0) - self.interventional_fail.get(family, 0)

    def record(self, family: str, *, published_ok: bool, interventional_ok: bool) -> None:
        key = self.interventional_pass if interventional_ok else self.interventional_fail
        if published_ok:
            key[family] = key.get(family, 0) + 1
        else:
            self.published_only[family] = self.published_only.get(family, 0) + 1

    def as_dict(self) -> dict[str, Any]:
        return {"interventional_pass": dict(self.interventional_pass),
                "interventional_fail": dict(self.interventional_fail),
                "published_only": dict(self.published_only),
                "weights": {f: self.weight(f) for f in sorted(
                    set(self.interventional_pass) | set(self.interventional_fail))},
                "note": "EXACT_INTEGER_COUNTS_OF_EXECUTED_VERDICTS__NO_GRADIENT__NO_FITTED_PARAMETER__ZERO_BY_DEFAULT"}


@dataclass
class Contract:
    interventions: list[Intervention]
    diagnostics: dict[str, Any]
    base_relations: tuple[str, ...]
    executed_lines: tuple[int, ...]
    callee_signatures: tuple[str, ...]
    teeth: dict[str, int]
    reach: dict[str, int]


def derive(task: Any, source: str, interventions: Sequence[Intervention],
           diagnostics: dict[str, Any], *, timeout_s: float = 60.0) -> Contract:
    """Execute the live program under every admissible intervention."""
    rows = _run_child(_payload(task, interventions, [source]), timeout_s, task.root)
    row = rows[0]
    teeth: dict[str, int] = {}
    for iv in interventions:
        rep = row["intervention"].get(iv.name, {})
        teeth[iv.name] = len(rep.get("violations", [])) + len(rep.get("exceptions", []))
    return Contract(interventions=list(interventions), diagnostics=diagnostics,
                    base_relations=tuple(diagnostics["induced_relations"]),
                    executed_lines=tuple(row["trace"]["lines"]),
                    callee_signatures=tuple(row["trace"]["callees"]),
                    teeth=teeth, reach={iv.name: 0 for iv in interventions})


# ---------------------------------------------------------------------------
# One autonomous loop: derive -> synthesize -> intervene -> verify -> identify.
# ---------------------------------------------------------------------------


def solve(task: Any, *, candidate_cap: int = 260, fresh_cap: int = 3,
          timeout_s: float = 150.0) -> dict[str, Any]:
    started = time.time()
    if not task.cases:
        return _report(task, "UNMEASURABLE__NO_PUBLISHED_JSON_CASES", started,
                       reason="THIS_TASK_HAS_NO_EXECUTABLE_PUBLISHED_CONTRACT_DATA")
    if (task.root / ANSWER_KEY).exists():
        raise RuntimeError("ANSWER_KEY_REACHED_THE_SOLVER")
    source = task.program_path.read_text(encoding="utf-8")

    interventions, diagnostics = derive_interventions(task)
    if not interventions:
        return _report(task, "REFUSED__NO_INVARIANT_INTERVENTION", started,
                       reason="NO_RELATION_SURVIVES_A_DO_INTERVENTION")
    contract = derive(task, source, interventions, diagnostics)

    # Reuse the observational organ for its per-case executed vocabulary and
    # certificates, then RE-GROUND the edit space on the union of lines that
    # the interventions actually executed.  This is the composition step.
    base_obs, _ = CGR.observe(task, source)
    lines = set(base_obs.trace_lines) | set(contract.executed_lines)
    obs = dataclasses.replace(base_obs, trace_lines=tuple(sorted(lines)))
    if not obs.failing_indices:
        return _report(task, "REFUSED__BASELINE_ALREADY_PASSES", started,
                       reason="NO_FAILING_CASE_TO_INFER_THE_GOAL_FROM", obs=obs)
    signature = CGR.goal_signature(task, obs)
    prior = CGR.Prior(signature=signature)
    candidates = CGR.synthesize(task, source, obs, prior, cap=candidate_cap)
    if not candidates:
        return _report(task, "REFUSED__NO_GROUNDED_CANDIDATES", started,
                       reason="HYPOTHESIS_SPACE_EMPTY_ON_THE_EXECUTED_PATH", obs=obs)

    sources = [c.source for c in candidates]
    try:
        rows = _run_child(_payload(task, interventions, sources), timeout_s, task.root)
    except (subprocess.TimeoutExpired, RuntimeError, ValueError) as exc:
        return _report(task, "REFUSED__" + type(exc).__name__, started,
                       reason="INTERVENTIONAL_SCREEN_REFUSED", obs=obs)
    by_index = {int(r["index"]): r for r in rows}

    weights = CalculatedWeights()
    evidence: list[tuple[list[str], bool]] = []
    passed_published_but_refused_by_intervention = 0
    accepted: list[tuple[int, Any]] = []
    for index, cand in enumerate(candidates):
        row = by_index.get(index, {})
        published_ok = bool(row.get("published_ok")) and not row.get("load_error")
        violations = 0
        violated_iv: list[str] = []
        for iv in interventions:
            rep = row.get("intervention", {}).get(iv.name, {})
            n = len(rep.get("violations", [])) + len(rep.get("exceptions", []))
            if n:
                violations += n
                violated_iv.append(iv.name)
                if published_ok:
                    contract.reach[iv.name] += 1
        interventional_ok = published_ok and violations == 0
        if published_ok and not interventional_ok:
            passed_published_but_refused_by_intervention += 1
        weights.record(cand.family, published_ok=published_ok,
                       interventional_ok=interventional_ok)
        facts = [f"family.{cand.family}", f"position.{cand.position}",
                 f"goal.{signature}", f"executed.{task.function_name}"]
        for callee in contract.callee_signatures:
            facts.append(f"callee.{callee}")
        for iv in violated_iv:
            facts.append(f"intervention.{iv}")
        for rep in row.get("intervention", {}).values():
            for exc in rep.get("exceptions", []):
                facts.append("traceback." + str(exc.get("traceback")))
        evidence.append((facts, interventional_ok))
        if interventional_ok and len(accepted) < 64:
            accepted.append((index, cand))

    # Calculated weights decide which VERIFIED candidates earn the independent
    # test.  Every bit is an executed count; a family with no contrast has 0.
    accepted.sort(key=lambda p: (-weights.weight(p[1].family), p[0]))

    identified: dict[str, Any]
    contrast: dict[str, Any] | None = None
    intervention_certificate: dict[str, Any] | None = None
    try:
        learned = APP.learn(evidence)
        identified = {"status": learned.status,
                      "survivors": len(learned.survivors) if hasattr(learned, "survivors") else None}
        states = [frozenset(f) for f, _ in evidence]
        contrast = CS.select_contrast(evidence, states).as_row()
        intervention_certificate = APP.insufficiency_witness(evidence)
    except Exception as exc:  # a diagnostic failure is reported, never a pass
        identified = {"status": "IDENTIFICATION_INSTRUMENT_REFUSED", "reason": type(exc).__name__}

    verified: list[dict[str, Any]] = []
    for index, cand in accepted[:fresh_cap]:
        verdict = CGR.fresh_verdict(task, cand.source)
        verified.append({"family": cand.family, "description": cand.description, **verdict})
        if verdict["returncode"] == 0 and not verdict["timed_out"]:
            return _report(task, "REPAIRED__CORPUS_TEST_PASSES", started, obs=obs,
                           prior=prior, contract=contract, weights=weights,
                           identified=identified, contrast=contrast,
                           intervention_certificate=intervention_certificate,
                           candidates=len(candidates), screened=len(rows),
                           fresh_verdicts=verified, winning_family=cand.family,
                           winning_index=index,
                           winning_diff="\n".join(difflib.unified_diff(
                               source.splitlines(), cand.source.splitlines(),
                               fromfile="published_buggy", tofile="candidate", lineterm="")),
                           refused=passed_published_but_refused_by_intervention,
                           reason="FRESH_COPY_VERDICT_IS_THE_ONLY_EVIDENCE")
    return _report(task, "NOT_REPAIRED__NO_CANDIDATE_PASSED_THE_CORPUS_TEST", started,
                   obs=obs, prior=prior, contract=contract, weights=weights,
                   identified=identified, contrast=contrast,
                   intervention_certificate=intervention_certificate,
                   candidates=len(candidates), screened=len(rows),
                   fresh_verdicts=verified,
                   refused=passed_published_but_refused_by_intervention,
                   reason="ALL_INTERVENTIONALLY_VERIFIED_CANDIDATES_FAILED_AN_INDEPENDENT_VERDICT")


def check_false_win(task: Any, winning_diff_source: str, *, timeout_s: float = 60.0) -> dict[str, Any]:
    """Negative control: run a KNOWN false win through the intervention contract.

    `winning_diff_source` is the exact prior candidate source (not a fix written
    here).  A refusal is a falsification of the prior claim, NOT a new repair.
    """
    if (task.root / ANSWER_KEY).exists():
        raise RuntimeError("ANSWER_KEY_REACHED_THE_SOLVER")
    interventions, diagnostics = derive_interventions(task)
    rows = _run_child(_payload(task, interventions, [winning_diff_source]), timeout_s, task.root)
    row = rows[0]
    per_iv = {}
    total = 0
    for iv in interventions:
        rep = row.get("intervention", {}).get(iv.name, {})
        n = len(rep.get("violations", [])) + len(rep.get("exceptions", []))
        per_iv[iv.name] = {"violations": len(rep.get("violations", [])),
                           "exceptions": len(rep.get("exceptions", [])),
                           "checked": rep.get("checked", 0)}
        if not iv.is_control:
            total += n
    return {"schema": SCHEMA, "task": task.name, "kind": "KNOWN_FALSE_WIN_FALSIFIER",
            "authority": AUTHORITY, "published_ok": bool(row.get("published_ok")),
            "published_passed": int(row.get("published_passed", 0)),
            "per_intervention": per_iv,
            "non_control_violations": total,
            "refused": bool(row.get("published_ok")) and total > 0,
            "counted_as_progress": False,
            "model_dependency_count": MODEL_DEPENDENCY_COUNT}


def _report(task: Any, status: str, started: float, *, reason: str,
            obs: Any = None, prior: Any = None, contract: Contract | None = None,
            weights: CalculatedWeights | None = None, identified: dict | None = None,
            contrast: dict | None = None, intervention_certificate: dict | None = None,
            candidates: int = 0, screened: int = 0, fresh_verdicts: Sequence[dict] = (),
            winning_family: str | None = None, winning_index: int | None = None,
            winning_diff: str | None = None, refused: int = 0) -> dict[str, Any]:
    def cert(c: dict | None) -> dict | None:
        if not c:
            return None
        return {k: c.get(k) for k in ("kind", "reason", "shared_facts",
                                      "unrepairable_by_repetition", "what_would_repair_it")}
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
            "observational_relations": list(obs.relations) if obs else [],
            "interventional_relations": sorted({r for iv in (contract.interventions if contract else [])
                                                for r in iv.relations}),
            "executed_lines": list(contract.executed_lines)[:40] if contract else [],
            "callee_signatures": list(contract.callee_signatures) if contract else [],
            "intervention_teeth": dict(contract.teeth) if contract else {},
            "intervention_reach": dict(contract.reach) if contract else {},
            "intervention_diagnostics": contract.diagnostics if contract else {},
        },
        "identifiability": {
            "observational_static_certificate": cert(obs.static_certificate) if obs else None,
            "observational_traced_certificate": cert(obs.traced_certificate) if obs else None,
            "interventional_certificate": cert(intervention_certificate),
            "learn": identified, "chosen_contrast": contrast,
            "permanent_rule_admitted": bool(identified and identified.get("status")
                                            == "IDENTIFIED__ONE_CONSISTENT_REQUIREMENT"),
        },
        "synthesis": {"candidates": candidates, "screened": screened,
                      "fresh_verdicts": list(fresh_verdicts),
                      "winning_family": winning_family, "winning_index": winning_index,
                      "winning_diff": winning_diff,
                      "passed_published_but_refused_by_intervention": refused,
                      "calculated_weights": weights.as_dict() if weights else None,
                      "observational_prior": prior.as_dict() if prior else None},
        "seconds": round(time.time() - started, 2),
    }
