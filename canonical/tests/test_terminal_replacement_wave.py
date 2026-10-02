from __future__ import annotations
import tempfile, unittest
from pathlib import Path
from unittest import mock

from canonical.runtime import terminal_replacement_wave as wave


class TerminalReplacementWaveTests(unittest.TestCase):
    def test_contract_universe_is_exactly_ten(self):
        self.assertEqual(len(wave.CONTRACTS),10)
        self.assertEqual(len(set(wave.CONTRACTS)),10)

    def test_seed_binding_is_deterministic_and_commit_sensitive(self):
        a=wave.derive_seed("pkg-a","beacon-1","C::slot::00")
        self.assertEqual(a,wave.derive_seed("pkg-a","beacon-1","C::slot::00"))
        self.assertNotEqual(a,wave.derive_seed("pkg-b","beacon-1","C::slot::00"))
        self.assertNotEqual(a,wave.derive_seed("pkg-a","beacon-2","C::slot::00"))

    def test_full_protocol_requires_twelve_slots(self):
        with self.assertRaises(ValueError):
            wave.execute(candidate_package_commitment="pkg",post_freeze_beacon="preflight",slots_per_obligation=2)

    def test_preflight_one_slot_per_behavior_via_protocol_constant_override(self):
        # Exercise every branch without pretending this fixed preflight is terminal evidence.
        with tempfile.TemporaryDirectory() as td, mock.patch.object(wave,"CONTRACTS",wave.CONTRACTS):
            # Call the exact logic by temporarily accepting one slot only in a local wrapper.
            original=wave.execute
            def one_slot(**kwargs):
                # minimal in-test copy of protocol count gate: patch source constant is not enough,
                # so invoke all candidate/evaluator pairs directly with deterministic seed.
                behaviors={}
                for contract in wave.CONTRACTS:
                    seed=wave.derive_seed("preflight-package","preflight-beacon",contract+"::slot::00")
                    if contract in wave.c_suite.CONTRACTS:
                        case=wave.c_suite.generate_case(contract,seed,1)
                        got=wave.c_candidate.solve(wave.c_suite.public_task(case))
                        verdict=wave.c_suite.score_case(case,got)
                    else:
                        case=wave.r_suite.generate_case(contract,seed,1)
                        public=wave.r_suite.public_task(case)
                        case_dir=Path(td)/contract
                        case_dir.mkdir(parents=True,exist_ok=True)
                        got=wave.r_candidate.solve(public,workdir=case_dir)
                        artifact=None
                        if contract=="NATIVE_ARTIFACT_STRUCTURED_EDIT_PRESERVATION_001":
                            artifact=Path(got["output_path"]).read_bytes()
                        verdict=wave.r_suite.score_case(case,got,artifact_bytes=artifact)
                    behaviors[contract]=verdict.get("pass") is True
                return behaviors
            out=one_slot()
            self.assertEqual(len(out),10)
            self.assertTrue(all(out.values()),out)


if __name__=="__main__":
    unittest.main()
