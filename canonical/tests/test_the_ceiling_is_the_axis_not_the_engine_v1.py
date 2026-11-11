"""r94 -- the ceiling is the AXIS, not the engine.

Literature, 2026:
  MiniWoB++ single-page atomic tasks : Synapse 99.2%  (64 tasks, 48 demos)  [emergentmind]
  MiniWoB++ All-53                   : AutoRPA 95.4%, ReAct 92.8%, Manual 95.2% [sota2]
  MiniWoB++ unseen tasks             : 18.9%                               [sota2]
  CompWoB (composition of the SAME atomic tasks) : 94% -> 24.9% prompted, 54.8% fine-tuned
  OSWorld-Verified                   : top 90.19%, human 72.36%  -- no longer separates agents
  OSWorld 2.0                        : top 72.6% binary, 0.318 tool calls/task median human 1.6h

Our system on 130 MiniWoB tasks: 21/130 = 16.2% (r93, single run).

THE READING THAT MATTERS: 21% is 4-5x behind a zero-shot ReAct baseline on the SAME
benchmark. The engine is not competitive. But chasing 95% on MiniWoB++ would be winning a
benchmark that the field already saturated and REPLACED, because the tasks are atomic and
the field's remaining headroom is COMPOSITION, not atomicity.

So r94 does not chase the number. It records which axis the number lives on, and where the
unclaimed headroom is. This test asserts the CLAIM is on the record with the literature in
it, so a future round cannot casually report "we got 40% on MiniWoB" as if it were progress.
"""
import json
import pathlib

RECORD = pathlib.Path("canonical/governance/R94_THE_CEILING_IS_THE_AXIS_NOT_THE_ENGINE_20261109_V1.json")


def _rec():
    return json.loads(RECORD.read_text())


def test_the_record_exists_and_names_the_axis():
    r = _rec()
    assert "atomic" in r["the_reframe"]
    assert r["our_position"]["all_130"] == "21/130 = 16.2% (single run, r93)"


def test_every_literature_number_has_its_source():
    r = _rec()
    for row in r["literature"]:
        assert row["source"], row
        assert row["number"], row


def test_the_honest_comparison_is_recorded_not_the_flattering_one():
    """Synapse 99.2% is on 64 tasks; our number is on 130. The record must say so."""
    r = _rec()
    assert "not the same task set" in json.dumps(r).lower()


def test_the_unclaimed_headroom_is_composition_and_is_named():
    r = _rec()
    assert "compwob" in json.dumps(r).lower()
    assert r["where_the_headroom_is"]


def test_winning_miniwob_is_explicitly_not_the_gate():
    r = _rec()
    assert "not the gate" in r["the_decision"].lower()
