#!/usr/bin/env python3
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

CANONICAL_ROOT=pathlib.Path(__file__).resolve().parents[1]
RUNTIME_DIR=CANONICAL_ROOT/"runtime"

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

pypi=load("project_brain_test_platform_pypi",RUNTIME_DIR/"auto_pypi_library_acquisition.py")
npm=load("project_brain_test_platform_npm",RUNTIME_DIR/"auto_npm_library_acquisition.py")


class AutoAcquisitionPlatformAttestationTests(unittest.TestCase):
    def test_platform_normalization_is_fail_closed(self):
        for module,cases in (
            (pypi,[("linux","linux"),("linux2","linux"),("win32","windows"),("cygwin","windows"),("darwin","darwin")]),
            (npm,[("linux","linux"),("linux2","linux"),("win32","windows"),("cygwin","windows"),("darwin","darwin")]),
        ):
            for raw,expected in cases:
                with self.subTest(module=module.__name__,raw=raw), mock.patch.object(module.sys,"platform",raw):
                    self.assertEqual(module._verified_runtime_platform(),expected)
        with mock.patch.object(pypi.sys,"platform","plan9"):
            with self.assertRaisesRegex(pypi.AutoPyPIAcquisitionFailure,"PYPI_VERIFICATION_PLATFORM_UNSUPPORTED"):
                pypi._verified_runtime_platform()
        with mock.patch.object(npm.sys,"platform","plan9"):
            with self.assertRaisesRegex(npm.AutoNpmAcquisitionFailure,"NPM_VERIFICATION_PLATFORM_UNSUPPORTED"):
                npm._verified_runtime_platform()

    def test_pypi_pending_binding_attests_observed_windows_platform(self):
        goal="Encode canonical/astra_runtime/tmp/source.json as UBJSON and save canonical/astra_runtime/tmp/out.ubj."
        candidate={
            "project":"fake-ubjson","name":"fake-ubjson","version":"1.0.0",
            "metadata_url":"https://example.invalid/fake-ubjson/1.0.0/json",
            "license":"MIT","score":100,
        }
        contract={
            "fixture":[{"id":1,"text":"alpha"}],
            "module":"fake_ubjson","encode_callable":"dumps","decode_callable":"loads",
            "encode_kwargs":{},"decode_kwargs":{},"envelope_key":None,
            "schema":"PROJECT_BRAIN_PYPI_CODEC_CONTRACT_V1",
        }
        closure={
            "root":{"filename":"fake_ubjson-1.0.0-py3-none-any.whl","sha256":"a"*64,"path":"unused.whl"},
            "lock":{"schema":"PROJECT_BRAIN_PYPI_WHEEL_CLOSURE_V1","closure_sha256":"b"*64,"wheel_count":1},
        }
        with tempfile.TemporaryDirectory() as td, (
            mock.patch.object(pypi,"_candidate_pool",return_value=[candidate]),
            mock.patch.object(pypi,"_download_compatible_wheel_closure",return_value=closure),
            mock.patch.object(pypi,"_infer_codec_contract",return_value=contract),
            mock.patch.object(pypi.capability_discovery,"effect_queries",return_value=["encode","ubjson"]),
            mock.patch.object(pypi.sys,"platform","win32"),
        ):
            out=pypi.dispatch(goal,"TEST-PYPI-PLATFORM","canonical/astra_runtime/missions/TEST.json",td)
            pending=json.loads((pathlib.Path(td)/out["pending_binding_path"]).read_text(encoding="utf-8"))
        self.assertEqual(pending["registry_entry"]["platforms"],["windows"])

    def test_npm_pending_binding_attests_observed_windows_platform(self):
        goal="Using a zero-cost npm JavaScript library, encode canonical/astra_runtime/tmp/source.json and save canonical/astra_runtime/tmp/out.ubj."
        raw={"package":"fake-ubjson","name":"fake-ubjson","version":"1.0.0"}
        selected={
            "package":"fake-ubjson","name":"fake-ubjson","version":"1.0.0",
            "metadata_url":"https://example.invalid/fake-ubjson/1.0.0",
            "tarball_url":"https://example.invalid/fake-ubjson.tgz",
            "integrity":"sha512-AAAA","license":"MIT","score":100,
        }
        contract={
            "fixture":[{"id":1,"text":"alpha"}],
            "root_selector":"module","encode_export":"encode","decode_export":"decode",
            "integrity_algorithm":"sha512","integrity_digest_hex":"00",
        }
        with tempfile.TemporaryDirectory() as td, (
            mock.patch.object(npm,"_search_registry",return_value=[raw]),
            mock.patch.object(npm,"_metadata",return_value=selected),
            mock.patch.object(npm,"_probe_contract",return_value=contract),
            mock.patch.object(npm.sys,"platform","win32"),
        ):
            out=npm.dispatch(goal,"TEST-NPM-PLATFORM","canonical/astra_runtime/missions/TEST.json",td)
            pending=json.loads((pathlib.Path(td)/out["pending_binding_path"]).read_text(encoding="utf-8"))
        self.assertEqual(pending["registry_entry"]["platforms"],["windows"])


if __name__=="__main__":
    unittest.main(verbosity=2)
