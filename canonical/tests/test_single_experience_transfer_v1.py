"""Wave 46: does one experience help on the next repair? Measured, with the positive control first.

The value of a zero is entirely in whether the instrument could have produced a one. These tests
therefore pin both directions: the parser and scorer must register hits on a shape that repeats
under new identifiers, and the arms must refuse near misses. Only then do the receipt's zeros mean
what the receipt says they mean.

No network here. The harvest is a build-time step; its output is pinned by digest in the receipt.
"""
from __future__ import annotations

import json
import pathlib
import unittest

from canonical.swe_kernel.single_experience_transfer_v1 import (
    Repair,
    apply_compound_attr_rule,
    apply_subexpr_rule,
    evaluate,
    extract_minimal_compound_subexpr_pair,
    learn,
    learn_compound_attr_rules,
    learn_subexpr,
    parse_patch,
    score,
    score_combined,
    score_raw_traces,
    score_subexpr,
    self_check,
    shape_ceiling,
    split_by_file,
    split_chronological,
)

ROOT = pathlib.Path(__file__).resolve().parents[2]
RECEIPT = ROOT / "canonical/verification/SINGLE_EXPERIENCE_TRANSFER_20261124_V1.json"

FIXTURE = """@@ -10,3 +10,3 @@ def f(xs):
-    if len(xs) < limit:
+    if len(xs) <= limit:
         return False
@@ -40,7 +40,7 @@
-    total = 0
-    for i in range(n):
+    total = 1
+    for i in range(n - 1):
         total += i
@@ -70,2 +70,2 @@
-    value = compute(a, b, c, d, e, f, g)
+    value = compute(a, b, c, d, e, f, h)
"""


def _repairs(text: str = FIXTURE, path: str = "m.py") -> list[Repair]:
    return parse_patch(text, slug="x/y", sha="a" * 40, path=path)


class SelfCheckTest(unittest.TestCase):
    def test_positive_control_fires(self) -> None:
        report = self_check()
        self.assertEqual(report["verdict"], "SELF_CHECK_PASS", json.dumps(report))
        self.assertEqual(report["detail"]["positive_hits"], 1)
        self.assertEqual(report["detail"]["empty_hits"], 0)
        self.assertEqual(report["detail"]["near_miss_hits"], 0)


class ParserTest(unittest.TestCase):
    def test_compound_header_is_elided_not_dropped(self) -> None:
        repairs = _repairs()
        self.assertGreaterEqual(len(repairs), 1)
        self.assertEqual(repairs[0].before, "if len(xs) < limit:\n    pass")
        self.assertEqual(repairs[0].after, "if len(xs) <= limit:\n    pass")

    def test_interleaved_blocks_become_separate_repairs(self) -> None:
        """Two changed statements are two repairs, not one two-line repair: the unit is a statement."""
        text = "@@ -1,2 +1,2 @@\n-    a = 1\n+    a = 2\n-    b = 1\n+    b = 2\n"
        repairs = _repairs(text)
        self.assertEqual(len(repairs), 2)
        self.assertEqual([r.before for r in repairs], ["a = 1", "b = 1"])

    def test_oversized_block_is_skipped(self) -> None:
        body = "\n".join(f"-    x{i} = {i}" for i in range(9))
        after = "\n".join(f"+    x{i} = {i + 1}" for i in range(9))
        self.assertEqual(len(_repairs(f"@@ -1,9 +1,9 @@\n{body}\n{after}\n")), 0)

    def test_unchanged_hunk_is_skipped(self) -> None:
        text = "@@ -1,1 +1,1 @@\n-    a = 1\n+    a = 1\n"
        self.assertEqual(len(_repairs(text)), 0)


class SplitTest(unittest.TestCase):
    def setUp(self) -> None:
        self.pool = _repairs() + _repairs(path="n.py") + _repairs(path="o.py")

    def test_file_grouped_split_never_shares_a_file(self) -> None:
        train, test = split_by_file(self.pool)
        self.assertTrue(train and test)
        self.assertEqual(set(r.path for r in train) & set(r.path for r in test), set())

    def test_changed_file_split_never_shares_a_file(self) -> None:
        train, test = split_chronological(self.pool)
        self.assertEqual(set(r.path for r in train) & set(r.path for r in test), set())

    def test_grouped_split_keeps_every_repair(self) -> None:
        train, test = split_by_file(self.pool)
        self.assertEqual(len(train) + len(test), len(self.pool))


class ScorerTest(unittest.TestCase):
    def test_rule_learned_once_fires_on_a_renamed_instance(self) -> None:
        train = _repairs()
        held = _repairs("@@ -3,1 +3,1 @@\n-    if len(rows) < bound:\n+    if len(rows) <= bound:\n", path="z.py")
        result = score(learn(train), held)
        self.assertEqual(result["hits"], 1)

    def test_empty_store_is_zero(self) -> None:
        self.assertEqual(score([], _repairs())["hits"], 0)

    def test_near_miss_is_not_a_hit(self) -> None:
        train = _repairs()
        near = [Repair(slug="x/y", sha="e" * 40, path="w.py", index=0,
                       before="if len(rows) < bound:\n    pass",
                       after="if len(rows) > bound:\n    pass")]
        self.assertEqual(score(learn(train), near)["hits"], 0)

    def test_raw_traces_count_only_exact_repeats(self) -> None:
        train = _repairs()
        self.assertEqual(score_raw_traces(train, train)["hits"], len(train))
        near = [Repair(slug="x/y", sha="e" * 40, path="w.py", index=0,
                       before="if len(rows) < bound:\n    pass",
                       after="if len(rows) <= bound:\n    pass")]
        self.assertEqual(score_raw_traces(train, near)["hits"], 0)

    def test_shape_ceiling_bounds_reachability(self) -> None:
        train = _repairs()
        same = _repairs("@@ -1,1 +1,1 @@\n-    if a < b:\n+    if a <= b:\n", path="z.py")
        other = [Repair(slug="x/y", sha="f" * 40, path="q.py", index=0,
                        before="return compute(x)", after="return compute(y)")]
        self.assertEqual(shape_ceiling(learn(train), same)["same_root_as_some_rule"], 1)
        self.assertEqual(shape_ceiling(learn(train), other)["same_root_as_some_rule"], 0)

    def test_evaluate_reports_all_four_arms(self) -> None:
        train, test = split_by_file(_repairs() + _repairs(path="n.py"))
        report = evaluate(train, test)
        for arm in ("STORE", "SUBEXPR_STORE", "COMBINED_STORE", "EMPTY", "RAW_TRACE", "SHAPE_CEILING"):
            self.assertIn(arm, report)

    def test_subexpr_transfers_across_different_statement_wrappers(self) -> None:
        """A rule learned inside an `if` header must transfer into an unseen `return` or `assign`."""
        train = [
            Repair(
                slug="a/b", sha="1" * 40, path="p.py", index=0,
                before="if len(xs) < limit:\n    pass",
                after="if len(xs) <= limit:\n    pass",
            ),
        ]
        held = [
            Repair(
                slug="c/d", sha="2" * 40, path="q.py", index=0,
                before="ok = len(items) < cap",
                after="ok = len(items) <= cap",
            ),
        ]
        # Whole-statement store misses because root statement changed from If to Assign
        self.assertEqual(score(learn(train), held)["hits"], 0)
        # Compound-LHS sub-expression store reproduces the held-out after AST exactly
        sub_rules = learn_subexpr(train)
        self.assertEqual(score_subexpr(sub_rules, held)["hits"], 1)
        self.assertEqual(score_combined(learn(train), sub_rules, held)["hits"], 1)

    def test_bare_name_diff_is_never_admitted_as_subexpr_rule(self) -> None:
        """Fail-closed safety guard: bare `Name -> Name` diffs must never become wildcard rewrites."""
        train = [
            Repair(slug="a/b", sha="3" * 40, path="p.py", index=0, before="x = te", after="x = t"),
        ]
        self.assertIsNone(extract_minimal_compound_subexpr_pair("x = te", "x = t"))
        self.assertEqual(learn_subexpr(train), [])
        self.assertEqual(learn_compound_attr_rules(train), [])

    def test_compound_attr_rule_requires_two_witnesses_and_ignores_bare_names(self) -> None:
        one_witness = [
            Repair(slug="a/b", sha="4" * 40, path="p.py", index=0,
                   before="x: te.Self = obj", after="x: t.Self = obj"),
        ]
        self.assertEqual(learn_compound_attr_rules(one_witness), [])
        two_witnesses = one_witness + [
            Repair(slug="a/b", sha="5" * 40, path="p2.py", index=0,
                   before="y: te.ParamSpec = spec", after="y: t.ParamSpec = spec"),
        ]
        cars = learn_compound_attr_rules(two_witnesses)
        self.assertEqual(len(cars), 1)
        self.assertEqual(cars[0].owner_before, "te")
        self.assertEqual(cars[0].owner_after, "t")
        # Fires on unseen compound attribute `te.Concatenate` in another repo
        held_attr = [
            Repair(slug="c/d", sha="6" * 40, path="q.py", index=0,
                   before="z: te.Concatenate = fn", after="z: t.Concatenate = fn"),
        ]
        self.assertEqual(score_subexpr([], held_attr, compound_attr_rules=cars)["hits"], 1)
        # Never fires on bare local variable `te`
        self.assertEqual(apply_compound_attr_rule(cars[0], "val = te + 1"), [])


class ReceiptTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))

    def test_schema_and_self_check(self) -> None:
        self.assertEqual(self.receipt["schema"], "BRAIN_SINGLE_EXPERIENCE_TRANSFER_V1")
        self.assertEqual(self.receipt["self_check"]["verdict"], "SELF_CHECK_PASS")

    def test_runtime_dependency_count_is_zero(self) -> None:
        self.assertEqual(self.receipt["cost"]["model_calls"], 0)
        self.assertEqual(self.receipt["cost"]["network_calls_this_run"], 0)
        self.assertGreaterEqual(self.receipt["harvest"]["api_calls_original"], 1)

    def test_verdict_matches_the_arms_it_reports(self) -> None:
        verdict = self.receipt["verdict"]
        within = self.receipt["within_repository"]
        self.assertEqual(verdict["within_repository"]["store"], within["STORE"]["rate"])
        self.assertEqual(verdict["within_repository"]["raw_traces"], within["RAW_TRACE"]["rate"])
        self.assertEqual(verdict["abstraction_beats_verbatim"],
                         within["STORE"]["hits"] > within["RAW_TRACE"]["hits"])
        self.assertTrue(verdict["deletion_condition"])

    def test_cross_repository_result_is_recorded_with_its_size(self) -> None:
        cross = self.receipt["cross_repository"]
        self.assertGreaterEqual(cross["STORE"]["tested"], 1000)
        self.assertEqual(cross["contamination"], "CONTAMINATED_FOR_CATALOGUE")

    def test_it_does_not_claim_a_benchmark_result(self) -> None:
        self.assertIn("benchmark", " ".join(self.receipt["not_claimed"]).lower())


if __name__ == "__main__":
    unittest.main()
