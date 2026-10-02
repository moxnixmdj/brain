from __future__ import annotations
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from canonical.runtime.specification_multiplex_instrumentation_validator import evaluate

ROOT=Path(__file__).resolve().parents[2]

class SpecificationMultiplexInstrumentationValidatorTests(unittest.TestCase):
    def test_canonical_manifest_passes(self):
        out=evaluate(ROOT)
        self.assertTrue(out["pass"],out)

    def _mutated(self, mutate):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            gov=root/"canonical/governance"
            gov.mkdir(parents=True)
            for name in ("SPECIFICATION_PORTFOLIO_MULTIPLEX_INSTRUMENTATION_V1.json","BEHAVIORAL_CONTRACT_REGISTRY_V1.json"):
                src=ROOT/"canonical/governance"/name
                (gov/name).write_text(src.read_text(encoding="utf-8"),encoding="utf-8")
            p=gov/"SPECIFICATION_PORTFOLIO_MULTIPLEX_INSTRUMENTATION_V1.json"
            data=json.loads(p.read_text(encoding="utf-8"))
            mutate(data)
            p.write_text(json.dumps(data),encoding="utf-8")
            return evaluate(root)

    def test_hidden_oracle_leak_boundary_fails_closed(self):
        out=self._mutated(lambda d:d["candidate_visible_information"]["forbidden"].remove("VERIFIER_IMPLEMENTATION"))
        self.assertFalse(out["pass"])

    def test_missing_portfolio_boundary_fails_closed(self):
        out=self._mutated(lambda d:d["portfolio_information_boundaries"].pop("T3"))
        self.assertFalse(out["pass"])

    def test_pre_freeze_selection_fails_closed(self):
        out=self._mutated(lambda d:d["post_freeze_selector"].__setitem__("selection_before_downstream_portfolio_freeze",True))
        self.assertFalse(out["pass"])

    def test_self_promotion_fails_closed(self):
        out=self._mutated(lambda d:d["acceptance_accounting"].__setitem__("terminal_promotion_from_this_manifest",True))
        self.assertFalse(out["pass"])

if __name__=="__main__":
    unittest.main(verbosity=2)
