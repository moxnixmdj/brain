"""Regression and falsification tests for Unknown-Domain V5 full-total exact proof."""
from __future__ import annotations

import hashlib
from unittest.mock import patch

from canonical.runtime import unknown_domain_direct_candidate_v3 as candidate
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as g1
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as g2
from canonical.runtime import unknown_domain_direct_hidden_generator_v4 as g4
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
from canonical.runtime import unknown_domain_direct_v5_universal_proof_v1 as proof


def _run(pop):
    results=[]
    for visible,hidden in zip(pop["visible_cases"],pop["hidden_records"],strict=True):
        out=harness.execute_case(
            candidate_step=candidate.step,
            case_visible=visible,
            hidden_record=hidden,
        )
        assert out["scorer_result"]["pass"] is True,(visible["case_id"],out)
        results.append(out["scorer_result"])
    agg=scorer.aggregate(results)
    assert agg["all_27_cases_pass"] is True
    return agg


def test_v5_content_bound_universal_theorem():
    out=proof.prove()
    assert out["status"]==(
        "PASS__FULL_IDENTIFIER_TOTALITY_PLUS_EXACT_ADD2__"
        "UNIVERSAL_OVER_ALL_VALID_V4_PRODUCTION_INPUTS"
    )
    assert out["identifier_totality_proof"]["hmac_collision_freedom_assumed"] is False
    assert out["repairs"]["v2_add2_exact_ieee754_role_order_counterexample"] is True
    assert out["repairs"]["v2_truncated_identifier_universal_quantifier_hole"] is True
    assert out["repairs"]["scorer_or_harness_relaxed"] is False
    assert out["repairs"]["input_quantifier_weakened"] is False
    assert out["accounting"]["acceptance_credit_delta"]==0


def test_total_hmac_token_collision_still_emits_and_passes_all_27():
    # Strong adversarial falsifier: collapse every truncated/full _token value.
    # V4 must remain structurally injective and the unchanged exact scorer must
    # still pass all 27 cases.
    with patch.object(g1,"_token",lambda *args,**kwargs:"COLLIDE"):
        pop=g4._generate(
            beacon="V5-TOTAL-COLLISION-BEACON-000000000001",
            evaluator_secret=b"collision-secret"*3,
            namespace="COLLIDEV4",
        )
        assert pop["case_count"]==27

        case_ids=[x["case_id"] for x in pop["visible_cases"]]
        assert len(case_ids)==len(set(case_ids))==27

        feature_ids=set()
        receipt_ids=set()
        probe_ids=set()
        hypothesis_ids=set()
        action_ids=set()
        intentional_action_equalities=0

        for visible,hidden in zip(pop["visible_cases"],pop["hidden_records"],strict=True):
            if visible["leaf_id"]==g1.TRANSFER:
                source=set(visible["domain_a"]["tasks"][0]["inputs"])
                target=set(visible["domain_b"]["tasks"][0]["inputs"])
                assert source.isdisjoint(target)
                assert feature_ids.isdisjoint(source|target)
                feature_ids.update(source|target)

                receipt=visible["domain_a"]["earned_receipts"][0]["receipt_id"]
                assert receipt not in receipt_ids
                receipt_ids.add(receipt)

                local=[p["probe_id"] for p in visible["domain_b"]["allowed_probes"]]
                assert len(local)==len(set(local))==2
                assert probe_ids.isdisjoint(local)
                probe_ids.update(local)

                rel=set(hidden["transfer_relevant_feature_ids"])
                dist=set(hidden["distractor_feature_ids"])
                assert rel.isdisjoint(dist)
                assert len(rel)==len(hidden["transfer_relevant_feature_ids"])
                assert len(dist)==2
            else:
                hyps=visible["hypotheses"]
                hids=[h["hypothesis_id"] for h in hyps]
                assert len(hids)==len(set(hids))==2
                assert hypothesis_ids.isdisjoint(hids)
                hypothesis_ids.update(hids)

                acts=[h["terminal_consequence"] for h in hyps]
                if hidden["identifiability_status"]=="IDENTIFIABLE":
                    assert acts[0]==acts[1]
                    intentional_action_equalities+=1
                else:
                    assert acts[0]!=acts[1]
                action_ids.update(acts)

                local=[p["probe_id"] for p in visible["allowed_probes"]]
                assert len(local)==len(set(local))
                assert probe_ids.isdisjoint(local)
                probe_ids.update(local)

        assert len(feature_ids)==76
        assert len(receipt_ids)==12
        assert len(probe_ids)==39
        assert len(hypothesis_ids)==30
        assert len(action_ids)==25
        assert intentional_action_equalities==5

        _run(pop)


def test_exact_revoked_v2_add2_counterexample_is_repaired_by_current_candidate_v3():
    secret=hashlib.sha256(b"secret0").digest()
    beacon="beacon-qualification-0000000000000000"
    visible,hidden=g2._transfer_case(secret,beacon,4,namespace="REVOCATION")
    out=harness.execute_case(
        candidate_step=candidate.step,
        case_visible=visible,
        hidden_record=hidden,
    )
    assert out["scorer_result"]["pass"] is True
    assert out["candidate_terminal_action"]["terminal_consequence"]==hidden["gold_terminal_consequence"]
    assert out["probe_count"]<=2


def test_v4_exact_candidate_falsification_sweep_64_populations():
    for i in range(64):
        secret=hashlib.sha256(f"V5-SWEEP-SECRET-{i}".encode()).digest()
        beacon=f"V5-SWEEP-BEACON-{i:04d}-000000000000"
        pop=g4._generate(beacon=beacon,evaluator_secret=secret,namespace=f"SWEEP{i:04d}")
        _run(pop)


def test_v4_scope_is_zero_production_in_tests():
    out=proof.prove()
    assert out["scope"]["terminal_or_production_cases_generated_by_proof"]==0
    assert out["fresh_reality_required_for_this_exact_totalized_contract"] is False
    assert out["production_execution_information_gain_for_this_exact_totalized_contract"]==0
