import unittest
from canonical.runtime import open_world_hypothesis_guard_v4 as guard
from canonical.runtime import verified_probe_model_v5 as model
from canonical.runtime import adaptive_experiment_planner_v5 as planner
from canonical.runtime import universal_learning_adaptive_router_v5 as router

ENV="env-v5";GOAL="solve"
HS=[
    {"id":"h1","plausible":True,"best_action":"A"},
    {"id":"h2","plausible":True,"best_action":"A"},
    {"id":"h3","plausible":True,"best_action":"B"},
    {"id":"h4","plausible":True,"best_action":"B"},
]
def cov():
    return {"receipt_id":"cov","independent_verified":True,"exact_byte_bound":True,"conclusion":"success","decision_relevant_exhaustive":True,"scope_relation":"EXACT","environment_id":ENV,"goal_id":GOAL,"hypothesis_space_sha256":guard.hypothesis_digest(HS)}
def safe(aid):
    return {"receipt_id":"safe-"+aid,"independent_verified":True,"exact_byte_bound":True,"conclusion":"success","safe_under_all_admissible_worlds":True,"environment_id":ENV,"goal_id":GOAL,"action_id":aid}
def probe(aid,outcomes,cost):
    od=model.outcome_digest(action_id=aid,outcomes=outcomes)
    return {"id":aid,"outcome_by_hypothesis":outcomes,"time":cost,"safety_receipt":safe(aid),"outcome_model_receipt":{"receipt_id":"model-"+aid,"independent_verified":True,"exact_byte_bound":True,"conclusion":"success","decision_relevant_outcome_partition_complete":True,"environment_id":ENV,"goal_id":GOAL,"action_id":aid,"hypothesis_space_sha256":guard.hypothesis_digest(HS),"outcome_map_sha256":od}}
def probes():
    return [
      probe("direct",{"h1":"a","h2":"a","h3":"b","h4":"b"},5),
      probe("x",{"h1":"x","h2":"y","h3":"x","h4":"y"},1),
      probe("y",{"h1":"u","h2":"v","h3":"v","h4":"u"},1),
    ]

class Tests(unittest.TestCase):
    def test_outcome_model_digest_is_load_bearing(self):
        p=probe("x",{"h1":"x","h2":"y","h3":"x","h4":"y"},1)
        p["outcome_by_hypothesis"]["h4"]="tampered"
        with self.assertRaises(model.VerifiedProbeModelError):
            model.admit(environment_id=ENV,goal_id=GOAL,hypotheses=HS,probe=p)

    def test_unverified_outcome_model_rejected(self):
        p=probe("x",{"h1":"x","h2":"y","h3":"x","h4":"y"},1)
        p["outcome_model_receipt"]["independent_verified"]=False
        with self.assertRaises(model.VerifiedProbeModelError):
            model.admit(environment_id=ENV,goal_id=GOAL,hypotheses=HS,probe=p)

    def test_adaptive_plan_beats_greedy_direct_probe(self):
        out=planner.plan(environment_id=ENV,goal_id=GOAL,hypotheses=HS,hypothesis_coverage_receipt=cov(),probes=probes())
        self.assertEqual(out["status"],"VERIFIED_MINIMUM_WORST_CASE_ADAPTIVE_PLAN")
        self.assertIn(out["recommended_probe"],{"x","y"})
        self.assertEqual(out["worst_case_cost"],"2")
        self.assertEqual(out["worst_case_steps"],2)

    def test_closed_hypothesis_space_required(self):
        with self.assertRaises(Exception):
            planner.plan(environment_id=ENV,goal_id=GOAL,hypotheses=HS,hypothesis_coverage_receipt=None,probes=probes())

    def test_no_plan_when_verified_probes_cannot_resolve_actions(self):
        only=[probe("useless",{"h1":"z","h2":"z","h3":"z","h4":"z"},1)]
        out=planner.plan(environment_id=ENV,goal_id=GOAL,hypotheses=HS,hypothesis_coverage_receipt=cov(),probes=only)
        self.assertEqual(out["status"],"NO_VERIFIED_ADAPTIVE_RESOLUTION_PLAN")

    def test_router_refuses_unverified_probe_model(self):
        bad=probe("x",{"h1":"x","h2":"y","h3":"x","h4":"y"},1)
        bad["outcome_model_receipt"]["outcome_map_sha256"]="sha256:"+"0"*64
        out=router.route(goal=GOAL,environment_id=ENV,verified_coverage=False,goal_facts=["solve"],fallback_required_facts=["solve"],verified_facts=[],dependencies={},dependency_receipt=None,transfer_mappings=[],hypotheses=HS,hypothesis_coverage_receipt=cov(),residual_action_receipt=None,probes=[bad])
        self.assertEqual(out["route"],"ABSTAIN_OR_REQUEST_VERIFIED_MODEL")

    def test_router_selects_verified_adaptive_first_probe(self):
        out=router.route(goal=GOAL,environment_id=ENV,verified_coverage=False,goal_facts=["solve"],fallback_required_facts=["solve"],verified_facts=[],dependencies={},dependency_receipt=None,transfer_mappings=[],hypotheses=HS,hypothesis_coverage_receipt=cov(),residual_action_receipt=None,probes=probes())
        self.assertEqual(out["route"],"LEARN")
        self.assertIn(out["next_action"]["id"],{"x","y"})
        self.assertEqual(out["adaptive_plan"]["worst_case_cost"],"2")
        self.assertEqual(out["acceptance_credit_delta"],0)

if __name__=="__main__": unittest.main(verbosity=2)
