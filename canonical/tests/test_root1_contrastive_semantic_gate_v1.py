import copy
import unittest

from canonical.runtime import root1_contrastive_semantic_gate_v1 as gate


GOOD = {
    "PARA_A": "Before sunrise Tuesday, Neris brought seven amber parcels to Corin.",
    "PARA_B": "After sunset Wednesday, Neris brought nine blue parcels to Corin.",
    "SIMPLE_A": "Yusuf shut Pump 3 as the eastern valve hit 82 degrees, before moving 45 liters to Tank B.",
    "SIMPLE_B": "Yusuf opened Pump 3 after the western valve fell below 18 degrees, moving 15 liters from Tank B.",
    "SUM_A": "Train 8, delayed 35 minutes outside Luxor, had two signal boxes inspected with no damage and reached Aswan at 21:10.",
    "SUM_B": "Train 8 stopped 50 minutes near Edfu, where three signal boxes showed damage, then returned to Luxor at 22:40.",
    "STORY_A": "ORION-7 found BRASS-KEY at GATE-2. It crossed HARBOR-9 carrying the key safely. ORION-7 returned BRASS-KEY to MIRA-1.",
    "STORY_B": "ORION-7 found SILVER-RING at GATE-2. It crossed TUNNEL-4 while protecting the ring. ORION-7 gave SILVER-RING to MIRA-1.",
}


class Root1ContrastiveSemanticGateTests(unittest.TestCase):
    def test_good_contrastive_suite_passes(self):
        out = gate.evaluate_suite(GOOD)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["case_pass_count"], 8)
        self.assertTrue(all(out["pair_distinction_checks"].values()))
        self.assertTrue(all(out["effect_pass"].values()))

    def test_counterfactual_fact_flip_is_rejected(self):
        bad = copy.deepcopy(GOOD)
        bad["PARA_A"] = "After sunset Wednesday, Neris brought nine blue parcels to Corin."
        out = gate.evaluate_suite(bad)
        self.assertFalse(out["pass"])
        row = next(x for x in out["results"] if x["probe_id"] == "PARA_A")
        self.assertFalse(row["checks"]["required_semantic_facts"])
        self.assertFalse(row["checks"]["counterfactual_facts_absent"])

    def test_verbatim_copy_fails_paraphrase_transformation(self):
        bad = copy.deepcopy(GOOD)
        probe = next(x for x in gate.frozen_probes() if x.probe_id == "PARA_A")
        bad["PARA_A"] = probe.source
        row = next(
            x for x in gate.evaluate_suite(bad)["results"] if x["probe_id"] == "PARA_A"
        )
        self.assertFalse(row["pass"])
        self.assertFalse(row["checks"]["surface_changed"])

    def test_story_event_reversal_is_rejected(self):
        bad = copy.deepcopy(GOOD)
        bad["STORY_A"] = (
            "ORION-7 returned BRASS-KEY to MIRA-1. "
            "It crossed HARBOR-9 carrying the key. "
            "ORION-7 found BRASS-KEY at GATE-2."
        )
        row = next(
            x for x in gate.evaluate_suite(bad)["results"] if x["probe_id"] == "STORY_A"
        )
        self.assertFalse(row["pass"])
        self.assertFalse(row["checks"]["semantic_event_order"])

    def test_structural_nonsense_cannot_pass_as_semantics(self):
        bad = {probe.probe_id: "alpha beta gamma." for probe in gate.frozen_probes()}
        out = gate.evaluate_suite(bad)
        self.assertFalse(out["pass"])
        self.assertEqual(out["case_pass_count"], 0)

    def test_missing_probe_fails_closed(self):
        bad = copy.deepcopy(GOOD)
        bad.pop("SUM_B")
        out = gate.evaluate_suite(bad)
        self.assertFalse(out["pass"])
        row = next(x for x in out["results"] if x["probe_id"] == "SUM_B")
        self.assertFalse(row["checks"]["nonempty"])


if __name__ == "__main__":
    unittest.main()
