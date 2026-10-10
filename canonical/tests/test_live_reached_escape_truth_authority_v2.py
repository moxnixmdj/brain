from __future__ import annotations
import unittest
from unittest.mock import patch

from canonical.runtime import unified_cognitive_fabric_v1 as fabric
from canonical.runtime import reached_escape_state_kernel_v1 as kernel
from canonical.runtime import certified_reached_escape_state_constructor_v2 as truth
from canonical.runtime import reached_escape_repair_cycle_v1 as cycle


def state(*, policies=(), discriminators=()):
    return {
        "schema": kernel.STATE_SCHEMA,
        "state_id": "S",
        "regions": [{"region_id": "r1"}, {"region_id": "r2"}],
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


def truth_receipt(claim, kind, verified):
    core = {
        "schema": truth.RECEIPT_SCHEMA,
        "pass": True,
        "claim_sha256": truth._digest(claim),
        "candidate_state_sha256": claim["candidate_state_sha256"],
        "authority_kind": kind,
        "authority_id": "TEST_REACHED_ESCAPE_TRUTH_AUTHORITY",
        "verification_authority_mutated": False,
        "verified": verified,
    }
    return {**core, "receipt_sha256": truth._digest(core)}


def multiplex_verifier(request):
    if request.get("schema") == truth.CLAIM_SCHEMA:
        kind = request["claim_type"]
        if kind == "POLICY_ADEQUACY_SAFETY_AND_RESOURCE":
            return truth_receipt(
                request,
                kind,
                {
                    "safe": True,
                    "adequate_region_ids": list(request["adequate_region_ids"]),
                    "resource_bound": {"amount": 3, "unit": "WORK_UNIT"},
                },
            )
        if kind == "DISCRIMINATOR_TRUTH_SAFETY_COMPLETENESS_AND_RESOURCE":
            return truth_receipt(
                request,
                kind,
                {
                    "safe": True,
                    "truthful": True,
                    "complete": True,
                    "outcomes": dict(request["outcomes"]),
                    "resource_bound": {"amount": 2, "unit": "WORK_UNIT"},
                },
            )
    if request.get("schema") == cycle.VERIFY_REQUEST_SCHEMA:
        return {
            "schema": cycle.VERIFY_SCHEMA,
            "pass": True,
            "state_sha256": request["state_sha256"],
            "repair_sha256": request["repair_sha256"],
            "repair_dispatch_sha256": request["repair_dispatch_sha256"],
            "alternative_id": request["alternative_id"],
            "candidate_sha256": request["candidate_sha256"],
            "candidate_kind": request["candidate_kind"],
            "verified_properties": [request["required_verified_property"]],
            "independent_verification": True,
            "verifier_id": "TEST_INDEPENDENT_REACHED_ESCAPE_VERIFIER",
            "promotion_authority": False,
            "acceptance_authority": False,
            "terminal_authority": False,
        }
    return None


def repair_provider(request):
    alternatives = [
        row for row in request["alternatives"]
        if row["basis"]["provider_kind"] == "EVIDENCE_ACQUISITION"
    ]
    assert len(alternatives) == 1
    return {
        "schema": cycle.CANDIDATE_SCHEMA,
        "pass": True,
        "repair_sha256": request["repair_sha256"],
        "repair_dispatch_sha256": request["repair_dispatch_sha256"],
        "alternative_id": alternatives[0]["alternative_id"],
        "candidate_kind": "DISCRIMINATOR",
        "candidate": {
            "discriminator_id": "d_verified",
            "outcomes": {"r1": "A", "r2": "B"},
        },
        "truth_authority": False,
        "verification_authority": False,
        "promotion_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
    }


class LiveReachedEscapeTruthBoundaryTests(unittest.TestCase):
    def _run(self, payload, **providers):
        with patch.object(
            fabric.improvement_driver,
            "drain",
            return_value={
                "status": "IMPROVEMENT_QUEUE_STABLE",
                "pass": True,
                "progress_count": 0,
                "actions": [],
            },
        ):
            return fabric.run({
                "mode": "REACHED_ESCAPE_STATE",
                "payload": payload,
                "options": {"learn": False},
            }, **providers)

    def test_caller_flags_cannot_create_live_reached_state_authority(self):
        spoofed = state(policies=[policy("fabricated-policy", ("r1", "r2"))])
        out = self._run(spoofed)
        self.assertFalse(out["inner_pass"], out)
        self.assertEqual(out["result"]["status"], "FAIL_CLOSED__REACHED_ESCAPE_TRUTH_AUTHORITY")
        self.assertIn("VERIFIER_REQUIRED", out["result"]["reason"])

    def test_repair_enabled_path_cannot_bypass_truth_authority(self):
        spoofed = state(policies=[policy("fabricated-policy", ("r1", "r2"))])
        calls = {"provider": 0}
        def provider(request):
            calls["provider"] += 1
            return None
        out = self._run(
            spoofed,
            capability_expander=provider,
            semantic_authority_verifier=lambda request: None,
        )
        self.assertFalse(out["inner_pass"], out)
        self.assertEqual(out["result"]["status"], "FAIL_CLOSED__REACHED_ESCAPE_TRUTH_AUTHORITY")
        self.assertEqual(calls["provider"], 0)

    def test_verified_common_policy_remains_live(self):
        out = self._run(
            state(policies=[policy("p", ("r1", "r2"))]),
            semantic_authority_verifier=multiplex_verifier,
        )
        self.assertTrue(out["inner_pass"], out)
        self.assertEqual(out["result"]["schema"], truth.SCHEMA)
        self.assertTrue(out["result"]["truth_authority_bound"])
        self.assertTrue(out["result"]["resource_admissibility_proved"])
        self.assertEqual(
            out["result"]["kernel_result"]["status"],
            "TERMINALIZE_WITH_COMMON_POLICY",
        )

    def test_verified_repair_is_v2_recertified_before_live_pass(self):
        out = self._run(
            state(policies=[
                policy("p1", ("r1",)),
                policy("p2", ("r2",)),
            ]),
            capability_expander=repair_provider,
            semantic_authority_verifier=multiplex_verifier,
        )
        self.assertTrue(out["inner_pass"], out)
        self.assertEqual(out["result"]["status"], "PASS__REACHED_ESCAPE_REPAIR_CYCLE_CLOSED")
        self.assertTrue(out["result"]["truth_recertification_pass"])
        self.assertEqual(out["result"]["final_result"]["schema"], truth.SCHEMA)
        self.assertTrue(out["result"]["final_result"]["truth_authority_bound"])
        self.assertTrue(out["result"]["final_result"]["resource_admissibility_proved"])
        self.assertEqual(out["result"]["repair_rounds_completed"], 1)

if __name__ == "__main__":
    unittest.main(verbosity=2)
