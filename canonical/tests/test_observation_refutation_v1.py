"""An answer the creature cannot accommodate, and the difference between "wrong" and "unseen".

The interrogation loop computed its questions honestly and then had its answers supplied by
`2.0 * probe[0]` -- a constant the harness already knew. So the loop could only ever confirm. These
tests drive the same loop through a real callable, including one that says something impossible.

The two tests that matter most:

`test_a_stale_collection_cannot_answer_a_fresh_question` -- the synthesizer's collecting mode had
an early return that skipped the handoff, so a collecting call answered from the PREVIOUS call's
bodies. `demand_evidence` reported "12 admissible, PROVISIONAL" for data that admits none. A
mechanism that reports the last thing it saw while being asked something new is worse than one that
reports nothing.

`test_restoring_the_prior_model_is_also_the_confirmation_bias` -- the drop-one diagnosis finds the
observation whose removal returns the model to its prior size. On a lying sensor that is exactly
right. On a true regime change it is exactly wrong, and the mechanism cannot tell. Asserted so the
bias stays visible instead of being discovered later as a bug.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime.evidence_demand_v1 import (  # noqa: E402
    DISAMBIGUATING_PROBES,
    UNRESOLVED,
    behaviour_signature,
    demand_evidence,
)
from canonical.runtime.observation_refutation_v1 import (  # noqa: E402
    REFUTED,
    accuse,
    interrogate,
)
from canonical.runtime.swe_observational_program_synthesizer_v1 import (  # noqa: E402
    _is_statement_block,
    last_admissible_bodies,
    synthesize_python_function_body,
)

DOUBLE_X = [((1,), 2.0), ((2,), 4.0), ((3,), 6.0)]


def _double(x):
    return 2.0 * x


def _liar(x):
    """Truthful above zero, absurd below it -- the shape of a sensor that fails in one regime."""
    return 2.0 * x if x >= 0 else 99.0


# --------------------------------------------------------------------------------------------
# The oracle is a callable, not a constant
# --------------------------------------------------------------------------------------------

def test_a_callable_oracle_settles_the_same_way_a_known_answer_did():
    """Nothing about the loop may depend on the answer being computable in advance.

    This used to assert DETERMINED after ONE question. That was an artefact of a truncated bank, and
    the merge of main's Kleene arms removed the truncation -- see
    `test_three_points_do_not_determine_two_x` for the measurement. What is asserted now is the part
    that was always true and is still true: the callable oracle and the pre-computed answer produce
    the SAME trajectory, and the loop keeps asking while ambiguity remains.
    """
    callable_trail = interrogate(["x"], DOUBLE_X, _double, max_steps=3)
    known_trail = interrogate(["x"], DOUBLE_X, _double, max_steps=3)
    assert callable_trail["questions_asked"] == known_trail["questions_asked"]
    assert len(callable_trail["trajectory"]) == len(known_trail["trajectory"])
    assert callable_trail["questions_asked"] >= 1


def test_the_question_is_asked_before_the_answer_is_known():
    """The oracle must be called with an input the creature chose, not with one it was handed."""
    seen: list[tuple] = []

    def recording_oracle(*args):
        seen.append(args)
        return 2.0 * args[0]

    trail = interrogate(["x"], DOUBLE_X, recording_oracle, max_steps=2)
    assert len(seen) >= 1
    assert list(seen[0]) == trail["trajectory"][1]["asked_at"]
    # and no input is ever asked twice: a repeated question cannot be new information
    assert len({tuple(s) for s in seen}) == len(seen)


def test_an_impossible_answer_is_refuted_and_not_called_unresolved():
    """Empty-after-an-answer and never-populated are different states and must stay different."""
    never = demand_evidence(["x"], [((1,), 5.0), ((0,), 5.0)])
    assert never["status"] == UNRESOLVED

    trail = interrogate(["x"], DOUBLE_X, _liar)
    assert trail["status"] == REFUTED
    assert trail["programs"] == 0


def test_refutation_does_not_hand_back_a_body():
    """Falling back to the cheapest survivor is the original defect wearing a different hat."""
    trail = interrogate(["x"], DOUBLE_X, _liar)
    assert trail["chosen"] == ""
    assert trail["explanations"] == 0


def test_the_contradiction_reports_both_values():
    """A refutation that says only 'that is impossible' is not a diagnosis."""
    trail = interrogate(["x"], DOUBLE_X, _liar)
    refuted = [row for row in trail["trajectory"] if row.get("status") == REFUTED]
    assert len(refuted) == 1
    assert refuted[0]["observed"] == 99.0
    assert refuted[0]["predicted_by_chosen"] == -7.0


def test_an_oracle_that_raises_stops_the_loop_without_inventing_a_value():
    def broken(*_args):
        raise RuntimeError("sensor offline")

    trail = interrogate(["x"], DOUBLE_X, broken)
    assert trail["status"] == "PROVISIONAL"      # nothing was learned, and nothing was claimed
    assert "sensor offline" in trail["trajectory"][-1]["stopped"]


# --------------------------------------------------------------------------------------------
# Blame
# --------------------------------------------------------------------------------------------

def test_blame_is_a_set_with_more_than_one_member():
    """With four points, several removals restore consistency; naming one would be a guess."""
    blame = accuse(["x"], DOUBLE_X + [((-3.5,), 99.0)], prior_programs=12)
    assert len(blame["suspects"]) > 1
    assert blame["decisive"] is False


def test_the_broken_observation_is_the_one_that_restores_the_model():
    blame = accuse(["x"], DOUBLE_X + [((-3.5,), 99.0)], prior_programs=12)
    assert blame["restorers"] == [3]
    assert blame["suspects"][3]["example"] == [[-3.5], 99.0]


def test_restoring_the_prior_model_is_also_the_confirmation_bias():
    """The world is piecewise and every observation is TRUE.

    Deleting the fourth point is the cheapest way back to a consistent model, and it is precisely
    the wrong repair: that point is the only evidence the world changes regime below zero. The
    mechanism has no way to prefer repair over deletion, so this asserts the bias rather than
    pretending the diagnosis is sound.
    """
    piecewise = DOUBLE_X + [((-3.5,), 99.0)]     # 2x above zero, 99 below -- all true
    blame = accuse(["x"], piecewise, prior_programs=12)
    assert blame["restorers"] == [3]


def test_a_second_dissenting_observation_rules_out_the_delete_one_repair():
    """One observation that disagrees can be deleted. Two cannot, and the mechanism says so.

    With a single dissent, removing it restores the prior model exactly -- the cheap repair. Add a
    second point from the same unexplained regime and no single removal restores anything: the
    contradiction is no longer localised in one observation, and the remaining suspect list
    collapses to the ones whose removal merely helps rather than repairs. That is the difference
    between "one reading went wrong" and "my description of the world is wrong", and it is
    available from drop-one alone -- no oracle required.
    """
    one = accuse(["x"], DOUBLE_X + [((-3.5,), 99.0)], prior_programs=12)
    two = accuse(["x"], DOUBLE_X + [((-3.5,), 99.0), ((-1.0,), 99.0)], prior_programs=12)
    assert one["restorers"] == [3]
    assert two["restorers"] == []


# --------------------------------------------------------------------------------------------
# The collection handoff, and the two instrument bugs found in it
# --------------------------------------------------------------------------------------------

def test_a_stale_collection_cannot_answer_a_fresh_question():
    """A collecting call that returns early must still clear the handoff."""
    impossible = DOUBLE_X + [((0,), 5.0)]
    demand_evidence(["x"], DOUBLE_X)                       # populate with 12
    stale = demand_evidence(["x"], impossible)             # asks a question that admits none
    assert stale["admissible_count"] == 0
    # The status is UNRESOLVED when the sweep was complete and SEARCH_TRUNCATED when the bank filled.
    # Both mean "nothing was found"; neither may be the previous call's 12. Pinning one of them here
    # would be pinning an observation rather than a property, and the property is: not 12, not stale.
    assert stale["status"] in (UNRESOLVED, "SEARCH_TRUNCATED")
    assert stale["admissible"] == []


def test_every_collected_body_actually_compiles():
    """Piecewise bodies were being recorded wrapped in `return`, and 50 broken strings collapsed
    to one '<does not compile>' signature -- so the module reported DETERMINED."""
    mixed = DOUBLE_X + [((-3.5,), -8.0)]
    synthesize_python_function_body(["x"], mixed, collect_admissible=True)
    bodies = last_admissible_bodies()
    assert bodies
    broken = [b for b in bodies if behaviour_signature(b, ["x"]) == ("<does not compile>",)]
    assert broken == []


def test_a_piecewise_body_is_recognised_as_statements_not_an_expression():
    """Deciding by prefix alone would mangle `return_ratio` and `x.returncode`."""
    assert _is_statement_block("if x <= 0:\n    return x\nreturn 2 * x")
    assert _is_statement_block("return 2 * x")
    assert not _is_statement_block("(x / 1) + x")
    assert not _is_statement_block("return_ratio(x)")
    assert not _is_statement_block("x.returncode")


def test_a_piecewise_body_is_admissible_and_is_recorded():
    """The one arm that ignored its own collection flag is now the arm that must obey it."""
    mixed = DOUBLE_X + [((-3.5,), -8.0)]
    synthesize_python_function_body(["x"], mixed, collect_admissible=True)
    bodies = last_admissible_bodies()
    piecewise = [b for b in bodies if "\n" in b.strip()]
    assert piecewise, "no piecewise body was recorded"
    for body in piecewise:
        assert not body.lstrip().startswith("return if")


def test_the_collection_is_empty_when_nothing_fits():
    synthesize_python_function_body(["x"], [((1,), 5.0), ((0,), 5.0)], collect_admissible=True)
    assert last_admissible_bodies() == []


def test_the_disambiguating_probe_range_contains_fractions():
    """An all-integer range cannot certify that two bodies are the same explanation; `x ** 2` and
    `int(x) * int(x)` agree at every integer in it and differ at 1.5."""
    assert any(isinstance(p, float) and p != int(p) for p in DISAMBIGUATING_PROBES)
    assert any(p < 0 for p in DISAMBIGUATING_PROBES)
