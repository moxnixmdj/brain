"""What a missing part buys, measured at full suite scale, and the two ways that result can lie.

The measurement this pins (`canonical/verification/DERIVED_VALUE_FULL_SUITE_20261116_V1.json`)
exists because the tree's earlier claim about the value algebra rested on **eight pages chosen by
looking at them** -- the exact self-congratulation the owner's standing instruction forbids. Run it
on all 130 real pages instead and the headline changes in a way that matters more than the headline:

    the algebra REPLACES the literal vocabulary -> net negative (61 vs 62 on jsdom)
    the algebra is ADDED to it                 -> 5 pages gained, 0 lost, fewer actions spent
    same size, wrong witness (decoy)           -> 14 pages lost

So this module pins four things, and each fails in a direction that would send the roadmap wrong:

  * `test_replacement_loses_pages_but_addition_does_not` -- if this ever passes as "replacement
    wins too", the next session would ship the replacement and quietly lose the email-inbox family
    and `enter-password` (seven pages), which no eight-page study could see.
  * `test_every_gain_is_on_the_design_set` -- the load-bearing honesty test. Zero of the gains
    transfer outside the pages the operators were written for. A single off-design gain would be
    the most important number in the tree; there are none, and that must stay visible.
  * `test_the_decoy_loses` -- the negative control. If the decoy stopped losing, the addition's
    gain could be explained by "more values on offer" rather than by the rules.
  * `test_a_seed_cannot_carry_the_result` -- two seeds, and the direction holds in both.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.tools import derived_value_full_suite_receipt_v1 as receipt  # noqa: E402

PATH = ROOT / "canonical/verification/DERIVED_VALUE_FULL_SUITE_20261116_V1.json"


def _receipt() -> dict:
    return json.loads(PATH.read_text())


def _run(name: str) -> dict:
    return _receipt()["runs"][name]


def test_addition_gains_and_never_loses():
    """U is A plus values. It may add pages; it must never remove one."""
    for seed in ("chromium_seed_1060", "chromium_seed_771"):
        cmp = _run(seed)["union_vs_shipped"]
        assert cmp["gains"], f"{seed}: the addition bought nothing"
        assert cmp["losses"] == [], f"{seed}: the addition removed pages {cmp['losses']}"


def test_replacement_loses_pages_but_addition_does_not():
    """The finding an eight-page study could not see.

    Handing the equation instead of adding it is a net loss: seven pages go, five come.
    """
    jsdom = _run("jsdom_seed_1060_replacement")["replacement_vs_shipped"]
    assert jsdom["net"] < 0, "the replacement arm is no longer a net loss; the record needs rereading"
    assert jsdom["losses"], "the replacement arm lost no pages; the email-inbox finding is stale"

    added = _run("chromium_seed_1060")["union_vs_shipped"]
    assert added["net"] > 0 and added["losses"] == [], "addition must dominate the replacement"


def test_every_gain_is_on_the_design_set():
    """The honesty test: there is no transfer, and pretending otherwise is the failure mode."""
    for seed in ("chromium_seed_1060", "chromium_seed_771"):
        cmp = _run(seed)["union_vs_shipped"]
        assert cmp["gains_outside_design_set"] == [], (
            f"{seed}: a gain appeared outside the pages the operators were written for: "
            f"{cmp['gains_outside_design_set']} -- this would be transfer, and it needs its own note")


def test_held_out_pages_are_unchanged_by_the_addition():
    """121 held-out pages: the shipped hand and the union must solve exactly the same number."""
    for seed in ("chromium_seed_1060", "chromium_seed_771"):
        held = _run(seed)["held_out_only"]
        assert held["A_shipped_hand"] == held["U_union"], (
            f"{seed}: the addition changed held-out performance ({held})")


def test_the_decoy_loses():
    """Same size, same shape, wrong witness. If it did not lose, the gain would be volume."""
    for seed in ("chromium_seed_1060", "chromium_seed_771"):
        cmp = _run(seed)["decoy_vs_shipped"]
        assert cmp["net"] < 0, f"{seed}: the decoy no longer loses; the control has stopped working"
        assert len(cmp["losses"]) >= 10, f"{seed}: the decoy barely lost ({len(cmp['losses'])} pages)"


def test_a_seed_cannot_carry_the_result():
    """The direction has to survive a reseed, or it is one lucky draw of page seeds."""
    first = _run("chromium_seed_1060")["union_vs_shipped"]
    second = _run("chromium_seed_771")["union_vs_shipped"]
    assert first["net"] > 0 and second["net"] > 0
    assert set(first["gains"]) & set(second["gains"]), "the two seeds do not agree on any gain"
    assert first["losses"] == second["losses"] == []


def test_the_record_keeps_both_substrates():
    """jsdom has no layout; Chromium does. A page that is only measurable on one of them is a
    property of the instrument, and the receipt must not hide which produced which number."""
    runs = _receipt()["runs"]
    assert "chromium_seed_1060" in runs and "jsdom_seed_1060_union" in runs
    jsdom = runs["jsdom_seed_1060_union"]["summary"]["arms"]
    chrom = runs["chromium_seed_1060"]["summary"]["arms"]
    assert chrom["A_shipped_hand"]["solved"] > jsdom["A_shipped_hand"]["solved"], (
        "real layout must not solve fewer pages than jsdom for the same hand")


def test_design_set_is_exactly_the_eight_published_pages():
    assert receipt.DESIGN_SET == frozenset({
        "simple-arithmetic", "simple-algebra", "scroll-text", "text-transform",
        "enter-time", "search-engine", "use-slider", "guess-number"})


def test_summarise_counts_only_pages_it_was_given():
    rows = [{"task": "a", "arms": {arm: {"pass": True, "budget_spent": 3,
                                         "verified_on_fresh_page": True} for arm in receipt.ARMS}}]
    out = receipt.summarise(rows)
    assert out["pages"] == 1
    assert all(out["arms"][arm]["solved"] == 1 for arm in receipt.ARMS)


def test_compare_reports_gains_and_losses_separately():
    """A net number would have hidden the replacement's real shape (5 gains, 7 losses)."""
    def row(task, wins):
        return {"task": task, "arms": {arm: {"pass": arm in wins, "budget_spent": 1,
                                             "verified_on_fresh_page": arm in wins}
                                       for arm in receipt.ARMS}}
    rows = [row("kept", {"A_shipped_hand", "U_union"}),
            row("gained", {"U_union"}),
            row("lost", {"A_shipped_hand"})]
    cmp = receipt.compare(rows, "U_union")
    assert cmp["gains"] == ["gained"] and cmp["losses"] == ["lost"] and cmp["net"] == 0
