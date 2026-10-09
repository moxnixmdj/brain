import tempfile
import unittest
from pathlib import Path

from canonical.runtime import bound_stdlib_dispatch_nonwidening_audit_v1 as audit


def good_slice():
    p=Path(__file__).resolve().parents[1]/"verification"/"ASTRA_BOUND_STDLIB_DISPATCH_SLICE_20261009_V1.py"
    return p.read_text(encoding="utf-8")


class StdlibDispatchAuditTests(unittest.TestCase):
    def run_slice(self,text):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            p=root/audit.SLICE
            p.parent.mkdir(parents=True)
            p.write_text(text,encoding="utf-8")
            return audit.audit(root)

    def test_exact_current_slice_passes(self):
        out=audit.audit(Path(__file__).resolve().parents[2])
        self.assertTrue(out["pass"])

    def test_network_call_in_local_dependency_fails(self):
        s=good_slice().replace(
            "spec=importlib.util.find_spec(module)",
            "urllib.request.urlopen('https://example.com')\n                spec=importlib.util.find_spec(module)"
        )
        with self.assertRaisesRegex(audit.StdlibDispatchAuditError,"STDLIB_BRANCH_AUTHORITY_WIDENING"):
            self.run_slice(s)

    def test_local_branch_redirect_to_pypi_fails(self):
        s=good_slice().replace(
            "dependency=_ensure_local_dependency(source)",
            "dependency=_ensure_pypi_dependency(source)"
        )
        with self.assertRaisesRegex(audit.StdlibDispatchAuditError,"LOCAL_SOURCE_NOT_ROUTED_TO_LOCAL_DEPENDENCY_CHECK"):
            self.run_slice(s)

    def test_adapter_name_sanitizer_removal_fails(self):
        s=good_slice().replace(
            'if not module_name or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_" for ch in module_name):',
            'if not module_name:'
        )
        with self.assertRaisesRegex(audit.StdlibDispatchAuditError,"ADAPTER_NAME_SANITIZER_MISSING"):
            self.run_slice(s)

    def test_adapter_path_escape_fails(self):
        s=good_slice().replace(
            'ROOT/"canonical"/"runtime"/"bound_capabilities"/(module_name+".py")',
            'ROOT/"tmp"/(module_name+".py")'
        )
        with self.assertRaisesRegex(audit.StdlibDispatchAuditError,"ADAPTER_PATH_NOT_FIXED_TO_BOUND_CAPABILITIES"):
            self.run_slice(s)

    def test_second_adapter_entrypoint_call_fails(self):
        s=good_slice().replace(
            "result=fn(call_args,ROOT)",
            "result=fn(call_args,ROOT)\n    result2=fn(call_args,ROOT)"
        )
        with self.assertRaisesRegex(audit.StdlibDispatchAuditError,"ADAPTER_ENTRYPOINT_CALL_COUNT_NOT_ONE"):
            self.run_slice(s)

    def test_wrong_astra_blob_binding_fails(self):
        s=good_slice().replace(audit.EXPECTED_ASTRA_GIT_BLOB_SHA,"0"*40)
        with self.assertRaisesRegex(audit.StdlibDispatchAuditError,"SOURCE_ASTRA_BLOB_BINDING_MISMATCH"):
            self.run_slice(s)


if __name__=="__main__":
    unittest.main(verbosity=2)
