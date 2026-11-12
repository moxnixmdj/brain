#!/usr/bin/env python3
"""Automatic generalization from one showing, settled by evidence.

Why this exists
---------------
Measured 2026-11-12 (`ONE_SHOWING_IS_LITERAL_TWO_SHOWINGS_ARE_GENERAL_20261112_V1.md`):
one showing gives a literal rule (`product == None -> product is None`, 1/4 unseen sites);
two showings give a general rule (`?1 == None -> ?1 is None`, 4/4). The gap is not the
mechanism -- `edit_by_example_v1.wider()` already computes the generalization candidate
from one showing -- it is that nothing uses it automatically or safely:

* literal is too narrow: refuses valid generalizations (`invoice.paid == None`);
* wider is too broad: fires where it should not (`pairs(n) = n * 2` -> `n * 3`);
* neither is automatically correct, and the system waits for the user to provide a
  second showing instead of settling the question itself.

This module closes that gap. From one showing it computes both hypotheses --
**literal** (exact) and **wider** (generalized) -- applies both to the target, and:

1. **Agreement** (both produce the same edit, or both refuse) -> admit, no question.
2. **No wider reading exists** -> literal is maximal; apply it directly.
3. **Disagreement, no oracle** -> refuse, fail closed; the disagreement is recorded
   as the questions worth asking.
4. **Disagreement, oracle present** -> ask the oracle about the wider edit first
   (the generalization hypothesis). Admit wider on confirmation; fall back to
   literal on contradiction; refuse when neither is confirmed.

The oracle is the minimum question interface: `oracle(target_text, edited_text) -> bool`,
"is this edit correct?" It is whatever can answer that -- a test, a teacher, a spec.
One question settles the generalization; the asymmetric protocol (admit on confirmation,
refuse on contradiction) is the same discipline as `settled_admission_v1`, applied to
the rule question instead of the target question.

Authority NONE. Zero model dependency. $0 spend. `truth.achieved` stays false.
"""
from __future__ import annotations

from typing import Any, Callable

from canonical.swe_kernel.taught_actions import edit_by_example_v1 as ebe

# Actions
ADMIT_AGREEMENT = "ADMIT_AGREEMENT"
ADMIT_LITERAL_MAXIMAL = "ADMIT_LITERAL_MAXIMAL"
ADMIT_WIDER_SETTLED = "ADMIT_WIDER_SETTLED"
ADMIT_LITERAL_SETTLED = "ADMIT_LITERAL_SETTLED"
REFUSE_UNSETTLED = "REFUSE_UNSETTLED"
REFUSE_NEITHER_CONFIRMED = "REFUSE_NEITHER_CONFIRMED"
REFUSED_SHAPE = "REFUSED_SHAPE"

Oracle = Callable[[str, str], bool]


def _try_apply(rules: list, target: str) -> str | None:
    """Apply rules to target; None when the learner refuses (no fitting place)."""
    try:
        return ebe.repeated(rules, target, "the example")
    except ebe.Refused:
        return None


def settle_generalization(
    before_text: str,
    after_text: str,
    target_text: str,
    *,
    oracle: Oracle | None = None,
) -> dict[str, Any]:
    """Generalize from one showing and settle the generalization on the target.

    Returns a JSON-safe dict. `action` is one of the module's action constants.
    `edited_text` is present only when an edit is admitted. `ebe.Refused` from the
    demonstration itself (unlearnable change) propagates unchanged: a lesson that
    cannot be learned at all is the caller's error, not a settlement decision.
    """
    rules, readings = ebe.learn_all([(before_text, after_text)], wide=True)

    literal_text = _try_apply(rules, target_text)

    # No wider reading: literal is already maximally general.
    if not readings:
        if literal_text is None:
            return {
                "action": REFUSED_SHAPE,
                "why": "no wider reading exists and the literal rule has no fitting place in the target",
                "rule_descriptions": [str(r) for r in rules],
                "wider_descriptions": [],
                "edited_text": None,
                "probes_asked": [],
                "terminal_authority": False,
            }
        return {
            "action": ADMIT_LITERAL_MAXIMAL,
            "why": "no wider reading exists; the literal rule is maximally general and fits the target",
            "rule_descriptions": [str(r) for r in rules],
            "wider_descriptions": [],
            "edited_text": literal_text,
            "probes_asked": [],
            "terminal_authority": False,
        }

    wider_text = _try_apply(readings, target_text)

    # Agreement: both hypotheses produce the same edit (or both refuse).
    if literal_text == wider_text:
        if literal_text is None:
            return {
                "action": REFUSED_SHAPE,
                "why": "neither the literal nor the wider rule has a fitting place in the target",
                "rule_descriptions": [str(r) for r in rules],
                "wider_descriptions": [str(r) for r in readings],
                "edited_text": None,
                "probes_asked": [],
                "terminal_authority": False,
            }
        return {
            "action": ADMIT_AGREEMENT,
            "why": "literal and wider agree on the target; no generalization question arises",
            "rule_descriptions": [str(r) for r in rules],
            "wider_descriptions": [str(r) for r in readings],
            "edited_text": literal_text,
            "probes_asked": [],
            "terminal_authority": False,
        }

    # Disagreement: the version space is {literal, wider}. Settle it.
    if oracle is None:
        return {
            "action": REFUSE_UNSETTLED,
            "why": "literal and wider disagree on the target and no oracle was given to settle them; "
                   "admitting either would bank a guess. Fail closed.",
            "rule_descriptions": [str(r) for r in rules],
            "wider_descriptions": [str(r) for r in readings],
            "edited_text": None,
            "probes_asked": [],
            "literal_text": literal_text,
            "wider_text": wider_text,
            "terminal_authority": False,
        }

    probes_asked: list[str] = []

    # Ask about the wider edit first: it is the generalization hypothesis.
    if wider_text is not None:
        probes_asked.append("wider")
        if oracle(target_text, wider_text):
            return {
                "action": ADMIT_WIDER_SETTLED,
                "why": "the oracle confirmed the wider (generalized) edit; the generalization transfers",
                "rule_descriptions": [str(r) for r in rules],
                "wider_descriptions": [str(r) for r in readings],
                "edited_text": wider_text,
                "probes_asked": probes_asked,
                "terminal_authority": False,
            }

    # Wider contradicted (or absent): fall back to literal.
    if literal_text is not None:
        probes_asked.append("literal")
        if oracle(target_text, literal_text):
            return {
                "action": ADMIT_LITERAL_SETTLED,
                "why": "the oracle contradicted the wider edit but confirmed the literal edit; "
                       "the generalization does not transfer to this target",
                "rule_descriptions": [str(r) for r in rules],
                "wider_descriptions": [str(r) for r in readings],
                "edited_text": literal_text,
                "probes_asked": probes_asked,
                "terminal_authority": False,
            }

    return {
        "action": REFUSE_NEITHER_CONFIRMED,
        "why": "the oracle confirmed neither the wider nor the literal edit; refusing both",
        "rule_descriptions": [str(r) for r in rules],
        "wider_descriptions": [str(r) for r in readings],
        "edited_text": None,
        "probes_asked": probes_asked,
        "terminal_authority": False,
    }
