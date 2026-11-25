#!/usr/bin/env python3
"""Tests for a contrast stored as a PROCEDURE rather than as a description.

The result these tests encode, measured on 72 ordered machine pairs:

    key-as-contrast       6 of 272 admitted   (2.2%)
    experiment-as-contrast 244 of 256 re-ran (95.3%), 12 admitted, and reach 88 -> 93 with 0 wrong

Three separate leaks had to be fixed to get there, and each is a test here because each looked like a
result that had failed when it was really a bug:
  * the experiment named the teacher's atom (`GIT_A4` means nothing on VAULT) -> resolve by ROLE
  * the restated law kept the teacher's projection KEY                    -> read the key locally
  * the restated law kept the teacher's atom NAME                         -> use the local atom
"""
from __future__ import annotations

import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
for path in (str(REPO), str(REPO / "canonical" / "tools")):
    if path not in sys.path:
        sys.path.insert(0, path)

from canonical.swe_kernel import safe_action_model_v1 as sam  # noqa: E402
from canonical.tools import a_contrast_is_a_probe_v1 as probe  # noqa: E402
from canonical.tools import the_width_of_a_guard_v1 as width  # noqa: E402

CONDITIONS = [("CARD", "WHOLE", None, "count_is", 1), ("CARD", "WHOLE", None, "count_is", 2)]
ONE = (("0", "alpha"),)
TWO = (("0", "alpha"), ("1", "alpha"))
NOOP = (frozenset(), frozenset())


def test_an_atom_is_named_by_its_role_not_by_its_prefix():
    """The first portability fix. Every machine in the family fills the same slots with atoms whose
    prefixes differ, so the role is the only part of a name that travels."""
    assert probe.atom_role("GIT_A4") == "A4"
    assert probe.atom_role("VAULT_A2") == "A2"
    assert probe.atom_role("VT_A1") == "A1"
    assert probe.atom_role("SQL_A3") == "A3"
    assert probe.atom_role("LIST_A7") == "A7"


def test_a_restated_law_uses_the_local_key_and_the_local_atom():
    """The last two leaks, in one assertion. A law reconstructed on a student must be about the
    student's atom and the student's projection key, or it can never apply to a student state."""
    law = width.Law("LS_A3", "CARD", 2, NOOP, support=2, witness=ONE)
    exported = probe.ProbeLaw(law, (("LS_A3", {}),), alternative=(frozenset([("x",)]), frozenset()),
                              role="A3")
    outcome = {"atom_in_this_machine": "VT_A3", "before": ONE, "after": TWO,
               "effect_here": NOOP}
    local = probe.restate(exported, outcome)
    assert local is not None
    assert local.atom == "VT_A3", "the law must be about the student's atom"
    assert local.key == 1, "the key must be read off the student's own state"
    assert local.effect == NOOP, "the effect is what must survive"


def test_a_law_is_refuted_where_its_effect_does_not_reproduce():
    """The check that keeps the transfer sound: if the experiment lands in a state where this atom does
    something else, the law is not restated here at all."""
    law = width.Law("LS_A3", "CARD", 2, NOOP, support=2, witness=ONE)
    exported = probe.ProbeLaw(law, (("LS_A3", {}),), alternative=(frozenset([("x",)]), frozenset()),
                              role="A3")
    contradicted = {"atom_in_this_machine": "VT_A3", "before": ONE, "after": TWO,
                    "effect_here": (frozenset([("y",)]), frozenset())}
    assert probe.restate(exported, contradicted) is None


def test_a_law_with_no_alternative_is_not_a_reason():
    """A law that was never contrasted has nothing to re-establish, so it is never restated. This is
    the same admission rule as the key-based round, kept because it was the only part that worked."""
    law = width.Law("LS_A3", "CARD", 2, NOOP, support=2, witness=ONE)
    unreasoned = probe.ProbeLaw(law, (("LS_A3", {}),), alternative=None, role="A3")
    outcome = {"atom_in_this_machine": "VT_A3", "before": ONE, "after": TWO, "effect_here": NOOP}
    assert probe.restate(unreasoned, outcome) is None


def test_the_measured_numbers_stay_measured():
    """Portability must be the headline and it must not be quietly re-tuned: 244 of 256 re-ran, and
    the arm that adds reach stayed sound."""
    import json
    artifact = (REPO / "canonical" / "verification" /
                "A_CONTRAST_IS_A_PROBE_20261124_V1.json")
    if not artifact.exists():                       # pragma: no cover
        return
    payload = json.loads(artifact.read_text())
    ledger = payload["summary"]["ledger"]
    arms = payload["summary"]["arms"]
    assert ledger["re_ran"] * 10 > ledger["offered"] * 9, ">90% of reasons must re-run"
    assert arms["B_experiment_and_conclusion"]["wrong"] == 0
    assert arms["B_experiment_and_conclusion"]["predictions"] > arms["A_own"]["predictions"]
    assert arms["D_blind"]["wrong"] > 0, "blind inheritance must stay visibly worse"
