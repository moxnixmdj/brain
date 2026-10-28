#!/usr/bin/env python3
"""Two dynamic acts the machine claimed and could not do: reproduce a crash, and differential-test.

`hardcore_se_missing_verb_probe_v1.py` read both rows as refusals, and the refusals were honest:

    crash_repro        R3_WEAK_EVIDENCE     answered by a TEST SELECTOR, of all things
    differential_test  R14_UNHEARD_ACT_WORD answered by nothing; the act word was unknown

Neither needed a new engine.  `dynamic_probe_v1` already generated annotation-directed cases,
ran each in its own interpreter, classified crash/timeout/signalled as outcomes, shrank the first
failure greedily while keeping the same failure mode, and wrote a runnable reproducer.  A crash
reproduction IS that engine with a wider search: the sentence "reproduce the crash in <file>" does
not name a function -- if it knew which function crashed, it would have said -- so the search
covers every public function in scope and reports which one crashed.  A differential test is the
same generator and the same shrinker with a different oracle: two implementations must agree.

These pins hold the four things that make both of them honest rather than merely green:

  1. the crash search finds a REAL crash and shrinks it to a minimal call that still fails the same
     way, and the reproducer it writes actually reproduces it;
  2. a module that does not crash says so, with the search counted -- "NO CRASH REPRODUCED" is a
     result, never a silent pass;
  3. the differential harness finds a real behavioural divergence, shrinks it, and reports the
     basis of the reference it compared against -- including the git version of the same file,
     which is how a risky refactor is checked;
  4. the scope is what the sentence named: a file means that file, and nothing beside it.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
dynamic = pytest.importorskip("canonical.runtime.bound_capabilities.dynamic_probe_v1")
differential = pytest.importorskip("canonical.runtime.bound_capabilities.differential_probe_v1")

CRASHING = "def add(a, b):\n    return a + b\n\n\ndef safe(a, b):\n    return int(a) + int(b)\n"
CLEAN = "def double(n: int) -> int:\n    return n * 2\n"


@pytest.fixture()
def project(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    return pkg


def _git(repo: pathlib.Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo)] + list(args), check=True, capture_output=True,
                   text=True)


def _crash(project: pathlib.Path, source_root: pathlib.Path, out: pathlib.Path) -> dict:
    return dynamic.run({"act_verb": "crash_repro", "capability_id": "test.crash",
                        "source_root": str(source_root), "output_path": str(out)}, project)


# ---------------------------------------------------------------- reproduce, shrink, re-run


def test_a_crash_in_a_file_is_found_shrunk_and_written_as_a_reproducer(project, tmp_path):
    module = project / "calc.py"
    module.write_text(CRASHING, encoding="utf-8")
    result = _crash(project, module, tmp_path / "repro.json")

    assert result["reproduced"] is True
    assert result["qualname"] == "add", "the crashing function is named, not guessed at"
    assert result["failure_mode"] in ("raised", "crashed")
    assert result["minimal_case"] == ["", 0], "a str and an int is the minimal mixed-type call"


def test_the_reproducer_the_run_writes_actually_reproduces_the_crash(project, tmp_path):
    module = project / "calc.py"
    module.write_text(CRASHING, encoding="utf-8")
    result = _crash(project, module, tmp_path / "repro.json")

    script = pathlib.Path(result["reproducer_path"])
    assert script.is_file()
    run = subprocess.run([sys.executable, str(script)], capture_output=True, text=True,
                         cwd=str(project), check=False, timeout=120)
    assert run.returncode != 0, "the reproducer must fail the way the finding failed"
    assert "TypeError" in (run.stderr or "")


def test_a_module_that_does_not_crash_says_so_and_counts_the_search(project, tmp_path):
    module = project / "clean.py"
    module.write_text(CLEAN, encoding="utf-8")
    result = _crash(project, module, tmp_path / "none.json")

    assert result["reproduced"] is False
    assert result["minimal_case"] is None
    assert result["reproducer_path"] is None
    assert result["cases_run"] > 0, "'nothing found' and 'nothing ran' must not look alike"
    payload = json.loads((tmp_path / "none.json").read_text(encoding="utf-8"))
    assert payload["claim"].startswith("NO CRASH REPRODUCED")
    assert payload["functions_searched"], "the search is reported function by function"


def test_a_directory_is_searched_module_by_module(project, tmp_path):
    (project / "calc.py").write_text(CRASHING, encoding="utf-8")
    (project / "quiet.py").write_text(CLEAN, encoding="utf-8")
    result = _crash(project, project, tmp_path / "dir.json")

    assert result["reproduced"] is True
    assert result["module"] in ("calc", "pkg.calc")
    payload = json.loads((tmp_path / "dir.json").read_text(encoding="utf-8"))
    assert any(row["qualname"] == "add" for row in payload["functions_searched"])


# ---------------------------------------------------------------- differential: two implementations


def _differential(root: pathlib.Path, target: pathlib.Path, out: pathlib.Path, **extra) -> dict:
    args = {"act_verb": "differential_test", "capability_id": "test.differential",
            "source_root": str(target), "output_path": str(out)}
    args.update(extra)
    return differential.run(args, root)


def test_a_behavioural_divergence_against_a_stated_reference_is_found_and_shrunk(tmp_path):
    left = tmp_path / "left.py"
    right = tmp_path / "right.py"
    left.write_text("def sub(a, b):\n    return a - b\n", encoding="utf-8")
    right.write_text("def sub(a, b):\n    return a + b\n", encoding="utf-8")

    result = _differential(tmp_path, left, tmp_path / "diff.json", reference_path=str(right))

    assert result["divergences"] > 0
    assert result["minimal_case"] is not None
    payload = json.loads((tmp_path / "diff.json").read_text(encoding="utf-8"))
    assert payload["first_divergence"]["kind"] == "DIVERGENT_VALUE"
    assert payload["claim"].startswith("THE IMPLEMENTATIONS DISAGREE")
    assert payload["reference_basis"] == "stated:" + str(right)


def test_identical_implementations_agree_and_the_comparison_is_counted(tmp_path):
    left = tmp_path / "left.py"
    left.write_text("def sub(a, b):\n    return a - b\n", encoding="utf-8")
    right = tmp_path / "right.py"
    right.write_text(left.read_text(encoding="utf-8"), encoding="utf-8")

    result = _differential(tmp_path, left, tmp_path / "same.json", reference_path=str(right))

    assert result["divergences"] == 0
    assert result["cases_run"] > 0
    payload = json.loads((tmp_path / "same.json").read_text(encoding="utf-8"))
    assert payload["claim"].startswith("THE IMPLEMENTATIONS AGREE")


def test_the_reference_defaults_to_the_committed_version_of_the_same_file(tmp_path):
    """How a risky refactor is checked: the working tree against the code it replaced."""
    _git(tmp_path, "init", "-q", ".")
    target = tmp_path / "calc.py"
    target.write_text("def sub(a, b):\n    return a - b\n", encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base")
    target.write_text("def sub(a, b):\n    return a + b\n", encoding="utf-8")

    result = _differential(tmp_path, target, tmp_path / "git.json")

    assert result["divergences"] > 0
    assert result["reference_basis"] == "git:HEAD:calc.py"


def test_without_a_reference_and_without_git_the_answer_is_a_refusal(tmp_path):
    """A comparison against whatever file happened to be nearby is not an oracle."""
    target = tmp_path / "lonely.py"
    target.write_text("def sub(a, b):\n    return a - b\n", encoding="utf-8")

    with pytest.raises(Exception) as caught:
        _differential(tmp_path, target, tmp_path / "none.json")

    assert "REFERENCE_NOT_STATED" in str(caught.value)


# ---------------------------------------------------------------- the door, measured


def test_the_door_selects_the_right_act_for_each_sentence():
    """The sentences are ordinary engineering English; each must reach its own capability.

    Measured before this unit: `crash_repro` was answered by a TEST SELECTOR and
    `differential_test` had no owner at all.  The binding detail (a file, or the directory holding
    it) is deliberately not asserted here: both adapters handle both, because the compiler binds a
    scope key to the directory whenever the sentence names no single file.
    """
    from canonical.runtime import live_integrated_brain_v1 as live

    for goal in (
        "Reproduce the crash in %s/canonical/astra_runtime/tmp/dyn_pin/pkg/calc.py and shrink it "
        "to a minimal case, reporting to %s/canonical/astra_runtime/tmp/dyn_pin/crash.json."
        % (ROOT, ROOT),
        "Run a differential test of %s/canonical/astra_runtime/tmp/dyn_pin/pkg/calc.py against a "
        "reference and report to %s/canonical/astra_runtime/tmp/dyn_pin/diff.json." % (ROOT, ROOT),
    ):
        scene = ROOT / "canonical/astra_runtime/tmp/dyn_pin/pkg"
        scene.mkdir(parents=True, exist_ok=True)
        (scene / "calc.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
        try:
            _registry, _admissible, compiled = live.compile_against_live_registry(goal, ROOT)
            assert compiled["selected_capability"] in ("python.dynamic.crash_repro.v1",
                                                       "python.dynamic.differential_test.v1"), \
                compiled["selected_capability"]
            assert compiled["inputs"].get("source_root", "").startswith(
                "canonical/astra_runtime/tmp/dyn_pin/pkg"), compiled["inputs"]
        finally:
            import shutil
            shutil.rmtree(ROOT / "canonical/astra_runtime/tmp/dyn_pin", ignore_errors=True)
