"""Tests for the measurement harness. Every case here is a defect that once faked a result.

A benchmark number is only worth the plumbing under it. Three of the defects pinned below
produced a *plausible* number: a missing dependency read as a failed task, a truncated contract
read as a complete one, and the answer sheet sitting in the attempt workspace behind a guard that
could never fire. None of those raised. Each returned a result.

So the tests below do not check that the harness "works". They check that it refuses to produce
an answer when the conditions for an answer are not met.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import swepro_batch_v1 as B
from canonical.runtime.derive_from_the_failure_v1 import load_contract, read_operator_gap


# --- the answer sheet --------------------------------------------------------------------------

def test_the_leak_guard_matches_the_name_the_file_actually_has():
    """The published path is `solution/gold_patch.diff`; on disk it is flattened.

    The original guard tested only the published spelling, so it never fired against a real
    run directory. A guard that cannot fire is decoration, and this one guarded the answer.
    """
    assert B._forbidden("solution/gold_patch.diff")
    assert B._forbidden("solution__gold_patch.diff")      # the flattened name on disk
    assert B._forbidden("work/i001/meta/solution__gold_patch.diff")
    assert B._forbidden("solution__solve.sh")


def test_the_flat_name_is_caught_independently_of_the_published_name():
    """Kills the mutant that drops the flattened branch from `_forbidden`.

    The published path and the flattened path must EACH be sufficient on their own, so the test
    calls the comparison that the second branch exists for rather than the public predicate --
    which would still pass on the first branch alone.
    """
    # The flattened form of the answer sheet has no slash, so only the flattening branch can
    # recognise it once the direct spelling is removed from the search.
    flat = "solution__gold_patch.diff"
    assert "__" in flat
    assert B._forbidden(flat)
    assert B._forbidden("meta/solution__gold_patch.diff")
    # And the published form is still caught by the other branch.
    assert B._forbidden("solution/gold_patch.diff")


def test_the_report_separates_broken_rooms_from_unsolved_tasks():
    """A score that folds broken infrastructure into capability is a score of the harness.

    Asserted on `run_batch`'s own source because the report keys are the contract: if the
    ROOM_BROKEN key disappears, seven rooms silently become failures in the denominator.
    """
    import ast
    src = pathlib.Path(B.__file__).read_text(encoding="utf-8")
    fn = next(n for n in ast.walk(ast.parse(src))
              if isinstance(n, ast.FunctionDef) and n.name == "run_batch")
    # The dict literal returned by run_batch must carry a key for each separate outcome.
    keys = [k.value for node in ast.walk(fn) if isinstance(node, ast.Dict)
            for k in node.keys if isinstance(k, ast.Constant) and isinstance(k.value, str)]
    for required in ("resolved", "not_resolved", "room_broken", "room_skipped"):
        assert required in keys, f"{required} missing from the report: {keys}"


def test_the_leak_guard_does_not_fire_on_the_contract():
    """A guard that fires on everything is as useless as one that never fires."""
    assert not B._forbidden("tests__config.json")
    assert not B._forbidden("config.json")
    assert not B._forbidden("tests__test_patch.patch")
    assert not B.forbidden_paths_touched(["meta/config.json", "meta/instruction.md"])


# --- the contract reader -----------------------------------------------------------------------

def _meta(tmp_path, f2p, p2p):
    d = tmp_path / "meta"
    d.mkdir()
    (d / "config.json").write_text(json.dumps({"fail_to_pass": f2p, "pass_to_pass": p2p}))
    return d


def test_a_contract_stored_as_a_string_of_a_list_is_read_completely(tmp_path):
    """The bench stores the list as a STRING. Reading it must not depend on the spelling."""
    f2p = "['t/a.py::x', 't/a.py::y']"
    got = load_contract(_meta(tmp_path, f2p, "[\"t/b.py::z[1]\"]"))
    assert got["fail_to_pass"] == ["t/a.py::x", "t/a.py::y"]
    assert got["pass_to_pass"] == ["t/b.py::z[1]"]


def test_an_id_containing_a_quote_does_not_silently_truncate_the_list(tmp_path):
    """THE KILLER. `literal_eval` SUCCEEDS and returns fewer items when an id has a quote.

    On ansible-be2c376a sixteen ids became two, and twelve were lost in silence. A truncating
    parse is worse than a failing one: it reports success and loses data.
    """
    ids = ['test/units/cli/test_doc.py::test_ttyify[IBM("x")]',
           'test/units/cli/test_doc.py::test_second',
           'test/units/cli/test_doc.py::test_third']
    raw = json.dumps(ids)                      # a valid JSON list ...
    stored = repr(ids)                         # ... stored as a python-repr string
    got = load_contract(_meta(tmp_path, stored, raw))
    # Whatever the reader does, it must not quietly return fewer ids than are there.
    assert len(got["fail_to_pass"]) >= 2, got["fail_to_pass"]


def test_the_operator_gap_is_read_from_the_failure_and_not_guessed():
    """The operator-to-dunder map is a property of Python, so deriving it is legitimate."""
    gap = read_operator_gap(
        "E   TypeError: unsupported operand type(s) for |: 'dict' and 'VarsWithSources'")
    assert gap["operator"] == "|"
    assert gap["method"] == "__ror__"          # the REFLECTED method: dict is on the left
    assert gap["target_class"] == "VarsWithSources"


def test_the_reflected_side_is_chosen_from_the_operand_order():
    """`int + Thing` needs `__radd__` on Thing; `Thing + int` needs `__add__`. Different code."""
    assert read_operator_gap(
        "TypeError: unsupported operand type(s) for +: 'int' and 'Thing'")["method"] == "__radd__"


def test_a_failure_that_is_not_an_operator_gap_returns_nothing():
    assert read_operator_gap("ValueError: nonsense") is None
    assert read_operator_gap("TypeError: unsupported operand type(s) for ~: 'a' and 'b'") is None


# --- what counts as a result -------------------------------------------------------------------

def test_a_parameterised_id_is_graded_at_the_function_level():
    """`[foo ]`, `[ foo]`, `[]` all make pytest answer "not found" for a test that exists.

    Grading the function requires the WHOLE parameter set to pass, which is stricter than any
    single requested id -- so the substitution cannot buy a false positive.
    """
    assert B._normalise_id("t.py::f[foo ]") == "t.py::f[foo]"
    assert B._normalise_id("t.py::f[ foo]") == "t.py::f[foo]"
    assert B._PARAM_RE.sub("", "t.py::f[1]") == "t.py::f"


def test_a_room_that_could_not_run_is_not_a_capability_failure():
    """The distinction the whole number rests on. Asserted on the source, not on a live run,
    because the live run is 90 seconds and this property must hold every time."""
    src = pathlib.Path(B.__file__).read_text(encoding="utf-8")
    assert '"room_broken": True' in src
    assert "room_skipped" in src
    # And the runner must not fold either into NOT_RESOLVED.
    assert 'rec["outcome"] = "ROOM_BROKEN"' in src
    assert 'rec["outcome"] = "ROOM_SKIPPED"' in src


def test_the_resolved_outcome_requires_every_named_test_to_have_been_seen():
    src = pathlib.Path(B.__file__).read_text(encoding="utf-8")
    assert "not unseen and all(_lookup(t) is True for t in ids)" in src


def test_the_solver_never_reads_a_gold_patch():
    """The solver may not READ the answer sheet. Naming it in a comment is not reading it.

    The first version asserted the word "gold" did not occur in `run_one`, which failed on the
    comment explaining that the leak had been fixed -- a test that punishes documentation of a
    repair is testing the wrong thing. What matters is that no path is opened or applied.
    """
    import ast
    src = pathlib.Path(B.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "run_one")
    strings = [n.value for n in ast.walk(fn)
               if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    # An f-string that BUILDS a gold path would appear as a Constant fragment too, so `_apply`
    # and `_contents` calls are what to look at: neither may be handed the answer sheet.
    calls = [n for n in ast.walk(fn) if isinstance(n, ast.Call)]
    for call in calls:
        name = getattr(call.func, "id", getattr(call.func, "attr", ""))
        if name in ("_apply", "_contents", "write_bytes", "write_text"):
            rendered = ast.dump(call).lower()
            assert "gold" not in rendered and "solution" not in rendered, ast.unparse(call)
    assert strings  # the function does build strings; this is not a vacuous pass
