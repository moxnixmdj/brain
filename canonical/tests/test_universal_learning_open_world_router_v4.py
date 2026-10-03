import unittest
from canonical.runtime import goal_dependency_delta_v4 as delta
from canonical.runtime import open_world_hypothesis_guard_v4 as guard
from canonical.runtime import universal_learning_open_world_router_v4 as router

ENV="env"; GOAL="solve"

def dep_receipt(goals,deps):
    return {"receipt_id":"dep","independent_verified":True,"exact_byte_bound":True,"conclusion":"success","decision_relevant_dependency_graph_complete":True,"environment_id":ENV,"goal_id":GOAL,"dependency_graph_sha256":delta.dependency_digest(goals=goals,dependencies=deps)}

def cov_receipt(hs):
    return {"receipt_id":"cov","independent_verified":True,"exact_byte_bound":True,"conclusion":"success","decision_relevant_exhaustive":True,"scope_relation":"EXACT","environment_id":ENV,"goal_id":GOAL,"hypothesis_space_sha256":guard.hypothesis_digest(hs)}

def residual_receipt(action):
    return {"receipt_id":"res","independent_verified":True,"exact_byte_bound":True,"conclusion":"success","all_unmodeled_decision_relevant_alternatives_imply_action":True,"environment_id":ENV,"goal_id":GOAL,"action":action}

def safe(aid):
    return {"receipt_id":"safe-"+aid,"independent_verified":True,"exact_byte_bound":True,"conclusion":"success","safe_under_all_admissible_worlds":True,"environment_id":ENV,"goal_id":GOAL,"action_id":aid}

class V4Tests(unittest.TestCase):
    def test_goal_delta_prunes_irrelevant_branch_and_stops_at_verified_boundary(self):
        deps={"solve":["parse","execute"],"parse":["syntax"],"execute":["runtime"],"irrelevant":["noise"]}
        out=delta.minimum_goal_delta(environment_id=ENV,goal_id=GOAL,goals=["solve"],verified_facts=["parse"],dependencies=deps,dependency_receipt=dep_receipt(["solve"],deps))
        self.assertEqual(out["missing"],["execute","runtime","solve"])
        self.assertEqual(out["verified_boundary"],["parse"])
        self.assertNotIn("noise",out["missing"])

    def test_goal_delta_rejects_cycle(self):
        deps={"solve":["x"],"x":["solve"]}
        with self.assertRaises(delta.GoalDependencyDeltaError):
            delta.minimum_goal_delta(environment_id=ENV,goal_id=GOAL,goals=["solve"],verified_facts=[],dependencies=deps,dependency_receipt=dep_receipt(["solve"],deps))

    def test_open_hypothesis_space_cannot_stop_just_because_declared_models_agree(self):
        hs=[{"id":"h1","plausible":True,"best_action":"A","probability":"1/2"},{"id":"h2","plausible":True,"best_action":"A","probability":"1/2"}]
        out=guard.decision_sufficient(environment_id=ENV,goal_id=GOAL,hypotheses=hs)
        self.assertFalse(out["sufficient"])
        self.assertIn("OPEN_WORLD_RESIDUAL",out["reason"])

    def test_exhaustive_receipt_allows_decision_sufficiency(self):
        hs=[{"id":"h1","plausible":True,"best_action":"A"},{"id":"h2","plausible":True,"best_action":"A"}]
        out=guard.decision_sufficient(environment_id=ENV,goal_id=GOAL,hypotheses=hs,coverage_receipt=cov_receipt(hs))
        self.assertTrue(out["sufficient"])
        self.assertTrue(out["open_world_safe"])

    def test_residual_action_invariance_can_close_without_enumerating_every_world(self):
        hs=[{"id":"h1","plausible":True,"best_action":"A"},{"id":"h2","plausible":True,"best_action":"A"}]
        out=guard.decision_sufficient(environment_id=ENV,goal_id=GOAL,hypotheses=hs,residual_action_receipt=residual_receipt("A"))
        self.assertTrue(out["sufficient"])
        self.assertFalse(out["hypothesis_space_closed"])

    def test_stale_hypothesis_receipt_rejected(self):
        hs=[{"id":"h1","plausible":True,"best_action":"A"}]
        rec=cov_receipt(hs);rec["hypothesis_space_sha256"]="sha256:"+"0"*64
        with self.assertRaises(guard.OpenWorldHypothesisError):
            guard.decision_sufficient(environment_id=ENV,goal_id=GOAL,hypotheses=hs,coverage_receipt=rec)

    def test_probability_free_minimax_probe_ranking(self):
        hs=[{"id":"h1","plausible":True,"best_action":"A","probability":"999/1000"},{"id":"h2","plausible":True,"best_action":"B","probability":"1/1000"}]
        actions=[
            {"id":"useless","outcome_by_hypothesis":{"h1":"same","h2":"same"},"time":1,"safety_receipt":safe("useless")},
            {"id":"split","outcome_by_hypothesis":{"h1":"left","h2":"right"},"time":2,"safety_receipt":safe("split")},
        ]
        out=guard.robust_rank(environment_id=ENV,goal_id=GOAL,hypotheses=hs,actions=actions)
        self.assertEqual([x["id"] for x in out["ranked"]],["split"])
        self.assertFalse(out["probability_model_required"])

    def test_probe_without_open_world_safety_receipt_is_never_ranked(self):
        hs=[{"id":"h1","plausible":True,"best_action":"A"},{"id":"h2","plausible":True,"best_action":"B"}]
        out=guard.robust_rank(environment_id=ENV,goal_id=GOAL,hypotheses=hs,actions=[{"id":"p","outcome_by_hypothesis":{"h1":"x","h2":"y"},"time":1}])
        self.assertEqual(out["ranked"],[])
        self.assertEqual(out["rejected"][0]["id"],"p")

    def test_router_uses_goal_delta_and_refuses_false_consensus(self):
        deps={"solve":["needed"],"irrelevant":["noise"]}
        hs=[{"id":"h1","plausible":True,"best_action":"A"},{"id":"h2","plausible":True,"best_action":"A"}]
        out=router.route(goal=GOAL,environment_id=ENV,verified_coverage=False,goal_facts=["solve"],fallback_required_facts=["solve","needed","irrelevant","noise"],verified_facts=[],dependencies=deps,dependency_receipt=dep_receipt(["solve"],deps),transfer_mappings=[],hypotheses=hs,hypothesis_coverage_receipt=None,residual_action_receipt=None,actions=[])
        self.assertEqual(out["novelty_delta"]["missing"],["needed","solve"])
        self.assertEqual(out["route"],"ABSTAIN_OR_REQUEST_DISCRIMINATOR")

    def test_router_can_use_safe_probe_in_open_world(self):
        hs=[{"id":"h1","plausible":True,"best_action":"A"},{"id":"h2","plausible":True,"best_action":"B"}]
        out=router.route(goal=GOAL,environment_id=ENV,verified_coverage=False,goal_facts=["solve"],fallback_required_facts=["solve"],verified_facts=[],dependencies={},dependency_receipt=None,transfer_mappings=[],hypotheses=hs,hypothesis_coverage_receipt=None,residual_action_receipt=None,actions=[{"id":"p","outcome_by_hypothesis":{"h1":"x","h2":"y"},"time":1,"safety_receipt":safe("p")}])
        self.assertEqual(out["route"],"LEARN")
        self.assertEqual(out["next_action"]["id"],"p")
        self.assertEqual(out["acceptance_credit_delta"],0)
        self.assertFalse(out["fresh_reality_authority"])

if __name__=="__main__":
    unittest.main(verbosity=2)
