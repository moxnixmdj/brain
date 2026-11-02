"""A fact about a file must not be answered by printing the file.

Measured on ``75eeed7`` through ``solve()`` over 35 ordinary engineering
sentences, 24 reported ``pass=True`` -- and three of those passes were false:

    "Show the permissions of the file X" -> cat X  -> the whole file, certified
    "Show the size of the file X"        -> cat X  -> the whole file, certified

The row that caught them is the ``cat`` row, whose first alternation matches ANY
"show ... file" sentence at all.  Not one byte of that output says what the
permissions are or how big the file is.  This is the dominant defect shape there
is -- a capability reporting a pass on a sentence it does not own is worse than a
refusal, because a refusal says what it cannot check and this says the opposite
of what was asked, with a receipt.

The row's own comment already learned this lesson once, for "the lines containing
text", and scoped its guard to that single phrasing.  The general law is written
right there: *"Refusing to guess the value is right; answering a different
question is not."*

The answer was available all along.  ``stat`` is on the read-only allowlist and
``_known_programs`` already returns it -- only the route was missing.  The rows
now sit BEFORE ``cat``, by this table's own stated rule that the narrower claim
about a path comes before the general one, and each is keyed on a noun that names
a FACT rather than on a verb, so "show the file X" keeps printing the file.

Every test here fails on ``75eeed7`` except the four that pin behaviour which
must not change.
"""

import pathlib
import shutil
import sys
import unittest

_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from canonical.runtime import live_brain_route_admission_v1 as admission  # noqa: E402

BODY = "alpha one\ngamma two\n"


class _File(unittest.TestCase):
    """One file per test, removed by addCleanup.

    Named for its content, never "test_something": path segments are query terms
    for the routing suites, so a scratch path carrying that word would leak into
    any ranking measured in the same process.
    """

    _NEXT = 0

    def setUp(self):
        import os

        type(self)._NEXT += 1
        self.base = (
            _ROOT / "canonical/astra_runtime/tmp"
            / ("factq_%d_%d" % (os.getpid(), type(self)._NEXT))
        )
        self.base.mkdir(parents=True)
        self.file = self.base / "alpha.txt"
        self.file.write_text(BODY)
        self.addCleanup(shutil.rmtree, self.base, True)
        self._n = 0

    def answer(self, goal):
        # A unique task id per call: the admission front door keeps per-task
        # state, and reusing one id across sentences in the same process made
        # later answers come back empty.
        self._n += 1
        out = admission.solve({"task_id": "FACTQ_%d" % self._n, "goal": goal})
        steps = ((out.get("composer_execution") or {}).get("steps") or [{}])
        step = steps[0]
        argv = (step.get("args") or {}).get("argv") or []
        stdout = str((step.get("result") or {}).get("stdout") or "")
        return out, [str(part) for part in argv], stdout


class AFactAboutAFileIsNotItsContentsTests(_File):
    def test_the_permissions_are_answered_with_the_permissions(self):
        out, argv, stdout = self.answer(
            "Show the permissions of the file %s" % self.file
        )
        self.assertIs(out.get("pass"), True, str(out.get("status")))
        self.assertEqual(argv[0], "stat")
        self.assertEqual(stdout.strip(), _mode_string(self.file.stat().st_mode))
        self.assertNotIn("alpha one", stdout)

    def test_the_size_is_answered_in_bytes(self):
        _, argv, stdout = self.answer("Show the size of the file %s" % self.file)
        self.assertEqual(argv[0], "stat")
        self.assertEqual(stdout.strip(), str(len(BODY)))
        self.assertNotIn("alpha one", stdout)

    def test_the_size_agrees_with_the_bytes_on_disk(self):
        """The falsification: a wrong format string still prints a number."""
        self.file.write_text(BODY + "third line\n")
        _, _, stdout = self.answer("Show the size of the file %s" % self.file)
        self.assertEqual(stdout.strip(), str(self.file.stat().st_size))

    def test_the_owner_is_answered_with_the_owner(self):
        import pwd

        _, argv, stdout = self.answer("Show the owner of the file %s" % self.file)
        self.assertEqual(argv[0], "stat")
        self.assertEqual(
            stdout.strip(),
            pwd.getpwuid(self.file.stat().st_uid).pw_name,
        )

    def test_the_answer_is_reproducible_from_the_argv_alone(self):
        """A promise is stateable only if derivable from the argv."""
        _, argv, stdout = self.answer("Show the permissions of the file %s" % self.file)
        self.assertIn("-c", argv)
        self.assertEqual(argv[-1], str(self.file))
        import subprocess

        again = subprocess.run(argv, capture_output=True, text=True)
        self.assertEqual(again.returncode, 0)
        self.assertEqual(again.stdout, stdout)


class TheFileItselfIsStillPrintedWhenThatIsWhatWasAskedTests(_File):
    def test_show_the_contents_still_reads_the_file(self):
        _, argv, stdout = self.answer("Show the contents of the file %s" % self.file)
        self.assertEqual(argv[0], "cat")
        self.assertEqual(stdout, BODY)

    def test_show_the_file_still_reads_the_file(self):
        _, argv, stdout = self.answer("Show the file %s" % self.file)
        self.assertEqual(argv[0], "cat")
        self.assertEqual(stdout, BODY)

    def test_a_count_of_lines_is_still_a_count(self):
        _, argv, stdout = self.answer("How many lines are in the file %s" % self.file)
        self.assertEqual(argv[0], "wc")
        self.assertIn("-l", argv)
        self.assertTrue(stdout.startswith("2"), stdout)

    def test_a_count_of_bytes_is_still_a_count_and_not_a_stat(self):
        """"How many bytes" is a COUNT and already had its own row; `stat` must
        not steal it."""
        _, argv, stdout = self.answer("How many bytes are in the file %s" % self.file)
        self.assertEqual(argv[0], "wc")
        self.assertIn("-c", argv)
        self.assertTrue(stdout.startswith(str(len(BODY))), stdout)


def _mode_string(mode):
    import stat as _stat

    return "".join(
        _filetype_letter(mode)
        + _triad(mode, _stat.S_IRUSR, _stat.S_IWUSR, _stat.S_IXUSR)
        + _triad(mode, _stat.S_IRGRP, _stat.S_IWGRP, _stat.S_IXGRP)
        + _triad(mode, _stat.S_IROTH, _stat.S_IWOTH, _stat.S_IXOTH)
    )


def _filetype_letter(mode):
    import stat as _stat

    if _stat.S_ISDIR(mode):
        return "d"
    if _stat.S_ISLNK(mode):
        return "l"
    return "-"


def _triad(mode, r, w, x):
    return ("r" if mode & r else "-") + ("w" if mode & w else "-") + (
        "x" if mode & x else "-"
    )


if __name__ == "__main__":
    unittest.main(verbosity=2)
