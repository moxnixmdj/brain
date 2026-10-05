from __future__ import annotations
import inspect
import unittest
from canonical.runtime import zero_ambient_namespace_launcher_v1 as m

class NamespaceCarrierInjectionTests(unittest.TestCase):
    def test_internal_runner_requires_callable_carrier(self):
        with self.assertRaisesRegex(m.NamespaceConfinementError,"POPEN_IMPL_NOT_CALLABLE"):
            m._run_confined({},popen_impl=None)

    def test_internal_runner_uses_injected_carrier(self):
        src=inspect.getsource(m._run_confined)
        self.assertIn("proc=popen_impl(cmd,**popen_kw)",src)

    def test_public_runner_preserves_default_behavior(self):
        src=inspect.getsource(m.run_confined)
        self.assertIn("_run_confined(policy,popen_impl=subprocess.Popen)",src)

if __name__=="__main__": unittest.main(verbosity=2)
