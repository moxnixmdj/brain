from __future__ import annotations

import unittest

from canonical.runtime.astra_runtime import Blocker, _shell_prior_result_env


class AstraExplicitCrossStepBindingTests(unittest.TestCase):
    def setUp(self):
        self.prior = [
            {
                "adapter": "http",
                "body_excerpt": "<title>Python 3.14.0</title>",
                "stdout": "should-not-leak",
                "status": 200,
            },
            {
                "adapter": "shell",
                "stdout": "later-secret",
                "returncode": 0,
            },
        ]

    def test_default_denies_all_prior_results(self):
        self.assertEqual(_shell_prior_result_env({"adapter": "shell"}, self.prior), {})

    def test_exact_body_excerpt_binding_exports_only_body(self):
        step = {
            "adapter": "shell",
            "prior_result_bindings": [
                {"step_index": 0, "fields": ["body_excerpt"]}
            ],
        }
        env = _shell_prior_result_env(step, self.prior)
        self.assertEqual(env, {"ASTRA_STEP_0_BODY": "<title>Python 3.14.0</title>"})
        self.assertNotIn("ASTRA_STEP_0_STDOUT", env)
        self.assertNotIn("ASTRA_STEP_0_RESULT_JSON", env)
        self.assertNotIn("ASTRA_STEP_1_STDOUT", env)

    def test_declared_result_json_is_exact_selected_step_only(self):
        step = {
            "adapter": "shell",
            "prior_result_bindings": [
                {"step_index": 1, "fields": ["result_json"]}
            ],
        }
        env = _shell_prior_result_env(step, self.prior)
        self.assertEqual(set(env), {"ASTRA_STEP_1_RESULT_JSON"})
        self.assertIn('"stdout": "later-secret"', env["ASTRA_STEP_1_RESULT_JSON"])

    def test_unknown_field_fails_closed(self):
        step = {
            "adapter": "shell",
            "prior_result_bindings": [
                {"step_index": 0, "fields": ["stderr"]}
            ],
        }
        with self.assertRaisesRegex(Blocker, "FIELD_FORBIDDEN"):
            _shell_prior_result_env(step, self.prior)

    def test_missing_declared_field_fails_closed(self):
        step = {
            "adapter": "shell",
            "prior_result_bindings": [
                {"step_index": 1, "fields": ["body_excerpt"]}
            ],
        }
        with self.assertRaisesRegex(Blocker, "FIELD_MISSING"):
            _shell_prior_result_env(step, self.prior)

    def test_out_of_range_step_fails_closed(self):
        step = {
            "adapter": "shell",
            "prior_result_bindings": [
                {"step_index": 2, "fields": ["stdout"]}
            ],
        }
        with self.assertRaisesRegex(Blocker, "STEP_INDEX_UNAVAILABLE"):
            _shell_prior_result_env(step, self.prior)

    def test_duplicate_step_binding_fails_closed(self):
        step = {
            "adapter": "shell",
            "prior_result_bindings": [
                {"step_index": 0, "fields": ["body_excerpt"]},
                {"step_index": 0, "fields": ["result_json"]},
            ],
        }
        with self.assertRaisesRegex(Blocker, "STEP_DUPLICATE"):
            _shell_prior_result_env(step, self.prior)

    def test_extra_binding_keys_fail_closed(self):
        step = {
            "adapter": "shell",
            "prior_result_bindings": [
                {"step_index": 0, "fields": ["body_excerpt"], "optional": True}
            ],
        }
        with self.assertRaisesRegex(Blocker, "BINDING_KEYS_INVALID"):
            _shell_prior_result_env(step, self.prior)


if __name__ == "__main__":
    unittest.main(verbosity=2)
