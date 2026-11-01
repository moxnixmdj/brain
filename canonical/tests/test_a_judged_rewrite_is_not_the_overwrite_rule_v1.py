"""The rule that protects a source file from a report was blocking the edit itself.

Measured 2026-11-01: ``Format <path>/calc.py.`` refused, and the composer's own run of
the sentence failed one layer down with

    LocalExecutionFailure:OUTPUT_OVERWRITES_A_STATED_SOURCE:
        output_path=canonical/astra_runtime/tmp/test_formatter/calc.py:read_as=argv

``ruff format A`` rewrites A.  The binder hands the capability A as ``output_path`` and
as an ``argv`` operand, and the write-authority rule -- which exists so a capability
cannot write its REPORT over the source it read -- refused, because it asks only whether
a destination is also a source.  It never asked the question that separates the two
cases: can anything CHECK the result afterwards?

The exemption is exactly as wide as the postcondition table.  A program with an entry in
``_MUTATING_POSTCONDITIONS`` re-derives its own promise from disk, so a rewrite of the
file it names is the job, not the accident.  A program with no entry there keeps the old
refusal, byte for byte.
"""
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import raw_goal_trace_acceptance_v1 as accept  # noqa: E402
from canonical.runtime import write_authority_v1 as wa  # noqa: E402


class AJudgedRewriteIsNotTheOverwriteRule(unittest.TestCase):

    def setUp(self) -> None:
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="brain-write-rule-"))
        (self.root / "calc.py").write_text("def add(a,b):\n    return a+b\n", encoding="utf-8")

    def test_a_program_with_a_postcondition_may_rewrite_the_file_it_names(self) -> None:
        self.assertIn("ruff", accept._MUTATING_POSTCONDITIONS,
                      "the formatter lost its judging entry again")
        self.assertIsNone(wa.violation(
            self.root,
            {"argv": ["ruff", "format", "calc.py"], "output_path": "calc.py"},
            "shell.command.run"))

    def test_the_exemption_is_the_table_and_not_a_list_of_programs(self) -> None:
        """Whatever the acceptance layer can judge, it may rewrite -- and only that."""
        judged = set(accept._MUTATING_POSTCONDITIONS)
        self.assertTrue({"ruff", "sed", "cp"} <= judged, judged)
        for program in sorted(judged):
            self.assertIsNone(wa.violation(
                self.root, {"argv": [program, "calc.py"], "output_path": "calc.py"},
                "shell.command.run"), program)

    def test_a_program_nobody_can_check_is_still_refused(self) -> None:
        reason = wa.violation(
            self.root,
            {"argv": ["unsome-tool", "calc.py"], "output_path": "calc.py"},
            "shell.command.run")
        self.assertIn("OUTPUT_OVERWRITES_A_STATED_SOURCE", str(reason))

    def test_a_report_written_over_its_own_source_is_still_refused(self) -> None:
        reason = wa.violation(
            self.root,
            {"output_path": "calc.py", "source_root": "."},
            "code.multilanguage.parse.tree_sitter.v1")
        self.assertIn("OUTPUT_OVERWRITES_A_STATED_SOURCE", str(reason))


if __name__ == "__main__":
    unittest.main()
