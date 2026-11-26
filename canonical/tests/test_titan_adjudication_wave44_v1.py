"""Wave 44: the titans were never broken, they were never checked.

The brief this wave answers proposed wiring twenty large unwired modules into the front door. The
adjudicator says all forty-three it named import cleanly and forty of them prove nothing, so the
tests here do three jobs: pin the two contracts adopted in this wave, reproduce the titan census
from the ledger, and keep the instrument's two relative-path defects from coming back.
"""
from __future__ import annotations

import json
import pathlib
import unittest

from canonical.runtime.futamura_leapfrog_kernel_v1 import (
    ConformalEValueGate,
    self_check as futamura_self_check,
)
from canonical.swe_kernel.egraph_and_deductive_synthesizer_v1 import (
    EGraph,
    ENode,
    self_check as egraph_self_check,
)
from canonical.tools.dark_matter_adjudicator_v1 import (
    BROKEN,
    IMPORTS_ONLY,
    PROVEN,
    adjudicate_importable,
    run,
)

ROOT = pathlib.Path(__file__).resolve().parents[2]
LEDGER = ROOT / "canonical/verification/TITAN_ADJUDICATION_20261126_V1.json"


class FutamuraContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = futamura_self_check()

    def test_self_check_passes(self) -> None:
        self.assertEqual(self.report["verdict"], "SELF_CHECK_PASS")
        self.assertEqual(self.report["checks"], self.report["passed"])

    def test_null_breach_rate_is_inside_the_villes_bound(self) -> None:
        self.assertLessEqual(self.report["breach_rate"], 0.05 + 3 * (0.05 * 0.95 / 400) ** 0.5)

    def test_the_guarantee_is_not_bought_by_never_committing(self) -> None:
        gate = ConformalEValueGate(alpha=0.05)
        committed = False
        for step in range(12):
            if gate.observe(f"s{step}", passed=True, null_pass_prob=0.25)["verdict"] == "COMMIT":
                committed = True
                break
        self.assertTrue(committed)

    def test_a_witness_outranks_accumulated_evidence(self) -> None:
        gate = ConformalEValueGate(alpha=0.05)
        for step in range(10):
            gate.observe(f"s{step}", passed=True, null_pass_prob=0.25)
        self.assertEqual(gate.decision()["verdict"], "COMMIT")
        gate.observe("w", passed=False, null_pass_prob=0.25, hard_contradiction=True)
        self.assertEqual(gate.decision()["verdict"], "ABSTAIN_FAIL_CLOSED")

    def test_alpha_is_validated(self) -> None:
        for bad in (0.0, 1.0, -0.5):
            with self.assertRaises(ValueError):
                ConformalEValueGate(alpha=bad)


class EGraphContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = egraph_self_check()

    def test_self_check_passes(self) -> None:
        self.assertEqual(self.report["verdict"], "SELF_CHECK_PASS")
        self.assertEqual(self.report["checks"], self.report["passed"])

    def test_congruence_closure_propagates_a_law_to_parents(self) -> None:
        g = EGraph()
        a, zero, one = (g.add(ENode(op, ())) for op in ("var:a", "const:0", "const:1"))
        law = g.add(ENode("add", (a, zero)))
        g.union(law, a)
        g.rebuild()
        self.assertEqual(g.find(g.add(ENode("add", (law, one)))),
                         g.find(g.add(ENode("add", (a, one)))))

    def test_an_egraph_that_merges_everything_would_fail_this(self) -> None:
        g = EGraph()
        a, one = g.add(ENode("var:a", ())), g.add(ENode("const:1", ()))
        other = g.add(ENode("add", (a, one)))
        self.assertNotEqual(g.find(other), g.find(a))


class InstrumentRegressionTest(unittest.TestCase):
    def test_relative_paths_resolve_instead_of_raising(self) -> None:
        """Wave 43's `run` crashed on relative paths; the titan sweep is exactly that call."""
        report = run(modules=["canonical/swe_kernel/metamorphic_laws_v1.py"], probe=False)
        self.assertEqual(report["candidates"], 1)
        self.assertEqual(report["verdicts"][0]["verdict"], IMPORTS_ONLY)

    def test_an_unnameable_candidate_does_not_abort_the_sweep(self) -> None:
        report = run(modules=["canonical/does_not_exist_v1.py",
                              "canonical/swe_kernel/metamorphic_laws_v1.py"],
                     probe=False, workers=2)
        self.assertEqual(report["candidates"], 2)

    def test_a_titan_proves_when_its_contract_is_called(self) -> None:
        verdict = adjudicate_importable(
            "canonical.swe_kernel.egraph_and_deductive_synthesizer_v1", timeout=120.0)
        self.assertEqual(verdict.verdict, PROVEN)
        self.assertEqual(verdict.evidence.get("checks"), 9)


class TitanLedgerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ledger = json.loads(LEDGER.read_text(encoding="utf-8"))

    def test_claim_table_has_a_verdict_for_every_claim(self) -> None:
        claims = self.ledger["brief_claim_verification"]
        self.assertGreaterEqual(len(claims), 8)
        self.assertTrue({row["verdict"] for row in claims.values()}
                        <= {"VERIFIED", "FAILED", "UNVERIFIED", "UNVERIFIABLE"})

    def test_the_failed_claims_are_recorded_as_failed(self) -> None:
        claims = self.ledger["brief_claim_verification"]
        self.assertEqual(claims["iteration_75_commit_209bbc6c"]["verdict"], "FAILED")
        self.assertEqual(claims["pr_7144_clean_and_22_of_22_green"]["verdict"], "FAILED")
        self.assertEqual(claims["1746_unwired_non_test_modules_ge_180_loc"]["verdict"], "FAILED")

    def test_titan_counts_account_for_every_candidate(self) -> None:
        titan = self.ledger["titan_adjudication"]
        self.assertEqual(sum(titan["counts"].values()), titan["candidates"])
        self.assertEqual(len(titan["proven"]), titan["counts"][PROVEN])
        self.assertEqual(titan["counts"][BROKEN], 0)

    def test_every_proven_titan_still_passes_its_own_checks(self) -> None:
        for row in self.ledger["titan_adjudication"]["proven"]:
            verdict = adjudicate_importable(row["module"], timeout=180.0)
            self.assertEqual(verdict.verdict, PROVEN, row["module"])
            self.assertEqual(verdict.evidence.get("checks"), row["checks"], row["module"])

    def test_census_refresh_is_consistent(self) -> None:
        census = self.ledger["census_refresh"]
        self.assertEqual(sum(census["counts"].values()), census["candidates"])
        self.assertEqual(census["counts"][PROVEN], len(self.ledger["titan_adjudication"]["proven"]) + 5)


if __name__ == "__main__":
    unittest.main()
