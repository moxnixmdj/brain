from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.terminal_route_executor_compiler import (
    _extract_direct_descriptor,
    _extract_multiplex_descriptor,
    compile_plan,
)


class TerminalRouteExecutorCompilerTests(unittest.TestCase):
    def test_direct_descriptor_uses_frozen_count_not_global_shortcut(self):
        out = _extract_direct_descriptor({
            "population": {
                "sample_count": 2000,
                "generator": "canonical/runtime/g.py",
                "route_population_version": "POP_V1",
                "case_id_rule": "B::POP_V1::slot::<index>",
                "seed_rule": "HASH(commitment,beacon,case_id)",
                "adaptive_case_selection": False,
                "case_replacement": False,
                "replay_for_tuning": False,
            }
        })
        self.assertIsNotNone(out)
        self.assertEqual(out["sample_count"], 2000)
        self.assertTrue(out["anti_adaptive"])

    def test_multiplex_descriptor_requires_explicit_parent_evidence_and_rule(self):
        self.assertIsNone(_extract_multiplex_descriptor({"terminal_acceptance": {}}))
        out = _extract_multiplex_descriptor({
            "terminal_acceptance": {
                "terminal_evidence_source": "THE_FROZEN_T1_TERMINAL_OBSERVATIONS",
                "proof_rule": "DIRECT_INSTRUMENTATION_AND_PARENT_ACCEPTANCE_MUST_PASS",
            }
        })
        self.assertEqual(out["terminal_evidence_source"], "THE_FROZEN_T1_TERMINAL_OBSERVATIONS")

    def _write(self, root: Path, rel: str, obj) -> None:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")

    def _fixture(self, bind_all: bool = True) -> Path:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        ids = [f"B{i:02d}" for i in range(12)]

        self._write(root, "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json", {
            "active_contracted_residuals": [{"behavior_id": x} for x in ids],
        })
        self._write(root, "canonical/governance/ACTIVE_TERMINAL_PROOF_BASIS_V1.json", {
            "contracts": [
                {"behavior_id": x, "portfolio": "T0", "route": f"canonical/governance/routes/{x}.json"}
                for x in ids
            ],
        })
        self._write(root, "canonical/governance/GLOBAL_TERMINAL_REPLACEMENT_POPULATION_PROTOCOL_V2.json", {
            "active_contracts": ids,
            "frozen_route_bindings": {
                x: {"route": f"canonical/governance/routes/{x}.json", "proof_mode": "TEST"}
                for x in ids
            },
        })
        self._write(root, "canonical/governance/TERMINAL_WAVE_EXECUTION_AUTHORITY_V1.json", {
            "execution_authority": True,
        })
        self._write(root, "canonical/governance/TERMINAL_ROUTE_SPECIFIC_EXECUTOR_MANIFEST_V1.json", {
            "routes": [
                {
                    "behavior_id": x,
                    "frozen_route": f"canonical/governance/routes/{x}.json",
                    "executor_status": "BOUND_EXACT_ROUTE_EXECUTOR" if bind_all else "MISSING_ROUTE_SPECIFIC_TERMINAL_EXECUTOR_BINDING",
                    "executor_path": f"canonical/runtime/executors/{x}.py" if bind_all else None,
                    "terminal_result_status": "NOT_EXECUTED",
                }
                for x in ids
            ],
        })
        for i, x in enumerate(ids):
            if i < 6:
                route = {
                    "population": {
                        "sample_count": 100 + i,
                        "generator": f"canonical/runtime/g{i}.py",
                        "route_population_version": f"POP{i}",
                        "case_id_rule": f"{x}::POP{i}::slot::<index>",
                        "seed_rule": "HASH(commitment,beacon,case_id)",
                        "adaptive_case_selection": False,
                        "case_replacement": False,
                        "replay_for_tuning": False,
                    }
                }
            else:
                route = {
                    "terminal_acceptance": {
                        "terminal_evidence_source": "THE_FROZEN_PARENT_TERMINAL_OBSERVATIONS",
                        "proof_rule": "DIRECT_INSTRUMENTATION_AND_PARENT_ACCEPTANCE_MUST_PASS",
                    }
                }
            self._write(root, f"canonical/governance/routes/{x}.json", route)
        return root

    def test_full_fixture_compiles_to_six_direct_six_multiplex_and_launch_ready(self):
        out = compile_plan(self._fixture(bind_all=True))
        self.assertTrue(out["structural_ready"], out)
        self.assertTrue(out["launch_ready"], out)
        self.assertEqual(out["active_contract_count"], 12)
        self.assertEqual(out["direct_population_count"], 6)
        self.assertEqual(out["multiplex_instrumentation_count"], 6)
        self.assertEqual(out["errors"], [])

    def test_unbound_executors_block_launch_without_blocking_structural_plan(self):
        out = compile_plan(self._fixture(bind_all=False))
        self.assertTrue(out["structural_ready"], out)
        self.assertFalse(out["launch_ready"])
        self.assertEqual(len(out["unbound_executor_contracts"]), 12)


if __name__ == "__main__":
    unittest.main()
