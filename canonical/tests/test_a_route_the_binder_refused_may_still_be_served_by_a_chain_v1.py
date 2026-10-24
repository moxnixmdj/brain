"""A binder's refusal may refute a selection -- and it may not open a write.

`capability_selection_retrieval_v1.admit` binds the sentence against a
capability's declared contract with the pinned binder.  Its verdict was used in
exactly one direction: to GRANT typed admission.  When it refused, the reason was
discarded and the route fell through to a lexical rule that could not see it.

Measured on b018600:

    "Write the text 'hello patch' to the file out.txt
     and save the report to out.txt.done.json."

        selected  document.convert.markdown_pdf.pandoc_weasyprint, score 7,
                  on the single word "report"
        text.file.write, sharing write, text and file with the sentence,
                  score 0 -- all three are generic tokens
        admit()   BINDING_REFUSED:markdown_path:
                  0_type_compatible_existing_files_named

The converter had already said it could not serve the sentence and was selected
anyway; the request then died at R3_WEAK_EVIDENCE having written nothing.

Reading the same verdict the other way let a chain answer it.  That immediately
exposed the boundary, which is why the second class of test here is the important
one: opened on EVERY binding refusal, the fallthrough let "Check the file X" --
which names a file and states no text -- reach composition, where PATH_OUTPUT
binds the only path in the sentence and the chain overwrote the file with a JSON
report while reporting pass=True.  That is the data-destruction class PR #6119
closed.  A sentence that states no content has nothing to compose into a write.
"""

import shutil
import unittest
from time import perf_counter_ns

from canonical.runtime import live_brain_route_admission_v1 as ra

ROOT = ra.ROOT
SCRATCH = "canonical/astra_runtime/tmp/chain1"


def _fresh(name):
    d = ROOT / ("%s/%s" % (SCRATCH, name))
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    return "%s/%s" % (SCRATCH, name)


def _solve(goal):
    return ra.solve({"task_id": "CH%d" % perf_counter_ns(), "goal": goal})


class TestAStatedWriteIsHeldToTheFileItNamed(unittest.TestCase):

    def test_the_file_the_sentence_named_is_the_one_named_in_the_refusal(self):
        base = _fresh("w1")
        target = "%s/out.txt" % base
        goal = ("Write the text 'hello patch' to the file %s "
                "and save the report to %s/report.json." % (target, base))
        result = _solve(goal)
        if result.get("pass") is True:
            self.assertTrue((ROOT / target).is_file(), "passed without the file")
            return
        errors = " ".join(result.get("promised_artifact_errors") or [])
        self.assertIn(
            target, errors,
            "refused without naming the file the sentence asked for: %s / %s"
            % (result.get("status"), result.get("failure_class")),
        )

    def test_the_refusal_is_not_a_weak_evidence_rule(self):
        """The reason must be the real one, not a lexical-rule placeholder."""
        base = _fresh("w2")
        goal = ("Write the text 'hello patch' to the file %s/out.txt "
                "and save the report to %s/report.json." % (base, base))
        result = _solve(goal)
        self.assertNotEqual(
            str(result.get("failure_class")),
            "ROUTE_ADMISSION_REJECTED:R3_WEAK_EVIDENCE",
            "still blaming weak lexical evidence for a route the binder refuted",
        )


class TestARequestThatStatesNoTextIsNeverComposedIntoAWrite(unittest.TestCase):
    """The boundary. This is the test that must never be relaxed."""

    def test_a_read_request_does_not_have_its_file_overwritten(self):
        base = _fresh("r1")
        target = "%s/data.txt" % base
        (ROOT / target).write_text("the original bytes\n", encoding="utf-8")
        _solve("Check the file %s" % target)
        self.assertEqual(
            (ROOT / target).read_text(encoding="utf-8"),
            "the original bytes\n",
            "a request that stated no text wrote over the file it named",
        )

    def test_no_read_request_reports_success_over_a_file_it_changed(self):
        base = _fresh("r2")
        damaged = []
        for verb in ("Check", "Read", "Inspect", "Verify", "Count"):
            d = _fresh("r2_%s" % verb.lower())
            f = "%s/d.txt" % d
            (ROOT / f).write_text("untouched\n", encoding="utf-8")
            r = _solve("%s the file %s" % (verb, f))
            if (ROOT / f).read_text(encoding="utf-8") != "untouched\n":
                damaged.append((verb, r.get("status")))
        self.assertEqual(damaged, [], "%d of 5 read requests damaged their file" % len(damaged))


if __name__ == "__main__":
    unittest.main()
