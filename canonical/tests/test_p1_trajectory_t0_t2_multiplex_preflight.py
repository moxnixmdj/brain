from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.p1_trajectory_t0_t2_multiplex_preflight import (
    BINDING,
    MANIFEST,
    REQUIRED_DEPS,
    evaluate,
)

ROOT = Path(__file__).resolve().parents[2]


class P1TrajectoryT0T2MultiplexPreflightTests(unittest.TestCase):
    def test_live_binding(self):
        out = evaluate(ROOT)
        self.assertTrue(out["pass"], out)

    def fixture(self, mutate=None, manifest_mutate=None, missing_dep=None):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for rel in REQUIRED_DEPS:
                if rel == missing_dep:
                    continue
                src = ROOT / rel
                dst = root / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(src.read_bytes())
            b = json.loads((ROOT / BINDING).read_text(encoding="utf-8"))
            m = json.loads((ROOT / MANIFEST).read_text(encoding="utf-8"))
            if mutate:
                mutate(b)
            if manifest_mutate:
                manifest_mutate(m)
            p = root / BINDING
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(b), encoding="utf-8")
            p = root / MANIFEST
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(m), encoding="utf-8")
            return evaluate(root)

    def test_hidden_cause_leak_fails(self):
        out = self.fixture(lambda b: b["candidate_visible_information"].append("HIDDEN_CAUSE_LABEL"))
        self.assertFalse(out["pass"])

    def test_synthetic_whole_domain_overclaim_fails(self):
        out = self.fixture(lambda b: b["terminal_acceptance"].__setitem__("standalone_synthetic_whole_domain_score_forbidden", False))
        self.assertFalse(out["pass"])

    def test_cross_behavior_inheritance_fails(self):
        out = self.fixture(lambda b: b["terminal_acceptance"].__setitem__("proof_rule", "CREDIT_FROM_BROWSER_OR_DELEGATION"))
        self.assertFalse(out["pass"])

    def test_missing_recovery_surface_route_fails(self):
        def mutate(m):
            for row in m["portfolios"]["T2"]["surfaces"]:
                if row.get("id") == "RECOVERY_SCOPE_COMPOSITION":
                    row["proof_routes"] = []
        out = self.fixture(manifest_mutate=mutate)
        self.assertFalse(out["pass"])

    def test_missing_nonidentifiability_check_fails(self):
        out = self.fixture(lambda b: b["evaluator"]["required_checks"].remove("NONIDENTIFIABLE_OR_CAUSALLY_EQUIVALENT_CASE_DOES_NOT_FORCE_UNIQUE_CAUSE"))
        self.assertFalse(out["pass"])

    def test_missing_multistep_mutation_fails(self):
        out = self.fixture(lambda b: b["evaluator"]["required_mutations"].remove("DROP_CAUSAL_PREDECESSOR_IN_MULTI_STEP_CHAIN"))
        self.assertFalse(out["pass"])

    def test_post_freeze_tuning_fails(self):
        out = self.fixture(lambda b: b["contamination"].__setitem__("post_freeze_case_specific_tuning", True))
        self.assertFalse(out["pass"])

    def test_premature_admission_fails(self):
        out = self.fixture(lambda b: b.__setitem__("prewave_admissible", True))
        self.assertFalse(out["pass"])

    def test_exact_opus_dependency_reintroduced_fails(self):
        out = self.fixture(lambda b: b["terminal_acceptance"].__setitem__("no_exact_opus_case_level_comparator_required_for_prewave_admission", False))
        self.assertFalse(out["pass"])

    def test_missing_dependency_fails(self):
        out = self.fixture(missing_dep=REQUIRED_DEPS[0])
        self.assertFalse(out["pass"])
        self.assertTrue(any(x.startswith("DEPENDENCY_MISSING:") for x in out["errors"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
