#!/usr/bin/env python3
import importlib.util
import pathlib
import sys
import unittest
from unittest import mock

CANONICAL_ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNTIME_PATH = CANONICAL_ROOT / "runtime" / "astra_runtime.py"
spec = importlib.util.spec_from_file_location("astra_runtime_verifier_target", RUNTIME_PATH)
runtime = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = runtime
spec.loader.exec_module(runtime)

class RuntimeVerificationTests(unittest.TestCase):
    def test_stdout_marker_cannot_hide_nonzero_exit(self):
        step={"verify":{"type":"stdout_contains","text":"MATCH"}}
        result={"adapter":"shell","returncode":3,"stdout":"MATCH"}
        self.assertFalse(runtime.verify(step,result))

    def test_existing_file_cannot_hide_nonzero_exit(self):
        step={"verify":{"type":"file_exists","path":"canonical/laws/MODEL_NON_DEPENDENCE_LAW_V1.md"}}
        result={"adapter":"shell","returncode":2,"stdout":""}
        self.assertFalse(runtime.verify(step,result))

    def test_zero_exit_and_stdout_marker_pass(self):
        step={"verify":{"type":"stdout_contains","text":"MATCH"}}
        result={"adapter":"shell","returncode":0,"stdout":"MATCH"}
        self.assertTrue(runtime.verify(step,result))

    def test_nonzero_requires_explicit_override(self):
        step={"verify":{"type":"stdout_contains","text":"EXPECTED","allow_nonzero_returncode":True}}
        result={"adapter":"shell","returncode":7,"stdout":"EXPECTED"}
        self.assertTrue(runtime.verify(step,result))

    def test_python_source_verifier_has_ast_parser(self):
        tree=runtime.ast.parse("def f():\n    return 1\n")
        self.assertEqual(tree.body[0].name,"f")

    def test_shell_adapter_invokes_bash_as_argv_for_paths_with_spaces(self):
        completed=mock.Mock(returncode=0,stdout="OK\n",stderr="")
        with mock.patch.object(runtime,"_resolve_bash_executable",return_value="C:/Program Files/Git/bin/bash.exe"):
            with mock.patch.object(runtime.subprocess,"run",return_value=completed) as run:
                result=runtime.run_shell({"command":"echo OK"})
        args,kwargs=run.call_args
        self.assertEqual(args[0],["C:/Program Files/Git/bin/bash.exe","-lc","echo OK"])
        self.assertNotIn("shell",kwargs)
        self.assertEqual(result["returncode"],0)


    def test_mission_identity_normalizes_windows_and_posix_slashes(self):
        with __import__("tempfile").TemporaryDirectory() as td:
            root=pathlib.Path(td)
            mission=root/"canonical"/"astra_runtime"/"missions"/"M.json"
            mission.parent.mkdir(parents=True,exist_ok=True)
            mission.write_text('{"mission_id":"M","steps":[]}\n',encoding="utf-8")
            with mock.patch.object(runtime,"ROOT",root):
                posix_path,posix_rel=runtime._canonical_mission_path(
                    "canonical/astra_runtime/missions/M.json"
                )
                windows_path,windows_rel=runtime._canonical_mission_path(
                    "canonical\\astra_runtime\\missions\\M.json"
                )
            self.assertEqual(posix_path,mission.resolve())
            self.assertEqual(windows_path,mission.resolve())
            self.assertEqual(posix_rel,"canonical/astra_runtime/missions/M.json")
            self.assertEqual(windows_rel,posix_rel)

    def test_mission_identity_rejects_repository_escape(self):
        with __import__("tempfile").TemporaryDirectory() as td:
            root=pathlib.Path(td)
            with mock.patch.object(runtime,"ROOT",root):
                with self.assertRaisesRegex(runtime.Blocker,"MISSION_PATH_OUTSIDE_ROOT"):
                    runtime._canonical_mission_path("../outside.json")


    def test_supervisor_binding_attaches_only_to_fresh_state(self):
        state={"history":[],"next_step":0}
        out=runtime._bind_supervisor_identity(state,"AGENT-1","TASK-1")
        self.assertEqual(out["supervisor_agent_id"],"AGENT-1")
        self.assertEqual(out["supervisor_task_id"],"TASK-1")

    def test_supervisor_bound_state_requires_same_identity(self):
        state={
            "history":[],"next_step":0,
            "supervisor_agent_id":"AGENT-1",
            "supervisor_task_id":"TASK-1",
        }
        with self.assertRaisesRegex(runtime.Blocker,"STATE_SUPERVISOR_AGENT_ID_MISMATCH"):
            runtime._bind_supervisor_identity(dict(state),"AGENT-2","TASK-1")
        with self.assertRaisesRegex(runtime.Blocker,"STATE_SUPERVISOR_TASK_ID_MISMATCH"):
            runtime._bind_supervisor_identity(dict(state),"AGENT-1","TASK-2")
        with self.assertRaisesRegex(runtime.Blocker,"SUPERVISOR_BINDING_REQUIRED_FOR_BOUND_STATE"):
            runtime._bind_supervisor_identity(dict(state),None,None)

    def test_nonfresh_unbound_state_cannot_be_retroactively_claimed(self):
        state={"history":[{"step_index":0}],"next_step":1}
        with self.assertRaisesRegex(runtime.Blocker,"STATE_SUPERVISOR_BINDING_MISSING_ON_NONFRESH_STATE"):
            runtime._bind_supervisor_identity(state,"AGENT-1","TASK-1")

    def test_supervisor_env_binding_requires_both_fields(self):
        with mock.patch.dict(runtime.os.environ,{
            "PROJECT_BRAIN_AGENT_ID":"AGENT-1",
            "PROJECT_BRAIN_TASK_ID":"TASK-1",
        },clear=False):
            self.assertEqual(runtime._supervisor_binding_from_env(),("AGENT-1","TASK-1"))
        with mock.patch.dict(runtime.os.environ,{
            "PROJECT_BRAIN_AGENT_ID":"AGENT-1",
            "PROJECT_BRAIN_TASK_ID":"",
        },clear=False):
            with self.assertRaisesRegex(runtime.Blocker,"SUPERVISOR_BINDING_INCOMPLETE"):
                runtime._supervisor_binding_from_env()

if __name__=="__main__":
    unittest.main(verbosity=2)
