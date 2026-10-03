from __future__ import annotations
import hashlib, json, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

def raw(rel:str)->bytes:
    return (ROOT/rel).read_bytes()

def load(rel:str):
    return json.loads(raw(rel).decode("utf-8"))

def blob(rel:str)->str:
    b=raw(rel)
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

class TerminalSchedulingV11ActiveAuthorityTests(unittest.TestCase):
    def test_exact_v11_candidate_is_fail_closed(self):
        p="canonical/governance/TERMINAL_SCHEDULING_V11_ACTIVE_AUTHORITY_V1.json"
        x=load(p)
        self.assertEqual(x["schema"],"PROJECT_BRAIN_TERMINAL_SCHEDULING_V11_ACTIVE_AUTHORITY_V1")
        self.assertFalse(x["execution_authority"])
        self.assertFalse(x["promotion_authority"])
        self.assertFalse(x["fresh_reality_authority"])
        self.assertEqual(x["incremental_spend_usd"],0)
        self.assertEqual(x["acceptance_credit_delta"],0)
        self.assertEqual(x["capability_credit_delta"],0)
        self.assertEqual(x["family_credit_delta"],0)
        self.assertEqual(x["ownership_credit_delta"],0)
        self.assertEqual(x["live_world"]["frozen_predicates"],38)
        self.assertEqual(x["live_world"]["proved_predicates"],11)
        self.assertEqual(x["live_world"]["unresolved_predicates"],27)
        self.assertEqual(x["live_world"]["opus55_acceptance"],"4/19_PASS__15/19_OPEN")
        self.assertEqual(x["live_world"]["tool_learning_success_route_noninferior"],"OPEN")

    def test_v5_chain_exact_blobs_are_bound(self):
        x=load("canonical/governance/TERMINAL_SCHEDULING_V11_ACTIVE_AUTHORITY_V1.json")
        td=x["tool_discovery_retrieval_authority"]
        expected={
          "canonical/runtime/tool_discovery_retrieval_authority_gate_v1.py":"c3324e574c1fafb6aaab443f49b7a9600966e754",
          "canonical/governance/TOOL_DISCOVERY_RESIDUAL_WITNESS_RETRIEVAL_FRONTIER_V5_ACTIVATION_V1.json":"8b8b80d43972bb7113b193baaf21dbda292d595e",
          "canonical/verification/RETRIEVAL_V5_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"acd898bdea67ef0337e33b4335426fbe0dd7320d",
          "canonical/verification/RETRIEVAL_V5_FEDERATION_EXECUTION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"cd1501e167a5429ad0d918e080c527e6d43b8a4d",
          "canonical/verification/RETRIEVAL_V5_LIVE_GATE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"aa3a1ff960ba0f02ff5ad118053cf1b7d382d91b",
        }
        for path,sha in expected.items():
            self.assertEqual(blob(path),sha,(path,blob(path),sha))
        self.assertEqual(x["live_scheduler"]["retrieval_gate_git_blob_sha"],expected["canonical/runtime/tool_discovery_retrieval_authority_gate_v1.py"])
        self.assertEqual(td["activation_git_blob_sha"],expected["canonical/governance/TOOL_DISCOVERY_RESIDUAL_WITNESS_RETRIEVAL_FRONTIER_V5_ACTIVATION_V1.json"])
        self.assertEqual(td["activation_verification_git_blob_sha"],expected["canonical/verification/RETRIEVAL_V5_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"])
        self.assertEqual(td["execution_verification_git_blob_sha"],expected["canonical/verification/RETRIEVAL_V5_FEDERATION_EXECUTION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"])
        self.assertEqual(td["live_gate_verification_git_blob_sha"],expected["canonical/verification/RETRIEVAL_V5_LIVE_GATE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"])

    def test_all_independent_v5_receipts_pass(self):
        a=load("canonical/verification/RETRIEVAL_V5_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json")
        e=load("canonical/verification/RETRIEVAL_V5_FEDERATION_EXECUTION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json")
        g=load("canonical/verification/RETRIEVAL_V5_LIVE_GATE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json")
        self.assertEqual(a["independent_runner"]["conclusion"],"success")
        self.assertEqual(e["independent_runner"]["conclusion"],"success")
        self.assertEqual(g["independent_runner"]["conclusion"],"success")
        self.assertTrue(a["verified"]["strict_success_only_source_cell_consumption_mandatory"])
        self.assertTrue(a["verified"]["partial_batch_epoch_consumption_forbidden"])
        self.assertTrue(e["verified"]["transient_failure_remains_unconsumed_and_retryable"])
        self.assertTrue(e["verified"]["epoch_consumption_does_not_authorize_nonexistence"])
        self.assertTrue(g["verified"]["v2_v3_v4_v5_chain_passes"])
        self.assertTrue(g["verified"]["zero_credit_preserved"])

    def test_no_retrieval_semantic_regression(self):
        x=load("canonical/governance/TERMINAL_SCHEDULING_V11_ACTIVE_AUTHORITY_V1.json")
        td=x["tool_discovery_retrieval_authority"]
        self.assertTrue(td["mandatory"])
        self.assertFalse(td["direct_or_stale_bypass_allowed"])
        self.assertFalse(td["failed_or_rejected_cell_consumption_allowed"])
        self.assertFalse(td["partial_batch_epoch_consumption_allowed"])
        self.assertFalse(td["same_consumed_source_epoch_replay_allowed"])
        self.assertFalse(td["no_result_means_nonexistence"])
        self.assertFalse(td["open_world_epoch_consumption_means_complete"])

    def test_v10_is_exact_superseded_base(self):
        x=load("canonical/governance/TERMINAL_SCHEDULING_V11_ACTIVE_AUTHORITY_V1.json")
        self.assertEqual(blob("canonical/governance/TERMINAL_SCHEDULING_V10_ACTIVE_AUTHORITY_V1.json"),"b1d37d015d93eb71fba1742a498b793b5a2a4ea0")
        self.assertEqual(x["supersedes"]["git_blob_sha"],"b1d37d015d93eb71fba1742a498b793b5a2a4ea0")

if __name__=="__main__":
    unittest.main(verbosity=2)
