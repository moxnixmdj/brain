"""A fact verified at step 1 and falsified at step 3 by a legal action.

Pinned: the receipt. Live: the invalidation rule itself -- absence is a value, a wildcard frame is a prefix,
and a control chain must not raise.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import standing_facts_v1 as facts  # noqa: E402

RECEIPT = ROOT / "canonical" / "verification" / "STANDING_FACTS_20261116_V1.json"


@pytest.fixture(scope="module")
def report() -> dict:
    return json.loads(RECEIPT.read_text(encoding="utf-8"))


def test_absence_is_a_value_and_disappearance_falsifies_a_fact() -> None:
    state = {"a": b"x"}
    established = facts.establish(state, 1)
    still, broken = facts.revalidate(established, {}, 2)
    assert still == [] and len(broken) == 1
    assert broken[0]["value_now"] is None


def test_a_wildcard_in_a_frame_is_read_as_a_prefix() -> None:
    contract = {"frame": {"creates": ["chunk_*"], "modifies": [], "removes": []}}
    touch = facts.touched(contract, {"src": "in.txt", "dst": "out.dat"})
    assert touch == {"chunk_*"}
    established = facts.establish({"chunk_aa": b"1", "keep.txt": b"2"}, 1)
    risky = facts.at_risk(established, touch)
    assert [fact["path"] for fact in risky] == ["chunk_aa"]


def test_the_receipt_numbers(report: dict) -> None:
    assert report["chains_run"] == 3
    assert report["per_step_only"]["claims_success_on_every_step"] == 3
    assert report["frame_scoped_ledger"]["detected"] == 3
    assert report["frame_scoped_ledger"]["false_invalidations_on_controls"] == 0
    assert report["lead_in_steps"]["values"] == [2, 2, 2]
    assert len(report["goal_check"]["failed_on"]) == 3


def test_every_passing_step_is_the_point(report: dict) -> None:
    # if a sabotage step were illegal, the previous receipt would have caught it and this would prove nothing
    for entry in report["per_chain"]:
        for step in entry["sabotaged"]["steps"]:
            assert step["contract_verdict"] == "HOLDS", (entry["chain"], step["name"])


def test_the_cause_is_localised_where_the_symptom_cannot_be(report: dict) -> None:
    for entry in report["per_chain"]:
        run = entry["sabotaged"]
        invalidated = [step for step in run["steps"] if step["invalidated"]]
        assert len(invalidated) == 1
        assert invalidated[0]["sabotage"] is True
        assert run["goal"]["symptom_at_step"] == len(run["steps"])
        assert run["goal"]["symptom_at_step"] - invalidated[0]["step"] == 2


def test_the_ledger_costs_less_than_rehashing_everything(report: dict) -> None:
    assert report["cost"]["facts_revalidated_frame_scoped"] < report["rehash_all"]["facts_revalidated"]


def test_the_limit_is_named(report: dict) -> None:
    assert "remote service" in report["limit"]
    assert "Repair" in report["limit"]
    assert "cannot see" in report["environment"]["why_real"]


def test_a_live_chain_detects_at_the_causal_step_and_a_control_stays_quiet() -> None:
    import tempfile
    import shutil

    work = pathlib.Path(tempfile.mkdtemp(prefix="brain-facts-test-"))
    try:
        contract = facts.acquire("cp {src} {dst}", "cp", facts.ACQUISITION, facts.TEXT)
        steps = [
            {"name": "make", "template": "cp {src} {dst}", "program": "cp", "src": "in.txt",
             "dst": "work.dat", "contract": contract},
            {"name": "overwrite", "template": "cp {src} {dst}", "program": "cp", "src": "decoy.txt",
             "dst": "work.dat", "sabotage": True, "contract": contract},
        ]
        run = facts.chain(work, steps, "cmp work.dat in.txt")
        assert run["frame_scoped"]["first_invalidation_step"] == 2
        assert run["per_step_only"]["claims_success"] is True
        control = facts.chain(work, [steps[0]], "cmp work.dat in.txt")
        assert control["frame_scoped"]["invalidations"] == []
    finally:
        shutil.rmtree(work, ignore_errors=True)
