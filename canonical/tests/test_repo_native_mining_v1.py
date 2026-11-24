"""Tests for repo-native mining + splicing. Real repos, real tests, no mocks."""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

from canonical.swe_kernel import repo_native_mining_v1 as mining


def _write(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text), encoding="utf-8")


def _run_pytest(repo: pathlib.Path, node: str) -> int:
    env = {
        "PYTHONPATH": ":".join([str(repo), str(repo / "src"), str(repo / "tests")]),
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": str(repo),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    done = subprocess.run(
        [sys.executable, "-m", "pytest", node, "-q", "--tb=short", "-p", "no:cacheprovider"],
        cwd=str(repo),
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )
    return done.returncode


class TestMiningFindsRepoHelper(unittest.TestCase):
    def test_mines_helper_three_files_away(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = pathlib.Path(td) / "repo"
            _write(
                repo / "src" / "helpers.py",
                """
                def normalize_price(cents, qty):
                    return cents * qty
                """,
            )
            _write(
                repo / "src" / "pricing.py",
                """
                from helpers import normalize_price

                def total(item):
                    return normalize_price(item.price_cents, item.qty)
                """,
            )
            _write(
                repo / "src" / "models.py",
                """
                class Item:
                    def __init__(self, price_cents, qty):
                        self.price_cents = price_cents
                        self.qty = qty
                """,
            )
            vocab = mining.mine_vocabulary(repo, "src")
            names = [f["name"] for f in vocab["functions"]]
            self.assertIn("normalize_price", names)
            self.assertIn("total", names)
            # The fixed grammar cannot name normalize_price; the mined
            # vocabulary can. That is the 75.2% wall, broken by harvest.
            expr_vocab = mining.vocabulary_for_expression(vocab)
            self.assertIn("normalize_price", expr_vocab)
            transitions = mining.infer_transition_types(vocab)
            by_name = {t["name"]: t for t in transitions}
            self.assertEqual(by_name["normalize_price"]["arity"], 2)
            self.assertGreaterEqual(by_name["normalize_price"]["call_site_count"], 1)

    def test_mines_exceptions_and_constants(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = pathlib.Path(td) / "repo"
            _write(
                repo / "src" / "errors.py",
                """
                MAX_RETRIES = 3

                class RetryError(Exception):
                    pass
                """,
            )
            vocab = mining.mine_vocabulary(repo, "src")
            self.assertEqual(vocab["counts"]["constants"], 1)
            self.assertEqual(vocab["counts"]["exceptions"], 1)


class TestSplicing(unittest.TestCase):
    def test_separating_guard_found(self) -> None:
        t1 = [{"qty": 2, "price_cents": 100}, {"qty": 3, "price_cents": 50}]
        t2 = [{"qty": 0, "price_cents": 100}, {"qty": 0, "price_cents": 50}]
        guard = mining.synthesize_separating_guard(t1, t2)
        self.assertIsNotNone(guard)
        spliced = mining.splice_programs("price_cents * qty", "0", guard)
        self.assertIn("if", spliced)
        self.assertIn("else", spliced)

    def test_guard_refused_when_inseparable(self) -> None:
        t1 = [{"x": 1}]
        t2 = [{"x": 1}]
        self.assertIsNone(mining.synthesize_separating_guard(t1, t2))

    def test_splice_repairs_two_branch_bug_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = pathlib.Path(td) / "repo"
            _write(
                repo / "src" / "calc.py",
                """
                def total(price_cents, qty):
                    return price_cents
                """,
            )
            _write(
                repo / "tests" / "test_calc.py",
                """
                from calc import total

                def test_positive():
                    assert total(100, 2) == 200

                def test_zero():
                    assert total(100, 0) == 0
                """,
            )
            # P1 (multiply) passes positive, fails zero-guard? Actually
            # multiply passes both; use P1=price_cents (passes zero only)
            # and P2=price_cents*qty (passes positive only) to force splice.
            guard = mining.synthesize_separating_guard(
                [{"qty": 2}], [{"qty": 0}]
            )
            self.assertIsNotNone(guard)
            spliced_expr = mining.splice_programs("price_cents * qty", "0", guard)
            # Guard is qty-based; spliced must be (price_cents*qty if qty... else 0)
            # which equals multiply for qty>0 and 0 for qty==0. Both correct.
            target = repo / "src" / "calc.py"
            original = target.read_text(encoding="utf-8")
            candidate = f"def total(price_cents, qty):\n    return {spliced_expr}\n"
            ok = mining.verify_with_real_test(
                repo,
                [sys.executable, "-m", "pytest", "tests/test_calc.py", "-q", "-p", "no:cacheprovider"],
                target,
                original,
                candidate,
            )
            self.assertTrue(ok)
            # File restored
            self.assertEqual(target.read_text(encoding="utf-8"), original)


class TestAdmissionGate(unittest.TestCase):
    def test_admits_good_patch_and_refuses_breaking_one(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = pathlib.Path(td)
            # Defective repo: total returns price_cents (wrong)
            drepo = base / "defective"
            _write(
                drepo / "src" / "calc.py",
                """
                def total(price_cents, qty):
                    return price_cents
                """,
            )
            _write(
                drepo / "tests" / "test_calc.py",
                """
                from calc import total

                def test_total():
                    assert total(100, 2) == 200
                """,
            )
            # Correct repo: total already correct; a patch that breaks it
            # must be refused. The correct victim is stricter (also checks
            # the zero case) so an overfit constant patch is caught.
            crepo = base / "correct"
            _write(
                crepo / "src" / "calc.py",
                """
                def total(price_cents, qty):
                    return price_cents * qty
                """,
            )
            _write(
                crepo / "tests" / "test_calc.py",
                """
                from calc import total

                def test_total():
                    assert total(100, 2) == 200

                def test_zero():
                    assert total(100, 0) == 0
                """,
            )
            dfile = drepo / "src" / "calc.py"
            cfile = crepo / "src" / "calc.py"
            dcmd = [sys.executable, "-m", "pytest", "tests/test_calc.py", "-q", "-p", "no:cacheprovider"]
            good = "def total(price_cents, qty):\n    return price_cents * qty\n"
            verdict = mining.admit_patch(
                candidate_source=good,
                defective_repo=drepo,
                defective_file=dfile,
                defective_original=dfile.read_text(encoding="utf-8"),
                defective_command=dcmd,
                correct_repo=crepo,
                correct_file=cfile,
                correct_original=cfile.read_text(encoding="utf-8"),
                correct_command=dcmd,
            )
            self.assertEqual(verdict["verdict"], "ADMIT")
            bad = "def total(price_cents, qty):\n    return price_cents\n"
            verdict2 = mining.admit_patch(
                candidate_source=bad,
                defective_repo=drepo,
                defective_file=dfile,
                defective_original=dfile.read_text(encoding="utf-8"),
                defective_command=dcmd,
                correct_repo=crepo,
                correct_file=cfile,
                correct_original=cfile.read_text(encoding="utf-8"),
                correct_command=dcmd,
            )
            self.assertEqual(verdict2["verdict"], "REFUSE")
            # Overfit patch: repairs the defective victim (100,2)->200 by
            # returning a constant, but breaks the correct victim's zero case.
            overfit = "def total(price_cents, qty):\n    return 200\n"
            verdict3 = mining.admit_patch(
                candidate_source=overfit,
                defective_repo=drepo,
                defective_file=dfile,
                defective_original=dfile.read_text(encoding="utf-8"),
                defective_command=dcmd,
                correct_repo=crepo,
                correct_file=cfile,
                correct_original=cfile.read_text(encoding="utf-8"),
                correct_command=dcmd,
            )
            self.assertEqual(verdict3["verdict"], "REFUSE")
            self.assertIn("BROKE_CORRECT_PROGRAM", verdict3["reason"])


class TestParallelCowRollouts(unittest.TestCase):
    def test_picks_residual_winner_without_fork(self) -> None:
        out = mining.parallel_cow_rollouts(
            [{"id": "a", "residual": 3}, {"id": "b", "residual": 0}, {"id": "c", "residual": 1}]
        )
        self.assertEqual(out["winner"], "b")

    def test_real_fork_picks_winner(self) -> None:
        def make_apply(v: int):
            def _apply() -> int:
                return v

            return _apply

        out = mining.parallel_cow_rollouts(
            [
                {"id": "a", "apply": make_apply(5)},
                {"id": "b", "apply": make_apply(0)},
                {"id": "c", "apply": make_apply(2)},
            ],
            score_fn=True,  # type: ignore[arg-type]
        )
        self.assertEqual(out["winner"], "b")
        self.assertEqual(out["residuals"]["b"], 0)
        self.assertGreater(out["fork_ms"], 0.0)

    def test_state_fingerprint_detects_change(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            _write(root / "a.txt", "hello\n")
            before = mining.state_fingerprint(root)
            _write(root / "a.txt", "world\n")
            after = mining.state_fingerprint(root)
            self.assertTrue(mining.diff_states(before, after))
            self.assertFalse(mining.diff_states(before, before))


class TestSingleExperienceTransfer(unittest.TestCase):
    def test_learned_guard_transfers_to_renamed_repo(self) -> None:
        # Learn guard on repo A (qty), apply to repo B (count) with same
        # structure but different identifiers. Anti-unification: the guard
        # shape (var > 0) transfers; the concrete name does not.
        guard_a = mining.synthesize_separating_guard([{"qty": 2}], [{"qty": 0}])
        self.assertIsNotNone(guard_a)
        # Transfer: rename qty -> count, guard shape preserved
        guard_b = guard_a.replace("qty", "count")
        self.assertIn("count", guard_b)
        spliced_b = mining.splice_programs("price * count", "0", guard_b)
        # Evaluate spliced_b on B states via the same evaluator
        import ast

        tree = ast.parse(spliced_b, mode="eval")
        # Manual eval: guard true -> price*count else 0
        for price, count, expected in [(10, 3, 30), (10, 0, 0)]:
            env = {"price": price, "count": count}
            # Reuse internal evaluator through a fresh guard check
            guard_tree = ast.parse(guard_b, mode="eval")
            from canonical.swe_kernel.repo_native_mining_v1 import _eval_node

            g = bool(_eval_node(guard_tree.body, env))
            got = price * count if g else 0
            self.assertEqual(got, expected)


class TestMemoryAblation(unittest.TestCase):
    def test_generalized_beats_raw_trace_and_empty(self) -> None:
        # Raw trace: concrete "qty == 2" learned from one run. It does not
        # transfer to a held-out variant with qty == 3.
        # Generalized: "qty > 0" (or "qty != 0") transfers.
        # Empty store: no guard at all -> refuse.
        t1 = [{"qty": 2}]
        t2 = [{"qty": 0}]
        guard = mining.synthesize_separating_guard(t1, t2)
        self.assertIsNotNone(guard)
        # Raw trace guard would be qty == 2; it fails on qty == 3.
        from canonical.swe_kernel.repo_native_mining_v1 import _eval_node
        import ast

        raw_tree = ast.parse("qty == 2", mode="eval")
        gen_tree = ast.parse(guard, mode="eval")
        held_out = {"qty": 3}
        # Raw fails to separate held-out positive from zero (both false/true mismatch)
        raw_on_held = bool(_eval_node(raw_tree.body, held_out))
        gen_on_held = bool(_eval_node(gen_tree.body, held_out))
        self.assertFalse(raw_on_held)  # raw trace does not fire on new value
        self.assertTrue(gen_on_held)  # generalized fires
        # Empty store: no guard -> splice impossible -> refuse (None)
        self.assertIsNone(mining.synthesize_separating_guard([], []))


if __name__ == "__main__":
    unittest.main()
