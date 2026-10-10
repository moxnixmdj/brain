from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import professional_quality_subject_dependency_closure_v2 as d

def blob(path:Path)->str:
    raw=path.read_bytes()
    return sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def write(path:Path,value)->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(value if isinstance(value,str) else json.dumps(value,indent=2)+"\n")

class SubjectDependencyClosureV2Tests(unittest.TestCase):
    def _repo(self,*,dynamic=False):
        td=tempfile.TemporaryDirectory(); root=Path(td.name)
        base=root/"canonical/runtime/base.py"
        child=root/"canonical/runtime/child.py"
        external_tool=root/"canonical/runtime/external_tool.py"
        config=root/"canonical/governance/config.json"
        evidence=root/"canonical/verification/evidence.json"
        scope=root/"canonical/governance/scope.json"
        write(child,"VALUE=1\n");write(external_tool,"VALUE=2\n")
        write(config,{"x":1});write(evidence,{"pass":True});write(scope,{"scope":"bounded"})
        src="from canonical.runtime import child\nCONFIG='canonical/governance/config.json'\nRECEIPT='canonical/verification/evidence.json'\n"
        if dynamic:src+="import importlib\nname='canonical.runtime.'+'late'\nimportlib.import_module(name)\n"
        write(base,src)
        subject_path=root/"canonical/governance/subject.json"
        write(subject_path,{"system_material":{"components":[{"path":"canonical/runtime/base.py","git_blob_sha":blob(base)}]}})
        write(root/d.WORKLIST_PATH,{"candidate_subject":{"path":"canonical/governance/subject.json","git_blob_sha":blob(subject_path)}})
        entries=[]
        for rid in d.EXPECTED_ROOTS:
            entries.append({
                "root_id":rid,"scope_id":rid+"::S",
                "reusable_compiler":{"path":"canonical/runtime/external_tool.py","git_blob_sha":blob(external_tool)},
                "source_receipt":{"path":"canonical/verification/evidence.json","git_blob_sha":blob(evidence)},
                "scope_governance":{"path":"canonical/governance/scope.json","git_blob_sha":blob(scope)},
            })
        write(root/d.REGISTRY_PATH,{"entries":entries})
        return td,root

    def test_subject_seed_not_external_verifier_tooling(self):
        td,root=self._repo()
        with td:out=d.compile_closure(repo_root=root)
        self.assertTrue(out["pass"],out)
        self.assertIn("canonical/runtime/child.py",out["missing_subject_components"])
        self.assertIn("canonical/governance/config.json",out["missing_subject_components"])
        self.assertNotIn("canonical/runtime/external_tool.py",out["required_system_material"])
        for row in out["roots"]:
            self.assertEqual(row["system_material_mechanisms"],[])
            self.assertEqual(row["external_verification_mechanisms"],["canonical/runtime/external_tool.py"])

    def test_verification_and_scope_receipts_remain_external(self):
        td,root=self._repo()
        with td:out=d.compile_closure(repo_root=root)
        self.assertIn("canonical/verification/evidence.json",out["runtime_external_evidence_references"])
        self.assertNotIn("canonical/verification/evidence.json",out["required_system_material"])
        for row in out["roots"]:
            self.assertIn("canonical/verification/evidence.json",row["external_evidence_inputs"])
            self.assertIn("canonical/governance/scope.json",row["external_evidence_inputs"])

    def test_subject_can_close_after_exact_missing_material_added(self):
        td,root=self._repo()
        with td:
            first=d.compile_closure(repo_root=root)
            sp=root/"canonical/governance/subject.json";subject=json.loads(sp.read_text())
            for rel in first["missing_subject_components"]:
                p=root/rel
                subject["system_material"]["components"].append({"path":rel,"git_blob_sha":blob(p)})
            write(sp,subject)
            second=d.compile_closure(repo_root=root)
        self.assertTrue(second["pass"],second)
        self.assertTrue(second["subject_dependency_closure_complete"])
        self.assertEqual(second["missing_subject_component_count"],0)

    def test_dynamic_import_in_declared_system_fails_closed(self):
        td,root=self._repo(dynamic=True)
        with td:out=d.compile_closure(repo_root=root)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"TRANSITIVE_RUNTIME_CLOSURE_OPEN")

    def test_all_twelve_roots_required(self):
        td,root=self._repo()
        with td:
            p=root/d.REGISTRY_PATH;o=json.loads(p.read_text());o["entries"]=o["entries"][:-1];write(p,o)
            out=d.compile_closure(repo_root=root)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"ROOT_SCOPED_SUPPORT_MISSING")

if __name__=="__main__":
    unittest.main()
