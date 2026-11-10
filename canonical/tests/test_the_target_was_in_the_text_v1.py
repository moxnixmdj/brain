"""The addresser was blind to the majority of what it was looking at.

For four rounds I addressed by role + accessible NAME. A MiniWob checkbox, link, button or
option very often has NO accessible name at all: the label lives in a sibling StaticText node.
`ax_nodes` dropped StaticText as noise. So the agent could not see the word it was told to
click, on 13 of 16 sampled tasks, while that word was demonstrably on the screen.

    NAMES on click-collapsible-2 : ['Section #1', 'Section #2', 'Section #3']
    TEXT  on the same screen     : ['Section #1', 'Odio tortor facilisi arcu. Mus', 'Section #2']

With text nodes included and reveals allowed, 13/16 sampled targets are found, and EVERY hit
is a StaticText node.

Two measurement errors on the way here, both kept:

  v1  kept trailing punctuation in the literal ("lacus,") so true matches scored as misses
  v1  counted values-to-be-typed ("Leonie") as screen targets
  v2  counted the GOAL SENTENCE itself as a hit, because the instruction is rendered text
  v2  measured "names after revealing" instead of "names ever seen", and tab switching
      REPLACES content, so 3 -> 3 looked like nothing happened

The last one is the real lesson: the addressable set of a screen is temporal, not spatial.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
ROOT = pathlib.Path(__file__).resolve().parents[2]

FOUND = json.loads((ROOT / "canonical/evaluation/bench/find_in_text_v2.json").read_text())
ORD = json.loads((ROOT / "canonical/evaluation/bench/ordering_130_v2.json").read_text())


def test_every_hit_was_a_text_node_not_a_name():
    roles = {x["hit_role"] for x in FOUND if x["hit_role"]}
    assert roles == {"StaticText"}, roles


def test_most_targets_are_found_once_text_is_included():
    assert sum(1 for x in FOUND if x["found"]) == 13
    assert len(FOUND) == 16


def test_the_two_misses_are_a_different_problem():
    """click-dialog asks for 'x'; the control is a button named 'Close'. No string match can
    bridge action-vs-label. That is semantics, and it needs a model."""
    miss = {x["task"] for x in FOUND if not x["found"]}
    assert "click-dialog" in miss and "click-dialog-2" in miss


def test_addressing_without_text_is_the_older_blind_addresser():
    """The default must stay unchanged so the r71 result is still reproducible, and the
    text-blind behaviour is now a recorded limitation rather than an invisible one."""
    txt = (ROOT / "canonical/runtime/address_v1.py").read_text()
    assert "StaticText\" and not keep_text" in txt
    assert "def read_text" in txt


def test_the_ordering_measure_excluded_values_to_be_typed():
    targets = [r for r in ORD if r.get("literal") and not r.get("is_value_to_type")]
    values = [r for r in ORD if r.get("literal") and r.get("is_value_to_type")]
    assert len(values) == 8
    assert len(targets) == 28
    on = [r for r in targets if r["on_screen_at_t0"]]
    assert len(on) == 6, "name-based visibility at t0 was 6/28 = 21%"
