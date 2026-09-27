#!/usr/bin/env python3
import importlib
import pathlib
import sys
import unittest
from unittest import mock

CANONICAL_ROOT=pathlib.Path(__file__).resolve().parents[1]
RUNTIME_DIR=CANONICAL_ROOT/"runtime"
if str(RUNTIME_DIR) not in sys.path:
    sys.path.insert(0,str(RUNTIME_DIR))

router=importlib.import_module("auto_capability_acquisition")
github=importlib.import_module("auto_github_source_acquisition")


class GenericGitHubSourceFallbackTests(unittest.TestCase):
    def test_generic_binary_goal_is_eligible_for_pinned_github_source(self):
        goal=(
            "Encode canonical/CANONICAL_POINTER.json as UBJSON and save "
            "canonical/astra_runtime/artifacts/CANONICAL_POINTER.ubj"
        )
        self.assertTrue(github.supports(goal))

    def test_non_encoding_goal_is_not_eligible(self):
        self.assertFalse(github.supports("Summarize canonical/CANONICAL_POINTER.json"))

    def test_router_falls_through_from_pypi_to_github_source(self):
        goal=(
            "Encode canonical/CANONICAL_POINTER.json as UBJSON and save "
            "canonical/astra_runtime/artifacts/CANONICAL_POINTER.ubj"
        )
        expected={
            "status":"ACQUISITION_DISPATCHED",
            "supplier_class":"github_source_python",
            "capability_id":"auto.github.example",
        }
        with (
            mock.patch.object(router.auto_pypi_library_acquisition,"supports",return_value=True),
            mock.patch.object(
                router.auto_pypi_library_acquisition,
                "dispatch",
                side_effect=RuntimeError("NO_BOUNDED_PYPI_CANDIDATE"),
            ),
            mock.patch.object(router.auto_github_source_acquisition,"supports",return_value=True),
            mock.patch.object(
                router.auto_github_source_acquisition,
                "dispatch",
                return_value=expected,
            ) as github_dispatch,
            mock.patch.object(
                router.auto_apt_cli_acquisition,
                "dispatch",
                side_effect=AssertionError("APT must not run after GitHub success"),
            ),
        ):
            out=router.dispatch(
                goal,
                "TEST-GENERIC-GITHUB-FALLBACK",
                "canonical/astra_runtime/missions/TEST.json",
                CANONICAL_ROOT.parent,
                discovery={"candidates":[]},
            )
        self.assertIs(out,expected)
        github_dispatch.assert_called_once()

    def test_router_preserves_all_failure_classes_when_fallbacks_fail(self):
        goal=(
            "Encode canonical/CANONICAL_POINTER.json as UBJSON and save "
            "canonical/astra_runtime/artifacts/CANONICAL_POINTER.ubj"
        )
        with (
            mock.patch.object(router.auto_pypi_library_acquisition,"supports",return_value=True),
            mock.patch.object(router.auto_pypi_library_acquisition,"dispatch",side_effect=RuntimeError("pypi")),
            mock.patch.object(router.auto_github_source_acquisition,"supports",return_value=True),
            mock.patch.object(router.auto_github_source_acquisition,"dispatch",side_effect=RuntimeError("github")),
            mock.patch.object(router.auto_apt_cli_acquisition,"dispatch",side_effect=RuntimeError("apt")),
        ):
            with self.assertRaises(router.AutoAcquisitionFailure) as ctx:
                router.dispatch(
                    goal,
                    "TEST-GENERIC-GITHUB-FALLBACK",
                    "canonical/astra_runtime/missions/TEST.json",
                    CANONICAL_ROOT.parent,
                    discovery={"candidates":[]},
                )
        detail=str(ctx.exception)
        self.assertIn("pypi_python_library",detail)
        self.assertIn("github_source_python",detail)
        self.assertIn("apt_cli",detail)


if __name__=="__main__":
    unittest.main(verbosity=2)
