from __future__ import annotations

from copy import deepcopy
import unittest

from canonical.runtime import professional_quality_whole_leaf_behavior_contract_domain_v1 as d

LEAF = "PQ::R1_TARGET_SPECIFICATION::SEMANTIC"
ROOT_ID = "R1_TARGET_SPECIFICATION"


def contract():
    return {
        "behavior_id": d.BEHAVIOR_ID,
        "source": "test",
        "inputs": "User objective, audience, source evidence, artifact type, constraints and current draft/render",
        "environment_state": "test environment",
        "allowed_information": "test information",
        "required_output_or_action": "test output",
        "success_condition": "test success",
        "failure_condition": "test failure",
        "terminal_consequence": "test consequence",
        "verification_route": "test verification",
        "dependency_boundary": "test dependency",
        "scope": "test scope",
    }


def registry():
    return {"active_contracted_residuals": [contract()]}


def manifest():
    return {
        "roots": [{
            "root_id": ROOT_ID,
            "contract": "Freeze objective, audience and decision-relevant target semantics.",
            "semantic_leaf": {
                "id": LEAF,
                "obligation": "PROVE_DOMAIN_SEMANTIC_SUFFICIENCY_FOR_R1_TARGET_SPECIFICATION",
                "acceptance": (
                    "ALL_ADMISSIBLE_R1_TARGET_SPECIFICATION_INPUTS_ARE_GROUNDED_"
                    "AND_DECISION_RELEVANT_AMBIGUITY_IS_RESOLVED"
                ),
            },
            "execution_leaf": {
                "id": "PQ::R1_TARGET_SPECIFICATION::EXECUTION",
                "obligation": "VERIFY_DOMAIN_EXECUTION_FOR_R1_TARGET_SPECIFICATION",
                "acceptance": "EXECUTION_ACCEPTANCE",
            },
        }]
    }


def subject():
    return {
        "subject_kind": d.gate.SUBJECT_KIND,
        "subject_id": d.gate.SUBJECT_ID,
        "subject_sha256": d.gate.SUBJECT_SHA256,
        "system_material": {
            "components": [{
                "path": d.REGISTRY_PATH,
                "git_blob_sha": d.REGISTRY_BLOB,
            }]
        },
    }


def claim_scope():
    meta = d.gate._manifest_leaf(manifest(), LEAF)
    scope = d.canonical_scope_definition(contract())
    epoch = "2026-10-10T15:50:00Z"
    claim = d.gate.build_claim(meta, scope, epoch=epoch)
    return {
        "schema": d.gate.CLAIM_SCOPE_SCHEMA,
        "leaf_id": LEAF,
        "root_id": ROOT_ID,
        "kind": "SEMANTIC",
        "behavior_id": d.BEHAVIOR_ID,
        "subject_kind": d.gate.SUBJECT_KIND,
        "subject_id": d.gate.SUBJECT_ID,
        "subject_sha256": d.gate.SUBJECT_SHA256,
        "leaf_acceptance": meta["acceptance"],
        "scope_definition": scope,
        "epoch": epoch,
        "claim": claim,
    }


def certificate(cs=None):
    cs = cs or claim_scope()
    cid = cs["claim"]["claim_id"]
    return {
        "schema": d.gate.CERT_SCHEMA,
        "leaf_id": cs["leaf_id"],
        "claim_id": cid,
        "claim_scope_git_blob_sha": "a" * 40,
        "scope_certificate": {
            "id": "R1_SEMANTIC_WHOLE_DOMAIN_SCOPE_V1",
            "target_scope_id": "scope://professional-quality/whole-leaf/" + cid,
            "claim_id": cid,
            "basis": "UNIVERSAL_FORMAL_SCOPE_PROOF",
            "verified": True,
            "independent": True,
            "scope_relation": "EXACT",
            "formal_completeness": True,
            "all_admissible_target_inputs_proved": True,
            "premise_set_id": "behavior-contract-domain:" + d._canon_sha(cs["scope_definition"]),
        },
        "semantic_truth_authority": False,
        "execution_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


class BehaviorContractWholeLeafDomainTests(unittest.TestCase):
    def test_exact_full_behavior_domain_passes_without_property_truth(self):
        out = d.verify_claim_scope_documents(
            manifest=manifest(),
            subject=subject(),
            registry=registry(),
            claim_scope=claim_scope(),
        )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["whole_leaf_domain_equivalence_proved"])
        self.assertFalse(out["leaf_property_truth_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_success_filtered_domain_fails_closed(self):
        cs = claim_scope()
        cs["scope_definition"]["domain_definition"]["success_or_property_filter"] = "ONLY_SUCCESSFUL_INPUTS"
        out = d.verify_claim_scope_documents(
            manifest=manifest(), subject=subject(), registry=registry(), claim_scope=cs
        )
        self.assertFalse(out["pass"])
        self.assertIn("WHOLE_DOMAIN_DEFINITION_NOT_EXACT_CANONICAL_CONTRACT_UNIVERSE", out["errors"])
        self.assertIn("SUCCESS_OR_PROPERTY_FILTER_MUST_BE_FORBIDDEN", out["errors"])

    def test_leaf_specific_inclusion_filter_fails_closed(self):
        cs = claim_scope()
        cs["scope_definition"]["domain_definition"]["inclusion_filter"] = "SUPPORTED_DOCX_ONLY"
        out = d.verify_claim_scope_documents(
            manifest=manifest(), subject=subject(), registry=registry(), claim_scope=cs
        )
        self.assertFalse(out["pass"])
        self.assertIn("DOMAIN_INCLUSION_FILTER_FORBIDDEN", out["errors"])

    def test_subject_registry_drift_fails_closed(self):
        s = subject()
        s["system_material"]["components"][0]["git_blob_sha"] = "0" * 40
        out = d.verify_claim_scope_documents(
            manifest=manifest(), subject=s, registry=registry(), claim_scope=claim_scope()
        )
        self.assertFalse(out["pass"])
        self.assertIn("SUBJECT_BEHAVIOR_REGISTRY_BLOB_STALE", out["errors"])

    def test_alternate_behavior_contract_fails_exact_scope(self):
        r = registry()
        r["active_contracted_residuals"][0]["scope"] = "narrower scope"
        out = d.verify_claim_scope_documents(
            manifest=manifest(), subject=subject(), registry=r, claim_scope=claim_scope()
        )
        self.assertFalse(out["pass"])
        self.assertIn("WHOLE_DOMAIN_DEFINITION_NOT_EXACT_CANONICAL_CONTRACT_UNIVERSE", out["errors"])

    def test_claim_substitution_fails_closed(self):
        cs = claim_scope()
        cs["claim"]["claim_id"] = "0" * 64
        out = d.verify_claim_scope_documents(
            manifest=manifest(), subject=subject(), registry=registry(), claim_scope=cs
        )
        self.assertFalse(out["pass"])
        self.assertIn("CLAIM_CONTENT_ADDRESS_MISMATCH", out["errors"])

    def test_exact_scope_certificate_passes_scope_only(self):
        cs = claim_scope()
        out = d.verify_scope_certificate_documents(
            claim_scope=cs,
            certificate=certificate(cs),
        )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["scope_cover_proved"])
        self.assertFalse(out["leaf_property_truth_authority"])
        self.assertFalse(out["quality_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_scope_certificate_cannot_use_subset_relation(self):
        cs = claim_scope()
        cert = certificate(cs)
        cert["scope_certificate"]["scope_relation"] = "SUBSET"
        out = d.verify_scope_certificate_documents(claim_scope=cs, certificate=cert)
        self.assertFalse(out["pass"])
        self.assertIn("SCOPE_RELATION_MUST_BE_EXACT", out["errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
