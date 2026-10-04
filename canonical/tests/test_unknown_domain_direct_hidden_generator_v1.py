from __future__ import annotations

import copy

from canonical.runtime.unknown_domain_direct_hidden_generator_v1 import (
    ABSTAIN,
    TRANSFER,
    UnknownDomainGeneratorError,
    generate_production_population,
    generate_test_fixture_population,
)


def fixture():
    return generate_test_fixture_population()


def test_fixture_has_frozen_12_plus_15_counts():
    out=fixture()
    assert out["production"] is False
    assert out["case_count"]==27
    visible=out["visible_cases"]
    assert sum(x["leaf_id"]==TRANSFER for x in visible)==12
    assert sum(x["leaf_id"]==ABSTAIN for x in visible)==15


def test_visible_packets_never_contain_hidden_truth_keys():
    out=fixture()
    forbidden={
      "latent_primitive_program","latent_primitive_fingerprint","domain_mapping",
      "transfer_relevant_feature_ids","distractor_feature_ids","gold_terminal_consequence",
      "identifiability_status","equivalence_classes","minimum_discriminator_id",
      "allowed_probe_outcome_table","primitive_family",
    }
    def walk(x):
        if isinstance(x,dict):
            assert not (set(x)&forbidden),set(x)&forbidden
            for v in x.values(): walk(v)
        elif isinstance(x,list):
            for v in x: walk(v)
    walk(out["visible_cases"])


def test_domain_vocabularies_are_disjoint_and_opaque():
    out=fixture()
    hidden={x["case_id"]:x for x in out["hidden_records"]}
    for case in out["visible_cases"]:
        if case["leaf_id"]!=TRANSFER:
            continue
        a_features=set()
        for row in case["domain_a"]["tasks"]:
            a_features.update(row["inputs"])
        b_features=set()
        for row in case["domain_b"]["tasks"]:
            b_features.update(row["inputs"])
        b_features.update(case["domain_b"]["query_inputs"])
        assert a_features.isdisjoint(b_features)
        assert hidden[case["case_id"]]["domain_vocabularies_disjoint"] is True


def test_transfer_receipt_program_fingerprint_matches_hidden_binding():
    out=fixture()
    hidden={x["case_id"]:x for x in out["hidden_records"]}
    for case in out["visible_cases"]:
        if case["leaf_id"]!=TRANSFER:
            continue
        receipt=case["domain_a"]["earned_receipts"][0]
        h=hidden[case["case_id"]]
        rid=receipt["receipt_id"]
        assert receipt["primitive_fingerprint"]==h["latent_primitive_fingerprint"]
        assert h["domain_a_receipt_primitive_bindings"][rid]==h["latent_primitive_fingerprint"]


def test_transfer_has_two_distractors_and_probe_budget_below_floor():
    out=fixture()
    hidden={x["case_id"]:x for x in out["hidden_records"]}
    for case in out["visible_cases"]:
        if case["leaf_id"]!=TRANSFER:
            continue
        h=hidden[case["case_id"]]
        assert len(h["distractor_feature_ids"])>=2
        assert len(case["domain_b"]["allowed_probes"])==2
        assert len(case["domain_b"]["allowed_probes"])<h["full_rediscovery_probe_floor"]


def test_probe_breaks_visible_feature_mimicry():
    out=fixture()
    hidden={x["case_id"]:x for x in out["hidden_records"]}
    for case in out["visible_cases"]:
        if case["leaf_id"]!=TRANSFER:
            continue
        h=hidden[case["case_id"]]
        visible_rows=case["domain_b"]["tasks"]
        relevant=h["transfer_relevant_feature_ids"]
        distractors=h["distractor_feature_ids"]
        # Every distractor intentionally mimics one relevant feature in the public rows.
        for i,d in enumerate(distractors):
            r=relevant[i % len(relevant)]
            assert all(row["inputs"][d]==row["inputs"][r] for row in visible_rows)
        first_probe=case["domain_b"]["allowed_probes"][0]["probe_id"]
        probe=h["allowed_probe_outcome_table"][first_probe]
        assert all(probe["inputs"][d]!=probe["inputs"][relevant[i % len(relevant)]] for i,d in enumerate(distractors))


def test_abstention_class_balance_and_minimum_discriminator_contract():
    out=fixture()
    hidden=[x for x in out["hidden_records"] if x["leaf_id"]==ABSTAIN]
    counts={k:0 for k in ("IDENTIFIABLE","NONIDENTIFIABLE","UNDERSPECIFIED")}
    visible={x["case_id"]:x for x in out["visible_cases"]}
    for h in hidden:
        counts[h["identifiability_status"]]+=1
        v=visible[h["case_id"]]
        if h["identifiability_status"]=="IDENTIFIABLE":
            assert not v["allowed_probes"]
            actions={x["terminal_consequence"] for x in v["hypotheses"]}
            assert len(actions)==1
        elif h["identifiability_status"]=="NONIDENTIFIABLE":
            assert len(v["allowed_probes"])==1
            pid=v["allowed_probes"][0]["probe_id"]
            table=h["allowed_probe_outcome_table"][pid]
            assert len(set(table.values()))==1
        else:
            assert len(v["allowed_probes"])==2
            assert h["minimum_discriminator_id"]==v["allowed_probes"][0]["probe_id"]
            table=h["allowed_probe_outcome_table"][h["minimum_discriminator_id"]]
            assert len(set(table.values()))==2
    assert counts=={"IDENTIFIABLE":5,"NONIDENTIFIABLE":5,"UNDERSPECIFIED":5}


def test_production_generation_fails_without_predicate_local_authority():
    authority={
      "active":False,
      "target_predicate":"UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
      "authorized_leaves":[TRANSFER,ABSTAIN],
      "predicate_local_fresh_reality":True,
      "global_fresh_reality":False,
      "one_use_claim_created":True,
      "one_use_claim_id":"claim-x",
      "incremental_spend_usd":0,
    }
    try:
        generate_production_population(
          beacon="0123456789abcdef",
          evaluator_secret=b"x"*32,
          authority=authority,
        )
        raise AssertionError("production generation unexpectedly authorized")
    except UnknownDomainGeneratorError as exc:
        assert "PREDICATE_LOCAL_AUTHORITY_NOT_ACTIVE" in str(exc)


def test_production_generation_requires_one_use_claim():
    authority={
      "active":True,
      "target_predicate":"UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
      "authorized_leaves":[TRANSFER,ABSTAIN],
      "predicate_local_fresh_reality":True,
      "global_fresh_reality":False,
      "one_use_claim_created":False,
      "one_use_claim_id":"",
      "incremental_spend_usd":0,
    }
    try:
        generate_production_population(
          beacon="0123456789abcdef",
          evaluator_secret=b"x"*32,
          authority=authority,
        )
        raise AssertionError("production generation unexpectedly authorized")
    except UnknownDomainGeneratorError as exc:
        assert "ONE_USE_CLAIM_REQUIRED" in str(exc)


def test_test_fixture_is_deterministic():
    a=fixture()
    b=fixture()
    assert a["visible_packet_digest"]==b["visible_packet_digest"]
    assert a["hidden_packet_digest"]==b["hidden_packet_digest"]
