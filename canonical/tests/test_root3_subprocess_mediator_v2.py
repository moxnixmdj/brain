from __future__ import annotations

import base64
import io
import pathlib
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import root3_subprocess_mediator_v2 as m
from canonical.runtime.bound_capabilities import browser_chromedriver as browser
from canonical.runtime.bound_capabilities import jq_query


class _FakePopen:
    def __init__(self):
        self.returncode = 0
        self.terminated = False
        self.killed = False
    def terminate(self): self.terminated = True
    def wait(self, timeout=None): return self.returncode
    def kill(self): self.killed = True


class ClassBoundMediatorV2Tests(unittest.TestCase):
    def tearDown(self):
        try:
            m.uninstall()
        except Exception:
            subprocess.run = m._ORIGINAL_RUN
            subprocess.Popen = m._ORIGINAL_POPEN
            m._AUTHORIZER = None
            m._AUTHORITY_ID = None
            m._CLASS_EXECUTORS = {}
            m._INSTALLED = False

    def allow(self, seen):
        def auth(request):
            seen.append(dict(request))
            return {"allowed": True, "authorization_sha256": "a" * 64}
        return auth

    def test_unregistered_caller_fails_before_authorizer(self):
        seen = []
        m.install(self.allow(seen), authority_id="TEST")
        with self.assertRaisesRegex(
            m.ProcessEffectDenied, "SUBPROCESS_CALLSITE_CLASSIFICATION_DENIED"
        ):
            subprocess.run(["never", "runs"])
        self.assertEqual(seen, [])

    def test_registered_jq_denies_when_class_executor_missing(self):
        seen = []
        m.install(self.allow(seen), authority_id="TEST")
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            (root / "in.json").write_text('{"x":1}\n', encoding="utf-8")
            with self.assertRaisesRegex(
                m.ProcessEffectDenied,
                "PROCESS_EFFECT_CLASS_EXECUTOR_NOT_BOUND:READ_ONLY_DECLARED_QUERY",
            ):
                jq_query.run(
                    {"input_path":"in.json","output_path":"out.txt","filter":"."},
                    root,
                )
        self.assertEqual(len(seen), 1)
        self.assertEqual(
            seen[0]["callsite"]["effect_class"], "READ_ONLY_DECLARED_QUERY"
        )
        self.assertEqual(
            seen[0]["callsite"]["module_path"],
            "canonical/runtime/bound_capabilities/jq_query.py",
        )
        self.assertEqual(seen[0]["callsite"]["lineno"], 41)

    def test_registered_jq_executes_only_bound_exact_class_executor(self):
        auth_seen = []
        exec_seen = []
        def executor(context):
            exec_seen.append(context)
            return subprocess.CompletedProcess(
                args=context["args"][0], returncode=0, stdout="ok\n", stderr=""
            )
        m.install(
            self.allow(auth_seen),
            authority_id="TEST",
            class_executors={"READ_ONLY_DECLARED_QUERY": executor},
        )
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            (root / "in.json").write_text('{"x":1}\n', encoding="utf-8")
            out = jq_query.run(
                {"input_path":"in.json","output_path":"out.txt","filter":"."},
                root,
            )
            self.assertTrue(out["output_verified"])
        self.assertEqual(len(auth_seen), 1)
        self.assertEqual(len(exec_seen), 1)
        self.assertEqual(exec_seen[0]["effect_class"], "READ_ONLY_DECLARED_QUERY")
        self.assertEqual(exec_seen[0]["api"], "subprocess.run")

    def test_executor_cannot_spawn_reentrantly_through_mediator(self):
        auth_seen = []
        def executor(context):
            subprocess.run(["nested", "forbidden"])
        m.install(
            self.allow(auth_seen),
            authority_id="TEST",
            class_executors={"READ_ONLY_DECLARED_QUERY": executor},
        )
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            (root / "in.json").write_text('{"x":1}\n', encoding="utf-8")
            with self.assertRaisesRegex(
                m.ProcessEffectDenied,
                "SUBPROCESS_EFFECT_DURING_CLASS_EXECUTOR_FORBIDDEN",
            ):
                jq_query.run(
                    {"input_path":"in.json","output_path":"out.txt","filter":"."},
                    root,
                )

    def test_real_browser_popen_routes_only_to_loopback_executor(self):
        auth_seen = []
        exec_seen = []
        png = b"\x89PNG\r\n\x1a\n" + b"x" * 200
        def loopback_executor(context):
            exec_seen.append(context)
            return _FakePopen()
        def fake_json(method, url, payload=None, timeout=30):
            if url.endswith("/status"): return {"value":{"ready":True}}
            if url.endswith("/session") and method=="POST":
                return {"value":{"sessionId":"s"}}
            if url.endswith("/url") and method=="GET":
                return {"value":"https://example.test/"}
            if url.endswith("/title"): return {"value":"Example"}
            if url.endswith("/execute/sync"):
                return {"value":{"text":"hello","width":800,"height":800,"ready":"complete"}}
            if url.endswith("/screenshot"):
                return {"value":base64.b64encode(png).decode("ascii")}
            return {}
        m.install(
            self.allow(auth_seen),
            authority_id="TEST",
            class_executors={"LOCAL_LOOPBACK_SERVICE": loopback_executor},
        )
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            with patch.object(browser,"_free_port",return_value=43210), \
                 patch.object(browser,"_json_request",side_effect=fake_json):
                out=browser.run(
                    {"url":"https://example.test/","screenshot_path":"shot.png","result_path":"result.json"},
                    root,
                )
            self.assertTrue(out["output_verified"])
        self.assertEqual(len(exec_seen),1)
        self.assertEqual(exec_seen[0]["effect_class"],"LOCAL_LOOPBACK_SERVICE")
        self.assertEqual(exec_seen[0]["api"],"subprocess.Popen")
        self.assertEqual(auth_seen[0]["callsite"]["lineno"],50)

    def test_unknown_executor_class_rejected_on_install(self):
        with self.assertRaisesRegex(m.MediatorStateError,"UNKNOWN_EFFECT_CLASS_EXECUTOR"):
            m.install(
                lambda r: {"allowed":False},
                authority_id="TEST",
                class_executors={"NOT_A_CLASS": lambda c: None},
            )

    def test_uninstall_restores_exact_originals(self):
        m.install(lambda r: {"allowed":False}, authority_id="TEST")
        self.assertIsNot(subprocess.run,m._ORIGINAL_RUN)
        self.assertIsNot(subprocess.Popen,m._ORIGINAL_POPEN)
        m.uninstall()
        self.assertIs(subprocess.run,m._ORIGINAL_RUN)
        self.assertIs(subprocess.Popen,m._ORIGINAL_POPEN)


if __name__=="__main__":
    unittest.main(verbosity=2)
