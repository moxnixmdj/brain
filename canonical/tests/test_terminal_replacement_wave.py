from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from canonical.runtime import terminal_replacement_wave as wave


class TerminalReplacementWaveTests(unittest.TestCase):
    def test_required_active_contract_universe_is_exactly_twelve(self):
        self.assertEqual(len(wave.REQUIRED_ACTIVE_CONTRACTS), 12)
        self.assertEqual(len(set(wave.REQUIRED_ACTIVE_CONTRACTS)), 12)
        self.assertIn("CAD_DRAWING_TO_GLOBAL_SOLID_TOPOLOGY_AND_ENVELOPE_001", wave.REQUIRED_ACTIVE_CONTRACTS)
        self.assertIn("SA_CCR_CREDIT_EFFECTIVE_NOTIONAL_AND_ADDON_001", wave.REQUIRED_ACTIVE_CONTRACTS)

    def test_current_implementation_coverage_fails_closed_on_missing_two(self):
        coverage = wave.contract_coverage()
        self.assertFalse(coverage["pass"])
        self.assertEqual(
            coverage["missing"],
            [
                "CAD_DRAWING_TO_GLOBAL_SOLID_TOPOLOGY_AND_ENVELOPE_001",
                "SA_CCR_CREDIT_EFFECTIVE_NOTIONAL_AND_ADDON_001",
            ],
        )
        self.assertEqual(coverage["unexpected"], [])

    def test_seed_binding_is_deterministic_and_commit_sensitive(self):
        a = wave.derive_seed("pkg-a", "beacon-1", "C::slot::00")
        self.assertEqual(a, wave.derive_seed("pkg-a", "beacon-1", "C::slot::00"))
        self.assertNotEqual(a, wave.derive_seed("pkg-b", "beacon-1", "C::slot::00"))
        self.assertNotEqual(a, wave.derive_seed("pkg-a", "beacon-2", "C::slot::00"))

    def test_terminal_execution_refuses_before_generating_any_case_when_contracts_missing(self):
        with tempfile.TemporaryDirectory() as td, \
             mock.patch.object(wave.c_suite, "generate_case") as c_generate, \
             mock.patch.object(wave.r_suite, "generate_case") as r_generate:
            with self.assertRaisesRegex(ValueError, "TERMINAL_CONTRACT_COVERAGE_INCOMPLETE"):
                wave.execute(
                    candidate_package_commitment="pkg",
                    post_freeze_beacon="beacon",
                    repo_root=Path(td),
                )
            c_generate.assert_not_called()
            r_generate.assert_not_called()

    def test_terminal_execution_refuses_when_prequalification_is_not_authorized(self):
        with tempfile.TemporaryDirectory() as td, \
             mock.patch.object(wave, "CONTRACTS", wave.REQUIRED_ACTIVE_CONTRACTS), \
             mock.patch.object(
                 wave.prequal,
                 "evaluate",
                 return_value={
                     "pass": False,
                     "execution_authority": False,
                     "authorization": "NONE",
                     "failed_predicates": ["P1_INFORMATION_LEAK"],
                 },
             ), \
             mock.patch.object(wave.c_suite, "generate_case") as c_generate, \
             mock.patch.object(wave.r_suite, "generate_case") as r_generate:
            with self.assertRaisesRegex(ValueError, "TERMINAL_PREQUALIFICATION_NOT_AUTHORIZED"):
                wave.execute(
                    candidate_package_commitment="pkg",
                    post_freeze_beacon="beacon",
                    repo_root=Path(td),
                )
            c_generate.assert_not_called()
            r_generate.assert_not_called()

    def test_full_protocol_requires_exactly_twelve_slots(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError, "TERMINAL_PROTOCOL_REQUIRES_EXACTLY_12_SLOTS"):
                wave.execute(
                    candidate_package_commitment="pkg",
                    post_freeze_beacon="beacon",
                    slots_per_obligation=2,
                    repo_root=Path(td),
                )


if __name__ == "__main__":
    unittest.main()
