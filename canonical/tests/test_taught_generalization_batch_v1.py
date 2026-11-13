"""Generalizing a demonstrated edit needs evidence at each newly tried site."""
import json
import os
import subprocess
import sys
from pathlib import Path

from canonical.swe_kernel.taught_actions import edit_by_example_v1 as learner


BEFORE = "def status(self):\n    return self.thread.isAlive()\n"
AFTER = BEFORE.replace("isAlive", "is_alive")


def make_lesson():
    Path("alive.lesson").write_bytes(learner.lesson_text([(BEFORE, AFTER)], ["example"]))


def test_a_covered_site_after_eight_uncovered_sites_is_tried(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    make_lesson()
    source = "\n".join(
        f"def f{i}(v{i}):\n    return v{i}.isAlive()\n" for i in range(9)
    )
    Path("pool.py").write_text(source)
    Path("check_pool.py").write_text(
        "import pool\n"
        "class Thread:\n"
        "    def isAlive(self): return True\n"
        "    def is_alive(self): return True\n"
        "def test_last():\n"
        "    assert pool.f8(Thread())\n"
    )

    assert learner.main(("repeat_tried", ("pool.py", "alive.lesson", "check_pool.py"))) == 0
    changed = Path("pool.py").read_text()
    assert changed == source.replace("v8.isAlive()", "v8.is_alive()")
    lesson = json.loads(Path("alive.lesson").read_text())
    assert len(lesson["examples"]) == 2
    assert len(lesson["examples"][1]["not settled"]) == 8


def test_a_later_bad_site_does_not_erase_earlier_verified_changes(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    make_lesson()
    source = "\n".join(
        f"def f{i}(v{i}):\n    return v{i}.isAlive()\n" for i in range(9)
    )
    Path("pool.py").write_text(source)
    Path("check_pool.py").write_text(
        "import pool\n"
        "class Thread:\n"
        "    def isAlive(self): return True\n"
        "    def is_alive(self): return True\n"
        "class Other:\n"
        "    def isAlive(self): return True\n"
        "def test_first():\n"
        "    for i in range(8): assert getattr(pool, 'f' + str(i))(Thread())\n"
        "def test_last():\n"
        "    assert pool.f8(Other())\n"
    )
    assert learner.main(("repeat_tried", ("pool.py", "alive.lesson", "check_pool.py"))) == 0
    edited = Path("pool.py").read_text()
    assert edited == source.replace(".isAlive()", ".is_alive()", 8)
    lesson = json.loads(Path("alive.lesson").read_text())
    assert "left line 26" in lesson["examples"][1]["shown by"]


def test_a_timeout_when_probing_a_site_is_not_evidence(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(learner, "CHECK_SECONDS", 1)
    monkeypatch.setattr(learner, "ALL_CHECKS_SECONDS", 15)
    make_lesson()
    source = "def running(thread):\n    return thread.isAlive()\n"
    Path("pool.py").write_text(source)
    Path("check_pool.py").write_text(
        "import pool\n"
        "class Thread:\n"
        "    def isAlive(self): return True\n"
        "    def is_alive(self): return True\n"
        "def test_running():\n"
        "    try:\n"
        "        assert pool.running(Thread())\n"
        "    except ValueError:\n"
        "        while True: pass\n"
    )
    prior = Path("alive.lesson").read_bytes()
    assert learner.main(("repeat_tried", ("pool.py", "alive.lesson", "check_pool.py"))) == 3
    assert Path("pool.py").read_text() == source
    assert Path("alive.lesson").read_bytes() == prior


def test_a_passing_batch_cannot_promote_a_failing_subset(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    make_lesson()
    source = "def first(a):\n    return a.isAlive()\n\ndef second(b):\n    return b.isAlive()\n"
    Path("pool.py").write_text(source)
    Path("check_pool.py").write_text(
        "import pool\n"
        "class Thread:\n"
        "    def isAlive(self): return 'old'\n"
        "    def is_alive(self): return 'new'\n"
        "def test_pair():\n"
        "    a = pool.first(Thread())\n"
        "    try:\n"
        "        b = pool.second(Thread())\n"
        "    except ValueError:\n"
        "        b = 'new'\n"
        "    assert a == b\n"
    )
    prior = Path("alive.lesson").read_bytes()
    assert learner.main(("repeat_tried", ("pool.py", "alive.lesson", "check_pool.py"))) == 3
    assert Path("pool.py").read_text() == source
    assert Path("alive.lesson").read_bytes() == prior


def test_batching_also_works_for_a_different_demonstrated_edit(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    before = "def empty(first):\n    return first == None\n"
    after = before.replace("== None", "is None")
    Path("none.lesson").write_bytes(learner.lesson_text([(before, after)], ["example"]))
    source = "\n".join(f"def f{i}(v{i}):\n    return v{i} == None\n" for i in range(10))
    Path("values.py").write_text(source)
    Path("check_values.py").write_text(
        "import values\n"
        "def test_last():\n"
        "    assert values.f9(None)\n"
        "    assert not values.f9(1)\n"
    )
    assert learner.main(("repeat_tried", ("values.py", "none.lesson", "check_values.py"))) == 0
    assert Path("values.py").read_text() == source.replace("v9 == None", "v9 is None")
    lesson = json.loads(Path("none.lesson").read_text())
    assert len(lesson["examples"][1]["not settled"]) == 9


def test_a_later_settled_site_can_generalize_after_process_restart(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    make_lesson()
    # The original lesson names only self.thread; the later file uses a new receiver.
    other = "def available(worker):\n    return worker.isAlive()\n"
    Path("other.py").write_text(other)
    assert learner.main(("repeat", ("other.py", "alive.lesson"))) == 3
    assert Path("other.py").read_text() == other

    source = "\n".join(f"def f{i}(v{i}):\n    return v{i}.isAlive()\n" for i in range(9))
    Path("pool.py").write_text(source)
    Path("check_pool.py").write_text(
        "import pool\n"
        "class Thread:\n"
        "    def isAlive(self): return True\n"
        "    def is_alive(self): return True\n"
        "def test_last():\n"
        "    assert pool.f8(Thread())\n"
    )
    assert learner.main(("repeat_tried", ("pool.py", "alive.lesson", "check_pool.py"))) == 0

    # A fresh interpreter re-reads the persisted lesson, not the training process's memory.
    root = Path(__file__).resolve().parents[2]
    env = dict(os.environ, PYTHONPATH=str(root), PYTHONDONTWRITEBYTECODE="1")
    completed = subprocess.run(
        [sys.executable, "-c", "from canonical.swe_kernel.taught_actions import edit_by_example_v1 as e; "
         "raise SystemExit(e.main(('repeat', ('other.py', 'alive.lesson'))))"],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert Path("other.py").read_text() == other.replace("isAlive", "is_alive")


def test_check_import_crash_cannot_prove_a_test_observed_the_mutation(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    make_lesson()
    source = "def active(worker):\n    return worker.isAlive()\n"
    Path("pool.py").write_text(source)
    Path("check_pool.py").write_text(
        "import pool\n"
        "class Thread:\n"
        "    def isAlive(self): return True\n"
        "    def is_alive(self): return True\n"
        "pool.active(Thread())  # executed during import, before tests can be discovered\n"
        "def test_unrelated():\n"
        "    assert len('ok') == 2\n"
    )
    prior = Path("alive.lesson").read_bytes()
    assert learner.main(("repeat_tried", ("pool.py", "alive.lesson", "check_pool.py"))) == 3
    assert Path("pool.py").read_text() == source
    assert Path("alive.lesson").read_bytes() == prior


def test_a_check_that_cannot_import_is_not_a_valid_baseline(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    make_lesson()
    source = "def status(self):\n    return self.thread.isAlive()\n"
    Path("pool.py").write_text(source)
    Path("check_pool.py").write_text("raise RuntimeError('could not load tests')\n")
    prior = Path("alive.lesson").read_bytes()
    assert learner.main(("repeat_tried", ("pool.py", "alive.lesson", "check_pool.py"))) == 3
    assert Path("pool.py").read_text() == source
    assert Path("alive.lesson").read_bytes() == prior


def test_no_tests_after_edit_refuses_and_restores_the_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    make_lesson()
    source = BEFORE
    Path("pool.py").write_text(source)
    Path("check_pool.py").write_text(
        "import pool\n"
        "class Thread:\n"
        "    def isAlive(self): return True\n"
        "    def is_alive(self): return False\n"
        "class Holder:\n"
        "    thread = Thread()\n"
        "if pool.status(Holder()):\n"
        "    def test_old_behavior():\n"
        "        assert pool.status(Holder())\n"
    )
    prior = Path("alive.lesson").read_bytes()
    assert learner.main(("repeat_tried", ("pool.py", "alive.lesson", "check_pool.py"))) == 3
    assert Path("pool.py").read_text() == source
    assert Path("alive.lesson").read_bytes() == prior


def test_a_disappearing_test_cannot_make_an_edit_pass(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    make_lesson()
    Path("pool.py").write_text(BEFORE)
    Path("check_pool.py").write_text(
        "import pool\n"
        "class Thread:\n"
        "    def isAlive(self): return True\n"
        "    def is_alive(self): return False\n"
        "class Holder:\n"
        "    thread = Thread()\n"
        "def test_unrelated():\n"
        "    assert len('ok') == 2\n"
        "if pool.status(Holder()):\n"
        "    def test_old_behavior():\n"
        "        assert pool.status(Holder())\n"
    )
    prior = Path("alive.lesson").read_bytes()
    assert learner.main(("repeat_tried", ("pool.py", "alive.lesson", "check_pool.py"))) == 3
    assert Path("pool.py").read_text() == BEFORE
    assert Path("alive.lesson").read_bytes() == prior


def test_skipping_a_previously_running_test_refuses_and_restores(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    make_lesson()
    Path("pool.py").write_text(BEFORE)
    Path("check_pool.py").write_text(
        "import pool, unittest\n"
        "class Thread:\n"
        "    def isAlive(self): return True\n"
        "    def is_alive(self): return False\n"
        "class Holder:\n"
        "    thread = Thread()\n"
        "class Tests(unittest.TestCase):\n"
        "    @unittest.skipUnless(pool.status(Holder()), 'disabled')\n"
        "    def test_old_behavior(self):\n"
        "        self.assertTrue(pool.status(Holder()))\n"
        "    def test_unrelated(self):\n"
        "        self.assertEqual(len('ok'), 2)\n"
    )
    prior = Path("alive.lesson").read_bytes()
    assert learner.main(("repeat_tried", ("pool.py", "alive.lesson", "check_pool.py"))) == 3
    assert Path("pool.py").read_text() == BEFORE
    assert Path("alive.lesson").read_bytes() == prior


def test_all_skipped_tests_are_not_a_baseline(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    make_lesson()
    Path("pool.py").write_text(BEFORE)
    Path("check_pool.py").write_text(
        "import unittest\n"
        "class Tests(unittest.TestCase):\n"
        "    @unittest.skip('not available')\n"
        "    def test_skipped(self):\n"
        "        self.assertEqual(len('ok'), 2)\n"
    )
    assert learner.main(("repeat_tried", ("pool.py", "alive.lesson", "check_pool.py"))) == 3
    assert Path("pool.py").read_text() == BEFORE
