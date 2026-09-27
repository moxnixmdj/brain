#!/usr/bin/env python3
import json
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
RUNNER = ROOT / "canonical" / "runtime" / "node_codec_runner.js"


class NodeCodecRunnerProjectionTests(unittest.TestCase):
    def _run(self, decode_body):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            package = root / "package"
            package.mkdir()
            (package / "package.json").write_text(
                json.dumps({"name":"tuple-codec","version":"1.0.0","main":"index.js"}),
                encoding="utf-8",
            )
            (package / "index.js").write_text(
                "exports.encode=(v)=>Buffer.from(JSON.stringify(v));\n"
                "exports.decode=(b)=>" + decode_body + ";\n",
                encoding="utf-8",
            )
            source = root / "source.json"
            binary = root / "payload.bin"
            source.write_text('{"x":[1,2],"ok":true}\n', encoding="utf-8")
            raw = source.read_text(encoding="utf-8").strip().encode("utf-8")
            binary.write_bytes(raw)
            proc = subprocess.run(
                ["node", str(RUNNER)],
                input=json.dumps({
                    "mode":"probe_decode",
                    "package_root":str(package),
                    "json_path":str(source),
                    "binary_path":str(binary),
                }),
                text=True,
                capture_output=True,
                cwd=ROOT,
                timeout=20,
            )
            return proc

    def test_accepts_value_offset_tuple_only_on_full_consumption(self):
        proc = self._run("[JSON.parse(Buffer.from(b).toString()), b.length]")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        observed = json.loads(proc.stdout)
        self.assertTrue(observed["ok"])
        self.assertEqual(observed["decode_export"], "decode")
        self.assertEqual(
            observed["decode_projection"],
            "tuple_value_full_consumption",
        )

    def test_rejects_value_offset_tuple_with_partial_consumption(self):
        proc = self._run("[JSON.parse(Buffer.from(b).toString()), b.length-1]")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("NO_COMPATIBLE_NODE_DECODE_CONTRACT", proc.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
