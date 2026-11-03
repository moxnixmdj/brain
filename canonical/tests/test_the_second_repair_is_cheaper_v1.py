"""The learning chain is on by default, and the second repair is measurably cheaper.

What this pins
--------------
`python.software.repair.apply.verified.v1` holds the whole learning chain and shipped with
`retained_learning` defaulting to `{"enabled": False}`. No production caller ever set it, so
the chain was dormant: every repair searched cold, forever, while a benchmark tool proved the
same chain removes search entirely.

Measured 2026-11-02 through this exact capability, one lesson, two arms:

    first repair on an unseen project   1+ search invocations, teaches
    second repair, memory present       0 search invocations, recalled

The invariant asserted here is the one the improvement actually claims -- a COST saving on the
second encounter -- and not a solve-rate change, because there is no solve-rate change to
claim: the cold arm solved the same cases. A test that asserted a solve-rate gain would be
asserting something measurement denies.

Why a derived scope is safe, and what these tests are allowed to assume
---------------------------------------------------------------------
The scope is a cost filter, not a safety filter. `RetainedRepairSession` wires the verifier to
`ProjectTestOracle`, which runs the project's real suite on every recall. So a wrong or stale
memory costs oracle calls and a fallback to search; it cannot propose a patch the suite would
accept wrongly. The negative controls below hold that from the other side: a project whose
correct answer differs from the stored lesson must still be repaired correctly, and the tests
must never be edited.

Every accepting row is paired with the nearest world in which it must fail.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime.bound_capabilities import python_repair_apply_verified_v1 as apply  # noqa: E402
from canonical.swe_kernel import retained_scope_derivation_v1 as scope  # noqa: E402


# --------------------------------------------------------------------------- fixtures
# Full modules, for rewriting a subject.py in place.
BROKEN = "def within(x, hi):\n    return x <= hi\n"
FIXED = "def within(x, hi):\n    return x < hi\n"
# Bare expressions, for building one.
BROKEN_BODY = "x <= hi"
FIXED_BODY = "x < hi"


def make_project(root: Path, *, body: str = BROKEN_BODY,
                 test_body: str | None = None) -> Path:
    """A project the store has never seen. One source module, one test module."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "subject.py").write_text("def within(x, hi):\n    return " + body + "\n")
    (root / "test_subject.py").write_text(
        test_body
        or (
            "import unittest\n"
            "from subject import within\n"
            "class Checks(unittest.TestCase):\n"
            " def test_boundary(self):\n"
            "  for x, hi in [(0,0),(3,3),(4,3),(2,3),(-1,0)]:\n"
            "   self.assertEqual(within(x, hi), x < hi)\n"
        )
    )
    return root


def repair(root: Path, index: int, **extra) -> dict:
    args = {
        "source_root": ".",
        "test_paths": ["test_subject.py"],
        "output_path": f"reports/run{index}.json",
        "timeout_s": 60,
    }
    args.update(extra)
    return apply.run(args, root)


def suite_green(root: Path) -> bool:
    import subprocess
    p = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", ".", "-p",
                        "test_*.py", "-q"], cwd=str(root), capture_output=True, text=True)
    return p.returncode == 0


# --------------------------------------------------------------------------- the claim
def test_the_chain_is_derived_on_without_any_caller_configuration(tmp_path):
    """Baseline: the default was enabled=False, so this derivation did not exist at all."""
    project = make_project(tmp_path / "proj")
    result = repair(project, 0)
    derivation = result["retained_learning_derivation"]
    assert derivation["source"] == scope.DERIVED
    assert derivation["declined_reason"] is None
    assert derivation["scope_id"] and derivation["scope_id"].startswith("python/tests/")
    assert derivation["allow_operator_generalization"] is True
    assert result["retained_learning"]["enabled"] is True


def test_the_second_repair_of_the_same_kind_spends_no_search(tmp_path):
    """The whole point. Fails on the previous code, where both runs searched."""
    project = make_project(tmp_path / "proj")

    first = repair(project, 0)
    assert first["pass"] is True
    assert first["applied"] is True
    assert first["repair_search_invocations"] >= 1, "the first encounter must have to search"
    assert suite_green(project)

    # the same breakage returns; memory is now present
    (project / "subject.py").write_text(BROKEN)
    second = repair(project, 1)

    assert second["pass"] is True
    assert second["applied"] is True
    assert second["retained_learning"]["hit"] is True, "the lesson must be recalled"
    assert second["repair_search_invocations"] == 0, (
        "a recalled plan must not search; got %d invocations"
        % second["repair_search_invocations"])
    assert suite_green(project)


def test_the_recalled_patch_is_the_correct_patch_not_merely_a_passing_one(tmp_path):
    """Nearest world: a recall that applies *something* and gets lucky on the visible suite."""
    project = make_project(tmp_path / "proj")
    repair(project, 0)
    (project / "subject.py").write_text(BROKEN)
    second = repair(project, 1)

    applied_body = (project / "subject.py").read_text()
    assert "<=" not in applied_body and "<" in applied_body
    assert second["retained_learning"]["verification"]["kind"] == "TEST_SUITE"
    assert second["retained_learning"]["whole_task_correctness_proved"] is False


def test_tests_are_never_edited_to_make_a_recall_apply(tmp_path):
    project = make_project(tmp_path / "proj")
    before = (project / "test_subject.py").read_bytes()
    repair(project, 0)
    (project / "subject.py").write_text(BROKEN)
    repair(project, 1)
    assert (project / "test_subject.py").read_bytes() == before


# --------------------------------------------------------------------------- the refusals
def test_a_different_correct_answer_is_still_repaired_correctly(tmp_path):
    """Negative control: the stored lesson is the WRONG answer for this project.

    A recall fitted to the first lesson must not be applied here. The oracle rejects it and
    the solver falls back to search, which is the cost the design accepts -- so this row is
    allowed to search, and is not allowed to be wrong.
    """
    taught = make_project(tmp_path / "taught")
    repair(taught, 0)                       # learns "< hi"

    other = make_project(
        tmp_path / "other",
        body=BROKEN_BODY,
        test_body=(
            "import unittest\n"
            "from subject import within\n"
            "class Checks(unittest.TestCase):\n"
            " def test_boundary(self):\n"
            "  for x, hi in [(0,0),(3,3),(4,3)]:\n"
            "   self.assertEqual(within(x, hi), x <= hi)\n"
        ),
    )
    result = repair(other, 0)
    assert result["pass"] is True
    assert suite_green(other)


def test_an_explicit_off_is_honoured_and_never_overridden(tmp_path):
    """A caller that states a decision keeps it; derivation only supplies what is unstated."""
    project = make_project(tmp_path / "proj")
    result = repair(project, 0, retained_learning={"enabled": False})
    assert result["retained_learning"] == {"enabled": False}
    assert result["retained_learning_derivation"]["source"] == "CALLER_STATED"


def test_two_source_files_decline_with_a_named_reason(tmp_path):
    """With more than one module, 'which file' is not a fact the tree states."""
    project = make_project(tmp_path / "proj")
    (project / "helper.py").write_text("def unrelated():\n    return 1\n")
    result = repair(project, 0)
    derivation = result["retained_learning_derivation"]
    assert derivation["source"] is None
    assert derivation["declined_reason"] == "DECLINED:MULTIPLE_SOURCE_FILES_TARGET_AMBIGUOUS"
    assert result["retained_learning"] == {"enabled": False}
    assert result["pass"] is True, "declining to learn must not prevent the repair"


def test_no_test_corpus_declines_rather_than_scoping_against_nothing(tmp_path):
    config, report = scope.derive_retained_config(
        repo=tmp_path, source_root=tmp_path, test_paths=[], explicit=None)
    assert config is None
    assert report["declined_reason"] == "DECLINED:NO_TEST_CORPUS_TO_SCOPE_AGAINST"


def test_the_scope_key_is_stable_and_corpus_specific(tmp_path):
    a = tmp_path / "a"
    b = tmp_path / "b"
    for d in (a, b):
        d.mkdir()
        (d / "test_one.py").write_text("")
        (d / "test_two.py").write_text("")
    same = scope.derive_scope_id(a, [a / "test_one.py", a / "test_two.py"])
    reordered = scope.derive_scope_id(a, [a / "test_two.py", a / "test_one.py"])
    narrowed = scope.derive_scope_id(a, [a / "test_one.py"])
    assert same == reordered, "order must not change the key"
    assert same != narrowed, "a different corpus must not collide"
    other = scope.derive_scope_id(b, [b / "test_one.py", b / "test_two.py"])
    assert same == other, "the same corpus on a different checkout must agree"


def test_the_memory_location_is_reported_not_hidden(tmp_path):
    project = make_project(tmp_path / "proj")
    result = repair(project, 0)
    assert result["retained_learning_derivation"]["db_path"].endswith(".sqlite")
    assert (project / ".brain" / "retained_repair_skills.sqlite").is_file()
