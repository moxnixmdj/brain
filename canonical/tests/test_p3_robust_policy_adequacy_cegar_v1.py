import json
import tempfile
import unittest
from pathlib import Path

import canonical.runtime.p3_robust_policy_adequacy_cegar_v1 as kernel


class P3RobustPolicyAdequacyCegarV1Tests(unittest.TestCase):
    def setUp(self):
        self._old_root = kernel.ROOT
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        kernel.ROOT = self.root
        (self.root / "canonical/governance").mkdir(parents=True)
        (self.root / "canonical/verification").mkdir(parents=True)

    def tearDown(self):
        kernel.ROOT = self._old_root
        self._tmp.cleanup()

    def _binding(self, policy_id, condition):
        gov = self.root / "canonical/governance" / f"{policy_id}.json"
        ver = self.root / "canonical/verification" / f"{policy_id}.json"
        gov.write_text(
            json.dumps(
                {
                    "schema": kernel.ADEQUACY_SCHEMA,
                    "policy_id": policy_id,
                    "policy_condition_sha256": kernel._condition_sha256(condition),
                    "adequacy_proved": True,
                    "brain_owned": True,
                    "load_bearing_constraints_preserved": True,
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        gov_blob = kernel._git_blob_sha(gov)
        ver.write_text(
            json.dumps(
                {
                    "schema": kernel.VERIFY_SCHEMA,
                    "policy_id": policy_id,
                    "subject_git_blob_sha": gov_blob,
                    "pass": True,
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        return {
            "adequacy_certificate_path": f"canonical/governance/{policy_id}.json",
            "adequacy_certificate_blob_sha": gov_blob,
            "independent_verification_path": f"canonical/verification/{policy_id}.json",
            "independent_verification_blob_sha": kernel._git_blob_sha(ver),
        }

    def test_common_policy_is_proved_over_every_surviving_model(self):
        x = {"op": "ATOM", "id": "x"}
        binding = self._binding("p", x)
        out = kernel.solve(
            {
                "decision_basis": ["x"],
                "formal_source_constraints": [x],
                "proposed_refinements": [x],
                "policy_conditions": {"p": x},
                "policy_adequacy_bindings": {"p": binding},
            }
        )
        self.assertTrue(out["pass"])
        self.assertEqual(
            out["status"], "COMMON_POLICY_CERTIFIED_ACROSS_ALL_SURVIVING_MODELS"
        )
        self.assertEqual(out["selected_policy_id"], "p")
        self.assertEqual(out["surviving_model_count"], 1)
        self.assertTrue(out["policy_adequacy_authority"])
        self.assertFalse(out["db_admission_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_exact_one_bit_discriminator_is_selected_when_it_resolves_both_branches(self):
        x = {"op": "ATOM", "id": "x"}
        not_x = {"op": "NOT", "arg": x}
        out = kernel.solve(
            {
                "decision_basis": ["x"],
                "policy_conditions": {"p_true": x, "p_false": not_x},
                "policy_adequacy_bindings": {
                    "p_true": self._binding("p_true", x),
                    "p_false": self._binding("p_false", not_x),
                },
                "discriminators": [
                    {
                        "discriminator_id": "observe_x",
                        "formula": x,
                        "cost_units": 1,
                    }
                ],
            }
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNRESOLVED__MINIMUM_ONE_STEP_POLICY_CHANGING_DISCRIMINATOR_SELECTED",
        )
        self.assertEqual(
            out["selected_discriminator"]["discriminator_id"], "observe_x"
        )
        branches = {
            row["outcome"]: row["selected_policy_id"]
            for row in out["selected_discriminator"]["branches"]
        }
        self.assertEqual(branches, {False: "p_false", True: "p_true"})
        self.assertTrue(out["truthful_discriminator_observation_required"])
        self.assertFalse(out["terminal_authority"])

    def test_missing_adequacy_authentication_blocks_policy_use(self):
        x = {"op": "ATOM", "id": "x"}
        out = kernel.solve(
            {
                "decision_basis": ["x"],
                "policy_conditions": {"p": x},
                "discriminators": [
                    {"discriminator_id": "observe_x", "formula": x, "cost_units": 0}
                ],
            }
        )
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "NO_AUTHENTICATED_POLICY_ADEQUACY")

    def test_policy_cover_hole_blocks_discriminator_selection(self):
        x = {"op": "ATOM", "id": "x"}
        out = kernel.solve(
            {
                "decision_basis": ["x"],
                "policy_conditions": {"p_true": x},
                "policy_adequacy_bindings": {
                    "p_true": self._binding("p_true", x),
                },
                "discriminators": [
                    {"discriminator_id": "observe_x", "formula": x, "cost_units": 1}
                ],
            }
        )
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "AUTHENTICATED_POLICY_COVER_INCOMPLETE")
        self.assertEqual(out["detail"]["uncovered_models"][0]["valuation"], {"x": False})

    def test_unproved_refinement_cannot_shrink_state(self):
        x = {"op": "ATOM", "id": "x"}
        not_x = {"op": "NOT", "arg": x}
        out = kernel.solve(
            {
                "decision_basis": ["x"],
                "formal_source_constraints": [],
                "proposed_refinements": [x],
                "policy_conditions": {"p_true": x, "p_false": not_x},
                "policy_adequacy_bindings": {
                    "p_true": self._binding("p_true", x),
                    "p_false": self._binding("p_false", not_x),
                },
                "discriminators": [
                    {"discriminator_id": "observe_x", "formula": x, "cost_units": 1}
                ],
            }
        )
        self.assertEqual(out["surviving_model_count"], 2)
        self.assertEqual(len(out["semantic_state"]["rejected_refinements"]), 1)
        self.assertEqual(
            out["selected_discriminator"]["discriminator_id"], "observe_x"
        )

    def test_cheapest_resolving_discriminator_wins_deterministically(self):
        x = {"op": "ATOM", "id": "x"}
        not_x = {"op": "NOT", "arg": x}
        out = kernel.solve(
            {
                "decision_basis": ["x"],
                "policy_conditions": {"p_true": x, "p_false": not_x},
                "policy_adequacy_bindings": {
                    "p_true": self._binding("p_true", x),
                    "p_false": self._binding("p_false", not_x),
                },
                "discriminators": [
                    {"discriminator_id": "expensive", "formula": x, "cost_units": 9},
                    {"discriminator_id": "cheap", "formula": x, "cost_units": 1},
                ],
            }
        )
        self.assertEqual(out["selected_discriminator"]["discriminator_id"], "cheap")

    def test_nonresolving_declared_discriminator_preserves_counterexample(self):
        x = {"op": "ATOM", "id": "x"}
        y = {"op": "ATOM", "id": "y"}
        not_x = {"op": "NOT", "arg": x}
        out = kernel.solve(
            {
                "decision_basis": ["x", "y"],
                "policy_conditions": {"p_true": x, "p_false": not_x},
                "policy_adequacy_bindings": {
                    "p_true": self._binding("p_true", x),
                    "p_false": self._binding("p_false", not_x),
                },
                "discriminators": [
                    {"discriminator_id": "observe_y", "formula": y, "cost_units": 1}
                ],
            }
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNRESOLVED__NO_DECLARED_ONE_STEP_DISCRIMINATOR_CLOSES_POLICY_REGIONS",
        )
        self.assertIsNotNone(out["conflicting_policy_region_witness"])
        self.assertFalse(out["terminal_authority"])

    def test_forged_verification_subject_is_rejected(self):
        x = {"op": "ATOM", "id": "x"}
        binding = self._binding("p", x)
        ver = self.root / binding["independent_verification_path"]
        payload = json.loads(ver.read_text(encoding="utf-8"))
        payload["subject_git_blob_sha"] = "0" * 40
        ver.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        binding["independent_verification_blob_sha"] = kernel._git_blob_sha(ver)

        out = kernel.solve(
            {
                "decision_basis": ["x"],
                "formal_source_constraints": [x],
                "proposed_refinements": [x],
                "policy_conditions": {"p": x},
                "policy_adequacy_bindings": {"p": binding},
            }
        )
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "NO_AUTHENTICATED_POLICY_ADEQUACY")


if __name__ == "__main__":
    unittest.main()
