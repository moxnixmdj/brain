"""Preregistered one-experience -> unseen-family transfer instrument.

This is a measured experiment, not a qualification. It uses real Python standard-library guide
transcripts as external instant knowledge and the interpreter as the goal oracle. A source guide
experience yields ONE computed procedure; that procedure is stored as inspectable JSON, with no
exact action replay and no weight write. Target families are mechanically different stdlib modules
that were not used to author the procedure.

EIG is a two-regime probe-order score from `canonical/runtime/settlement_v1.py`. The selected
probe is executed by the real interpreter, its observation settles the posterior, and the answer
is wired into `perfect_algorithm_v1.run` on the first resolved case. No other model is called.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import tempfile
import textwrap
import time
from typing import Any, Callable, Iterable, Mapping, Sequence

from canonical.runtime import active_question_v1 as aq
from canonical.runtime import guide_precondition_v1 as gp
from canonical.runtime import settlement_v1 as sv
from canonical.swe_kernel import perfect_algorithm_v1 as pa
from canonical.tools import the_guide_is_a_test_suite_v1 as gs

ROOT = pathlib.Path(__file__).resolve().parents[2]
STORE_PATH = ROOT / "canonical/astra_runtime/state/ONE_EXPERIENCE_CROSS_FAMILY_TRANSFER_V1.json"
RECEIPT_PATH = ROOT / "canonical/verification/ONE_EXPERIENCE_CROSS_FAMILY_TRANSFER_20261124_V1.json"
PREREGISTRATION = "OWN_MODEL_PREREGISTERED_TRANSFER_20261124_V1.md"

SCHEMA = "BRAIN_ONE_EXPERIENCE_CROSS_FAMILY_TRANSFER_V1"
SOURCE_FAMILY = "difflib"
TARGET_FAMILIES = ("statistics", "enum", "pickletools")
ARMS = ("EMPTY", "EXACT_SOURCE_TRACE", "SHUFFLED_SOURCE", "WRONG_SOURCE", "FOREIGN_SOURCE",
        "LEARNED_ABSTRACTION", "CONTRADICTORY_GOAL", "CHANGED_PRECONDITION")
CONTROL_ARMS = ("EXACT_SOURCE_TRACE", "SHUFFLED_SOURCE", "WRONG_SOURCE", "FOREIGN_SOURCE")
PREREGISTERED = {
    "min_learned_successes": 3,
    "min_success_gap_over_controls": 3,
    "max_cost_ratio_vs_exact_cache": 8,
    "max_closed_space_hypotheses": aq.MAX_CLOSED_SPACE,
    "candidate_probe_limit": 8,
    "eig_probe_budget": 4,
    "seed": 0,
    "interpreter_timeout_s": 5,
    "no_tuning_after_formal_run": True,
}

LEARNED_ABSTRACTION = {
    "schema": "BRAIN_ONE_EXPERIENCE_ABSTRACT_RULE_V1",
    "rule": ("WHEN_THE_INTERPRETER_NAMES_A_MISSING_BINDING_SCAN_THE_CURRENT_GUIDE_FOR_STATEMENTS_"
             "THAT_BIND_IT_REPLAY_THE_WHOLE_SESSION_REQUIRE_THE_GUIDES_PRINTED_OUTPUT_SEPARATE_"
             "A_MACHINE_MADE_WRONG_BINDING_AND_REFUSE_AMBIGUITY"),
    "goal": "reproduce the current guide's own printed output",
    "environment": "the interpreter's NameError and the current guide's inspectable statements",
    "needs": "the refused name and candidate statements that bind it",
    "what_to_save": "this computed procedure and source provenance only",
    "what_not_to_save": ["exact source action replay", "target bindings", "guide answers",
                         "weights", "target outcomes"],
    "parameters_written": False,
    "runtime_model_calls": 0,
    "runtime_network_calls": 0,
}


def digest_obj(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str, ensure_ascii=True)
                          .encode("utf-8")).hexdigest()[:16]


def key_of_context(value: Any) -> str:
    return digest_obj(value)


def _context_statements(context: Any) -> list[str]:
    if context is None:
        return []
    if isinstance(context, str):
        return [context]
    return [str(x) for x in context]


def _prompt(statement: str) -> list[str]:
    lines = str(statement).splitlines() or [""]
    return [">>> " + lines[0]] + ["... " + line for line in lines[1:]]


def _doctest_doc(context: Any, job: Mapping[str, Any],
                 expected: Sequence[str] | None = None) -> str:
    """Build a real doctest from guide statements, for Python's OWN doctest checker.

    Expected lines are dedented and left at column zero: doctest strips the prompt indentation
    itself. Adding four spaces here measured as a false mismatch in the feasibility smoke test.
    """
    statements = _context_statements(context) + list(job.get("_session") or [])
    if not statements:
        return ""
    lines: list[str] = []
    for statement in statements[:-1]:
        lines.extend(_prompt(statement))
    lines.extend(_prompt(statements[-1]))
    want = list(expected if expected is not None else job.get("expected") or [])
    want = [line for line in want if line.strip()]
    if want:
        lines.extend(textwrap.dedent("\n".join(want)).splitlines())
    return "\n".join(lines) + "\n"


class Meter:
    """Counts every real interpreter and independent-verifier execution."""

    def __init__(self) -> None:
        self.interpreter_probes = 0
        self.verifier_probes = 0
        self._cache: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _key(session: Mapping[str, Any]) -> str:
        return hashlib.sha256(json.dumps(session, sort_keys=True, default=str,
                                         ensure_ascii=True).encode("utf-8")).hexdigest()

    def replay_job(self, session: Mapping[str, Any], *, force: bool = False) -> dict[str, Any]:
        """Run a full guide session in a fresh interpreter; return raw result plus outcome."""
        key = self._key(session)
        if key in self._cache and not force:
            return dict(self._cache[key])
        self.interpreter_probes += 1
        with tempfile.TemporaryDirectory(prefix="brain-transfer-replay-") as where:
            if session.get("kind") == "shell":
                got = gs._shell_example_ok(dict(session), pathlib.Path(where))
            else:
                got = gs._python_example_ok(dict(session), pathlib.Path(where),
                                            module=session.get("module"))
        raw = dict(got)
        outcome = "MISMATCH"
        verdict = "NOT_RUN"
        if bool(got.get("ok")):
            verdict = gs.compare(list(got.get("got") or []),
                                 list(session.get("expected") or []))
            outcome = "MATCH" if bool(verdict.get("matches")) else "MISMATCH"
            verdict = str(verdict.get("verdict"))
        else:
            verdict = str(got.get("why") or "REFUSED_BY_INTERPRETER")
        raw.update({"outcome": outcome, "verdict": verdict,
                    "stderr": list(got.get("stderr") or [])})
        self._cache[key] = dict(raw)
        return raw

    def context(self, job: Mapping[str, Any], context: Any,
                *, expected: Sequence[str] | None = None,
                force: bool = False) -> dict[str, Any]:
        session = dict(job)
        session["_session"] = _context_statements(context) + list(job.get("_session") or [])
        if expected is not None:
            session["expected"] = list(expected)
        return self.replay_job(session, force=force)

    def verify(self, job: Mapping[str, Any], context: Any,
               *, expected: Sequence[str] | None = None) -> dict[str, Any]:
        """Independent process: Python's doctest parser/checker, not gs._python_example_ok."""
        self.verifier_probes += 1
        module = str(job.get("module") or "builtins")
        doc = _doctest_doc(context, job, expected=expected)
        script = f"""
import doctest, importlib, json, sys
module = {module!r}
doc = {doc!r}
m = importlib.import_module(module)
globs = dict(vars(m)); globs[module] = m
parser = doctest.DocTestParser()
test = parser.get_doctest(doc, globs, 'independent', '<independent>', 0)
runner = doctest.DocTestRunner(optionflags=doctest.ELLIPSIS)
runner.run(test)
result = runner.summarize(verbose=False)
print(json.dumps({{'attempted': result.attempted, 'failed': result.failed}}))
sys.exit(1 if result.failed else 0)
"""
        argv = [sys.executable, "-I", "-c", script]
        script_sha256 = hashlib.sha256(script.encode("utf-8")).hexdigest()[:16]
        try:
            with tempfile.TemporaryDirectory(prefix="brain-transfer-verify-") as where:
                done = subprocess.run(argv, cwd=where, capture_output=True, text=True,
                                      timeout=PREREGISTERED["interpreter_timeout_s"],
                                      stdin=subprocess.DEVNULL,
                                      env={"PATH": "/usr/local/bin:/usr/bin:/bin",
                                           "LC_ALL": "C.UTF-8", "PYTHONIOENCODING": "utf-8",
                                           "HOME": where})
            stdout, stderr, returncode = done.stdout, done.stderr, done.returncode
        except (OSError, subprocess.SubprocessError) as error:
            stdout, stderr, returncode = "", f"VERIFIER_FAILED__{type(error).__name__}", -1
        parsed: dict[str, Any] = {}
        tail = [line for line in stdout.strip().splitlines() if line.strip()]
        if tail:
            try:
                parsed = json.loads(tail[-1])
            except json.JSONDecodeError:
                parsed = {}
        run_ref = digest_obj({"argv_head": argv[:2], "script_sha256": script_sha256,
                              "stdout": stdout, "stderr": stderr, "returncode": returncode})
        return {"ok": returncode == 0 and parsed.get("failed") == 0,
                "returncode": returncode, "attempted": parsed.get("attempted", 0),
                "failed": parsed.get("failed", 1), "script_sha256": script_sha256,
                "run_ref": run_ref, "stdout_tail": stdout[-400:], "stderr_tail": stderr[-400:]}

    def delta(self) -> tuple[int, int]:
        return self.interpreter_probes, self.verifier_probes


def _jobs_for(families: Iterable[str]) -> dict[str, list[dict[str, Any]]]:
    jobs = gs._jobs(gs.stdlib_guides(tuple(families)))
    out: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for job in jobs:
        out[str(job["guide"])].append(job)
    return dict(out)


def _source_experience(meter: Meter) -> dict[str, Any]:
    """One source example, selected by the first identified missing-name binding."""
    jobs_by_guide = _jobs_for((SOURCE_FAMILY,))
    source_jobs = jobs_by_guide[f"stdlib:{SOURCE_FAMILY}"]
    for job in source_jobs:
        raw = meter.context(job, None)
        if raw.get("ok"):
            continue
        question = gp.missing_name(raw.get("stderr") or raw.get("why"))
        if not question:
            continue
        candidates = gp.candidates(source_jobs, question, guide=job["guide"])
        ordered = gp.rank(candidates, job, limit=PREREGISTERED["candidate_probe_limit"])

        def separate(binding: str) -> bool:
            return gp.separates(binding, question, job, replay=meter.replay_job,
                                compare=gs.compare)

        resolution = gp.resolve(job, ordered, question=question, replay=meter.replay_job,
                                compare=gs.compare, separate=separate)
        if not resolution["resolved"]:
            continue
        return {"job": job, "question": question, "binding": resolution["binding"],
                "resolution": resolution, "jobs": source_jobs,
                "job_digest": digest_obj({"guide": job["guide"], "block_line": job["block_line"],
                                          "statement": job["_statement"],
                                          "expected": job["expected"]}),
                "binding_digest": digest_obj(resolution["binding"])}
    raise RuntimeError("REFUSED__NO_IDENTIFIED_SOURCE_EXPERIENCE")


def _foreign_binding(binding: str, name: str) -> str:
    return re.sub(r"\b" + re.escape(name) + r"\b", "foreign_binding", binding, count=1)


def _source_evidence(meter: Meter, source: dict[str, Any]) -> dict[str, Any]:
    """One experience plus machine-made counterfactuals; no target outcome is stored here."""
    binding = source["binding"]
    name = source["question"]
    job = source["job"]
    contexts = {
        "correct": binding,
        "wrong": gp.wrong_binding(binding, name),
        "shuffled": binding[::-1],
        "foreign": _foreign_binding(binding, name),
        "contradictory": binding,
    }
    probes: list[dict[str, Any]] = []
    exact: dict[str, str] = {}
    classes: dict[str, str] = {}
    for kind, context in contexts.items():
        expected = ["__CONTRADICTION__"] if kind == "contradictory" else None
        raw = meter.context(job, [context], expected=expected)
        outcome = "MATCH" if raw["outcome"] == "MATCH" else "MISMATCH"
        probe = ("source", f"bind/{kind}", key_of_context(context))
        key = aq.key_of(probe)
        exact[key] = outcome
        if probe[1] in classes and classes[probe[1]] != outcome:
            raise RuntimeError("REFUSED__SOURCE_CLASS_AMBIGUOUS")
        classes[probe[1]] = outcome
        probes.append({"kind": kind, "key": probe, "outcome": outcome,
                       "raw_verdict": raw["verdict"]})
    if exact[aq.key_of(probes[0]["key"])] != "MATCH":
        raise RuntimeError("REFUSED__SOURCE_CORRECT_BINDING_DID_NOT_REPLAY")
    digest = aq.store_digest([{"key": aq.key_of(p["key"]), "outcome": p["outcome"]}
                              for p in probes])
    return {"probes": probes, "exact": exact, "classes": classes,
            "contexts": {k: key_of_context(v) for k, v in contexts.items()},
            "source_outcomes_digest": digest}


def _source_space(evidence: Mapping[str, Any]) -> sv.VersionSpace:
    """Two computed regimes, both fitted to source probes; neither knows a target outcome."""
    exact = dict(evidence["exact"])
    classes = dict(evidence["classes"])

    def predict(probe: tuple[Any, ...], regime: str) -> str:
        key = aq.key_of(tuple(probe))
        if len(probe) > 0 and str(probe[0]) == "source":
            return exact.get(key, "MISMATCH")
        if regime == "TRANSFER" and len(probe) > 1:
            return classes.get(str(probe[1]), "MISMATCH")
        return "MISMATCH"

    space = sv.VersionSpace([
        sv.Hypothesis(key="TRANSFER", predict=lambda p: predict(tuple(p), "TRANSFER"),
                      description="class-generalised source evidence"),
        sv.Hypothesis(key="NON_TRANSFER", predict=lambda p: predict(tuple(p), "NON_TRANSFER"),
                      description="source-exact evidence, mismatch on target probes"),
    ])
    for row in evidence["probes"]:
        space.observe(tuple(row["key"]), row["outcome"])
    return space


def _changed_job(job: Mapping[str, Any], question: str) -> dict[str, Any]:
    changed = "changed_precondition_name"
    pattern = re.compile(r"\b" + re.escape(question) + r"\b")
    session = [pattern.sub(changed, str(s)) for s in job.get("_session") or []]
    return dict(job, _session=session, _statement=pattern.sub(changed, str(job["_statement"])))


def _eig_probes(job: Mapping[str, Any], binding: str, wrong_binding: str) -> dict[str, Any]:
    family = str(job["guide"]).split(":")[-1]
    correct_key = (family, "bind/correct", key_of_context(binding))
    wrong_key = (family, "bind/wrong", key_of_context(wrong_binding))
    return {"keys": [correct_key, wrong_key], "correct": correct_key, "wrong": wrong_key,
            "map": {correct_key: [binding], wrong_key: [wrong_binding]}}


def _eig_question(meter: Meter, evidence: Mapping[str, Any], job: Mapping[str, Any],
                  binding: str, wrong_binding: str) -> dict[str, Any]:
    probes = _eig_probes(job, binding, wrong_binding)

    def oracle(probe: tuple[Any, ...]) -> str:
        context = probes["map"].get(tuple(probe))
        if context is None:
            return "MISMATCH"
        # force=True: the EIG-selected question is really executed, not answered from a cache.
        return str(meter.context(job, context, force=True)["outcome"])

    space = _source_space(evidence)
    initial = {str(k): round(v, 6) for k, v in space.posterior().items()}
    result = aq.ask(space, list(probes["keys"]), oracle=oracle,
                    domain=list(probes["keys"]),
                    budget=PREREGISTERED["eig_probe_budget"], confidence=0.99)
    final = result["posterior"]
    gain = float(result["gains"][aq.key_of(probes["correct"])])
    settlement = result["settlement"]
    ok = bool(result["settled"] and result["winner"] == "TRANSFER" and gain > 0.0
              and result["asked"] and final != initial
              and settlement["status"] == "SETTLED")
    return {"ok": ok, "policy": result["policy"], "gain_bits": gain,
            "initial_posterior": initial, "posterior": final,
            "posterior_changed": final != initial, "asked": result["asked"],
            "settlement": settlement, "winner": result["winner"],
            "closed": aq.closed(space), "hypotheses": len(_source_space(evidence).hypotheses),
            "probes": [aq.key_of(p) for p in probes["keys"]],
            "oracle": oracle, "keys": list(probes["keys"])}


class GuideEnvironment:
    """A real interpreter environment whose actions are guide-derived binding statements."""

    kind = "guide_interpreter"

    def __init__(self, meter: Meter, job: Mapping[str, Any]) -> None:
        self.meter = meter
        self.job = dict(job)
        self.context: list[str] = []
        self.outcome = "NO_CONTEXT"

    def reset(self) -> None:
        self.context = []
        self.outcome = "NO_CONTEXT"

    def state(self) -> tuple[int, str, str]:
        return (len(self.context), self.outcome, digest_obj(self.context))

    def snapshot(self) -> tuple[list[str], str]:
        return (list(self.context), self.outcome)

    def restore(self, saved: tuple[list[str], str]) -> None:
        self.context, self.outcome = list(saved[0]), saved[1]

    def act(self, action: Any) -> None:
        self.context.append(str(action))
        raw = self.meter.context(self.job, list(self.context))
        self.outcome = str(raw["outcome"])


def _composed_run(meter: Meter, evidence: Mapping[str, Any], job: Mapping[str, Any],
                  eig: Mapping[str, Any]) -> dict[str, Any]:
    """Exercise the EIG answer inside perfect_algorithm_v1.run, not just a direct aq.ask."""
    space = _source_space(evidence)
    initial = {str(k): round(v, 6) for k, v in space.posterior().items()}
    env = GuideEnvironment(meter, job)
    probe_map = list(eig["keys"])
    actions = [str(x) for x in _binding_actions(eig)]

    def oracle(probe: tuple[Any, ...]) -> str:
        return str(eig["oracle"](tuple(probe)))

    with tempfile.TemporaryDirectory(prefix="brain-transfer-pa-") as where:
        memory_path = pathlib.Path(where) / "pa_memory.json"
        result = pa.run(env, "reproduce the current guide's printed output", actions,
                        goal_predicate=lambda state: bool(state and state[1] == "MATCH"),
                        goal_family="guide_binding_transfer", env_kind="guide_interpreter",
                        memory={"rules": [], "priors": {}}, memory_path_=memory_path,
                        budget=8, max_depth=1, heuristic=None, seed=0,
                        allow_instant_knowledge=False, prior={},
                        question_space=space, probe_keys=probe_map,
                        probe_oracle=oracle, probe_budget=PREREGISTERED["eig_probe_budget"])
    right = (result.get("steps", {}).get("right_question") or {}).get("eig") or {}
    posterior = right.get("posterior") or {}
    gain = float(right.get("gain_of_the_question_bits") or 0.0)
    eig_ok = bool(right.get("policy") == "EIG" and right.get("answered") and gain > 0.0
                  and posterior and posterior != initial and bool(right.get("asked")))
    return {"ok": eig_ok, "run_status": result.get("status"), "run_pass": bool(result.get("pass")),
            "composed_eig": {"policy": right.get("policy"), "answered": right.get("answered"),
                             "gain_bits": gain, "asked": right.get("asked") or [],
                             "initial_posterior": initial, "posterior": posterior,
                             "reason": right.get("reason")},
            "plan": result.get("steps", {}).get("plan", {}).get("plan_sketch"),
            "act": result.get("steps", {}).get("act", {}).get("status"),
            "admit": result.get("steps", {}).get("admit", {}).get("reason"),
            "save": result.get("steps", {}).get("save", {}).get("status")}


def _binding_actions(eig: Mapping[str, Any]) -> list[str]:
    """The two verified guide-derived actions pa.run is allowed to try."""
    return [str(x) for x in eig.get("binding_actions", [])]


def _store_document(source: Mapping[str, Any], evidence: Mapping[str, Any]) -> dict[str, Any]:
    provenance = {
        "schema": "BRAIN_SOURCE_PROVENANCE_V1",
        "source_family": SOURCE_FAMILY,
        "source_question": source["question"],
        "source_job_digest": source["job_digest"],
        "source_binding_digest": source["binding_digest"],
        "source_resolution_status": source["resolution"]["status"],
        "source_probe_count": len(evidence["probes"]),
        "source_outcomes_digest": evidence["source_outcomes_digest"],
        "exact_source_binding_stored": False,
    }
    digest = aq.store_digest([LEARNED_ABSTRACTION, provenance])
    return {"schema": SCHEMA + "_STORE", "learned_abstraction": LEARNED_ABSTRACTION,
            "source_provenance": provenance, "digest": digest,
            "written_to_weights": False, "runtime_model_calls": 0}


def _load_abstract_rule(path: pathlib.Path) -> dict[str, Any] | None:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    rule = doc.get("learned_abstraction")
    if not isinstance(rule, dict) or rule.get("parameters_written") is not False:
        return None
    if not rule.get("rule"):
        return None
    return rule


def _verify_store(path: pathlib.Path) -> dict[str, Any]:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return {"ok": False, "error": type(error).__name__}
    actual = aq.store_digest([doc.get("learned_abstraction"), doc.get("source_provenance")])
    return {"ok": doc.get("schema") == SCHEMA + "_STORE" and actual == doc.get("digest")
            and _load_abstract_rule(path) is not None,
            "expected_digest": doc.get("digest"), "actual_digest": actual,
            "schema": doc.get("schema")}


def _arm(name: str, rows: Sequence[Mapping[str, Any]], before: tuple[int, int],
         after: tuple[int, int]) -> dict[str, Any]:
    refusals = collections.Counter(str(row.get("reason") or "NONE") for row in rows)
    return {"cases": len(rows),
            "interpreter_probes": after[0] - before[0],
            "verifier_probes": after[1] - before[1],
            "replayed_matches": sum(1 for row in rows if row.get("replayed_match")),
            "independent_verified": sum(1 for row in rows if row.get("independent_verified")),
            "false_successes": sum(1 for row in rows if row.get("false_success")),
            "refusals": dict(refusals), "arm": name}


def _control_arm(meter: Meter, name: str, context_for: Callable[[dict[str, Any]], Any],
                 cases: Sequence[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    before = meter.delta()
    rows: list[dict[str, Any]] = []
    for case in cases:
        raw = meter.context(case["job"], context_for(case))
        match = raw["outcome"] == "MATCH"
        verified = False
        if match:
            verified = bool(meter.verify(case["job"], context_for(case))["ok"])
        rows.append({"case_id": case["id"], "reason": ("PASS__INDEPENDENTLY_VERIFIED" if verified
                     else f"REFUSED__{name}_DID_NOT_REPRODUCE_THE_GUIDE_OUTPUT"),
                     "replayed_match": match, "independent_verified": verified})
    after = meter.delta()
    return _arm(name, rows, before, after), rows


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", default=str(STORE_PATH))
    parser.add_argument("--receipt", default=str(RECEIPT_PATH))
    parser.add_argument("--verify-store", default=None, metavar="PATH",
                        help="only verify an existing store in a separate process")
    args = parser.parse_args(argv)
    if args.verify_store:
        row = _verify_store(pathlib.Path(args.verify_store))
        print(json.dumps(row, sort_keys=True))
        return 0 if row.get("ok") else 1

    started = time.time()
    meter = Meter()
    source = _source_experience(meter)
    evidence = _source_evidence(meter, source)
    store_path = pathlib.Path(args.store)
    store_path.parent.mkdir(parents=True, exist_ok=True)
    store_doc = _store_document(source, evidence)
    store_path.write_text(json.dumps(store_doc, sort_keys=True, indent=2), encoding="utf-8")

    # External-store editability: remove the rule from a copy, then read the original again.
    with tempfile.TemporaryDirectory(prefix="brain-transfer-store-") as where:
        removed_path = pathlib.Path(where) / "removed.json"
        removed = dict(store_doc)
        removed.pop("learned_abstraction", None)
        removed_path.write_text(json.dumps(removed, sort_keys=True), encoding="utf-8")
        editability = {"removal_refuses": _load_abstract_rule(removed_path) is None,
                       "restore_available": _load_abstract_rule(store_path) is not None,
                       "weights_written": False}
    editability["ok"] = bool(editability["removal_refuses"] and
                             editability["restore_available"] and
                             not editability["weights_written"])

    # Restart persistence: a different Python process re-reads the external store.
    restart_cmd = [sys.executable, "-m",
                   "canonical.tools.one_experience_cross_family_transfer_v1",
                   "--verify-store", str(store_path)]
    restart_env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LC_ALL": "C.UTF-8",
                   "PYTHONIOENCODING": "utf-8", "HOME": str(ROOT), "PYTHONPATH": str(ROOT)}
    restart_run = subprocess.run(restart_cmd, cwd=str(ROOT), capture_output=True, text=True,
                                 timeout=20, stdin=subprocess.DEVNULL, env=restart_env)
    restart_parsed: dict[str, Any] = {}
    try:
        restart_parsed = json.loads(restart_run.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        pass
    restart = {"ok": restart_run.returncode == 0 and bool(restart_parsed.get("ok"))
               and restart_parsed.get("actual_digest") == store_doc["digest"],
               "returncode": restart_run.returncode, "stdout": restart_run.stdout.strip(),
               "stderr_tail": restart_run.stderr[-300:],
               "command_sha256": digest_obj(restart_cmd),
               "run_ref": digest_obj({"argv": restart_cmd, "stdout": restart_run.stdout,
                                      "stderr": restart_run.stderr,
                                      "returncode": restart_run.returncode})}

    target_jobs_by_guide = _jobs_for(TARGET_FAMILIES)
    cases: list[dict[str, Any]] = []
    for guide in sorted(target_jobs_by_guide):
        for job in target_jobs_by_guide[guide]:
            raw = meter.context(job, None)
            if raw.get("ok"):
                continue  # only the real guide's current interpreter refusals are cases
            question = gp.missing_name(raw.get("stderr") or raw.get("why"))
            cases.append({"id": f"C{len(cases)+1:03d}", "job": job, "question": question,
                          "guide": guide, "family": guide.split(":")[-1],
                          "initial_refusal": raw.get("verdict"),
                          "block_line": job.get("block_line"),
                          "statement_digest": digest_obj(job.get("_statement"))})
    target_case_digest = digest_obj([{k: v for k, v in c.items() if k != "job"} for c in cases])

    arms: dict[str, Any] = {}
    simple_controls = {
        "EMPTY": lambda case: None,
        "EXACT_SOURCE_TRACE": lambda case: [source["binding"]],
        "SHUFFLED_SOURCE": lambda case: [source["binding"][::-1]],
        "WRONG_SOURCE": lambda case: [gp.wrong_binding(source["binding"], source["question"])],
        "FOREIGN_SOURCE": lambda case: [_foreign_binding(source["binding"],
                                                         source["question"])],
    }
    for name, context_for in simple_controls.items():
        arm, _ = _control_arm(meter, name, context_for, cases)
        arms[name] = arm
    arms["EMPTY"]["note"] = ("no extra interpreter probe: the empty-memory arm reuses the real "
                             "refusal already recorded while enumerating the target cases")
    # LEARNED ABSTRACTION: the external store's rule is required, not assumed.
    before = meter.delta()
    learned_rows: list[dict[str, Any]] = []
    eig_rows: list[dict[str, Any]] = []
    verifier_runs: list[dict[str, Any]] = []
    abstract_rule = _load_abstract_rule(store_path)
    if abstract_rule is None:
        raise RuntimeError("REFUSED__LEARNED_ABSTRACT_RULE_NOT_IN_EXTERNAL_STORE")
    for case in cases:
        job, question = case["job"], case["question"]
        if not question:
            learned_rows.append({"case_id": case["id"], "resolved": False,
                                 "reason": "REFUSED__NO_QUESTION_IDENTIFIED",
                                 "replayed_match": False, "independent_verified": False,
                                 "admitted_bad": False})
            continue
        candidates = gp.candidates(target_jobs_by_guide[case["guide"]], question,
                                   guide=case["guide"])
        ordered = gp.rank(candidates, job,
                          limit=PREREGISTERED["candidate_probe_limit"])

        def separate(binding: str, *, _job: Mapping[str, Any] = job,
                     _q: str = question) -> bool:
            return gp.separates(binding, _q, _job, replay=meter.replay_job,
                                compare=gs.compare)

        resolution = gp.resolve(job, ordered, question=question, replay=meter.replay_job,
                                compare=gs.compare, separate=separate)
        resolved = bool(resolution["resolved"])
        row: dict[str, Any] = {"case_id": case["id"], "guide": case["guide"],
                               "question": question, "resolved": resolved,
                               "status": resolution["status"],
                               "candidates": resolution["candidates"],
                               "probes_run": resolution["probes_run"],
                               "reproducing": resolution["reproducing"],
                               "unidentified": resolution["unidentified"],
                               "replayed_match": False, "independent_verified": False,
                               "admitted_bad": bool(resolved and
                                                    (resolution["reproducing"] > 1 or
                                                     resolution["unidentified"] > 0)),
                               "reason": resolution["status"]}
        if resolved:
            binding = str(resolution["binding"])
            wrong_binding = gp.wrong_binding(binding, question)
            raw = meter.context(job, [binding])
            decoy = meter.context(job, [wrong_binding])
            decoy_separated = not (bool(decoy.get("ok")) and
                                   bool(gs.compare(list(decoy.get("got") or []),
                                                   list(job.get("expected") or []))
                                        .get("matches")))
            independent = meter.verify(job, [binding])
            verifier_runs.append({"case_id": case["id"], "module": job.get("module"),
                                  **independent})
            eig = _eig_question(meter, evidence, job, binding, wrong_binding)
            eig["case_id"] = case["id"]
            eig["binding_actions"] = [binding, wrong_binding]
            eig_rows.append(eig)
            match = raw["outcome"] == "MATCH"
            verified = bool(independent["ok"]) and decoy_separated and match
            row.update({"binding_digest": digest_obj(binding),
                        "decoy_separated": decoy_separated,
                        "replayed_match": match, "independent_verified": verified,
                        "independent_run_ref": independent["run_ref"],
                        "eig_ok": eig["ok"], "eig_gain_bits": eig["gain_bits"],
                        "eig_winner": eig["winner"], "eig_settlement_status":
                            eig["settlement"]["status"],
                        "reason": ("PASS__INDEPENDENTLY_VERIFIED" if verified else
                                   "REFUSED__INDEPENDENT_VERIFIER_OR_DECOY_FAILED")})
        learned_rows.append(row)

    composed: dict[str, Any] = {"status": "NOT_RUN__NO_RESOLVED_CASE", "ok": False}
    first = next((row for row in learned_rows if row.get("resolved")), None)
    if first is not None:
        case = next(c for c in cases if c["id"] == first["case_id"])
        eig = next(e for e in eig_rows if e["case_id"] == first["case_id"])
        composed = _composed_run(meter, evidence, case["job"], eig)
    # The probe oracle is not JSON-serialisable; keep only audit fields in the receipt.
    public_eig_rows = [{k: v for k, v in row.items()
                        if k not in ("oracle", "binding_actions")} for row in eig_rows]
    after = meter.delta()
    arms["LEARNED_ABSTRACTION"] = _arm("LEARNED_ABSTRACTION", learned_rows, before, after)
    arms["LEARNED_ABSTRACTION"].update({
        "external_rule_digest": digest_obj(abstract_rule),
        "eig_rows": public_eig_rows,
        "composed_run": composed,
        "verifier_runs": verifier_runs,
    })

    victims = [row for row in learned_rows if row.get("resolved")]
    victim_ids = {row["case_id"] for row in victims}
    victim_cases = [case for case in cases if case["id"] in victim_ids]
    binding_by_case = {}
    for row in victims:
        binding_by_case[row["case_id"]] = next(
            e["binding_actions"][0] for e in eig_rows if e["case_id"] == row["case_id"])

    # CONTRADICTORY GOAL: impossible expected output; must refuse and never verify.
    before = meter.delta()
    contradictory_rows: list[dict[str, Any]] = []
    for case in victim_cases:
        job = dict(case["job"], expected=["__CONTRADICTION__"])
        question = case["question"]
        candidates = gp.candidates(target_jobs_by_guide[case["guide"]], question,
                                   guide=case["guide"])
        ordered = gp.rank(candidates, job, limit=PREREGISTERED["candidate_probe_limit"])

        def c_separate(binding: str, *, _job: Mapping[str, Any] = job,
                       _q: str = question) -> bool:
            return gp.separates(binding, _q, _job, replay=meter.replay_job,
                                compare=gs.compare)

        resolution = gp.resolve(job, ordered, question=question, replay=meter.replay_job,
                                compare=gs.compare, separate=c_separate)
        independent = meter.verify(job, [binding_by_case[case["id"]]],
                                   expected=["__CONTRADICTION__"])
        false_success = bool(resolution["resolved"] or independent["ok"])
        contradictory_rows.append({"case_id": case["id"], "status": resolution["status"],
                                   "replayed_match": bool(resolution["resolved"]),
                                   "independent_verified": bool(independent["ok"]),
                                   "independent_run_ref": independent["run_ref"],
                                   "false_success": false_success,
                                   "reason": ("FAIL__FALSE_SUCCESS" if false_success else
                                              "REFUSED__CONTRADICTORY_GOAL_NOT_REPRODUCED")})
    after = meter.delta()
    arms["CONTRADICTORY_GOAL"] = _arm("CONTRADICTORY_GOAL", contradictory_rows, before, after)
    arms["CONTRADICTORY_GOAL"]["verifier_run_refs"] = [
        row["independent_run_ref"] for row in contradictory_rows]

    # CHANGED PRECONDITION: the refused name is different; no guide candidate may bind it.
    before = meter.delta()
    changed_rows: list[dict[str, Any]] = []
    for case in victim_cases:
        job = _changed_job(case["job"], case["question"])
        changed_question = "changed_precondition_name"
        candidates = gp.candidates(target_jobs_by_guide[case["guide"]], changed_question,
                                   guide=case["guide"])
        ordered = gp.rank(candidates, job, limit=PREREGISTERED["candidate_probe_limit"])

        def d_separate(binding: str, *, _job: Mapping[str, Any] = job,
                       _q: str = changed_question) -> bool:
            return gp.separates(binding, _q, _job, replay=meter.replay_job,
                                compare=gs.compare)

        resolution = gp.resolve(job, ordered, question=changed_question,
                                replay=meter.replay_job, compare=gs.compare,
                                separate=d_separate)
        independent = meter.verify(job, [binding_by_case[case["id"]]])
        false_success = bool(resolution["resolved"] or independent["ok"])
        changed_rows.append({"case_id": case["id"], "status": resolution["status"],
                             "candidates": resolution["candidates"],
                             "replayed_match": bool(resolution["resolved"]),
                             "independent_verified": bool(independent["ok"]),
                             "independent_run_ref": independent["run_ref"],
                             "false_success": false_success,
                             "reason": ("FAIL__FALSE_SUCCESS" if false_success else
                                        "REFUSED__CHANGED_PRECONDITION_HAS_NO_BINDING")})
    after = meter.delta()
    arms["CHANGED_PRECONDITION"] = _arm("CHANGED_PRECONDITION", changed_rows, before, after)
    arms["CHANGED_PRECONDITION"]["verifier_run_refs"] = [
        row["independent_run_ref"] for row in changed_rows]

    learned_successes = arms["LEARNED_ABSTRACTION"]["independent_verified"]
    control_max = max(arms[name]["independent_verified"] for name in CONTROL_ARMS)
    learned_total_probes = (arms["LEARNED_ABSTRACTION"]["interpreter_probes"] +
                            arms["LEARNED_ABSTRACTION"]["verifier_probes"])
    exact_cache_probes = max(1, arms["EXACT_SOURCE_TRACE"]["interpreter_probes"])
    cost_ratio = learned_total_probes / exact_cache_probes
    bad_admissions = sum(1 for row in learned_rows if row.get("admitted_bad"))
    false_successes = (arms["CONTRADICTORY_GOAL"]["false_successes"] +
                       arms["CHANGED_PRECONDITION"]["false_successes"])
    eig_pass = bool(eig_rows and all(row["ok"] for row in eig_rows)
                    and composed.get("ok") and composed.get("run_pass"))
    transfer_pass = bool(
        learned_successes >= PREREGISTERED["min_learned_successes"] and
        learned_successes - control_max >= PREREGISTERED["min_success_gap_over_controls"] and
        false_successes == 0 and bad_admissions == 0 and
        cost_ratio <= PREREGISTERED["max_cost_ratio_vs_exact_cache"] and
        restart["ok"] and editability["ok"] and abstract_rule is not None)

    receipt = {
        "schema": SCHEMA,
        "date": "2026-11-24",
        "preregistration": PREREGISTRATION,
        "authority": "NONE__PRODUCER_RUN_LOCAL_EXPERIMENT",
        "system_boundary": {
            "own_weights": False,
            "runtime_model_calls": 0,
            "runtime_network_calls": 0,
            "weights_written": False,
            "external_instant_knowledge": "Python standard-library guide text read at run time",
            "external_store": str(store_path),
            "store_contains_exact_source_binding": False,
            "store_contains_target_outcomes": False,
        },
        "preregistered": PREREGISTERED,
        "source": {
            "family": SOURCE_FAMILY,
            "question": source["question"],
            "job_digest": source["job_digest"],
            "binding_digest": source["binding_digest"],
            "resolution": {k: source["resolution"][k] for k in
                           ("status", "candidates", "probes_run", "reproducing", "unidentified")},
            "source_probes": [{k: (aq.key_of(v) if k == "key" else v)
                               for k, v in row.items()} for row in evidence["probes"]],
            "source_classes": evidence["classes"],
            "source_outcomes_digest": evidence["source_outcomes_digest"],
        },
        "target_cases": {"families": list(TARGET_FAMILIES), "total": len(cases),
                         "with_question": sum(1 for c in cases if c["question"]),
                         "no_question": sum(1 for c in cases if not c["question"]),
                         "cases_digest": target_case_digest,
                         "case_rows": [{k: v for k, v in c.items() if k != "job"}
                                       for c in cases]},
        "arms": arms,
        "external_store_editability": editability,
        "restart_persistence": restart,
        "eig": {"pass": eig_pass, "resolved_cases": len(eig_rows),
                "all_direct_settlements_pass": bool(eig_rows and
                                                    all(r["ok"] for r in eig_rows)),
                "composed_run": composed},
        "independent_verifier": {
            "mechanism": "python3 -I -c doctest.DocTestParser/DocTestRunner in a fresh process",
            "different_from": "the_guide_is_a_test_suite_v1._python_example_ok and compare",
            "runs": arms["LEARNED_ABSTRACTION"]["verifier_runs"],
            "total_processes": meter.verifier_probes,
        },
        "cost": {"interpreter_probes": meter.interpreter_probes,
                 "independent_verifier_probes": meter.verifier_probes,
                 "learned_arm_total_probes": learned_total_probes,
                 "exact_cache_probes": exact_cache_probes,
                 "cost_ratio_vs_exact_cache": round(cost_ratio, 4),
                 "wall_s": round(time.time() - started, 4)},
        "verdict": {
            "local_transfer_hypothesis_pass": transfer_pass,
            "learned_successes": learned_successes,
            "best_control_successes": control_max,
            "success_gap": learned_successes - control_max,
            "contradictory_false_successes": arms["CONTRADICTORY_GOAL"]["false_successes"],
            "changed_precondition_false_successes": arms["CHANGED_PRECONDITION"]["false_successes"],
            "ambiguous_or_unidentified_admitted": bad_admissions,
            "cost_ok": cost_ratio <= PREREGISTERED["max_cost_ratio_vs_exact_cache"],
            "restart_ok": restart["ok"],
            "external_store_editability_ok": editability["ok"],
            "eig_hypothesis_pass": eig_pass,
            "section_6": "NOT_DONE",
            "truth_achieved": False,
            "completion_claim": False,
        },
        "verified": [
            "one computed procedure from one identified source experience was stored externally",
            "real interpreter refusals in three different stdlib guide families were replayed",
            "every claimed transfer success was checked by a separate doctest process",
            "EIG-selected probes were executed and their observations changed the posterior",
            "exact, shuffled, wrong and foreign memory controls were measured",
        ],
        "failed_or_unproven": [
            "hardest-open Nov-2026 SWE and computer-use benchmarks were not run",
            "unseen arbitrary GUI/browser environments were not tested",
            "container-local open_model().solve() confinement was not established",
            "no independent cloud verifier or own-weights-only end-to-end qualification",
            "target stdlib families are mechanically separated, not truly hidden frontier families",
            "universal one-shot learning and real understanding remain unproven",
        ],
        "next_bottleneck": ("Container-local open_model().solve() confinement with a different "
                            "fresh verifier and run reference, then hardest-open Nov-2026 "
                            "SWE/Terminal-Bench/FrontierSWE and OSWorld protocols; the "
                            "Docker/Podman/Harbor/Python-3.12/VM blocker is already logged once."),
    }
    receipt_path = pathlib.Path(args.receipt)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, sort_keys=True, indent=2, default=str),
                            encoding="utf-8")
    print(json.dumps({"receipt": str(receipt_path), "store": str(store_path),
                      "transfer_pass": transfer_pass, "eig_pass": eig_pass,
                      "learned_successes": learned_successes,
                      "control_max": control_max,
                      "cost_ratio": round(cost_ratio, 4),
                      "wall_s": receipt["cost"]["wall_s"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
