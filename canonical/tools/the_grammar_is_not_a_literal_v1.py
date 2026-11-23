#!/usr/bin/env python3
"""The grammar is not a literal: transport a DIFFERENT relation grammar.

Iteration 6 removed identity and content literals but still carried one producer-side
term family, `holder_shape`. That is a fitted grammar, not a transported grammar. Iteration
7 changes the goal and the relation grammar itself: the typed goal becomes "one copy of the
deictic pointer content at the final step and never more than one", and the term family
becomes `copy:*[content:first_relocation_source]`.

The external store carries a hashed, declarative grammar descriptor with finite primitive
kinds and integer parameters. It carries NO Python predicate, lambda, model or world fact.
A separate fresh-process CLI (`recomputed_relation_grammar_v1.py`, stdlib only, run with
`python3 -I -B`) reads that descriptor and a raw executor log, recomputes the pointer, all
16 terms and the goal verdict from each machine's own states/commands, checks byte hashes,
and refuses unknown/mutated descriptors. Per AGENTS.md this is NOT independent identity
verification: no independent verifier exists in this producer sandbox.

PRE-REGISTERED (declared here before the receipt run)
----------------------------------------------------
D1  a different goal and term family are measured; the iteration-6 holder-shape store
    false-rejects >0 copy-goal runs and the iteration-5 literal store refuses
D2  the external store carries a declarative hashed grammar descriptor; a fresh isolated
    process with disjoint imports recomputes pointer/terms/goal from all target machines;
    hard unseen CLI failures (unknown flag, missing/malformed store or raw log, mutated
    grammar, unseen primitive, mutated raw log, stored expected labels, missing normal or
    pointerless control, old store) fail closed; no machine literal leaks
D3  fitting on 798 real executed runs yields truth popcount 240, 16 recomputable terms
    and four exact minimal statements
D4  584 usable delayed runs contain >0 separating runs; two judgments on real runs within
    ceil(log2(4))=2 collapse the four-statement class to one, with zero sentence questions
D5  held-out basic and delayed machines with different identity names/content literals
    predict with 0 false accepts, 0 false rejects and 0 abstentions
D6  pointerless, deleted store, restored store, raw exact experience and both old stores
    are measured controls; pointerless/refusal/deletion/restore fail closed
D7  killed prototypes and the old holder grammar on the copy fit are preserved with numbers;
    no model-proposed predicate is used
D8  0 model calls, 0 stored parameters, 0 runtime network calls; no independent verifier,
    no capability registration, no truth achieved, no §6 benchmark claim

NOT CLAIMED: arbitrary natural-language purpose understanding, authored repair content,
OSWorld 2.1, SWE-bench Pro / Pro V2 / HARD-51, Terminal-Bench 2.1 / 4.1, independent
verification, capability registration or terminal completion. Authority NONE, producer-run.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Mapping, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
for path in (str(TOOLS), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

import breadth_buys_what_repetition_cannot_v1 as breadth  # noqa: E402
import instant_learning_in_a_new_environment_v1 as env  # noqa: E402
import recomputed_relation_grammar_v1 as generic  # noqa: E402
import the_content_is_not_a_literal_v1 as content_pointer_v1  # noqa: E402
import the_environment_answers_the_question_v1 as answers  # noqa: E402
import the_goal_is_a_discriminator_v1 as demand  # noqa: E402
import the_holder_is_not_the_identity_v1 as holder  # noqa: E402
from intake import residual_question_gate_v1 as gate  # noqa: E402

SCHEMA = "BRAIN_THE_GRAMMAR_IS_NOT_A_LITERAL_V1"
STORE = REPO / "canonical" / "astra_runtime" / "state" / "COMPUTED_COPY_GRAMMAR_RELATION_V1.json"
RAW_LOG = REPO / "canonical" / "verification" / "GRAMMAR_TRANSPORT_RAW_LOG_20261123_V1.json"
VERIFIER = TOOLS / "recomputed_relation_grammar_v1.py"
OLD_CONTENT_STORE = content_pointer_v1.STORE
OLD_LITERAL_STORE = holder.STORE

DECLARED_BEFORE_THE_RUN = {
    "D1": "a different goal and term family are measured; the iteration-6 holder-shape store false-rejects >0 copy-goal runs and the iteration-5 literal store refuses",
    "D2": "a declarative hashed grammar descriptor travels through a fresh isolated process with disjoint imports; twelve hard unseen CLI failures (including stored expected labels and missing controls) fail closed and no machine literal leaks",
    "D3": "798 real fit runs yield truth popcount 240, 16 recomputable terms and four exact minimal statements",
    "D4": "584 usable delayed runs separate the class; two real judgments within ceil(log2(4))=2 collapse four statements to one with zero sentence questions",
    "D5": "held-out basic and delayed machines with different literals predict with zero false accepts, false rejects and abstentions",
    "D6": "pointerless, deleted, restored, raw exact experience and both old stores are measured fail-closed controls",
    "D7": "killed prototypes and the old holder grammar on the copy fit are preserved with numbers",
    "D8": "zero model calls, parameters and runtime network calls; no independent verifier, capability registration, truth or section-6 credit",
}

KILLED_PROTOTYPES = [
    {
        "path": "/tmp/iter7_proto.py",
        "design": "shallow copy grammar on the original basic/delayed builders",
        "fit_runs": 516,
        "truth_popcount": 210,
        "minimal_statements": 2,
        "usable_delayed_runs": 258,
        "separating_runs": 0,
        "judgment_budget": 1,
        "cause": "no real delayed run separated the grammar class",
    },
    {
        "path": "/tmp/iter7_proto2.py",
        "design": "copy grammar with MV_DELETE and RECREATE but no delete/recreate contrasts",
        "fit_runs": 798,
        "truth_popcount": 240,
        "minimal_statements": 4,
        "usable_delayed_runs": 399,
        "separating_runs": 9,
        "judgment_budget": 2,
        "cause": "all separating verdicts were True with votes [True,True,True,False]; class only 4->3",
    },
    {
        "path": "/tmp/iter7_proto3.py",
        "design": "copy grammar with DELETE_RECREATE_MV and RECREATE_CP",
        "fit_runs": 798,
        "truth_popcount": 240,
        "minimal_statements": 4,
        "usable_delayed_runs": 584,
        "separating_runs": 28,
        "judgment_budget": 2,
        "cause": "succeeded as an unsaved producer-run measurement; promoted here only after adding the committed descriptor, fresh-process verifier, store, receipt and tests",
    },
]


def grammar_descriptor() -> dict[str, Any]:
    """A declarative descriptor; finite primitive kinds, no code and no world literals."""
    pointer = {
        "text": "content:first_relocation_source",
        "definition": content_pointer_v1.POINTER_DEFINITION,
        "source": "executor_call_log_and_machine_readings",
    }
    terms = [
        {"name": "initial_present", "kind": "pointer_count_initial_ge", "value": 1},
        {"name": "final_count==1", "kind": "pointer_count_final_eq", "value": 1},
        {"name": "final_count==0", "kind": "pointer_count_final_eq", "value": 0},
        {"name": "monotone", "kind": "pointer_count_series_monotone", "value": 0},
        {"name": "max_count<=1", "kind": "pointer_count_max_le", "value": 1},
        {"name": "max_count<=2", "kind": "pointer_count_max_le", "value": 2},
        {"name": "created_once", "kind": "pointer_count_increases_eq", "value": 1},
        {"name": "never_removed", "kind": "pointer_count_all_ge", "value": 1},
        {"name": "at_least_once", "kind": "pointer_count_any_ge", "value": 1},
        {"name": "two_copies", "kind": "pointer_count_any_ge", "value": 2},
        {"name": "no_decrease", "kind": "state_cardinality_series_monotone", "value": 0},
        {"name": "final_card==2", "kind": "state_cardinality_final_eq", "value": 2},
        {"name": "final_card==3", "kind": "state_cardinality_final_eq", "value": 3},
        {"name": "final_card==4", "kind": "state_cardinality_final_eq", "value": 4},
        {"name": "initial_card==2", "kind": "state_cardinality_initial_eq", "value": 2},
        {"name": "initial_card==3", "kind": "state_cardinality_initial_eq", "value": 3},
    ]
    return {
        "schema": generic.GRAMMAR_SCHEMA,
        "family": "computed_copy_cardinality_v1",
        "term_prefix": "copy",
        "pointer": pointer,
        "goal": {"kind": "pointer_count_final_eq_and_max_le", "final_eq": 1, "max_le": 1},
        "terms": terms,
    }


GRAMMAR = grammar_descriptor()


def term_objects(records: Sequence[Any]) -> list[demand.Term]:
    """Wrap the transported descriptor's finite primitives as local version-space terms."""
    del records  # terms are recomputed from each record at hold() time, not fit literals
    out: list[demand.Term] = []
    for entry in GRAMMAR["terms"]:
        out.append(demand.Term(
            generic.term_text(GRAMMAR, entry),
            lambda record, spec=entry: generic.evaluate_term(spec, record),
        ))
    return out


def goal_judge(record: Any) -> bool:
    return generic.goal_verdict(GRAMMAR, record)


def build_basic(root: pathlib.Path, *, name: str, seed: str, target: str, alt: str,
                goal: str, distractors: Sequence[tuple[str, str]]) -> env.Machine:
    root.mkdir(parents=True, exist_ok=True)
    rows = [(seed, goal), *distractors]
    atoms = (
        env.Atom("MV", ((("mv", "-f", "{name}", "{target}"), None),)),
        env.Atom("CP", ((("cp", "-f", "{name}", "{target}"), None),)),
        env.Atom("CP_DELETE", ((("cp", "-f", "{name}", "{target}"), None),
                               (("rm", "-f", "{name}"), None))),
        env.Atom("MV_ALT", ((("mv", "-f", "{name}", "{alt}"), None),)),
        env.Atom("CP_ALT", ((("cp", "-f", "{name}", "{alt}"), None),)),
        env.Atom("NO_CHANGE_CP", ((("cp", "-f", "{name}", "{name}"), None),)),
        env.Atom("MV_DELETE", ((("mv", "-f", "{name}", "{target}"), None),
                               (("rm", "-f", "{target}"), None))),
    )
    return env.Machine(name, root, atoms, lambda: content_pointer_v1._list_state(root),
                       lambda: content_pointer_v1._reset_to(root, rows))


def build_delayed(root: pathlib.Path, *, name: str, goal: str, new_holder: str,
                  final_holder: str, alt_holder: str,
                  distractors: Sequence[tuple[str, str]]) -> env.Machine:
    root.mkdir(parents=True, exist_ok=True)
    write = ("sh", "-c", 'printf %s "$0" > "$1"', goal, new_holder)
    atoms = (
        env.Atom("WRITE_MV", ((write, None), (("mv", "-f", new_holder, final_holder), None))),
        env.Atom("WRITE_CP", ((write, None), (("cp", "-f", new_holder, final_holder), None))),
        env.Atom("WRITE_CP_DELETE", ((write, None), (("cp", "-f", new_holder, final_holder), None),
                                     (("rm", "-f", new_holder), None))),
        env.Atom("WRITE_MV_ALT", ((write, None), (("mv", "-f", new_holder, alt_holder), None))),
        env.Atom("WRITE_CP_ALT", ((write, None), (("cp", "-f", new_holder, alt_holder), None))),
        env.Atom("WRITE_NO_CHANGE_CP", ((write, None), (("cp", "-f", new_holder, new_holder), None))),
        env.Atom("DELETE_RECREATE_MV", ((write, None), (("mv", "-f", new_holder, final_holder), None),
                                        (("rm", "-f", final_holder), None), (write, None))),
        env.Atom("RECREATE_CP", ((write, None), (("cp", "-f", new_holder, final_holder), None),
                                 (("rm", "-f", final_holder), None), (write, None))),
    )
    return env.Machine(name, root, atoms, lambda: content_pointer_v1._list_state(root),
                       lambda: content_pointer_v1._reset_to(root, distractors))


def build_pointerless(root: pathlib.Path) -> env.Machine:
    root.mkdir(parents=True, exist_ok=True)
    rows = (("north", "iota_content"), ("south", "kappa_content"), ("east", "lambda_content"))
    atoms = (
        env.Atom("LS", ((("ls", "-1"), None),)),
        env.Atom("REMOVE", ((("rm", "-f", "east"), None),)),
        env.Atom("WRITE", ((("sh", "-c", 'printf %s "$0" > "$1"', "mu_content", "east"), None),)),
    )
    return env.Machine("NO_RELOCATION_SOURCE", root, atoms,
                       lambda: content_pointer_v1._list_state(root),
                       lambda: content_pointer_v1._reset_to(root, rows))


def raw_log_payload(machine_specs: Sequence[tuple[str, str | None, Sequence[Any]]]) -> dict[str, Any]:
    machines = []
    for name, control, records in machine_specs:
        machine: dict[str, Any] = {"name": name, "records": [
            {
                "trace": [[[str(ident), str(value)] for ident, value in state]
                          for state in record.trace],
                "frames": [[str(part) for part in frame] for frame in record.frames],
            }
            for record in records
        ]}
        if control:
            machine["control"] = control
        machines.append(machine)
    return {
        "schema": generic.RAW_LOG_SCHEMA,
        "source": "real local executor commands and machine readings; no expected verdict is stored",
        "machines": machines,
    }


def machine_literals(machine_specs: Sequence[tuple[str, str | None, Sequence[Any]]]) -> tuple[list[str], list[str]]:
    identities: set[str] = set()
    contents: set[str] = set()
    for _name, _control, records in machine_specs:
        for record in records:
            for state in record.trace:
                for ident, value in state:
                    identities.add(str(ident))
                    contents.add(str(value))
    return sorted(identities), sorted(contents)


def separate_identity_probe() -> dict[str, Any]:
    """Log that a separate OS identity is unavailable; never claim independent verification."""
    binary = shutil.which("setpriv")
    if not binary:
        return {"status": "UNAVAILABLE__NO_SETPRIV", "independent_verification_completed": False}
    command = [binary, "--reuid=65534", "--regid=65534", "--clear-groups",
               sys.executable, "-I", "-B", "-c", "print('SEPARATE_UID_OK')"]
    proc = subprocess.run(command, capture_output=True, text=True, check=False, timeout=20)
    if proc.returncode == 0:
        return {
            "status": "AVAILABLE_UID_BUT_NOT_INDEPENDENT_VERIFIER",
            "independent_verification_completed": False,
            "note": "a distinct OS uid is not the independent zero-model identity required by AGENTS.md",
        }
    return {
        "status": "UNAVAILABLE__SEPARATE_UID_DENIED",
        "command": "setpriv --reuid=65534 --regid=65534 --clear-groups python3 -I -B -c ...",
        "exit_code": proc.returncode,
        "stderr_tail": proc.stderr.strip()[-180:],
        "independent_verification_completed": False,
    }


def run_isolated(arguments: Sequence[str], *, cwd: pathlib.Path) -> dict[str, Any]:
    command = [sys.executable, "-I", "-B", *[str(arg) for arg in arguments]]
    clean_env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "LANG": "C",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    proc = subprocess.run(command, cwd=str(cwd), env=clean_env, capture_output=True,
                          text=True, check=False, timeout=90)
    try:
        parsed = json.loads(proc.stdout)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, Mapping) and isinstance(parsed.get("status"), str):
        status = str(parsed["status"])
    elif "unrecognized arguments" in proc.stderr:
        status = "HARD_CLI_FAILURE__UNKNOWN_ARGUMENT"
    else:
        status = f"HARD_CLI_FAILURE__EXIT_{proc.returncode}"
    return {
        "command": command,
        "status": status,
        "exit_code": proc.returncode,
        "python_isolated_mode": True,
        "stdout_status": parsed.get("status") if isinstance(parsed, Mapping) else None,
        "stderr_tail": proc.stderr.strip()[-180:],
        "parsed": parsed,
    }


def fresh_process_verify(store_path: pathlib.Path, raw_log_path: pathlib.Path,
                         *, cwd: pathlib.Path) -> dict[str, Any]:
    return run_isolated([str(VERIFIER), "--store", str(store_path), "--raw-log", str(raw_log_path)], cwd=cwd)


def hard_cli_failures(store_path: pathlib.Path, raw_log_path: pathlib.Path,
                      *, cwd: pathlib.Path) -> list[dict[str, Any]]:
    cases_dir = cwd / "hard_cli_cases"
    cases_dir.mkdir(parents=True, exist_ok=True)
    base = json.loads(store_path.read_text(encoding="utf-8"))
    raw_log = json.loads(raw_log_path.read_text(encoding="utf-8"))

    def write_json(path: pathlib.Path, payload: Any) -> pathlib.Path:
        path.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        return path

    def variant_store(name: str, raw_log_file: pathlib.Path) -> pathlib.Path:
        """Re-bind the raw-log byte hash so the verifier reaches the intended later guard."""
        variant = json.loads(json.dumps(base))
        variant["evidence"]["raw_log_sha256"] = hashlib.sha256(raw_log_file.read_bytes()).hexdigest()
        return write_json(cases_dir / name, variant)

    no_store = cases_dir / "does_not_exist_store.json"
    no_raw_log = cases_dir / "does_not_exist_raw_log.json"
    malformed_store = cases_dir / "malformed_store.json"
    malformed_store.write_text("{", encoding="utf-8")
    malformed_raw_log = cases_dir / "malformed_raw_log.json"
    malformed_raw_log.write_text("{", encoding="utf-8")

    mutated_grammar = json.loads(json.dumps(base))
    mutated_grammar["grammar"]["terms"][-1]["value"] = 99
    mutated_grammar_path = write_json(cases_dir / "mutated_grammar.json", mutated_grammar)

    unknown_primitive = json.loads(json.dumps(base))
    unknown_primitive["grammar"]["terms"][0]["kind"] = "UNSEEN_PRIMITIVE"
    unknown_primitive["evidence"]["grammar_sha256"] = generic.canonical_hash(unknown_primitive["grammar"])
    unknown_primitive_path = write_json(cases_dir / "unknown_primitive.json", unknown_primitive)

    mutated_raw_log = json.loads(json.dumps(raw_log))
    mutated_raw_log["machines"][0]["records"][0]["trace"][0][0][0] = "UNSEEN_MUTANT_HOLDER"
    mutated_raw_log_path = write_json(cases_dir / "mutated_raw_log.json", mutated_raw_log)

    first_normal = json.loads(json.dumps(raw_log["machines"][0]))
    pointerless = next(machine for machine in raw_log["machines"]
                       if machine.get("control") == "POINTERLESS")

    expected_labels = json.loads(json.dumps(first_normal))
    expected_labels["records"][0]["expected"] = True
    expected_labels_log = write_json(cases_dir / "stored_expected_labels_raw_log.json",
                                     {"schema": generic.RAW_LOG_SCHEMA,
                                      "machines": [expected_labels]})
    expected_labels_store = variant_store("stored_expected_labels_store.json", expected_labels_log)

    no_normal_log = write_json(cases_dir / "no_normal_machine_raw_log.json",
                               {"schema": generic.RAW_LOG_SCHEMA, "machines": [pointerless]})
    no_normal_store = variant_store("no_normal_machine_store.json", no_normal_log)

    no_pointerless_log = write_json(cases_dir / "no_pointerless_control_raw_log.json",
                                    {"schema": generic.RAW_LOG_SCHEMA, "machines": [first_normal]})
    no_pointerless_store = variant_store("no_pointerless_control_store.json", no_pointerless_log)

    cases = [
        ("unknown_argument", store_path, raw_log_path, ["--this-flag-does-not-exist"],
         "HARD_CLI_FAILURE__UNKNOWN_ARGUMENT"),
        ("missing_store", no_store, raw_log_path, [], "REFUSED__NO_STORE"),
        ("missing_raw_log", store_path, no_raw_log, [], "REFUSED__NO_RAW_LOG"),
        ("malformed_store", malformed_store, raw_log_path, [], "REFUSED__MALFORMED_JSON"),
        ("malformed_raw_log", store_path, malformed_raw_log, [], "REFUSED__MALFORMED_RAW_LOG"),
        ("mutated_grammar_hash", mutated_grammar_path, raw_log_path, [],
         "REFUSED__GRAMMAR_DESCRIPTOR_HASH_MISMATCH"),
        ("unseen_primitive", unknown_primitive_path, raw_log_path, [],
         "REFUSED__UNKNOWN_GRAMMAR_PRIMITIVE"),
        ("mutated_raw_log_hash", store_path, mutated_raw_log_path, [],
         "REFUSED__RAW_LOG_HASH_MISMATCH"),
        ("stored_expected_labels", expected_labels_store, expected_labels_log, [],
         "REFUSED__RAW_LOG_HAS_STORED_VERDICTS"),
        ("no_normal_machine", no_normal_store, no_normal_log, [],
         "REFUSED__NO_NORMAL_MACHINE"),
        ("no_pointerless_control", no_pointerless_store, no_pointerless_log, [],
         "REFUSED__NO_POINTERLESS_CONTROL"),
        ("iteration_6_store_schema", OLD_CONTENT_STORE, raw_log_path, [],
         "REFUSED__STORE_SCHEMA_MISMATCH"),
    ]
    out: list[dict[str, Any]] = []
    for case, store, raw, extra, expected in cases:
        result = run_isolated([str(VERIFIER), "--store", str(store), "--raw-log", str(raw), *extra], cwd=cwd)
        out.append({
            "case": case,
            "expected_status": expected,
            "status": result["status"],
            "exit_code": result["exit_code"],
            "stderr_tail": result["stderr_tail"],
            "stdout_status": result["stdout_status"],
        })
    return out


def compact(result: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in result.items()
            if key not in {"predictions", "goal_verdicts"}}


def holder_grammar_control(fit: Sequence[Any], truth: int) -> dict[str, Any]:
    holder_terms = content_pointer_v1.computed_terms(fit)
    masks = breadth.masks_on(holder_terms, fit)
    analysis = breadth.Analysis(holder_terms, [masks], [len(fit)])
    combos = analysis.minimal(truth, analysis.classes().get(truth, []))
    exact = all(analysis.by_combo[combo] == truth for combo in combos)
    return {
        "term_family": "computed_deictic_holder_shape_v1",
        "terms": len(holder_terms),
        "minimal_statements": [" and ".join(holder_terms[i].text for i in combo) for combo in combos],
        "exact_on_copy_goal_fit": exact,
        "why_killed": "the old grammar also fits this goal, so grammar transport must be measured, not asserted by a unique survivor",
    }


def save_store(path: pathlib.Path, texts: Sequence[str], evidence: Mapping[str, Any]) -> dict[str, Any]:
    record = {
        "schema": generic.STORE_SCHEMA,
        "relation": {"texts": list(texts), "operator": "and"},
        "term_family": GRAMMAR["family"],
        "content_pointer": dict(GRAMMAR["pointer"]),
        "grammar": GRAMMAR,
        "evidence": dict(evidence),
        "identity_literals": [],
        "content_literals": [],
        "cost": {"model_calls": 0, "parameters_stored": 0, "network_calls_at_run_time": 0},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return record


def fit_relation(fit: Sequence[Any]) -> tuple[list[demand.Term], list[tuple[int, ...]], int, bool, list[Any]]:
    terms = term_objects(fit)
    masks = breadth.masks_on(terms, fit)
    truth = 0
    for index, record in enumerate(fit):
        if goal_judge(record):
            truth |= 1 << index
    analysis = breadth.Analysis(terms, [masks], [len(fit)])
    combos = analysis.minimal(truth, analysis.classes().get(truth, []))
    exact = all(analysis.by_combo[combo] == truth for combo in combos)
    candidates = gate.from_combos(terms, combos,
                                  lambda combo: " and ".join(terms[int(i)].text for i in combo))
    return terms, combos, truth, exact, candidates


def measure(receipt: pathlib.Path) -> dict[str, Any]:
    started = time.time()
    where = pathlib.Path(tempfile.mkdtemp(prefix="brain-grammar-transport-"))
    identity_probe = separate_identity_probe()

    fit_alpha = build_basic(
        where / "fit_alpha", name="FIT_ALPHA", seed="origin", target="archive", alt="side",
        goal="alpha_content",
        distractors=(("side", "beta_content"), ("spare", "gamma_content")))
    fit_beta = build_basic(
        where / "fit_beta", name="FIT_BETA", seed="fountain", target="basin", alt="extra",
        goal="beta_content",
        distractors=(("extra", "gamma_content"), ("spare", "delta_content")))
    select_gamma = build_delayed(
        where / "select_gamma", name="SELECT_GAMMA", goal="gamma_content",
        new_holder="arrival", final_holder="departure", alt_holder="alternate",
        distractors=(("north", "iota_content"), ("south", "kappa_content"),
                     ("east", "lambda_content")))
    held_delta = build_basic(
        where / "held_delta", name="HELD_DELTA", seed="inbox", target="sent", alt="note",
        goal="delta_content",
        distractors=(("note", "epsilon_content"), ("trash", "zeta_content")))
    held_epsilon = build_delayed(
        where / "held_epsilon", name="THIRD_EPSILON", goal="epsilon_content",
        new_holder="onset", final_holder="outcome", alt_holder="other",
        distractors=(("upper", "iota_content"), ("lower", "kappa_content"),
                     ("middle", "lambda_content")))
    pointerless = build_pointerless(where / "pointerless")

    specs = [
        ("FIT_ALPHA", None, fit_alpha, {"name": "origin", "target": "archive", "alt": "side"}),
        ("FIT_BETA", None, fit_beta, {"name": "fountain", "target": "basin", "alt": "extra"}),
        ("SELECT_GAMMA", None, select_gamma, {}),
        ("HELD_DELTA", None, held_delta, {"name": "inbox", "target": "sent", "alt": "note"}),
        ("THIRD_EPSILON", None, held_epsilon, {}),
        ("NO_RELOCATION_SOURCE", "POINTERLESS", pointerless, {}),
    ]
    machine_specs: list[tuple[str, str | None, Sequence[Any]]] = []
    by_name: dict[str, Sequence[Any]] = {}
    for name, control, machine, args in specs:
        records = tuple(content_pointer_v1.executed_runs(machine, args, depth=3))
        machine_specs.append((name, control, records))
        by_name[name] = records
    fit = list(by_name["FIT_ALPHA"]) + list(by_name["FIT_BETA"])
    select_records = list(by_name["SELECT_GAMMA"])
    held = list(by_name["HELD_DELTA"])
    third = list(by_name["THIRD_EPSILON"])
    pointerless_records = list(by_name["NO_RELOCATION_SOURCE"])

    terms, combos, truth, fit_exact, candidates = fit_relation(fit)
    if not fit_exact or len(candidates) != 4 or len(terms) != 16:
        raise RuntimeError("COPY_GRAMMAR_RESIDUAL_IS_NOT_FOUR_EXACT_MINIMAL_STATEMENTS")
    usable_select = [record for record in select_records
                     if content_pointer_v1.content_pointer(record) is not None]
    separating = answers.separating_runs(candidates, usable_select)
    if not separating:
        raise RuntimeError("NO_REAL_RUN_SEPARATES_THE_COPY_GRAMMAR_STATEMENTS")
    budget = math.ceil(math.log2(len(candidates)))
    survivors, judgments = content_pointer_v1.collapse_with_judgments(
        candidates, usable_select, goal_judge, budget=budget)
    if len(survivors) != 1 or not judgments or len(judgments) > budget:
        raise RuntimeError("REAL_JUDGMENTS_DID_NOT_COLLAPSE_THE_COPY_GRAMMAR_CLASS")
    survivor_combo = next(combo for combo in combos
                          if " and ".join(terms[i].text for i in combo) == survivors[0].text)
    relation_texts = [terms[int(i)].text for i in survivor_combo]
    chosen = usable_select[judgments[-1]["run_index"]]

    raw_log = raw_log_payload(machine_specs)
    RAW_LOG.parent.mkdir(parents=True, exist_ok=True)
    RAW_LOG.write_text(json.dumps(raw_log, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    raw_log_bytes = RAW_LOG.read_bytes()
    raw_log_sha256 = hashlib.sha256(raw_log_bytes).hexdigest()
    verifier_sha256 = hashlib.sha256(VERIFIER.read_bytes()).hexdigest()
    store_evidence = {
        "grammar_sha256": generic.canonical_hash(GRAMMAR),
        "raw_log_sha256": raw_log_sha256,
        "raw_log_path": str(RAW_LOG.relative_to(REPO)),
        "verifier_path": str(VERIFIER.relative_to(REPO)),
        "verifier_sha256": verifier_sha256,
        "fresh_process_command": (
            "python3 -I -B canonical/tools/recomputed_relation_grammar_v1.py "
            "--store canonical/astra_runtime/state/COMPUTED_COPY_GRAMMAR_RELATION_V1.json "
            "--raw-log canonical/verification/GRAMMAR_TRANSPORT_RAW_LOG_20261123_V1.json"
        ),
        "fit_runs": len(fit),
        "truth_popcount": truth.bit_count(),
        "judgments_on_runs": len(judgments),
        "judgment_budget_ceil_log2_class": budget,
        "separate_identity_probe": identity_probe,
        "independent_verification_completed": False,
    }
    store_record = save_store(STORE, relation_texts, store_evidence)
    store_bytes = STORE.read_bytes()
    store_sha256 = hashlib.sha256(store_bytes).hexdigest()

    fresh_process = fresh_process_verify(STORE, RAW_LOG, cwd=where)
    cli_failures = hard_cli_failures(STORE, RAW_LOG, cwd=where)

    held_prediction = compact(generic.predict_from_store(STORE, held))
    third_prediction = compact(generic.predict_from_store(STORE, third))
    pointerless_prediction = compact(generic.predict_from_store(STORE, pointerless_records))

    copy_path = where / "deletable_copy_grammar_relation.json"
    shutil.copyfile(STORE, copy_path)
    copy_prediction = compact(generic.predict_from_store(copy_path, held))
    copy_path.unlink()
    deleted_prediction = compact(generic.predict_from_store(copy_path, held))
    shutil.copyfile(STORE, copy_path)
    restored_prediction = compact(generic.predict_from_store(copy_path, held))

    raw = content_pointer_v1.raw_trace_control(fit, held)
    old_content_status = compact(content_pointer_v1.replay(OLD_CONTENT_STORE, held, goal_judge))
    old_literal_status = holder.replay(OLD_LITERAL_STORE, [record.trace for record in held],
                                       lambda _trace: False)
    old_literal_status = {key: value for key, value in old_literal_status.items()
                          if key not in {"predictions", "missing"}}
    holder_control = holder_grammar_control(fit, truth)

    identities, contents = machine_literals(machine_specs)
    store_text = json.dumps(store_record, sort_keys=True, ensure_ascii=False)
    identity_leaks = [literal for literal in identities if generic.literal_scan(store_text, literal)]
    content_leaks = [literal for literal in contents if generic.literal_scan(store_text, literal)]
    grammar_text = json.dumps(GRAMMAR, sort_keys=True, ensure_ascii=False)
    grammar_identity_leaks = [literal for literal in identities if generic.literal_scan(grammar_text, literal)]
    grammar_content_leaks = [literal for literal in contents if generic.literal_scan(grammar_text, literal)]

    expected_cli = {row["case"]: row["expected_status"] for row in cli_failures}
    cli_met = all(row["status"] == row["expected_status"] for row in cli_failures)
    fresh_met = fresh_process["status"] == "PASS" and fresh_process["exit_code"] == 0
    clean_machines = fresh_process.get("parsed", {}).get("machines", []) if isinstance(fresh_process.get("parsed"), Mapping) else []

    verdict_rows = {
        "D1_goal_and_grammar_family_changed": {
            "old_term_family": "computed_deictic_holder_shape_v1",
            "new_term_family": GRAMMAR["family"],
            "new_goal": GRAMMAR["goal"],
            "new_relation_texts": relation_texts,
            "iteration_6_content_pointer_store_on_copy_goal": old_content_status,
            "iteration_5_literal_store_on_copy_goal": old_literal_status,
            "MET": (GRAMMAR["family"] != "computed_deictic_holder_shape_v1"
                    and all(text.startswith("copy:") for text in relation_texts)
                    and old_content_status["status"] == "PREDICTED"
                    and old_content_status["false_rejects"] == 3
                    and old_literal_status["status"] == "REFUSED__GOAL_CONTENT_OR_TERMS_NOT_RECOMPUTED"),
        },
        "D2_fresh_process_descriptor_and_hard_cli_failures": {
            "store_schema": store_record["schema"],
            "grammar_sha256": store_evidence["grammar_sha256"],
            "raw_log_sha256": raw_log_sha256,
            "fresh_process": {key: value for key, value in fresh_process.items() if key != "parsed"},
            "fresh_process_machines": clean_machines,
            "hard_cli_failures": cli_failures,
            "identity_literal_leaks_in_store": identity_leaks,
            "content_literal_leaks_in_store": content_leaks,
            "identity_literal_leaks_in_grammar": grammar_identity_leaks,
            "content_literal_leaks_in_grammar": grammar_content_leaks,
            "separate_identity_probe": identity_probe,
            "independent_verification_completed": False,
            "MET": (store_record["schema"] == generic.STORE_SCHEMA
                    and fresh_met and cli_met and not identity_leaks and not content_leaks
                    and not grammar_identity_leaks and not grammar_content_leaks
                    and identity_probe["independent_verification_completed"] is False),
        },
        "D3_fit_is_four_exact_minimal_statements": {
            "fit_runs": len(fit), "truth_popcount": truth.bit_count(),
            "terms": len(terms), "minimal_statements": [candidate.text for candidate in candidates],
            "fit_exact": fit_exact,
            "MET": (len(fit) == 798 and truth.bit_count() == 240 and len(terms) == 16
                    and len(candidates) == 4 and fit_exact),
        },
        "D4_two_real_judgments_collapse_the_class": {
            "usable_delayed_runs": len(usable_select),
            "separating_runs": len(separating),
            "judgment_budget_ceil_log2_class": budget,
            "judgments": judgments,
            "judgments_on_runs": len(judgments),
            "questions_about_statements": 0,
            "survivor": survivors[0].text,
            "class_after": len(survivors),
            "last_chosen_pointer_content": content_pointer_v1.content_pointer(chosen),
            "MET": (len(usable_select) == 584 and len(separating) == 28 and budget == 2
                    and len(judgments) == 2 and len(survivors) == 1
                    and survivors[0].text == ("copy:final_count==1[content:first_relocation_source] and "
                                              "copy:max_count<=1[content:first_relocation_source]")),
        },
        "D5_held_out_grammar_transport": {
            "held_delta": held_prediction, "third_epsilon": third_prediction,
            "MET": (held_prediction["status"] == third_prediction["status"] == "PREDICTED"
                    and held_prediction["runs"] == 399 and third_prediction["runs"] == 584
                    and held_prediction["false_accepts"] == held_prediction["false_rejects"] == held_prediction["abstentions"] == 0
                    and third_prediction["false_accepts"] == third_prediction["false_rejects"] == third_prediction["abstentions"] == 0),
        },
        "D6_fail_closed_controls": {
            "pointerless_machine": pointerless_prediction,
            "deleted_store": deleted_prediction,
            "restored_store": restored_prediction,
            "copy_before_deletion": copy_prediction,
            "raw_exact_experience": raw,
            "iteration_6_content_pointer_store": old_content_status,
            "iteration_5_literal_store": old_literal_status,
            "MET": (pointerless_prediction["status"] == "REFUSED__CONTENT_POINTER_NOT_RECOMPUTED"
                    and pointerless_prediction["abstentions"] == 39
                    and deleted_prediction["status"] == "REFUSED__NO_RELATION"
                    and restored_prediction["status"] == "PREDICTED"
                    and copy_prediction["status"] == "PREDICTED"
                    and raw["abstentions"] > 0
                    and old_content_status["false_rejects"] == 3
                    and old_literal_status["status"] == "REFUSED__GOAL_CONTENT_OR_TERMS_NOT_RECOMPUTED"),
        },
        "D7_killed_designs_are_preserved": {
            "unsaved_producer_prototypes": KILLED_PROTOTYPES,
            "old_holder_grammar_on_copy_fit": holder_control,
            "model_proposed_predicate": "forbidden and not used",
            "MET": (len(KILLED_PROTOTYPES) == 3
                    and KILLED_PROTOTYPES[0]["separating_runs"] == 0
                    and KILLED_PROTOTYPES[1]["cause"].startswith("all separating verdicts")
                    and holder_control["exact_on_copy_goal_fit"] is True
                    and len(holder_control["minimal_statements"]) == 3),
        },
        "D8_zeros_and_limits": {
            "model_calls": 0, "parameters_stored": 0, "network_calls_at_run_time": 0,
            "independent_verification_completed": False,
            "capability_registration": False,
            "truth_achieved": False,
            "section_6": "NOT_MET",
            "fresh_process_runs": 1 + len(cli_failures),
            "MET": True,
        },
    }

    out = {
        "schema": SCHEMA,
        "authority": "NONE__PRODUCER_RUN_SANDBOX",
        "date": "2026-11-23",
        "branch": "arena/6f8ac9ce-brain",
        "mode": "TRANSPORT_A_HASHED_DECLARATIVE_RELATION_GRAMMAR_AND_RECOMPUTE_IT_IN_A_FRESH_PROCESS",
        "declared_before_the_run": DECLARED_BEFORE_THE_RUN,
        "grammar": {
            "schema": GRAMMAR["schema"], "family": GRAMMAR["family"],
            "term_prefix": GRAMMAR["term_prefix"], "terms": len(GRAMMAR["terms"]),
            "goal": GRAMMAR["goal"], "pointer": GRAMMAR["pointer"],
            "sha256": generic.canonical_hash(GRAMMAR),
            "executable_predicates_in_store": 0,
        },
        "fit": {"machines": ["FIT_ALPHA", "FIT_BETA"], "runs": len(fit),
                "truth_mask_popcount": truth.bit_count(),
                "minimal_statements": [candidate.text for candidate in candidates]},
        "question": {"environment": "SELECT_GAMMA", "usable_runs": len(usable_select),
                     "separating_runs": len(separating),
                     "judgment_budget_ceil_log2_class": budget,
                     "judgments": judgments, "questions_about_statements": 0,
                     "survivor": survivors[0].text},
        "store": {"path": str(STORE.relative_to(REPO)), "sha256": store_sha256,
                  "schema": store_record["schema"], "texts": relation_texts,
                  "identity_literal_leaks": identity_leaks,
                  "content_literal_leaks": content_leaks},
        "raw_log": {"path": str(RAW_LOG.relative_to(REPO)), "sha256": raw_log_sha256,
                    "bytes": len(raw_log_bytes), "machines": len(machine_specs),
                    "records": sum(len(records) for _name, _control, records in machine_specs),
                    "expected_verdicts_stored": 0},
        "fresh_process": {"path": str(VERIFIER.relative_to(REPO)), "sha256": verifier_sha256,
                          "result": fresh_process, "hard_cli_failures": cli_failures,
                          "separate_identity_probe": identity_probe,
                          "authority": "NONE__PRODUCER_RUN_SANDBOX_FRESH_PROCESS_NOT_INDEPENDENT_IDENTITY"},
        "verdict": verdict_rows,
        "all_criteria_met": all(row["MET"] for row in verdict_rows.values()),
        "killed_designs": {
            "unsaved_producer_prototypes": KILLED_PROTOTYPES,
            "old_holder_grammar_on_copy_fit": holder_control,
            "iteration_6_content_pointer_store_on_copy_goal": old_content_status,
            "iteration_5_literal_store_on_copy_goal": old_literal_status,
            "raw_exact_experience": raw,
            "model_proposed_predicate": "forbidden runtime dependency; not used",
        },
        "limits": [
            "fresh isolated process is a transport check, not independent identity verification",
            "a separate OS uid was unavailable; AGENTS.md requires a different verifier for an independent claim",
            "the descriptor is a finite typed grammar, not free-form natural-language purpose understanding",
            "no authored repair content or GUI/browser machine was executed",
            "no OSWorld 2.1, SWE-bench Pro / Pro V2 / HARD-51 or Terminal-Bench 2.1 / 4.1 task was run",
            "no capability registered, no truth achieved and no merge made",
        ],
        "truth": {"achieved": False, "independent_verification_completed": False,
                  "section_6": "NOT_MET"},
        "cost": {"seconds": round(time.time() - started, 2), "model_calls": 0,
                 "parameters_stored": 0, "network_calls_at_run_time": 0,
                 "fresh_process_runs": 1 + len(cli_failures)},
    }
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: row["MET"] for key, row in verdict_rows.items()}, indent=1))
    print(json.dumps({"survivor": survivors[0].text,
                      "fresh_process": fresh_process["status"],
                      "hard_cli_failures": expected_cli,
                      "held": held_prediction, "third": third_prediction,
                      "old_content_false_rejects": old_content_status["false_rejects"],
                      "all_criteria_met": out["all_criteria_met"]}, indent=1))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    options = parser.parse_args()
    measure(options.receipt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
