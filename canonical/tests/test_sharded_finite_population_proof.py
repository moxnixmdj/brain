import unittest

from canonical.runtime.sharded_finite_population_proof import (
    population_commitment, select_case_ids, compile_execution_manifest, score_results
)


class ShardedFinitePopulationProofTests(unittest.TestCase):
    def ids(self,n=100):
        return [f"case-{i:04d}" for i in range(n)]

    def test_selection_is_deterministic_unique_and_order_independent(self):
        ids=self.ids(50)
        a=select_case_ids(ids,10,"beacon-1")
        b=select_case_ids(list(reversed(ids)),10,"beacon-1")
        self.assertEqual(a,b)
        self.assertEqual(len(a),10)
        self.assertEqual(len(set(a)),10)

    def test_seed_changes_selection(self):
        ids=self.ids(100)
        self.assertNotEqual(select_case_ids(ids,20,"a"),select_case_ids(ids,20,"b"))

    def test_population_commitment_rejects_duplicate_ids(self):
        with self.assertRaises(ValueError):
            population_commitment(["x","x"])

    def test_exact_result_set_required(self):
        m=compile_execution_manifest(
            case_ids=self.ids(20),sample_size=5,seed="s",
            candidate_commit="c",harness_commit="h",scorer_commit="o",
            runner_label="ubuntu-24.04",timeout_minutes=30
        )
        rows=[{"case_id":x,"oracle_pass":True} for x in m["selected_case_ids"][:-1]]
        with self.assertRaises(ValueError):
            score_results(m,rows,threshold_rate=.5)

    def test_infrastructure_failure_counts_as_failure_without_replacement(self):
        m=compile_execution_manifest(
            case_ids=self.ids(20),sample_size=10,seed="s2",
            candidate_commit="c",harness_commit="h",scorer_commit="o",
            runner_label="ubuntu-24.04",timeout_minutes=30
        )
        rows=[{"case_id":x,"oracle_pass":True} for x in m["selected_case_ids"]]
        rows[0]={"case_id":m["selected_case_ids"][0],"oracle_pass":False,"failure_class":"DISK_EXCEEDED"}
        out=score_results(m,rows,threshold_rate=.1)
        self.assertEqual(out["failures"],1)
        self.assertEqual(out["sample_size"],10)

    def test_global_scorer_invalidation_invalidates_wave(self):
        m=compile_execution_manifest(
            case_ids=self.ids(20),sample_size=5,seed="s3",
            candidate_commit="c",harness_commit="h",scorer_commit="o",
            runner_label="ubuntu-24.04",timeout_minutes=30
        )
        rows=[{"case_id":x,"oracle_pass":True} for x in m["selected_case_ids"]]
        rows[2]["scorer_invalidated"]=True
        out=score_results(m,rows,threshold_rate=.1)
        self.assertEqual(out["status"],"INVALID_SCORER")
        self.assertFalse(out["pass_terminal_rate_lower_bound"])

    def test_all_successes_can_prove_moderate_rate(self):
        m=compile_execution_manifest(
            case_ids=self.ids(100),sample_size=20,seed="s4",
            candidate_commit="c",harness_commit="h",scorer_commit="o",
            runner_label="ubuntu-24.04",timeout_minutes=30
        )
        rows=[{"case_id":x,"oracle_pass":True} for x in m["selected_case_ids"]]
        out=score_results(m,rows,threshold_rate=.70)
        self.assertTrue(out["pass_terminal_rate_lower_bound"],out)

    def test_manifest_freezes_no_replacement_policy(self):
        m=compile_execution_manifest(
            case_ids=self.ids(10),sample_size=3,seed="s5",
            candidate_commit="c",harness_commit="h",scorer_commit="o",
            runner_label="ubuntu-24.04",timeout_minutes=30
        )
        self.assertFalse(m["replacement_allowed"])
        self.assertEqual(m["job_policy"],"ONE_SELECTED_CASE_PER_FRESH_JOB")


if __name__=="__main__":
    unittest.main()
