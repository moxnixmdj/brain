"""A use nobody showed is settled by the project's own check, not by a guess and not by a flat refusal.

One example cannot say which parts of the changed code matter: ``self.thread.isAlive()`` shown once says
nothing about ``t.isAlive()``.  Until now the action refused such a place or left it alone.  The action
``repeat_tried`` tries it against a check -- a Python file of the project that is run -- and keeps it only
when two runs agree: no test that passed before fails with the place changed, and a test that passes with
it fails when that place is made to fail.  A check that passes either way settles nothing, and the place
stays as it was.

What a check settles is written back into the lesson: a kept place widens it, a place a test spoke against
counts as left alone, and the unsettled places are named so they count neither way at the next use.
"""
from __future__ import annotations

import json
import pathlib

import pytest

from canonical.swe_kernel.taught_actions import edit_by_example_v1 as by_example

WATCH_WAS = (
    "import threading\n"
    "\n"
    "\n"
    "class Watch:\n"
    "    def __init__(self):\n"
    "        self.thread = threading.Thread(target=print)\n"
    "\n"
    "    def busy(self):\n"
    "        return self.thread.isAlive()\n"
)
WATCH_IS = WATCH_WAS.replace("isAlive", "is_alive")

POOL = (
    "import threading\n"
    "\n"
    "\n"
    "class Probe:\n"
    "    def isAlive(self):\n"
    "        return True\n"
    "\n"
    "\n"
    "def running(threads):\n"
    "    return [t for t in threads if t.isAlive()]\n"
    "\n"
    "\n"
    "def probe_ok(probe):\n"
    "    return probe.isAlive()\n"
    "\n"
    "\n"
    "def never_run(job):\n"
    "    return job.isAlive()\n"
)

CHECK = (
    "import threading\n"
    "import unittest\n"
    "\n"
    "import pool\n"
    "\n"
    "\n"
    "class PoolTest(unittest.TestCase):\n"
    "    def test_running(self):\n"
    "        done = threading.Thread(target=print)\n"
    "        done.start()\n"
    "        done.join()\n"
    "        self.assertEqual(pool.running([done]), [])\n"
    "\n"
    "    def test_probe(self):\n"
    "        self.assertTrue(pool.probe_ok(pool.Probe()))\n"
)


def _world(tmp_path, monkeypatch, **files):
    monkeypatch.chdir(tmp_path)
    for name, text in files.items():
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)


def _lesson(path: str, *examples) -> None:
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(path).write_bytes(by_example.lesson_text(list(examples), ["was -> is"] * len(examples)))


def _tried(target="pool.py", lesson="alive.lesson", check="check_pool.py"):
    return by_example.main(("repeat_tried", (target, lesson, check)))


# ----------------------------------------------------------------------------- what the check settles


def test_a_tested_place_is_kept_a_broken_one_left_and_an_unrun_one_not_settled(tmp_path, monkeypatch, capsys):
    _world(tmp_path, monkeypatch, **{"pool.py": POOL, "check_pool.py": CHECK})
    _lesson("alive.lesson", (WATCH_WAS, WATCH_IS))
    assert _tried() == 0
    assert "tried the rest with check_pool.py" in capsys.readouterr().out
    edited = pathlib.Path("pool.py").read_text()
    assert "if t.is_alive()" in edited                       # test_running settles it: fails when it fails
    assert "probe.isAlive()" in edited                       # test_probe fails with it changed: left alone
    assert "job.isAlive()" in edited                         # never run: the check says nothing about it
    assert "def isAlive(self)" in edited                     # a definition is not a use; never touched
    held = json.loads(pathlib.Path("alive.lesson").read_text())
    # The left-alone place keeps the two rules apart: `?1.isAlive` would reach `probe.isAlive()`, which a test defends.
    assert held["teaches"] == [
        {"change": "self.thread.isAlive -> self.thread.is_alive", "shown": ["called with 0 arguments"]},
        {"change": "t.isAlive -> t.is_alive", "shown": ["called with 0 arguments"]}]
    told = held["examples"][1]["shown by"]
    assert "kept line 10" in told and "left line 14" in told and "not settled, line 18" in told
    assert held["examples"][1]["not settled"] == [[18, 11, 18, 22]]


def test_the_next_file_needs_no_try_for_what_the_check_settled(tmp_path, monkeypatch, capsys):
    plain = "def running(threads):\n    return [t for t in threads if t.isAlive()]\n"
    check = CHECK.replace("    def test_probe(self):\n        self.assertTrue(pool.probe_ok(pool.Probe()))\n", "")
    _world(tmp_path, monkeypatch, **{"pool.py": plain, "check_pool.py": check,
                                     "other.py": "def alive(job):\n    return job.isAlive()\n"})
    _lesson("alive.lesson", (WATCH_WAS, WATCH_IS))
    assert by_example.main(("repeat", ("other.py", "alive.lesson"))) == 3      # one example: too narrow
    assert _tried() == 0
    capsys.readouterr()
    held = json.loads(pathlib.Path("alive.lesson").read_text())
    assert held["teaches"] == [{"change": "?1.isAlive -> ?1.is_alive", "shown": ["called with 0 arguments"]}]
    assert by_example.main(("repeat", ("other.py", "alive.lesson"))) == 0      # the kept try widened the lesson
    assert pathlib.Path("other.py").read_text() == "def alive(job):\n    return job.is_alive()\n"


def test_a_place_the_check_spoke_against_kills_the_wider_reading(tmp_path, monkeypatch, capsys):
    _world(tmp_path, monkeypatch, **{"pool.py": POOL, "check_pool.py": CHECK,
                                     "other.py": "def alive(job):\n    return job.isAlive()\n"})
    _lesson("alive.lesson", (WATCH_WAS, WATCH_IS))
    assert _tried() == 0
    capsys.readouterr()
    # `probe.isAlive()` was defended by a test, so `?1.isAlive` is contradicted; `job.isAlive()` is not even tried.
    assert _tried("other.py", "alive.lesson", "check_pool.py") == 3
    assert "nothing in the file has the form" in capsys.readouterr().out
    assert pathlib.Path("other.py").read_text() == "def alive(job):\n    return job.isAlive()\n"


def test_a_check_that_fails_before_and_after_changes_nothing(tmp_path, monkeypatch, capsys):
    broken = CHECK.replace("self.assertEqual(pool.running([done]), [])", "self.assertEqual(pool.missing(), 1)")
    _world(tmp_path, monkeypatch, **{"pool.py": POOL, "check_pool.py": broken})
    _lesson("alive.lesson", (WATCH_WAS, WATCH_IS))
    assert _tried() == 3
    assert "nothing was changed" in capsys.readouterr().out
    assert pathlib.Path("pool.py").read_text() == POOL


def test_a_check_without_anything_to_run_is_refused(tmp_path, monkeypatch, capsys):
    _world(tmp_path, monkeypatch, **{"pool.py": POOL, "check_pool.py": "WORDS = 'no test and no script'\n"})
    _lesson("alive.lesson", (WATCH_WAS, WATCH_IS))
    assert _tried() == 3
    assert "holds nothing that can be run here" in capsys.readouterr().out
    assert pathlib.Path("pool.py").read_text() == POOL


def test_a_check_that_does_not_end_is_refused(tmp_path, monkeypatch, capsys):
    _world(tmp_path, monkeypatch, **{"pool.py": POOL,
                                     "check_pool.py": "if __name__ == '__main__':\n    while True:\n        pass\n"})
    _lesson("alive.lesson", (WATCH_WAS, WATCH_IS))
    monkeypatch.setattr(by_example, "CHECK_SECONDS", 2)
    assert _tried() == 3
    assert "does not come to an end" in capsys.readouterr().out
    assert pathlib.Path("pool.py").read_text() == POOL


def test_a_script_counts_as_one_test(tmp_path, monkeypatch, capsys):
    script = ("import pool\n"
              "import threading\n"
              "\n"
              "if __name__ == '__main__':\n"
              "    done = threading.Thread(target=print)\n"
              "    done.start()\n"
              "    done.join()\n"
              "    assert pool.running([done]) == []\n")
    _world(tmp_path, monkeypatch, **{"pool.py": POOL, "check_pool.py": script})
    _lesson("alive.lesson", (WATCH_WAS, WATCH_IS))
    assert _tried() == 0
    capsys.readouterr()
    assert "if t.is_alive()" in pathlib.Path("pool.py").read_text()
    assert "probe.isAlive()" in pathlib.Path("pool.py").read_text()            # the script never runs probe_ok


def test_a_check_that_swallows_the_failure_settles_nothing(tmp_path, monkeypatch, capsys):
    # The check reaches the place, but inside a try/except that swallows whatever the place raises.
    # The made-to-fail run then passes too, so the check says nothing, and the place stays as it was.
    forgiving = (
        "import unittest\n"
        "\n"
        "import pool\n"
        "\n"
        "\n"
        "class SoftTest(unittest.TestCase):\n"
        "    def test_probe(self):\n"
        "        try:\n"
        "            pool.probe_ok(pool.Probe())\n"
        "        except Exception:\n"
        "            pass\n"
    )
    only_probe = ("class Probe:\n"
                  "    def isAlive(self):\n"
                  "        return True\n"
                  "\n"
                  "\n"
                  "def probe_ok(probe):\n"
                  "    return probe.isAlive()\n")
    _world(tmp_path, monkeypatch, **{"pool.py": only_probe, "check_pool.py": forgiving})
    _lesson("alive.lesson", (WATCH_WAS, WATCH_IS))
    assert _tried() == 3
    assert "says nothing about that code" in capsys.readouterr().out
    assert pathlib.Path("pool.py").read_text() == only_probe


def test_what_the_lesson_itself_shows_is_not_up_for_debate(tmp_path, monkeypatch, capsys):
    # `self.thread.isAlive()` is what the lesson shows; a check that fails only after that change refuses the edit.
    watcher = WATCH_WAS
    angry = ("import unittest\n"
             "\n"
             "import pool\n"
             "\n"
             "\n"
             "class SourceTest(unittest.TestCase):\n"
             "    def test_text(self):\n"
             "        self.assertIn('isAlive', open('pool.py').read())\n")
    _world(tmp_path, monkeypatch, **{"pool.py": watcher, "check_pool.py": angry})
    _lesson("alive.lesson", (WATCH_WAS, WATCH_IS))
    assert _tried() == 3
    # The check reads the file from disk, so only the last write catches it: the file is put back as it was.
    assert "fails on the edited file" in capsys.readouterr().out
    assert pathlib.Path("pool.py").read_text() == watcher


# ----------------------------------------------------------------------------- the wider reading


def test_the_wider_reading_blanks_what_the_change_copied_and_keeps_what_it_is_about():
    helpers = "def get(x):\n    return x\n\n\ndef fetch(x):\n    return x + 1\n\n\n"
    rules, readings = by_example.learn_all([(
        helpers + "def quote(price, rate):\n    return round(get(price) + rate, 2)\n",
        helpers + "def quote(price, rate):\n    return round(fetch(price) + rate, 2)\n")], wide=True)
    assert [str(rule) for rule in rules] == ["get(price) -> fetch(price)"]
    assert [str(rule) for rule in readings] == ["get(?1) -> fetch(?1)"]


def test_an_imported_module_the_change_copied_does_not_widen():
    # The smallest changed piece of `yaml.load(stream)` is `yaml.load` itself, and `yaml` is an import:
    # it is what the change is about, never a blank.
    rules, readings = by_example.learn_all([(
        "import yaml\n\n\ndef read(stream):\n    return yaml.load(stream)\n",
        "import yaml\n\n\ndef read(stream):\n    return yaml.safe_load(stream)\n")], wide=True)
    assert [str(rule) for rule in rules] == ["yaml.load -> yaml.safe_load"]
    assert readings == []


def test_the_wider_reading_respects_what_other_examples_left_alone():
    # The example also holds `other.isAlive()` unchanged, so no wider reading may reach it.
    was = ("def busy(worker, other):\n"
           "    keep = other.isAlive()\n"
           "    return worker.isAlive() and keep\n")
    now = was.replace("worker.isAlive()", "worker.is_alive()")
    rules, readings = by_example.learn_all([(was, now)], wide=True)
    assert [str(rule) for rule in rules] == ["worker.isAlive -> worker.is_alive"]
    assert readings == []


def test_a_change_that_copied_nothing_has_no_wider_reading():
    rules, readings = by_example.learn_all([(
        "import time\n\n\ndef now():\n    return time.clock()\n",
        "import time\n\n\ndef now():\n    return time.perf_counter()\n")], wide=True)
    assert [str(rule) for rule in rules] == ["time.clock -> time.perf_counter"]
    assert readings == []


# ----------------------------------------------------------------------------- unsettled places in a lesson


def test_an_unsettled_place_counts_neither_as_changed_nor_as_left_alone():
    first = ("def busy(worker):\n    return worker.isAlive()\n",
             "def busy(worker):\n    return worker.is_alive()\n")
    second_was = "def all_busy(crew, boss):\n    return crew.isAlive() and boss.isAlive()\n"
    second_is = "def all_busy(crew, boss):\n    return crew.is_alive() and boss.isAlive()\n"
    # `boss.isAlive()` left alone keeps the two changed places from becoming one `?1.isAlive` rule ...
    narrow = by_example.learn_all([first, (second_was, second_is)])
    assert [str(rule) for rule in narrow] == ["worker.isAlive -> worker.is_alive", "crew.isAlive -> crew.is_alive"]
    # ... but a place a check could not settle is no evidence either way, and the rule becomes one.
    rules = by_example.learn_all([first, (second_was, second_is, ((2, 30, 2, 42),))])
    assert [str(rule) for rule in rules] == ["?1.isAlive -> ?1.is_alive"]


def test_a_lesson_whose_unsettled_places_name_no_code_is_refused(tmp_path, monkeypatch):
    _world(tmp_path, monkeypatch, **{"target.py": "def busy(t):\n    return t.isAlive()\n"})
    _lesson("alive.lesson", (WATCH_WAS, WATCH_IS))
    held = json.loads(pathlib.Path("alive.lesson").read_text())
    held["examples"][0]["not settled"] = [[99, 0, 99, 4]]
    pathlib.Path("alive.lesson").write_text(json.dumps(held))
    with pytest.raises(by_example.Refused, match="no piece of code"):
        by_example.lesson_examples("alive.lesson")


def test_the_check_must_be_a_python_file_inside_the_project(tmp_path, monkeypatch, capsys):
    _world(tmp_path, monkeypatch, **{"pool.py": POOL})
    _lesson("alive.lesson", (WATCH_WAS, WATCH_IS))
    assert _tried(check="missing.py") == 3
    assert "must be a Python file that exists" in capsys.readouterr().out
    assert _tried(check="../outside.py") == 3
