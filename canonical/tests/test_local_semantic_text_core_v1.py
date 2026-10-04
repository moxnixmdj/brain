import unittest

from canonical.runtime import local_semantic_text_core_v1 as core


class LocalSemanticTextCoreV1Tests(unittest.TestCase):
    def test_summarize_is_extractive_and_grounded(self):
        prompt = (
            "Summarize the following passage: "
            "Mercury is the closest planet to the Sun. "
            "It completes an orbit in about 88 Earth days. "
            "Its surface has many impact craters. "
            "Because it has almost no atmosphere, temperatures vary sharply. "
            "Maintain a trigram overlap of 40% (±2%) with the provided reference text."
        )
        out = core.produce(prompt)
        self.assertEqual(out["status"], "PASS")
        self.assertEqual(out["intent"], "summarize")
        self.assertEqual(out["grounding_class"], "EXTRACTIVE_SOURCE_SENTENCE_SUBSET")
        self.assertNotIn("trigram overlap", out["source"].lower())
        source_sentences = set(core._sentences(out["source"]))
        for sentence in core._sentences(out["seed"]):
            self.assertIn(sentence, source_sentences)
        self.assertGreaterEqual(out["grounding"]["source_coverage"], 0.45)
        self.assertEqual(out["learned_parameter_count"], 0)

    def test_simplify_preserves_facts_and_reduces_complex_phrases(self):
        prompt = (
            "Simplify the following text: "
            "Prior to launch, the team utilized approximately 12 sensors in order to "
            "demonstrate that the system had the ability to operate safely; "
            "the test facilitated a faster review."
        )
        out = core.produce(prompt)
        self.assertEqual(out["status"], "PASS")
        seed = out["seed"]
        self.assertIn("12", seed)
        self.assertIn("team", seed.lower())
        self.assertIn("before", seed.lower())
        self.assertIn("used", seed.lower())
        self.assertIn("about", seed.lower())
        self.assertIn("show", seed.lower())
        self.assertIn("can", seed.lower())
        self.assertNotIn("utilized", seed.lower())
        self.assertGreaterEqual(out["grounding"]["source_coverage"], 0.65)

    def test_paraphrase_changes_surface_without_detaching_from_source(self):
        prompt = (
            "Paraphrase: The system works because the network is available. "
            "Furthermore, the operator can consider the result."
        )
        out = core.produce(prompt)
        self.assertEqual(out["status"], "PASS")
        self.assertEqual(out["intent"], "paraphrase")
        self.assertNotEqual(out["seed"], out["source"])
        self.assertIn("network", out["seed"].lower())
        self.assertIn("operator", out["seed"].lower())
        self.assertIn("result", out["seed"].lower())
        self.assertGreaterEqual(out["grounding"]["source_coverage"], 0.65)

    def test_paraphrase_fallback_is_explicit_reformulation_not_invention(self):
        prompt = "Rewrite: Cats sleep on warm windowsills."
        out = core.produce(prompt)
        self.assertEqual(out["status"], "PASS")
        self.assertTrue(out["seed"].lower().startswith("in other words,"))
        self.assertIn("cats sleep on warm windowsills", out["seed"].lower())

    def test_story_keeps_prompt_premise_verbatim_and_adds_structure(self):
        prompt = (
            "Write a fictional story about an engineer who discovers that a bridge sensor "
            "has been reporting the wrong value during a storm."
        )
        out = core.produce(prompt)
        self.assertEqual(out["status"], "PASS")
        self.assertEqual(out["intent"], "story")
        self.assertTrue(out["evidence"]["premise_verbatim_preserved"])
        self.assertIn("engineer", out["seed"].lower())
        self.assertIn("bridge sensor", out["seed"].lower())
        self.assertIn("storm", out["seed"].lower())
        self.assertIn("complication", out["seed"].lower())
        self.assertGreaterEqual(out["grounding"]["source_coverage"], 0.65)

    def test_constraint_tail_is_not_treated_as_semantic_source(self):
        prompt = (
            "Rewrite it better: During the migration, the team isolated the workspace. "
            "The response must include keyword metricism in the 3-rd sentence."
        )
        out = core.produce(prompt)
        self.assertEqual(out["status"], "PASS")
        self.assertNotIn("metricism", out["source"].lower())
        self.assertIn("migration", out["source"].lower())

    def test_unknown_intent_fails_closed(self):
        out = core.produce("Explain why the sky looks blue.")
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["error"], "UNRECOGNIZED_SEMANTIC_INTENT")

    def test_thin_story_premise_fails_closed(self):
        out = core.produce("Write a story about rain.")
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["error"], "PREMISE_TOO_THIN")

    def test_no_network_or_learned_state_claimed(self):
        out = core.produce(
            "Simplify: Due to the fact that the process is lengthy, we commence early."
        )
        self.assertEqual(out["status"], "PASS")
        self.assertEqual(out["model_dependency_count"], 0)
        self.assertEqual(out["learned_parameter_count"], 0)
        self.assertFalse(out["network_used"])
        self.assertEqual(out["external_tools_used"], [])
        self.assertEqual(out["incremental_spend_usd"], 0)


if __name__ == "__main__":
    unittest.main()
