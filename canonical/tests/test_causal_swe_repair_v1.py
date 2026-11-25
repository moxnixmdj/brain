#!/usr/bin/env python3
"""Unit tests for Zero-Leakage Causal SWE Repair Engine (stdlib unittest runnable)."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from canonical.swe_kernel import causal_swe_repair_v1 as swe


class CausalSWERepairTests(unittest.TestCase):
    def test_autonomous_localization_and_falsy_non_none_guard_repair(self) -> None:
        with tempfile.TemporaryDirectory(prefix="swe-falsy-") as tmp:
            wt = Path(tmp)
            (wt / "src" / "pkg").mkdir(parents=True)
            (wt / "src" / "pkg" / "__init__.py").write_text("", encoding="utf-8")
            (wt / "src" / "pkg" / "pipeline.py").write_text(
                "class Wrapper:\n"
                "    def __init__(self, fn):\n"
                "        self.fn = fn\n"
                "    def __call__(self, x):\n"
                "        return self.fn(x)\n\n"
                "def normalize_step(converter):\n"
                "    if converter and not isinstance(converter, Wrapper):\n"
                "        return Wrapper(converter)\n"
                "    return converter\n\n"
                "def run_value(converter, val):\n"
                "    step = normalize_step(converter)\n"
                "    if step is None:\n"
                "        return val\n"
                "    return step(val)\n",
                encoding="utf-8",
            )
            (wt / "tests").mkdir()
            (wt / "tests" / "test_pipeline.py").write_text(
                "import unittest\n"
                "from pkg.pipeline import Wrapper, normalize_step, run_value\n\n"
                "class FalsyCallable:\n"
                "    def __len__(self):\n"
                "        return 0\n"
                "    def __call__(self, x):\n"
                "        return x + 10\n\n"
                "class PipelineTests(unittest.TestCase):\n"
                "    def test_none_converter(self):\n"
                "        self.assertEqual(run_value(None, 5), 5)\n"
                "    def test_ordinary_callable(self):\n"
                "        s = normalize_step(lambda x: x * 2)\n"
                "        self.assertIsInstance(s, Wrapper)\n"
                "        self.assertEqual(s(4), 8)\n"
                "    def test_falsy_callable_is_wrapped(self):\n"
                "        s = normalize_step(FalsyCallable())\n"
                "        self.assertIsInstance(s, Wrapper)\n"
                "        self.assertEqual(s(3), 13)\n",
                encoding="utf-8",
            )
            mem = swe.SWERepairMemory()
            res = swe.repair_worktree(wt, "tests/test_pipeline.py", memory=mem)
            self.assertTrue(res["pass"], res)
            self.assertEqual(res["repaired_file"], "src/pkg/pipeline.py")
            self.assertEqual(res["winning_family"], "FALSY_NON_NONE_GUARD")
            self.assertEqual(res["tests_failing_after"], 0)
            self.assertEqual(res["tests_passing_after"], 3)

    def test_iterator_materialization_repair_without_site_hint(self) -> None:
        with tempfile.TemporaryDirectory(prefix="swe-iter-") as tmp:
            wt = Path(tmp)
            (wt / "pkg").mkdir()
            (wt / "pkg" / "__init__.py").write_text("", encoding="utf-8")
            (wt / "pkg" / "builder.py").write_text(
                "def build_schema(fields, hook):\n"
                "    if hook is not None:\n"
                "        fields = hook(fields)\n"
                "    names = [f for f in fields]\n"
                "    count = len([f for f in fields])\n"
                "    return names, count\n",
                encoding="utf-8",
            )
            (wt / "tests").mkdir()
            (wt / "tests" / "test_builder.py").write_text(
                "import unittest\n"
                "from pkg.builder import build_schema\n\n"
                "class BuilderTests(unittest.TestCase):\n"
                "    def test_list_hook(self):\n"
                "        self.assertEqual(build_schema(['a', 'b'], lambda fs: [x.upper() for x in fs]), (['A', 'B'], 2))\n"
                "    def test_generator_hook_not_exhausted(self):\n"
                "        self.assertEqual(build_schema(['a', 'b'], lambda fs: (x.upper() for x in fs)), (['A', 'B'], 2))\n",
                encoding="utf-8",
            )
            res = swe.repair_worktree(wt, "tests/test_builder.py")
            self.assertTrue(res["pass"], res)
            self.assertEqual(res["winning_family"], "ITERATOR_MATERIALIZATION")
            self.assertEqual(res["tests_passing_after"], 2)

    def test_membership_extension_and_did_not_raise_repairs(self) -> None:
        # 1. Membership extension (`name != '__version_info__'` -> `name not in ('__version_info__', '__version__')`)
        with tempfile.TemporaryDirectory(prefix="swe-member-") as tmp:
            wt = Path(tmp)
            (wt / "mod.py").write_text(
                "import warnings\n"
                "DATA = {'__version__': '1.2.0', '__version_info__': (1, 2, 0), 'old_api': 99}\n"
                "def lookup_attr(name):\n"
                "    if name not in DATA:\n"
                "        raise AttributeError(name)\n"
                "    if name != '__version_info__':\n"
                "        warnings.warn('deprecated', DeprecationWarning)\n"
                "    return DATA[name]\n",
                encoding="utf-8",
            )
            (wt / "tests").mkdir()
            (wt / "tests" / "test_mod.py").write_text(
                "import unittest, warnings\n"
                "from mod import lookup_attr\n\n"
                "class ModTests(unittest.TestCase):\n"
                "    def test_old_api_warns(self):\n"
                "        with warnings.catch_warnings(record=True) as w:\n"
                "            warnings.simplefilter('always')\n"
                "            self.assertEqual(lookup_attr('old_api'), 99)\n"
                "            self.assertEqual(len(w), 1)\n"
                "    def test_version_info_no_warn(self):\n"
                "        with warnings.catch_warnings(record=True) as w:\n"
                "            warnings.simplefilter('always')\n"
                "            lookup_attr('__version_info__')\n"
                "            self.assertEqual(len(w), 0)\n"
                "    def test_dunder_version_no_warn(self):\n"
                "        with warnings.catch_warnings(record=True) as w:\n"
                "            warnings.simplefilter('always')\n"
                "            self.assertEqual(lookup_attr('__version__'), '1.2.0')\n"
                "            self.assertEqual(len(w), 0)\n",
                encoding="utf-8",
            )
            res = swe.repair_worktree(wt, "tests/test_mod.py")
            self.assertTrue(res["pass"], res)
            self.assertIn(res["winning_family"], {"MEMBERSHIP_SET_EXTENSION", "STUN_GUARD_SYNTHESIS"})

        # 2. DID NOT RAISE parser guard widening
        with tempfile.TemporaryDirectory(prefix="swe-dnr-") as tmp2:
            wt2 = Path(tmp2)
            (wt2 / "ver.py").write_text(
                "class InvalidTokenError(ValueError):\n"
                "    pass\n\n"
                "def parse_token(raw):\n"
                "    if not raw:\n"
                "        raise InvalidTokenError('empty')\n"
                "    return raw\n",
                encoding="utf-8",
            )
            (wt2 / "tests").mkdir()
            (wt2 / "tests" / "test_ver.py").write_text(
                "import unittest\n"
                "from ver import InvalidTokenError, parse_token\n\n"
                "class VerTests(unittest.TestCase):\n"
                "    def test_valid_ascii(self):\n"
                "        self.assertEqual(parse_token('v1.2'), 'v1.2')\n"
                "        self.assertEqual(parse_token('alpha-3'), 'alpha-3')\n"
                "    def test_empty_rejected(self):\n"
                "        with self.assertRaises(InvalidTokenError):\n"
                "            parse_token('')\n"
                "    def test_non_ascii_rejected(self):\n"
                "        with self.assertRaises(InvalidTokenError):\n"
                "            parse_token('v1.\\u0662')\n",
                encoding="utf-8",
            )
            res2 = swe.repair_worktree(wt2, "tests/test_ver.py")
            self.assertTrue(res2["pass"], res2)
            self.assertIn(
                res2["winning_family"],
                ("DID_NOT_RAISE_PREDICATE", "GUARD_DISJUNCTIVE_RELAXATION", "STUN_GUARD_SYNTHESIS"),
            )

    def test_degenerate_guard_and_runner_canary_anti_lobotomy_gate(self) -> None:
        import ast
        guard = ast.parse("exception is not None", mode="eval").body
        self.assertTrue(swe._is_degenerate_guard_extension(guard, "exception is None"))
        self.assertTrue(swe._is_degenerate_guard_extension(guard, "exception is not None"))
        self.assertFalse(swe._is_degenerate_guard_extension(guard, "flag is True"))

        with tempfile.TemporaryDirectory(prefix="swe-canary-") as tmp:
            wt = Path(tmp)
            self.assertTrue(swe.verify_runner_canary(wt))


if __name__ == "__main__":
    unittest.main()
