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

    def test_generic_single_capability_matches_specialized_python_audit_action(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            (root/"canonical"/"runtime").mkdir(parents=True)
            registry={"python.source.audit.ast":self.entry()}
            context=["canonical/runtime"]

            generic=compiler._compile_single_goal(
                self.clause(),registry,root,context_paths=context
            )
            self.assertEqual(generic["selected_capability"],"python.source.audit.ast")
            self.assertEqual(generic["inputs"],{
                "source_root":"canonical/runtime",
                "output_path":"canonical/astra_runtime/tmp/PYTHON_RUNTIME_AUDIT.json",
            })
            generic_action=compiler._render_template(
                registry["python.source.audit.ast"]["action_template"],
                generic["inputs"],
            )
            specialized=compiler._compile_python_source_audit(
                self.clause(),context,registry,root
            )
            self.assertIsNotNone(specialized)
            self.assertEqual(generic_action,specialized["action"])

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
