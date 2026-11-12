"""The falsifiability probe must be able to fail, and must not confuse "raises" with "checks".

Two failure modes would make this a rubber stamp in its own right:

  * calling a guarded assignment unguarded (or the reverse), which is what separates "success
    reported only when a condition held" from "success reported unconditionally";
  * counting a predicate as a defect when the adapter raises on failure, which would relabel an
    honest exception gate as a lie.

Both are tested against synthetic source, so the test does not depend on any particular adapter.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from runtime_predicate_falsifiability_probe_20261112 import (  # noqa: E402
    ALWAYS_TRUE_GUARDED_RAISES,
    ALWAYS_TRUE_NO_RAISE,
    ALWAYS_TRUE_UNGUARDED_RAISES,
    DECLARATION_MISMATCH,
    DYNAMIC,
    NO_SOURCE,
    NOT_STATICALLY_VISIBLE,
    _guarded_assignments,
    _signals_failure,
    classify,
    run,
)

KNOWN_CLASSES = {
    DECLARATION_MISMATCH,
    NO_SOURCE,
    ALWAYS_TRUE_NO_RAISE,
    ALWAYS_TRUE_UNGUARDED_RAISES,
    ALWAYS_TRUE_GUARDED_RAISES,
    DYNAMIC,
    NOT_STATICALLY_VISIBLE,
}


def _classify_source(tmp_path: Path, source: str, *, field="output_verified", value=True,
                     declared=("output_verified",)) -> dict:
    adapter = tmp_path / "adapter.py"
    adapter.write_text(source, encoding="utf-8")
    row = {
        "action_template": {"expect": {"type": "field_equals", "field": field, "value": value}},
        "result_fields": list(declared),
        "source": {"adapter_path": "adapter.py"},
    }
    return classify("synthetic", row, tmp_path)


def test_unguarded_success_is_recognised(tmp_path):
    source = (
        "def run(args):\n"
        "    if not args:\n"
        "        raise ValueError('no args')\n"
        "    result = {}\n"
        "    result['output_verified'] = True\n"
        "    return result\n"
    )
    assert _classify_source(tmp_path, source)["class"] == ALWAYS_TRUE_UNGUARDED_RAISES


def test_guarded_success_is_not_called_a_defect(tmp_path):
    source = (
        "def run(args):\n"
        "    result = {}\n"
        "    result['output_verified'] = True\n"
        "    if not ok():\n"
        "        raise ValueError('failed')\n"
        "    return result\n"
    )
    # `ok()` is an explicit check before returning, but the assignment itself is unguarded --
    # the probe must say unguarded rather than flatter the source.
    assert _classify_source(tmp_path, source)["class"] == ALWAYS_TRUE_UNGUARDED_RAISES

    guarded = (
        "def run(args):\n"
        "    result = {}\n"
        "    if verify(args):\n"
        "        result['output_verified'] = True\n"
        "    else:\n"
        "        raise ValueError('failed')\n"
        "    return result\n"
    )
    assert _classify_source(tmp_path, guarded)["class"] == ALWAYS_TRUE_GUARDED_RAISES


def test_no_failure_signal_at_all_is_the_defect(tmp_path):
    source = "def run(args):\n    return {'output_verified': True}\n"
    assert _classify_source(tmp_path, source)["class"] == ALWAYS_TRUE_NO_RAISE


def test_a_computed_value_is_dynamic(tmp_path):
    source = "def run(args):\n    result = {}\n    result['output_verified'] = check()\n    return result\n"
    assert _classify_source(tmp_path, source)["class"] == DYNAMIC


def test_an_undeclared_predicate_field_is_a_mismatch(tmp_path):
    source = "def run(args):\n    return {'status': 'ok'}\n"
    assert _classify_source(tmp_path, source, declared=("status",))["class"] == DECLARATION_MISMATCH


def test_guard_detection_is_structural():
    guarded = ast.parse("if x:\n    d['k'] = 1\n")
    unguarded = ast.parse("d['k'] = 1\n")
    assert _guarded_assignments(guarded, "k") == (1, 0)
    assert _guarded_assignments(unguarded, "k") == (0, 1)


def test_raise_detection_does_not_fire_on_a_docstring():
    clean = ast.parse("def run():\n    '''raise is a word here'''\n    return 1\n")
    raiser = ast.parse("def run():\n    raise SystemExit(1)\n")
    assert _signals_failure(clean) is False
    assert _signals_failure(raiser) is True


def test_the_census_partitions_the_registry_and_finds_no_unconditional_silent_success():
    result = run()
    records = result["records"]
    counts = result["summary"]["classes"]

    assert sum(counts.values()) == len(records) == result["summary"]["capabilities"]
    assert set(counts) <= KNOWN_CLASSES
    # The strongest claim in the note: nowhere in the bound surface does an adapter report
    # success unconditionally with no failure signal at all.
    assert counts.get(ALWAYS_TRUE_NO_RAISE, 0) == 0
    # And the weaker class is real, not empty -- otherwise the note would be describing a
    # problem the probe cannot actually see.
    assert counts.get(ALWAYS_TRUE_UNGUARDED_RAISES, 0) > 0
    assert result["summary"]["defects"] == counts.get(DECLARATION_MISMATCH, 0)


def test_the_run_is_deterministic():
    import json

    assert json.dumps(run(), sort_keys=True) == json.dumps(run(), sort_keys=True)
