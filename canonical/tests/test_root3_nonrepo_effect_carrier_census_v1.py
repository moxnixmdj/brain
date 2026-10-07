from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from canonical.runtime.root3_nonrepo_effect_carrier_census_v1 import (
    CarrierCensusError, compile_census, git_blob_sha,
)


class CarrierCensusTests(unittest.TestCase):
    def _fixture(self, root: Path):
        adir=root/"canonical/runtime/bound_capabilities"
        adir.mkdir(parents=True)
        texts={
          "inp":"import thirdparty\ndef run(): return 1\n",
          "child":"import subprocess\ndef run(): return subprocess.run(['x'])\n",
          "browser":"import subprocess,urllib.request\ndef run():\n subprocess.Popen(['chromedriver']); x='127.0.0.1'\n",
        }
        blobs={}
        for name,text in texts.items():
            p=adir/(name+".py"); p.write_text(text); blobs[name]=git_blob_sha(p.read_bytes())
        reg=root/"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
        reg.write_text(json.dumps({"capabilities":{
          "A":{"source":{"type":"pypi"},"adapter_module":"inp"},
          "B":{"source":{"type":"apt"},"adapter_module":"child"},
          "C":{"source":{"type":"system_tool"},"adapter_module":"browser"},
          "D":{"source":{"type":"python_stdlib"},"adapter_module":"ignored"},
        }}))
        manifest=root/"canonical/governance/ROOT3_NONREPO_EFFECT_CARRIER_CENSUS_C1_CANDIDATE_V1.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({
          "schema":"PROJECT_BRAIN_ROOT3_NONREPO_EFFECT_CARRIER_CENSUS_C1_CANDIDATE_V1",
          "subject":{"registry_path":"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json","registry_git_blob_sha":git_blob_sha(reg.read_bytes())},
          "expected_nonrepo_source_types":["apt","pypi","system_tool"],
          "expected_nonrepo_capability_ids":["A","B","C"],
          "adapter_carrier_map":{"inp":"IN_PROCESS_THIRD_PARTY_PYTHON","child":"CHILD_PROCESS_TOOL","browser":"EXTERNAL_BROWSER_BRIDGE"},
          "adapter_blobs":blobs,
          "expected_counts":{"nonrepo_capabilities":3,"unique_nonrepo_adapters":3,"IN_PROCESS_THIRD_PARTY_PYTHON":1,"CHILD_PROCESS_TOOL":1,"EXTERNAL_BROWSER_BRIDGE":1},
        }))
        return manifest

    def test_three_carrier_census(self):
        with TemporaryDirectory() as td:
            root=Path(td); self._fixture(root)
            out=compile_census(root,"canonical/governance/ROOT3_NONREPO_EFFECT_CARRIER_CENSUS_C1_CANDIDATE_V1.json")
            self.assertEqual(out["nonrepo_capability_count"],3)
            self.assertEqual(out["unique_nonrepo_adapter_count"],3)
            self.assertFalse(out["c1_scope_complete"])
            self.assertEqual(out["acceptance_credit_delta"],0)

    def test_blob_drift_fails_closed(self):
        with TemporaryDirectory() as td:
            root=Path(td); self._fixture(root)
            p=root/"canonical/runtime/bound_capabilities/inp.py"
            p.write_text(p.read_text()+"# drift\n")
            with self.assertRaisesRegex(CarrierCensusError,"ADAPTER_BLOB_DRIFT"):
                compile_census(root,"canonical/governance/ROOT3_NONREPO_EFFECT_CARRIER_CENSUS_C1_CANDIDATE_V1.json")

    def test_inprocess_subprocess_bypass_fails_closed(self):
        with TemporaryDirectory() as td:
            root=Path(td); m=self._fixture(root)
            p=root/"canonical/runtime/bound_capabilities/inp.py"
            p.write_text("import subprocess\ndef run(): subprocess.run(['x'])\n")
            d=json.loads(m.read_text())
            d["adapter_blobs"]["inp"]=git_blob_sha(p.read_bytes())
            m.write_text(json.dumps(d))
            with self.assertRaisesRegex(CarrierCensusError,"IN_PROCESS_ADAPTER_HAS_SUBPROCESS"):
                compile_census(root,"canonical/governance/ROOT3_NONREPO_EFFECT_CARRIER_CENSUS_C1_CANDIDATE_V1.json")


if __name__=="__main__":
    unittest.main(verbosity=2)
