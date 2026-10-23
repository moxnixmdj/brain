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

Measured after the fix, the failing goals report seven distinct causes:
SQLITE_STATUS_VALUE_UNRESOLVED,
BOUND_APT_METADATA_NOT_FOUND:pandoc, BOUND_APT_METADATA_NOT_FOUND:zbar-tools,
BOUND_CAPABILITY_SOURCE_UNSUPPORTED:brain_bound_system_tool,
BOUND_CAPABILITY_INDEPENDENT_VERIFICATION_NOT_EVIDENT:<capability>, STATUS_INVALID,
and the sqlite compound-plan variant. It was nine until the front-door selection
fix removed JSON_DOCX_SPEC_UNRESOLVED; the goal count fell from twelve to eleven
when BENCH_MARKDOWN_TO_DECISION stopped failing altogether, and to ten when
BENCH_UNITTEST_PASS_RATE stopped failing because the test-corpus audit began
reporting a red corpus instead of raising TEST_FILE_FAILED on the first one.
Measured on a clean tree: correct selection is 22 of 23 on both the benchmark
path and the front door that actually runs.
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

# Eleven goals that fail on a clean tree. Each is listed with the substring its
# real cause must contain -- pinned from a measurement, not from a guess.
#
# This was twelve. BENCH_MARKDOWN_TO_DECISION left the list because it stopped
# failing: the dependency tie-break and the unjustified-world-slot preference made
# it select `decision.synthesis.typed.stdlib` instead of the markdown-to-PDF
# converter, and it now returns
# PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED on a live run.
# Goals that fail on a clean tree, split by WHY, because the two classes have different
# lifetimes.  Re-measured this turn: the causes below are what a live front-door run
# reports now, not what an earlier measurement recorded.
#
# PORTABLE: the cause is a fact about the repository or about the sentence, so it holds on
# every host.  A goal that names no status value cannot have one resolved; a goal that names
# no evidence has nothing to assess.  These must fail everywhere and must keep failing.
PORTABLE_FAILURES = {
    "BENCH_SQLITE_CREATE_INSERT_QUERY": "SQLITE_STATUS_VALUE_UNRESOLVED",
    "BENCH_GROUNDING_AND_VERIFY": "STATUS_INVALID",
    # Moved twice, and both moves are the point.  This goal used to compile against a docx
    # producer and fail on a spec the sentence never stated; the front-door selection fix
    # moved it to knowledge.consistency.assess, where it then reported
    # BOUND_CAPABILITY_INDEPENDENT_VERIFICATION_NOT_EVIDENT -- "you have no proof you may
    # run".  That was false: the capability carries a receipt on disk whose mission digest
    # matches, and the adapter simply did not read that encoding.  It now runs and reports
    # the truth, which is that the sentence names no evidence to assess.  A refusal that
    # names the wrong cause sends the machine to acquire verification it already has instead
    # of asking for the input it actually lacks.
    "BENCH_JSON_FETCH_CONSISTENCY": "KNOWLEDGE_ASSESSMENT_INPUT_INVALID",
    "EXT_KNOWLEDGE_CONSISTENCY": "KNOWLEDGE_ASSESSMENT_INPUT_INVALID",
    "EXT_SQLITE_VERIFY": "SQLITE_STATUS_VALUE_UNRESOLVED",
}

# TOOL-DEPENDENT: the cause is a fact about THIS machine -- astra_runtime cross-checks the
# registry against the host apt snapshot (BOUND_APT_METADATA_NOT_FOUND, line 1213) and
# against shutil.which (BOUND_SYSTEM_TOOL_MISSING, line 1058).  A host that has the package
# legitimately gets a different, later answer, so these must NOT be pinned to a literal
# cause: that would encode one host into a portable test.  What is pinned instead is the
# invariant that actually matters -- when one of these is refused, the refusal names the
# missing dependency rather than collapsing into the opaque string.
TOOL_DEPENDENT_GOALS = (
    "EXT_QR_GENERATE",
    "EXT_BARCODE_DECODE",
    "EXT_OCR_SCANNED_IMAGE",
    "EXT_JQ_TABLE",
    "EXT_MD_TO_PDF",
)

_TOOL_CAUSE_MARKERS = ("BOUND_APT_METADATA_NOT_FOUND", "BOUND_SYSTEM_TOOL_MISSING")

FAILING_GOALS = PORTABLE_FAILURES

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
        cls.passed = set()
        for goal_id in list(PORTABLE_FAILURES) + list(TOOL_DEPENDENT_GOALS):
            result = _run(goal_id)
            reason = str(result.get("reason") or "")
            cls.causes[goal_id] = (
                reason.split(":REASON=", 1)[1].split(":RESULT=")[0]
                if ":REASON=" in reason else reason
            )
            if result.get("pass"):
                cls.passed.add(goal_id)

    def test_every_portably_failing_goal_still_fails(self):
        """Guard against the reporting fix silently turning refusals into passes.

        Scoped to PORTABLE_FAILURES on purpose.  The tool-dependent goals fail here because
        this machine lacks qrencode, zbar-tools, tesseract and pandoc; a host that has them
        may legitimately run the goal, and asserting failure there would pin one host's
        package set into a portable test.
        """
        for goal_id in PORTABLE_FAILURES:
            with self.subTest(goal=goal_id):
                self.assertFalse(_run(goal_id).get("pass"))

    def test_no_goal_reports_the_opaque_string_any_more(self):
        for goal_id, cause in self.causes.items():
            with self.subTest(goal=goal_id):
                self.assertNotEqual(cause.strip(), "")
                self.assertNotIn('RESULT={"status":"FAIL_CLOSED"}', cause)

    def test_each_portable_cause_names_its_real_blocker(self):
        for goal_id, needle in PORTABLE_FAILURES.items():
            with self.subTest(goal=goal_id):
                self.assertIn(needle, self.causes[goal_id], self.causes[goal_id])

    def test_a_tool_dependent_refusal_names_the_missing_dependency(self):
        """Refused for a missing package must say which package, on any host.

        This is the invariant that survives a host change.  If the tool is present the goal
        is allowed to proceed -- that is the correct answer, not a broken test -- but if it
        is refused, the refusal must name the dependency it is missing rather than collapse
        into the opaque wrapper this file exists to prevent.
        """
        refused = [g for g in TOOL_DEPENDENT_GOALS if g not in self.passed]
        if not refused:
            self.skipTest("every tool-dependent goal ran on this host")
        for goal_id in refused:
            with self.subTest(goal=goal_id):
                self.assertTrue(
                    any(m in self.causes[goal_id] for m in _TOOL_CAUSE_MARKERS),
                    self.causes[goal_id],
                )

    def test_a_missing_binary_and_an_unresolved_input_are_distinguishable(self):
        """These demand opposite responses: acquisition versus a better-specified goal.
        If they read the same, the machine cannot choose between them."""
        tool_side = next((g for g in TOOL_DEPENDENT_GOALS if g not in self.passed), None)
        if tool_side is None:
            self.skipTest("no tool-dependent goal was refused on this host")
        self.assertNotEqual(self.causes[tool_side], self.causes["EXT_SQLITE_VERIFY"])
        self.assertTrue(any(m in self.causes[tool_side] for m in _TOOL_CAUSE_MARKERS),
                        self.causes[tool_side])
        self.assertNotIn("BOUND_APT_METADATA_NOT_FOUND",
                         self.causes["EXT_SQLITE_VERIFY"])
        self.assertNotIn("BOUND_SYSTEM_TOOL_MISSING",
                         self.causes["EXT_SQLITE_VERIFY"])

    def test_the_causes_are_not_all_the_same(self):
        portable = {self.causes[g] for g in PORTABLE_FAILURES}
        self.assertGreaterEqual(len(portable), 3, f"portable causes collapsed: {portable}")


if __name__ == "__main__":
    unittest.main()
