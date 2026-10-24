"""There is exactly one way to ask why a goal failed, and it is never blank.

The diagnosis lives in a different field depending on which layer refused: the
compiler boundary writes `compiler_detail`, the controller writes `reason`, the
truth check writes `tool_truth_errors`.  Measured on bcb5661a over the 72 verified
capabilities named in prose, all 70 failures carried a diagnosis -- but 67 of them
were blank in `reason`, which is the only field the end-to-end measurement harness
read when it built the "why" column of its failure report.

So two-thirds of the failure report had no cause in it, and a failure that was
fully diagnosed looked like one with no cause at all.  Worse,
`environment_blocker()` read `reason` alone, so a machine problem reported by the
compiler layer would have been counted as a Brain failure -- which corrupts a pass
rate rather than merely understating a message.
"""
import json
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
for _p in (str(ROOT), str(ROOT / "canonical/runtime"), str(ROOT / "execution_guard")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from canonical.runtime.live_brain_route_admission_v1 import failure_reason, solve  # noqa: E402
import live_solver_end_to_end_measurement_v1 as harness  # noqa: E402


def _prose(cid):
    stem = re.sub(r"\.py\.auto\.v\d+$", "", cid.rsplit("/", 1)[-1])
    return "Run the " + stem.replace("_", " ").replace(".", " ") + "."


class OneAnswerForWhyTest(unittest.TestCase):

    def test_the_compiler_layer_is_read(self):
        self.assertEqual(
            failure_reason({"pass": False,
                            "compiler_detail": "text.file.write:contract_not_stated:content"}),
            "text.file.write:contract_not_stated:content")

    def test_it_falls_back_through_every_layer_in_order(self):
        self.assertEqual(failure_reason({"pass": False, "reason": "Blocker:X"}), "Blocker:X")
        self.assertEqual(failure_reason({"pass": False, "tool_truth_errors": ["A", "B"]}), "A; B")
        self.assertEqual(failure_reason({"pass": False, "blocker": "B"}), "B")
        self.assertEqual(
            failure_reason({"pass": False, "failure_class": "FC", "status": "S"}), "FC")

    def test_the_most_specific_field_wins(self):
        """A compiler diagnosis must not be hidden behind a generic class."""
        self.assertEqual(
            failure_reason({"pass": False,
                            "compiler_detail": "cap:contract_not_stated:x",
                            "reason": "generic",
                            "failure_class": "CLASS"}),
            "cap:contract_not_stated:x")

    def test_no_failure_anywhere_in_the_class_has_a_blank_cause(self):
        """All 72: a failing result always yields a non-empty reason.  Measured on
        bcb5661a, 67 of the 70 failures were blank in `reason` alone."""
        caps = sorted(json.loads(
            (ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text()
        )["capabilities"])
        self.assertGreaterEqual(len(caps), 72)
        blank = []
        seen = 0
        for cap in caps:
            result = solve({"task_id": "WHY", "goal": _prose(cap)})
            if result.get("pass") is True:
                continue
            seen += 1
            if not failure_reason(result).strip():
                blank.append(cap)
        self.assertGreater(seen, 0)
        self.assertEqual(blank, [], "failures with no cause: %s" % blank)

    def test_a_machine_problem_reported_by_the_compiler_is_still_a_machine_problem(self):
        """The regression this prevents: environment_blocker read `reason` alone,
        so a blocker surfaced by another layer counted as a Brain failure."""
        self.assertEqual(
            harness.environment_blocker(
                {"reason": "", "compiler_detail": "BOUND_APT_PACKAGE_NOT_INSTALLED:foo"}),
            "BOUND_APT_PACKAGE_NOT_INSTALLED")
        self.assertEqual(
            harness.environment_blocker(
                {"reason": "Blocker:BOUND_APT_METADATA_NOT_FOUND:zint"}),
            "BOUND_APT_METADATA_NOT_FOUND")

    def test_a_genuine_brain_failure_is_not_excused_as_environment(self):
        """The accessor must not turn every failure into an environment blocker."""
        for result in ({"reason": "", "compiler_detail": "text.file.write:contract_not_stated:content"},
                       {"reason": "Blocker:SQLITE_VALUE_MISMATCH"},
                       {"failure_class": "TOOL_REPORTED_NON_SUCCESS"}):
            self.assertIsNone(harness.environment_blocker(result), result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
