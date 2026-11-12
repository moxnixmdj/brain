#!/usr/bin/env python3
"""What does first contact with an environment NOBODY HERE WROTE actually cost?

Why this file exists
--------------------
Every number this repository has for "instant learning in a new environment" comes from an
environment the same session wrote: five constructed families (lock, toggles, accumulator,
grid, modulo counter) and a small filesystem. The record already says where that leads --
"the probe re-created the instance it taught", "an environment unsolvable by construction",
"every ceiling is authored by the operator". An author cannot hold out what he designed.

ARC-AGI-3 is the public instrument built for exactly this question: 25 public interactive
games, no instructions, a human baseline action count per level, and a score that is the
SQUARE of (human actions / agent actions). It measures how cheaply an agent acquires a
skill it has never seen, which is the claim, and nothing in it was written here.

What is measured
----------------
For each public game, level by level, with a per-level action budget of K x the human
baseline (the official benchmarking agent uses the same shape of budget):

    random       uniform choice among the offered actions (control: what luck buys)
    as_is        `environment_learning_v1.learn_model` -- the machine's existing first
                 contact: random walks of 1..6 actions from reset
    nearest      `systematic_exploration_v1`, experiment where you stand
    nearest+prior  ... and schedule untried actions by measured effect rate
    shallowest   ... breadth first from the level start

Every arm sees the same thing: the 64x64 frame, the offered action ids, and, when clicking
is offered, one click target per same-coloured connected region of the frame. No arm is
told what anything means, where the goal is, or that a level exists; a level ends when the
environment's own `levels_completed` counter moves.

The score is NOT computed here. Each arm plays through the official `arc_agi` toolkit in
OFFLINE mode and the toolkit's own scorecard does the arithmetic. This file's tally of
levels and actions is compared with the scorecard's and a mismatch is an instrument fault
that stops the run -- a number two counters disagree about is not reported.

What the instrument checks about itself
---------------------------------------
A near-zero score is only worth reading if the adapter can reach what the game responds to.
`--check-clicks` takes, at each game's first state, every click the ENGINE lists as valid and
every target the adapter offers, each from a fresh copy of the game, and reports whether each
listed click's outcome is also produced by one of the adapter's targets. It exits non-zero if
the one-click-per-region abstraction hides a click the engine lists. It is made at the first
state only, and nothing it reads is shown to an arm.

What this is not
----------------
  * Not a leaderboard entry. The public games are a practice set, the runtime here is not
    the competition's, and the toolkit was installed on Python 3.11 with
    `--ignore-requires-python` (it declares >=3.12). That deviation is written into every
    result this file emits.
  * Not evidence about the private set, GUI use, or coding.
  * Not a capability receipt. `authority: NONE`, sandbox measurement, producer-run.

Usage (the toolkit and the games are NOT vendored; see `--help` for where they come from)

    python3 canonical/tools/arc_agi_3_public_exploration_measure_v1.py \
        --environments-dir /path/to/environment_files --multipliers 2 5 20 --out result.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
import os
import platform
import random
import sys
import time
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "PROJECT_BRAIN_ARC_AGI_3_PUBLIC_EXPLORATION_MEASUREMENT_V1"
ARMS = ("random", "as_is", "nearest", "nearest+prior", "shallowest")
SEEDED_ARMS = ("random", "as_is")
AS_IS_MAX_DEPTH = 6  # the default `max_depth` of `environment_learning_v1.learn_model`


class _Stop(Exception):
    """The level ended or its budget is spent. Raised from inside `act` so no arm overruns."""


# --------------------------------------------------------------------------- #
# what a frame offers
# --------------------------------------------------------------------------- #
def click_targets(grid: Sequence[Sequence[int]]) -> list[tuple[int, int, int]]:
    """One (x, y, colour) per 4-connected same-coloured region, in scan order.

    The point chosen is the region's own cell nearest its centroid, so it is always inside
    the region even when the region is a ring or an L.
    """
    height = len(grid)
    width = len(grid[0]) if height else 0
    seen = [[False] * width for _ in range(height)]
    out: list[tuple[int, int, int]] = []
    for y0 in range(height):
        row_seen = seen[y0]
        for x0 in range(width):
            if row_seen[x0]:
                continue
            colour = grid[y0][x0]
            stack = [(x0, y0)]
            seen[y0][x0] = True
            cells: list[tuple[int, int]] = []
            while stack:
                x, y = stack.pop()
                cells.append((x, y))
                if x > 0 and not seen[y][x - 1] and grid[y][x - 1] == colour:
                    seen[y][x - 1] = True
                    stack.append((x - 1, y))
                if x + 1 < width and not seen[y][x + 1] and grid[y][x + 1] == colour:
                    seen[y][x + 1] = True
                    stack.append((x + 1, y))
                if y > 0 and not seen[y - 1][x] and grid[y - 1][x] == colour:
                    seen[y - 1][x] = True
                    stack.append((x, y - 1))
                if y + 1 < height and not seen[y + 1][x] and grid[y + 1][x] == colour:
                    seen[y + 1][x] = True
                    stack.append((x, y + 1))
            cx = sum(c[0] for c in cells) / len(cells)
            cy = sum(c[1] for c in cells) / len(cells)
            px, py = min(cells, key=lambda c: ((c[0] - cx) ** 2 + (c[1] - cy) ** 2, c[1], c[0]))
            out.append((px, py, int(colour)))
    return out


class Observation:
    """What the adapter hands to a learner. Deliberately small: a frame and what it offers."""

    __slots__ = ("level", "frame_bytes", "state_name", "offered", "key")

    def __init__(self, level: int, frame_bytes: bytes, state_name: str,
                 offered: tuple[str, ...]) -> None:
        self.level = level
        self.frame_bytes = frame_bytes
        self.state_name = state_name
        self.offered = offered
        self.key = hashlib.sha1(b"%d|" % level + frame_bytes).hexdigest()[:20]

    # `environment_learning_v1.state_key` identifies a hashable observation by `str()`, so the
    # existing learner is given the same identity the new one is, not a memory address.
    def __str__(self) -> str:
        return self.key

    __repr__ = __str__

    def __hash__(self) -> int:
        return hash(self.key)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Observation) and other.key == self.key


def action_class(action: str) -> str:
    """Effects are pooled per key press, and per COLOUR of the region clicked."""
    if action.startswith("C:"):
        return "C:" + action.rsplit(":", 1)[1]
    return action


class LevelEnv:
    """One level of one game as reset() / act() / state(). Every act is a real game action."""

    def __init__(self, env: Any, budget: int, *, raise_on_level_done: bool) -> None:
        from arcengine import GameAction, GameState

        self._GameAction, self._GameState = GameAction, GameState
        self.env = env
        self.budget = int(budget)
        self.raise_on_level_done = raise_on_level_done
        first = env.observation_space
        self.level = int(first.levels_completed)
        self.actions_taken = 0
        self.resets = 0
        self.deaths = 0
        self.done = False
        self._dirty = False  # an action was taken since the level started or was last reset
        self._observation = self._wrap(first)
        self.unique_keys = {self._observation.key}

    # -- observation ------------------------------------------------------- #
    def _wrap(self, raw: Any) -> Observation:
        import numpy as np

        frame = np.asarray(raw.frame[-1])
        offered: list[str] = []
        for action_id in raw.available_actions:
            if int(action_id) == 6:
                offered.extend("C:%d:%d:%d" % t for t in click_targets(frame.tolist()))
            else:
                offered.append("A%d" % int(action_id))
        return Observation(int(raw.levels_completed), frame.tobytes(), raw.state.name,
                           tuple(offered))

    def state(self) -> Observation:
        return self._observation

    def offered(self, observation: Observation) -> tuple[str, ...]:
        return observation.offered

    def is_dead(self, observation: Observation) -> bool:
        return observation.state_name == "GAME_OVER"

    def is_goal(self, observation: Observation) -> bool:
        return observation.level > self.level or observation.state_name == "WIN"

    # -- action ------------------------------------------------------------ #
    def reset(self) -> None:
        # The engine turns a reset with no action since the last one into a FULL game reset,
        # back to level 1. A learner that resets twice in a row must not pay for that.
        if not self._dirty or self.done:
            return
        # Measured 2026-11-11 against the toolkit's own scorecard: a level reset is COUNTED AS
        # AN ACTION. This file's first tally treated resets as free and the cross-check below
        # refused the run (140 != 110 on ls20). A reset therefore spends budget like any act.
        if self.actions_taken >= self.budget:
            raise _Stop("BUDGET")
        raw = self.env.reset()
        self.resets += 1
        self.actions_taken += 1
        self._dirty = False
        self._observation = self._wrap(raw)

    def act(self, action: Any) -> None:
        if self.done:
            raise _Stop("LEVEL_DONE")
        if self.actions_taken >= self.budget:
            raise _Stop("BUDGET")
        if self.is_dead(self._observation):
            self.reset()
        text = str(action)
        if text.startswith("C:"):
            _, x, y, _ = text.split(":")
            raw = self.env.step(self._GameAction.ACTION6, data={"x": int(x), "y": int(y)})
        else:
            raw = self.env.step(self._GameAction.from_id(int(text[1:])))
        self.actions_taken += 1
        self._dirty = True
        self._observation = self._wrap(raw)
        self.unique_keys.add(self._observation.key)
        if self.is_dead(self._observation):
            self.deaths += 1
        if self.is_goal(self._observation):
            self.done = True
            if self.raise_on_level_done:
                raise _Stop("LEVEL_DONE")


# --------------------------------------------------------------------------- #
# the arms
# --------------------------------------------------------------------------- #
def _play_random(level_env: LevelEnv, seed: int) -> dict[str, Any]:
    rng = random.Random(seed)
    try:
        while True:
            observation = level_env.state()
            if level_env.is_dead(observation):
                level_env.reset()
                observation = level_env.state()
            level_env.act(rng.choice(observation.offered))
    except _Stop:
        pass
    return {}


def _play_as_is(level_env: LevelEnv, seed: int) -> dict[str, Any]:
    from canonical.runtime import environment_learning_v1 as el

    # `learn_model` takes one fixed action list, so it gets what the level's first frame offers.
    actions = list(level_env.state().offered)
    trial = 0
    try:
        while True:
            el.learn_model(level_env, actions, budget=1, seed=seed * 100003 + trial,
                           max_depth=AS_IS_MAX_DEPTH)
            trial += 1
    except _Stop:
        pass
    return {"trials": trial}


def _play_systematic(level_env: LevelEnv, order: str, effect_prior: bool) -> dict[str, Any]:
    from canonical.runtime import systematic_exploration_v1 as sx

    try:
        result = sx.explore_to_goal(
            level_env, [], is_goal=level_env.is_goal, action_budget=level_env.budget,
            actions_of=level_env.offered, is_dead=level_env.is_dead,
            key_of=lambda observation: observation.key, action_class=action_class,
            effect_prior=effect_prior, order=order, reset_cost=1, include_model=False)
    except _Stop:  # must not happen: the explorer charges a reset exactly as the adapter does
        raise SystemExit("INSTRUMENT_FAULT__EXPLORER_AND_ADAPTER_DISAGREE_ABOUT_THE_BUDGET")
    if result["budget_spent"] != level_env.actions_taken:
        raise SystemExit("INSTRUMENT_FAULT__EXPLORER_COST_%s_ADAPTER_COST_%s" % (
            result["budget_spent"], level_env.actions_taken))
    keep = ("status", "state_count", "transition_count", "experiment_acts", "travel_acts",
            "surprises", "revisit_rate", "self_loops", "resets", "exhausted")
    return {k: result.get(k) for k in keep}


def play_game(arc: Any, game_id: str, card_id: str, arm: str, multiplier: float,
              seed: int) -> dict[str, Any]:
    env = arc.make(game_id, scorecard_id=card_id, seed=0)
    baseline = list(env.info.baseline_actions or [])
    levels: list[dict[str, Any]] = []
    while True:
        raw = env.observation_space
        level = int(raw.levels_completed)
        if raw.state.name == "WIN" or level >= len(baseline):
            break
        budget = math.ceil(baseline[level] * multiplier)
        level_env = LevelEnv(env, budget, raise_on_level_done=arm in SEEDED_ARMS)
        if arm == "random":
            detail = _play_random(level_env, seed + 7919 * level)
        elif arm == "as_is":
            detail = _play_as_is(level_env, seed + 7919 * level)
        else:
            detail = _play_systematic(level_env, "shallowest" if arm == "shallowest" else "nearest",
                                      arm.endswith("+prior"))
        row = {"level": level, "baseline": baseline[level], "budget": budget,
               "actions": level_env.actions_taken, "completed": level_env.done,
               "resets": level_env.resets, "deaths": level_env.deaths,
               "unique_frames": len(level_env.unique_keys),
               "offered_at_start": len(level_env.state().offered) if not level_env.done else None}
        row.update({"x_" + k: v for k, v in detail.items()})
        levels.append(row)
        if not level_env.done:
            break
    return {"game_id": game_id, "tags": list(env.info.tags or []), "baseline": baseline,
            "levels_completed": sum(r["completed"] for r in levels),
            "actions": sum(r["actions"] for r in levels), "levels": levels}


# --------------------------------------------------------------------------- #
# the run
# --------------------------------------------------------------------------- #
def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def environment_manifest(environments_dir: Path) -> dict[str, Any]:
    files = sorted(p for p in environments_dir.rglob("*") if p.is_file()
                   and p.suffix in (".py", ".json") and "__pycache__" not in p.parts)
    digest = hashlib.sha256()
    listing = {}
    for p in files:
        h = _sha256(p)
        listing[str(p.relative_to(environments_dir))] = h
        digest.update(str(p.relative_to(environments_dir)).encode() + b"\0" + h.encode() + b"\n")
    return {"files": len(files), "tree_sha256": digest.hexdigest(), "sha256": listing}


def run(environments_dir: str, multipliers: Sequence[float], seeds: Sequence[int],
        arms: Sequence[str], games: Sequence[str] | None = None,
        progress: Callable[[str], None] | None = None) -> dict[str, Any]:
    logging.disable(logging.CRITICAL)
    import arc_agi
    import arcengine
    from arc_agi import Arcade, OperationMode

    say = progress or (lambda _text: None)
    arc = Arcade(operation_mode=OperationMode.OFFLINE, environments_dir=environments_dir)
    infos = sorted(arc.get_environments(), key=lambda e: e.game_id)
    if games:
        infos = [e for e in infos if any(e.game_id.startswith(g) for g in games)]
    if not infos:
        raise SystemExit("NO_ENVIRONMENTS_FOUND_IN " + environments_dir)

    cells = []
    for multiplier in multipliers:
        for arm in arms:
            for seed in (seeds if arm in SEEDED_ARMS else (0,)):
                started = time.time()
                card_id = arc.create_scorecard()
                played = [play_game(arc, e.game_id, card_id, arm, multiplier, seed) for e in infos]
                card = arc.close_scorecard(card_id)
                official = {env.id: env for env in card.environments}
                faults = []
                for row in played:
                    theirs = official.get(row["game_id"])
                    if theirs is None:
                        faults.append("%s:MISSING_FROM_SCORECARD" % row["game_id"])
                        continue
                    row["official_score"] = round(float(theirs.score), 4)
                    if int(theirs.levels_completed) != row["levels_completed"]:
                        faults.append("%s:LEVELS %s!=%s" % (row["game_id"], theirs.levels_completed,
                                                            row["levels_completed"]))
                    if int(theirs.actions) != row["actions"]:
                        faults.append("%s:ACTIONS %s!=%s" % (row["game_id"], theirs.actions,
                                                             row["actions"]))
                if faults:
                    raise SystemExit("INSTRUMENT_FAULT__TALLY_DISAGREES_WITH_OFFICIAL_SCORECARD "
                                     + "; ".join(faults))
                cell = {
                    "arm": arm, "budget_multiplier": multiplier, "seed": seed,
                    "official_score": round(float(card.score), 4),
                    "games": len(played),
                    "games_with_a_level_completed": sum(r["levels_completed"] > 0 for r in played),
                    "levels_completed": sum(r["levels_completed"] for r in played),
                    "levels_total": sum(len(r["baseline"]) for r in played),
                    "actions": sum(r["actions"] for r in played),
                    "duration_s": round(time.time() - started, 2),
                    "per_game": played,
                }
                cells.append(cell)
                say("K=%-5g %-14s seed=%d  score=%7.4f  levels=%3d/%d  games>0=%2d/%d  %6.1fs" % (
                    multiplier, arm, seed, cell["official_score"], cell["levels_completed"],
                    cell["levels_total"], cell["games_with_a_level_completed"], cell["games"],
                    cell["duration_s"]))

    summary = []
    for multiplier in multipliers:
        for arm in arms:
            mine = [c for c in cells if c["arm"] == arm and c["budget_multiplier"] == multiplier]
            scores = [c["official_score"] for c in mine]
            levels = [c["levels_completed"] for c in mine]
            summary.append({
                "budget_multiplier": multiplier, "arm": arm, "runs": len(mine),
                "official_score_mean": round(sum(scores) / len(scores), 4),
                "official_score_min": min(scores), "official_score_max": max(scores),
                "levels_completed_mean": round(sum(levels) / len(levels), 2),
                "levels_completed_min": min(levels), "levels_completed_max": max(levels),
                "levels_total": mine[0]["levels_total"],
            })

    return {
        "schema": SCHEMA,
        "authority": "NONE",
        "measurement_class": "MEASURED_SANDBOX__PRODUCER_RUN__NOT_INDEPENDENT_VERIFICATION",
        "date_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "instrument": {
            "benchmark": "ARC-AGI-3 public games, played offline through the official toolkit",
            "scoring": "arc_agi toolkit scorecard (per level min(115, (baseline/actions)^2*100), "
                       "level-index weighted, mean over games; a level reset counts as an "
                       "action); not computed by this file",
            "arc_agi_version": getattr(arc_agi, "__version__", None) or _dist_version("arc-agi"),
            "arcengine_version": _dist_version("arcengine"),
            "python": platform.python_version(),
            "deviation": "toolkit declares python>=3.12; installed here with "
                         "--ignore-requires-python on %s" % platform.python_version(),
            "environments": environment_manifest(Path(environments_dir)),
            "games": [e.game_id for e in infos],
        },
        "subject": {
            "model_dependency_count": 0, "trained_parameters": 0, "network_calls": 0,
            "arms": list(arms), "seeds_for_random_arms": list(seeds),
            "as_is_max_depth": AS_IS_MAX_DEPTH,
            "what_every_arm_is_given": "the 64x64 frame, the offered action ids, and one click "
                                       "target per same-coloured 4-connected region",
            "what_no_arm_is_given": "rules, goals, instructions, level structure, other levels",
        },
        "summary": summary,
        "cells": cells,
    }


def _outcome(raw: Any) -> str:
    """A frame, its state name and its level as one comparable key."""
    frame = raw.frame[-1]
    rows = frame.tolist() if hasattr(frame, "tolist") else frame
    cells = json.dumps([[int(v) for v in row] for row in rows], separators=(",", ":"))
    return "%s|%s|%d" % (hashlib.sha1(cells.encode()).hexdigest()[:16], raw.state.name,
                         int(raw.levels_completed))


def click_abstraction_check(
    arc: Any, game_ids: Sequence[str], *, click: Callable[[Any, int, int], Any],
    targets_of: Callable[[Sequence[Sequence[int]]], Sequence[tuple[int, int, int]]] = click_targets,
) -> dict[str, Any]:
    """Does one click per same-coloured region hide anything the engine says is clickable?

    At the first state of each game that offers clicking, every click the ENGINE lists as valid
    is taken from a fresh copy of the game, and so is every target the adapter offers. A listed
    click is covered when the frame, state and level it leads to are also reached by one of the
    adapter's targets. First state only: what the abstraction hides later is not examined.
    """
    per_game = []
    for game_id in game_ids:
        first = arc.make(game_id, seed=0)
        raw = first.observation_space
        if 6 not in [int(a) for a in raw.available_actions]:
            continue
        frame = raw.frame[-1]
        grid = frame.tolist() if hasattr(frame, "tolist") else frame
        try:
            listed = sorted({(int(a.data["x"]), int(a.data["y"]))
                             for a in first._game._get_valid_clickable_actions()})
        except Exception:  # the engine's own list is private API: absent is reported, not guessed
            listed = None
        targets = [(int(x), int(y)) for x, y, _colour in targets_of(grid)]

        def outcome_of(point: tuple[int, int]) -> str:
            return _outcome(click(arc.make(game_id, seed=0), point[0], point[1]))

        reached = {outcome_of(point) for point in targets}
        listed_outcomes = [outcome_of(point) for point in (listed or [])]
        per_game.append({
            "game": game_id.split("-")[0],
            "engine_list_available": listed is not None,
            "engine_listed_clicks": len(listed or []),
            "engine_distinct_outcomes": len(set(listed_outcomes)),
            "adapter_targets": len(targets),
            "adapter_distinct_outcomes": len(reached),
            "engine_listed_clicks_covered": sum(o in reached for o in listed_outcomes),
        })
    listed_total = sum(g["engine_listed_clicks"] for g in per_game)
    covered = sum(g["engine_listed_clicks_covered"] for g in per_game)
    if listed_total == 0:
        status = "NOT_CHECKED__THE_ENGINE_LISTED_NO_CLICK"
    elif covered == listed_total:
        status = "PASS__EVERY_CLICK_THE_ENGINE_LISTS_IS_REACHED_BY_AN_ADAPTER_TARGET"
    else:
        status = "FAULT__THE_CLICK_ABSTRACTION_HIDES_A_CLICK_THE_ENGINE_LISTS"
    return {"scope": "FIRST_STATE_OF_EACH_GAME_ONLY", "status": status,
            "games_offering_clicks": len(per_game),
            "games_where_the_engine_lists_clicks": sum(g["engine_listed_clicks"] > 0
                                                       for g in per_game),
            "engine_listed_clicks": listed_total, "engine_listed_clicks_covered": covered,
            "per_game": per_game}


def digest(results: Sequence[tuple[str, dict[str, Any]]]) -> dict[str, Any]:
    """Several full results reduced to one small record that is worth committing.

    Deterministic and lossy on purpose: every run keeps its official score, its level and action
    totals and the exact levels it completed; the per-level rows of levels that were not completed
    are folded into a count of why they stopped. Each input is named by the sha256 of its bytes,
    and inputs measured with a different toolkit or on different game files are refused rather
    than mixed.
    """
    if not results:
        raise SystemExit("DIGEST_NEEDS_AT_LEAST_ONE_RESULT")
    first = results[0][1]
    pinned = ("arc_agi_version", "arcengine_version", "python")
    sources, runs, summary = [], [], []
    for sha, result in results:
        if result.get("schema") != SCHEMA:
            raise SystemExit("DIGEST_INPUT_IS_NOT_A_RESULT_OF_THIS_TOOL")
        here, there = result["instrument"], first["instrument"]
        if (any(here.get(k) != there.get(k) for k in pinned)
                or here["environments"]["tree_sha256"] != there["environments"]["tree_sha256"]
                or result["subject"]["as_is_max_depth"] != first["subject"]["as_is_max_depth"]):
            raise SystemExit("DIGEST_INPUTS_WERE_NOT_MEASURED_WITH_THE_SAME_INSTRUMENT")
        sources.append({"sha256": sha, "date_utc": result["date_utc"],
                        "budget_multipliers": sorted({c["budget_multiplier"]
                                                      for c in result["cells"]})})
        summary.extend(result["summary"])
        for cell in result["cells"]:
            completed, stopped = [], {}
            for game in cell["per_game"]:
                for row in game["levels"]:
                    if row["completed"]:
                        completed.append("%s:L%d:%d/%d" % (game["game_id"].split("-")[0],
                                                           row["level"], row["actions"],
                                                           row["baseline"]))
                    else:
                        why = row.get("x_status") or (
                            "BUDGET_SPENT" if row["actions"] >= row["budget"] else "STOPPED_EARLY")
                        stopped[why] = stopped.get(why, 0) + 1
            runs.append({"arm": cell["arm"], "budget_multiplier": cell["budget_multiplier"],
                         "seed": cell["seed"], "official_score": cell["official_score"],
                         "levels_completed": cell["levels_completed"],
                         "levels_total": cell["levels_total"], "actions": cell["actions"],
                         "completed_levels_as_game_level_actions_over_human": completed,
                         "levels_not_completed_by_reason": dict(sorted(stopped.items()))})
    instrument = dict(first["instrument"])
    environments = dict(instrument["environments"])
    environments.pop("sha256", None)  # the tree hash names the files; the per-file list is in the inputs
    instrument["environments"] = environments
    return {
        "schema": SCHEMA + "_DIGEST",
        "authority": "NONE",
        "measurement_class": "MEASURED_SANDBOX__PRODUCER_RUN__NOT_INDEPENDENT_VERIFICATION",
        "digest_of": sources,
        "instrument": instrument,
        "subject": first["subject"] | {"arms": sorted({r["arm"] for r in runs})},
        "human_reference_score": 100.0,
        "summary": summary,
        "runs": runs,
    }


def _dist_version(name: str) -> str | None:
    try:
        from importlib.metadata import version

        return version(name)
    except Exception:
        return None


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        epilog="The toolkit: pip install --ignore-requires-python --no-deps arcengine arc-agi "
               "(plus numpy pydantic flask requests pillow python-dotenv). The games: the "
               "`environment_files/` directory the official toolkit downloads, or a public mirror "
               "of it; its tree hash is recorded in the result.")
    parser.add_argument("--environments-dir", default=None)
    parser.add_argument("--digest-from", nargs="+", default=None, metavar="RESULT_JSON",
                        help="do not play: reduce full results written by --out to one small "
                             "record (written to --out)")
    parser.add_argument("--multipliers", type=float, nargs="+", default=[2.0, 5.0, 20.0])
    parser.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    parser.add_argument("--arms", nargs="+", default=list(ARMS), choices=ARMS)
    parser.add_argument("--games", nargs="*", default=None, help="game id prefixes; default all")
    parser.add_argument("--check-clicks", action="store_true",
                        help="do not play: check the adapter's click abstraction against the "
                             "clicks the engine itself lists as valid (written to --out)")
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)

    if args.digest_from:
        loaded = []
        for name in args.digest_from:
            raw = Path(name).read_bytes()
            loaded.append((hashlib.sha256(raw).hexdigest(), json.loads(raw)))
        record = digest(loaded)
        text = json.dumps(record, indent=1, sort_keys=False) + "\n"
        if args.out:
            Path(args.out).write_text(text)
            print("wrote", args.out)
        else:
            print(text, end="")
        return 0
    if not args.environments_dir:
        parser.error("--environments-dir is required unless --digest-from is given")

    if args.check_clicks:
        logging.disable(logging.CRITICAL)
        from arc_agi import Arcade, OperationMode
        from arcengine import GameAction

        arc = Arcade(operation_mode=OperationMode.OFFLINE,
                     environments_dir=args.environments_dir)
        ids = sorted(e.game_id for e in arc.get_environments())
        if args.games:
            ids = [g for g in ids if any(g.startswith(prefix) for prefix in args.games)]
        check = click_abstraction_check(
            arc, ids, click=lambda env, x, y: env.step(GameAction.ACTION6,
                                                       data={"x": x, "y": y}))
        environments = environment_manifest(Path(args.environments_dir))
        environments.pop("sha256", None)
        record = {
            "schema": SCHEMA + "_CLICK_ABSTRACTION_CHECK",
            "authority": "NONE",
            "measurement_class": "MEASURED_SANDBOX__PRODUCER_RUN__NOT_INDEPENDENT_VERIFICATION",
            "date_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "instrument": {"arc_agi_version": _dist_version("arc-agi"),
                           "arcengine_version": _dist_version("arcengine"),
                           "python": platform.python_version(),
                           "environments": environments, "games": ids},
            "check": check,
        }
        for row in check["per_game"]:
            print("%-5s engine lists %3d clicks (%3d outcomes)  adapter %3d targets "
                  "(%3d outcomes)  covered %d/%d" % (
                      row["game"], row["engine_listed_clicks"], row["engine_distinct_outcomes"],
                      row["adapter_targets"], row["adapter_distinct_outcomes"],
                      row["engine_listed_clicks_covered"], row["engine_listed_clicks"]))
        print("%s  %d/%d" % (check["status"], check["engine_listed_clicks_covered"],
                             check["engine_listed_clicks"]))
        if args.out:
            Path(args.out).write_text(json.dumps(record, indent=1, sort_keys=False) + "\n")
            print("wrote", args.out)
        return 0 if check["status"].startswith("PASS") else 1

    result = run(args.environments_dir, args.multipliers, args.seeds, args.arms, args.games,
                 progress=lambda text: print(text, flush=True))
    print()
    print("%-6s %-14s %4s %10s %18s %14s" % ("K", "arm", "runs", "score", "score min..max",
                                              "levels mean"))
    for row in result["summary"]:
        print("%-6g %-14s %4d %10.4f %8.4f..%-8.4f %8.2f/%d" % (
            row["budget_multiplier"], row["arm"], row["runs"], row["official_score_mean"],
            row["official_score_min"], row["official_score_max"],
            row["levels_completed_mean"], row["levels_total"]))
    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=1, sort_keys=False) + "\n")
        print("\nwrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
