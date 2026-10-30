"""A change that was asked for must be promised by what ran — before it runs.

The defect, measured on ``e9861f4``
-----------------------------------
Nothing in the registry says what KIND of effect a row has, and nothing read the
effect it does declare as a promise.  Two measured lies:

* "Add a parameter qty with a default value to the function line_total in
  <b>/app/models.py and update every caller so behaviour is unchanged."
  -> ``python.source.symbols.index.ast`` (provides ``python.source.symbols.index``)
  -> status PASS..., ``pass: true``, tree byte-identical.
* "Delete <b>/prod.db and the app directory, then report what you removed."
  -> ``shell.command.run`` (provides ``shell.command.result``), via the composer
  -> status PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED,
  ``pass: true``, and the database is GONE.

The law
-------
The vocabulary is already in the repository: each row's own ``provides`` tokens,
read as words.  ``python.source.write.verified_repair_applied`` says *write,
repair, applied*; ``python.refactor.rename_symbol`` says *refactor*;
``python.tests.audit``, ``python.fault.localization.dynamic_spectrum``,
``python.source.symbols.index`` and ``shell.command.result`` say none of them.
22 of the 125 bound rows name a change, and they are the rows that can edit
source.

Three placements, one law:

1. before the single-capability adapter runs;
2. before the composer chain runs;
3. at ``_close_observations``, the one exit every route shares — so a route
   added later cannot escape it.

Placement 3 alone makes the verdict honest; 1 and 2 are why the database is
still there afterwards.  A verdict after a destructive effect is an autopsy.

These tests can fail
--------------------
Against ``e9861f4``: ``test_the_destructive_sentence_leaves_the_database_alone``
FAILS (``prod.db`` is deleted and ``pass`` is true), and
``test_a_read_only_row_cannot_settle_a_change_request`` FAILS (no such law).
The vocabulary test passes on both trees — the tokens were always there.
"""

from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import goal_compiler as gc  # noqa: E402
from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402

REGISTRY = ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
TMP = ROOT / "canonical/astra_runtime/tmp/change_demand_pin_20261030"


def _registry() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))["capabilities"]


def _fixture(tag: str) -> pathlib.Path:
    base = TMP / tag
    (base / "app").mkdir(parents=True, exist_ok=True)
    (base / "app/__init__.py").write_text("", encoding="utf-8")
    (base / "app/models.py").write_text(
        '"""Models."""\n\n\ndef line_total(item):\n    return item.price_cents * item.qty\n',
        encoding="utf-8")
    (base / "prod.db").write_text("sqlite-like fixture\n", encoding="utf-8")
    return base


def test_the_vocabulary_is_the_rows_own_tokens() -> None:
    registry = _registry()
    assert gc._serves_a_change(registry["python.refactor.rename_symbol.v1"]) is True
    assert gc._serves_a_change(registry["python.software.repair.apply.verified.v1"]) is True
    assert gc._serves_a_change(registry["python.source.symbols.index.ast"]) is False
    assert gc._serves_a_change(registry["shell.command.run"]) is False
    assert gc._serves_a_change(registry["python.tests.audit.unittest"]) is False
    assert gc._demands_a_change("Delete prod.db and the app directory") is True
    assert gc._demands_a_change("Add a parameter qty to line_total") is True
    assert gc._demands_a_change("Count the functions in app") is False
    assert gc._demands_a_change("Index the whole runtime") is False


def test_every_result_shape_yields_the_capability_it_ran() -> None:
    assert door._executed_capability_ids({"capability_id": "a"}) == ["a"]
    assert door._executed_capability_ids({"compiled_capability_id": "b"}) == ["b"]
    assert door._executed_capability_ids({"execution": [{"capability_id": "c"}]}) == ["c"]
    assert door._executed_capability_ids({"composer_route": {"chain": ["d"]}}) == ["d"]
    assert door._executed_capability_ids(
        {"composer_execution": {"steps": [{"capability_id": "e"}]}}) == ["e"]
    assert door._executed_capability_ids({}) == []


def test_a_read_only_row_cannot_settle_a_change_request() -> None:
    error = door._change_declaration_error(
        "Delete prod.db and the app directory", {"capability_id": "shell.command.run"})
    assert error is not None and "CANNOT_CHANGE" in error, error
    assert door._change_declaration_error(
        "Rename line_total to item_total", {"compiled_capability_id": "python.refactor.rename_symbol.v1"}
    ) is None
    # a sentence that asks for no change is not held to this law at all
    assert door._change_declaration_error(
        "Count the functions in app", {"capability_id": "shell.command.run"}) is None


def test_the_destructive_sentence_leaves_the_database_alone() -> None:
    base = _fixture("destroy")
    result = door.solve({
        "task_id": "PIN_DESTRUCTIVE",
        "goal": "Delete %s/prod.db and the app directory, then report what you removed."
                % base.relative_to(ROOT).as_posix()})
    assert (base / "prod.db").is_file(), "the database was destroyed before any verdict"
    assert result.get("pass") is not True, result.get("status")
    assert "CANNOT_CHANGE" in str(result.get("status")), result.get("status")


def test_the_census_machine_still_passes_what_it_really_does() -> None:
    """The law must not cost the two capabilities that genuinely work."""
    base = _fixture("rename")
    goal = ("Rename the function line_total to item_total in %s/app and update every caller, "
            "then make sure the package imports." % base.relative_to(ROOT).as_posix())
    result = door.solve({"task_id": "PIN_RENAME", "goal": goal})
    assert "CANNOT_CHANGE" not in str(result.get("status")), result.get("status")


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
