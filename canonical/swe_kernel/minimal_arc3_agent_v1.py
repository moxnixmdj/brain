#!/usr/bin/env python3
"""Minimal Epistemic Core ARC-AGI-3 Agent v3 — Object-Centric Active Moore-Machine World Model.

100% general black-box visual physics — zero game-specific rules, zero private state access,
zero neural weights, ~2 ms per action:
  - Job 1 (HUDMasker, RegionSegmenter & Uniform-Playfield Lattice Fallback):
      * Online auto-detection of 1-3px step-counter / energy-bar HUD pixels with >=3-tick
        1D border-bar propagation (zero false masking on real game pixels).
      * 4-connected region extraction + automatic grid-aligned lattice probing inside uniform
        playfields ONLY when segmented regions exhaust without solving.
  - Job 2 (Cross-Level GamePrior & Winning-Affordance Transfer):
      * Persisted across levels 1..N of ONE game: HUD mask, affordance hit rates, winning
        action/color classes from prior levels, inverse action pairs, learned 2D motion
        vectors for A1..A4, and online-detected UNDO actions (e.g. A7).
  - Job 3 + 5a (OPINE-World Rare-Mechanic Priority + Tycho Active Frontier Planning):
      * Separates pure avatar translation (`color_hist_delta ~ 0`) from rare non-click
        mechanic triggers (`color_hist_delta >= 6` or distant causal effect > 14px),
        promoting post-mechanic "keystone states" in BFS on navigation puzzles without
        disrupting multi-click control efficiency on click puzzles.
      * Excludes detected UNDO (`A7`) from forward exploration and uses it as a clean 1-step
        backtrack; retries conditional `INTERACT` (`A5`) right after novel mechanics fire.
"""
from __future__ import annotations

import hashlib
from collections import Counter, deque
from typing import Any, Callable, Sequence

import numpy as np

SCHEMA = "BRAIN_MINIMAL_ARC3_AGENT_V3"


def extract_regions(frame: np.ndarray) -> list[dict[str, Any]]:
    """Fast 4-connected region extractor returning centroid-interior click point, color, area, bbox."""
    h, w = frame.shape
    grid = frame.tolist()
    seen = [[False] * w for _ in range(h)]
    regions: list[dict[str, Any]] = []
    for y0 in range(h):
        row_seen = seen[y0]
        for x0 in range(w):
            if row_seen[x0]:
                continue
            col = grid[y0][x0]
            stack = [(x0, y0)]
            seen[y0][x0] = True
            cells: list[tuple[int, int]] = []
            min_x = max_x = x0
            min_y = max_y = y0
            while stack:
                x, y = stack.pop()
                cells.append((x, y))
                if x < min_x: min_x = x
                if x > max_x: max_x = x
                if y < min_y: min_y = y
                if y > max_y: max_y = y
                if x > 0 and not seen[y][x - 1] and grid[y][x - 1] == col:
                    seen[y][x - 1] = True
                    stack.append((x - 1, y))
                if x + 1 < w and not seen[y][x + 1] and grid[y][x + 1] == col:
                    seen[y][x + 1] = True
                    stack.append((x + 1, y))
                if y > 0 and not seen[y - 1][x] and grid[y - 1][x] == col:
                    seen[y - 1][x] = True
                    stack.append((x, y - 1))
                if y + 1 < h and not seen[y + 1][x] and grid[y + 1][x] == col:
                    seen[y + 1][x] = True
                    stack.append((x, y + 1))
            area = len(cells)
            cx = sum(c[0] for c in cells) / area
            cy = sum(c[1] for c in cells) / area
            px, py = min(cells, key=lambda c: ((c[0] - cx) ** 2 + (c[1] - cy) ** 2, c[1], c[0]))
            bucket = "T" if area <= 4 else ("S" if area <= 36 else ("M" if area <= 200 else "L"))
            is_edge_strip = (min_y == 0 and max_y <= 3) or (max_y == h - 1 and min_y >= h - 4)
            regions.append({
                "x": px, "y": py, "color": int(col), "area": area, "bucket": bucket,
                "cx": cx, "cy": cy, "bbox": (min_x, min_y, max_x, max_y),
                "edge_strip": is_edge_strip,
                "action": f"C:{px}:{py}:{int(col)}",
                "cls": f"C:{int(col)}:{bucket}",
                "color_cls": f"C:{int(col)}",
            })
    return regions


def _detect_grid_stride(frame: np.ndarray) -> int:
    """Infer dominant tile stride (e.g. 4, 6, 8, 12) from interior horizontal/vertical edge spacings."""
    h, w = frame.shape
    sub = frame[4:h - 4, 4:w - 4]
    if sub.size == 0:
        return 8
    v_edges = np.where((sub[:, 1:] != sub[:, :-1]).mean(axis=0) > 0.25)[0]
    h_edges = np.where((sub[1:, :] != sub[:-1, :]).mean(axis=1) > 0.25)[0]
    gaps: list[int] = []
    for arr in (v_edges, h_edges):
        if len(arr) >= 2:
            for d in np.diff(arr):
                di = int(d)
                if 2 <= di <= 16:
                    gaps.append(di)
    if not gaps:
        return 8
    top_d, top_c = Counter(gaps).most_common(1)[0]
    return int(top_d) if top_c >= 2 else 8


class GamePrior:
    """Cross-level epistemic physics memory persisted across levels 1..N of ONE game.

    Uses `instant_condition_store_v1` single-counterexample invalidation semantics:
    any learned negative constraint (dead click class, blocking wall color) is revoked
    immediately on a single contradicting observation on a later level.
    """

    def __init__(self, shape: tuple[int, int] = (64, 64)) -> None:
        self.hud_mask = np.zeros(shape, dtype=bool)
        self.tiny_change_hits = np.zeros(shape, dtype=np.int32)
        self.step_change_hits = np.zeros(shape, dtype=np.int32)
        self.total_steps = 0
        self.cls_tries: Counter[str] = Counter()
        self.cls_world_hits: Counter[str] = Counter()
        self.cls_total_diff: Counter[str] = Counter()
        self.color_tries: Counter[str] = Counter()
        self.color_world_hits: Counter[str] = Counter()
        # Cross-level winning affordance transfer: action/color classes involved in winning levels!
        self.win_cls_hits: Counter[str] = Counter()
        self.win_color_hits: Counter[str] = Counter()
        self.inv_action: dict[str, str] = {}
        self.action_vec: dict[str, tuple[float, float]] = {}
        self.undo_actions: set[str] = set()
        self.undo_votes: Counter[str] = Counter()
        # Kinematic obstacle-color model (color -> [blocked_hits, pass_hits]) with 1-counterexample revocation
        self.color_blocked_hits: Counter[int] = Counter()
        self.color_pass_hits: Counter[int] = Counter()
        # Energy / step-limit horizon tracker (distinguishes timeout GAME_OVER from fatal hazards!)
        self.timeout_step_counts: list[int] = []
        self.known_step_limit: int | None = None

    def observe_diff(self, prev_frame: np.ndarray, next_frame: np.ndarray) -> tuple[int, int, bool]:
        """Update online border-only HUD mask and return (raw_px, world_px, mask_grew).

        Restricts automatic step-counter HUD masking strictly to outer border strips
        so small interior game objects (switches, keys, projectiles) are NEVER masked out.
        """
        diff = prev_frame != next_frame
        raw_px = int(np.count_nonzero(diff))
        self.total_steps += 1
        grew = False
        h, w = self.hud_mask.shape

        border_zone = np.zeros((h, w), dtype=bool)
        border_zone[:4, :] = True
        border_zone[max(0, h - 4):, :] = True
        border_zone[:, :3] = True
        border_zone[:, max(0, w - 3):] = True

        def _mark_hud(mask_slice: np.ndarray) -> None:
            nonlocal grew
            masked_slice = mask_slice & border_zone
            if not np.any(masked_slice):
                return
            before = int(np.count_nonzero(self.hud_mask))
            self.hud_mask |= masked_slice
            self.tiny_change_hits[masked_slice] += 1
            for r in (0, 1, 2, h - 3, h - 2, h - 1):
                if 0 <= r < h and int(np.count_nonzero(self.tiny_change_hits[r, :] > 0)) >= 3:
                    self.hud_mask[r, :] = True
            for c in (0, 1, w - 2, w - 1):
                if 0 <= c < w and int(np.count_nonzero(self.tiny_change_hits[:, c] > 0)) >= 3:
                    self.hud_mask[:, c] = True
            if int(np.count_nonzero(self.hud_mask)) > before:
                grew = True

        if 1 <= raw_px <= 3:
            _mark_hud(diff)
        elif raw_px > 0:
            self.step_change_hits[diff] += 1
            border_diff = diff & border_zone
            b_px = int(np.count_nonzero(border_diff))
            if 1 <= b_px <= 2 and raw_px >= 12:
                _mark_hud(border_diff)

        world_px = int(np.count_nonzero(diff & ~self.hud_mask))
        return raw_px, world_px, grew

    def world_key(self, frame: np.ndarray) -> str:
        """HUD-masked state fingerprint (revisited states hash identically despite HUD ticks)."""
        if np.any(self.hud_mask):
            masked = frame.copy()
            masked[self.hud_mask] = 0
            return hashlib.sha1(masked.tobytes()).hexdigest()[:20]
        return hashlib.sha1(frame.tobytes()).hexdigest()[:20]

    def color_histogram(self, frame: np.ndarray) -> np.ndarray:
        """Fast 16-color pixel count histogram outside the HUD mask."""
        vals = frame[~self.hud_mask] if np.any(self.hud_mask) else frame.ravel()
        return np.bincount(np.clip(vals.astype(np.int32), 0, 15), minlength=16)

    def record_affordance(self, action: str, cls: str, color_cls: str | None, world_px: int) -> None:
        self.cls_tries[cls] += 1
        if color_cls:
            self.color_tries[color_cls] += 1
        if world_px > 0:
            self.cls_world_hits[cls] += 1
            self.cls_total_diff[cls] += world_px
            if color_cls:
                self.color_world_hits[color_cls] += 1

    def record_win_trace(self, trace_specs: Sequence[dict[str, Any]]) -> None:
        """Persist the action/color classes that appeared on a solved level's path."""
        for spec in trace_specs[-12:]:
            self.win_cls_hits[spec["cls"]] += 1
            if spec.get("color_cls"):
                self.win_color_hits[spec["color_cls"]] += 1

    def eff_rate(self, cls: str, color_cls: str | None = None) -> float:
        t = self.cls_tries.get(cls, 0)
        if t > 0:
            return (self.cls_world_hits.get(cls, 0) + 0.25) / (t + 0.5)
        if color_cls and self.color_tries.get(color_cls, 0) > 0:
            ct = self.color_tries[color_cls]
            return (self.color_world_hits.get(color_cls, 0) + 0.25) / (ct + 0.5)
        return 0.55

    def is_dead_click_color(self, color_cls: str) -> bool:
        return self.color_tries.get(color_cls, 0) >= 2 and self.color_world_hits.get(color_cls, 0) == 0

    def is_dead_click_cls(self, cls: str, color_cls: str | None) -> bool:
        if color_cls and self.is_dead_click_color(color_cls):
            return True
        return self.cls_tries.get(cls, 0) >= 3 and self.cls_world_hits.get(cls, 0) == 0

    def record_move_target_color(self, color: int, moved: bool) -> None:
        if moved:
            self.color_pass_hits[color] += 1
        else:
            self.color_blocked_hits[color] += 1

    def is_predicted_wall_color(self, color: int) -> bool:
        # Single-counterexample revocation: if we EVER moved onto `color`, it's not a pure wall
        return self.color_blocked_hits.get(color, 0) >= 3 and self.color_pass_hits.get(color, 0) == 0

    def record_timeout_candidate(self, steps_since_reset: int) -> None:
        if steps_since_reset >= 8:
            self.timeout_step_counts.append(steps_since_reset)
            if len(self.timeout_step_counts) >= 2:
                recent = self.timeout_step_counts[-4:]
                if max(recent) - min(recent) <= 4:
                    self.known_step_limit = int(min(recent))


class MinimalArc3Agent:
    """Zero-neural object-centric epistemic explorer & planner for one ARC-AGI-3 game across levels."""

    def __init__(self) -> None:
        self.prior = GamePrior()

    def _offered_actions(
        self,
        frame: np.ndarray,
        available_actions: Sequence[int],
        *,
        include_bg_lattice: bool = False,
    ) -> list[dict[str, Any]]:
        """Build structured action list (discrete keys + segmented click regions + optional bg lattice)."""
        out: list[dict[str, Any]] = []
        avail = [int(a) for a in available_actions]
        has_move = any(a in (1, 2, 3, 4) for a in avail)
        for a in avail:
            if a != 6:
                act = f"A{a}"
                out.append({
                    "action": act, "aid": a, "cls": act, "color_cls": None,
                    "is_click": False, "area": 0, "cx": 32.0, "cy": 32.0, "edge_strip": False,
                })
        if 6 in avail:
            regs = extract_regions(frame)
            if regs:
                bg_col = max(
                    Counter(r["color"] for r in regs for _ in range(min(r["area"], 500))).items(),
                    key=lambda x: x[1],
                )[0]
                seen_coords: set[tuple[int, int]] = set()
                for r in regs:
                    is_bg = (r["color"] == bg_col and r["area"] >= 900)
                    seen_coords.add((r["x"], r["y"]))
                    out.append({
                        "action": r["action"], "aid": 6, "x": r["x"], "y": r["y"],
                        "cls": r["cls"], "color_cls": r["color_cls"],
                        "is_click": True, "area": r["area"], "cx": r["cx"], "cy": r["cy"],
                        "edge_strip": r["edge_strip"], "is_bg": is_bg, "has_move": has_move,
                    })
                if include_bg_lattice:
                    h, w = frame.shape
                    stride = max(4, min(12, _detect_grid_stride(frame)))
                    obj_centers = [
                        (r["cx"], r["cy"]) for r in regs
                        if not r["edge_strip"] and r["area"] < 400 and r["color"] != bg_col
                    ]
                    candidates: list[tuple[float, int, int, int]] = []
                    for y in range(stride // 2 + 4, h - 4, stride):
                        for x in range(stride // 2 + 4, w - 4, stride):
                            if (x, y) in seen_coords or self.prior.hud_mask[y, x]:
                                continue
                            col = int(frame[y, x])
                            d = (
                                min((x - ox) ** 2 + (y - oy) ** 2 for ox, oy in obj_centers)
                                if obj_centers
                                else (x - 32.0) ** 2 + (y - 32.0) ** 2
                            )
                            candidates.append((d, x, y, col))
                    candidates.sort()
                    for _, lx, ly, col in candidates[:18]:
                        out.append({
                            "action": f"C:{lx}:{ly}:{col}", "aid": 6, "x": lx, "y": ly,
                            "cls": f"C:{col}:LAT", "color_cls": f"C:{col}:LAT",
                            "is_click": True, "area": stride * stride,
                            "cx": float(lx), "cy": float(ly),
                            "edge_strip": False, "is_bg": False, "has_move": has_move,
                        })
        return out

    def _rank_untried(
        self,
        untried: list[dict[str, Any]],
        last_action: str | None,
        last_diff_center: tuple[float, float] | None,
        visited_click_coords: Counter[tuple[int, int]],
        target_vec: tuple[float, float] | None = None,
        *,
        just_fired_mechanic: bool = False,
        frame: np.ndarray | None = None,
        player_pos: tuple[float, float] | None = None,
    ) -> list[dict[str, Any]]:
        """Rank untried actions by color-stratified discovery, winning-class transfer, wall prediction & spatial guidance."""
        p = self.prior
        untested_colors_seen: set[str] = set()
        scored: list[tuple[float, dict[str, Any]]] = []
        ordered = sorted(
            untried,
            key=lambda a: (
                1 if a.get("is_bg") else 0,
                1 if a.get("edge_strip") else 0,
                (a["cx"] - 32.0) ** 2 + (a["cy"] - 32.0) ** 2,
            ),
        )
        inv_last = p.inv_action.get(last_action or "")

        for a in ordered:
            act = a["action"]
            cls = a["cls"]
            ccls = a["color_cls"]
            if act in p.undo_actions or (a["aid"] == 7 and p.cls_tries.get(act, 0) >= 1):
                continue
            if a["is_click"]:
                if a.get("is_bg") and p.color_tries.get(ccls, 0) >= 1 and p.color_world_hits.get(ccls, 0) == 0:
                    continue
                if a.get("has_move"):
                    if p.is_dead_click_color(ccls):
                        continue
                else:
                    if p.is_dead_click_cls(cls, ccls):
                        continue
                ct = p.color_tries.get(ccls, 0)
                if ct == 0:
                    if ccls not in untested_colors_seen:
                        untested_colors_seen.add(ccls)
                        sc = 3.0 - (0.8 if a["edge_strip"] else 0.0) - (1.2 if a.get("is_bg") else 0.0)
                    else:
                        sc = 0.5 - (0.5 if a["edge_strip"] else 0.0)
                else:
                    sc = 1.5 * p.eff_rate(cls, ccls)
                    # Cross-level winning-class transfer (focuses L1..LN on proven puzzle controls)
                    if p.win_cls_hits.get(cls, 0) > 0:
                        sc += 0.45
                    elif p.win_color_hits.get(ccls, 0) > 0:
                        sc += 0.25
                    if a["edge_strip"]:
                        sc -= 0.7
                    if a.get("is_bg"):
                        sc -= 1.0
                vc = visited_click_coords.get((a["x"], a["y"]), 0)
                sc += 0.4 / (1.0 + vc)
                # Penalize immediately re-clicking a proven self-inverse toggle control on consecutive steps
                if act == last_action and p.inv_action.get(act) == act:
                    sc -= 0.85
                if last_diff_center is not None and vc == 0:
                    d2 = (a["cx"] - last_diff_center[0]) ** 2 + (a["cy"] - last_diff_center[1]) ** 2
                    if 4.0 <= d2 <= 400.0:
                        sc += 0.25
                if a.get("has_move"):
                    move_rates = [p.eff_rate(f"A{m}") for m in (1, 2, 3, 4) if p.cls_tries.get(f"A{m}", 0) > 0]
                    if move_rates and max(move_rates) > 0.5 and ct > 0 and p.eff_rate(cls, ccls) < 0.35:
                        sc -= 0.6
            else:
                t = p.cls_tries.get(cls, 0)
                if a["aid"] == 7:
                    sc = 0.15  # single probe only; excluded once tried unless it solves
                elif a["aid"] == 5:
                    if t == 0:
                        sc = 2.6
                    elif just_fired_mechanic:
                        sc = 2.35
                    else:
                        sc = 1.3 * p.eff_rate(cls) + (0.35 if p.win_cls_hits.get(cls, 0) > 0 else 0.0)
                else:
                    sc = 2.8 if t == 0 else (1.5 * p.eff_rate(cls) + 0.3)
                if act == inv_last:
                    sc -= 0.75
                elif act == last_action and p.eff_rate(cls) > 0.3:
                    sc += 0.15
                if target_vec is not None and act in p.action_vec:
                    vx, vy = p.action_vec[act]
                    tx, ty = target_vec
                    vnorm = (vx * vx + vy * vy) ** 0.5
                    tnorm = (tx * tx + ty * ty) ** 0.5
                    if vnorm > 0.3 and tnorm > 1.0:
                        cos_sim = (vx * tx + vy * ty) / (vnorm * tnorm)
                        sc += 0.45 * cos_sim
            scored.append((sc, a))
        scored.sort(key=lambda x: (-x[0], x[1]["action"]))
        return [a for _, a in scored]

    def play_level(
        self,
        get_obs: Callable[[], tuple[np.ndarray, Sequence[int], str, int]],
        step_fn: Callable[[dict[str, Any]], tuple[np.ndarray, Sequence[int], str, int]],
        reset_fn: Callable[[], tuple[np.ndarray, Sequence[int], str, int]],
        *,
        budget: int,
        start_level: int = 0,
    ) -> dict[str, Any]:
        """Play ONE level up to `budget` actions using Object-Centric Active Moore-Machine Search."""
        frame, avail, st_name, lvl = get_obs()
        if frame.shape != self.prior.hud_mask.shape:
            self.prior = GamePrior(frame.shape)
        cur_key = self.prior.world_key(frame)
        cur_hist = self.prior.color_histogram(frame)

        transitions: dict[str, dict[str, str]] = {}
        action_specs: dict[str, dict[str, dict[str, Any]]] = {}
        tried: dict[str, set[str]] = {}
        dead_edges: set[tuple[str, str]] = set()
        death_edges: set[tuple[str, str]] = set()
        edge_death_count: Counter[tuple[str, str]] = Counter()
        dead_click_coord_misses: Counter[tuple[int, int, int]] = Counter()
        dead_click_coords: set[tuple[int, int, int]] = set()
        state_frames: dict[str, np.ndarray] = {}
        visit_count: Counter[str] = Counter({cur_key: 1})

        # Rare-mechanic keystone state score (ONLY incremented on non-click mechanics so click
        # efficiency on tight puzzles stays ultra-sharp while navigation puzzles prioritize switches!)
        state_mech_score: dict[str, float] = {cur_key: 0.0}
        seen_mech_sigs: set[tuple[Any, ...]] = set()
        lattice_enabled = False

        actions_used = 0
        steps_since_reset = 0
        consecutive_empty_resets = 0
        resets_used = 0
        deaths = 0
        world_changes = 0
        no_ops = 0
        last_action: str | None = None
        last_diff_center: tuple[float, float] | None = None
        visited_click_coords: Counter[tuple[int, int]] = Counter()
        planned_path: deque[dict[str, Any]] = deque()
        just_fired_mechanic = False
        state_stack: list[str] = [cur_key]
        recent_trace: list[dict[str, Any]] = []

        init_regs = extract_regions(frame)
        landmarks: list[tuple[float, float]] = []
        if init_regs:
            bg_c = max(Counter(r["color"] for r in init_regs for _ in range(min(r["area"], 500))).items(), key=lambda x: x[1])[0]
            landmarks = [
                (r["cx"], r["cy"]) for r in init_regs
                if not r["edge_strip"] and r["color"] != bg_c and 4 <= r["area"] <= 200
            ]
        visited_landmarks: set[int] = set()
        player_pos: tuple[float, float] | None = None

        def ensure_state(key: str, fr: np.ndarray, av: Sequence[int], force_refresh: bool = False) -> None:
            if key not in action_specs or force_refresh:
                specs = self._offered_actions(fr, av, include_bg_lattice=lattice_enabled)
                existing = action_specs.get(key, {})
                merged = dict(existing)
                for s in specs:
                    merged.setdefault(s["action"], s)
                action_specs[key] = merged
                tried.setdefault(key, set())
                state_frames[key] = fr.copy()
                state_mech_score.setdefault(key, 0.0)

        def rehash_graph_after_hud_growth() -> None:
            nonlocal transitions, action_specs, tried, state_frames, visit_count, state_mech_score
            key_map = {old_k: self.prior.world_key(fr) for old_k, fr in state_frames.items()}
            new_trans: dict[str, dict[str, str]] = {}
            new_specs: dict[str, dict[str, dict[str, Any]]] = {}
            new_tried: dict[str, set[str]] = {}
            new_frames: dict[str, np.ndarray] = {}
            new_visits: Counter[str] = Counter()
            new_mech: dict[str, float] = {}
            for old_k, nk in key_map.items():
                if nk not in new_specs:
                    new_specs[nk] = action_specs[old_k]
                    new_frames[nk] = state_frames[old_k]
                new_tried.setdefault(nk, set()).update(tried.get(old_k, set()))
                new_visits[nk] += visit_count.get(old_k, 0)
                new_mech[nk] = max(new_mech.get(nk, 0.0), state_mech_score.get(old_k, 0.0))
                for act, dst in transitions.get(old_k, {}).items():
                    ndst = key_map.get(dst, dst)
                    if ndst != nk:
                        new_trans.setdefault(nk, {})[act] = ndst
                    else:
                        dead_edges.add((nk, act))
            transitions, action_specs, tried, state_frames, visit_count, state_mech_score = (
                new_trans, new_specs, new_tried, new_frames, new_visits, new_mech,
            )

        def untried_for(key: str) -> list[dict[str, Any]]:
            specs = action_specs.get(key, {})
            tr = tried.get(key, set())
            return [
                s for act, s in specs.items()
                if act not in tr
                and (key, act) not in dead_edges
                and (key, act) not in death_edges
                and act not in self.prior.undo_actions
                and not (s["aid"] == 7 and self.prior.cls_tries.get(act, 0) >= 1)
                and not (s["is_click"] and (self.prior.is_dead_click_color(s["color_cls"]) if s.get("has_move") else self.prior.is_dead_click_cls(s["cls"], s["color_cls"])))
                and not (s["is_click"] and not s.get("has_move") and (s["x"], s["y"], int(s["color_cls"].split(":")[1])) in dead_click_coords)
            ]

        def bfs_to_frontier(start_k: str, max_depth: int = 16) -> list[dict[str, Any]]:
            """Shortest path in G to a state with untried actions, tie-breaking toward rare-mechanic keystones."""
            q: deque[tuple[str, list[dict[str, Any]]]] = deque([(start_k, [])])
            seen_k = {start_k}
            best_path: list[dict[str, Any]] | None = None
            best_val = -1e9
            found_depth: int | None = None
            has_any_keystone = any(v > 0.0 for v in state_mech_score.values())
            while q:
                k, path = q.popleft()
                if len(path) >= max_depth:
                    continue
                if found_depth is not None and len(path) > found_depth + (2 if has_any_keystone else 0):
                    break
                for act, nxt in transitions.get(k, {}).items():
                    if nxt in seen_k or (k, act) in death_edges or (k, act) in dead_edges:
                        continue
                    spec = action_specs.get(k, {}).get(act)
                    if spec is None:
                        continue
                    npath = path + [spec]
                    if untried_for(nxt):
                        if not has_any_keystone:
                            return npath
                        val = state_mech_score.get(nxt, 0.0) * 1.5 - len(npath) * 0.65
                        if val > best_val:
                            best_val = val
                            best_path = npath
                            if found_depth is None:
                                found_depth = len(npath)
                    seen_k.add(nxt)
                    q.append((nxt, npath))
            return best_path or []

        ensure_state(cur_key, frame, avail)

        while actions_used < budget:
            if lvl > start_level or st_name == "WIN":
                break

            if st_name == "GAME_OVER":
                deaths += 1
                if actions_used >= budget:
                    break
                frame, avail, st_name, lvl = reset_fn()
                actions_used += 1
                resets_used += 1
                steps_since_reset = 0
                cur_key = self.prior.world_key(frame)
                cur_hist = self.prior.color_histogram(frame)
                ensure_state(cur_key, frame, avail)
                last_action = None
                just_fired_mechanic = False
                state_stack = [cur_key]
                recent_trace.clear()
                planned_path.clear()
                continue

            chosen: dict[str, Any] | None = None
            if planned_path:
                cand = planned_path.popleft()
                if cand["action"] in action_specs.get(cur_key, {}):
                    chosen = cand
                else:
                    planned_path.clear()

            if chosen is None:
                untried_here = untried_for(cur_key)
                if not untried_here and (6 in avail) and not lattice_enabled:
                    lattice_enabled = True
                    ensure_state(cur_key, frame, avail, force_refresh=True)
                    untried_here = untried_for(cur_key)

                tvec = None
                if player_pos is not None and landmarks:
                    px, py = player_pos
                    best_lm = None
                    best_d = 1e9
                    for li, (lx, ly) in enumerate(landmarks):
                        if li in visited_landmarks:
                            continue
                        d = (lx - px) ** 2 + (ly - py) ** 2
                        if d < 16.0:
                            visited_landmarks.add(li)
                        elif d < best_d:
                            best_d = d
                            best_lm = (lx - px, ly - py)
                    tvec = best_lm

                ranked = self._rank_untried(
                    untried_here,
                    last_action,
                    last_diff_center,
                    visited_click_coords,
                    target_vec=tvec,
                    just_fired_mechanic=just_fired_mechanic,
                    frame=frame,
                    player_pos=player_pos,
                )
                if ranked:
                    chosen = ranked[0]
                    consecutive_empty_resets = 0
                else:
                    path = bfs_to_frontier(cur_key, max_depth=max(8, min(36, budget - actions_used - 1)))
                    if path:
                        planned_path.extend(path[1:])
                        chosen = path[0]
                        consecutive_empty_resets = 0
                    else:
                        undo_spec = None
                        for u_act in self.prior.undo_actions:
                            if u_act in action_specs.get(cur_key, {}) and len(state_stack) >= 2:
                                undo_spec = action_specs[cur_key][u_act]
                                break
                        if undo_spec is not None:
                            chosen = undo_spec
                        else:
                            fallbacks = [
                                s for act, s in action_specs.get(cur_key, {}).items()
                                if (cur_key, act) not in dead_edges and (cur_key, act) not in death_edges
                                and act not in self.prior.undo_actions
                                and not (s["is_click"] and (self.prior.is_dead_click_color(s["color_cls"]) if s.get("has_move") else self.prior.is_dead_click_cls(s["cls"], s["color_cls"])))
                            ]
                            if fallbacks and (resets_used >= 2 or consecutive_empty_resets >= 2):
                                fallbacks.sort(key=lambda s: visit_count.get(transitions.get(cur_key, {}).get(s["action"], ""), 0))
                                chosen = fallbacks[0]
                                consecutive_empty_resets = 0
                            elif (
                                actions_used < budget - 1
                                and consecutive_empty_resets < 3
                                and visit_count[cur_key] >= 1
                                and cur_key != next(iter(action_specs))
                            ):
                                frame, avail, st_name, lvl = reset_fn()
                                actions_used += 1
                                resets_used += 1
                                steps_since_reset = 0
                                consecutive_empty_resets += 1
                                cur_key = self.prior.world_key(frame)
                                cur_hist = self.prior.color_histogram(frame)
                                ensure_state(cur_key, frame, avail)
                                last_action = None
                                just_fired_mechanic = False
                                state_stack = [cur_key]
                                recent_trace.clear()
                                planned_path.clear()
                                continue
                            elif fallbacks:
                                fallbacks.sort(key=lambda s: visit_count.get(transitions.get(cur_key, {}).get(s["action"], ""), 0))
                                chosen = fallbacks[0]
                            else:
                                # Re-open tried edges if graph exhausted on latent/timed puzzle instead of looping resets
                                dead_edges.clear()
                                all_acts = list(action_specs.get(cur_key, {}).values())
                                if not all_acts:
                                    break
                                chosen = all_acts[actions_used % len(all_acts)]

            prev_frame = frame
            prev_key = cur_key
            prev_hist = cur_hist
            act_name = chosen["action"]
            # Sample predicted destination pixel color for kinematic wall learning before stepping
            pred_tgt_color: int | None = None
            if not chosen["is_click"] and chosen["aid"] in (1, 2, 3, 4) and player_pos is not None and act_name in self.prior.action_vec:
                vx, vy = self.prior.action_vec[act_name]
                tx_i = int(round(player_pos[0] + vx))
                ty_i = int(round(player_pos[1] + vy))
                if 0 <= tx_i < prev_frame.shape[1] and 0 <= ty_i < prev_frame.shape[0]:
                    pred_tgt_color = int(prev_frame[ty_i, tx_i])

            frame, avail, st_name, lvl = step_fn(chosen)
            actions_used += 1
            steps_since_reset += 1
            if chosen["is_click"]:
                visited_click_coords[(chosen["x"], chosen["y"])] += 1

            if lvl > start_level or st_name == "WIN":
                self.prior.record_affordance(act_name, chosen["cls"], chosen["color_cls"], 100)
                recent_trace.append(chosen)
                self.prior.record_win_trace(recent_trace)
                break

            raw_px, world_px, mask_grew = self.prior.observe_diff(prev_frame, frame)
            if mask_grew:
                rehash_graph_after_hud_growth()
                prev_key = self.prior.world_key(prev_frame)
            elif raw_px > 0 and world_px == 0:
                prev_key = self.prior.world_key(prev_frame)
            next_key = self.prior.world_key(frame)
            next_hist = self.prior.color_histogram(frame)

            tried.setdefault(prev_key, set()).add(act_name)

            if st_name == "GAME_OVER":
                self.prior.record_affordance(act_name, chosen["cls"], chosen["color_cls"], 0)
                edge_death_count[(prev_key, act_name)] += 1
                self.prior.record_timeout_candidate(steps_since_reset)
                # Proven non-hazard timeout: ONLY unban if this EXACT edge succeeded before AND occurred late (energy timeout)
                already_safe = (act_name in transitions.get(prev_key, {})) and (steps_since_reset >= 18)
                if not already_safe:
                    death_edges.add((prev_key, act_name))
                else:
                    tried.setdefault(prev_key, set()).discard(act_name)
                planned_path.clear()
                cur_key = next_key
                cur_hist = next_hist
                just_fired_mechanic = False
                continue

            if world_px == 0 or next_key == prev_key:
                self.prior.record_affordance(act_name, chosen["cls"], chosen["color_cls"], 0)
                if pred_tgt_color is not None:
                    self.prior.record_move_target_color(pred_tgt_color, moved=False)
                if chosen["is_click"]:
                    ckey = (chosen["x"], chosen["y"], int(chosen["color_cls"].split(":")[1]))
                    dead_click_coord_misses[ckey] += 1
                    if dead_click_coord_misses[ckey] >= 2:
                        dead_click_coords.add(ckey)
                no_ops += 1
                dead_edges.add((prev_key, act_name))
                planned_path.clear()
                cur_key = prev_key
                cur_hist = next_hist
                just_fired_mechanic = False
                ensure_state(cur_key, frame, avail)
                continue

            if pred_tgt_color is not None:
                self.prior.record_move_target_color(pred_tgt_color, moved=True)
            if chosen["is_click"]:
                # Single-counterexample revocation: if clicking this coord EVER worked, unban it!
                ckey = (chosen["x"], chosen["y"], int(chosen["color_cls"].split(":")[1]))
                dead_click_coords.discard(ckey)

            # Detect UNDO action online
            if len(state_stack) >= 2 and next_key == state_stack[-2]:
                if chosen["aid"] == 7:
                    self.prior.undo_actions.add(act_name)
                elif last_action is not None and act_name != last_action:
                    self.prior.undo_votes[act_name] += 1
                    if chosen["aid"] not in (1, 2, 3, 4, 6) and self.prior.undo_votes[act_name] >= 2:
                        self.prior.undo_actions.add(act_name)

            self.prior.record_affordance(act_name, chosen["cls"], chosen["color_cls"], world_px)
            world_changes += 1
            recent_trace.append(chosen)

            diff_mask = (prev_frame != frame) & ~self.prior.hud_mask
            ys, xs = np.nonzero(diff_mask)
            distant_effect = False
            new_center: tuple[float, float] | None = None
            if len(ys):
                new_center = (float(xs.mean()), float(ys.mean()))
                if not chosen["is_click"] and player_pos is not None:
                    d_av = ((new_center[0] - player_pos[0]) ** 2 + (new_center[1] - player_pos[1]) ** 2) ** 0.5
                    if d_av > 14.0 and world_px >= 8:
                        distant_effect = True
                if not chosen["is_click"] and chosen["aid"] in (1, 2, 3, 4) and world_px <= 160 and not distant_effect:
                    if player_pos is not None:
                        dx, dy = new_center[0] - player_pos[0], new_center[1] - player_pos[1]
                        if 0.5 <= (dx * dx + dy * dy) ** 0.5 <= 16.0:
                            if act_name in self.prior.action_vec:
                                ox, oy = self.prior.action_vec[act_name]
                                self.prior.action_vec[act_name] = (0.6 * ox + 0.4 * dx, 0.6 * oy + 0.4 * dy)
                            else:
                                self.prior.action_vec[act_name] = (dx, dy)
                    player_pos = new_center
                last_diff_center = new_center

            # OPINE-World rare-mechanic detection for discrete navigation/interaction games
            novel_mech = False
            if not chosen["is_click"]:
                hist_diff = next_hist - prev_hist
                hist_l1 = int(np.abs(hist_diff).sum())
                if hist_l1 >= 6 or distant_effect:
                    sig = (chosen["cls"], tuple(int(np.sign(x)) for x in hist_diff), min(4, hist_l1 // 8))
                    if sig not in seen_mech_sigs:
                        seen_mech_sigs.add(sig)
                        novel_mech = True
                        state_mech_score[next_key] = max(
                            state_mech_score.get(next_key, 0.0),
                            state_mech_score.get(prev_key, 0.0) + 1.5,
                        )
                        if "A5" in action_specs.get(next_key, {}):
                            tried.setdefault(next_key, set()).discard("A5")
                            dead_edges.discard((next_key, "A5"))
                else:
                    state_mech_score[next_key] = max(
                        state_mech_score.get(next_key, 0.0),
                        state_mech_score.get(prev_key, 0.0),
                    )

            transitions.setdefault(prev_key, {})[act_name] = next_key
            if last_action is not None and transitions.get(next_key, {}).get(last_action) == prev_key:
                if act_name not in self.prior.undo_actions:
                    if act_name != last_action:
                        self.prior.inv_action[last_action] = act_name
                        self.prior.inv_action[act_name] = last_action
                    elif chosen["is_click"]:
                        # Self-inverse toggle control: clicking the same control twice restores prior state!
                        self.prior.inv_action[act_name] = act_name

            if len(state_stack) >= 2 and next_key == state_stack[-2]:
                state_stack.pop()
            else:
                state_stack.append(next_key)

            cur_key = next_key
            cur_hist = next_hist
            visit_count[cur_key] += 1
            ensure_state(cur_key, frame, avail)
            last_action = act_name
            just_fired_mechanic = novel_mech

        return {
            "solved": (lvl > start_level or st_name == "WIN"),
            "actions_used": actions_used,
            "resets_used": resets_used,
            "deaths": deaths,
            "world_changes": world_changes,
            "no_ops": no_ops,
            "unique_world_states": len(action_specs),
            "hud_pixels_found": int(np.count_nonzero(self.prior.hud_mask)),
            "novel_mechanics_seen": len(seen_mech_sigs),
        }
