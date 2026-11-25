"""Zero-Model OSWorld 2.1 Policy Provider for BrainOSWorldAgentV8 (0 Neural Weights, 0 VLMs).

Wires Project Brain's pure-canvas framebuffer perception (`extract_canvas_regions` /
`diff_framebuffers`), accessibility-tree parsing, and persistent `ExternalCausalLawStore`
directly into `BrainOSWorldAgentV8`:
  1. Pure-stdlib PNG RGB/RGBA decoder (zero PIL/numpy/torch dependency) with stride
     downsampling + exact screen-coordinate rescaling;
  2. Multi-modal deterministic targeting: External L2 memory recall -> A11y tree -> pure-canvas
     foreground widget tomography (works even when `accessibility_tree` is completely absent!);
  3. Live differential visual tomography: compares consecutive screenshots to learn causal
     GUI transitions into `ExternalCausalLawStore` and prune no-op coordinates;
  4. Strict `PROJECT_BRAIN_OSWORLD_V21_GUI_GOAL_EVIDENCE_V1` receipt generation so
     `BrainOSWorldAgentV8` ONLY accepts `DONE` on independently verified current-state evidence.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import struct
import xml.etree.ElementTree as ET
import zlib
from typing import Any, Callable, Mapping, Sequence

from canonical.swe_kernel import universal_computer_agent_v1 as uca

SCHEMA = "PROJECT_BRAIN_OSWORLD_V21_ZERO_MODEL_POLICY_V1"
GOAL_EVIDENCE_SCHEMA = "PROJECT_BRAIN_OSWORLD_V21_GUI_GOAL_EVIDENCE_V1"
PRODUCER_MODEL_CALLS = 0


def encode_rgb_to_png(rgb_grid: Sequence[Sequence[tuple[int, int, int]]]) -> bytes:
    """Pure-stdlib 8-bit RGB PNG encoder (for deterministic synthetic screenshots & testing)."""
    height = len(rgb_grid)
    width = len(rgb_grid[0]) if height else 0

    def _chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    raw_rows = bytearray()
    for row in rgb_grid:
        raw_rows.append(0)  # Filter type 0 (None)
        for r, g, b in row:
            raw_rows.extend((int(r) & 0xFF, int(g) & 0xFF, int(b) & 0xFF))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(bytes(raw_rows), level=6))
        + _chunk(b"IEND", b"")
    )


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def decode_png_to_rgb(
    png_bytes: bytes, *, max_dim: int = 160
) -> tuple[list[list[tuple[int, int, int]]], int, int, float, float]:
    """Pure-stdlib 8-bit RGB/RGBA/Grayscale PNG decoder with optional stride downsampling.

    Returns `(rgb_grid, orig_width, orig_height, scale_x, scale_y)` where screen coordinate
    `(x_screen, y_screen) = (int(cx * scale_x), int(cy * scale_y))`.
    """
    if len(png_bytes) < 24 or not png_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return [], 0, 0, 1.0, 1.0
    pos = 8
    width = height = bit_depth = color_type = 0
    idat_parts: list[bytes] = []
    while pos + 8 <= len(png_bytes):
        length, ctype = struct.unpack(">I4s", png_bytes[pos : pos + 8])
        data = png_bytes[pos + 8 : pos + 8 + length]
        pos += 12 + length
        if ctype == b"IHDR" and len(data) >= 13:
            width, height, bit_depth, color_type = struct.unpack(">IIBB", data[:10])
        elif ctype == b"IDAT":
            idat_parts.append(data)
        elif ctype == b"IEND":
            break

    if width <= 0 or height <= 0 or bit_depth != 8 or color_type not in (0, 2, 6):
        return [], width, height, 1.0, 1.0

    bpp = {0: 1, 2: 3, 6: 4}[color_type]
    stride = width * bpp
    raw = zlib.decompress(b"".join(idat_parts))
    if len(raw) < height * (1 + stride):
        return [], width, height, 1.0, 1.0

    # Reconstruct scanlines (PNG filters 0..4)
    recon = bytearray(height * stride)
    for y in range(height):
        f_type = raw[y * (1 + stride)]
        row_in = raw[y * (1 + stride) + 1 : (y + 1) * (1 + stride)]
        row_off = y * stride
        prev_off = (y - 1) * stride
        for i in range(stride):
            x_val = row_in[i]
            a = recon[row_off + i - bpp] if i >= bpp else 0
            b = recon[prev_off + i] if y > 0 else 0
            c = recon[prev_off + i - bpp] if (y > 0 and i >= bpp) else 0
            if f_type == 0:
                v = x_val
            elif f_type == 1:
                v = (x_val + a) & 0xFF
            elif f_type == 2:
                v = (x_val + b) & 0xFF
            elif f_type == 3:
                v = (x_val + ((a + b) >> 1)) & 0xFF
            elif f_type == 4:
                v = (x_val + _paeth(a, b, c)) & 0xFF
            else:
                v = x_val
            recon[row_off + i] = v

    step_x = max(1, (width + max_dim - 1) // max_dim)
    step_y = max(1, (height + max_dim - 1) // max_dim)
    grid: list[list[tuple[int, int, int]]] = []
    for y in range(0, height, step_y):
        row_off = y * stride
        row_rgb: list[tuple[int, int, int]] = []
        for x in range(0, width, step_x):
            off = row_off + x * bpp
            if bpp == 1:
                g = recon[off]
                row_rgb.append((g, g, g))
            else:
                row_rgb.append((recon[off], recon[off + 1], recon[off + 2]))
        grid.append(row_rgb)

    scale_x = width / max(1, len(grid[0])) if grid else 1.0
    scale_y = height / max(1, len(grid)) if grid else 1.0
    return grid, width, height, scale_x, scale_y


def parse_a11y_nodes(a11y_tree: Any) -> list[dict[str, Any]]:
    """Parse XML or JSON OSWorld accessibility tree into clickable node dicts with centers."""
    nodes: list[dict[str, Any]] = []
    if not a11y_tree:
        return nodes
    if isinstance(a11y_tree, Mapping):
        raw_list = list(a11y_tree.get("nodes") or [])
        if not raw_list and any(k in a11y_tree for k in ("name", "text", "bbox")):
            raw_list = [a11y_tree]
        for nd in raw_list:
            if not isinstance(nd, Mapping):
                continue
            bbox = nd.get("bbox")
            if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
                x0, y0, x1, y1 = (int(v) for v in bbox)
                nodes.append(
                    {
                        "name": str(nd.get("name") or ""),
                        "role": str(nd.get("role") or ""),
                        "text": str(nd.get("text") or ""),
                        "bbox": (x0, y0, x1, y1),
                        "cx": (x0 + x1) // 2,
                        "cy": (y0 + y1) // 2,
                    }
                )
        return nodes

    if isinstance(a11y_tree, str) and "<" in a11y_tree:
        try:
            root = ET.fromstring(a11y_tree)
        except ET.ParseError:
            return nodes
        for el in root.iter():
            attrs = el.attrib
            # Support both `screencoord="(x, y)" size="(w, h)"` (AT-SPI Linux) and `bbox="x0,y0,x1,y1"`
            cx = cy = -1
            bbox_t: tuple[int, int, int, int] | None = None
            sc = next((v for k, v in attrs.items() if k.endswith("screencoord")), "")
            sz = next((v for k, v in attrs.items() if k.endswith("size")), "")
            if sc and sz:
                ms = re.findall(r"-?\d+", sc)
                mz = re.findall(r"-?\d+", sz)
                if len(ms) >= 2 and len(mz) >= 2:
                    x0, y0, w, h = int(ms[0]), int(ms[1]), int(mz[0]), int(mz[1])
                    if w > 0 and h > 0:
                        bbox_t = (x0, y0, x0 + w, y0 + h)
                        cx, cy = x0 + w // 2, y0 + h // 2
            elif "bbox" in attrs:
                mb = re.findall(r"-?\d+", attrs["bbox"])
                if len(mb) >= 4:
                    x0, y0, x1, y1 = (int(v) for v in mb[:4])
                    bbox_t = (x0, y0, x1, y1)
                    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
            name = str(attrs.get("name") or "").strip()
            text = str(el.text or attrs.get("text") or "").strip()
            if bbox_t and cx >= 0 and cy >= 0 and (name or text):
                nodes.append(
                    {
                        "name": name,
                        "role": str(el.tag.split("}")[-1]),
                        "text": text,
                        "bbox": bbox_t,
                        "cx": cx,
                        "cy": cy,
                    }
                )
    return nodes


class ZeroModelOSWorldPolicy:
    """Zero-model, state-conditioned OSWorld 2.1 policy provider for `BrainOSWorldAgentV8`.

    Strictly 0 external model calls (`PRODUCER_MODEL_CALLS = 0`).
    Combines:
      - External L2 persistent GUI transition memory (`ExternalCausalLawStore`)
      - Accessibility-tree deterministic targeting (`parse_a11y_nodes`)
      - Pure-canvas RGB widget segmentation & differential tomography (`extract_canvas_regions`, `diff_framebuffers`)
      - Explicit deterministic current-state goal verification (`PROJECT_BRAIN_OSWORLD_V21_GUI_GOAL_EVIDENCE_V1`)
    """

    def __init__(
        self,
        *,
        law_store_path: str | pathlib.Path | None = None,
        visual_goal_verifier: Callable[[Sequence[Sequence[tuple[int, int, int]]]], bool] | None = None,
        a11y_goal_verifier: Callable[[Sequence[Mapping[str, Any]]], bool] | None = None,
    ) -> None:
        self.store = uca.ExternalCausalLawStore(law_store_path)
        self.visual_goal_verifier = visual_goal_verifier
        self.a11y_goal_verifier = a11y_goal_verifier
        self._prev_rgb: list[list[tuple[int, int, int]]] | None = None
        self._prev_frame_hash: str = ""
        self._prev_action: dict[str, Any] | None = None
        self._prev_instruction_sig: str = ""
        self._tried_actions_by_frame: dict[str, set[str]] = {}
        self._noop_actions_by_frame: dict[str, set[str]] = {}
        self._typed_payloads: set[str] = set()
        self._focused_input_coord: tuple[int, int] | None = None
        self.memory_recall_hits: int = 0
        self.visual_transitions_learned: int = 0
        self.noop_actions_pruned: int = 0

    def reset_episode(self) -> None:
        self._prev_rgb = None
        self._prev_frame_hash = ""
        self._prev_action = None
        self._prev_instruction_sig = ""
        self._tried_actions_by_frame = {}
        self._noop_actions_by_frame = {}
        self._typed_payloads = set()
        self._focused_input_coord = None

    @staticmethod
    def _action_key(act: Mapping[str, Any]) -> str:
        t = str(act.get("type") or "").upper()
        if t in ("CLICK", "DOUBLE_CLICK", "RIGHT_CLICK"):
            return f"{t}:{int(act.get('x') or 0)}:{int(act.get('y') or 0)}"
        if t == "TYPE":
            return f"TYPE:{act.get('text') or ''}"
        if t == "HOTKEY":
            return "HOTKEY:" + "+".join(str(k).lower() for k in (act.get("keys") or ()))
        if t == "PRESS":
            return f"PRESS:{str(act.get('key') or '').lower()}"
        return json.dumps(dict(act), sort_keys=True)

    @staticmethod
    def _extract_instruction_intents(instruction: str) -> dict[str, Any]:
        """Zero-model compositional extraction of TYPE payloads and HOTKEY/PRESS intents."""
        inst = instruction or ""
        type_texts: list[str] = []
        # Match quoted payloads following typing/entry/search verbs (or standalone quotes with type/enter/write/search)
        for m in re.finditer(
            r"""(?:type|enter|write|input|fill|search|rename|set\s+to|name\s+it)\s+(?:in\s+|into\s+)?['"]([^'"]{1,160})['"]""",
            inst,
            re.I,
        ):
            val = m.group(1)
            if val not in type_texts:
                type_texts.append(val)
        hotkeys: list[list[str]] = []
        for m in re.finditer(
            r"\b((?:ctrl|control|alt|shift|super|cmd|meta)(?:\s*\+\s*[a-z0-9_]+)+)\b",
            inst,
            re.I,
        ):
            parts = [p.strip().lower() for p in re.split(r"\s*\+\s*", m.group(1)) if p.strip()]
            norm = ["ctrl" if p == "control" else ("win" if p in ("super", "meta") else p) for p in parts]
            if len(norm) >= 2 and norm not in hotkeys:
                hotkeys.append(norm)
        press_keys: list[str] = []
        for m in re.finditer(r"\bpress\s+(enter|return|tab|escape|esc|backspace|delete|space)\b", inst, re.I):
            k = m.group(1).lower()
            k = "enter" if k == "return" else ("esc" if k == "escape" else k)
            if k not in press_keys:
                press_keys.append(k)
        return {"type_texts": type_texts, "hotkeys": hotkeys, "press_keys": press_keys}

    def _goal_sig(self, instruction: str) -> str:
        norm = " ".join(re.findall(r"[a-z0-9]+", (instruction or "").lower()))
        return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:12]

    def _record_visual_transition(
        self,
        curr_rgb: list[list[tuple[int, int, int]]],
        curr_hash: str,
        *,
        goal_reached: bool,
    ) -> None:
        if self._prev_rgb is None or self._prev_action is None or not self._prev_frame_hash:
            return
        if not curr_rgb or len(curr_rgb) != len(self._prev_rgb):
            return
        diff = uca.diff_framebuffers(self._prev_rgb, curr_rgb)
        changed = int(diff.get("changed_pixels") or 0)
        act_key = self._action_key(self._prev_action)
        if changed > 0 or goal_reached:
            act_type = str(self._prev_action.get("type") or "CLICK").upper()
            act_json = json.dumps(self._prev_action, sort_keys=True)
            lid = f"osw_gui::{hashlib.sha256(f'{self._prev_instruction_sig}:{self._prev_frame_hash}:{act_key}'.encode()).hexdigest()[:10]}"
            cmd_tmpl = (
                [act_type, str(int(self._prev_action.get("x") or 0)), str(int(self._prev_action.get("y") or 0))]
                if act_type in ("CLICK", "DOUBLE_CLICK", "RIGHT_CLICK")
                else [act_type, act_json]
            )
            law = uca.ParameterizedCausalLaw(
                law_id=lid,
                domain="osworld_gui",
                tool_or_action=act_type,
                command_template=cmd_tmpl,
                preconditions={
                    "goal_sig": self._prev_instruction_sig,
                    "frame_hash": self._prev_frame_hash,
                },
                effects={
                    "after_frame_hash": curr_hash,
                    "changed_pixels": changed,
                    "goal_reached": bool(goal_reached),
                    "action_payload": dict(self._prev_action),
                },
                provenance={"action_key": act_key, "changed_pixels": changed},
                generalized=True,
            )
            self.store.admit(law)
            self.visual_transitions_learned += 1
        elif curr_hash == self._prev_frame_hash:
            # Record L3 local no-op coordinate/action pruning so we never repeat dead elements on this frame!
            self._noop_actions_by_frame.setdefault(self._prev_frame_hash, set()).add(act_key)
            self.noop_actions_pruned += 1

    def _recall_l2_gui_action(self, goal_sig: str, frame_hash: str) -> dict[str, Any] | None:
        """Query ExternalCausalLawStore for a verified GUI transition on `(goal_sig, frame_hash)`."""
        best: uca.ParameterizedCausalLaw | None = None
        for law in self.store.active_laws(domain="osworld_gui"):
            pre = law.preconditions or {}
            if pre.get("goal_sig") == goal_sig and pre.get("frame_hash") == frame_hash:
                if (law.effects or {}).get("goal_reached"):
                    best = law
                    break
                if best is None:
                    best = law
        if best is None:
            return None
        payload = (best.effects or {}).get("action_payload")
        if isinstance(payload, Mapping) and payload.get("type"):
            recalled = dict(payload)
        elif len(best.command_template) >= 3 and best.command_template[0] in ("CLICK", "DOUBLE_CLICK", "RIGHT_CLICK"):
            recalled = {
                "type": best.command_template[0],
                "x": int(best.command_template[1]),
                "y": int(best.command_template[2]),
            }
        elif len(best.command_template) >= 2:
            try:
                recalled = json.loads(best.command_template[1])
            except Exception:
                return None
        else:
            return None
        self.memory_recall_hits += 1
        recalled["_recalled_law_id"] = best.law_id
        return recalled

    def __call__(self, state: Mapping[str, Any]) -> Mapping[str, Any]:
        instruction = str(state.get("instruction") or "")
        shot_bytes = bytes(state.get("screenshot_bytes") or b"")
        shot_sha = str(state.get("screenshot_sha256") or hashlib.sha256(shot_bytes).hexdigest())
        goal_sig = self._goal_sig(instruction)

        rgb_grid, orig_w, orig_h, scale_x, scale_y = decode_png_to_rgb(shot_bytes)
        frame_hash = uca.hash_framebuffer(rgb_grid) if rgb_grid else shot_sha[:16]
        a11y_nodes = parse_a11y_nodes(state.get("a11y_tree"))

        # 1. Explicit Current-State Deterministic Goal Verification
        goal_pass = False
        evidence_basis = ""
        if self.a11y_goal_verifier is not None and a11y_nodes:
            try:
                if bool(self.a11y_goal_verifier(a11y_nodes)):
                    goal_pass = True
                    evidence_basis = "EXPLICIT_CURRENT_A11Y_PREDICATE"
            except Exception:
                goal_pass = False
        if not goal_pass and self.visual_goal_verifier is not None and rgb_grid:
            try:
                if bool(self.visual_goal_verifier(rgb_grid)):
                    goal_pass = True
                    evidence_basis = "EXPLICIT_CURRENT_VISUAL_PREDICATE"
            except Exception:
                goal_pass = False

        # 2. Record differential visual transition from previous action -> ExternalCausalLawStore!
        self._record_visual_transition(rgb_grid, frame_hash, goal_reached=goal_pass)

        if goal_pass:
            pred_sha = hashlib.sha256(f"{evidence_basis}:{goal_sig}:{shot_sha}".encode("utf-8")).hexdigest()
            return {
                "response": f"Verified goal completion via {evidence_basis} (0 model calls).",
                "actions": [{"type": "DONE"}],
                "_goal_evidence": {
                    "schema": GOAL_EVIDENCE_SCHEMA,
                    "pass": True,
                    "basis": evidence_basis,
                    "current_screenshot_sha256": shot_sha,
                    "predicate_sha256": pred_sha,
                    "task_specific_policy_data": False,
                    "external_model_dependency": False,
                },
                "_policy_receipt": {
                    "schema": SCHEMA,
                    "model_calls": 0,
                    "memory_recall_hits": self.memory_recall_hits,
                    "visual_transitions_learned": self.visual_transitions_learned,
                },
            }

        tried = self._tried_actions_by_frame.setdefault(frame_hash, set())
        noops = self._noop_actions_by_frame.get(frame_hash, set())
        intents = self._extract_instruction_intents(instruction)

        def _commit(act_dict: dict[str, Any], resp_txt: str, receipt: dict[str, Any]) -> Mapping[str, Any]:
            akey = self._action_key(act_dict)
            tried.add(akey)
            if act_dict.get("type") == "TYPE":
                self._typed_payloads.add(str(act_dict.get("text") or ""))
            self._prev_rgb = rgb_grid
            self._prev_frame_hash = frame_hash
            self._prev_action = dict(act_dict)
            self._prev_instruction_sig = goal_sig
            return {
                "response": resp_txt,
                "actions": [act_dict],
                "_policy_receipt": receipt,
            }

        # 3. 1-Shot L2 Memory Recall from ExternalCausalLawStore (supports CLICK/TYPE/HOTKEY/PRESS!)
        recalled = self._recall_l2_gui_action(goal_sig, frame_hash)
        if recalled is not None:
            law_id = str(recalled.pop("_recalled_law_id", ""))
            akey = self._action_key(recalled)
            if akey not in tried and akey not in noops:
                return _commit(
                    recalled,
                    f"Replaying verified L2 GUI law {law_id} ({akey}).",
                    {"schema": SCHEMA, "source": "L2_GUI_MEMORY_1SHOT", "law_id": law_id, "model_calls": 0},
                )

        # 4. Channel 1: Compositional Multi-Step Intent + Accessibility-Tree Targeting
        input_roles = {"entry", "text", "textbox", "input", "searchbox", "combobox", "password-text"}
        inst_tokens = {t.lower() for t in re.findall(r"[a-zA-Z0-9_]{3,}", instruction)}
        pending_texts = [t for t in intents["type_texts"] if t not in self._typed_payloads]

        # 4a. If a text payload is pending AND an input field was just clicked (focused), emit TYPE!
        if pending_texts and self._focused_input_coord is not None:
            act_type = {"type": "TYPE", "text": pending_texts[0]}
            if self._action_key(act_type) not in tried:
                self._focused_input_coord = None
                return _commit(
                    act_type,
                    f"Typing instruction payload '{pending_texts[0]}' into focused field.",
                    {"schema": SCHEMA, "source": "MULTI_STEP_TYPE_INTENT", "model_calls": 0},
                )

        # 4b. If a text payload is pending and an A11y input/entry field is visible, focus it first!
        if pending_texts and a11y_nodes:
            best_inp: tuple[int, dict[str, Any]] | None = None
            for nd in a11y_nodes:
                if str(nd.get("role") or "").lower() not in input_roles:
                    continue
                act_c = {"type": "CLICK", "x": int(nd["cx"]), "y": int(nd["cy"])}
                akey = self._action_key(act_c)
                if akey in tried or akey in noops:
                    continue
                nd_tokens = {t.lower() for t in re.findall(r"[a-zA-Z0-9_]{3,}", f"{nd['name']} {nd['text']}")}
                score = 10 + len(inst_tokens & nd_tokens)
                if best_inp is None or score > best_inp[0]:
                    best_inp = (score, nd)
            if best_inp is not None:
                nd = best_inp[1]
                cx, cy = int(nd["cx"]), int(nd["cy"])
                self._focused_input_coord = (cx, cy)
                return _commit(
                    {"type": "CLICK", "x": cx, "y": cy},
                    f"Focusing A11y input field '{nd['name'] or nd['role']}' at ({cx}, {cy}) before typing.",
                    {"schema": SCHEMA, "source": "A11Y_INPUT_FOCUS", "model_calls": 0},
                )

        # 4c. If all text payloads are typed (or none requested), check explicit HOTKEY / PRESS intents!
        if not pending_texts:
            for hk in intents["hotkeys"]:
                act_hk = {"type": "HOTKEY", "keys": list(hk)}
                akey = self._action_key(act_hk)
                if akey not in tried and akey not in noops:
                    return _commit(
                        act_hk,
                        f"Executing instruction hotkey {'+'.join(hk)}.",
                        {"schema": SCHEMA, "source": "MULTI_STEP_HOTKEY_INTENT", "model_calls": 0},
                    )
            for pk in intents["press_keys"]:
                act_pk = {"type": "PRESS", "key": pk}
                akey = self._action_key(act_pk)
                if akey not in tried and akey not in noops:
                    return _commit(
                        act_pk,
                        f"Pressing instruction key '{pk}'.",
                        {"schema": SCHEMA, "source": "MULTI_STEP_PRESS_INTENT", "model_calls": 0},
                    )

        # 4d. General Accessibility-Tree deterministic node matching (buttons, menus, tabs, checkboxes)
        best_a11y: tuple[int, dict[str, Any]] | None = None
        for nd in a11y_nodes:
            act_c = {"type": "CLICK", "x": int(nd["cx"]), "y": int(nd["cy"])}
            akey = self._action_key(act_c)
            if akey in tried or akey in noops:
                continue
            nd_tokens = {t.lower() for t in re.findall(r"[a-zA-Z0-9_]{3,}", f"{nd['name']} {nd['text']}")}
            ov = len(inst_tokens & nd_tokens)
            if ov > 0 and (best_a11y is None or ov > best_a11y[0]):
                best_a11y = (ov, nd)
        if best_a11y is not None:
            nd = best_a11y[1]
            cx, cy = int(nd["cx"]), int(nd["cy"])
            return _commit(
                {"type": "CLICK", "x": cx, "y": cy},
                f"Clicking A11y target '{nd['name'] or nd['text']}' at ({cx}, {cy}).",
                {"schema": SCHEMA, "source": "A11Y_TREE_MATCH", "model_calls": 0},
            )

        # 5. Channel 2: Pure-Canvas RGB Framebuffer Widget Segmentation (`extract_canvas_regions`)
        if rgb_grid:
            regions = uca.extract_canvas_regions(rgb_grid, min_area=4)
            for reg in regions:
                sx = max(0, min(1919, int(round(reg.cx * scale_x))))
                sy = max(0, min(1079, int(round(reg.cy * scale_y))))
                act_c = {"type": "CLICK", "x": sx, "y": sy}
                akey = self._action_key(act_c)
                if akey in tried or akey in noops:
                    continue
                return _commit(
                    act_c,
                    f"Pure-canvas tomography probing foreground region #{reg.region_id} at ({sx}, {sy}).",
                    {
                        "schema": SCHEMA,
                        "source": "PURE_CANVAS_TOMOGRAPHY",
                        "region_id": reg.region_id,
                        "regions_detected": len(regions),
                        "model_calls": 0,
                    },
                )

        return {
            "response": "No unprobed interactive target remaining; emitting WAIT.",
            "actions": [{"type": "WAIT"}],
            "_policy_receipt": {"schema": SCHEMA, "source": "EXHAUSTED_WAIT", "model_calls": 0},
        }
