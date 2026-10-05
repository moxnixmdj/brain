import math
import unittest

from canonical.runtime import h100_representation_invariant_accounting_v1 as a

class H100RepresentationInvariantAccountingTests(unittest.TestCase):
    def test_arbitrary_bytes_roundtrip_through_deterministic_source(self):
        payload = bytes(range(256)) * 16
        source = a.encode_payload_as_deterministic_source(payload)
        self.assertEqual(a.recover_payload_from_deterministic_source(source), payload)

    def test_legacy_rule_can_hide_arbitrary_payload(self):
        payload = bytes(range(256)) * 16
        source = a.encode_payload_as_deterministic_source(payload)
        self.assertGreater(len(source), len(payload))
        self.assertEqual(
            a.legacy_extension_based_learned_bytes(
                artifact_kind="DETERMINISTIC_PROGRAM",
                stored_bytes=len(source),
            ),
            0,
        )

    def test_provenance_survives_lossless_reencoding(self):
        original = a.Provenance(
            artifact_id="weights.bin",
            persisted_after_exposure=True,
            value_selected_using_capability_evidence=True,
        )
        source = a.Provenance(
            artifact_id="weights_as_source.py",
            persisted_after_exposure=True,
            value_selected_using_capability_evidence=False,
            lossless_transform_of_learned_artifact=True,
            source_artifact_id="weights.bin",
        )
        self.assertTrue(original.learned)
        self.assertTrue(source.learned)

    def test_uniform_three_way_post_data_selector_is_nonzero(self):
        self.assertAlmostEqual(a.uniform_selection_information_bits(3), math.log2(3))
        self.assertEqual(a.finite_selector_storage_bytes(3), 1)

    def test_preexposure_fixed_algorithm_has_zero_postexposure_information(self):
        p = a.Provenance(
            artifact_id="generic_solver.py",
            persisted_after_exposure=False,
            value_selected_using_capability_evidence=False,
        )
        c = a.representation_invariant_certificate(
            semantic_payload_bytes=1000,
            prior_probability=1/3,
            provenance=p,
        )
        self.assertFalse(c["learned"])
        self.assertEqual(c["semantic_payload_bytes"], 0)
        self.assertEqual(c["selection_information_bits"], 0.0)

    def test_lossless_reencoding_preserves_selection_information(self):
        prior = 1/7
        original = a.Provenance(
            artifact_id="selected.bin",
            persisted_after_exposure=True,
            value_selected_using_capability_evidence=True,
        )
        recoded = a.Provenance(
            artifact_id="selected.py",
            persisted_after_exposure=True,
            value_selected_using_capability_evidence=False,
            lossless_transform_of_learned_artifact=True,
            source_artifact_id="selected.bin",
        )
        c1 = a.representation_invariant_certificate(
            semantic_payload_bytes=64,
            prior_probability=prior,
            provenance=original,
        )
        c2 = a.representation_invariant_certificate(
            semantic_payload_bytes=64,
            prior_probability=prior,
            provenance=recoded,
        )
        self.assertAlmostEqual(c1["selection_information_bits"], c2["selection_information_bits"])
        self.assertTrue(c1["learned"] and c2["learned"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
