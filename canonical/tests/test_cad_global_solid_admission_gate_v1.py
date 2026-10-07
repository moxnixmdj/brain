import unittest
from canonical.runtime.cad_global_solid_admission_gate_v1 import verify, CADAdmissionError, REQUIRED_GLOBAL_CATEGORIES

H="a"*64
C="b"*64

def receipt(**kw):
    x={"independent_or_objective":True,"drawing_bound":True,"candidate_bound":True,
       "drawing_sha256":H,"candidate_sha256":C}
    x.update(kw); return x

def fixture():
    contract={
      "scope_complete":True,
      "drawing_sha256":H,
      "required_views":["TOP","FRONT","SIDE","SECTION_AA"],
      "global_categories":sorted(REQUIRED_GLOBAL_CATEGORIES),
      "topology":{"scope_complete":True,"expected_euler":-6},
    }
    candidate={
      "candidate_sha256":C,
      "watertight":True,
      "one_connected_solid":True,
      "view_receipts":{v:receipt(global_envelope_match=True) for v in contract["required_views"]},
      "global_receipts":{g:receipt(status="PROVED_MATCH",match=True) for g in contract["global_categories"]},
      "topology_receipt":receipt(observed_euler=-6),
    }
    return contract,candidate

class T(unittest.TestCase):
    def test_complete_global_certificate_passes(self):
        c,x=fixture()
        y=verify(c,x)
        self.assertTrue(y["pass"])
        self.assertEqual(y["global_category_count"],6)

    def test_local_only_fails_closed(self):
        c,x=fixture()
        x["view_receipts"]={}
        x["global_receipts"]={}
        with self.assertRaises(CADAdmissionError):
            verify(c,x)

    def test_spent_extra_handle_regression_fails(self):
        c,x=fixture()
        x["topology_receipt"]["observed_euler"]=-8
        with self.assertRaisesRegex(CADAdmissionError,"TOPOLOGY_EULER_MISMATCH"):
            verify(c,x)

    def test_missing_view_fails(self):
        c,x=fixture()
        del x["view_receipts"]["SECTION_AA"]
        with self.assertRaisesRegex(CADAdmissionError,"VIEW_RECEIPT_SET_MISMATCH"):
            verify(c,x)

    def test_missing_global_category_fails(self):
        c,x=fixture()
        c["global_categories"].remove("PRINCIPAL_INERTIA")
        x["global_receipts"].pop("PRINCIPAL_INERTIA")
        with self.assertRaisesRegex(CADAdmissionError,"GLOBAL_CATEGORY_CONTRACT_INCOMPLETE"):
            verify(c,x)

    def test_unproved_derivative_fails(self):
        c,x=fixture()
        x["global_receipts"]["GLOBAL_VOLUME"].update(status="PROVED_DERIVATIVE",match=None,derivation_proved=False)
        with self.assertRaisesRegex(CADAdmissionError,"DERIVATION_UNPROVED"):
            verify(c,x)

if __name__=="__main__":
    unittest.main(verbosity=2)
