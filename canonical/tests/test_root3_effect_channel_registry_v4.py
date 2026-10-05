from __future__ import annotations
import json,tempfile,unittest
from pathlib import Path
from canonical.runtime.root3_effect_channel_registry_v4 import audit,git_blob_sha

def wr(p:Path,text:str)->str:
    p.parent.mkdir(parents=True,exist_ok=True); p.write_text(text,encoding="utf-8"); return git_blob_sha(p.read_bytes())

class C1V4Tests(unittest.TestCase):
    def fixture(self, extra_helper="", import_child=True):
        td=tempfile.TemporaryDirectory(); self.addCleanup(td.cleanup); root=Path(td.name)
        astra=root/"canonical/runtime/astra_runtime.py"
        helper=root/"canonical/runtime/helper.py"
        child=root/"canonical/runtime/new_parser.py"
        adapter=root/"canonical/runtime/bound_capabilities/adapter.py"
        reg=root/"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
        parent=root/"canonical/governance/ROOT3_EFFECT_CHANNEL_REGISTRY_C1_CANDIDATE_V2.json"
        manifest=root/"canonical/governance/ROOT3_EFFECT_CHANNEL_REGISTRY_C1_CANDIDATE_V4.json"
        wr(astra,"from canonical.runtime import helper\n")
        helper_text=("from canonical.runtime import new_parser\n" if import_child else "")+"import urllib.request\nfrom pathlib import Path\ndef f():\n    urllib.request.urlopen('x')\n    Path('x').write_text('x')\n"+extra_helper
        wr(helper,helper_text); wr(child,"from pathlib import Path\ndef read(p): return Path(p).read_bytes()\n"); wr(adapter,"import sympy\ndef run(): return 1\n")
        reg.parent.mkdir(parents=True,exist_ok=True); reg.write_text(json.dumps({"capabilities":{}})); rsha=git_blob_sha(reg.read_bytes())
        pobj={"subject":{"astra_runtime":{"path":"canonical/runtime/astra_runtime.py"}},"expected_repo_dynamic_universe":{"fixed_loader_sites":{"x":"canonical/runtime/helper.py"},"literal_runtime_helpers":[],"ordinary_adapter_modules":["adapter"]}}
        parent.parent.mkdir(parents=True,exist_ok=True); parent.write_text(json.dumps(pobj)); psha=git_blob_sha(parent.read_bytes())
        m={"schema":"PROJECT_BRAIN_ROOT3_EFFECT_CHANNEL_REGISTRY_C1_CANDIDATE_V4","parent":{"path":str(parent.relative_to(root)),"git_blob_sha":psha},"bound_registry":{"path":str(reg.relative_to(root)),"git_blob_sha":rsha},"declared":{"network_modules":["canonical/runtime/helper.py"],"child_process_modules":[],"local_filesystem_write_modules":["canonical/runtime/helper.py"],"inprocess_third_party_imports":{"canonical/runtime/bound_capabilities/adapter.py":["sympy"]},"registry_constrained_dynamic_imports":{},"untrusted_dynamic_import_modules":{}}}
        manifest.write_text(json.dumps(m))
        return root,str(manifest.relative_to(root))
    def test_recursive_from_import_is_visible_and_passes(self):
        root,m=self.fixture(); out=audit(root,m); self.assertTrue(out["pass"],out); self.assertIn("canonical/runtime/new_parser.py",out["closure_git_blobs"])
    def test_undeclared_subprocess_fails_closed(self):
        root,m=self.fixture(extra_helper="    import subprocess\n    subprocess.run(['true'])\n"); out=audit(root,m); self.assertFalse(out["pass"]); self.assertTrue(any(x.startswith("UNDECLARED_CHILD_PROCESS:") for x in out["errors"]))
    def test_stale_effect_declaration_fails_closed(self):
        root,m=self.fixture(); obj=json.loads((root/m).read_text()); obj["declared"]["child_process_modules"]=["canonical/runtime/helper.py"]; (root/m).write_text(json.dumps(obj)); out=audit(root,m); self.assertFalse(out["pass"]); self.assertTrue(any(x.startswith("STALE_DECLARED_CHILD_PROCESS:") for x in out["errors"]))
    def test_git_blob_known_vector(self):
        self.assertEqual(git_blob_sha(b"hello\n"),"ce013625030ba8dba906f756967f9e9ca394464a")
if __name__=="__main__": unittest.main(verbosity=2)
