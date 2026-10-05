import copy
import unittest

from canonical.runtime import cross_family_residual_proof_transport_v1 as transport


class CrossFamilyResidualProofTransportV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry, cls.manifest, cls.proofs, cls.blob_errors = transport.load_documents()

    def derive(self, registry=None, manifest=None, proofs=None):
        return transport.validate_documents(
            copy.deepcopy(self.registry if registry is None else registry),
            copy.deepcopy(self.manifest if manifest is None else manifest),
            copy.deepcopy(self.proofs if proofs is None else proofs),
        )

    def test_current_exact_bytes_and_transport_pass(self):
        out = transport.derive()
        self.assertTrue(out["valid"], out)
        self.assertTrue(out["exact_blob_binding"], out)
        self.assertEqual(
            out["transports"]["TASK_TO_DELEGATION_GRAPH_001"],
            [
                "COMPLEX_MULTI_TOOL_AGENCY",
                "MULTI_CAPABILITY_COMPOSITION",
                "SUBAGENT_DELEGATION_AND_COORDINATION",
            ],
        )
        self.assertEqual(
            out["transports"]["TOOL_ROUTE_DISCOVERY_AND_SELECTION_001"],
            [
                "BUSINESS_WORKFLOW_AUTOMATION",
                "COMPLEX_MULTI_TOOL_AGENCY",
                "COMPUTER_AND_BROWSER_USE",
                "MULTI_CAPABILITY_COMPOSITION",
                "TOOL_DISCOVERY_SELECTION_AND_LEARNING",
                "UNKNOWN_DOMAIN_ADAPTATION",
            ],
        )
        self.assertEqual(
            out["transports"]["TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"],
            [
                "ADVANCED_AGENTIC_CODING",
                "AGENTIC_SCIENTIFIC_RESEARCH",
                "BUSINESS_WORKFLOW_AUTOMATION",
                "COMPLEX_MULTI_TOOL_AGENCY",
                "COMPUTER_AND_BROWSER_USE",
                "INSTRUCTION_FOLLOWING_SCOPE_AND_JUDGMENT",
                "MULTI_CAPABILITY_COMPOSITION",
                "SELF_VERIFICATION_DEBUGGING_AND_RECOVERY",
            ],
        )

    def test_source_family_must_be_single_residual(self):
        registry = copy.deepcopy(self.registry)
        registry["family_to_residual_contracts"]["SELF_VERIFICATION_DEBUGGING_AND_RECOVERY"].append(
            "ANOTHER_RESIDUAL"
        )
        out = self.derive(registry=registry)
        self.assertFalse(out["valid"])
        self.assertTrue(any(e.startswith("SOURCE_NOT_SINGLE_RESIDUAL") for e in out["errors"]))

    def test_recovery_must_be_objective_ceiling_or_floor(self):
        proofs = copy.deepcopy(self.proofs)
        proofs[transport.RECOVERY]["verified"]["objective_ceiling_or_floor"] = False
        out = self.derive(proofs=proofs)
        self.assertFalse(out["valid"])
        self.assertIn("RECOVERY_NOT_OBJECTIVE_CEILING_OR_FLOOR", out["errors"])

    def test_tool_scope_must_be_universal(self):
        proofs = copy.deepcopy(self.proofs)
        proofs[transport.TOOL_SCOPE]["verified"]["universal_scope_proved"] = False
        out = self.derive(proofs=proofs)
        self.assertFalse(out["valid"])
        self.assertIn("TOOL_UNIVERSAL_SCOPE_NOT_PROVED", out["errors"])

    def test_source_family_must_remain_currently_owned(self):
        manifest = copy.deepcopy(self.manifest)
        for family in manifest["families"]:
            if family.get("id") == "TOOL_DISCOVERY_SELECTION_AND_LEARNING":
                family["opus55_acceptance_state"] = "OPEN"
        out = self.derive(manifest=manifest)
        self.assertFalse(out["valid"])
        self.assertIn(
            "SOURCE_NOT_CURRENTLY_OWNED:TOOL_DISCOVERY_SELECTION_AND_LEARNING",
            out["errors"],
        )

    def test_delegation_must_exclude_empirical_generalization(self):
        proofs = copy.deepcopy(self.proofs)
        proofs[transport.DELEGATION_SCOPE]["verified"] = [
            x
            for x in proofs[transport.DELEGATION_SCOPE]["verified"]
            if x != "NO_EMPIRICAL_GENERALIZATION"
        ]
        out = self.derive(proofs=proofs)
        self.assertFalse(out["valid"])
        self.assertIn("DELEGATION_EMPIRICAL_GENERALIZATION_NOT_EXCLUDED", out["errors"])


if __name__ == "__main__":
    unittest.main()
