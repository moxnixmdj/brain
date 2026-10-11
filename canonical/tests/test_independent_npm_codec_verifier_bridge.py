#!/usr/bin/env python3
import base64
import hashlib
import importlib.util
import io
import json
import os
import pathlib
import sys
import tempfile
import tarfile
import unittest
from unittest import mock

CANONICAL_ROOT=pathlib.Path(__file__).resolve().parents[1]
RUNTIME=CANONICAL_ROOT/"runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0,str(RUNTIME))

spec=importlib.util.spec_from_file_location("independent_npm_codec_verifier_bridge_target",RUNTIME/"independent_npm_codec_verifier.py")
verifier=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=verifier
spec.loader.exec_module(verifier)

class IndependentNpmVerifierBridgeTests(unittest.TestCase):
    def test_network_constrained_verifier_emits_bridge_request(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            (root/"canonical"/"input.json").parent.mkdir(parents=True)
            (root/"canonical"/"input.json").write_text('{"x":1}\n',encoding="utf-8")
            (root/"canonical"/"out.ubj").write_bytes(b"{}")
            task_id="SI-REAL-UBJSON-SNAPSHOT-001"
            bridge=(
                root/"canonical"/"same_identity_worker"/"external_tool_bridge"/task_id
            )
            with mock.patch.object(verifier.astra_runtime,"ROOT",root), \
                 mock.patch.object(
                     verifier.astra_runtime,
                     "_authorize_external_information",
                     return_value={"pass":True},
                 ), \
                 mock.patch.dict(os.environ,{
                     "PROJECT_BRAIN_EXTERNAL_TOOL_BRIDGE_DIR":str(bridge),
                     "PROJECT_BRAIN_AGENT_ID":"SUPERWORKER-UNIFIED-1",
                     "PROJECT_BRAIN_TASK_ID":task_id,
                 },clear=False):
                with self.assertRaisesRegex(
                    verifier.IndependentNpmCodecVerifierFailure,
                    "EXTERNAL_TOOL_REQUEST_PENDING"
                ):
                    verifier.verify(
                        "ubj","canonical/input.json","canonical/out.ubj",
                        "NeuroJSON/pybj",root
                    )
            requests=list(bridge.glob("*.request.json"))
            self.assertEqual(len(requests),1)
            req=json.loads(requests[0].read_text(encoding="utf-8"))
            self.assertEqual(req["schema"],"PROJECT_BRAIN_EXTERNAL_TOOL_REQUEST_V1")
            self.assertEqual(req["kind"],"urlopen")
            self.assertEqual(req["agent_id"],"SUPERWORKER-UNIFIED-1")
            self.assertEqual(req["task_id"],"SI-REAL-UBJSON-SNAPSHOT-001")
            self.assertIn("registry.npmjs.org/-/v1/search",req["payload"]["url"])
            self.assertIn("text=ubjson",req["payload"]["url"])


    def test_materializes_integrity_verified_dependency_closure(self):
        def tgz(name, version, body):
            raw_file = io.BytesIO()
            with tarfile.open(fileobj=raw_file, mode="w:gz") as tf:
                files = {
                    "package/package.json": json.dumps({
                        "name": name,
                        "version": version,
                        "main": "index.js",
                    }).encode(),
                    "package/index.js": body.encode(),
                }
                for filename, raw in files.items():
                    info = tarfile.TarInfo(filename)
                    info.size = len(raw)
                    tf.addfile(info, io.BytesIO(raw))
            return raw_file.getvalue()

        def row(path, name, version, raw):
            digest = hashlib.sha512(raw).digest()
            integrity = "sha512-" + base64.b64encode(digest).decode("ascii")
            return {
                "install_path": path,
                "package": name,
                "version": version,
                "resolved_url": "https://registry.npmjs.org/" + name + "/-/" + name + "-" + version + ".tgz",
                "integrity": integrity,
                "integrity_algorithm": "sha512",
                "integrity_digest_hex": digest.hex(),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "content_b64": base64.b64encode(raw).decode("ascii"),
                "bytes": len(raw),
            }

        root_raw = tgz("bjd", "0.3.2", "module.exports={};\n")
        dep_raw = tgz("buffer", "6.0.3", "module.exports={};\n")
        root_row = row("node_modules/bjd", "bjd", "0.3.2", root_raw)
        dep_row = row("node_modules/buffer", "buffer", "6.0.3", dep_raw)
        closure = {
            "schema": "PROJECT_BRAIN_EXTERNAL_NPM_PACKAGE_CLOSURE_V1",
            "root_package": "bjd",
            "root_version": "0.3.2",
            "package_count": 2,
            "total_bytes": len(root_raw) + len(dep_raw),
            "packages": [root_row, dep_row],
        }
        candidate = {
            "package": "bjd",
            "version": "0.3.2",
            "integrity": root_row["integrity"],
        }
        with tempfile.TemporaryDirectory() as td:
            package_root, evidence = verifier._materialize_npm_closure(
                closure, pathlib.Path(td) / "site", candidate
            )
            self.assertTrue((package_root / "package.json").is_file())
            self.assertTrue(
                (pathlib.Path(td) / "site" / "node_modules" / "buffer" / "package.json").is_file()
            )
            self.assertEqual(evidence["integrity_digest_hex"], root_row["integrity_digest_hex"])


if __name__=="__main__":
    unittest.main(verbosity=2)
