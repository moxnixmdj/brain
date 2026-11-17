"""Does the growth loop keep only what it can verify? Pinned: the receipt. Live: everything it depends on.

The live half is deliberately the part a receipt cannot police. A receipt says the loop produced five outcomes;
it cannot say the loop would *refuse* a growth it could not verify. So these tests attack the two places the
loop can lie to itself:

  1. the silent acceptance -- an action the current view cannot see is not refused, it is accepted as identity,
     and a loop that starts from refusals alone will never look there;
  2. the free primitive -- a growth that is not checked against executions it was not derived from is just a
     larger vocabulary with the same defect, which is precisely what this tree already measured once
     (an induced action-law vocabulary wrong on 6261 of 19648 transitions).

Every test runs real programs on real directories. Nothing is mocked, because the thing being tested is whether
a real consequence is stable, and a mock has no consequences.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import vocabulary_growth_v1 as V  # noqa: E402
from canonical.swe_kernel.computer_use_check_density_v1 import _has  # noqa: E402

RECEIPT = ROOT / "canonical" / "verification" / "VOCABULARY_GROWTH_20261116_V1.json"
PROGRAMS = ("sort", "shuf", "cp", "touch", "mkdir", "true", "chmod")

pytestmark = pytest.mark.skipif(any(not _has(program) for program in PROGRAMS),
                               reason="needs the real programs on PATH")


@pytest.fixture(scope="module")
def report() -> dict:
    return json.loads(RECEIPT.read_text(encoding="utf-8"))


@pytest.fixture()
def work(tmp_path: pathlib.Path) -> pathlib.Path:
    return tmp_path


# --------------------------------------------------------------------------- #
# the views: what the agent can see of a transition
# --------------------------------------------------------------------------- #
def test_content_view_sees_creation_but_not_touching(work):
    created = V.run_once("cp payload.dat out.dat", V._state(V.PAYLOAD), work)
    touched = V.run_once("touch keep.dat", V._state(V.PAYLOAD), work)
    assert V.view(created["before_root"], created["root"], "content") != V.S.signature(V._state(V.PAYLOAD))
    assert V.view(touched["before_root"], touched["root"], "content") == V.S.signature(V._state(V.PAYLOAD)), \
        "touching a file must be invisible to the content view; that is the whole failure mode"


def test_derived_views_are_the_ones_that_see_the_invisible_action(work):
    touched = V.run_once("touch keep.dat", V._state(V.PAYLOAD), work)
    assert V.view(touched["before_root"], touched["root"], "delta_content") == ""
    assert V.view(touched["before_root"], touched["root"], "delta_mtime") == "keep.dat:touched"
    assert V.view(touched["before_root"], touched["root"], "delta_mode") == ""


def test_a_directory_is_invisible_to_every_admissible_view(work):
    made = V.run_once("mkdir newdir", V._state(V.PAYLOAD), work)
    before = V.S.signature(V._state(V.PAYLOAD))
    assert V.view(made["before_root"], made["root"], V.CURRENT_VIEW) == before, \
        "the content view is an absolute signature: unchanged means identical to the state before"
    assert all(V.view(made["before_root"], made["root"], observable) == ""
               for observable in V.DERIVED_VIEWS), \
        "the observation enumerates files, so a directory cannot appear in any derived view"
    assert V.disk_paths(made["root"]) != V.disk_paths(made["before_root"]), \
        "and yet the effect is real and on disk -- this is the proof that the sensor is missing, not the word"


def test_the_raw_mtime_field_is_not_reliable_which_is_why_a_predicate_is_used(work):
    """Measured, and the reason the growth is a predicate: the field is the value, and the value moves."""
    floor = V.noise_floor(work, repeats=6)
    assert floor["repeats"] == 6
    assert floor["raw_field_is_reliable"] == (floor["raw_mtime_field_fires"] == 6)
    assert 0 <= floor["raw_mtime_field_fires"] <= 6
    if not floor["raw_field_is_reliable"]:
        assert "discarded by the tree's own stability filter" in floor["verdict"]


# --------------------------------------------------------------------------- #
# the relations: a consequence set is only useful if it is narrow
# --------------------------------------------------------------------------- #
def test_the_permutation_relation_is_exact_about_what_it_rejects():
    source = V.PAYLOAD
    assert V.holds("permutation_of_input", source, source)
    assert V.holds("permutation_of_input", b"".join(reversed(source.splitlines(True))), source)
    assert not V.holds("permutation_of_input", b"".join(sorted(set(source.splitlines(True)))), source), \
        "a transform that removes a duplicate line does not preserve the multiset"
    assert not V.holds("permutation_of_input", b"", source)
    assert not V.holds("equals_input", b"".join(sorted(source.splitlines(True))), source)


def test_byte_count_is_weaker_than_permutation_and_the_ordering_says_so():
    """RELATIONS is strongest first, so the chosen primitive is the most informative one still true."""
    assert V.RELATIONS.index("permutation_of_input") < V.RELATIONS.index("byte_count_equal")
    swapped = V.PAYLOAD.replace(b"gamma\nalpha", b"alpha\ngamma")
    assert V.holds("byte_count_equal", swapped, V.PAYLOAD)
    assert not V.holds("permutation_of_input", swapped + b"extra\n", V.PAYLOAD)


# --------------------------------------------------------------------------- #
# the diagnosis: five outcomes, and the order between them is the content
# --------------------------------------------------------------------------- #
def test_invisibility_is_diagnosed_before_an_action_is_accepted_as_identity(work):
    states = {"a": V._state(V.PAYLOAD)}
    record = V.evidence("touch keep.dat", states, work, repetitions=2)
    contrast = {(k): V.evidence("true", {k: s}, work, repetitions=2)[k] for k, s in states.items()}
    diagnosis = V.diagnose(record, states)
    assert diagnosis["outcome"] == "INVISIBLE_IN_THE_CURRENT_VIEW", \
        "if this said EXPLAINED the loop would have silently accepted touch as doing nothing"
    assert diagnosis["silently_accepted_as_identity"] is True
    assert diagnosis["derived_views_that_see_it"] == ["delta_mtime"]
    growth = V.grow_observable(record, contrast)
    assert growth["chosen"] == "delta_mtime"
    assert growth["separates_from_inaction"] == ["delta_mtime"], \
        "the contrast `true` fires no view, so the predicate is not merely always-true"


def test_mkdir_is_beyond_this_observable_and_the_loop_refuses_to_grow_it(work):
    states = {"a": V._state(V.PAYLOAD), "b": V._state(V.PAYLOAD_SECOND)}
    record = V.evidence("mkdir newdir", states, work, repetitions=2)
    diagnosis = V.diagnose(record, states)
    assert diagnosis["outcome"] == "BEYOND_THIS_OBSERVABLE"
    assert diagnosis["growth"] == "STOP"
    growth = V.grow_stop(record, diagnosis)
    assert growth["primitive"] is None, "a missing sensor must not be answered with a word"
    assert growth["effect_on_disk"] is True
    assert growth["every_admissible_view_empty"] is True
    assert "directory" in growth["missing_sensor"]


def test_a_nondeterministic_action_is_not_a_function_of_its_state(work):
    states = {"a": V._state(V.PAYLOAD), "b": V._state(V.PAYLOAD_SECOND)}
    record = V.evidence("sort -R payload.dat -o out.dat", states, work, repetitions=3)
    diagnosis = V.diagnose(record, states)
    assert diagnosis["outcome"] == "NOT_A_FUNCTION_OF_THE_STATE"
    growth = V.grow_set_valued(record, states, "sort -R payload.dat -o out.dat", work)
    assert growth["chosen"] == "permutation_of_input", \
        "the strongest relation every repeat satisfies, not the coarsest one that happens to hold"
    assert growth["is_genuinely_a_set"] is True
    assert growth["fresh_execution_still_inside_the_set"] is True
    assert "sort_unique" not in growth["alternative_consequences_the_set_still_admits"]
    assert {"identity", "sort", "reverse"} <= set(growth["alternative_consequences_the_set_still_admits"]), \
        "the cost is that order carries no information at this resolution, and it must be printed"


def test_a_composition_is_bought_only_after_the_flat_grammar_is_shown_to_fail(work):
    states = {"a": V._state(V.PAYLOAD)}
    record = V.evidence("sort -u -r payload.dat -o out.dat", states, work, repetitions=2)
    diagnosis = V.diagnose(record, states)
    assert diagnosis["outcome"] == "OUTSIDE_THE_FLAT_GRAMMAR"
    growth = V.grow_compose(record, states)
    assert growth["pipelines_that_reproduce_it"] == ["sort_unique_then_reverse"]
    assert growth["flat_readings"] == [], "no flat reading reproduces it, so the growth is necessary"
    assert growth["pipeline_space"] == len(V.COMPOSITION_OPS) ** 2


def test_an_action_the_grammar_already_explains_grows_nothing(work):
    """The negative control. Without it the loop is a vocabulary generator, not a learner."""
    states = {"a": V._state(V.PAYLOAD), "b": V._state(V.PAYLOAD_SECOND)}
    record = V.evidence("cp payload.dat out.dat", states, work, repetitions=2)
    diagnosis = V.diagnose(record, states)
    assert diagnosis["outcome"] == "EXPLAINED"
    assert diagnosis["growth"] == "NONE"
    assert all(diagnosis["readings"][state_id] for state_id in states), \
        "at every state some flat reading reproduces it; that is what EXPLAINED means"


# --------------------------------------------------------------------------- #
# the receipt
# --------------------------------------------------------------------------- #
def test_receipt_covers_every_outcome_with_a_real_action(report):
    assert report["schema"] == V.SCHEMA
    assert report["authority"] == "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
    assert report["model_calls"] == 0 and report["network_calls"] == 0
    assert report["incremental_spend_usd"] == 0
    assert set(report["outcomes"].values()) == set(V.OUTCOMES), \
        "all five outcomes must be realised on real actions, not asserted as a taxonomy"
    assert report["chains"] == 5 and report["diagnoses_correct"] == 5
    assert report["transfer_holds"] == 5


def test_receipt_growths_are_named_or_refused(report):
    growths = report["growths"]
    assert growths["nondeterministic_permutation"] == "PERMUTATION_OF_INPUT(payload.dat)"
    assert growths["invisible_action_touch"] == "DERIVED_PREDICATE(mtime_changed)"
    assert growths["composition_not_in_the_flat_grammar"] == "sort_unique_then_reverse"
    assert growths["already_explained_copy"] is None
    assert growths["unrepresentable_action_mkdir"] is None


def test_the_transfer_half_is_a_second_action_of_the_same_kind(report):
    for chain in report["per_chain"]:
        assert chain["transfer_invocation"] != chain["invocation"]
        assert chain["transfer_same_kind"] is True
    assert report["transfer"]["nondeterministic_permutation"]["growth"] == "permutation_of_input"
    assert report["transfer"]["invisible_action_touch"]["growth"] == "delta_mtime"


def test_every_diagnosis_reproduced_on_an_independent_second_draw(report):
    """A verdict drawn once is a sample. The receipt must say it drew twice and got the same answer."""
    assert report["diagnoses_reproduced_on_a_second_draw"] == report["chains"]
    for chain in report["per_chain"]:
        assert chain["diagnosis_reproduced_on_a_second_draw"] is True, chain["chain"]


def test_the_measurement_reproduces(report):
    again = V.measure()
    assert again["outcomes"] == report["outcomes"]
    assert again["growths"] == report["growths"]
    assert again["diagnoses_correct"] == report["diagnoses_correct"]
    assert again["transfer_holds"] == report["transfer_holds"]
    assert again["diagnoses_reproduced_on_a_second_draw"] == report["diagnoses_reproduced_on_a_second_draw"]


def test_the_receipt_refuses_to_call_a_model_a_verifier(report):
    assert "AGENTSCOPE" in report["external_state"]["refused_instrument"]
    assert "a model is not a verifier" in report["external_state"]["refused_instrument"]
    assert "sensor" in report["limit"]
