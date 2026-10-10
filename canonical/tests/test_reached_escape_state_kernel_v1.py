from __future__ import annotations

import copy
import unittest

from canonical.runtime import reached_escape_state_kernel_v1 as k


def state(*, regions=("r1","r2"), policies=(), discriminators=()):
    return {
        "schema": k.STATE_SCHEMA,
        "state_id": "S",
        "regions": [{"region_id": rid} for rid in regions],
        "policies": list(policies),
        "discriminators": list(discriminators),
    }


def policy(pid, covers):
    return {
        "policy_id": pid,
        "authenticated": True,
        "safe": True,
        "adequate_region_ids": list(covers),
    }


def disc(did, outcomes):
    return {
        "discriminator_id": did,
        "authenticated": True,
        "safe": True,
        "truthful": True,
        "complete": True,
        "outcomes": dict(outcomes),
    }


class ReachedEscapeStateKernelV1Tests(unittest.TestCase):
    def test_common_policy_terminalizes_deterministically(self):
        s=state(policies=[policy("p2",["r1","r2"]),policy("p1",["r1","r2"])])
        out=k.evaluate(s)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["status"],"TERMINALIZE_WITH_COMMON_POLICY")
        self.assertEqual(out["selected_policy_id"],"p1")
        self.assertTrue(out["reached_state_progress_proved"])
        self.assertFalse(out["global_escape_progress_totality_proved"])

    def test_minimax_splitter_is_selected(self):
        s=state(
            regions=("r1","r2","r3","r4"),
            policies=[policy("a",["r1"]),policy("b",["r2"]),policy("c",["r3"]),policy("d",["r4"])],
            discriminators=[
                disc("weak",{"r1":0,"r2":0,"r3":0,"r4":1}),
                disc("balanced",{"r1":0,"r2":0,"r3":1,"r4":1}),
            ],
        )
        out=k.evaluate(s)
        self.assertEqual(out["status"],"STRICT_PROGRESS_WITH_DISCRIMINATOR")
        self.assertEqual(out["selected_discriminator_id"],"balanced")
        self.assertEqual(out["maximum_branch_region_count"],2)
        self.assertTrue(out["all_nonempty_branches_strict_subsets"])
        self.assertFalse(out["next_action"]["execution_authority"])

    def test_constant_discriminators_do_not_fake_progress(self):
        s=state(
            policies=[policy("a",["r1"]),policy("b",["r2"])],
            discriminators=[disc("q",{"r1":"same","r2":"same"})],
        )
        out=k.evaluate(s)
        self.assertEqual(out["status"],"UNSPLITTABLE_POLICY_CONFLICT")
        self.assertFalse(out["reached_state_progress_proved"])

    def test_unsplittable_obstruction_and_repair_are_content_addressed(self):
        s=state(policies=[policy("a",["r1"]),policy("b",["r2"])])
        a=k.evaluate(s); b=k.evaluate(copy.deepcopy(s))
        self.assertEqual(a["obstruction_sha256"],b["obstruction_sha256"])
        self.assertEqual(a["repair_request"]["request_sha256"],b["repair_request"]["request_sha256"])
        classes={x["repair_class"] for x in a["repair_request"]["required_postcondition_any"]}
        self.assertEqual(classes,{
            "ACQUIRE_TRUTHFUL_DISTINGUISHING_OBSERVATION",
            "ACQUIRE_OR_SYNTHESIZE_COMMON_ADEQUATE_POLICY",
        })
        self.assertFalse(a["repair_request"]["global_acquirability_claimed"])

    def test_adding_common_policy_repairs_unsplittable_class(self):
        s=state(policies=[policy("a",["r1"]),policy("b",["r2"])])
        self.assertEqual(k.evaluate(s)["status"],"UNSPLITTABLE_POLICY_CONFLICT")
        s["policies"].append(policy("common",["r1","r2"]))
        self.assertEqual(k.evaluate(s)["status"],"TERMINALIZE_WITH_COMMON_POLICY")

    def test_adding_splitter_repairs_unsplittable_class(self):
        s=state(policies=[policy("a",["r1"]),policy("b",["r2"])])
        self.assertEqual(k.evaluate(s)["status"],"UNSPLITTABLE_POLICY_CONFLICT")
        s["discriminators"].append(disc("q",{"r1":"x","r2":"y"}))
        self.assertEqual(k.evaluate(s)["status"],"STRICT_PROGRESS_WITH_DISCRIMINATOR")

    def test_incomplete_discriminator_fails_closed(self):
        s=state(discriminators=[disc("q",{"r1":0})])
        out=k.evaluate(s)
        self.assertFalse(out["pass"])
        self.assertIn("OUTCOME_DOMAIN_NOT_EXACT",out["reason"])

    def test_untrusted_policy_fails_closed(self):
        bad=policy("p",["r1","r2"]); bad["authenticated"]=False
        out=k.evaluate(state(policies=[bad]))
        self.assertFalse(out["pass"])
        self.assertIn("POLICY_NOT_AUTHENTICATED_SAFE",out["reason"])

    def test_duplicate_region_fails_closed(self):
        out=k.evaluate(state(regions=("r1","r1")))
        self.assertFalse(out["pass"])
        self.assertIn("DUPLICATE_REGION_ID",out["reason"])

    def test_single_region_without_common_policy_is_truthful_obstruction(self):
        out=k.evaluate(state(regions=("r1",)))
        self.assertEqual(out["status"],"UNSPLITTABLE_POLICY_CONFLICT")
        self.assertFalse(out["open_ended_mission_terminal_proved"])

    def test_no_outcome_claims_global_terminal_success(self):
        cases=[
            state(policies=[policy("p",["r1","r2"])]),
            state(policies=[policy("a",["r1"]),policy("b",["r2"])],discriminators=[disc("q",{"r1":0,"r2":1})]),
            state(policies=[policy("a",["r1"]),policy("b",["r2"])]),
        ]
        for s in cases:
            out=k.evaluate(s)
            self.assertFalse(out["global_escape_progress_totality_proved"])
            self.assertFalse(out["open_ended_mission_terminal_proved"])
            self.assertFalse(out["terminal_authority"])
            self.assertEqual(out["terminal_credit_delta"],0)


if __name__=="__main__":
    unittest.main(verbosity=2)
