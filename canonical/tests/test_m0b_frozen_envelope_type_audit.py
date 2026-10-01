import json
import unittest
from canonical.runtime.m0b_frozen_envelope_type_audit import validate

SUPPORTED={
    "aggregate","selection","entity_reconciliation","hierarchy_closure",
    "geometry_reconstruction","numeric_formula","artifact","state_transition",
    "measurement_calibration","signal_correction","method_model_selection"
}

def registry(ids):
    return {"active_contracted_residuals":[{"behavior_id":x} for x in ids]}

def bindings(ids):
    return {
        "schema":"PROJECT_BRAIN_M0B_FROZEN_ENVELOPE_TYPE_BINDINGS_V1",
        "supported_transform_kinds":sorted(SUPPORTED),
        "bindings":[{"behavior_id":x,"transform_kinds":["selection"],"basis":"explicit frozen mapping"} for x in ids],
    }

class Tests(unittest.TestCase):
    def test_exact_cover_passes(self):
        self.assertEqual(validate(registry(["A","B"]),bindings(["A","B"]),SUPPORTED),[])

    def test_missing_behavior_fails(self):
        e=validate(registry(["A","B"]),bindings(["A"]),SUPPORTED)
        self.assertIn("FROZEN_BEHAVIOR_UNTYPED:B",e)

    def test_extra_behavior_fails(self):
        e=validate(registry(["A"]),bindings(["A","B"]),SUPPORTED)
        self.assertIn("NONREGISTRY_BEHAVIOR_BOUND:B",e)

    def test_unknown_kind_fails(self):
        b=bindings(["A"]); b["bindings"][0]["transform_kinds"]=["mystery"]
        e=validate(registry(["A"]),b,SUPPORTED)
        self.assertTrue(any(x.startswith("UNSUPPORTED_TRANSFORM_KIND:A:") for x in e))

    def test_duplicate_binding_fails(self):
        b=bindings(["A"]); b["bindings"].append(dict(b["bindings"][0]))
        e=validate(registry(["A"]),b,SUPPORTED)
        self.assertIn("BINDING_BEHAVIOR_ID_DUPLICATE:A",e)

    def test_registry_drift_fails_closed(self):
        b=bindings(["A"])
        e=validate(registry(["A","NEW"]),b,SUPPORTED)
        self.assertIn("FROZEN_BEHAVIOR_UNTYPED:NEW",e)

if __name__=="__main__":
    unittest.main()
