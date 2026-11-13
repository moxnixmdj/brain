#!/usr/bin/env python3
"""Pinned tests for bringing a name the file already imports, and for its measured worth."""
from __future__ import annotations

import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel.taught_actions import bring_names_v1 as B
from canonical.swe_kernel.taught_actions import edit_by_example_v1 as E

FIXTURE = ROOT / "canonical/tests/fixtures/bring_names_measure_v1.json"

BEFORE = """from datetime import UTC, datetime

def f():
    return datetime.utcnow()
"""
AFTER = """from datetime import UTC, datetime

def f():
    return datetime.now(UTC)
"""


def rules():
    return E.learn(BEFORE, AFTER)


class Bringing(unittest.TestCase):
    def test_the_name_joins_the_line_the_file_already_has(self):
        target = "from datetime import date, datetime, timedelta\n\ndef g():\n    return datetime.utcnow()\n"
        text, brought = B.bring(target, rules())
        self.assertEqual(brought, {"UTC": "from datetime import UTC"})
        self.assertIn("from datetime import UTC, date, datetime, timedelta\n", text)
        self.assertNotIn("from datetime import date, datetime, timedelta, UTC", text)

    def test_the_organ_then_makes_the_edit_on_the_brought_text(self):
        target = "from datetime import date, datetime, timedelta\n\ndef g():\n    return datetime.utcnow()\n"
        text, count = B.rewrite_with_brought_names(rules(), target)
        self.assertEqual(count, 1)
        self.assertIn("datetime.now(UTC)", text)
        self.assertIn("from datetime import UTC, date, datetime, timedelta", text)

    def test_a_brought_import_without_an_applied_rule_is_not_returned(self):
        target = "from datetime import datetime\n\ndef g(value):\n    return value\n"
        text, count = B.rewrite_with_brought_names(rules(), target)
        self.assertEqual(text, target)
        self.assertEqual(count, 0)

    def test_a_star_import_is_refused(self):
        target = "from datetime import *\n\ndef g():\n    return datetime.utcnow()\n"
        with self.assertRaises(B.Refused):
            B.bring(target, rules())

    def test_a_relative_import_is_not_invented(self):
        relative = E.learn(
            "from .utils import Helper\n\ndef f(x):\n    return Helper(x)\n",
            "from .utils import Helper\n\ndef f(x):\n    return Helper(x).run()\n",
        )
        target = "def g(x):\n    return Helper(x)\n"
        self.assertEqual(B.bring(target, relative), (None, {}))

    def test_a_name_the_target_already_binds_is_not_brought(self):
        target = "from datetime import datetime\nUTC = 1\n\ndef g():\n    return datetime.now(UTC)\n"
        self.assertEqual(B.bring(target, rules()), (None, {}))

    def test_a_new_standard_library_line_is_added_when_the_module_is_absent(self):
        target = "import os\n\ndef g():\n    return os.getcwd()\n"
        text, brought = B.bring(target, rules())
        self.assertEqual(brought, {"UTC": "from datetime import UTC"})
        self.assertIn("from datetime import UTC\n", text)


class Measured(unittest.TestCase):
    def test_the_recorded_measurement_is_the_one_pinned(self):
        record = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(record["schema"], "BRING_NAMES_MEASURE_V1")
        self.assertEqual(record["authority"], "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT")
        base = record["summary"]["base"]
        self.assertEqual((base["right"], base["developers_changes"]), (386, 1674))
        self.assertAlmostEqual(base["coverage"], 0.230585, places=6)
        self.assertAlmostEqual(base["precision"], 0.946078, places=6)
        brought = record["summary"]["brought"]
        self.assertEqual(brought["right"], 493)
        self.assertAlmostEqual(brought["coverage"], 0.294504, places=6)
        self.assertAlmostEqual(brought["precision"], 0.912963, places=6)
        self.assertEqual(brought["wrong_changes"], 17)
        self.assertEqual(brought["whole_files"], 134)
        self.assertEqual(base["wrong_changes"], 14)
        self.assertEqual(base["whole_files"], 117)
        rows = record["per_pull_request"]
        self.assertEqual(rows["arigatoexpress/Project-Go-Forward#483"]["brought"]["right"], 150)
        self.assertEqual(rows["arigatoexpress/Project-Go-Forward#483"]["base"]["right"], 43)
        self.assertEqual(rows["kuangjiafa/automagician#55"]["brought"]["right"], 0)
        self.assertEqual(rows["kuangjiafa/automagician#55"]["brought"]["wrong_changes"], 1)


if __name__ == "__main__":
    unittest.main()
