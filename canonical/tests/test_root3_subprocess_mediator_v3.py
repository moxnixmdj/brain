from __future__ import annotations
import base64,json,pathlib,subprocess,tempfile,unittest
from unittest.mock import patch

from canonical.runtime import root3_subprocess_mediator_v3 as m
from canonical.runtime import root3_readonly_namespace_plan_v1 as planner
from canonical.runtime import zero_ambient_namespace_launcher_v1 as ns
from canonical.runtime.bound_capabilities import jq_query

class MediatorV3Tests(unittest.TestCase):
    def tearDown(self):
        try: m.uninstall()
        except Exception:
            subprocess.run=m._ORIGINAL_RUN
            subprocess.Popen=m._ORIGINAL_POPEN
            m._AUTHORIZER=None
            m._AUTHORITY_ID=None
            m._CLASS_PLANNERS={}
            m._INSTALLED=False

    def allow(self,seen):
        def auth(request):
            seen.append(dict(request))
            return {"allowed":True,"authorization_sha256":"a"*64}
        return auth

    def fake_carrier(self,seen):
        def run(policy,*,popen_impl):
            seen.append((policy,popen_impl))
            payload=(json.dumps({
              "returncode":0,
              "stdout_b64":base64.b64encode(b'{"x":1}\n').decode(),
              "stderr_b64":""
            },sort_keys=True,separators=(",",":"))+"\n").encode()
            return {"status":"CHILD_EXITED","broker_payload":payload}
        return run

    def test_jq_routes_plan_to_mediator_owned_carrier(self):
        auth_seen=[]; carrier_seen=[]
        with tempfile.TemporaryDirectory() as td, \
             patch.object(planner.shutil,"which",side_effect=lambda x:"/usr/bin/python3" if x=="python3" else "/usr/bin/"+x), \
             patch.object(planner.os,"geteuid",return_value=1001), patch.object(planner.os,"getegid",return_value=1001), \
             patch.object(ns.os,"geteuid",return_value=1001), patch.object(ns.os,"getegid",return_value=1001), \
             patch.object(m.ns,"_run_confined",side_effect=self.fake_carrier(carrier_seen)):
            root=pathlib.Path(td); (root/"in.json").write_text('{"x":1}\n')
            m.install(self.allow(auth_seen),authority_id="T",class_planners={"READ_ONLY_DECLARED_QUERY":planner.build})
            out=jq_query.run({"input_path":"in.json","output_path":"out.txt","filter":"."},root)
        self.assertTrue(out["output_verified"])
        self.assertEqual(len(auth_seen),1)
        self.assertEqual(len(carrier_seen),1)
        self.assertIs(carrier_seen[0][1],m._ORIGINAL_POPEN)

    def test_missing_plan_denies(self):
        m.install(lambda r:{"allowed":True,"authorization_sha256":"b"*64},authority_id="T")
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td); (root/"in.json").write_text('{"x":1}\n')
            with self.assertRaisesRegex(Exception,"PLANNER_NOT_BOUND"):
                jq_query.run({"input_path":"in.json","output_path":"out.txt","filter":"."},root)

    def test_planner_cannot_spawn(self):
        def bad(context):
            subprocess.run(["nested"])
        m.install(lambda r:{"allowed":True,"authorization_sha256":"c"*64},authority_id="T",class_planners={"READ_ONLY_DECLARED_QUERY":bad})
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td); (root/"in.json").write_text('{"x":1}\n')
            with self.assertRaisesRegex(Exception,"DURING_CLASS_PLANNER"):
                jq_query.run({"input_path":"in.json","output_path":"out.txt","filter":"."},root)

    def test_uninstall_restores_exact_originals(self):
        m.install(lambda r:{"allowed":False},authority_id="T")
        m.uninstall()
        self.assertIs(subprocess.run,m._ORIGINAL_RUN)
        self.assertIs(subprocess.Popen,m._ORIGINAL_POPEN)

if __name__=="__main__": unittest.main(verbosity=2)
