from __future__ import annotations

import importlib.util
import pathlib
import subprocess
import sys
import tempfile
import textwrap
import unittest

BASE=pathlib.Path("canonical/runtime/bound_capabilities")
SPEC=importlib.util.spec_from_file_location(
    "semantic_v9", BASE/"python_software_request_semantic_acceptance_v1.py"
)
v9=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(v9)


class PythonSoftwareRequestSemanticAcceptanceV1Tests(unittest.TestCase):
    def execute(self, task: str, files: dict[str,str]):
        compiled=v9.compile_request(task)
        self.assertTrue(compiled["coverage_complete"], compiled)
        program=v9.render_test(compiled)
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            for name,body in files.items():
                p=root/name
                p.parent.mkdir(parents=True,exist_ok=True)
                p.write_text(textwrap.dedent(body),encoding="utf-8")
            (root/"semantic_acceptance.py").write_text(program,encoding="utf-8")
            proc=subprocess.run(
                [sys.executable,"semantic_acceptance.py"],
                cwd=root,text=True,capture_output=True,timeout=5,
            )
            return compiled,program,proc

    def test_call_bool_compiles_across_lossless_dot_segments_and_executes(self):
        task="Calling m.f with JSON arguments [3] must be true."
        compiled,_,proc=self.execute(task,{"m.py":"def f(x): return x == 3\n"})
        self.assertEqual(proc.returncode,0,proc.stderr)
        self.assertIn("V9_SEMANTIC_ACCEPTANCE_PASS",proc.stdout)
        self.assertGreater(len(compiled["required_obligation_ids"]),1)
        self.assertEqual(
            set(compiled["required_obligation_ids"]),
            set(compiled["compiled_obligation_ids"]),
        )
        self.assertEqual(compiled["cells"][0]["kind"],"PYTHON_CALL_EQUALS")

    def test_call_equals_json_string_ending_period(self):
        task='Calling m.f with JSON arguments [] must equal "ready.".'
        compiled,_,proc=self.execute(task,{"m.py":"def f(): return 'ready.'\n"})
        self.assertEqual(proc.returncode,0,proc.stderr)
        self.assertEqual(compiled["cells"][0]["spec"]["expected"],"ready.")

    def test_call_raises_builtin(self):
        task="Calling m.f with JSON arguments [0] must raise ValueError."
        _,_,proc=self.execute(
            task,
            {"m.py":"def f(x):\n    if x == 0: raise ValueError('x')\n    return x\n"},
        )
        self.assertEqual(proc.returncode,0,proc.stderr)

    def test_file_text_with_dot_path_executes(self):
        task='File "m.py" must contain exact text "return 7".'
        compiled,_,proc=self.execute(task,{"m.py":"def f():\n    return 7\n"})
        self.assertEqual(proc.returncode,0,proc.stderr)
        self.assertEqual(compiled["cells"][0]["kind"],"FILE_TEXT_CONTAINS_EXACT")

    def test_function_and_class_lines_compose_with_complete_lossless_coverage(self):
        task='Python function f must exist in file "m.py".\nPython class C must exist in file "m.py".'
        compiled,_,proc=self.execute(
            task,
            {"m.py":"def f(): return 1\nclass C:\n    pass\n"},
        )
        self.assertEqual(proc.returncode,0,proc.stderr)
        self.assertEqual(len(compiled["cells"]),2)
        self.assertEqual(
            set(compiled["required_obligation_ids"]),
            set(compiled["compiled_obligation_ids"]),
        )

    def test_supported_semantic_failure_is_observed_by_generated_test(self):
        task="Calling m.f with JSON arguments [3] must be false."
        compiled=v9.compile_request(task)
        self.assertTrue(compiled["coverage_complete"],compiled)
        program=v9.render_test(compiled)
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            (root/"m.py").write_text("def f(x): return True\n",encoding="utf-8")
            (root/"semantic_acceptance.py").write_text(program,encoding="utf-8")
            proc=subprocess.run(
                [sys.executable,"semantic_acceptance.py"],
                cwd=root,text=True,capture_output=True,timeout=5,
            )
            self.assertNotEqual(proc.returncode,0)

    def test_unsupported_prose_remains_blocking_residual(self):
        out=v9.compile_request("Fix the parser bug.")
        self.assertFalse(out["pass"],out)
        self.assertFalse(out["coverage_complete"])
        self.assertTrue(out["residual_obligation_ids"])
        with self.assertRaisesRegex(v9.SemanticAcceptanceError,"SEMANTIC_COVERAGE_INCOMPLETE"):
            v9.render_test(out)

    def test_mixed_supported_and_unsupported_lines_cannot_partially_accept(self):
        task="Calling m.f with JSON arguments [3] must be true.\nMake it elegant."
        out=v9.compile_request(task)
        self.assertFalse(out["pass"],out)
        self.assertTrue(out["compiled_obligation_ids"])
        self.assertTrue(out["residual_obligation_ids"])
        self.assertTrue(
            set(out["compiled_obligation_ids"]).isdisjoint(out["residual_obligation_ids"])
        )
        self.assertEqual(
            set(out["required_obligation_ids"]),
            set(out["compiled_obligation_ids"])|set(out["residual_obligation_ids"]),
        )

    def test_injection_shaped_callable_is_not_compiled(self):
        task="Calling __import__('os').system with JSON arguments [\"id\"] must equal 0."
        out=v9.compile_request(task)
        self.assertFalse(out["coverage_complete"],out)
        self.assertTrue(out["residual_obligation_ids"])

    def test_malformed_json_is_residual_with_compile_error(self):
        task="Calling m.f with JSON arguments [1,] must equal 2."
        out=v9.compile_request(task)
        self.assertFalse(out["coverage_complete"],out)
        self.assertTrue(out["compile_errors"])
        self.assertTrue(out["residual_obligation_ids"])

    def test_external_module_cannot_satisfy_repository_local_call_cell(self):
        task='Calling json.dumps with JSON arguments [{"a":1}] must equal "{\\"a\\": 1}".'
        compiled=v9.compile_request(task)
        self.assertTrue(compiled["coverage_complete"],compiled)
        program=v9.render_test(compiled)
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            (root/"semantic_acceptance.py").write_text(program,encoding="utf-8")
            proc=subprocess.run(
                [sys.executable,"semantic_acceptance.py"],
                cwd=root,text=True,capture_output=True,timeout=5,
            )
            self.assertNotEqual(proc.returncode,0)
            self.assertIn("SEMANTIC_MODULE_NOT_UNIQUE_REPOSITORY_LOCAL",proc.stderr)

    def test_bound_run_writes_content_addressed_compilation(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            out=v9.run({
                "task_text":"Calling m.f with JSON arguments [3] must be true.",
                "output_path":"semantic.json",
            },root)
            self.assertTrue(out["coverage_complete"],out)
            self.assertTrue(out["output_verified"])
            self.assertTrue(out["acceptance_program_sha256"])
            self.assertTrue((root/"semantic.json").is_file())

    def test_deterministic_compilation_and_rendering(self):
        task='Python function f must exist in file "m.py".\nCalling m.f with JSON arguments [2] must equal 4.'
        a=v9.compile_request(task)
        b=v9.compile_request(task)
        self.assertEqual(a,b)
        self.assertEqual(v9.render_test(a),v9.render_test(b))
        self.assertEqual(a["model_dependency_count"],0)
        self.assertEqual(a["external_general_purpose_model_runtime_dependency_count"],0)
        self.assertEqual(a["incremental_spend_usd"],0)


if __name__=="__main__":
    unittest.main(verbosity=2)
