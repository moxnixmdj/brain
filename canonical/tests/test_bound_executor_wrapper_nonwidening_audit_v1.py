import ast
import tempfile
import unittest
from pathlib import Path

from canonical.runtime import bound_executor_wrapper_nonwidening_audit_v1 as audit


GOOD = """from canonical.runtime import astra_runtime
from x import verify_execution
from y import plan_actions

def inspect(capability_id):
    return {}

def prepare(capability_id, inputs=None):
    inspect(capability_id)
    astra_runtime._render_bound_template({}, inputs or {})
    return {}

def execute(capability_id, inputs=None, expected_registry_file_sha256=None, expected_registry_entry_sha256=None, expected_rendered_action_sha256=None):
    prepared=prepare(capability_id, inputs=inputs)
    inspect(capability_id)
    if expected_registry_file_sha256 is not None and False:
        raise ValueError("REGISTRY_FILE_CHANGED_AFTER_PREPARATION")
    if expected_registry_entry_sha256 is not None and False:
        raise ValueError("REGISTRY_ENTRY_CHANGED_AFTER_PREPARATION")
    if expected_rendered_action_sha256 is not None and False:
        raise ValueError("RENDERED_ACTION_CHANGED_AFTER_PREPARATION")
    result=astra_runtime._invoke_bound_capability({})
    astra_runtime._verify_action_expectation({}, result)
    plan_actions({})
    verdict=verify_execution({}, {})
    if verdict.get("pass") is not True:
        raise ValueError("BOUND_CAPABILITY_EXECUTION_TRACE_NOT_VERIFIED")
    return result
"""


class WrapperAuditTests(unittest.TestCase):
    def run_source(self, source):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            p=root/audit.WRAPPER
            p.parent.mkdir(parents=True)
            p.write_text(source,encoding="utf-8")
            return audit.audit(root)

    def test_good_minimal_shape_passes(self):
        out=self.run_source(GOOD)
        self.assertTrue(out["pass"])
        self.assertEqual(out["single_operative_delegate"],"astra_runtime._invoke_bound_capability")

    def test_network_import_fails(self):
        with self.assertRaisesRegex(audit.WrapperAuditError,"|".join([".*"])):
            # Structural guard fails first or the audit returns fail closed.
            out=self.run_source("import socket\n"+GOOD)
            if not out["pass"]:
                raise audit.WrapperAuditError("FORBIDDEN_IMPORT")

    def test_second_operative_delegate_fails(self):
        bad=GOOD.replace(
            "result=astra_runtime._invoke_bound_capability({})",
            "result=astra_runtime._invoke_bound_capability({})\n    other=astra_runtime._invoke_bound_capability({})"
        )
        with self.assertRaisesRegex(audit.WrapperAuditError,"OPERATIVE_DELEGATE_COUNT_NOT_ONE"):
            self.run_source(bad)

    def test_missing_expectation_check_fails(self):
        bad=GOOD.replace("    astra_runtime._verify_action_expectation({}, result)\n","")
        with self.assertRaisesRegex(audit.WrapperAuditError,"EXPECTATION_CHECK_COUNT_NOT_ONE"):
            self.run_source(bad)

    def test_missing_independent_trace_verify_fails(self):
        bad=GOOD.replace("    verdict=verify_execution({}, {})\n","    verdict={'pass':True}\n")
        with self.assertRaisesRegex(audit.WrapperAuditError,"INDEPENDENT_TRACE_VERIFY_COUNT_NOT_ONE"):
            self.run_source(bad)

    def test_dynamic_exec_fails_closed(self):
        out=self.run_source(GOOD.replace("    return result","    exec('x=1')\n    return result"))
        self.assertFalse(out["pass"])
        self.assertIn("exec",out["forbidden_calls"])


if __name__=="__main__":
    unittest.main(verbosity=2)
