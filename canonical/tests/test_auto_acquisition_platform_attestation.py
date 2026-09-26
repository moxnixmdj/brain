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
if str(RUNTIME_DIR) not in sys.path:
    sys.path.insert(0,str(RUNTIME_DIR))

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

pypi=load("project_brain_test_platform_pypi",RUNTIME_DIR/"auto_pypi_library_acquisition.py")
npm=load("project_brain_test_platform_npm",RUNTIME_DIR/"auto_npm_library_acquisition.py")
compiler=load("project_brain_test_platform_compiler",RUNTIME_DIR/"goal_compiler.py")
promoter=load("project_brain_test_platform_promoter",RUNTIME_DIR/"promote_pending_binding.py")
npm_utils=load("project_brain_test_npm_utils",RUNTIME_DIR/"npm_package_utils.py")
astra=load("project_brain_test_astra_runtime",RUNTIME_DIR/"astra_runtime.py")


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
        with tempfile.TemporaryDirectory() as td:
            mission=pathlib.Path(td)/"canonical"/"astra_runtime"/"missions"/"TEST.json"
            mission.parent.mkdir(parents=True,exist_ok=True)
            mission.write_text('{"goal":"immutable"}\n',encoding="utf-8")
            with (
                mock.patch.object(pypi,"_candidate_pool",return_value=[candidate]),
            mock.patch.object(pypi,"_download_compatible_wheel_closure",return_value=closure),
            mock.patch.object(pypi,"_infer_codec_contract",return_value=contract),
            mock.patch.object(pypi.capability_discovery,"effect_queries",return_value=["encode","ubjson"]),
                mock.patch.object(pypi.sys,"platform","win32"),
            ):
                out=pypi.dispatch(goal,"TEST-PYPI-PLATFORM","canonical/astra_runtime/missions/TEST.json",td)
                pending=json.loads((pathlib.Path(td)/out["pending_binding_path"]).read_text(encoding="utf-8"))
        self.assertEqual(pending["registry_entry"]["platforms"],["windows"])
        self.assertIn("structured.binary.encode.ubj",pending["registry_entry"]["provides"])
        self.assertNotIn("structured.binary.encode.json",pending["registry_entry"]["provides"])

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
        with tempfile.TemporaryDirectory() as td:
            mission=pathlib.Path(td)/"canonical"/"astra_runtime"/"missions"/"TEST.json"
            mission.parent.mkdir(parents=True,exist_ok=True)
            mission.write_text('{"goal":"immutable"}\n',encoding="utf-8")
            with (
                mock.patch.object(npm,"_search_registry",return_value=[raw]),
            mock.patch.object(npm,"_metadata",return_value=selected),
            mock.patch.object(npm,"_probe_contract",return_value=contract),
                mock.patch.object(npm.sys,"platform","win32"),
            ):
                out=npm.dispatch(goal,"TEST-NPM-PLATFORM","canonical/astra_runtime/missions/TEST.json",td)
                pending=json.loads((pathlib.Path(td)/out["pending_binding_path"]).read_text(encoding="utf-8"))
        self.assertEqual(pending["registry_entry"]["platforms"],["windows"])


    def test_compiler_excludes_explicitly_inapplicable_platforms(self):
        registry={
            "linux.only":{
                "status":"VERIFIED_BOUND_CAPABILITY","platforms":["linux"],
                "provides":["demo.effect"],"requires":[],"keywords":["demo"],
                "action_template":{"type":"invoke_capability","args":{"capability_id":"linux.only"}},
            },
            "windows.ok":{
                "status":"VERIFIED_BOUND_CAPABILITY","platforms":["windows"],
                "provides":["demo.effect"],"requires":[],"keywords":["demo"],
                "action_template":{"type":"invoke_capability","args":{"capability_id":"windows.ok"}},
            },
            "legacy.no.platform":{
                "status":"VERIFIED_BOUND_CAPABILITY",
                "provides":["legacy.effect"],"requires":[],"keywords":["legacy"],
                "action_template":{"type":"invoke_capability","args":{"capability_id":"legacy.no.platform"}},
            },
        }
        with mock.patch.object(compiler.sys,"platform","win32"):
            filtered=compiler._platform_admissible_registry(registry)
        self.assertNotIn("linux.only",filtered)
        self.assertIn("windows.ok",filtered)
        self.assertIn("legacy.no.platform",filtered)

    def test_compiler_platform_normalization_fails_closed(self):
        with mock.patch.object(compiler.sys,"platform","plan9"):
            with self.assertRaisesRegex(compiler.GoalCompilationFailure,"GOAL_COMPILATION_PLATFORM_UNSUPPORTED"):
                compiler._platform_admissible_registry({})

    def test_promotion_rejects_same_implementation_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            runtime_dir=root/"canonical"/"runtime"
            mission_dir=root/"canonical"/"astra_runtime"/"missions"
            evidence_dir=root/"canonical"/"astra_runtime"/"evidence"
            pending_dir=root/"canonical"/"astra_runtime"/"pending_bindings"
            for p in (runtime_dir,mission_dir,evidence_dir,pending_dir):
                p.mkdir(parents=True,exist_ok=True)
            registry_path=runtime_dir/"BOUND_CAPABILITY_REGISTRY_V1.json"
            registry_path.write_text(json.dumps({"schema":"PROJECT_BRAIN_BOUND_CAPABILITY_REGISTRY_V1","capabilities":{}}),encoding="utf-8")
            mission_path=mission_dir/"ORIGIN.json"
            mission_path.write_text('{"goal":"immutable"}\n',encoding="utf-8")
            pending_path=pending_dir/"pending.json"
            verify_path=evidence_dir/"verify.json"
            pending={
                "schema":"PROJECT_BRAIN_PENDING_AUTO_BINDING_V1",
                "capability_id":"auto.test",
                "origin_mission_path":"canonical/astra_runtime/missions/ORIGIN.json",
                "origin_mission_sha256_at_acquisition":__import__("hashlib").sha256(
                    mission_path.read_bytes()
                ).hexdigest(),
                "verification_mission_id":"VERIFY-AUTO-TEST",
                "registry_entry":{
                    "status":"BOUND_PENDING_INDEPENDENT_VERIFICATION",
                    "source":{"type":"pypi"},
                    "action_template":{"type":"invoke_capability","args":{"capability_id":"auto.test"}},
                },
            }
            verified={
                "schema":"PROJECT_BRAIN_AUTO_BINDING_VERIFICATION_V1",
                "capability_id":"auto.test",
                "verification_mission_id":"VERIFY-AUTO-TEST",
                "independent_verified":True,
                "semantic_roundtrip":{"verified":True,"implementation_independent":False},
            }
            pending_path.write_text(json.dumps(pending),encoding="utf-8")
            verify_path.write_text(json.dumps(verified),encoding="utf-8")
            argv=["promote_pending_binding.py",
                  "canonical/astra_runtime/pending_bindings/pending.json",
                  "canonical/astra_runtime/evidence/verify.json"]
            with (
                mock.patch.object(promoter,"ROOT",root),
                mock.patch.object(promoter,"REGISTRY",registry_path),
                mock.patch.object(sys,"argv",argv),
            ):
                with self.assertRaisesRegex(RuntimeError,"VERIFICATION_IMPLEMENTATION_NOT_INDEPENDENT"):
                    promoter.main()


    def test_blind_cbor_replan_shape_filters_linux_and_uses_distinct_verifier(self):
        goal=(
            "Encode canonical/astra_runtime/fixtures/AUTO_BLIND_CBOR_SOURCE.json as CBOR "
            "and save canonical/astra_runtime/tmp/AUTO_BLIND_CBOR.cbor. "
            "Independently decode the CBOR artifact using a different implementation than "
            "the producer and verify the decoded records are exactly identical to "
            "canonical/astra_runtime/fixtures/AUTO_BLIND_CBOR_SOURCE.json in values, "
            "order, field names, and record count."
        )
        def entry(platforms,cid):
            return {
                "status":"VERIFIED_BOUND_CAPABILITY",
                "platforms":platforms,
                "provides":["structured.binary.encode","structured.binary.encode.cbor"],
                "requires":["json.file.available"],
                "keywords":["encode","json","cbor"],
                "adapter_module":"python_library_codec",
                "source":{"type":"pypi","project":cid,"version":"1.0.0"},
                "action_template":{
                    "type":"invoke_capability",
                    "args":{
                        "capability_id":cid,
                        "module":"fake_cbor",
                        "encode_callable":"dumps",
                        "decode_callable":"loads",
                        "encode_kwargs":{},
                        "decode_kwargs":{},
                        "envelope_key":None,
                        "json_path":"${input.json_path}",
                        "output_path":"${input.output_path}",
                    },
                    "expect":{"type":"field_equals","field":"output_verified","value":True},
                },
            }

        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            source=root/"canonical"/"astra_runtime"/"fixtures"/"AUTO_BLIND_CBOR_SOURCE.json"
            source.parent.mkdir(parents=True,exist_ok=True)
            source.write_text('[{"id":1,"text":"alpha"}]\n',encoding="utf-8")

            with mock.patch.object(compiler.sys,"platform","win32"):
                with self.assertRaises(compiler.GoalCompilationFailure):
                    compiler.compile_goal(
                        goal,
                        {"linux.cbor":entry(["linux"],"linux.cbor")},
                        root,
                    )

                compiled=compiler.compile_goal(
                    goal,
                    {
                        "linux.cbor":entry(["linux"],"linux.cbor"),
                        "auto.pypi.fake-cbor":entry(["windows"],"auto.pypi.fake-cbor"),
                    },
                    root,
                )

        self.assertEqual(compiled["compiler_mode"],"DETERMINISTIC_COMPOUND_ACTION_PLAN")
        self.assertEqual(
            [a["type"] for a in compiled["controller_actions"]],
            ["invoke_capability","verify_with_independent_npm_codec","finish"],
        )
        producer=compiled["controller_actions"][0]["args"]
        self.assertEqual(
            producer["json_path"],
            "canonical/astra_runtime/fixtures/AUTO_BLIND_CBOR_SOURCE.json",
        )
        self.assertEqual(
            producer["output_path"],
            "canonical/astra_runtime/tmp/AUTO_BLIND_CBOR.cbor",
        )
        verifier=compiled["controller_actions"][1]["args"]
        self.assertEqual(verifier["format"],"cbor")
        self.assertEqual(verifier["producer_capability_id"],"auto.pypi.fake-cbor")


    def test_npm_zero_dependency_policy_rejects_hidden_runtime_surfaces(self):
        bad_cases=(
            {"optionalDependencies":{"native-addon":"1.0.0"}},
            {"peerDependencies":{"peer-runtime":"1.0.0"}},
            {"bundledDependencies":["vendored-runtime"]},
            {"bundleDependencies":["vendored-runtime"]},
        )
        for meta in bad_cases:
            with self.subTest(meta=meta):
                with self.assertRaises(npm_utils.NpmPackageFailure):
                    npm_utils.validate_zero_dependency_package(meta)

    def test_npm_zero_dependency_policy_accepts_clean_package(self):
        observed=npm_utils.validate_zero_dependency_package({
            "dependencies":{},
            "optionalDependencies":{},
            "peerDependencies":{},
            "scripts":{"test":"node test.js"},
        })
        self.assertEqual(observed["dependency_count"],0)


    def test_controller_accepts_cross_supplier_npm_verifier_action(self):
        step={
            "id":"goal",
            "max_controller_actions":4,
            "controller_actions":[
                {
                    "type":"verify_with_independent_npm_codec",
                    "args":{
                        "format":"cbor",
                        "json_path":"canonical/astra_runtime/fixtures/AUTO_BLIND_CBOR_SOURCE.json",
                        "binary_path":"canonical/astra_runtime/tmp/AUTO_BLIND_CBOR.cbor",
                        "producer_project":"fake-cbor",
                        "producer_capability_id":"auto.pypi.fake-cbor",
                    },
                    "expect":{"type":"field_equals","field":"verified","value":True},
                },
                {"type":"finish","args":{"summary":"DONE"}},
            ],
        }
        mission={"mission_id":"TEST-CROSS-SUPPLIER-CONTROLLER"}
        checkpoint={
            "schema":"PROJECT_BRAIN_CONTROLLER_CHECKPOINT_V1",
            "mission_id":mission["mission_id"],
            "step_id":"goal",
            "plan_sha256":"x",
            "status":"IN_PROGRESS",
            "completed_actions":[],
            "next_action_index":0,
            "resume_count":0,
        }
        def fake_goal_action(action):
            if action["type"]=="verify_with_independent_npm_codec":
                return {"type":action["type"],"verified":True}
            if action["type"]=="finish":
                return {"type":"finish","summary":"DONE"}
            raise AssertionError(action)
        with (
            mock.patch.object(
                astra,"_load_controller_checkpoint",
                return_value=(astra.ROOT/"canonical"/"astra_runtime"/"state"/"TEST_CONTROLLER_CHECKPOINT.json",checkpoint,False),
            ),
            mock.patch.object(
                astra,"_write_controller_checkpoint",
                side_effect=lambda path,data,trace,status="IN_PROGRESS": {
                    **data,
                    "completed_actions":list(trace),
                    "status":status,
                },
            ),
            mock.patch.object(astra,"_goal_action",side_effect=fake_goal_action),
        ):
            out=astra._run_model_independent_goal(step,mission,"demo")
        self.assertEqual(out["final_summary"],"DONE")
        self.assertEqual(out["trace"][0]["plan"]["type"],"verify_with_independent_npm_codec")


    def test_promotion_rejects_origin_mission_drift_before_registry_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            runtime_dir=root/"canonical"/"runtime"
            mission_dir=root/"canonical"/"astra_runtime"/"missions"
            evidence_dir=root/"canonical"/"astra_runtime"/"evidence"
            pending_dir=root/"canonical"/"astra_runtime"/"pending_bindings"
            for p in (runtime_dir,mission_dir,evidence_dir,pending_dir):
                p.mkdir(parents=True,exist_ok=True)
            registry_path=runtime_dir/"BOUND_CAPABILITY_REGISTRY_V1.json"
            original_registry={"schema":"PROJECT_BRAIN_BOUND_CAPABILITY_REGISTRY_V1","capabilities":{}}
            registry_path.write_text(json.dumps(original_registry,sort_keys=True)+"\n",encoding="utf-8")
            before=registry_path.read_bytes()

            mission_path=mission_dir/"ORIGIN.json"
            mission_path.write_text('{"goal":"original"}\n',encoding="utf-8")
            frozen=__import__("hashlib").sha256(mission_path.read_bytes()).hexdigest()
            mission_path.write_text('{"goal":"tampered"}\n',encoding="utf-8")

            pending_path=pending_dir/"pending.json"
            verify_path=evidence_dir/"verify.json"
            pending={
                "schema":"PROJECT_BRAIN_PENDING_AUTO_BINDING_V1",
                "capability_id":"auto.test",
                "origin_mission_path":"canonical/astra_runtime/missions/ORIGIN.json",
                "origin_mission_sha256_at_acquisition":frozen,
                "verification_mission_id":"VERIFY-AUTO-TEST",
                "registry_entry":{
                    "status":"BOUND_PENDING_INDEPENDENT_VERIFICATION",
                    "source":{"type":"pypi"},
                    "action_template":{"type":"invoke_capability","args":{"capability_id":"auto.test"}},
                },
            }
            verified={
                "schema":"PROJECT_BRAIN_AUTO_BINDING_VERIFICATION_V1",
                "capability_id":"auto.test",
                "verification_mission_id":"VERIFY-AUTO-TEST",
                "independent_verified":True,
                "semantic_roundtrip":{
                    "verified":True,
                    "implementation_independent":True,
                    "independent_verifier":{
                        "verified":True,
                        "implementation_independent":True,
                        "supplier_class_independent":True,
                    },
                },
            }
            pending_path.write_text(json.dumps(pending),encoding="utf-8")
            verify_path.write_text(json.dumps(verified),encoding="utf-8")
            argv=["promote_pending_binding.py",
                  "canonical/astra_runtime/pending_bindings/pending.json",
                  "canonical/astra_runtime/evidence/verify.json"]
            with (
                mock.patch.object(promoter,"ROOT",root),
                mock.patch.object(promoter,"REGISTRY",registry_path),
                mock.patch.object(sys,"argv",argv),
            ):
                with self.assertRaisesRegex(RuntimeError,"ORIGIN_MISSION_DRIFT_BEFORE_PROMOTION"):
                    promoter.main()
            self.assertEqual(registry_path.read_bytes(),before)


    def test_invalid_origin_mission_path_fails_before_supplier_discovery(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            outside=root/"NOT_A_MISSION.json"
            outside.write_text('{"goal":"invalid authority"}\n',encoding="utf-8")
            pool=mock.Mock(return_value=[])
            with mock.patch.object(pypi,"_candidate_pool",pool):
                with self.assertRaisesRegex(
                    pypi.AutoPyPIAcquisitionFailure,
                    "PYPI_ORIGIN_MISSION_PATH_INVALID"
                ):
                    pypi.dispatch(
                        "Encode canonical/astra_runtime/tmp/source.json as CBOR and save canonical/astra_runtime/tmp/out.cbor.",
                        "TEST-INVALID-AUTHORITY",
                        "NOT_A_MISSION.json",
                        td,
                    )
            pool.assert_not_called()


    def test_npm_search_accepts_explicit_verifier_format_hint(self):
        class FakeResponse:
            def __enter__(self):
                return self
            def __exit__(self,*args):
                return False
            def read(self,*args):
                return json.dumps({
                    "objects":[{
                        "package":{
                            "name":"cbor-test",
                            "version":"1.0.0",
                            "description":"CBOR codec",
                            "keywords":["cbor"],
                        }
                    }]
                }).encode("utf-8")
        with mock.patch.object(npm.urllib.request,"urlopen",return_value=FakeResponse()) as urlopen:
            candidates=npm._search_registry("",limit=5,format_hint="cbor")
        self.assertEqual(candidates[0]["format"],"cbor")
        self.assertIn("text=cbor",urlopen.call_args.args[0].full_url)
        with self.assertRaisesRegex(npm.AutoNpmAcquisitionFailure,"NPM_OUTPUT_FORMAT_INVALID"):
            npm._search_registry("",format_hint="../cbor")


if __name__=="__main__":
    unittest.main(verbosity=2)
