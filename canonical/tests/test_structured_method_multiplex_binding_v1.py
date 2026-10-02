from __future__ import annotations
import json,tempfile,unittest
from pathlib import Path
from canonical.runtime.verify_structured_method_multiplex_binding_v1 import evaluate,DEPENDENCIES,BINDING

ROOT=Path(__file__).resolve().parents[2]

class Tests(unittest.TestCase):
    def test_live_binding(self):
        out=evaluate(ROOT); self.assertTrue(out["pass"],out)
    def _mut(self,fn):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for rel in DEPENDENCIES:
                p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text("{}",encoding="utf-8")
            d=json.loads((ROOT/BINDING).read_text(encoding="utf-8"));fn(d)
            p=root/BINDING;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d),encoding="utf-8")
            return evaluate(root)
    def test_oracle_leak_fails(self):
        def m(d): d["candidate_visible_information"].append("INDEPENDENT_EXPECTED_GRAPH_TOPOLOGY")
        self.assertFalse(self._mut(m)["pass"])
    def test_surface_loss_fails(self):
        self.assertFalse(self._mut(lambda d:d["direct_surface_bindings"].pop())["pass"])
    def test_synthetic_overclaim_fails(self):
        self.assertFalse(self._mut(lambda d:d["terminal_acceptance"].__setitem__("standalone_synthetic_whole_domain_score_forbidden",False))["pass"])
    def test_contamination_fails(self):
        self.assertFalse(self._mut(lambda d:d["contamination"].__setitem__("case_replacement",True))["pass"])

if __name__=="__main__": unittest.main()
