"""The page is the guide: unit tests always run; the live end-to-end test skips
honestly when its prerequisites are absent (real app tree, node, a Chromium with
DevTools on 9222). No test here claims a benchmark score.
"""
from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from canonical.runtime.gui_room_v1 import GuiRoom  # noqa: E402
from canonical.tools import the_page_is_the_guide_v1 as tool  # noqa: E402

APP_DIR = pathlib.Path(os.environ.get("BRAIN_GUI_TODOMVC_DIR",
                                      "/tmp/todomvc/todomvc-backbone-es6-gh-pages"))
DEBUG_PORT_URL = os.environ.get("CDP_DEBUG_URL", "http://127.0.0.1:9222").rstrip("/")


def prereqs() -> tuple[bool, str]:
    if not shutil.which("node"):
        return False, "node not found"
    if not APP_DIR.is_dir():
        return False, f"real app tree not at {APP_DIR}"
    try:
        import urllib.request
        with urllib.request.urlopen(DEBUG_PORT_URL + "/json/version", timeout=2) as r:
            if r.status != 200:
                return False, f"CDP endpoint returned {r.status}"
    except Exception as e:  # noqa: BLE001
        return False, f"no Chromium DevTools on {DEBUG_PORT_URL}: {e}"
    return True, "ok"


class GroundUniqueTests(unittest.TestCase):
    ELS = [
        {"role": "textbox", "name": "What needs to be done?", "text": "",
         "container_text": "", "enabled": True, "id": "new-todo", "x": 100, "y": 50},
        {"role": "checkbox", "name": "", "text": "",
         "container_text": "BRAIN-TRAIN-X", "enabled": True, "id": "", "x": 20, "y": 90},
        {"role": "checkbox", "name": "", "text": "",
         "container_text": "BRAIN-OTHER", "enabled": True, "id": "", "x": 20, "y": 130},
    ]

    def test_unique_match_selects(self):
        got = GuiRoom.ground_unique(self.ELS, role="textbox")
        self.assertEqual(got["status"], "SELECT")
        self.assertEqual(got["element"]["id"], "new-todo")

    def test_container_join_disambiguates(self):
        got = GuiRoom.ground_unique(self.ELS, role="checkbox", container_contains="BRAIN-TRAIN-X")
        self.assertEqual(got["status"], "SELECT")
        self.assertEqual(got["element"]["y"], 90)

    def test_no_match_escalates(self):
        got = GuiRoom.ground_unique(self.ELS, role="checkbox", container_contains="ABSENT")
        self.assertEqual(got["status"], "ESCALATE")

    def test_ambiguous_escalates(self):
        dupes = self.ELS + [dict(self.ELS[1])]
        got = GuiRoom.ground_unique(dupes, role="checkbox", container_contains="BRAIN-TRAIN-X")
        self.assertEqual(got["status"], "ESCALATE")
        self.assertIn("AMBIGUOUS", got["reason"])

    def test_disabled_candidates_are_refused(self):
        off = [dict(e, enabled=False) for e in self.ELS]
        got = GuiRoom.ground_unique(off, role="textbox")
        self.assertEqual(got["status"], "ESCALATE")


class AntiUnificationTests(unittest.TestCase):
    def test_only_the_datum_becomes_a_slot(self):
        trace = [
            {"verb": "set_text", "role": "textbox", "target": "UNIQUE", "text": "NEED-DATUM-1"},
            {"verb": "press", "key": "Enter"},
            {"verb": "click", "role": "checkbox", "container_contains": "NEED-DATUM-1"},
        ]
        out = tool.generalize_verified_trace(trace, "NEED-DATUM-1")
        self.assertEqual(out[0]["text"], "S0")
        self.assertEqual(out[2]["container_contains"], "S0")
        self.assertEqual(out[1]["key"], "Enter")  # mechanism, not datum
        self.assertEqual(out[0]["target"], "UNIQUE")

    def test_datum_absent_means_empty_slots(self):
        trace = [{"verb": "press", "key": "Enter"}]
        out = tool.generalize_verified_trace(trace, "NEED-DATUM-1")
        self.assertEqual(out, trace)


@unittest.skipUnless(prereqs()[0], prereqs()[1])
class LiveWebEnvironmentTests(unittest.TestCase):
    """The whole circuit on the real app in a real browser. Skips, never fakes."""

    def test_learn_admit_save_recall_and_controls(self):
        proc = subprocess.run(
            [sys.executable, str(REPO / "canonical/tools/the_page_is_the_guide_v1.py")],
            capture_output=True, text=True, timeout=600)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        receipt = REPO / "canonical/verification/THE_PAGE_IS_THE_GUIDE_20261124_V1.json"
        data = json.loads(receipt.read_text())
        claims = data["claims"]
        for name, value in claims.items():
            self.assertTrue(value, name)
        self.assertEqual(data["cost"]["model_calls"], 0)
        self.assertEqual(data["cost"]["network_calls_at_run_time"], 0)
        blob = json.dumps(data["saved_rule"])
        for datum in (tool.TRAIN_T, tool.ADMIT_A, tool.ADMIT_B, tool.RECALL_T):
            self.assertNotIn(datum, blob)


if __name__ == "__main__":
    unittest.main()
