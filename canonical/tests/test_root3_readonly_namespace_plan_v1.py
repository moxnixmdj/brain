from __future__ import annotations
import pathlib,tempfile,unittest
from unittest.mock import patch
from canonical.runtime import root3_readonly_namespace_plan_v1 as p
from canonical.runtime import zero_ambient_namespace_launcher_v1 as ns

def context(root):
    src=pathlib.Path(root)/"in.json"
    src.write_text('{"x":1}\n',encoding="utf-8")
    return {
      "effect_class":"READ_ONLY_DECLARED_QUERY",
      "api":"subprocess.run",
      "args":(["jq",".",str(src)],),
      "kwargs":{"cwd":pathlib.Path(root),"text":True,"capture_output":True,"timeout":30},
      "callsite":{"module_path":"canonical/runtime/bound_capabilities/jq_query.py","lineno":41,"process_api":"subprocess.run"},
    }

class PlannerTests(unittest.TestCase):
    def test_valid_plan_is_bound_to_private_namespace_policy(self):
        with tempfile.TemporaryDirectory() as td, \
             patch.object(p.shutil,"which",side_effect=lambda x:"/usr/bin/python3" if x=="python3" else "/usr/bin/"+x), \
             patch.object(p.os,"geteuid",return_value=1001), patch.object(p.os,"getegid",return_value=1001), \
             patch.object(ns.os,"geteuid",return_value=1001), patch.object(ns.os,"getegid",return_value=1001):
            out=p.build(context(td))
        self.assertEqual(len(out["policy_sha256"]),64)
        self.assertIn("/input/in.json"," ".join(out["policy"]["argv"]))
        self.assertEqual(out["policy"]["authority"]["network"],"PRIVATE_NAMESPACE_LOOPBACK_ONLY")

    def test_unknown_site_denies(self):
        with tempfile.TemporaryDirectory() as td:
            c=context(td); c["callsite"]["lineno"]=42
            with self.assertRaisesRegex(Exception,"SITE_NOT_ADMITTED"):
                p.build(c)

    def test_shell_denies(self):
        with tempfile.TemporaryDirectory() as td:
            c=context(td); c["kwargs"]["shell"]=True
            with self.assertRaisesRegex(Exception,"SHELL_FORBIDDEN"):
                p.build(c)

if __name__=="__main__": unittest.main(verbosity=2)
