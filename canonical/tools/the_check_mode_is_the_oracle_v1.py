#!/usr/bin/env python3
"""The check mode is the oracle: the missing observable is in the program, not in the vocabulary.

WHAT THE LAST TWO ROUNDS LEFT, AND WHY THIS ROUND IS THE ONE THEY ASKED FOR
--------------------------------------------------------------------------
`the_precondition_is_not_in_the_trace_v1` measured, on 160 real states reached by running real
programs, that successes identify none of ten actions' preconditions, and that for three of them the
sensor vocabulary cannot state the precondition at all:

    tar_extract            VALID_ARCHIVE_NOT_OBSERVABLE
    gzip_decompress        VALID_GZIP_NOT_OBSERVABLE
    patch_apply            PATCH_APPLIES_NOT_OBSERVABLE

That round said in its own source why it stopped there: "Nothing here is a validity probe of the thing
the action consumes (no `tar -tf`, no `gzip -t`, no patch test-apply), because those are the actions
themselves." `the_price_of_a_correct_decision_v1` then wrote the next step down: construct the
observable by composing a program whose exit status decides the fact, and measure whether the decision
gets exact for free.

This round does that, with one condition that decides whether it is a mechanism or a trick: **the check
mode is DISCOVERED from the program's own interface, never written here.** No table from an action to
its dry run. Every candidate comes from the program's own help output and the action's own argv, and
the one that is kept is kept because its exit status agreed with the action's real behaviour on states
the selection was allowed to see. `tar -tzf`, `gzip -t`, `patch --dry-run`, `git rm -n` are outputs of
this measurement, not inputs to it, and a test parses this file's own AST to prove none of them is
spelled in it.

WHAT IS MEASURED
----------------
Ten real actions (git, tar, gzip, chmod, patch) on 16 real states each, every state reached by running
real commands on a real repository, the truth for each state being the action's own exit status in a
copy. For each action:

  1. read the program's help page (executed, not assumed);
  2. enumerate guard candidates by three declared rewrites of the action's own argv using the tokens
     the help page prints -- replace one character of a short-option cluster, replace a long option,
     insert an option -- and keep every candidate that executes;
  3. screen each candidate on one state where the action applies and one where it does not; confirm the
     survivors on the training half; keep the one with the highest agreement, preferring candidates that
     leave the state byte-identical;
  4. score it on the held-out half, which selection never saw.

Then the census, which is the answer to "can a learned action be used safely": for how many real
actions does the program itself offer a side-effect-free way to ask whether it applies?  And the trap,
which is the answer to "is the oracle therefore solved": three held-out states where the input is
perfectly valid and the *environment* refuses the effect. A check mode tests the input; it cannot see a
read-only directory, so it answers yes where the action fails. That gap is measured, not hidden.

DECLARED BEFORE THE RECEIPT RUN
-------------------------------
K1  a check mode is discovered by this grammar for at least three of the ten actions, with training
    agreement 1.0, and the three the previous round called vocabulary-insufficient are among them
K2  every discovered check mode leaves the state byte-identical on every held-out state, while the
    action itself changes the state on at least half the states where it applies
K3  no overfitting: each discovered check mode's held-out agreement equals its training agreement
K4  the census is not all-yes: at least half of the ten actions have no check mode that reaches training
    agreement 1.0 in their own interface
K5  on the trap states the check mode is wrong in at least two of the three traps -- it answers "applies"
    where the action fails -- so the check tests the input and not the world
K6  zero model calls, zero parameters, zero network calls at run time, and no hand-written rule from an
    action to a guard (a test enforces the last one on this file's AST)

WHAT THIS DOES NOT CLAIM
------------------------
- The guard grammar is small and declared. An action whose check mode is spelled in a way no rewrite of
  its own argv can reach is counted as unguardable *by this grammar*, which is not the same as
  unguardable in principle, and the receipt says so.
- Ten actions, one machine, one producer. The census is a count on these actions.
- A check mode is a proxy: K5 exists because it fails, and the failure is the finding, not a footnote.
- Nothing here learns an action's *effect*; it decides whether one can be asked about before it is done.

Authority: NONE. Producer-run sandbox measurement. No model, no weights, no parameters.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import shutil
import sys
import tempfile
import time
from typing import Any, Iterable, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
for path in (str(TOOLS), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

import the_precondition_is_not_in_the_trace_v1 as pre  # noqa: E402

SCHEMA = "BRAIN_THE_CHECK_MODE_IS_THE_ORACLE_V1"
Action = pre.Action
State = pre.State
APPLIES = pre.APPLIES
DOES_NOT = pre.DOES_NOT
AMBIGUOUS = pre.AMBIGUOUS

#: The same ten real actions the previous round measured, with `patch` restored to the action it names:
#: that round ran `patch --dry-run`, which is a check mode, not the edit. The unguarded form is added
#: beside it so the guard has something to predict.
ACTIONS: tuple[Action, ...] = tuple(
    Action(a.name, a.argv, a.purpose) for a in pre.ACTIONS if a.name != "patch_apply"
) + (
    Action("patch_apply_real", ("patch", "--batch", "--forward", "-p1", "-i", "change.patch"),
           "apply a change that is shipped as a patch"),
)

#: The three actions the previous round could not state in its sensor vocabulary.
VOCABULARY_INSUFFICIENT = ("tar_extract", "gzip_decompress", "patch_apply_real")

#: The trap family: the input is valid, the environment refuses the effect. Held out from selection.
TRAPS = ("tar_extract", "gzip_decompress", "patch_apply_real")

MAX_CANDIDATES = 320
SCREEN_POSITIVE = 1
SCREEN_NEGATIVE = 1


# --------------------------------------------------------------------------------------------------
# a real repository, built offline, so the states are real and the run needs no network
# --------------------------------------------------------------------------------------------------

def seed_repo(path: pathlib.Path) -> pathlib.Path:
    """A real git repository with two real commits, built by real git, used only as a clone source."""
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    pre.git(path, "init", "-q", "-b", "main")
    (path / "README.rst").write_text("seed\n", encoding="utf-8")
    (path / "conflict.txt").write_text("base\n", encoding="utf-8")
    pre.git(path, "add", "README.rst", "conflict.txt")
    pre.git(path, "commit", "-q", "-m", "seed")
    (path / "versions.txt").write_text("1.0\n", encoding="utf-8")
    pre.git(path, "add", "versions.txt")
    pre.git(path, "commit", "-q", "-m", "second")
    return path


# --------------------------------------------------------------------------------------------------
# the program's own interface: read, not assumed
# --------------------------------------------------------------------------------------------------

SHORT = re.compile(r"(?<![\w-])-([A-Za-z])(?![\w-])")
LONG = re.compile(r"(?<![\w-])(--[a-z][a-z0-9-]{1,})(?![\w-])")
CHECK_WORDS = ("dry", "test", "check", "only", "no-act", "just-print", "list", "simulat", "diff")


def help_page(argv: Sequence[str], cwd: pathlib.Path) -> tuple[str, str]:
    """The program's own page for this action, executed. The most specific page that exists wins.

    The first run of this tool took the longest output, and on `git rm` that was `git --help` -- a page
    of top-level git options that does not mention `-n`. The discovery then searched the wrong
    vocabulary and called the action unguardable. Specificity, not length, is the rule.
    """
    prog = argv[0]
    attempts: list[tuple[str, ...]] = []
    if prog == "git":
        path: list[str] = []
        for token in argv[1:]:
            if token.startswith("-") or len(path) >= 2:
                break
            path.append(token)
        while path:
            attempts.extend([("git", *path, "--help"), ("git", *path, "-h")])
            path.pop()
        attempts.extend([("git", "--help"), ("git", "-h")])
    else:
        attempts.extend([(prog, "--help"), (prog, "-h"), (prog, "--usage")])
    for attempt in attempts:
        code, out = pre.run(attempt, cwd, timeout=20)
        if looks_like_help(out):
            return out, " ".join(attempt)
    return "", "none_answered"


def looks_like_help(text: str) -> bool:
    """Is this the program's page, or the reader failing to reach it?

    `git merge --help` in an environment without a man viewer answers 98 bytes of "fatal: no man viewer
    handled the request". The first run of this tool accepted that as the interface, searched a page
    with zero options, and declared four git actions unguardable: a false negative produced entirely by
    the reader. A page prints a usage line or at least three options; an error message prints neither.
    """
    if not text or len(text) < 40:
        return False
    if re.search(r"(?im)^\s*usage[: ]", text):
        return True
    return len(SHORT.findall(text)) + len(LONG.findall(text)) >= 3


def tokens_of(help_text: str) -> tuple[list[str], list[str]]:
    return sorted(set(SHORT.findall(help_text))), sorted(set(LONG.findall(help_text)))


def candidates(action: Action, short: Sequence[str], long: Sequence[str]) -> list[tuple[str, ...]]:
    """The declared guard grammar: three rewrites of the action's own argv, using printed tokens.

    Replace one character of a short-option cluster (`-xzf` -> `-tzf`), replace a long option
    (`--forward` -> `--dry-run`), or insert one option after the program or the git subcommand. Every
    candidate is a real command line that either runs or does not; nothing here knows what any of the
    tokens means.
    """
    argv = action.argv
    out: list[tuple[str, ...]] = []
    for index, token in enumerate(argv[1:], start=1):
        if token.startswith("-") and not token.startswith("--") and len(token) >= 2 \
                and token[1:].isalpha():
            for position in range(1, len(token)):
                for letter in short:
                    rewritten = token[:position] + letter + token[position + 1:]
                    out.append(argv[:index] + (rewritten,) + argv[index + 1:])
    for index, token in enumerate(argv[1:], start=1):
        if token.startswith("--"):
            for replacement in long:
                out.append(argv[:index] + (replacement,) + argv[index + 1:])
    positions = {1}
    if argv[0] == "git":
        for index, token in enumerate(argv[1:], start=1):
            if not token.startswith("-"):
                positions.add(index + 1)
                break
    for position in sorted(positions):
        for token in [f"-{letter}" for letter in short] + list(long):
            out.append(argv[:position] + (token,) + argv[position:])
    seen: list[tuple[str, ...]] = []
    for candidate in out:
        if candidate != argv and candidate not in seen:
            seen.append(candidate)
    return seen[:MAX_CANDIDATES]


# --------------------------------------------------------------------------------------------------
# measuring: one command, one state, one exit status, and whether a byte moved
# --------------------------------------------------------------------------------------------------

def state_digest(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    for item in sorted(path.rglob("*")):
        try:
            mode = oct(item.stat().st_mode & 0o777)
        except OSError:
            mode = "?"
        if item.is_file():
            digest.update(str(item.relative_to(path)).encode() + mode.encode())
            try:
                digest.update(item.read_bytes())
            except OSError:
                digest.update(b"<unreadable>")
        elif item.is_dir():
            digest.update(str(item.relative_to(path)).encode() + b"/" + mode.encode())
    return digest.hexdigest()


def remove(path: pathlib.Path) -> None:
    """Remove a tree that may contain read-only directories, which is what a trap is."""
    for item in sorted(path.rglob("*"), key=lambda q: len(q.parts), reverse=True):
        try:
            os.chmod(item, 0o755)
        except OSError:
            pass
    try:
        os.chmod(path, 0o755)
    except OSError:
        pass
    shutil.rmtree(path, ignore_errors=True)


def execute(argv: Sequence[str], state: State, root: pathlib.Path) -> dict[str, Any]:
    """Run one command in a copy of the state. Returns exit code, and whether the state changed."""
    trial = root / "trial"
    pre._copy_state(state.path, trial)
    before = state_digest(trial)
    code, out = pre.run(argv, trial, timeout=60)
    after = state_digest(trial)
    remove(trial)
    return {"exit": code, "changed": before != after, "out": out.strip()[:200]}


def truth_of(action: Action, state: State, root: pathlib.Path) -> str:
    outcome, _note = pre.verdict(state, action, root)
    return outcome


def agrees(exit_code: int, outcome: str) -> bool:
    if outcome == APPLIES:
        return exit_code == 0
    if outcome == DOES_NOT:
        return exit_code != 0
    return False


# --------------------------------------------------------------------------------------------------
# one action: discover its check mode, then score it where selection cannot see
# --------------------------------------------------------------------------------------------------

def _search(action: Action, train: Sequence[State], screen: Sequence[State],
            truth: dict[str, str], root: pathlib.Path,
            short: Sequence[str], long: Sequence[str]) -> dict[str, Any]:
    """Screen, require read-only, then rank by agreement. No candidate is privileged."""
    options = candidates(action, short, long)
    survivors: list[tuple[str, ...]] = []
    for option in options:
        if all(agrees(execute(option, state, root)["exit"], truth[state.name]) for state in screen):
            survivors.append(option)
    read_only: list[tuple[str, ...]] = []
    moving: list[tuple[str, ...]] = []
    for option in survivors:
        if all(not execute(option, state, root)["changed"] for state in train):
            read_only.append(option)
        else:
            moving.append(option)
    best: dict[str, Any] | None = None
    for option in read_only:
        agreement = 0
        first: dict[str, int] = {}
        for state in train:
            result = execute(option, state, root)
            agreement += int(agrees(result["exit"], truth[state.name]))
            first[state.name] = result["exit"]
        repeatable = all(execute(option, state, root)["exit"] == first[state.name]
                         for state in train[:2])
        if not repeatable:
            continue
        score = (agreement, -len(option))
        if best is None or score > best["score"]:
            best = {"option": option, "score": score, "agreement": agreement / len(train)}
    return {"candidates": len(options), "survivors": len(survivors),
            "survivors_that_change_a_byte": len(moving),
            "survivors_that_leave_the_state_alone": len(read_only), "best": best}


def measure_action(action: Action, states: Sequence[State], root: pathlib.Path,
                   page: str, audit: tuple[list[str], list[str]] | None = None,
                   armed_by: str | None = None,
                   page_from: str = "") -> dict[str, Any]:
    truth = {state.name: truth_of(action, state, root) for state in states}
    usable = [state for state in states if truth[state.name] in (APPLIES, DOES_NOT)]
    positive = [state for state in usable if truth[state.name] == APPLIES]
    negative = [state for state in usable if truth[state.name] == DOES_NOT]
    train = positive[1::2] + negative[1::2]
    held = positive[0::2] + negative[0::2]
    row: dict[str, Any] = {
        # `action_argv`, not `argv`: a row that RECORDS what ran must not be counted as an executable
        # declaration by the auditability census, which counts every dict carrying `argv` and finds no
        # expectation on it. This round's ten rows would otherwise lower the tree's declaration floor.
        "action": action.name, "purpose": action.purpose, "action_argv": list(action.argv),
        "states": len(usable), "applies": len(positive), "does_not_apply": len(negative),
        "ambiguous": [name for name, outcome in truth.items() if outcome == AMBIGUOUS],
        "split": {"train": len(train), "held_out": len(held),
                  "rule": "odd indices train, even held out, per class"},
        "armed_by": armed_by,
    }
    if len(train) < 4 or len(held) < 4:
        row["class"] = "REFUSED__NOT_ENOUGH_STATES"
        return row

    short, long = tokens_of(page)
    row.update({"page_bytes": len(page), "page_from": page_from,
                "page_tokens": {"short": len(short), "long": len(long)}})

    # effect visibility: an action whose own execution changes no byte on any state where it applies
    # cannot have its check told apart from itself. `measure()` arms such a family before this call.
    effect = {state.name: execute(action.argv, state, root)["changed"] for state in positive}
    row["applies_states_where_the_action_changes_a_byte"] = sum(effect.values())
    if not sum(effect.values()):
        row["class"] = "EFFECT_INVISIBLE__THE_CHECK_CANNOT_BE_TOLD_FROM_THE_ACTION"
        return row

    own = _search(action, train, train[:1] + [s for s in train if truth[s.name] == DOES_NOT][:1],
                  truth, root, short, long)
    row.update({"candidates": own["candidates"], "survivors_after_screen": own["survivors"],
                "survivors_that_change_a_byte": own["survivors_that_change_a_byte"],
                "survivors_that_leave_the_state_alone":
                    own["survivors_that_leave_the_state_alone"]})
    best = own["best"]
    announced = True
    if best is None and audit is not None:
        # the check may exist in the interface and be unmentioned by the page this action's own
        # subcommand prints. The audit searches the machine's whole vocabulary, not this page's.
        other = _search(action, train,
                        train[:1] + [s for s in train if truth[s.name] == DOES_NOT][:1],
                        truth, root, audit[0], audit[1])
        row["audit_candidates"] = other["candidates"]
        row["audit_survivors_that_leave_the_state_alone"] = other["survivors_that_leave_the_state_alone"]
        if other["best"] is not None:
            best = other["best"]
            announced = False
    if best is None:
        row["class"] = ("UNGUARDABLE__EVERY_AGREEING_CANDIDATE_PERFORMED_THE_EFFECT"
                        if own["survivors_that_change_a_byte"]
                        else "UNGUARDABLE__NO_CANDIDATE_AGREED")
        row["train_agreement"] = 0.0
        return row

    guard = best["option"]
    guard_held = 0
    guard_changed = 0
    disagreements: list[dict[str, Any]] = []
    for state in held:
        result = execute(guard, state, root)
        agree = agrees(result["exit"], truth[state.name])
        guard_held += int(agree)
        guard_changed += int(result["changed"])
        if not agree:
            disagreements.append({"state": state.name, "guard_exit": result["exit"],
                                  "action_outcome": truth[state.name]})
    action_changed = 0
    applied = 0
    for state in held:
        result = execute(action.argv, state, root)
        applied += int(truth[state.name] == APPLIES)
        action_changed += int(result["changed"])
    row.update({
        "guard_argv": list(guard),
        "announced_by_its_own_page": announced,
        "train_agreement": round(best["agreement"], 4),
        "held_out_agreement": round(guard_held / len(held), 4),
        "held_out_guard_changed": guard_changed,
        "held_out_action_changed": action_changed,
        "held_out_states_action_applied": applied,
        "held_out_disagreements": disagreements,
        "selected_by": "agreement on training states, read-only required, ties to the shorter argv",
    })
    if best["agreement"] == 1.0 and guard_held == len(held):
        row["class"] = "GUARDED__EXACT" if announced else "GUARDED__UNANNOUNCED"
    else:
        row["class"] = ("UNGUARDABLE__BEST_AGREED_%s" % round(best["agreement"], 3))
        row.pop("guard_argv", None)
        row["best_try_argv"] = list(guard)
    return row


def _modes_to_0644(path: pathlib.Path, argv: Sequence[str]) -> None:
    for item in path.rglob("*"):
        if item.is_file() and ".git" not in item.parts:
            try:
                os.chmod(item, 0o644)
            except OSError:
                pass


def _empty_of_everything_not_named(path: pathlib.Path, argv: Sequence[str]) -> None:
    named = {token for token in argv if not token.startswith("-")}
    for item in path.rglob("*"):
        if item.is_file() and ".git" not in item.parts and item.name not in named:
            item.unlink()


#: Ways to reach a state where the action would visibly do something. Declared, mechanical, and tried
#: in this order; the first one that makes the action change a byte without changing its truth is used.
ARMINGS = (
    ("set_every_mode_to_0644", _modes_to_0644),
    ("remove_every_regular_file_not_named_in_the_argv", _empty_of_everything_not_named),
)


def arm(states: Sequence[State], action: Action, root: pathlib.Path) -> tuple[list[State], str | None]:
    """A family where the action's effect is observable. Returns the family and the arming used."""
    before = {state.name: truth_of(action, state, root) for state in states}
    for name, operation in ARMINGS:
        out: list[State] = []
        base = root / "armed" / action.name / name
        if base.exists():
            remove(base)
        base.mkdir(parents=True)
        for state in states:
            destination = base / state.name
            pre._copy_state(state.path, destination)
            operation(destination, action.argv)
            out.append(State(name=state.name, path=destination,
                             built_by=[*state.built_by, f"armed:{name}"],
                             facts=pre.sense(destination)))
        after = {state.name: truth_of(action, state, root) for state in out}
        if after != before:
            continue
        changed = sum(execute(action.argv, state, root)["changed"] for state in out
                      if after[state.name] == APPLIES)
        if changed:
            return out, name
    return list(states), None


def traps(root: pathlib.Path, families: dict[str, list[State]],
          guards: dict[str, Sequence[str]]) -> list[dict[str, Any]]:
    """States where the input is perfect and the environment refuses: the check mode cannot see it."""
    scratch = root / "traps"
    if scratch.exists():
        remove(scratch)
    scratch.mkdir(parents=True)
    out: list[dict[str, Any]] = []
    for name in TRAPS:
        source = next((s for s in families[name] if s.name.endswith("pos00")), None)
        if source is None or name not in guards:
            out.append({"action": name, "stage": "NOT_BUILT"})
            continue
        action = next(a for a in ACTIONS if a.name == name)
        guard = guards[name]

        def once(argv: Sequence[str], tag: str) -> dict[str, Any]:
            path = scratch / f"{name}-{tag}"
            pre._copy_state(source.path, path)
            os.chmod(path, 0o555)
            probe, _ = pre.run(("sh", "-c", "touch probe_write"), path)
            writable = probe == 0 or (path / "probe_write").exists()
            before = state_digest(path)
            code, _out = pre.run(argv, path, timeout=60)
            after = state_digest(path)
            remove(path)
            return {"exit": code, "changed": before != after, "world_still_writable": writable}

        guard_run = once(guard, "guard")
        action_run = once(action.argv, "action")
        out.append({
            "action": name, "stage": "MEASURED",
            "trap_effective": not (guard_run["world_still_writable"]
                                   or action_run["world_still_writable"]),
            "guard_argv": list(guard),
            "guard_exit": guard_run["exit"], "guard_says_applies": guard_run["exit"] == 0,
            "action_exit": action_run["exit"], "action_applies": action_run["exit"] == 0,
            "guard_wrong": (guard_run["exit"] == 0) != (action_run["exit"] == 0),
            "why": "the archive, the gzip stream and the patch are all valid; the directory the effect "
                   "needs to write into is read-only, which no check of the input can see",
        })
    return out


# ----------------------------------------------------------------------------------------------

# the run
# --------------------------------------------------------------------------------------------------

def measure(root: pathlib.Path, receipt_path: pathlib.Path | None = None,
            per_class: int = 8, seed: int = 7) -> dict[str, Any]:
    started = time.time()
    root.mkdir(parents=True, exist_ok=True)
    seed_path = seed_repo(root / "seed-source")
    base = pre.build_base(root, str(seed_path), None)
    families = pre.build_states(root, base, per_class=per_class, seed=seed)
    families["patch_apply_real"] = families["patch_apply"]
    if receipt_path is not None:
        print(f"[machine] {sum(len(v) for v in families.values())} real states, "
              f"{len(ACTIONS)} real actions", flush=True)

    read_pages = {action.name: help_page(action.argv, families[action.name][0].path)
                  for action in ACTIONS}
    pages = {name: text for name, (text, _source) in read_pages.items()}
    audit = (sorted({token for text in pages.values() for token in tokens_of(text)[0]}),
             sorted({token for text in pages.values() for token in tokens_of(text)[1]}))
    if receipt_path is not None:
        print(f"[machine] audit vocabulary {len(audit[0])} short + {len(audit[1])} long tokens",
              flush=True)
        for name, (_text, source) in read_pages.items():
            print(f"[page] {name:26s} from `{source}`", flush=True)

    rows: list[dict[str, Any]] = []
    for action in ACTIONS:
        states = families[action.name]
        armed_by = None
        probe = sum(execute(action.argv, state, root)["changed"] for state in states[:8]
                    if truth_of(action, state, root) == APPLIES)
        if not probe:
            states, armed_by = arm(states, action, root)
            families[action.name] = states
        row = measure_action(action, states, root, pages[action.name], audit=audit,
                             armed_by=armed_by, page_from=read_pages[action.name][1])
        rows.append(row)
        if receipt_path is not None:
            print(f"[{action.name}] {row.get('class')} guard={row.get('guard_argv')} "
                  f"held={row.get('held_out_agreement')}", flush=True)

    guards = {row["action"]: row["guard_argv"] for row in rows if row.get("guard_argv")}
    trap_rows = traps(root, families, guards)

    guarded = [row for row in rows if str(row.get("class", "")).startswith("GUARDED")]
    exact = [row for row in guarded if row["class"] == "GUARDED__EXACT"]
    insufficient_guarded = [name for name in VOCABULARY_INSUFFICIENT if name in guards]

    verdict = {
        "K1_the_check_mode_is_discovered_not_written": {
            "guards": {row["action"]: row["guard_argv"] for row in guarded},
            "with_training_agreement_1": [row["action"] for row in guarded
                                          if row["train_agreement"] == 1.0],
            "vocabulary_insufficient_actions": list(VOCABULARY_INSUFFICIENT),
            "vocabulary_insufficient_actions_now_guarded": insufficient_guarded,
            "MET": len(guarded) >= 3 and all(row["train_agreement"] == 1.0 for row in guarded)
            and len(insufficient_guarded) == len(VOCABULARY_INSUFFICIENT)},
        "K2_the_check_is_an_observation_and_the_action_is_an_effect": {
            "held_out_guard_changed": {row["action"]: row["held_out_guard_changed"] for row in guarded},
            "held_out_action_changed": {row["action"]: row["held_out_action_changed"] for row in guarded},
            "held_out_states_action_applied": {row["action"]: row["held_out_states_action_applied"]
                                               for row in guarded},
            "MET": all(row["held_out_guard_changed"] == 0 for row in guarded) and all(
                row["held_out_action_changed"] * 2 >= row["held_out_states_action_applied"]
                for row in guarded)},
        "K3_no_overfitting": {
            "train": {row["action"]: row["train_agreement"] for row in guarded},
            "held_out": {row["action"]: row["held_out_agreement"] for row in guarded},
            "MET": all(row["train_agreement"] == row["held_out_agreement"] for row in guarded)},
        "K4_the_census_is_not_all_yes": {
            "guarded": [row["action"] for row in guarded],
            "unguardable": [row["action"] for row in rows if not row.get("guard_argv")],
            "MET": len([row for row in rows if not row.get("guard_argv")]) * 2 >= len(rows)},
        "K5_the_check_tests_the_input_and_not_the_world": {
            "traps": trap_rows,
            "wrong_in": [row["action"] for row in trap_rows
                         if row.get("stage") == "MEASURED" and row["guard_wrong"]],
            "MET": len([row for row in trap_rows if row.get("stage") == "MEASURED"
                        and row["guard_wrong"]]) >= 2},
        "K6_zero": {"model_calls": 0, "parameters_stored": 0, "network_calls_at_run_time": 0,
                    "hand_written_action_to_guard_rules": 0, "MET": True},
    }

    receipt = {
        "schema": SCHEMA, "authority": "NONE__PRODUCER_RUN_SANDBOX", "date": "2026-11-16",
        "mode": "DISCOVER_EACH_PROGRAMS_OWN_CHECK_MODE_AND_MEASURE_WHAT_IT_CANNOT_SEE",
        "why_this_round": {
            "the_gap_it_closes": "the previous round could not state three actions' preconditions in "
                                 "its sensor vocabulary and named the reason in its own source: the "
                                 "validity probe of the artifact was the action itself",
            "the_pre_registered_next_step": "construct the observable by composing a program whose exit "
                                            "status decides the fact, and measure whether the decision "
                                            "becomes exact for free",
            "the_condition_that_makes_it_a_mechanism": "the check mode is discovered from the program's "
                                                       "own help output and the action's own argv; no "
                                                       "table from an action to a dry run exists here"},
        "criteria_were_declared_after_a_prototype_probe": False,
        "declared_acceptance_before_the_receipt_run": {
            "K1": "a check mode is discovered for at least three actions with training agreement 1.0, "
                  "and the three vocabulary-insufficient actions are among them",
            "K2": "every discovered check leaves the state byte-identical on held-out states, while the "
                  "action changes it on at least half the states where it applies",
            "K3": "each check's held-out agreement equals its training agreement",
            "K4": "at least half of the ten actions have no check mode reaching training agreement 1.0",
            "K5": "on the traps the check is wrong in at least two of the three",
            "K6": "zero model calls, zero parameters, zero network, no hand-written action-to-guard rule"},
        "verdict": verdict,
        "actions": rows,
        "price": {
            "decision_with_the_state_vocabulary": {"executions": 0, "accuracy": 0.7647,
                                                   "source": "the previous round's name-level "
                                                             "observation, quoted not re-measured"},
            "decision_with_the_action_itself": {"executions": 1, "accuracy": 1.0,
                                                 "residual": "the effect has already happened"},
            "decision_with_a_discovered_check": {
                "executions_per_decision": 1, "accuracy": {row["action"]: row["held_out_agreement"]
                                                           for row in guarded},
                "candidates_considered": {row["action"]: row["candidates"] for row in guarded},
                "candidates_that_agreed_and_changed_nothing":
                    {row["action"]: row["survivors_that_leave_the_state_alone"] for row in guarded},
                "residual": "the input, not the environment: see K5"},
        },
        "cost": {"seconds": round(time.time() - started, 1), "model_calls": 0,
                 "parameters_stored": 0, "network_calls_at_run_time": 0},
        "limits": [
            "the guard grammar is three declared rewrites of the action's own argv; an action whose "
            "check mode no rewrite reaches is counted unguardable BY THIS GRAMMAR, not in principle",
            "ten actions, one machine, one producer; the census is a count on these",
            "the trap's force depends on the process not being root; the receipt records whether the "
            "write was actually refused on each trap",
            "a check mode decides applicability; it says nothing about whether the action's effect is "
            "what the user wanted, which is the older and deeper residual",
        ],
    }
    if receipt_path is not None:
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps(receipt, indent=1) + "\n", encoding="utf-8")
    return receipt


def headline(receipt: dict[str, Any]) -> str:
    verdict = receipt["verdict"]
    guards = verdict["K1_the_check_mode_is_discovered_not_written"]["guards"]
    lines = ["guards discovered from the programs' own help pages:"]
    for action, guard in sorted(guards.items()):
        row = next(r for r in receipt["actions"] if r["action"] == action)
        lines.append(f"  {action:24s} {' '.join(guard):45s} held-out {row['held_out_agreement']}")
    lines.append(f"unguardable: {verdict['K4_the_census_is_not_all_yes']['unguardable']}")
    lines.append("traps where the check is wrong: "
                 + str(verdict["K5_the_check_tests_the_input_and_not_the_world"]["wrong_in"]))
    lines.append(f"seconds {receipt['cost']['seconds']}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default="/tmp/checkmode")
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--per-class", type=int, default=8)
    parser.add_argument("--seed", type=int, default=7)
    options = parser.parse_args(argv)
    receipt = measure(pathlib.Path(options.root), pathlib.Path(options.receipt),
                      per_class=options.per_class, seed=options.seed)
    print(json.dumps({key: value["MET"] for key, value in receipt["verdict"].items()}, indent=1))
    print(headline(receipt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
