from __future__ import annotations
import ast,asyncio,json,os,pathlib,tempfile,unittest
from unittest.mock import patch
from canonical.runtime import harbor_dna_storage_agent_v1 as a
from execution_guard.logical_attempt_identity_v2 import logical_attempt_id

class HarborDNAStorageAgentV1Tests(unittest.TestCase):
    def _env(self):
        claim="sha256:"+"2"*64; digest="sha256:"+"1"*64; slot="terminal-bench-science/synthetic-dna::trial-0"
        logical=logical_attempt_id(slot_id=slot,task_digest=digest,execution_claim_binding_digest=claim)
        return {"BRAIN_SLOT_ID":slot,"BRAIN_TASK_DIGEST":digest,"BRAIN_EXECUTION_CLAIM_BINDING_DIGEST":claim,
                "BRAIN_LOGICAL_ATTEMPT_ID":logical,"BRAIN_TASK_ARTIFACTS_JSON":json.dumps(["/results"])},logical

    def test_claim_bound_identity(self):
        env,logical=self._env()
        with patch.dict(os.environ,env,clear=False): self.assertEqual(a.logical_attempt_id_for_goal("Implement DNA storage codec"),logical)

    def test_payload_classifies_without_models(self):
        env,_=self._env()
        with patch.dict(os.environ,env,clear=False):
            p=a.build_payload("Implement a DNA storage codec that encodes and decodes as /results/codec.py.")
        self.assertEqual(p["contract_precheck"]["mode"],"implementation")
        self.assertEqual(p["model_dependency_count"],0); self.assertEqual(p["network_dependency_count"],0)

    def test_transfer_commands_bounded_and_network_free(self):
        rows=a._append_commands("/tmp/x.py",b"abc"*10000)
        self.assertGreater(len(rows),2)
        for command in rows:
            self.assertLessEqual(len(command),12000)
            low=command.lower()
            for token in ("curl ","wget ","git clone","pip install","apt install"):
                self.assertNotIn(token,low)

    def test_no_model_or_network_dependencies(self):
        tree=ast.parse(pathlib.Path(a.__file__).read_text(encoding="utf-8"))
        imported=set()
        for n in ast.walk(tree):
            if isinstance(n,ast.Import): imported.update(x.name for x in n.names)
            if isinstance(n,ast.ImportFrom) and n.module: imported.add(n.module)
        forbidden={"openai","anthropic","transformers","torch","requests","httpx","urllib","socket","ollama","vllm","litellm"}
        self.assertFalse(any(x.split('.')[0] in forbidden for x in imported),sorted(imported))

    def test_run_waits_on_start_barrier_before_effects(self):
        env,logical=self._env(); events=[]
        class DummyContext: cost_usd=None
        class TestAgent(a.HarborDNAStorageAgent):
            def __init__(self,logs): self.logs_dir=logs
        async def fake_wait(value): self.assertEqual(value,logical); events.append("barrier")
        async def fake_run(instruction,environment): events.append("effect"); return {"schema":a.SCHEMA,"status":"PASS__DNA_STORAGE_AGENT_EXECUTED"}
        with tempfile.TemporaryDirectory() as td,patch.dict(os.environ,env,clear=False),patch.object(a.start_barrier,"await_start_commit",fake_wait),patch.object(a,"run_dna_storage_goal",fake_run):
            asyncio.run(TestAgent(pathlib.Path(td)).run("Implement DNA storage codec",object(),DummyContext()))
            self.assertEqual(events,["barrier","effect"])

if __name__=="__main__": unittest.main(verbosity=2)
