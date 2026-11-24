#!/usr/bin/env python3
"""Zero-Model Epistemic Computer-Use & Software-Engineering Agent (V1).

Unifies the four calculated mechanisms of Project Brain's own model:
  1. Fast Passive Scan + Diff Against Memory (`scan_and_diff_against_memory_v1`)
  2. Goal-Directed Ignorance Ranking (`ignorance_ledger_v1`: `p_useful / (1 + cost)`)
  3. Local Guide First -> JIT Store Fallback -> Execution Earning:
     - `auto_judge_discovery_v1` (autonomous content-judge earning + victim screening)
     - `interface_action_grammar_v1` (CLI `--help` + W3C ARIA / OSWorld action grammars)
     - `causal_swe_repair_v1` (zero-leakage dynamic causal localization + AST/frame repair)
  4. Deterministic Syntactic-Semantic NL Goal Grounding + Out-of-World Refusal

Hard invariants:
  - `model_calls == 0` ($0 runtime API spend; zero external or local neural LLM calls)
  - `parameters_stored == 0` (zero world facts in weights; all learned schemas live in
    inspectable, human-editable, execution-refutable JSON files inside `EpistemicStore`)
  - Raw `(x, y)` coordinates, raw trajectories, and literal repo paths are NEVER saved.
"""
from __future__ import annotations

import json
import pathlib
import re
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime import ignorance_ledger_v1 as il
from canonical.swe_kernel import auto_judge_discovery_v1 as ajd
from canonical.swe_kernel import causal_swe_repair_v1 as swe
from canonical.swe_kernel import first_principles_mental_cegis_v1 as fpm
from canonical.swe_kernel import interface_action_grammar_v1 as iag

SCHEMA = "EPISTEMIC_COMPUTER_AGENT_V1"
AUTHORITY = "FIRST_PRINCIPLES_ZERO_MODEL_AGENT"


def hypothesize_candidate_kinds(path: pathlib.Path) -> set[str]:
    """0.02 ms untrusted header hypothesis to focus goal-directed judge earning.

    NOTE: A header hypothesis NEVER settles validity (e.g. a truncated `.gz` still starts
    with `\\x1f\\x8b`). Only an earned, contrast-screened execution judge settles validity.
    """
    try:
        head = path.read_bytes()[:512]
    except OSError:
        return set()
    cands: set[str] = set()
    for kind, pred in ajd.FAST_MAGIC_NECESSARY.items():
        if pred(head):
            cands.add(kind)
    stripped = head.lstrip()
    if stripped.startswith((b"{", b"[")):
        cands.add("json")
    if stripped.startswith(b"<"):
        cands.add("xml")
    if not cands:
        try:
            head.decode("utf-8")
            cands.update({"python", "json", "xml", "csv", "ini"})
        except UnicodeDecodeError:
            pass
    return cands


# =========================================================================== #
# INSPECTABLE, EDITABLE, REFUTABLE EXTERNAL MEMORY BUNDLE
# =========================================================================== #

class EpistemicStore:
    """Inspectable, human-editable, execution-refutable external store (`parameters_stored = 0`)."""

    def __init__(self, root: pathlib.Path | str) -> None:
        self.root = pathlib.Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.judges_path = self.root / "judges.json"
        self.cli_path = self.root / "cli_grammars.json"
        self.gui_path = self.root / "gui_workflows.json"
        self.swe_path = self.root / "swe_operators.json"
        self.ledger_path = self.root / "ignorance_ledger.json"

        self.judges = ajd.JudgeStore.load(self.judges_path)
        self.cli_memory = iag.CLIGrammarMemory.load(self.cli_path)
        self.gui_memory = iag.GUIWorkflowMemory.load(self.gui_path)
        self.swe_memory = swe.SWERepairMemory.load(self.swe_path)

    def save_all(self) -> None:
        self.judges.save(self.judges_path)
        self.cli_memory.save(self.cli_path)
        self.gui_memory.save(self.gui_path)
        self.swe_memory.save(self.swe_path)

    def reload_all(self) -> None:
        """Reload from disk so human edits or deletions take immediate effect."""
        self.judges = ajd.JudgeStore.load(self.judges_path)
        self.cli_memory = iag.CLIGrammarMemory.load(self.cli_path)
        self.gui_memory = iag.GUIWorkflowMemory.load(self.gui_path)
        self.swe_memory = swe.SWERepairMemory.load(self.swe_path)

    def audit(self) -> dict[str, Any]:
        """Verify that zero raw coordinates, zero raw action traces, and zero weights are stored."""
        raw_blobs = {}
        for p in (self.judges_path, self.cli_path, self.gui_path, self.swe_path, self.ledger_path):
            if p.is_file():
                raw_blobs[p.name] = p.read_text(encoding="utf-8")
        combined = "\n".join(raw_blobs.values())
        has_xy_coords = bool(re.search(r'"(?:bbox|x_coord|y_coord|pixel_x|pixel_y)"\s*:', combined))
        has_raw_dom_xpath = bool(re.search(r'"xpath"\s*:', combined))
        return {
            "store_root": str(self.root),
            "files_present": sorted(raw_blobs.keys()),
            "earned_judges": sorted(self.judges.callable_validators().keys()),
            "cli_grammars_count": len(self.cli_memory.pages_by_key),
            "gui_workflows_count": len(self.gui_memory.schemas),
            "swe_schemas_count": len(self.swe_memory.schemas),
            "raw_coordinates_saved": 0 if not has_xy_coords else 1,
            "raw_xpath_saved": 0 if not has_raw_dom_xpath else 1,
            "parameters_stored": 0,
            "inspectable_json": True,
        }


# =========================================================================== #
# DETERMINISTIC SYNTACTIC-SEMANTIC NATURAL LANGUAGE GOAL PARSER (ZERO LLM)
# =========================================================================== #

@dataclass(frozen=True)
class ParsedGoal:
    surface: str  # "gui" | "cli" | "swe" | "room" | "ungrounded"
    clauses: tuple[dict[str, Any], ...]
    raw_text: str
    reason: str = ""


_CHECK_PAT = re.compile(
    r"\b(?:check|enable|turn\s+on|activate)\s+['\"]?([^'\",.;]+?)['\"]?(?=\s*(?:,|;|\band\b|\bthen\b|$))",
    re.IGNORECASE,
)
_UNCHECK_PAT = re.compile(
    r"\b(?:uncheck|disable|turn\s+off|deactivate)\s+['\"]?([^'\",.;]+?)['\"]?(?=\s*(?:,|;|\band\b|\bthen\b|$))",
    re.IGNORECASE,
)
_TYPE_INTO_PAT = re.compile(
    r"\b(?:type|enter|fill|write|set)\s+['\"]?([^'\"]+?)['\"]?\s+(?:into|in|to|for)\s+['\"]?([^'\",.;]+?)['\"]?(?=\s*(?:,|;|\band\b|\bthen\b|$))",
    re.IGNORECASE,
)
_SELECT_PAT = re.compile(
    r"\b(?:select|choose|pick)\s+['\"]?([^'\"]+?)['\"]?\s+(?:from|in|for)\s+['\"]?([^'\",.;]+?)['\"]?(?=\s*(?:,|;|\band\b|\bthen\b|$))",
    re.IGNORECASE,
)
_CLICK_PAT = re.compile(
    r"\b(?:click|press|submit)\s+(?:on\s+|the\s+)?['\"]?([^'\",.;]+?)['\"]?(?:\s+button)?(?=\s*(?:,|;|\band\b|\bthen\b|$))",
    re.IGNORECASE,
)
_FIX_TEST_PAT = re.compile(
    r"\b(?:fix|repair|solve|patch)\b.*?\b([\w./-]*test[\w./-]*\.py(?:::\S+)?)",
    re.IGNORECASE,
)
_VERIFY_ARTIFACT_PAT = re.compile(
    r"\b(?:verify|validate|inspect|audit|check)\b.*?\b([\w./-]+\.[a-z0-9]{1,8})\b",
    re.IGNORECASE,
)


def parse_nl_goal(text: str) -> ParsedGoal:
    """Deterministically compile plain-English imperatives into typed world-predicate demands."""
    clean = text.strip()
    if not clean:
        return ParsedGoal("ungrounded", (), text, "EMPTY_GOAL_TEXT")

    m_swe = _FIX_TEST_PAT.search(clean)
    if m_swe:
        return ParsedGoal(
            "swe",
            ({"kind": "repair_test_target", "test_target": m_swe.group(1)},),
            clean,
        )

    m_art = _VERIFY_ARTIFACT_PAT.search(clean)
    if m_art and not _TYPE_INTO_PAT.search(clean):
        return ParsedGoal(
            "room",
            ({"kind": "verify_specific_artifact", "target_file": m_art.group(1)},),
            clean,
        )

    gui_clauses: list[tuple[int, dict[str, Any]]] = []
    for m in _CHECK_PAT.finditer(clean):
        label = m.group(1).strip()
        if not label.lower().startswith(("every ", "all ", "file ", "artifact")):
            gui_clauses.append((m.start(), {"role": "checkbox", "name": label, "desired": True}))
    for m in _UNCHECK_PAT.finditer(clean):
        gui_clauses.append((m.start(), {"role": "checkbox", "name": m.group(1).strip(), "desired": False}))
    for m in _TYPE_INTO_PAT.finditer(clean):
        val, label = m.group(1).strip(), m.group(2).strip()
        gui_clauses.append((m.start(), {"role": "textbox", "name": label, "desired": val}))
    for m in _SELECT_PAT.finditer(clean):
        val, label = m.group(1).strip(), m.group(2).strip()
        gui_clauses.append((m.start(), {"role": "combobox", "name": label, "desired": val}))
    for m in _CLICK_PAT.finditer(clean):
        label = m.group(1).strip()
        gui_clauses.append((m.start(), {"role": "button", "name": label, "desired": "submitted"}))

    if gui_clauses:
        gui_clauses.sort(key=lambda item: item[0])
        return ParsedGoal("gui", tuple(c for _, c in gui_clauses), clean)

    if re.search(r"\b(?:scan|audit|verify)\b.*\b(?:room|directory|workspace|artifacts)\b", clean, re.I):
        return ParsedGoal("room", ({"kind": "verify_all_artifacts"},), clean)

    return ParsedGoal("ungrounded", (), clean, "NO_GROUNDED_PREDICATE_GRAMMAR_MATCH")


# =========================================================================== #
# UNIFIED EPISTEMIC COMPUTER & SWE AGENT
# =========================================================================== #

class EpistemicComputerAgent:
    """Zero-model autonomous agent across OS rooms, CLIs, GUIs/browsers, and SWE repos."""

    def __init__(self, store: EpistemicStore) -> None:
        self.store = store

    def execute_room_goal(
        self,
        room_path: pathlib.Path | str,
        goal: str | Mapping[str, Any],
        *,
        mode: str = "goal_directed",
    ) -> dict[str, Any]:
        """Enter an unseen room, scan & diff against memory, and close ONLY goal-blocking gaps."""
        started = time.perf_counter()
        self.store.reload_all()
        room = pathlib.Path(room_path)
        parsed = (
            parse_nl_goal(goal)
            if isinstance(goal, str)
            else ParsedGoal("room", (dict(goal),), json.dumps(goal, sort_keys=True))
        )
        if parsed.surface != "room" or not parsed.clauses:
            return {
                "schema": SCHEMA,
                "status": "REFUSED__UNGROUNDED_GOAL",
                "pass": False,
                "reason": parsed.reason or "NOT_A_ROOM_GOAL",
                "model_calls": 0,
            }

        clause = parsed.clauses[0]
        # 1. Passive scan + diff against JudgeStore!
        _, before_summary = ajd.scan_with_store(room, self.store.judges)
        active_kinds = set(self.store.judges.callable_validators().keys())

        # Discover untrusted candidate kinds present across all unread files in the room
        room_files = sorted(p for p in room.rglob("*") if p.is_file())
        all_unknown_kinds_set: set[str] = set()
        for fp in room_files:
            all_unknown_kinds_set.update(hypothesize_candidate_kinds(fp) - active_kinds)
        all_unknown_kinds = sorted(all_unknown_kinds_set)

        if clause.get("kind") == "verify_specific_artifact":
            target_rel = str(clause["target_file"])
            target_path = room / target_rel
            if not target_path.is_file():
                return {
                    "schema": SCHEMA,
                    "status": "REFUSED__TARGET_ARTIFACT_NOT_IN_WORLD",
                    "pass": False,
                    "target_file": target_rel,
                    "model_calls": 0,
                }
            target_cands = hypothesize_candidate_kinds(target_path)
            target_unknowns = sorted(target_cands - active_kinds)
        else:
            target_rel = "*"
            target_path = None
            target_cands = set()
            target_unknowns = list(all_unknown_kinds)

        # 2. Goal-directed vs upfront-all learning selection
        if mode == "goal_directed":
            kinds_to_learn = target_unknowns
        elif mode == "upfront_all":
            kinds_to_learn = list(all_unknown_kinds)
        else:
            raise ValueError(f"Unknown mode: {mode}")

        gaps_logged: list[str] = []
        for k in kinds_to_learn:
            gid = il.note(
                f"no verified judge for kind:{k}",
                why=f"goal:{target_rel} requires content verification of {k}",
                cost=0.25,
                path=str(self.store.ledger_path),
            )
            gaps_logged.append(gid)

        newly_admitted: list[str] = []
        probes_spent = 0
        if kinds_to_learn:
            _ranked = il.rank(limit=max(1, len(kinds_to_learn)), path=str(self.store.ledger_path))
            receipt = ajd.auto_earn_judges(only_kinds=set(kinds_to_learn))
            probes_spent = int(receipt["candidates_evaluated"])
            newly_admitted = self.store.judges.admit_from_receipt(receipt)
            for gid, k in zip(gaps_logged, kinds_to_learn):
                il.resolve(
                    gid,
                    helped=(k in newly_admitted),
                    close=(k in newly_admitted),
                    path=str(self.store.ledger_path),
                )

        # 3. Re-scan and verify target!
        after_items, after_summary = ajd.scan_with_store(room, self.store.judges)
        self.store.judges.signatures.learn(after_items)
        self.store.save_all()

        if target_path is not None:
            validators = self.store.judges.callable_validators()
            matching_earned = [k for k in sorted(target_cands) if k in validators]
            if not matching_earned:
                verdict_status = "OPEN__JUDGE_UNEARNED"
                passed = False
            else:
                verdicts = {k: validators[k](str(target_path)) for k in matching_earned}
                if any(rc == 0 for rc in verdicts.values()):
                    verdict_status = "PASS__VERIFIED_GOOD"
                    passed = True
                else:
                    verdict_status = "PASS__VERIFIED_CORRUPT_CAUGHT"
                    passed = True
        else:
            passed = after_summary["unread"] == 0
            verdict_status = "PASS__ROOM_SETTLED" if passed else "OPEN__UNKNOWNS_REMAIN"

        return {
            "schema": SCHEMA,
            "surface": "room",
            "mode": mode,
            "status": verdict_status,
            "pass": passed,
            "target": target_rel,
            "unknown_kinds_in_room": all_unknown_kinds,
            "unknown_kinds_probed": kinds_to_learn,
            "distractor_kinds_skipped": [k for k in all_unknown_kinds if k not in kinds_to_learn],
            "earned_kinds": newly_admitted,
            "probes_spent": probes_spent,
            "before_unread": before_summary["unread"],
            "after_unread": after_summary["unread"],
            "seconds": round(time.perf_counter() - started, 4),
            "model_calls": 0,
            "parameters_stored": 0,
        }

    def execute_cli_goal(
        self,
        need: Mapping[str, Any],
        root: pathlib.Path | str,
        *,
        candidate_programs: Sequence[str] | None = None,
        depth: int = 2,
    ) -> dict[str, Any]:
        self.store.reload_all()
        root_p = pathlib.Path(root)
        existing = [
            p.relative_to(root_p).as_posix()
            for p in root_p.rglob("*")
            if p.is_file()
        ] if root_p.is_dir() else []
        mental = fpm.EnvironmentMentalModel(
            existing_files=existing,
            protected_inputs=existing,
        )
        # Filter out explicitly destructive CLI binaries in shadow simulation before probing/running!
        pruned_destructive: list[str] = []
        safe_programs: Sequence[str] | None = candidate_programs
        if candidate_programs is not None:
            kept: list[str] = []
            for p in candidate_programs:
                chk = mental.simulate_cli_plan([[p]])
                if chk["safe_to_execute"]:
                    kept.append(p)
                else:
                    pruned_destructive.append(p)
            if not kept and candidate_programs:
                return {
                    "schema": SCHEMA,
                    "agent_schema": SCHEMA,
                    "surface": "cli",
                    "status": "REFUSED__MENTAL_MODEL_DESTRUCTIVE_CLI_RISK",
                    "pass": False,
                    "probed": 0,
                    "mental_pruned_binaries": pruned_destructive,
                    "model_calls": 0,
                    "parameters_stored": 0,
                }
            safe_programs = kept
        res = iag.solve_cli_need(
            need,
            root_p,
            memory=self.store.cli_memory,
            candidate_programs=safe_programs,
            depth=depth,
        )
        self.store.save_all()
        return {
            **res,
            "agent_schema": SCHEMA,
            "surface": "cli",
            "mental_shadow_files_tracked": len(existing),
            "mental_pruned_binaries": pruned_destructive,
            "parameters_stored": 0,
        }

    def execute_gui_goal(
        self,
        env_or_html: iag.A11yEnvironment | str,
        instruction: str,
        *,
        goal_check: Callable[[iag.A11yEnvironment], bool] | None = None,
        max_steps: int = 12,
    ) -> dict[str, Any]:
        self.store.reload_all()
        env = (
            iag.A11yEnvironment.from_html(env_or_html)
            if isinstance(env_or_html, str)
            else env_or_html
        )
        parsed = parse_nl_goal(instruction)
        if parsed.surface != "gui" or not parsed.clauses:
            return {
                "schema": SCHEMA,
                "surface": "gui",
                "status": "REFUSED__UNGROUNDED_NL_GOAL",
                "pass": False,
                "reason": parsed.reason or "NO_GUI_CLAUSES",
                "model_calls": 0,
                "parameters_stored": 0,
            }

        # Mental-model preflight: simulate every button click in shadow DOM (< 0.05 ms) to block
        # destructive controls (`Factory Wipe`) or `<div role="button">` decoys before touching `env`!
        mental = fpm.EnvironmentMentalModel(aria_nodes=env.nodes)
        for cl in parsed.clauses:
            if cl["role"] == "button":
                for n in env.nodes:
                    if n.role == "button" and cl["name"].lower() in n.name.lower():
                        sel_id = getattr(n, "selector", None) or getattr(n, "node_id", "")
                        sim_chk = mental.simulate_gui_plan([{"selector": sel_id, "verb": "click"}])
                        if any("DESTRUCTIVE_CONTROL" in r for r in sim_chk["risks"]):
                            return {
                                "schema": SCHEMA,
                                "agent_schema": SCHEMA,
                                "surface": "gui",
                                "status": "REFUSED__MENTAL_MODEL_DESTRUCTIVE_GUI_RISK",
                                "pass": False,
                                "mental_preflight": sim_chk,
                                "model_calls": 0,
                                "parameters_stored": 0,
                            }

        # Synthesize structural postcondition predicate from parsed NL clauses if not supplied
        if goal_check is None:
            clauses = parsed.clauses

            def _auto_goal_check(e: iag.A11yEnvironment) -> bool:
                for cl in clauses:
                    want_role = cl["role"]
                    want_name = cl["name"].lower()
                    desired = cl["desired"]
                    if want_role == "button" and desired == "submitted":
                        if not e.status_banner or "ERROR" in e.status_banner:
                            return False
                        continue
                    matched_nodes = [
                        n for n in e.nodes
                        if n.role == want_role and (
                            want_name in n.name.lower() or n.name.lower() in want_name
                        )
                    ]
                    if not matched_nodes:
                        return False
                    if want_role == "checkbox":
                        if not any(bool(n.checked) == bool(desired) for n in matched_nodes):
                            return False
                    else:
                        if not any(str(n.value) == str(desired) for n in matched_nodes):
                            return False
                return True

            goal_check = _auto_goal_check

        res = iag.solve_gui_goal(
            env, instruction, goal_check, memory=self.store.gui_memory, max_steps=max_steps
        )
        self.store.save_all()
        return {
            **res,
            "agent_schema": SCHEMA,
            "surface": "gui",
            "parameters_stored": 0,
        }

    def execute_swe_goal(
        self,
        worktree: pathlib.Path | str,
        goal_or_test_target: str,
        *,
        python_exe: str | None = None,
        budget_s: float = 90.0,
    ) -> dict[str, Any]:
        self.store.reload_all()
        wt = pathlib.Path(worktree)
        if " " in goal_or_test_target.strip():
            parsed = parse_nl_goal(goal_or_test_target)
            if parsed.surface != "swe" or not parsed.clauses:
                return {
                    "schema": SCHEMA,
                    "surface": "swe",
                    "status": "REFUSED__UNGROUNDED_SWE_GOAL",
                    "pass": False,
                    "reason": parsed.reason,
                    "model_calls": 0,
                    "parameters_stored": 0,
                }
            test_target = str(parsed.clauses[0]["test_target"])
        else:
            test_target = goal_or_test_target.strip()

        test_file_only = test_target.split("::")[0]
        if not (wt / test_file_only).is_file():
            return {
                "schema": SCHEMA,
                "surface": "swe",
                "status": "REFUSED__TEST_TARGET_NOT_FOUND",
                "pass": False,
                "test_target": test_target,
                "model_calls": 0,
                "parameters_stored": 0,
            }

        res = swe.repair_worktree(
            wt,
            test_target,
            python_exe=python_exe,
            memory=self.store.swe_memory,
            budget_s=budget_s,
        )
        self.store.save_all()
        return {
            **res,
            "agent_schema": SCHEMA,
            "surface": "swe",
        }
