from __future__ import annotations
import json,tempfile,unittest
from pathlib import Path
from canonical.runtime.verify_t3_research_control_prewave_v1 import evaluate

ROOT=Path(__file__).resolve().parents[2]

class T3ResearchControlPrewaveTests(unittest.TestCase):
    def test_live_binding_passes(self):
        out=evaluate(ROOT)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["errors"],[])
        self.assertFalse(out["execution_authority"])

    def test_hidden_oracle_leak_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            rels=[
              "canonical/governance/T3_RESEARCH_CONTROL_MULTIPLEX_TERMINAL_BINDING_V1.json",
              "canonical/verification/HLE_STRICT_LOWER_BOUND_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
              "canonical/verification/RESEARCH_CONTROL_INFORMATION_SAFE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
              "canonical/governance/T3_UNKNOWN_DOMAIN_SCOPE_AUDIT_V1.json",
              "canonical/verification/HARBOR_ZERO_COST_TERMINAL_CARRIER_PREFLIGHT_20261002_V1.json",
              "canonical/runtime/research_control_information_safe_candidate.py",
              "canonical/runtime/research_control_information_safe_proof.py",
            ]
            for rel in rels:
                src=ROOT/rel; dst=root/rel; dst.parent.mkdir(parents=True,exist_ok=True)
                dst.write_bytes(src.read_bytes())
            p=root/"canonical/governance/T3_RESEARCH_CONTROL_MULTIPLEX_TERMINAL_BINDING_V1.json"
            d=json.loads(p.read_text())
            d["information_boundary"]["candidate_receives_hidden_oracle"]=True
            p.write_text(json.dumps(d))
            self.assertFalse(evaluate(root)["pass"])

    def test_unbound_unknown_domain_contract_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            rels=[
              "canonical/governance/T3_RESEARCH_CONTROL_MULTIPLEX_TERMINAL_BINDING_V1.json",
              "canonical/verification/HLE_STRICT_LOWER_BOUND_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
              "canonical/verification/RESEARCH_CONTROL_INFORMATION_SAFE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
              "canonical/governance/T3_UNKNOWN_DOMAIN_SCOPE_AUDIT_V1.json",
              "canonical/verification/HARBOR_ZERO_COST_TERMINAL_CARRIER_PREFLIGHT_20261002_V1.json",
              "canonical/runtime/research_control_information_safe_candidate.py",
              "canonical/runtime/research_control_information_safe_proof.py",
            ]
            for rel in rels:
                src=ROOT/rel; dst=root/rel; dst.parent.mkdir(parents=True,exist_ok=True)
                dst.write_bytes(src.read_bytes())
            p=root/"canonical/governance/T3_UNKNOWN_DOMAIN_SCOPE_AUDIT_V1.json"
            d=json.loads(p.read_text())
            d["coverage"]["unbound_contracts"]=["TOOL_ROUTE_DISCOVERY_AND_SELECTION_001"]
            d["coverage"]["bound_contract_count"]=2
            p.write_text(json.dumps(d))
            self.assertFalse(evaluate(root)["pass"])

if __name__=="__main__":
    unittest.main()
