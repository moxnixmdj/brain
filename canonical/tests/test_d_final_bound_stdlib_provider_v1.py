import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime import d_final_bound_stdlib_provider_v1 as p


def _entry(adapter="demo_adapter", source_type="python_stdlib"):
    return {
        "status":"VERIFIED_BOUND_CAPABILITY",
        "incremental_spend_usd":0,
        "verification":{"producer_independent":True},
        "source":{"type":source_type,"module":"json"},
        "adapter_module":adapter,
        "entrypoint":"run",
        "requires":[],
        "provides":["demo.effect"],
        "cost":1,
        "action_template":{
            "type":"invoke_capability",
            "args":{
                "capability_id":"demo.cap",
                "value":"${input.value}"
            },
            "expect":{"type":"field_equals","field":"verified","value":True}
        }
    }


class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory(prefix="d-final-provider-")
        self.root=Path(self.t.name)
        (self.root/"canonical/runtime").mkdir(parents=True)
        self.adapter=self.root/"demo_adapter.py"
        self.adapter.write_text(
            "def run(args,root):\n"
            "    return {'verified': args.get('value') == 'fresh', 'echo': args.get('value')}\n",
            encoding="utf-8",
        )
        self.registry=self.root/"registry.json"
        self._write_registry(_entry())

    def tearDown(self):
        self.t.cleanup()

    def _write_registry(self, entry):
        self.registry.write_text(json.dumps({
            "schema":"PROJECT_BRAIN_BOUND_CAPABILITY_REGISTRY_V1",
            "capabilities":{"demo.cap":entry}
        },sort_keys=True),encoding="utf-8")

    def test_inspect_accepts_exact_verified_stdlib_row(self):
        out=p.inspect("demo.cap",registry_path=self.registry)
        self.assertEqual(out["capability_id"],"demo.cap")
        self.assertEqual(len(out["registry_file_sha256"]),64)
        self.assertEqual(len(out["registry_entry_sha256"]),64)

    def test_registry_file_drift_fails(self):
        out=p.inspect("demo.cap",registry_path=self.registry)
        self.registry.write_text(self.registry.read_text()+"\n",encoding="utf-8")
        with self.assertRaisesRegex(p.DFinalBoundProviderError,"REGISTRY_FILE_SHA256_MISMATCH"):
            p.inspect(
                "demo.cap",
                registry_path=self.registry,
                expected_registry_file_sha256=out["registry_file_sha256"],
            )

    def test_registry_entry_drift_fails(self):
        out=p.inspect("demo.cap",registry_path=self.registry)
        e=_entry()
        e["cost"]=9
        self._write_registry(e)
        with self.assertRaisesRegex(p.DFinalBoundProviderError,"REGISTRY_ENTRY_SHA256_MISMATCH"):
            p.inspect(
                "demo.cap",
                registry_path=self.registry,
                expected_registry_entry_sha256=out["registry_entry_sha256"],
            )

    def test_non_stdlib_row_rejected(self):
        self._write_registry(_entry(source_type="pypi"))
        with self.assertRaisesRegex(p.DFinalBoundProviderError,"SOURCE_NOT_D_FINAL_STDLIB"):
            p.inspect("demo.cap",registry_path=self.registry)

    def test_missing_input_fails_closed(self):
        blob=p._git_blob(self.adapter.read_bytes())
        out=p.execute(
            "demo.cap",
            inputs={},
            repo_root=self.root,
            registry_path=self.registry,
            adapter_path=self.adapter,
            expected_adapter_git_blob_sha=blob,
        )
        self.assertFalse(out["pass"])
        self.assertIn("BOUND_CAPABILITY_INPUT_MISSING:value",out["errors"][0])

    def test_adapter_byte_drift_fails_closed(self):
        blob=p._git_blob(self.adapter.read_bytes())
        self.adapter.write_text("def run(args,root): return {'verified':True}\n",encoding="utf-8")
        out=p.execute(
            "demo.cap",
            inputs={"value":"fresh"},
            repo_root=self.root,
            registry_path=self.registry,
            adapter_path=self.adapter,
            expected_adapter_git_blob_sha=blob,
        )
        self.assertFalse(out["pass"])
        self.assertIn("ADAPTER_GIT_BLOB_MISMATCH",out["errors"][0])

    def test_expectation_failure_fails_closed(self):
        blob=p._git_blob(self.adapter.read_bytes())
        out=p.execute(
            "demo.cap",
            inputs={"value":"not-fresh"},
            repo_root=self.root,
            registry_path=self.registry,
            adapter_path=self.adapter,
            expected_adapter_git_blob_sha=blob,
        )
        self.assertFalse(out["pass"])
        self.assertIn("ACTION_EXPECTATION_FAILED:verified",out["errors"][0])

    def test_render_is_structural_and_fail_closed(self):
        value={"a":"${input.x}","b":["pre-${input.y}-post"]}
        self.assertEqual(p._render(value,{"x":{"k":1},"y":2}),{"a":{"k":1},"b":["pre-2-post"]})
        with self.assertRaisesRegex(p.DFinalBoundProviderError,"BOUND_CAPABILITY_INPUT_MISSING"):
            p._render({"x":"${input.missing}"},{})


if __name__=="__main__":
    unittest.main(verbosity=2)
