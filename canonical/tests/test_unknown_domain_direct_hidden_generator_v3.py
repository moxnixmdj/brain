from __future__ import annotations

import copy

import pytest

from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as g2
from canonical.runtime import unknown_domain_direct_hidden_generator_v3 as g3


def _packet():
    return g2.generate_qualification_fixture_population(
        beacon="NAMESPACE-TOTALITY-QUALIFICATION-0001"
    )


def test_v3_accepts_current_valid_v2_fixture_without_semantic_rewrite():
    packet=_packet()
    out=g3.validate_packet(packet)
    assert out==packet
    assert out["case_count"]==27


def test_v3_rejects_transfer_relevant_identifier_collision():
    packet=copy.deepcopy(_packet())
    i=next(i for i,h in enumerate(packet["hidden_records"]) if len(h.get("transfer_relevant_feature_ids",[]))==2)
    ids=packet["hidden_records"][i]["transfer_relevant_feature_ids"]
    ids[1]=ids[0]
    with pytest.raises(g3.UnknownDomainGeneratorV3Error,match="TRANSFER_RELEVANT.*DUPLICATE"):
        g3.validate_packet(packet)


def test_v3_rejects_transfer_distractor_identifier_collision():
    packet=copy.deepcopy(_packet())
    i=next(i for i,h in enumerate(packet["hidden_records"]) if h.get("distractor_feature_ids"))
    ids=packet["hidden_records"][i]["distractor_feature_ids"]
    ids[1]=ids[0]
    with pytest.raises(g3.UnknownDomainGeneratorV3Error,match="TRANSFER_DISTRACTORS_DUPLICATE"):
        g3.validate_packet(packet)


def test_v3_rejects_duplicate_transfer_probe_ids_even_if_table_was_overwritten():
    packet=copy.deepcopy(_packet())
    i=next(i for i,v in enumerate(packet["visible_cases"]) if v.get("domain_b",{}).get("allowed_probes"))
    probes=packet["visible_cases"][i]["domain_b"]["allowed_probes"]
    probes[1]["probe_id"]=probes[0]["probe_id"]
    with pytest.raises(g3.UnknownDomainGeneratorV3Error,match="TRANSFER_PROBE_IDS_DUPLICATE"):
        g3.validate_packet(packet)


def test_v3_rejects_nonidentifiable_action_collision():
    packet=copy.deepcopy(_packet())
    i=next(i for i,h in enumerate(packet["hidden_records"]) if h.get("identifiability_status")=="NONIDENTIFIABLE")
    hypotheses=packet["visible_cases"][i]["hypotheses"]
    hypotheses[1]["terminal_consequence"]=hypotheses[0]["terminal_consequence"]
    with pytest.raises(g3.UnknownDomainGeneratorV3Error,match="NONIDENTIFIABLE_CONSEQUENCE_COLLISION"):
        g3.validate_packet(packet)


def test_v3_rejects_duplicate_underspecified_discriminator_ids():
    packet=copy.deepcopy(_packet())
    i=next(i for i,h in enumerate(packet["hidden_records"]) if h.get("identifiability_status")=="UNDERSPECIFIED")
    probes=packet["visible_cases"][i]["allowed_probes"]
    probes[1]["probe_id"]=probes[0]["probe_id"]
    with pytest.raises(g3.UnknownDomainGeneratorV3Error,match="ABSTENTION_PROBE_IDS_DUPLICATE"):
        g3.validate_packet(packet)


def test_v3_rejects_source_feature_namespace_collapse():
    packet=copy.deepcopy(_packet())
    i=next(i for i,v in enumerate(packet["visible_cases"]) if len(v["domain_a"]["earned_receipts"][0]["normalized_primitive_program"]["roles"])==2)
    row=packet["visible_cases"][i]["domain_a"]["tasks"][0]
    row["inputs"].pop(next(iter(row["inputs"])))
    with pytest.raises(g3.UnknownDomainGeneratorV3Error,match="SOURCE_TASK_0_FEATURE_NAMESPACE_NOT_INJECTIVE"):
        g3.validate_packet(packet)
