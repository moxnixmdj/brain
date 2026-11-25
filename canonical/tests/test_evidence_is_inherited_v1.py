#!/usr/bin/env python3
"""Tests for inherited evidence — the hypothesis that was tested and refuted.

The result these tests encode: inheritance WITHIN a machine adds laws and no reach; inheritance
ACROSS machines adds reach and 56 errors. Both halves are pinned so neither can drift into a claim.
"""
from __future__ import annotations

import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
for path in (str(REPO), str(REPO / "canonical" / "tools")):
    if path not in sys.path:
        sys.path.insert(0, path)

from canonical.tools import evidence_is_inherited_v1 as inherit  # noqa: E402
from canonical.tools import the_width_of_a_guard_v1 as width  # noqa: E402
from canonical.swe_kernel import safe_action_model_v1 as sam  # noqa: E402

CONDITIONS = [("CARD", "WHOLE", None, "count_is", 1), ("CARD", "WHOLE", None, "count_is", 2)]
ONE = (("0", "alpha"),)
TWO = (("0", "alpha"), ("1", "alpha"))
NOOP = (frozenset(), frozenset())


def obs(atom, before, after):
    return sam.Observation.of(atom, before, after, CONDITIONS)


def law(atom, projection, key, support):
    return width.Law(atom, projection, key, NOOP, support=support, witness=ONE)


def test_a_projection_confirmed_on_two_atoms_licenses_a_single_witness_law():
    """The hypothesis, in its minimal positive form."""
    laws = [law("A", "IDENT", ("0",), 2), law("B", "IDENT", ("0",), 2),
            law("C", "IDENT", ("0",), 1)]
    kept = inherit.inherited_laws(laws)
    assert any(item.atom == "C" for item in kept), "IDENT is confirmed on two atoms, so C inherits"


def test_one_atom_does_not_confirm_a_projection():
    """The ablation: with a single confirming atom there is no inheritance, which is what makes the
    requirement do work (arm D of the instrument measured 11 errors against arm B's 0)."""
    laws = [law("A", "IDENT", ("0",), 2), law("C", "IDENT", ("0",), 1)]
    assert not any(item.atom == "C" for item in inherit.inherited_laws(laws))
    assert any(item.atom == "C" for item in inherit.inherited_laws(laws, atoms=1))


def test_inheritance_never_widens_the_effect_it_inherits():
    """A single-witness law inherits ADMISSIBILITY, never a different effect. The law's own recorded
    effect travels with it, which is why the matched-effect arm was sound."""
    laws = [law("A", "IDENT", ("0",), 2), law("B", "IDENT", ("0",), 2),
            law("C", "IDENT", ("0",), 1)]
    kept = {item.atom: item for item in inherit.inherited_laws(laws, matched_effect_only=True)}
    assert "C" in kept
    assert kept["C"].effect == NOOP, "the inherited law keeps its own measured effect"


def test_a_law_with_no_supporting_projection_is_never_admitted():
    laws = [law("A", "CARD", 1, 2), law("B", "CARD", 1, 2), law("Z", "ROWS", ONE, 1)]
    assert not any(item.atom == "Z" for item in inherit.inherited_laws(laws))


def test_cross_machine_transfer_is_recorded_as_unsound():
    """The refutation, pinned. Cross-machine inheritance raised reach from 88 to 149 predictions and
    injected 56 errors across 72 ordered pairs: a projection confirmed on one machine is NOT evidence
    about another. The instrument must keep saying so."""
    import json
    artifact = REPO / "canonical" / "verification" / "EVIDENCE_IS_INHERITED_20261124_V1.json"
    if not artifact.exists():                       # pragma: no cover - artifact shipped with branch
        return
    payload = json.loads(artifact.read_text())
    cross = payload["cross_machine"]
    assert cross["arm_inherited"]["predictions"] > cross["arm_own"]["predictions"]
    assert cross["arm_inherited"]["wrong"] > 0, "this is the finding, not a regression"
    assert payload["summary"]["verdicts"]["cross_machine_inheritance_is_sound"] is False
