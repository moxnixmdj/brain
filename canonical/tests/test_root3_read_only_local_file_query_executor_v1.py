from __future__ import annotations
import json
import pathlib
import sqlite3
import subprocess
import tempfile
import tarfile
import unittest

from canonical.runtime import root3_read_only_local_file_query_executor_v1 as ro
from canonical.runtime import root3_subprocess_mediator_v2 as mediator
from canonical.runtime.root3_subprocess_effect_class_registry_v1 import EXPECTED
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

    def test_supported_subset_is_exactly_five_of_current_eight(self):
        current={k for k,v in EXPECTED.items() if v=="READ_ONLY_DECLARED_QUERY"}
        self.assertEqual(len(current),5)
        self.assertEqual(len(ro.SUPPORTED),5)
        self.assertTrue(set(ro.SUPPORTED).issubset(current))
        self.assertEqual(len(current-set(ro.SUPPORTED)),0)

    def test_target_is_nested_inside_namespace_wrapper_not_raw_spawn(self):
        import base64
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            src=root/"in.json"; src.write_text('{"x":1}\n',encoding="utf-8")
            ctx={
              "effect_class":"READ_ONLY_DECLARED_QUERY",
              "callsite":{
                "module_path":"canonical/runtime/bound_capabilities/jq_query.py",
                "lineno":41,"process_api":"subprocess.run",
              },
              "args":(["jq","-r",".x",str(src)],),
              "kwargs":{"cwd":root,"text":True,"capture_output":True,"timeout":60},
            }
            prepared=ro._prepare(ctx)
            policy=prepared["policy"]
            self.assertEqual(policy["argv"][0],"/usr/bin/python3")
            self.assertEqual(policy["argv"][1:3],["-I","-c"])
            spec=json.loads(base64.urlsafe_b64decode(policy["argv"][4]).decode("utf-8"))
            self.assertEqual(pathlib.Path(spec["argv"][0]).name,"jq")
            self.assertEqual(spec["argv"][-1],"/input/in.json")
            self.assertEqual(spec["cwd"],"/input")

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

    def test_real_tar_listing_runs_inside_namespace(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            payload=root/"x.txt"; payload.write_text("hello\n",encoding="utf-8")
            archive=root/"a.tar.gz"
            with tarfile.open(archive,"w:gz") as tf:
                tf.add(payload,arcname="x.txt")
            ex=ro.make_executor(popen_impl=mediator._ORIGINAL_POPEN)
            ctx={
              "effect_class":"READ_ONLY_DECLARED_QUERY",
              "callsite":{
                "module_path":"canonical/runtime/bound_capabilities/archive_verify_gnu_tar.py",
                "lineno":32,"process_api":"subprocess.run",
              },
              "args":(["tar","-tzf",str(archive)],),
              "kwargs":{"text":True,"capture_output":True,"timeout":60},
            }
            p=ex(ctx)
            self.assertEqual(p.returncode,0)
            self.assertEqual(p.stdout.strip(),"x.txt")

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
