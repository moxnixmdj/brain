"""What the operand walls are, counted -- and the two ways this count could mislead the roadmap.

The measurement (`canonical/verification/DECLARED_TRIGGER_AND_OPERAND_TAXONOMY_20261116_V1.json`)
exists to stop a specific mistake. The previous session measured that adding a value algebra gains
5 pages, all of them inside the 8 pages its rules were written on, and **0 of 121 held out**. The
tempting next move was "add more operators". Reading the source says why more operators would have
failed the same way: every rule is gated on a hand-written English phrase ("last word", "below",
"shown"), which is a fact about the design pages and not a fact about a new page.

So this pins three things, and each fails in a direction that would send the roadmap wrong:

  * `test_the_declared_surface_is_six_pages` -- if a "declared format" prior looked like a big
    lever, the next session would build it. It covers SIX pages. It is a rounding error and must
    stay labelled as one.
  * `test_no_class_holds_more_than_six_pages` -- the shape of the miss is a long tail, not one
    bottleneck. If a single class ever holds most of the remainder, the roadmap changes; until it
    does, "the single bottleneck" is a question with a false premise on this suite.
  * `test_no_page_is_unclassified` -- every page the hand cannot solve is accounted for. A page
    falling out of the taxonomy would be silently dropped from every downstream count.

And one test that guards the *instrument*, because this session produced a real instance of the
defect: three pages would not reset under jsdom and came back with an empty instruction. Treating
that as "no class" would have made an instrument limit look like a property of the pages.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime import declared_trigger_census_v1 as census  # noqa: E402

PATH = ROOT / "canonical/verification/DECLARED_TRIGGER_AND_OPERAND_TAXONOMY_20261116_V1.json"


def _receipt() -> dict:
    return json.loads(PATH.read_text())


def test_the_declared_surface_is_six_pages():
    """A prior over DECLARED formats covers 6 of 123 pages. Not a bottleneck."""
    surface = _receipt()["declared_surface"]
    assert surface["pages_declaring_a_format"] == 6, surface["declaring_pages"]
    assert set(surface["declaring_pages"]) == {
        "enter-date", "enter-password", "enter-time", "guess-number",
        "login-user", "login-user-popup"}
    assert surface["pages_usable"] == 123


def test_most_pages_have_nothing_to_type_at_all():
    """84 of 123 pages have no typeable field. The operand-typing framework cannot reach them,
    which is why 'add another value operator' was never going to be the coverage fix."""
    surface = _receipt()["declared_surface"]
    assert surface["pages_with_no_typeable_field"] == 84
    assert surface["pages_with_a_typeable_field"] == 39
    assert surface["input_type_counts"]["text"] == 37


def test_no_class_holds_more_than_six_pages():
    """The shape of the remainder: sixteen classes, largest six. No single bottleneck."""
    tax = _receipt()["taxonomy"]
    assert tax["pages_unsolved"] == 46
    assert tax["classes"] == 16
    assert tax["largest_class"] == 6
    assert max(v["n"] for v in tax["by_class"].values()) == 6


def test_no_page_is_unclassified():
    """Every unsolved page is accounted for; the three jsdom-refused pages are read from their
    own HTML rather than dropped."""
    tax = _receipt()["taxonomy"]
    assert "UNCLASSIFIED" not in tax["by_class"], tax["by_class"].get("UNCLASSIFIED")
    assert sum(v["n"] for v in tax["by_class"].values()) == tax["pages_unsolved"]
    read_from_html = {"bisect-angle", "hover-shape", "moving-items"}
    classified = {p for v in tax["by_class"].values() for p in v["pages"]}
    assert read_from_html <= classified


def test_an_instrument_failure_does_not_become_a_finding():
    """jsdom refused three pages. Their instruction is read from the page file, so the taxonomy
    never reports 'unclassified because the bridge failed'."""
    assert set(census.FROM_HTML) == {"bisect-angle", "hover-shape", "moving-items"}
    assert census.classify(census.FROM_HTML["hover-shape"])["class"] == "A_PERCEPTUAL_PROPERTY"
    assert census.classify(census.FROM_HTML["bisect-angle"])["class"] == "A_GEOMETRIC_CONSTRUCTION"


def test_text_is_not_a_declared_format():
    """`text` declares nothing. If it were counted as declaring a format, the surface would read
    43 instead of 6 and a useless lever would look useful."""
    assert "text" not in census.DECLARING_INPUT_TYPES
    assert {"date", "time", "number"} <= census.DECLARING_INPUT_TYPES


def test_the_taxonomy_is_reproducible_from_the_pages():
    """Re-deriving from the stored rows must give the same counts as the stored summary."""
    receipt = _receipt()
    again = census.taxonomy({"pages": _pages_as_measured()}, receipt["census_rows"])
    assert again["pages_unsolved"] == receipt["taxonomy"]["pages_unsolved"]
    assert again["largest_class"] == receipt["taxonomy"]["largest_class"]


def _pages_as_measured():
    """Rebuild the minimal page list the taxonomy needs from this session's own record.

    The full-suite receipt carries every page; the ones the union hand solved are the complement
    of the stored taxonomy, so this reconstructs them without re-running Chromium.
    """
    stored = _receipt()["taxonomy"]
    unsolved = {p for v in stored["by_class"].values() for p in v["pages"]}
    return [{"task": t, "arms": {"U_union": {"pass": t not in unsolved}}} for t in sorted(unsolved)]


def test_a_page_classified_by_its_hardest_need():
    """`choose-date` has no typeable field but does not need a point: the date is derivable and
    the cell must be found. Classifying by 'has a field' would have said POINT and built the
    wrong part."""
    row = {r["task"]: r for r in _receipt()["taxonomy"]["rows"]}
    assert row["choose-date"]["typeable_fields"] == 0
    assert row["choose-date"]["class"] == "A_TIME_PLACED_ON_A_GRID"
    assert row["hot-cold"]["class"] == "A_POINT_NOT_AN_ELEMENT"


def test_the_rule_fires_on_the_phrase_not_the_task():
    """The mechanism of non-transfer, demonstrated rather than argued.

    Same page, same text on it, same field to type into -- only the instruction's WORDS change.
    The rule stops firing and the correct value disappears. That is why a gain on the eight design
    pages cannot appear on a ninth: the trigger is the phrasing the author read, so a page that
    phrases the identical task differently is a page the algebra has never seen.

    This needs the real page files and the jsdom bridge. It is skipped, not faked, when they are
    absent -- an instrument that is not installed must never be reported as a passing result.
    """
    import copy
    import pathlib as _p
    html = _p.Path("/tmp/miniwob-plusplus/miniwob/html")
    mods = _p.Path("/tmp/mw/node_modules")
    if not html.is_dir() or not mods.is_dir():
        import pytest
        pytest.skip("MiniWoB pages and jsdom are not installed in this sandbox")

    from canonical.tools import miniwob_one_success_generalisation_measure_v1 as tool
    from canonical.runtime import derived_value_v1 as dv

    bridge = tool.Bridge(str(html), str(mods), substrate="jsdom")
    try:
        bridge.load("scroll-text")
        observation = bridge.reset(seed=1060)
        real = [row["rule"] for row in dv.derivations(observation)]
        assert "LAST_WORD" in real, real

        reworded = copy.deepcopy(observation)
        reworded["utterance"] = ("Extract the final token of the text area, put it into the text "
                                 "field and press Submit.")
        after = [row["rule"] for row in dv.derivations(reworded)]
        assert "LAST_WORD" not in after, (
            f"the rule survived a rewording: {after} -- if this ever holds, the trigger is not the "
            "phrase and the transfer story in the receipt needs rewriting")
    finally:
        bridge.close()
