from __future__ import annotations
import unittest
from canonical.runtime import root3_bound_class_admission_v1 as admission

def req(path,line,cls,argv,**kw):
    return {
      "schema":"PROJECT_BRAIN_ROOT3_SUBPROCESS_MEDIATOR_REQUEST_V2",
      "api":"subprocess.run",
      "command":{"kind":"ARGV","items":[{"kind":"STRING","value":x} for x in argv]},
      "cwd":kw.get("cwd"),"env":None,"stdin":None,"stdout":None,"stderr":None,
      "input":None,"shell":False,"text":True,"capture_output":True,
      "timeout":kw.get("timeout"),"encoding":None,"errors":None,"close_fds":None,
      "callsite":{"module_path":path,"lineno":line,"process_api":"subprocess.run","function":"run","effect_class":cls,"registry_site_count":18,"runtime_join":"EXACT_PATH_LINE_API"},
      "request_sha256":"a"*64
    }

class Tests(unittest.TestCase):
    def setUp(self):
        self.authorize=admission.make_authorizer(verifier=lambda x:x)

    def test_all_six_current_profiles_allow(self):
        cases=[
          req("canonical/runtime/bound_capabilities/archive_verify_gnu_tar.py",32,"READ_ONLY_DECLARED_QUERY",["tar","-tzf","/tmp/a.tar.gz"]),
          req("canonical/runtime/bound_capabilities/jq_query.py",41,"READ_ONLY_DECLARED_QUERY",["jq",".","/tmp/a.json"]),
          req("canonical/runtime/bound_capabilities/pdf_ocr_tesseract.py",44,"READ_ONLY_DECLARED_QUERY",["tesseract","/tmp/a.png","stdout","-l","eng","--psm","6"]),
          req("canonical/runtime/bound_capabilities/sqlite_verify_cli.py",66,"READ_ONLY_DECLARED_QUERY",["sqlite3","-json","/tmp/a.db","SELECT 1"]),
          req("canonical/runtime/bound_capabilities/yq_yaml_json.py",21,"READ_ONLY_DECLARED_QUERY",["yq",".","/tmp/a.yaml"]),
          req("canonical/runtime/bound_capabilities/pdf_ocr_tesseract.py",29,"TEMPORARY_FILESYSTEM_TRANSFORM",["pdftoppm","-f","1","-l","5","-r","150","-png","/tmp/a.pdf","/tmp/project-brain-ocr-x/page"],timeout=180),
        ]
        for request in cases:
            out=self.authorize(request)
            self.assertTrue(out["allowed"],out)
            self.assertEqual(len(out["authorization_sha256"]),64)

    def test_nonbound_effect_class_denies(self):
        request=req("canonical/runtime/astra_runtime.py",1215,"BOUND_CHILD_CODE_EXECUTION",["python","x.py"])
        self.assertFalse(self.authorize(request)["allowed"])

    def test_dangerous_jq_and_mutating_sql_deny(self):
        jq=req("canonical/runtime/bound_capabilities/jq_query.py",41,"READ_ONLY_DECLARED_QUERY",["jq",'import "x" as x; .',"/tmp/a.json"])
        sql=req("canonical/runtime/bound_capabilities/sqlite_verify_cli.py",66,"READ_ONLY_DECLARED_QUERY",["sqlite3","-json","/tmp/a.db","DROP TABLE x"])
        self.assertFalse(self.authorize(jq)["allowed"])
        self.assertFalse(self.authorize(sql)["allowed"])

    def test_shell_and_ambient_env_deny(self):
        request=req("canonical/runtime/bound_capabilities/yq_yaml_json.py",21,"READ_ONLY_DECLARED_QUERY",["yq",".","/tmp/a.yaml"])
        request["shell"]=True
        self.assertFalse(self.authorize(request)["allowed"])
        request["shell"]=False
        request["env"]={"key_count":1,"binding_sha256":"b"*64}
        self.assertFalse(self.authorize(request)["allowed"])

    def test_out_of_range_temp_request_denies(self):
        request=req("canonical/runtime/bound_capabilities/pdf_ocr_tesseract.py",29,"TEMPORARY_FILESYSTEM_TRANSFORM",["pdftoppm","-f","1","-l","999","-r","150","-png","/tmp/a.pdf","/tmp/project-brain-ocr-x/page"],timeout=180)
        self.assertFalse(self.authorize(request)["allowed"])

if __name__=="__main__":
    unittest.main(verbosity=2)
