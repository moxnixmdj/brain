"""Unit & cross-repo transfer tests for `polyglot_cst_skill_inducer_v1.py`.

Proves zero-LLM (`model_calls == 0`), zero-weight (`parameters_stored == 0`)
single-experience executable coding skill induction across C and JavaScript:
  1. Never-hardcoded C CWE-190 saturating-add skill: UNSOLVED before learning ->
     admit from ONE unrelated 4-line example (zero concrete name leakage) ->
     VERIFIED on ATTEMPT #1 in unseen C repo with different identifiers ->
     immediately UNSOLVED again after deleting the 1 JSON entry.
  2. Never-hardcoded JS null-prototype `Object.prototype.hasOwnProperty.call`:
     False before learning -> VERIFIED on ATTEMPT #1 after 1 experience.
  3. Relational sibling hole induction (`foo_lwr_cp` -> `foo_upr_cp` transferring
     to `to_lwr_ch` -> `to_upr_ch` only when target sibling exists).
  4. Fail-closed foreign-identifier refusal + online counterexample narrowing +
     external JSON persistence.
"""
from __future__ import annotations

import json
import pathlib
import tempfile
import unittest

from canonical.runtime import multilang_causal_swe_engine_v1 as ML_SWE
from canonical.runtime import polyglot_cst_skill_inducer_v1 as CST


class PolyglotCstSkillInducerV1Tests(unittest.TestCase):
    def test_01_c_single_experience_learn_transfer_and_immediate_forget(self) -> None:
        exp_before = (
            "#include <limits.h>\n"
            "int sat_add(int lhs, int rhs) {\n"
            "    return lhs + rhs;\n"
            "}\n"
        )
        exp_after = (
            "#include <limits.h>\n"
            "int sat_add(int lhs, int rhs) {\n"
            "    if (rhs > 0 && lhs > INT_MAX - rhs) return INT_MAX;\n"
            "    return lhs + rhs;\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(prefix="cst_test_c_") as td:
            root = pathlib.Path(td)
            (root / "tests").mkdir()
            (root / "quota.c").write_text(
                "#include <limits.h>\n"
                "int add_quota(int used, int delta) {\n"
                "    return used + delta;\n"
                "}\n",
                encoding="utf-8",
            )
            (root / "tests" / "test_quota.c").write_text(
                "#include <assert.h>\n"
                "#include <limits.h>\n"
                "int add_quota(int used, int delta);\n"
                "int main(void) {\n"
                "    assert(add_quota(10, 20) == 30);\n"
                "    assert(add_quota(INT_MAX - 5, 100) == INT_MAX);\n"
                "    return 0;\n"
                "}\n",
                encoding="utf-8",
            )

            # Empty memory fails (proves bug class is NOT hardcoded)
            r0 = ML_SWE.solve_c_repository(root, ["tests/test_quota.c"], memory={}, max_candidates=10, timeout_s=20.0)
            self.assertNotEqual(r0["status"], "VERIFIED")

            # Learn from ONE unrelated experience; assert zero concrete name leakage
            store = CST.new_cst_store()
            adm = CST.admit_cst_skill(store, exp_before, exp_after, language="c")
            self.assertTrue(adm["admitted"], adm)
            raw_sk = json.dumps(adm["skill"])
            for concrete in ("lhs", "rhs", "sat_add"):
                self.assertNotIn(concrete, raw_sk)

            # Persist to external JSON and reload
            store_path = root / "cst_store.json"
            CST.save_cst_store(store, store_path)
            loaded = CST.load_cst_store(store_path)
            self.assertEqual(loaded["parameters_stored"], 0)
            self.assertFalse(loaded["external_model_dependency"])

            # Solve unseen C repo on Attempt #1 via learned CST skill
            r1 = ML_SWE.solve_c_repository(
                root, ["tests/test_quota.c"], memory={"polyglot_cst_skills": loaded}, max_candidates=10, timeout_s=20.0
            )
            self.assertEqual(r1["status"], "VERIFIED", r1)
            self.assertEqual(r1["winner"]["tier"], "C_CST_TIER0_LEARNED_SKILL")
            self.assertEqual(r1["winner"]["attempt"], 1)
            self.assertEqual(r1["model_calls"], 0)
            self.assertEqual(r1["parameters_stored"], 0)

            # Delete JSON entry -> immediate forgetting
            self.assertTrue(CST.delete_cst_skill(loaded, adm["skill_id"]))
            r2 = ML_SWE.solve_c_repository(
                root, ["tests/test_quota.c"], memory={"polyglot_cst_skills": loaded}, max_candidates=10, timeout_s=20.0
            )
            self.assertNotEqual(r2["status"], "VERIFIED")

    def test_02_js_single_experience_learn_and_transfer(self) -> None:
        js_b = "function hasField(bag, field) {\n  return bag.hasOwnProperty(field);\n}\n"
        js_a = "function hasField(bag, field) {\n  return Object.prototype.hasOwnProperty.call(bag, field);\n}\n"
        with tempfile.TemporaryDirectory(prefix="cst_test_js_") as td:
            root = pathlib.Path(td)
            (root / "lookup.js").write_text(
                "function containsKey(records, name) {\n"
                "  return records.hasOwnProperty(name);\n"
                "}\n"
                "module.exports = { containsKey };\n",
                encoding="utf-8",
            )
            (root / "test_lookup.js").write_text(
                "const test = require('node:test');\n"
                "const assert = require('node:assert/strict');\n"
                "const { containsKey } = require('./lookup.js');\n"
                "test('null-proto safe lookup', () => {\n"
                "  const m = Object.create(null); m.k = 1;\n"
                "  assert.strictEqual(containsKey(m, 'k'), true);\n"
                "  assert.strictEqual(containsKey(m, 'z'), false);\n"
                "});\n",
                encoding="utf-8",
            )
            r0 = ML_SWE.solve_js_repository(root, ["test_lookup.js"], memory={}, max_candidates=10, timeout_s=20.0)
            self.assertFalse(r0["verified"])

            store = CST.new_cst_store()
            adm = CST.admit_cst_skill(store, js_b, js_a, language="js")
            self.assertTrue(adm["admitted"], adm)
            self.assertNotIn("bag", json.dumps(adm["skill"]))
            self.assertNotIn("field", json.dumps(adm["skill"]))

            r1 = ML_SWE.solve_js_repository(
                root, ["test_lookup.js"], memory={"polyglot_cst_skills": store}, max_candidates=10, timeout_s=20.0
            )
            self.assertTrue(r1["verified"], r1)
            self.assertEqual(r1["winner"]["tier"], "JS_CST_TIER0_LEARNED_SKILL")
            self.assertEqual(r1["winner"]["attempt"], 1)
            self.assertEqual(r1["model_calls"], 0)

    def test_03_relational_sibling_hole_foreign_refusal_and_counterexample_narrowing(self) -> None:
        # 1. Foreign unbound identifier refused fail-closed
        bad = CST.induce_cst_skill(
            "int f(int x) { return x; }\n",
            "int f(int x) { return secret_repo_helper(x); }\n",
            language="c",
        )
        self.assertFalse(bad["admitted"])
        self.assertIn("FOREIGN_IDENT_UNBOUND", bad["reason"])

        # 2. Relational sibling hole (`foo_lwr_cp` -> `foo_upr_cp` transfers to `to_lwr_ch` -> `to_upr_ch`)
        rel_b = (
            "int foo_lwr_cp(int);\nint foo_upr_cp(int);\n"
            "int eq(int x, int y) {\n  if (foo_lwr_cp(x) != foo_lwr_cp(y)) return 0;\n  return 1;\n}\n"
        )
        rel_a = (
            "int foo_lwr_cp(int);\nint foo_upr_cp(int);\n"
            "int eq(int x, int y) {\n  if ((foo_lwr_cp(x) != foo_lwr_cp(y)) && (foo_upr_cp(x) != foo_upr_cp(y))) return 0;\n  return 1;\n}\n"
        )
        store = CST.new_cst_store()
        adm = CST.admit_cst_skill(store, rel_b, rel_a, language="c")
        self.assertTrue(adm["admitted"], adm)
        self.assertTrue(adm["skill"]["relational_holes"])

        target_ok = (
            "int to_lwr_ch(int c);\nint to_upr_ch(int c);\n"
            "int same(int p, int q) {\n  if (to_lwr_ch(p) != to_lwr_ch(q)) return 0;\n  return 1;\n}\n"
        )
        ms = CST.recall_cst_candidates(store, target_ok, language="c")
        self.assertTrue(ms)
        self.assertIn("to_upr_ch(p) != to_upr_ch(q)", ms[0]["patched_source"])

        # 3. Online counterexample narrowing skips non-matching files, preserves matching files
        ce = CST.record_cst_counterexample(store, adm["skill_id"], distinguishing_token="to_upr_ch")
        self.assertEqual(ce["status"], CST.STATUS_NARROWED)
        self.assertTrue(CST.recall_cst_candidates(store, target_ok, language="c"))
        other = (
            "int x_lwr_fn(int c);\nint x_upr_fn(int c);\n"
            "int same(int p, int q) {\n  if (x_lwr_fn(p) != x_lwr_fn(q)) return 0;\n  return 1;\n}\n"
        )
        self.assertEqual(CST.recall_cst_candidates(store, other, language="c"), [])

        # 4. Unseparable counterexample quarantines skill fail-closed
        q = CST.record_cst_counterexample(store, adm["skill_id"])
        self.assertEqual(q["status"], CST.STATUS_QUARANTINED)
        self.assertEqual(CST.recall_cst_candidates(store, target_ok, language="c"), [])


if __name__ == "__main__":
    unittest.main()
