from __future__ import annotations
import ast
import hashlib
import json
import os
import pathlib
import unittest
from unittest.mock import patch

from canonical.runtime import harbor_science_dna_storage_agent_v1 as a
from execution_guard.logical_attempt_identity_v2 import logical_attempt_id


class HarborScienceDNAStorageAgentV1Tests(unittest.TestCase):
    def test_request_is_visible_contract_only(self):
        env={"BRAIN_TASK_ARTIFACTS_JSON":json.dumps(["/root/results"])}
        with patch.dict(os.environ,env,clear=False):
            out=a.build_request("Encode /root/data/payload.bin as DNA and write encoded.dna in the result directory.")
        self.assertEqual(out["prevalidated_plan"]["mode"],"encode")
        self.assertEqual(out["prevalidated_plan"]["input_path"],"/root/data/payload.bin")
        self.assertEqual(out["prevalidated_plan"]["output_path"],"/root/results/encoded.dna")
        self.assertEqual(out["model_dependency_count"],0)

    def test_bundle_contains_exact_brain_owned_sources(self):
        bundle=a._bundle_sources()
        self.assertIn(a.REMOTE_ROOT+"/canonical/runtime/dna_storage_codec_v1.py",bundle)
        self.assertIn(a.REMOTE_ROOT+"/canonical/runtime/dna_storage_task_adapter_v1.py",bundle)
        for path,data in bundle.items():
            self.assertIsInstance(data,bytes)
            self.assertLess(len(data),100000)
            self.assertEqual(len(hashlib.sha256(data).hexdigest()),64)

    def test_transfer_commands_are_bounded_and_network_free(self):
        data=b"x"*25000
        commands=a._append_commands("/tmp/project_brain_dna_storage_v1/test.bin",data)
        self.assertGreater(len(commands),2)
        for command in commands:
            self.assertLessEqual(len(command),12000)
            low=command.lower()
            for token in ("curl ","wget ","git clone","git fetch","pip install","apt install"):
                self.assertNotIn(token,low)

    def test_claim_bound_identity(self):
        slot="terminal-bench-science/synthetic-dna-family::trial-0"
        digest="sha256:"+"1"*64
        claim="sha256:"+"2"*64
        attempt=logical_attempt_id(slot_id=slot,task_digest=digest,execution_claim_binding_digest=claim)
        env={
            "BRAIN_SLOT_ID":slot,
            "BRAIN_TASK_DIGEST":digest,
            "BRAIN_EXECUTION_CLAIM_BINDING_DIGEST":claim,
            "BRAIN_LOGICAL_ATTEMPT_ID":attempt,
        }
        with patch.dict(os.environ,env,clear=False):
            self.assertEqual(a.logical_attempt_id_for_goal("Encode a payload."),attempt)

    def test_identity_mismatch_fails_closed(self):
        env={
            "BRAIN_SLOT_ID":"synthetic",
            "BRAIN_TASK_DIGEST":"sha256:"+"1"*64,
            "BRAIN_EXECUTION_CLAIM_BINDING_DIGEST":"sha256:"+"2"*64,
            "BRAIN_LOGICAL_ATTEMPT_ID":"3"*64,
        }
        with patch.dict(os.environ,env,clear=False):
            with self.assertRaises(RuntimeError):
                a.logical_attempt_id_for_goal("Encode a payload.")

    def test_no_rank23_or_benchmark_answer_binding(self):
        source=pathlib.Path(a.__file__).read_text(encoding="utf-8").lower()
        self.assertNotIn("rank23",source)
        self.assertNotIn("dna-storage-codec::trial-0",source)
        self.assertNotIn("terminal-bench-science",source)

    def test_no_model_or_network_dependencies(self):
        source=pathlib.Path(a.__file__).read_text(encoding="utf-8")
        tree=ast.parse(source)
        imported=set()
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):
                imported.update(n.name for n in node.names)
            elif isinstance(node,ast.ImportFrom) and node.module:
                imported.add(node.module)
        forbidden={"openai","anthropic","transformers","torch","requests","httpx","urllib","socket","ollama","vllm","litellm"}
        self.assertFalse(any(name.split(".")[0] in forbidden for name in imported),sorted(imported))
        self.assertEqual(a.MODEL_DEPENDENCY_COUNT,0)
        self.assertEqual(a.NETWORK_DEPENDENCY_COUNT,0)


if __name__=="__main__":
    unittest.main(verbosity=2)
