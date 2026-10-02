import unittest
from canonical.runtime.acceptance_capability_source_gate_v2 import evaluate

def owned_no_model():
    return {
        "benchmark_harness_zero_cost": True,
        "scorer_frozen": True,
        "brain_candidate_bound": True,
        "brain_owned_operative_configuration": True,
        "configuration_materially_constrains_execution": True,
        "capability_package_contains_configuration": True,
        "promotion_evaluates_brain_configured_system": True,
        "external_hidden_target_capability_provider": False,
        "ownership_claim_relies_on_model_standalone_superiority": False,
        "future_use_requires_capability_rediscovery": False,
        "model_role": "NONE",
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }

class Tests(unittest.TestCase):
    def test_owned_no_model_route_passes(self):
        out=evaluate(owned_no_model())
        self.assertTrue(out["pass"],out)

    def test_owned_general_substrate_route_passes(self):
        route=owned_no_model()
        route.update({
            "model_role":"GENERAL_COGNITION_SUBSTRATE",
            "model_dependency_count":1,
            "model_dependencies_declared":True,
            "general_substrate_test_pass":True,
        })
        out=evaluate(route)
        self.assertTrue(out["pass"],out)

    def test_hidden_target_capability_provider_blocks(self):
        route=owned_no_model()
        route.update({
            "model_role":"GENERAL_COGNITION_SUBSTRATE",
            "model_dependency_count":1,
            "model_dependencies_declared":True,
            "general_substrate_test_pass":False,
            "external_hidden_target_capability_provider":True,
        })
        out=evaluate(route)
        self.assertFalse(out["pass"])
        self.assertIn("HIDDEN_TARGET_CAPABILITY_PROVIDER_NOT_ZERO",out["errors"])
        self.assertIn("GENERAL_SUBSTRATE_TEST_NOT_PROVEN",out["errors"])

    def test_model_presence_alone_does_not_block(self):
        route=owned_no_model()
        route.update({
            "model_role":"GENERAL_COGNITION_SUBSTRATE",
            "model_dependency_count":2,
            "model_dependencies_declared":True,
            "general_substrate_test_pass":True,
        })
        out=evaluate(route)
        self.assertTrue(out["pass"],out)

    def test_unclassified_model_role_fails_closed(self):
        route=owned_no_model()
        route["model_role"]="UNKNOWN"
        route["model_dependency_count"]=1
        out=evaluate(route)
        self.assertFalse(out["pass"])
        self.assertIn("MODEL_ROLE_UNCLASSIFIED",out["errors"])

    def test_provider_routing_only_configuration_blocks(self):
        route=owned_no_model()
        route["configuration_materially_constrains_execution"]=False
        route["external_hidden_target_capability_provider"]=True
        out=evaluate(route)
        self.assertFalse(out["pass"])
        self.assertIn("CONFIGURATION_MATERIAL_CONTROL_NOT_PROVEN",out["errors"])

    def test_nonzero_spend_blocks(self):
        route=owned_no_model()
        route["incremental_spend_usd"]=0.01
        out=evaluate(route)
        self.assertFalse(out["pass"])
        self.assertIn("INCREMENTAL_SPEND_NOT_ZERO",out["errors"])

if __name__=="__main__":
    unittest.main(verbosity=2)
