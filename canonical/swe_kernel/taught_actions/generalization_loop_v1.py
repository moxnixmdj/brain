#!/usr/bin/env python3
"""Candidate-rule settlement from one showing; a narrow experiment, not a solution.

Measured 2026-11-12 on one synthetic Python edit family: `edit_by_example_v1.wider()`
can produce a rule that transforms four target shapes, but can also over-generalize
(e.g. changing `* 2` to `* 3`). Neither candidate agreement nor the absence of a wider
reading proves that an edit is correct or applicable.

This module computes literal and wider candidates. It returns no admitted edit without
an oracle. With an oracle, it asks about the wider candidate first, falls back to the
literal candidate after contradiction, and refuses if no candidate is confirmed. The
oracle is trusted input (`oracle(target_text, edited_text) -> bool`); a weak or scripted
predicate cannot establish real-world correctness. No file is written or executed here.

This is a candidate-selection helper for one operator family, not generalization across
arbitrary coding or computer-use tasks. Authority NONE; zero model dependency; $0 spend;
`truth.achieved` stays false.
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
REFUSE_UNVERIFIED = "REFUSE_UNVERIFIED"
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

    # No wider reading: the literal candidate is the only hypothesis, not a verified edit.
    if not readings:
        if literal_text is None:
            return {
                "action": REFUSED_SHAPE,
                "why": "no wider reading exists and the literal rule has no fitting place in the target",
                "rule_descriptions": [str(r) for r in rules],
                "wider_descriptions": [],
                "edited_text": None,
                "candidate_text": None,
                "probes_asked": [],
                "terminal_authority": False,
            }
        if oracle is None:
            return {
                "action": REFUSE_UNVERIFIED,
                "why": "the literal candidate is maximally general but no oracle verified its correctness",
                "rule_descriptions": [str(r) for r in rules],
                "wider_descriptions": [],
                "edited_text": None,
                "candidate_text": literal_text,
                "probes_asked": [],
                "terminal_authority": False,
            }
        if oracle(target_text, literal_text):
            return {
                "action": ADMIT_LITERAL_MAXIMAL,
                "why": "no wider reading exists and the oracle confirmed the literal candidate",
                "rule_descriptions": [str(r) for r in rules],
                "wider_descriptions": [],
                "edited_text": literal_text,
                "candidate_text": literal_text,
                "probes_asked": ["literal"],
                "terminal_authority": False,
            }
        return {
            "action": REFUSE_NEITHER_CONFIRMED,
            "why": "the oracle rejected the only available literal candidate",
            "rule_descriptions": [str(r) for r in rules],
            "wider_descriptions": [],
            "edited_text": None,
            "candidate_text": literal_text,
            "probes_asked": ["literal"],
            "terminal_authority": False,
        }

    wider_text = _try_apply(readings, target_text)

    # Agreement resolves which hypothesis to ask about, not whether it is correct.
    if literal_text == wider_text:
        if literal_text is None:
            return {
                "action": REFUSED_SHAPE,
                "why": "neither the literal nor the wider rule has a fitting place in the target",
                "rule_descriptions": [str(r) for r in rules],
                "wider_descriptions": [str(r) for r in readings],
                "edited_text": None,
                "candidate_text": None,
                "probes_asked": [],
                "terminal_authority": False,
            }
        if oracle is None:
            return {
                "action": REFUSE_UNVERIFIED,
                "why": "literal and wider agree, but agreement does not verify the candidate; no oracle was given",
                "rule_descriptions": [str(r) for r in rules],
                "wider_descriptions": [str(r) for r in readings],
                "edited_text": None,
                "candidate_text": literal_text,
                "probes_asked": [],
                "terminal_authority": False,
            }
        if oracle(target_text, literal_text):
            return {
                "action": ADMIT_AGREEMENT,
                "why": "literal and wider agree and the oracle confirmed their shared candidate",
                "rule_descriptions": [str(r) for r in rules],
                "wider_descriptions": [str(r) for r in readings],
                "edited_text": literal_text,
                "candidate_text": literal_text,
                "probes_asked": ["agreement"],
                "terminal_authority": False,
            }
        return {
            "action": REFUSE_NEITHER_CONFIRMED,
            "why": "the oracle rejected the candidate on which literal and wider agree",
            "rule_descriptions": [str(r) for r in rules],
            "wider_descriptions": [str(r) for r in readings],
            "edited_text": None,
            "candidate_text": literal_text,
            "probes_asked": ["agreement"],
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
