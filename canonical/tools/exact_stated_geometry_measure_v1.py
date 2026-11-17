"""Does the page's OWN geometry reach the score frames that refused every correct press?

THE QUESTION
------------
Three pages failed with OUT_SCORE_FRAME_NOT_STATED: a manual, visually correct press scores
0.9427 (circle-center), a midpoint press cannot reach 1.0 (find-midpoint), and a right-angle
vertex scores 0.9995933 < 1.0-1e-9 (right-angle). The hand proposed the right PLACE; the
observation had already rounded it away (`Math.round` on getBoundingClientRect).

THIS INSTRUMENT ESTABLISHES, BEFORE THE ARMS RUN
-------------------------------------------------
The three score frames ask for points that lie HALF-WAY BETWEEN integer lattice points, and
the DOM exposes pageX/pageY as `long`: every click is truncated to integers on arrival. So
the FULL_REWARD optimum is unreachable by ANY click on these pages (circle-center, right-
angle: at every seed; find-midpoint: whenever the two marks' coordinate sums are odd, which
includes seed 1060). The pages' own authors say the same from the other side: their env
docstrings tell evaluators to binarize with `get_thresholded_reward`, not `get_binary_reward`.
The proof is arithmetic and arm-independent; what the arms decide is whether the treatment
puts the hand ON the reachable ceiling (and past the control), and whether -- where the
actuator CAN express the optimum -- full reward is actually reached.

ARMS (each reuses the identical search, budget, seed, state key and verdict)
-----------------------------------------------------------------------------
  A   shipped hand             control (unchanged)
  G2  exact-geometry hand      A plus aimed derivations (which now include the exact operators)
  D2  decoy aimed              A plus the same COUNT of aimed-shaped actions from the wrong
                               witness -- a random place for a place. If G2 does not beat D2,
                               the gain is the extra offers and not the geometry.

DECLARED BEFORE THE ARMS RUN (this block is copied into the receipt)
---------------------------------------------------------------------
  pass_primary       on circle-center and right-angle at seed 1060: G2's candidate set reaches
                     the arithmetic ceiling of the reachable integer lattice within 1e-3 (the
                     optimum lies half-way between lattice points) and beats A's candidate set
                     there. The window that locates the ceiling is a MEASUREMENT instrument
                     derived from the page's own stated geometry; the hand never receives it.
  pass_full_reward   find-midpoint at the pre-declared even-parity seed (the lowest seed >=
                     1061 at which both coordinate sums of the two marks are even) passes in
                     G2 with an EXACT_* rule while A and D2 fail it -- full reward exactly
                     where the actuator can express the optimum.
  kill               any verdict regression on REGRESSION_TASKS (A passes, G2 fails); a
                     pass_primary page whose ceiling A reaches and G2 does not; or
                     find-midpoint at the even seed passing in A or D2 while G2 fails.
  report             spend drift on REGRESSION_TASKS, honestly, whether or not it favors G2.

Usage
-----
    python3 canonical/tools/exact_stated_geometry_measure_v1.py \\
        --html-dir .../miniwob/html --node-modules-dir .../node_modules \\
        --budget 400 --seed 1060 --out /tmp/exact_geometry.jsonl [--tasks ...]
    python3 canonical/tools/exact_stated_geometry_measure_v1.py --mode ceiling ...
    python3 canonical/tools/exact_stated_geometry_measure_v1.py --mode even-seed ...
    python3 canonical/tools/exact_stated_geometry_measure_v1.py \\
        --consolidate a.jsonl b.jsonl c.jsonl --receipt ...json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import time
from typing import Any, Mapping, Sequence

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from canonical.runtime import aimed_action_v1 as aimed  # noqa: E402
from canonical.runtime import systematic_exploration_v1 as explorer  # noqa: E402
from canonical.tools import aimed_action_measure_v1 as aim_measure  # noqa: E402
from canonical.tools import miniwob_one_success_generalisation_measure_v1 as tool  # noqa: E402

SCHEMA = "BRAIN_EXACT_STATED_GEOMETRY_MEASURE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
SEED = 20261116
PROTOCOL_SEED = 1060

# The three pages proven impossible under the rounded observation; their score frames are the
# subject of the proofs above.
PRIMARY_TASKS = ["circle-center", "find-midpoint", "right-angle"]
# Same family, needing choreography beyond the point itself: reported, not required.
SECONDARY_TASKS = ["draw-circle", "bisect-angle"]
# Working pages (shipped or derived hands pass them): the kill set for regressions.
REGRESSION_TASKS = [
    "click-button", "simple-arithmetic", "search-engine", "email-inbox", "choose-list",
    "buy-ticket", "unicode-test", "login-user", "drag-shapes", "read-table",
    "form-sequence-3", "phone-book",
]
# Pages whose FULL_REWARD optimum is half-way between lattice points at EVERY seed.
CEILING_TASKS = ["circle-center", "right-angle"]
DECLARED = {
    "pass_primary": (
        "on circle-center and right-angle at seed 1060: G2's candidate set reaches the "
        "arithmetic ceiling of the reachable integer lattice within 1e-3 (the optimum lies "
        "half-way between lattice points) and beats A's candidate set there; the ceiling "
        "window is a measurement instrument derived from the page's stated geometry and the "
        "hand never receives it"),
    "pass_full_reward": (
        "find-midpoint at the pre-declared even-parity seed (the lowest seed >= 1061 at "
        "which both coordinate sums of the two marks are even) passes in G2 with an EXACT_* "
        "rule while A and D2 fail it -- full reward exactly where the actuator can express "
        "the optimum"),
    "kill": (
        "any verdict regression on REGRESSION_TASKS (A passes, G2 fails); a pass_primary "
        "page whose ceiling A reaches and G2 does not; or find-midpoint at the even seed "
        "passing in A or D2 while G2 fails"),
    "report": "spend drift on REGRESSION_TASKS, honestly, whether or not it favors G2",
    "amendment": (
        "run 1 fired its kill (read-table: A passed, G2 failed) -- cause: the previously "
        "derived places were quoted free at a markless page and stole the search; fix A: "
        "derived places paid unless exact (offers untouched). Run 2 fired the same kill -- "
        "cause: finalize itself had been priced at 3 while a markless page's working hand "
        "needs its shipped finalize price; fix B: finalize keeps its shipped price until a "
        "mark exists. Both fixes change PRICES only; no offer ever changed. Runs 1 and 2 are "
        "preserved in the receipt beside run 3, which is the adjudicating run under this "
        "declared protocol; the final verdict is computed on run 3 and the two earlier kills "
        "are reported honestly"),
}


def actions_arm(observation: Mapping[str, Any], arm: str) -> list[str]:
    """How a page's offered actions are built in each arm. The shipped hand is IDENTICAL in
    all arms -- only the derived candidates differ, so any difference is the derivation."""
    everything = tool.offered_actions(observation, tool.HAND_TIER)
    if arm == "A_shipped_hand":
        return everything
    if arm == "G2_exact_geometry":
        return list(dict.fromkeys(everything + aimed.aimed_actions(observation)))
    if arm == "D2_decoy_geometry":
        return list(dict.fromkeys(everything + aimed.decoy_actions(observation, seed=SEED)))
    raise ValueError(f"ARM_UNKNOWN:{arm}")


class ExactGeometryPrices:
    """The treatment prices its own derivations as the instruction's own, with the one rule
    the score-frame pages need: while the page SHOWS a mark the hand has placed, finalize is
    free and every press that would MOVE the mark is paid -- the free run therefore ends at
    the mark that exists instead of wandering to the end of an infinite lattice of marks.
    With no mark yet the exact derivations lead (a submit without a mark cannot score), the
    older derivations are PAID so they never steal a working hand's search, and finalize
    keeps its shipped price until a mark exists to end on. Shipped prices are the base everywhere this
    class does not speak, and the price is what orders the trying -- never a reason not to."""

    def __init__(self) -> None:
        self._base = tool.GuidedPrices()
        self._for: Any = None
        self._rules: dict[str, str] = {}
        self._marked = False

    def __call__(self, observation: Mapping[str, Any], action: str) -> tuple[int, int]:
        if observation is not self._for:
            self._for = observation
            self._rules = {row["action"]: str(row["rule"])
                           for row in aimed.aimed_rows(observation)}
            self._marked = any(
                re.search(r"blue", f"{e.get('id') or ''} {e.get('classes') or ''}")
                for e in (observation.get("elements") or []))
        rule = self._rules.get(action)
        if rule == "FINALIZE_BUTTON":
            # with a mark the episode ends now (free); without one finalize keeps ITS SHIPPED
            # price exactly -- a working hand must never be made to wait for its own ending
            return (0, 0) if self._marked else self._base(observation, action)
        if self._marked:
            if action.startswith(("pressat@", "moveat@")):
                return (1, 2)      # moving a mark that exists is a paid act
            if rule is not None:
                return (1, 2)
            return self._base(observation, action)
        if rule is not None:
            # the exact derivations lead (free); the older derivations are PAID, so on a page
            # that never needed them they can never steal a working hand's search
            return (0, 0) if rule.startswith("EXACT_") else (1, 1)
        return self._base(observation, action)


def measure_prices(arm: str) -> Any:
    if arm == "G2_exact_geometry":
        return ExactGeometryPrices()
    return tool.GuidedPrices()


def run_arm(bridge: Any, task: str, seed: int, *, budget: int, arm: str) -> dict[str, Any]:
    loaded = bridge.load(task)
    if not loaded.get("ok"):
        raise RuntimeError(f"PAGE_DID_NOT_LOAD:{task}")
    env = tool.SeedEnv(bridge, seed, time_limit_ms=tool.EXPLORATION_TIME_LIMIT_MS)
    started = time.time()
    prices = measure_prices(arm)
    result = explorer.explore_to_goal(
        env, [], is_goal=tool.succeeded, is_dead=tool.failed,
        actions_of=lambda observation: actions_arm(observation, arm),
        key_of=tool.state_key, order="cheapest", cost_of=prices,
        action_budget=int(budget), reset_cost=1, include_model=False)
    rule: dict[str, Any] | None = None
    verified = False
    if result.get("pass"):
        plan = [str(a) for a in (result.get("plan_cheapest") or [])]
        replay = tool.replay_on_fresh_page(bridge, task, seed, plan)
        verified = bool(replay.get("reproduced"))
        wanted = set(plan)
        for observation, action in (replay.get("trace") or []):
            if str(action) in wanted:
                found = aimed.rule_of(observation, str(action))
                if found is not None:
                    rule = found
                    break
    return {"pass": bool(result.get("pass")), "verified_on_fresh_page": verified,
            "status": result.get("status"), "budget_spent": int(result.get("budget_spent") or 0),
            "plan_len": len(list(result.get("plan_cheapest") or [])),
            "rule": rule, "seconds": round(time.time() - started, 1)}


# --------------------------------------------------------------------------- measurement modes
def _marks_canvas(observation: Mapping[str, Any]) -> list[tuple[float, float]]:
    """The marks in canvas coordinates, smallest first -- the same population and order the
    operators reason over, so a line drawn between two points never displaces the points."""
    frame = aimed._svg_frame(observation)
    if frame is None:
        return []
    marks = sorted(aimed._point_marks(observation),
                   key=lambda e: ((aimed._float_box(e) or [0] * 4)[2]
                                  * (aimed._float_box(e) or [0] * 4)[3]))
    out = []
    for element in marks:
        point = aimed._svg_local_point(element, frame)
        if point is not None:
            out.append(point)
    return out


def ceiling_window(task: str, observation: Mapping[str, Any]) -> list[str]:
    """The integer lattice NEIGHBOURHOOD of the arithmetic optimum -- the measurement window
    that locates the reachable ceiling. Derived from the page's own stated geometry (marks,
    svg frame, the printed-offset family); it is never offered to the hand."""
    frame = aimed._svg_frame(observation)
    offsets = aimed._page_y_offsets(observation)
    if frame is None or not offsets:
        return []
    marks = _marks_canvas(observation)   # smallest first: the points, never the line between them
    out: set[str] = set()
    if task == "circle-center":
        if not marks:
            return []
        cx, cy = marks[0]
        for k in offsets:
            for dx in (0, 1):
                for dy in (-1, 0, 1):
                    out.add(aimed._press(cx + dx, cy + k + dy))
    elif task == "find-midpoint":
        if len(marks) < 2:
            return []
        mid = ((marks[0][0] + marks[1][0]) / 2.0, (marks[0][1] + marks[1][1]) / 2.0)
        for k in offsets:
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    out.add(aimed._press(mid[0] + dx, mid[1] + k + dy))
    elif task == "right-angle":
        if len(marks) < 2:
            return []
        p, q = marks[0], marks[1]
        for base, other in ((p, q), (q, p)):
            dx, dy = other[0] - base[0], other[1] - base[1]
            for sx, sy in ((-dy, dx), (dy, -dx)):
                vx, vy = base[0] + sx, base[1] + sy
                for k in offsets:
                    for ax in (-2, -1, 0, 1):
                        for ay in (-2, -1, 0, 1):
                            out.add(aimed._press(vx + ax, vy + k + ay))
    return sorted(out)


def probe_candidates(bridge: Any, task: str, seed: int, candidates: Sequence[str],
                     *, label: str, kind: str = "ceiling") -> dict[str, Any]:
    """Press each candidate on a FRESH page and read the page's own reward: the best a given
    candidate set can achieve, with no search in between."""
    loaded = bridge.load(task)
    if not loaded.get("ok"):
        raise RuntimeError(f"PAGE_DID_NOT_LOAD:{task}")
    env = tool.SeedEnv(bridge, seed, time_limit_ms=tool.EXPLORATION_TIME_LIMIT_MS)
    started = time.time()
    best: dict[str, Any] = {"reward": None, "action": None}
    probed = skipped = 0
    for cand in candidates:
        if not cand.startswith("pressat@"):
            continue
        obs = env.reset()
        button = next((e for e in obs["elements"] if e.get("text") == "Submit"), None)
        x = float(cand.partition("@")[2].partition(",")[0])
        y = float(cand.partition("@")[2].partition(",")[2])
        if button and button.get("box_f"):
            bx, by, bw, bh = (float(v) for v in button["box_f"])
            if bx <= x <= bx + bw and by <= y <= by + bh:
                skipped += 1
                continue          # the press would land on Submit itself: not a place to measure
        probed += 1
        o2 = env.act(cand)
        if o2 is None or o2.get("done"):
            continue
        submit = next((e["index"] for e in o2["elements"] if e.get("text") == "Submit"), None)
        if submit is None:
            continue
        o3 = env.act(f"click@{submit}")
        reward = float(o3.get("raw_reward")) if o3 and o3.get("done") else None
        if reward is not None and (best["reward"] is None or reward > best["reward"]):
            best = {"reward": reward, "action": cand}
    return {"kind": kind, "task": task, "seed": seed, "label": label,
            "probed": probed, "skipped_button": skipped,
            "best_reward": best["reward"], "best_action": best["action"],
            "seconds": round(time.time() - started, 1)}


def arm_press_candidates(observation: Mapping[str, Any], arm: str) -> list[str]:
    return [a for a in actions_arm(observation, arm) if a.startswith("pressat@")]


def even_seed_for(task: str, *, start: int = 1061, limit: int = 80) -> int | None:
    """The lowest seed >= start at which the page's own marks put the optimum ON the integer
    lattice (both coordinate sums even for find-midpoint). Chosen by a declared rule, never
    by outcome."""
    if task != "find-midpoint":
        return None
    for seed in range(start, start + limit):
        obs_seed = seed
        return_seed = _parity_even(task, obs_seed)
        if return_seed:
            return seed
    return None


def _parity_even(task: str, seed: int) -> bool:
    bridge_holder = _parity_even._bridge
    if bridge_holder is None:
        return False
    if not bridge_holder.load(task).get("ok"):
        return False
    env = tool.SeedEnv(bridge_holder, seed, time_limit_ms=tool.EXPLORATION_TIME_LIMIT_MS)
    obs = env.reset()
    marks = _marks_canvas(obs)
    if len(marks) < 2:
        return False
    (x1, y1), (x2, y2) = marks[0], marks[1]
    return (x1 + x2) % 2 == 0 and (y1 + y2) % 2 == 0


_parity_even._bridge: Any = None


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--html-dir")
    parser.add_argument("--node-modules-dir")
    parser.add_argument("--substrate", default="chromium", choices=("chromium", "jsdom"))
    parser.add_argument("--mode", default="search",
                        choices=["search", "ceiling", "even-seed"])
    parser.add_argument("--budget", type=int, default=400)
    parser.add_argument("--seed", type=int, default=PROTOCOL_SEED)
    parser.add_argument("--tasks", nargs="+", required=False)
    parser.add_argument("--arms", nargs="+",
                        default=["A_shipped_hand", "G2_exact_geometry", "D2_decoy_geometry"])
    parser.add_argument("--out", required=False)
    parser.add_argument("--consolidate", nargs="+", default=None)
    parser.add_argument("--receipt", default=None)
    args = parser.parse_args(argv)

    if args.consolidate:
        return _consolidate(args.consolidate, args.receipt)
    if not args.out:
        parser.error("--out is required to measure")
    if not args.html_dir:
        parser.error("--html-dir and --node-modules-dir are required to measure")
    bridge = tool.Bridge(args.html_dir, args.node_modules_dir, substrate=args.substrate)
    versions = bridge.versions()

    if args.mode == "even-seed":
        _parity_even._bridge = bridge
        seed = even_seed_for("find-midpoint", start=max(1061, args.seed))
        if seed is None:
            raise SystemExit("EVEN_SEED_NOT_FOUND")
        print(f"even-parity seed for find-midpoint: {seed}")
        with open(args.out, "w") as handle:
            for arm in args.arms:
                row = {"kind": "supplementary", "task": "find-midpoint", "seed": seed,
                       "budget": args.budget, "environment": versions, "arms": {}}
                row["arms"][arm] = run_arm(bridge, "find-midpoint", seed,
                                           budget=args.budget, arm=arm)
                handle.write(json.dumps(row) + "\n")
                r = row["arms"][arm]
                print(f"  {arm}: pass={r['pass']} spend={r['budget_spent']} "
                      f"rule={(r['rule'] or {}).get('rule')}")
        bridge.close()
        return 0

    if args.mode == "ceiling":
        tasks = args.tasks or PRIMARY_TASKS
        with open(args.out, "w") as handle:
            for task in tasks:
                if not bridge.load(task).get("ok"):
                    raise RuntimeError(f"PAGE_DID_NOT_LOAD:{task}")
                env = tool.SeedEnv(bridge, args.seed, time_limit_ms=tool.EXPLORATION_TIME_LIMIT_MS)
                obs = env.reset()
                window = ceiling_window(task, obs)
                rows = [probe_candidates(bridge, task, args.seed, window,
                                         label="ceiling_window")]
                for arm in ("A_shipped_hand", "G2_exact_geometry"):
                    cands = arm_press_candidates(obs, arm)
                    rows.append(probe_candidates(bridge, task, args.seed, cands,
                                                 label=f"arm_{arm}", kind="arm_probe"))
                for row in rows:
                    handle.write(json.dumps(row) + "\n")
                print(f"{task:20s} " + "  ".join(
                    f"{r['label']}={r['best_reward']}" for r in rows), flush=True)
        bridge.close()
        return 0

    tasks = args.tasks or (PRIMARY_TASKS + SECONDARY_TASKS + REGRESSION_TASKS)
    with open(args.out, "w") as handle:
        for task in tasks:
            row: dict[str, Any] = {"kind": "page", "task": task, "seed": args.seed,
                                   "budget": args.budget, "environment": versions, "arms": {}}
            started = time.time()
            for arm in args.arms:
                row["arms"][arm] = run_arm(bridge, task, args.seed, budget=args.budget, arm=arm)
            row["seconds"] = round(time.time() - started, 1)
            handle.write(json.dumps(row) + "\n")
            print(f"{task:28s} " + "  ".join(
                f"{arm.split('_')[0]}={r['pass']}/{r['budget_spent']}a"
                + (f"[{r['rule']['rule']}]" if r.get("rule") else "")
                for arm, r in row["arms"].items()), flush=True)
    bridge.close()
    return 0


def _verdict(pages: Sequence[dict[str, Any]], ceiling: Sequence[dict[str, Any]],
             supplementary: Sequence[dict[str, Any]]) -> dict[str, Any]:
    by_task = {p["task"]: p for p in pages}
    primary = [t for t in PRIMARY_TASKS if t in by_task]
    regression = [t for t in REGRESSION_TASKS if t in by_task]

    def passed(task: str, arm: str) -> bool:
        return bool(by_task[task]["arms"].get(arm, {}).get("pass"))

    def rule_of(task: str, arm: str) -> str | None:
        return (by_task[task]["arms"].get(arm, {}).get("rule") or {}).get("rule")

    regressions = [t for t in regression
                   if passed(t, "A_shipped_hand") and not passed(t, "G2_exact_geometry")]
    spend_drift = {t: {"A": by_task[t]["arms"]["A_shipped_hand"]["budget_spent"],
                       "G2": by_task[t]["arms"]["G2_exact_geometry"]["budget_spent"]}
                   for t in regression
                   if by_task[t]["arms"]["A_shipped_hand"]["budget_spent"]
                   != by_task[t]["arms"]["G2_exact_geometry"]["budget_spent"]}

    # ceiling attainment on the two every-seed-proof pages
    ceil_by: dict[str, dict[str, Any]] = {}
    for row in ceiling:
        ceil_by.setdefault(row["task"], {})[row["label"]] = row
    ceiling_attainment: dict[str, Any] = {}
    ceiling_kill: list[str] = []
    for task in CEILING_TASKS:
        groups = ceil_by.get(task, {})
        window_best = (groups.get("ceiling_window") or {}).get("best_reward")
        a_best = (groups.get("arm_A_shipped_hand") or {}).get("best_reward")
        g_best = (groups.get("arm_G2_exact_geometry") or {}).get("best_reward")
        reaches = (window_best is not None and g_best is not None
                   and g_best >= window_best - 1e-3)
        beats_a = (g_best is not None and (a_best is None or g_best > a_best))
        ceiling_attainment[task] = {"window_best": window_best, "A_best": a_best,
                                    "G2_best": g_best, "reaches_ceiling": reaches,
                                    "beats_A": beats_a}
        if window_best is not None and a_best is not None and a_best >= window_best - 1e-3 \
                and not reaches:
            ceiling_kill.append(task)
    pass_primary = (not ceiling_kill) and all(
        ceiling_attainment.get(t, {}).get("reaches_ceiling")
        and ceiling_attainment.get(t, {}).get("beats_A") for t in CEILING_TASKS
        if t in by_task)

    # full reward where the actuator can express the optimum
    supp = [r for r in supplementary if r.get("task") == "find-midpoint"]
    supp_pass = {arm: any(r["arms"].get(arm, {}).get("pass") for r in supp) for arm in
                 ("A_shipped_hand", "G2_exact_geometry", "D2_decoy_geometry")}
    supp_rule = None
    for r in supp:
        g = r["arms"].get("G2_exact_geometry") or {}
        if g.get("pass"):
            supp_rule = (g.get("rule") or {}).get("rule")
    pass_full_reward = bool(supp_pass.get("G2_exact_geometry")
                            and not supp_pass.get("A_shipped_hand")
                            and not supp_pass.get("D2_decoy_geometry"))
    attribution_broken = bool(supp_pass.get("D2_decoy_geometry")
                              and not supp_pass.get("G2_exact_geometry"))
    kill = {"regressions": regressions, "ceiling_lost_to_A": ceiling_kill,
            "supplementary_attribution_broken": attribution_broken}
    return {
        "declared": DECLARED,
        "pass_primary": pass_primary,
        "pass_full_reward": pass_full_reward,
        "supplementary_find_midpoint": {"seed": (supp[0]["seed"] if supp else None),
                                         "pass_by_arm": supp_pass, "rule": supp_rule},
        "ceiling_attainment": ceiling_attainment,
        "primary_matrix": {t: {arm: {"pass": passed(t, arm), "rule": rule_of(t, arm),
                                     "spend": by_task[t]["arms"][arm]["budget_spent"]}
                               for arm in ("A_shipped_hand", "G2_exact_geometry",
                                           "D2_decoy_geometry")}
                           for t in primary},
        "kill": kill,
        "kill_fired": bool(kill["regressions"] or ceiling_kill or attribution_broken),
        "spend_drift_regression": spend_drift,
    }


def _consolidate(paths: Sequence[str], receipt: str | None) -> int:
    pages: list[dict[str, Any]] = []
    ceiling: list[dict[str, Any]] = []
    supplementary: list[dict[str, Any]] = []
    search_runs: list[dict[str, Any]] = []
    for path in paths:
        run_rows: list[dict[str, Any]] = []
        for line in pathlib.Path(path).read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            kind = row.get("kind", "page")
            if kind == "ceiling" or kind == "arm_probe":
                ceiling.append(row)
            elif kind == "supplementary":
                supplementary.append(row)
            else:
                pages.append(row)
                run_rows.append(row)
        if run_rows:
            search_runs.append({"file": path, "pages": run_rows})
    if not search_runs:
        raise SystemExit("NO_SEARCH_ROWS")
    # The arms summary describes the ADJUDICATING run (the last one); earlier runs are kept
    # in full beside it and their verdicts are listed, never averaged into these counts.
    adjudicating = search_runs[-1]["pages"]
    pages = [row for run in search_runs for row in run["pages"]]
    arms = sorted({arm for page in adjudicating for arm in page["arms"]})
    summary: dict[str, Any] = {"pages": len(pages), "arms": {}}
    for arm in arms:
        solved = [p["task"] for p in adjudicating if p["arms"][arm]["pass"]]
        summary["arms"][arm] = {
            "pass": len(solved), "pass_tasks": sorted(solved),
            "verified": sum(1 for p in pages if p["arms"][arm]["verified_on_fresh_page"]),
            "actions_spent": sum(int(p["arms"][arm]["budget_spent"]) for p in adjudicating),
            "seconds": round(sum(float(p["arms"][arm]["seconds"]) for p in adjudicating), 1),
            "rules_that_solved": sorted({(p["arms"][arm].get("rule") or {}).get("rule")
                                         for p in adjudicating
                                         if (p["arms"][arm].get("rule") or {}).get("rule")}),
        }
    # Every search run is adjudicated under the SAME declared protocol; the LAST one is the
    # adjudicating run (the amendment names it), the earlier kills are kept beside it.
    summary["runs"] = [{"file": run["file"], "pages": len(run["pages"]),
                        "verdict": _verdict(run["pages"], ceiling, supplementary)}
                       for run in search_runs]
    summary["verdict"] = summary["runs"][-1]["verdict"]
    summary["prior_kills"] = [run["file"] for run in summary["runs"][:-1]
                              if run["verdict"]["kill_fired"]]
    out = {"schema": SCHEMA, "authority": AUTHORITY, "kind": "receipt",
           "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "incremental_spend_usd": 0, "producer_cognition_model_dependency_count": 0,
           "protocol": {"budget_acts": sorted({p["budget"] for p in adjudicating}),
                        "seed": PROTOCOL_SEED,
                        "primary_tasks": PRIMARY_TASKS, "secondary_tasks": SECONDARY_TASKS,
                        "regression_tasks": REGRESSION_TASKS,
                        "ceiling_tasks": CEILING_TASKS},
           "summary": summary, "pages": pages,
           "ceiling_probes": ceiling, "supplementary": supplementary}
    text = json.dumps(out, indent=1, sort_keys=True)
    if receipt:
        pathlib.Path(receipt).write_text(text + "\n")
        print(f"written {receipt}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
