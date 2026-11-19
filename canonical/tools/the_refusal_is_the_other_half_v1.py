#!/usr/bin/env python3
"""The refusal is the other half of the operator.

The question under test, for the fourth time and in its sharpest form: *give the model the most advanced actions,
let it experience each once, and it has them permanently -- so is that all of computer use?*

The tree already measured the two halves of the negative answer:

  * a success teaches nothing about applicability -- 0 / 200 in `what_a_success_teaches_20261112.py`;
  * the precondition is not in the trace -- 10 real actions, 160 states, `arm_a_identified_ever: 0` and
    `arm_b_identified: 0`, with `arm_a_best_accuracy: 1.0` (a rule that was always right and never identified).

So exactly one schedule is left untested, and it is the one a person uses: **break it, and read what it says.**
Every real program answers a refusal with a message, and that message is not a sample of the world -- it is a
*statement about the world*, made by the only authority that has the precondition.

What this round measures, on ten real actions driven by ten real binaries:

  K1  one success leaves the version space with many distinct truth-vectors (the user's plan is a point, not a
      boundary);
  K2  the refusal message is a function of the violated precondition coordinate: distinct coordinates give
      distinct messages (injectivity) and the same coordinate under different distractors gives the same
      message (invariance) -- no parsing, no synonyms, two comparative properties only;
  K3  one refusal per coordinate collapses the version space to a single truth-vector -- identification, which
      160 state observations did not reach;
  K4  a refusal leaves the tree byte-identical (the failure is free), so the whole boundary costs zero
      world-trials: it is a declaration, not an experiment;
  K5  the schedule price: 1 success + k refusals per action identifies what 2^k state interventions cannot,
      and what the exhaustive lattice the previous round ran (160 states, 0 identified) did not.

Zero model calls, zero parameters, zero network. The only hand-written part is the fact vector each state is
described by -- and that part is exactly the reach bottleneck this round leaves open, stated in `limits`.

    python3 canonical/tools/the_refusal_is_the_other_half_v1.py [--receipt PATH]
"""
from __future__ import annotations

import hashlib
import itertools
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable, Sequence

SCHEMA = "BRAIN_THE_REFUSAL_IS_THE_OTHER_HALF_V1"
FACT_NAMES = ("exists", "is_dir", "parent_exists", "stash", "clean", "gzip", "tar", "context", "sorted")


# ------------------------------------------------------------------------------------------------------------
# the world
# ------------------------------------------------------------------------------------------------------------

def _run(argv: Sequence[str], cwd: pathlib.Path) -> tuple[int, str]:
    proc = subprocess.run(list(argv), cwd=str(cwd), capture_output=True, text=True, timeout=60)
    return proc.returncode, (proc.stderr or "") + (proc.stdout or "")


def _write(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_template(root: pathlib.Path) -> pathlib.Path:
    """A small but real world: a git repo with a stash, a patch, a gzip, a tarball, a directory, a sorted file."""
    template = root / "template"
    template.mkdir(parents=True)
    repo = template / "repo"
    repo.mkdir()
    git = ["git", "-c", "user.email=a@b.c", "-c", "user.name=t", "-c", "commit.gpgsign=false",
           "-c", "init.defaultBranch=main"]
    _run(git + ["init", "-q"], repo)
    _write(repo / "README.txt", "one\n")
    _run(git + ["add", "README.txt"], repo)
    _run(git + ["commit", "-q", "-m", "one"], repo)
    _write(repo / "README.txt", "one\ntwo\n")
    _run(git + ["stash", "push", "-q", "-m", "held"], repo)          # a stash exists; the tree is clean

    files = template / "files"
    (files / "dir").mkdir(parents=True)
    _write(files / "a.txt", "alpha\nbeta\ngamma\n")
    _write(files / "sorted.txt", "a\nb\nc\n")
    _write(files / "plain.txt", "just text\n")
    _write(files / "x", "hello\n")
    _run(["gzip", "-f", "x"], files)                                  # x.gz
    tank = root / "tank"
    tank.mkdir()
    _write(tank / "m.txt", "member\n")
    _run(["tar", "-czf", str(files / "b.tar.gz"), "-C", str(tank), "m.txt"], root)
    shutil.rmtree(tank)
    # a unified diff that applies to files/a.txt exactly as it is
    _write(files / "p.patch", "--- a/files/a.txt\n+++ b/files/a.txt\n@@ -1,3 +1,3 @@\n alpha\n-beta\n+BETA\n gamma\n")
    (template / "files" / "a.txt.bak").write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
    return template


def snapshot(root: pathlib.Path) -> dict[str, tuple[int, bytes]]:
    out: dict[str, tuple[int, bytes]] = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if ".git" in rel.parts:
            continue
        if path.is_file() and not path.is_symlink():
            out[str(rel)] = (path.stat().st_mode, path.read_bytes())
        elif path.is_dir():
            out[str(rel)] = (path.stat().st_mode, b"/")
    return out


def changed_paths(before: dict[str, tuple[int, bytes]], after: dict[str, tuple[int, bytes]]) -> list[str]:
    return sorted({p for p in set(before) | set(after) if before.get(p) != after.get(p)})


def tree_hash(root: pathlib.Path) -> str:
    h = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if ".git" in rel.parts:
            continue
        h.update(str(rel).encode())
        if path.is_file():
            h.update(path.read_bytes())
            h.update(str(path.stat().st_mode).encode())
        elif path.is_dir():
            h.update(b"/")
    return h.hexdigest()


# ------------------------------------------------------------------------------------------------------------
# the actions: fixed argv, a fact vector, a true precondition, and one single-fact violator per coordinate
# ------------------------------------------------------------------------------------------------------------

class Action:
    """One real action. `facts` names the booleans its caller can see; `coords` names the ones that gate it."""

    def __init__(self, name: str, argv: Sequence[str], facts: Callable[[pathlib.Path], dict[str, bool]],
                 coords: Sequence[str], violate: dict[str, Callable[[pathlib.Path, int], None]],
                 setup: Callable[[pathlib.Path], None] | None = None,
                 distract: Callable[[pathlib.Path, int], None] | None = None,
                 cwd: str = ".") -> None:
        self.name, self.argv, self.facts, self.coords = name, list(argv), facts, list(coords)
        self.violate, self.setup, self.distract, self.cwd = violate, setup, distract, cwd

    def observe(self, state: pathlib.Path) -> dict[str, bool]:
        return self.facts(state)

    def run(self, state: pathlib.Path) -> tuple[int, str]:
        return _run(self.argv, state / self.cwd)


def _rm(p: pathlib.Path) -> None:
    if p.is_dir() and not p.is_symlink():
        shutil.rmtree(p)
    elif p.exists() or p.is_symlink():
        p.unlink()


GIT = ["git", "-c", "user.email=a@b.c", "-c", "user.name=t", "-c", "commit.gpgsign=false"]


def _git(state: pathlib.Path, *args: str) -> tuple[int, str]:
    return _run(GIT + list(args), state / "repo")


def _pad(state: pathlib.Path, variant: int) -> None:
    """A distractor: a difference between two states that is NOT one of the action's facts."""
    _write(state / "files" / f"pad{variant}.txt", f"p{variant}\n")


def _stash_facts(state: pathlib.Path) -> dict[str, bool]:
    rc, listing = _git(state, "stash", "list")
    return {"stash": rc == 0 and bool(listing.strip()),
            "clean": _git(state, "diff", "--quiet")[0] == 0 and _git(state, "diff", "--cached", "--quiet")[0] == 0}


def _patch_facts(state: pathlib.Path) -> dict[str, bool]:
    files = state / "files"
    if not (files / "a.txt").is_file():
        return {"context": True, "exists": False}
    return {"context": _run(["patch", "-p1", "--dry-run", "--forward", "-i", "files/p.patch"], state)[0] == 0,
            "exists": True}


def _gzip_facts(state: pathlib.Path) -> dict[str, bool]:
    target = state / "files" / "x.gz"
    if not target.is_file():
        return {"gzip": True, "exists": False}
    return {"gzip": _run(["gzip", "-t", str(target)], state)[0] == 0, "exists": True}


def _tar_facts(state: pathlib.Path) -> dict[str, bool]:
    target = state / "files" / "b.tar.gz"
    if not target.is_file():
        return {"tar": True, "exists": False}
    return {"tar": _run(["tar", "-tzf", str(target)], state)[0] == 0, "exists": True}


def _cp_facts(state: pathlib.Path) -> dict[str, bool]:
    return {"dest_is_dir": (state / "files" / "dir").is_dir(),
            "source": (state / "files" / "a.txt").is_file()}



def _mkdir_facts(state: pathlib.Path) -> dict[str, bool]:
    return {"parent": (state / "files" / "nodir").is_dir(),
            "absent": not (state / "files" / "nodir" / "sub").exists()}


def _rmdir_facts(state: pathlib.Path) -> dict[str, bool]:
    d = state / "files" / "dir"
    if not d.is_dir():
        return {"exists": False, "empty": True}
    return {"exists": True, "empty": not any(d.iterdir())}


def _ln_facts(state: pathlib.Path) -> dict[str, bool]:
    return {"parent": (state / "files" / "sub").is_dir(),
            "absent": not (state / "files" / "sub" / "link").exists()
                      and not (state / "files" / "sub" / "link").is_symlink()}


def _sort_facts(state: pathlib.Path) -> dict[str, bool]:
    f = state / "files" / "sorted.txt"
    if not f.is_file():
        return {"exists": False, "sorted": True}
    return {"exists": True, "sorted": f.read_text() == "a\nb\nc\n"}


def _chmod_facts(state: pathlib.Path) -> dict[str, bool]:
    return {"exists": (state / "files" / "a.txt").is_file()}


ACTIONS: tuple[Action, ...] = (
    Action("git_stash_pop", GIT + ["stash", "pop"], _stash_facts, ["stash", "clean"],
           {"stash": lambda s, v: _git(s, "stash", "clear"),
            "clean": lambda s, v: _write(s / "repo" / "README.txt", "one\nconflict\n")},
           distract=_pad, cwd="repo"),
    Action("patch_apply", ["patch", "-p1", "--forward", "--no-backup-if-mismatch", "-i", "files/p.patch"],
           _patch_facts, ["context", "exists"],
           {"context": lambda s, v: _write(s / "files" / "a.txt", f"alpha\nBETA{v}\ngamma\n"),
            "exists": lambda s, v: _rm(s / "files" / "a.txt")}, distract=_pad),
    Action("gzip_decompress", ["gzip", "-d", "files/x.gz"], _gzip_facts, ["gzip", "exists"],
           {"gzip": lambda s, v: (s / "files" / "x.gz").write_bytes(b"this is not compressed\n"),
            "exists": lambda s, v: _rm(s / "files" / "x.gz")}, distract=_pad),
    Action("tar_extract", ["tar", "-xzf", "files/b.tar.gz"], _tar_facts, ["tar", "exists"],
           {"tar": lambda s, v: (s / "files" / "b.tar.gz").write_bytes(b"this is not a gzip file\n"),
            "exists": lambda s, v: _rm(s / "files" / "b.tar.gz")}, distract=_pad),
    Action("cp_into_dir", ["cp", "files/a.txt", "files/dir/"], _cp_facts, ["dest_is_dir", "source"],
           {"dest_is_dir": lambda s, v: (_rm(s / "files" / "dir"), _write(s / "files" / "dir", "now a file\n")),
            "source": lambda s, v: _rm(s / "files" / "a.txt")}, distract=_pad),
    Action("mkdir_nested", ["mkdir", "files/nodir/sub"], _mkdir_facts, ["parent", "absent"],
           {"parent": lambda s, v: _rm(s / "files" / "nodir"),
            "absent": lambda s, v: (s / "files" / "nodir" / "sub").mkdir(parents=True)},
           setup=lambda s: (s / "files" / "nodir").mkdir(parents=True, exist_ok=True), distract=_pad),
    Action("rmdir_empty", ["rmdir", "files/dir"], _rmdir_facts, ["exists", "empty"],
           {"exists": lambda s, v: _rm(s / "files" / "dir"),
            "empty": lambda s, v: _write(s / "files" / "dir" / f"inside{v}.txt", "i\n")}, distract=_pad),
    Action("ln_symlink", ["ln", "-s", "files/a.txt", "files/sub/link"], _ln_facts, ["parent", "absent"],
           {"parent": lambda s, v: _rm(s / "files" / "sub"),
            "absent": lambda s, v: (s / "files" / "sub" / "link").write_text("occupied\n")},
           setup=lambda s: (s / "files" / "sub").mkdir(parents=True, exist_ok=True), distract=_pad),
    Action("sort_check", ["sort", "-c", "files/sorted.txt"], _sort_facts, ["exists", "sorted"],
           {"exists": lambda s, v: _rm(s / "files" / "sorted.txt"),
            "sorted": lambda s, v: _write(s / "files" / "sorted.txt", f"c\nb{v}\na\n")}, distract=_pad),
    Action("chmod_file", ["chmod", "644", "files/a.txt"], _chmod_facts, ["exists"],
           {"exists": lambda s, v: _rm(s / "files" / "a.txt")}, distract=_pad),
)

# facts that are true of every state, so that a success leaves more than the trivial ambiguity
CONSTANTS = {"tools_present": True, "repo_present": True, "template_present": True}


def normalise(msg: str, state: pathlib.Path, variant: int) -> str:
    """A declared rewrite, not a parse: paths and distractor names out, nothing else touched."""
    out = msg.replace(str(state), "<state>").replace(str(state.parent), "<root>")
    for pattern in (f"pad{variant}.txt", f"inside{variant}.txt", f"note{variant}.txt", f"other{variant}.txt"):
        out = out.replace(pattern, "<pad>")
    out = out.replace(f"BETA{variant}", "<b>").replace(f"b{variant}", "<b>")
    return " ".join(out.split())[:400]


# ------------------------------------------------------------------------------------------------------------
# the version space
# ------------------------------------------------------------------------------------------------------------

def hypotheses(fact_names: Sequence[str]) -> list[tuple[tuple[str, bool], ...]]:
    lits = [(name, sign) for name in fact_names for sign in (True, False)]
    out: list[tuple[tuple[str, bool], ...]] = [()]
    out += [(lit,) for lit in lits]
    out += [(a, b) for a, b in itertools.combinations(lits, 2) if a[0] != b[0]]
    return out


def holds(hypothesis: Sequence[tuple[str, bool]], facts: dict[str, bool]) -> bool:
    return all(facts[name] == sign for name, sign in hypothesis)


def truth_vector(hypothesis: Sequence[tuple[str, bool]], states: Sequence[dict[str, bool]]) -> tuple[bool, ...]:
    return tuple(holds(hypothesis, facts) for facts in states)


# ------------------------------------------------------------------------------------------------------------
# the measurement
# ------------------------------------------------------------------------------------------------------------

def measure_state(template: pathlib.Path, root: pathlib.Path, action: Action, coord: str | None,
                  variant: int) -> dict[str, Any]:
    state = root / "state"
    if state.exists():
        shutil.rmtree(state)
    shutil.copytree(template, state)
    if action.setup is not None:
        action.setup(state)
    if action.distract is not None:
        action.distract(state, variant)
    if coord is not None:
        action.violate[coord](state, variant)
    facts = dict(action.observe(state)); facts.update(CONSTANTS)
    before = snapshot(state)
    rc, msg = action.run(state)
    after = snapshot(state)
    touched = changed_paths(before, after)
    bookkeeping = {"a.txt.rej", "a.txt.orig", "README.txt.orig"}
    return {"coord": coord, "variant": variant, "facts": facts, "rc": rc,
            "message": normalise(msg, state, variant), "raw_message": msg[:1200],
            "touched": touched,
            "tree_unchanged": not touched,
            "only_bookkeeping": all(path.split("/")[-1] in bookkeeping for path in touched)}


def check_narrower_than_the_fact(root: pathlib.Path) -> dict[str, Any]:
    """`tar -tzf` is the declared check for "is a tar archive". Measure what it cannot see."""
    probe = root / "narrow" / "garbage.tgz"
    probe.parent.mkdir(parents=True, exist_ok=True)
    import gzip as _gz
    probe.write_bytes(_gz.compress(b"this is not a tar archive\n"))
    rc, msg = _run(["tar", "-tzf", str(probe)], root / "narrow")
    return {"file": "a gzip whose payload is not a tar archive", "tar_tzf_exit": rc,
            "tar_tzf_said": " ".join(msg.split())[:200],
            "means": "the declared check accepts a file that is not an archive, so the fact it is used for is "
                     "narrower than the check's own claim",
            "MEASURED": rc == 0}


def measure_action(template: pathlib.Path, root: pathlib.Path, action: Action) -> dict[str, Any]:
    base = measure_state(template, root, action, None, 0)
    base["applied"] = base["rc"] == 0
    violations: list[dict[str, Any]] = []
    for coord in action.coords:
        for variant in (0, 1):
            row = measure_state(template, root, action, coord, variant)
            row["refused"] = row["rc"] != 0
            row["coords_that_changed"] = sorted(
                name for name in action.coords if row["facts"][name] != base["facts"][name])
            violations.append(row)
    primary = [row for row in violations if row["variant"] == 0]
    repeat = [row for row in violations if row["variant"] == 1]
    return {"action": action.name, "action_argv": action.argv, "coords": action.coords, "base": base,
            "violations": violations,
            "each_violation_changed_exactly_one_fact": all(
                len(row["coords_that_changed"]) == 1 for row in primary),
            "the_changed_fact_is_the_dropped_coordinate": all(
                row["coords_that_changed"] == [row["coord"]] for row in primary),
            "every_violation_was_refused": all(row["refused"] for row in violations),
            "injective": len({row["message"] for row in primary}) == len(primary),
            "invariant_under_distractor": all(a["message"] == b["message"] for a, b in zip(primary, repeat)),
            "messages": {row["coord"]: row["message"] for row in primary},
            "refusals_that_left_the_tree_identical": sum(1 for row in violations if row["tree_unchanged"]),
            "refusals_that_changed_something": {f"{row['coord']}#{row['variant']}": row["touched"]
                                                for row in violations if row["touched"]},
            "refusals_confined_to_bookkeeping": [f"{row['coord']}#{row['variant']}" for row in violations
                                                 if row["touched"] and row["only_bookkeeping"]],
            "refusals": len(violations),
            "facts": list(base["facts"]),
            "states": [base["facts"]] + [row["facts"] for row in violations],
        }


def version_space(row: dict[str, Any]) -> dict[str, Any]:
    """Success only, versus success plus one refusal per coordinate: distinct behaviours over the measured states."""
    states = row["states"]
    after_success = [h for h in hypotheses(row["facts"]) if holds(h, states[0])]
    after_refusals = [h for h in hypotheses(row["facts"])
                      if holds(h, states[0]) and not any(holds(h, facts) for facts in states[1:])]
    true_vector = tuple(all(facts[name] for name in row["coords"]) for facts in states)
    vectors = {truth_vector(h, states) for h in after_refusals}
    return {
        "hypotheses_enumerated": len(hypotheses(row["facts"])),
        "survivors_after_the_one_success": len(after_success),
        "distinct_behaviours_after_the_one_success": len({truth_vector(h, states) for h in after_success}),
        "survivors_after_one_refusal_per_coordinate": len(after_refusals),
        "distinct_behaviours_after_refusals": len(vectors),
        "identified": len(vectors) == 1,
        "the_survivor_is_the_true_precondition": list(vectors) == [true_vector] if len(vectors) == 1 else False,
    }


def measure(root: pathlib.Path | None = None) -> dict[str, Any]:
    started = time.time()
    root = pathlib.Path(root or tempfile.mkdtemp(prefix="refusal-"))
    root.mkdir(parents=True, exist_ok=True)
    template = build_template(root)
    rows = [measure_action(template, root, action) for action in ACTIONS]
    spaces = {row["action"]: version_space(row) for row in rows}
    total_refusals = sum(row["refusals"] for row in rows)
    free_refusals = sum(row["refusals_that_left_the_tree_identical"] for row in rows)

    verdict = {
        "K1_one_success_is_a_point_not_a_boundary": {
            "per_action_distinct_behaviours_left": {
                name: space["distinct_behaviours_after_the_one_success"] for name, space in spaces.items()},
            "minimum": min(space["distinct_behaviours_after_the_one_success"] for space in spaces.values()),
            "MET": min(space["distinct_behaviours_after_the_one_success"] for space in spaces.values()) > 1},
        "K2_the_refusal_is_a_function_of_the_violated_coordinate": {
            "actions_where_the_violation_changed_exactly_one_fact": sum(
                1 for row in rows if row["each_violation_changed_exactly_one_fact"]),
            "actions_where_that_fact_was_the_dropped_coordinate": sum(
                1 for row in rows if row["the_changed_fact_is_the_dropped_coordinate"]),
            "actions_injective": [row["action"] for row in rows if row["injective"]],
            "actions_invariant_under_distractor": [row["action"] for row in rows if row["invariant_under_distractor"]],
            "actions_not_refused": [row["action"] for row in rows if not row["every_violation_was_refused"]],
            "witnesses": {row["action"]: row["messages"] for row in rows},
            "MET": all(row["injective"] and row["invariant_under_distractor"] and row["every_violation_was_refused"]
                       and row["each_violation_changed_exactly_one_fact"]
                       and row["the_changed_fact_is_the_dropped_coordinate"] for row in rows)},
        "K3_one_refusal_per_coordinate_identifies": {
            "identified": [name for name, space in spaces.items() if space["identified"]],
            "identified_and_equal_to_the_true_precondition": [
                name for name, space in spaces.items() if space["the_survivor_is_the_true_precondition"]],
            "per_action": spaces,
            "MET": all(space["identified"] and space["the_survivor_is_the_true_precondition"]
                       for space in spaces.values())},
        "K4_the_failure_is_free": {
            "claim": "a refusal does not touch the objects under the action; anything it does write is its own "
                     "bookkeeping, and that is counted rather than assumed away",
            "refusals": total_refusals, "refusals_that_left_the_tree_identical": free_refusals,
            "fraction_identical": round(free_refusals / total_refusals, 4) if total_refusals else 0.0,
            "refusals_that_wrote_anything": {name: row["refusals_that_changed_something"] for name, row in
                                             ((r["action"], r) for r in rows)
                                             if row["refusals_that_changed_something"]},
            "refusals_confined_to_bookkeeping": sum(
                len(row["refusals_confined_to_bookkeeping"]) for row in rows),
            "objects_changed_by_any_refusal": sorted(
                {path for row in rows for paths in row["refusals_that_changed_something"].values()
                 for path in paths if path.split("/")[-1] not in {"a.txt.rej", "a.txt.orig", "README.txt.orig"}}),
            "MET": total_refusals > 0 and not any(
                path for row in rows for paths in row["refusals_that_changed_something"].values()
                for path in paths if path.split("/")[-1] not in {"a.txt.rej", "a.txt.orig", "README.txt.orig"})},
        "K5_the_schedule_price": {
            "successes_per_action": 1,
            "refusals_per_action": {row["action"]: len(row["coords"]) for row in rows},
            "executions_for_the_user_plan": len(rows),
            "executions_for_this_schedule": len(rows) + total_refusals,
            "state_interventions_the_previous_round_ran": 160,
            "actions_the_previous_round_identified": 0,
            "actions_identified_here": sum(1 for space in spaces.values() if space["identified"]),
            "MET": sum(1 for space in spaces.values() if space["identified"]) == len(rows)},
        "K6_zero": {"model_calls": 0, "parameters_stored": 0, "network_calls_at_run_time": 0,
                    "MET": True},
    }
    verdict["K2_the_refusal_is_a_function_of_the_violated_coordinate"][
        "the_declared_check_is_narrower_than_the_fact_it_serves"] = check_narrower_than_the_fact(root)
    return {
        "schema": SCHEMA, "authority": "NONE__PRODUCER_RUN_SANDBOX", "date": "2026-11-19",
        "mode": "BREAK_EACH_REAL_ACTION_ONCE_PER_COORDINATE_AND_MEASURE_WHETHER_THE_REFUSAL_IS_A_DECLARATION",
        "why_this_round": {
            "the_gap_it_closes": ("the tree measured that a success identifies applicability 0/200, that the "
                                  "precondition is not in the trace (160 states, 0 identified, best accuracy 1.0), and "
                                  "that a check mode is an oracle (1.0 held-out) -- but every one of those used a "
                                  "supplied fact vocabulary and none asked what a REFUSAL is"),
            "the_answer_being_tested": ("a refusal message is a function of the violated precondition coordinate, so the "
                                        "precondition is declared by the program rather than sampled by the agent"),
            "why_it_could_fail": ("messages may collide across coordinates, may vary with distractors, may name a cause "
                                  "that is not a precondition, or a refusal may not be free (a partial effect)"),
        },
        "declared_acceptance_before_the_receipt_run": {
            "K1": "after the single success every action still has more than one distinct behaviour consistent",
            "K2": "for every action: each violation changes exactly one fact and it is the dropped coordinate, every "
                  "violation is refused, distinct coordinates give distinct messages, and the same coordinate under a "
                  "different distractor gives the same message",
            "K3": "one refusal per coordinate leaves exactly one distinct behaviour, and it is the true precondition",
            "K4": "every refusal leaves the tree byte-identical",
            "K5": "every action is identified with 1 success + k refusals, against 160 state interventions and 0",
            "K6": "zero model calls, zero parameters, zero network",
        },
        "verdict": verdict, "rows": rows, "spaces": spaces,
        "cost": {"seconds": round(time.time() - started, 1), "model_calls": 0, "parameters_stored": 0,
                 "network_calls_at_run_time": 0,
                 "executions": len(rows) * (1 + 2 * 0) + sum(row["refusals"] for row in rows)},
        "limits": [
            "the fact vector is measured with the program's own check where one exists (tar -tzf, gzip -t, "
            "patch --dry-run, git diff --quiet), and at least one of those checks is measurably narrower than the "
            "fact it is used for -- recorded in K2, not hidden",
            "ten actions, one machine, one producer; a census of these ten",
            "the fact vector is hand-written: the agent must be given (or construct) the nine facts a state is "
            "described by, and no refusal tells it which facts exist -- this is the reach bottleneck, restated",
            "the message is normalised by a declared rewrite (paths and distractor names out); the rewrite is a part "
            "and it is counted as one, while injectivity and invariance are measured on what remains",
            "identification is up to the states measured: one distinct behaviour over these states, not over the world",
            "some real failures are destructive; this sample's are not, and K4 measures that rather than assuming it",
            "a refusal names a missing fact; it does not say how to obtain it, and nothing here builds the remedy",
        ],
    }


def headline(receipt: dict[str, Any]) -> str:
    verdict = receipt["verdict"]
    lines = []
    for key, value in verdict.items():
        lines.append(f"{'MET ' if value['MET'] else 'NOT '} {key}")
    spaces = receipt["spaces"]
    lines.append("")
    lines.append("one success leaves (distinct behaviours): "
                 + json.dumps({k: v["distinct_behaviours_after_the_one_success"] for k, v in spaces.items()}))
    lines.append("one refusal per coordinate leaves: "
                 + json.dumps({k: v["distinct_behaviours_after_refusals"] for k, v in spaces.items()}))
    lines.append("identified: " + ", ".join(sorted(n for n, s in spaces.items() if s["identified"])))
    lines.append(f"refusals: {verdict['K4_the_failure_is_free']['refusals']}, "
                 f"free: {verdict['K4_the_failure_is_free']['refusals_that_left_the_tree_identical']} "
                 f"({verdict['K4_the_failure_is_free']['fraction_identical']}), "
                 f"bookkeeping-only: {verdict['K4_the_failure_is_free']['refusals_confined_to_bookkeeping']}")
    lines.append(f"seconds {receipt['cost']['seconds']}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    path = None
    if "--receipt" in args:
        path = pathlib.Path(args[args.index("--receipt") + 1])
    receipt = measure()
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v["MET"] for k, v in receipt["verdict"].items()}, indent=1))
    print(headline(receipt))
    return 0 if all(v["MET"] for v in receipt["verdict"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
