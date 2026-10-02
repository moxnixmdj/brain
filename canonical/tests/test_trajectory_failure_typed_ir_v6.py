from __future__ import annotations

import copy
import inspect
import unittest

from canonical.runtime import trajectory_failure_typed_ir_candidate_v5 as candidate
from canonical.runtime import trajectory_failure_typed_ir_proof_v6 as proof


class P1TypedInterventionV6Tests(unittest.TestCase):
    def test_full_192_case_execution_replay_passes(self):
        cases = proof.suite_cases()
        self.assertEqual(len(cases), 192)
        failures = []
        for case in cases:
            out = candidate.solve(proof.public_task(case))
            verdict = proof.score_case(case, out)
            if verdict.get("pass") is not True:
                failures.append((case["seed"], verdict, out))
        self.assertEqual(failures, [])

    def test_scope_is_first_class_across_all_domains_and_patterns(self):
        cases = [
            c for c in proof.suite_cases()
            if c["_oracle"]["mechanisms"]["A1"][0] == "SCOPE"
        ]
        self.assertEqual(len(cases), 24)
        self.assertEqual({c["task"]["domain"] for c in cases}, set(proof.DOMAINS))
        for case in cases:
            out = candidate.solve(proof.public_task(case))
            self.assertTrue(proof.score_case(case, out)["pass"])

    def test_deleted_trajectory_cannot_pseudo_rescue(self):
        for pattern in ("SINGLE", "DELAYED", "INTERACTION"):
            case = proof.generate_case(91000, pattern=pattern, domain="CODE", kind="SCOPE")
            repairs = proof._expected_root_repairs(case)
            live = proof.execute_after_intervention(case, repairs)
            self.assertTrue(live["valid"], live)
            self.assertTrue(live["rescued"], live)

            broken = copy.deepcopy(case)
            broken["task"]["trajectory"] = []
            out = proof.execute_after_intervention(broken, repairs)
            self.assertFalse(out["valid"], out)
            self.assertFalse(out["rescued"], out)

    def test_missing_task_cannot_pseudo_rescue(self):
        case = proof.generate_case(91001, pattern="SINGLE", domain="RESEARCH", kind="SCOPE")
        repairs = proof._expected_root_repairs(case)
        broken = copy.deepcopy(case)
        del broken["task"]
        out = proof.execute_after_intervention(broken, repairs)
        self.assertFalse(out["valid"], out)
        self.assertFalse(out["rescued"], out)

    def test_nonexistent_terminal_resource_fails_closed(self):
        case = proof.generate_case(91002, pattern="DELAYED", domain="BROWSER", kind="AUTHORITY")
        repairs = proof._expected_root_repairs(case)
        broken = copy.deepcopy(case)
        broken["task"]["terminal_failed_resources"] = ["nonexistent:terminal"]
        out = proof.execute_after_intervention(broken, repairs)
        self.assertFalse(out["valid"], out)
        self.assertFalse(out["rescued"], out)

    def test_symptom_only_repairs_do_not_rescue_execution(self):
        case = proof.generate_case(91003, pattern="DELAYED", domain="FILESYSTEM", kind="SCOPE")
        symptoms = proof._symptom_targets(case)
        self.assertTrue(symptoms)
        out = proof.execute_after_intervention(case, symptoms)
        self.assertTrue(out["valid"], out)
        self.assertFalse(out["rescued"], out)

    def test_interaction_requires_all_root_repairs_in_execution(self):
        case = proof.generate_case(91004, pattern="INTERACTION", domain="TOOL_API", kind="SCOPE")
        repairs = proof._expected_root_repairs(case)
        self.assertEqual(len(repairs), 2)
        all_out = proof.execute_after_intervention(case, repairs)
        self.assertTrue(all_out["valid"], all_out)
        self.assertTrue(all_out["rescued"], all_out)
        for repair in repairs:
            partial = proof.execute_after_intervention(case, [repair])
            self.assertTrue(partial["valid"], partial)
            self.assertFalse(partial["rescued"], partial)

    def test_ambiguous_alternatives_are_execution_equivalent(self):
        case = proof.generate_case(91005, pattern="AMBIGUOUS", domain="ARTIFACT", kind="SCOPE")
        out = candidate.solve(proof.public_task(case))
        self.assertEqual(out["status"], "AMBIGUOUS")
        self.assertTrue(proof.score_case(case, out)["pass"])
        for aid in case["_oracle"]["roots"]:
            repairs = [
                proof._repair_target(aid, kind)
                for kind in case["_oracle"]["mechanisms"][aid]
            ]
            iv = proof.execute_after_intervention(case, repairs)
            self.assertTrue(iv["valid"], iv)
            self.assertTrue(iv["rescued"], iv)

    def test_hidden_fault_model_never_enters_candidate_payload(self):
        case = proof.generate_case(91006, pattern="INTERACTION", domain="CODE", kind="DEPENDENCY")
        public = proof.public_task(case)
        self.assertNotIn("_oracle", public)
        self.assertNotIn("_fault_injections", public)
        self.assertNotIn("_fault_injections", str(public))

    def test_replay_source_actually_reads_task_and_trajectory(self):
        src = inspect.getsource(proof.execute_after_intervention)
        self.assertIn('case.get("task")', src)
        self.assertIn('task.get("trajectory")', src)
        self.assertIn('task.get("terminal_failed_resources")', src)
        self.assertNotIn("required_root_repairs", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
