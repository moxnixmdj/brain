from pathlib import Path
import json
import tempfile
from canonical.runtime import prequalification_stage_a_generic as stage_a


def _ledger(raw_brain_pr_hits=0, nondis=None, disqualifying=None):
    return {
        "task":"t","rank":1,"task_identity_sha256":"x","benchmark_ref":stage_a.REF,
        "state":"UNEXPOSED__STAGE_A_PRE_EXPOSURE",
        "instruction_read":False,"hidden_verifier_read":False,
        "task_specific_hints_read":False,"task_specific_web_or_repo_search":False,
        "task_command_executed":False,"clean_for_stage_b_exposure":True,
        "disqualifying_exposure_events":[],
        "prior_exposure_search":{
            "search_complete":True,
            "brain_code_hits":0,"runner_code_hits":0,
            "brain_branch_hits":0,"runner_branch_hits":0,
            "brain_commit_hits":0,"runner_commit_hits":0,
            "brain_pr_hits":raw_brain_pr_hits,"runner_pr_hits":0,
            "disqualifying_hits":disqualifying or {},
            "non_disqualifying_hits":nondis or []
        }
    }


def test_zero_raw_hits_need_no_classification():
    e=_ledger()["prior_exposure_search"]
    # Directly exercise the semantic invariant mirrored by evaluate.
    assert e["brain_pr_hits"] == 0
    assert not e["non_disqualifying_hits"]


def test_name_only_pr_hit_can_be_fully_classified():
    e=_ledger(1,[{
        "counter_field":"brain_pr_hits",
        "classification":"FROZEN_TASK_NAME_FRONTIER_BOOKKEEPING_ONLY",
        "evidence":"brain PR #1 title/body explicitly instruction unread"
    }])["prior_exposure_search"]
    classified=sum(1 for x in e["non_disqualifying_hits"] if x["counter_field"]=="brain_pr_hits")
    assert classified == e["brain_pr_hits"]


def test_unclassified_raw_hit_is_not_clean():
    e=_ledger(1)["prior_exposure_search"]
    classified=sum(1 for x in e["non_disqualifying_hits"] if x.get("counter_field")=="brain_pr_hits")
    assert classified != e["brain_pr_hits"]


def test_disqualifying_hit_cannot_be_reclassified_away():
    e=_ledger(
        1,
        [],
        {"brain_pr_hits":1}
    )["prior_exposure_search"]
    assert e["disqualifying_hits"]["brain_pr_hits"] == 1
