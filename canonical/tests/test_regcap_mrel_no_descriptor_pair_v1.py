from __future__ import annotations
import unittest
from canonical.runtime import regcap_mrel_no_descriptor_pair_v1 as nd
from canonical.runtime import regcap_mrel_pair_discriminator_v1 as pair
from canonical.runtime import regcap_necessary_property_authority_v1 as regcap
from canonical.runtime import mrel_necessary_property_authority_v1 as mrel

def fake_projection(pack):
    return {"pass":True,"receipt":{"fragment_ids":sorted(str(x["fragment_id"]) for x in pack.get("fragments",[])),"receipt_sha256":"a"*64},"source_fragment_authority":True,"terminal_authority":False}

class Tests(unittest.TestCase):
    def test_ccob_no_descriptor_selects_ccob(self):
        text="The cushion is 2.5% CET1 above the regulatory minimum."
        out=nd.resolve_relative(text,source_id="doc:c",pair_id=pair.CCOB_MREL,candidate_concept_ids=[regcap.CCOB,mrel.MREL],projection_verifier=fake_projection)
        self.assertTrue(out["pass"],out); self.assertEqual(out["selected_concept_id"],regcap.CCOB)

    def test_ccyb_no_descriptor_selects_ccyb(self):
        text="The cushion is released when system-wide risk crystallises or dissipates."
        out=nd.resolve_relative(text,source_id="doc:y",pair_id=pair.CCYB_MREL,candidate_concept_ids=[regcap.CCYB,mrel.MREL],projection_verifier=fake_projection)
        self.assertTrue(out["pass"],out); self.assertEqual(out["selected_concept_id"],regcap.CCYB)

    def test_mrel_no_descriptor_selects_mrel_against_ccob(self):
        text="The minimum requirement for own funds and eligible liabilities shall be determined by the resolution authority under Article 45c."
        out=nd.resolve_relative(text,source_id="doc:m1",pair_id=pair.CCOB_MREL,candidate_concept_ids=[regcap.CCOB,mrel.MREL],projection_verifier=fake_projection)
        self.assertTrue(out["pass"],out); self.assertEqual(out["selected_concept_id"],mrel.MREL)

    def test_mrel_no_descriptor_selects_mrel_against_ccyb(self):
        text="The minimum requirement for own funds and eligible liabilities shall be determined by the resolution authority under Article 45c."
        out=nd.resolve_relative(text,source_id="doc:m2",pair_id=pair.CCYB_MREL,candidate_concept_ids=[regcap.CCYB,mrel.MREL],projection_verifier=fake_projection)
        self.assertTrue(out["pass"],out); self.assertEqual(out["selected_concept_id"],mrel.MREL)

    def test_shared_generic_text_stays_open(self):
        out=nd.resolve_relative("The requirement absorbs losses.",source_id="doc:o",pair_id=pair.CCOB_MREL,candidate_concept_ids=[regcap.CCOB,mrel.MREL],projection_verifier=fake_projection)
        self.assertFalse(out["pass"]); self.assertEqual(out["status"],"OPEN__NO_BOUND_NO_DESCRIPTOR_PAIR_CONTEXT_SIGNATURE")

    def test_mixed_markers_fail_closed(self):
        text="The cushion is 2.5% CET1 above the regulatory minimum. The minimum requirement for own funds and eligible liabilities shall be determined by the resolution authority under Article 45c."
        out=nd.compile_context(text,source_id="doc:x",pair_id=pair.CCOB_MREL)
        self.assertFalse(out["pass"]); self.assertEqual(out["status"],"FAIL_CLOSED")

    def test_wrong_pair_fails_closed(self):
        out=nd.resolve_relative("The cushion is released when system-wide risk crystallises or dissipates.",source_id="doc:b",pair_id=pair.CCYB_MREL,candidate_concept_ids=[regcap.CCOB,mrel.MREL],projection_verifier=fake_projection)
        self.assertFalse(out["pass"]); self.assertEqual(out["reason"],"CANDIDATE_SET_MUST_EQUAL_BOUND_PAIR")

    def test_source_authority_failure_fails_closed(self):
        out=nd.resolve_relative("The cushion is 2.5% CET1 above the regulatory minimum.",source_id="doc:c",pair_id=pair.CCOB_MREL,candidate_concept_ids=[regcap.CCOB,mrel.MREL],projection_verifier=lambda _p:{"pass":False})
        self.assertFalse(out["pass"]); self.assertEqual(out["status"],"FAIL_CLOSED")

    def test_no_global_or_terminal_authority(self):
        out=nd.resolve_relative("The cushion is released when system-wide risk crystallises or dissipates.",source_id="doc:y",pair_id=pair.CCYB_MREL,candidate_concept_ids=[regcap.CCYB,mrel.MREL],projection_verifier=fake_projection)
        self.assertTrue(out["pass"],out)
        self.assertFalse(out["global_semantic_identity_authority"]); self.assertFalse(out["terminal_authority"]); self.assertEqual(out["terminal_credit_delta"],0)

if __name__=="__main__": unittest.main(verbosity=2)
