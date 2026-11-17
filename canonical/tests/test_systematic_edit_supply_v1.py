#!/usr/bin/env python3
"""Pins what one demonstration can amortise in real engineering, from the shipped receipt.

The laws these tests hold down, from `canonical/verification/SYSTEMATIC_EDIT_SUPPLY_20261116_V1.json`:

  * the corpus is real history from five public repositories, pinned by sha256, so the numbers are
    reproducible offline and cannot drift silently;
  * only about a sixth of real commits contain a sibling site at all -- for the rest, "do it once"
    is one acquisition per instance, because there is nothing for the demonstration to generalise to;
  * where a sibling exists, most of what a demonstration gets right is a VERBATIM repeat: the same
    edit text belongs there too, so memory covers it and nothing has to be induced;
  * on the pairs that genuinely need induction, the demonstration reproduces the developer's edit
    about half the time and is wrong the other half -- which is the published ceiling, not perfection;
  * determinacy erodes with edit size: a five-line demonstration forces almost nothing.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:  # pragma: no cover - import wiring
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import systematic_edit_supply_v1 as supply  # noqa: E402

RECEIPT = ROOT / "canonical" / "verification" / "SYSTEMATIC_EDIT_SUPPLY_20261116_V1.json"


def _report() -> dict:
    return json.loads(RECEIPT.read_text(encoding="utf-8"))


def _live() -> dict:
    return supply.measure()


def test_the_corpus_is_real_history_and_pinned() -> None:
    report = _report()
    assert report["corpus"]["records"] == 393
    assert len(report["corpus"]["repos"]) == 5
    assert report["corpus"]["sha256"].startswith("b47d9c9c23e641a8")
    corpus = ROOT / report["corpus"]["path"]
    assert corpus.exists()
    records = supply.read_corpus(corpus)
    assert len(records) == 393
    assert all(len(record["sha"]) == 40 for record in records)


def test_only_a_minority_of_real_commits_have_a_sibling_to_learn_from() -> None:
    loose = _report()["by_rung"]["shape_only"]
    assert loose["commits_scanned"] == 268
    assert loose["commits_with_sibling_sites"] == 43
    assert loose["supply_share"] == 0.1604


def test_most_of_what_memory_covers_is_a_verbatim_repeat() -> None:
    loose = _report()["by_rung"]["shape_only"]
    assert loose["outcomes"]["verbatim"] == 103
    assert loose["determined"] == 134
    assert loose["outcomes"]["verbatim"] > loose["determined"] // 2


def test_induction_reproduces_the_developer_about_half_the_time() -> None:
    loose = _report()["by_rung"]["shape_only"]
    pairs = loose["pairs"]
    verbatim = loose["outcomes"]["verbatim"]
    generalising = pairs - verbatim
    matched = loose["determined"] - verbatim + loose["lucky"]
    assert generalising == 142
    assert 0.5 < matched / generalising < 0.6
    assert loose["wrong_share"] == 0.2612


def test_determinacy_erodes_with_edit_size() -> None:
    buckets = _report()["by_rung"]["shape_only"]["by_demonstration_size"]
    assert buckets["2"]["pairs"] == 197
    assert buckets["5"]["pairs"] == 14
    assert buckets["5"]["determined"] == 3


def test_a_stricter_context_rung_shrinks_supply_and_raises_precision() -> None:
    rungs = _report()["by_rung"]
    assert rungs["context_both"]["commits_with_sibling_sites"] < \
        rungs["shape_only"]["commits_with_sibling_sites"]
    assert rungs["context_both"]["determined_share"] > rungs["shape_only"]["determined_share"]


def test_abstraction_puts_identifiers_numbers_and_literals_in_holes() -> None:
    template, holes = supply.abstract("x = foo(3, 'bar')")
    assert holes == (("ID", "x"), ("ID", "foo"), ("NUM", "3"), ("STR", "'bar'"))
    assert template.count("\x00") == 4


def test_induce_rebinds_what_the_target_determines_and_flags_what_it_cannot() -> None:
    demo = supply.Site("a.py", ["    return foo(x)"], ["    return foo(x, y)"])
    target = supply.Site("b.py", ["    return baz(q)"], ["    return baz(q, y)"])
    result = supply.induce(demo, target)
    assert result["verdict"] == "exact"
    assert result["lines"] == ["    return baz(q, y)"]
    # `return` and `baz` and `q` are bound through the removed line; `y` is introduced by the edit,
    # so it is copied rather than derived, and the marking says exactly that.
    assert result["copied"] == [[False, False, False, True]]


def test_induce_reports_a_value_the_demonstration_cannot_supply() -> None:
    demo = supply.Site("a.py", ['version = "1.0"'], ['version = "1.1"'])
    target = supply.Site("b.py", ['version = "2.0"'], ['version = "2.1"'])
    result = supply.induce(demo, target)
    assert result["verdict"] == "constant_differs"
    assert result["lines"] == ['version = "1.1"']


def test_derivation_carries_the_demonstrations_own_arithmetic_onto_the_target() -> None:
    """1.0 -> 1.1 taught at 2.0 must give 2.1, and the value must count as derived, not copied."""
    demo = supply.Site("a.py", ['version = "1.0"'], ['version = "1.1"'])
    target = supply.Site("b.py", ['version = "2.0"'], ['version = "2.1"'])
    copied = supply.induce(demo, target)
    derived = supply.induce(demo, target, derive=True)
    assert copied["verdict"] == "constant_differs" and copied["derived"] == 0
    assert derived["verdict"] == "exact"
    assert derived["lines"] == ['version = "2.1"']
    assert derived["derived"] == 1
    assert not any(any(flags) for flags in derived["copied"])


def test_a_contrast_only_licenses_the_shift_it_can_reproduce() -> None:
    demo = supply.Site("a.py", ['version = "1.0"'], ['version = "1.1"'])
    agreeing = supply.Site("c.py", ['version = "2.0"'], ['version = "2.1"'])
    disagreeing = supply.Site("c.py", ['version = "2.0"'], ['version = "2.9"'])
    numeric = next(i for i, (_kind, text) in enumerate(demo.holes_removed)
                   if supply._numeric(text))
    demo_base, demo_value = demo.holes_removed[numeric][1], demo.holes_added[numeric][1]
    assert supply._contrast_agrees(agreeing, demo_base, demo_value)
    assert not supply._contrast_agrees(disagreeing, demo_base, demo_value)


def test_derived_values_are_right_only_a_fifth_of_the_time_on_real_history() -> None:
    """The value layer is the hole: firing on 42 of 142 inductive pairs, right on 9 of them."""
    loose = _live()["by_rung"]["shape_only"]
    assert loose["derive_arm"]["pairs_where_derivation_fired"] == 42
    assert loose["derive_arm"]["pairs_where_derivation_was_right"] == 9
    assert loose["contrast_arm"]["pairs_where_derivation_fired"] == 15
    assert loose["contrast_arm"]["pairs_where_derivation_was_right"] == 6
    # Derivation barely moves the aggregate: the whole gain is a handful of pairs, and it creates
    # new wrong values (rebound_wrong 20 -> 33) where copying happened to be right.
    assert loose["outcomes"]["constant_differs"] == 31
    assert loose["derive_arm"]["outcomes"]["constant_differs"] == 12
    assert loose["derive_arm"]["outcomes"]["rebound_wrong"] > loose["outcomes"]["rebound_wrong"]
    # A second demonstration doubles the precision of a derived value and makes the system abstain
    # more: the contrast is the acquisition unit, and even it leaves the value unidentifiable.
    assert loose["contrast_arm"]["pairs_where_derivation_fired"] < \
        loose["derive_arm"]["pairs_where_derivation_fired"]
    assert (loose["contrast_arm"]["pairs_where_derivation_was_right"]
            / loose["contrast_arm"]["pairs_where_derivation_fired"]) > 1.5 * (
        loose["derive_arm"]["pairs_where_derivation_was_right"]
        / loose["derive_arm"]["pairs_where_derivation_fired"])


def test_the_derivation_receipt_is_the_run_it_claims_to_be() -> None:
    root = pathlib.Path(__file__).resolve().parents[2]
    receipt = root / "canonical/verification/SYSTEMATIC_EDIT_DERIVATION_20261116_V1.json"
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    assert payload["corpus"]["sha256"].startswith("b47d9c9c23e641a8")
    live = _live()
    for arm in ("derive_arm", "contrast_arm"):
        assert payload["by_rung"]["shape_only"][arm]["pairs_where_derivation_fired"] == \
            live["by_rung"]["shape_only"][arm]["pairs_where_derivation_fired"]
        assert payload["by_rung"]["shape_only"][arm]["pairs_where_derivation_was_right"] == \
            live["by_rung"]["shape_only"][arm]["pairs_where_derivation_was_right"]
    assert payload["by_rung"]["shape_only"]["outcomes"]["verbatim"] == 103
