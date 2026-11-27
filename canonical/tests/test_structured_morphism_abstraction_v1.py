"""Wave 45: the store was empty because the abstraction was degenerate, not because recall was slow.

`AUTONOMOUS_CAUSAL_SWE_AND_COMPUTER_USE_RECEIPT_20261124_V2` measured store-vs-empty as identical
*and* recorded why: the learned pattern was one hole over the whole body, so it matched one exact
string and produced 0 proposals on its own witness, on a held-out same-family body, and on file
text. These tests pin the operator that replaces it and, just as important, pin what it refuses:

  * fidelity  -- a rule reproduces its own witness;
  * transfer  -- a rule fires on the same shape under renamed identifiers and shifted literals;
  * refusal   -- unrelated pairs, pinned literals and no-op morphisms are refused, so a store
                 built on this cannot re-ship the degenerate entry;
  * ablation  -- removing name parameterization breaks transfer, which is the measured reason the
                 part exists (nothing here is carried without a measurement).
"""
from __future__ import annotations

import json
import pathlib
import unittest

from canonical.swe_kernel.structured_morphism_abstraction_v1 import (
    ADMITTED,
    REFUSED_DEGENERATE,
    REFUSED_TRANSFER,
    _self_check,
    abstract,
    admit,
    apply_rule,
    hole_share,
    main,
    rename,
    structured_nodes,
)

ROOT = pathlib.Path(__file__).resolve().parents[2]

# Family 1: an exclusive bound that skipped the last element (the witness the operator must keep).
BOUND = ("for i in range(len(xs) - 1):\n    total += xs[i]",
         "for i in range(len(xs)):\n    total += xs[i]")
BOUND_VARIANT = ("for j in range(len(ys) - 1):\n    acc += ys[j]",
                 "for j in range(len(ys)):\n    acc += ys[j]")
BOUND_THIRD = ("for k in range(len(rows) - 1):\n    seen += rows[k]",
               "for k in range(len(rows)):\n    seen += rows[k]")

# Family 2: a comparison that excluded the boundary value.
COMPARE = ("if count < limit:\n    accept(count)",
           "if count <= limit:\n    accept(count)")
COMPARE_VARIANT = ("if used < budget:\n    spend(used)",
                   "if used <= budget:\n    spend(used)")

# Family 3: a wrapper that was peeled (projection, not projection-of-a-literal).
PEEL = ("return int(str(value))", "return str(value)")

# A pair whose after side is a value the before side cannot derive: must not transfer.
PINNED = ("request(url, timeout=30)", "request(url, timeout=60)")
PINNED_VARIANT = ("fetch(endpoint, timeout=45)", "fetch(endpoint, timeout=90)")


class SelfCheckTest(unittest.TestCase):
    def test_self_check_passes(self) -> None:
        report = _self_check()
        self.assertEqual(report["verdict"], "SELF_CHECK_PASS", json.dumps(report)[:1200])
        self.assertEqual(report["passed"], report["checks"])

    def test_cli_exit_zero(self) -> None:
        self.assertEqual(main(["--self-check"]), 0)


class FidelityTest(unittest.TestCase):
    def test_rule_reproduces_its_witness(self) -> None:
        for before, after in (BOUND, COMPARE, PEEL):
            with self.subTest(before=before.splitlines()[0]):
                rule = abstract(before, after)
                self.assertEqual(apply_rule(rule, before), after)

    def test_rule_is_not_the_identity(self) -> None:
        rule = abstract(*BOUND)
        self.assertNotEqual(rule.to_dict()["lhs"], rule.to_dict()["rhs"])


class TransferTest(unittest.TestCase):
    def test_renamed_variant_transfers(self) -> None:
        for (before, after), (v_before, v_after) in (((BOUND, BOUND_VARIANT), (COMPARE, COMPARE_VARIANT))):
            with self.subTest(before=before.splitlines()[0]):
                self.assertEqual(admit(before, after, (v_before, v_after))["verdict"], ADMITTED)

    def test_unseen_third_surface_transfers(self) -> None:
        """Never seen during abstraction: different identifiers, different containers."""
        rule = abstract(*BOUND)
        self.assertEqual(apply_rule(rule, BOUND_THIRD[0]), BOUND_THIRD[1])

    def test_rename_is_the_fixture_builder(self) -> None:
        self.assertEqual(
            rename(BOUND[0], {"i": "j", "xs": "ys", "total": "acc"}).splitlines()[-1].strip(),
            BOUND_VARIANT[0].splitlines()[-1].strip(),
        )

    def test_pinned_literal_does_not_transfer(self) -> None:
        """A constant the before side cannot derive is exactly what a store must refuse."""
        verdict = admit(*PINNED, PINNED_VARIANT)["verdict"]
        self.assertEqual(verdict, REFUSED_TRANSFER)


class RefusalTest(unittest.TestCase):
    def test_unrelated_pair_is_refused(self) -> None:
        self.assertEqual(admit("x + 1", "n * k")["verdict"], REFUSED_DEGENERATE)

    def test_mismatched_statement_counts_are_refused_not_misaligned(self) -> None:
        """Adding a statement changes the shape; silently zipping statements would invent a rule."""
        verdict = admit("total = 0", "total = 0\nindex = 0")["verdict"]
        self.assertNotEqual(verdict, ADMITTED)

    def test_syntax_error_is_fail_closed(self) -> None:
        self.assertNotEqual(admit("def (:", "x")["verdict"], ADMITTED)

    def test_no_op_is_refused(self) -> None:
        result = admit("alpha + beta", "alpha + beta")
        self.assertNotEqual(result["verdict"], ADMITTED)


class AblationTest(unittest.TestCase):
    def test_name_parameterization_is_load_bearing(self) -> None:
        """Without it the rule still reproduces its witness but cannot fire on a new surface."""
        pinned = abstract(*BOUND, parameterize_names=False)
        self.assertEqual(apply_rule(pinned, BOUND[0]), BOUND[1])
        self.assertNotEqual(apply_rule(pinned, BOUND_THIRD[0]), BOUND_THIRD[1])
        parameterized = abstract(*BOUND)
        self.assertEqual(apply_rule(parameterized, BOUND_THIRD[0]), BOUND_THIRD[1])

    def test_degeneracy_is_measurable(self) -> None:
        """The old store's artifact was one hole over everything: hole_share 1.0, no structure."""
        rule = abstract(*BOUND)
        self.assertLess(hole_share(rule.rhs), 0.5)
        self.assertGreater(structured_nodes(rule.rhs), 3)


class LedgerTest(unittest.TestCase):
    LEDGER = ROOT / "canonical/verification/STRUCTURED_MORPHISM_ABSTRACTION_20261124_V1.json"

    def test_ledger_records_the_store_ablation_it_answers(self) -> None:
        ledger = json.loads(self.LEDGER.read_text(encoding="utf-8"))
        self.assertEqual(ledger["schema"], "BRAIN_STRUCTURED_MORPHISM_ABSTRACTION_WAVE45_V1")
        blame = ledger["what_it_answers"]
        self.assertEqual(blame["store_vs_empty"], "identical")
        self.assertIn("single hole over the whole body", blame["recorded_cause"])
        self.assertEqual(ledger["self_check"]["verdict"], "SELF_CHECK_PASS")

    def test_ledger_claims_no_benchmark_result(self) -> None:
        ledger = json.loads(self.LEDGER.read_text(encoding="utf-8"))
        self.assertTrue(ledger["not_claimed"])
        self.assertIn("benchmark", " ".join(ledger["not_claimed"]).lower())


if __name__ == "__main__":
    unittest.main()
