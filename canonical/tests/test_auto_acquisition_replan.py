#!/usr/bin/env python3
import importlib.util
import hashlib
import json
import pathlib
import sys
import tempfile
import types
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

runtime=load(
    "project_brain_test_auto_acquisition_replan_runtime",
    RUNTIME_DIR/"astra_runtime.py",
)
promoter=load(
    "project_brain_test_auto_acquisition_replan_promoter",
    RUNTIME_DIR/"promote_pending_binding.py",
)


class AutoAcquisitionReplanTests(unittest.TestCase):
    def test_verification_requires_complete_child_and_promoted_registry_entry(self):
        mid="ASTRA-RUNTIME-AUTO-FANIN-CAPABILITY-PROPOSAL-001"
        rel="canonical/astra_runtime/missions/ASTRA_RUNTIME_AUTO_FANIN_CAPABILITY_PROPOSAL_001.json"
        dispatch={
            "status":"ACQUISITION_DISPATCHED",
            "capability_id":"auto.test.capability",
            "verification_mission_id":mid,
            "verification_mission_path":rel,
        }
        tmp_parent=CANONICAL_ROOT/"astra_runtime"/"tmp"
        tmp_parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=tmp_parent) as td:
            state_dir=pathlib.Path(td)
            (state_dir/(mid+".json")).write_text(
                json.dumps({"status":"COMPLETE"}),encoding="utf-8"
            )
            proc=types.SimpleNamespace(returncode=0,stdout="ok",stderr="")
            with (
                mock.patch.object(runtime,"STATE_DIR",state_dir),
                mock.patch.object(runtime.subprocess,"run",return_value=proc),
                mock.patch.object(
                    runtime,
                    "_load_bound_capability_registry",
                    return_value={
                        "auto.test.capability":{
                            "status":"VERIFIED_BOUND_CAPABILITY"
                        }
                    },
                ),
            ):
                out=runtime._verify_and_promote_acquisition(dispatch)
        self.assertEqual(out["status"],"VERIFIED_AND_PROMOTED")
        self.assertEqual(out["capability_id"],"auto.test.capability")

    def test_run_goal_continues_after_verified_acquisition_in_same_invocation(self):
        goal="Create a bounded zero-cost artifact."
        compile_failure=runtime.Blocker(
            "GOAL_COMPILATION_FAILED:GOAL_COMPILATION_NO_VERIFIED_CAPABILITY_MATCH"
        )
        compiled={"target_effects":["auto.effect.test"]}
        dispatch={
            "status":"ACQUISITION_DISPATCHED",
            "capability_id":"auto.test",
            "verification_mission_id":"VERIFY-AUTO-TEST",
            "verification_mission_path":"canonical/astra_runtime/missions/VERIFY_AUTO_TEST.json",
        }
        auto=types.SimpleNamespace(dispatch=mock.Mock(return_value=dispatch))
        completed={"verified":True,"controller_mode":"MODEL_INDEPENDENT_ACTION_PLAN"}
        with (
            mock.patch.object(runtime,"_run_verified_capability_proposal",return_value=None),
            mock.patch.object(runtime,"_run_capability_planned_goal",return_value=None),
            mock.patch.object(runtime,"_run_model_independent_goal",return_value=None),
            mock.patch.object(
                runtime,"_compile_plain_goal",
                side_effect=[compile_failure,compiled],
            ) as compile_mock,
            mock.patch.object(
                runtime,"_write_goal_gap_classification",
                return_value=(pathlib.Path("gap.json"),{}),
            ),
            mock.patch.object(runtime,"_load_auto_capability_acquisition",return_value=auto),
            mock.patch.object(runtime,"writej"),
            mock.patch.object(
                runtime,"_verify_and_promote_acquisition",
                return_value={
                    "status":"VERIFIED_AND_PROMOTED",
                    "capability_id":"auto.test",
                },
            ),
            mock.patch.object(
                runtime,"_run_compiled_plain_goal",
                return_value=completed,
            ) as execute_mock,
        ):
            out=runtime.run_goal(
                {"goal_ref":"goal"},
                {
                    "mission_id":"TEST-AUTO-ACQUISITION-REPLAN",
                    "goal":goal,
                    "_runtime_mission_path":"canonical/astra_runtime/missions/TEST.json",
                },
            )
        self.assertTrue(out["verified"])
        self.assertEqual(out["controller_mode"],"MODEL_INDEPENDENT_ACTION_PLAN")
        self.assertEqual(out["model_dependency_count"],0)
        self.assertEqual(out["cognition_dependency_class"],"MODEL_INDEPENDENT")
        self.assertEqual(compile_mock.call_count,2)
        execute_mock.assert_called_once_with(
            {"goal_ref":"goal"},
            mock.ANY,
            goal,
            compiled,
        )
        self.assertEqual(out["auto_acquisition"]["status"],"VERIFIED_AND_PROMOTED")
        self.assertEqual(out["acquisition_goal"],goal)

    def test_promotion_never_rewrites_originating_mission(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            runtime_dir=root/"canonical"/"runtime"
            mission_dir=root/"canonical"/"astra_runtime"/"missions"
            evidence_dir=root/"canonical"/"astra_runtime"/"evidence"
            pending_dir=root/"canonical"/"astra_runtime"/"pending_bindings"
            for path in (runtime_dir,mission_dir,evidence_dir,pending_dir):
                path.mkdir(parents=True,exist_ok=True)
            registry_path=runtime_dir/"BOUND_CAPABILITY_REGISTRY_V1.json"
            registry_path.write_text(
                json.dumps({"schema":"TEST","capabilities":{}}),
                encoding="utf-8",
            )
            mission_path=mission_dir/"ORIGIN.json"
            original=b'{"goal":"immutable authority"}\n'
            mission_path.write_bytes(original)
            pending_path=pending_dir/"pending.json"
            verify_path=evidence_dir/"verify.json"
            pending={
                "schema":"PROJECT_BRAIN_PENDING_AUTO_BINDING_V1",
                "capability_id":"auto.test",
                "origin_mission_path":"canonical/astra_runtime/missions/ORIGIN.json",
                "origin_mission_sha256_at_acquisition":hashlib.sha256(original).hexdigest(),
                "verification_mission_id":"VERIFY-AUTO-TEST",
                "registry_entry":{
                    "status":"BOUND_PENDING_INDEPENDENT_VERIFICATION",
                    "source":{"type":"python_stdlib"},
                    "action_template":{"type":"test"},
                },
            }
            verified={
                "schema":"PROJECT_BRAIN_AUTO_BINDING_VERIFICATION_V1",
                "capability_id":"auto.test",
                "verification_mission_id":"VERIFY-AUTO-TEST",
                "independent_verified":True,
                "adapter_result":{"verified":True},
            }
            pending_path.write_text(json.dumps(pending),encoding="utf-8")
            verify_path.write_text(json.dumps(verified),encoding="utf-8")
            argv=[
                "promote_pending_binding.py",
                "canonical/astra_runtime/pending_bindings/pending.json",
                "canonical/astra_runtime/evidence/verify.json",
            ]
            with (
                mock.patch.object(promoter,"ROOT",root),
                mock.patch.object(promoter,"REGISTRY",registry_path),
                mock.patch.object(sys,"argv",argv),
                mock.patch("builtins.print"),
            ):
                promoter.main()
            self.assertEqual(mission_path.read_bytes(),original)
            promoted=json.loads(registry_path.read_text(encoding="utf-8"))
            self.assertEqual(
                promoted["capabilities"]["auto.test"]["status"],
                "VERIFIED_BOUND_CAPABILITY",
            )
            pending_after=json.loads(pending_path.read_text(encoding="utf-8"))
            self.assertEqual(pending_after["status"],"PROMOTED_VERIFIED")
            self.assertEqual(
                pending_after["origin_mission_sha256_verified_at_promotion"],
                hashlib.sha256(original).hexdigest(),
            )


if __name__=="__main__":
    unittest.main(verbosity=2)
