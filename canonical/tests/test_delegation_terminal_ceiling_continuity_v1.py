from __future__ import annotations
import hashlib
import json
import unittest
from pathlib import Path

from canonical.runtime.terminal_ceiling_witness_lifter_v1 import evaluate

ROOT = Path(__file__).resolve().parents[2]

def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))

def git_blob_sha(rel: str) -> str:
    data=(ROOT / rel).read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

class DelegationTerminalCeilingContinuityTests(unittest.TestCase):
    def test_live_delegation_continuity_candidate(self):
        spec=load("canonical/governance/DELEGATION_TERMINAL_CEILING_CONTINUITY_INPUT_V1.json")
        binding_path=spec["binding_path"]
        current_sha=git_blob_sha(binding_path)
        self.assertEqual(current_sha,spec["current_binding_blob_sha"])
        self.assertEqual(current_sha,spec["terminal_snapshot"]["binding_blob_sha"])

        terminal=load(spec["terminal_result"])
        self.assertEqual(terminal["execution_snapshot_commit"],spec["terminal_snapshot"]["commit_sha"])
        self.assertEqual(terminal["artifact"]["full_result_sha256"],spec["terminal_full_result_sha256"])
        observed=terminal["direct_terminal_population"]["routes"][spec["behavior_id"]]
        self.assertEqual(observed,spec["observed_population"])

        out=evaluate(
            family=spec["family"],
            behavior_id=spec["behavior_id"],
            binding_path=binding_path,
            protocols=load("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"),
            registry=load("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"),
            binding=load(binding_path),
            executor_manifest=load("canonical/governance/TERMINAL_ROUTE_SPECIFIC_EXECUTOR_MANIFEST_V1.json"),
            terminal_result=terminal,
            binding_blob_sha=current_sha,
            terminal_snapshot_binding_blob_sha=spec["terminal_snapshot"]["binding_blob_sha"],
            binding_verification=load(spec["current_binding_verification"]),
        )
        self.assertTrue(out["pass"],out)
        w=out["candidate_witness"]
        self.assertEqual(w["family"],"SUBAGENT_DELEGATION_AND_COORDINATION")
        self.assertEqual(w["source_case_count"],132)
        self.assertEqual(w["result"]["brain_lower_bound"],1.0)
        self.assertEqual(w["result"]["theoretical_upper_bound"],1.0)
        self.assertFalse(w["verified"])
        self.assertFalse(w["independent"])
        self.assertFalse(out["promotion_authority"])

if __name__=="__main__":
    unittest.main(verbosity=2)
