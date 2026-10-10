from __future__ import annotations
import json
from pathlib import Path
import unittest

from canonical.runtime import professional_quality_scoped_evidence_v1 as v

ROOT=Path(__file__).resolve().parents[2]


def load(rel):
    return json.loads((ROOT/rel).read_text())


class FactoredR10RegistryAdmissionTests(unittest.TestCase):
    def test_factored_receipt_admitted_by_r10_validator(self):
        registry=load("canonical/governance/PROFESSIONAL_QUALITY_SCOPED_EVIDENCE_REGISTRY_20261010_V1.json")
        entry=next(x for x in registry["entries"] if x["scope_id"]=="PQ::R10::DECISION_SUFFICIENCY::LOSSLESS_MINIMUM_INFORMATION")
        source=load(entry["source_receipt"]["path"])
        history=load(entry["compiler_verification"]["path"])
        errors, scope=v._validate_r10(
            entry,source,history,entry["reusable_compiler"]["git_blob_sha"]
        )
        self.assertEqual(errors,[],errors)
        self.assertEqual(scope["kind"],v.R10_KIND)
        self.assertIn("PROVIDERS_CANNOT_MUTATE_VERIFICATION_AUTHORITY",scope["guarantees"])
        self.assertIn("NO_GLOBAL_R10_LEAF_OR_ROOT_CLOSURE",scope["limitations"])

    def test_factored_receipt_requires_exact_equivalence(self):
        registry=load("canonical/governance/PROFESSIONAL_QUALITY_SCOPED_EVIDENCE_REGISTRY_20261010_V1.json")
        entry=next(x for x in registry["entries"] if x["scope_id"]=="PQ::R10::DECISION_SUFFICIENCY::LOSSLESS_MINIMUM_INFORMATION")
        source=load(entry["source_receipt"]["path"])
        history=load(entry["compiler_verification"]["path"])
        source["replay"]["decision_contract_output_exact_equal"]=False
        errors,_=v._validate_r10(entry,source,history,entry["reusable_compiler"]["git_blob_sha"])
        self.assertIn("SOURCE_FACTORED_REPLAY_INVALID",errors)

    def test_factored_receipt_cannot_switch_predecessor(self):
        registry=load("canonical/governance/PROFESSIONAL_QUALITY_SCOPED_EVIDENCE_REGISTRY_20261010_V1.json")
        entry=next(x for x in registry["entries"] if x["scope_id"]=="PQ::R10::DECISION_SUFFICIENCY::LOSSLESS_MINIMUM_INFORMATION")
        source=load(entry["source_receipt"]["path"])
        history=load(entry["compiler_verification"]["path"])
        source["exact_blobs"]["predecessor_runtime"]="0"*40
        errors,_=v._validate_r10(entry,source,history,entry["reusable_compiler"]["git_blob_sha"])
        self.assertIn("SOURCE_PREDECESSOR_RUNTIME_MISMATCH",errors)


if __name__=="__main__":
    unittest.main()
