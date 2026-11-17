"""Computer-use check density, and the property that keeps it honest: replay and novelty are different.

Pinned exactly: the receipt's numbers. Checked live: only the structural invariants that must hold on any
machine (a full observation never sees less than a coarse one, replay never sees less than novelty), so a
different container cannot fail the suite for being different, and a regression in the instrument still
does.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import computer_use_check_density_v1 as density  # noqa: E402

RECEIPT = ROOT / "canonical" / "verification" / "COMPUTER_USE_CHECK_DENSITY_20261116_V1.json"


@pytest.fixture(scope="module")
def report() -> dict:
    return json.loads(RECEIPT.read_text(encoding="utf-8"))


def test_mutants_are_derived_mechanically_from_the_template() -> None:
    kinds = {kind for kind, _command in density._mutants("tar -cf {dst} {src}")}
    assert kinds == {"wrong_source", "wrong_target", "drop_target", "swap_source_target",
                     "drop_first_flag"}
    assert density._mutants("sha256sum in.txt") == []


def test_the_three_observation_models_see_different_amounts() -> None:
    import tempfile

    root = pathlib.Path(tempfile.mkdtemp())
    try:
        (root / "a.txt").write_bytes(b"hello")
        (root / "b.txt").write_bytes(b"hello")
        assert density._observe(root, "listing") == "a.txt|b.txt"
        assert density._observe(root, "coarse") == "a.txt:5|b.txt:5"
        assert density._observe(root, "full") != density._observe(root, "coarse")
    finally:
        import shutil
        shutil.rmtree(root, ignore_errors=True)


def test_the_receipt_numbers(report: dict) -> None:
    assert report["tasks_run"] == 9
    assert report["mutants"] == 34
    assert [skip["task"] for skip in report["tasks_skipped"]] == ["gunzip"]
    by_obs = report["density_by_observation"]
    assert by_obs["full"]["density"] == 1.0
    assert by_obs["full"]["INDISTINGUISHABLE"] == 0
    assert by_obs["coarse"]["density"] == 0.9706
    assert by_obs["listing"]["density"] == 0.7647
    assert by_obs["listing"]["indistinguishable_share"] == 0.2353


def test_replay_and_novelty_are_not_the_same_problem(report: dict) -> None:
    regime = report["density_by_regime"]
    assert regime["full"]["replay_density"] == 1.0
    assert regime["full"]["novel_density"] == 0.5
    # without a recorded consequence, the 17 difference-detections are unavailable
    assert report["density_by_observation"]["full"]["DIFFERS"] == 17
    for model in ("full", "coarse", "listing"):
        assert regime[model]["replay_density"] >= regime[model]["novel_density"]


def test_a_live_run_upholds_the_ordering_without_pinning_the_machine() -> None:
    live = density.measure()
    by_obs = live["density_by_observation"]
    assert live["mutants"] > 0
    assert by_obs["full"]["density"] >= by_obs["coarse"]["density"] >= by_obs["listing"]["density"]
    assert by_obs["full"]["density"] == 1.0
    for model in ("full", "coarse", "listing"):
        assert live["density_by_regime"][model]["replay_density"] >= \
            live["density_by_regime"][model]["novel_density"]


def test_the_receipt_says_what_it_is_and_is_not(report: dict) -> None:
    environment = report["environment"]
    assert "real directory" in environment["kind"]
    assert set(environment["observation_models"]) == {"full", "coarse", "listing"}
    assert "recorded consequence" in environment["what_an_oracle_needs"]
    assert "neither zero nor" in report["what_this_shows"]
