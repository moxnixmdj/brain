#!/usr/bin/env python3
"""Tests for Unified Interface Action-Grammar Engine (CLI + GUI/ARIA)."""
from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from canonical.swe_kernel import interface_action_grammar_v1 as iag


SETTINGS_APP_V1_HTML = """
<!doctype html>
<html>
<body>
  <div role="tablist">
    <button id="tab-general" role="tab" aria-selected="true" aria-controls="panel-general" data-x="20" data-y="20" data-w="120" data-h="32">General</button>
    <button id="tab-security" role="tab" aria-selected="false" aria-controls="panel-security" data-x="150" data-y="20" data-w="120" data-h="32">Security</button>
  </div>
  <div id="panel-general">
    <label for="display-name">Display Name</label>
    <input id="display-name" type="text" value="guest" data-x="40" data-y="80" data-w="200" data-h="32">
  </div>
  <div id="panel-security" hidden>
    <label for="tfa-toggle">Two-Factor Authentication</label>
    <input id="tfa-toggle" type="checkbox" data-x="40" data-y="130" data-w="24" data-h="24">
    <label for="backup-email">Recovery Email</label>
    <input id="backup-email" type="email" value="" required data-x="40" data-y="180" data-w="240" data-h="32">
    <label for="session-policy">Session Timeout</label>
    <select id="session-policy" data-x="40" data-y="230" data-w="180" data-h="32">
      <option selected>24 hours</option>
      <option>15 minutes</option>
      <option>1 hour</option>
    </select>
    <!-- Adversarial lying ARIA widget: claims role=button, has NO handler! -->
    <div id="fake-save-div" role="button" data-x="40" data-y="290" data-w="140" data-h="36">Save Security Settings</div>
    <button id="real-save-btn" data-x="200" data-y="290" data-w="140" data-h="36">Save Security Settings</button>
  </div>
</body>
</html>
"""

# Completely re-laid-out unseen V2 app: different IDs, shifted coordinates (x+500, y+300),
# reversed tab order, extra distractor widgets, different wording casing!
SETTINGS_APP_V2_UNSEEN_HTML = """
<!doctype html>
<html>
<body>
  <div id="promo-banner">
    <button id="dismiss-promo" data-x="40" data-y="290" data-w="140" data-h="36">Upgrade Plan</button>
    <button id="wrong-btn-at-old-save-coords" data-x="200" data-y="290" data-w="140" data-h="36">Delete Account</button>
  </div>
  <div role="tablist">
    <button id="nav-audit" role="tab" aria-selected="true" aria-controls="sec-audit" data-x="520" data-y="320" data-w="120" data-h="32">Audit Logs</button>
    <button id="nav-sec-v2" role="tab" aria-selected="false" aria-controls="sec-pane-v2" data-x="660" data-y="320" data-w="140" data-h="32">Account Security</button>
  </div>
  <div id="sec-audit">
    <input id="filter-logs" type="search" placeholder="Filter logs" data-x="520" data-y="380" data-w="200" data-h="32">
  </div>
  <div id="sec-pane-v2" hidden>
    <select id="timeout-sel-v2" aria-label="Session Timeout Policy" data-x="540" data-y="520" data-w="200" data-h="32">
      <option selected>24 hours</option>
      <option>15 minutes</option>
      <option>1 hour</option>
    </select>
    <input id="rec-mail-v2" type="email" aria-label="Recovery Email Address" required data-x="540" data-y="460" data-w="240" data-h="32">
    <input id="mfa-chk-v2" type="checkbox" aria-label="Enable Two-Factor Authentication" data-x="540" data-y="410" data-w="24" data-h="24">
    <button id="commit-sec-v2" data-x="720" data-y="590" data-w="160" data-h="36">Apply Security Settings</button>
  </div>
</body>
</html>
"""


def _security_goal_held(env: iag.A11yEnvironment, expected_email: str, expected_timeout: str) -> bool:
    by_role_name = {(n.role, n.name.lower()): n for n in env.nodes}
    tfa = next((n for (_, nm), n in by_role_name.items() if "two" in nm and "factor" in nm), None)
    mail = next((n for (_, nm), n in by_role_name.items() if "recovery" in nm and "email" in nm), None)
    timeout = next((n for (_, nm), n in by_role_name.items() if "timeout" in nm), None)
    return bool(
        tfa and tfa.checked is True
        and mail and mail.value == expected_email
        and timeout and timeout.value == expected_timeout
        and env.status_banner.startswith("SAVED_OK")
    )


class InterfaceActionGrammarTests(unittest.TestCase):
    def test_cli_unseen_room_two_edge_path_and_warm_memory_zero_reprobes(self) -> None:
        mem = iag.CLIGrammarMemory()
        subset = ("tar", "gzip", "bzip2", "cp", "mv", "rm", "sort", "grep", "ls")

        with tempfile.TemporaryDirectory(prefix="cli-unseen-1-") as tmp1:
            room1 = Path(tmp1) / "workspace_alpha"
            (room1 / "backend" / "services").mkdir(parents=True)
            (room1 / "backend" / "services" / "handler.py").write_text(
                "def handle():\n    return 42\n", encoding="utf-8"
            )
            need1 = {
                "id": "U01",
                "need": "archive the backend directory and then compress the archive",
                "target": "compressed",
                "requires": [
                    {"check": "compressed", "kind": "compressed"},
                    {"check": "exists_kind", "path": "backend", "kind": "directory"},
                ],
            }
            cold = iag.solve_cli_need(need1, room1, memory=mem, candidate_programs=subset, depth=2)
            self.assertTrue(cold["pass"], cold)
            self.assertGreater(cold["probed"], 0)
            self.assertEqual(cold["recalled_from_memory"], 0)
            self.assertGreaterEqual(len(cold["path"]), 2)

            # Persist memory and reload in a completely different unseen room!
            mem_file = Path(tmp1) / "cli_mem.json"
            mem.save(mem_file)
            saved_raw = mem_file.read_text(encoding="utf-8")
            self.assertNotIn("workspace_alpha", saved_raw)
            self.assertNotIn("handler.py", saved_raw)
            warm_mem = iag.CLIGrammarMemory.load(mem_file)

        with tempfile.TemporaryDirectory(prefix="cli-unseen-2-") as tmp2:
            room2 = Path(tmp2) / "completely_new_tree"
            (room2 / "telemetry").mkdir(parents=True)
            (room2 / "telemetry" / "events.log").write_text("e2\ne1\ne3\n", encoding="utf-8")
            need2 = {
                "id": "U02",
                "need": "compress the plain file events.log",
                "target": "compressed",
                "requires": [{"check": "compressed", "kind": "compressed"}],
            }
            warm = iag.solve_cli_need(need2, room2, memory=warm_mem, candidate_programs=subset, depth=2)
            self.assertTrue(warm["pass"], warm)
            # Zero binary `--help` subprocesses on the warm run!
            self.assertEqual(warm["probed"], 0)
            self.assertGreater(warm["recalled_from_memory"], 0)

            # Out-of-world need is refused cleanly before running any command
            impossible = {
                "id": "H99",
                "need": "book a flight to Tokyo next Friday",
                "target": "plain",
                "requires": [{"check": "contains_text", "kind": "plain", "text": "Tokyo"}],
            }
            refused = iag.solve_cli_need(impossible, room2, memory=warm_mem, candidate_programs=subset)
            self.assertFalse(refused["pass"])
            self.assertEqual(refused["status"], "REFUSED__NAMES_NOTHING_IN_THIS_WORLD")

    def test_gui_a11y_grammar_beats_lying_aria_and_transfers_across_unseen_layout(self) -> None:
        mem = iag.GUIWorkflowMemory()
        env1 = iag.A11yEnvironment.from_html(
            SETTINGS_APP_V1_HTML,
            submit_effects={"real-save-btn": {"banner": "SAVED_OK", "respect_required": True}},
        )
        goal1 = (
            "enable two factor authentication and set recovery email to sec@brain.org "
            "and select '15 minutes' for session timeout"
        )
        res1 = iag.solve_gui_goal(
            env1,
            goal1,
            lambda e: _security_goal_held(e, "sec@brain.org", "15 minutes"),
            memory=mem,
        )
        self.assertTrue(res1["pass"], res1)
        self.assertEqual(res1["model_calls"], 0)
        # Proves the lying `<div role="button">` decoy was detected as ACCEPTED_INERT and bypassed!
        self.assertGreaterEqual(res1["inert_widgets_refuted"], 1)
        # Proves OSWorld pyautogui lowering was produced
        self.assertTrue(any(cmd.startswith("pyautogui.click(") for cmd in res1["pyautogui"]))
        self.assertTrue(any("sec@brain.org" in cmd for cmd in res1["pyautogui"]))

        # Control 1: Naive coordinate replay of `res1` on unseen V2 layout MUST FAIL (clicks Delete Account!)
        env2_coord = iag.A11yEnvironment.from_html(
            SETTINGS_APP_V2_UNSEEN_HTML,
            submit_effects={
                "commit-sec-v2": {"banner": "SAVED_OK", "respect_required": True},
                "wrong-btn-at-old-save-coords": {"banner": "DESTRUCTIVE_DELETE_TRIGGERED", "respect_required": False},
            },
        )
        # Replay exact V1 click coordinates on V2:
        env2_coord.act({"x": 150 + 60, "y": 20 + 16})
        env2_coord.act({"x": 200 + 70, "y": 290 + 18})
        self.assertFalse(_security_goal_held(env2_coord, "ops@new-org.io", "1 hour"))
        self.assertEqual(env2_coord.status_banner, "DESTRUCTIVE_DELETE_TRIGGERED")

        # Generalized Schema Transfer on unseen V2 layout with DIFFERENT arguments!
        env2 = iag.A11yEnvironment.from_html(
            SETTINGS_APP_V2_UNSEEN_HTML,
            submit_effects={
                "commit-sec-v2": {"banner": "SAVED_OK", "respect_required": True},
                "wrong-btn-at-old-save-coords": {"banner": "DESTRUCTIVE_DELETE_TRIGGERED", "respect_required": False},
            },
        )
        goal2 = (
            "enable two factor authentication and set recovery email to ops@new-org.io "
            "and select '1 hour' for session timeout"
        )
        res2 = iag.solve_gui_goal(
            env2,
            goal2,
            lambda e: _security_goal_held(e, "ops@new-org.io", "1 hour"),
            memory=mem,
        )
        self.assertTrue(res2["pass"], res2)
        self.assertNotEqual(env2.status_banner, "DESTRUCTIVE_DELETE_TRIGGERED")

        # Contradiction / Changed-Precondition Test: corrupt the stored schema, verify active refutation + recovery!
        sig = next(iter(mem.schemas))
        mem.schemas[sig]["steps"] = [{"role": "button", "slot_tokens": ["upgrade", "plan"], "verb": "invoke", "uses_clause_value": False}]
        env2_contradict = iag.A11yEnvironment.from_html(
            SETTINGS_APP_V2_UNSEEN_HTML,
            submit_effects={"commit-sec-v2": {"banner": "SAVED_OK", "respect_required": True}},
        )
        res_recovered = iag.solve_gui_goal(
            env2_contradict,
            goal2,
            lambda e: _security_goal_held(e, "ops@new-org.io", "1 hour"),
            memory=mem,
        )
        self.assertTrue(res_recovered["pass"], res_recovered)
        self.assertTrue(res_recovered["refuted_stale_memory"])

        # Out-of-world GUI instruction must refuse before clicking anything
        impossible = iag.solve_gui_goal(
            env2_contradict,
            "order pepperoni pizza for tonight",
            lambda _e: False,
            memory=mem,
        )
        self.assertFalse(impossible["pass"])
        self.assertEqual(impossible["status"], "REFUSED__NAMES_NOTHING_IN_THIS_INTERFACE")
        self.assertEqual(impossible["steps_taken"], 0)


if __name__ == "__main__":
    unittest.main()
