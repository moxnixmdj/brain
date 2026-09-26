#!/usr/bin/env python3
import importlib.util
import pathlib
import sys
import tempfile
import unittest

CANONICAL_ROOT=pathlib.Path(__file__).resolve().parents[1]
PATH=CANONICAL_ROOT/"runtime"/"goal_compiler.py"
spec=importlib.util.spec_from_file_location("goal_compiler_root_binding_target",PATH)
compiler=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=compiler
spec.loader.exec_module(compiler)


class GenericContextRootBindingTests(unittest.TestCase):
    def entry(self):
        return {
            "status":"VERIFIED_BOUND_CAPABILITY",
            "action_template":{
                "type":"invoke_capability",
                "args":{
                    "capability_id":"python.source.audit.ast",
                    "source_root":"${input.source_root}",
                    "output_path":"${input.output_path}",
                },
                "expect":{"type":"field_equals","field":"output_verified","value":True},
            },
            "adapter_module":"python_source_audit",
            "keywords":["python","source","audit","imports","functions","classes","sha256"],
            "provides":["python.source.audit"],
            "requires":[],
        }

    def clause(self):
        return (
            "Create canonical/astra_runtime/tmp/PYTHON_RUNTIME_AUDIT.json containing "
            "one record per .py file with its repository-relative path, SHA-256, "
            "top-level imported module names, top-level function names, and top-level class names"
        )

    def historical_goal(self):
        return (
            "Inspect every Python file under canonical/runtime. "
            "Create canonical/astra_runtime/tmp/PYTHON_RUNTIME_AUDIT.json containing "
            "one record per .py file with its repository-relative path, SHA-256, "
            "top-level imported module names, top-level function names, and top-level class names. "
            "Include totals for files, functions, classes, and distinct imported modules. "
            "Finally independently verify against the raw Python source files that every reported "
            "file exists, every reported SHA-256 matches its exact bytes, every reported top-level "
            "function and class is actually defined in that file, and fail if any Python file under "
            "canonical/runtime is missing from the audit."
        )

    def test_historical_python_audit_compiles_without_specialized_shim(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            runtime_dir=root/"canonical"/"runtime"
            runtime_dir.mkdir(parents=True)
            (runtime_dir/"sample.py").write_text("def sample():\n    return 1\n",encoding="utf-8")
            registry={"python.source.audit.ast":self.entry()}

            compiled=compiler.compile_goal(self.historical_goal(),registry,root)
            self.assertFalse(hasattr(compiler,"_compile_python_source_audit"))
            self.assertEqual(compiled["compiler_mode"],"DETERMINISTIC_COMPOUND_ACTION_PLAN")
            self.assertEqual(compiled["compiled_parts"][0]["mode"],"NATIVE_TREE_INSPECTION")
            audit=compiled["compiled_parts"][1]
            self.assertEqual(audit["mode"],"VERIFIED_CAPABILITY")
            self.assertEqual(audit["selected_capability"],"python.source.audit.ast")
            self.assertEqual(audit["inputs"],{
                "source_root":"canonical/runtime",
                "output_path":"canonical/astra_runtime/tmp/PYTHON_RUNTIME_AUDIT.json",
            })
            self.assertEqual(compiled["controller_actions"][1],{
                "type":"invoke_capability",
                "args":{
                    "capability_id":"python.source.audit.ast",
                    "source_root":"canonical/runtime",
                    "output_path":"canonical/astra_runtime/tmp/PYTHON_RUNTIME_AUDIT.json",
                },
                "expect":{"type":"field_equals","field":"output_verified","value":True},
            })
            self.assertEqual(compiled["compiled_parts"][2]["mode"],"PYTHON_AUDIT_TOTALS_INCLUDED")
            self.assertEqual(compiled["compiled_parts"][3]["mode"],"INDEPENDENT_PYTHON_SOURCE_VERIFICATION")

    def test_multiple_context_directories_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            (root/"canonical"/"runtime").mkdir(parents=True)
            (root/"canonical"/"other").mkdir(parents=True)
            entry=self.entry()
            with self.assertRaisesRegex(
                compiler.GoalCompilationFailure,
                "GOAL_DIRECTORY_BINDING_REQUIRED",
            ):
                compiler._bind_inputs(
                    self.clause(),
                    root,
                    entry,
                    context_paths=["canonical/runtime","canonical/other"],
                )


if __name__=="__main__":
    unittest.main(verbosity=2)
