#!/usr/bin/env python3
"""Unified Interface Action-Grammar Engine (CLI Repertoire + GUI/Browser A11y Tree).

Every structured computer interface publishes an action grammar:
  1. OS / CLI programs publish `Usage:` slots, typed carrier flags, summary/option verbs,
     and refusal sentences (`--help`).
  2. GUI / Browser applications publish W3C ARIA / AT-SPI Accessibility Trees:
     `(role, accessible_name, value, states, options, bounds)`.

This module unifies both under one zero-model, zero-parameter epistemic mechanism and
closes the three gaps named at the end of `THE_GUIDE_IS_AN_ACTION_GRAMMAR_20261124_V1.md`:
  - Unseen CLI rooms & content-addressed grammar memory keyed by `sha256(binary)[:16]:name`
    plus generalized refusal-switch memory (with automatic refutation on failure).
  - Real HTML/DOM -> W3C ARIA Accessibility Tree compiler + multi-step planner + execution
    verifier + OSWorld `pyautogui` action lowering (`osworld_computer_surface_v1`).
  - Lying-ARIA / `ACCEPTED_INERT` detection (when `<div role="button">` has no handler and
    leaves the accessibility tree unchanged, the affordance is refuted in-place and the
    search routes through working controls or multi-step tab/disclosure prerequisites).
  - Generalized semantic workflow memory (`role + slot_tokens + verb`, parameterized by
    goal arguments -- never coordinates or DOM indices), with active refutation when an
    environment changes its precondition contract.

Model calls: 0. Stored world-fact weights: 0. Runtime network: 0. Authority: NONE.
"""
from __future__ import annotations

import copy
import hashlib
import html.parser
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOLS = ROOT / "canonical" / "tools"
for _p in (str(ROOT), str(TOOLS)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from canonical.runtime import osworld_computer_surface_v1 as osworld_surface  # noqa: E402
import the_guide_is_an_action_grammar_v1 as cli_grammar  # noqa: E402

SCHEMA = "PROJECT_BRAIN_INTERFACE_ACTION_GRAMMAR_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"


# =========================================================================== #
# PART 1: CONTENT-ADDRESSED CLI GRAMMAR + REFUTABLE REFUSAL MEMORY
# =========================================================================== #

def binary_identity_key(program: str) -> str | None:
    """`sha256(binary)[:16]:invoked_name` -- distinguishes multicall symlinks (`xz` vs `unxz`)
    and invalidates automatically if the binary on disk is upgraded or replaced."""
    resolved_path = shutil.which(program)
    if not resolved_path:
        return None
    try:
        digest = hashlib.sha256(pathlib.Path(resolved_path).read_bytes()).hexdigest()[:16]
    except OSError:
        return None
    invoked = os.path.basename(program)
    return f"{digest}:{invoked}"


class CLIGrammarMemory:
    """External, inspectable, refutable store for parsed CLI grammars & learned refusal flags."""

    def __init__(self) -> None:
        # key = "<sha256_16>:<invoked_name>" -> serializable page dict
        self.pages_by_key: dict[str, dict[str, Any]] = {}
        # key = "<sha256_16>:<invoked_name>:<verb>:<refusal_form>" -> {"flag": ..., "uses": ..., "refutations": ...}
        self.refusal_repairs: dict[str, dict[str, Any]] = {}

    def lookup_page(self, program: str) -> tuple[str | None, dict[str, Any] | None]:
        key = binary_identity_key(program)
        if key is None:
            return None, None
        cached = self.pages_by_key.get(key)
        return key, (copy.deepcopy(cached) if cached is not None else None)

    def store_page(self, key: str, page: Mapping[str, Any]) -> None:
        serializable = {
            "program": page["program"],
            "subcommand": page.get("subcommand"),
            "ok": bool(page.get("ok")),
            "reason": page.get("reason"),
            "read_seconds": page.get("read_seconds", 0.0),
            "synopsis": page["synopsis"],
            "declared": page["declared"],
            "roles": page["roles"],
            "checks": page["checks"],
            # Do NOT store 200KB raw `--help` prose in persistent memory ("best part is no part"):
            # only the extracted structural grammar is needed for compilation and edges.
            "raw": "",
        }
        self.pages_by_key[key] = serializable

    def record_refusal_repair(
        self, binary_key: str, verb: str, form: str, flag: str
    ) -> None:
        rkey = f"{binary_key}:{verb}:{form}"
        row = self.refusal_repairs.get(rkey) or {
            "binary_key": binary_key,
            "verb": verb,
            "form": form,
            "flag": flag,
            "successes": 0,
            "refutations": 0,
        }
        row["flag"] = flag
        row["successes"] = int(row.get("successes", 0)) + 1
        self.refusal_repairs[rkey] = row

    def learned_flag_for(self, binary_key: str, verb: str) -> str | None:
        for rkey, row in self.refusal_repairs.items():
            if (
                row.get("binary_key") == binary_key
                and row.get("verb") == verb
                and int(row.get("refutations", 0)) == 0
                and int(row.get("successes", 0)) > 0
            ):
                return str(row["flag"])
        return None

    def refute_repair(self, binary_key: str, verb: str, flag: str) -> int:
        count = 0
        for row in self.refusal_repairs.values():
            if (
                row.get("binary_key") == binary_key
                and row.get("verb") == verb
                and row.get("flag") == flag
            ):
                row["refutations"] = int(row.get("refutations", 0)) + 1
                count += 1
        return count

    def save(self, path: pathlib.Path | str) -> None:
        p = pathlib.Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": SCHEMA + "_CLI_MEMORY",
            "pages_by_key": self.pages_by_key,
            "refusal_repairs": self.refusal_repairs,
        }
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(p)

    @classmethod
    def load(cls, path: pathlib.Path | str) -> "CLIGrammarMemory":
        mem = cls()
        p = pathlib.Path(path)
        if not p.is_file():
            return mem
        raw = json.loads(p.read_text(encoding="utf-8"))
        mem.pages_by_key = dict(raw.get("pages_by_key") or {})
        mem.refusal_repairs = dict(raw.get("refusal_repairs") or {})
        return mem


def survey_with_memory(
    names: Sequence[str],
    memory: CLIGrammarMemory,
    *,
    wall_budget: float = 60.0,
) -> dict[str, Any]:
    """Read CLI pages with content-addressed caching: unchanged binaries cost 0 subprocesses."""
    started = time.perf_counter()
    pages: dict[str, Any] = {}
    probed = 0
    recalled = 0
    for name in names:
        if time.perf_counter() - started > wall_budget:
            break
        key, cached = memory.lookup_page(name)
        if key is None:
            continue
        if cached is not None:
            recalled += 1
            if cached.get("ok") and cached["synopsis"].get("ok"):
                pages[name] = cached
            continue
        probed += 1
        page = cli_grammar.page_of(name)
        memory.store_page(key, page)
        if page["ok"] and page["synopsis"]["ok"]:
            pages[name] = page
    return {
        "pages": pages,
        "probed": probed,
        "recalled_from_memory": recalled,
        "seconds": round(time.perf_counter() - started, 4),
    }


def solve_cli_need(
    need: Mapping[str, Any],
    root: pathlib.Path,
    *,
    memory: CLIGrammarMemory | None = None,
    candidate_programs: Sequence[str] | None = None,
    depth: int = 2,
) -> dict[str, Any]:
    """Solve a natural-language file/archive/transform need in an arbitrary unseen `root`."""
    started = time.perf_counter()
    memory = memory if memory is not None else CLIGrammarMemory()
    names = list(candidate_programs) if candidate_programs is not None else cli_grammar.executable_names()
    survey_out = survey_with_memory(names, memory)
    pages = survey_out["pages"]
    edges, _ = cli_grammar.graph(pages)

    # Inject any non-refuted learned refusal switch into matching edges before compiling!
    for edge in edges:
        bkey = binary_identity_key(edge["program"])
        if bkey and not edge.get("flag"):
            learned_flag = memory.learned_flag_for(bkey, edge["verb"])
            if learned_flag and learned_flag in edge["page"]["declared"]:
                edge["flag"] = learned_flag
                edge["source"] = "flag"

    gate = cli_grammar.admissible(dict(need), root, pages)
    if not gate["admissible"]:
        return {
            "schema": SCHEMA,
            "status": "REFUSED__" + str(gate["reason"]),
            "pass": False,
            "probed": survey_out["probed"],
            "recalled_from_memory": survey_out["recalled_from_memory"],
            "seconds": round(time.perf_counter() - started, 4),
            "model_calls": 0,
        }

    room_kinds = set(cli_grammar.typed(root).values())
    weights = cli_grammar.idf(pages, cli_grammar.content_words(need["need"]))
    if need["target"] == "absent":
        found = cli_grammar.reachable_path(
            [e for e in edges if e["out_kind"] == "plain" and e["verb"] in ("remove", "rename")],
            room_kinds,
            "plain",
            depth=1,
            need=need["need"],
        )
    else:
        found = cli_grammar.reachable_path(
            edges, room_kinds, need["target"], depth=depth, need=need["need"], weights=weights
        )
    if not found:
        return {
            "schema": SCHEMA,
            "status": "REFUSED__NO_PATH_OF_DECLARED_TRANSITIONS",
            "pass": False,
            "probed": survey_out["probed"],
            "recalled_from_memory": survey_out["recalled_from_memory"],
            "seconds": round(time.perf_counter() - started, 4),
            "model_calls": 0,
        }

    budget = cli_grammar.Budget()
    for candidate in found["paths"][:cli_grammar.PATHS_TRIED]:
        if budget.left <= 0:
            break
        with tempfile.TemporaryDirectory(prefix="cli-try-") as tmp:
            sandbox = pathlib.Path(tmp) / "room"
            shutil.copytree(root, sandbox)
            attempt_row = cli_grammar.execute_path(
                candidate, dict(need), sandbox, exclude=(), budget=budget, rounds=3
            )
            if attempt_row["status"] == "PASS__GOAL_HELD":
                # Commit the verified state back to `root` and record any refusal repair learned!
                for child in list(root.iterdir()):
                    if child.is_dir() and not child.is_symlink():
                        shutil.rmtree(child)
                    else:
                        child.unlink()
                for child in sandbox.iterdir():
                    dest = root / child.name
                    if child.is_dir():
                        shutil.copytree(child, dest)
                    else:
                        shutil.copy2(child, dest)

                for step_row in attempt_row.get("steps") or []:
                    prog = step_row.get("program")
                    verb = step_row.get("verb")
                    bkey = binary_identity_key(prog) if prog else None
                    if not bkey or not verb:
                        continue
                    for att in step_row.get("attempts") or []:
                        clause = att.get("clause") or {}
                        if clause.get("flag") and clause.get("form"):
                            memory.record_refusal_repair(
                                bkey, verb, str(clause["form"]), str(clause["flag"])
                            )

                return {
                    "schema": SCHEMA,
                    "status": "PASS__GOAL_HELD",
                    "pass": True,
                    "path": attempt_row["path"],
                    "steps": attempt_row["steps"],
                    "created": attempt_row["created"],
                    "probed": survey_out["probed"],
                    "recalled_from_memory": survey_out["recalled_from_memory"],
                    "runs_spent": budget.spent,
                    "seconds": round(time.perf_counter() - started, 4),
                    "model_calls": 0,
                }

    return {
        "schema": SCHEMA,
        "status": "OPEN__NO_PATH_REACHED_THE_GOAL",
        "pass": False,
        "probed": survey_out["probed"],
        "recalled_from_memory": survey_out["recalled_from_memory"],
        "runs_spent": budget.spent,
        "seconds": round(time.perf_counter() - started, 4),
        "model_calls": 0,
    }


# =========================================================================== #
# PART 2: W3C ARIA / AT-SPI ACCESSIBILITY TREE AS AN ACTION GRAMMAR (ZERO VLM)
# =========================================================================== #

# W3C Core-AAM 1.2 role -> typed behavioral contract:
#   - verb: the state transition this widget performs
#   - needs_text: whether invoking it binds a value argument (`type`/`select`)
ROLE_GRAMMAR: dict[str, dict[str, Any]] = {
    "textbox": {"verb": "fill", "needs_value": True},
    "searchbox": {"verb": "fill", "needs_value": True},
    "spinbutton": {"verb": "fill", "needs_value": True},
    "combobox": {"verb": "select", "needs_value": True},
    "listbox": {"verb": "select", "needs_value": True},
    "checkbox": {"verb": "toggle", "needs_value": False},
    "switch": {"verb": "toggle", "needs_value": False},
    "radio": {"verb": "select_radio", "needs_value": False},
    "tab": {"verb": "activate_tab", "needs_value": False},
    "disclosure": {"verb": "expand", "needs_value": False},
    "button": {"verb": "invoke", "needs_value": False},
    "menuitem": {"verb": "invoke", "needs_value": False},
    "link": {"verb": "navigate", "needs_value": False},
}

_GUI_STOPWORDS = frozenset({
    "a", "an", "the", "to", "in", "on", "at", "for", "with", "and", "or", "then",
    "set", "change", "update", "enter", "type", "fill", "click", "press", "push",
    "tap", "select", "choose", "pick", "enable", "disable", "turn", "check",
    "uncheck", "open", "go", "into", "field", "box", "button", "tab", "page",
    "form", "please", "make", "sure", "is", "are", "be", "as", "by", "from", "of",
})


def _gui_tokens(text: str) -> list[str]:
    return [
        w for w in re.findall(r"[a-z0-9]+", (text or "").lower())
        if w not in _GUI_STOPWORDS and len(w) > 1
    ]


@dataclass
class A11yNode:
    """One accessible node extracted from HTML DOM or an AT-SPI / OSWorld tree."""

    node_id: str
    role: str
    name: str
    value: str = ""
    checked: bool | None = None
    expanded: bool | None = None
    selected: bool | None = None
    disabled: bool = False
    required: bool = False
    options: list[str] = field(default_factory=list)
    controls: str | None = None
    panel_id: str | None = None
    hidden: bool = False
    bounds: tuple[int, int, int, int] = (0, 0, 100, 32)  # (x, y, width, height)
    wired: bool = True  # False for broken `<div role="button">` with no handler

    def center(self) -> tuple[int, int]:
        x, y, w, h = self.bounds
        return (x + max(1, w) // 2, y + max(1, h) // 2)

    def as_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "role": self.role,
            "name": self.name,
            "value": self.value,
            "checked": self.checked,
            "expanded": self.expanded,
            "selected": self.selected,
            "disabled": self.disabled,
            "required": self.required,
            "options": list(self.options),
            "controls": self.controls,
            "panel_id": self.panel_id,
            "hidden": self.hidden,
            "bounds": list(self.bounds),
        }


class _HTMLToA11yParser(html.parser.HTMLParser):
    """Deterministic W3C HTML-AAM 1.0 + Accessible Name Computation parser (stdlib only)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.labels_by_for: dict[str, list[str]] = {}
        self._in_label_for: str | None = None
        self._raw_elements: list[dict[str, Any]] = []
        self._stack: list[dict[str, Any]] = []
        self._panel_stack: list[tuple[str, bool]] = []
        self._select_stack: dict[str, Any] | None = None
        self._current_option: list[str] | None = None
        self._option_selected: bool = False
        self._auto_idx = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        amap = {k.lower(): (v if v is not None else "") for k, v in attrs}
        t = tag.lower()
        role = self._compute_role(t, amap)

        # Track visibility containers with an exact 1-to-1 tag stack so close tags never drift
        is_hidden = ("hidden" in amap) or (amap.get("aria-hidden", "").lower() == "true")
        pushed_panel = False
        if t in ("div", "section", "fieldset", "form", "details"):
            parent_pid = self._panel_stack[-1][0] if self._panel_stack else ""
            parent_hidden = self._panel_stack[-1][1] if self._panel_stack else False
            if role is None:
                pid = amap.get("id") or parent_pid
                eff_hidden = (
                    True if (t == "details" and "open" not in amap)
                    else (parent_hidden or is_hidden)
                )
                if t == "details" and not amap.get("id"):
                    pid = f"details_{self._auto_idx}"
            else:
                # A leaf interactive widget (`<div role="button">`) belongs to its parent panel!
                pid = parent_pid
                eff_hidden = parent_hidden or is_hidden
            self._panel_stack.append((pid, eff_hidden, t))
            pushed_panel = True

        if t == "label" and amap.get("for"):
            self._in_label_for = amap["for"]
            self.labels_by_for.setdefault(self._in_label_for, [])
            return

        if t == "option" and self._select_stack is not None:
            self._current_option = []
            self._option_selected = "selected" in amap
            return

        if role is None:
            return

        self._auto_idx += 1
        nid = amap.get("id") or amap.get("name") or f"el_{self._auto_idx}"
        active_panels = self._panel_stack[:-1] if pushed_panel and role is not None else self._panel_stack
        panel_id = next((pid for pid, _, _ in reversed(active_panels) if pid), None)
        inherited_hidden = any(h for _, h, _ in active_panels)
        if t == "summary" and self._panel_stack:
            # <summary> itself is visible even when its <details> is closed!
            inherited_hidden = any(h for _, h, _ in self._panel_stack[:-1])

        bounds = self._parse_bounds(amap, self._auto_idx)
        # Native HTML interactive elements carry built-in browser behavior; custom ARIA
        # `<div role="button">` / `<span role="checkbox">` require an explicit handler
        # (`onclick` / `data-action` / `data-target` / `href`) -- absence is broken ARIA!
        native_interactive = t in ("button", "input", "select", "textarea", "a", "summary")
        has_handler = any(k in amap for k in ("onclick", "data-action", "data-target", "href"))
        wired = native_interactive or has_handler

        elem: dict[str, Any] = {
            "tag": t,
            "attrs": amap,
            "node_id": nid,
            "role": role,
            "text_parts": [],
            "options": [],
            "selected_option": "",
            "panel_id": panel_id,
            "hidden": is_hidden or inherited_hidden,
            "bounds": bounds,
            "wired": wired,
            "controls": amap.get("aria-controls") or amap.get("data-controls") or (
                self._panel_stack[-1][0] if t == "summary" and self._panel_stack else None
            ),
        }
        self._raw_elements.append(elem)
        if t == "select":
            self._select_stack = elem
        elif t not in ("input",):
            self._stack.append(elem)

    def handle_data(self, data: str) -> None:
        if self._in_label_for is not None:
            self.labels_by_for[self._in_label_for].append(data)
        if self._current_option is not None:
            self._current_option.append(data)
            return
        if self._stack:
            self._stack[-1]["text_parts"].append(data)

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t == "label":
            self._in_label_for = None
            return
        if t == "option" and self._select_stack is not None and self._current_option is not None:
            opt_text = " ".join("".join(self._current_option).split())
            if opt_text:
                self._select_stack["options"].append(opt_text)
                if self._option_selected or not self._select_stack["selected_option"]:
                    self._select_stack["selected_option"] = opt_text
            self._current_option = None
            return
        if t == "select":
            self._select_stack = None
            return
        if self._stack and self._stack[-1]["tag"] == t:
            self._stack.pop()
        if t in ("div", "section", "fieldset", "form", "details") and self._panel_stack:
            # Pop matching container frame if any
            self._panel_stack.pop()

    @staticmethod
    def _compute_role(tag: str, amap: Mapping[str, str]) -> str | None:
        explicit = amap.get("role", "").strip().lower()
        if explicit in ROLE_GRAMMAR:
            return explicit
        if tag == "button":
            return "button"
        if tag == "a" and "href" in amap:
            return "link"
        if tag == "textarea":
            return "textbox"
        if tag == "select":
            return "combobox"
        if tag == "summary":
            return "disclosure"
        if tag == "input":
            itype = amap.get("type", "text").strip().lower()
            if itype in ("text", "email", "password", "url", "tel"):
                return "textbox"
            if itype == "search":
                return "searchbox"
            if itype == "number":
                return "spinbutton"
            if itype == "checkbox":
                return "checkbox"
            if itype == "radio":
                return "radio"
            if itype in ("submit", "button", "reset"):
                return "button"
        return None

    @staticmethod
    def _parse_bounds(amap: Mapping[str, str], idx: int) -> tuple[int, int, int, int]:
        try:
            x = int(amap.get("data-x", 40))
            y = int(amap.get("data-y", 30 + idx * 44))
            w = int(amap.get("data-w", 180))
            h = int(amap.get("data-h", 32))
            return (x, y, w, h)
        except ValueError:
            return (40, 30 + idx * 44, 180, 32)

    def build_nodes(self) -> list[A11yNode]:
        nodes: list[A11yNode] = []
        for raw in self._raw_elements:
            amap = raw["attrs"]
            nid = raw["node_id"]
            role = raw["role"]
            label_text = " ".join("".join(self.labels_by_for.get(amap.get("id", ""), [])).split())
            inner_text = " ".join("".join(raw["text_parts"]).split())
            acc_name = (
                amap.get("aria-label")
                or label_text
                or amap.get("placeholder")
                or amap.get("title")
                or (amap.get("value") if raw["tag"] == "input" and role == "button" else "")
                or inner_text
                or nid
            ).strip()

            checked: bool | None = None
            if role in ("checkbox", "switch", "radio"):
                if "aria-checked" in amap:
                    checked = amap["aria-checked"].lower() == "true"
                else:
                    checked = "checked" in amap

            expanded: bool | None = None
            if role == "disclosure" or "aria-expanded" in amap:
                expanded = amap.get("aria-expanded", "false").lower() == "true"

            selected: bool | None = None
            if role == "tab":
                selected = amap.get("aria-selected", "false").lower() == "true"

            disabled = ("disabled" in amap) or (amap.get("aria-disabled", "").lower() == "true")
            required = ("required" in amap) or (amap.get("aria-required", "").lower() == "true")
            value = raw["selected_option"] if raw["tag"] == "select" else amap.get("value", "")

            nodes.append(
                A11yNode(
                    node_id=nid,
                    role=role,
                    name=acc_name,
                    value=value,
                    checked=checked,
                    expanded=expanded,
                    selected=selected,
                    disabled=disabled,
                    required=required,
                    options=list(raw["options"]),
                    controls=raw.get("controls"),
                    panel_id=raw.get("panel_id"),
                    hidden=bool(raw["hidden"]),
                    bounds=raw["bounds"],
                    wired=bool(raw["wired"]),
                )
            )
        return nodes


class A11yEnvironment:
    """Interactive GUI / Browser environment backed by a live Accessibility Tree.

    Supports real HTML documents OR pre-parsed AT-SPI node lists, deterministic state
    transitions (tabs, disclosures, inputs, selects, checkboxes, submit handlers, and
    realistic unwired ARIA decoys), snapshot/restore, and OSWorld `pyautogui` lowering.
    """

    def __init__(
        self,
        nodes: Sequence[A11yNode],
        *,
        screen: tuple[int, int] = (1280, 800),
        submit_effects: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> None:
        self._initial = [copy.deepcopy(n) for n in nodes]
        self.nodes: list[A11yNode] = [copy.deepcopy(n) for n in nodes]
        self.screen = osworld_surface.Screen(screen[0], screen[1])
        self.submit_effects = {k: dict(v) for k, v in (submit_effects or {}).items()}
        self.status_banner: str = ""
        self.navigated_url: str = ""
        self.pyautogui_log: list[str] = []

    @classmethod
    def from_html(
        cls,
        html_source: str,
        *,
        screen: tuple[int, int] = (1280, 800),
        submit_effects: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> "A11yEnvironment":
        parser = _HTMLToA11yParser()
        parser.feed(html_source)
        return cls(parser.build_nodes(), screen=screen, submit_effects=submit_effects)

    def reset(self) -> None:
        self.nodes = [copy.deepcopy(n) for n in self._initial]
        self.status_banner = ""
        self.navigated_url = ""
        self.pyautogui_log.clear()

    def snapshot_digest(self) -> str:
        payload = {
            "visible": [n.as_dict() for n in self.visible_nodes()],
            "banner": self.status_banner,
            "url": self.navigated_url,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def visible_nodes(self) -> list[A11yNode]:
        return [n for n in self.nodes if not n.hidden]

    def find_by_point(self, x: int, y: int) -> A11yNode | None:
        for n in reversed(self.visible_nodes()):
            bx, by, bw, bh = n.bounds
            if bx <= x < bx + bw and by <= y < by + bh:
                return n
        return None

    def act(self, action: Mapping[str, Any]) -> dict[str, Any]:
        """Execute a typed action (by `node_id` OR raw `(x, y)` coordinate) and lower to OSWorld."""
        before = self.snapshot_digest()
        target: A11yNode | None = None
        if "node_id" in action:
            target = next(
                (n for n in self.visible_nodes() if n.node_id == action["node_id"]),
                None,
            )
        elif "x" in action and "y" in action:
            target = self.find_by_point(int(action["x"]), int(action["y"]))

        if target is None or target.disabled:
            return {
                "accepted": False,
                "changed": False,
                "reason": "TARGET_NOT_VISIBLE_OR_DISABLED",
            }

        cx, cy = target.center()
        verb = str(action.get("verb") or ROLE_GRAMMAR.get(target.role, {}).get("verb") or "invoke")
        compiled_cmds: list[str] = []

        # Lowering to verified OSWorld pyautogui commands proves desktop surface compatibility!
        compiled_cmds.append(
            osworld_surface.compile_osworld_pyautogui({"type": "click", "x": cx, "y": cy}, self.screen)
        )
        if verb == "fill":
            val = str(action.get("value") or "")
            if val:
                compiled_cmds.append(
                    osworld_surface.compile_osworld_pyautogui({"type": "type", "text": val}, self.screen)
                )
        self.pyautogui_log.extend(compiled_cmds)

        # If the widget is unwired (`<div role="button">` with no handler), clicking it is INERT!
        if not target.wired:
            after = self.snapshot_digest()
            return {
                "accepted": True,
                "changed": before != after,
                "status": "ACCEPTED_INERT",
                "pyautogui": compiled_cmds,
            }

        if verb == "fill" and target.role in ("textbox", "searchbox", "spinbutton"):
            target.value = str(action.get("value") or "")
        elif verb == "toggle" and target.role in ("checkbox", "switch"):
            target.checked = not bool(target.checked)
        elif verb == "select_radio" and target.role == "radio":
            for other in self.nodes:
                if other.role == "radio" and other.panel_id == target.panel_id:
                    other.checked = False
            target.checked = True
        elif verb == "select" and target.role in ("combobox", "listbox"):
            val = str(action.get("value") or "")
            matched = next(
                (opt for opt in target.options if opt.lower() == val.lower() or val.lower() in opt.lower()),
                None,
            )
            if matched is None:
                return {"accepted": False, "changed": False, "reason": f"OPTION_NOT_DECLARED:{val}"}
            target.value = matched
        elif verb == "activate_tab" and target.role == "tab":
            for n in self.nodes:
                if n.role == "tab":
                    n.selected = (n.node_id == target.node_id)
                    if n.controls:
                        for child in self.nodes:
                            if child.panel_id == n.controls:
                                child.hidden = not n.selected
        elif verb == "expand" and target.controls:
            target.expanded = not bool(target.expanded)
            for child in self.nodes:
                if child.panel_id == target.controls:
                    child.hidden = not target.expanded
        elif verb in ("invoke", "navigate"):
            effect = self.submit_effects.get(target.node_id) or {}
            # Check required visible/form preconditions if declared
            req_missing = [
                n.node_id for n in self.nodes
                if n.required and not (n.value or n.checked)
            ]
            if req_missing and effect.get("respect_required", True):
                self.status_banner = f"ERROR: required field missing: {req_missing[0]}"
            else:
                if "reveal_panel" in effect:
                    for child in self.nodes:
                        if child.panel_id == effect["reveal_panel"]:
                            child.hidden = False
                if "banner" in effect:
                    self.status_banner = str(effect["banner"])
                elif target.role == "button":
                    self.status_banner = f"SUBMITTED:{target.name}"
                if "url" in effect:
                    self.navigated_url = str(effect["url"])

        after = self.snapshot_digest()
        changed = before != after
        return {
            "accepted": True,
            "changed": changed,
            "status": "ACCEPTED_CHANGED" if changed else "ACCEPTED_INERT",
            "pyautogui": compiled_cmds,
        }


# --------------------------------------------------------------------------- #
# Goal parsing & Generalized Workflow Memory (Role + Slot Tokens, NEVER (x,y))
# --------------------------------------------------------------------------- #

def parse_gui_goal(instruction: str) -> dict[str, Any]:
    """Extract quoted/literal values and clause-level intents from a natural-language goal.

    Zero LLM calls: extracts quoted strings, email/URL/number literals, boolean polarity
    (`enable`/`check` vs `disable`/`uncheck`), and clause tokens split on `and` / `then` / `,`.
    """
    clauses_raw = [
        c.strip() for c in re.split(r"\b(?:and then|then|and)\b|[;,]", instruction)
        if c.strip()
    ]
    clauses: list[dict[str, Any]] = []
    for raw in clauses_raw:
        quoted = re.findall(r"['\"]([^'\"]+)['\"]", raw)
        cleaned = re.sub(r"['\"][^'\"]+['\"]", " ", raw)
        emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", cleaned)
        urls = re.findall(r"https?://\S+", cleaned)
        numbers = re.findall(r"\b\d+(?:\.\d+)?\b", cleaned)
        value_lit = (quoted or emails or urls or numbers or [None])[0]
        if value_lit:
            cleaned = cleaned.replace(str(value_lit), " ")
        low = cleaned.lower()
        polarity: bool | None = None
        if value_lit is None:
            if re.search(r"\b(?:disable|uncheck|turn\s+off|off)\b", low):
                polarity = False
            elif re.search(r"\b(?:enable|check|turn\s+on|activate)\b", low):
                polarity = True
        clauses.append({
            "raw": raw,
            "tokens": _gui_tokens(cleaned),
            "value": value_lit,
            "polarity": polarity,
        })
    return {"instruction": instruction, "clauses": clauses}


class GUIWorkflowMemory:
    """Stores generalized `(role, slot_tokens, verb)` schemas -- NEVER coordinates or IDs."""

    def __init__(self) -> None:
        self.schemas: dict[str, dict[str, Any]] = {}

    def record_schema(self, goal_signature: str, steps: Sequence[Mapping[str, Any]]) -> None:
        abstracted = []
        for s in steps:
            abstracted.append({
                "role": s["role"],
                "slot_tokens": sorted(set(_gui_tokens(s["name"]))),
                "verb": s["verb"],
                "uses_clause_value": bool(s.get("uses_clause_value")),
            })
        row = self.schemas.get(goal_signature) or {
            "goal_signature": goal_signature,
            "steps": abstracted,
            "admitted_runs": 0,
            "refutations": 0,
        }
        row["steps"] = abstracted
        row["admitted_runs"] = int(row.get("admitted_runs", 0)) + 1
        row["refutations"] = 0
        self.schemas[goal_signature] = row

    def lookup(self, goal_signature: str) -> dict[str, Any] | None:
        row = self.schemas.get(goal_signature)
        if row and int(row.get("refutations", 0)) == 0:
            return row
        return None

    def refute(self, goal_signature: str) -> None:
        if goal_signature in self.schemas:
            self.schemas[goal_signature]["refutations"] = (
                int(self.schemas[goal_signature].get("refutations", 0)) + 1
            )

    def save(self, path: pathlib.Path | str) -> None:
        p = pathlib.Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        payload = {"schema": SCHEMA + "_GUI_MEMORY", "schemas": self.schemas}
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(p)

    @classmethod
    def load(cls, path: pathlib.Path | str) -> "GUIWorkflowMemory":
        mem = cls()
        p = pathlib.Path(path)
        if not p.is_file():
            return mem
        raw = json.loads(p.read_text(encoding="utf-8"))
        mem.schemas = dict(raw.get("schemas") or {})
        return mem


def _goal_signature(parsed: Mapping[str, Any]) -> str:
    parts = []
    for c in parsed["clauses"]:
        toks = "+".join(sorted(set(c["tokens"])))
        pol = "T" if c["polarity"] is True else ("F" if c["polarity"] is False else "N")
        has_v = "V" if c["value"] is not None else "0"
        parts.append(f"{toks}:{pol}:{has_v}")
    return "|".join(parts)


def _score_node_for_clause(node: A11yNode, clause: Mapping[str, Any]) -> float:
    # W3C ARIA role-type compatibility: never confuse a container (`tab`/`disclosure`) or
    # action button with a boolean toggle (`polarity`) or value-entry (`value`) demand!
    raw_low = str(clause.get("raw") or "").lower()
    if node.role in ("tab", "disclosure") and not any(
        w in raw_low for w in ("tab", "section", "open", "switch to", "expand")
    ):
        return 0.0
    if clause["polarity"] is not None and node.role not in ("checkbox", "switch", "radio"):
        return 0.0
    if clause["value"] is not None and not ROLE_GRAMMAR[node.role]["needs_value"]:
        return 0.0

    node_toks = set(_gui_tokens(node.name)) | set(
        t for opt in node.options for t in _gui_tokens(opt)
    )
    clause_toks = set(clause["tokens"])
    overlap = len(node_toks & clause_toks)
    score = 4.0 * overlap
    if clause["value"] is not None:
        val_str = str(clause["value"]).lower()
        if any(val_str == opt.lower() or val_str in opt.lower() for opt in node.options):
            score += 6.0
        elif node.role in ("textbox", "searchbox", "spinbutton"):
            score += 2.0 if overlap > 0 else -2.0
    if clause["polarity"] is not None and node.role in ("checkbox", "switch"):
        score += 3.0 if overlap > 0 else 0.0
    if node.role in ("button", "menuitem", "link") and clause["value"] is None and clause["polarity"] is None:
        score += 2.5 if overlap > 0 else 0.0
    return score


def solve_gui_goal(
    env: A11yEnvironment,
    instruction: str,
    goal_check: Any,
    *,
    memory: GUIWorkflowMemory | None = None,
    max_steps: int = 12,
) -> dict[str, Any]:
    """Solve a multi-step GUI task over `env`'s live Accessibility Tree with zero VLM/LLM calls.

    1. Refuses out-of-world instructions (`REFUSED__NAMES_NOTHING_IN_THIS_INTERFACE`) when no
       token in the instruction overlaps ANY node in the environment's universe.
    2. Tries admitted generalized workflow schema from `memory` first (if available); if any
       step fails to bind, turns out `ACCEPTED_INERT`, or misses `goal_check`, refutes the
       schema and falls back to live Accessibility-Tree grammar planning!
    3. During live planning, automatically expands tabs/disclosures when a clause's best target
       isn't visible yet, detects lying ARIA widgets (`ACCEPTED_INERT`) and blacklists them for
       the current state digest so the planner never loops on a dead widget!
    """
    started = time.perf_counter()
    parsed = parse_gui_goal(instruction)
    sig = _goal_signature(parsed)

    # Admissibility check over the interface's published vocabulary
    all_interface_tokens = {
        t
        for n in env.nodes
        for t in (_gui_tokens(n.name) + [ot for opt in n.options for ot in _gui_tokens(opt)])
    }
    goal_tokens = {t for c in parsed["clauses"] for t in c["tokens"]}
    goal_values = {
        t for c in parsed["clauses"] if c["value"] for t in _gui_tokens(str(c["value"]))
    }
    if not ((goal_tokens | goal_values) & all_interface_tokens):
        return {
            "schema": SCHEMA,
            "status": "REFUSED__NAMES_NOTHING_IN_THIS_INTERFACE",
            "pass": False,
            "steps_taken": 0,
            "seconds": round(time.perf_counter() - started, 4),
            "model_calls": 0,
        }

    # Fast path: replay generalized role+slot schema from memory (bound to live nodes, NOT (x,y)!)
    replayed_from_memory = False
    refuted_memory = False
    if memory is not None:
        schema = memory.lookup(sig)
        if schema is not None:
            env.reset()
            ok_replay = True
            replay_trace: list[dict[str, Any]] = []
            val_clauses = [c["value"] for c in parsed["clauses"] if c["value"] is not None]
            val_idx = 0
            for step_spec in schema["steps"]:
                want_role = step_spec["role"]
                want_toks = set(step_spec["slot_tokens"])
                candidates = [
                    n for n in env.visible_nodes()
                    if not n.disabled and n.role == want_role and (set(_gui_tokens(n.name)) & want_toks or not want_toks)
                ]
                if not candidates and want_role == "tab":
                    candidates = [
                        n for n in env.visible_nodes()
                        if not n.disabled and n.role == "tab" and not n.selected
                    ]
                candidates.sort(
                    key=lambda n: -len(set(_gui_tokens(n.name)) & want_toks)
                )
                if not candidates:
                    ok_replay = False
                    break
                chosen = candidates[0]
                act_payload: dict[str, Any] = {"node_id": chosen.node_id, "verb": step_spec["verb"]}
                if step_spec.get("uses_clause_value"):
                    if val_idx >= len(val_clauses):
                        ok_replay = False
                        break
                    act_payload["value"] = val_clauses[val_idx]
                    val_idx += 1
                res = env.act(act_payload)
                replay_trace.append({"node_id": chosen.node_id, "role": chosen.role, "name": chosen.name, **res})
                if not res.get("accepted") or not res.get("changed"):
                    ok_replay = False
                    break
            if ok_replay and bool(goal_check(env)):
                return {
                    "schema": SCHEMA,
                    "status": "PASS__REPLAYED_GENERALIZED_SCHEMA",
                    "pass": True,
                    "from_memory": True,
                    "steps_taken": len(replay_trace),
                    "trace": replay_trace,
                    "pyautogui": list(env.pyautogui_log),
                    "seconds": round(time.perf_counter() - started, 4),
                    "model_calls": 0,
                }
            # Schema failed on this instance (changed precondition or lying widget): REFUTE IT!
            memory.refute(sig)
            refuted_memory = True
            env.reset()

    # Live goal-directed Accessibility-Tree grammar planner
    inert_blacklist: set[tuple[str, str]] = set()  # (state_digest, node_id)
    tried_containers: set[str] = set()
    executed_steps: list[dict[str, Any]] = []
    clause_done: list[bool] = [False] * len(parsed["clauses"])

    for _step_num in range(max_steps):
        if bool(goal_check(env)):
            break
        state_dig = env.snapshot_digest()
        acted_this_turn = False

        # Find the first unsatisfied clause and pick the highest-scoring non-blacklisted visible node
        for idx, clause in enumerate(parsed["clauses"]):
            if clause_done[idx]:
                continue
            scored: list[tuple[float, A11yNode]] = []
            for node in env.visible_nodes():
                if node.disabled or (state_dig, node.node_id) in inert_blacklist:
                    continue
                s = _score_node_for_clause(node, clause)
                if s > 0:
                    scored.append((s, node))
            scored.sort(key=lambda pair: -pair[0])

            if scored:
                _, best_node = scored[0]
                verb = ROLE_GRAMMAR[best_node.role]["verb"]
                # Skip toggle if checkbox already matches desired polarity!
                if verb == "toggle" and clause["polarity"] is not None and bool(best_node.checked) == clause["polarity"]:
                    clause_done[idx] = True
                    acted_this_turn = True
                    break
                payload = {"node_id": best_node.node_id, "verb": verb}
                uses_val = False
                if ROLE_GRAMMAR[best_node.role]["needs_value"]:
                    if clause["value"] is not None:
                        payload["value"] = clause["value"]
                        uses_val = True
                    elif best_node.options:
                        # Match option by clause tokens
                        opt_match = next(
                            (o for o in best_node.options if set(_gui_tokens(o)) & set(clause["tokens"])),
                            best_node.options[0],
                        )
                        payload["value"] = opt_match
                res = env.act(payload)
                executed_steps.append({
                    "node_id": best_node.node_id,
                    "role": best_node.role,
                    "name": best_node.name,
                    "verb": verb,
                    "uses_clause_value": uses_val,
                    "status": res.get("status"),
                    "changed": res.get("changed"),
                })
                if not res.get("changed"):
                    # Lying ARIA (`ACCEPTED_INERT`): blacklist at this state and retry clause!
                    inert_blacklist.add((state_dig, best_node.node_id))
                else:
                    clause_done[idx] = True
                acted_this_turn = True
                break

        if acted_this_turn:
            continue

        # Once all clauses are satisfied, commit/submit in the active view before leaving it!
        if all(clause_done):
            submit_btns = [
                n for n in env.visible_nodes()
                if not n.disabled
                and n.role == "button"
                and (state_dig, n.node_id) not in inert_blacklist
                and any(w in n.name.lower() for w in ("save", "submit", "apply", "confirm", "ok", "update"))
            ]
            if submit_btns:
                btn = submit_btns[0]
                res = env.act({"node_id": btn.node_id, "verb": "invoke"})
                executed_steps.append({
                    "node_id": btn.node_id,
                    "role": btn.role,
                    "name": btn.name,
                    "verb": "invoke",
                    "uses_clause_value": False,
                    "status": res.get("status"),
                    "changed": res.get("changed"),
                })
                if not res.get("changed"):
                    inert_blacklist.add((state_dig, btn.node_id))
                continue
            break

        # No visible control matched a pending clause -> explore an unopened tab or disclosure!
        containers = [
            n for n in env.visible_nodes()
            if not n.disabled
            and n.role in ("tab", "disclosure")
            and n.node_id not in tried_containers
            and not (n.role == "tab" and n.selected)
            and not (n.role == "disclosure" and n.expanded)
            and (state_dig, n.node_id) not in inert_blacklist
        ]
        # Rank containers by lexical overlap with remaining clauses first, then untried order
        rem_toks = {
            t for i, c in enumerate(parsed["clauses"]) if not clause_done[i] for t in c["tokens"]
        }
        containers.sort(key=lambda n: -len(set(_gui_tokens(n.name)) & rem_toks))
        if containers:
            cont = containers[0]
            tried_containers.add(cont.node_id)
            verb = ROLE_GRAMMAR[cont.role]["verb"]
            res = env.act({"node_id": cont.node_id, "verb": verb})
            executed_steps.append({
                "node_id": cont.node_id,
                "role": cont.role,
                "name": cont.name,
                "verb": verb,
                "uses_clause_value": False,
                "status": res.get("status"),
                "changed": res.get("changed"),
            })
            if not res.get("changed"):
                inert_blacklist.add((state_dig, cont.node_id))
            continue

        break

    solved = bool(goal_check(env))
    if solved and memory is not None:
        # Only persist the minimal causal steps (`changed == True`), NEVER inert decoy clicks!
        causal_steps = [s for s in executed_steps if s.get("changed")]
        memory.record_schema(sig, causal_steps)

    return {
        "schema": SCHEMA,
        "status": "PASS__GOAL_VERIFIED" if solved else "OPEN__GOAL_NOT_REACHED",
        "pass": solved,
        "from_memory": replayed_from_memory,
        "refuted_stale_memory": refuted_memory,
        "inert_widgets_refuted": len(inert_blacklist),
        "steps_taken": len(executed_steps),
        "trace": executed_steps,
        "pyautogui": list(env.pyautogui_log),
        "seconds": round(time.perf_counter() - started, 4),
        "model_calls": 0,
    }
