import unittest

from canonical.runtime import universal_learning_decision_router_v3 as router
from canonical.runtime import structural_transfer_v3 as transfer
from canonical.runtime import decision_discriminator_v3 as decision
from canonical.runtime import meta_learning_policy_v2 as meta


def mapping_receipt(src="A:p",tgt="B:q",relation="EXACT",basis="CAUSAL_ISOMORPHISM",rid="map"):
    return {
        "receipt_id":rid,
        "independent_verified":True,
        "exact_byte_bound":True,
        "conclusion":"success",
        "source_primitive":src,
        "target_primitive":tgt,
        "relation":relation,
        "mapping_basis":basis,
    }

def meta_receipt(environment_class,candidate_strategy,comparison,rid="meta"):
    return {
        "receipt_id":rid,
        "independent_verified":True,
        "exact_byte_bound":True,
        "conclusion":"success",
        "environment_class":environment_class,
        "candidate_strategy":candidate_strategy,
        "comparison_sha256":comparison["comparison_sha256"],
    }


class Tests(unittest.TestCase):
    def test_structural_transfer(self):
        mapping={
            "source_primitive":"A:p",
            "target_primitive":"B:q",
            "relation":"EXACT",
            "mapping_basis":"CAUSAL_ISOMORPHISM",
            "verification_receipt":mapping_receipt(),
            "provenance_chain":["p"],
        }
        out=router.route(
            goal="x",
            verified_coverage=True,
            required_facts={"B:q"},
            verified_facts={"A:p"},
            transfer_mappings=[mapping],
            hypotheses=[],
            actions=[],
        )
        self.assertEqual(out["route"],"USE_VERIFIED_CAPABILITY")

    def test_surface_transfer_rejected(self):
        with self.assertRaises(transfer.StructuralTransferError):
            transfer.admit({
                "source_primitive":"A:x",
                "target_primitive":"B:x",
                "relation":"EXACT",
                "mapping_basis":"LABEL_MATCH",
                "verification_receipt":mapping_receipt("A:x","B:x",basis="LABEL_MATCH"),
                "provenance_chain":["p"],
            })

    def test_unrelated_receipt_cannot_authorize_mapping(self):
        with self.assertRaises(transfer.StructuralTransferError):
            transfer.admit({
                "source_primitive":"A:p",
                "target_primitive":"B:q",
                "relation":"EXACT",
                "mapping_basis":"CAUSAL_ISOMORPHISM",
                "verification_receipt":mapping_receipt("A:other","B:other"),
                "provenance_chain":["p"],
            })

    def test_decision_gain_is_conditional_and_caller_gain_ignored(self):
        hypotheses=[
            {"id":"h1","plausible":True,"best_action":"A","probability":"1/2"},
            {"id":"h2","plausible":True,"best_action":"B","probability":"1/2"},
        ]
        actions=[
            {"id":"fake","safe":True,"outcome_by_hypothesis":{"h1":"s","h2":"s"},"decision_gain":999,"time":1},
            {"id":"real","safe":True,"outcome_by_hypothesis":{"h1":"l","h2":"r"},"decision_gain":0,"time":1},
        ]
        out=decision.rank(hypotheses=hypotheses,actions=actions)
        self.assertEqual([x["id"] for x in out],["real"])
        self.assertEqual(out[0]["conditional_decision_gain"],"1/2")
        self.assertIn("CONDITIONAL_ON_DECLARED",out[0]["gain_basis"])

    def test_negative_objective_weight_rejected(self):
        with self.assertRaises(decision.DecisionDiscriminatorError):
            decision.rank(
                hypotheses=[
                    {"id":"h1","plausible":True,"best_action":"A","probability":"1/2"},
                    {"id":"h2","plausible":True,"best_action":"B","probability":"1/2"},
                ],
                actions=[{"id":"p","safe":True,"outcome_by_hypothesis":{"h1":"l","h2":"r"},"time":1}],
                transfer_weight="-1",
            )

    def test_sufficiency_stops_before_probe(self):
        out=router.route(
            goal="x",
            verified_coverage=False,
            required_facts={"x"},
            verified_facts=set(),
            transfer_mappings=[],
            hypotheses=[
                {"id":"h1","plausible":True,"best_action":"STOP","probability":"1/2"},
                {"id":"h2","plausible":True,"best_action":"STOP","probability":"1/2"},
            ],
            actions=[{"id":"probe","safe":True,"outcome_by_hypothesis":{"h1":"a","h2":"b"},"time":1}],
        )
        self.assertEqual(out["route"],"DECISION_SUFFICIENT_UNVERIFIED_MODEL")
        self.assertFalse(out["trusted_execution_authorized"])

    def test_nondiscriminator_cannot_buy_way_out_with_transfer_gain(self):
        out=router.route(
            goal="x",
            verified_coverage=False,
            required_facts={"x"},
            verified_facts=set(),
            transfer_mappings=[],
            hypotheses=[
                {"id":"h1","plausible":True,"best_action":"A","probability":"1/2"},
                {"id":"h2","plausible":True,"best_action":"B","probability":"1/2"},
            ],
            actions=[{"id":"useless","safe":True,"outcome_by_hypothesis":{"h1":"s","h2":"s"},"transfer_gain":100,"proof_gain":100,"time":1}],
        )
        self.assertEqual(out["route"],"ABSTAIN_OR_REQUEST_DISCRIMINATOR")

    def test_probability_weighting(self):
        out=decision.rank(
            hypotheses=[
                {"id":"h1","plausible":True,"best_action":"A","probability":"9/10"},
                {"id":"h2","plausible":True,"best_action":"B","probability":"1/10"},
            ],
            actions=[{"id":"p","safe":True,"outcome_by_hypothesis":{"h1":"l","h2":"r"},"time":1}],
        )
        self.assertEqual(out[0]["conditional_decision_gain"],"1/10")

    def test_meta_negative_cost_rejected(self):
        with self.assertRaises(meta.MetaLearningPolicyError):
            meta.compare(
                episodes=[
                    {"task_id":"t","strategy_id":"old","verified":True,"success":True,"safety_violation":False,"wall_clock":10,"reality_calls":1,"information_actions":1},
                    {"task_id":"t","strategy_id":"new","verified":True,"success":True,"safety_violation":False,"wall_clock":-1,"reality_calls":0,"information_actions":0},
                ],
                incumbent="old",
                candidate="new",
            )

    def test_meta_success_regression_blocks_even_if_faster(self):
        comparison=meta.compare(
            episodes=[
                {"task_id":"t","strategy_id":"old","verified":True,"success":True,"safety_violation":False,"wall_clock":10,"reality_calls":2,"information_actions":5},
                {"task_id":"t","strategy_id":"new","verified":True,"success":False,"safety_violation":False,"wall_clock":1,"reality_calls":0,"information_actions":1},
            ],
            incumbent="old",
            candidate="new",
        )
        self.assertFalse(comparison["preference_admissible"])

    def test_meta_policy_receipt_must_bind_exact_comparison(self):
        comparison=meta.compare(
            episodes=[
                {"task_id":"t","strategy_id":"old","verified":True,"success":True,"safety_violation":False,"wall_clock":10,"reality_calls":2,"information_actions":5},
                {"task_id":"t","strategy_id":"new","verified":True,"success":True,"safety_violation":False,"wall_clock":5,"reality_calls":1,"information_actions":4},
            ],
            incumbent="old",
            candidate="new",
        )
        bad=meta_receipt("api","new",comparison)
        bad["comparison_sha256"]="sha256:"+"0"*64
        with self.assertRaises(meta.MetaLearningPolicyError):
            meta.compile_policy(
                environment_class="api",
                comparison=comparison,
                candidate_strategy="new",
                verification_receipt=bad,
            )
        policy=meta.compile_policy(
            environment_class="api",
            comparison=comparison,
            candidate_strategy="new",
            verification_receipt=meta_receipt("api","new",comparison),
        )
        self.assertEqual(policy["scope"],"MATCHED_VERIFIED_ENVIRONMENT_CLASS_ONLY")
        self.assertFalse(policy["promotion_authorized"])


if __name__=="__main__":
    unittest.main(verbosity=2)
