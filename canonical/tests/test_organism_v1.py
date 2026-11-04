"""The process must earn the three words it uses: initiative, prediction, surprise.

Every test exists because the first two runs were already wrong in that exact way:

  * run 1: fourteen ticks, one target, **zero predictions**. The bandit scored ORGANS, so every
    target inside an organ shared a score and an alphabetical tie-break picked the same one
    forever, and the prediction lookup used a key the state never stored. An organism that never
    predicts cannot be surprised, and one that never explores learns nothing.
  * surprise must be measured against a prediction written BEFORE the action. A tick with no
    prediction is *unpredicted*, never *correct* -- counting "no prediction" as "right" is how a
    system reports 100% accuracy on a question it declined to answer.
  * the process may not widen its own organ set. A faculty that adds faculties is not an organism,
    it is a privileges bug.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import organism_v1 as org  # noqa: E402


# --------------------------------------------------------------------------- stubs
class Stub(org.Organ):
    """An organ whose every answer is scripted, so the loop can be judged on its own."""

    def __init__(self, name, observations, targets=("t1", "t2"), predicts="FIXED"):
        self.name = name
        self.observations = list(observations)
        self._targets = list(targets)
        self._predicts = predicts
        self.acted = 0

    def targets(self):
        return [{"id": t} for t in self._targets]

    def predict(self, target, record):
        return self._predicts if record.get("attempts") else None

    def act(self, target):
        self.acted += 1
        return {"applied": True}

    def observe(self, target, acted):
        return self.observations.pop(0) if self.observations else "FIXED"


def _state():
    return org.blank_state()


# --------------------------------------------------------------------------- prediction
def test_a_prediction_is_written_before_the_action_it_describes():
    state = _state()
    org.tick(state, {"o": Stub("o", ["FIXED"])})
    kinds = [e["kind"] for e in state["journal"]]
    assert kinds == ["PREDICTION", "OUTCOME"], kinds
    assert state["journal"][0]["seq"] < state["journal"][1]["seq"]


def test_surprise_is_a_mismatch_between_the_prediction_and_the_observation():
    state = _state()
    stub = Stub("o", ["FIXED", "STILL_THERE"], targets=("t1", "t2"))
    org.tick(state, {"o": stub})            # t1: unpredicted
    org.tick(state, {"o": stub})            # t2: unpredicted
    org.tick(state, {"o": stub})            # t1: predicted FIXED, observed FIXED
    assert state["counts"]["predicted"] == 1
    assert state["counts"]["surprised"] == 0

    stub.observations = ["STILL_THERE"]
    stub._targets = ["t3"]                  # a fresh target so it is attended
    state["targets"]["o::t3"] = {"attempts": 1, "confirmations": 1}   # pretend it has history
    org.tick(state, {"o": stub})
    assert state["counts"]["surprised"] == 1, "a contradicted prediction was not a surprise"


def test_an_unpredicted_action_is_never_counted_as_correct():
    state = _state()
    org.tick(state, {"o": Stub("o", ["FIXED"], targets=("t1",))})
    counts = state["counts"]
    assert counts["actions"] == 1
    assert counts["predicted"] == 0
    assert counts["surprised"] == 0
    got = org.summary(state)
    assert got["unpredicted"] == 1
    assert got["surprise_rate_when_predicted"] is None, (
        "no predictions must not read as a perfect rate")
    # The journal must carry the same distinction, not just the summary: an unpredicted tick
    # recorded as surprise=False would read, to anyone replaying the log, as a prediction that
    # held. Measured 2026-11-04: a mutant writing False here survived the suite until this
    # assertion existed, because `unpredicted` is derived from counts and never read the field.
    outcome = [e for e in state["journal"] if e["kind"] == "OUTCOME"][0]
    assert outcome["surprise"] is None, (
        f"an unpredicted tick was journaled as surprise={outcome['surprise']!r}, not None")


# --------------------------------------------------------------------------- initiative
def test_every_target_is_visited_before_any_is_revisited():
    """Run 1 attended one target fourteen times. The arm is the target, not the organ."""
    state = _state()
    stub = Stub("o", ["FIXED"] * 20, targets=("a", "b", "c", "d"))
    for _ in range(4):
        org.tick(state, {"o": stub})
    visited = {e["target"] for e in state["journal"] if e["kind"] == "OUTCOME"}
    assert visited == {"a", "b", "c", "d"}, visited


def test_what_worked_is_retired_and_nothing_is_churned():
    state = _state()
    stub = Stub("o", ["FIXED"] * 20, targets=("a",))
    for _ in range(6):
        org.tick(state, {"o": stub})
    assert state["targets"]["o::a"].get("retired_at") is not None
    acted = [e for e in state["journal"] if e["kind"] == "OUTCOME"]
    # one unpredicted first visit, then RETIRE_AFTER_CONFIRMATIONS predictions that held
    assert len(acted) <= org.RETIRE_AFTER_CONFIRMATIONS + 1, (
        f"a settled target was attended {len(acted)} times: that is churn")
    assert any(e["kind"] == "IDLE" for e in state["journal"][-2:]), (
        "after retiring its only target it invented work instead of resting")


def test_when_there_is_nothing_left_it_rests_and_says_so():
    state = _state()
    stub = Stub("o", ["FIXED"] * 40, targets=("a",))
    for _ in range(8):
        org.tick(state, {"o": stub})
    idles = [e for e in state["journal"] if e["kind"] == "IDLE"]
    assert idles, "an idle tick must be recorded, or the process looks busy when it is not"
    assert "saw" in idles[0]


def test_the_policy_changes_because_of_what_happened():
    """Same code, different actions on tick 2 and tick 6, because of the outcome."""
    state = _state()
    good = Stub("good", ["FIXED"] * 30, targets=("a", "b"))
    bad = Stub("bad", ["STILL_THERE"] * 30, targets=("a", "b"))
    organs = {"good": good, "bad": bad}
    for _ in range(12):
        org.tick(state, organs)
    assert good.acted > 0 and bad.acted > 0
    # the organ that keeps failing must not be favoured at the end
    late = [e["organ"] for e in state["journal"] if e["kind"] == "OUTCOME"][-4:]
    assert late.count("bad") <= late.count("good"), late


def test_a_surprising_target_keeps_being_investigated():
    """An unresolved oddity outranks a settled one. Curiosity has to be in the arithmetic, or
    the organism is just an optimiser for the things it already understands."""
    state = _state()
    stub = Stub("o", ["STILL_THERE", "STILL_THERE", "STILL_THERE"], targets=("odd",))
    state["targets"]["o::odd"] = {"attempts": 3, "confirmations": 0, "surprises": 3}
    other = Stub("p", ["FIXED"], targets=("dull",))
    state["targets"]["p::dull"] = {"attempts": 9, "confirmations": 9}
    org.tick(state, {"o": stub, "p": other})
    last = [e for e in state["journal"] if e["kind"] == "OUTCOME"][-1]
    assert last["target"] == "odd", last


# --------------------------------------------------------------------------- persistence
def test_a_restart_continues_the_same_life(tmp_path):
    path = tmp_path / "state.json"
    first = org.live(ticks=2, state_path=path, verbose=False,
                     on_tick=None)
    identity = first["identity"]
    # `live` builds the real organs; two ticks is enough to establish a life on disk.
    second = org.live(ticks=1, state_path=path, verbose=False)
    assert second["identity"] == identity, "a restart began a new life instead of continuing one"
    assert second["restarts"] == first["restarts"] + 1
    assert second["tick"] > first["tick"]
    kinds = [e["kind"] for e in second["journal"]]
    assert "RESUME" in kinds


def test_the_journal_is_append_only_and_monotonic():
    state = _state()
    org.tick(state, {"o": Stub("o", ["FIXED"])})
    seqs = [e["seq"] for e in state["journal"]]
    assert seqs == sorted(seqs)
    before = [dict(e) for e in state["journal"]]
    org.tick(state, {"o": Stub("o", ["FIXED"])})
    assert state["journal"][:len(before)] == before, "earlier entries were rewritten"


def test_the_organism_cannot_widen_its_own_organ_set():
    """A faculty that grants itself faculties is a privileges bug wearing a metaphor."""
    organs = org.build_organs()
    assert set(org.PROTECTED_ACTIONS) >= {"widen_organs", "promote_self", "flip_terminal"}
    for name in organs:
        assert name in {"effect", "receipt", "lease", "measurement", "derived"}, name
    source = Path(ROOT / "canonical/runtime/organism_v1.py").read_text()
    assert "ORGANS = {" not in source, "a global mutable organ registry invites self-widening"


def test_it_uses_no_model_and_no_network():
    source = Path(ROOT / "canonical/runtime/organism_v1.py").read_text()
    for forbidden in ("import requests", "import openai", "urllib.request", "http://",
                      "https://"):
        assert forbidden not in source, forbidden


# --------------------------------------------------------------------------- accounting
def test_the_bookkeeping_closes():
    state = _state()
    stub = Stub("o", ["FIXED", "STILL_THERE"] * 10, targets=("a", "b", "c"))
    for _ in range(10):
        org.tick(state, {"o": stub})
    got = org.summary(state)
    assert got["predicted"] + got["unpredicted"] == got["actions"]
    predictions = sum(1 for e in state["journal"] if e["kind"] == "PREDICTION")
    outcomes = sum(1 for e in state["journal"] if e["kind"] == "OUTCOME")
    assert predictions == outcomes == got["actions"], (predictions, outcomes, got["actions"])


def test_the_report_claims_nothing_about_sentience():
    got = org.summary(_state())
    joined = " ".join(got["non_claims"])
    assert "ACTING_ALONE_IS_NOT_BEING_ALIVE" in joined
    assert "SURPRISE_IS_A_BOOLEAN" in joined
    assert got["authority"] == "NO_CAPABILITY_CREDIT_INITIATIVE_MEASUREMENT_ONLY"


# --------------------------------------------------------------------------- learning
class _BrokenFix:
    """A defect class whose fixer runs but whose verifier keeps saying STILL_THERE.

    This is the world that separates 'surprised' from 'teachable': the world does not move,
    so a learner must stop being surprised, and a system that only asserts its hope must not.
    """

    def __init__(self):
        self.fixes = 0

    def find(self):
        return [{"defect_id": "d1"}]

    def fix(self, defect):
        self.fixes += 1
        return {"applied": True}

    def verify(self, defect):
        return False


def test_an_organ_predicts_from_its_own_history_not_from_hope():
    organ = org._LoopOrgan("k", _BrokenFix)
    target = {"id": "d1", "defect": {}}
    assert organ.predict(target, {}) == "FIXED", "with no history the claim must be its intent"
    assert organ.predict(target, {"verdicts": {"STILL_THERE": 3}}) == "STILL_THERE", (
        "a target with a past must be predicted from that past")


def test_a_surprise_costs_one_lesson_not_one_per_tick():
    state = _state()
    organ = org._LoopOrgan("k", _BrokenFix)
    for _ in range(6):
        org.tick(state, {"k": organ})
    got = org.summary(state)
    # It learns on the first surprise, confirms twice, then retires the target and rests:
    # 3 actions, then 3 idle ticks. Grinding the same broken fix six times would be a fail.
    assert got["actions"] == 3, got
    assert got["idle_ticks"] == 3, got
    assert got["surprises"] == 1, (
        f"the world never moved but it was surprised {got['surprises']} times: "
        "it is not learning, it is repeating its mistake")
    assert got["surprise_early"] == 1.0 and got["surprise_late"] == 0.0, got
    # and the lesson is in the journal, not just in the summary
    outcomes = [e for e in state["journal"] if e["kind"] == "OUTCOME"]
    assert [e["surprise"] for e in outcomes] == [True, False, False], outcomes


def test_a_long_happy_history_does_not_outvote_a_fresh_breakage():
    """The measured failure of 2026-11-04, pinned.

    Live run: eight healthy ticks, then the archive adapter silently changed. The organism
    predicted EFFECT_HELD from the modal verdict of the target's whole life and was surprised
    at t35, t38 AND t39 -- three times for one change, because history outvoted evidence.
    One change must cost one surprise.
    """
    state = _state()
    stub = Stub("o", ["OK"], targets=("t1",))
    stub.predict = lambda target, record: org._expected(record, default=None)
    for _ in range(8):
        stub.observations = ["OK"]
        org.tick(state, {"o": stub})
    before = org.summary(state)["surprises"]
    stub.observations = ["BROKEN"] * 4
    # the target was retired after two confirmations; reopen it so the breakage is reachable
    state["targets"]["o::t1"].pop("retired_at", None)
    rows = [org.tick(state, {"o": stub}) for _ in range(4)]
    after = org.summary(state)["surprises"]
    assert after - before == 1, (
        f"one breakage after a long healthy history cost {after - before} surprises, not 1")
    assert rows[0]["observed"] == "BROKEN" and rows[0]["predicted"] == "OK"
    assert rows[1]["predicted"] == "BROKEN", (
        "it saw the breakage and still expected the old world: memory, not learning")


def test_the_journal_says_where_a_prediction_came_from():
    """A prediction from the model and a prediction from the target's own record are different
    claims. If the log cannot tell them apart, no one can check whether the model ever spoke
    about something it had never seen -- and that is the only reason the model is here."""
    state = _state()
    stub = Stub("o", ["FIXED"] * 6, targets=("t1", "t2", "t3"))
    stub.senses = lambda target: {"s": 1.0}
    for _ in range(6):
        org.tick(state, {"o": stub})
    predictions = [e for e in state["journal"] if e["kind"] == "PREDICTION"]
    assert predictions, "nothing was predicted"
    assert all("from_model" in e and "first_visit" in e for e in predictions), (
        "a prediction without provenance cannot be audited")
