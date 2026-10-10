from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import regcap_definite_buffer_reference_v1 as ref
from canonical.runtime import regcap_buffer_reference_truth_certificate_v1 as cert
from canonical.runtime import regcap_necessary_property_authority_v1 as regcap
from canonical.runtime import semantic_truth_dispatch_v1 as dispatch


def fake_surface_check(**_kwargs):
    return (
        {"normalized_registry": {"concepts": []}},
        {"pass": True, "receipt_sha256": "a" * 64},
        None,
    )


def locate(text, surface="the buffer"):
    start = text.casefold().index(surface.casefold())
    return start, start + len(surface)


def selected(concept):
    return {
        "pass": True,
        "status": "PASS__UNIQUE_LOCAL_BUFFER_REFERENCE_IDENTITY",
        "selected_concept_id": concept,
        "reference_identity_authority": True,
        "semantic_truth_authority": True,
        "terminal_authority": False,
    }


class Tests(unittest.TestCase):
    def test_unique_prior_ccyb_resolves_the_buffer(self):
        text = "CCyB increased. The buffer was later released."
        start, end = locate(text)
        with patch.object(ref, "_registry_surface_check", side_effect=fake_surface_check):
            out = ref.resolve_reference(
                text, source_id="doc:A", start=start, end=end
            )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["selected_concept_id"], regcap.CCYB)
        self.assertTrue(out["reference_identity_authority"])
        self.assertFalse(out["global_alias_authority"])

    def test_unique_prior_ccob_same_sentence_resolves(self):
        text = "The capital conservation buffer remained stable and the buffer absorbed losses."
        start, end = locate(text)
        with patch.object(ref, "_registry_surface_check", side_effect=fake_surface_check):
            out = ref.resolve_reference(
                text, source_id="doc:A", start=start, end=end
            )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["selected_concept_id"], regcap.CCOB)

    def test_two_distinct_prior_buffer_concepts_preserve_ambiguity(self):
        text = "CCoB was stable. CCyB increased. The buffer was later released."
        start, end = locate(text)
        with patch.object(ref, "_registry_surface_check", side_effect=fake_surface_check):
            out = ref.resolve_reference(
                text, source_id="doc:A", start=start, end=end
            )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNRESOLVED__MULTIPLE_AUTHENTICATED_BUFFER_ANTECEDENTS",
        )
        self.assertEqual(
            set(out["candidate_concept_ids"]),
            {regcap.CCOB, regcap.CCYB},
        )
        self.assertTrue(out["ambiguity_preserved"])

    def test_nearest_does_not_override_two_distinct_candidates(self):
        text = "CCoB and then CCyB were discussed; CCyB was nearer. The buffer changed."
        start, end = locate(text)
        with patch.object(ref, "_registry_surface_check", side_effect=fake_surface_check):
            out = ref.resolve_reference(
                text, source_id="doc:A", start=start, end=end
            )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNRESOLVED__MULTIPLE_AUTHENTICATED_BUFFER_ANTECEDENTS",
        )

    def test_multiple_mentions_of_same_concept_still_resolve(self):
        text = "CCyB was raised and the countercyclical capital buffer stayed active. The buffer was released."
        start, end = locate(text)
        with patch.object(ref, "_registry_surface_check", side_effect=fake_surface_check):
            out = ref.resolve_reference(
                text, source_id="doc:A", start=start, end=end
            )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["selected_concept_id"], regcap.CCYB)

    def test_no_prior_authenticated_buffer_is_unresolved(self):
        text = "The buffer was released."
        start, end = locate(text)
        with patch.object(ref, "_registry_surface_check", side_effect=fake_surface_check):
            out = ref.resolve_reference(
                text, source_id="doc:A", start=start, end=end
            )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNRESOLVED__NO_AUTHENTICATED_PRIOR_BUFFER_ANTECEDENT",
        )

    def test_later_concept_mention_is_not_antecedent(self):
        text = "The buffer was released. CCyB was discussed later."
        start, end = locate(text)
        with patch.object(ref, "_registry_surface_check", side_effect=fake_surface_check):
            out = ref.resolve_reference(
                text, source_id="doc:A", start=start, end=end
            )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNRESOLVED__NO_AUTHENTICATED_PRIOR_BUFFER_ANTECEDENT",
        )

    def test_two_sentences_back_is_outside_bound_scope(self):
        text = "CCoB was discussed. Noise happened. CCyB increased. The buffer was released."
        start, end = locate(text)
        with patch.object(ref, "_registry_surface_check", side_effect=fake_surface_check):
            out = ref.resolve_reference(
                text, source_id="doc:A", start=start, end=end
            )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["selected_concept_id"], regcap.CCYB)
        self.assertNotIn(regcap.CCOB, out["candidate_concept_ids"])

    def test_this_buffer_is_outside_exact_reference_scope(self):
        text = "CCyB increased. This buffer was released."
        start, end = locate(text, "This buffer")
        with patch.object(ref, "_registry_surface_check", side_effect=fake_surface_check):
            out = ref.resolve_reference(
                text, source_id="doc:A", start=start, end=end
            )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNRESOLVED__REFERENCE_FORM_OUTSIDE_BOUND_SCOPE",
        )

    def test_truth_certificate_proves_matching_local_reference_true(self):
        text = "CCyB increased. The buffer was later released."
        start, end = locate(text)
        with patch.object(
            cert.reference,
            "resolve_reference",
            return_value=selected(regcap.CCYB),
        ):
            out = cert.evaluate({
                "truth_kind": cert.TRUTH_KIND,
                "predicate_id": "caller",
                "source_text": text,
                "source_id": "doc:A",
                "start": start,
                "end": end,
                "target_concept_id": regcap.CCYB,
            })
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "TRUE")
        self.assertTrue(out["reference_identity_authority"])
        self.assertFalse(out["global_identity_authority"])

    def test_different_proved_reference_identity_is_unknown_not_false(self):
        text = "CCyB increased. The buffer was later released."
        start, end = locate(text)
        with patch.object(
            cert.reference,
            "resolve_reference",
            return_value=selected(regcap.CCYB),
        ):
            out = cert.evaluate({
                "truth_kind": cert.TRUTH_KIND,
                "predicate_id": "caller",
                "source_text": text,
                "source_id": "doc:A",
                "start": start,
                "end": end,
                "target_concept_id": regcap.CCOB,
            })
        self.assertFalse(out["pass"])
        self.assertEqual(out["predicate_truth"], "UNKNOWN")
        self.assertEqual(
            out["status"],
            "UNKNOWN__DIFFERENT_LOCAL_REFERENCE_IDENTITY",
        )

    def test_dispatcher_routes_buffer_reference_identity(self):
        expected = {"pass": True, "predicate_truth": "TRUE"}
        with patch.object(
            dispatch,
            "evaluate_regcap_buffer_reference",
            return_value=expected,
        ) as fn:
            out = dispatch.evaluate({
                "truth_kind": "REGCAP_BUFFER_REFERENCE_IDENTITY",
                "predicate_id": "x",
            })
        self.assertEqual(out, expected)
        fn.assert_called_once()

    def test_no_global_or_terminal_authority(self):
        text = "CCyB increased. The buffer was later released."
        start, end = locate(text)
        with patch.object(ref, "_registry_surface_check", side_effect=fake_surface_check):
            out = ref.resolve_reference(
                text, source_id="doc:A", start=start, end=end
            )
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["global_alias_authority"])
        self.assertFalse(out["open_world_coreference_complete"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
