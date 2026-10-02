from __future__ import annotations
import json,tempfile,unittest
from pathlib import Path
from canonical.runtime.research_t3_objective_binding_validator import BINDING,evaluate

ROOT=Path(__file__).resolve().parents[2]

class Tests(unittest.TestCase):
    def fixture(self,mutate=None):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            b=json.loads((ROOT/BINDING).read_text())
            if mutate: mutate(b)
            for row in (b.get("exact_bound_blobs") or {}).values():
                src=ROOT/row["path"]; dst=root/row["path"]; dst.parent.mkdir(parents=True,exist_ok=True); dst.write_bytes(src.read_bytes())
            rec=ROOT/"canonical/verification/RESEARCH_CONTROL_INFORMATION_SAFE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
            dst=root/rec.relative_to(ROOT); dst.parent.mkdir(parents=True,exist_ok=True); dst.write_bytes(rec.read_bytes())
            p=root/BINDING; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(b))
            return evaluate(root)
    def test_live_binding(self): self.assertTrue(evaluate(ROOT)["pass"],evaluate(ROOT))
    def test_hidden_oracle_leak_fails(self):
        self.assertFalse(self.fixture(lambda b:b["information_boundary"].__setitem__("candidate_receives_hidden_oracle",True))["pass"])
    def test_premature_hle_deletion_authority_fails(self):
        self.assertFalse(self.fixture(lambda b:b["weaker_dependency_reconciliation"].__setitem__("deletion_authorized_before_independent_binding_verification",True))["pass"])
    def test_missing_domain_fails(self):
        self.assertFalse(self.fixture(lambda b:b["source_pool"]["domain_cycle"].pop())["pass"])
    def test_adaptive_selector_fails(self):
        self.assertFalse(self.fixture(lambda b:b["selector"].__setitem__("adaptive_case_selection",True))["pass"])
    def test_cross_contract_overclaim_fails(self):
        self.assertFalse(self.fixture(lambda b:b["contract_boundary"].__setitem__("tool_route_discovery_owned_here",True))["pass"])
    def test_premature_prewave_fails(self):
        self.assertFalse(self.fixture(lambda b:b.__setitem__("prewave_admissible",True))["pass"])
if __name__=="__main__":unittest.main(verbosity=2)
