#!/usr/bin/env python3
import importlib.util
import pathlib
import sys
import unittest
from unittest import mock

CANONICAL_ROOT=pathlib.Path(__file__).resolve().parents[1]
RUNTIME=CANONICAL_ROOT/"runtime"
spec=importlib.util.spec_from_file_location(
    "npm_package_utils_builtin_boundary_target",RUNTIME/"npm_package_utils.py"
)
utils=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=utils
spec.loader.exec_module(utils)


class NpmBuiltinDependencyBoundaryTests(unittest.TestCase):
    def test_runtime_proven_node_builtin_dependency_is_allowed(self):
        meta={"dependencies":{"buffer":"^6.0.3"}}
        with mock.patch.object(utils,"node_builtin_modules",return_value={"buffer","fs","path"}):
            out=utils.validate_builtin_only_runtime_dependencies(meta)
        self.assertEqual(out["declared_dependency_count"],1)
        self.assertEqual(out["external_runtime_dependency_count"],0)
        self.assertEqual(out["builtin_runtime_dependencies"],["buffer"])

    def test_external_runtime_dependency_still_fails_closed(self):
        meta={"dependencies":{"left-pad":"1.3.0"}}
        with mock.patch.object(utils,"node_builtin_modules",return_value={"buffer","fs","path"}):
            with self.assertRaisesRegex(
                utils.NpmPackageFailure,"NPM_EXTERNAL_RUNTIME_DEPENDENCIES_UNSUPPORTED"
            ):
                utils.validate_builtin_only_runtime_dependencies(meta)

    def test_lifecycle_script_remains_forbidden(self):
        meta={"dependencies":{"buffer":"^6.0.3"},"scripts":{"install":"node install.js"}}
        with mock.patch.object(utils,"node_builtin_modules",return_value={"buffer"}):
            with self.assertRaisesRegex(
                utils.NpmPackageFailure,"NPM_LIFECYCLE_SCRIPTS_REJECTED"
            ):
                utils.validate_builtin_only_runtime_dependencies(meta)


if __name__=="__main__":
    unittest.main(verbosity=2)
