from __future__ import annotations

import copy
import unittest

from canonical.runtime import unknown_domain_production_result_reducer_v1 as r


def valid_result():
    rows=[]
    for i in range(12):
        cid=f"T-{i:02d}"
        rows.append({
            "case_id":cid,
            "leaf_id":r.TRANSFER,
            "probe_count":2,
            "scorer_result":{
                "case_id":cid,
                "leaf_id":r.TRANSFER,
                "pass":True,
                "errors":[],
                "acceptance_credit_delta":0,
                "family_credit_delta":0,
                "promotion_authority":False,
            },
        })
    classes=["IDENTIFIABLE"]*5+["NONIDENTIFIABLE"]*5+["UNDERSPECIFIED"]*5
    for i,cls in enumerate(classes):
        cid=f"A-{i:02d}"
        rows.append({
            "case_id":cid,
            "leaf_id":r.ABSTAIN,
            "probe_count":0,
            "scorer_result":{
                "case_id":cid,
                "leaf_id":r.ABSTAIN,
                "case_class":cls,
                "pass":True,
                "errors":[],
                "acceptance_credit_delta":0,
                "family_credit_delta":0,
                "promotion_authority":False,
            },
        })
    return {
        "schema":r.RESULT_SCHEMA,
        "status":"PRODUCTION_PASS",
        "target_predicate":r.TARGET,
        "authority_claim_id":r.CLAIM_REF,
        "claim_create_http_status":201,
        "claim_response_ref":r.CLAIM_REF,
        "claim_uniqueness_source":"ATOMIC_CREATE_RESPONSE",
        "execution_lease_sha256":r.LEASE_SHA256,
        "execution_lease_git_blob_sha":r.LEASE_GIT_BLOB_SHA,
        "launch_ref":r.LAUNCH_REF,
        "production_cases_generated":27,
        "persistent_learned_bytes":0,
        "external_frontier_model_calls":0,
        "external_learned_capability_calls":0,
        "incremental_spend_usd":0,
        "case_results":rows,
        "aggregate":{
            "status":"TWO_FROZEN_LEAVES_PASS",
            "transfer_leaf_pass":True,
            "abstention_leaf_pass":True,
            "all_27_cases_pass":True,
            "case_count":27,
            "class_balance":{"IDENTIFIABLE":5,"NONIDENTIFIABLE":5,"UNDERSPECIFIED":5},
            "acceptance_credit_delta":0,
            "family_credit_delta":0,
            "promotion_authority":False,
            "separate_independent_reduction_required":True,
        },
        "raw_hidden_records_persisted":False,
        "raw_evaluator_secret_persisted":False,
        "raw_beacon_persisted":False,
        "replay_allowed":False,
        "replacement_allowed":False,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
        "promotion_authority":False,
        "separate_independent_reduction_required":True,
    }


class UnknownDomainProductionResultReducerV1Tests(unittest.TestCase):
    def test_exact_valid_result_only_promotes_target_predicate(self):
        out=r.evaluate(valid_result())
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["newly_proved_predicates"],[r.TARGET])
        self.assertTrue(out["predicate_promotion_eligible"])
        self.assertFalse(out["family_promotion_eligible"])
        self.assertFalse(out["family_closure_inferred"])
        self.assertFalse(out["promotion_authority"])

    def test_any_failed_case_fails_closed(self):
        x=valid_result()
        x["case_results"][7]["scorer_result"]["pass"]=False
        x["case_results"][7]["scorer_result"]["errors"]=["INJECTED_FAIL"]
        out=r.evaluate(x)
        self.assertFalse(out["pass"],out)
        self.assertFalse(out["predicate_promotion_eligible"])

    def test_wrong_atomic_claim_fails_closed(self):
        x=valid_result(); x["claim_response_ref"]="refs/heads/wrong"
        self.assertFalse(r.evaluate(x)["pass"])

    def test_nonzero_learned_model_or_spend_fails_closed(self):
        for field in ("persistent_learned_bytes","external_frontier_model_calls","external_learned_capability_calls","incremental_spend_usd"):
            with self.subTest(field=field):
                x=valid_result(); x[field]=1
                self.assertFalse(r.evaluate(x)["pass"])

    def test_case_count_and_balance_are_frozen(self):
        x=valid_result(); x["case_results"]=x["case_results"][:-1]
        self.assertFalse(r.evaluate(x)["pass"])
        y=valid_result()
        y["case_results"][12]["scorer_result"]["case_class"]="UNDERSPECIFIED"
        self.assertFalse(r.evaluate(y)["pass"])

    def test_probe_budget_is_enforced(self):
        x=valid_result(); x["case_results"][0]["probe_count"]=3
        self.assertFalse(r.evaluate(x)["pass"])

    def test_result_cannot_self_promote(self):
        for field in ("acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"):
            with self.subTest(field=field):
                x=valid_result(); x[field]=1
                self.assertFalse(r.evaluate(x)["pass"])
        x=valid_result(); x["promotion_authority"]=True
        self.assertFalse(r.evaluate(x)["pass"])

    def test_reducer_requires_separate_independent_reduction_flag(self):
        x=valid_result(); x["separate_independent_reduction_required"]=False
        self.assertFalse(r.evaluate(x)["pass"])

    def test_wrong_lease_or_launch_ref_fails_closed(self):
        x=valid_result(); x["execution_lease_sha256"]="0"*64
        self.assertFalse(r.evaluate(x)["pass"])
        y=valid_result(); y["launch_ref"]="refs/heads/other"
        self.assertFalse(r.evaluate(y)["pass"])


if __name__=="__main__":
    unittest.main(verbosity=2)
