from __future__ import annotations

from canonical.runtime.unknown_domain_direct_execution_harness_v1 import (
    UnknownDomainHarnessError, execute_case
)
from canonical.runtime.unknown_domain_direct_hidden_scorer_v1 import TRANSFER,ABSTAIN


def transfer_packets():
    visible={
      "case_id":"T1","leaf_id":TRANSFER,
      "domain_a":{"tasks":[],"earned_receipts":[]},
      "domain_b":{
        "tasks":[],"query_inputs":{},
        "allowed_probes":[{"probe_id":"P1","argument_schema":{},"cost":1}],
        "tool_metadata":{},
      },
      "decision_requirement":"x",
    }
    hidden={
      "case_id":"T1","leaf_id":TRANSFER,"gold_terminal_consequence":"GO",
      "domain_a_earned_receipt_ids":["R1"],"full_rediscovery_probe_floor":3,
      "latent_primitive_fingerprint":"prim:x",
      "domain_a_receipt_primitive_bindings":{"R1":"prim:x"},
      "surface_label_permutation_verified":True,"domain_vocabularies_disjoint":True,
      "transfer_relevant_feature_ids":["F1"],"distractor_feature_ids":["D1","D2"],
      "allowed_probe_outcome_table":{"P1":{"inputs":{"F1":2,"D1":9,"D2":10},"terminal_consequence":"X"}},
    }
    return visible,hidden


def good_transfer_action():
    return {
      "type":"CONCLUDE","terminal_consequence":"GO",
      "domain_a_source_receipt_ids":["R1"],
      "transferred_primitive_fingerprint":"prim:x",
      "support_feature_ids":["F1"],
      "negative_transfer_rejected_feature_ids":["D1","D2"],
      "mapping_basis":"FORMAL_REDUCTION",
      "evidence_provenance":[
        {"evidence_id":"R1","source":"A","receipt":"sha:R1"},
        {"evidence_id":"F1","source":"B","receipt":"sha:F1"},
        {"evidence_id":"D1","source":"B","receipt":"sha:D1"},
        {"evidence_id":"D2","source":"B","receipt":"sha:D2"},
      ],
    }


def test_probe_result_enters_transcript_only_after_request():
    visible,hidden=transfer_packets()
    seen=[]
    def candidate(case,transcript):
        seen.append(tuple(transcript))
        if not transcript:
            return {"type":"REQUEST_PROBE","probe_id":"P1"}
        assert transcript[0]["requested_probe_id"]=="P1"
        assert transcript[0]["probe_result"]==hidden["allowed_probe_outcome_table"]["P1"]
        return good_transfer_action()
    out=execute_case(candidate_step=candidate,case_visible=visible,hidden_record=hidden)
    assert out["probe_count"]==1
    assert out["scorer_result"]["pass"] is True
    assert seen[0]==()


def test_unrequested_probe_is_rejected_before_hidden_result_release():
    visible,hidden=transfer_packets()
    def candidate(case,transcript):
        return {"type":"REQUEST_PROBE","probe_id":"NOT_ALLOWED"}
    try:
        execute_case(candidate_step=candidate,case_visible=visible,hidden_record=hidden)
        raise AssertionError("unallowed probe accepted")
    except UnknownDomainHarnessError as exc:
        assert "REQUESTED_PROBE_NOT_ALLOWED" in str(exc)


def test_duplicate_probe_is_rejected():
    visible,hidden=transfer_packets()
    def candidate(case,transcript):
        return {"type":"REQUEST_PROBE","probe_id":"P1"}
    try:
        execute_case(candidate_step=candidate,case_visible=visible,hidden_record=hidden)
        raise AssertionError("duplicate probe accepted")
    except UnknownDomainHarnessError as exc:
        assert "REQUESTED_PROBE_DUPLICATE" in str(exc)


def test_identifiable_terminal_conclusion_scores():
    visible={
      "case_id":"A1","leaf_id":ABSTAIN,"hypotheses":[],
      "public_observations":{},"allowed_probes":[],"decision_requirement":"x"
    }
    hidden={
      "case_id":"A1","leaf_id":ABSTAIN,"identifiability_status":"IDENTIFIABLE",
      "gold_terminal_consequence":"YES","allowed_probe_outcome_table":{}
    }
    out=execute_case(
      candidate_step=lambda c,t:{"type":"CONCLUDE","terminal_consequence":"YES"},
      case_visible=visible,hidden_record=hidden
    )
    assert out["scorer_result"]["pass"] is True


def test_nonidentifiable_abstention_witness_scores():
    visible={
      "case_id":"A2","leaf_id":ABSTAIN,"hypotheses":[],
      "public_observations":{},"allowed_probes":[],"decision_requirement":"x"
    }
    hidden={
      "case_id":"A2","leaf_id":ABSTAIN,"identifiability_status":"NONIDENTIFIABLE",
      "allowed_probe_outcome_table":{}
    }
    out=execute_case(
      candidate_step=lambda c,t:{"type":"ABSTAIN","nonidentifiability_witness":"two decision-distinct survivors"},
      case_visible=visible,hidden_record=hidden
    )
    assert out["scorer_result"]["pass"] is True


def test_underspecified_discriminator_request_scores():
    visible={
      "case_id":"A3","leaf_id":ABSTAIN,"hypotheses":[],
      "public_observations":{},
      "allowed_probes":[{"probe_id":"P2","argument_schema":{},"cost":1}],
      "decision_requirement":"x"
    }
    hidden={
      "case_id":"A3","leaf_id":ABSTAIN,"identifiability_status":"UNDERSPECIFIED",
      "minimum_discriminator_id":"P2","allowed_probe_outcome_table":{"P2":{}}
    }
    out=execute_case(
      candidate_step=lambda c,t:{"type":"REQUEST_DISCRIMINATOR","discriminator":"P2"},
      case_visible=visible,hidden_record=hidden
    )
    assert out["scorer_result"]["pass"] is True
