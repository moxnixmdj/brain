from __future__ import annotations
import pathlib, subprocess, tempfile, unittest
ROOT=pathlib.Path("/home/sprite/root3-package-v1")
sys.path.insert(0,str(ROOT))
from canonical.runtime import root3_read_only_declared_query_executor_v2 as d
from canonical.runtime import root3_read_only_local_file_query_executor_v1 as local
from canonical.runtime import root3_read_only_package_metadata_executor_v1 as pkg
from canonical.runtime.root3_subprocess_effect_class_registry_v1 import EXPECTED

class DispatcherTests(unittest.TestCase):
    def test_union_is_exact_all_fifteen_read_only_sites(self):
        target={k for k,v in EXPECTED.items() if v=="READ_ONLY_DECLARED_QUERY"}
        self.assertEqual(len(target),15)
        self.assertFalse(set(local.SUPPORTED)&set(pkg.SUPPORTED))
        self.assertEqual(set(d.SUPPORTED),target)
        self.assertEqual(len(d.SUPPORTED),15)

    def test_unknown_read_only_callsite_denied(self):
        ex=d.make_executor(popen_impl=subprocess.Popen)
        ctx={"effect_class":"READ_ONLY_DECLARED_QUERY","callsite":{"module_path":"x.py","lineno":1,"process_api":"subprocess.run"},"args":(["echo","x"],),"kwargs":{"text":True,"capture_output":True,"timeout":1}}
        with self.assertRaisesRegex(d.ReadOnlyDeclaredQueryDenied,"NOT_SUPPORTED"):
            ex(ctx)

    def test_real_local_file_route_still_works(self):
        ex=d.make_executor(popen_impl=subprocess.Popen)
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            src=root/"in.json"; src.write_text('{"x":1}\n')
            ctx={"effect_class":"READ_ONLY_DECLARED_QUERY","callsite":{"module_path":"canonical/runtime/bound_capabilities/jq_query.py","lineno":41,"process_api":"subprocess.run"},"args":(["jq",".x",str(src)],),"kwargs":{"cwd":root,"text":True,"capture_output":True,"timeout":60}}
            p=ex(ctx)
            self.assertEqual(p.returncode,0)
            self.assertEqual(p.stdout.strip(),"1")

    def test_real_package_metadata_route_still_works(self):
        ex=d.make_executor(popen_impl=subprocess.Popen)
        ctx={"effect_class":"READ_ONLY_DECLARED_QUERY","callsite":{"module_path":"canonical/runtime/capability_discovery.py","lineno":359,"process_api":"subprocess.run"},"args":(["apt-cache","policy","bash"],),"kwargs":{"text":True,"capture_output":True,"timeout":10}}
        p=ex(ctx)
        self.assertEqual(p.returncode,0)
        self.assertIn("Candidate:",p.stdout)

if __name__=="__main__":
    unittest.main(verbosity=2)
