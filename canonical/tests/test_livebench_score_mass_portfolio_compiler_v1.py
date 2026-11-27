import unittest

from canonical.runtime import livebench_score_mass_portfolio_compiler_v1 as portfolio


class LiveBenchScoreMassPortfolioCompilerV1Tests(unittest.TestCase):
    def test_composes_six_exact_public_checker_contracts(self):
        prompt = " ".join([
            "The response must contain between 4 and 6 words.",
            "Use at least 4 unique words in the response.",
            "Include exactly 2 numbers in the response.",
            portfolio._CONSONANT_PHRASE,
            portfolio._PARENS_PHRASE,
            portfolio._QUOTES_PHRASE,
        ])
        out = portfolio.compile_portfolio(prompt, total_instruction_count=6)
        self.assertEqual(out["status"], "PASS_COMPONENT")
        self.assertEqual(out["recognized_checker_count"], 6)
        self.assertEqual(out["guaranteed_satisfied_supported_count"], 6)
        self.assertEqual(out["score_lower_bound"], "1")
        constraints = portfolio.parse_supported_constraints(prompt)
        self.assertTrue(all(
            portfolio.validate_constraint(out["response"], c)
            for c in constraints
        ))

    def test_partial_credit_replaces_all_or_nothing_blocking(self):
        prompt = " ".join([
            "The response must contain between 1 and 1 words.",
            "Use at least 3 unique words in the response.",
        ])
        out = portfolio.compile_portfolio(prompt, total_instruction_count=2)
        self.assertEqual(out["recognized_checker_count"], 2)
        self.assertEqual(out["guaranteed_satisfied_supported_count"], 1)
        self.assertEqual(out["score_lower_bound"], "1/4")
        self.assertTrue(out["weakly_dominates_every_generated_candidate"])

    def test_no_whitespace_and_special_bullet_can_compose(self):
        prompt = " ".join([
            "The output should not contain any whitespace.",
            "Answer with a list of items, instead of bullet points use !?!?.",
        ])
        out = portfolio.compile_portfolio(prompt, total_instruction_count=2)
        self.assertEqual(out["guaranteed_satisfied_supported_count"], 2)
        self.assertEqual(out["score_lower_bound"], "1")
        self.assertFalse(any(ch.isspace() for ch in out["response"]))
        self.assertGreaterEqual(out["response"].count("!?!?"), 2)

    def test_unknown_constraints_are_never_counted_as_solved(self):
        prompt = (
            "The response must contain between 2 and 3 words. "
            "Explain photosynthesis with perfect semantic accuracy."
        )
        out = portfolio.compile_portfolio(prompt, total_instruction_count=3)
        self.assertEqual(out["recognized_checker_count"], 1)
        self.assertEqual(out["guaranteed_satisfied_supported_count"], 1)
        self.assertEqual(out["score_lower_bound"], "1/6")
        self.assertFalse(out["semantic_capability_claim"])

    def test_total_count_is_not_needed_for_candidate_dominance(self):
        prompt = " ".join([
            "Use at least 3 unique words in the response.",
            portfolio._PARENS_PHRASE,
            portfolio._QUOTES_PHRASE,
        ])
        out = portfolio.compile_portfolio(prompt)
        self.assertEqual(out["guaranteed_satisfied_supported_count"], 3)
        self.assertIsNone(out["score_lower_bound"])
        self.assertIn("K_IS_CONSTANT", out["score_lower_bound_reason"])

    def test_subbullet_public_checker_is_reproduced_exactly(self):
        prompt = portfolio._SUB_BULLET_PHRASE
        out = portfolio.compile_portfolio(prompt, total_instruction_count=1)
        self.assertEqual(out["score_lower_bound"], "1")
        constraint = portfolio.parse_supported_constraints(prompt)[0]
        self.assertTrue(portfolio.validate_constraint(out["response"], constraint))

    def test_invalid_total_count_fails_closed(self):
        prompt = " ".join([
            "Use at least 3 unique words in the response.",
            portfolio._PARENS_PHRASE,
        ])
        with self.assertRaises(portfolio.PortfolioError):
            portfolio.compile_portfolio(prompt, total_instruction_count=1)

    def test_empty_or_unsupported_prompt_blocks(self):
        with self.assertRaises(portfolio.PortfolioError):
            portfolio.compile_portfolio("")
        out = portfolio.compile_portfolio("Explain photosynthesis.")
        self.assertEqual(out["status"], "BLOCKED")
        self.assertEqual(out["guaranteed_satisfied_supported_count"], 0)


if __name__ == "__main__":
    unittest.main()
