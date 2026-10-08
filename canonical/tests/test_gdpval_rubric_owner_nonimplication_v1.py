import json
from pathlib import Path

from canonical.runtime.gdpval_rubric_owner_nonimplication_v1 import prove

ROOT=Path(__file__).resolve().parents[2]
SURFACE=ROOT/"canonical/governance/GDPVAL_AA_V21_OWNER_JUDGE_PUBLIC_SURFACE_20261007_V1.json"


def test_two_world_rubric_nonimplication():
    out=prove(json.loads(SURFACE.read_text()))
    assert out["status"]=="PASS__PUBLIC_RUBRIC_SATISFACTION_DOES_NOT_LOGICALLY_DETERMINE_OWNER_PAIRWISE_VERDICT"
    assert out["same_public_rubric_state_in_both_worlds"] is True
    assert out["worlds"]["W_RUBRIC_MONOTONE"]["brain_vs_opus"]=="BRAIN_WIN"
    assert out["worlds"]["W_STYLE_OR_OTHER_LATENT_FACTOR"]["brain_vs_opus"]=="OPUS_WIN"
    assert out["only_deliberate_difference"]=="UNBOUND_OWNER_PAIRWISE_RELATION_EXTENSION"
    assert out["terminal_credit_delta"]==0


def test_fails_closed_if_prompt_becomes_bound():
    doc=json.loads(SURFACE.read_text())
    doc["not_yet_bound_fail_closed"]["exact_pairwise_judge_prompt_or_message_template"]=True
    out=prove(doc)
    assert out["status"]=="FAIL_CLOSED__PREMISES_NOT_MET"
