from __future__ import annotations
import unittest
import json
from canonical.runtime import current_escape_q_qualitative_acceptance_v1 as q
from canonical.runtime import robust_common_policy_db_admission_v1 as robust
from canonical.runtime import qualitative_pairwise_prompt_nonentailment_v1 as nonent

class CurrentEscapeQQualitativeAcceptanceTests(unittest.TestCase):
    def test_current_q_rows_are_covered_by_shared_acceptance_relation_law(self):
        out=q.evaluate_current()
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["current_q_count"],2)
        self.assertEqual(out["current_q_rows"],[
            "PROWORK_GDPVAL_GE_1846",
            "PROWORK_AA_BRIEFCASE_GE_1822__SHARED_MEASUREMENT_WITH_ARTIFACT",
        ])
        self.assertTrue(out["shared_q_acceptance_law_bound"])
        self.assertFalse(out["all_current_q_rows_closed"])
        self.assertEqual(out["current_q_row_acceptance_closed_count"],0)
        self.assertFalse(out["prompt_metadata_alone_sufficient"])
        self.assertIn("ROBUST_COMMON_POLICY",out["sound_closure_routes"])
        self.assertIn("MINIMUM_AUTHENTIC_RELATION_INFORMATION",out["sound_closure_routes"])

    def test_unknown_q_row_fails_closed(self):
        oq={"reduction":{
            "current_frontier_row_count":1,
            "O_OBJECTIVE_ACCEPTANCE":0,
            "Q_QUALITATIVE_RELATIVE_ORDER":1,
            "mixed":0,
            "unclassified":0,
            "Q_rows":["UNKNOWN_Q"],
        }}
        frozen={"exhaustive_rows":[
            {"obligation":"KNOWN_Q","regime":"Q_QUALITATIVE_RELATIVE_ORDER","basis":"x"}
        ]}
        theorem={"theorem":"x","special_cases":{"Q_QUALITATIVE_RELATIVE_ORDER":"x"}}
        cut={"minimum_information_cut":{"sufficient_disjunction":["A","B","C"]}}
        out=q.evaluate(oq,frozen,theorem,cut)
        self.assertFalse(out["pass"])
        self.assertIn("UNKNOWN_Q",out["missing_from_frozen_q_universe"])

    def test_public_prompt_metadata_alone_still_does_not_entail_preference(self):
        spec={
            "shared_contract":{
                "prompt_blob_sha":"1"*40,
                "input_digest":"2"*64,
                "judge_identities":["J1","J2"],
                "aggregation_digest":"3"*64,
                "output_schema":"PAIRWISE_A_OR_B",
            },
            "worlds":[
                {"same_public_contract":True,"judge_semantics_bound":False,"preference":"A"},
                {"same_public_contract":True,"judge_semantics_bound":False,"preference":"B"},
            ],
        }
        out=nonent.evaluate(spec)
        self.assertTrue(out["pass"])
        self.assertFalse(out["unique_preference_entailed"])

    def test_robust_policy_route_requires_complete_possibility_set(self):
        payload={
            "cell_id":"Q_CELL",
            "policy_id":"P",
            "cell_scope_sound":True,
            "possibility_set_complete":False,
            "all_load_bearing_terminal_dimensions_bound":True,
            "brain_owned_policy_proved":True,
            "deployed_route_exactly_realizes_policy":True,
            "authorized_resource_bound_proved":True,
            "worlds":[
                {"world_id":"W1","policy_adequate":True,"adequacy_independently_verified":True,"hard_constraints_satisfied":True}
            ],
            "content_bindings":{"x":"y"},
        }
        out=robust.evaluate(payload)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"POSSIBILITY_SET_COMPLETENESS_UNPROVED")

    def test_robust_policy_route_passes_only_with_all_worlds_adequate(self):
        payload={
            "cell_id":"Q_CELL",
            "policy_id":"P",
            "cell_scope_sound":True,
            "possibility_set_complete":True,
            "all_load_bearing_terminal_dimensions_bound":True,
            "brain_owned_policy_proved":True,
            "deployed_route_exactly_realizes_policy":True,
            "authorized_resource_bound_proved":True,
            "worlds":[
                {"world_id":"W1","policy_adequate":True,"adequacy_independently_verified":True,"hard_constraints_satisfied":True},
                {"world_id":"W2","policy_adequate":True,"adequacy_independently_verified":True,"hard_constraints_satisfied":True},
            ],
            "content_bindings":{"relation_set":"sha256:x"},
        }
        out=robust.evaluate(payload)
        self.assertTrue(out["pass"])
        self.assertTrue(out["db_admission_authorized"])
        self.assertFalse(out["terminal_authority"])


    def test_activation_binds_exact_bytes_and_preserves_zero_q_row_credit(self):
        root=q.ROOT
        activation=json.loads((root/"canonical/governance/ESCAPE_Q_QUALITATIVE_ACCEPTANCE_SHARED_LAW_ACTIVATION_20261010_V1.json").read_text())
        runtime_path=root/activation["runtime"]["path"]
        test_path=root/activation["tests"]["path"]
        self.assertEqual(q._git_blob_sha_bytes(runtime_path.read_bytes()),activation["runtime"]["git_blob_sha"])
        self.assertEqual(q._git_blob_sha_bytes(test_path.read_bytes()),activation["tests"]["git_blob_sha"])
        self.assertTrue(activation["current_frontier"]["shared_q_law_bound"])
        self.assertEqual(activation["current_frontier"]["current_q_row_acceptance_closed_count"],0)
        self.assertFalse(activation["current_frontier"]["prompt_metadata_alone_sufficient"])


    def test_current_oq_pointer_projects_both_shared_laws_without_row_credit(self):
        root=q.ROOT
        current=json.loads((root/"canonical/governance/CURRENT_ESCAPE_OQ_FRONTIER_REDUCTION_20261010_V1.json").read_text())
        self.assertTrue(current["objective_acceptance_shared_law"]["shared_law_bound"])
        self.assertTrue(current["qualitative_acceptance_shared_law"]["shared_law_bound"])
        self.assertEqual(current["objective_acceptance_shared_law"]["current_o_row_acceptance_closed_count"],0)
        self.assertEqual(current["qualitative_acceptance_shared_law"]["current_q_row_acceptance_closed_count"],0)
        self.assertFalse(current["qualitative_acceptance_shared_law"]["prompt_metadata_alone_sufficient"])
        self.assertIn("NO_CURRENT_Q_ROW_ACCEPTANCE_CLOSURE__SHARED_Q_IMPLICATION_ONLY",current["hard_nonclaims"])

if __name__=="__main__":
    unittest.main(verbosity=2)
