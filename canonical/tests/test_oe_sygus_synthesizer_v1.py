"""Tests for Unified Multi-Language OE-SyGuS + EUSolver Synthesizer v1
and its execution-guided integration in JS/TS & Python via ONE Front Door
(`open_model().solve(..., mode="EPISTEMIC")`).
"""
from __future__ import annotations

import pathlib
import tempfile
import unittest

from canonical.runtime import oe_sygus_synthesizer_v1 as OESYGUS
from canonical.runtime import universal_epistemic_kernel_v1 as UEK
from canonical.runtime.brain_unified_model_v1 import open_model


def _write_files(root: pathlib.Path, files: dict[str, str]) -> None:
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")


class TestOESyGuSSynthesizerV1(unittest.TestCase):
    def test_01_eusolver_separating_predicates_across_python_js_c(self) -> None:
        # Compound failure set: negative + non-integer float + NaN + Infinity vs valid non-negative ints
        failing = [{"size": -3}, {"size": 0.5}, {"size": "__NaN__"}, {"size": "__Inf__"}]
        passing = [{"size": 0}, {"size": 1}, {"size": 10}, {"size": 21}]

        for lang, expected_tokens in [
            ("js", ("Number.isInteger(size)", "size < 0", "||")),
            ("python", ("isinstance(size, int)", "size < 0", "or")),
            ("c", ("floor(size)", "size < 0", "||")),
        ]:
            preds = OESYGUS.synthesize_separating_predicates(failing, passing, lang=lang, max_results=4)
            self.assertTrue(preds, f"No predicate synthesized for {lang}")
            top = preds[0]["code"]
            for tok in expected_tokens:
                self.assertIn(tok, top, f"Expected {tok!r} in {top!r} ({lang})")
            # Must NOT overfit to exact literal 0.5 or -3
            self.assertNotIn("0.5", top)
            self.assertNotIn("-3", top)

    def test_02_oe_sygus_coercion_and_ite_synthesis(self) -> None:
        # Coercion: floats -> truncated integers across JS & Python
        ex_trunc = [({"n": 4.5}, 4), ({"n": 16.5}, 16), ({"n": 10}, 10), ({"n": 0}, 0)]
        js_res = OESYGUS.synthesize_value_expressions(ex_trunc, lang="js", max_results=6)
        self.assertTrue(any("Math.trunc(n)" in r["code"] or "(n | 0)" in r["code"] or "Math.floor(n)" in r["code"] for r in js_res), js_res)

        # Conditional ITE synthesis: clamp negative values to 0, else keep x
        ex_ite = [({"x": -5}, 0), ({"x": -1}, 0), ({"x": 0}, 0), ({"x": 3}, 3), ({"x": 9}, 9)]
        py_res = OESYGUS.synthesize_value_expressions(ex_ite, lang="python", max_results=6)
        self.assertTrue(any("max(" in r["code"] or "if" in r["code"] for r in py_res), py_res)

        # Plotkin anti-unification yields zero-repo, zero-weight skill
        law = OESYGUS.abstract_synthesized_repair(
            lang="js",
            error_kind="NON_TERM",
            guard_expr=OESYGUS.Expr("not_integer", (OESYGUS.Expr("var", ("size",), 1),), 2),
            action_kind="trunc_coercion",
            action_expr=OESYGUS.Expr("int32_trunc", (OESYGUS.Expr("var", ("size",), 1),), 2),
        )
        self.assertEqual(law["parameters_stored"], 0)
        self.assertNotIn("size", str(law))
        self.assertIn("$V0", law["guard_template"])

    def test_03_end_to_end_js_infinite_loop_and_float_coercion_frontdoor_with_unlearning(self) -> None:
        """Real JS repo where non-integer float causes infinite `while (i--)` loop (`rc=124`).
        Execution-guided entry/exit tracing + OE-SyGuS synthesizes coercion, passes tests with
        0 orphans, distills zero-weight law, and instantly unlearns via delete_memory_entry."""
        model = open_model()
        mem = UEK.new_universal_memory()

        with tempfile.TemporaryDirectory(prefix="brain_oesygus_js_") as td:
            root = pathlib.Path(td)
            _write_files(
                root,
                {
                    "package.json": '{"name":"tok-demo","type":"module","version":"1.0.0"}\n',
                    "index.js": (
                        "export function makeToken(size = 8) {\n"
                        "  if (!size) return ''\n"
                        "  let out = ''\n"
                        "  let i = size\n"
                        "  while (i--) {\n"
                        "    out += 'x'\n"
                        "  }\n"
                        "  return out\n"
                        "}\n"
                    ),
                    "test/tok.test.js": (
                        "import test from 'node:test'\n"
                        "import assert from 'node:assert/strict'\n"
                        "import { makeToken } from '../index.js'\n"
                        "test('handles integer sizes', () => {\n"
                        "  assert.equal(makeToken(0), '')\n"
                        "  assert.equal(makeToken(4), 'xxxx')\n"
                        "  assert.equal(makeToken(8).length, 8)\n"
                        "})\n"
                        "test('handles non-integer fractional size without infinite loop', () => {\n"
                        "  assert.equal(makeToken(4.5), 'xxxx')\n"
                        "})\n"
                    ),
                },
            )
            out = model.solve(
                "Fix failing JS test test/tok.test.js",
                mode="EPISTEMIC",
                inputs={"workspace": str(root), "test_targets": ["test/tok.test.js"], "memory": mem, "timeout_s": 18.0},
            )
            er = out["epistemic_result"]
            self.assertEqual(er["status"], "VERIFIED", er)
            self.assertEqual(er["model_calls"], 0)
            self.assertEqual(er["parameters_stored"], 0)
            w = er["swe_result"]["winner"]
            self.assertEqual(w["tier"], "JS_OE_SYGUS_EUSOLVER")
            lid = w.get("learned_law_id")
            self.assertTrue(lid and lid in mem["js_rewrite_laws"])
            # Instant unlearning
            self.assertTrue(UEK.delete_memory_entry(mem, lid))
            self.assertNotIn(lid, mem["js_rewrite_laws"])

    def test_04_end_to_end_python_eusolver_compound_guard_frontdoor(self) -> None:
        """Python function lacking a compound `(x < 0 or not isinstance(x, int))` validation guard."""
        model = open_model()
        with tempfile.TemporaryDirectory(prefix="brain_oesygus_py_") as td:
            root = pathlib.Path(td)
            _write_files(
                root,
                {
                    "calc.py": (
                        "def repeat_unit(n):\n"
                        "    return 'u' * int(n)\n"
                    ),
                    "test_calc.py": (
                        "import pytest\n"
                        "from calc import repeat_unit\n\n"
                        "def test_valid_counts():\n"
                        "    assert repeat_unit(0) == ''\n"
                        "    assert repeat_unit(3) == 'uuu'\n"
                        "    assert repeat_unit(5) == 'uuuuu'\n\n"
                        "def test_rejects_negative():\n"
                        "    with pytest.raises(ValueError):\n"
                        "        repeat_unit(-2)\n\n"
                        "def test_rejects_fractional():\n"
                        "    with pytest.raises(ValueError):\n"
                        "        repeat_unit(2.5)\n"
                    ),
                },
            )
            out = model.solve(
                "Fix failing pytest test_calc.py",
                mode="EPISTEMIC",
                inputs={"workspace": str(root), "timeout_s": 25.0},
            )
            er = out["epistemic_result"]
            self.assertEqual(er["status"], "VERIFIED", er)
            self.assertEqual(er["model_calls"], 0)
            self.assertEqual(er["parameters_stored"], 0)
            patched = (root / "calc.py").read_text(encoding="utf-8")
            self.assertIn("ValueError", patched)
            self.assertIn("isinstance", patched)

    def test_05_c_execution_guided_oe_sygus_eusolver_and_instant_unlearning(self) -> None:
        """Iter 47: Execution-guided C OE-SyGuS + EUSolver synthesizes a relational
        precondition guard (`offset >= count` / `offset < 0`) from live C execution traces
        through ONE Front Door, distills a Plotkin C law, and instantly unlearns it."""
        model = open_model()
        mem = UEK.new_universal_memory()
        with tempfile.TemporaryDirectory(prefix="brain_oesygus_c_") as td:
            root = pathlib.Path(td)
            _write_files(
                root,
                {
                    "slice_sum.h": "#pragma once\nint slice_sum(const int *arr, int count, int offset);\n",
                    "slice_sum.c": (
                        '#include "slice_sum.h"\n'
                        "int slice_sum(const int *arr, int count, int offset) {\n"
                        "    int total = 0;\n"
                        "    int i;\n"
                        "    for (i = offset; i < count; i++) {\n"
                        "        total += arr[i];\n"
                        "    }\n"
                        "    return total;\n"
                        "}\n"
                    ),
                    "test_slice.c": (
                        '#include <assert.h>\n#include "slice_sum.h"\n'
                        "int main(void) {\n"
                        "    int data[4] = {10, 20, 30, 40};\n"
                        "    assert(slice_sum(data, 4, 0) == 100);\n"
                        "    assert(slice_sum(data, 4, 2) == 70);\n"
                        "    assert(slice_sum(data, 3, 1) == 50);\n"
                        "    assert(slice_sum(data, 4, 4) == -1);\n"
                        "    return 0;\n"
                        "}\n"
                    ),
                },
            )
            out = model.solve(
                "Fix failing C test test_slice.c",
                mode="EPISTEMIC",
                inputs={"workspace": str(root), "memory": mem, "timeout_s": 30.0},
            )
            self.assertTrue(out["pass"], out)
            er = out["epistemic_result"]
            self.assertEqual(er["status"], "VERIFIED", er)
            self.assertEqual(er["model_calls"], 0)
            self.assertEqual(er["parameters_stored"], 0)
            swe = er["swe_result"]
            self.assertEqual(swe["winner"]["tier"], "C_OE_SYGUS_EUSOLVER", swe)
            law_id = swe["winner"]["learned_law_id"]
            self.assertIsNotNone(law_id)
            self.assertIn(law_id, mem["c_rewrite_laws"])
            # Instant unlearning verification
            self.assertTrue(UEK.delete_memory_entry(mem, law_id))
            self.assertNotIn(law_id, mem["c_rewrite_laws"])

    def test_06_python_inbody_s3_preserving_oe_sygus_branch_repair(self) -> None:
        """Iter 47: S3-preserving OE-SyGuS/EUSolver strengthens a side-effecting interior `if`
        branch using a zero-magic-number relational predicate (`limit <= used`) rather than an
        overfitting unary threshold (`used > 5`), and passes unseen holdout inputs."""
        import importlib.util

        model = open_model()
        with tempfile.TemporaryDirectory(prefix="brain_oesygus_py_s3_") as td:
            root = pathlib.Path(td)
            _write_files(
                root,
                {
                    "ledger.py": (
                        "def apply_bonus(balance, used, limit, active):\n"
                        "    out = balance\n"
                        "    if active:\n"
                        "        out += 50\n"
                        "    return out * 2\n"
                    ),
                    "test_ledger.py": (
                        "from ledger import apply_bonus\n\n"
                        "def test_ok1():\n"
                        "    assert apply_bonus(10, 3, 10, True) == 120\n\n"
                        "def test_ok2():\n"
                        "    assert apply_bonus(20, 5, 8, True) == 140\n\n"
                        "def test_inactive():\n"
                        "    assert apply_bonus(10, 2, 5, False) == 20\n\n"
                        "def test_over_limit_1():\n"
                        "    assert apply_bonus(10, 10, 10, True) == 20\n\n"
                        "def test_over_limit_2():\n"
                        "    assert apply_bonus(20, 12, 8, True) == 40\n"
                    ),
                },
            )
            out = model.solve(
                "Fix failing pytest test_ledger.py",
                mode="EPISTEMIC",
                inputs={"workspace": str(root), "timeout_s": 25.0},
            )
            self.assertTrue(out["pass"], out)
            er = out["epistemic_result"]
            self.assertEqual(er["status"], "VERIFIED", er)
            self.assertEqual(er["model_calls"], 0)
            self.assertEqual(er["parameters_stored"], 0)
            fix_desc = str((er.get("swe_result") or {}).get("fix") or "")
            self.assertTrue(fix_desc.startswith("oe_sygus_"), fix_desc)
            patched = (root / "ledger.py").read_text(encoding="utf-8")
            # S3 preservation: original `active` condition MUST remain intact!
            self.assertIn("active", patched)
            self.assertTrue("used" in patched and "limit" in patched, patched)
            # Zero-overfitting holdout generalization proof (fails under `used > 5`!):
            spec = importlib.util.spec_from_file_location("ledger_holdout", root / "ledger.py")
            assert spec is not None and spec.loader is not None
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            self.assertEqual(mod.apply_bonus(10, 7, 10, True), 120)
            self.assertEqual(mod.apply_bonus(10, 4, 4, True), 20)
            self.assertEqual(mod.apply_bonus(10, 99, 100, True), 120)
            self.assertEqual(mod.apply_bonus(10, 100, 100, True), 20)

    def test_07_python_did_not_raise_oe_sygus_nan_decimal_validation_guard(self) -> None:
        """Iter 48: Universal `DID NOT RAISE ValueError` OE-SyGuS validation guard synthesis
        handles float('nan'), negative float, Decimal('-1'), and parsed string sizes while
        staying type-safe on polymorphic inputs (str, None, bool, datetime.time)."""
        import datetime
        from decimal import Decimal
        import importlib.util

        model = open_model()
        with tempfile.TemporaryDirectory(prefix="brain_oesygus_dnr_") as td:
            root = pathlib.Path(td)
            _write_files(
                root,
                {
                    "sizer.py": (
                        "def parse_limit(limit):\n"
                        "    if isinstance(limit, str):\n"
                        "        limit = float(limit.replace('KB', '').strip()) * 1024\n"
                        "    if limit is None or isinstance(limit, bool):\n"
                        "        return None\n"
                        "    if hasattr(limit, 'hour'):\n"
                        "        return ('time', limit.hour)\n"
                        "    return ('size', limit)\n"
                    ),
                    "test_sizer.py": (
                        "import datetime\n"
                        "from decimal import Decimal\n"
                        "import pytest\n"
                        "from sizer import parse_limit\n\n"
                        "def test_valid_limits():\n"
                        "    assert parse_limit(100) == ('size', 100)\n"
                        "    assert parse_limit(0) == ('size', 0)\n"
                        "    assert parse_limit('2 KB') == ('size', 2048.0)\n"
                        "    assert parse_limit(None) is None\n"
                        "    assert parse_limit(False) is None\n"
                        "    assert parse_limit(datetime.time(12, 0)) == ('time', 12)\n\n"
                        "@pytest.mark.parametrize('bad', [-0.5, '-2 KB', float('nan'), Decimal('-1')])\n"
                        "def test_invalid_limits(bad):\n"
                        "    with pytest.raises(ValueError, match=r'^Invalid size limit'):\n"
                        "        parse_limit(bad)\n"
                    ),
                },
            )
            out = model.solve(
                "Fix failing pytest test_sizer.py",
                mode="EPISTEMIC",
                inputs={"workspace": str(root), "timeout_s": 25.0},
            )
            self.assertTrue(out["pass"], out)
            er = out["epistemic_result"]
            self.assertEqual(er["status"], "VERIFIED", er)
            self.assertEqual(er["model_calls"], 0)
            self.assertEqual(er["parameters_stored"], 0)
            fix_desc = str((er.get("swe_result") or {}).get("fix") or "")
            self.assertTrue(fix_desc.startswith("oe_sygus_validation_raise("), fix_desc)
            # Unseen holdout verification (Decimal('NaN'), -999, valid Decimal('5'), datetime.time)
            spec = importlib.util.spec_from_file_location("sizer_holdout", root / "sizer.py")
            assert spec is not None and spec.loader is not None
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            self.assertEqual(mod.parse_limit(Decimal("5")), ("size", Decimal("5")))
            self.assertEqual(mod.parse_limit(datetime.time(8, 30)), ("time", 8))
            with self.assertRaises(ValueError):
                mod.parse_limit(Decimal("NaN"))
            with self.assertRaises(ValueError):
                mod.parse_limit(-999)


if __name__ == "__main__":
    unittest.main()
