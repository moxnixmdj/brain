"""A clause that names nothing inherits the world the REQUEST named.

The defects, measured on ``e9861f4``
------------------------------------
``_compile_compound_goal`` started ``context_paths=[]`` and only ever appended
artifacts its own specialised compilers produced, so a later clause that names
no path ("... so they pass") had no world to inherit.  Completion fell through to
``world_binding_v1``, which scans the *tool's* working directory.  On

    "The tests in <b>/tests are failing. Fix the code so they pass."

the compiled plan carried

    part 0  test_paths  = "…/tests"        a STRING where the adapter iterates a list
            source_root = "…/tests"
    part 1  source_root = "canonical/tests"  the brain's OWN test suite, inside a
                                             sentence about a user fixture

and, once a later fix let both steps run, the pair executed, changed nothing,
left the suite red, and reported PASS.

The law
-------
1. ``*_paths`` is a LIST of paths.  A completion that picked one path picked a
   one-element list; it never picks a string.
2. A referent of a clause that names nothing is the referent the REQUEST named.
   "Inside" is the named path itself, or exactly one step outside it (the tree
   that holds what was named) -- any higher ancestor is a guess.
3. A clause that asks for a CHANGE may only be served by a capability whose own
   declared effects name a change.  The vocabulary is the row's ``provides``
   tokens read as words: ``python.refactor.rename_symbol`` says refactor,
   ``python.source.write.verified_repair_applied`` says write/repair/applied,
   ``python.tests.audit`` and ``shell.command.result`` say neither.

These tests can fail
--------------------
Against ``e9861f4``: ``test_the_request_world_is_the_context_every_clause_inherits``
FAILS (``context_paths`` starts empty), ``test_a_scope_slot_takes_the_directory_the_request_named``
FAILS (``_context_path_for_key`` only answered file-shaped keys) and
``test_a_change_clause_is_not_served_by_a_capability_that_cannot_change`` FAILS
(neither law existed).  The control test -- a named path is not widened to an
ancestor -- passes on both trees.
"""

from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import goal_compiler as gc  # noqa: E402

REGISTRY = ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
TMP = ROOT / "canonical/astra_runtime/tmp/request_world_pin_20261030"


def _fixture() -> pathlib.Path:
    base = TMP
    for sub in ("app", "tests"):
        (base / sub).mkdir(parents=True, exist_ok=True)
    (base / "app/__init__.py").write_text("", encoding="utf-8")
    (base / "app/models.py").write_text(
        '"""Models."""\n\n\nclass Item:\n    def __init__(self, name, price_cents, qty=1):\n'
        "        self.name = name\n        self.price_cents = price_cents\n        self.qty = qty\n\n\n"
        "def line_total(item):\n    return item.price_cents * item.qty\n", encoding="utf-8")
    (base / "tests/__init__.py").write_text("", encoding="utf-8")
    (base / "tests/test_models.py").write_text(
        "import unittest\n\nfrom app.models import Item, line_total\n\n\nclass T(unittest.TestCase):\n"
        "    def test_total(self):\n        self.assertEqual(line_total(Item('a', 100, 2)), 450)\n\n\n"
        'if __name__ == "__main__":\n    unittest.main()\n', encoding="utf-8")
    return base


def _registry() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))["capabilities"]


def test_the_request_world_is_the_context_every_clause_inherits() -> None:
    base = _fixture()
    named = base.relative_to(ROOT).as_posix() + "/tests"
    entry = dict(_registry()["python.tests.audit.unittest"])
    entry.setdefault("capability_id", "python.tests.audit.unittest")
    out = gc._complete_inputs_via_world_binding(
        "Fix the code so they pass", ROOT, "python.tests.audit.unittest", entry,
        context_paths=[named])
    assert out is not None, "the clause was refused instead of inheriting the request world"
    inputs, _provenance = out
    assert inputs.get("source_root") == named, inputs.get("source_root")
    assert inputs.get("source_root") != "canonical/tests"


def test_a_path_list_slot_never_holds_a_scalar() -> None:
    base = _fixture()
    named = base.relative_to(ROOT).as_posix() + "/tests"
    cid = "python.fault.localize.dynamic.dataflow.v1"
    entry = dict(_registry()[cid])
    entry.setdefault("capability_id", cid)
    out = gc._complete_inputs_via_world_binding(
        "The tests in " + named + " are failing", ROOT, cid, entry, context_paths=[named])
    assert out is not None, "the localiser could not be completed from the request world"
    inputs, _provenance = out
    assert not isinstance(inputs.get("test_paths"), str), inputs.get("test_paths")
    assert isinstance(inputs.get("test_paths", []), list), inputs.get("test_paths")
    assert str(inputs.get("source_root")) == named, inputs.get("source_root")


def test_a_change_clause_is_refused_not_executed_on_an_unchanged_tree() -> None:
    base = _fixture()
    named = base.relative_to(ROOT).as_posix() + "/tests"
    try:
        gc.compile_goal(f"The tests in {named} are failing. Fix the code so they pass.",
                        _registry(), ROOT)
    except gc.GoalCompilationFailure as exc:
        assert str(getattr(exc, "code", "")) == "GOAL_CHANGE_CLAUSE_SERVED_BY_A_CAPABILITY_THAT_CANNOT_CHANGE", exc
        return
    raise AssertionError("a change clause was compiled onto a capability that cannot change")


def test_a_scope_slot_takes_the_directory_the_request_named() -> None:
    named = "canonical/astra_runtime/tmp/x/tests"
    assert gc._context_path_for_key("source_root", [named]) == named
    assert gc._context_path_for_key("anchor_dir", ["pkg/app.py", "pkg"]) == "pkg"
    assert gc._context_path_for_key("anchor_dir", ["pkg/app.py"]) == "pkg"
    assert gc._context_path_for_key("source_root", []) is None


def test_a_referent_may_not_leave_the_request_world() -> None:
    named = "canonical/astra_runtime/tmp/x/one/tests"
    assert gc._referents_inside(named, [named], ROOT) is True
    assert gc._referents_inside("canonical/astra_runtime/tmp/x/one", [named], ROOT) is True
    # one step outside is the tree that holds what was named; two is a guess
    assert gc._referents_inside("canonical/tests", [named], ROOT) is False
    assert gc._referents_inside("canonical/astra_runtime/tmp", [named], ROOT) is False
    assert gc._referents_inside(".", [named], ROOT) is False


def test_a_change_clause_is_not_served_by_a_capability_that_cannot_change() -> None:
    registry = _registry()
    assert gc._demands_a_change("Fix the code so they pass") is True
    assert gc._demands_a_change("Rename the function a to b") is True
    assert gc._demands_a_change("Count the functions in D") is False
    assert gc._serves_a_change(registry["python.refactor.rename_symbol.v1"]) is True
    assert gc._serves_a_change(registry["python.software.repair.apply.verified.v1"]) is True
    assert gc._serves_a_change(registry["python.tests.audit.unittest"]) is False
    assert gc._serves_a_change(registry["shell.command.run"]) is False


def main() -> int:
    failures = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            fn()
            print("PASS", name)
        except AssertionError as exc:  # noqa: PERF203 - a runner, deliberately simple
            failures += 1
            print("FAIL", name, "->", str(exc)[:300])
    print("TOTAL", failures, "failed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
