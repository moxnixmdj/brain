#!/usr/bin/env python3
"""Minimal Epistemic Core ARC-AGI-3 Agent v1 (Zero-Neural Jobs 1 + 2 + 3 + 5a).

100% general black-box visual physics — zero game-specific rules, zero private state access,
zero neural weights, sub-millisecond per action:
  - Job 1 (HUDMasker & RegionSegmenter): online auto-detection of 1-3px action-counter /
    energy-bar HUD pixels so wall hits & dead clicks register as true zero-world-diff no-ops
    and revisited states hash identically even as HUD counters tick.
  - Job 2 (WorldGraphMemory & GamePrior): exact HUD-masked transition graph G(s, a) -> s',
    inverse-action discovery, death/wall pruning, and cross-level transfer of learned HUD masks
    and interactive color/action affordances across levels 1..N of a game.
  - Job 3 + 5a (Color-Stratified Affordance Probing + Frontier BFS): probes one interior region
    per untested color class first (eliminating 80-95% of dead tiles immediately), then plans
    shortest paths in G to the nearest unexplored meaningful frontier without needless resets.
"""
from __future__ import annotations

import hashlib
from collections import Counter, deque
from typing import Any, Callable, Sequence

import numpy as np

SCHEMA = "BRAIN_MINIMAL_ARC3_AGENT_V1"


def extract_regions(frame: np.ndarray) -> list[dict[str, Any]]:
    """Fast 4-connected region extractor returning centroid-interior click point, color, area."""
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
            # Border penalty: regions touching y==0 or y==h-1 with tiny height are often HUDs
            is_edge_strip = (min_y == 0 and max_y <= 3) or (max_y == h - 1 and min_y >= h - 4)
            regions.append({
                "x": px, "y": py, "color": int(col), "area": area, "bucket": bucket,
                "cx": cx, "cy": cy, "edge_strip": is_edge_strip,
                "action": f"C:{px}:{py}:{int(col)}",
                "cls": f"C:{int(col)}:{bucket}",
                "color_cls": f"C:{int(col)}",
            })
    return regions


class GamePrior:
    """Cross-level memory for ONE game (persisted from level 1 -> 2 -> ... -> N, zero game hacks)."""

    def __init__(self, shape: tuple[int, int] = (64, 64)) -> None:
        self.hud_mask = np.zeros(shape, dtype=bool)
        self.tiny_change_hits = np.zeros(shape, dtype=np.int32)
        self.step_change_hits = np.zeros(shape, dtype=np.int32)
        self.total_steps = 0
        # Affordance statistics by fine class (`A1`, `C:9:S`) and coarse color class (`C:9`)
        self.cls_tries: Counter[str] = Counter()
        self.cls_world_hits: Counter[str] = Counter()
        self.cls_total_diff: Counter[str] = Counter()
        self.color_tries: Counter[str] = Counter()
        self.color_world_hits: Counter[str] = Counter()
        self.inv_action: dict[str, str] = {}
        # Learned 2D motion vector (dx, dy) for discrete movement actions A1..A4
        self.action_vec: dict[str, tuple[float, float]] = {}

    def observe_diff(self, prev_frame: np.ndarray, next_frame: np.ndarray) -> tuple[int, int, bool]:
        """Update online HUD mask (with 1D border-bar propagation) and return (raw_px, world_px, mask_grew)."""
        diff = prev_frame != next_frame
        raw_px = int(np.count_nonzero(diff))
        self.total_steps += 1
        grew = False
        h, w = self.hud_mask.shape

        def _mark_hud(mask_slice: np.ndarray) -> None:
            nonlocal grew
            before = int(np.count_nonzero(self.hud_mask))
            self.hud_mask |= mask_slice
            self.tiny_change_hits[mask_slice] += 1
            # 1D Border-Bar Propagation (general visual physics):
            # Only propagate along an outer border line when >=3 distinct pixels in THAT EXACT
            # single row (y in {0,1,61,62,63}) or col (x in {0,1,62,63}) ticked as 1-3px HUD pixels!
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
            # Detect small isolated 1-2px HUD tick along extreme border (y in {0,61,62,63} or x in {0,63})
            # occurring alongside a larger interior move
            border_diff = diff.copy()
            border_diff[1:h - 3, 1:w - 1] = False
            b_px = int(np.count_nonzero(border_diff))
            if 1 <= b_px <= 2 and raw_px >= 12:
                _mark_hud(border_diff)
        world_px = int(np.count_nonzero(diff & ~self.hud_mask))
        return raw_px, world_px, grew

    def world_key(self, frame: np.ndarray) -> str:
        """HUD-masked state fingerprint (revisited cells hash identically despite HUD ticks!)."""
        if np.any(self.hud_mask):
            masked = frame.copy()
            masked[self.hud_mask] = 0
            return hashlib.sha1(masked.tobytes()).hexdigest()[:20]
        return hashlib.sha1(frame.tobytes()).hexdigest()[:20]

    def record_affordance(self, action: str, cls: str, color_cls: str | None, world_px: int) -> None:
        self.cls_tries[cls] += 1
        if color_cls:
            self.color_tries[color_cls] += 1
        if world_px > 0:
            self.cls_world_hits[cls] += 1
            self.cls_total_diff[cls] += world_px
            if color_cls:
                self.color_world_hits[color_cls] += 1

    def eff_rate(self, cls: str, color_cls: str | None = None) -> float:
        t = self.cls_tries.get(cls, 0)
        if t > 0:
            return (self.cls_world_hits.get(cls, 0) + 0.25) / (t + 0.5)
        if color_cls and self.color_tries.get(color_cls, 0) > 0:
            ct = self.color_tries[color_cls]
            return (self.color_world_hits.get(color_cls, 0) + 0.25) / (ct + 0.5)
        return 0.55  # optimistic prior for completely untested classes!

    def is_dead_click_color(self, color_cls: str) -> bool:
        return self.color_tries.get(color_cls, 0) >= 2 and self.color_world_hits.get(color_cls, 0) == 0


class MinimalArc3Agent:
    """Zero-neural epistemic explorer & planner for one ARC-AGI-3 game across all levels."""

    def __init__(self) -> None:
        self.prior = GamePrior()

    def _offered_actions(self, frame: np.ndarray, available_actions: Sequence[int]) -> list[dict[str, Any]]:
        """Build structured action list (discrete keys + segmented interior-ranked click regions)."""
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
                bg_col = max(Counter(r["color"] for r in regs for _ in range(min(r["area"], 500))).items(), key=lambda x: x[1])[0]
                for r in regs:
                    # Skip giant full-canvas background unless no other targets exist
                    is_bg = (r["color"] == bg_col and r["area"] >= 900)
                    out.append({
                        "action": r["action"], "aid": 6, "x": r["x"], "y": r["y"],
                        "cls": r["cls"], "color_cls": r["color_cls"],
                        "is_click": True, "area": r["area"], "cx": r["cx"], "cy": r["cy"],
                        "edge_strip": r["edge_strip"], "is_bg": is_bg, "has_move": has_move,
                    })
        return out

    def _rank_untried(
        self,
        untried: list[dict[str, Any]],
        last_action: str | None,
        last_diff_center: tuple[float, float] | None,
        visited_click_coords: Counter[tuple[int, int]],
        target_vec: tuple[float, float] | None = None,
    ) -> list[dict[str, Any]]:
        """Rank untried actions by color-stratified discovery + learned affordance + locality."""
        p = self.prior
        # On click actions, prefer FIRST trying 1 interior representative per untested color!
        untested_colors_seen: set[str] = set()
        scored: list[tuple[float, dict[str, Any]]] = []
        # Sort interior-first so the representative chosen for each untested color is near center!
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
            if a["is_click"]:
                if a.get("is_bg") and p.color_tries.get(ccls, 0) >= 1 and p.color_world_hits.get(ccls, 0) == 0:
                    continue
                if p.is_dead_click_color(ccls):
                    continue
                ct = p.color_tries.get(ccls, 0)
                if ct == 0:
                    # Color-stratified probe: boost ONE interior representative per untested color!
                    if ccls not in untested_colors_seen:
                        untested_colors_seen.add(ccls)
                        sc = 3.2 - (0.8 if a["edge_strip"] else 0.0) - (1.2 if a.get("is_bg") else 0.0)
                    else:
                        sc = 0.6 - (0.5 if a["edge_strip"] else 0.0)
                else:
                    rate = p.eff_rate(cls, ccls)
                    sc = 1.0 + 3.0 * rate
                    if a.get("is_bg"):
                        sc -= 1.5
                    if a["edge_strip"]:
                        sc -= 0.7
                    # Slight boost for clicking near where the world last changed (causal locality!)
                    if last_diff_center is not None:
                        dist = abs(a["cx"] - last_diff_center[0]) + abs(a["cy"] - last_diff_center[1])
                        sc += max(0.0, 0.45 - dist / 140.0)
                    # Diversity + novelty bonus: avoid hammering the exact same click coord over and over!
                    click_cnt = visited_click_coords.get((a["x"], a["y"]), 0)
                    if click_cnt == 0:
                        sc += 0.55
                    else:
                        sc -= min(1.8, 0.25 * click_cnt)
                    if act == last_action:
                        sc -= 0.45
            else:
                # Discrete movement / action (A1..A5, A7)
                rate = p.eff_rate(cls)
                sc = 1.8 + 2.8 * rate
                if a["aid"] == 7:
                    # A7 is often undo/reset-like: try after movement/click actions unless proven useful
                    sc -= 0.9 if p.cls_world_hits.get(cls, 0) == 0 else 0.2
                if act == inv_last:
                    # Don't immediately step backwards when exploring forward!
                    sc -= 0.85
                elif act == last_action and p.cls_world_hits.get(cls, 0) > 0:
                    # Slight momentum bonus in corridors (reduces zig-zagging!)
                    sc += 0.15
                # Visual object-approach alignment: prefer moves aligned toward nearest unvisited interior object!
                if target_vec is not None and act in p.action_vec:
                    vx, vy = p.action_vec[act]
                    tx, ty = target_vec
                    norm = ((vx * vx + vy * vy) ** 0.5) * ((tx * tx + ty * ty) ** 0.5)
                    if norm > 1e-6:
                        sc += 0.40 * ((vx * tx + vy * ty) / norm)
            scored.append((sc, a))
        scored.sort(key=lambda x: -x[0])
        return [a for _, a in scored]

    def play_level(
        self,
        get_obs: Callable[[], tuple[np.ndarray, Sequence[int], str, int]],
        step_fn: Callable[[dict[str, Any]], tuple[np.ndarray, Sequence[int], str, int]],
        reset_fn: Callable[[], tuple[np.ndarray, Sequence[int], str, int]],
        budget: int,
        start_level: int,
    ) -> dict[str, Any]:
        """Play one level up to `budget` real actions using live HUD-masked graph planning."""
        frame, avail, st_name, lvl = get_obs()
        if frame.shape != self.prior.hud_mask.shape:
            self.prior = GamePrior(frame.shape)

        # Level-local exact transition graph (Job 2)
        transitions: dict[str, dict[str, str]] = {}
        action_specs: dict[str, dict[str, dict[str, Any]]] = {}
        tried: dict[str, set[str]] = {}
        dead_edges: set[tuple[str, str]] = set()
        death_edges: set[tuple[str, str]] = set()
        visit_count: Counter[str] = Counter()
        visited_click_coords: Counter[tuple[int, int]] = Counter()
        state_frames: dict[str, tuple[np.ndarray, list[int]]] = {}

        cur_key = self.prior.world_key(frame)
        visit_count[cur_key] += 1
        last_action: str | None = None
        last_diff_center: tuple[float, float] | None = None
        player_pos: tuple[float, float] | None = None
        planned_path: deque[dict[str, Any]] = deque()
        # Extract distinct small/medium interior foreground objects at level start as navigation landmarks
        init_regs = extract_regions(frame)
        bg_c = max(Counter(r["color"] for r in init_regs for _ in range(min(r["area"], 500))).items(), key=lambda x: x[1])[0] if init_regs else 0
        landmarks: list[tuple[float, float]] = [
            (r["cx"], r["cy"]) for r in init_regs
            if r["color"] != bg_c and 2 <= r["area"] <= 140 and not r["edge_strip"] and 4 <= r["cy"] <= 59 and 4 <= r["cx"] <= 59
        ]
        visited_landmarks: set[int] = set()

        actions_used = 0
        resets_used = 0
        deaths = 0
        world_changes = 0
        no_ops = 0

        def ensure_state(key: str, fr: np.ndarray, av: Sequence[int]) -> None:
            if key not in action_specs:
                specs = self._offered_actions(fr, av)
                action_specs[key] = {s["action"]: s for s in specs}
                tried.setdefault(key, set())
                transitions.setdefault(key, {})
                state_frames[key] = (fr, list(av))

        def rehash_graph_after_hud_growth() -> None:
            """Re-merge states whose keys became identical once a border HUD bar was masked!"""
            nonlocal transitions, action_specs, tried, dead_edges, death_edges, visit_count, state_frames
            remap: dict[str, str] = {}
            for old_k, (fr, _) in list(state_frames.items()):
                remap[old_k] = self.prior.world_key(fr)
            new_trans: dict[str, dict[str, str]] = {}
            new_specs: dict[str, dict[str, dict[str, Any]]] = {}
            new_tried: dict[str, set[str]] = {}
            new_frames: dict[str, tuple[np.ndarray, list[int]]] = {}
            new_visits: Counter[str] = Counter()
            for old_k, nk in remap.items():
                if nk not in new_specs and old_k in action_specs:
                    new_specs[nk] = action_specs[old_k]
                    new_frames[nk] = state_frames[old_k]
                new_tried.setdefault(nk, set()).update(tried.get(old_k, ()))
                new_visits[nk] += visit_count.get(old_k, 0)
                t_row = new_trans.setdefault(nk, {})
                for act, dst in transitions.get(old_k, {}).items():
                    ndst = remap.get(dst, dst)
                    if ndst != nk:
                        t_row[act] = ndst
            dead_edges = {(remap.get(k, k), a) for k, a in dead_edges}
            death_edges = {(remap.get(k, k), a) for k, a in death_edges}
            transitions, action_specs, tried, state_frames, visit_count = new_trans, new_specs, new_tried, new_frames, new_visits

        def untried_for(key: str) -> list[dict[str, Any]]:
            specs = action_specs.get(key, {})
            tr = tried.get(key, set())
            return [
                s for act, s in specs.items()
                if act not in tr
                and (key, act) not in dead_edges
                and (key, act) not in death_edges
                and not (s["is_click"] and self.prior.is_dead_click_color(s["color_cls"]))
            ]

        def bfs_to_frontier(start_k: str, max_depth: int = 18) -> list[dict[str, Any]]:
            """Shortest path in G from start_k to the nearest state with an untried viable action."""
            q: deque[tuple[str, list[dict[str, Any]]]] = deque([(start_k, [])])
            seen_k = {start_k}
            while q:
                k, path = q.popleft()
                if len(path) >= max_depth:
                    continue
                for act, nxt in transitions.get(k, {}).items():
                    if nxt in seen_k or (k, act) in death_edges or (k, act) in dead_edges:
                        continue
                    spec = action_specs.get(k, {}).get(act)
                    if spec is None:
                        continue
                    npath = path + [spec]
                    if untried_for(nxt):
                        return npath
                    seen_k.add(nxt)
                    q.append((nxt, npath))
            return []

        ensure_state(cur_key, frame, avail)

        while actions_used < budget:
            if lvl > start_level or st_name == "WIN":
                break

            # If dead, pay 1 action for reset
            if st_name == "GAME_OVER":
                deaths += 1
                if actions_used >= budget:
                    break
                frame, avail, st_name, lvl = reset_fn()
                actions_used += 1
                resets_used += 1
                cur_key = self.prior.world_key(frame)
                ensure_state(cur_key, frame, avail)
                last_action = None
                planned_path.clear()
                continue

            # Choose next action: follow planned BFS path, else pick best untried here, else BFS!
            chosen: dict[str, Any] | None = None
            if planned_path:
                cand = planned_path.popleft()
                if cand["action"] in action_specs.get(cur_key, {}):
                    chosen = cand
                else:
                    planned_path.clear()

            if chosen is None:
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
                ranked = self._rank_untried(untried_here, last_action, last_diff_center, visited_click_coords, target_vec=tvec)
                if ranked:
                    chosen = ranked[0]
                else:
                    # Shortest path in live transition graph G to nearest unexplored state!
                    path = bfs_to_frontier(cur_key, max_depth=max(6, min(20, budget - actions_used - 1)))
                    if path:
                        planned_path.extend(path[1:])
                        chosen = path[0]
                    else:
                        # No frontier reachable: try any non-death/non-dead action at least visited, or reset!
                        fallbacks = [
                            s for act, s in action_specs.get(cur_key, {}).items()
                            if (cur_key, act) not in dead_edges and (cur_key, act) not in death_edges
                            and not (s["is_click"] and self.prior.is_dead_click_color(s["color_cls"]))
                        ]
                        if fallbacks and resets_used >= 2:
                            fallbacks.sort(key=lambda s: visit_count.get(transitions.get(cur_key, {}).get(s["action"], ""), 0))
                            chosen = fallbacks[0]
                        elif actions_used < budget - 1 and visit_count[cur_key] >= 1 and cur_key != next(iter(action_specs)):
                            # Reset back to level start to reach other branches
                            frame, avail, st_name, lvl = reset_fn()
                            actions_used += 1
                            resets_used += 1
                            cur_key = self.prior.world_key(frame)
                            ensure_state(cur_key, frame, avail)
                            last_action = None
                            planned_path.clear()
                            continue
                        elif fallbacks:
                            fallbacks.sort(key=lambda s: visit_count.get(transitions.get(cur_key, {}).get(s["action"], ""), 0))
                            chosen = fallbacks[0]
                        else:
                            # Absolute fallback: allow previously pruned click colors if everything failed
                            all_acts = list(action_specs.get(cur_key, {}).values())
                            if not all_acts:
                                break
                            chosen = all_acts[actions_used % len(all_acts)]

            # Execute chosen action
            prev_frame = frame
            prev_key = cur_key
            act_name = chosen["action"]
            frame, avail, st_name, lvl = step_fn(chosen)
            actions_used += 1
            if chosen["is_click"]:
                visited_click_coords[(chosen["x"], chosen["y"])] += 1

            if lvl > start_level or st_name == "WIN":
                self.prior.record_affordance(act_name, chosen["cls"], chosen["color_cls"], 100)
                break

            raw_px, world_px, mask_grew = self.prior.observe_diff(prev_frame, frame)
            if mask_grew:
                rehash_graph_after_hud_growth()
                prev_key = self.prior.world_key(prev_frame)
            elif raw_px > 0 and world_px == 0:
                prev_key = self.prior.world_key(prev_frame)
            next_key = self.prior.world_key(frame)

            tried.setdefault(prev_key, set()).add(act_name)
            self.prior.record_affordance(act_name, chosen["cls"], chosen["color_cls"], world_px)

            if st_name == "GAME_OVER":
                death_edges.add((prev_key, act_name))
                planned_path.clear()
                cur_key = next_key
                continue

            if world_px == 0 or next_key == prev_key:
                no_ops += 1
                dead_edges.add((prev_key, act_name))
                planned_path.clear()
                cur_key = prev_key
                ensure_state(cur_key, frame, avail)
                continue

            world_changes += 1
            diff_mask = (prev_frame != frame) & ~self.prior.hud_mask
            ys, xs = np.nonzero(diff_mask)
            if len(ys):
                new_center = (float(xs.mean()), float(ys.mean()))
                # Learn 2D motion vector (dx, dy) for discrete moves when a compact sprite shifts
                if not chosen["is_click"] and chosen["aid"] in (1, 2, 3, 4) and world_px <= 160:
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

            transitions.setdefault(prev_key, {})[act_name] = next_key
            # Detect inverse action pair online (`S0 --a--> S1 --b--> S0`)
            if last_action is not None and transitions.get(next_key, {}).get(last_action) == prev_key:
                if act_name != last_action:
                    self.prior.inv_action[last_action] = act_name
                    self.prior.inv_action[act_name] = last_action

            cur_key = next_key
            visit_count[cur_key] += 1
            ensure_state(cur_key, frame, avail)
            last_action = act_name

        return {
            "solved": (lvl > start_level or st_name == "WIN"),
            "actions_used": actions_used,
            "resets_used": resets_used,
            "deaths": deaths,
            "world_changes": world_changes,
            "no_ops": no_ops,
            "unique_world_states": len(action_specs),
            "hud_pixels_found": int(np.count_nonzero(self.prior.hud_mask)),
        }
