#!/usr/bin/env python3
import hashlib,importlib.util,json,pathlib,shutil,sys,tempfile,unittest
from unittest import mock

CANONICAL_ROOT=pathlib.Path(__file__).resolve().parents[1]
RUNTIME=CANONICAL_ROOT/"runtime"
if str(RUNTIME) not in sys.path: sys.path.insert(0,str(RUNTIME))

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec); sys.modules[name]=module; spec.loader.exec_module(module); return module

github=load("github_source_fallback_github",RUNTIME/"auto_github_source_acquisition.py")
acquire=load("github_source_fallback_router",RUNTIME/"auto_capability_acquisition.py")
runtime=load("github_source_fallback_runtime",RUNTIME/"astra_runtime.py")
adapter=load("github_source_fallback_adapter",RUNTIME/"bound_capabilities"/"github_source_codec.py")
verifier=load("github_source_fallback_verifier",RUNTIME/"verify_pending_cli_binding.py")

class GitHubSourceFallbackTests(unittest.TestCase):
    goal="Encode canonical/CANONICAL_POINTER.json as UBJSON and save canonical/astra_runtime/artifacts/out.ubj"

    def test_generic_binary_encode_goal_is_supported(self):
        self.assertTrue(github.supports(self.goal))
        self.assertFalse(github.supports("read a text file"))

    def test_router_falls_through_to_github_source(self):
        with mock.patch.object(acquire.auto_pypi_library_acquisition,"supports",return_value=True), \
             mock.patch.object(acquire.auto_pypi_library_acquisition,"dispatch",side_effect=RuntimeError("pypi blocked")), \
             mock.patch.object(acquire.auto_apt_cli_acquisition,"dispatch",side_effect=RuntimeError("apt blocked")), \
             mock.patch.object(acquire.auto_github_source_acquisition,"supports",return_value=True), \
             mock.patch.object(acquire.auto_github_source_acquisition,"dispatch",return_value={"status":"ACQUISITION_DISPATCHED","supplier_class":"github_source_python"}):
            out=acquire.dispatch(self.goal,"M","canonical/astra_runtime/missions/M.json",CANONICAL_ROOT.parent)
        self.assertEqual(out["supplier_class"],"github_source_python")

    def test_origin_mission_authority_is_frozen(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            mission=root/"canonical"/"astra_runtime"/"missions"/"M.json"
            mission.parent.mkdir(parents=True); mission.write_text('{"x":1}\n')
            self.assertEqual(github._origin_mission_sha256(root,"canonical/astra_runtime/missions/M.json"),hashlib.sha256(mission.read_bytes()).hexdigest())
            with self.assertRaises(github.AutoGitHubSourceAcquisitionFailure):
                github._origin_mission_sha256(root,"../outside.json")

    def test_source_rematerialization_verifies_hashes(self):
        raw=b"def dumps(x): return b'X'\ndef loads(x): return {'ok':1}\n"
        git_sha=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
        source={"type":"github_source","repository":"owner/repo","commit_sha":"a"*40,"files":[{
            "path":"codec.py","git_blob_sha1":git_sha,"sha256":hashlib.sha256(raw).hexdigest(),
            "size":len(raw),"raw_url":"https://raw.githubusercontent.com/owner/repo/"+"a"*40+"/codec.py"}]}
        class Response:
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def read(self,n=-1): return raw
        with tempfile.TemporaryDirectory() as td:
            old=runtime.ROOT; runtime.ROOT=pathlib.Path(td)
            try:
                with mock.patch.object(runtime.urllib.request,"urlopen",return_value=Response()):
                    dep=runtime._ensure_github_source_dependency(source)
                self.assertEqual(pathlib.Path(dep["source_root"],"codec.py").read_bytes(),raw)
                bad=json.loads(json.dumps(source)); bad["files"][0]["sha256"]="0"*64
                with mock.patch.object(runtime.urllib.request,"urlopen",return_value=Response()):
                    with self.assertRaisesRegex(runtime.Blocker,"SHA256_MISMATCH"):
                        runtime._ensure_github_source_dependency(bad)
            finally: runtime.ROOT=old

    def test_bound_adapter_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td); source=root/"source"; source.mkdir()
            (source/"codec.py").write_text("import json\ndef dumps(x): return json.dumps(x).encode()\ndef loads(b): return json.loads(b.decode())\n")
            (root/"in.json").write_text('{"a":[1,2]}')
            rt=root/"canonical"/"runtime"; rt.mkdir(parents=True)
            shutil.copy(RUNTIME/"github_source_codec_runner.py",rt/"github_source_codec_runner.py")
            observed=adapter.run({"_source_root":str(source),"module":"codec","encode_callable":"dumps","decode_callable":"loads","json_path":"in.json","output_path":"out.bin"},root)
            self.assertTrue(observed["output_verified"])
            decoded=adapter.run({"_source_root":str(source),"module":"codec","encode_callable":"dumps","decode_callable":"loads","mode":"decode_verify","binary_path":"out.bin"},root)
            self.assertTrue(decoded["verified"]); self.assertEqual(decoded["observed"],{"a":[1,2]})

    def test_independent_verifier_uses_distinct_repository(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td); runtime_dir=root/"canonical"/"runtime"; runtime_dir.mkdir(parents=True)
            shutil.copy(RUNTIME/"github_source_codec_runner.py",runtime_dir/"github_source_codec_runner.py")
            source=root/"verifier"; source.mkdir()
            (source/"codec2.py").write_text("import json\ndef loads(b): return json.loads(b.decode())\ndef dumps(x): return json.dumps(x).encode()\n")
            fixture=root/"fixture.json"; fixture.write_text('{"x":[1,2]}')
            output=root/"out.bin"; output.write_bytes(b'{"x":[1,2]}')
            pending={"goal":self.goal,"registry_entry":{"source":{"type":"github_source","repository":"prod/repo"}}}
            mat={"repo":"verify/repo","commit_sha":"b"*40,"source_root":source,"files":[],"modules":["codec2"]}
            contract={"module":"codec2","encode_callable":"dumps","decode_callable":"loads"}
            old=verifier.ROOT; verifier.ROOT=root
            try:
                with mock.patch.object(verifier.auto_github_source_acquisition,"_search",return_value=[{"repo":"prod/repo"},{"repo":"verify/repo"}]), \
                     mock.patch.object(verifier.auto_github_source_acquisition,"_materialize_candidate",return_value=mat), \
                     mock.patch.object(verifier.auto_github_source_acquisition,"_probe",return_value=contract):
                    result=verifier._independent_github_source_verifier(pending,fixture,output)
            finally: verifier.ROOT=old
            self.assertTrue(result["verified"]); self.assertEqual(result["verifier_repository"],"verify/repo")
            self.assertNotEqual(result["producer_repository"],result["verifier_repository"])

if __name__=="__main__":
    unittest.main(verbosity=2)
