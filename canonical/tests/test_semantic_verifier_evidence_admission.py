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
    "semantic_verifier_evidence_admission_test",
    RUNTIME_DIR/"verify_pending_cli_binding.py",
)
verifier=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=verifier
spec.loader.exec_module(verifier)


def candidate(name="fixture-verifier", *, matched_terms=None, strong=False):
    item={
        "name":name,
        "matched_terms":list(matched_terms or []),
        "integration_friction":0,
        "required_secret_count":0,
        "zero_cost_eligible":True,
        "version":"1.0",
        "archive_sha256":"a"*64,
    }
    if strong:
        item.update({
            "eligibility_status":"LOCAL_EXECUTABLE_OWNERSHIP_VERIFIED",
            "evidence_tier":"SEMANTIC_PACKAGE_EXECUTABLE_OWNERSHIP",
            "executable_semantic_evidence":{
                "command_paths":["/usr/bin/fixture-verifier"],
                "semantic_source":"AUTHORITATIVE_METADATA_PLUS_EXECUTABLE_OWNERSHIP",
            },
        })
    return item


class SemanticVerifierEvidenceAdmissionTests(unittest.TestCase):
    def test_legacy_two_matched_terms_remain_admitted(self):
        item=candidate(matched_terms=["decode","image"])
        self.assertTrue(verifier._semantic_verifier_candidate_has_sufficient_evidence(item))

    def test_strong_executable_semantic_evidence_admits_without_matched_terms(self):
        item=candidate(strong=True)
        self.assertEqual(item["matched_terms"],[])
        self.assertTrue(verifier._semantic_verifier_candidate_has_sufficient_evidence(item))

    def test_metadata_only_candidate_without_ownership_remains_rejected(self):
        item=candidate()
        item["eligibility_status"]="LOCAL_PACKAGE_METADATA_CANDIDATE_UNVERIFIED"
        item["evidence_tier"]="SEMANTIC_PACKAGE_METADATA"
        self.assertFalse(verifier._semantic_verifier_candidate_has_sufficient_evidence(item))

    def test_declared_tier_without_command_paths_is_rejected(self):
        item=candidate(strong=True)
        item["executable_semantic_evidence"]["command_paths"]=[]
        self.assertFalse(verifier._semantic_verifier_candidate_has_sufficient_evidence(item))

    def test_strong_evidence_reaches_probe_instead_of_empty_attempt_failure(self):
        item=candidate(strong=True)
        pending={
            "goal":"neutral transformation",
            "selected_supplier":{"name":"different-producer"},
            "semantic_verification":{
                "expected_text":"neutral-fixture",
                "goal":"neutral transformation",
            },
        }
        with mock.patch.object(
            verifier.capability_discovery,
            "search_apt_packages",
            return_value={"candidates":[item]},
        ), mock.patch.object(
            verifier.apt_cli_probe,
            "probe",
            side_effect=RuntimeError("SYNTHETIC_PROBE_REACHED"),
        ):
            with self.assertRaises(RuntimeError) as ctx:
                verifier._acquire_and_run_semantic_verifier(pending,"/unused/fixture")
        message=str(ctx.exception)
        self.assertIn("VERIFIER_PROBE_FAILED",message)
        self.assertIn("fixture-verifier",message)
        self.assertNotEqual(message,"SEMANTIC_VERIFIER_ACQUISITION_FAILED:[]")

    def test_producer_exclusion_still_prevents_self_verification(self):
        item=candidate(name="same-producer",strong=True)
        pending={
            "goal":"neutral transformation",
            "selected_supplier":{"name":"same-producer"},
            "semantic_verification":{"expected_text":"neutral-fixture"},
        }
        with mock.patch.object(
            verifier.capability_discovery,
            "search_apt_packages",
            return_value={"candidates":[item]},
        ), mock.patch.object(verifier.apt_cli_probe,"probe") as probe:
            with self.assertRaisesRegex(
                RuntimeError,
                r"SEMANTIC_VERIFIER_ACQUISITION_FAILED:\[\]",
            ):
                verifier._acquire_and_run_semantic_verifier(pending,"/unused/fixture")
        probe.assert_not_called()


if __name__=="__main__":
    unittest.main(verbosity=2)
