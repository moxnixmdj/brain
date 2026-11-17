"""Oracle density: how much of real work can the repository's own checks see at all.

Two kinds of assertion here. Pure functions are checked against hand cases. The density number is
pinned against the receipt and re-derived live when the corpus clones are present -- when they are not,
the receipt test still runs and the live test skips with a reason, so an offline checkout cannot pass
by silence.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import oracle_density_v1 as density  # noqa: E402
from canonical.swe_kernel.systematic_edit_supply_v1 import Site  # noqa: E402

RECEIPT = ROOT / "canonical" / "verification" / "ORACLE_DENSITY_20261116_V1.json"


@pytest.fixture(scope="module")
def report() -> dict:
    return json.loads(RECEIPT.read_text(encoding="utf-8"))


def _clones_present() -> bool:
    return all((density.DEFAULT_CLONE_DIR / name.replace("/", "__") / ".git").exists()
               for name in density.REPOS)


def test_old_and_new_test_layouts_are_both_recognised() -> None:
    assert density._is_test_file("tests/test_core.py")
    assert density._is_test_file("markupsafe/tests.py")      # the old in-package layout
    assert density._is_test_file("pkg/mod_test.py")
    assert not density._is_test_file("click/core.py")
    assert not density._is_test_file("tests/conftest.txt")


def test_a_package_init_is_looked_up_by_its_package_name() -> None:
    assert density._module_stems("src/markupsafe/__init__.py") == ("markupsafe",)
    assert density._module_stems("pkg/mod.py") == ("mod",)
    assert density._module_stems("pkg/data.json") == ()


def test_only_distinctive_identifiers_are_used_as_the_probe() -> None:
    site = Site("a.py", ['return self.render_value("x")'], ['return self.render_value("y")'])
    tokens = density._tokens(site)
    assert "render_value" in tokens
    assert "self" not in tokens and "return" not in tokens


def test_the_density_number_is_the_one_the_loop_uses(report: dict) -> None:
    assert report["corpus"]["sha256"].startswith("b47d9c9c23e641a8")
    assert report["sites"] == 691
    assert report["sites_in_source_files"] == 589
    assert report["sites_in_test_files"] == 102
    density = report["oracle_density"]
    assert density["names_a_token"] == 0.5042
    assert density["structured_names_a_token"] == 0.6167
    # the loop is computed on python only, because the strength constant was measured on code
    assert density["python_only"]["sites"] == 330
    assert density["python_only"]["names_a_token"] == 0.6788
    assert density["python_only"]["structured_names_a_token"] == 0.8203
    loop = report["loop"]
    assert loop["suite_strength_when_checked"] == 0.8021
    assert loop["expected_error_seen"] == 0.5445
    assert loop["expected_error_invisible"] == 0.4555
    assert loop["structured_expected_error_invisible"] == 0.342


def test_the_loop_arithmetic_is_what_it_says(report: dict) -> None:
    loop = report["loop"]
    code = report["oracle_density"]["python_only"]
    assert loop["expected_error_seen"] == round(
        code["names_a_token"] * loop["suite_strength_when_checked"], 4)
    assert loop["structured_expected_error_invisible"] == round(
        1 - code["structured_names_a_token"] * loop["suite_strength_when_checked"], 4)


@pytest.mark.skipif(not _clones_present(),
                    reason="corpus clones absent; run with --clone to reproduce live")
def test_the_receipt_is_reproducible_from_the_real_repositories(report: dict) -> None:
    live = density.measure()
    assert live["sites"] == report["sites"]
    assert live["oracle_density"]["names_a_token"] == report["oracle_density"]["names_a_token"]
    assert live["by_repo"] == report["by_repo"]
