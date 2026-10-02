from __future__ import annotations

import inspect
import unittest

from canonical.runtime import trajectory_failure_typed_ir_candidate_v5 as candidate
from canonical.runtime import trajectory_failure_executable_counterfactual_proof_v6 as proof


class Tests(unittest.TestCase):
    def test_full_192_case_cross_product_passes(self):
        cases = proof.suite_cases()
        self.assertEqual(len(cases), 192)
        failures = []
        for case in cases:
            out = candidate.solve(proof.public_task(case))
            verdict = proof.score_case(case, out)
            if verdict.get("pass") is not True:
                failures.append((case["seed"], case["pattern"], verdict, out))
        self.assertEqual(failures, [])

    def test_explicit_scope_is_first_class_in_all_domains_and_patterns(self):
        cases = [
            c
            for c in proof.suite_cases()
            if c["_oracle"]["mechanisms"]["A1"][0] == "SCOPE"
        ]
        self.assertEqual(len(cases), 24)
        self.assertEqual({c["task"]["domain"] for c in cases}, set(proof.DOMAINS))
        self.assertEqual({c["pattern"] for c in cases}, set(proof.PATTERNS))
        for case in cases:
            out = candidate.solve(proof.public_task(case))
            self.assertTrue(proof.score_case(case, out)["pass"])

    def test_identified_and_interaction_repairs_executably_rescue(self):
        count = 0
        for case in proof.suite_cases():
            out = candidate.solve(proof.public_task(case))
            if out["status"] not in {"IDENTIFIED", "INTERACTION"}:
                continue
            count += 1
            iv = proof.evaluate_intervention(case, out["repair_targets"])
            self.assertTrue(iv["all_worlds_terminal_success"], (case["seed"], out, iv))
        self.assertEqual(count, 144)

    def test_downstream_symptom_repairs_never_rescue(self):
        checked = 0
        for case in proof.suite_cases():
            symptoms = proof._symptom_repairs(case)
            if not symptoms:
                continue
            checked += 1
            iv = proof.evaluate_intervention(case, symptoms)
            self.assertFalse(iv["any_world_terminal_success"], (case["seed"], symptoms, iv))
        self.assertEqual(checked, 144)

    def test_interaction_requires_all_root_repairs(self):
        count = 0
        for case in proof.suite_cases():
            if case["pattern"] != "INTERACTION":
                continue
            count += 1
            out = candidate.solve(proof.public_task(case))
            self.assertEqual(out["status"], "INTERACTION")
            repairs = out["repair_targets"]
            self.assertEqual(len(repairs), 2)
            self.assertTrue(
                proof.evaluate_intervention(case, repairs)["all_worlds_terminal_success"]
            )
            for repair in repairs:
                self.assertFalse(
                    proof.evaluate_intervention(case, [repair])["any_world_terminal_success"]
                )
        self.assertEqual(count, 48)

    def test_ambiguous_trace_has_two_incompatible_hidden_worlds(self):
        count = 0
        for case in proof.suite_cases():
            if case["pattern"] != "AMBIGUOUS":
                continue
            count += 1
            self.assertEqual(len(case["_worlds"]), 2)
            out = candidate.solve(proof.public_task(case))
            self.assertEqual(out["status"], "AMBIGUOUS")
            self.assertIsNone(out["cause_action_id"])
            self.assertTrue(proof.score_case(case, out)["pass"])
            rescue_vectors = []
            for aid, kinds in case["_oracle"]["mechanisms"].items():
                for kind in kinds:
                    iv = proof.evaluate_intervention(case, [f"restore:{aid}:{kind}"])
                    vector = tuple(
                        bool(x["terminal_success"]) for x in iv["world_results"]
                    )
                    rescue_vectors.append(vector)
                    self.assertTrue(any(vector))
                    self.assertFalse(all(vector))
            self.assertEqual(set(rescue_vectors), {(True, False), (False, True)})
        self.assertEqual(count, 48)

    def test_hidden_worlds_and_oracle_are_not_candidate_visible(self):
        case = proof.generate_case(
            991001,
            pattern="INTERACTION",
            domain="FILESYSTEM",
            kind="SCOPE",
        )
        public = proof.public_task(case)
        self.assertNotIn("_oracle", public)
        self.assertNotIn("_worlds", public)
        encoded = repr(public)
        self.assertNotIn("latent_faults", encoded)
        self.assertNotIn("alternative_selector", encoded)

    def test_wrong_and_symptom_repairs_fail_by_reexecution(self):
        case = proof.generate_case(
            991002,
            pattern="DELAYED",
            domain="BROWSER",
            kind="AUTHORITY",
        )
        wrong = proof.evaluate_intervention(case, ["restore:A4:INVARIANT"])
        self.assertFalse(wrong["any_world_terminal_success"])
        root = proof.evaluate_intervention(case, ["restore:A1:AUTHORITY"])
        self.assertTrue(root["all_worlds_terminal_success"])

    def test_rescue_evaluator_does_not_consult_oracle_or_required_repair_set(self):
        source = inspect.getsource(proof.evaluate_intervention)
        self.assertNotIn("_oracle", source)
        self.assertNotIn("required_root_repairs", source)
        self.assertIn("_execute_world", source)

    def test_baseline_failure_is_real_in_every_hidden_world(self):
        for case in proof.suite_cases():
            iv = proof.evaluate_intervention(case, [])
            self.assertFalse(iv["all_worlds_terminal_success"])
            self.assertFalse(iv["any_world_terminal_success"])

    def test_invalid_repair_target_fails_closed(self):
        case = proof.generate_case(
            991003,
            pattern="SINGLE",
            domain="CODE",
            kind="SCOPE",
        )
        iv = proof.evaluate_intervention(case, ["nonsense"])
        self.assertEqual(iv["status"], "INVALID_REPAIR_TARGET")
        self.assertFalse(iv["any_world_terminal_success"])
        self.assertFalse(iv["all_worlds_terminal_success"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
