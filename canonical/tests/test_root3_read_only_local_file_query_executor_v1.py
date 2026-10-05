from __future__ import annotations
import json
import pathlib
import sqlite3
import subprocess
import tempfile
import unittest

from canonical.runtime import root3_read_only_local_file_query_executor_v1 as ro
from canonical.runtime import root3_subprocess_mediator_v2 as mediator
from canonical.runtime.bound_capabilities import jq_query, sqlite_verify_cli


class ReadOnlyLocalFileExecutorTests(unittest.TestCase):
    def tearDown(self):
        try:
            mediator.uninstall()
        except Exception:
            subprocess.run = mediator._ORIGINAL_RUN
            subprocess.Popen = mediator._ORIGINAL_POPEN
            mediator._AUTHORIZER = None
            mediator._AUTHORITY_ID = None
            mediator._CLASS_EXECUTORS = {}
            mediator._INSTALLED = False

    def allow(self, request):
        return {"allowed": True, "authorization_sha256": "a" * 64}

    def test_unsupported_apt_metadata_site_denies_before_spawn(self):
        calls=[]
        def never(*a,**kw):
            calls.append((a,kw))
            raise AssertionError("spawned")
        ex=ro.make_executor(popen_impl=never)
        ctx={
          "effect_class":"READ_ONLY_DECLARED_QUERY",
          "callsite":{
            "module_path":"canonical/runtime/capability_discovery.py",
            "lineno":267,
            "process_api":"subprocess.run",
          },
          "args":(["apt-cache","search","json"],),
          "kwargs":{"text":True,"capture_output":True,"timeout":20},
        }
        with self.assertRaisesRegex(ro.ReadOnlyQueryDenied,"NOT_YET_SUPPORTED"):
            ex(ctx)
        self.assertEqual(calls,[])

    def test_sqlite_update_is_rejected_before_spawn(self):
        calls=[]
        ex=ro.make_executor(popen_impl=lambda *a,**kw: calls.append(1))
        with tempfile.TemporaryDirectory() as td:
            db=pathlib.Path(td)/"x.db"; sqlite3.connect(db).close()
            ctx={
              "effect_class":"READ_ONLY_DECLARED_QUERY",
              "callsite":{
                "module_path":"canonical/runtime/bound_capabilities/sqlite_verify_cli.py",
                "lineno":66,"process_api":"subprocess.run",
              },
              "args":(["sqlite3","-json",str(db),"UPDATE x SET y=1"],),
              "kwargs":{"text":True,"capture_output":True,"timeout":60},
            }
            with self.assertRaisesRegex(ro.ReadOnlyQueryDenied,"MUTATING_OR_UNKNOWN_SQL"):
                ex(ctx)
        self.assertEqual(calls,[])

    def test_real_jq_call_routes_through_mediator_and_namespace(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            (root/"in.json").write_text('{"x":1}\n',encoding="utf-8")
            ex=ro.make_executor(popen_impl=mediator._ORIGINAL_POPEN)
            mediator.install(
                self.allow,
                authority_id="TEST",
                class_executors={"READ_ONLY_DECLARED_QUERY":ex},
            )
            out=jq_query.run(
                {"input_path":"in.json","output_path":"out.txt","filter":".x"},
                root,
            )
            self.assertTrue(out["output_verified"])
            self.assertEqual((root/"out.txt").read_text(encoding="utf-8").strip(),"1")

    def test_real_sqlite_verifier_routes_all_queries_through_namespace(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            source={"records":{"cap_a":{"status":"READY","value":"7"}}}
            (root/"source.json").write_text(json.dumps(source),encoding="utf-8")
            db=root/"x.db"
            con=sqlite3.connect(db)
            con.execute("create table capabilities(capability_id text primary key,status text,value text)")
            con.execute("insert into capabilities values('cap_a','READY','7')")
            con.commit(); con.close()
            ex=ro.make_executor(popen_impl=mediator._ORIGINAL_POPEN)
            mediator.install(
                self.allow,
                authority_id="TEST",
                class_executors={"READ_ONLY_DECLARED_QUERY":ex},
            )
            out=sqlite_verify_cli.run(
                {
                  "json_path":"source.json",
                  "sqlite_path":"x.db",
                  "goal":"verify table named capabilities READY",
                },
                root,
            )
            self.assertTrue(out["verified"])
            self.assertEqual(out["verified_rows"],1)

    def test_yq_and_tesseract_are_structurally_guarded_even_if_tools_absent(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            y=root/"x.yaml"; y.write_text("a: 1\n")
            yctx={
              "effect_class":"READ_ONLY_DECLARED_QUERY",
              "callsite":{
                "module_path":"canonical/runtime/bound_capabilities/yq_yaml_json.py",
                "lineno":21,"process_api":"subprocess.run",
              },
              "args":(["yq",".",str(y)],),
              "kwargs":{"cwd":root,"text":True,"capture_output":True,"timeout":60},
            }
            if subprocess.run(["sh","-c","command -v yq >/dev/null"]).returncode != 0:
                with self.assertRaisesRegex(ro.ReadOnlyQueryDenied,"EXECUTABLE_UNAVAILABLE"):
                    ro._prepare(yctx)
            image=root/"p.png"; image.write_bytes(b"not-a-real-image")
            tctx={
              "effect_class":"READ_ONLY_DECLARED_QUERY",
              "callsite":{
                "module_path":"canonical/runtime/bound_capabilities/pdf_ocr_tesseract.py",
                "lineno":44,"process_api":"subprocess.run",
              },
              "args":(["tesseract",str(image),"stdout","-l","eng","--psm","6"],),
              "kwargs":{"text":True,"capture_output":True,"timeout":180},
            }
            if subprocess.run(["sh","-c","command -v tesseract >/dev/null"]).returncode != 0:
                with self.assertRaisesRegex(ro.ReadOnlyQueryDenied,"EXECUTABLE_UNAVAILABLE"):
                    ro._prepare(tctx)


if __name__=="__main__":
    unittest.main(verbosity=2)
