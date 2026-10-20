"""Real-environment regression for missing bound system-tool prerequisites."""
from __future__ import annotations

import shutil
import unittest
import uuid
from pathlib import Path

from canonical.runtime import availability_v1
from canonical.runtime.live_brain_route_admission_v1 import ROOT, solve


BROWSER_CAPABILITY = "web.browser.rendered.capture.chromedriver"


class LiveSystemToolAvailabilityTests(unittest.TestCase):
    def test_registered_browser_availability_matches_real_chromedriver_path(self):
        registry = availability_v1.load_registry()
        entry = registry[BROWSER_CAPABILITY]
        present = shutil.which("chromedriver") is not None
        missing = availability_v1.missing(BROWSER_CAPABILITY, registry)

        self.assertEqual(missing, [] if present else ["chromedriver"])
        self.assertEqual(
            BROWSER_CAPABILITY in availability_v1.runnable(registry),
            present,
        )
        self.assertEqual(entry["source"]["executable"], "chromedriver")

    def test_live_goal_names_missing_driver_before_execution_or_output(self):
        if shutil.which("chromedriver") is not None:
            self.skipTest("the real browser driver is installed; missing-driver branch does not apply")

        task_id = "TEST_LIVE_MISSING_BROWSER_DRIVER_" + uuid.uuid4().hex
        work = ROOT / "canonical/astra_runtime/tmp" / task_id
        work.mkdir(parents=True, exist_ok=False)
        screenshot = work / "page.png"
        result_file = work / "page.json"
        screenshot_rel = screenshot.relative_to(ROOT).as_posix()
        result_rel = result_file.relative_to(ROOT).as_posix()
        goal = (
            "Using a rendered browser, open http://127.0.0.1:9 and capture the page. "
            f"Save a screenshot to {screenshot_rel} and save the result to {result_rel}."
        )
        try:
            result = solve({"task_id": task_id, "goal": goal})
            self.assertEqual(
                result["status"],
                "FAIL__CAPABILITY_ENVIRONMENT_PREREQUISITE_MISSING",
            )
            self.assertEqual(
                result["failure_class"],
                "CAPABILITY_ENVIRONMENT_DEPENDENCY_MISSING",
            )
            self.assertFalse(result["executed"])
            self.assertEqual(result["model_dependency_count"], 0)
            self.assertEqual(result["incremental_spend_usd"], 0)
            blocked = result["unavailable_capabilities"]
            self.assertEqual(
                blocked,
                [{
                    "capability_id": BROWSER_CAPABILITY,
                    "missing_executables": ["chromedriver"],
                }],
            )
            self.assertFalse(screenshot.exists())
            self.assertFalse(result_file.exists())
        finally:
            for path in work.iterdir():
                if path.is_file():
                    path.unlink()
            work.rmdir()
            state_dir = ROOT / "canonical/astra_runtime/state"
            for path in state_dir.glob(task_id + "__*"):
                if path.is_file():
                    path.unlink()


if __name__ == "__main__":
    unittest.main()
