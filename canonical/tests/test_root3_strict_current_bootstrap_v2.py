from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import root3_strict_current_bootstrap_v2 as boot


class BootstrapV2Tests(unittest.TestCase):
    def test_exact_current_class_partition(self):
        self.assertEqual(boot.CURRENT_PROCESS_SITE_COUNT,18)
        self.assertEqual(len(boot.EXPECTED),18)
        self.assertEqual(
            boot.BOUND_EFFECT_CLASSES,
            frozenset({"READ_ONLY_DECLARED_QUERY","TEMPORARY_FILESYSTEM_TRANSFORM"}),
        )
        self.assertEqual(
            boot.DENIED_EFFECT_CLASSES,
            frozenset(boot.CLASSES-boot.BOUND_EFFECT_CLASSES),
        )

    def test_install_binds_exactly_two_verified_classes(self):
        fake_read=lambda ctx: ("read",ctx)
        fake_temp=lambda ctx: ("temp",ctx)
        captured={}
        def fake_install(authorizer,*,authority_id,class_executors):
            captured["authority_id"]=authority_id
            captured["executors"]=dict(class_executors)
            return {
                "bound_effect_class_executors":sorted(class_executors),
                "unbound_effect_classes":sorted(boot.CLASSES-set(class_executors)),
                "run_guard_active":True,
                "popen_guard_active":True,
            }
        with patch.object(boot.read_only,"make_executor",return_value=fake_read), \
             patch.object(boot.temp_transform,"make_executor",return_value=fake_temp), \
             patch.object(boot.mediator,"install",side_effect=fake_install):
            out=boot.install_current(lambda req:{"allowed":False},authority_id="test-v2")
        self.assertEqual(
            set(captured["executors"]),
            {"READ_ONLY_DECLARED_QUERY","TEMPORARY_FILESYSTEM_TRANSFORM"},
        )
        self.assertIs(captured["executors"]["READ_ONLY_DECLARED_QUERY"],fake_read)
        self.assertIs(captured["executors"]["TEMPORARY_FILESYSTEM_TRANSFORM"],fake_temp)
        self.assertEqual(out["status"],"INSTALLED_FAIL_CLOSED")
        self.assertEqual(out["process_site_count"],18)

    def test_status_mismatch_fails_closed(self):
        with patch.object(boot.read_only,"make_executor",return_value=lambda ctx:None), \
             patch.object(boot.temp_transform,"make_executor",return_value=lambda ctx:None), \
             patch.object(boot.mediator,"install",return_value={
                 "bound_effect_class_executors":["READ_ONLY_DECLARED_QUERY"],
                 "unbound_effect_classes":sorted(boot.CLASSES-{"READ_ONLY_DECLARED_QUERY"}),
                 "run_guard_active":True,
                 "popen_guard_active":True,
             }):
            with self.assertRaisesRegex(boot.BootstrapError,"BOUND_EFFECT_CLASS_SET_MISMATCH"):
                boot.install_current(lambda req:{"allowed":False},authority_id="test-v2")

if __name__=="__main__":
    unittest.main(verbosity=2)
