#!/usr/bin/env python3
import hashlib,importlib.util,json,pathlib,sys,tempfile,unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
RUNTIME=ROOT/"runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0,str(RUNTIME))
spec=importlib.util.spec_from_file_location("source_codec_acq_target",RUNTIME/"auto_python_source_codec_acquisition.py")
src=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=src
spec.loader.exec_module(src)

def git_blob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def tree(files):
    rows=[]
    for path,content in files.items():
        raw=content.encode()
        rows.append({"path":path,"content":content,"git_blob_sha":git_blob(raw)})
    return {
      "schema":"PROJECT_BRAIN_EXTERNAL_SOURCE_TREE_V1",
      "repository":"example/codec",
      "revision":"a"*40,
      "files":rows,
    }

class SourceCodecAcquisitionTests(unittest.TestCase):
    def tearDown(self):
        src.set_external_source_tree_provider(None)

    def test_git_blob_mismatch_fails_closed(self):
        t=tree({"codec/__init__.py":"def dumpb(x): return b'x'\ndef loadb(x): return []\n"})
        t["files"][0]["git_blob_sha"]="0"*40
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(src.AutoPythonSourceCodecFailure,"SOURCE_TREE_GIT_BLOB_MISMATCH"):
                src._materialize(t,pathlib.Path(td))

    def test_non_python_build_file_is_rejected(self):
        t=tree({
          "codec/__init__.py":"def dumpb(x): return b'x'\ndef loadb(x): return []\n",
          "setup.py":"raise RuntimeError('must never execute')\n",
        })
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(src.AutoPythonSourceCodecFailure,"SOURCE_TREE_TOP_LEVEL_MODULE_UNSUPPORTED|SOURCE_TREE_NON_PYTHON_FILE"):
                src._materialize(t,pathlib.Path(td))

    def test_dispatch_creates_pending_binding_from_semantic_source_tree(self):
        module=(
          "import json\n"
          "def dumpb(value): return json.dumps(value,separators=(',',':')).encode()\n"
          "def loadb(payload): return json.loads(payload.decode())\n"
        )
        supplied=tree({"codec/__init__.py":module})
        src.set_external_source_tree_provider(lambda **kw: {"trees":[supplied]})
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            mission=root/"canonical"/"astra_runtime"/"missions"/"M.json"
            mission.parent.mkdir(parents=True)
            mission.write_text('{"mission_id":"M","steps":[]}\n')
            runtime=root/"canonical"/"runtime"; runtime.mkdir(parents=True)
            probe=(RUNTIME/"python_codec_probe.py").read_text()
            (runtime/"python_codec_probe.py").write_text(probe)
            out=src.dispatch(
              "Encode canonical/input.json as UBJSON and save canonical/output.ubj",
              "M","canonical/astra_runtime/missions/M.json",root,
            )
            pending=json.loads((root/out["pending_binding_path"]).read_text())
            verifier_path=root/out["verification_mission_path"]
            self.assertTrue(verifier_path.is_file())
            verifier=json.loads(verifier_path.read_text())
        self.assertEqual(out["status"],"ACQUISITION_DISPATCHED")
        self.assertEqual(out["supplier_class"],"content_addressed_python_source_tree")
        self.assertEqual(pending["contract"]["encode_callable"],"dumpb")
        self.assertEqual(pending["contract"]["decode_callable"],"loadb")
        self.assertEqual(pending["status"],"PENDING_INDEPENDENT_VERIFICATION")
        self.assertEqual(pending["registry_entry"]["source"]["type"],"git_source_tree")
        self.assertIn("structured.binary.encode.ubj",pending["registry_entry"]["provides"])
        self.assertEqual(verifier["steps"][0]["verify"]["text"],"PENDING_SOURCE_BINDING_EFFECT_VERIFIED")

if __name__=="__main__":
    unittest.main(verbosity=2)
