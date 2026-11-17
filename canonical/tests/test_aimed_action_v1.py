"""The aimed-action algebra: places derived from structure and instruction words, their rules,
the decoy control, and the hand's three new point actions through the shared harness."""
from __future__ import annotations

import sys
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from canonical.runtime import aimed_action_v1 as aimed  # noqa: E402
from canonical.tools import aimed_action_measure_v1 as measure  # noqa: E402
from canonical.tools import miniwob_one_success_generalisation_measure_v1 as tool  # noqa: E402


def element(index: int, parent: int, tag: str, **kw):
    rec = {"index": index, "parent": parent, "tag": tag, "text": "",
           "box": [0, 0, 10, 10], "can_click": False, "can_type": False}
    rec.update(kw)
    return rec


def circle_observation():
    return {
        "utterance": "Find and click on the center of the circle, then press submit.",
        "elements": [
            element(0, -1, "body", box=[0, 0, 480, 360]),
            element(1, 0, "svg", id="svg-grid", box=[2, 52, 150, 130]),
            element(2, 1, "circle", classes="black-circle", colour="white",
                    box=[24, 83, 74, 74], can_click=True),
            element(3, 0, "button", text="Submit", box=[30, 175, 98, 34], can_click=True),
        ]}


def slider_observation():
    return {
        "utterance": "Select 108 with the slider and hit Submit.",
        "elements": [
            element(0, -1, "body", box=[0, 0, 480, 360]),
            element(1, 0, "div", id="slider", box=[10, 60, 115, 18]),
            element(2, 1, "a", classes="ui-slider-handle", role="slider",
                    **{"aria-valuemin": "0", "aria-valuemax": "150", "aria-valuenow": "30"},
                    box=[36, 54, 16, 26], can_click=True),
            element(3, 0, "button", text="Submit", box=[10, 120, 80, 30], can_click=True),
        ]}


def test_centre_of_the_circle_is_the_box_centre():
    actions = aimed.aimed_actions(circle_observation())
    assert "pressat@61.0,120.0" in actions
    rule = aimed.rule_of(circle_observation(), "pressat@61.0,120.0")
    assert rule["rule"] == "CENTER_OF"
    assert rule["witness"]["element"] == 2


def test_slider_value_maps_through_aria_bounds():
    actions = aimed.aimed_actions(slider_observation())
    point = next(a for a in actions if a.startswith("pressat@"))
    x = float(point.split("@")[1].split(",")[0])
    # 108 of 150 along a track from x=10 width 115 -> 10 + 0.72*115 = 92.8
    assert x == pytest.approx(92.8, abs=0.2)


def test_ordinal_widgets_and_the_value_paired_with_the_field():
    observation = {
        "utterance": 'Check the 3rd radio button and enter the number "10" into the 2nd textbox.',
        "elements": [
            element(i, 0, "input", type=("radio" if i < 3 else "text"),
                    box=[10, 20 + 30 * i, 12, 12], can_click=(i < 3), can_type=(i >= 3), value="")
            for i in range(5)]}
    actions = aimed.aimed_actions(observation)
    assert "click@2" in actions            # the 3rd radio
    assert "type@4=10" in actions          # the 2nd textbox, the quoted value
    assert aimed.rule_of(observation, "type@4=10")["rule"] == "ORDINAL_FIELD_VALUE"


def test_date_cell_prefers_the_month_the_instruction_names():
    observation = {
        "utterance": "Select 11/10/2016 as the date and hit submit.",
        "elements": [
            element(0, -1, "table", box=[0, 0, 400, 300]),
            element(1, 0, "div", text="November", box=[0, 0, 200, 20]),
            element(2, 1, "td", text="10", box=[10, 40, 30, 20], can_click=True),
            element(3, 0, "div", text="December", box=[200, 0, 200, 20]),
            element(4, 3, "td", text="10", box=[210, 40, 30, 20], can_click=True)]}
    actions = aimed.aimed_actions(observation)
    first = aimed.rule_of(observation, actions[0])
    assert first["rule"] == "DATE_CELL"
    assert first["witness"]["element"] == 2          # the November cell, not December's
    assert first["witness"]["month_named"] is True


def test_shortest_flight_is_the_row_with_the_smallest_duration():
    observation = {
        "utterance": "Book the shortest one-way flight from: A to: B on 12/06/2016.",
        "elements": [
            element(0, -1, "table", box=[0, 0, 400, 300]),
            element(1, 0, "tr", box=[0, 20, 400, 24]),
            element(2, 1, "td", text="09:00", box=[0, 20, 80, 24], can_click=True),
            element(3, 1, "td", text="14:30", box=[80, 20, 80, 24], can_click=True),
            element(4, 0, "tr", box=[0, 50, 400, 24]),
            element(5, 4, "td", text="10:00", box=[0, 50, 80, 24], can_click=True),
            element(6, 4, "td", text="12:15", box=[80, 50, 80, 24], can_click=True)]}
    actions = aimed.aimed_actions(observation)
    assert "click@5" in actions and "click@6" in actions
    assert "click@2" not in actions
    witness = aimed.rule_of(observation, "click@5")["witness"]
    assert witness["measure"] == "dur" and witness["value"] == pytest.approx(2.25)


def test_odd_and_even_are_chosen_by_the_row_and_the_column():
    observation = {
        "utterance": "Mark the numbers below as odd or even and press submit when done.",
        "elements": [
            element(0, -1, "div", box=[0, 0, 400, 400]),
            element(1, 0, "td", text="odd", box=[60, 10, 40, 20]),
            element(2, 0, "td", text="even", box=[140, 10, 40, 20]),
            element(3, 0, "td", text="7", box=[0, 40, 40, 20]),
            element(4, 0, "input", type="radio", box=[62, 40, 14, 14], can_click=True),
            element(5, 0, "input", type="radio", box=[142, 40, 14, 14], can_click=True),
            element(6, 0, "td", text="8", box=[0, 70, 40, 20]),
            element(7, 0, "input", type="radio", box=[62, 70, 14, 14], can_click=True),
            element(8, 0, "input", type="radio", box=[142, 70, 14, 14], can_click=True)]}
    actions = aimed.aimed_actions(observation)
    assert "click@4" in actions   # 7 is odd -> the odd column, first number's row
    assert "click@8" in actions   # 8 is even -> the even column, second number's row
    assert aimed.rule_of(observation, "click@4")["witness"]["marks"] == "odd"


def test_nth_word_and_count_are_arithmetic_over_the_page():
    observation = {
        "utterance": "Find the 5th word in the paragraph, type that into the textbox and press \"Submit\".",
        "elements": [
            element(0, -1, "body", box=[0, 0, 480, 360]),
            element(1, 0, "div", text="alpha beta gamma delta epsilon zeta", box=[0, 0, 300, 60]),
            element(2, 0, "input", type="text", can_type=True, box=[0, 80, 200, 20], value="")]}
    assert "type@2=epsilon" in aimed.aimed_actions(observation)
    counting = {
        "utterance": "Type the total number of blocks into the textbox and press Submit.",
        "elements": [element(0, -1, "body", box=[0, 0, 480, 360])]
        + [element(1 + i, 0, "div", classes="block", box=[10 + 30 * i, 40, 24, 24]) for i in range(6)]
        + [element(20, 0, "input", type="text", can_type=True, box=[0, 90, 120, 20], value="")]}
    assert "type@20=6" in aimed.aimed_actions(counting)


def test_records_matching_every_instruction_word_are_the_rows_to_press():
    observation = {
        "utterance": "Search for thriller movies directed by George from year 1994.",
        "elements": [element(0, -1, "div", box=[0, 0, 480, 360])]
        + [element(1 + i, 0, "li", text=text, full_text=text, box=[0, 30 * i, 400, 28],
                   can_click=True)
           for i, text in enumerate(
               ["Comedy by Amy 1999", "Thriller by George 1994", "Drama by George 1994"])]}
    actions = aimed.aimed_actions(observation)
    assert actions == ["click@2"]
    assert set(aimed.rule_of(observation, "click@2")["witness"]["words"]) >= {"thriller", "george"}


def test_colour_wheel_is_an_ordered_ring_of_points():
    observation = {
        "utterance": "Select magenta with the color picker and hit Submit.",
        "elements": [
            element(0, -1, "body", box=[0, 0, 480, 360]),
            element(1, 0, "svg", classes="colorwheel", box=[100, 60, 200, 200], can_click=True)]}
    actions = [a for a in aimed.aimed_actions(observation) if a.startswith("pressat@")]
    assert len(actions) == 16
    first = aimed.rule_of(observation, actions[0])["witness"]
    assert first["wanted_hue"] == pytest.approx(300)   # magenta first, not an arbitrary angle


def test_move_on_target_when_the_instruction_holds_the_pointer_there():
    observation = {
        "utterance": "Keep your mouse inside the circle as it moves around.",
        "elements": [
            element(0, -1, "body", box=[0, 0, 480, 360]),
            element(1, 0, "circle", classes="moving-circle", box=[200, 150, 30, 30], can_click=True)]}
    actions = aimed.aimed_actions(observation)
    assert actions == ["moveat@215.0,165.0"]


def test_while_holding_only_release_places_are_offered():
    observation = {
        "utterance": "Draw a vertical line that runs through the dot, then press submit.",
        "holding": 1,
        "elements": [
            element(0, -1, "body", box=[0, 0, 480, 360]),
            element(1, 0, "circle", classes="dot", box=[100, 140, 8, 8], can_click=True)]}
    actions = aimed.aimed_actions(observation)
    assert actions and all(a.startswith("dropat@") for a in actions)
    assert not any(a.startswith(("pressat@", "moveat@", "click@", "type@")) for a in actions)


def test_decoy_has_the_same_count_shape_and_seed_is_deterministic():
    observation = circle_observation()
    real = aimed.aimed_actions(observation)
    decoy = aimed.decoy_actions(observation, seed=7)
    assert len(decoy) == len(real)
    for a, d in zip(real, decoy):
        assert a.partition("@")[0] == d.partition("@")[0]   # same shape, kind for kind
        assert a != d or a.startswith("click@")             # a random place, never the same place
    assert aimed.decoy_actions(observation, seed=7) == decoy
    assert aimed.decoy_actions(observation, seed=8) != decoy


def test_rule_of_roundtrip_and_no_crash_on_a_bare_page():
    observation = circle_observation()
    for action in aimed.aimed_actions(observation):
        assert aimed.rule_of(observation, action) is not None
    assert aimed.aimed_actions({"utterance": "", "elements": []}) == []
    assert aimed.rule_of({"utterance": "", "elements": []}, "pressat@1,1") is None


# ------------------------------------------------------------------ the hand's point actions


def test_point_actions_parse_price_and_replay_gate():
    parsed = tool.parse_action("pressat@12.5,40")
    assert parsed == {"type": "pressat", "x": 12.5, "y": 40.0}
    assert tool.parse_action("moveat@3,4")["type"] == "moveat"
    assert tool.parse_action("dropat@9,9")["type"] == "dropat"
    with pytest.raises(ValueError):
        tool.parse_action("pressat@nope,4")
    with pytest.raises(ValueError):
        tool.parse_action("pressat@nan,4")

    observation = circle_observation()
    assert tool.cannot_be_done(observation, parsed) is None      # a point needs no element
    holding = dict(observation, holding=2)
    assert tool.cannot_be_done(holding, {"type": "pressat", "x": 1, "y": 1}) is not None
    assert tool.cannot_be_done(holding, {"type": "dropat", "x": 1, "y": 1}) is None
    assert tool.cannot_be_done(observation, {"type": "dropat", "x": 1, "y": 1}) is not None

    prices = tool.GuidedPrices()
    assert prices(observation, "pressat@10,10") == (0, 2)
    assert prices(observation, "moveat@10,10") == (1, 2)


def test_aimed_arm_offers_shipped_plus_derived_and_decoy_is_control():
    observation = circle_observation()
    arm_a = measure.actions_arm(observation, "A_shipped_hand")
    arm_g = measure.actions_arm(observation, "G_aimed_hand")
    arm_d = measure.actions_arm(observation, "D_decoy_aimed")
    assert set(arm_a) <= set(arm_g)
    assert "pressat@61.0,120.0" in arm_g and "pressat@61.0,120.0" not in arm_a
    assert len(arm_d) == len(arm_g)
    assert "pressat@61.0,120.0" not in arm_d
    with pytest.raises(ValueError):
        measure.actions_arm(observation, "Z_unknown")


def test_aimed_prices_make_the_derivation_free_and_everything_else_untouched():
    observation = circle_observation()
    prices = measure.AimedPrices()
    assert prices(observation, "pressat@61.0,120.0") == (0, 0)
    named = next(a for a in tool.offered_actions(observation, tool.HAND_TIER)
                 if a.startswith("click@"))
    assert prices(observation, named) == tool.GuidedPrices()(observation, named)


def test_unsolved_pages_read_from_the_taxonomy_receipt():
    tasks = measure.unsolved_pages()
    assert len(tasks) == 46
    assert "circle-center" in tasks and "use-slider" in tasks and "visual-addition" in tasks


def test_rgb_and_hsl_colours_both_name_a_hue():
    # Chrome serialises inline colours to rgb(); a hue rule that only reads hsl never fires.
    assert aimed._colour_hue("rgb(0, 0, 255)") == pytest.approx(240.0, abs=0.5)
    assert aimed._colour_hue("hsl(120, 100%, 50%)") == pytest.approx(120.0, abs=0.5)
    assert aimed._colour_hue("purple") == pytest.approx(280.0, abs=0.5)
    assert aimed._colour_hue("not a colour") is None


def test_instructed_shades_press_every_span_that_paints_the_named_hue():
    observation = {
        "utterance": "Select all the shades of blue and press Submit.",
        "elements": [
            element(0, -1, "body", box=[0, 0, 480, 360]),
            element(1, 0, "span", box=[50, 60, 20, 20], can_click=True,
                    colour="rgb(0, 0, 255)"),
            element(2, 0, "span", box=[80, 60, 20, 20], can_click=True,
                    colour="hsl(240, 100%, 50%)"),
            element(3, 0, "span", box=[110, 60, 20, 20], can_click=True,
                    colour="rgb(255, 0, 0)"),
            element(4, 0, "button", text="Submit", box=[30, 175, 98, 34], can_click=True),
        ]}
    actions = aimed.aimed_actions(observation)
    for idx in (1, 2):
        assert f"click@{idx}" in actions
        assert aimed.rule_of(observation, f"click@{idx}")["rule"] == "CLICK_INSTRUCTED_SHADE"
    assert "click@3" not in actions          # red is not a shade of blue


def test_box_partition_frees_the_grabs_and_names_the_release():
    observation = {
        "utterance": ("Drag all rectangles into the left box and everything else into the "
                      "right box, then press Submit"),
        "holding": None,
        "elements": [
            element(0, -1, "body", box=[0, 0, 480, 360]),
            element(1, 0, "div", id="shape-container", box=[10, 80, 100, 60], can_click=True),
            element(2, 0, "div", id="shape-container", box=[360, 80, 100, 60], can_click=True),
            element(3, 0, "circle", box=[150, 90, 20, 20], can_click=True),
            element(4, 0, "rect", box=[200, 90, 30, 15], can_click=True),
            element(5, 0, "button", text="Submit", box=[30, 175, 98, 34], can_click=True),
        ]}
    actions = aimed.aimed_actions(observation)
    for idx in (3, 4):
        assert f"grab@{idx}" in actions
        assert aimed.rule_of(observation, f"grab@{idx}")["rule"] == "GRAB_FOR_BOX_PARTITION"
    held = dict(observation, holding=4)
    assert "dropat@60.0,110.0" in aimed.aimed_actions(held)
    assert aimed.rule_of(held, "dropat@60.0,110.0")["rule"] == "RELEASE_IN_INSTRUCTED_BOX"


def test_named_run_selection_gate_offers_gesture_then_style_only_when_selected():
    base = {
        "utterance": "give the text viverra. the style underlined and press Submit",
        "selection": "",
        "elements": [
            element(0, -1, "body", box=[0, 0, 480, 360]),
            element(1, 0, "p", text="Vestibulum duis velit viverra.",
                    box=[18, 92, 124, 37], can_click=True),
            element(2, 0, "button", text="underline", box=[60, 30, 40, 20], can_click=True),
            element(3, 0, "button", text="Submit", box=[30, 175, 98, 34], can_click=True),
        ]}
    clean = aimed.aimed_actions(base)
    assert "doubleat@150.3,103.1" in clean
    assert "dragat@14.0,117.9,150.0,117.9" in clean
    assert "click@2" not in clean            # no selection: the style button is not offered
    wrong = dict(base, selection="velit")
    wrong_actions = aimed.aimed_actions(wrong)
    assert wrong_actions[0] == "pressat@470.0,350.0"
    assert aimed.rule_of(wrong, "pressat@470.0,350.0")["rule"] == "CLEAR_A_WRONG_SELECTION"
    right = dict(base, selection="viverra.")
    right_actions = aimed.aimed_actions(right)
    assert "click@2" in right_actions
    assert aimed.rule_of(right, "click@2")["rule"] == "STYLE_CONTROL"
