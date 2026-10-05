from __future__ import annotations

import inspect
import subprocess
import unittest

from canonical.runtime import astra_runtime as astra
from canonical.runtime import root3_subprocess_mediator_v2 as mediator
from canonical.runtime import root3_strict_current_bootstrap_v2 as bootstrap
from canonical.runtime import root3_two_class_attempt_authorizer_v1 as authorizer


class Root3AstraEntrypointInstallTests(unittest.TestCase):
    def tearDown(self):
        try:
            mediator.uninstall()
        except Exception:
            subprocess.run=mediator._ORIGINAL_RUN
            subprocess.Popen=mediator._ORIGINAL_POPEN
            mediator._AUTHORIZER=None
            mediator._AUTHORITY_ID=None
            mediator._CLASS_EXECUTORS={}
            mediator._INSTALLED=False

    def test_helper_installs_exact_current_boundary(self):
        out=astra._activate_root3_subprocess_boundary()
        self.assertEqual(out["status"],"INSTALLED_EXACT_CURRENT_ROOT3_BOUNDARY")
        self.assertEqual(out["authority_id"],authorizer.AUTHORITY_ID)
        self.assertEqual(set(out["bound_effect_classes"]),set(bootstrap.BOUND_EFFECT_CLASSES))
        self.assertEqual(set(out["denied_effect_classes"]),set(bootstrap.DENIED_EFFECT_CLASSES))
        st=mediator.status()
        self.assertTrue(st["run_guard_active"])
        self.assertTrue(st["popen_guard_active"])

    def test_helper_reuses_only_exact_same_boundary(self):
        astra._activate_root3_subprocess_boundary()
        out=astra._activate_root3_subprocess_boundary()
        self.assertEqual(out["status"],"REUSED_EXACT_CURRENT_ROOT3_BOUNDARY")
        self.assertEqual(out["authority_id"],authorizer.AUTHORITY_ID)

    def test_preexisting_wrong_authority_fails_closed(self):
        fake={name:(lambda context: context) for name in bootstrap.BOUND_EFFECT_CLASSES}
        mediator.install(lambda req:{"allowed":False},authority_id="WRONG",class_executors=fake)
        with self.assertRaisesRegex(astra.Blocker,"ROOT3_PREEXISTING_SUBPROCESS_BOUNDARY_MISMATCH"):
            astra._activate_root3_subprocess_boundary()

    def test_main_installs_root3_before_external_bridge_and_step_loop(self):
        src=inspect.getsource(astra.main)
        install=src.index("_activate_root3_subprocess_boundary()")
        http=src.index("_activate_external_http_bridge()")
        step_loop=src.index('for i in range(state["next_step"],len(mission["steps"]))')
        self.assertLess(install,http)
        self.assertLess(install,step_loop)

    def test_root3_installation_is_after_mission_identity_binding(self):
        src=inspect.getsource(astra.main)
        identity=src.index('mission["_runtime_mission_path"]=mission_rel')
        install=src.index("_activate_root3_subprocess_boundary()")
        self.assertLess(identity,install)


if __name__=="__main__":
    unittest.main(verbosity=2)
