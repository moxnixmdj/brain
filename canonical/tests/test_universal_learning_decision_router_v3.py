import unittest

from canonical.runtime import universal_learning_decision_router_v3 as router
from canonical.runtime import structural_transfer_v3 as transfer
from canonical.runtime import decision_discriminator_v3 as decision
from canonical.runtime import meta_learning_policy_v2 as meta


def receipt(r="r"):
    return {
        "receipt_id":r,
        "independent_verified":True,
        "exact_byte_bound":True,
        "conclusion":"success",
    }


class Tests(unittest.TestCase):
    def test_structural_transfer(self):
        mapping={
            "source_primitive":"A:p",
            "target_primitive":"B:q",
            "relation":"EXACT",
            "mapping_basis":"CAUSAL_ISOMORPHISM",
            "verification_receipt":receipt("m"),
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
                "verification_receipt":receipt(),
                "provenance_chain":["p"],
            })

    def test_decision_gain_derived(self):
        hypotheses=[
            {"id":"h1","plausible":True,"best_action":"A","probability":"1/2"},
            {"id":"h2","plausible":True,"best_action":"B","probability":"1/2"},
        ]
        actions=[
            {
                "id":"fake",
                "safe":True,
                "outcome_by_hypothesis":{"h1":"s","h2":"s"},
                "decision_gain":999,
                "time":1,
            },
            {
                "id":"real",
                "safe":True,
                "outcome_by_hypothesis":{"h1":"l","h2":"r"},
                "decision_gain":0,
                "time":1,
            },
        ]
        out=decision.rank(hypotheses=hypotheses,actions=actions)
        self.assertEqual([x["id"] for x in out],["real"])
        self.assertEqual(out[0]["derived_decision_gain"],"1/2")

    def test_sufficiency_stops_before_probe(self):
        hypotheses=[
            {"id":"h1","plausible":True,"best_action":"STOP","probability":"1/2"},
            {"id":"h2","plausible":True,"best_action":"STOP","probability":"1/2"},
        ]
        out=router.route(
            goal="x",
            verified_coverage=False,
            required_facts={"x"},
            verified_facts=set(),
            transfer_mappings=[],
            hypotheses=hypotheses,
            actions=[
                {
                    "id":"probe",
                    "safe":True,
                    "outcome_by_hypothesis":{"h1":"a","h2":"b"},
                    "time":1,
                }
            ],
        )
        self.assertEqual(out["route"],"DECISION_SUFFICIENT_UNVERIFIED_MODEL")

    def test_no_discriminator_abstains(self):
        hypotheses=[
            {"id":"h1","plausible":True,"best_action":"A","probability":"1/2"},
            {"id":"h2","plausible":True,"best_action":"B","probability":"1/2"},
        ]
        out=router.route(
            goal="x",
            verified_coverage=False,
            required_facts={"x"},
            verified_facts=set(),
            transfer_mappings=[],
            hypotheses=hypotheses,
            actions=[
                {
                    "id":"useless",
                    "safe":True,
                    "outcome_by_hypothesis":{"h1":"s","h2":"s"},
                    "transfer_gain":100,
                    "time":1,
                }
            ],
        )
        self.assertEqual(out["route"],"ABSTAIN_OR_REQUEST_DISCRIMINATOR")

    def test_probability_weighting(self):
        hypotheses=[
            {"id":"h1","plausible":True,"best_action":"A","probability":"9/10"},
            {"id":"h2","plausible":True,"best_action":"B","probability":"1/10"},
        ]
        out=decision.rank(
            hypotheses=hypotheses,
            actions=[
                {
                    "id":"p",
                    "safe":True,
                    "outcome_by_hypothesis":{"h1":"l","h2":"r"},
                    "time":1,
                }
            ],
        )
        self.assertEqual(out[0]["derived_decision_gain"],"1/10")

    def test_meta_no_regression(self):
        episodes=[
            {
                "task_id":"t",
                "strategy_id":"old",
                "verified":True,
                "success":True,
                "safety_violation":False,
                "wall_clock":10,
                "reality_calls":2,
                "information_actions":5,
            },
            {
                "task_id":"t",
                "strategy_id":"new",
                "verified":True,
                "success":False,
                "safety_violation":False,
                "wall_clock":1,
                "reality_calls":0,
                "information_actions":1,
            },
        ]
        self.assertFalse(
            meta.compare(
                episodes=episodes,
                incumbent="old",
                candidate="new",
            )["preference_admissible"]
        )

    def test_meta_improvement_scoped(self):
        episodes=[
            {
                "task_id":"t",
                "strategy_id":"old",
                "verified":True,
                "success":True,
                "safety_violation":False,
                "wall_clock":10,
                "reality_calls":2,
                "information_actions":5,
            },
            {
                "task_id":"t",
                "strategy_id":"new",
                "verified":True,
                "success":True,
                "safety_violation":False,
                "wall_clock":5,
                "reality_calls":1,
                "information_actions":4,
            },
        ]
        comparison=meta.compare(
            episodes=episodes,
            incumbent="old",
            candidate="new",
        )
        policy=meta.compile_policy(
            environment_class="api",
            comparison=comparison,
            candidate_strategy="new",
            verification_receipt=receipt("meta"),
        )
        self.assertEqual(policy["scope"],"MATCHED_VERIFIED_ENVIRONMENT_CLASS_ONLY")
        self.assertFalse(policy["promotion_authorized"])


if __name__=="__main__":
    unittest.main(verbosity=2)
