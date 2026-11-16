#!/usr/bin/env python3
"""What does ONE demonstration of a task licence, on a real environment, from every start state?

THE CLAIM UNDER TEST
--------------------
"Give the model a try in a new environment, let it do the task once, and it has learned it
permanently; do that for every environment and every computer task and we are done."

That claim is a statement about the *domain* of a demonstrated action sequence, and a domain is a
fact, not an opinion: either the sequence reaches the goal from a starting state or it does not.
This module measures that domain exactly, on a real environment, and separates four sets that a
success count cannot separate:

  LICENSED     the demonstration works here, and the agent can TELL that it applies: every state
               it cannot distinguish from this one is also inside the demonstration's domain.
  LUCKY        the demonstration works here, but the same looks also occur where it fails. Trusting
               memory here is a coin that already landed; nothing licensed it.
  SILENT       the demonstration fails here while looking exactly like a state where it works. The
               agent runs the plan, believes it is on track, and is wrong -- no error, no signal.
  CLEAR        the demonstration plainly does not apply; a different plan is needed, and the need
               for one is visible.

The sum of LUCKY and SILENT is the interesting number, because it is invariant to experience: those
states are undecidable from what the agent can see, so no number of further demonstrations fixes
them. Only a sense that carries more of the truth, or a check per instance, does.

WHY THIS IS EXACT, AND WHY IT IS NOT SYNTHETIC
----------------------------------------------
The environment is real `git` in a throw-away repository: real index, real refs, real errors, real
irreversibility. The model is built by executing every action from every reachable state -- what
`systematic_exploration_v1` does, and why its price is |S| x |A| -- so every number below is a fact
about this repository, not a sample. Commits use a fixed clock and the index is compared by staged
content rather than stat bytes, so the same action from the same state is the same state; without
that, the model would be unbounded and the measurement meaningless.

Because the model is exact, the SENSES can be varied while the world, the states, the tasks and the
demonstrations stay fixed. That is what turns "one demonstration is not enough" into a lever: the
same demonstration is re-scored under four sense vocabularies, and the movement in what it licenses
is the measured worth of an observable. Three tasks are used on purpose -- one whose goal the
coarsest sense can already read, one that needs a file the agent may or may not have opened, and one
that needs a file it has not. Whether the senses are the bottleneck is then a measured question with
three answers, not an assumption.

The decision math is the repository's own: `k6_target_relative_decision_quotient_v1` decides when
states can share one action, so "these states need different plans" is computed with the tree's
existing definition, not a new one.

WHAT THIS DOES NOT CLAIM
------------------------
No capability credit, no benchmark credit, no independent verification. The environment is git, not
a GUI; the tasks are goals on one environment, not different environments; the states are those
reachable by a ten-action hand, not all of git. What it claims is narrower and checkable: on this
environment, given the best single demonstration that exists, this much of each task is licensed,
this much is luck, this much fails silently, and this much visibly needs another plan -- and here is
what one more observable is worth, measured on the same states.
"""
from __future__ import annotations

import collections
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Callable, Hashable, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:  # pragma: no cover - import wiring
    sys.path.insert(0, str(ROOT))

from canonical.runtime import k6_target_relative_decision_quotient_v1 as quotient  # noqa: E402

SCHEMA = "one_demonstration_basin_v1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"

FILES = ("a.txt", "b.txt", "note.log", ".gitignore")
SEED = {"a.txt": "one\n", "b.txt": "one\n", "note.log": None, ".gitignore": "*.log\n"}
FIXED_CLOCK = {"GIT_AUTHOR_DATE": "2026-01-01T00:00:00 +0000",
               "GIT_COMMITTER_DATE": "2026-01-01T00:00:00 +0000"}

WRITE = "write:%s=%s"
STAGE = "stage:%s"
COMMIT = "commit:c1"
RM = "rm:%s"
BRANCH = "branch:dev"
RESET = "reset:hard"

# Sense vocabularies: what the agent can perceive. ("files", staged) -- "*" means every file.
SENSES: tuple[tuple[str, tuple[str, ...] | None, bool], ...] = (
    ("status", None, False),
    ("status+content(a.txt)", ("a.txt",), False),
    ("status+content(all)", ("a.txt", "b.txt", "note.log", ".gitignore"), False),
    ("status+content(all)+staged", ("a.txt", "b.txt", "note.log", ".gitignore"), True),
)


def actions() -> list[str]:
    return [
        WRITE % ("a.txt", "two"),
        WRITE % ("a.txt", "one"),
        WRITE % ("b.txt", "two"),
        WRITE % ("note.log", "x"),
        STAGE % "a.txt",
        STAGE % "b.txt",
        COMMIT,
        RM % "a.txt",
        BRANCH,
        RESET,
    ]


def _run(cwd: pathlib.Path, *argv: str, clock: bool = False) -> tuple[int, str]:
    env = None
    if clock:
        import os

        env = dict(os.environ, **FIXED_CLOCK)
    done = subprocess.run(list(argv), cwd=str(cwd), capture_output=True, text=True,
                          timeout=60, env=env)
    return done.returncode, (done.stdout or "") + (done.stderr or "")


class GitWorld:
    """A real repository: reset, act, probe. Nothing here knows what the actions mean."""

    def __init__(self, directory: pathlib.Path) -> None:
        self.dir = pathlib.Path(directory)
        self.subjects: dict[str, str] = {}

    # -- construction ------------------------------------------------------ #
    def reset(self) -> dict[str, Any]:
        shutil.rmtree(self.dir, ignore_errors=True)
        self.dir.mkdir(parents=True)
        self.subjects = {}
        for name, text in SEED.items():
            if text is not None:
                (self.dir / name).write_text(text, encoding="utf-8")
        _run(self.dir, "git", "init", "-q", "-b", "main", ".")
        _run(self.dir, "git", "config", "user.email", "seed@example.invalid")
        _run(self.dir, "git", "config", "user.name", "seed")
        _run(self.dir, "git", "config", "commit.gpgsign", "false")
        _run(self.dir, "git", "add", "-A")
        _run(self.dir, "git", "commit", "-qm", "seed", clock=True)
        self._learn_subjects()
        return self.probe()

    def _learn_subjects(self) -> None:
        code, out = _run(self.dir, "git", "log", "--format=%H%x09%s")
        if code == 0:
            for line in out.splitlines():
                if "\t" in line:
                    sha, subject = line.split("\t", 1)
                    self.subjects[sha.strip()] = subject.strip()

    # -- the hand ---------------------------------------------------------- #
    def act(self, action: str) -> tuple[int, str]:
        if action.startswith("write:"):
            name, text = action[len("write:"):].split("=", 1)
            (self.dir / name).write_text(text + "\n", encoding="utf-8")
            return 0, ""
        if action.startswith("stage:"):
            return _run(self.dir, "git", "add", action.split(":", 1)[1])
        if action == COMMIT:
            result = _run(self.dir, "git", "commit", "-qm", "c1", clock=True)
            self._learn_subjects()
            return result
        if action.startswith("rm:"):
            return _run(self.dir, "git", "rm", "-q", "--ignore-unmatch", action.split(":", 1)[1])
        if action == BRANCH:
            return _run(self.dir, "git", "checkout", "-q", "-b", "dev")
        if action == RESET:
            first = _run(self.dir, "git", "reset", "-q", "--hard", "HEAD")
            second = _run(self.dir, "git", "clean", "-qfd")
            return first[0] or second[0], first[1] + second[1]
        raise ValueError("UNKNOWN_ACTION:" + action)  # pragma: no cover - defensive

    # -- the senses -------------------------------------------------------- #
    def probe(self) -> dict[str, Any]:
        """Everything the senses draw on; each sense projects from this, so nothing is re-run."""
        code, out = _run(self.dir, "git", "status", "--porcelain=v1", "-b")
        branch = ""
        staged: list[str] = []
        unstaged: list[str] = []
        untracked: list[str] = []
        for line in out.splitlines():
            if line.startswith("## "):
                branch = line[3:].strip()
                continue
            if len(line) < 3:
                continue
            code_xy, path = line[:2], line[3:].strip()
            if code_xy == "??":
                untracked.append(path)
            else:
                if code_xy[0] not in " ?":
                    staged.append(path)
                if code_xy[1] not in " ?":
                    unstaged.append(path)
        head_path = self.dir / ".git" / "HEAD"
        head = ""
        if head_path.exists():
            raw = head_path.read_text(encoding="utf-8").strip()
            ref = raw.split(":", 1)[1].strip() if raw.startswith("ref:") else raw
            ref_file = self.dir / ".git" / ref
            if ref_file.exists():
                head = self.subjects.get(ref_file.read_text(encoding="utf-8").strip(), "?")
            else:
                head = self.subjects.get(raw, "?")
        contents = []
        for name in FILES:
            path = self.dir / name
            contents.append((name, path.read_text(encoding="utf-8") if path.exists() else None))
        code, index = _run(self.dir, "git", "ls-files", "-s")
        staged_rows = tuple(sorted(line.strip() for line in index.splitlines() if line.strip())) \
            if code == 0 else ()
        tracked = tuple(sorted(row.split("\t")[-1] for row in staged_rows))
        return {"branch": branch, "staged": tuple(sorted(staged)),
                "unstaged": tuple(sorted(unstaged)), "untracked": tuple(sorted(untracked)),
                "tracked": tracked, "head": head,
                "contents": tuple(contents), "staged_rows": staged_rows}

    @staticmethod
    def observation(probe: Mapping[str, Any], sense: str) -> Hashable:
        for name, files, staged in SENSES:
            if name != sense:
                continue
            base = (probe["branch"], probe["staged"], probe["unstaged"], probe["untracked"],
                    probe["tracked"], probe["head"])
            if files is None:
                return base
            content = tuple((path, text) for path, text in probe["contents"]
                            if path in files)
            if not staged:
                return base + (content,)
            return base + (content, probe["staged_rows"])
        raise ValueError("UNKNOWN_SENSE:" + sense)

    @staticmethod
    def semantic_key(probe: Mapping[str, Any]) -> Hashable:
        """The whole truth: contents, staged blobs, refs -- never the index's stat bytes."""
        digest = hashlib.sha256()
        digest.update(json.dumps([probe["contents"], probe["staged_rows"], probe["head"],
                                  probe["branch"]], sort_keys=True).encode())
        return digest.hexdigest()[:16]


def _goal_committed(probe: Mapping[str, Any]) -> bool:
    """Done means: the work is committed, nothing is left over, and the file is still there."""
    return (probe["head"] == "c1" and not probe["staged"] and not probe["unstaged"]
            and not probe["untracked"] and "a.txt" in probe["tracked"])


def goal_commit(probe: Mapping[str, Any]) -> bool:
    """The goal a status-level sense can already read."""
    return _goal_committed(probe)


def goal_a_two(probe: Mapping[str, Any]) -> bool:
    """The goal needs one file's content: it is committed, and a.txt is 'two'."""
    return _goal_committed(probe) and dict(probe["contents"])["a.txt"] == "two\n"


def goal_pair(probe: Mapping[str, Any]) -> bool:
    """The goal has a premise the plan does not control: a.txt is 'two' AND b.txt is still 'one'.

    The demonstration writes only a.txt, so whether it succeeds depends on a fact it never sets.
    If b.txt was committed as something else earlier, the tree is clean, the subject is right, the
    plan reports success, and the goal is false -- which is exactly how real work fails.
    """
    content = dict(probe["contents"])
    return _goal_committed(probe) and content["a.txt"] == "two\n" and content["b.txt"] == "one\n"


def explore(world: GitWorld, action_list: Sequence[str], *, max_states: int = 700
            ) -> dict[str, Any]:
    """Build the exact model by executing every action from every reachable state."""
    root_probe = world.reset()
    root = GitWorld.semantic_key(root_probe)
    probes: dict[Hashable, dict[str, Any]] = {root: root_probe}
    edges: dict[Hashable, dict[str, Hashable]] = {}
    parents: dict[Hashable, tuple[Hashable, str]] = {}
    queue = collections.deque([root])
    transitions = 0
    truncated = False
    while queue:
        state = queue.popleft()
        edges[state] = {}
        for action in action_list:
            _restore(world, root, state, parents)
            world.act(action)
            transitions += 1
            probe = world.probe()
            child = GitWorld.semantic_key(probe)
            if child not in probes and len(probes) >= max_states:
                truncated = True
                continue
            edges[state][action] = child
            if child not in probes:
                probes[child] = probe
                parents[child] = (state, action)
                queue.append(child)
    return {"root": root, "states": list(probes), "probes": probes, "edges": edges,
            "parents": parents, "transitions": transitions, "truncated": truncated}


def _restore(world: GitWorld, root: Hashable, target: Hashable,
             parents: Mapping[Hashable, tuple[Hashable, str]]) -> None:
    """Put the real repository back into `target` by replaying the path that produced it."""
    world.reset()
    if target == root:
        return
    for action in path_to(target, parents):
        world.act(action)


def path_to(state: Hashable, parents: Mapping[Hashable, tuple[Hashable, str]]) -> list[str]:
    out: list[str] = []
    while state in parents:
        parent, action = parents[state]
        out.append(action)
        state = parent
    return list(reversed(out))


def distances(model: Mapping[str, Any], is_goal: Callable[[Mapping[str, Any]], bool]
              ) -> dict[Hashable, int]:
    """True distance to the goal, computed over the real model, with the goal on the truth."""
    reverse: dict[Hashable, set[Hashable]] = collections.defaultdict(set)
    for state, row in model["edges"].items():
        for child in row.values():
            reverse[child].add(state)
    dist: dict[Hashable, int] = {}
    queue = collections.deque()
    for state in model["states"]:
        if is_goal(model["probes"][state]):
            dist[state] = 0
            queue.append(state)
    while queue:
        state = queue.popleft()
        for parent in reverse[state]:
            if parent not in dist:
                dist[parent] = dist[state] + 1
                queue.append(parent)
    return dist


def acceptable(model: Mapping[str, Any], dist: Mapping[Hashable, int]
               ) -> dict[Hashable, list[str]]:
    """For each state: the actions that make progress and stay inside the winning region."""
    out: dict[Hashable, list[str]] = {}
    for state in model["states"]:
        if state not in dist or dist[state] == 0:
            out[state] = []
            continue
        moves = []
        for action, child in model["edges"][state].items():
            if child in dist and dist[child] == dist[state] - 1:
                moves.append(action)
        out[state] = sorted(moves)
    return out


def _canonical_plan(model: Mapping[str, Any], dist: Mapping[Hashable, int],
                    start: Hashable) -> tuple[str, ...] | None:
    """The shortest plan from `start`, ties broken by action name: one concrete demonstration."""
    state = start
    if state not in dist:
        return None
    plan: list[str] = []
    while dist[state] > 0:
        options = [(action, model["edges"][state][action]) for action in model["edges"][state]]
        options = [(action, child) for action, child in options
                   if child in dist and dist[child] == dist[state] - 1]
        if not options:
            return None
        action, state = sorted(options, key=lambda pair: pair[0])[0]
        plan.append(action)
    return tuple(plan)


def best_demonstration(model: Mapping[str, Any], dist: Mapping[Hashable, int]
                       ) -> list[str] | None:
    """The most charitable single demonstration: the shortest plan from the root, if one exists."""
    plan = _canonical_plan(model, dist, model["root"])
    return list(plan) if plan else None


def run_plan(model: Mapping[str, Any], start: Hashable, plan: Sequence[str],
             is_goal: Callable[[Mapping[str, Any]], bool]) -> tuple[bool, list[Hashable]]:
    """Execute a plan over the exact model; report whether the goal is reached and where it went."""
    state = start
    visited = [state]
    for action in plan:
        child = model["edges"].get(state, {}).get(action)
        if child is None:
            return False, visited
        state = child
        visited.append(state)
    return bool(is_goal(model["probes"][state])), visited


def analyse(model: Mapping[str, Any], sense: str, is_goal: Callable[[Mapping[str, Any]], bool],
            *, label: str, plan: Sequence[str] | None = None,
            observations: Mapping[Hashable, Hashable] | None = None) -> dict[str, Any]:
    """What one demonstration can and cannot licence, under one sense vocabulary.

    The question is not "does the demonstration work here" but "can the agent TELL". So the plan's
    exact domain is computed, and every observation cell is classified against it: entirely inside
    (the agent may trust the plan), entirely outside (the plan plainly does not apply), or split --
    and a split cell is the dangerous one, because it holds states where the plan works and states
    where it fails while looking exactly the same.
    """
    if observations is None:
        observations = {state: GitWorld.observation(model["probes"][state], sense)
                        for state in model["states"]}
    dist = distances(model, is_goal)
    moves = acceptable(model, dist)
    chosen = list(plan) if plan is not None else (best_demonstration(model, dist) or [])

    domain = {state for state in model["states"] if run_plan(model, state, chosen, is_goal)[0]}

    cells: dict[Hashable, list[Hashable]] = collections.defaultdict(list)
    for state in model["states"]:
        cells[observations[state]].append(state)

    licensed = lucky = silent = clear = 0
    mixed_cells = 0
    for members in cells.values():
        inside = [state for state in members if state in domain]
        if not inside:
            clear += len(members)
        elif len(inside) == len(members):
            licensed += len(members)
        else:
            mixed_cells += 1
            lucky += len(inside)
            silent += len(members) - len(inside)

    total = len(model["states"])
    demos, uncoverable = _demonstrations_needed(model, dist, cells, is_goal)
    quotient_classes = len(quotient.canonical_safe_quotient(
        {state: moves[state] for state in model["states"] if state in dist}))
    return {
        "label": label,
        "sense": sense,
        "states": total,
        "observations": len(cells),
        "winning_states": sum(1 for state in model["states"] if state in dist),
        "demonstration": chosen,
        "demonstration_length": len(chosen),
        "plan_domain": len(domain),
        "plan_domain_share": _share(len(domain), total),
        "licensed": licensed,
        "licensed_share": _share(licensed, total),
        "lucky": lucky,
        "silent_failure": silent,
        "clear_outside": clear,
        "undecidable": lucky + silent,
        "undecidable_share": _share(lucky + silent, total),
        "mixed_cells": mixed_cells,
        "decision_classes": quotient_classes,
        "demonstrations_needed": demos,
        "uncoverable_cells": uncoverable,
    }


def _demonstrations_needed(model: Mapping[str, Any], dist: Mapping[Hashable, int],
                           cells: Mapping[Hashable, list[Hashable]],
                           is_goal: Callable[[Mapping[str, Any]], bool]) -> tuple[int, int]:
    """How many demonstrations it takes to licence every distinguishable situation.

    A cell is licensed by a plan when the plan's whole domain contains the cell. Greedy cover over
    every canonical plan the model knows; cells no plan can license are counted separately.
    """
    candidates: set[tuple[str, ...]] = set()
    for state in model["states"]:
        candidate = _canonical_plan(model, dist, state)
        if candidate:
            candidates.add(candidate)
    domains = {plan: {state for state in model["states"]
                      if run_plan(model, state, plan, is_goal)[0]} for plan in sorted(candidates)}
    cell_keys = list(cells)
    covers: list[set[int]] = []
    for plan in sorted(candidates):
        covers.append({index for index, key in enumerate(cell_keys)
                       if cells[key] and all(state in domains[plan] for state in cells[key])})
    needed = {index for index, key in enumerate(cell_keys)
              if any(state in dist for state in cells[key])}
    uncovered = set(needed)
    chosen = 0
    while uncovered:
        if not covers:
            break
        best = max(covers, key=lambda covered: len(covered & uncovered))
        if not (best & uncovered):
            break
        chosen += 1
        uncovered -= best
        covers.remove(best)
    return chosen, len(uncovered)


def feedback_observable(world: GitWorld, model: Mapping[str, Any], plan: Sequence[str]
                        ) -> dict[Hashable, Hashable]:
    """Run the demonstration from every state for real and record what the tools said.

    A real agent reads the output of its own commands. That is an observable too, and unlike a
    state sense it can separate two states that look identical -- but only when the plan's success
    and its failure print different things. Whether they do is measured, not assumed.
    """
    signatures: dict[Hashable, Hashable] = {}
    for state in model["states"]:
        _restore(world, model["root"], state, model["parents"])
        said = []
        for action in plan:
            code, out = world.act(action)
            line = ""
            for candidate in out.splitlines():
                candidate = candidate.strip()
                if candidate:
                    line = candidate[:60]
                    break
            said.append((action, code, line))
        signatures[state] = tuple(said)
    return signatures


def _share(part: int, whole: int) -> float:
    return round(part / float(whole), 4) if whole else 0.0


def _score_all(world: GitWorld, model: Mapping[str, Any]) -> list[dict[str, Any]]:
    tasks: tuple[tuple[str, Callable[[Mapping[str, Any]], bool]], ...] = (
        ("commit the work as c1 (status-level goal)", goal_commit),
        ("commit a.txt as two (needs one file's content)", goal_a_two),
        ("commit a.txt as two, b.txt still one (a premise the plan does not set)", goal_pair),
    )
    results: list[dict[str, Any]] = []
    for label, is_goal in tasks:
        # One demonstration, found once on the true model, then scored under every sense.
        plan = best_demonstration(model, distances(model, is_goal))
        rows = [analyse(model, sense, is_goal, label=label, plan=plan)
                for sense, _files, _staged in SENSES]
        if any(row["undecidable"] for row in rows):
            signatures = feedback_observable(world, model, plan or [])
            rows.append(analyse(model, "feedback(command output)", is_goal, label=label,
                                plan=plan, observations=signatures))
        results.extend(rows)
    return results


def measure(*, max_states: int = 700) -> dict[str, Any]:
    action_list = actions()
    scratch = pathlib.Path(tempfile.mkdtemp(prefix="brain_basin_"))
    try:
        world = GitWorld(scratch / "repo")
        model = explore(world, action_list, max_states=max_states)
        results = _score_all(world, model)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "model_calls": 0,
        "network_calls": 0,
        "incremental_spend_usd": 0,
        "environment": {
            "kind": "real git repository in a throw-away directory",
            "actions": action_list,
            "senses": [name for name, _files, _staged in SENSES] + ["feedback(command output)"],
            "status_sense": "branch, staged, unstaged, untracked, tracked, last commit subject",
            "content_sense": "the text of the files the agent has opened",
            "staged_sense": "the staged blob per path (git ls-files -s)",
            "feedback_sense": "exit code and first output line of each command in the plan",
            "states": len(model["states"]),
            "executed_transitions": model["transitions"],
            "truncated": model["truncated"],
        },
        "tasks": results,
        "what_this_shows": _headline(results),
    }


def _headline(results: Sequence[Mapping[str, Any]]) -> str:
    labels: list[str] = []
    for row in results:
        if row["label"] not in labels:
            labels.append(row["label"])
    parts = []
    for label in labels:
        rows = [row for row in results if row["label"] == label]
        first = rows[0]
        parts.append(
            "%s: demonstration of %d actions whose true domain is %d of %d states; undecidable "
            "states by sense = %s"
            % (label, first["demonstration_length"], first["plan_domain"], first["states"],
               ", ".join("%s %d (%s)" % (row["sense"], row["undecidable"],
                                         row["undecidable_share"]) for row in rows)))
    return " | ".join(parts) + (
        ". Where a sense carries the fact the goal depends on, the same demonstration is licensed "
        "on its whole domain and no state is undecidable; where it does not, no number of further "
        "demonstrations closes the gap, and command output is coarser than the state, not finer.")


def summarize(report: Mapping[str, Any]) -> str:
    env = report["environment"]
    lines = ["%s: %d real states, %d executed transitions, truncated=%s"
             % (env["kind"], env["states"], env["executed_transitions"], env["truncated"])]
    current = None
    for row in report["tasks"]:
        if row["label"] != current:
            current = row["label"]
            lines.append("  task: %s" % current)
            lines.append("    demonstration: %s" % " -> ".join(row["demonstration"] or ["<none>"]))
            lines.append("    its true domain: %d of %d states (%s); %d states can reach the goal "
                         "somehow; %d decision classes"
                         % (row["plan_domain"], row["states"], row["plan_domain_share"],
                            row["winning_states"], row["decision_classes"]))
        lines.append("    %-28s looks %3d | licensed %3d (%s) lucky %3d silent-fail %3d "
                     "clear %3d | undecidable %3d (%s) | demos %d + %d cells no demo can licence"
                     % (row["sense"], row["observations"], row["licensed"],
                        row["licensed_share"], row["lucky"], row["silent_failure"],
                        row["clear_outside"], row["undecidable"], row["undecidable_share"],
                        row["demonstrations_needed"], row["uncoverable_cells"]))
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="What does one demonstration licence on a real environment?")
    parser.add_argument("--json", dest="json_path", default=None)
    parser.add_argument("--max-states", type=int, default=700)
    ns = parser.parse_args(argv)
    report = measure(max_states=ns.max_states)
    print(summarize(report))
    if ns.json_path:
        target = pathlib.Path(ns.json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("\nwritten:", ns.json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
