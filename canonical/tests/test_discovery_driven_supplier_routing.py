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

router=load("discovery_driven_supplier_router_test",RUNTIME_DIR/"auto_capability_acquisition.py")
npm=router.auto_npm_library_acquisition

class DiscoveryDrivenSupplierRoutingTests(unittest.TestCase):
    def test_discovery_rank_routes_apt_first(self):
        goal="Create an unfamiliar output artifact."
        discovery={
            "candidates":[
                {"name":"best-cli","binding_kind":"apt","discovery_source":"APT_CATALOG"},
                {"name":"fallback-lib","binding_kind":"pypi","discovery_source":"PYPI"},
            ]
        }
        expected={"status":"ACQUISITION_DISPATCHED","supplier_class":"apt_cli"}
        with (
            mock.patch.object(router.auto_pypi_library_acquisition,"supports",return_value=True),
            mock.patch.object(npm,"supports_effect",return_value=True),
            mock.patch.object(router.auto_apt_cli_acquisition,"dispatch",return_value=expected) as apt_dispatch,
            mock.patch.object(router.auto_pypi_library_acquisition,"dispatch",side_effect=AssertionError("unexpected pypi dispatch")),
            mock.patch.object(npm,"dispatch",side_effect=AssertionError("unexpected npm dispatch")),
        ):
            out=router.dispatch(goal,"M","canonical/astra_runtime/missions/M.json","/tmp",discovery=discovery)
        self.assertIs(out,expected)
        apt_dispatch.assert_called_once()

    def test_discovery_failure_falls_to_next_ranked_supplier(self):
        goal="Create an unfamiliar output artifact."
        discovery={
            "candidates":[
                {"name":"first-cli","binding_kind":"apt","discovery_source":"APT_CATALOG"},
                {"name":"second-lib","binding_kind":"pypi","discovery_source":"PYPI"},
            ]
        }
        expected={"status":"ACQUISITION_DISPATCHED","supplier_class":"pypi_python_library"}
        with (
            mock.patch.object(router.auto_pypi_library_acquisition,"supports",return_value=False),
            mock.patch.object(npm,"supports_effect",return_value=False),
            mock.patch.object(router.auto_apt_cli_acquisition,"dispatch",side_effect=RuntimeError("no safe cli")) as apt_dispatch,
            mock.patch.object(router.auto_pypi_library_acquisition,"dispatch",return_value=expected) as pypi_dispatch,
        ):
            out=router.dispatch(goal,"M","canonical/astra_runtime/missions/M.json","/tmp",discovery=discovery)
        self.assertIs(out,expected)
        apt_dispatch.assert_called_once()
        pypi_dispatch.assert_called_once()

if __name__=="__main__":
    unittest.main(verbosity=2)
