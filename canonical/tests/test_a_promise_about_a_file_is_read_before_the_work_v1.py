"""A promise about a file is read before the work, or it means nothing.

``_future_artifacts`` answers one question: which paths does this sentence name
that do not exist **yet**. "Yet" means before the work. On the main path it has
always been read before ``_execute``. In the composition branch it was read as an
argument to ``_composed_holds_up`` -- that is, *after* ``_try_composed`` had
already executed the chain.

So a file the work legitimately removed came back as a promise the chain had
failed to keep. Measured on ``6411cf6``:

    "Run the shell command mv A B"
        -> A moved to B correctly, B holds A's bytes
        -> FAIL_CLOSED__PROMISED_ARTIFACT_MISSING
        -> promised_artifact_errors: ["PROMISED_ARTIFACT_MISSING:A"]

The refusal named the source -- the one file the sentence asked to have gone.
The chain was refused for succeeding.

This is the same shape as the defects fixed in the preceding changes: a check
that looks right and is evaluated against the wrong world. It is narrow to
trigger, which is why it survived -- it needs a sentence that names no single
capability, so composition answers, and a chain that consumes one of the files
the sentence names.

The consequence for ``touch`` is reported rather than hidden. Reading the list
before the work means ``touch B`` now promises B, and B is created empty, so the
long-standing R6 rule that a promised artifact must be non-empty applies to it
and it is refused with PROMISED_ARTIFACT_EMPTY. It was passing before only
because the list was read after the file already existed. Whether an empty file
ought to satisfy a promise is a separate question about R6 and is deliberately
not decided here; what is fixed is the order in which the promise is read.

Measured after the change: the 367-prose corpus is unchanged at 223 pass / 144
fail with 174 exact-verified and identical failure kinds, and a stated ``mv``
reaches exact semantic acceptance for the first time -- the postcondition written
for it two changes ago was already in place and simply could not be reached.
"""

from __future__ import annotations

import shutil
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
RUNTIME = ROOT / "canonical" / "runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

# No English words: path components become goal tokens, so a directory named for
# the behaviour under test can change which capability is selected.
SCRATCH = "canonical/astra_runtime/tmp/h7d4m"
BODY = "banana\napple\ncherry\n"


def _solve(goal: str):
    from canonical.runtime.live_brain_route_admission_v1 import solve

    return solve({"task_id": "PROM_%x" % time.perf_counter_ns(), "goal": goal})


def _fresh() -> str:
    root = ROOT / SCRATCH
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    f = "%s/a1.txt" % SCRATCH
    (ROOT / f).write_text(BODY, encoding="utf-8")
    return f


class TestThePromiseListIsReadBeforeTheWork(unittest.TestCase):
    def setUp(self):
        self.f = _fresh()
        self.dest = "%s/b2.txt" % SCRATCH

    def tearDown(self):
        shutil.rmtree(ROOT / SCRATCH, ignore_errors=True)

    def test_the_list_names_what_is_absent_before_the_work_not_after(self):
        from canonical.runtime import live_brain_route_admission_v1 as L

        before = L._future_artifacts("Run the shell command mv %s %s" % (self.f, self.dest))
        self.assertEqual(before, [self.dest],
                         "before the work, only the destination is absent: %r" % before)
        # Now do the work, and read it again: the answer must differ, which is
        # exactly why the order matters.
        shutil.move(ROOT / self.f, ROOT / self.dest)
        after = L._future_artifacts("Run the shell command mv %s %s" % (self.f, self.dest))
        self.assertEqual(after, [self.f],
                         "after the work the same call names the source: %r" % after)
        self.assertNotEqual(before, after,
                            "the two readings are the same, so this test proves nothing")


class TestACommandThatConsumesAFileIsNotRefusedForConsumingIt(unittest.TestCase):
    def setUp(self):
        self.f = _fresh()
        self.dest = "%s/b2.txt" % SCRATCH

    def tearDown(self):
        shutil.rmtree(ROOT / SCRATCH, ignore_errors=True)

    def test_a_stated_move_is_verified_not_refused_for_its_own_source(self):
        result = _solve("Run the shell command mv %s %s" % (self.f, self.dest))
        self.assertNotIn(
            "PROMISED_ARTIFACT_MISSING:" + self.f,
            result.get("promised_artifact_errors") or [],
            "refused a move for removing the file the sentence asked it to remove",
        )
        self.assertTrue(str(result.get("status")).endswith(
            "EXACT_SEMANTIC_ACCEPTANCE_VERIFIED"),
            "a correct move was not certified: %s / %s"
            % (result.get("status"), result.get("promised_artifact_errors")))

    def test_a_stated_move_really_moved_the_bytes(self):
        _solve("Run the shell command mv %s %s" % (self.f, self.dest))
        self.assertFalse((ROOT / self.f).exists(), "the source is still there")
        self.assertTrue((ROOT / self.dest).is_file(), "the destination was not created")
        self.assertEqual((ROOT / self.dest).read_text(encoding="utf-8"), BODY)

    def test_a_stated_copy_is_still_verified(self):
        """Negative control: the fix must not narrow what already worked."""
        result = _solve("Run the shell command cp %s %s" % (self.f, self.dest))
        self.assertTrue(str(result.get("status")).endswith(
            "EXACT_SEMANTIC_ACCEPTANCE_VERIFIED"),
            "a correct copy stopped being certified: %s" % result.get("status"))
        self.assertTrue((ROOT / self.f).is_file(), "cp consumed its source")
        self.assertEqual((ROOT / self.dest).read_text(encoding="utf-8"), BODY)

    def test_a_stated_read_is_still_verified(self):
        result = _solve("Run the shell command cat %s" % self.f)
        self.assertTrue(str(result.get("status")).endswith(
            "EXACT_SEMANTIC_ACCEPTANCE_VERIFIED"),
            "a correct read stopped being certified: %s" % result.get("status"))


class TestAMissingPromiseIsStillAMissingPromise(unittest.TestCase):
    """The gate must still bite, or the fix is just a way past it."""

    def tearDown(self):
        shutil.rmtree(ROOT / SCRATCH, ignore_errors=True)

    def test_a_destination_that_is_never_created_is_still_refused(self):
        from canonical.runtime.live_brain_route_admission_v1 import (
            promised_artifact_errors,
        )

        _fresh()
        errors = promised_artifact_errors(
            "Run the shell command cp %s/a1.txt %s/b2.txt" % (SCRATCH, SCRATCH),
            ["%s/b2.txt" % SCRATCH],
        )
        self.assertEqual(errors, ["PROMISED_ARTIFACT_MISSING:%s/b2.txt" % SCRATCH])

    def test_an_empty_file_the_sentence_asked_to_be_written_is_still_refused(self):
        """The fake-output guard must still bite when there was something to write.

        This is the case the non-empty clause exists for: the sentence states
        text, and the file arrived holding none of it.  Reverting the scoping to
        "always non-empty" keeps this passing, so it is the pin that stops the
        scoped rule from being read as "the empty check was deleted".
        """
        from canonical.runtime.live_brain_route_admission_v1 import (
            promised_artifact_errors,
        )

        _fresh()
        dest = "%s/b2.txt" % SCRATCH
        (ROOT / dest).write_text("", encoding="utf-8")
        errors = promised_artifact_errors(
            "Write the text 'real content' to the file %s" % dest,
            [dest],
        )
        self.assertEqual(errors, ["PROMISED_ARTIFACT_EMPTY:" + dest])

    def test_an_empty_file_is_the_stated_result_when_no_text_was_promised(self):
        """`touch` makes an empty file. That is the whole of what was asked.

        A guard must be scoped to the claim the sentence actually makes.  This
        asserts the other half, so the pair above cannot pass by simply
        deleting the empty check.
        """
        from canonical.runtime.live_brain_route_admission_v1 import (
            promised_artifact_errors,
        )

        _fresh()
        dest = "%s/b3.txt" % SCRATCH
        (ROOT / dest).write_text("", encoding="utf-8")
        self.assertEqual(
            promised_artifact_errors("Run the shell command touch %s" % dest, [dest]),
            [],
        )

    def test_the_refusal_names_the_error_that_actually_fired(self):
        """A 0-byte file on disk was reported as MISSING.

        Measured: `touch` created the file, the evidence list said
        PROMISED_ARTIFACT_EMPTY, and the failure_class the caller received said
        PROMISED_ARTIFACT_MISSING -- the refusal named a reason its own evidence
        contradicted.  Both directions are pinned.
        """
        from canonical.runtime.live_brain_route_admission_v1 import (
            promised_artifact_class,
        )

        self.assertEqual(
            promised_artifact_class(["PROMISED_ARTIFACT_EMPTY:a/b.txt"]),
            "PROMISED_ARTIFACT_EMPTY",
        )
        self.assertEqual(
            promised_artifact_class(["PROMISED_ARTIFACT_MISSING:a/b.txt"]),
            "PROMISED_ARTIFACT_MISSING",
        )


if __name__ == "__main__":
    unittest.main()
