"""A second request must not die on the first request's scratch.

Measured 2026-10-30 with ``execution_guard/swe_request_probe_v1.py --suite hardcore``: two of 46
advanced requests printed a raw adapter error on stdout instead of an answer::

    {"error": "EDIT_PLAN_INPUT_INVALID", "error_kind": "systemic",
     "message": "output already exists: canonical/astra_runtime/tmp/spool_0_output.json"}

Cause: the DAG planner synthesises spool paths for slots a sentence does not name, and it makes
them deterministic ON PURPOSE -- "the same request always spools to the same place".  The adapters
then refused to write a path that already existed, so the first request worked and every later one
that needed the same slot was refused by its own leftovers.  Determinism was right; treating our
own scratch as somebody's file was not.

The rule pinned here is narrow, because the protection it touches is real:

  * a machine spool artifact (``canonical/astra_runtime/tmp/spool_*``) may be replaced by a later
    run -- it is scratch the machine itself created;
  * any other output path that already exists is somebody's file and is still refused.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402
from canonical.runtime.bound_capabilities import python_crossfile_edit_choreograph as crossfile  # noqa: E402
from canonical.runtime.bound_capabilities import python_symbol_resolve as resolver  # noqa: E402

WORK = "canonical/astra_runtime/tmp/test_spool_repeat"
SPOOL = ROOT / "canonical/astra_runtime/tmp/spool_0_output.json"


def _fresh(name: str) -> str:
    base = WORK + "/" + name
    shutil.rmtree(ROOT / base, ignore_errors=True)
    (ROOT / base / "pkg").mkdir(parents=True)
    (ROOT / base / "pkg" / "calc.py").write_text("def mul(a, b):\n    return a * b\n",
                                                 encoding="utf-8")
    return base


class OurOwnScratchIsScratch(unittest.TestCase):

    def test_the_spool_predicate_is_narrow(self):
        for value in ("canonical/astra_runtime/tmp/spool_0_output.json",
                      "canonical/astra_runtime/tmp/spool_3_report_1.json"):
            self.assertTrue(crossfile._is_machine_spool(value), value)
            self.assertTrue(resolver._is_machine_spool(value), value)
        for value in ("canonical/astra_runtime/tmp/report.json",
                      "canonical/runtime/spool_0_output.json",
                      "pkg/spool_0_output.json", "", None):
            self.assertFalse(crossfile._is_machine_spool(value), value)
            self.assertFalse(resolver._is_machine_spool(value), value)

    def test_a_left_over_spool_is_replaced_not_refused(self):
        base = _fresh("repeat")
        SPOOL.parent.mkdir(parents=True, exist_ok=True)
        SPOOL.write_text('{"left_over": true}', encoding="utf-8")
        result = door.solve({"task_id": "spool_repeat",
                             "goal": "Rename the symbol `mul` to `multiply` in %s/pkg/calc.py."
                                     % base})
        blob = json.dumps(result, default=str)
        self.assertNotIn("output already exists", blob)
        self.assertNotIn("EDIT_PLAN_INPUT_INVALID", blob)

    def test_a_user_file_that_already_exists_is_still_refused(self):
        base = _fresh("user_file")
        user_report = ROOT / base / "report.json"
        user_report.write_text('{"mine": true}', encoding="utf-8")
        with self.assertRaises(SystemExit):
            crossfile._safe_path(str(ROOT), base + "/report.json")
        self.assertEqual(user_report.read_text(encoding="utf-8"), '{"mine": true}')


if __name__ == "__main__":
    unittest.main()
