#!/usr/bin/env python3
import importlib.util, pathlib, sys, tempfile, types, unittest

CANONICAL_ROOT=pathlib.Path(__file__).resolve().parents[1]
PATH=CANONICAL_ROOT/"runtime"/"python_codec_probe.py"
spec=importlib.util.spec_from_file_location("python_codec_probe_test_target",PATH)
probe=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=probe
spec.loader.exec_module(probe)

class PythonCodecProbeTests(unittest.TestCase):
    def test_discovers_dumpb_loadb_without_package_special_case(self):
        module=types.SimpleNamespace(
            dumpb=lambda value: b"x",
            loadb=lambda payload: probe.FIXTURE,
        )
        self.assertIn(("dumpb","loadb"),probe.discover_pairs(module))

    def test_ignores_unrelated_public_callables(self):
        module=types.SimpleNamespace(open=lambda:None,connect=lambda:None,render=lambda:None)
        self.assertEqual(probe.discover_pairs(module),[])

    def test_actual_child_style_probe_accepts_semantic_pair(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            pkg=root/"fakecodec.py"
            pkg.write_text(
                "import json\n"
                "def dumpb(value): return json.dumps(value,separators=(',',':')).encode()\n"
                "def loadb(payload): return json.loads(payload.decode())\n",
                encoding="utf-8",
            )
            out=probe.probe_modules(root,["fakecodec"])
        self.assertTrue(out["ok"])
        self.assertEqual(out["encode_callable"],"dumpb")
        self.assertEqual(out["decode_callable"],"loadb")
        self.assertEqual(out["pair_discovery"],"bounded_public_semantic_callables")

if __name__=="__main__":
    unittest.main(verbosity=2)
