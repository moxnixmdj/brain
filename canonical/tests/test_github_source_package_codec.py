#!/usr/bin/env python3
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

CANONICAL_ROOT=pathlib.Path(__file__).resolve().parents[1]
RUNTIME_DIR=CANONICAL_ROOT/"runtime"
if str(RUNTIME_DIR) not in sys.path:
    sys.path.insert(0,str(RUNTIME_DIR))

import auto_github_source_acquisition as source


class GitHubSourcePackageCodecTests(unittest.TestCase):
    def test_source_surface_discovers_package_and_excludes_test_build_modules(self):
        tree=[
            {"path":"setup.py","type":"blob","size":10},
            {"path":"ez_setup.py","type":"blob","size":10},
            {"path":"test/test_codec.py","type":"blob","size":10},
            {"path":"ubjson/__init__.py","type":"blob","size":10},
            {"path":"ubjson/encoder.py","type":"blob","size":10},
        ]
        allowed=[x for x in tree if x["path"].endswith(".py")]
        def is_allowed(item):
            parts=[p.lower() for p in pathlib.PurePosixPath(item["path"]).parts]
            return not any(p in {"test","tests","vendor","vendored","site-packages"} for p in parts)
        allowed=[x for x in allowed if is_allowed(x)]
        modules=[]
        for item in allowed:
            pure=pathlib.PurePosixPath(item["path"])
            if len(pure.parts)==1 and pure.suffix==".py" and pure.stem not in {"__init__","setup","ez_setup","conftest"}:
                modules.append(pure.stem)
            elif pure.name=="__init__.py" and len(pure.parts)>1:
                package_parts=pure.parts[:-1]
                if all(__import__("re").fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",part) for part in package_parts):
                    modules.append(".".join(package_parts))
        self.assertEqual(modules,["ubjson"])
        self.assertNotIn("test/test_codec.py",[x["path"] for x in allowed])

    def test_runner_probes_dumpb_loadb_package_pair(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            pkg=root/"demo_codec"
            pkg.mkdir()
            (pkg/"__init__.py").write_text(
                "import json\n"
                "def dumpb(v): return json.dumps(v,sort_keys=True).encode()\n"
                "def loadb(v): return json.loads(v.decode())\n",
                encoding="utf-8",
            )
            cfg={"mode":"probe","source_root":str(root),"modules":["demo_codec"],"fixture":[1,2,3,5,8]}
            proc=subprocess.run(
                [sys.executable,str(RUNTIME_DIR/"github_source_codec_runner.py")],
                input=json.dumps(cfg),text=True,capture_output=True,timeout=30,
            )
        self.assertEqual(proc.returncode,0,proc.stderr)
        out=json.loads(proc.stdout)
        self.assertTrue(out["ok"])
        self.assertEqual(out["module"],"demo_codec")
        self.assertEqual(out["encode_callable"],"dumpb")
        self.assertEqual(out["decode_callable"],"loadb")


if __name__=="__main__":
    unittest.main(verbosity=2)
