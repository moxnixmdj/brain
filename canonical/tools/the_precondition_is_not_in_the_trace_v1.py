#!/usr/bin/env python3
"""An action is a conditional: the demonstration shows the action, never the condition.

THE CLAIM UNDER TEST. "Give the model the most advanced actions, let it do each one once in a new
environment, and it has learned them permanently -- so any computer use is solved." The first half of
that sentence is true and cheap: an action is a program, and a program replayed is exact. The second
half is the whole question, and it is not about storage. To USE an action you must decide that it
applies, and applicability is a set of states -- a precondition. One demonstration is one POINT of
that set. A point does not determine a set, and the tree has already measured on code that successes
alone identify 0 of 200 requirements (`applicability_v1`), that three successes buy nothing and the
first failure changes the answer (`A_SKILL_LEARNS_WHERE_IT_APPLIES_FROM_EXECUTED_OBSERVATIONS`).

What nobody measured is the part this question actually turns on: does any of that hold OUTSIDE a code
repository? "Any computer use" claims a law about environments, not about Python. So this round runs
the same law in a different environment class -- a real machine's own state, with real programs, and
with each program's own exit status as the oracle. Nothing here is a fixture invented to make a point:
real `git`, real `tar`, real `gzip`, real `patch`, real repository history, real files.

THREE ARMS, all on the same real states:

  (a) SUCCESSES ONLY, k = 1, 2, 4, 8 demonstrations of the same action. The strongest rule the evidence
      licenses is the intersection of the demonstrated states' facts. More successes make that
      intersection SMALLER, so the rule gets broader, monotonically, and lands on the base rate --
      never on the precondition, because a precondition is a fact about where the action FAILS.
  (b) CONTRASTS, chosen by `contrast_selection_v1` over states that are reachable on this machine.
      Cost in executions, and the accuracy bought.
  (c) VOCABULARY. Per action, whether an exact precondition exists in the sensor vocabulary at all is
      DECIDED by search, not assumed. Where it does not, no number of contrasts converges -- the
      insufficiency certificate, re-measured on a computer instead of on code.

WHY THE ORACLE IS THE PROGRAM'S EXIT STATUS. There is no annotation anywhere in this file about which
states "should" accept which action. `git stash pop` says so itself, by exiting 0 or not. The only
judgement I add is a refusal: a failure whose stderr is not a precondition violation (a conflict, a
network error) is AMBIGUOUS and is dropped from the evidence and counted, because a bad oracle would
manufacture the whole result.

COST. No model, no parameters, no learned weights. Real processes; a state is copied before it is
mutated so no observation destroys another.

Authority NONE. Producer-run measurement.
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
import pathlib
import random
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

SCHEMA = "BRAIN_THE_PRECONDITION_IS_NOT_IN_THE_TRACE_V1"

if str(pathlib.Path(__file__).resolve().parents[2]) not in sys.path:
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import applicability_v1 as APP  # noqa: E402
from canonical.runtime import contrast_selection_v1 as CONTRAST  # noqa: E402

APPLIES = "APPLIES"
DOES_NOT = "DOES_NOT_APPLY"
AMBIGUOUS = "AMBIGUOUS_ORACLE"

#: A mutation whose failure is *not* about applicability. If stderr says one of these, the outcome is
#: not evidence about the precondition and must not enter the learner.
AMBIGUITY_MARKERS = (
    "network", "timed out", "Could not resolve host", "permission denied", "No space left",
    "cannot lock ref", "unable to access", "Temporary failure",
)


# --------------------------------------------------------------------------------------------------
# The machine: real states, built by real commands
# --------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Action:
    """One real action on a real computer. `argv` runs in the state's directory."""

    name: str
    argv: tuple[str, ...]
    #: What the action is FOR, in the user's terms -- printed in the receipt.
    purpose: str


@dataclass
class State:
    name: str
    path: pathlib.Path
    #: How this state was reached, as the real commands that reached it.
    built_by: list[str] = field(default_factory=list)
    facts: tuple[str, ...] = ()


#: What each action's applicability actually turns on, established by construction and then CHECKED
#: against each program's own exit status. Recorded so that a witness found by search which disagrees
#: with it is visible as a coincidence instead of being reported as the truth.
INTENDED: dict[str, tuple[str, ...]] = {
    "git_stash_pop": ("stash.present",),
    "git_merge_abort": ("merge.in_progress",),
    "git_rebase_abort": ("rebase.in_progress",),
    "git_checkout_feature": ("branch.feature.exists",),
    "git_branch_delete_feature": ("branch.feature.exists", "branch.feature.merged"),
    "git_rm_cached_tracked": ("file.readme.tracked",),
    "tar_extract": ("VALID_ARCHIVE_NOT_OBSERVABLE",),
    "gzip_decompress": ("VALID_GZIP_NOT_OBSERVABLE",),
    "chmod_exec": ("file.script.nonempty",),
    "patch_apply": ("PATCH_APPLIES_NOT_OBSERVABLE",),
}


ACTIONS: tuple[Action, ...] = (
    Action("git_stash_pop", ("git", "stash", "pop"),
           "restore work that was set aside"),
    Action("git_merge_abort", ("git", "merge", "--abort"),
           "give up an interrupted merge"),
    Action("git_rebase_abort", ("git", "rebase", "--abort"),
           "give up an interrupted rebase"),
    Action("git_checkout_feature", ("git", "checkout", "feature"),
           "switch to the feature branch"),
    Action("git_branch_delete_feature", ("git", "branch", "-d", "feature"),
           "delete a branch that has been merged"),
    Action("git_rm_cached_tracked", ("git", "rm", "--cached", "-q", "README.rst"),
           "untrack a file while keeping it on disk"),
    Action("tar_extract", ("tar", "-xzf", "bundle.tgz"),
           "unpack an archive"),
    Action("gzip_decompress", ("gzip", "-d", "payload.gz"),
           "decompress a file"),
    Action("chmod_exec", ("chmod", "+x", "script.sh"),
           "make a file executable"),
    Action("patch_apply", ("patch", "--batch", "--forward", "-p1", "--dry-run", "-i",
                           "change.patch"),
           "apply a change that is shipped as a patch"),
)


def run(argv: Sequence[str], cwd: pathlib.Path, timeout: int = 60) -> tuple[int, str]:
    try:
        done = subprocess.run(list(argv), cwd=str(cwd), capture_output=True, text=True,
                              errors="replace", timeout=timeout)
        return done.returncode, (done.stdout or "") + (done.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, "timed out"
    except FileNotFoundError as exc:
        return 127, str(exc)


def git(path: pathlib.Path, *args: str) -> tuple[int, str]:
    return run(("git", "-c", "user.name=brain", "-c", "user.email=brain@example.com", *args), path)


# --------------------------------------------------------------------------------------------------
# The sensor vocabulary: what an agent on this machine can SEE with cheap read-only commands.
#
# Deliberately structural. Nothing here is a validity probe of the thing the action consumes (no
# `tar -tf`, no `gzip -t`, no patch test-apply), because those are the actions themselves: a vocabulary
# that contains the action's own oracle would make arm (c) vacuous and would prove nothing.
# --------------------------------------------------------------------------------------------------

def sense(path: pathlib.Path) -> tuple[str, ...]:
    facts: set[str] = set()
    code, out = git(path, "status", "--porcelain")
    tracked_dirty = [line for line in out.splitlines() if line and not line.startswith("??")]
    facts.add("worktree.clean" if not tracked_dirty else "worktree.dirty")
    facts.add("worktree.has_untracked" if any(
        line.startswith("??") for line in out.splitlines()) else "worktree.no_untracked")

    code, out = git(path, "stash", "list")
    facts.add("stash.present" if out.strip() else "stash.absent")

    facts.add("merge.in_progress" if (path / ".git" / "MERGE_HEAD").exists() else "merge.idle")
    facts.add("rebase.in_progress" if (path / ".git" / "rebase-merge").exists()
              or (path / ".git" / "rebase-apply").exists() else "rebase.idle")

    code, out = git(path, "branch", "--format=%(refname:short)")
    branches = set(out.split())
    facts.add("branch.feature.exists" if "feature" in branches else "branch.feature.absent")
    facts.add("branch.main.exists" if ("main" in branches or "master" in branches)
              else "branch.main.absent")
    if "feature" in branches:
        code, out = git(path, "branch", "--merged", "HEAD", "--format=%(refname:short)")
        facts.add("branch.feature.merged" if "feature" in set(out.split())
                  else "branch.feature.unmerged")

    code, out = git(path, "ls-files")
    tracked = set(out.splitlines())
    facts.add("file.readme.tracked" if "README.rst" in tracked else "file.readme.untracked")

    for name, key in (("bundle.tgz", "archive"), ("payload.gz", "gzip"), ("script.sh", "script"),
                      ("change.patch", "patch")):
        target = path / name
        facts.add(f"file.{key}.{'present' if target.exists() else 'absent'}")
        if target.exists():
            facts.add(f"file.{key}.nonempty" if target.stat().st_size > 0
                      else f"file.{key}.empty")
    if (path / "script.sh").exists():
        mode = (path / "script.sh").stat().st_mode
        facts.add("file.script.executable" if mode & 0o111 else "file.script.not_executable")
    return tuple(sorted(facts))


def _copy_state(source: pathlib.Path, destination: pathlib.Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination, symlinks=True)


def build_base(root: pathlib.Path, repo_url: str, commit: str | None) -> pathlib.Path:
    """A real repository at a real commit, prepared with real branches the states draw on."""
    base = root / "base"
    if base.exists():
        shutil.rmtree(base)
    run(("git", "clone", "-q", "--depth", "80", repo_url, str(base)), root, timeout=300)
    if commit:
        code, _out = git(base, "fetch", "-q", "--depth", "80", "origin", commit)
        if code == 0:
            git(base, "checkout", "-q", commit)
    git(base, "checkout", "-q", "-B", "main")
    git(base, "config", "user.name", "brain")
    git(base, "config", "user.email", "brain@example.com")
    # A real commit on main so that HEAD~1 is a real tree to fall back to.
    (base / "feature.txt").write_text("feature\n", encoding="utf-8")
    git(base, "add", "feature.txt")
    git(base, "commit", "-q", "-m", "feature commit")
    # Two branches that really conflict on the same line of the same file.
    (base / "conflict.txt").write_text("base\n", encoding="utf-8")
    git(base, "add", "conflict.txt")
    git(base, "commit", "-q", "-m", "conflict base")
    git(base, "checkout", "-q", "-b", "side")
    (base / "conflict.txt").write_text("side\n", encoding="utf-8")
    git(base, "commit", "-q", "-am", "side")
    git(base, "checkout", "-q", "main")
    (base / "conflict.txt").write_text("other\n", encoding="utf-8")
    git(base, "commit", "-q", "-am", "other")
    git(base, "checkout", "-q", "main")
    # A real patch, shipped as a file, that applies exactly to HEAD~1 and not to HEAD.
    code, diff = git(base, "--no-pager", "diff", "HEAD~1", "HEAD")
    if code == 0 and diff.strip():
        (base / "change.patch").write_text(diff, encoding="utf-8")
    return base


#: Real incidental conditions. These are the facts a demonstration will overfit to: none of them is
#: any action's precondition, and all of them are cheap to observe. A state is built from the action's
#: own precondition (present or absent) PLUS a few of these, so the trace rule has something wrong to
#: hold on to -- which is the whole phenomenon.
EXTRAS: tuple[str, ...] = ("untracked", "archive", "gzip", "script")


def _extras(path: pathlib.Path, chosen: Sequence[str], notes: list[str]) -> None:
    def step(*argv: str) -> int:
        code, _out = run(argv, path)
        notes.append(f"{' '.join(argv)} -> {code}")
        return code

    for extra in chosen:
        if extra == "untracked":
            (path / "scratch.txt").write_text("x\n", encoding="utf-8")
        elif extra == "archive":
            step("tar", "-czf", "bundle.tgz", "README.rst")
        elif extra == "gzip":
            (path / "payload.raw").write_text("payload\n", encoding="utf-8")
            step("gzip", "-kf", "payload.raw")
            if (path / "payload.raw.gz").exists():
                os.replace(path / "payload.raw.gz", path / "payload.gz")
            if (path / "payload.raw").exists():
                (path / "payload.raw").unlink()
        elif extra == "script":
            (path / "script.sh").write_text("#!/bin/sh\necho hi\n", encoding="utf-8")


def _positive(path: pathlib.Path, action: str, notes: list[str]) -> None:
    """Build the real state in which this action genuinely applies."""
    def step(*argv: str) -> int:
        code, _out = run(argv, path)
        notes.append(f"{' '.join(argv)} -> {code}")
        return code

    if action == "git_stash_pop":
        (path / "README.rst").write_text("local edit\n", encoding="utf-8")
        step("git", "add", "README.rst")
        step("git", "stash", "push", "-q")
    elif action == "git_merge_abort":
        step("git", "checkout", "-q", "side")
        step("git", "merge", "main")
    elif action == "git_rebase_abort":
        step("git", "checkout", "-q", "side")
        step("git", "rebase", "main")
    elif action == "git_checkout_feature":
        step("git", "branch", "feature")
    elif action == "git_branch_delete_feature":
        step("git", "branch", "feature")
    elif action == "git_rm_cached_tracked":
        pass  # README.rst is tracked in the base
    elif action == "tar_extract":
        step("tar", "-czf", "bundle.tgz", "README.rst")
    elif action == "gzip_decompress":
        (path / "payload.raw").write_text("payload\n", encoding="utf-8")
        step("gzip", "-kf", "payload.raw")
        if (path / "payload.raw.gz").exists():
            os.replace(path / "payload.raw.gz", path / "payload.gz")
        if (path / "payload.raw").exists():
            (path / "payload.raw").unlink()
    elif action == "chmod_exec":
        (path / "script.sh").write_text("#!/bin/sh\necho hi\n", encoding="utf-8")
    elif action == "patch_apply":
        step("git", "checkout", "-q", "HEAD~1")


def _negative(path: pathlib.Path, action: str, notes: list[str], variant: int) -> None:
    """Build a real state in which this action does not apply. `variant` picks HOW it fails."""
    def step(*argv: str) -> int:
        code, _out = run(argv, path)
        notes.append(f"{' '.join(argv)} -> {code}")
        return code

    if action == "git_stash_pop":
        if variant % 2:
            (path / "README.rst").write_text("local edit\n", encoding="utf-8")
            step("git", "add", "README.rst")
            step("git", "stash", "push", "-q")
            step("git", "stash", "pop", "-q")   # the stash was consumed
    elif action == "git_merge_abort":
        if variant % 2:
            step("git", "checkout", "-q", "side")
            step("git", "merge", "main")
            step("git", "merge", "--abort")
    elif action == "git_rebase_abort":
        if variant % 2:
            step("git", "checkout", "-q", "side")
            step("git", "rebase", "main")
            step("git", "rebase", "--abort")
    elif action == "git_checkout_feature":
        step("git", "branch", "-D", "feature")
    elif action == "git_branch_delete_feature":
        if variant % 2:
            step("git", "checkout", "-q", "-b", "tmp-diverged")
            (path / "diverged.txt").write_text("d\n", encoding="utf-8")
            step("git", "add", "diverged.txt")
            step("git", "commit", "-q", "-m", "diverged")
            step("git", "branch", "feature")
            step("git", "checkout", "-q", "main")
            step("git", "branch", "-D", "tmp-diverged")   # exists, and is NOT merged
        else:
            pass                                          # no such branch
    elif action == "git_rm_cached_tracked":
        step("git", "rm", "--cached", "-q", "README.rst")
    elif action == "tar_extract":
        if variant % 2:
            (path / "bundle.tgz").write_bytes(b"not an archive at all\n")
    elif action == "gzip_decompress":
        if variant % 2:
            (path / "payload.gz").write_bytes(b"not gzip at all\n")
    elif action == "chmod_exec":
        if (path / "script.sh").exists():
            (path / "script.sh").unlink()
    elif action == "patch_apply":
        if variant % 2:
            pass                                       # HEAD, so the patch cut at HEAD~1 is stale
        else:
            if (path / "change.patch").exists():
                (path / "change.patch").unlink()        # nothing to apply


#: Extras that would themselves decide the action, and so are forbidden in that action's family.
FORBIDDEN: dict[str, frozenset[str]] = {
    # an extra that would decide the action must not appear in that action's family
    "chmod_exec": frozenset({"script"}),
    "tar_extract": frozenset({"archive"}),
    "gzip_decompress": frozenset({"gzip"}),
}


def build_states(root: pathlib.Path, base: pathlib.Path, per_class: int = 8,
                 seed: int = 7) -> dict[str, list[State]]:
    """A real state family per action: `per_class` states where it applies, and where it does not.

    Each state is reached by running real programs on a copy of a real repository. The incidental
    conditions are drawn at random (seeded) from `EXTRAS`, so the two classes differ in the action's
    precondition AND in nothing systematic -- which is what makes the trace rule's error measurable
    rather than confounded.
    """
    scratch = root / "states"
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True)
    families: dict[str, list[State]] = {}
    for action in ACTIONS:
        rng = random.Random(f"{seed}:{action.name}")
        states: list[State] = []
        for want in (True, False):
            for index in range(per_class):
                path = scratch / f"{action.name}-{'pos' if want else 'neg'}{index:02d}"
                _copy_state(base, path)
                notes: list[str] = []
                if want:
                    _positive(path, action.name, notes)
                else:
                    _negative(path, action.name, notes, index)
                extras = [e for e in EXTRAS
                          if e not in FORBIDDEN.get(action.name, frozenset())
                          and rng.random() < 0.45]
                _extras(path, extras, notes)
                states.append(State(name=path.name, path=path, built_by=notes, facts=sense(path)))
        families[action.name] = states
    return families


# --------------------------------------------------------------------------------------------------
# The oracle: run the action in a copy, read the exit status
# --------------------------------------------------------------------------------------------------

def verdict(state: State, action: Action, root: pathlib.Path) -> tuple[str, str]:
    """APPLIES / DOES_NOT_APPLY / AMBIGUOUS_ORACLE, decided by the program itself."""
    trial = root / "trial"
    _copy_state(state.path, trial)
    code, out = run(action.argv, trial)
    shutil.rmtree(trial, ignore_errors=True)
    if code == 0:
        return APPLIES, out.strip()[:200]
    if any(marker in out for marker in AMBIGUITY_MARKERS):
        return AMBIGUOUS, out.strip()[:200]
    return DOES_NOT, out.strip()[:200]


# --------------------------------------------------------------------------------------------------
# Arm (a): what successes alone license. Two ends of the same version space, both reported.
# --------------------------------------------------------------------------------------------------

def intersection(fact_sets: Iterable[Sequence[str]]) -> frozenset[str]:
    sets = [frozenset(s) for s in fact_sets]
    if not sets:
        return frozenset()
    out = sets[0]
    for s in sets[1:]:
        out &= s
    return out


def accuracy(rule, rows: Sequence[tuple[frozenset[str], bool]]) -> dict[str, float]:
    if not rows:
        return {"accuracy": 0.0, "precision": 0.0, "recall": 0.0, "n": 0}
    correct = 0
    tp = fp = fn = 0
    for facts, truth in rows:
        guess = rule(facts)
        correct += int(guess == truth)
        tp += int(guess and truth)
        fp += int(guess and not truth)
        fn += int((not guess) and truth)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    return {"accuracy": round(correct / len(rows), 4), "precision": round(precision, 4),
            "recall": round(recall, 4), "n": len(rows)}


# --------------------------------------------------------------------------------------------------
# Arm (c): does the vocabulary contain the precondition at all? Decided by search, not assumed.
# --------------------------------------------------------------------------------------------------

def exact_precondition(table: Sequence[tuple[frozenset[str], bool]],
                       vocabulary: Sequence[str], max_size: int = 4) -> tuple[str, ...] | None:
    """The smallest fact set whose presence is equivalent to APPLIES on the observed table.

    None means no such set exists inside this vocabulary -- the observable the action's applicability
    turns on is not in what the agent can see, and no amount of execution will put it there.
    """
    positives = [facts for facts, ok in table if ok]
    negatives = [facts for facts, ok in table if not ok]
    if not positives or not negatives:
        return None
    candidate_facts = sorted({fact for facts in positives for fact in facts})
    for size in range(0, max_size + 1):
        for combo in itertools.combinations(candidate_facts, size):
            key = frozenset(combo)
            if all(key <= facts for facts in positives) and not any(
                    key <= facts for facts in negatives):
                return tuple(sorted(key))
    return None


# --------------------------------------------------------------------------------------------------
# The measurement
# --------------------------------------------------------------------------------------------------

def measure(root: pathlib.Path, repo_url: str, commit: str | None, seed: int = 7,
            per_class: int = 8, receipt_path: pathlib.Path | None = None) -> dict[str, Any]:
    started = time.time()
    root.mkdir(parents=True, exist_ok=True)
    base = build_base(root, repo_url, commit)
    families = build_states(root, base, per_class=per_class, seed=seed)
    if receipt_path is not None:
        print(f"[machine] {sum(len(v) for v in families.values())} real states on {repo_url}",
              flush=True)

    rows: list[dict[str, Any]] = []
    for action in ACTIONS:
        states = families[action.name]
        table: list[tuple[str, frozenset[str], str, str]] = []
        for state in states:
            outcome, note = verdict(state, action, root)
            table.append((state.name, frozenset(state.facts), outcome, note))
        positive = [row for row in table if row[2] == APPLIES]
        negative = [row for row in table if row[2] == DOES_NOT]
        ambiguous = [row for row in table if row[2] == AMBIGUOUS]

        row: dict[str, Any] = {
            "action": action.name,
            "purpose": action.purpose,
            "argv": list(action.argv),
            "states": len(table),
            "applies": len(positive),
            "does_not_apply": len(negative),
            "ambiguous_oracle": [{"state": name, "why": note[:140]}
                                 for name, _f, _o, note in ambiguous],
            "vocabulary_size": len(states[0].facts),
        }
        if len(positive) < 3 or len(negative) < 3:
            row["stage"] = "REFUSED__NOT_ENOUGH_STATES_OF_EITHER_KIND"
            rows.append(row)
            if receipt_path is not None:
                print(f"[{action.name}] {row['stage']} (+{len(positive)}/-{len(negative)})",
                      flush=True)
            continue

        full = [(facts, outcome == APPLIES) for _n, facts, outcome, _note in table]
        witness = exact_precondition(full, states[0].facts)
        row["exact_precondition_in_vocabulary"] = list(witness) if witness else None
        row["intended_precondition"] = list(INTENDED.get(action.name, ()))
        row["witness_agrees_with_intent"] = (witness is not None
                                             and tuple(sorted(witness))
                                             == tuple(sorted(INTENDED.get(action.name, ()))))
        # A fact that takes ONE value across every state of the family cannot be refuted by any
        # observation, so it survives in every requirement the learner will ever report. That is the
        # arithmetic behind a residual "several consistent requirements" that no experiment removes.
        seen: dict[str, set[str]] = {}
        for _n, facts, _o, _note in table:
            for fact in facts:
                seen.setdefault(fact.split(".")[0] + "." + fact.split(".")[1]
                                if fact.count(".") >= 1 else fact, set()).add(fact)
        constants = [group for group, values in seen.items() if len(values) == 1]
        row["fact_groups_that_never_vary"] = sorted(constants)
        row["fact_groups"] = len(seen)

        # Held out: every second state of each class. Demonstrations never see these.
        held = [*positive[::2], *negative[::2]]
        held_names = {name for name, _f, _o, _n in held}
        held_rows = [(facts, outcome == APPLIES) for _n, facts, outcome, _n2 in
                     [(n, f, o, note) for n, f, o, note in held]]
        base_rate = round(sum(1 for _f, ok in held_rows if ok) / len(held_rows), 4)

        # (a) successes only: k demonstrations of the same action, all of them successes.
        curve: list[dict[str, Any]] = []
        demo_pool = [row_ for row_ in positive if row_[0] not in held_names]
        for k in (1, 2, 4):
            if k > len(demo_pool):
                break
            demos = demo_pool[:k]
            licensed = intersection(facts for _n, facts, _o, _c in demos)
            boundary = APP.learn([(sorted(facts), True) for _n, facts, _o, _c in demos])
            # `most_specific` is the intersection; `most_general` is the empty requirement. Both are
            # consistent with successes alone, so the evidence licenses no behaviour either way.
            curve.append({
                "demonstrations": k,
                "learner_status": boundary.status,
                "learner_reason": boundary.reason,
                "licensed_requirement_size": len(licensed),
                "rule_from_demonstrations": accuracy(
                    lambda facts, key=licensed: key <= facts, held_rows),
                "rule_always_true": accuracy(lambda facts: True, held_rows),
                "survivors": boundary.survivor_count,
                "most_general": list(boundary.most_general),
                "rule_equals_the_true_precondition": bool(witness) and licensed == frozenset(witness),
            })
        row["arm_a_successes_only"] = curve
        row["held_out_base_rate"] = base_rate

        # (b) contrasts: the tree's own selector chooses which reachable state to try next.
        pool = [row_ for row_ in positive + negative if row_[0] not in held_names]
        # One representative per FACT SIGNATURE: two states the sensor cannot tell apart are one
        # observation, and pretending otherwise would inflate the evidence.
        available: dict[frozenset[str], tuple[str, bool]] = {}
        for name, facts, outcome, _n in pool:
            available.setdefault(facts, (name, outcome == APPLIES))
        start_row = demo_pool[0]
        evidence: list[tuple[tuple[str, ...], bool]] = [(sorted(start_row[1]), True)]
        available.pop(start_row[1], None)
        executed = 1
        trajectory: list[dict[str, Any]] = []
        boundary = APP.learn(evidence)
        while not boundary.identified and executed < 12 and available:
            contrast = CONTRAST.select_contrast(evidence, [sorted(sig) for sig in available])
            if not contrast.informative:
                trajectory.append({"stop": contrast.reason,
                                   "survivors_before": contrast.survivors_before})
                break
            chosen = frozenset(contrast.state)
            entry = available.pop(chosen, None)
            if entry is None:
                # the selector named a state the sensor cannot distinguish from one already seen
                trajectory.append({"stop": "CHOSEN_STATE_ALREADY_OBSERVED"})
                break
            name, truth = entry
            evidence.append((sorted(chosen), truth))
            executed += 1
            boundary = APP.learn(evidence)
            trajectory.append({"state": name, "outcome": truth,
                               "status": boundary.status,
                               "survivors": boundary.survivor_count})
        if boundary.identified:
            key = frozenset(boundary.required or ())
        else:
            # the honest fallback: the least demanding requirement the evidence still allows
            key = frozenset(boundary.most_general)
            row["arm_b_fallback_requirement_size"] = len(key)
        row["arm_b_contrasts"] = {
            "executions": executed,
            "survivors_after_evidence": boundary.survivor_count,
            "stop_reason": (trajectory[-1].get("stop") if trajectory else None),
            "status": boundary.status,
            "requirement": sorted(boundary.required or ()),
            "accuracy_on_held_out": accuracy(lambda facts, k=key: k <= facts, held_rows),
            "matches_exact_precondition": (tuple(sorted(boundary.required or ()))
                                           == witness) if boundary.identified else False,
            "trajectory": trajectory,
        }

        # The true half of the claim: a program replayed is exact and permanent.
        replays = 0
        for name, _f, _o, _c in demo_pool[:3]:
            state = next(st for st in states if st.name == name)
            outcome, _note = verdict(state, action, root)
            replays += int(outcome == APPLIES)
        row["retention_replays_ok"] = f"{replays}/{min(3, len(demo_pool))}"

        row["stage"] = "MEASURED"
        rows.append(row)
        if receipt_path is not None:
            print(f"[{action.name}] vocab={'yes' if witness else 'NO '} "
                  f"base_rate={base_rate} "
                  f"armA={[c['rule_from_demonstrations']['accuracy'] for c in curve]} "
                  f"armB={row['arm_b_contrasts']['accuracy_on_held_out']['accuracy']} "
                  f"in {executed} exec", flush=True)

    measured = [r for r in rows if r["stage"] == "MEASURED"]
    sufficient = [r for r in measured if r["exact_precondition_in_vocabulary"]]
    insufficient = [r for r in measured if not r["exact_precondition_in_vocabulary"]]
    summary = {
        "actions_attempted": len(rows),
        "actions_measured": len(measured),
        "actions_refused": len(rows) - len(measured),
        "vocabulary_sufficient": len(sufficient),
        "vocabulary_insufficient": len(insufficient),
        "insufficient_actions": [r["action"] for r in insufficient],
        "arm_a_accuracy_by_k": {
            str(k): round(sum(next(c for c in r["arm_a_successes_only"] if c["demonstrations"] == k
                                   )["rule_from_demonstrations"]["accuracy"]
                              for r in measured if any(c["demonstrations"] == k
                                                       for c in r["arm_a_successes_only"]))
                          / max(1, sum(1 for r in measured
                                       if any(c["demonstrations"] == k
                                              for c in r["arm_a_successes_only"]))), 4)
            for k in (1, 2, 4)
        },
        "arm_a_identified_ever": sum(1 for r in measured
                                     for c in r["arm_a_successes_only"]
                                     if c["learner_status"] == APP.IDENTIFIED),
        "arm_b_accuracy_sufficient": round(sum(
            r["arm_b_contrasts"]["accuracy_on_held_out"]["accuracy"] for r in sufficient)
            / max(1, len(sufficient)), 4),
        "arm_b_accuracy_insufficient": round(sum(
            r["arm_b_contrasts"]["accuracy_on_held_out"]["accuracy"] for r in insufficient)
            / max(1, len(insufficient)), 4),
        "arm_b_identified": sum(1 for r in measured
                                if r["arm_b_contrasts"]["status"] == APP.IDENTIFIED),
        "arm_b_executions": sum(r["arm_b_contrasts"]["executions"] for r in measured),
        "arm_a_rule_equalled_the_true_precondition": sum(
            1 for r in measured for c in r["arm_a_successes_only"]
            if c.get("rule_equals_the_true_precondition")),
        "arm_a_best_accuracy": round(max(
            [c["rule_from_demonstrations"]["accuracy"] for r in measured
             for c in r["arm_a_successes_only"]] or [0.0]), 4),
        "retention_total": sum(int(v.split("/")[0]) for v in
                               (r["retention_replays_ok"] for r in measured)),
        "retention_attempted": sum(int(v.split("/")[1]) for v in
                                   (r["retention_replays_ok"] for r in measured)),
        "selector_stops_unfalsifiable": sum(
            1 for r in measured
            if (r["arm_b_contrasts"]["stop_reason"] or "").startswith("EVERY_REACHABLE_STATE")),
        "arm_b_matches_exact_precondition": sum(
            1 for r in measured if r["arm_b_contrasts"]["matches_exact_precondition"]),
        "ambiguous_oracle_total": sum(len(r["ambiguous_oracle"]) for r in rows),
        "retention": {r["action"]: r["retention_replays_ok"] for r in measured},
        "seconds": round(time.time() - started, 1),
        "parameters_stored": 0,
        "model_calls": 0,
    }
    receipt = {
        "schema": SCHEMA,
        "authority": "NONE__PRODUCER_RUN_SANDBOX",
        "date": "2026-11-26",
        "environment": {"kind": "real machine: git, tar, gzip, patch", "base_repo": repo_url,
                        "commit": commit,
                        "states": sum(len(v) for v in families.values())},
        "oracle": ("each program's own exit status; a failure whose stderr names a non-precondition "
                   "cause is AMBIGUOUS and dropped"),
        "summary": summary,
        "rows": rows,
    }
    if receipt_path is not None:
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps(receipt, indent=1) + "\n", encoding="utf-8")
    return receipt


def headline(receipt: dict[str, Any]) -> str:
    s = receipt["summary"]
    return (f"{s['actions_measured']} real actions on a real machine; precondition inside the sensor "
            f"vocabulary for {s['vocabulary_sufficient']} and outside it for "
            f"{s['vocabulary_insufficient']} ({', '.join(s['insufficient_actions'])}); "
            f"successes only reach {s['arm_a_accuracy_by_k'].get('8')} at k=8 and identify "
            f"{s['arm_a_identified_ever']} requirements; contrasts reach "
            f"{s['arm_b_accuracy_sufficient']} on the sufficient actions and "
            f"{s['arm_b_accuracy_insufficient']} on the insufficient ones, identifying "
            f"{s['arm_b_identified']} in {s['arm_b_executions']} executions")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default="/tmp/precondition")
    parser.add_argument("--repo", default="https://github.com/pypa/packaging.git")
    parser.add_argument("--commit", default=None)
    parser.add_argument("--receipt", default=None)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--per-class", type=int, default=8)
    args = parser.parse_args(argv)
    receipt_path = pathlib.Path(args.receipt) if args.receipt else None
    receipt = measure(pathlib.Path(args.root), args.repo, args.commit, seed=args.seed,
                      per_class=args.per_class, receipt_path=receipt_path)
    print(headline(receipt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
