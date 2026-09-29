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

spec=importlib.util.spec_from_file_location(
    "auto_apt_cli_provider_neutral_admission_test",
    RUNTIME_DIR/"auto_apt_cli_acquisition.py",
)
apt=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=apt
spec.loader.exec_module(apt)


def candidate(name, *, binding_kind="apt", score=0.0, description="barcode generator"):
    return {
        "discovery_source":"SYNTHETIC_PROVIDER",
        "name":name,
        "description":description,
        "matched_terms":[],
        "score":score,
        "integration_friction":0,
        "required_secret_count":0,
        "zero_cost_eligible":True,
        "binding_kind":binding_kind,
        "version":"1.0",
        "archive_sha256":"a"*64,
    }


class ProviderNeutralAptAdmissionTests(unittest.TestCase):
    def test_low_numeric_score_apt_candidate_is_admitted(self):
        discovery={"candidates":[candidate("low-scale-tool",score=0.000001)]}
        with mock.patch.object(apt.capability_discovery,"effect_queries",return_value=["barcode"]):
            out=apt._viable_candidates(discovery,"Generate a barcode image.")
        self.assertEqual([x["name"] for x in out],["low-scale-tool"])

    def test_binding_kind_not_source_name_controls_apt_admission(self):
        item=candidate("future-provider-tool",score=-500.0)
        item["discovery_source"]="AN_UNSEEN_APT_DISCOVERY_PROVIDER"
        with mock.patch.object(apt.capability_discovery,"effect_queries",return_value=["barcode"]):
            out=apt._viable_candidates({"candidates":[item]},"Generate a barcode image.")
        self.assertEqual(out[0]["name"],"future-provider-tool")

    def test_non_apt_binding_is_rejected_even_with_huge_score(self):
        item=candidate("not-an-apt-tool",binding_kind="pypi",score=10**12)
        with mock.patch.object(apt.capability_discovery,"effect_queries",return_value=["barcode"]):
            with self.assertRaisesRegex(apt.AutoAcquisitionFailure,"NO_LOW_FRICTION_APT_CLI_CANDIDATE"):
                apt._viable_candidates({"candidates":[item]},"Generate a barcode image.")

    def test_provider_relative_order_not_raw_score_breaks_equal_role_ties(self):
        first=candidate("first-provider-ranked",score=0.000001)
        second=candidate("second-provider-ranked",score=10**12)
        with mock.patch.object(apt.capability_discovery,"effect_queries",return_value=["barcode"]):
            out=apt._viable_candidates(
                {"candidates":[first,second]},
                "Generate a barcode image.",
            )
        self.assertEqual([x["name"] for x in out[:2]],[
            "first-provider-ranked",
            "second-provider-ranked",
        ])
        self.assertEqual(out[0]["_acquisition_provider_rank"],1)
        self.assertEqual(out[1]["_acquisition_provider_rank"],2)


if __name__=="__main__":
    unittest.main(verbosity=2)
