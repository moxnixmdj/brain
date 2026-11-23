#!/usr/bin/env python3
"""The content is not a literal: compute the goal pointer from the executor's call log.

Iteration 5 removed identity literals from the carried relation, but the relation text still said
`holder_shape:... [probe_seed_content]`. A machine whose goal content had a different name refused.
That refusal was honest; it was also the next bottleneck. A literal is not a pointer.

This round computes the goal content deictically. The only carried object is a **relation schema**:

    holder_shape:<feature>[content:first_relocation_source]

`content:first_relocation_source` is recomputed from THIS machine's own executed call log. The first
`mv`/`cp` command in the log names a source operand. Read that operand's content from the initial
state if it was there; otherwise read it from the state immediately before the command (a content
that appeared mid-run). No identity literal, no content literal, no model and no stored world fact is
needed. The relation terms are then recomputed from the machine's `(identity, content)` rows and the
executor's own call log; replay refuses when the pointer cannot be recomputed.

PRE-REGISTERED (declared here before the receipt run)
----------------------------------------------------
C1  the iteration-5 literal-content store still refuses a machine with a different content literal,
    and the new computed term family contains zero fit identity or content literals
C2  fitting on real runs where identity names AND content literals differ from iteration 5 yields
    three minimal pointer-relative statements, exact on the fit; a real delayed-content environment
    separates them; two judgments on real runs (the ceil(log2(3)) budget) collapse the class to one,
    with zero questions about statements
C3  the saved relation predicts a held-out OVERWRITE-style machine with new identity names and a
    new content literal, 0 false accepts, 0 false rejects and 0 abstentions; the pointer contents
    are recomputed from that machine and no literal is in the store
C4  a third machine with yet another set of identity names and content literals predicts with 0
    errors and 0 abstentions; no identity or content literal from any fit/held-out machine appears
    in the external store
C5  a machine with no relocation-source command refuses; deleting the store refuses; restoring it
    predicts; raw exact runs abstain while the relation does not; the old literal store refuses
C6  killed designs are measured: a naive initial-content pointer makes >0 errors on delayed-content
    runs; raw exact traces abstain; the prior full canonical-trace table already had >0 abstentions;
    no model-proposed pointer is used
C7  0 model calls, 0 stored parameters, 0 network calls at run time; every state is read after a
    real command executed by the local executor, and the call log is the executor's own

NOT CLAIMED: a GUI, a browser, OSWorld 2.1, SWE-bench Pro / Pro V2 / HARD-51, Terminal-Bench,
repository repair, independent verification, capability registration, or terminal completion. The
call log is an observable the executor already has; this is not a claim that every possible goal has
a relocation-source pointer. Authority NONE, producer-run sandbox.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import itertools
import json
import math
import pathlib
import re
import shutil
import sys
import tempfile
import time
from typing import Any, Callable, Mapping, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
for path in (str(TOOLS), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

import breadth_buys_what_repetition_cannot_v1 as breadth  # noqa: E402
import instant_learning_in_a_new_environment_v1 as env  # noqa: E402
import the_environment_answers_the_question_v1 as answers  # noqa: E402
import the_goal_is_a_discriminator_v1 as demand  # noqa: E402
import the_holder_is_not_the_identity_v1 as holder  # noqa: E402
from intake import residual_question_gate_v1 as gate  # noqa: E402

SCHEMA = "BRAIN_THE_CONTENT_IS_NOT_A_LITERAL_V1"
STORE_SCHEMA = "BRAIN_COMPUTED_CONTENT_POINTER_RELATION_V1"
STORE = REPO / "canonical" / "astra_runtime" / "state" / "COMPUTED_CONTENT_POINTER_RELATION_V1.json"
OLD_STORE = holder.STORE
PRIOR_RECEIPT = REPO / "canonical" / "verification" / "THE_HOLDER_IS_NOT_THE_IDENTITY_20261123_V1.json"
POINTER_TEXT = "content:first_relocation_source"
POINTER_DEFINITION = (
    "the content of the first mv/cp source operand in the executor call log, read from the initial "
    "state when that operand existed there, otherwise from the state immediately before that command"
)

Trace = tuple[tuple[tuple[str, str], ...], ...]
Frame = tuple[str, ...]
Judge = Callable[["ExecutedRun"], bool]

DECLARED_BEFORE_THE_RUN = {
    "C1": "the prior literal-content store refuses and the computed term texts contain zero fit identity or content literals",
    "C2": "three minimal pointer-relative statements are exact on fit, separated by two real delayed-content judgments within the ceil(log2(3)) budget",
    "C3": "new-literal OVERWRITE held-out prediction is exact with zero abstentions and a recomputed content pointer",
    "C4": "a third new-identity/new-content machine is exact with zero abstentions and the store has no machine literals",
    "C5": "pointerless machine refuses, deletion refuses, restore predicts, raw traces abstain, old store refuses",
    "C6": "naive initial pointer, raw traces and the prior canonical table are measured as killed designs",
    "C7": "zeros and real executions with an executor call log",
}


@dataclasses.dataclass(frozen=True)
class ExecutedRun:
    """A real run: a state after EVERY executed substep, plus the exact command for each substep."""
    trace: Trace
    frames: tuple[Frame, ...]


@dataclasses.dataclass(frozen=True)
class MachineSpec:
    name: str
    machine: env.Machine
    args: dict[str, str]
    records: tuple[ExecutedRun, ...]


def contains_literal(text: str, literal: str) -> bool:
    """Literal match that does not confuse `source` with `first_relocation_source`."""
    return re.search(r"(?<![A-Za-z0-9_])" + re.escape(literal) + r"(?![A-Za-z0-9_])", text) is not None


def executed_runs(machine: env.Machine, args: Mapping[str, str], *, depth: int = 3) -> list[ExecutedRun]:
    """Enumerate real command sequences; retain the executor's own substep call log.

    This reuses `the_goal_is_a_quotient_of_the_trace_v1`'s repair: when a state-only projection is
    insufficient, add the executor's call log as an observable. Here each substep is executed by
    `env._run` and the machine's own reader is called after it. No transition is simulated.
    """
    bound = dict(args)
    out: list[ExecutedRun] = []
    seen: set[tuple[Trace, tuple[Frame, ...]]] = set()
    for length in range(1, depth + 1):
        for sequence in itertools.product(machine.atoms, repeat=length):
            machine.reset()
            states: list[tuple[tuple[str, str], ...]] = [tuple(machine.read())]
            frames: list[Frame] = []
            for atom in sequence:
                for argv, stdin in atom.steps:
                    command = tuple(str(env.bind(step, bound)) for step in argv)
                    frames.append(command)
                    env._run(command, cwd=machine.root, stdin=env.bind(stdin, bound))  # type: ignore[attr-defined]
                    states.append(tuple(machine.read()))
            record = ExecutedRun(tuple(states), tuple(frames))
            key = (record.trace, record.frames)
            if key not in seen:
                seen.add(key)
                out.append(record)
    machine.reset()
    return out


def relocation_source(command: Frame) -> str | None:
    """The source operand of a real mv/cp command; options are skipped, no name is supplied."""
    if not command or pathlib.PurePosixPath(command[0]).name not in {"mv", "cp"}:
        return None
    positional = [arg for arg in command[1:] if not arg.startswith("-")]
    return positional[0] if len(positional) >= 2 else None


def content_pointer(record: ExecutedRun) -> str | None:
    """Compute the content deictically from the initial state, pre-command states and call log."""
    initial = {ident: value for ident, value in record.trace[0]}
    for index, command in enumerate(record.frames):
        source = relocation_source(command)
        if source is None:
            continue
        if source in initial:
            return initial[source]
        before = {ident: value for ident, value in record.trace[index]}
        if source in before:
            return before[source]
    return None


def moved_judge(record: ExecutedRun) -> bool:
    """The original was moved, not copied-then-deleted, for the COMPUTED goal content."""
    content = content_pointer(record)
    if content is None:
        return False
    holders = [[ident for ident, value in state if value == content] for state in record.trace]
    if any(len(row) > 1 for row in holders):
        return False
    first = next((row for row in holders if row), None)
    if not first or not holders[-1]:
        return False
    return holders[-1] != first


def observed_pointers(records: Sequence[ExecutedRun]) -> list[str]:
    return sorted({content for record in records if (content := content_pointer(record)) is not None})


def computed_terms(records: Sequence[ExecutedRun]) -> list[demand.Term]:
    """Recomputable pointer-relative terms; no content literal is instantiated in a term text."""
    if not observed_pointers(records):
        return []
    out: list[demand.Term] = []
    for feature in holder.FEATURE_ORDER:
        out.append(demand.Term(
            f"holder_shape:{feature}[{POINTER_TEXT}]",
            lambda record, feature=feature: holder.shape_features(
                holder.holder_shape(record.trace, content_pointer(record)))[feature],
        ))
    return out


def candidates_from(terms: Sequence[demand.Term],
                    combos: Sequence[tuple[int, ...]]) -> list[gate.Candidate]:
    return gate.from_combos(terms, combos,
                            lambda combo: " and ".join(terms[int(i)].text for i in combo))


def fit_computed_relation(fit: Sequence[ExecutedRun],
                          judge: Judge) -> tuple[list[demand.Term], list[tuple[int, ...]], int]:
    if any(content_pointer(record) is None for record in fit):
        raise RuntimeError("CONTENT_POINTER_NOT_RECOMPUTED_ON_FIT")
    terms = computed_terms(fit)
    masks = breadth.masks_on(terms, fit)
    truth = 0
    for index, record in enumerate(fit):
        if judge(record):
            truth |= 1 << index
    analysis = breadth.Analysis(terms, [masks], [len(fit)])
    combos = analysis.minimal(truth, analysis.classes().get(truth, []))
    exact = all(analysis.by_combo[combo] == truth for combo in combos)
    if not terms or len(combos) < 2 or not exact:
        raise RuntimeError("POINTER_RESIDUAL_IS_NOT_AN_EXACT_AMBIGUOUS_CLASS")
    return terms, combos, truth


def collapse_with_judgments(candidates: Sequence[gate.Candidate],
                            records: Sequence[ExecutedRun], judge: Judge,
                            *, budget: int) -> tuple[list[gate.Candidate], list[dict[str, Any]]]:
    """Active judgments on REAL runs, never a question about which statement to keep."""
    active = list(candidates)
    used: set[int] = set()
    judgments: list[dict[str, Any]] = []
    for _ in range(budget):
        if len(active) < 2:
            break
        separating = [index for index in answers.separating_runs(active, records)
                      if index not in used]
        if not separating:
            break
        chosen_index = min(separating, key=lambda index: len(records[index].frames))
        chosen = records[chosen_index]
        verdict = bool(judge(chosen))
        survivors = [candidate for candidate in active
                     if bool(candidate.holds(chosen)) == verdict]
        if len(survivors) == len(active):
            continue
        judgments.append({"run_index": chosen_index, "run_steps": len(chosen.frames),
                          "judgment_on_the_run": verdict, "class_before": len(active),
                          "class_after": len(survivors),
                          "surviving_texts": [candidate.text for candidate in survivors]})
        used.add(chosen_index)
        active = survivors
        if len(active) == 1:
            break
    return active, judgments


def _list_state(root: pathlib.Path) -> list[tuple[str, str]]:
    return [(p.name, p.read_text(encoding="utf-8", errors="replace").strip())
            for p in sorted(root.iterdir()) if p.is_file()]


def _reset_to(root: pathlib.Path, rows: Sequence[tuple[str, str]]) -> None:
    for path in list(root.iterdir()):
        if path.is_file():
            path.unlink()
    for name, content in rows:
        (root / name).write_text(content, encoding="utf-8")


def build_basic(root: pathlib.Path, *, name: str, seed: str, target: str, alt: str,
                goal: str, distractors: Sequence[tuple[str, str]]) -> env.Machine:
    """Every atom has a real mv/cp source operand, so every run has a computable pointer."""
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
    )
    return env.Machine(name, root, atoms, lambda: _list_state(root),
                       lambda: _reset_to(root, rows))


def build_delayed(root: pathlib.Path, *, name: str, goal: str, new_holder: str, final_holder: str,
                  alt_holder: str, distractors: Sequence[tuple[str, str]]) -> env.Machine:
    """Goal content appears AFTER step 0; every atom writes it and then performs a real relocation."""
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
    )
    return env.Machine(name, root, atoms, lambda: _list_state(root),
                       lambda: _reset_to(root, distractors))


def build_pointerless(root: pathlib.Path) -> env.Machine:
    """A control with no mv/cp source operand: the pointer must refuse, not guess."""
    root.mkdir(parents=True, exist_ok=True)
    rows = (("north", "iota_content"), ("south", "kappa_content"), ("east", "lambda_content"))
    atoms = (
        env.Atom("LS", ((("ls", "-1"), None),)),
        env.Atom("REMOVE_EAST", ((("rm", "-f", "east"), None),)),
        env.Atom("WRITE_EAST", ((("sh", "-c", 'printf %s "$0" > "$1"', "mu_content", "east"), None),)),
    )
    return env.Machine("NO_RELOCATION_SOURCE", root, atoms, lambda: _list_state(root),
                       lambda: _reset_to(root, rows))


def machine_literals(specs: Sequence[MachineSpec]) -> tuple[list[str], list[str]]:
    identities: set[str] = set()
    contents: set[str] = set()
    for spec in specs:
        for record in spec.records:
            for state in record.trace:
                for ident, value in state:
                    identities.add(ident)
                    contents.add(value)
    return sorted(identities), sorted(contents)


def save_relation(path: pathlib.Path, texts: Sequence[str], evidence: Mapping[str, Any]) -> dict[str, Any]:
    record = {
        "schema": STORE_SCHEMA,
        "relation": {"texts": list(texts), "operator": "and"},
        "term_family": "computed_deictic_holder_shape_v1",
        "content_pointer": {
            "text": POINTER_TEXT,
            "definition": POINTER_DEFINITION,
            "source": "executor_call_log_and_machine_readings",
        },
        "feature_order": list(holder.FEATURE_ORDER),
        "evidence": {
            "term_sha256": hashlib.sha256("\n".join(texts).encode("utf-8")).hexdigest()[:16],
            "judgment_on_the_run": bool(evidence["judgment_on_the_run"]),
            "chosen_run_steps": int(evidence["chosen_run_steps"]),
            "judgments_on_runs": int(evidence["judgments_on_runs"]),
            "judgment_budget_ceil_log2_class": int(evidence["judgment_budget_ceil_log2_class"]),
            "fit_runs": int(evidence["fit_runs"]),
        },
        "identity_literals": [],
        "content_literals": [],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
    return record


def load_relation(path: pathlib.Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    record = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(record, dict) or record.get("schema") != STORE_SCHEMA:
        raise ValueError("STORE_SCHEMA_MISMATCH")
    return record


def replay(path: pathlib.Path, records: Sequence[ExecutedRun], judge: Judge) -> dict[str, Any]:
    """Recompute the pointer and all stored terms from THIS machine's executed runs."""
    loaded = load_relation(path)
    if loaded is None:
        return {"status": "REFUSED__NO_RELATION", "abstentions": len(records)}
    failures = [index for index, record in enumerate(records) if content_pointer(record) is None]
    if failures:
        return {"status": "REFUSED__CONTENT_POINTER_NOT_RECOMPUTED",
                "runs": len(records), "abstentions": len(failures),
                "pointer_failures": len(failures)}
    available = {term.text: term for term in computed_terms(records)}
    wanted = list(loaded["relation"]["texts"])
    missing = [text for text in wanted if text not in available]
    if missing:
        return {"status": "REFUSED__TERMS_NOT_RECOMPUTED", "missing": missing,
                "abstentions": len(records)}
    predicates = [available[text] for text in wanted]
    predictions = [all(predicate.holds(record) for predicate in predicates) for record in records]
    false_accepts = sum(1 for predicted, record in zip(predictions, records)
                        if predicted and not judge(record))
    false_rejects = sum(1 for predicted, record in zip(predictions, records)
                        if not predicted and judge(record))
    return {"status": "PREDICTED", "runs": len(records), "abstentions": 0,
            "false_accepts": false_accepts, "false_rejects": false_rejects,
            "texts": wanted, "pointer_contents_recomputed_from_this_machine": observed_pointers(records),
            "terms_recomputed_from_this_machine": len(available),
            "predictions": predictions}


def raw_trace_control(fit: Sequence[ExecutedRun], held: Sequence[ExecutedRun]) -> dict[str, Any]:
    seen = {record.trace for record in fit}
    abstentions = sum(record.trace not in seen for record in held)
    return {"fit_runs": len(fit), "held_out_runs": len(held), "abstentions": abstentions}


def naive_initial_pointer(record: ExecutedRun) -> str:
    """A killed design: pick a content from step 0 instead of computing the deictic pointer."""
    return sorted({value for _ident, value in record.trace[0]})[0]


def naive_pointer_errors(records: Sequence[ExecutedRun], texts: Sequence[str],
                         judge: Judge) -> dict[str, Any]:
    features = [text.split(":", 1)[1].split("[", 1)[0] for text in texts]
    errors = 0
    contents: set[str] = set()
    for record in records:
        content = naive_initial_pointer(record)
        contents.add(content)
        predicted = all(holder.shape_features(holder.holder_shape(record.trace, content))[feature]
                        for feature in features)
        errors += int(predicted != bool(judge(record)))
    return {"definition": "lexically first content in the initial state",
            "runs": len(records), "errors": errors, "pointer_contents_tried": sorted(contents)}


def old_store_status(records: Sequence[ExecutedRun]) -> dict[str, Any]:
    """The iteration-5 store still carries a literal; on these traces it must refuse."""
    result = holder.replay(OLD_STORE, [record.trace for record in records], lambda _trace: False)
    return {key: value for key, value in result.items() if key != "predictions"}


def measure(receipt: pathlib.Path) -> dict[str, Any]:
    started = time.time()
    where = pathlib.Path(tempfile.mkdtemp(prefix="brain-content-pointer-"))

    fit_alpha = build_basic(
        where / "fit_alpha", name="MOVE_ALPHA", seed="origin", target="archive", alt="side",
        goal="alpha_content",
        distractors=(("side", "beta_content"), ("spare", "gamma_content")),
    )
    fit_beta = build_basic(
        where / "fit_beta", name="EXTRA_BETA", seed="fountain", target="basin", alt="extra",
        goal="beta_content",
        distractors=(("extra", "gamma_content"), ("spare", "delta_content")),
    )
    select_gamma = build_delayed(
        where / "select_gamma", name="DELAY_GAMMA", goal="gamma_content", new_holder="arrival",
        final_holder="departure", alt_holder="alternate",
        distractors=(("north", "iota_content"), ("south", "kappa_content"),
                     ("east", "lambda_content")),
    )
    held_delta = build_basic(
        where / "held_delta", name="OVERWRITE_DELTA", seed="inbox", target="sent", alt="note",
        goal="delta_content",
        distractors=(("note", "epsilon_content"), ("trash", "zeta_content")),
    )
    held_epsilon = build_delayed(
        where / "held_epsilon", name="THIRD_EPSILON", goal="epsilon_content",
        new_holder="onset", final_holder="outcome", alt_holder="other",
        distractors=(("upper", "iota_content"), ("lower", "kappa_content"),
                     ("middle", "lambda_content")),
    )
    pointerless = build_pointerless(where / "pointerless")

    specs = [
        MachineSpec("MOVE_ALPHA", fit_alpha, {"name": "origin", "target": "archive", "alt": "side"},
                    tuple(executed_runs(fit_alpha, {"name": "origin", "target": "archive", "alt": "side"}))),
        MachineSpec("EXTRA_BETA", fit_beta, {"name": "fountain", "target": "basin", "alt": "extra"},
                    tuple(executed_runs(fit_beta, {"name": "fountain", "target": "basin", "alt": "extra"}))),
        MachineSpec("DELAY_GAMMA", select_gamma, {},
                    tuple(executed_runs(select_gamma, {}))),
        MachineSpec("OVERWRITE_DELTA", held_delta,
                    {"name": "inbox", "target": "sent", "alt": "note"},
                    tuple(executed_runs(held_delta, {"name": "inbox", "target": "sent", "alt": "note"}))),
        MachineSpec("THIRD_EPSILON", held_epsilon, {},
                    tuple(executed_runs(held_epsilon, {}))),
        MachineSpec("NO_RELOCATION_SOURCE", pointerless, {},
                    tuple(executed_runs(pointerless, {}))),
    ]
    by_name = {spec.name: spec for spec in specs}
    fit = list(by_name["MOVE_ALPHA"].records) + list(by_name["EXTRA_BETA"].records)
    select_records = list(by_name["DELAY_GAMMA"].records)
    usable_select = [record for record in select_records if content_pointer(record) is not None]
    held = list(by_name["OVERWRITE_DELTA"].records)
    third = list(by_name["THIRD_EPSILON"].records)
    pointerless_records = list(by_name["NO_RELOCATION_SOURCE"].records)

    terms, combos, truth = fit_computed_relation(fit, moved_judge)
    candidates = candidates_from(terms, combos)
    separating = answers.separating_runs(candidates, usable_select)
    if not separating:
        raise RuntimeError("NO_REAL_RUN_SEPARATES_THE_POINTER_RELATIVE_STATEMENTS")
    budget = math.ceil(math.log2(len(candidates)))
    survivors, judgments = collapse_with_judgments(candidates, usable_select, moved_judge,
                                                    budget=budget)
    collapsed = len(survivors) == 1 and len(judgments) <= budget
    if not collapsed or not judgments:
        raise RuntimeError("REAL_JUDGMENTS_DID_NOT_COLLAPSE_THE_POINTER_RELATIVE_CLASS")
    chosen = usable_select[judgments[-1]["run_index"]]
    verdict = bool(judgments[-1]["judgment_on_the_run"])
    survivor_combo = next(combo for combo in combos
                          if " and ".join(terms[i].text for i in combo) == survivors[0].text)
    relation_texts = [terms[int(i)].text for i in survivor_combo]
    store_record = save_relation(STORE, relation_texts,
                                 {"judgment_on_the_run": verdict,
                                  "chosen_run_steps": judgments[-1]["run_steps"],
                                  "judgments_on_runs": len(judgments),
                                  "judgment_budget_ceil_log2_class": budget,
                                  "fit_runs": len(fit)})

    held_prediction = replay(STORE, held, moved_judge)
    third_prediction = replay(STORE, third, moved_judge)
    pointerless_prediction = replay(STORE, pointerless_records, moved_judge)
    old_status = old_store_status(held)

    copy_path = where / "deletable_content_pointer_relation.json"
    shutil.copyfile(STORE, copy_path)
    copy_prediction = replay(copy_path, held, moved_judge)
    copy_path.unlink()
    deleted_prediction = replay(copy_path, held, moved_judge)
    shutil.copyfile(STORE, copy_path)
    restored_prediction = replay(copy_path, held, moved_judge)

    raw = raw_trace_control(fit, held)
    naive = naive_pointer_errors(usable_select, relation_texts, moved_judge)
    prior = json.loads(PRIOR_RECEIPT.read_text(encoding="utf-8"))
    prior_canonical = prior["verdict"]["R6_killed_designs_are_measured"]

    identities, contents = machine_literals(specs)
    store_text = json.dumps(store_record, ensure_ascii=False)
    identity_leaks = [literal for literal in identities if contains_literal(store_text, literal)]
    content_leaks = [literal for literal in contents if contains_literal(store_text, literal)]
    term_texts_join = "\n".join(term.text for term in terms)
    term_identity_leaks = [literal for literal in identities if contains_literal(term_texts_join, literal)]
    term_content_leaks = [literal for literal in contents if contains_literal(term_texts_join, literal)]
    fit_exact = all(bool(candidate.holds(record)) == bool(moved_judge(record))
                    for candidate in candidates for record in fit)
    pointer_counts = {spec.name: {"runs": len(spec.records),
                                  "pointer_failures": sum(content_pointer(record) is None for record in spec.records),
                                  "pointer_contents": observed_pointers(spec.records)}
                      for spec in specs}

    verdict_rows = {
        "C1_prior_literal_store_refuses_and_terms_are_literal_free": {
            "old_store": old_status,
            "computed_terms": len(terms),
            "term_identity_literal_leaks": term_identity_leaks,
            "term_content_literal_leaks": term_content_leaks,
            "MET": (old_status["status"] == "REFUSED__GOAL_CONTENT_OR_TERMS_NOT_RECOMPUTED"
                    and not term_identity_leaks and not term_content_leaks),
        },
        "C2_three_pointer_statements_and_two_real_delayed_judgments": {
            "fit_runs": len(fit),
            "minimal_statements": [candidate.text for candidate in candidates],
            "fit_exact": fit_exact,
            "select_runs": len(select_records),
            "select_pointer_failures": pointer_counts["DELAY_GAMMA"]["pointer_failures"],
            "separating_runs": len(separating),
            "judgment_budget_ceil_log2_class": budget,
            "judgments": judgments,
            "judgments_on_runs": len(judgments),
            "questions_about_statements": 0,
            "survivor": survivors[0].text,
            "class_after": len(survivors),
            "MET": (len(candidates) == 3 and fit_exact and len(separating) > 0
                    and collapsed and len(judgments) == 2 and budget == 2),
        },
        "C3_exact_new_content_held_out_prediction": {
            "prediction": {key: value for key, value in held_prediction.items() if key != "predictions"},
            "MET": (held_prediction["status"] == "PREDICTED"
                    and held_prediction["false_accepts"] == 0
                    and held_prediction["false_rejects"] == 0
                    and held_prediction["abstentions"] == 0),
        },
        "C4_third_new_names_and_no_literals_in_store": {
            "prediction": {key: value for key, value in third_prediction.items() if key != "predictions"},
            "identity_literals_in_store": identity_leaks,
            "content_literals_in_store": content_leaks,
            "store": str(STORE.relative_to(REPO)),
            "MET": (third_prediction["status"] == "PREDICTED"
                    and third_prediction["false_accepts"] == 0
                    and third_prediction["false_rejects"] == 0
                    and third_prediction["abstentions"] == 0
                    and not identity_leaks and not content_leaks),
        },
        "C5_fail_closed_deletion_restore_raw_and_old_store": {
            "pointerless_machine": {key: value for key, value in pointerless_prediction.items()
                                    if key != "predictions"},
            "deleted_store": deleted_prediction,
            "restored_store": {key: value for key, value in restored_prediction.items()
                               if key != "predictions"},
            "copy_before_deletion": {key: value for key, value in copy_prediction.items()
                                     if key != "predictions"},
            "raw_exact_experience": raw,
            "relation_abstentions": held_prediction["abstentions"],
            "MET": (pointerless_prediction["status"] == "REFUSED__CONTENT_POINTER_NOT_RECOMPUTED"
                    and pointerless_prediction["abstentions"] == len(pointerless_records)
                    and deleted_prediction["status"] == "REFUSED__NO_RELATION"
                    and restored_prediction["status"] == "PREDICTED"
                    and raw["abstentions"] > 0 and held_prediction["abstentions"] == 0
                    and old_status["status"] == "REFUSED__GOAL_CONTENT_OR_TERMS_NOT_RECOMPUTED"),
        },
        "C6_killed_designs_are_measured": {
            "naive_initial_content_pointer": naive,
            "raw_exact_experience": raw,
            "prior_full_canonical_trace_table": {
                "overwrite_abstentions": prior_canonical["full_canonical_trace_table_overwrite"]["abstentions"],
                "third_name_abstentions": prior_canonical["full_canonical_trace_table_third"]["abstentions"],
            },
            "model_proposed_pointer": "forbidden and not used",
            "MET": (naive["errors"] > 0 and raw["abstentions"] > 0
                    and prior_canonical["full_canonical_trace_table_overwrite"]["abstentions"] > 0
                    and prior_canonical["full_canonical_trace_table_third"]["abstentions"] > 0),
        },
        "C7_zeros_and_real_execution": {
            "model_calls": 0, "parameters_stored": 0, "network_calls_at_run_time": 0,
            "real_runs": {spec.name: len(spec.records) for spec in specs},
            "MET": True,
        },
    }

    out = {
        "schema": SCHEMA, "authority": "NONE__PRODUCER_RUN_SANDBOX", "date": "2026-11-23",
        "branch": "arena/6f8ac9ce-brain",
        "mode": "COMPUTE_THE_CONTENT_POINTER_FROM_THE_EXECUTOR_CALL_LOG",
        "declared_before_the_run": DECLARED_BEFORE_THE_RUN,
        "content_pointer": {"text": POINTER_TEXT, "definition": POINTER_DEFINITION,
                            "source": "executor_call_log_and_machine_readings"},
        "computed_grammar": {
            "term_family": "computed_deictic_holder_shape_v1",
            "terms": len(terms), "feature_order": list(holder.FEATURE_ORDER),
            "minimal_statements": [candidate.text for candidate in candidates],
        },
        "fit": {"machines": ["MOVE_ALPHA", "EXTRA_BETA"], "runs": len(fit),
                "truth_mask_popcount": truth.bit_count(), "pointer_counts": pointer_counts},
        "question": {"environment": "DELAY_GAMMA", "separating_runs": len(separating),
                     "judgment_budget_ceil_log2_class": budget,
                     "judgments": judgments,
                     "judgments_on_runs": len(judgments),
                     "questions_about_statements": 0,
                     "survivor": survivors[0].text,
                     "last_chosen_pointer_content": content_pointer(chosen)},
        "store": {"path": str(STORE.relative_to(REPO)), "schema": STORE_SCHEMA,
                  "texts": relation_texts,
                  "sha256": hashlib.sha256(STORE.read_bytes()).hexdigest()[:16],
                  "identity_literal_leaks": identity_leaks,
                  "content_literal_leaks": content_leaks},
        "verdict": verdict_rows,
        "all_criteria_met": all(row["MET"] for row in verdict_rows.values()),
        "killed_designs": {
            "literal_content_store": old_status,
            "naive_initial_content_pointer": naive,
            "raw_exact_experience": raw,
            "full_canonical_trace_table": {
                "receipt": str(PRIOR_RECEIPT.relative_to(REPO)),
                "overwrite_abstentions": prior_canonical["full_canonical_trace_table_overwrite"]["abstentions"],
                "third_name_abstentions": prior_canonical["full_canonical_trace_table_third"]["abstentions"],
            },
            "model_proposed_pointer": "forbidden runtime dependency; not used",
        },
        "limits": [
            "the pointer requires an executor call log with a relocation source; a machine without one refuses",
            "this is a typed deictic pointer, not free-form natural-language instruction understanding",
            "no GUI, browser, OSWorld 2.1, SWE-bench Pro / Pro V2 or Terminal-Bench task was run",
            "producer-run sandbox; no independent identity re-ran this receipt",
            "no capability registered and no truth achieved",
        ],
        "cost": {"seconds": round(time.time() - started, 2), "model_calls": 0,
                 "parameters_stored": 0, "network_calls_at_run_time": 0},
    }
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({key: row["MET"] for key, row in verdict_rows.items()}, indent=1))
    print(json.dumps({"survivor": survivors[0].text,
                      "held": {k: v for k, v in held_prediction.items() if k != "predictions"},
                      "third": {k: v for k, v in third_prediction.items() if k != "predictions"},
                      "pointerless": pointerless_prediction,
                      "naive_errors": naive["errors"]}, indent=1))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    options = parser.parse_args()
    measure(options.receipt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
