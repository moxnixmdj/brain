import unittest

from canonical.runtime.counterexample_guided_causal_architecture_synthesizer_v1 import synthesize


class CounterexampleGuidedArchitectureSynthesizerV1Tests(unittest.TestCase):
    def test_minimum_verified_hybrid_beats_slower_monolith(self):
        manifest = {
            "initial_facts": ["task.raw"],
            "components": [
                {
                    "id": "source-ingest",
                    "kind": "MECHANISM",
                    "requires": ["task.raw"],
                    "provides": ["source.ready"],
                    "verified": True,
                    "brain_owned": True,
                    "donor_independent": True,
                    "cost": {"wall_clock": 1},
                },
                {
                    "id": "artifact-builder",
                    "kind": "MECHANISM",
                    "requires": ["source.ready"],
                    "provides": ["artifact.complete"],
                    "verified": True,
                    "brain_owned": True,
                    "donor_independent": True,
                    "cost": {"wall_clock": 1},
                },
                {
                    "id": "slow-monolith",
                    "kind": "MECHANISM",
                    "requires": ["task.raw"],
                    "provides": ["artifact.complete"],
                    "verified": True,
                    "brain_owned": True,
                    "donor_independent": True,
                    "cost": {"wall_clock": 10},
                },
            ],
            "target": {"required_effects": ["artifact.complete"], "max_components": 3},
        }
        out = synthesize(manifest)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["winner"]["components"], ["artifact-builder", "source-ingest"])
        self.assertEqual(out["winner"]["wall_clock"], 2.0)

    def test_counterexample_forces_smallest_repair_gate(self):
        manifest = {
            "initial_facts": ["task.raw"],
            "components": [
                {
                    "id": "executor",
                    "kind": "MECHANISM",
                    "requires": ["task.raw"],
                    "provides": ["task.complete"],
                    "verified": True,
                    "brain_owned": True,
                    "donor_independent": True,
                    "cost": {"wall_clock": 1},
                },
                {
                    "id": "independent-acceptance",
                    "kind": "VERIFIER",
                    "requires": ["task.complete"],
                    "provides": ["task.accepted"],
                    "verified": True,
                    "brain_owned": True,
                    "donor_independent": True,
                    "cost": {"wall_clock": 1},
                },
            ],
            "counterexamples": [
                {
                    "id": "false-finish",
                    "trigger_all": ["task.complete"],
                    "repair_any": ["task.accepted"],
                }
            ],
            "target": {"required_effects": ["task.complete"], "max_components": 2},
        }
        out = synthesize(manifest)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["winner"]["components"], ["executor", "independent-acceptance"])
        self.assertIn("task.accepted", out["winner"]["closure"])

    def test_missing_causal_effect_is_named_instead_of_inventing_family(self):
        manifest = {
            "initial_facts": ["chart.image"],
            "components": [
                {
                    "id": "ocr",
                    "kind": "MECHANISM",
                    "requires": ["chart.image"],
                    "provides": ["chart.text"],
                    "verified": True,
                    "brain_owned": True,
                    "donor_independent": True,
                    "cost": {"wall_clock": 1},
                }
            ],
            "target": {"required_effects": ["chart.visual-reasoning"], "max_components": 1},
        }
        out = synthesize(manifest)
        self.assertFalse(out["pass"])
        self.assertEqual(out["classification"], "NEW_PRIMITIVE_REQUIRED")
        self.assertEqual(out["missing_required_effects"], ["chart.visual-reasoning"])

    def test_donor_bound_component_is_rejected(self):
        manifest = {
            "components": [
                {
                    "id": "opaque-donor",
                    "kind": "MECHANISM",
                    "requires": [],
                    "provides": ["goal.done"],
                    "verified": True,
                    "brain_owned": False,
                    "donor_independent": False,
                    "cost": {"wall_clock": 0},
                }
            ],
            "target": {"required_effects": ["goal.done"], "max_components": 1},
        }
        out = synthesize(manifest)
        self.assertFalse(out["pass"])
        self.assertEqual(out["classification"], "NEW_PRIMITIVE_REQUIRED")
        self.assertEqual(out["rejected_component_ids"], ["opaque-donor"])

    def test_candidate_component_can_be_synthesized_but_not_promoted(self):
        manifest = {
            "allow_candidate_components": True,
            "components": [
                {
                    "id": "new-discriminator",
                    "kind": "DISCRIMINATOR",
                    "requires": [],
                    "provides": ["policy.selector"],
                    "verified": False,
                    "brain_owned": True,
                    "donor_independent": True,
                    "cost": {"wall_clock": 1, "persistent_bits": 0},
                }
            ],
            "target": {"required_effects": ["policy.selector"], "max_components": 1},
        }
        out = synthesize(manifest)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["winner"]["verification_required"], ["new-discriminator"])
        self.assertTrue(out["requires_independent_verification_before_promotion"])
        self.assertFalse(out["terminal_credit"])

    def test_positive_incremental_spend_is_inadmissible(self):
        manifest = {
            "components": [
                {
                    "id": "paid-oracle",
                    "kind": "MECHANISM",
                    "requires": [],
                    "provides": ["answer"],
                    "verified": True,
                    "brain_owned": True,
                    "donor_independent": True,
                    "cost": {"wall_clock": 0, "incremental_spend_usd": 0.01},
                }
            ],
            "target": {"required_effects": ["answer"], "max_components": 1},
        }
        out = synthesize(manifest)
        self.assertFalse(out["pass"])
        self.assertEqual(out["rejected_component_ids"], ["paid-oracle"])

    def test_unreachable_dependency_does_not_count_as_architecture(self):
        manifest = {
            "components": [
                {
                    "id": "downstream",
                    "kind": "MECHANISM",
                    "requires": ["missing.input"],
                    "provides": ["goal.done"],
                    "verified": True,
                    "brain_owned": True,
                    "donor_independent": True,
                    "cost": {"wall_clock": 1},
                }
            ],
            "target": {"required_effects": ["goal.done"], "max_components": 1},
        }
        out = synthesize(manifest)
        self.assertFalse(out["pass"])
        self.assertEqual(out["classification"], "NO_ADMISSIBLE_ARCHITECTURE_WITHIN_BOUND")

    def test_tie_break_is_deterministic(self):
        components = []
        for cid in ["b", "a"]:
            components.append(
                {
                    "id": cid,
                    "kind": "MECHANISM",
                    "requires": [],
                    "provides": ["goal"],
                    "verified": True,
                    "brain_owned": True,
                    "donor_independent": True,
                    "cost": {"wall_clock": 1},
                }
            )
        out = synthesize({"components": components, "target": {"required_effects": ["goal"], "max_components": 1}})
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["winner"]["components"], ["a"])


if __name__ == "__main__":
    unittest.main()
