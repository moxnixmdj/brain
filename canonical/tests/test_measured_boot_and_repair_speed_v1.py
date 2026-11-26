"""Regression guard for the two measured boot costs, and for the repair the swap table buys.

Each test pins a number that was measured on 2026-11-24 and would otherwise silently regress:
deferring the fabric's 27 eager capability imports, validating the unified model's core cache by
stat signature instead of re-hashing 11.6 MB, and generating an operator-swap repair candidate
for an arithmetic bug. The thresholds are deliberately loose (a hard timeout, not a microbenchmark)
so the tests assert the ORDER of magnitude that was fixed, not a machine-specific timing.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile
import textwrap
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def _import_seconds(module: str, repeats: int = 3) -> float:
    """Fastest of N cold subprocess imports, in seconds."""
    best = float("inf")
    for _ in range(repeats):
        code = (
            "import time,sys;"
            f"t=time.perf_counter();import {module};"
            "print(time.perf_counter()-t)"
        )
        out = subprocess.run(
            [sys.executable, "-c", code],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=180,
        )
        if out.returncode != 0:
            raise AssertionError(f"import {module} failed: {out.stderr[-400:]}")
        best = min(best, float(out.stdout.strip().splitlines()[-1]))
    return best


class TestFabricImportIsDeferred(unittest.TestCase):
    def test_deferred_import_stays_under_its_measured_budget(self):
        """Was 188 ms while it eagerly imported 239 canonical modules; deferred it is ~28 ms."""
        measured = _import_seconds("canonical.runtime.unified_cognitive_fabric_v1")
        self.assertLess(
            measured,
            0.120,
            f"fabric import regressed to {measured * 1000:.0f} ms; the deferred-import table "
            "in unified_cognitive_fabric_v1 is the thing that keeps it cheap",
        )

    def test_fabric_no_longer_opens_an_http_client_to_build_a_table(self):
        code = (
            "import sys\n"
            "import canonical.runtime.unified_cognitive_fabric_v1\n"
            "print([m for m in sys.modules if m in ('http.client','urllib.request')])\n"
        )
        out = subprocess.run(
            [sys.executable, "-c", code], cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=180
        )
        self.assertEqual(out.returncode, 0, out.stderr[-400:])
        self.assertEqual(out.stdout.strip(), "[]", "an import-only fabric must not open a socket stack")

    def test_every_deferred_alias_still_resolves(self):
        """Deferral must not become a broken attribute: all declared aliases resolve."""
        code = textwrap.dedent(
            """
            import json
            from canonical.runtime import unified_cognitive_fabric_v1 as fabric
            aliases = list(fabric._LAZY_IMPORTS)
            failed = {}
            for name in aliases:
                try:
                    getattr(fabric, name)
                except Exception as exc:  # noqa: BLE001 - report, do not crash
                    failed[name] = f"{type(exc).__name__}: {exc}"
            print(json.dumps({"count": len(aliases), "failed": failed}))
            """
        )
        out = subprocess.run(
            [sys.executable, "-c", code], cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=180
        )
        self.assertEqual(out.returncode, 0, out.stderr[-600:])
        import json

        payload = json.loads(out.stdout.strip().splitlines()[-1])
        self.assertGreater(payload["count"], 20)
        self.assertEqual(payload["failed"], {}, "a deferred alias stopped resolving")


class TestUnifiedModelCacheSkipsTheFullHash(unittest.TestCase):
    def test_warm_open_is_much_cheaper_than_as_json_parse(self):
        """The cache used to read+sha256 all 11.6 MB before loading the 0.89 MB core."""
        artifact = pathlib.Path("canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json")
        self.assertTrue((REPO_ROOT / artifact).is_file(), "artifact missing")
        code = textwrap.dedent(
            f"""
            import time, sys
            sys.path.insert(0, {str(REPO_ROOT)!r})
            from canonical.runtime.brain_unified_model_v1 import open_model
            open_model()                       # warm
            t = time.perf_counter(); open_model(); warm = time.perf_counter() - t
            print(warm)
            """
        )
        t = subprocess.run(
            [sys.executable, "-c", code], cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=300
        )
        self.assertEqual(t.returncode, 0, t.stderr[-600:])
        warm = float(t.stdout.strip().splitlines()[-1])
        self.assertLess(warm, 0.15, f"warm open_model took {warm * 1000:.0f} ms; the stat-signature "
                                    "cache path did not fire")


class TestOperatorSwapRepairIsReachable(unittest.TestCase):
    """The 34-line swap tables existed for months outside the repair chain."""

    def test_generator_turns_minus_into_plus_on_an_implicated_line(self):
        from canonical.swe_kernel.metamorphic_habitation_zipper_v1 import (
            generate_operator_swap_candidates,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "calc.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
            cands = generate_operator_swap_candidates(root, "calc.py", {2}, max_candidates=8)
            self.assertTrue(cands, "no operator-swap candidate for `a - b`")
            patched = {c.patched_source for c in cands}
            self.assertIn(
                "def add(a, b):\n    return a+b\n",
                {p.rstrip("\n") + "\n" for p in patched},
                f"expected an `a+b` patch, got {[p.splitlines()[-1] for p in patched]}",
            )

    def test_generator_covers_comparisons_too(self):
        from canonical.swe_kernel.metamorphic_habitation_zipper_v1 import (
            generate_operator_swap_candidates,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "cmp.py").write_text("def pos(x):\n    return x < 0\n", encoding="utf-8")
            cands = generate_operator_swap_candidates(root, "cmp.py", {2}, max_candidates=12)
            bodies = {c.patched_source.splitlines()[-1].strip() for c in cands}
            self.assertTrue(any("<=" in b or ">" in b for b in bodies), bodies)

    def test_the_whole_zipper_repairs_a_one_character_bug(self):
        """End-to-end: the case that returned UNSOLVED_WITHIN_BUDGET now repairs in ~1 s."""
        from canonical.swe_kernel.metamorphic_habitation_zipper_v1 import (
            repair_repo_unified_zero_model as repair,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "calc.py").write_text(
                'def add(a, b):\n    """Return the sum of a and b."""\n    return a - b\n',
                encoding="utf-8",
            )
            (root / "test_calc.py").write_text(
                "import unittest\nfrom calc import add\n\n\n"
                "class T(unittest.TestCase):\n"
                "    def test_add(self):\n        self.assertEqual(add(2, 3), 5)\n\n\n"
                'if __name__ == "__main__":\n    unittest.main()\n',
                encoding="utf-8",
            )
            result = repair(
                str(root),
                "test_calc.py",
                issue_text="add(2,3) returns 5 but add returns -1. Fix add so it adds.",
                timeout_s=180,
                keep_patch_applied=True,
            )
            self.assertTrue(result.get("repaired"), f"not repaired: {result.get('reason')}")
            self.assertEqual(result.get("mechanism"), "OPERATOR_SWAP_AST")
            check = subprocess.run(
                [sys.executable, "-m", "pytest", "test_calc.py", "-q"],
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=180,
            )
            self.assertEqual(check.returncode, 0, check.stdout[-400:])


if __name__ == "__main__":
    unittest.main()
