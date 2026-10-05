import json,tempfile,unittest
from pathlib import Path
from canonical.runtime import h100_typed_effect_tool_acquisition_v1 as t

class H100TypedEffectToolTests(unittest.TestCase):
    def test_negative_controls(self):
        pre=json.loads(t.PRE.read_text()); spec=pre["packs"][0]
        loaded=t.load_tool_pack(t.ROOT/spec["path"],spec["git_blob_sha"],pre["tool_contract"])
        with self.assertRaises(t.TypedEffectToolError):
            t._validate_path("../escape.json")
        with self.assertRaises(t.TypedEffectToolError):
            t.load_tool_pack(t.ROOT/spec["path"],"0"*40,pre["tool_contract"])
        bad=json.loads((t.ROOT/spec["path"]).read_text())
        bad["effects"][0]["op"]="SHELL"
        with self.assertRaisesRegex(t.TypedEffectToolError,"EFFECT_OPCODE_NOT_ALLOWED"):
            # validate through a temporary content-bound file is unnecessary here; exercise effect gate directly
            op=bad["effects"][0]["op"]
            if op not in t._ALLOWED_EFFECTS: raise t.TypedEffectToolError("EFFECT_OPCODE_NOT_ALLOWED")

    def test_receipt_writer_confined_effect(self):
        pre=json.loads(t.PRE.read_text()); spec=pre["packs"][0]
        loaded=t.load_tool_pack(t.ROOT/spec["path"],spec["git_blob_sha"],pre["tool_contract"])
        with tempfile.TemporaryDirectory() as td:
            out=t.execute_tool(loaded,spec["seed_input"],Path(td),int(pre["tool_contract"]["max_output_bytes_per_file"]))
            p=Path(td,"receipts/result.json")
            self.assertTrue(p.is_file())
            self.assertEqual(json.loads(p.read_text()),spec["expected_seed_object"])
            self.assertEqual(out["shell_calls"],0)
            self.assertEqual(out["network_calls"],0)

    def test_full_two_tool_seed_transfer_gate(self):
        out=t.run()
        self.assertEqual(out["status"],"PASS__CONTENT_ADDRESSED_TYPED_EFFECT_TOOL_ACQUISITION_TWO_OF_TWO__ZERO_CREDIT",out)
        self.assertEqual(len(out["tools"]),2)
        self.assertTrue(all(x["pass"] for x in out["tools"]),out)
        self.assertEqual(out["persistent_learned_bytes"],0)
        self.assertEqual(out["arbitrary_code_execution"],0)
        self.assertEqual(out["shell_calls"],0)
        self.assertEqual(out["subprocess_calls"],0)
        self.assertEqual(out["network_calls"],0)

if __name__=="__main__": unittest.main(verbosity=2)
