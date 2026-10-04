from __future__ import annotations
import unittest

from canonical.runtime import mechanism_discovery_v6 as mech
from canonical.runtime import safe_adaptive_experiment_synthesizer_v6 as synth
from canonical.runtime import universal_learning_mechanism_router_v6 as router
from canonical.runtime import open_world_hypothesis_guard_v4 as guard4

ENV="env";GOAL="solve";EPOCH="epoch-1";STATE="state-1"

CANDIDATES=[
    {"id":"m1","best_action":"A","predictions":{"p":"x","q":"u"},"invariants":["i-common","i-1"],"provenance":["src-a"]},
    {"id":"m2","best_action":"A","predictions":{"p":"x","q":"v"},"invariants":["i-common","i-2"],"provenance":["src-b"]},
    {"id":"m3","best_action":"B","predictions":{"p":"y","q":"u"},"invariants":["i-common","i-3"],"provenance":["src-c"]},
]

def mechanism_hypotheses(candidates=CANDIDATES):
    return [{"id":c["id"],"plausible":True,"best_action":c["best_action"]} for c in candidates]

def coverage(candidates=CANDIDATES):
    hs=mechanism_hypotheses(candidates)
    return {
        "receipt_id":"coverage",
        "independent_verified":True,
        "exact_byte_bound":True,
        "conclusion":"success",
        "decision_relevant_exhaustive":True,
        "scope_relation":"EXACT",
        "environment_id":ENV,
        "goal_id":GOAL,
        "hypothesis_space_sha256":guard4.hypothesis_digest(hs),
    }

def class_digest(candidates=CANDIDATES):
    import hashlib,json
    rows=[]
    for c in mech.normalize_candidates(candidates):
        rows.append({"id":c["id"],"digest":c["digest"],"best_action":c["best_action"]})
    body=json.dumps(rows,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    return "sha256:"+hashlib.sha256(body).hexdigest()

def safe(pid):
    return {
        "receipt_id":"safe-"+pid,
        "independent_verified":True,
        "exact_byte_bound":True,
        "conclusion":"success",
        "safe_under_all_admissible_worlds":True,
        "environment_id":ENV,
        "goal_id":GOAL,
        "probe_id":pid,
        "experiment_epoch":EPOCH,
        "state_fingerprint":STATE,
    }

def probe(pid,outcomes,wall=1,candidates=CANDIDATES):
    return {
        "id":pid,
        "outcome_by_mechanism":outcomes,
        "wall_clock":wall,
        "resource_cost":0,
        "residual_risk":0,
        "incremental_spend_usd_ub":0,
        "safety_receipt":safe(pid),
        "outcome_model_receipt":{
            "receipt_id":"model-"+pid,
            "independent_verified":True,
            "exact_byte_bound":True,
            "conclusion":"success",
            "deterministic_within_bound_mechanism_class":True,
            "decision_relevant_outcome_partition_complete_within_class":True,
            "observation_only_or_state_restored":True,
            "experiment_epoch":EPOCH,
            "state_fingerprint":STATE,
            "environment_id":ENV,
            "goal_id":GOAL,
            "probe_id":pid,
            "mechanism_class_sha256":class_digest(candidates),
            "outcome_map_sha256":synth.outcome_digest(probe_id=pid,outcomes=outcomes),
        },
    }

class MechanismDiscoveryV6Tests(unittest.TestCase):
    def test_observation_eliminates_inconsistent_mechanisms(self):
        out=mech.update(candidates=CANDIDATES,observations=[{"probe_id":"p","outcome":"x"}])
        self.assertEqual([x["id"] for x in out["survivors"]],["m1","m2"])
        self.assertEqual([x["id"] for x in out["eliminated"]],["m3"])

    def test_all_candidates_falsified_requests_language_expansion(self):
        out=mech.update(candidates=CANDIDATES,observations=[{"probe_id":"p","outcome":"outside"}])
        self.assertEqual(out["status"],"MODEL_CLASS_FALSIFIED__EXPAND_HYPOTHESIS_LANGUAGE")
        self.assertFalse(out["true_mechanism_proved"])

    def test_single_survivor_is_not_truth(self):
        out=mech.update(
            candidates=CANDIDATES,
            observations=[{"probe_id":"p","outcome":"x"},{"probe_id":"q","outcome":"u"}],
        )
        self.assertEqual([x["id"] for x in out["survivors"]],["m1"])
        self.assertEqual(out["status"],"ONE_SURVIVING_CANDIDATE__NOT_VERIFIED_TRUTH")
        self.assertFalse(out["true_mechanism_proved"])

    def test_decision_quotient_collapses_same_action(self):
        out=mech.decision_quotient(CANDIDATES[:2])
        self.assertEqual(out["mechanism_count"],2)
        self.assertEqual(out["decision_class_count"],1)
        self.assertTrue(out["decision_sufficient_inside_declared_class"])
        self.assertFalse(out["open_world_sufficiency_proved"])

    def test_common_invariant_is_candidate_only(self):
        out=mech.common_invariant_candidates(CANDIDATES)
        self.assertEqual(out["candidate_invariants"],["i-common"])
        self.assertFalse(out["candidate_invariants"]==out["verified_invariants"])
        self.assertTrue(out["separate_verification_required"])

    def test_invariant_verification_requires_independent_receipt(self):
        receipt={
            "receipt_id":"inv","independent_verified":True,"exact_byte_bound":True,
            "conclusion":"success","behavior_preserving_on_claimed_scope":True,
            "scope_relation":"PROVEN_SUPERSET","invariant":"i-common",
            "source_mechanism_ids":["m1","m2"],
        }
        out=mech.verify_invariant_candidate(
            invariant="i-common",source_mechanism_ids=["m1","m2"],receipt=receipt
        )
        self.assertTrue(out["verified"])
        bad=dict(receipt);bad["independent_verified"]=False
        with self.assertRaises(mech.MechanismDiscoveryError):
            mech.verify_invariant_candidate(
                invariant="i-common",source_mechanism_ids=["m1","m2"],receipt=bad
            )

    def test_contradictory_observation_rejected(self):
        with self.assertRaises(mech.MechanismDiscoveryError):
            mech.normalize_observations([
                {"probe_id":"p","outcome":"x"},{"probe_id":"p","outcome":"y"}
            ])

class ExperimentSynthesizerV6Tests(unittest.TestCase):
    def test_exact_conditional_plan_without_open_world_closure(self):
        probes=[
            probe("cheap",{"m1":"x","m2":"x","m3":"y"},1),
            probe("expensive",{"m1":"a","m2":"b","m3":"c"},5),
        ]
        out=synth.synthesize(
            environment_id=ENV,goal_id=GOAL,candidates=CANDIDATES,probes=probes,
            hypothesis_coverage_receipt=None,
        )
        self.assertEqual(out["status"],"CONDITIONAL_EXACT_PLAN_OVER_DECLARED_MECHANISM_CLASS")
        self.assertFalse(out["open_world_terminal_decision_authorized"])
        self.assertEqual(out["recommended_probe"],"cheap")

    def test_closed_space_marks_open_world_exact_plan(self):
        probes=[probe("direct",{"m1":"a","m2":"a","m3":"b"},2)]
        out=synth.synthesize(
            environment_id=ENV,goal_id=GOAL,candidates=CANDIDATES,probes=probes,
            hypothesis_coverage_receipt=coverage(),
        )
        self.assertEqual(out["status"],"OPEN_WORLD_EXACT_ADAPTIVE_PLAN")
        self.assertTrue(out["open_world_terminal_decision_authorized"])

    def test_positive_spend_rejected(self):
        p=probe("p",{"m1":"a","m2":"a","m3":"b"},1)
        p["incremental_spend_usd_ub"]="0.01"
        with self.assertRaises(synth.ExperimentSynthesisError):
            synth.synthesize(
                environment_id=ENV,goal_id=GOAL,candidates=CANDIDATES,probes=[p]
            )

    def test_unverified_safety_rejected(self):
        p=probe("p",{"m1":"a","m2":"a","m3":"b"},1)
        p["safety_receipt"]["independent_verified"]=False
        with self.assertRaises(synth.ExperimentSynthesisError):
            synth.synthesize(
                environment_id=ENV,goal_id=GOAL,candidates=CANDIDATES,probes=[p]
            )

    def test_tampered_outcome_map_rejected(self):
        p=probe("p",{"m1":"a","m2":"a","m3":"b"},1)
        p["outcome_by_mechanism"]["m3"]="tampered"
        with self.assertRaises(synth.ExperimentSynthesisError):
            synth.synthesize(
                environment_id=ENV,goal_id=GOAL,candidates=CANDIDATES,probes=[p]
            )

    def test_multi_step_plan_can_beat_direct_expensive_probe(self):
        candidates=[
            {"id":"m1","best_action":"A","predictions":{"x":"0","y":"0"},"invariants":[],"provenance":[]},
            {"id":"m2","best_action":"B","predictions":{"x":"0","y":"1"},"invariants":[],"provenance":[]},
            {"id":"m3","best_action":"C","predictions":{"x":"1","y":"0"},"invariants":[],"provenance":[]},
            {"id":"m4","best_action":"D","predictions":{"x":"1","y":"1"},"invariants":[],"provenance":[]},
        ]
        def p(pid,outcomes,wall):
            q=probe(pid,outcomes,wall,candidates=candidates)
            return q
        probes=[
            p("direct",{"m1":"a","m2":"b","m3":"c","m4":"d"},5),
            p("x",{"m1":"0","m2":"0","m3":"1","m4":"1"},1),
            p("y",{"m1":"0","m2":"1","m3":"0","m4":"1"},1),
        ]
        out=synth.synthesize(
            environment_id=ENV,goal_id=GOAL,candidates=candidates,probes=probes
        )
        self.assertIn(out["recommended_probe"],{"x","y"})
        self.assertEqual(out["worst_case_wall_clock"],"2")
        self.assertEqual(out["worst_case_steps"],2)

class RouterV6Tests(unittest.TestCase):
    def base_kwargs(self):
        return dict(
            goal=GOAL,environment_id=ENV,verified_coverage=False,
            goal_facts=["solve"],fallback_required_facts=["solve"],
            verified_facts=[],dependencies={},dependency_receipt=None,
            transfer_mappings=[],mechanism_candidates=CANDIDATES,
            observations=[],hypothesis_coverage_receipt=None,
            residual_action_receipt=None,verified_skills=[],
        )

    def test_all_candidates_falsified_routes_to_model_language_expansion(self):
        kw=self.base_kwargs()
        kw["observations"]=[{"probe_id":"p","outcome":"outside"}]
        kw["probes"]=[]
        out=router.route(**kw)
        self.assertEqual(out["route"],"EXPAND_MECHANISM_LANGUAGE")
        self.assertEqual(out["next_action"]["type"],"GENERATE_NEW_MECHANISM_CANDIDATES")
        self.assertFalse(out["trusted_execution_authorized"])

    def test_safe_probe_selected_without_false_open_world_decision(self):
        kw=self.base_kwargs()
        kw["probes"]=[probe("p",{"m1":"x","m2":"x","m3":"y"},1)]
        out=router.route(**kw)
        self.assertEqual(out["route"],"LEARN")
        self.assertEqual(out["next_action"]["type"],"SAFE_PROBE")
        self.assertFalse(out["adaptive_plan"]["open_world_terminal_decision_authorized"])
        self.assertFalse(out["trusted_execution_authorized"])

    def test_v6_invariant_bundle(self):
        out=router.prove_v6_invariants()
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["m_open_model_expansion_preserved"])
        self.assertFalse(out["semantic_success_rate_proved"])
        self.assertFalse(out["unknown_domain_acceptance_proved"])
        self.assertEqual(out["acceptance_credit_delta"],0)
        self.assertFalse(out["promotion_authority"])

if __name__=="__main__":
    unittest.main(verbosity=2)
