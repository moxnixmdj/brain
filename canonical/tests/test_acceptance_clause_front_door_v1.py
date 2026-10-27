"""The measured-repair loop must complete and be accepted from one sentence."""

from __future__ import annotations

import json
import pathlib
import shutil
import sys
import unittest
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import live_brain_route_admission_v1 as admission  # noqa: E402

TMP_ROOT = ROOT / "canonical" / "astra_runtime" / "tmp" / "test_acceptance_clause_front_door"


class TestMeasuredRepairAcceptanceFromOneSentence(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(TMP_ROOT, ignore_errors=True)
        self.work = TMP_ROOT / uuid.uuid4().hex[:12]
        self.work.mkdir(parents=True)
        (self.work / "m.py").write_text(
            "def f(x):\n    return x < 3\n", encoding="utf-8"
        )
        (self.work / "trace_fail.py").write_text(
            "from m import f\nassert f(3)\n", encoding="utf-8"
        )
        (self.work / "trace_pass.py").write_text(
            "from m import f\nassert f(2)\n", encoding="utf-8"
        )
        (self.work / "test_all.py").write_text(
            "from m import f\nassert f(3)\nassert f(2)\nassert not f(4)\n",
            encoding="utf-8",
        )
        self.rel = str(self.work.relative_to(ROOT)).replace("\\", "/")
        self.source_before = (self.work / "m.py").read_bytes()

    def tearDown(self):
        shutil.rmtree(TMP_ROOT, ignore_errors=True)

    def _goal(self, objectives="`tests_pass` must be true and `python_parse_ok` must be true",
              prefix_extra=""):
        return (
            "Write a measured acceptance repair report to "
            f"{self.rel}/report.json for the source root {self.rel} "
            f"{prefix_extra}using the test path {self.rel}/test_all.py "
            f"where {objectives}"
        )

    def _solve(self, goal):
        return admission.solve({
            "task_id": "ACCEPTANCE_CLAUSE_" + uuid.uuid4().hex[:16],
            "goal": goal,
        })

    def _adapter_result(self, out):
        rows = out.get("execution") or []
        self.assertTrue(rows, out)
        return rows[0].get("result") or {}

    def test_a_report_goal_does_not_promise_a_source_mutation(self):
        self.assertEqual(admission._promised_source_files(self._goal()), [])

    def test_the_front_door_completes_repair_measurement_and_acceptance(self):
        goal = self._goal()
        out = self._solve(goal)
        self.assertTrue(out.get("pass"), out)
        self.assertEqual(out.get("compiled_capability_id"),
                         "python.software.repair.measured_acceptance.v1")
        self.assertNotIn("promised_source_change_errors", out)
        adapter = self._adapter_result(out)
        self.assertEqual(
            adapter.get("status"),
            "PASS__REPAIR_REALIZED_MEASURED_AND_ACCEPTED",
        )
        self.assertTrue(adapter.get("acceptance_stop_authorized"))
        self.assertEqual(adapter.get("semantic_residual_obligation_ids"), [])
        self.assertTrue(adapter.get("output_verified"))
        self.assertEqual((self.work / "m.py").read_bytes(), self.source_before)
        report = json.loads((self.work / "report.json").read_text(encoding="utf-8"))
        self.assertTrue(report["pass"], report)
        self.assertEqual(report["measured_fields"]["tests_pass"], True)
        self.assertEqual(report["measured_fields"]["python_parse_ok"], True)

    def test_a_hidden_requirement_in_the_routing_prefix_still_fails_closed(self):
        goal = self._goal(prefix_extra="preserve every secret file ")
        out = self._solve(goal)
        self.assertFalse(out.get("pass"), out)
        adapter = self._adapter_result(out)
        self.assertFalse(adapter.get("pass"), adapter)
        self.assertTrue(adapter.get("semantic_residual_obligation_ids"))

    def test_a_false_objective_cannot_be_accepted(self):
        goal = self._goal(objectives="`tests_pass` must be false")
        out = self._solve(goal)
        self.assertFalse(out.get("pass"), out)
        adapter = self._adapter_result(out)
        self.assertTrue(adapter.get("repair_pass"), adapter)
        self.assertFalse(adapter.get("acceptance_stop_authorized"), adapter)


if __name__ == "__main__":
    unittest.main(verbosity=2)
