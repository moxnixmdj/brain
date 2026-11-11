from __future__ import annotations
import json,tempfile,unittest
from pathlib import Path
from canonical.runtime.verify_cad_t0_final_prewave_v1 import verify
ROOT=Path(__file__).resolve().parents[2]

class CadT0FinalPrewaveTests(unittest.TestCase):
    def test_live_branch_binding_passes(self):
        out=verify(ROOT);self.assertTrue(out["pass"],out);self.assertEqual(out["errors"],[])

    def test_candidate_measurement_authority_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            rels=[
              "canonical/governance/CAD_T0_MULTIPLEX_TERMINAL_BINDING_V1.json",
              "canonical/governance/CAD_T0_ORACLE_EXTRACTION_POPULATION_BINDING_V1.json",
              "canonical/governance/CAD_T0_EVALUATOR_OBSERVATION_SCHEMA_V1.json",
              "canonical/verification/CAD_T0_MULTIPLEX_SCORER_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
              "canonical/governance/GLOBAL_TERMINAL_REPLACEMENT_POPULATION_PROTOCOL_V2.json",
              "canonical/runtime/cad_t0_oracle_extractor.py",
              "canonical/runtime/cad_t0_multiplex_scorer.py",
              "canonical/governance/TERMINAL_PORTFOLIO_BINDING_MANIFESTS_V1.json",
            ]
            for rel in rels:
                s=ROOT/rel;d=root/rel;d.parent.mkdir(parents=True,exist_ok=True);d.write_bytes(s.read_bytes())
            # Copy every dependency named by the oracle binding.
            oracle=json.loads((root/"canonical/governance/CAD_T0_ORACLE_EXTRACTION_POPULATION_BINDING_V1.json").read_text())
            for rel in oracle["dependencies"]:
                d=root/rel
                if not d.exists():
                    s=ROOT/rel;d.parent.mkdir(parents=True,exist_ok=True);d.write_bytes(s.read_bytes())
            p=root/"canonical/governance/CAD_T0_ORACLE_EXTRACTION_POPULATION_BINDING_V1.json"
            oracle["oracle_extraction"]["candidate_self_report_as_oracle"]=True
            p.write_text(json.dumps(oracle))
            self.assertFalse(verify(root)["pass"])

if __name__=="__main__":
    unittest.main()
