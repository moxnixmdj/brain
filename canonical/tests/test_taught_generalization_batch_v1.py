"""Generalizing a demonstrated edit needs evidence at each newly tried site."""
import json
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
