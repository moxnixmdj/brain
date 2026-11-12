"""Problem 2 pinned: the router generalizes 100%, and the ceiling is capability, not matching.

The owner's framing was "exact recall works, similar tasks do not". Measured here:

  * 11 of 11 paraphrases are answered with memory OFF. The generalization that was reported
    missing is already done by the router, by keyword matching, and it needed no memory.
  * 0 of 0 failing paraphrases could be rescued by a remembered procedure, because there were
    no failing paraphrases to rescue among paraphrases of a capability that EXISTS.
  * 4 of 6 refused tasks have NO capability behind them at all. "Sum a column of numbers in a
    csv" is AMBIGUOUS among sqlite and xlsx *creators* because nothing in the 145-row registry
    sums a CSV column. That is not a matching failure and no matcher can fix it.

So the honest shape of Problem 2 in this tree is: generalization is not the bottleneck where a
capability exists; coverage is the bottleneck where it does not.

A failure here means the numbers moved: re-measure and rewrite the document rather than
editing assertions to fit.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

import problem_2_generalization_benchmark_v1 as B
from canonical.runtime import procedure_memory_v1 as PM


@pytest.fixture(scope="module")
def measured():
    with tempfile.TemporaryDirectory() as tmp:
        state = Path(tmp) / "exp.json"
        router = B.router_already_generalizes(state)
        memory = B.memory_rescues(state)
    return {"router": router, "memory": memory}


@pytest.fixture(scope="module")
def ceiling():
    return B.coverage_ceiling()


# ------------------------------------------------------------------------------------------
# The matching layer, which is the part I built this round
# ------------------------------------------------------------------------------------------
def test_opposite_directions_never_share_a_signature():
    """THE DEFECT IN THE OLD KEY, pinned.

    `experience_v1.signature_of` sorts the words, so "convert yaml to json" and
    "convert json to yaml" produce the identical key and teaching one answers the other.
    """
    from canonical.runtime import experience_v1 as EXP

    old_a = EXP.signature_of("convert yaml to json")
    old_b = EXP.signature_of("convert json to yaml")
    assert old_a == old_b, "the old key no longer collides; re-read the document"

    new_a = PM.signature("convert yaml to json")
    new_b = PM.signature("convert json to yaml")
    assert new_a != new_b
    assert not PM.agrees_on_direction(new_a, new_b)


def test_a_paraphrase_reaches_the_same_signature():
    """The generalization the memory is FOR: wording, inflection and fillers are not new tasks."""
    base = PM.signature("convert the yaml file a.yaml to json using yq")
    for phrase in (
        "convert the yaml file b.yaml to json using yq",
        "convert the yaml file a.yaml to json with yq",
    ):
        assert PM.agrees_on_direction(PM.signature(phrase), base)
        assert PM.similarity(PM.signature(phrase), base) >= 0.7


def test_singular_and_plural_of_the_same_word_converge():
    """The stemmer's one hard requirement. `cases`/`case` both -> case, not cas/case."""
    for singular, plural in (("file", "files"), ("yaml", "yamls"), ("column", "columns"),
                             ("entry", "entries"), ("cases", "case")):
        assert PM._stem(singular) == PM._stem(plural), (singular, plural)
    for word in ("gas", "bus"):
        assert PM._stem(word) == word


def test_only_a_verified_receipt_may_teach():
    """A failure is not a lesson about the next sentence that resembles it."""
    out = PM.learn("sum a column in a csv", "csv.sum", verified=False)
    assert out["learned"] is False
    assert out["why"] == "ONLY_A_VERIFIED_RECEIPT_MAY_TEACH_A_PROCEDURE"


def test_opposite_task_is_not_rescued_by_memory(tmp_path):
    """Train "yaml->json", ask "json->yaml": memory must not answer it."""
    import canonical.runtime.experience_v1 as EXP

    saved = EXP.DEFAULT_STATE
    try:
        state = tmp_path / "exp.json"
        PM.learn("convert yaml to json with yq", "yaml.to_json.yq", verified=True, path=state)
        EXP.DEFAULT_STATE = state
        hit = PM.recall("convert json to yaml with yq", path=state)
        assert hit is None, f"opposite direction was recalled as {hit}"
    finally:
        EXP.DEFAULT_STATE = saved


# ------------------------------------------------------------------------------------------
# THE LOAD-BEARING MEASUREMENT
# ------------------------------------------------------------------------------------------
def test_the_router_already_generalizes(measured):
    """11 of 11 paraphrases answered with memory OFF.

    The paraphrase set is drawn from a capability that exists (yaml->json via yq), so a
    paraphrase failure here would be a routing defect. There are none -- WHEN THE TOOL IS
    INSTALLED. The substrate is declared rather than assumed: `yq` and `pyyaml` are
    per-interpreter user installs and do not survive a new interpreter or a wiped sandbox
    (measured in two rounds). Without them this test skips instead of reporting a routing
    failure that is really an absent binary.
    """
    router = measured["router"]
    if not router.get("routable"):
        pytest.skip(f"tool substrate absent: {router.get('substrate')}")
    assert router["total"] >= 11
    assert router["answered_without_memory"] == router["total"], (
        f"{router['total'] - router['answered_without_memory']} paraphrases now fail without "
        "memory -- that would give the memory something real to rescue and this round's "
        "conclusion would need re-measuring")


def test_memory_has_nothing_to_rescue_among_reachable_capabilities(measured):
    """0 testable paraphrases. Honest reporting, not a win for memory.

    This test exists so that the next round cannot claim a memory improvement by measuring
    paraphrases the router already answered. If `testable` becomes non-zero, the memory can
    finally be judged on the thing it was built for.
    """
    memory = measured["memory"]
    if not memory.get("routable"):
        pytest.skip(f"tool substrate absent: {memory.get('substrate')}")
    assert memory["testable"] == 0, (
        f"{memory['testable']} paraphrases now fail without memory -- re-run "
        "problem_2_generalization_benchmark_v1.py and record the rescue rate")
    assert memory["rescued"] == 0


def test_most_refused_tasks_have_no_capability_behind_them(ceiling):
    """4 of 6. The ceiling is what the machine can DO, not what it can find.

    A capability that cannot be built cannot be remembered, so no amount of matching,
    embedding, or experience changes these rows. This is the number that bounds Problem 2.
    """
    assert ceiling["total"] == 6
    assert ceiling["no_capability_exists"] == 4, ceiling["rows"]


def test_the_two_reachable_refusals_are_reachable(ceiling):
    """The other two DO have a capability that mentions the right words -- they are matchable."""
    reachable = [r for r in ceiling["rows"] if r["capability_exists"]]
    assert len(reachable) == 2
    assert {r["task"] for r in reachable} == {"diff two files", "sort the lines of a file"}
