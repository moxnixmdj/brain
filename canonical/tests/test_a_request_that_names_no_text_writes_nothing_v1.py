"""A request that names no text must not write anything.

Measured on ``25e3d67``: **13 of 15 ordinary non-write requests destroyed the file
they were told about, and every one of them reported ``pass=True``.**

    "Read the file canonical/astra_runtime/tmp/x9k2p/note.txt"
        -> note.txt now contains "canonical/astra_runtime/tmp/x9k2p/note.txt"

Read, count, delete, sort, reverse, show, print, sum, search, truncate. The file
was opened for writing and filled with its own name.

One line did it. ``bind`` fills a STRING slot from ``extract_content``, and when
the sentence states no text it fell back to ``paths[0]`` -- so a filename became
the payload. And because a read names exactly one path, that same path also bound
``PATH_OUTPUT``, which takes ``paths[-1]``. The source and the destination were
the same file, so the read overwrote what it was reading.

This is the same family as the defect fixed in PR #6118, one layer up. There, a
payload the sentence stated was edited on the way to the disk. Here, a payload the
sentence never stated was invented -- and invention is worse, because there is
nothing in the request for an acceptance check to disagree with. The payload guard
added in #6118 asks whether the text appears in the sentence; a filename from the
sentence passes that question, so "Find the text hello in note.txt" wrote "hello"
into note.txt and was certified exact.

The fix is to stop inventing. A STRING slot with no stated text is left unbound,
the composer reports ``OPEN__COMPOSER_SLOT_UNBOUND``, and nothing is written.
Measured: files damaged 13 of 15 -> 0 of 15, and requests reporting ``pass=True``
while damaging a file 13 of 15 -> 0 of 15. Legitimate writes are untouched: 367
prose 223/144 with identical failure kinds, benchmark 23/23 and 22/23, CI 136 OK,
live-path suites identical to baseline.

These tests are hard in the sense that they read the file back. They do not trust
``pass``, ``status`` or any producer flag, because the defect was precisely a
green verdict over a destroyed file.
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

from canonical.runtime.composer_route_v1 import bind  # noqa: E402

# No English words, on purpose: every component of a path in a request becomes a
# goal token, so a directory named for the behaviour under test can change which
# capability is selected and make these tests fail for an unrelated reason.
SCRATCH = "canonical/astra_runtime/tmp/x9k2p"
ORIGINAL = "PRECIOUS ORIGINAL CONTENT\n"

# Split by what the sentence ASKS FOR, which is the distinction the single list
# this replaced could not make.  Measured after ordinary prose requests began to
# run real commands: "Delete the file a1.txt" deleted a1.txt, and the old list
# called that damage.  It was not damage -- it was the request.  A guard that
# cannot tell the two apart stops being a guard and becomes a ban.
#
# These twelve state no mutation.  The file must survive byte for byte, which is
# the claim PR #6119 established and the one that matters.
NON_MUTATING_REQUESTS = (
    "Read the file {f}",
    "Count the lines in the file {f}",
    "Sort the lines of the file {f}",
    "Reverse the file {f}",
    "Show the file {f}",
    "Print the file {f}",
    "Sum the numbers in the file {f}",
    "Check the file {f}",
    "Verify the file {f}",
    "Search the file {f}",
    # "Truncate the file {f}" is NOT in this list, and was.  Truncating is a
    # mutation -- it is the plainest way to say "empty this file" -- so a corpus
    # of requests that state no mutation was the wrong home for it, and keeping it
    # here pinned a refusal of work the sentence plainly asked for.  It is served
    # by `sed -i 1,$d` and pinned as served in the ordinary-sentence suite.

    "Diff the file {f} against {g}",
)

# These three state a mutation, so the file MUST change -- and must change to
# exactly the state the sentence described, and no further.  This is a harder
# claim than the one it replaces: "nothing happened" was satisfied by a machine
# that did nothing at all, while this is only satisfied by one that did the
# requested work and stopped there.  The second file is the control: it is never
# an operand of any of these three, so if it moves, the request overshot.
STATED_MUTATIONS = (
    # (template, source must survive?, destination contents after)
    ("Delete the file {f}", False, "other\n"),
    ("Copy the file {f} to {g}", True, ORIGINAL),
    ("Move the file {f} to {g}", False, ORIGINAL),
)

# Kept under the old name so the count of guarded requests stays visible: the
# guard still covers fifteen sentences, it now just knows which ones mutate.
NON_WRITE_REQUESTS = NON_MUTATING_REQUESTS + tuple(t for t, _, _ in STATED_MUTATIONS)


def _stated_end_state(template: str):
    """What the sentence promised, as (source_present, destination_contents)."""
    for tmpl, source_present, dest_contents in STATED_MUTATIONS:
        if tmpl == template:
            return source_present, dest_contents
    # No mutation stated: both files exactly as they were.
    return True, "other\n"



def _fresh_two() -> tuple[str, str]:
    root = ROOT / SCRATCH
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    f = "%s/a1.txt" % SCRATCH
    g = "%s/b2.txt" % SCRATCH
    (ROOT / f).write_text(ORIGINAL, encoding="utf-8")
    (ROOT / g).write_text("other\n", encoding="utf-8")
    return f, g


def _solve(goal: str):
    from canonical.runtime.live_brain_route_admission_v1 import solve

    return solve({"task_id": "NOWRITE_%x" % time.perf_counter_ns(), "goal": goal})


class TestNoTextNoWrite(unittest.TestCase):
    """The file a request merely mentions must survive the request."""

    def tearDown(self):
        shutil.rmtree(ROOT / SCRATCH, ignore_errors=True)

    def test_a_request_that_states_no_mutation_leaves_the_file_intact(self):
        damaged = []
        for template in NON_MUTATING_REQUESTS:
            f, g = _fresh_two()
            _solve(template.format(f=f, g=g))
            if not (ROOT / f).is_file():
                damaged.append((template, "the file it only read was removed"))
                continue
            if (ROOT / f).read_text(encoding="utf-8") != ORIGINAL:
                damaged.append((template, (ROOT / f).read_text(encoding="utf-8")[:60]))
            if not (ROOT / g).is_file() or (ROOT / g).read_text(encoding="utf-8") != "other\n":
                damaged.append((template, "second file altered"))
        self.assertEqual(
            damaged,
            [],
            "%d of %d requests that name a file but state no mutation changed it" % (
                len(damaged), len(NON_MUTATING_REQUESTS)),
        )

    def test_a_stated_mutation_does_what_was_stated_and_nothing_more(self):
        """The half the old list got wrong: doing the work is not damage.

        Harder than the assertion it replaces.  "Nothing changed" passes for a
        machine that did nothing; this passes only for one that performed
        exactly the stated mutation and left the untouched file alone.
        """
        wrong = []
        for template, source_present, dest_contents in STATED_MUTATIONS:
            f, g = _fresh_two()
            _solve(template.format(f=f, g=g))
            if (ROOT / f).is_file() != source_present:
                wrong.append((template, "source present=%s, stated=%s"
                              % ((ROOT / f).is_file(), source_present)))
            if not (ROOT / g).is_file() or (ROOT / g).read_text(encoding="utf-8") != dest_contents:
                wrong.append((template, "destination is %r, stated %r"
                              % ((ROOT / g).read_text(encoding="utf-8")
                                 if (ROOT / g).is_file() else None, dest_contents)))
        self.assertEqual(wrong, [], "a stated mutation did not do exactly what "
                                    "was stated: %r" % wrong)

    def test_no_request_reports_success_over_an_end_state_it_did_not_state(self):
        """The sharp half, restated so it still bites now that commands run.

        The defect PR #6119 found was a green verdict over a destroyed file.
        That is still the thing to catch, but "destroyed" is no longer the test
        -- a request may now legitimately destroy a file.  The test is whether
        the verdict is green over an end state the SENTENCE did not state.
        """
        false_passes = []
        for template in NON_WRITE_REQUESTS:
            f, g = _fresh_two()
            result = _solve(template.format(f=f, g=g))
            source_present, dest_contents = _stated_end_state(template)
            if (ROOT / f).is_file() != source_present:
                matches = False
            else:
                matches = ((ROOT / g).is_file()
                           and (ROOT / g).read_text(encoding="utf-8") == dest_contents)
            if result.get("pass") is True and not matches:
                false_passes.append(template)
        self.assertEqual(
            false_passes,
            [],
            "reported pass=True over an end state the sentence never stated: %r"
            % false_passes,
        )

    def test_reading_a_file_does_not_fill_it_with_its_own_name(self):
        f, _ = _fresh_two()
        _solve("Read the file %s" % f)
        self.assertEqual((ROOT / f).read_text(encoding="utf-8"), ORIGINAL)


class TestBinderDoesNotInventAPayload(unittest.TestCase):
    """The mechanism, at the level where it can be stated exactly."""

    SIGNATURE = {"content": "STRING", "output_path": "PATH_OUTPUT"}

    def test_a_sentence_with_no_stated_text_leaves_the_slot_unbound(self):
        args = bind(self.SIGNATURE, "Read the file canonical/astra_runtime/tmp/x9k2p/a1.txt")
        self.assertNotIn(
            "content",
            args,
            "the binder invented a payload the sentence never stated: %r" % args.get("content"),
        )

    def test_a_filename_is_never_used_as_the_payload(self):
        goal = "Count the lines in the file canonical/astra_runtime/tmp/x9k2p/a1.txt"
        args = bind(self.SIGNATURE, goal)
        self.assertNotEqual(args.get("content"), "canonical/astra_runtime/tmp/x9k2p/a1.txt")

    def test_a_stated_text_still_binds(self):
        """Negative control: the fix must not stop real writes from binding."""
        args = bind(
            self.SIGNATURE,
            "Write the text hello world to the file canonical/astra_runtime/tmp/x9k2p/a1.txt",
        )
        self.assertEqual(args.get("content"), "hello world")


class TestLegitimateWritesStillWork(unittest.TestCase):
    """The other negative control, end to end."""

    CASES = (
        ("Write the text hello world to the file %s", "hello world"),
        ("Write the text the results are in the attachment to the file %s",
         "the results are in the attachment"),
    )

    def tearDown(self):
        shutil.rmtree(ROOT / SCRATCH, ignore_errors=True)

    def test_a_stated_text_is_still_written_verbatim(self):
        wrong = []
        for template, expected in self.CASES:
            root = ROOT / SCRATCH
            shutil.rmtree(root, ignore_errors=True)
            root.mkdir(parents=True, exist_ok=True)
            out = "%s/c3.txt" % SCRATCH
            _solve(template % out)
            got = (ROOT / out).read_text(encoding="utf-8") if (ROOT / out).is_file() else None
            if got != expected:
                wrong.append((template[:40], got))
        self.assertEqual(wrong, [], "a legitimate write stopped working: %r" % wrong)


if __name__ == "__main__":
    unittest.main()
