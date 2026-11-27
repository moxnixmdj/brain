from __future__ import annotations

import copy
import unittest

from canonical.verification.composition_p2_ingress_only_reducer_v1 import (
    SCHEMA,
    reduce_certificate,
)

H40 = "a" * 40
H64 = "b" * 64


def valid_certificate():
    return {
        "schema": SCHEMA,
        "exact_scope_id": "FROZEN_COMPOSITION_MATCHED_PORTFOLIO_V1",
        "runtime_scope_sha": H40,
        "verified_initial_inputs_content_bound": True,
        "external_nondeterminism_is_evidence_ingress": True,
        "runtime_route_totality": {
            "all_admissible_composition_macrosteps_use_declared_action_types": True,
            "capsule_v2_no_bypass": True,
            "action_type_set_complete": True,
            "independent_scope_receipt_sha": H64,
        },
        "action_types": [
            {
                "action_type": "pure_transform",
                "class": "PURE",
                "implementation_blob_sha": H40,
                "independent_receipt_sha": H64,
                "capsule_v2_bound": True,
                "output_lineage_binds_exact_action_result": True,
                "no_external_evidence_reads": True,
            },
            {
                "action_type": "evidence_ingress",
                "class": "INGRESS",
                "implementation_blob_sha": H40,
                "independent_receipt_sha": H64,
                "capsule_v2_bound": True,
                "output_lineage_binds_exact_action_result": True,
                "external_evidence_input_totality": True,
                "source_identity_content_bound": True,
                "payload_content_bound": True,
                "no_unreturned_load_bearing_evidence": True,
            },
        ],
    }


class Tests(unittest.TestCase):
    def test_valid_certificate_reduces_p2(self):
        out = reduce_certificate(valid_certificate())
        self.assertTrue(out["p2_load_bearing_provenance_completeness"], out)
        self.assertEqual(out["ingress_action_types"], ["evidence_ingress"])
        self.assertEqual(out["pure_action_types"], ["pure_transform"])
        self.assertEqual(out["acceptance_credit_delta"], 0)

    def test_each_global_boolean_fails_closed(self):
        paths = [
            ("verified_initial_inputs_content_bound",),
            ("external_nondeterminism_is_evidence_ingress",),
            ("runtime_route_totality", "all_admissible_composition_macrosteps_use_declared_action_types"),
            ("runtime_route_totality", "capsule_v2_no_bypass"),
            ("runtime_route_totality", "action_type_set_complete"),
        ]
        for path in paths:
            cert = valid_certificate()
            target = cert
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = False
            out = reduce_certificate(cert)
            self.assertFalse(out["p2_load_bearing_provenance_completeness"], (path, out))

    def test_each_action_class_obligation_fails_closed(self):
        pure_keys = [
            "capsule_v2_bound",
            "output_lineage_binds_exact_action_result",
            "no_external_evidence_reads",
        ]
        ingress_keys = [
            "capsule_v2_bound",
            "output_lineage_binds_exact_action_result",
            "external_evidence_input_totality",
            "source_identity_content_bound",
            "payload_content_bound",
            "no_unreturned_load_bearing_evidence",
        ]
        for index, keys in ((0, pure_keys), (1, ingress_keys)):
            for key in keys:
                cert = valid_certificate()
                cert["action_types"][index][key] = False
                out = reduce_certificate(cert)
                self.assertFalse(
                    out["p2_load_bearing_provenance_completeness"],
                    (index, key, out),
                )

    def test_unknown_or_duplicate_action_types_fail_closed(self):
        cert = valid_certificate()
        cert["action_types"][0]["class"] = "MAYBE"
        self.assertFalse(
            reduce_certificate(cert)["p2_load_bearing_provenance_completeness"]
        )

        cert = valid_certificate()
        cert["action_types"][1]["action_type"] = cert["action_types"][0]["action_type"]
        self.assertFalse(
            reduce_certificate(cert)["p2_load_bearing_provenance_completeness"]
        )

    def test_missing_or_bad_content_hash_fails_closed(self):
        cert = valid_certificate()
        cert["runtime_scope_sha"] = "not-a-hash"
        self.assertFalse(
            reduce_certificate(cert)["p2_load_bearing_provenance_completeness"]
        )
        cert = valid_certificate()
        cert["action_types"][1].pop("independent_receipt_sha")
        self.assertFalse(
            reduce_certificate(cert)["p2_load_bearing_provenance_completeness"]
        )

    def test_mutating_ingress_to_hide_evidence_fails_closed(self):
        cert = valid_certificate()
        cert["action_types"][1]["no_unreturned_load_bearing_evidence"] = False
        out = reduce_certificate(cert)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertFalse(out["p2_load_bearing_provenance_completeness"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
