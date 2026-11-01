"""A census on an empty substrate is not a census.

Measured 2026-11-01 on ``c0576``-era main, same commit, same 49 sentences, one variable:

    bare image                           census 36 of 49 served   matrix 42 REAL
    after scripts/restore_substrate_v1.py  census 36 of 49 served   matrix 44 REAL

The census count did not move, so nothing looked wrong -- and that is the point of the test.
The MATRIX moved by two, on ``type_check`` (``PASS_BASELINE_ONLY`` -> ``PASS``) and ``lint``
(``PASS_SYNTAX_ONLY`` -> ``PASS``), which means two verdicts were facts about the machine and
were printed in the same column as facts about the tree. ``scripts/restore_substrate_v1.py``
existed the whole time. No instrument read its verdict; nothing called it.

What is asserted here, and how it is independently checked:

* the gate refuses to let the instrument print a board, and it refuses by EXIT CODE with the
  reason on stdout -- checked by running the real ``main()`` of the real instruments, not by
  calling a helper and trusting its return value;
* when it refuses, no artefact is written -- the JSON file the census would have produced does
  not exist afterwards, so a log cannot be mistaken for a measurement;
* the oracle for "the substrate is incomplete" is ``scripts/restore_substrate_v1.py --check``
  run as a subprocess against this image, whose printed ``modules_present=N/10`` must agree with
  what the precondition reports. The instrument never gets to grade its own homework;
* ``--allow-incomplete-substrate`` still measures, and prints its caveat BEFORE the first number.

The substituted probe in the refusal tests is a different IMAGE, not a different code path.
"""
from __future__ import annotations

import importlib.util
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
GUARD = ROOT / "execution_guard"
if str(GUARD) not in sys.path:
    sys.path.insert(0, str(GUARD))

import substrate_precondition_v1 as precondition_mod  # noqa: E402
import swe_advanced_probe_v1 as census_mod  # noqa: E402
import swe_capability_matrix_v1 as matrix_mod  # noqa: E402

EMPTY_IMAGE = {
    "ready": False,
    "modules_present": 1,
    "modules_total": 10,
    "modules_missing": ["pytest", "ruff", "mypy", "hypothesis", "tree_sitter",
                        "tree_sitter_languages", "coverage", "bandit", "crosshair"],
    "binaries_missing": [],
    "parser_installed": None,
    "parser_expected": "0.20.4",
}
READY_IMAGE = dict(EMPTY_IMAGE, ready=True, modules_present=10, modules_total=10,
                   modules_missing=[], parser_installed="0.20.4")


class _Image:
    """A stand-in for this machine: the same shape ``restore_substrate_v1.verify`` returns."""

    def __init__(self, **state: object) -> None:
        self.state = state

    def __call__(self) -> dict[str, object]:
        return dict(self.state)


class TheCensusRefusesToCountOnAnEmptySubstrate(unittest.TestCase):
    def setUp(self) -> None:
        self._saved_probe = precondition_mod.probe
        self._saved_restore = precondition_mod.restore
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def tearDown(self) -> None:
        precondition_mod.probe = self._saved_probe
        precondition_mod.restore = self._saved_restore

    def _empty_image_that_cannot_be_restored(self) -> pathlib.Path:
        precondition_mod.probe = _Image(**EMPTY_IMAGE)
        precondition_mod.restore = lambda: False
        return pathlib.Path(self._tmp.name) / "census.json"

    def test_the_census_exits_non_zero_and_writes_no_board(self) -> None:
        out = self._empty_image_that_cannot_be_restored()
        code = census_mod.main(["--json", str(out)])
        self.assertEqual(2, code, "an empty substrate must not produce a census exit code")
        self.assertFalse(out.exists(), "a board was written on an image that cannot measure")

    def test_the_matrix_exits_non_zero_and_writes_no_board(self) -> None:
        out = self._empty_image_that_cannot_be_restored()
        code = matrix_mod.run(as_json=True)
        self.assertEqual(2, code, "an empty substrate must not produce a matrix exit code")

    def test_the_refusal_names_what_is_missing(self) -> None:
        self._empty_image_that_cannot_be_restored()
        status = precondition_mod.precondition()
        self.assertFalse(status.usable)
        self.assertEqual("SUBSTRATE_INCOMPLETE", status.verdict)
        for module in ("ruff", "mypy", "pytest"):
            self.assertIn(module, status.reason)

    def test_one_restore_is_attempted_before_refusing(self) -> None:
        calls: list[int] = []

        def restore() -> bool:
            calls.append(1)
            return True

        states = [_Image(**EMPTY_IMAGE), _Image(**READY_IMAGE)]
        precondition_mod.probe = lambda: states[min(len(calls), 1)]()
        precondition_mod.restore = restore
        status = precondition_mod.precondition()
        self.assertEqual(1, len(calls), "the one command that fixes this must be run once")
        self.assertTrue(status.usable)
        self.assertTrue(status.restored)

    def test_an_allowed_incomplete_run_says_so_before_any_number(self) -> None:
        import io
        precondition_mod.probe = _Image(**EMPTY_IMAGE)
        precondition_mod.restore = lambda: False
        said = io.StringIO()
        status = precondition_mod.precondition(allow_incomplete=True, out=said)
        self.assertTrue(status.usable)
        self.assertEqual("SUBSTRATE_INCOMPLETE_ALLOWED", status.verdict)
        lines = [ln for ln in said.getvalue().splitlines() if ln.strip()]
        self.assertTrue(lines[0].startswith("SUBSTRATE "), lines)
        self.assertTrue(any("SUBSTRATE_CAVEAT" in ln for ln in lines), lines)
        self.assertLess(next(i for i, ln in enumerate(lines) if "SUBSTRATE_CAVEAT" in ln),
                        len(lines), "the caveat must be printed with the verdict, not after it")


class ThePreconditionAgreesWithTheRestoreScript(unittest.TestCase):
    """The oracle: the repository's own ``--check``, run as a subprocess, on this image."""

    def test_modules_present_matches_the_restore_script(self) -> None:
        done = subprocess.run([sys.executable, str(ROOT / "scripts" / "restore_substrate_v1.py"),
                               "--check"], cwd=str(ROOT), capture_output=True, text=True,
                              timeout=300)
        match = re.search(r"modules_present=(\d+)/(\d+)", done.stdout)
        self.assertIsNotNone(match, done.stdout + done.stderr)
        present, total = int(match.group(1)), int(match.group(2))

        status = precondition_mod.precondition(restore_if_missing=False)
        self.assertEqual(present, status.modules_present, done.stdout)
        self.assertEqual(total, status.modules_total, done.stdout)
        # And the exit code of the owner is the verdict the precondition reports.
        self.assertEqual(done.returncode == 0, status.ready,
                         "the instrument and the one command that owns this disagree\n"
                         + done.stdout)


if __name__ == "__main__":
    unittest.main()
