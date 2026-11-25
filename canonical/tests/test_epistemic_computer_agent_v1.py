#!/usr/bin/env python3
"""Unit tests for the unified Zero-Model Epistemic Computer & SWE Agent (V1)."""
from __future__ import annotations

import gzip
import json
import sqlite3
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from canonical.swe_kernel import epistemic_computer_agent_v1 as eca
from canonical.swe_kernel import interface_action_grammar_v1 as iag


LAYOUT_A = """
<div>
  <button role="tab" id="tab-overview" aria-controls="p-overview" aria-selected="true">Overview</button>
  <button role="tab" id="tab-sec" aria-controls="p-sec" aria-selected="false">Security</button>
  <div role="tabpanel" id="p-overview">
    <label for="org">Org Name</label>
    <input id="org" type="text" value="Arena" />
  </div>
  <div role="tabpanel" id="p-sec" hidden>
    <label for="mfa">Enable Two-Factor Auth</label>
    <input id="mfa" type="checkbox" />
    <label for="rec">Recovery Email</label>
    <input id="rec" type="email" value="" />
    <button id="save-btn" type="submit">Save Changes</button>
  </div>
</div>
"""

LAYOUT_B_REDESIGNED = """
<main>
  <button role="tab" id="nav-billing" aria-controls="sec-billing" aria-selected="true">Billing</button>
  <button role="tab" id="nav-protect" aria-controls="sec-protect" aria-selected="false">Account Protection</button>
  <section role="tabpanel" id="sec-billing"></section>
  <section role="tabpanel" id="sec-protect" hidden>
    <input id="inp-recovery" type="text" aria-label="Recovery Email" value="" />
    <input id="chk-2fa" type="checkbox" aria-label="Enable Two-Factor Auth" />
    <button id="btn-commit" type="submit">Save Changes</button>
  </section>
</main>
"""


class EpistemicComputerAgentTests(unittest.TestCase):
    def _populate_mixed_room(self, room: Path) -> None:
        (room / "payload.gz").write_bytes(gzip.compress(b'{"ok": true}'))
        with zipfile.ZipFile(room / "bundle.zip", "w") as zf:
            zf.writestr("a.txt", "hello")
        (room / "config.xml").write_text("<root><item id='1'/></root>", encoding="utf-8")
        (room / "notes.json").write_text('{"k": [1, 2, 3]}', encoding="utf-8")
        conn = sqlite3.connect(room / "local.sqlite")
        conn.execute("CREATE TABLE t (x INT)")
        conn.commit()
        conn.close()

    def test_goal_directed_beats_upfront_all_learning_in_mixed_room(self) -> None:
        with tempfile.TemporaryDirectory(prefix="eca-room-") as tmp:
            base = Path(tmp)
            room = base / "room"
            room.mkdir()
            self._populate_mixed_room(room)

            # Agent 1: Goal-directed active learning ("Verify artifact payload.gz")
            gd_store = eca.EpistemicStore(base / "store_gd")
            gd_agent = eca.EpistemicComputerAgent(gd_store)
            gd_res = gd_agent.execute_room_goal(
                room, "Verify artifact payload.gz", mode="goal_directed"
            )
            self.assertTrue(gd_res["pass"], gd_res)
            self.assertEqual(gd_res["unknown_kinds_probed"], ["gzip"])
            self.assertGreaterEqual(len(gd_res["distractor_kinds_skipped"]), 4)

            # Agent 2: Upfront "learn everything in room first" baseline
            up_store = eca.EpistemicStore(base / "store_upfront")
            up_agent = eca.EpistemicComputerAgent(up_store)
            up_res = up_agent.execute_room_goal(
                room, "Verify artifact payload.gz", mode="upfront_all"
            )
            self.assertTrue(up_res["pass"], up_res)
            self.assertGreaterEqual(len(up_res["unknown_kinds_probed"]), 5)
            # Goal-directed spends strictly fewer probes and faster wall-clock time!
            self.assertLess(gd_res["probes_spent"], up_res["probes_spent"])
            self.assertLess(gd_res["seconds"], up_res["seconds"])

            # Corrupt target artifact is caught on warm recall with 0 extra probes!
            (room / "bad.gz").write_bytes(b"\x1f\x8b\x08\x00CORRUPT_STREAM")
            warm_res = gd_agent.execute_room_goal(
                room, "Verify artifact bad.gz", mode="goal_directed"
            )
            self.assertEqual(warm_res["status"], "PASS__VERIFIED_CORRUPT_CAUGHT")
            self.assertEqual(warm_res["probes_spent"], 0)

    def test_nl_gui_grounding_redesign_transfer_audit_and_refusals(self) -> None:
        with tempfile.TemporaryDirectory(prefix="eca-gui-") as tmp:
            store = eca.EpistemicStore(Path(tmp) / "store")
            agent = eca.EpistemicComputerAgent(store)

            nl_cmd = (
                "check Enable Two-Factor Auth, enter backup@arena.local into Recovery Email, "
                "and click Save Changes"
            )
            env_a = iag.A11yEnvironment.from_html(LAYOUT_A)
            res_a = agent.execute_gui_goal(env_a, nl_cmd)
            self.assertTrue(res_a["pass"], res_a)
            self.assertEqual(res_a["model_calls"], 0)

            # Redesigned layout B (different tags, different tab names, different coordinates)
            env_b = iag.A11yEnvironment.from_html(LAYOUT_B_REDESIGNED)
            res_b = agent.execute_gui_goal(env_b, nl_cmd)
            self.assertTrue(res_b["pass"], res_b)

            # Audit external JSON store: 0 parameters, 0 coordinates, 0 xpaths!
            audit = store.audit()
            self.assertEqual(audit["parameters_stored"], 0)
            self.assertEqual(audit["raw_coordinates_saved"], 0)
            self.assertEqual(audit["raw_xpath_saved"], 0)
            self.assertGreaterEqual(audit["gui_workflows_count"], 1)

            # Inspectable + human-editable: edit JSON on disk and verify agent reloads it!
            raw_gui = json.loads(store.gui_path.read_text(encoding="utf-8"))
            self.assertIn("schemas", raw_gui)
            raw_gui["schemas"] = {}
            store.gui_path.write_text(json.dumps(raw_gui), encoding="utf-8")
            store.reload_all()
            self.assertEqual(store.audit()["gui_workflows_count"], 0)

            # Out-of-world & ungrounded NL commands are refused cleanly
            refused_world = agent.execute_gui_goal(
                LAYOUT_A,
                "click Activate Quantum Shield",
            )
            self.assertFalse(refused_world["pass"])
            self.assertEqual(refused_world["status"], "REFUSED__NAMES_NOTHING_IN_THIS_INTERFACE")

            refused_nl = agent.execute_gui_goal(
                LAYOUT_A,
                "write a haiku about autumn leaves",
            )
            self.assertFalse(refused_nl["pass"])
            self.assertEqual(refused_nl["status"], "REFUSED__UNGROUNDED_NL_GOAL")

    def test_nl_swe_repair_and_operator_prior_persistence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="eca-swe-") as tmp:
            base = Path(tmp)
            store = eca.EpistemicStore(base / "store")
            agent = eca.EpistemicComputerAgent(store)

            wt = base / "repo"
            wt.mkdir()
            (wt / "calc.py").write_text(
                "def apply_hook(fn, val):\n"
                "    if fn:\n"
                "        return fn(val)\n"
                "    return val\n",
                encoding="utf-8",
            )
            (wt / "tests").mkdir()
            (wt / "tests" / "test_calc.py").write_text(
                "import unittest\n"
                "from calc import apply_hook\n\n"
                "class EmptyLenCallable:\n"
                "    def __len__(self): return 0\n"
                "    def __call__(self, v): return v + 7\n\n"
                "class CalcTests(unittest.TestCase):\n"
                "    def test_none(self): self.assertEqual(apply_hook(None, 4), 4)\n"
                "    def test_falsy_callable(self): self.assertEqual(apply_hook(EmptyLenCallable(), 4), 11)\n",
                encoding="utf-8",
            )
            res = agent.execute_swe_goal(wt, "Fix the failing tests in tests/test_calc.py")
            self.assertTrue(res["pass"], res)
            self.assertEqual(res["model_calls"], 0)
            self.assertEqual(res["parameters_stored"], 0)
            self.assertGreaterEqual(store.audit()["swe_schemas_count"], 1)


if __name__ == "__main__":
    unittest.main()
