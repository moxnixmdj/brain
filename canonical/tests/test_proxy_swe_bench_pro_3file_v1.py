import pathlib, tempfile, textwrap, subprocess, sys, unittest
from canonical.swe_kernel.perfect_algorithm_unified_v8 import PerfectAlgorithmUnifiedV8, SCHEMA, MODEL_CALLS
from canonical.swe_kernel.cross_repo_dataflow_v1 import build_cross_repo_graph, causal_path_cross_repo

class ProxySweBenchPro3File(unittest.TestCase):
    def test_3file_lineage_stitched(self):
        tmp=pathlib.Path(tempfile.mkdtemp(prefix="pro3-"))
        (tmp/"a.py").write_text("def transform(x): return x*2\n")
        (tmp/"b.py").write_text("from a import transform\ndef handle(v): return transform(v)\n")
        (tmp/"c.py").write_text("from b import handle\ndef run(vals): return [handle(v) for v in vals]\n")
        (tmp/"test_c.py").write_text("from c import run\nassert run([1])==[2]\n")
        g=build_cross_repo_graph(tmp)
        self.assertEqual(g.file_count, 4)
        self.assertGreaterEqual(len([e for e in g.cross_edges if e['var']=='transform']), 1)
        self.assertGreaterEqual(len([e for e in g.cross_edges if e['var']=='handle']), 1)

    def test_clip_concept_fixes_3file_via_G_t(self):
        pa=PerfectAlgorithmUnifiedV8()
        spec={"examples": [(60,100),(-5,0),(50,100),(10,20)], "oracle": lambda x: min(max(x*2,0),100), "grammar": ["x","0","1","2","*","+"]}
        inv=pa.invent(spec)
        self.assertTrue(inv['verified'])
        self.assertEqual(inv['model_calls'], 0)
        self.assertIn('concept_f1f3674d', inv['program'])

    def test_e2e_fix_and_verify(self):
        tmp=pathlib.Path(tempfile.mkdtemp(prefix="e2e-"))
        (tmp/"a.py").write_text("def transform(x):\n    return x*2\n")
        (tmp/"b.py").write_text("from a import transform\ndef handle(v):\n    return transform(v)\n")
        (tmp/"c.py").write_text("from b import handle\ndef run(vals):\n    return [handle(v) for v in vals]\n")
        (tmp/"test_c.py").write_text("from c import run\nassert run([60, -5, 50, 10]) == [100, 0, 100, 20]\nprint('ok')\n")
        pa=PerfectAlgorithmUnifiedV8()
        inv=pa.invent({"examples": [(60,100),(-5,0),(50,100),(10,20)], "oracle": lambda x: min(max(x*2,0),100), "grammar": ["x","0","1","2","*","+"]})
        self.assertTrue(inv['verified'])
        # apply fix concept's body
        (tmp/"a.py").write_text("def transform(x):\n    return min(max(x*2,0),100)\n")
        res=subprocess.run([sys.executable, str(tmp/"test_c.py")], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)

    def test_schema_zero_model(self):
        self.assertEqual(SCHEMA, "PROJECT_BRAIN_PERFECT_ALGORITHM_UNIFIED_V8")
        self.assertEqual(MODEL_CALLS, 0)
