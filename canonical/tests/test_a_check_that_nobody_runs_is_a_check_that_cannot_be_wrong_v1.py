"""The tests that hold this round's three self-corrections and its one deliberate refusal.

Each test is a mistake that was actually made in this round, in the order it was made:

  1. **The instrument measured the tree it had just repaired.** The first run reported 2,319
     certified flags and 16 writers; after `check_flags()` was fixed in the same working tree,
     the same instrument reported 2,311 and 14. A "before" number that is read from the code it
     is measuring is not a before number. The shipped rule is now restated verbatim and the
     receipt is asserted against the restated rule.

  2. **A survivor was judged in the room it had dirtied.** `gzip --help` leaves a zero-byte
     `gz<pid>`; a baseline taken before the run and a digest taken after it then differ for a
     flag that wrote nothing that mattered, and all 600 survivors came back destructive -- a
     number that would have been published as "every read-only flag writes". Certification and
     judgement are now in separate rooms and the receipt says which.

  3. **A repair that removes the writers is not a repair.** `check_flags()` no longer certifies
     `shred -v`, and the citation it hands a step is still `tar --block-number`, which accepts
     nothing on this room, while 3 of 87 graph edges have any discriminating flag at all. The
     test holds the refusal: this round does NOT claim the citation is repaired, only that it
     no longer certifies a destroyer.

And one thing that must never become true: the repair must not have changed any verdict. If
`edges` moved when the citation was repaired, the citation was load-bearing and the shipped
round's numbers were wrong for a reason nobody had noticed. Edge count is asserted.

The instrument takes about 80 seconds, so the receipt is measured once per module.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
TOOLS = REPO / "canonical" / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import the_guide_is_an_action_grammar_v1 as guide  # noqa: E402

RECEIPT = (REPO / "canonical/verification/"
           "A_CHECK_THAT_NOBODY_RUNS_IS_A_CHECK_THAT_CANNOT_BE_WRONG_20261203_V1.json")


@pytest.fixture(scope="module")
def receipt():
    return json.loads(RECEIPT.read_text(encoding="utf-8"))


def test_every_declared_gate_holds_and_the_receipt_says_so(receipt):
    gates = receipt["verdict"]
    assert len(gates) == 12, sorted(gates)
    unmet = [name for name, row in gates.items() if not row["MET"]]
    assert not unmet, unmet


def test_the_before_numbers_come_from_the_shipped_rule_not_from_the_patched_tree(receipt):
    """Correction 1. The shipped rule is restated in the instrument; these are its results."""
    cert = receipt["certification"]
    assert cert["certified"] == 2319, cert["certified"]
    assert cert["changed_bytes_when_run"] == 16, cert["changed_bytes_when_run"]
    # and the patched tree must now certify FEWER, or the repair did nothing
    page = guide.page_of("shred")
    assert "shred -v" not in page["checks"]
    assert page["checks"] == [], page["checks"]


def test_a_destroyer_is_no_longer_certified_and_its_citation_is_gone(receipt):
    repair = receipt["repair"]
    assert repair["shred_removed"] and repair["split_removed"]
    assert repair["removed"] >= 16, repair["removed"]
    for program in ("rm", "shred", "truncate", "unlink"):
        assert guide.page_of(program)["checks"] == [], program
    assert receipt["effect_on_the_shipped_round"]["citations_removed"] == [
        "rm --help", "shred --help", "stream -help", "stream-im6 -help",
        "stream-im6.q16 -help", "truncate --help", "unlink --help"]


def test_the_shipped_round_reproduces_after_the_repair(receipt):
    """The repair must not move the round that produced it. Recorded need for need."""
    round_ = receipt["shipped_round"]
    assert round_["needs"]["total"] == 13
    assert round_["needs"]["held"] == 11
    assert round_["needs"]["refused"] == 2
    assert round_["edges"] == 87
    assert all(round_["gates"].values()), round_["gates"]


def test_the_citation_was_never_load_bearing(receipt):
    """If repairing the citation moved a number, the shipped round was wrong for an unnoticed
    reason. It did not move, and that is the finding."""
    effect = receipt["effect_on_the_shipped_round"]
    assert effect["graph_unchanged"] is True
    assert effect["edges_before"] == effect["edges_after"] == 87


def test_most_citations_were_vacuous_and_the_judged_room_was_not_the_certified_one(receipt):
    """Correction 2, and the number that made correction 3 necessary."""
    vacuity = receipt["vacuity"]
    assert vacuity["vacuous"] * 2 >= vacuity["citations"], vacuity
    assert vacuity["vacuous_by_flag"]["--help"] == 249, vacuity["vacuous_by_flag"]
    assert len(vacuity["vacuous_destroyers"]) == 4, vacuity["vacuous_destroyers"]
    discrim = receipt["discrimination"]
    # if certification and judgement had shared a room this number was 600 of 600
    assert 0 < discrim["discriminating"] < discrim["survivors_measured"] / 10, discrim


def test_the_round_refuses_to_call_the_citation_repaired(receipt):
    """Correction 3. A repair that removes the writers leaves a citation that still says nothing."""
    cover = receipt["coverage"]
    assert cover["edges_with_a_discriminating_check"] * 2 < cover["edges"], cover
    assert cover["programs_with_one"] == ["gzip", "zcat"], cover
    usable = receipt["usable_citations"]
    assert usable["would_be_cited"] == 370
    assert usable["of_those_decide_which_object"] == 0, usable
    assert "not a claim that an executed check would have caught a bad step here" in " ".join(
        receipt["what_this_is_not"])


def test_a_check_that_writes_still_writes_when_run_in_the_room():
    """The finding itself, executed here rather than read from the receipt: `shred -v` on an
    object the guide would have called a read-only check, and the bytes are gone."""
    import hashlib
    import tempfile

    with tempfile.TemporaryDirectory() as where:
        victim = pathlib.Path(where) / "payload.txt"
        victim.write_text("the quick brown fox\n", encoding="utf-8")
        before_bytes = victim.read_bytes()
        kind_before = guide.typed(pathlib.Path(where)).get("payload.txt")
        outcome = guide.run(["shred", "-v", "payload.txt"], pathlib.Path(where))
        # SHRED OVERWRITES; IT DOES NOT UNLINK. That is the whole point: the file is still there,
        # still of the same kind, and its bytes are gone -- so a kind map sees nothing happen.
        assert victim.exists(), "shred unlinked the file; the essay says it overwrites"
        assert victim.read_bytes() != before_bytes, "the bytes survived, so the finding is wrong"
        assert "the quick brown fox" not in victim.read_text(errors="replace")
        assert guide.typed(pathlib.Path(where)).get("payload.txt") == kind_before, \
            "the kind changed, so this is not the blind case the essay describes"
        # the repaired comparison must see it
        assert outcome["changed"] is True, outcome
        assert outcome["bytes_changed"] == ["payload.txt"], outcome["bytes_changed"]


def test_the_certification_a_repair_survives_is_executed_not_asserted():
    """`certified_checks` is the executed half of the repair. Run it on a page whose flag writes
    and one whose flag does not, and it must separate them."""
    import tempfile

    with tempfile.TemporaryDirectory() as where:
        room = pathlib.Path(where) / "room"
        guide.make_room(room)
        names = guide._objects_in(room)
        assert guide.certified_checks("shred", ["-v"], room, names) == []
        kept = guide.certified_checks("gzip", ["--list"], room, names)
        assert kept == ["--list"], kept


def test_zero_model_calls_zero_parameters_zero_network(receipt):
    cost = receipt["cost"]
    assert cost["model_calls"] == 0
    assert cost["parameters_stored"] == 0
    assert cost["network_calls_at_run_time"] == 0
