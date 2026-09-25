#!/usr/bin/env python3
import importlib.util
import pathlib
import sys
import unittest

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

if __name__=="__main__":
    unittest.main(verbosity=2)
