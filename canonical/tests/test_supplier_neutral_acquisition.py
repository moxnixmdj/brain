#!/usr/bin/env python3
import importlib.util
import pathlib
import sys
import unittest
from unittest import mock

CANONICAL_ROOT=pathlib.Path(__file__).resolve().parents[1]
RUNTIME_DIR=CANONICAL_ROOT/"runtime"
if str(RUNTIME_DIR) not in sys.path:
    sys.path.insert(0,str(RUNTIME_DIR))

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

router=load("supplier_neutral_router_test",RUNTIME_DIR/"auto_capability_acquisition.py")
npm=router.auto_npm_library_acquisition

class SupplierNeutralAcquisitionTests(unittest.TestCase):
    def test_generic_codec_goal_falls_through_to_npm_before_apt(self):
        goal="Encode canonical/CANONICAL_POINTER.json as UBJSON and save canonical/astra_runtime/artifacts/out.ubj."
        expected={"status":"ACQUISITION_DISPATCHED","supplier_class":"npm_javascript_library"}
        with (
            mock.patch.object(router.auto_pypi_library_acquisition,"supports",return_value=True),
            mock.patch.object(router.auto_pypi_library_acquisition,"dispatch",side_effect=RuntimeError("no safe wheel")),
            mock.patch.object(npm,"supports_effect",return_value=True),
            mock.patch.object(npm,"dispatch",return_value=expected) as npm_dispatch,
            mock.patch.object(router.auto_apt_cli_acquisition,"dispatch",side_effect=AssertionError("APT must not run after npm succeeds")),
        ):
            out=router.dispatch(goal,"M","canonical/astra_runtime/missions/M.json","/tmp")
        self.assertIs(out,expected)
        npm_dispatch.assert_called_once()

    def test_explicit_pypi_request_does_not_fall_through(self):
        goal="Using a PyPI Python library, encode source.json as UBJSON and save out.ubj."
        with (
            mock.patch.object(router.auto_pypi_library_acquisition,"dispatch",side_effect=RuntimeError("no contract")),
            mock.patch.object(npm,"dispatch") as npm_dispatch,
            mock.patch.object(router.auto_apt_cli_acquisition,"dispatch") as apt_dispatch,
        ):
            with self.assertRaisesRegex(router.AutoAcquisitionFailure,"NO_COMPATIBLE_REQUIRED_SUPPLIER_CONTRACT"):
                router.dispatch(goal,"M","canonical/astra_runtime/missions/M.json","/tmp")
        npm_dispatch.assert_not_called()
        apt_dispatch.assert_not_called()

    def test_explicit_apt_request_does_not_fall_through(self):
        goal="Using an apt Ubuntu package, encode source.json as UBJSON and save out.ubj."
        with (
            mock.patch.object(router.auto_apt_cli_acquisition,"dispatch",side_effect=RuntimeError("no contract")),
            mock.patch.object(router.auto_pypi_library_acquisition,"dispatch") as pypi_dispatch,
            mock.patch.object(npm,"dispatch") as npm_dispatch,
        ):
            with self.assertRaisesRegex(router.AutoAcquisitionFailure,"NO_COMPATIBLE_REQUIRED_SUPPLIER_CONTRACT"):
                router.dispatch(goal,"M","canonical/astra_runtime/missions/M.json","/tmp")
        pypi_dispatch.assert_not_called()
        npm_dispatch.assert_not_called()

if __name__=="__main__":
    unittest.main(verbosity=2)
