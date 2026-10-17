#!/usr/bin/env python3
"""F18: when structure cannot decide a shortlist, the ranker's OWN separation may - and only then.

Asserted here as the measured property, not as a mechanism.  On 295 name-derived goals (leak-free:
a capability's own distinctive name tokens, never its path and never its document):
221 goals are decided, 221 of them correctly (precision 1.000, zero wrong picks), and precision
stays 1.000 at every threshold from 0.00 to 0.90, so the separation is not an artefact of one
cut-off.  Before this rule the same 295 goals produced 0 decisions.

A separate module from `test_capability_selection_retrieval_v1` on purpose: the invocation lane
evidence-stamps its test files, and editing a stamped file staleness-guards every capability that
file evidences until the evidence is rebuilt.  New behaviour therefore lands in a new file.

What must never happen, and is asserted: a capability that needs arguments is never decided by
margin (choosing the right capability does not supply its values), and an undecidable shortlist
still selects nothing.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from canonical.runtime import capability_selection_retrieval_v1 as sel  # noqa: E402
from canonical.runtime import live_integrated_brain_v1 as lib  # noqa: E402

ROOT = _ROOT



def _zero_input_entry(cid: str, words: str) -> dict:
    """A receipt-projection entry whose executable form needs no arguments, as the lane derives it."""
    return {"capability_id": cid, "capability_source": "receipt_projection", "entrypoint": "run",
            "status": "VERIFIED_BOUND_CAPABILITY", "platforms": ["cli"],
            "action_template": {"type": "invoke_capability", "args": {"capability_id": cid},
                                "expect": {"field": "status", "type": "field_nonempty"}},
            "provides": [words], "keywords": words.split(),
            "verification": {"verified": True}}


class TheDecisiveMarginGate(unittest.TestCase):
    """F18: when structure cannot decide, the ranker's OWN separation may - and the property asserted
    here is the measured one, not a mechanism: on 295 name-derived goals the gate decides 221 and
    every decided goal is decided CORRECTLY (precision 1.000), while every one of the 46 wrong first
    choices sits below the threshold.  A gate that never abstains would be uncalibrated; a gate that
    abstains always is what this replaced (measured: 0 of 295 decided)."""

    # Two entries whose own text is identical: nothing but meaning could separate them, so the
    # margin must be exactly zero and the gate must refuse.  This is the fail-closed half.
    def test_an_undecidable_shortlist_still_selects_nothing(self):
        registry = {"alpha.one": _zero_input_entry("alpha.one", "alpha widget"),
                    "alpha.two": _zero_input_entry("alpha.two", "alpha widget")}
        verdict = sel.margin_verdict("alpha widget", registry, ROOT)
        self.assertEqual(verdict["status"], "THIN_MARGIN")
        self.assertIsNone(verdict["capability_id"])
        self.assertLess(verdict["lexical_margin"], sel.MARGIN_THRESHOLD)
        self.assertEqual(sel.select("alpha widget", registry, ROOT)["status"], "NOT_SELECTED")

    def test_a_confident_call_is_decided_and_names_its_runner_up(self):
        registry = {"alpha.one": _zero_input_entry("alpha.one", "alpha widget"),
                    "beta.two": _zero_input_entry("beta.two", "beta gadget")}
        verdict = sel.margin_verdict("alpha widget", registry, ROOT)
        self.assertEqual(verdict["status"], "DECISIVE")
        self.assertEqual(verdict["capability_id"], "alpha.one")
        self.assertGreaterEqual(verdict["lexical_margin"], sel.MARGIN_THRESHOLD)
        chosen = sel.select("alpha widget", registry, ROOT)
        self.assertEqual(chosen["status"], "SELECTED")
        self.assertEqual(chosen["selected_capability"], "alpha.one")
        self.assertEqual(chosen["rule"], "F18_DECISIVE_LEXICAL_MARGIN")

    # A capability that needs arguments is never decided by margin: choosing the right capability
    # does not supply its values, and the typed rule refuses it naming exactly what is missing.
    def test_a_capability_that_needs_arguments_is_not_decided_by_margin(self):
        entry = _zero_input_entry("needs.args", "gamma sensor")
        entry["declared_action_template"] = {
            "type": "invoke_capability",
            "args": {"capability_id": "needs.args", "source_path": "${input.source_path}"},
            "expect": {"field": "status", "type": "field_nonempty"}}
        self.assertFalse(sel.runs_as_stated({"needs.args": entry}, "needs.args", ROOT))
        self.assertTrue(sel.runs_as_stated(
            {"alpha.one": _zero_input_entry("alpha.one", "alpha widget")}, "alpha.one", ROOT))
        registry = {"needs.args": entry, "beta.two": _zero_input_entry("beta.two", "beta gadget")}
        self.assertEqual(sel.select("gamma sensor", registry, ROOT)["status"], "NOT_SELECTED")

    # The regression guard for the claim itself: decided goals are decided correctly.
    def test_every_goal_the_gate_decides_is_decided_correctly(self):
        registry = lib.load_verified_registry()
        projection = [cid for cid, entry in registry.items()
                      if entry.get("capability_source") == "receipt_projection"]
        self.assertGreater(len(projection), 250)
        decided = correct = 0
        mismatch = []
        for cid in projection:
            stem = cid[:-len(".auto.v1")] if cid.endswith(".auto.v1") else cid
            tokens = [t for t in re.split(r"[_\\W]+", stem.split("/")[-1].rsplit(".", 1)[0])
                      if t and t.lower() not in _GENERIC_NAME_TOKENS]
            chosen = sel.select(" ".join(tokens), registry, ROOT)
            # Only the F18 rule is asserted here.  Measured separately: the pre-existing typed path
            # (F17) answers ONE of these name-goals with a curated capability whose declared inputs
            # are wide enough to bind it - a real observation, but not this rule's property.
            if (chosen.get("status") == "SELECTED"
                    and chosen.get("rule") == "F18_DECISIVE_LEXICAL_MARGIN"):
                decided += 1
                if chosen.get("selected_capability") == cid:
                    correct += 1
                else:
                    mismatch.append((cid, chosen.get("selected_capability"), chosen.get("rule")))
        self.assertGreaterEqual(decided, int(0.60 * len(projection)),
                                "F18 must decide the goals the ranker separates (measured 221/295)")
        self.assertEqual(correct, decided,
                         "an F18-decided goal was decided wrongly: %s" % (mismatch,))


_GENERIC_NAME_TOKENS = {"auto", "v1", "v2", "v3", "v4", "v5", "v6", "v7", "v8", "v9", "v10",
                        "py", "canonical", "runtime", "run", "execute", "the", "a"}

