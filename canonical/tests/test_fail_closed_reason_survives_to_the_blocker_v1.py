"""A refusal must carry its cause, or the machine cannot act on it.

`verified_bound_capability_execution_adapter_v1.execute` caught every exception and
returned the cause in `errors`, a LIST:

    {"status": "FAIL_CLOSED", "pass": False, "errors": ["RuntimeError:INPUT_FILE_MISSING"]}

The controller's blocker builder, `astra_runtime._verify_action_expectation`, reads
`result["reason"]` or `result["error"]` -- SINGULAR keys -- and appends ":REASON=" only
when one is present. So the cause was in the payload and invisible to the only message
anyone ever reads.

Measured consequence: all twelve failing benchmark goals reported the byte-identical
string

    Blocker:ACTION_EXPECTATION_FAILED:pass:OBSERVED=False:RESULT={"status":"FAIL_CLOSED"}

A machine that cannot say why it refused cannot route the refusal. It cannot tell a
missing C binary that needs acquisition from a goal that is genuinely under-specified
and correctly fail-closed -- and those two demand opposite responses.

The fix reuses the convention this repository already uses one module over:
`bound_capability_execution_verifier_v1` sets `"reason"` to exactly
`type(exc).__name__ + ":" + str(exc)`. Nothing is loosened. `status` stays
FAIL_CLOSED, `pass` stays False, `errors` is untouched, and the caller's expectation
still fails.

Measured after the fix, the same twelve goals report nine distinct causes:
SQLITE_STATUS_VALUE_UNRESOLVED, JSON_DOCX_SPEC_UNRESOLVED, TEST_FILE_FAILED:<path>,
BOUND_APT_METADATA_NOT_FOUND:pandoc, BOUND_APT_METADATA_NOT_FOUND:zbar-tools,
BOUND_CAPABILITY_SOURCE_UNSUPPORTED:brain_bound_system_tool,
BOUND_CAPABILITY_INDEPENDENT_VERIFICATION_NOT_EVIDENT:<capability>, STATUS_INVALID,
and the sqlite compound-plan variant. Acceptance stays 11 of 23, verified episodes
stay 9, and correct selection stays 21 of 23.
"""
from __future__ import annotations

import pathlib
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from canonical.runtime import goal_compilation_benchmark_v1 as benchmark  # noqa: E402
from canonical.runtime import live_integrated_brain_v1 as live  # noqa: E402
from canonical.runtime import (  # noqa: E402
    verified_bound_capability_execution_adapter_v1 as adapter,
)

# The opaque string every refusal used to collapse into.
_OPAQUE = 'ACTION_EXPECTATION_FAILED:pass:OBSERVED=False:RESULT={"status":"FAIL_CLOSED"}'

# Twelve goals that fail on a clean tree. Each is listed with the substring its real
# cause must contain -- pinned from a measurement, not from a guess.
FAILING_GOALS = {
    "BENCH_SQLITE_CREATE_INSERT_QUERY": "SQLITE_STATUS_VALUE_UNRESOLVED",
    "BENCH_GROUNDING_AND_VERIFY": "STATUS_INVALID",
    "BENCH_JSON_FETCH_CONSISTENCY": "JSON_DOCX_SPEC_UNRESOLVED",
    "BENCH_UNITTEST_PASS_RATE": "TEST_FILE_FAILED",
    "BENCH_MARKDOWN_TO_DECISION": "BOUND_APT_METADATA_NOT_FOUND:pandoc",
    "EXT_QR_GENERATE": "BOUND_CAPABILITY_INDEPENDENT_VERIFICATION_NOT_EVIDENT",
    "EXT_BARCODE_DECODE": "BOUND_APT_METADATA_NOT_FOUND:zbar-tools",
    "EXT_OCR_SCANNED_IMAGE": "BOUND_CAPABILITY_SOURCE_UNSUPPORTED",
    "EXT_KNOWLEDGE_CONSISTENCY": "BOUND_CAPABILITY_INDEPENDENT_VERIFICATION_NOT_EVIDENT",
    "EXT_JQ_TABLE": "BOUND_APT_METADATA_NOT_FOUND:pandoc",
    "EXT_SQLITE_VERIFY": "SQLITE_STATUS_VALUE_UNRESOLVED",
    "EXT_MD_TO_PDF": "BOUND_APT_METADATA_NOT_FOUND:pandoc",
}

_GOALS = {g["id"]: g["goal"] for g in
          benchmark.BENCHMARK_GOALS + benchmark.EXTENDED_BENCHMARK_GOALS}

def _run(goal_id):
    """One real front-door run under a unique task_id.

    A repeated task_id is short-circuited by the controller, so a fixed id would make
    this suite pass once and silently skip afterwards.
    """
    import uuid
    task_id = f"REASON_{goal_id}_{uuid.uuid4().hex[:8]}"
    return live.run_raw_goal({"task_id": task_id, "goal": _GOALS[goal_id]})


class FailClosedPayloadCarriesItsCauseTests(unittest.TestCase):
    """The adapter-level contract, measured on a capability that really raises."""

    @classmethod
    def setUpClass(cls):
        # sqlite.table.verify_against_json_records raises out of run() when the JSON it
        # is pointed at is absent -- a real failure, not a stub.
        cls.out = adapter.execute(
            "sqlite.table.verify_against_json_records",
            inputs={
                "capability_id": "sqlite.table.verify_against_json_records",
                "goal": "Verify a sqlite table round trip.",
                "json_path": "canonical/astra_runtime/tmp/THIS_FILE_DOES_NOT_EXIST.json",
                "sqlite_path": "canonical/astra_runtime/tmp/REASON_PROBE.sqlite",
            },
        )

    def test_the_cause_is_reported_under_the_key_the_blocker_reads(self):
        self.assertIsInstance(self.out.get("reason"), str)
        self.assertTrue(self.out["reason"], "reason must not be empty")

    def test_reason_and_errors_carry_the_same_string(self):
        """One cause, one spelling. If the two ever diverge, one of them is a lie."""
        self.assertEqual(self.out["errors"], [self.out["reason"]])

    def test_the_cause_names_the_exception_type_and_its_message(self):
        self.assertRegex(self.out["reason"], r"^[A-Za-z_][A-Za-z0-9_]*:.+")

    def test_fail_closed_is_preserved_exactly(self):
        """This is a reporting fix, not a loosening. The refusal must be unchanged."""
        self.assertEqual(self.out["status"], "FAIL_CLOSED")
        self.assertIs(self.out["pass"], False)
        self.assertIs(self.out["terminal_authority"], False)

    def test_nothing_is_leaked_into_a_result_shape(self):
        """A refused execution must not look like a produced artifact."""
        for leaked in ("result", "output_path", "output_sha256", "verified_output"):
            self.assertNotIn(leaked, self.out)

    def test_a_successful_execution_does_not_gain_a_reason(self):
        """The `reason` key belongs to the exception path only."""
        ok = adapter.execute(
            "python.source.audit.ast",
            inputs={
                "capability_id": "python.source.audit.ast",
                "source_root": "canonical/runtime/bound_capabilities",
                "output_path": "canonical/astra_runtime/tmp/REASON_PROBE_AUDIT.json",
            },
        )
        if ok.get("status") == "FAIL_CLOSED":
            self.skipTest("capability unavailable in this environment")
        self.assertNotIn("reason", ok)


class ControllerBlockerCarriesTheCauseTests(unittest.TestCase):
    """End to end: the message a caller actually reads must name the cause."""

    def test_a_failing_goal_no_longer_reports_the_opaque_string(self):
        result = _run("EXT_SQLITE_VERIFY")
        self.assertFalse(result.get("pass"))
        reason = str(result.get("reason") or "")
        self.assertNotEqual(reason, "Blocker:" + _OPAQUE)
        self.assertIn(":REASON=", reason, reason)

    def test_the_cause_is_the_specific_one_not_a_generic_wrapper(self):
        result = _run("EXT_SQLITE_VERIFY")
        reason = str(result.get("reason") or "")
        cause = reason.split(":REASON=", 1)[1].split(":RESULT=")[0]
        self.assertIn("SQLITE_STATUS_VALUE_UNRESOLVED", cause)


class EveryRefusalIsDistinguishableTests(unittest.TestCase):
    """The point of the change: refusals that demand opposite responses must differ."""

    @classmethod
    def setUpClass(cls):
        cls.causes = {}
        for goal_id in FAILING_GOALS:
            result = _run(goal_id)
            reason = str(result.get("reason") or "")
            cls.causes[goal_id] = (
                reason.split(":REASON=", 1)[1].split(":RESULT=")[0]
                if ":REASON=" in reason else reason
            )

    def test_every_failing_goal_still_fails(self):
        """Guard against the reporting fix silently turning refusals into passes."""
        for goal_id in FAILING_GOALS:
            with self.subTest(goal=goal_id):
                self.assertFalse(_run(goal_id).get("pass"))

    def test_no_goal_reports_the_opaque_string_any_more(self):
        for goal_id, cause in self.causes.items():
            with self.subTest(goal=goal_id):
                self.assertNotEqual(cause.strip(), "")
                self.assertNotIn('RESULT={"status":"FAIL_CLOSED"}', cause)

    def test_each_cause_names_its_real_blocker(self):
        for goal_id, needle in FAILING_GOALS.items():
            with self.subTest(goal=goal_id):
                self.assertIn(needle, self.causes[goal_id], self.causes[goal_id])

    def test_a_missing_binary_and_an_unresolved_input_are_distinguishable(self):
        """These demand opposite responses: acquisition versus a better-specified goal.
        If they read the same, the machine cannot choose between them."""
        self.assertNotEqual(
            self.causes["EXT_MD_TO_PDF"], self.causes["EXT_SQLITE_VERIFY"]
        )
        self.assertIn("BOUND_APT_METADATA_NOT_FOUND", self.causes["EXT_MD_TO_PDF"])
        self.assertNotIn("BOUND_APT_METADATA_NOT_FOUND",
                         self.causes["EXT_SQLITE_VERIFY"])

    def test_the_causes_are_not_all_the_same(self):
        self.assertGreaterEqual(len(set(self.causes.values())), 5,
                                f"causes collapsed: {self.causes}")


if __name__ == "__main__":
    unittest.main()
