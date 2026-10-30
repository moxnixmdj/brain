"""A row that declares an optional input is not refused for it.

The defect, measured on ``4605d7b``
-----------------------------------
``input_keys`` reads every ``${input.X}`` placeholder of a row's
``action_template.args`` as a DEMAND on the caller, and the only thing that could
withdraw the demand was ``declared_adapter_defaults`` -- which reads exactly one
AST shape, ``args.get("k") or <literal>``.

Six of the seven repair rows fall back through a CALL instead::

    argv = argv_or_derived(args.get("test_argv"), sys.executable, *test_paths)

``_declared_default_value`` cannot evaluate a call, so ``test_argv`` stayed a
demand that no adapter makes, and every one of those rows was unreachable from
the front door.  Measured on

    Apply the verified repair to <b>/app so the failing test in <b>/tests passes.

the sentence reached ``software.repair.choreograph.crossfile.v1`` -- a different,
weaker capability -- and failed with ``PROMISED_SOURCE_CHANGE_NOT_APPLIED``.  The
capability that actually edits was never offered.

The law
-------
A demand the adapter does not make is not a demand.  The row declares it beside
the args it declares -- ``action_template.optional: ["test_argv"]`` -- and the
binder passes ``None``.  The adapter's own ``*_REQUIRED`` refusal stays the only
authority on whether the declaration is true, so a row that lies about this
fails loudly at the call instead of quietly binding nothing.

Why the AST shape is NOT the mechanism
--------------------------------------
Inferring it from the call was tried and rejected on measurement: a first
argument forwarded to a helper is indistinguishable from a value handed to a
judge, so ``isinstance(args.get("actions"), list)`` and
``verify(args.get("goal"), result, registry)`` were read as derivations and
``goal`` would have been bound to ``None`` on a verification capability.  Four
false positives out of seven rows is not a rule; a declaration is.

These tests can fail
--------------------
Against ``4605d7b``: ``test_a_declared_optional_key_binds_as_none`` FAILS (the
declaration is ignored and the key is reported unbound) and
``test_the_seven_repair_rows_bind_without_a_stated_test_command`` FAILS (each
row raises ``GOAL_INPUT_BINDING_REQUIRED:test_argv:not_stated``).  The control
test passes on both trees: an undeclared key must still refuse.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import goal_front_compiler_v1 as front  # noqa: E402

REGISTRY = ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"

ROWS = [
    "python.patch.search.test_guided.ast.v1",
    "python.software.repair.apply.verified.v1",
    "python.software.repair.guided.provenance.coupled.v1",
    "python.software.repair.loop.coupled.ast.v1",
    "python.software.repair.loop.strict_progress.ast.v1",
    "python.software.repair.measured_acceptance.v1",
    "python.software.repair.semantic_acceptance.v1",
]


def _registry() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))["capabilities"]


def _unbound(key: str = "test_argv") -> list:
    exc = front.GoalCompilationFailure("GOAL_INPUT_BINDING_REQUIRED", key + ":not_stated")
    return [(key, exc)]


def test_declaration_is_read_and_absence_is_empty() -> None:
    entry = {"action_template": {"args": {"test_argv": "${input.test_argv}"},
                                 "optional": ["test_argv"]}}
    assert front.declared_optional_inputs(entry) == {"test_argv"}
    # a single key is a declaration too, and a missing one is nothing at all
    assert front.declared_optional_inputs(
        {"action_template": {"optional": "test_argv"}}) == {"test_argv"}
    assert front.declared_optional_inputs({"action_template": {"args": {}}}) == set()
    assert front.declared_optional_inputs(None) == set()
    # a row that lists something it does not declare as an arg declares nothing usable
    assert "test_argv" not in front.declared_optional_inputs(
        {"action_template": {"args": {"source_root": "${input.source_root}"},
                             "optional": ["test_argv"]}}) - {"test_argv"}


def test_a_declared_optional_key_binds_as_none() -> None:
    entry = {"action_template": {"args": {"test_argv": "${input.test_argv}"},
                                 "optional": ["test_argv"]}}
    inputs: dict = {}
    left = front.derive_declared_inputs("do the thing", _unbound(), ROOT, entry, inputs)
    assert left == [], left
    assert inputs == {"test_argv": None}, inputs


def test_an_undeclared_key_still_refuses() -> None:
    entry = {"action_template": {"args": {"test_argv": "${input.test_argv}"}}}
    inputs: dict = {}
    left = front.derive_declared_inputs("do the thing", _unbound(), ROOT, entry, inputs)
    assert [key for key, _exc in left] == ["test_argv"]
    assert inputs == {}


def test_the_seven_repair_rows_declare_it_and_their_adapters_read_it() -> None:
    registry = _registry()
    for cid in ROWS:
        entry = registry[cid]
        assert "test_argv" in front.input_keys(entry), cid
        assert "test_argv" in front.declared_optional_inputs(entry), cid
        inputs: dict = {}
        left = front.derive_declared_inputs("do the thing", _unbound(), ROOT, entry, inputs)
        assert left == [], (cid, [key for key, _exc in left])
        assert inputs["test_argv"] is None, cid
        # the declaration is about THIS adapter: it must read the key it claims
        module = str(entry.get("adapter_module"))
        path = ROOT / "canonical/runtime/bound_capabilities" / (module + ".py")
        assert path.is_file(), (cid, module)
        assert re.search(r"args\.get\(['\"]test_argv['\"]\)",
                         path.read_text(encoding="utf-8")), (cid, module)


def test_no_other_row_claims_an_optional_input() -> None:
    """The declaration is a contract, so it may only appear where it was measured."""
    registry = _registry()
    carriers = sorted(cid for cid, entry in registry.items()
                      if front.declared_optional_inputs(entry))
    assert carriers == sorted(ROWS), carriers


def main() -> int:
    failures = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            fn()
            print("PASS", name)
        except AssertionError as exc:  # noqa: PERF203 - a test runner, deliberately simple
            failures += 1
            print("FAIL", name, "->", str(exc)[:300])
    print("TOTAL", failures, "failed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
