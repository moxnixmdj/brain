import json,tempfile,unittest
from pathlib import Path
from canonical.runtime import h100_verified_effect_tool_registry_v1 as r

class H100EffectToolRegistryV1Tests(unittest.TestCase):
    def test_snapshot(self):
        s=r.registry_snapshot()
        self.assertEqual(s["entry_count"],2)
        self.assertEqual(s["persistent_learned_bytes"],0)

    def test_receipt_writer_transfer_invocation(self):
        with tempfile.TemporaryDirectory() as td:
            out=r.invoke("JSON_RECEIPT_WRITER_V1",{"name":"Bob","score":-1.25,"passed":False},Path(td))
            self.assertEqual(out["status"],"VERIFIED_EFFECT_TOOL_INVOKED")
            self.assertEqual(out["raw_tool_acquisition_attempts_before_hit"],0)
            obj=json.loads(Path(td,"receipts/result.json").read_text())
            self.assertEqual(obj,{"name":"Bob","score":-1.25,"passed":False,"schema":"H100_TOOL_RECEIPT_V1"})

    def test_ledger_seed_plus_transfer(self):
        with tempfile.TemporaryDirectory() as td:
            r.invoke("JSONL_LEDGER_APPEND_V1",{"event":"alpha","value":7},Path(td))
            r.invoke("JSONL_LEDGER_APPEND_V1",{"event":"beta","value":-3},Path(td))
            rows=[json.loads(x) for x in Path(td,"ledger/events.jsonl").read_text().splitlines()]
            self.assertEqual(rows,[
                {"event":"alpha","value":7,"schema":"H100_LEDGER_EVENT_V1"},
                {"event":"beta","value":-3,"schema":"H100_LEDGER_EVENT_V1"}
            ])

    def test_unknown_tool_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(r.EffectToolRegistryError,"TOOL_ID_NOT_VERIFIED"):
                r.invoke("SHELL_ANYTHING_V1",{},Path(td))

if __name__=="__main__": unittest.main(verbosity=2)
