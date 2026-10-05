from __future__ import annotations
import base64, hashlib, json, pathlib, subprocess, sys, tempfile, unittest
from unittest.mock import patch

from canonical.runtime import root3_repository_test_execution_executor_v1 as m

ASTRA=("canonical/runtime/astra_runtime.py",1215,"subprocess.run")
AUDIT=("canonical/runtime/bound_capabilities/python_test_audit.py",50,"subprocess.run")
OTHER=("canonical/runtime/auto_python_source_codec_acquisition.py",217,"subprocess.run")

def ctx(root, key=ASTRA, timeout=180):
    p=pathlib.Path(root)/"canonical/tests/test_x.py"
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text("print('ok')\n",encoding="utf-8")
    return {
      "effect_class":"BOUND_CHILD_CODE_EXECUTION",
      "callsite":{"module_path":key[0],"lineno":key[1],"process_api":key[2]},
      "args":([sys.executable,str(p)],),
      "kwargs":{"cwd":pathlib.Path(root),"text":True,"capture_output":True,"timeout":timeout},
    }

class T(unittest.TestCase):
    def test_exact_two_sites_prepare_same_mode_and_bind_test_hash(self):
        with tempfile.TemporaryDirectory() as td:
            for key in (ASTRA,AUDIT):
                x=m._prepare(ctx(td,key))
                self.assertEqual(x["profile"],"REPOSITORY_TEST_EXECUTION")
                self.assertEqual(x["timeout"],180.0)
                self.assertEqual(x["policy"]["input_dir"],str(pathlib.Path(td).resolve()))
                spec=json.loads(base64.urlsafe_b64decode(x["encoded_spec"]).decode())
                raw=(pathlib.Path(td)/"canonical/tests/test_x.py").read_bytes()
                self.assertEqual(spec["test_sha256"],hashlib.sha256(raw).hexdigest())

    def test_other_bound_child_mode_denied_before_spawn(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(m.RepositoryTestExecutionDenied):
                m._prepare(ctx(td,OTHER))

    def test_non_registry_timeout_denied(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(m.RepositoryTestExecutionDenied,"TIMEOUT_NOT_FROZEN_180"):
                m._prepare(ctx(td,ASTRA,181))

    def test_path_outside_repo_denied(self):
        with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as other:
            x=ctx(td)
            p=pathlib.Path(other)/"x.py"; p.write_text("pass\n")
            x["args"]=([sys.executable,str(p)],)
            with self.assertRaises(m.RepositoryTestExecutionDenied):
                m._prepare(x)

    def test_executor_returns_completed_process_from_confined_broker(self):
        with tempfile.TemporaryDirectory() as td:
            x=ctx(td,AUDIT)
            prepared=m._prepare(x)
            payload={
              "timed_out":False,"returncode":0,
              "stdout_b64":base64.b64encode(b"Ran 1 test in 0.1s\nOK\n").decode(),
              "stderr_b64":"","test_sha256":prepared["test_sha256"],
            }
            with patch.object(m.conf,"_run_confined_with_popen",return_value=payload):
                exe=m.make_executor(popen_impl=lambda *a,**k:None,repo_root=td)
                out=exe(x)
            self.assertEqual(out.returncode,0)
            self.assertIn("Ran 1 test",out.stdout)

    def test_broker_hash_drift_denied(self):
        with tempfile.TemporaryDirectory() as td:
            x=ctx(td)
            payload={"timed_out":False,"returncode":0,"stdout_b64":"","stderr_b64":"","test_sha256":"0"*64}
            with patch.object(m.conf,"_run_confined_with_popen",return_value=payload):
                exe=m.make_executor(popen_impl=lambda *a,**k:None,repo_root=td)
                with self.assertRaisesRegex(m.RepositoryTestExecutionDenied,"BROKER_TEST_HASH_MISMATCH"):
                    exe(x)

if __name__=="__main__": unittest.main(verbosity=2)
