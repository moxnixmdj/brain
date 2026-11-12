"""Whatever a project's own test starts while Brain reads it, that test's own tearDown must end.

History (measured 2026-11-11). `whitebox_introspector_and_trace_synthesizer_v1.harvest_live_io_examples`
runs the test files of the project under repair inside the *calling* interpreter, to record what the
functions under repair are expected to return. For a `unittest.TestCase` it called `setUp()` and the
test method, and nothing else: `tearDown()` was never called and the cleanups a test registered were
never run.

So everything a suite arms per test stayed armed in the solver after the harvest returned: timers,
patches, open files, temporary directories, environment changes. The case that exposed it was the
plainest one. A suite gave every test a time limit -- an alarm set in `setUp`, cancelled in
`tearDown`. A normal test run is unaffected. Read by the harvest, the alarm stayed armed with its
full time and expired later, in the middle of the solver's own work. The repair did not fail on its
merits; the process solving it was interrupted by a timer that belonged to somebody else's test.

This is the same family as `test_solver_leaves_no_import_shadow_v1.py` (the harvest restored
`sys.path` and never `sys.modules`): code that borrows the caller's interpreter has to give all of
it back.

The order pinned here is `unittest`'s own, from the standard library's documentation: `tearDown` runs
after the test method whether it passed or not, but only if `setUp` succeeded; the cleanups run in
every case, after `tearDown`, or straight after a `setUp` that raised.
"""
from __future__ import annotations

import pathlib
import signal
import sys
import threading

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import whitebox_introspector_and_trace_synthesizer_v1 as whitebox  # noqa: E402

_MODULE_UNDER_REPAIR = "def double(x):\n    return x + x\n"

# A suite that writes down each step of its own life cycle next to itself.
_SUITE_HEAD = (
    "import pathlib\n"
    "import unittest\n"
    "from calc_under_repair import double\n"
    "\n"
    "LOG = pathlib.Path(__file__).with_name('life_cycle.log')\n"
    "\n"
    "def note(word):\n"
    "    with LOG.open('a', encoding='utf-8') as fh:\n"
    "        fh.write(word + '\\n')\n"
    "\n"
)

_ORDINARY_SUITE = _SUITE_HEAD + (
    "class DoubleTests(unittest.TestCase):\n"
    "    def setUp(self):\n"
    "        note('setUp')\n"
    "        self.addCleanup(note, 'cleanup')\n"
    "    def tearDown(self):\n"
    "        note('tearDown')\n"
    "    def test_three(self):\n"
    "        self.assertEqual(double(3), 6)\n"
    "    def test_two(self):\n"
    "        self.assertEqual(double(2), 4)\n"
)

_SUITE_WITH_A_TIME_LIMIT = _SUITE_HEAD + (
    "import signal\n"
    "\n"
    "class DoubleTests(unittest.TestCase):\n"
    "    def setUp(self):\n"
    "        signal.setitimer(signal.ITIMER_REAL, 600)\n"
    "    def tearDown(self):\n"
    "        signal.setitimer(signal.ITIMER_REAL, 0)\n"
    "    def test_two(self):\n"
    "        self.assertEqual(double(2), 4)\n"
)

_SUITE_WHOSE_SET_UP_FAILS = _SUITE_HEAD + (
    "class DoubleTests(unittest.TestCase):\n"
    "    def setUp(self):\n"
    "        note('setUp began')\n"
    "        self.addCleanup(note, 'cleanup')\n"
    "        raise RuntimeError('the fixture could not be built')\n"
    "    def tearDown(self):\n"
    "        note('tearDown')\n"
    "    def test_two(self):\n"
    "        self.assertEqual(double(2), 4)\n"
)

_SUITE_WHOSE_TEAR_DOWN_FAILS = _SUITE_HEAD + (
    "class DoubleTests(unittest.TestCase):\n"
    "    def setUp(self):\n"
    "        self.addCleanup(note, 'cleanup')\n"
    "    def tearDown(self):\n"
    "        note('tearDown')\n"
    "        raise RuntimeError('the fixture could not be taken down')\n"
    "    def test_three(self):\n"
    "        self.assertEqual(double(3), 6)\n"
    "    def test_two(self):\n"
    "        self.assertEqual(double(2), 4)\n"
)


def _project(tmp_path: pathlib.Path, suite: str) -> tuple[pathlib.Path, pathlib.Path]:
    (tmp_path / "calc_under_repair.py").write_text(_MODULE_UNDER_REPAIR, encoding="utf-8")
    (tmp_path / "tests").mkdir()
    test_file = tmp_path / "tests" / "test_calc_under_repair.py"
    test_file.write_text(suite, encoding="utf-8")
    return tmp_path, test_file


def _harvest(tmp_path: pathlib.Path, suite: str) -> tuple[list, list[str]]:
    project, test_file = _project(tmp_path, suite)
    harvested = whitebox.harvest_live_io_examples(project, [test_file], {"double"})
    log = test_file.with_name("life_cycle.log")
    steps = log.read_text(encoding="utf-8").split("\n")[:-1] if log.exists() else []
    examples = list(harvested.get("double", ([], []))[0])
    return examples, steps


def test_every_set_up_is_followed_by_its_tear_down_and_its_cleanups(tmp_path):
    examples, steps = _harvest(tmp_path, _ORDINARY_SUITE)

    # Two test methods, each a whole life cycle, in unittest's order.
    assert steps == ["setUp", "tearDown", "cleanup", "setUp", "tearDown", "cleanup"]
    # Ending the tests properly must not cost the harvest what it came for.
    assert sorted(examples) == [((2,), 4), ((3,), 6)]


@pytest.mark.skipif(not hasattr(signal, "setitimer"), reason="needs POSIX interval timers")
def test_a_time_limit_a_project_test_arms_is_not_left_armed_in_the_solver(tmp_path):
    if threading.current_thread() is not threading.main_thread():
        pytest.skip("interval timers belong to the main thread")
    if signal.getitimer(signal.ITIMER_REAL)[0] > 0:
        pytest.skip("this runner is already using the real-time alarm")
    try:
        examples, _ = _harvest(tmp_path, _SUITE_WITH_A_TIME_LIMIT)
        seconds_left = signal.getitimer(signal.ITIMER_REAL)[0]
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)

    assert seconds_left == 0.0, f"a project test's alarm is still armed in this process ({seconds_left:.0f} s left)"
    assert examples == [((2,), 4)]


def test_a_set_up_that_fails_gets_its_cleanups_and_no_tear_down(tmp_path):
    examples, steps = _harvest(tmp_path, _SUITE_WHOSE_SET_UP_FAILS)

    assert steps == ["setUp began", "cleanup"]
    # The test method never ran. What the harvest returns here it read from the test's text.
    assert examples == [((2,), 4)]


def test_a_tear_down_that_fails_stops_neither_the_cleanups_nor_the_next_test(tmp_path):
    examples, steps = _harvest(tmp_path, _SUITE_WHOSE_TEAR_DOWN_FAILS)

    assert steps == ["tearDown", "cleanup", "tearDown", "cleanup"]
    assert sorted(examples) == [((2,), 4), ((3,), 6)]
