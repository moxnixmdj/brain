"""Tests for OBSERVATIONAL_POOL_IS_EMPTY_BY_CONSTRUCTION_V1.

These pin the arithmetic AND the reading of `count_survivors`, which cost this session a wrong
turn. `count_survivors(allowed, exclusions)` counts `|{C subset allowed : C hits every exclusion}|`,
so an exclusion row `D_i` is the set of facts a failure DROPPED, and it kept `n - |D_i|`. A draft
of this module read `D_i = [20, 20]` as the KEPT set, concluded the corpus was already
interventional, and reported a 4x advantage where the truth is 524,288x. `test_D_is_the_dropped_set`
exists so that misreading cannot ship.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, "/home/user/brain")

from canonical.runtime import applicability_v1 as A  # noqa: E402
from canonical.tools import observational_pool_is_empty_by_construction_v1 as M  # noqa: E402


def test_law_holds_in_both_pools():
    """Every state eliminates exactly 2^kept, worst case -- the law from #6906."""
    for block in (M.run()["observational"], M.run()["interventional"]):
        for row in block["rows"]:
            assert row["law_check_2_to_the_kept"] == 2 ** row["kept"]
            assert row["eliminates"] == 2 ** row["kept"]


def test_real_corpus_numbers_match_the_merged_receipt():
    """|A|=23, D_i=[20,20] -> survivors 2^23 - 8, i.e. the corpus eliminated 8."""
    result = M.run()
    assert result["observational"]["candidates"] == 23
    assert result["price_of_not_intervening"]["whole_observed_pool_eliminated"] == 8
    universe = M.universe(23)
    facts = sorted(universe)
    dropped = frozenset(facts[:20])
    assert M.survivors(universe, [dropped, dropped]) == 8_388_600 == 2 ** 23 - 8


def test_D_is_the_dropped_set_not_the_kept_set():
    """The misreading that cost a wrong turn: |D_i|=20 means kept 3, not kept 20."""
    universe = M.universe(23)
    dropped = frozenset(sorted(universe)[:20])
    observed = M.pool_report(universe, [dropped], "one")
    assert observed["rows"][0]["dropped"] == 20
    assert observed["rows"][0]["kept"] == 3
    assert observed["rows"][0]["eliminates"] == 2 ** 3


def test_duplication_is_what_wasted_the_corpus():
    """Two DISTINCT kept-3 failures buy 15; the corpus's duplicate pair bought 8."""
    universe = M.universe(23)
    facts = sorted(universe)
    a = frozenset(facts[:20])       # dropped these 20, kept 3
    b = frozenset(facts[3:23])      # dropped a different 20, kept 3
    before = 2 ** 23
    two_distinct = before - M.survivors(universe, [a, b])
    duplicated = before - M.survivors(universe, [a, a])
    assert two_distinct == 15
    assert duplicated == 8
    assert two_distinct > duplicated, "the second failure bought 7, not 8"


def test_one_near_miss_halves_the_space():
    """A near miss dropping ONE candidate keeps 22 and eliminates 2^22 -- half of 2^23."""
    universe = M.universe(23)
    near = frozenset({sorted(universe)[0]})   # drops exactly one, keeps 22
    assert M.elimination(universe, 2 ** 23, near) == 2 ** 22
    assert M.elimination(universe, 2 ** 23, near) == 2 ** 23 // 2


def test_one_near_miss_versus_the_whole_real_corpus():
    """524,288x. Not 4x -- that was the misreading; not 131,072x -- that was an invented pool."""
    result = M.run()
    price = result["price_of_not_intervening"]
    assert price["whole_pool_vs_one_near_miss"] == 524_288
    assert price["whole_pool_vs_one_near_miss"] == 2 ** 19


def test_no_invented_pool_is_used():
    """The observational pool must be the receipt's real D_i, not a plausible story."""
    observed = M.run()["observational"]
    assert observed["states"] == 2
    assert observed["best_kept"] == 3, "D_i=[20,20] over |A|=23 keeps 3"
    assert observed["total_dropped_across_states"] == 40  # 20 dropped, twice


def test_realizability_gate_is_declared_not_asserted():
    """Intervention is only admissible if reachable; this module must not claim it is."""
    gate = M.run()["realizability_gate"]
    assert gate["status"] == "NOT_MEASURED_HERE"
    assert "constructor_v2" in gate["component"]


def test_authority_is_none_and_spend_is_zero():
    result = M.run()
    assert result["authority"].startswith("NONE")
    assert result["incremental_spend_usd"] == 0
    assert result["producer_cognition_model_dependency_count"] == 0


def test_receipt_round_trips_from_disk():
    import json
    path = Path("canonical/verification/"
                "OBSERVATIONAL_POOL_IS_EMPTY_BY_CONSTRUCTION_20261116_V1.json")
    if not path.exists():
        return
    on_disk = json.loads(path.read_text())
    live = M.run()
    assert on_disk["price_of_not_intervening"] == live["price_of_not_intervening"]
