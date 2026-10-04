#!/usr/bin/env python3
import importlib.util
import pathlib
import sys
import unittest

CANONICAL=pathlib.Path(__file__).resolve().parents[1]
ROOT=CANONICAL.parent

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module

compiler=load("goal_compiler_exact_literal_test",CANONICAL/"runtime"/"goal_compiler.py")

class ExactLiteralRoutingTests(unittest.TestCase):
    def test_unquoted_literal_uses_finish_without_capability(self):
        out=compiler.compile_goal("Reply with exactly SYNTHETIC_OK.",{},ROOT)
        self.assertEqual(out["compiler_mode"],"DETERMINISTIC_EXACT_LITERAL_RESPONSE")
        self.assertEqual(out["finish_summary"],"SYNTHETIC_OK")
        self.assertEqual(out["controller_actions"],[
            {"type":"finish","args":{"summary":"SYNTHETIC_OK"}}
        ])
        self.assertNotIn("selected_capability",out)

    def test_general_unrelated_token(self):
        out=compiler.compile_goal("Respond with exactly ROUTE_42.",{},ROOT)
        self.assertEqual(out["finish_summary"],"ROUTE_42")

    def test_quoted_literal_preserves_spaces(self):
        out=compiler.compile_goal('Output exactly "hello neutral world".',{},ROOT)
        self.assertEqual(out["finish_summary"],"hello neutral world")

    def test_ambiguous_phrase_not_claimed_by_literal_router(self):
        self.assertIsNone(
            compiler._compile_exact_literal_response_goal(
                "Reply with exactly hello neutral world."
            )
        )

    def test_explanatory_goal_not_claimed_by_literal_router(self):
        self.assertIsNone(
            compiler._compile_exact_literal_response_goal(
                "Explain exactly why the neutral example works."
            )
        )

    def test_multiline_not_claimed_by_literal_router(self):
        self.assertIsNone(
            compiler._compile_exact_literal_response_goal(
                "Reply with exactly TOKEN\nThen continue."
            )
        )

if __name__=="__main__":
    unittest.main(verbosity=2)
