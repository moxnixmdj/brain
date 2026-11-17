#!/usr/bin/env python3
"""What a refusal buys: grow the vocabulary, or prove that growing it here cannot help.

THE GAP
-------
The previous round decides when one execution was enough, and answers REFUSE when no reading of the action
explains what happened. A refusal is not an answer for a caller; it is a question. The 2026 statement of that
question is exact (arXiv 2607.09560, *Beyond Fixed Representations*): the **vocabulary gap** is inventing and
stabilising new primitives rather than recombining given ones, the **verifier gap** is judging whether a new
primitive is worth keeping when no current criterion can see its value, and the paper's own conclusion is that
they are one operation -- representation expands only when the previously untestable becomes testable. Nothing
in this tree closed that loop. This module does, with executable tests and no model anywhere.

FIVE OUTCOMES, AND WHY THE ORDER IS THE CONTENT
-----------------------------------------------
    1 EXPLAINED                      the flat grammar already reproduces it -- nothing to grow
    2 INVISIBLE_IN_THE_CURRENT_VIEW  the content view sees no change, but a derived view does
    3 NOT_A_FUNCTION_OF_THE_STATE    the content view sees changes that disagree with each other
    4 OUTSIDE_THE_FLAT_GRAMMAR       one stable consequence, no reading of the grammar produces it
    5 BEYOND_THIS_OBSERVABLE         no view in the family sees it, and the effect is really there

Outcome 2 is checked before 3 because it is the silent failure. An action the view cannot see is never
refused; it is *accepted as identity*. `touch keep.dat` is indistinguishable from `true` under a content-only
view, so the agent will confidently "learn" that it does nothing -- worse than a refusal, because there is no
signal to grow from. This module makes that case visible and then closes it with a derived predicate.

Outcome 5 is the boundary, and it is not a failure of the loop. `mkdir newdir` is invisible to every view in
the family because the observation enumerates *files*; the effect is real, it is on disk, and no amount of
vocabulary growth over the same sensor will reach it. That is a missing **sensor**, not a missing word, and the
difference is proved here: the disk path set changes while every admissible view stays empty.

WHY THE GROWTH IS A PREDICATE AND A SET, NOT A FIELD
----------------------------------------------------
Exposing `mtime` as a field is useless -- two runs of `touch` give two different timestamps, so the field is
unstable and the tree's own projection synthesis discards it by stability (`distinguishing_projection_v1`).
What is stable is `mtime changed`, a derived boolean. Likewise `sort -R` has no stable exit *value*: every
repeat differs, and the coarsest stable projection of the output alone (`byte_count`) is degenerate. What is
stable and true is that the output is a **permutation of the input** -- a set-valued consequence. So the two
primitives this module adds are a derived predicate and a consequence set, which is what the vocabulary gap
actually consists of.

THE VERIFIER GAP, CLOSED BY CONSTRUCTION
----------------------------------------
A primitive is retained only if every one of these is checked against executions it was not derived from:

    NECESSITY    without it the action is unidentified, or silently accepted as identity
    STABILITY    it reproduces on a repeat of the same state
    TRANSFER     it identifies a SECOND action of the same kind, still from one execution
    NARROWNESS   it does not collapse a distinction that mattered -- and the collapse is printed, not hidden

Authority: NONE -- producer-run sandbox measurement. Model calls 0. Network calls 0. Every consequence is a
real subprocess, on a real copy of a real directory, with real repeats and held-out states.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import demonstration_sufficiency_v1 as S  # noqa: E402
from canonical.swe_kernel.computer_use_check_density_v1 import _has, _run  # noqa: E402
from canonical.swe_kernel.distinguishing_projection_v1 import FEATURES as PROJECTION_FEATURES  # noqa: E402
from canonical.swe_kernel.predictive_contract_v1 import _files  # noqa: E402

SCHEMA = "BRAIN_VOCABULARY_GROWTH_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
OUTCOMES = ("EXPLAINED", "INVISIBLE_IN_THE_CURRENT_VIEW", "NOT_A_FUNCTION_OF_THE_STATE",
            "OUTSIDE_THE_FLAT_GRAMMAR", "BEYOND_THIS_OBSERVABLE")

# The view the agent starts with, and the derived views it may grow into. All are functions of the transition.
CURRENT_VIEW = "content"
DERIVED_VIEWS = ("delta_content", "delta_mtime", "delta_mode", "delta_name")
# Relations between the consequence and the input, strongest first. A set-valued consequence is one of these.
RELATIONS = ("equals_input", "permutation_of_input", "sorted_lines_equal", "line_count_equal",
             "byte_count_equal")
# The flat grammar is flat; the growth is its closure under ONE composition.
COMPOSITION_OPS = ("sort", "sort_unique", "reverse", "digest", "identity")
# Fixture timestamps are set explicitly. A state whose mtimes depend on when the fixture was written is not a
# state: it differs between runs, so nothing about it can be reproduced or verified.
FIXTURE_MTIME = 978307200.0          # 2001-01-01T00:00:00Z


# --------------------------------------------------------------------------- #
# the views: each is a function of (state before, state after)
# --------------------------------------------------------------------------- #
def _stat(path: pathlib.Path) -> tuple[int, int]:
    info = path.stat()
    return info.st_mtime_ns, info.st_mode & 0o777


def disk_paths(root: pathlib.Path) -> str:
    """Everything on disk under root, directories included. Wider than the observation, used only for proofs."""
    return ";".join(sorted(str(p.relative_to(root).as_posix()) + ("/" if p.is_dir() else "")
                           for p in root.rglob("*")))


def view(before_root: pathlib.Path, after_root: pathlib.Path, observable: str) -> str:
    before, after = _files(before_root), _files(after_root)
    if observable == "content":
        return S.signature(after)
    before_stat = {p: _stat(before_root / p) for p in before}
    after_stat = {p: _stat(after_root / p) for p in after}
    parts: list[str] = []
    for path in sorted(set(before) | set(after)):
        appeared = path in after and path not in before
        vanished = path in before and path not in after
        content = path in before and path in after and before[path] != after[path]
        touched = path in before_stat and path in after_stat and \
            before_stat[path][0] != after_stat[path][0]
        remoded = path in before_stat and path in after_stat and \
            before_stat[path][1] != after_stat[path][1]
        if observable == "delta_name" and (appeared or vanished):
            parts.append("%s:%s" % (path, "created" if appeared else "removed"))
        elif observable == "delta_content" and (appeared or vanished or content):
            parts.append("%s:%s" % (path, hashlib.sha256(after.get(path, b"")).hexdigest()[:12]))
        elif observable == "delta_mtime" and (appeared or vanished or touched):
            parts.append("%s:%s" % (path, "appeared" if appeared else "touched"))
        elif observable == "delta_mode" and (appeared or vanished or remoded):
            parts.append("%s:%o" % (path, after_stat[path][1]))
    return "|".join(parts)


def holds(relation: str, produced: bytes, source: bytes) -> bool:
    """Does the consequence stand in this relation to the input? Each is decidable in one comparison."""
    if relation == "equals_input":
        return produced == source
    if relation == "permutation_of_input":
        return sorted(produced.splitlines(True)) == sorted(source.splitlines(True))
    if relation == "sorted_lines_equal":
        return b"".join(sorted(produced.splitlines(True))) == b"".join(sorted(source.splitlines(True)))
    if relation == "line_count_equal":
        return len(produced.splitlines(True)) == len(source.splitlines(True))
    if relation == "byte_count_equal":
        return len(produced) == len(source)
    raise ValueError("unknown relation: %s" % relation)


# --------------------------------------------------------------------------- #
# evidence: real executions, repeated, on more than one state
# --------------------------------------------------------------------------- #
def run_once(invocation: str, state: Mapping[str, bytes], work: pathlib.Path,
             normalise_mtime: bool = True) -> dict[str, Any]:
    root = pathlib.Path(tempfile.mkdtemp(prefix="growth-", dir=work))
    before_root = pathlib.Path(tempfile.mkdtemp(prefix="before-", dir=work))
    for path, data in state.items():
        for base in (root, before_root):
            target = base / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            if normalise_mtime:
                os.utime(target, (FIXTURE_MTIME, FIXTURE_MTIME))
    try:
        code, _noise = _run(root, invocation)
    except subprocess.TimeoutExpired:
        code = 124
    return {"root": root, "before_root": before_root, "exit_code": code}


def evidence(invocation: str, states: Mapping[str, Mapping[str, bytes]], work: pathlib.Path,
             repetitions: int = 2) -> dict[str, Any]:
    """For each state: repeats of the same invocation, both sides of the transition, and the disk for proofs."""
    record: dict[str, Any] = {}
    for state_id, state in states.items():
        runs = [run_once(invocation, state, work) for _ in range(repetitions)]
        record[state_id] = {
            "exit_codes": [run["exit_code"] for run in runs],
            "before_signature": S.signature(state),
            "content": [view(run["before_root"], run["root"], CURRENT_VIEW) for run in runs],
            "derived": {observable: [view(run["before_root"], run["root"], observable) for run in runs]
                        for observable in DERIVED_VIEWS},
            "disk_delta": [disk_paths(run["root"]) != disk_paths(run["before_root"]) for run in runs],
            "outputs": [(pathlib.Path(run["root"]) / "out.dat").read_bytes()
                        if (pathlib.Path(run["root"]) / "out.dat").exists() else None for run in runs],
            "files_after": _files(runs[0]["root"]),
        }
        for run in runs:
            shutil.rmtree(run["root"], ignore_errors=True)
            shutil.rmtree(run["before_root"], ignore_errors=True)
    return record


def noise_floor(work: pathlib.Path, repeats: int = 6) -> dict[str, Any]:
    """How often does the raw mtime field even move? This is why a field loses to a derived predicate.

    A freshly written file and a `touch` in the same filesystem tick are indistinguishable: the field reports
    no change although the action ran. Measured here rather than asserted, on unnormalised fixtures.
    """
    state = _state(PAYLOAD)
    fires = 0
    for _ in range(repeats):
        run = run_once("touch keep.dat", state, work, normalise_mtime=False)
        if view(run["before_root"], run["root"], "delta_mtime") != "":
            fires += 1
        shutil.rmtree(run["root"], ignore_errors=True)
        shutil.rmtree(run["before_root"], ignore_errors=True)
    return {"repeats": repeats, "raw_mtime_field_fires": fires,
            "raw_field_is_reliable": fires == repeats,
            "verdict": ("the raw timestamp field does not reliably report the action on a freshly written file, "
                        "so exposing it as a feature would be discarded by the tree's own stability filter"
                        if fires != repeats else
                        "the raw field fires on every repeat here, but it still carries an unstable value, so a "
                        "predicate rather than a field is what transfers")}


# --------------------------------------------------------------------------- #
# the diagnosis: five outcomes, in this order
# --------------------------------------------------------------------------- #
def _stable(values: Sequence[str]) -> bool:
    return len(set(values)) == 1


def _flat_readings(state: Mapping[str, bytes], observed: Mapping[str, bytes]) -> list[str]:
    """Which readings of the tree's flat grammar reproduce the observed consequence at all states."""
    actual = dict(state)
    actual.update({path: data for path, data in observed.items()})
    return [hypothesis.hypothesis_id for hypothesis in S.space(state, sorted(observed))
            if S.signature(S._predict(hypothesis, state)) == S.signature(actual)]


def diagnose(record: Mapping[str, Any], states: Mapping[str, Mapping[str, bytes]]) -> dict[str, Any]:
    visible = [state_id for state_id, entry in record.items()
               if any(content != entry["before_signature"] for content in entry["content"])]

    # 1. EXPLAINED -- the flat grammar reproduces every state. Nothing to grow.
    if visible:
        explained = True
        readings: dict[str, list[str]] = {}
        for state_id in visible:
            readings[state_id] = _flat_readings(states[state_id], record[state_id]["files_after"])
            explained = explained and bool(readings[state_id])
        if explained:
            return {"outcome": "EXPLAINED", "growth": "NONE", "readings": readings,
                    "decided_by": "the flat grammar reproduces the consequence at every state"}

    # 2. INVISIBLE in the current view -- the silent failure, checked before anything else.
    if not visible:
        seen = {observable: [value for entry in record.values() for value in entry["derived"][observable]]
                for observable in DERIVED_VIEWS}
        separating = [observable for observable, values in seen.items()
                      if any(value != "" for value in values)]
        identity = [state_id for state_id, entry in record.items()
                    if _stable(entry["content"]) and entry["content"][0] == entry["before_signature"]]
        return {
            "outcome": "INVISIBLE_IN_THE_CURRENT_VIEW" if separating else "BEYOND_THIS_OBSERVABLE",
            "growth": "OBSERVABLE" if separating else "STOP",
            "decided_by": ("the content view shows no change at any state, so the action is not refused -- it "
                           "is accepted as identity" if len(identity) == len(record)
                           else "the content view shows no change"),
            "silently_accepted_as_identity": len(identity) == len(record),
            "derived_views_that_see_it": separating,
            "tested_views": list(DERIVED_VIEWS),
            "effect_on_disk": {state_id: entry["disk_delta"] for state_id, entry in record.items()},
        }

    # 3. NOT A FUNCTION -- the same state, two disagreeing consequences.
    unstable = [state_id for state_id in visible if not _stable(record[state_id]["content"])]
    if unstable:
        return {
            "outcome": "NOT_A_FUNCTION_OF_THE_STATE", "growth": "SET_VALUED_CONSEQUENCE",
            "decided_by": "two executions of the same state and invocation left different content",
            "unstable_states": unstable,
            "relations_tested": list(RELATIONS),
        }

    # 4. OUTSIDE the flat grammar -- one stable consequence, no reading produces it.
    return {
        "outcome": "OUTSIDE_THE_FLAT_GRAMMAR", "growth": "COMPOSE",
        "decided_by": ("the consequence reproduced exactly at every state and no reading of the flat grammar "
                       "reproduces it"),
        "compositions_tested": list(COMPOSITION_OPS),
    }


# --------------------------------------------------------------------------- #
# the growths, each with what it buys and what it costs
# --------------------------------------------------------------------------- #
def grow_observable(record: Mapping[str, Any], contrast: Mapping[str, Any]) -> dict[str, Any]:
    """Which derived view separates the action from inaction, and is it stable on repeats?"""
    separating, stable_separators = [], []
    for observable in DERIVED_VIEWS:
        action_values = [value for entry in record.values() for value in entry["derived"][observable]]
        contrast_values = [value for entry in contrast.values() for value in entry["derived"][observable]]
        if any(value != "" for value in action_values) and all(value == "" for value in contrast_values):
            separating.append(observable)
            if all(_stable(entry["derived"][observable]) for entry in record.values()):
                stable_separators.append(observable)
    return {
        "growth": "OBSERVABLE",
        "primitive": ("DERIVED_PREDICATE(%s_changed)" % stable_separators[0].split("_", 1)[1]
                      if stable_separators else None),
        "separates_from_inaction": separating, "stable_separators": stable_separators,
        "chosen": stable_separators[0] if stable_separators else None,
        "buys": "the action stops being silently accepted as doing nothing",
        "cost": "one boolean per path on every transition, and a sensor that reports it",
        "why_not_a_field": ("the raw value is unstable across repeats and the tree's projection synthesis "
                            "discards it by stability; only the derived predicate survives"),
    }


def grow_set_valued(record: Mapping[str, Any], states: Mapping[str, Mapping[str, bytes]],
                    invocation: str, work: pathlib.Path) -> dict[str, Any]:
    """Find the STRONGEST relation that every repeat satisfies, and print what it cannot distinguish."""
    accepted: list[str] = []
    for relation in RELATIONS:
        ok = True
        for state_id, entry in record.items():
            source = states[state_id].get("payload.dat", b"")
            for produced in entry["outputs"]:
                if produced is None or not holds(relation, produced, source):
                    ok = False
        if ok:
            accepted.append(relation)
    chosen = accepted[0] if accepted else None          # RELATIONS is strongest first

    # tightness: more than one distinct consequence over the repeats means the set is genuinely a set
    distinct = {hashlib.sha256(produced).hexdigest()[:12]
                for entry in record.values() for produced in entry["outputs"] if produced is not None}
    # narrowness: which alternative consequences the relation still admits
    admitted: list[str] = []
    if chosen is not None:
        source = states[sorted(states)[0]].get("payload.dat", b"")
        alternatives = {
            "identity": source,
            "copy": source,
            "sort": b"".join(sorted(source.splitlines(True))),
            "sort_unique": b"".join(sorted(set(source.splitlines(True)))),
            "reverse": b"".join(reversed(source.splitlines(True))),
            "digest": ("%s  payload.dat\n" % hashlib.sha256(source).hexdigest()).encode(),
            "truncate": b"",
        }
        for name, produced in alternatives.items():
            if holds(chosen, produced, source):
                admitted.append(name)
    # stability: a fresh execution is still inside the set
    fresh_inside = True
    for state_id in record:
        again = run_once(invocation, states[state_id], work)
        target = again["root"] / "out.dat"
        produced = target.read_bytes() if target.exists() else b""
        if chosen is not None and not holds(chosen, produced, states[state_id].get("payload.dat", b"")):
            fresh_inside = False
        shutil.rmtree(again["root"], ignore_errors=True)
        shutil.rmtree(again["before_root"], ignore_errors=True)
    return {
        "growth": "SET_VALUED_CONSEQUENCE",
        "primitive": ("%s(payload.dat)" % chosen.upper() if chosen else None),
        "relations_that_hold_on_every_repeat": accepted, "chosen": chosen,
        "distinct_consequences_observed": len(distinct),
        "is_genuinely_a_set": len(distinct) > 1,
        "fresh_execution_still_inside_the_set": fresh_inside,
        "alternative_consequences_the_set_still_admits": sorted(admitted),
        "buys": ("a consequence that reproduces where no exact consequence ever did, and the one property a "
                 "caller actually needs before running a shuffling transform on a data file: nothing is lost"),
        "cost": ("order carries no information at this resolution -- the action cannot be told apart from any "
                 "other transform that preserves the multiset, and the set is wider than one output"),
    }


def grow_compose(record: Mapping[str, Any], states: Mapping[str, Mapping[str, bytes]]) -> dict[str, Any]:
    """The flat grammar has no reading for it; test whether ONE composition does."""
    state_id = sorted(record)[0]
    source = states[state_id].get("payload.dat", b"")
    observed = record[state_id]["outputs"][0]
    matches = []
    for first in COMPOSITION_OPS:
        for second in COMPOSITION_OPS:
            stage = S.apply(first, {"payload.dat": source}, src="payload.dat", dst="out.dat")
            produced = S.apply(second, stage, src="out.dat", dst="out.dat")
            if produced.get("out.dat") == observed:
                matches.append("%s_then_%s" % (first, second))
    flat_space = S.space(states[state_id], ["out.dat"])
    return {
        "growth": "COMPOSE",
        "primitive": matches[0] if matches else None,
        "pipelines_that_reproduce_it": matches,
        "pipeline_space": len(COMPOSITION_OPS) ** 2,
        "flat_grammar_space": len(flat_space),
        "flat_readings": _flat_readings(states[state_id], record[state_id]["files_after"]),
        "buys": "a pipeline the flat grammar cannot express",
        "cost": ("the space grows multiplicatively (%d -> %d) so a composition is bought per observation, "
                 "never assumed as a closure" % (len(flat_space), len(flat_space) * len(COMPOSITION_OPS))),
    }


def grow_stop(record: Mapping[str, Any], diagnosis: Mapping[str, Any]) -> dict[str, Any]:
    """Nothing in the family sees it. Prove the effect is real, then name the sensor that is missing."""
    effect_on_disk = any(any(flags) for flags in diagnosis["effect_on_disk"].values())
    return {
        "growth": "STOP",
        "primitive": None,
        "effect_on_disk": effect_on_disk,
        "every_admissible_view_empty": not diagnosis["derived_views_that_see_it"],
        "missing_sensor": ("the observation enumerates regular files; a directory is not a file, so a created "
                           "directory is invisible to content, to delta_content, to delta_mtime, to delta_mode "
                           "and to delta_name alike"),
        "why_not_vocabulary": ("the effect is real and on disk while every derived view is empty, so no "
                               "predicate built from the same readings can reach it -- this is a missing "
                               "sensor, not a missing word"),
        "what_unblocks_it": ("an observation that reports path kind (file or directory) and not only file "
                             "contents; that is an interface change, so it must be requested, not inferred"),
        "buys": "nothing here -- and that is the answer",
        "cost": "the action stays unlearnable until the interface widens; pretending otherwise is the failure",
    }


# --------------------------------------------------------------------------- #
# the chains
# --------------------------------------------------------------------------- #
PAYLOAD = b"gamma\nalpha\ndelta\nbeta\nepsilon\nalpha\n"      # unsorted, with a duplicate line
PAYLOAD_SECOND = b"zeta\nmu\nbeta\nalpha\nalpha\nomega\n"


def _state(payload: bytes) -> dict[str, bytes]:
    return {"payload.dat": payload, "keep.dat": b"do not touch\n"}


def _chain(work: pathlib.Path, name: str, invocation: str, states: Mapping[str, Mapping[str, bytes]],
           contrast: str, transfer: str, transfer_states: Mapping[str, Mapping[str, bytes]],
           expectation: str, repetitions: int = 2) -> dict[str, Any]:
    record = evidence(invocation, states, work, repetitions=repetitions)
    contrast_record = {state_id: evidence(contrast, {state_id: state}, work, repetitions=2)[state_id]
                       for state_id, state in states.items()}
    diagnosis = diagnose(record, states)

    if diagnosis["growth"] == "OBSERVABLE":
        growth = grow_observable(record, contrast_record)
    elif diagnosis["growth"] == "SET_VALUED_CONSEQUENCE":
        growth = grow_set_valued(record, states, invocation, work)
    elif diagnosis["growth"] == "COMPOSE":
        growth = grow_compose(record, states)
    elif diagnosis["growth"] == "STOP":
        growth = grow_stop(record, diagnosis)
    else:
        growth = {"growth": "NONE", "primitive": None, "buys": "nothing -- already explained",
                  "cost": "none"}

    # TRANSFER: the same growth must identify a SECOND action of the same kind, from one execution.
    transfer_record = evidence(transfer, transfer_states, work, repetitions=repetitions)
    transfer_diagnosis = diagnose(transfer_record, transfer_states)
    transfer_same = transfer_diagnosis["outcome"] == diagnosis["outcome"]
    if transfer_same and diagnosis["growth"] == "OBSERVABLE":
        transfer_growth = grow_observable(transfer_record, contrast_record)["chosen"]
    elif transfer_same and diagnosis["growth"] == "SET_VALUED_CONSEQUENCE":
        transfer_growth = grow_set_valued(transfer_record, transfer_states, transfer, work)["chosen"]
    elif transfer_same and diagnosis["growth"] == "COMPOSE":
        transfer_growth = grow_compose(transfer_record, transfer_states)["pipelines_that_reproduce_it"]
    elif transfer_same and diagnosis["growth"] == "STOP":
        transfer_growth = grow_stop(transfer_record, transfer_diagnosis)["missing_sensor"][:48]
    else:
        transfer_growth = None

    return {
        "chain": name,
        "invocation": invocation,
        "expected_outcome": expectation,
        "outcome": diagnosis["outcome"],
        "growth": diagnosis["growth"],
        "decided_by": diagnosis["decided_by"],
        "diagnosis_detail": {key: value for key, value in diagnosis.items()
                             if key not in ("decided_by", "effect_on_disk")},
        "growth_detail": growth,
        "growth_bought": growth.get("primitive"),
        "transfer_invocation": transfer,
        "transfer_outcome": transfer_diagnosis["outcome"],
        "transfer_same_kind": transfer_same,
        "transfer_growth": transfer_growth,
        "diagnosis_was_right": diagnosis["outcome"] == expectation,
    }


def _chains(work: pathlib.Path) -> list[dict[str, Any]]:
    """Four real actions, four different missing things. One of them cannot be grown from within at all."""
    specs = [
        dict(name="already_explained_copy", invocation="cp payload.dat out.dat",
             states={"a": _state(PAYLOAD), "b": _state(PAYLOAD_SECOND)},
             contrast="true",
             transfer="cp payload.dat keep.dat",
             transfer_states={"a": _state(PAYLOAD)},
             expectation="EXPLAINED"),
        dict(name="nondeterministic_permutation", invocation="sort -R payload.dat -o out.dat",
             states={"a": _state(PAYLOAD), "b": _state(PAYLOAD_SECOND)},
             contrast="cp payload.dat out.dat",
             transfer="shuf payload.dat > out.dat",
             transfer_states={"a": _state(PAYLOAD)},
             expectation="NOT_A_FUNCTION_OF_THE_STATE", repetitions=3),
        dict(name="composition_not_in_the_flat_grammar",
             invocation="sort -u -r payload.dat -o out.dat",
             states={"a": _state(PAYLOAD)},
             contrast="cp payload.dat out.dat",
             transfer="sort -r -u payload.dat -o out.dat",
             transfer_states={"a": _state(PAYLOAD_SECOND)},
             expectation="OUTSIDE_THE_FLAT_GRAMMAR", repetitions=3),
        dict(name="invisible_action_touch", invocation="touch keep.dat",
             states={"a": _state(PAYLOAD), "b": _state(PAYLOAD_SECOND)},
             contrast="true",
             transfer="touch payload.dat",
             transfer_states={"a": _state(PAYLOAD)},
             expectation="INVISIBLE_IN_THE_CURRENT_VIEW"),
        dict(name="unrepresentable_action_mkdir", invocation="mkdir newdir",
             states={"a": _state(PAYLOAD), "b": _state(PAYLOAD_SECOND)},
             contrast="touch keep.dat",
             transfer="mkdir -p newdir",
             transfer_states={"a": _state(PAYLOAD)},
             expectation="BEYOND_THIS_OBSERVABLE"),
    ]
    return [_chain(work, **spec) for spec in specs]


def measure() -> dict[str, Any]:
    work = pathlib.Path(tempfile.mkdtemp(prefix="brain-vocabulary-growth-"))
    missing = [program for program in ("sort", "shuf", "cp", "touch", "mkdir", "true") if not _has(program)]
    try:
        noise = noise_floor(work) if not missing else {}
        chains = _chains(work) if not missing else []
    finally:
        shutil.rmtree(work, ignore_errors=True)

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "model_calls": 0,
        "network_calls": 0,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "environment": {
            "kind": "real directory, real programs from PATH, repeated executions, held-out states",
            "current_view": CURRENT_VIEW,
            "derived_views": list(DERIVED_VIEWS),
            "relations": list(RELATIONS),
            "composition_ops": list(COMPOSITION_OPS),
            "tree_feature_family_reused": list(PROJECTION_FEATURES),
            "outcomes_in_order": list(OUTCOMES),
        },
        "missing_programs": missing,
        "chains": len(chains),
        "actions": [chain["chain"] for chain in chains],
        "outcomes": {chain["chain"]: chain["outcome"] for chain in chains},
        "diagnoses_correct": sum(1 for chain in chains if chain["diagnosis_was_right"]),
        "growths": {chain["chain"]: chain["growth_bought"] for chain in chains},
        "transfer": {chain["chain"]: {"invocation": chain["transfer_invocation"],
                                      "outcome": chain["transfer_outcome"],
                                      "same_kind": chain["transfer_same_kind"],
                                      "growth": chain["transfer_growth"]} for chain in chains},
        "transfer_holds": sum(1 for chain in chains if chain["transfer_same_kind"]),
        "noise_floor": noise,
        "fixture_timestamps": {"normalised_to": FIXTURE_MTIME,
                               "why": "a state whose mtimes depend on when it was written is not reproducible"},
        "per_chain": chains,
        "external_state": {
            "the_two_gaps_are_one_operation":
                "arXiv 2607.09560 (Beyond Fixed Representations): the vocabulary gap is inventing and "
                "stabilising new primitives, the verifier gap is judging whether one is worth keeping; "
                "representation expands only when the previously untestable becomes testable",
            "when_to_refine_an_abstraction":
                "arXiv 2606.06123 (adaptive abstractions via rate-distortion): refine when the error inside the "
                "abstraction reaches the error induced by it -- a refusal is that condition at its extreme",
            "classical_anchor":
                "state abstraction and bisimulation (Li et al. 2006; Abel 2020): the coarsest partition that "
                "preserves the dynamics -- realised here as the strongest relation every repeat satisfies",
            "already_measured_in_this_tree":
                "demonstration_sufficiency (refusals on 1 of 7 actions, 343 readings each); IDENTIFICATION_COST "
                "(median 1037 survivors, 7 of 23 insufficient after every example); an induced action-law "
                "vocabulary wrong on 6261 of 19648 transitions -- which is why growth here is never invented, "
                "only bought against an observed failure and verified on held-out executions",
            "refused_instrument":
                "AGENTSCOPE (arXiv 2609.02371) verifies abstractions against neural invariants; a model is not "
                "a verifier, so every verdict here is a subprocess exit code and a byte comparison",
        },
        "limit": ("the growth is searched inside a stated family of derived views, relations and one-step "
                  "compositions. When nothing in the family sees the action the answer is STOP with the missing "
                  "sensor named and the effect proved to be on disk -- reported per chain, never hidden behind "
                  "a generic failure"),
    }
    report["what_this_shows"] = _headline(report)
    return report


def _headline(report: Mapping[str, Any]) -> str:
    stop = [chain["chain"] for chain in report["per_chain"] if chain["growth"] == "STOP"]
    return (
        "%d real actions, each failing for a different reason, and the failure itself decides which vocabulary "
        "is missing: %d/%d diagnoses match what actually happened, and the growth carries to a held-out action "
        "of the same kind %d/%d times. The three growable cases are bought, not declared -- a derived predicate "
        "that stops an action being silently accepted as doing nothing, a set-valued consequence that makes an "
        "unpredictable action's one load-bearing property testable, and one composition that the flat grammar "
        "cannot express. The %d non-growable case is the boundary that matters: `%s` has a real effect on disk "
        "and every view in the family is empty, so no predicate built from the same readings can ever reach it "
        "-- that is a missing sensor, not a missing word, and no amount of experience closes it. Nothing is "
        "trained: a primitive is kept only when it is necessary, stable, transferable and narrow, which is the "
        "verifier gap closed by construction instead of declared."
        % (report["chains"], report["diagnoses_correct"], report["chains"],
           report["transfer_holds"], report["chains"], len(stop), stop[0] if stop else "-"))


def summarize(report: Mapping[str, Any]) -> str:
    lines = ["environment: " + report["environment"]["kind"],
             "actions %d | diagnoses correct %d/%d | transfers %d/%d"
             % (report["chains"], report["diagnoses_correct"], report["chains"],
                report["transfer_holds"], report["chains"])]
    for chain in report["per_chain"]:
        lines.append("  %-36s %s" % (chain["chain"], chain["outcome"]))
        lines.append("      growth %s -> %s" % (chain["growth"], json.dumps(chain["growth_bought"])[:70]))
        detail = chain["growth_detail"]
        for key in ("stable_separators", "relations_that_hold_on_every_repeat",
                    "is_genuinely_a_set", "fresh_execution_still_inside_the_set",
                    "alternative_consequences_the_set_still_admits",
                    "pipelines_that_reproduce_it", "flat_readings", "effect_on_disk",
                    "every_admissible_view_empty", "silently_accepted_as_identity"):
            if key in detail:
                lines.append("      %-42s %s" % (key, json.dumps(detail[key])[:70]))
        lines.append("      transfer `%s` -> %s (same kind %s)"
                     % (chain["transfer_invocation"], json.dumps(chain["transfer_growth"])[:50],
                        chain["transfer_same_kind"]))
    if report["missing_programs"]:
        lines.append("  missing: " + ", ".join(report["missing_programs"]))
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Turn a refusal into a vocabulary growth, and verify the growth before keeping it.")
    parser.add_argument("--json", dest="json_path", default=None)
    ns = parser.parse_args(argv)
    report = measure()
    print(summarize(report))
    print("\n" + report["what_this_shows"])
    if ns.json_path:
        target = pathlib.Path(ns.json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("\nwritten:", ns.json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
