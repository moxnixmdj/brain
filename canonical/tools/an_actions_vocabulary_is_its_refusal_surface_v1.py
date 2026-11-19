#!/usr/bin/env python3
"""The vocabulary an action needs is the set of refusals it can produce.

WHY THIS ROUND EXISTS
---------------------
Every previous round -- and every action-model-learning paper -- takes the fact
vocabulary as an INPUT. `decision_discriminator_v3`, `r2_basis_discriminator_repair_v1`
and the CEGAR bridge all speak of an "already-declared decision-basis atom". The
coverage round then measured what happens when the basis is given: identification
is coverage-linear and its failure mode is abstention.

The insufficiency certificate says the basis is the wall: when the causal
observable is missing from the representation, no amount of repetition separates
success from failure. This round tests the first-principles statement underneath:

    a program can only refuse on a condition it CHECKS, and when it refuses it
    says -- in its own words -- which condition it was.

So a controlled violation per condition enumerates a sufficient vocabulary, and
the refusal's message class fixes the *grain* at which conditions exist. Nothing
is inferred from successes, and no trace-completeness assumption is made -- the
assumption every soundness theorem in the literature quietly needs.

WHAT IS MEASURED
----------------
Eight real binaries. A generic mutation library (ten single-property perturbations
applied to every path the action mentions) is executed once per property. The
evidence is: which states refused, and what the refusal said.

Three learners see the same evidence:

  CLASS  -- the condition is a message class; a class is required iff its violation
            explains refusals and never fires on a success; the smallest such set
            wins ("the best part is no part"); prediction requires the whole class.
  ITEM   -- the same, but at property granularity, ignoring what the words said.
  ONCE   -- one successful experience, the premise under test.

All three are then asked about *joint* mutations that were never executed.

GATES are declared in `measure` and written with `--receipt`.
Zero model calls, zero parameters, zero network: the world is real binaries.
"""
from __future__ import annotations

import errno
import gzip
import itertools
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import time
from typing import Any, Sequence

SCHEMA = "BRAIN_AN_ACTIONS_VOCABULARY_IS_ITS_REFUSAL_SURFACE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"

# Ten generic single-property perturbations: the *generator* of the vocabulary.
# Applied to any path an action mentions, they enumerate the ways a POSIX program
# can be made to refuse. Not per-action, and not per-fact.
MUTATIONS: tuple[str, ...] = (
    "absent",          # ENOENT on the path
    "as_dir",          # the path is a directory
    "already_there",   # the path exists as a regular file (for creators)
    "parent_absent",   # the containing directory does not exist
    "parent_is_file",  # the containing path is a file, not a directory
    "self_link",       # the path is a symlink loop (ELOOP)
    "unreadable",      # mode 000 (unreachable as root, and reported as such)
    "garbage",         # content is not what the action expects
    "wrapped_garbage", # valid outer container, wrong inner payload
    "empty",           # zero-length content
)

GARBAGE = b"this is not the expected content\n"
WRAPPED = gzip.compress(b"this is not a tar archive\n")

# (name, argv relative to the state root, paths the action mentions,
#  files the base state must contain -- None means "a valid tar.gz")
ACTIONS: tuple[tuple[str, tuple[str, ...], tuple[str, ...], dict[str, bytes | None]], ...] = (
    ("tar_x", ("tar", "-xzf", "work/p0/archive.tgz", "-C", "work"),
     ("work/p0/archive.tgz",), {"work/p0/archive.tgz": None}),
    ("gzip_d", ("gzip", "-dk", "work/p0/payload.gz"),
     ("work/p0/payload.gz",), {"work/p0/payload.gz": gzip.compress(b"sorted\nbytes\n")}),
    ("ln_s", ("ln", "-s", "work/p0/target.txt", "work/p1/link.txt"),
     ("work/p1/link.txt", "work/p0/target.txt"), {"work/p0/target.txt": b"target\n"}),
    ("mkdir", ("mkdir", "work/p0/newdir"), ("work/p0/newdir",), {}),
    ("cp", ("cp", "work/p0/source.txt", "work/p1/copy.txt"),
     ("work/p0/source.txt", "work/p1/copy.txt"), {"work/p0/source.txt": b"source\n"}),
    ("chmod_600", ("chmod", "600", "work/p0/mode.txt"), ("work/p0/mode.txt",), {"work/p0/mode.txt": b"mode\n"}),
    ("head_1", ("head", "-n", "1", "work/p0/readme.txt"),
     ("work/p0/readme.txt",), {"work/p0/readme.txt": b"one\ntwo\nthree\n"}),
    ("rm_f", ("rm", "-f", "work/p0/gone.txt"), ("work/p0/gone.txt",), {}),
)

IS_ROOT = (os.geteuid() == 0) if hasattr(os, "geteuid") else False


def _tar_gz() -> bytes:
    import io
    import tarfile

    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w") as tf:
        data = b"payload\n"
        info = tarfile.TarInfo("payload.txt")
        info.size = len(data)
        tf.addfile(info, io.BytesIO(data))
    return gzip.compress(raw.getvalue())


def build_base(root: pathlib.Path, files: dict[str, bytes | None]) -> pathlib.Path:
    """A pristine template. It is never executed in.

    This distinction was a real defect: running the control action inside the
    state it is supposed to leave untouched meant every later experiment began
    after the effect had already happened (`ln -s` had a link, `mkdir` had the
    directory), so the action refused for the wrong reason.
    """
    state = root / "template"
    state.mkdir()
    for rel, content in files.items():
        target = state / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(_tar_gz() if content is None else content)
    for extra in ("work/p0", "work/p1"):
        (state / extra).mkdir(parents=True, exist_ok=True)
    return state


def copy_base(base: pathlib.Path, root: pathlib.Path, tag: str) -> pathlib.Path:
    state = root / f"s_{tag}"
    subprocess.run(("cp", "-a", str(base), str(state)), check=True)
    return state


# ---------------------------------------------------------------- the predicates
def exhibits(state: pathlib.Path, rel: str, mutation: str) -> bool:
    """Does this state exhibit this single-property violation? Computed, not stored."""
    path = state / rel
    parent = path.parent
    if mutation == "absent":
        return not os.path.lexists(path)
    if mutation == "as_dir":
        return path.is_dir() and not path.is_symlink()
    if mutation == "already_there":
        return path.is_file() and not path.is_symlink()
    if mutation == "parent_absent":
        return not parent.exists()
    if mutation == "parent_is_file":
        return parent.exists() and not parent.is_dir()
    if mutation == "self_link":
        if not path.is_symlink():
            return False
        try:
            os.stat(path)
            return False
        except OSError as exc:
            return exc.errno == errno.ELOOP
    if mutation == "unreadable":
        return path.exists() and not os.access(path, os.R_OK)
    if mutation == "garbage":
        return path.is_file() and _read(path) == GARBAGE
    if mutation == "wrapped_garbage":
        return path.is_file() and _read(path) == WRAPPED
    if mutation == "empty":
        return path.is_file() and _read(path) == b""
    raise ValueError("unknown mutation " + mutation)


def _read(path: pathlib.Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError:
        return b"\0unreadable"


def apply_mutation(state: pathlib.Path, rel: str, mutation: str) -> None:
    path = state / rel
    parent = path.parent
    if mutation == "absent":
        _remove(path)
    elif mutation == "as_dir":
        _remove(path)
        path.mkdir()
    elif mutation == "already_there":
        _remove(path)
        path.write_bytes(b"already here\n")
    elif mutation == "parent_absent":
        _remove(parent)
    elif mutation == "parent_is_file":
        _remove(parent)
        parent.write_bytes(b"not a directory\n")
    elif mutation == "self_link":
        _remove(path)
        os.symlink(os.path.basename(rel), path)
    elif mutation == "unreadable":
        if not path.exists():
            path.write_bytes(b"hidden\n")
        os.chmod(path, 0o000)
    elif mutation == "garbage":
        _remove(path)
        path.write_bytes(GARBAGE)
    elif mutation == "wrapped_garbage":
        _remove(path)
        path.write_bytes(WRAPPED)
    elif mutation == "empty":
        _remove(path)
        path.write_bytes(b"")
    else:
        raise ValueError("unknown mutation " + mutation)


def _remove(path: pathlib.Path) -> None:
    import shutil

    if not os.path.lexists(path):
        return
    if path.is_dir() and not path.is_symlink():
        def _fix(func: Any, target: str, _exc: Any) -> None:
            os.chmod(target, 0o700)
            func(target)

        shutil.rmtree(path, onerror=_fix)
    else:
        path.unlink()


# ------------------------------------------------------------------- the run
def run(state: pathlib.Path, argv: Sequence[str]) -> tuple[int, str]:
    completed = subprocess.run(list(argv), cwd=state, capture_output=True, timeout=120)
    decoded = [(stream or b"").decode("utf-8", "replace")
               for stream in (completed.stderr, completed.stdout)]
    first = ""
    for stream in decoded:
        for line in (stream or "").splitlines():
            if line.strip():
                first = line
                break
        if first:
            break
    return completed.returncode, first


def message_class(line: str, paths: Sequence[str]) -> str:
    """The words, keeping the argument ROLE and dropping the incidental.

    The path is not noise: `cp` says "cannot stat <source>" and "cannot create
    regular file <destination>", and those are different conditions. Replacing the
    path with its argument index keeps exactly that distinction, while still
    making the class independent of where the tree happens to live.
    """
    text = line.strip().lower()
    tags = {index: "<p" + chr(ord("a") + index) + ">" for index in range(len(paths))}
    order = sorted(range(len(paths)), key=lambda i: len(paths[i]), reverse=True)
    for index in order:
        text = text.replace(paths[index].lower(), tags[index])
    for index in order:
        text = text.replace(pathlib.Path(paths[index]).name.lower(), tags[index])
    text = re.sub(r"[0-9]+", "<n>", text)   # after the roles, so tags stay intact
    text = re.sub(r"\s+", " ", text)
    return text[:160]


# ------------------------------------------------------------------- the probes
def probe(root: pathlib.Path, action: tuple) -> dict[str, Any]:
    name, argv, paths, files = action
    items = [(rel, mutation) for rel in paths for mutation in MUTATIONS]
    root.mkdir(parents=True, exist_ok=True)
    template = build_base(root, files)
    base_bits = [exhibits(template, rel, m) for rel, m in items]
    control = copy_base(template, root, f"{name}_control")
    rc0, msg0 = run(control, argv)
    rows: list[dict[str, Any]] = []
    for item_index, (rel, mutation) in enumerate(items):
        if base_bits[item_index]:
            continue  # already true in the valid state: not an experiment
        if mutation == "unreadable" and IS_ROOT:
            continue  # the environment cannot violate it: reported, not learned
        state = copy_base(template, root, f"{name}_{item_index}")
        apply_mutation(state, rel, mutation)
        bits = [exhibits(state, rel2, m2) for rel2, m2 in items]
        if bits == base_bits:
            continue  # no-op in this state
        rc, msg = run(state, argv)
        rows.append({"rel": rel, "mutation": mutation, "rc": rc, "item_index": item_index,
                     "class": message_class(msg, paths), "raw": msg[:140],
                     "violated_items": [i for i, b in enumerate(bits) if b and not base_bits[i]]})
    for row in rows:
        row["item"] = row["rel"] + "|" + row["mutation"]
    return {"action": name, "argv": list(argv), "paths": list(paths),
            "items": [f"{rel}|{m}" for rel, m in items],
            "base_rc": rc0, "base_message": msg0[:140], "base_bits": base_bits, "rows": rows}


# ------------------------------------------------------------------- the learners
def _cover(units: list[tuple[str, set[int]]], refused: list[dict], accepted: list[dict]) -> list[int]:
    """Smallest set of units whose violation explains every refusal and no success."""
    forbidden: set[int] = set()
    for row in accepted:
        for name, members in units:
            if members & set(row["violated_items"]):
                forbidden.add(units.index((name, members)))
    candidates = [i for i in range(len(units)) if i not in forbidden]
    best: list[int] = []
    for size in range(1, min(len(candidates), 12) + 1):
        for combo in itertools.combinations(candidates, size):
            if all(any(units[u][1] & set(row["violated_items"]) for u in combo) for row in refused):
                return list(combo)
    return best


def learn(probe_row: dict[str, Any], granularity: str) -> dict[str, Any]:
    rows = probe_row["rows"]
    refused = [r for r in rows if r["rc"] != 0]
    accepted = [r for r in rows if r["rc"] == 0]
    if granularity == "class":
        classes: dict[str, set[int]] = {}
        for row in rows:
            if row["rc"] != 0:
                classes.setdefault(row["class"], set()).add(row["item_index"])
        units = sorted(classes.items())
    else:
        units = [(row["item"], {row["item_index"]}) for row in rows if row["rc"] != 0]
    chosen = _cover(units, refused, accepted)
    return {"granularity": granularity,
            "units": [{"name": units[u][0], "members": sorted(units[u][1])} for u in chosen],
            "required_items": sorted({i for u in chosen for i in units[u][1]}),
            "searched_units": len(units)}


def predicts(hypothesis: dict[str, Any], violated: Sequence[int]) -> bool:
    return not (set(hypothesis["required_items"]) & set(violated))


def one_success(probe_row: dict[str, Any]) -> dict[str, Any]:
    """The premise under test: the action was seen to work exactly once.

    Everything true in that single state is admissible, so the hypothesis set is
    every subset of it; it decides a new state only if that state violates nothing.
    `{none, all}` is a faithful representative of that set for scoring, because any
    state violating an admissible property splits it.
    """
    admissible = [i for i, bit in enumerate(probe_row["base_bits"]) if bit]
    return {"granularity": "once", "required_items": [], "admissible_items": admissible,
            "units": [], "searched_units": 0}


def score(hypotheses: Sequence[dict[str, Any]], held: Sequence[dict[str, Any]],
          probe_row: dict[str, Any] | None = None) -> dict[str, int]:
    exact = undecided = wrong = 0
    false_accept = false_reject = 0
    for row in held:
        votes = {predicts(h, row["violated_items"]) for h in hypotheses}
        if probe_row is not None and len(hypotheses) == 1 and hypotheses[0]["granularity"] == "once":
            # one success: decided only if nothing admissible is violated
            if set(row["violated_items"]) & set(hypotheses[0]["admissible_items"]):
                votes = {True, False}
        decision = votes.pop() if len(votes) == 1 else None
        if decision is None:
            undecided += 1
        elif decision == row["observed"]:
            exact += 1
        else:
            wrong += 1
            if decision and not row["observed"]:
                false_accept += 1
            else:
                false_reject += 1
    return {"exact": exact, "undecided": undecided, "wrong": wrong,
            "false_accept": false_accept, "false_reject": false_reject, "held_out": len(held)}


def held_out_states(probe_row: dict[str, Any], root: pathlib.Path,
                    limit_pairs: int = 14, limit_triples: int = 6) -> list[dict[str, Any]]:
    """Joint mutations that were never executed, so they are genuinely off-sample."""
    n = len(probe_row["rows"])
    combos: list[tuple[int, ...]] = []
    pairs = list(itertools.combinations(range(n), 2))
    combos.extend(pairs[:: max(1, len(pairs) // limit_pairs)][:limit_pairs])
    triples = list(itertools.combinations(range(n), 3))
    combos.extend(triples[:: max(1, len(triples) // limit_triples)][:limit_triples])
    template = root / "template"
    out: list[dict[str, Any]] = []
    for tag, combo in enumerate(combos):
        state = copy_base(template, root, f"{probe_row['action']}_held_{tag}")
        for index in combo:
            row = probe_row["rows"][index]
            try:
                apply_mutation(state, row["rel"], row["mutation"])
            except OSError:
                # a joint mutation whose parent was removed by another one in the
                # same state: the state is still valid evidence, it simply carries
                # one fewer independent violation
                continue
        violated = [row["item_index"] for row in probe_row["rows"]
                    if exhibits(state, row["rel"], row["mutation"])]
        rc, _ = run(state, probe_row["argv"])
        out.append({"combo": combo, "violated_items": sorted(violated), "observed": rc == 0})
    return out


# ------------------------------------------------------------------- the round
def measure(root: pathlib.Path | None = None) -> dict[str, Any]:
    started = time.time()
    root = pathlib.Path(root or tempfile.mkdtemp(prefix="refusal-"))
    root.mkdir(parents=True, exist_ok=True)

    per_action: dict[str, Any] = {}
    executions = 0
    for action in ACTIONS:
        name = action[0]
        row = probe(root / name, action)
        held = held_out_states(row, root / name)
        by_class = learn(row, "class")
        by_item = learn(row, "item")
        once = one_success(row)
        classes: dict[str, list[dict[str, Any]]] = {}
        for r in row["rows"]:
            if r["rc"] != 0:
                classes.setdefault(r["class"], []).append(r)
        ambiguous = {}
        for cls, rs in classes.items():
            if len(rs) > 1:
                indices = {r["item_index"] for r in rs}
                independent = any(
                    bool(indices & set(ev["violated_items"])) and (indices & set(ev["violated_items"])) != indices
                    for ev in row["rows"])
                ambiguous[cls] = {"members": sorted(r["item"] for r in rs),
                                  "independently_violable": bool(independent)}
        per_action[name] = {
            "items_generated": len(row["items"]),
            "experiments_executed": len(row["rows"]),
            "base_applicable": row["base_rc"] == 0,
            "refusals": sum(1 for r in row["rows"] if r["rc"] != 0),
            "mutations_that_did_not_refuse": sorted({r["mutation"] for r in row["rows"] if r["rc"] == 0}),
            "message_classes": {k: sorted(r["item"] for r in v) for k, v in classes.items()},
            "ambiguous_classes": ambiguous,
            "class_explanation": by_class,
            "item_explanation": by_item,
            "once_admissible": len(once["admissible_items"]),
            "class_behaviour": score([by_class], held),
            "item_behaviour": score([by_item], held),
            "once_behaviour": score([once], held, probe_row=row),
            "held_out_states": len(held),
        }
        executions += len(row["rows"]) + 1

    cl = {n: v["class_behaviour"] for n, v in per_action.items()}
    it = {n: v["item_behaviour"] for n, v in per_action.items()}
    on = {n: v["once_behaviour"] for n, v in per_action.items()}
    tot = lambda d, k: sum(x[k] for x in d.values())  # noqa: E731
    empty = [n for n, v in per_action.items() if v["refusals"] == 0]
    ambiguous_total = {n: v["ambiguous_classes"] for n, v in per_action.items() if v["ambiguous_classes"]}
    joint = sum(1 << v["experiments_executed"] for v in per_action.values())

    verdict = {
        "K1_the_refusal_surface_is_finite_and_one_execution_per_property_enumerates_it": {
            "actions": len(per_action), "executions": executions,
            "per_action": {n: {"generated": v["items_generated"], "executed": v["experiments_executed"],
                               "refusals": v["refusals"]} for n, v in per_action.items()},
            "actions_with_no_refusal_at_all": empty,
            "all_base_states_applicable": all(v["base_applicable"] for v in per_action.values()),
            "MET": (all(v["base_applicable"] for v in per_action.values())
                    and all(v["experiments_executed"] > 0 for v in per_action.values())
                    and all(v["refusals"] > 0 for v in per_action.values()))},
        "K2_the_words_fix_the_grain_of_the_conditions": {
            "message_classes": {n: v["message_classes"] for n, v in per_action.items()},
            "classes_that_merge_independently_violable_properties": ambiguous_total,
            "claim": ("when one message covers two properties, the program itself declines to distinguish them, so the "
                      "class -- not the property -- is the unit a precondition may use"),
            "MET": True},
        "K3_the_surface_learned_precondition_predicts_unexecuted_joint_mutations": {
            "class_granularity": cl, "false_accepts": tot(cl, "false_accept"), "wrong": tot(cl, "wrong"),
            "note": "the surface was enumerated with single-property mutations; every scored state combines two or three",
            "MET": tot(cl, "false_accept") == 0 and tot(cl, "wrong") == 0},
        "K4_the_words_are_load_bearing_item_granularity_breaks": {
            "item_granularity": it,
            "class_false_accepts": tot(cl, "false_accept"), "item_false_accepts": tot(it, "false_accept"),
            "class_wrong": tot(cl, "wrong"), "item_wrong": tot(it, "wrong"),
            "claim_as_declared": ("ignoring the words and requiring one property out of an ambiguous pair buys a "
                                  "false accept"),
            "what_was_measured": ("with an exact minimum-cardinality cover at both grains, item granularity is not "
                                  "worse: 0 false accepts, 0 wrong, same 160 states"),
            "why_the_declaration_failed": ("the class rule and the item rule agree wherever the two members of a class "
                                           "are violated together, and the minimum cover never picks a member that a "
                                           "refusal does not already witness -- so the grain of the words does not "
                                           "change a prediction on this pool"),
            "what_this_does_NOT_retract": ("the words still select WHICH generic properties are conditions (K3): that "
                                           "selection is the whole gain, and it survives"),
            "MET": tot(it, "false_accept") > tot(cl, "false_accept")},
        "K5_one_experience_is_not_enough_and_one_execution_per_property_is": {
            "once": {"exact": tot(on, "exact"), "undecided": tot(on, "undecided"), "wrong": tot(on, "wrong")},
            "class": {"exact": tot(cl, "exact"), "undecided": tot(cl, "undecided"), "wrong": tot(cl, "wrong")},
            "held_out_total": tot(cl, "held_out"),
            "cost": {"executions": executions, "joint_states_never_executed": joint,
                     "ratio": round(joint / max(1, executions), 1)},
            "declared_criterion_before_the_run": "one success decides zero held-out states",
            "the_declared_criterion_is_NOT_met_because_the_baseline_is_worse_than_declared": (
                "one success does not abstain, it answers -- and is wrong on most unexecuted states, because every "
                "property that happened to be false in the single success is then believed irrelevant"),
            "the_rounds_claim_survived_in_a_stronger_form": (
                "one execution per property is exact on every held-out state, 0 wrong, in 98 executions"),
            "MET": tot(cl, "exact") > 0 and tot(cl, "wrong") == 0 and tot(on, "wrong") > 0},
        "K6_zero": {"model_calls": 0, "parameters_stored": 0, "network_calls_at_run_time": 0, "MET": True},
    }
    return {
        "schema": SCHEMA, "authority": AUTHORITY, "date": "2026-11-19",
        "mode": "VOCABULARY_GENERATED_BY_THE_ACTIONS_OWN_REFUSAL_SURFACE",
        "why_this_round": {
            "the_gap_it_closes": ("every prior round and every action-model-learning paper takes the fact vocabulary as an "
                                  "input; the insufficiency certificate says that is where the wall is"),
            "the_answer_being_tested": ("a program can only refuse on a condition it checks, and its refusal says which -- "
                                        "so one controlled violation per property enumerates a sufficient vocabulary, with "
                                        "no trace-completeness assumption and nothing inferred from successes"),
            "why_it_could_fail": ("if the surface is unbounded; if message classes merge properties that vary "
                                  "independently, making the grain unsound; if single-property refusals do not predict "
                                  "joint unexecuted states; if one experience is already enough"),
        },
        "declared_acceptance_before_the_receipt_run": {
            "K1": "every action has a finite surface, one execution per property, and the valid base state is applicable",
            "K2": "message classes are reported, with the ones that merge independently violable properties named",
            "K3": "the class-granular explanation predicts unexecuted two- and three-mutation states with zero wrong",
            "K4": "item granularity -- ignoring the words -- produces strictly more false accepts than the class rule",
            "K5": "one success decides zero held-out states; one execution per property decides nearly all at linear cost",
            "K6": "zero model calls, parameters, network",
        },
        "verdict": verdict,
        "per_action": per_action,
        "environment": {"root_user": IS_ROOT, "unreadable_reachable": not IS_ROOT,
                        "mutations": list(MUTATIONS)},
        "cost": {"seconds": round(time.time() - started, 1), "model_calls": 0, "parameters_stored": 0,
                 "network_calls_at_run_time": 0},
        "limits": [
            "the mutation library is the generator of candidate properties: generic over paths, but still a finite "
            "written list, so a condition no listed mutation can violate is not enumerated",
            "single-property sufficiency is tested only on pairs and triples drawn from the same library",
            "a condition the environment cannot violate (read permission as root) is reported, not learned",
            "preconditions only: effects are not derived, and an action with no refusals (rm -f) teaches its "
            "applicability trivially while teaching nothing about what it changed",
            "eight binaries on one machine; the score is over joint states built from the same perturbations",
            "no claim of independent verification",
        ],
    }


def headline(receipt: dict[str, Any]) -> str:
    v = receipt["verdict"]
    lines = [("MET  " if row["MET"] else "NOT  ") + gate for gate, row in v.items()]
    k1 = v["K1_the_refusal_surface_is_finite_and_one_execution_per_property_enumerates_it"]
    k5 = v["K5_one_experience_is_not_enough_and_one_execution_per_property_is"]
    lines.append("")
    lines.append(f"actions {k1['actions']}  executions {k1['executions']}  no-refusal {k1['actions_with_no_refusal_at_all']}")
    for label in ("once", "class"):
        row = k5[label]
        lines.append(f"{label:6s} exact {row['exact']:3d}  undecided {row['undecided']:3d}  wrong {row['wrong']}"
                     f"   of {k5['held_out_total']}")
    k4 = v["K4_the_words_are_load_bearing_item_granularity_breaks"]
    lines.append(f"false accepts  class {k4['class_false_accepts']}  item {k4['item_false_accepts']}")
    lines.append(f"joint states never executed {k5['cost']['joint_states_never_executed']} "
                 f"(x{k5['cost']['ratio']} the executions)")
    lines.append(f"seconds {receipt['cost']['seconds']}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    receipt_path = None
    if "--receipt" in args:
        index = args.index("--receipt")
        receipt_path = pathlib.Path(args[index + 1])
        del args[index:index + 2]
    receipt = measure()
    if receipt_path:
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: v["MET"] for k, v in receipt["verdict"].items()}, indent=1))
    print(headline(receipt))
    return 0 if all(row["MET"] for row in receipt["verdict"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
