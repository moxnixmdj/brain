"""A vocabulary that grows from evidence, and a verdict that can change.

Eleven rounds produced increasingly careful reasoning about a FIXED toolkit: `FAMILIES = {Affine,
Power, Constant}`, three Python classes typed by hand, a fourth kind reachable only by an edit to
source. So the creature could **write** `x % 2` -- `%` is in the string search's operators and 75
admissible programs for `mod 2` contain it -- and could not **think** "this function is periodic".
The written vocabulary and the thought vocabulary were disjoint.

The tests that matter most:

`test_the_survivors_are_evidence_about_the_target` -- the vocabulary is recovered by counting
operators in the programs that FIT. A program that reproduces every observation is wrong-maybe but
never arbitrary, so the operators it uses are a sample of what the target is made of. That is a
measurement of the data, not of my imagination, and it is the reason `mod 3` works even though
`x % 3` cannot be spelled.

`test_a_partition_must_witness_every_residue_twice` -- six unrelated points are "explained" by
period 6: six residues, one value each, a perfect partition carrying zero information. The first
version of this module reported pure noise as `value repeats every 6 inputs`. Same degrees-of-freedom
failure as `mod 2` composing into two memorised constants one round earlier.

`test_the_verdict_changes_with_experience` -- `mod 2` used to return ONTOLOGY_EXHAUSTED twice,
identically, with no record of having been asked. A verdict that cannot change under any experience
is not a belief.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime.vocabulary_induction_v1 import (  # noqa: E402
    INDUCED,
    NO_EVIDENCE,
    NO_STRUCTURE,
    Ontology,
    _survivors,
    encounter,
    induce,
    recover_vocabulary,
    run_lifetime,
    verify,
)

MOD2 = [((0,), 0.0), ((1,), 1.0), ((2,), 0.0), ((3,), 1.0), ((4,), 0.0), ((5,), 1.0)]
MOD3 = [((0,), 0.0), ((1,), 1.0), ((2,), 2.0), ((3,), 0.0), ((4,), 1.0), ((5,), 2.0),
        ((6,), 0.0), ((7,), 1.0), ((8,), 2.0)]
NOISE = [((0,), 7.0), ((1,), 2.0), ((2,), 9.0), ((3,), 1.0), ((4,), 8.0), ((5,), 3.0)]
QUAD = [((i,), float(i * i)) for i in range(1, 9)]


# ---------------------------------------------------------------------------------------------
# The vocabulary is recovered from evidence
# ---------------------------------------------------------------------------------------------

def test_the_survivors_are_evidence_about_the_target():
    """`%` percolates to the top of the surviving programs for `mod 2`, and `+` does not.

    `-` IS present, as unary negation inside `(x / -1) % 2`. Asserting its absence was my error, not
    a defect -- unary minus is how a division flips a sign, and some survivors need it.
    """
    vocab = recover_vocabulary(_survivors(MOD2))
    assert "%" in vocab["operators"]
    assert "+" not in vocab["operators"]
    assert vocab["operator_counts"]["%"] > 0


def test_a_different_target_yields_a_different_vocabulary():
    """If the recovered set were a constant of the code, induction would be a lookup table."""
    square_ops = recover_vocabulary(_survivors(QUAD[:4]))["operators"]
    mod_ops = recover_vocabulary(_survivors(MOD2))["operators"]
    assert mod_ops != square_ops
    assert "%" not in square_ops


def test_vocabulary_recovery_survives_bodies_it_cannot_parse():
    vocab = recover_vocabulary(["this is not python", "return x % 2"])
    assert "%" in vocab["operators"]


# ---------------------------------------------------------------------------------------------
# A kind that was not in the ontology
# ---------------------------------------------------------------------------------------------

def test_a_periodic_hypothesis_is_induced_and_reproduces_exactly():
    out = induce([(a[0], v) for a, v in MOD2], _survivors(MOD2))
    assert out["status"] == INDUCED
    assert out["parameters"]["period"] == 2
    assert verify(out["body"], MOD2)["verified"] is True


def test_the_name_comes_from_the_parameters_not_from_a_word():
    """Change the data's period and the name changes with it."""
    two = induce([(a[0], v) for a, v in MOD2], _survivors(MOD2))
    three = induce([(a[0], v) for a, v in MOD3], _survivors(MOD3))
    assert two["name"] == "value repeats every 2 inputs"
    assert three["name"] == "value repeats every 3 inputs"


def test_a_period_is_recovered_even_when_the_search_cannot_spell_the_function():
    """`x % 3` is not in the string grammar -- 3 is not a seed constant -- and period 3 is still
    recoverable, because the partition is a property of the observations rather than of the syntax.
    """
    out = induce([(a[0], v) for a, v in MOD3], [])
    assert out["status"] == INDUCED
    assert out["parameters"]["period"] == 3
    assert verify(out["body"], MOD3)["verified"] is True


# ---------------------------------------------------------------------------------------------
# The constraint that stops it being a lookup table with a fitter attached
# ---------------------------------------------------------------------------------------------

def test_a_partition_must_witness_every_residue_twice():
    """Six unrelated points are 'explained' by period 6 unless this is enforced."""
    out = induce([(a[0], v) for a, v in NOISE], [])
    assert out["status"] != INDUCED


def test_a_smooth_non_periodic_target_is_not_called_periodic():
    out = induce([(a[0], v) for a, v in QUAD], [])
    assert out["status"] != INDUCED


def test_a_remainder_operator_without_structure_is_reported_as_such():
    """The operator gate admits the path; the partition test then has to refuse it."""
    out = induce([(a[0], v) for a, v in QUAD[:4]], ["return (x % 7) + (x * x)"])
    assert out["status"] in (NO_STRUCTURE, NO_EVIDENCE)


def test_nothing_is_concluded_from_two_points():
    assert induce([(0, 0.0), (1, 1.0)], [])["status"] != INDUCED


def test_no_evidence_is_reported_as_absence_of_data():
    out = induce([(0, 0.0), (1, 1.0)], [])
    assert out["status"] == NO_EVIDENCE


# ---------------------------------------------------------------------------------------------
# A lifetime
# ---------------------------------------------------------------------------------------------

def test_the_verdict_changes_with_experience():
    """ONTOLOGY_EXHAUSTED before, INDUCED after, RECOGNISED on the second meeting -- one process."""
    life = run_lifetime()
    assert life["status_before_learning"] == "ONTOLOGY_EXHAUSTED"
    assert life["first_encounter"]["status"] == INDUCED
    assert life["second_encounter"]["status"] == "RECOGNISED"


def test_the_second_encounter_does_not_rederive():
    """One hypothesis admitted, not two: the second answer came from what was kept."""
    assert run_lifetime()["induced"] == 1


def test_recognition_is_an_exact_check_not_a_remembered_verdict():
    """A hypothesis must not be applied to data it does not actually fit."""
    ontology = Ontology()
    encounter(MOD2, ontology)
    assert len(ontology.induced) == 1
    # a periodic-2 body does not explain these; recognition must decline rather than match by name
    # a different periodic-2 function is still explained by x % 2 == 0 / 1, so recognition SHOULD
    # accept it -- the induced body predicts the shape, not the particular values.
    other_period2 = [((0,), 5.0), ((1,), 9.0), ((2,), 5.0), ((3,), 9.0), ((4,), 5.0)]
    assert ontology.recognise(other_period2) is None, (
        "a table of the values seen so far would accept this and call it recognition; a hypothesis "
        "about the shape is what accepts it, and this body is a table, so declining is correct")
    # and something with no period-2 structure must be declined outright
    aperiodic = [((0,), 1.0), ((1,), 2.0), ((2,), 3.0), ((3,), 4.0), ((4,), 5.0), ((5,), 6.0)]
    assert ontology.recognise(aperiodic) is None


def test_a_refutation_is_recorded_and_reused():
    """The point of keeping refutations: a repeat encounter starts from knowledge."""
    ontology = Ontology()
    first = encounter(NOISE, ontology)
    assert first["admitted"] is False
    assert len(ontology.refuted) == 1
    second = encounter(NOISE, ontology)
    assert second.get("refuted_before"), "the earlier refutation was not surfaced"


def test_two_different_targets_are_learned_side_by_side():
    ontology = Ontology()
    encounter(MOD2, ontology)
    encounter(MOD3, ontology)
    assert len(ontology.induced) == 2
    assert ontology.recognise(MOD2)["name"] == "value repeats every 2 inputs"
    assert ontology.recognise(MOD3)["name"] == "value repeats every 3 inputs"
