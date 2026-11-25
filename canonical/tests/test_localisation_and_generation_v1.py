"""Localisation and generation, measured separately.

The point of separating them: V34 could not say whether it was failing to find the place or failing to know
what to do there. It reported both as "refused". These tests keep that distinction from collapsing again.
"""
from __future__ import annotations

import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from canonical.tools import assertion_localisation_v1 as locate  # noqa: E402
from canonical.tools import behavioural_emission_v2 as generate  # noqa: E402

RECEIPT = REPO / "canonical" / "corpus" / "localisation_and_generation_20261124_V1.json"


def test_a_test_file_is_never_package_code():
    assert locate.is_package_code("src/pkg/module.py")
    assert not locate.is_package_code("tests/test_mod.py")
    assert not locate.is_package_code("docs/conf.py")
    assert not locate.is_package_code("CHANGELOG.md")


def test_assertion_names_are_read_from_the_failing_assert():
    source = "def test_x():\n    assert Infinity <= Infinity\n    assert tomli.TOMLDecodeError().__module__ == 'tomli'\n"
    found = locate.failing_assertion(source, 3)
    assert found and "TOMLDecodeError" in locate.names_in(found[0])


def test_a_string_value_is_never_matched_by_substring():
    """'tomli' is a substring of 'tomli._parser'. A value is matched as a literal, never as a substring."""
    literals = generate.string_literals("x = 'tomli._parser'\n")
    assert "tomli" not in literals
    assert "tomli._parser" in literals


def test_a_text_only_change_is_recognised_as_cosmetic(tmp_path):
    path = tmp_path / "m.py"
    path.write_text("raise Error(f'bad \"{value!r}\"')\n")
    candidate = {"path": path, "text": "raise Error(f'bad  {value!r} ')\n"}
    assert generate.is_cosmetic(candidate, {path: path.write_text("") or "raise Error(f'bad \"{value!r}\"')\n"})


def test_a_structural_change_is_not_cosmetic(tmp_path):
    path = tmp_path / "m.py"
    original = "def loads(s):\n    return parse(s)\n"
    path.write_text(original)
    candidate = {"path": path, "text": "def loads(s, *, f=None):\n    return parse(s, f=f)\n"}
    assert not generate.is_cosmetic(candidate, {path: original})


def test_a_task_whose_fix_edits_test_data_is_excluded_not_refused():
    assert generate.TEST_FIXTURE_TASKS
    for reason in generate.TEST_FIXTURE_TASKS.values():
        assert "fixture" in reason or "test" in reason


def test_receipt_separates_localisation_from_generation():
    receipt = json.loads(RECEIPT.read_text())
    assert receipt["part_one_localisation"]["frame_baseline_V34"]["found_nothing"] == 10
    assert receipt["part_one_localisation"]["combined_ranked"]["any_at_5"] == 10
    generation = receipt["part_two_generation"]
    assert generation["solved"] == 3
    assert generation["denominator"] == 8
    assert generation["solved_that_only_change_text"] == 1


def test_the_ablation_is_recorded_as_zero_difference():
    receipt = json.loads(RECEIPT.read_text())
    ablation = receipt["ablation_store_vs_empty"]
    assert ablation["difference"] == 0
    assert "generation, not localisation" in ablation["why"]


def test_no_benchmark_claim_appears_in_the_receipt():
    """The receipt may *mention* benchmarks to disclaim them. It may not assert a score."""
    receipt = json.loads(RECEIPT.read_text())
    assert "benchmark" not in receipt
    text = json.dumps(receipt)
    for forbidden in ("pass@1", "resolved_rate", "score"):
        assert forbidden not in text
