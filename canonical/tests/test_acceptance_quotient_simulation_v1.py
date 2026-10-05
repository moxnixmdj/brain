from __future__ import annotations

import unittest

from canonical.runtime.acceptance_quotient_simulation_v1 import (
    verify_acceptance_quotient_certificate,
)


def base():
    return {
        "target_states": ["T0", "T1", "T2"],
        "brain_states": ["B0", "B1", "B2"],
        "initial_target_states": ["T0"],
        "initial_brain_states": ["B0"],
        "terminal_target_states": ["T2"],
        "terminal_brain_states": ["B2"],
        "relation": [["T0", "B0"], ["T1", "B1"], ["T2", "B2"]],
        "target_cut_edges": [
            {"id": "E01", "from": "T0", "to": "T1"},
            {"id": "E12", "from": "T1", "to": "T2"},
        ],
        "brain_macro_edges": [
            {
                "from": "B0",
                "to": "B1",
                "covers_target_edge_ids": ["E01"],
                "scope_authority_invariant": True,
                "realizability_receipt": {
                    "path": "canonical/verification/r0.json",
                    "git_blob_sha": "0123456789abcdef0123456789abcdef01234567",
                    "scope_complete": True,
                    "universal_from_abstract_class": True,
                    "independent_or_objective": True,
                },
            },
            {
                "from": "B1",
                "to": "B2",
                "covers_target_edge_ids": ["E12"],
                "scope_authority_invariant": True,
                "realizability_receipt": {
                    "path": "canonical/verification/r1.json",
                    "git_blob_sha": "1123456789abcdef0123456789abcdef01234567",
                    "scope_complete": True,
                    "universal_from_abstract_class": True,
                    "independent_or_objective": True,
                },
            },
        ],
        "abstraction_receipt": {
            "path": "canonical/verification/abstraction.json",
            "git_blob_sha": "2123456789abcdef0123456789abcdef01234567",
            "acceptance_complete": True,
            "load_bearing_observations_complete": True,
            "target_conservative_coverage": True,
            "independent_or_objective": True,
        },
    }


class Tests(unittest.TestCase):
    def test_pass(self):
        self.assertEqual(verify_acceptance_quotient_certificate(base())["status"], "PASS")

    def test_lossy_abstraction(self):
        cert = base()
        cert["abstraction_receipt"]["acceptance_complete"] = False
        verdict = verify_acceptance_quotient_certificate(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("ACCEPTANCE_COMPLETE_NOT_TRUE", verdict["reason"])

    def test_missing_load_bearing(self):
        cert = base()
        cert["abstraction_receipt"]["load_bearing_observations_complete"] = False
        self.assertEqual(verify_acceptance_quotient_certificate(cert)["status"], "FAIL_CLOSED")

    def test_spurious_edge(self):
        cert = base()
        cert["brain_macro_edges"][0]["realizability_receipt"]["universal_from_abstract_class"] = False
        verdict = verify_acceptance_quotient_certificate(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("UNIVERSAL_FROM_ABSTRACT_CLASS_NOT_TRUE", verdict["reason"])

    def test_scope_invariant(self):
        cert = base()
        cert["brain_macro_edges"][1]["scope_authority_invariant"] = False
        verdict = verify_acceptance_quotient_certificate(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("SCOPE_AUTHORITY_INVARIANT_NOT_TRUE", verdict["reason"])

    def test_missing_match(self):
        cert = base()
        cert["brain_macro_edges"] = cert["brain_macro_edges"][:1]
        verdict = verify_acceptance_quotient_certificate(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("LOCAL_QUOTIENT_SIMULATION_MISSING", verdict["reason"])

    def test_terminal(self):
        cert = base()
        cert["terminal_brain_states"] = ["B1"]
        verdict = verify_acceptance_quotient_certificate(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("TERMINAL_PRESERVATION_MISSING", verdict["reason"])

    def test_initial(self):
        cert = base()
        cert["relation"] = [["T1", "B1"], ["T2", "B2"]]
        verdict = verify_acceptance_quotient_certificate(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("INITIALIZATION_UNSATISFIED", verdict["reason"])

    def test_unreachable_bad_pair_ignored(self):
        cert = base()
        cert["target_states"].append("TX")
        cert["brain_states"].append("BX")
        cert["relation"].append(["TX", "BX"])
        self.assertEqual(verify_acceptance_quotient_certificate(cert)["status"], "PASS")


if __name__ == "__main__":
    unittest.main(verbosity=2)
