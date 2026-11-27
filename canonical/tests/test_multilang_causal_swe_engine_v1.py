"""Tests for Multi-Language Causal Angelic SWE Engine v1 (JavaScript / TypeScript / Node.js)
and its unified dispatch + Tier-0 cross-repo skill transfer via `open_model().solve(..., mode="EPISTEMIC")`.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import tempfile
import unittest

from canonical.runtime.brain_unified_model_v1 import open_model
from canonical.runtime import multilang_causal_swe_engine_v1 as ML_SWE
from canonical.runtime import universal_epistemic_kernel_v1 as UEK


def _write_files(root: pathlib.Path, files: dict[str, str]) -> None:
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")


class TestMultiLangCausalSWEEngineV1(unittest.TestCase):
    def test_v8_cov_localization_and_all_core_js_operators(self) -> None:
        cases = [
            (
                "regex_signed_decimal",
                "JS_REGEX_LITERAL_REPAIR",
                {
                    "package.json": '{"name":"dur","scripts":{"test":"node --test"}}\n',
                    "parse.js": (
                        "function parseDuration(str) {\n"
                        "  const m = /^((?:\\d+)?-?(?:\\d+)?\\.?\\d+) *(s|ms)?$/i.exec(str);\n"
                        "  if (!m) return NaN;\n"
                        "  const n = parseFloat(m[1]);\n"
                        "  return (m[2] || 'ms') === 's' ? n * 1000 : n;\n"
                        "}\n"
                        "module.exports = { parseDuration };\n"
                    ),
                    "parse.test.js": (
                        "const test = require('node:test');\n"
                        "const assert = require('node:assert/strict');\n"
                        "const { parseDuration } = require('./parse.js');\n"
                        "test('negative decimals and invalid mid-sign', () => {\n"
                        "  assert.equal(parseDuration('-10.5s'), -10500);\n"
                        "  assert.equal(parseDuration('2.5s'), 2500);\n"
                        "  assert.equal(Number.isNaN(parseDuration('10-5s')), true);\n"
                        "});\n"
                    ),
                },
            ),
            (
                "empty_string_ternary_unwrap",
                "JS_TRUTHINESS_AND_EMPTY_GUARD",
                {
                    "package.json": '{"name":"enc","scripts":{"test":"node --test"}}\n',
                    "fmt.js": (
                        "function formatPair(k, v, enc) {\n"
                        "  const out = v ? enc(v) : '';\n"
                        "  return k + '=' + out;\n"
                        "}\n"
                        "module.exports = { formatPair };\n"
                    ),
                    "fmt.test.js": (
                        "const test = require('node:test');\n"
                        "const assert = require('node:assert/strict');\n"
                        "const { formatPair } = require('./fmt.js');\n"
                        "test('applies encoder to empty string', () => {\n"
                        "  const wrap = (s) => '[' + s + ']';\n"
                        "  assert.equal(formatPair('a', '1', wrap), 'a=[1]');\n"
                        "  assert.equal(formatPair('a', '', wrap), 'a=[]');\n"
                        "});\n"
                    ),
                },
            ),
            (
                "leading_delimiter_loop_index_guard",
                "JS_LEADING_DELIM_ACCUM_REPAIR",
                {
                    "package.json": '{"name":"joiner","scripts":{"test":"node --test"}}\n',
                    "joiner.js": (
                        "function joinHeader(obj) {\n"
                        "  const keys = Object.keys(obj);\n"
                        "  let str = '';\n"
                        "  for (let i = 0; i < keys.length; i++) {\n"
                        "    const k = keys[i];\n"
                        "    const v = obj[k];\n"
                        "    if (v === undefined) continue;\n"
                        "    if (i > 0) str += '; ';\n"
                        "    str += k + '=' + v;\n"
                        "  }\n"
                        "  return str;\n"
                        "}\n"
                        "module.exports = { joinHeader };\n"
                    ),
                    "joiner.test.js": (
                        "const test = require('node:test');\n"
                        "const assert = require('node:assert/strict');\n"
                        "const { joinHeader } = require('./joiner.js');\n"
                        "test('omits leading delimiter when first key is undefined', () => {\n"
                        "  assert.equal(joinHeader({ a: '1', b: '2' }), 'a=1; b=2');\n"
                        "  assert.equal(joinHeader({ a: undefined, b: '2' }), 'b=2');\n"
                        "});\n"
                    ),
                },
            ),
            (
                "dynamic_options_flag_override",
                "JS_OPTIONS_FLAG_OVERRIDE",
                {
                    "package.json": '{"name":"opts","scripts":{"test":"node --test"}}\n',
                    "checker.js": (
                        "function checkLeaf(val, limit, options) {\n"
                        "  if (val.pre && !options.allowPre) return false;\n"
                        "  return val.n < limit;\n"
                        "}\n"
                        "function checkRange(val, limit, options = {}) {\n"
                        "  const needTuple = val.pre && !options.allowPre;\n"
                        "  if (val.kind === 'ge' && !checkLeaf(val, limit, options)) {\n"
                        "    return false;\n"
                        "  }\n"
                        "  if (needTuple && !val.matched) return false;\n"
                        "  return true;\n"
                        "}\n"
                        "module.exports = { checkRange };\n"
                    ),
                    "checker.test.js": (
                        "const test = require('node:test');\n"
                        "const assert = require('node:assert/strict');\n"
                        "const { checkRange } = require('./checker.js');\n"
                        "test('checks bound with allowPre when tuple already verified', () => {\n"
                        "  assert.equal(checkRange({ kind: 'ge', n: 5, pre: true, matched: true }, 10), true);\n"
                        "  assert.equal(checkRange({ kind: 'ge', n: 5, pre: true, matched: false }, 10), false);\n"
                        "  assert.equal(checkRange({ kind: 'ge', n: 12, pre: true, matched: true }, 10), false);\n"
                        "});\n"
                    ),
                },
            ),
        ]

        for name, expected_tier, files in cases:
            with self.subTest(case=name):
                with tempfile.TemporaryDirectory(prefix=f"brain_js_{name}_") as td:
                    root = pathlib.Path(td)
                    _write_files(root, files)
                    res = ML_SWE.solve_js_repository(root, timeout_s=20.0)
                    self.assertEqual(res["status"], "VERIFIED", f"{name}: {res}")
                    self.assertEqual(res["model_calls"], 0)
                    self.assertEqual(res["parameters_stored"], 0)
                    self.assertEqual(res["winner"]["tier"], expected_tier)

    def test_one_front_door_js_dispatch_and_cross_repo_tier0_skill_transfer(self) -> None:
        model = open_model()
        mem = UEK.new_universal_memory()

        with tempfile.TemporaryDirectory(prefix="brain_js_transfer_") as td:
            td_p = pathlib.Path(td)
            repo_a = td_p / "alpha_metrics"
            _write_files(
                repo_a,
                {
                    "package.json": '{"name":"alpha-metrics","scripts":{"test":"node --test"}}\n',
                    "metrics.js": (
                        "function encodeMetric(val) {\n"
                        "  if (typeof val === 'number' && isNaN(val) === false) {\n"
                        "    return String(val);\n"
                        "  }\n"
                        "  throw new TypeError('bad metric');\n"
                        "}\n"
                        "module.exports = { encodeMetric };\n"
                    ),
                    "metrics.test.js": (
                        "const test = require('node:test');\n"
                        "const assert = require('node:assert/strict');\n"
                        "const { encodeMetric } = require('./metrics.js');\n"
                        "test('rejects non-finite numbers', () => {\n"
                        "  assert.equal(encodeMetric(42), '42');\n"
                        "  assert.throws(() => encodeMetric(Infinity), TypeError);\n"
                        "  assert.throws(() => encodeMetric(-Infinity), TypeError);\n"
                        "  assert.throws(() => encodeMetric(NaN), TypeError);\n"
                        "});\n"
                    ),
                },
            )

            r1 = model.solve(
                "Fix the failing test in metrics.test.js",
                mode="EPISTEMIC",
                inputs={"workspace": str(repo_a), "memory": mem},
            )
            er1 = r1["epistemic_result"]
            self.assertEqual(er1["status"], "VERIFIED")
            self.assertEqual(er1["modality"], "swe_js_codebase")
            self.assertEqual(er1["model_calls"], 0)
            self.assertEqual(er1["parameters_stored"], 0)
            self.assertGreaterEqual(len(mem["js_rewrite_laws"]), 1)

            # Inspectable external law must contain zero workspace paths or concrete names
            law_json = json.dumps(mem["js_rewrite_laws"])
            self.assertNotIn("alpha_metrics", law_json)
            self.assertNotIn("/tmp/", law_json)
            self.assertNotIn("encodeMetric", law_json)

            # Completely unseen repo B with different filename & variable name -> Tier-0 Attempt #1!
            repo_b = td_p / "beta_ledger"
            _write_files(
                repo_b,
                {
                    "package.json": '{"name":"beta-ledger","scripts":{"test":"node --test"}}\n',
                    "ledger.js": (
                        "function formatBalance(balance) {\n"
                        "  if (typeof balance === 'number' && isNaN(balance) === false) {\n"
                        "    return '$' + balance.toFixed(2);\n"
                        "  }\n"
                        "  throw new RangeError('invalid balance');\n"
                        "}\n"
                        "module.exports = { formatBalance };\n"
                    ),
                    "ledger.test.js": (
                        "const test = require('node:test');\n"
                        "const assert = require('node:assert/strict');\n"
                        "const { formatBalance } = require('./ledger.js');\n"
                        "test('rejects Infinity balance', () => {\n"
                        "  assert.equal(formatBalance(7.5), '$7.50');\n"
                        "  assert.throws(() => formatBalance(Infinity), RangeError);\n"
                        "  assert.throws(() => formatBalance(NaN), RangeError);\n"
                        "});\n"
                    ),
                },
            )

            r2 = model.solve(
                "Fix the failing test in ledger.test.js",
                mode="EPISTEMIC",
                inputs={"workspace": str(repo_b), "memory": mem},
            )
            er2 = r2["epistemic_result"]
            self.assertEqual(er2["status"], "VERIFIED")
            self.assertEqual(er2["modality"], "swe_js_codebase")
            self.assertEqual(er2["mode"], "TIER0_JS_SKILL_RECALL")
            self.assertEqual(er2["swe_result"]["winner"]["tier"], "JS_TIER0_SKILL_RECALL")
            self.assertEqual(er2["swe_result"]["winner"]["attempt"], 1)
            self.assertEqual(er2["model_calls"], 0)
            self.assertEqual(er2["parameters_stored"], 0)

    def test_c_asan_null_deref_uaf_disjunct_sibling_and_tier0_transfer(self) -> None:
        cases = [
            (
                "c_null_deref_entry_guard",
                "C_NULL_PTR_DEREF_GUARD",
                {
                    "box.h": "typedef struct { int val; double dval; } Box;\ndouble set_box(Box *b, double n);\n",
                    "box.c": (
                        "#include <stddef.h>\n"
                        "#include <math.h>\n"
                        "#include \"box.h\"\n"
                        "double set_box(Box *b, double n)\n"
                        "{\n"
                        "    if (n > 100.0) { b->val = 100; }\n"
                        "    else { b->val = (int)n; }\n"
                        "    return b->dval = n;\n"
                        "}\n"
                    ),
                    "test_box.c": (
                        "#include <assert.h>\n"
                        "#include <math.h>\n"
                        "#include <stddef.h>\n"
                        "#include \"box.h\"\n"
                        "int main(void) {\n"
                        "    Box b = {0, 0.0};\n"
                        "    assert(set_box(&b, 5.0) == 5.0);\n"
                        "    assert(b.val == 5);\n"
                        "    assert(set_box(NULL, 5.0) == 0.0 || isnan(set_box(NULL, 5.0)));\n"
                        "    return 0;\n"
                        "}\n"
                    ),
                },
            ),
            (
                "c_asan_uaf_clear_index_reset",
                "C_ASAN_UAF_CLEAR_INDEX_RESET",
                {
                    "tbl.c": (
                        "#include <stdlib.h>\n"
                        "#include <string.h>\n"
                        "#define EMPTY_SLOT ((size_t)-1)\n"
                        "typedef struct {\n"
                        "    size_t cap;\n"
                        "    size_t count;\n"
                        "    size_t *slots;\n"
                        "    char **keys;\n"
                        "} Tbl;\n"
                        "Tbl *tbl_new(size_t cap) {\n"
                        "    size_t i;\n"
                        "    Tbl *t = (Tbl *)calloc(1, sizeof(Tbl));\n"
                        "    t->cap = cap;\n"
                        "    t->slots = (size_t *)malloc(cap * sizeof(size_t));\n"
                        "    t->keys = (char **)calloc(cap, sizeof(char *));\n"
                        "    for (i = 0; i < cap; i++) t->slots[i] = EMPTY_SLOT;\n"
                        "    return t;\n"
                        "}\n"
                        "void tbl_put(Tbl *t, const char *k) {\n"
                        "    size_t idx = t->count++;\n"
                        "    t->keys[idx] = (char *)malloc(strlen(k) + 1);\n"
                        "    strcpy(t->keys[idx], k);\n"
                        "    t->slots[0] = idx;\n"
                        "}\n"
                        "int tbl_has(Tbl *t, const char *k) {\n"
                        "    size_t i;\n"
                        "    for (i = 0; i < t->cap; i++) {\n"
                        "        size_t cell = t->slots[i];\n"
                        "        if (cell == EMPTY_SLOT) return 0;\n"
                        "        if (strcmp(t->keys[cell], k) == 0) return 1;\n"
                        "    }\n"
                        "    return 0;\n"
                        "}\n"
                        "void tbl_clear(Tbl *t) {\n"
                        "    size_t i;\n"
                        "    for (i = 0; i < t->count; i++) {\n"
                        "        free(t->keys[i]);\n"
                        "    }\n"
                        "    t->count = 0;\n"
                        "}\n"
                    ),
                    "test_tbl.c": (
                        "#include <assert.h>\n"
                        "#include \"tbl.c\"\n"
                        "int main(void) {\n"
                        "    Tbl *t = tbl_new(4);\n"
                        "    tbl_put(t, \"abc\");\n"
                        "    assert(tbl_has(t, \"abc\") == 1);\n"
                        "    tbl_clear(t);\n"
                        "    assert(tbl_has(t, \"abc\") == 0);\n"
                        "    return 0;\n"
                        "}\n"
                    ),
                },
            ),
            (
                "c_disjunct_condition_refinement",
                "C_DISJUNCT_CONDITION_REFINEMENT",
                {
                    "list.c": (
                        "#include <stddef.h>\n"
                        "typedef struct Node { struct Node *prev; struct Node *next; int id; } Node;\n"
                        "typedef struct { Node *child; } Parent;\n"
                        "Node *detach_node(Parent *parent, Node *item)\n"
                        "{\n"
                        "    if ((parent == NULL) || (parent->child == NULL) || (item == NULL) || (item->prev == NULL))\n"
                        "    {\n"
                        "        return NULL;\n"
                        "    }\n"
                        "    if (item != parent->child)\n"
                        "    {\n"
                        "        item->prev->next = item->next;\n"
                        "    }\n"
                        "    if (item == parent->child)\n"
                        "    {\n"
                        "        parent->child = item->next;\n"
                        "    }\n"
                        "    item->prev = NULL;\n"
                        "    item->next = NULL;\n"
                        "    return item;\n"
                        "}\n"
                    ),
                    "test_list.c": (
                        "#include <assert.h>\n"
                        "#include \"list.c\"\n"
                        "int main(void) {\n"
                        "    Node a = {NULL, NULL, 1};\n"
                        "    Node b = {NULL, NULL, 2};\n"
                        "    Parent p = {&a};\n"
                        "    a.next = &b;\n"
                        "    /* Head item with prev==NULL must still detach; middle item with prev==NULL returns NULL */\n"
                        "    assert(detach_node(&p, &b) == NULL);\n"
                        "    assert(detach_node(&p, &a) == &a);\n"
                        "    return 0;\n"
                        "}\n"
                    ),
                },
            ),
        ]

        for name, expected_tier, files in cases:
            with self.subTest(case=name):
                with tempfile.TemporaryDirectory(prefix=f"brain_c_{name}_") as td:
                    root = pathlib.Path(td)
                    _write_files(root, files)
                    res = ML_SWE.solve_c_repository(root, timeout_s=25.0)
                    self.assertEqual(res["status"], "VERIFIED", f"{name}: {res}")
                    self.assertEqual(res["model_calls"], 0)
                    self.assertEqual(res["parameters_stored"], 0)
                    self.assertEqual(res["winner"]["tier"], expected_tier)

        # End-to-end ONE front door (`open_model().solve(..., mode="EPISTEMIC")`) + Tier-0 C transfer
        model = open_model()
        mem = UEK.new_universal_memory()
        with tempfile.TemporaryDirectory(prefix="brain_c_transfer_") as td:
            td_p = pathlib.Path(td)
            c_repo_a = td_p / "c_alpha"
            _write_files(
                c_repo_a,
                {
                    "node.c": (
                        "#include <stddef.h>\n"
                        "typedef struct N { int v; struct N *next; } N;\n"
                        "void set_next_val(N *p, int x) {\n"
                        "    p->next->v = x;\n"
                        "}\n"
                    ),
                    "test_node.c": (
                        "#include <assert.h>\n"
                        "#include \"node.c\"\n"
                        "int main(void) {\n"
                        "    N b = {0, NULL};\n"
                        "    N a = {1, &b};\n"
                        "    set_next_val(&a, 7);\n"
                        "    assert(b.v == 7);\n"
                        "    set_next_val(&b, 9);\n"
                        "    return 0;\n"
                        "}\n"
                    ),
                },
            )
            r1 = model.solve(
                "Fix the NULL pointer dereference failing test_node.c",
                mode="EPISTEMIC",
                inputs={"workspace": str(c_repo_a), "memory": mem},
            )
            er1 = r1["epistemic_result"]
            self.assertEqual(er1["status"], "VERIFIED")
            self.assertEqual(er1["modality"], "swe_c_codebase")
            self.assertEqual(er1["model_calls"], 0)
            self.assertEqual(er1["parameters_stored"], 0)
            self.assertGreaterEqual(len(mem["c_rewrite_laws"]), 1)

            c_repo_b = td_p / "c_beta"
            _write_files(
                c_repo_b,
                {
                    "link.c": (
                        "#include <stddef.h>\n"
                        "typedef struct L { int count; struct L *peer; } L;\n"
                        "void bump_peer(L *head) {\n"
                        "    head->peer->count += 1;\n"
                        "}\n"
                    ),
                    "test_link.c": (
                        "#include <assert.h>\n"
                        "#include \"link.c\"\n"
                        "int main(void) {\n"
                        "    L y = {2, NULL};\n"
                        "    L x = {1, &y};\n"
                        "    bump_peer(&x);\n"
                        "    assert(y.count == 3);\n"
                        "    bump_peer(&y);\n"
                        "    return 0;\n"
                        "}\n"
                    ),
                },
            )
            r2 = model.solve(
                "Fix the NULL pointer dereference failing test_link.c",
                mode="EPISTEMIC",
                inputs={"workspace": str(c_repo_b), "memory": mem},
            )
            er2 = r2["epistemic_result"]
            self.assertEqual(er2["status"], "VERIFIED")
            self.assertEqual(er2["modality"], "swe_c_codebase")
            self.assertEqual(er2["mode"], "TIER0_C_SKILL_RECALL")
            self.assertEqual(er2["swe_result"]["winner"]["tier"], "C_TIER0_SKILL_RECALL")
            self.assertEqual(er2["model_calls"], 0)
            self.assertEqual(er2["parameters_stored"], 0)

    def test_cpp17_ubsan_sigabrt_early_return_and_memrl_quarantine(self) -> None:
        cases = [
            (
                "cpp17_ubsan_signed_abs_overflow_header_only",
                "C_UBSAN_SIGNED_OVERFLOW_GUARD",
                {
                    "include/intparse.hpp": (
                        "#pragma once\n"
                        "#include <cstdint>\n"
                        "#include <cstdlib>\n"
                        "#include <limits>\n"
                        "template <typename T>\n"
                        "uint64_t abs_min_limit() {\n"
                        "    return static_cast<uint64_t>(std::abs(static_cast<intmax_t>((std::numeric_limits<T>::min)())));\n"
                        "}\n"
                    ),
                    "test_intparse.cpp": (
                        "#include <cassert>\n"
                        "#include <cstdint>\n"
                        "#include \"intparse.hpp\"\n"
                        "int main() {\n"
                        "    assert(abs_min_limit<int32_t>() == 2147483648ULL);\n"
                        "    assert(abs_min_limit<int64_t>() == 9223372036854775808ULL);\n"
                        "    return 0;\n"
                        "}\n"
                    ),
                },
            ),
            (
                "cpp17_sigabrt_assert_caller_null_guard",
                "C_SIGABRT_NULL_ARG_GUARD",
                {
                    "vars.cpp": (
                        "#include <cassert>\n"
                        "#include <cstring>\n"
                        "struct StrVar {\n"
                        "    const char* value;\n"
                        "    bool set(const char* s) {\n"
                        "        assert(s);\n"
                        "        value = s;\n"
                        "        return std::strlen(s) >= 0;\n"
                        "    }\n"
                        "};\n"
                        "bool copy_var(StrVar* lhs, const StrVar* rhs) {\n"
                        "    return lhs->set(rhs->value);\n"
                        "}\n"
                    ),
                    "test_vars.cpp": (
                        "#include <cassert>\n"
                        "struct StrVar { const char* value; bool set(const char* s); };\n"
                        "bool copy_var(StrVar* lhs, const StrVar* rhs);\n"
                        "int main() {\n"
                        "    StrVar a{\"hi\"}, b{nullptr}, out{nullptr};\n"
                        "    assert(copy_var(&out, &a) && out.value[0] == 'h');\n"
                        "    StrVar out2{nullptr};\n"
                        "    assert(copy_var(&out2, &b));\n"
                        "    return 0;\n"
                        "}\n"
                    ),
                },
            ),
            (
                "cpp17_early_return_field_propagation",
                "C_EARLY_RETURN_FIELD_PROPAGATION",
                {
                    "loader.cpp": (
                        "#include <cstddef>\n"
                        "enum Enc { enc_auto = 0, enc_utf8 = 1 };\n"
                        "struct ParseRes { int status; Enc encoding; };\n"
                        "ParseRes make_res(int st) { return ParseRes{st, enc_auto}; }\n"
                        "ParseRes load_buf(const char* data, size_t n) {\n"
                        "    Enc detected_encoding = enc_utf8;\n"
                        "    if (n == 0) return make_res(0);\n"
                        "    ParseRes res = make_res(data[0] ? 0 : 1);\n"
                        "    res.encoding = detected_encoding;\n"
                        "    return res;\n"
                        "}\n"
                    ),
                    "test_loader.cpp": (
                        "#include <cstdio>\n"
                        "#include <cstddef>\n"
                        "enum Enc { enc_auto = 0, enc_utf8 = 1 };\n"
                        "struct ParseRes { int status; Enc encoding; };\n"
                        "ParseRes load_buf(const char* data, size_t n);\n"
                        "int main() {\n"
                        "    ParseRes result = load_buf(nullptr, 0);\n"
                        "    if (!(result.encoding == enc_utf8)) {\n"
                        "        std::printf(\"Test load_buf_empty failed: result.encoding == enc_utf8 is false at test_loader.cpp:9\\n\");\n"
                        "        return 1;\n"
                        "    }\n"
                        "    return 0;\n"
                        "}\n"
                    ),
                },
            ),
        ]

        mem = UEK.new_universal_memory()
        for name, expected_tier, files in cases:
            with self.subTest(case=name):
                with tempfile.TemporaryDirectory(prefix=f"brain_cpp_{name}_") as td:
                    root = pathlib.Path(td)
                    _write_files(root, files)
                    res = ML_SWE.solve_c_repository(root, memory=mem, timeout_s=30.0)
                    self.assertEqual(res["status"], "VERIFIED", f"{name}: {res}")
                    self.assertEqual(res["model_calls"], 0)
                    self.assertEqual(res["parameters_stored"], 0)
                    self.assertEqual(res["winner"]["tier"], expected_tier)

        # Verify MemRL Q-value decay -> automatic quarantine -> compress_and_prune_memory eviction
        self.assertGreaterEqual(len(mem["c_rewrite_laws"]), 3)
        sample_lid = next(iter(mem["c_rewrite_laws"]))
        ML_SWE._update_memrl_law(mem["c_rewrite_laws"], sample_lid, success=False)
        self.assertEqual(mem["c_rewrite_laws"][sample_lid]["status"], "ACTIVE")
        ML_SWE._update_memrl_law(mem["c_rewrite_laws"], sample_lid, success=False)
        self.assertEqual(mem["c_rewrite_laws"][sample_lid]["status"], "QUARANTINED")
        prune_stats = UEK.compress_and_prune_memory(mem)
        self.assertEqual(prune_stats["pruned_multilang_laws"], 1)
        self.assertNotIn(sample_lid, mem["c_rewrite_laws"])

    def test_iter27_js_coupled_sibling_template_sync_and_python_laws_51_52(self) -> None:
        # 1. JS intra-block coupled `${z}` drop across sibling branches
        with self.subTest(case="js_coupled_intra_block_drop"):
            with tempfile.TemporaryDirectory(prefix="brain_js_sync_a_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "package.json": '{"name": "rng-a", "version": "1.0.0"}\n',
                        "lib/range.js": (
                            "'use strict'\n"
                            "const fmtRange = (M, m, p, options) => {\n"
                            "  const z = options.includePrerelease ? '-0' : ''\n"
                            "  let ret\n"
                            "  if (m === 'x') {\n"
                            "    ret = `>=${M}.0.0${z} <${+M + 1}.0.0-0`\n"
                            "  } else {\n"
                            "    if (M === '0') {\n"
                            "      if (m === '0') {\n"
                            "        ret = `>=${M}.${m}.${p}${z} <${M}.${m}.${+p + 1}-0`\n"
                            "      } else {\n"
                            "        ret = `>=${M}.${m}.${p}${z} <${M}.${+m + 1}.0-0`\n"
                            "      }\n"
                            "    } else {\n"
                            "      ret = `>=${M}.${m}.${p} <${+M + 1}.0.0-0`\n"
                            "    }\n"
                            "  }\n"
                            "  return ret\n"
                            "}\n"
                            "module.exports = { fmtRange }\n"
                        ),
                        "test/range.test.js": (
                            "const assert = require('assert')\n"
                            "const { fmtRange } = require('../lib/range')\n"
                            "assert.strictEqual(fmtRange('1', 'x', 'x', { includePrerelease: true }), '>=1.0.0-0 <2.0.0-0')\n"
                            "assert.strictEqual(fmtRange('0', '0', '3', { includePrerelease: true }), '>=0.0.3 <0.0.4-0')\n"
                            "assert.strictEqual(fmtRange('0', '2', '3', { includePrerelease: true }), '>=0.2.3 <0.3.0-0')\n"
                            "assert.strictEqual(fmtRange('1', '2', '3', { includePrerelease: true }), '>=1.2.3 <2.0.0-0')\n"
                        ),
                    },
                )
                res = ML_SWE.solve_js_repository(root, ["test/range.test.js"], timeout_s=20.0)
                self.assertEqual(res["status"], "VERIFIED", res)
                self.assertEqual(res["winner"]["tier"], "JS_COUPLED_SIBLING_TEMPLATE_SYNC")
                self.assertEqual(res["model_calls"], 0)
                self.assertEqual(res["parameters_stored"], 0)

        # 2. JS inter-function sibling `const z = options.<flag> ? ...` + template interpolation transfer
        with self.subTest(case="js_coupled_inter_fn_sync"):
            with tempfile.TemporaryDirectory(prefix="brain_js_sync_b_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "package.json": '{"name": "rng-b", "version": "1.0.0"}\n',
                        "lib/range.js": (
                            "'use strict'\n"
                            "const isX = v => !v || v === 'x'\n"
                            "const fmtTilde = (M, m, p, options) => {\n"
                            "  const r = options.loose ? 1 : 0\n"
                            "  let ret\n"
                            "  if (isX(m)) {\n"
                            "    ret = `>=${M}.0.0 <${+M + 1}.0.0-0`\n"
                            "  } else if (isX(p)) {\n"
                            "    ret = `>=${M}.${m}.0 <${M}.${+m + 1}.0-0`\n"
                            "  } else {\n"
                            "    ret = `>=${M}.${m}.${p} <${M}.${+m + 1}.0-0`\n"
                            "  }\n"
                            "  return r >= 0 ? ret : ''\n"
                            "}\n"
                            "const fmtCaret = (M, m, p, options) => {\n"
                            "  const r = options.loose ? 1 : 0\n"
                            "  const z = options.includePrerelease ? '-0' : ''\n"
                            "  let ret\n"
                            "  if (isX(m)) {\n"
                            "    ret = `>=${M}.0.0${z} <${+M + 1}.0.0-0`\n"
                            "  } else if (isX(p)) {\n"
                            "    if (M === '0') {\n"
                            "      ret = `>=${M}.${m}.0${z} <${M}.${+m + 1}.0-0`\n"
                            "    } else {\n"
                            "      ret = `>=${M}.${m}.0${z} <${+M + 1}.0.0-0`\n"
                            "    }\n"
                            "  } else {\n"
                            "    ret = `>=${M}.${m}.${p} <${+M + 1}.0.0-0`\n"
                            "  }\n"
                            "  return r >= 0 ? ret : ''\n"
                            "}\n"
                            "module.exports = { fmtTilde, fmtCaret }\n"
                        ),
                        "test/range.test.js": (
                            "const assert = require('assert')\n"
                            "const { fmtTilde, fmtCaret } = require('../lib/range')\n"
                            "assert.strictEqual(fmtCaret('2', 'x', 'x', { includePrerelease: true }), '>=2.0.0-0 <3.0.0-0')\n"
                            "assert.strictEqual(fmtTilde('2', 'x', 'x', { includePrerelease: true }), '>=2.0.0-0 <3.0.0-0')\n"
                            "assert.strictEqual(fmtTilde('1', '2', 'x', { includePrerelease: true }), '>=1.2.0-0 <1.3.0-0')\n"
                            "assert.strictEqual(fmtTilde('1', '2', '3', { includePrerelease: true }), '>=1.2.3 <1.3.0-0')\n"
                        ),
                    },
                )
                res = ML_SWE.solve_js_repository(root, ["test/range.test.js"], timeout_s=20.0)
                self.assertEqual(res["status"], "VERIFIED", res)
                self.assertEqual(res["winner"]["tier"], "JS_COUPLED_SIBLING_TEMPLATE_SYNC")

        # 3. Python Law #51 (`TIER3_SIGN_PREFIX_PRESERVING_FORMAT`) + Law #52 (`TIER3_REGEX_PORT_RANGE_TIGHTEN`)
        #    through ONE front door `open_model().solve(..., mode="EPISTEMIC")` on a `src/`-layout repo!
        from canonical.runtime import causal_angelic_swe_engine_v1 as PY_SWE

        with self.subTest(case="py_law51_sign_prefix_preserving_format"):
            with tempfile.TemporaryDirectory(prefix="brain_py_law51_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "src/fmtpkg/__init__.py": "",
                        "src/fmtpkg/conv.py": (
                            "def float_to_url(value: float) -> str:\n"
                            "    value_str = str(float(value))\n"
                            "    if 'e' not in value_str:\n"
                            "        return value_str\n"
                            "    sig, _, exp_str = value_str.partition('e')\n"
                            "    left, _, right = sig.partition('.')\n"
                            "    exp = int(exp_str)\n"
                            "    if exp > 0:\n"
                            "        return f\"{left}{right}{'0' * (exp - len(right))}.0\"\n"
                            "    return f\"0.{'0' * (-exp - len(left))}{left}{right}\"\n"
                        ),
                        "tests/test_conv.py": (
                            "from fmtpkg.conv import float_to_url\n"
                            "def test_small_floats():\n"
                            "    assert float_to_url(1e-5) == '0.00001'\n"
                            "    assert float_to_url(-1e-5) == '-0.00001'\n"
                            "    assert float_to_url(-1.25e-5) == '-0.0000125'\n"
                        ),
                    },
                )
                res = PY_SWE.solve_repository(root, ["tests/test_conv.py"], timeout_s=20.0)
                self.assertEqual(res["status"], "VERIFIED", res)
                self.assertEqual(res["winner"]["tier"], "TIER3_SIGN_PREFIX_PRESERVING_FORMAT")

        with self.subTest(case="py_law52_rfc_port_regex_via_one_front_door"):
            with tempfile.TemporaryDirectory(prefix="brain_py_law52_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "src/netpkg/__init__.py": "",
                        "src/netpkg/host.py": (
                            "import re\n"
                            "_host_re = re.compile(r'([a-z0-9.-]+)(?::[0-9]+)?', re.ASCII | re.IGNORECASE)\n"
                            "def valid_host(h: str) -> bool:\n"
                            "    return bool(h) and _host_re.fullmatch(h) is not None\n"
                        ),
                        "tests/test_host.py": (
                            "from netpkg.host import valid_host\n"
                            "def test_ports():\n"
                            "    assert valid_host('a.test:8080')\n"
                            "    assert valid_host('a.test:65535')\n"
                            "    assert not valid_host('a.test:0')\n"
                            "    assert not valid_host('a.test:0443')\n"
                            "    assert not valid_host('a.test:65536')\n"
                        ),
                    },
                )
                model = open_model()
                out = model.solve(
                    "Fix the failing host port validation tests in tests/test_host.py",
                    mode="EPISTEMIC",
                    inputs={"workspace": str(root), "memory": UEK.new_universal_memory()},
                )
                er = out["epistemic_result"]
                self.assertEqual(er["status"], "VERIFIED", er)
                self.assertEqual(er["modality"], "swe_codebase")
                self.assertIn("TIER3_REGEX_PORT_RANGE_TIGHTEN", str(er.get("mode") or ""))
                self.assertEqual(out["model_calls"], 0)
                self.assertEqual(out["parameters_stored"], 0)

    def test_iter28_mocha_shim_nan_quantifier_asan_oob_stage2_multihunk_and_persist_delete(self) -> None:
        # 1. JS zero-dep mocha_shim + NaN-safe comparison inversion + Stage-2 multi-file composition
        with self.subTest(case="js_mocha_shim_and_stage2_multifile_progress"):
            with tempfile.TemporaryDirectory(prefix="brain_js_iter28_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "package.json": '{"name": "http-fresh-mini", "version": "1.0.0"}\n',
                        "lib/datecheck.js": (
                            "'use strict'\n"
                            "exports.isStaleDate = function (lastMod, modSince) {\n"
                            "  return !lastMod || Date.parse(lastMod) > Date.parse(modSince)\n"
                            "}\n"
                        ),
                        "lib/etagcheck.js": (
                            "'use strict'\n"
                            "exports.matchesEtag = function (list, etag) {\n"
                            "  for (var i = 0; i < list.length; i++) {\n"
                            "    var m = list[i]\n"
                            "    if (m !== etag) {\n"
                            "      return false\n"
                            "    }\n"
                            "  }\n"
                            "  return true\n"
                            "}\n"
                        ),
                        "test/fresh.js": (
                            "const assert = require('assert')\n"
                            "const { isStaleDate } = require('../lib/datecheck')\n"
                            "const { matchesEtag } = require('../lib/etagcheck')\n"
                            "describe('mini fresh', function () {\n"
                            "  it('rejects invalid date as stale', function () {\n"
                            "    assert.strictEqual(isStaleDate('invalid', 'Mon, 01 Jan 2024 00:00:00 GMT'), true)\n"
                            "    assert.strictEqual(isStaleDate('Mon, 01 Jan 2024 00:00:00 GMT', 'Mon, 01 Jan 2024 00:00:00 GMT'), false)\n"
                            "  })\n"
                            "  it('matches when at least one ETag matches', function () {\n"
                            "    assert.strictEqual(matchesEtag(['a', 'b'], 'b'), true)\n"
                            "    assert.strictEqual(matchesEtag(['a', 'b'], 'c'), false)\n"
                            "  })\n"
                            "})\n"
                        ),
                    },
                )
                model = open_model()
                out = model.solve(
                    "Fix both failing Mocha tests in test/fresh.js",
                    mode="EPISTEMIC",
                    inputs={"workspace": str(root), "memory": UEK.new_universal_memory()},
                )
                er = out["epistemic_result"]
                self.assertEqual(er["status"], "VERIFIED", er)
                self.assertEqual(er["modality"], "swe_js_codebase")
                self.assertEqual(er["swe_result"]["runner"], "mocha_shim")
                self.assertEqual(er["swe_result"]["winner"]["tier"], "JS_STAGE2_COMPOSED_PROGRESS")
                self.assertEqual(out["model_calls"], 0)
                self.assertEqual(out["parameters_stored"], 0)

        # 2. C/C++17 header-only `.h` ASan buffer-overrun guard + persistent disk JSON save/load/delete
        #    + cross-session Tier-0 recall + C Stage-2 causal-shift multi-hunk composition!
        with self.subTest(case="c_asan_oob_persist_cross_session_tier0_and_delete"):
            with tempfile.TemporaryDirectory(prefix="brain_c_iter28_oob_") as td:
                base = pathlib.Path(td)
                repo_a = base / "parser_a"
                _write_files(
                    repo_a,
                    {
                        "numparse.h": (
                            "#pragma once\n"
                            "#include <stddef.h>\n"
                            "static int check_num(const char* src, size_t size) {\n"
                            "    size_t offset = 0;\n"
                            "    while (offset < size && src[offset] >= '0' && src[offset] <= '9') offset++;\n"
                            "    if ((offset < size) && ('.' == src[offset])) {\n"
                            "        offset++;\n"
                            "        if (!('0' <= src[offset] && src[offset] <= '9')) {\n"
                            "            return 1;\n"
                            "        }\n"
                            "    }\n"
                            "    return 0;\n"
                            "}\n"
                        ),
                        "test_numparse.cpp": (
                            "#include <cassert>\n"
                            "#include \"numparse.h\"\n"
                            "int main() {\n"
                            "    const char bad[2] = {'1', '.'};\n"
                            "    assert(check_num(bad, 2) == 1);\n"
                            "    const char good[3] = {'1', '.', '5'};\n"
                            "    assert(check_num(good, 3) == 0);\n"
                            "    return 0;\n"
                            "}\n"
                        ),
                    },
                )
                model = open_model()
                mem1 = UEK.new_universal_memory()
                out1 = model.solve(
                    "Fix the ASan buffer overrun failing test_numparse.cpp",
                    mode="EPISTEMIC",
                    inputs={"workspace": str(repo_a), "memory": mem1},
                )
                er1 = out1["epistemic_result"]
                self.assertEqual(er1["status"], "VERIFIED", er1)
                self.assertEqual(er1["modality"], "swe_c_codebase")
                self.assertEqual(er1["swe_result"]["winner"]["tier"], "C_ASAN_BUFFER_BOUNDS_GUARD")
                lid = er1["swe_result"]["winner"]["learned_law_id"]
                self.assertTrue(lid and lid in mem1["c_rewrite_laws"])

                # Persist to disk JSON -> reload in a fresh session -> Tier-0 recall on a 2nd unseen repo!
                mem_file = base / "epistemic_mem.json"
                UEK.save_universal_memory(mem1, mem_file)
                mem2 = UEK.load_universal_memory(mem_file)
                self.assertIn(lid, mem2["c_rewrite_laws"])

                repo_b = base / "parser_b"
                _write_files(
                    repo_b,
                    {
                        "scan.h": (
                            "#pragma once\n"
                            "#include <stddef.h>\n"
                            "static int scan_hex(const char* buf, size_t len) {\n"
                            "    size_t pos = 0;\n"
                            "    if ((pos < len) && (buf[pos] == 'x')) {\n"
                            "        pos++;\n"
                            "        if (!('0' <= buf[pos] && buf[pos] <= '9')) {\n"
                            "            return -1;\n"
                            "        }\n"
                            "    }\n"
                            "    return 0;\n"
                            "}\n"
                        ),
                        "test_scan.cpp": (
                            "#include <cassert>\n"
                            "#include \"scan.h\"\n"
                            "int main() {\n"
                            "    const char edge[1] = {'x'};\n"
                            "    assert(scan_hex(edge, 1) == -1);\n"
                            "    const char ok[2] = {'x', '7'};\n"
                            "    assert(scan_hex(ok, 2) == 0);\n"
                            "    return 0;\n"
                            "}\n"
                        ),
                    },
                )
                out2 = model.solve(
                    "Fix the ASan buffer overflow failing test_scan.cpp",
                    mode="EPISTEMIC",
                    inputs={"workspace": str(repo_b), "memory": mem2},
                )
                er2 = out2["epistemic_result"]
                self.assertEqual(er2["status"], "VERIFIED", er2)
                self.assertEqual(er2["mode"], "TIER0_C_SKILL_RECALL")
                self.assertEqual(er2["swe_result"]["winner"]["tier"], "C_TIER0_SKILL_RECALL")
                self.assertEqual(mem2["c_rewrite_laws"][lid]["verified_uses"], 2)
                # External inspectable deletion removes the learned law cleanly without retraining
                self.assertTrue(UEK.delete_memory_entry(mem2, lid))
                self.assertNotIn(lid, mem2["c_rewrite_laws"])

        with self.subTest(case="c_stage2_causal_shift_multihunk_composition"):
            with tempfile.TemporaryDirectory(prefix="brain_c_iter28_s2_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "pair.c": (
                            "#include <stddef.h>\n"
                            "typedef struct { int v; } Box;\n"
                            "int read_a(Box* a) {\n"
                            "    return a->v;\n"
                            "}\n"
                            "int read_b(Box* b) {\n"
                            "    return b->v;\n"
                            "}\n"
                        ),
                        "test_pair.c": (
                            "#include <assert.h>\n"
                            "#include \"pair.c\"\n"
                            "int main(void) {\n"
                            "    Box x = {5};\n"
                            "    assert(read_a(&x) == 5);\n"
                            "    assert(read_a(NULL) == 0);\n"
                            "    assert(read_b(&x) == 5);\n"
                            "    assert(read_b(NULL) == 0);\n"
                            "    return 0;\n"
                            "}\n"
                        ),
                    },
                )
                res = ML_SWE.solve_c_repository(root, ["test_pair.c"], timeout_s=30.0)
                self.assertEqual(res["status"], "VERIFIED", res)
                self.assertEqual(res["winner"]["tier"], "C_STAGE2_COMPOSED_PROGRESS")
                self.assertEqual(res["model_calls"], 0)
                self.assertEqual(res["parameters_stored"], 0)

    def test_iter29_tape_shim_optional_chain_falsy_zero_digit_count_and_coord_projection(self) -> None:
        # 1. Zero-dep tape_shim + JS_TYPEERROR_OPTIONAL_MEMBER_GUARD
        with self.subTest(case="js_tape_shim_optional_member_guard"):
            with tempfile.TemporaryDirectory(prefix="brain_js_iter29_opt_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "package.json": '{"name": "mini-cli", "scripts": {"test": "tape test/index.js"}}\n',
                        "lib/index.js": (
                            "module.exports = function parse(defaults) {\n"
                            "  const buckets = { string: [], boolean: [] };\n"
                            "  for (const k in defaults) {\n"
                            "    buckets[typeof defaults[k]].push(k);\n"
                            "  }\n"
                            "  return buckets;\n"
                            "};\n"
                        ),
                        "test/index.js": (
                            "const test = require('tape');\n"
                            "const parse = require('../lib');\n"
                            "test('null default does not throw', t => {\n"
                            "  const res = parse({ a: 'hi', b: null });\n"
                            "  t.deepEqual(res, { string: ['a'], boolean: [] });\n"
                            "  t.end();\n"
                            "});\n"
                        ),
                    },
                )
                res = ML_SWE.solve_js_repository(root, ["test/index.js"], timeout_s=20.0)
                self.assertEqual(res["status"], "VERIFIED", res)
                self.assertEqual(res["runner"], "tape_shim")
                self.assertEqual(res["winner"]["tier"], "JS_TYPEERROR_OPTIONAL_MEMBER_GUARD")
                self.assertEqual(res["model_calls"], 0)

        # 2. Zero-dep tape_shim + JS_FALSY_ZERO_NUMERIC_COERCION_FIX
        with self.subTest(case="js_falsy_zero_numeric_coercion"):
            with tempfile.TemporaryDirectory(prefix="brain_js_iter29_fz_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "package.json": '{"name": "mini-num", "scripts": {"test": "tape test/index.js"}}\n',
                        "lib/index.js": (
                            "function isBool(x) { return typeof x === 'boolean'; }\n"
                            "function toNum(any) {\n"
                            "  return (!isBool(any) && Number(any)) || any;\n"
                            "}\n"
                            "module.exports = toNum;\n"
                        ),
                        "test/index.js": (
                            "const test = require('tape');\n"
                            "const toNum = require('../lib');\n"
                            "test('zero coerces to number 0', t => {\n"
                            "  t.strictEqual(toNum('0'), 0);\n"
                            "  t.strictEqual(toNum('42'), 42);\n"
                            "  t.strictEqual(toNum('abc'), 'abc');\n"
                            "  t.strictEqual(toNum(true), true);\n"
                            "  t.end();\n"
                            "});\n"
                        ),
                    },
                )
                res = ML_SWE.solve_js_repository(root, ["test/index.js"], timeout_s=20.0)
                self.assertEqual(res["status"], "VERIFIED", res)
                self.assertEqual(res["winner"]["tier"], "JS_FALSY_ZERO_NUMERIC_COERCION_FIX")
                self.assertEqual(res["model_calls"], 0)

        # 3. C_COUPLED_WHILE_TO_DO_WHILE_DIGIT_COUNT (2-loop Pass-1 sizer + Pass-2 writer)
        with self.subTest(case="c_coupled_digit_count_do_while_and_tier0_recall"):
            mem = UEK.new_universal_memory()
            with tempfile.TemporaryDirectory(prefix="brain_c_iter29_dc_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "numfmt.h": (
                            "#include <stddef.h>\n"
                            "static size_t num_size(unsigned long parsed_number) {\n"
                            "  size_t i = 0;\n"
                            "  while (0 != parsed_number) {\n"
                            "    parsed_number /= 10;\n"
                            "    i++;\n"
                            "  }\n"
                            "  return i;\n"
                            "}\n"
                            "static size_t num_write(unsigned long parsed_number, char* out) {\n"
                            "  unsigned long backup = parsed_number;\n"
                            "  size_t i = 0;\n"
                            "  while (0 != parsed_number) {\n"
                            "    parsed_number /= 10;\n"
                            "    i++;\n"
                            "  }\n"
                            "  parsed_number = backup;\n"
                            "  backup = i;\n"
                            "  do {\n"
                            "    out[i - 1] = (char)('0' + (parsed_number % 10));\n"
                            "    parsed_number /= 10;\n"
                            "    i--;\n"
                            "  } while (0 != parsed_number);\n"
                            "  out[backup] = '\\0';\n"
                            "  return backup;\n"
                            "}\n"
                        ),
                        "test_numfmt.c": (
                            "#include <assert.h>\n"
                            "#include <string.h>\n"
                            "#include \"numfmt.h\"\n"
                            "int main(void) {\n"
                            "  char buf[32];\n"
                            "  assert(num_size(0) == 1);\n"
                            "  assert(num_write(0, buf) == 1 && strcmp(buf, \"0\") == 0);\n"
                            "  assert(num_write(42, buf) == 2 && strcmp(buf, \"42\") == 0);\n"
                            "  return 0;\n"
                            "}\n"
                        ),
                    },
                )
                res = ML_SWE.solve_c_repository(root, ["test_numfmt.c"], memory=mem, timeout_s=30.0)
                self.assertEqual(res["status"], "VERIFIED", res)
                self.assertEqual(res["winner"]["tier"], "C_COUPLED_WHILE_TO_DO_WHILE_DIGIT_COUNT")
                self.assertEqual(res["winner"]["attempt"], 1)
                self.assertIsNotNone(res["winner"]["learned_law_id"])
                # Tier-0 recall on second unseen problem
                res2 = ML_SWE.solve_c_repository(root, ["test_numfmt.c"], memory=mem, timeout_s=30.0)
                self.assertEqual(res2["status"], "VERIFIED", res2)
                self.assertEqual(res2["winner"]["tier"], "C_TIER0_SKILL_RECALL")

        # 4. C++17 C_DOUBLE_PROJECTION_UNWRAP + C_GROW_ONLY_RESIZE_GUARD composed via C_STAGE2_COMPOSED_PROGRESS
        with self.subTest(case="cpp_double_projection_and_grow_only_resize_stage2"):
            with tempfile.TemporaryDirectory(prefix="brain_cpp_iter29_grid_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "src/grid.h": (
                            "#pragma once\n"
                            "#include <vector>\n"
                            "class Grid {\n"
                            "public:\n"
                            "  std::vector<std::vector<int>> rows;\n"
                            "  size_t GetDataColumnIndex(size_t idx) const { return idx + 1; }\n"
                            "  size_t GetDataColumnCount() const { return rows.empty() ? 0 : rows[0].size(); }\n"
                            "  void SetColumn(size_t pColumnIdx, int v) {\n"
                            "    const size_t dataColumnIdx = GetDataColumnIndex(pColumnIdx);\n"
                            "    if ((dataColumnIdx + 1) > GetDataColumnCount()) {\n"
                            "      for (auto itRow = rows.begin(); itRow != rows.end(); ++itRow) {\n"
                            "        itRow->resize(GetDataColumnIndex(dataColumnIdx + 1));\n"
                            "      }\n"
                            "    }\n"
                            "    rows[0].at(dataColumnIdx) = v;\n"
                            "  }\n"
                            "};\n"
                        ),
                        "tests/test_grid.cpp": (
                            "#include <cassert>\n"
                            "#include <stdexcept>\n"
                            "#include <iostream>\n"
                            "#include \"grid.h\"\n"
                            "int main() {\n"
                            "  try {\n"
                            "    Grid g;\n"
                            "    g.rows.push_back({});\n"
                            "    g.SetColumn(0, 9);\n"
                            "    if (g.rows[0].size() != 2) { std::cout << \"test_grid.cpp:10 failed\" << std::endl; return 1; }\n"
                            "    Grid g2;\n"
                            "    g2.rows.push_back({1, 2});\n"
                            "    g2.rows.push_back({1, 2, 3, 4});\n"
                            "    g2.SetColumn(1, 8);\n"
                            "    if (g2.rows[1].at(3) != 4) return 1;\n"
                            "  } catch (const std::exception& ex) {\n"
                            "    std::cout << \"exception: \" << ex.what() << std::endl;\n"
                            "    return 1;\n"
                            "  }\n"
                            "  return 0;\n"
                            "}\n"
                        ),
                    },
                )
                res = ML_SWE.solve_c_repository(root, ["tests/test_grid.cpp"], timeout_s=30.0)
                self.assertEqual(res["status"], "VERIFIED", res)
                self.assertEqual(res["winner"]["tier"], "C_STAGE2_COMPOSED_PROGRESS")
                self.assertIn("C_DOUBLE_PROJECTION_UNWRAP", res["winner"]["description"])
                self.assertIn("C_GROW_ONLY_RESIZE_GUARD", res["winner"]["description"])
                self.assertEqual(res["model_calls"], 0)

    def test_iter30_asan_twopass_twin_rewind_flag_skip_and_js_dep_reorder_clamp(self) -> None:
        # 1. C_SPECULATIVE_ADVANCE_NO_REWIND + ASan two-pass twin localization + MemRL Tier-0 recall
        with self.subTest(case="c_speculative_advance_rewind_and_tier0_recall"):
            mem = UEK.new_universal_memory()
            with tempfile.TemporaryDirectory(prefix="brain_c_iter30_rw_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "lexer.h": (
                            "#include <stddef.h>\n"
                            "typedef struct { const char* src; size_t size; size_t offset; } Lex;\n"
                            "static int lex_skip_comment(Lex* state) {\n"
                            "  if (state->offset >= state->size) { return 0; }\n"
                            "  if ('/' == state->src[state->offset]) {\n"
                            "    state->offset++;\n"
                            "    if ('/' == state->src[state->offset]) {\n"
                            "      while (state->offset < state->size && state->src[state->offset] != '\\n') state->offset++;\n"
                            "      return 1;\n"
                            "    } else if ('*' == state->src[state->offset]) {\n"
                            "      state->offset++;\n"
                            "      return 1;\n"
                            "    }\n"
                            "  }\n"
                            "  return 0;\n"
                            "}\n"
                        ),
                        "test_lexer.c": (
                            "#include <assert.h>\n"
                            "#include \"lexer.h\"\n"
                            "int main(void) {\n"
                            "  Lex s = { \"/x\", 2, 0 };\n"
                            "  assert(lex_skip_comment(&s) == 0);\n"
                            "  assert(s.offset == 0);\n"
                            "  Lex c = { \"//hi\", 4, 0 };\n"
                            "  assert(lex_skip_comment(&c) == 1 && c.offset == 4);\n"
                            "  return 0;\n"
                            "}\n"
                        ),
                    },
                )
                res = ML_SWE.solve_c_repository(root, ["test_lexer.c"], memory=mem, timeout_s=30.0)
                self.assertEqual(res["status"], "VERIFIED", res)
                self.assertEqual(res["winner"]["tier"], "C_SPECULATIVE_ADVANCE_NO_REWIND")
                self.assertIsNotNone(res["winner"]["learned_law_id"])
                res2 = ML_SWE.solve_c_repository(root, ["test_lexer.c"], memory=mem, timeout_s=30.0)
                self.assertEqual(res2["status"], "VERIFIED", res2)
                self.assertEqual(res2["winner"]["tier"], "C_TIER0_SKILL_RECALL")

        # 2. C_FLAG_SKIP_REMAINDER_BLOCK (special-case keyword must not fall through to digit loop)
        with self.subTest(case="c_flag_skip_remainder_block"):
            with tempfile.TemporaryDirectory(prefix="brain_c_iter30_fs_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "numtok.h": (
                            "#include <stddef.h>\n"
                            "#include <string.h>\n"
                            "static int scan_num(const char* src, size_t size, size_t* out_off) {\n"
                            "  size_t offset = 0;\n"
                            "  int found_sign = 0;\n"
                            "  int inf_or_nan = 0;\n"
                            "  if (1) {\n"
                            "    if (offset + 3 <= size && memcmp(src + offset, \"NaN\", 3) == 0) {\n"
                            "      offset += 3;\n"
                            "      inf_or_nan = 1;\n"
                            "    }\n"
                            "    if (found_sign && !inf_or_nan && offset < size) {\n"
                            "      return 1;\n"
                            "    }\n"
                            "    if (offset < size && '0' == src[offset]) {\n"
                            "      offset++;\n"
                            "    }\n"
                            "    while (offset < size && '0' <= src[offset] && src[offset] <= '9') {\n"
                            "      offset++;\n"
                            "    }\n"
                            "  }\n"
                            "  if (offset < size && src[offset] != ']') return 1;\n"
                            "  *out_off = offset;\n"
                            "  return 0;\n"
                            "}\n"
                        ),
                        "test_numtok.c": (
                            "#include <assert.h>\n"
                            "#include \"numtok.h\"\n"
                            "int main(void) {\n"
                            "  size_t off = 0;\n"
                            "  assert(scan_num(\"NaN]\", 4, &off) == 0 && off == 3);\n"
                            "  assert(scan_num(\"NaN0]\", 5, &off) == 1);\n"
                            "  assert(scan_num(\"42]\", 3, &off) == 0 && off == 2);\n"
                            "  return 0;\n"
                            "}\n"
                        ),
                    },
                )
                res = ML_SWE.solve_c_repository(root, ["test_numtok.c"], timeout_s=30.0)
                self.assertEqual(res["status"], "VERIFIED", res)
                self.assertEqual(res["winner"]["tier"], "C_FLAG_SKIP_REMAINDER_BLOCK")
                self.assertEqual(res["model_calls"], 0)

        # 3. JS_SIBLING_BLOCK_DEP_REORDER (write-before-read producer/consumer reorder)
        with self.subTest(case="js_sibling_block_dep_reorder"):
            with tempfile.TemporaryDirectory(prefix="brain_js_iter30_dep_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "package.json": '{"name": "mini-dep", "scripts": {"test": "tape test/index.js"}}\n',
                        "lib/index.js": (
                            "module.exports = function cascade(opts) {\n"
                            "  opts.string.forEach(k => {\n"
                            "    opts.string = opts.string.concat(opts.alias[k] || []);\n"
                            "  });\n"
                            "\n"
                            "  if (opts.default) {\n"
                            "    for (const k in opts.default) {\n"
                            "      (opts[typeof opts.default[k]] || []).push(k);\n"
                            "    }\n"
                            "  }\n"
                            "  return opts.string;\n"
                            "};\n"
                        ),
                        "test/index.js": (
                            "const test = require('tape');\n"
                            "const cascade = require('../lib');\n"
                            "test('default string cascades to alias', t => {\n"
                            "  const res = cascade({ string: [], alias: { a: ['alpha'] }, default: { a: 'hi' } });\n"
                            "  t.deepEqual(res, ['a', 'alpha']);\n"
                            "  t.end();\n"
                            "});\n"
                        ),
                    },
                )
                res = ML_SWE.solve_js_repository(root, ["test/index.js"], timeout_s=20.0)
                self.assertEqual(res["status"], "VERIFIED", res)
                self.assertEqual(res["winner"]["tier"], "JS_SIBLING_BLOCK_DEP_REORDER")
                self.assertEqual(res["model_calls"], 0)

        # 4. JS_INTERVAL_SUB_LOWER_CLAMP + zero-dep `deep-equal` shim
        with self.subTest(case="js_interval_sub_lower_clamp_and_deep_equal_shim"):
            with tempfile.TemporaryDirectory(prefix="brain_js_iter30_cl_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "package.json": '{"name": "mini-rng", "scripts": {"test": "mocha test/rng.js"}}\n',
                        "index.js": (
                            "module.exports = function suffixRange(size, suffixLen) {\n"
                            "  let start = size - suffixLen;\n"
                            "  let end = size - 1;\n"
                            "  if (end > size - 1) end = size - 1;\n"
                            "  if (start > end || start < 0) return -1;\n"
                            "  return [{ start, end }];\n"
                            "};\n"
                        ),
                        "test/rng.js": (
                            "const assert = require('assert');\n"
                            "const deepEqual = require('deep-equal');\n"
                            "const suffixRange = require('..');\n"
                            "describe('suffixRange', () => {\n"
                            "  it('clamps suffix exceeding size', () => {\n"
                            "    assert.ok(deepEqual(suffixRange(100, 500), [{ start: 0, end: 99 }]));\n"
                            "    assert.strictEqual(suffixRange(100, 0), -1);\n"
                            "  });\n"
                            "});\n"
                        ),
                    },
                )
                res = ML_SWE.solve_js_repository(root, ["test/rng.js"], timeout_s=20.0)
                self.assertEqual(res["status"], "VERIFIED", res)
                self.assertEqual(res["winner"]["tier"], "JS_INTERVAL_SUB_LOWER_CLAMP")
                self.assertEqual(res["model_calls"], 0)

    def test_09_iter31_c_short_circuit_norm_compare_safe_decoder_and_harness_auto_select(self) -> None:
        """Iter 31: C short-circuit bounds swap (Pass 0n), normalized comparator order-equivalence
        consistency + live Tier-0 MemRL recall (Pass 0p), safe sibling decoder delegation with
        multi-line C signatures (Pass 0q), harness-only `main.c` primary-TU auto-selection, and
        `compress_and_prune_memory(None)` safety. Zero LLM, zero weights."""
        import shutil
        if not shutil.which("gcc"):
            self.skipTest("gcc not available")

        # 0. compress_and_prune_memory(None) safety
        with self.subTest(case="compress_and_prune_memory_none_safe"):
            res_none = UEK.compress_and_prune_memory(None)
            self.assertEqual(res_none["pruned_error_laws"], 0)
            self.assertEqual(res_none["pruned_multilang_laws"], 0)

        # 1. Pass 0n (`C_ASAN_CONJUNCT_SHORT_CIRCUIT_SWAP`) + harness-only `main.c` auto-deferral
        with self.subTest(case="c_asan_conjunct_short_circuit_swap_and_auto_tu"):
            with tempfile.TemporaryDirectory(prefix="brain_c_iter31_sc_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "mini_str.h": (
                            "#include <stddef.h>\n"
                            "static char *mini_ncat(char *dst, const char *src, size_t n) {\n"
                            "  char *d = dst;\n"
                            "  while ('\\0' != *d) d++;\n"
                            "  while (('\\0' != *src) && (0 != n--)) {\n"
                            "    *d++ = *src++;\n"
                            "  }\n"
                            "  *d = '\\0';\n"
                            "  return dst;\n"
                            "}\n"
                        ),
                        "test/utest.h": (
                            "#include <stdio.h>\n"
                            "#include <stdlib.h>\n"
                            "#define UTEST_MAIN() int main(void) { extern int run_all(void); return run_all(); }\n"
                            "#define ASSERT_EQ(a, b) do { if ((a) != (b)) { fprintf(stderr, \"FAIL %s:%d\\n\", __FILE__, __LINE__); return 1; } } while (0)\n"
                        ),
                        "test/main.c": '#include "utest.h"\nUTEST_MAIN()\n',
                        "test/no_malloc.c": '#include "utest.h"\nint dummy(void) { ASSERT_EQ(1, 1); return 0; }\n',
                        "test/test_shared.h": (
                            '#include "mini_str.h"\n'
                            '#include <string.h>\n'
                            "int run_all(void) {\n"
                            "  char buf[16] = \"hi\";\n"
                            "  char exact[3] = {'a', 'b', 'c'};\n"
                            "  mini_ncat(buf, exact, 3);\n"
                            "  ASSERT_EQ(buf[0], 'h');\n"
                            "  ASSERT_EQ(buf[1], 'i');\n"
                            "  ASSERT_EQ(buf[2], 'a');\n"
                            "  ASSERT_EQ(buf[3], 'b');\n"
                            "  ASSERT_EQ(buf[4], 'c');\n"
                            "  ASSERT_EQ(buf[5], '\\0');\n"
                            "  return 0;\n"
                            "}\n"
                        ),
                        "test/test.c": '#include "utest.h"\n#include "test_shared.h"\n',
                    },
                )
                # Zero test_targets hand-holding: auto-selects test/test.c over test/main.c and test/no_malloc.c!
                res = ML_SWE.solve_c_repository(root, timeout_s=20.0)
                self.assertEqual(res["status"], "VERIFIED", res)
                self.assertEqual(res["winner"]["tier"], "C_ASAN_CONJUNCT_SHORT_CIRCUIT_SWAP")
                self.assertEqual(res["model_calls"], 0)
                self.assertEqual(res["parameters_stored"], 0)

        # 2. Pass 0p (`C_NORM_COMPARE_CONSISTENCY`) + live cross-project Tier-0 MemRL recall
        with self.subTest(case="c_norm_compare_consistency_and_tier0_transfer"):
            mem = UEK.new_universal_memory()
            with tempfile.TemporaryDirectory(prefix="brain_c_iter31_nc1_") as td1:
                root1 = pathlib.Path(td1)
                _write_files(
                    root1,
                    {
                        "cmp1.h": (
                            "static int lower_cp(int c) { return (c >= 'A' && c <= 'Z') ? (c + 32) : c; }\n"
                            "static int my_casecmp(const char *a, const char *b) {\n"
                            "  for (;;) {\n"
                            "    int cp1 = (unsigned char)*a++;\n"
                            "    int cp2 = (unsigned char)*b++;\n"
                            "    int orig1 = cp1;\n"
                            "    int orig2 = cp2;\n"
                            "    cp1 = lower_cp(cp1);\n"
                            "    cp2 = lower_cp(cp2);\n"
                            "    if ((0 == orig1) && (0 == orig2)) {\n"
                            "      return 0;\n"
                            "    } else if (cp1 == cp2) {\n"
                            "      continue;\n"
                            "    }\n"
                            "    if (orig1 < orig2) {\n"
                            "      return -1;\n"
                            "    } else if (orig1 > orig2) {\n"
                            "      return 1;\n"
                            "    }\n"
                            "  }\n"
                            "}\n"
                        ),
                        "test_cmp1.c": (
                            '#include <stdio.h>\n#include "cmp1.h"\n'
                            "int main(void) {\n"
                            '  if (my_casecmp(".gdoc", ".GSHeeT") != -15) { fprintf(stderr, "FAIL:my_casecmp:%d\\n", __LINE__); return 1; }\n'
                            '  if (my_casecmp(".gsheet", ".gSLiDe") != -4) { fprintf(stderr, "FAIL:my_casecmp:%d\\n", __LINE__); return 1; }\n'
                            "  return 0;\n"
                            "}\n"
                        ),
                    },
                )
                r1 = ML_SWE.solve_c_repository(root1, ["test_cmp1.c"], memory=mem, timeout_s=20.0)
                self.assertEqual(r1["status"], "VERIFIED", r1)
                self.assertEqual(r1["winner"]["tier"], "C_NORM_COMPARE_CONSISTENCY")
                law_id = r1["winner"].get("learned_law_id")
                self.assertTrue(law_id and law_id in mem["c_rewrite_laws"])

            with tempfile.TemporaryDirectory(prefix="brain_c_iter31_nc2_") as td2:
                root2 = pathlib.Path(td2)
                _write_files(
                    root2,
                    {
                        "cmp2.h": (
                            "#include <stddef.h>\n"
                            "static int fold_ch(int c) { return (c >= 'A' && c <= 'Z') ? (c + 32) : c; }\n"
                            "static int my_ncasecmp(const char *p, const char *q, size_t n) {\n"
                            "  do {\n"
                            "    int x = (unsigned char)*p++;\n"
                            "    int y = (unsigned char)*q++;\n"
                            "    int ox = x;\n"
                            "    int oy = y;\n"
                            "    x = fold_ch(x);\n"
                            "    y = fold_ch(y);\n"
                            "    if ((0 == ox) && (0 == oy)) {\n"
                            "      return 0;\n"
                            "    } else if (x == y) {\n"
                            "      continue;\n"
                            "    }\n"
                            "    if (ox < oy) {\n"
                            "      return -1;\n"
                            "    } else if (ox > oy) {\n"
                            "      return 1;\n"
                            "    }\n"
                            "  } while (--n > 0);\n"
                            "  return 0;\n"
                            "}\n"
                        ),
                        "test_cmp2.c": (
                            '#include <stdio.h>\n#include "cmp2.h"\n'
                            "int main(void) {\n"
                            '  if (my_ncasecmp(".gdoc", ".GSHeeT", 5) != -15) { fprintf(stderr, "FAIL:my_ncasecmp:%d\\n", __LINE__); return 1; }\n'
                            "  return 0;\n"
                            "}\n"
                        ),
                    },
                )
                r2 = ML_SWE.solve_c_repository(root2, ["test_cmp2.c"], memory=mem, timeout_s=20.0)
                self.assertEqual(r2["status"], "VERIFIED", r2)
                self.assertEqual(r2["winner"]["tier"], "C_TIER0_SKILL_RECALL")
                self.assertEqual(r2["winner"]["skill_id_used"], law_id)
                self.assertEqual(mem["c_rewrite_laws"][law_id]["verified_uses"], 2)

        # 3. Pass 0q (`C_SIBLING_SAFE_DECODER_DELEGATE`) with multi-line C signature + ASan OOB
        with self.subTest(case="c_sibling_safe_decoder_delegate_multiline_sig"):
            with tempfile.TemporaryDirectory(prefix="brain_c_iter31_sd_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "dec.h": (
                            "#include <stddef.h>\n"
                            "static const unsigned char *\n"
                            "mini_codepoint(const unsigned char *s,\n"
                            "               int *out_cp) {\n"
                            "  if (0xe0 == (0xf0 & s[0]) && '\\0' != s[1] && '\\0' != s[2]) {\n"
                            "    *out_cp = ((0x0f & s[0]) << 12) | ((0x3f & s[1]) << 6) | (0x3f & s[2]);\n"
                            "    return s + 3;\n"
                            "  }\n"
                            "  *out_cp = s[0];\n"
                            "  return s + 1;\n"
                            "}\n"
                            "static const unsigned char *\n"
                            "mini_rcodepoint(const unsigned char *s,\n"
                            "                int *out_cp) {\n"
                            "  const unsigned char *p = s;\n"
                            "  if (0xe0 == (0xf0 & p[0])) {\n"
                            "    *out_cp = ((0x0f & p[0]) << 12) | ((0x3f & p[1]) << 6) | (0x3f & p[2]);\n"
                            "  } else {\n"
                            "    *out_cp = p[0];\n"
                            "  }\n"
                            "  return p - 1;\n"
                            "}\n"
                        ),
                        "test_dec.c": (
                            '#include <stdlib.h>\n#include "dec.h"\n'
                            "int main(void) {\n"
                            "  unsigned char ok3[4] = {0xe2, 0x82, 0xac, 0x00};\n"
                            "  int cp = 0;\n"
                            "  mini_rcodepoint(ok3, &cp);\n"
                            "  if (cp != 0x20ac) return 2;\n"
                            "  unsigned char *b = (unsigned char *)malloc(2);\n"
                            "  b[0] = 0xe2; b[1] = 0x00;\n"
                            "  mini_rcodepoint(b, &cp);\n"
                            "  free(b);\n"
                            "  return (cp == 0xe2) ? 0 : 1;\n"
                            "}\n"
                        ),
                    },
                )
                res = ML_SWE.solve_c_repository(root, ["test_dec.c"], timeout_s=20.0)
                self.assertEqual(res["status"], "VERIFIED", res)
                self.assertEqual(res["winner"]["tier"], "C_SIBLING_SAFE_DECODER_DELEGATE")
                self.assertEqual(res["model_calls"], 0)

    def test_10_iter32_cpp17_template_overload_empty_iter_prefix_monoid_and_sibling_sync(self) -> None:
        """Iter 32: Five universal C++17 causal laws (`C_CPP_TEMPLATE_TRAIT_OVERLOAD_GENERALIZE`,
        `C_EMPTY_CONTAINER_ITERATOR_GUARD`, `C_HARDCODED_PREFIX_CHAR_TO_EXPR`,
        `C_RECURSIVE_VECTOR_ACCUMULATOR_MERGE`, `C_SIBLING_METHOD_TRAILING_BLOCK_SYNC`) +
        live MemRL Tier-0 recall across two independent C++17 projects. Zero LLM, zero weights."""
        import shutil
        if not shutil.which("g++"):
            self.skipTest("g++ not available")

        # 1. Pass 0r: Compile-time overload generalization `store(double&) -> std::is_floating_point<T>` + Tier-0 recall
        with self.subTest(case="cpp17_template_trait_overload_generalize_and_tier0_recall"):
            mem = UEK.new_universal_memory()
            with tempfile.TemporaryDirectory(prefix="brain_cpp_iter32_ovl1_") as td1:
                root1 = pathlib.Path(td1)
                _write_files(
                    root1,
                    {
                        "holder.hpp": (
                            "#include <type_traits>\n"
                            "#include <string>\n"
                            "struct Holder {\n"
                            "  std::string raw;\n"
                            "  auto &store_val(double &var) {\n"
                            "    var = static_cast<double>(std::stod(raw));\n"
                            "    return *this;\n"
                            "  }\n"
                            "};\n"
                        ),
                        "test_holder.cpp": (
                            '#include "holder.hpp"\n'
                            "int main() {\n"
                            '  Holder h{"3.5"};\n'
                            "  float f = 0.0f;\n"
                            "  h.store_val(f);\n"
                            "  return (f > 3.4f && f < 3.6f) ? 0 : 1;\n"
                            "}\n"
                        ),
                    },
                )
                r1 = ML_SWE.solve_c_repository(root1, ["test_holder.cpp"], memory=mem, timeout_s=25.0)
                self.assertEqual(r1["status"], "VERIFIED", r1)
                self.assertEqual(r1["winner"]["tier"], "C_CPP_TEMPLATE_TRAIT_OVERLOAD_GENERALIZE")
                law_id = r1["winner"].get("learned_law_id")
                self.assertTrue(law_id and law_id in mem["c_rewrite_laws"])

            with tempfile.TemporaryDirectory(prefix="brain_cpp_iter32_ovl2_") as td2:
                root2 = pathlib.Path(td2)
                _write_files(
                    root2,
                    {
                        "sink.hpp": (
                            "#include <type_traits>\n"
                            "#include <string>\n"
                            "struct Sink {\n"
                            "  std::string txt;\n"
                            "  auto &bind_num(double &out) {\n"
                            "    out = static_cast<double>(std::stod(txt));\n"
                            "    return *this;\n"
                            "  }\n"
                            "};\n"
                        ),
                        "test_sink.cpp": (
                            '#include "sink.hpp"\n'
                            "int main() {\n"
                            '  Sink s{"2.25"};\n'
                            "  float v = 0.0f;\n"
                            "  s.bind_num(v);\n"
                            "  return (v > 2.2f && v < 2.3f) ? 0 : 1;\n"
                            "}\n"
                        ),
                    },
                )
                r2 = ML_SWE.solve_c_repository(root2, ["test_sink.cpp"], memory=mem, timeout_s=25.0)
                self.assertEqual(r2["status"], "VERIFIED", r2)
                self.assertEqual(r2["winner"]["tier"], "C_TIER0_SKILL_RECALL")
                self.assertEqual(r2["winner"]["skill_id_used"], law_id)
                self.assertEqual(mem["c_rewrite_laws"][law_id]["verified_uses"], 2)

        # 2. Pass 0s: Empty-container `std::next(std::begin(args))` SEGV guard
        with self.subTest(case="cpp17_empty_container_iterator_guard"):
            with tempfile.TemporaryDirectory(prefix="brain_cpp_iter32_emp_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "iter_scan.hpp": (
                            "#include <iterator>\n#include <string>\n#include <vector>\n"
                            "inline int count_tail(const std::vector<std::string> &items) {\n"
                            "  int n = 0;\n"
                            "  auto end = std::end(items);\n"
                            "  for (auto it = std::next(std::begin(items)); it != end; ++it) {\n"
                            "    n += static_cast<int>(it->size());\n"
                            "  }\n"
                            "  return n;\n"
                            "}\n"
                        ),
                        "test_iter_scan.cpp": (
                            '#include "iter_scan.hpp"\n'
                            "int main() {\n"
                            "  std::vector<std::string> empty_v{};\n"
                            "  if (count_tail(empty_v) != 0) return 1;\n"
                            '  if (count_tail({"prog", "ab"}) != 2) return 2;\n'
                            "  return 0;\n"
                            "}\n"
                        ),
                    },
                )
                res = ML_SWE.solve_c_repository(root, ["test_iter_scan.cpp"], timeout_s=25.0)
                self.assertEqual(res["status"], "VERIFIED", res)
                self.assertEqual(res["winner"]["tier"], "C_EMPTY_CONTAINER_ITERATOR_GUARD")
                self.assertEqual(res["model_calls"], 0)

        # 3. Pass 0t: Hardcoded prefix char `std::string{'-', tok[j]}` -> `tok[0]`
        with self.subTest(case="cpp17_hardcoded_prefix_char_to_expr"):
            with tempfile.TemporaryDirectory(prefix="brain_cpp_iter32_pfx_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "flags.hpp": (
                            "#include <string>\n#include <vector>\n"
                            "inline bool is_pfx(char c) { return c == '-' || c == '+'; }\n"
                            "inline std::vector<std::string> expand_flags(const std::string &tok) {\n"
                            "  std::vector<std::string> out;\n"
                            "  if (tok.size() > 1 && is_pfx(tok[0]) && !is_pfx(tok[1])) {\n"
                            "    for (std::size_t j = 1; j < tok.size(); ++j) {\n"
                            "      auto part = std::string{'-', tok[j]};\n"
                            "      out.push_back(part);\n"
                            "    }\n"
                            "  }\n"
                            "  return out;\n"
                            "}\n"
                        ),
                        "test_flags.cpp": (
                            '#include <cstdio>\n#include "flags.hpp"\n'
                            "int main() {\n"
                            '  auto r = expand_flags("+ab");\n'
                            '  if (r.size() != 2 || r[0] != "+a" || r[1] != "+b") { std::fprintf(stderr, "FAIL:expand_flags\\n"); return 1; }\n'
                            "  return 0;\n"
                            "}\n"
                        ),
                    },
                )
                res = ML_SWE.solve_c_repository(root, ["test_flags.cpp"], timeout_s=25.0)
                self.assertEqual(res["status"], "VERIFIED", res)
                self.assertEqual(res["winner"]["tier"], "C_HARDCODED_PREFIX_CHAR_TO_EXPR")
                self.assertEqual(res["model_calls"], 0)

        # 4. Pass 0u (`C_RECURSIVE_VECTOR_ACCUMULATOR_MERGE`) & Pass 0v (`C_SIBLING_METHOD_TRAILING_BLOCK_SYNC`)
        with self.subTest(case="cpp17_recursive_accumulator_merge_and_sibling_trailing_sync"):
            with tempfile.TemporaryDirectory(prefix="brain_cpp_iter32_rec_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "subcmd.hpp": (
                            "#include <stdexcept>\n#include <string>\n#include <vector>\n"
                            "struct Node {\n"
                            "  Node *child = nullptr;\n"
                            "  std::vector<std::string> collect_unknown(const std::vector<std::string> &args) {\n"
                            "    std::vector<std::string> unknown_args{};\n"
                            "    for (std::size_t i = 0; i < args.size(); ++i) {\n"
                            '      if (args[i] == "sub" && child != nullptr) {\n'
                            "        std::vector<std::string> rest(args.begin() + i + 1, args.end());\n"
                            "        return child->collect_unknown(\n"
                            "            rest);\n"
                            "      }\n"
                            "      unknown_args.push_back(args[i]);\n"
                            "    }\n"
                            "    return unknown_args;\n"
                            "  }\n"
                            "};\n"
                        ),
                        "test_subcmd.cpp": (
                            '#include <cstdio>\n#include "subcmd.hpp"\n'
                            "int main() {\n"
                            "  Node leaf{};\n"
                            "  Node root{&leaf};\n"
                            '  auto res = root.collect_unknown({"--p", "sub", "--c"});\n'
                            '  if (res != std::vector<std::string>{"--p", "--c"}) { std::fprintf(stderr, "FAIL:collect_unknown\\n"); return 1; }\n'
                            "  return 0;\n"
                            "}\n"
                        ),
                    },
                )
                res_u = ML_SWE.solve_c_repository(root, ["test_subcmd.cpp"], timeout_s=25.0)
                self.assertEqual(res_u["status"], "VERIFIED", res_u)
                self.assertEqual(res_u["winner"]["tier"], "C_RECURSIVE_VECTOR_ACCUMULATOR_MERGE")

            with tempfile.TemporaryDirectory(prefix="brain_cpp_iter32_sib_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "validator.hpp": (
                            "#include <stdexcept>\n#include <vector>\n"
                            "struct Item { bool used = false; void validate() const {} };\n"
                            "struct Checker {\n"
                            "  std::vector<Item> items;\n"
                            "  void parse_strict() {\n"
                            "    for (const auto &it : items) {\n"
                            "      it.validate();\n"
                            "    }\n"
                            "    if (items.size() >= 2 && items[0].used && items[1].used) {\n"
                            '      throw std::runtime_error("mutex violation");\n'
                            "    }\n"
                            "  }\n"
                            "  int parse_known() {\n"
                            "    int count = 0;\n"
                            "    for (const auto &it : items) {\n"
                            "      it.validate();\n"
                            "    }\n"
                            "    return count;\n"
                            "  }\n"
                            "};\n"
                        ),
                        "test_validator.cpp": (
                            '#include <cstdio>\n#include "validator.hpp"\n'
                            "int main() {\n"
                            "  Checker c{{{true}, {true}}};\n"
                            "  try {\n"
                            "    c.parse_known();\n"
                            '    std::fprintf(stderr, "FAIL:parse_known did not throw\\n");\n'
                            "    return 1;\n"
                            "  } catch (const std::runtime_error &) {\n"
                            "    return 0;\n"
                            "  }\n"
                            "}\n"
                        ),
                    },
                )
                res_v = ML_SWE.solve_c_repository(root, ["test_validator.cpp"], timeout_s=25.0)
                self.assertEqual(res_v["status"], "VERIFIED", res_v)
                self.assertEqual(res_v["winner"]["tier"], "C_SIBLING_METHOD_TRAILING_BLOCK_SYNC")

    def test_11_iter33_ts_vitest_mocha_this_and_atomic_multifile_js(self) -> None:
        """Iter 33: Zero-dep Node v22 vitest_shim (TS+ESM NodeNext), Mocha `this` fixtures,
        Ops 0g/0h/0i/0j, cross-repo MemRL Tier-0 TS recall, and atomic multi-file JS repair via ONE Front Door."""
        from canonical.runtime.brain_unified_model_v1 import open_model
        from canonical.runtime import universal_epistemic_kernel_v1 as UEK

        # 1. Zero-dep TS + Vitest shim (describe.each + .js->.ts NodeNext resolution) + Op 0g + MemRL Tier-0 cross-repo transfer
        with self.subTest(case="ts_vitest_op0g_and_memrl_tier0_transfer"):
            with tempfile.TemporaryDirectory(prefix="brain_ts_iter33_0g_") as td:
                base = pathlib.Path(td)
                repo_a = base / "hdr_a"
                _write_files(
                    repo_a,
                    {
                        "package.json": '{"name":"hdr-a","devDependencies":{"vitest":"^3.0.0"}}\n',
                        "src/index.ts": (
                            'const TEXT_REGEXP = /^[\\u000b\\u0020-\\u007e]*$/;\n'
                            "export function validText(s: string): boolean {\n"
                            "  return TEXT_REGEXP.test(s);\n"
                            "}\n"
                        ),
                        "src/index.spec.ts": (
                            'import { describe, it, expect } from "vitest";\n'
                            'import { validText } from "./index.js";\n'
                            'describe("validText", () => {\n'
                            '  it.each(["hello", "a\\tb"])("accepts %s", (s: string) => {\n'
                            "    expect(validText(s)).toBe(true);\n"
                            "  });\n"
                            '  it("rejects vertical tab", () => {\n'
                            '    expect(validText("a\\u000bb")).toBe(false);\n'
                            "  });\n"
                            "});\n"
                        ),
                    },
                )
                mem = UEK.new_universal_memory()
                res_a = ML_SWE.solve_js_repository(repo_a, ["src/index.spec.ts"], memory=mem, timeout_s=20.0)
                self.assertEqual(res_a["status"], "VERIFIED", res_a)
                self.assertEqual(res_a["runner"], "vitest_shim")
                self.assertEqual(res_a["winner"]["tier"], "JS_REGEX_HTAB_VTAB_TYPO_FIX")
                lid = res_a["winner"]["learned_law_id"]
                self.assertTrue(lid and lid in mem["js_rewrite_laws"])

                # Cross-repo Tier-0 instant recall on a brand-new TS repo with the same \u000b typo
                repo_b = base / "hdr_b"
                _write_files(
                    repo_b,
                    {
                        "package.json": '{"name":"hdr-b","devDependencies":{"vitest":"^3.0.0"}}\n',
                        "src/fmt.ts": (
                            'const QUOTED_RE = /^[\\u000b\\u0020-\\u007e\\u0080-\\u00ff]*$/;\n'
                            "export function okQuoted(v: string): boolean { return QUOTED_RE.test(v); }\n"
                        ),
                        "src/fmt.spec.ts": (
                            'import { describe, it, assert } from "vitest";\n'
                            'import { okQuoted } from "./fmt";\n'
                            'describe("okQuoted", () => {\n'
                            '  it("allows HTAB and rejects VTAB", () => {\n'
                            '    assert.isTrue(okQuoted("foo\\tbar"));\n'
                            '    assert.isFalse(okQuoted("foo\\u000bbar"));\n'
                            "  });\n"
                            "});\n"
                        ),
                    },
                )
                res_b = ML_SWE.solve_js_repository(repo_b, ["src/fmt.spec.ts"], memory=mem, timeout_s=20.0)
                self.assertEqual(res_b["status"], "VERIFIED", res_b)
                self.assertEqual(res_b["winner"]["tier"], "JS_TIER0_SKILL_RECALL")
                self.assertEqual(res_b["winner"]["skill_id_used"], lid)
                self.assertEqual(res_b["winner"]["attempt"], 1)

        # 2. Op 0h: JS_MAP_FIRST_WRITE_GUARD (2-hunk TS parameter parser)
        with self.subTest(case="ts_vitest_op0h_map_first_write_guard"):
            with tempfile.TemporaryDirectory(prefix="brain_ts_iter33_0h_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "package.json": '{"name":"kv-ts","devDependencies":{"vitest":"^3.0.0"}}\n',
                        "src/kv.ts": (
                            "export function parseKv(raw: string): Record<string, string> {\n"
                            "  const params: Record<string, string> = {};\n"
                            '  for (const part of raw.split(";")) {\n'
                            '    const idx = part.indexOf("=");\n'
                            "    if (idx < 0) continue;\n"
                            "    const key = part.slice(0, idx).trim();\n"
                            "    const val = part.slice(idx + 1).trim();\n"
                            '    if (val.startsWith(\'"\') && val.endsWith(\'"\')) {\n'
                            "      params[key] = val.slice(1, -1);\n"
                            "      continue;\n"
                            "    }\n"
                            "    params[key] = val;\n"
                            "  }\n"
                            "  return params;\n"
                            "}\n"
                        ),
                        "src/kv.spec.ts": (
                            'import { describe, it, expect } from "vitest";\n'
                            'import { parseKv } from "./kv";\n'
                            'describe("parseKv", () => {\n'
                            '  it("keeps first duplicate parameter", () => {\n'
                            '    expect(parseKv(\'a="first"; a=second; b=one; b="two"\')).toEqual({ a: "first", b: "one" });\n'
                            "  });\n"
                            "});\n"
                        ),
                    },
                )
                res_h = ML_SWE.solve_js_repository(root, ["src/kv.spec.ts"], timeout_s=20.0)
                self.assertEqual(res_h["status"], "VERIFIED", res_h)
                self.assertEqual(res_h["winner"]["tier"], "JS_MAP_FIRST_WRITE_GUARD")

        # 3. Op 0i: JS_STRICT_PARSEINT_DECIMAL_GUARD (non-empty token sentinel guard)
        with self.subTest(case="js_mocha_op0i_strict_parseint_sentinel_guard"):
            with tempfile.TemporaryDirectory(prefix="brain_js_iter33_0i_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "package.json": '{"name":"span-js","devDependencies":{"mocha":"^10.0.0"}}\n',
                        "index.js": (
                            "module.exports = function parseSpan(size, str) {\n"
                            "  var eq = str.indexOf('=');\n"
                            "  if (eq === -1) return -2;\n"
                            "  var parts = str.slice(eq + 1).split('-');\n"
                            "  var start = parseInt(parts[0], 10);\n"
                            "  var end = parseInt(parts[1], 10);\n"
                            "  if (isNaN(start)) { start = size - end; end = size - 1; }\n"
                            "  else if (isNaN(end)) { end = size - 1; }\n"
                            "  if (isNaN(start) || isNaN(end) || start > end) return -1;\n"
                            "  return { start: start, end: end };\n"
                            "};\n"
                        ),
                        "test/span.js": (
                            "var assert = require('assert');\n"
                            "var parseSpan = require('..');\n"
                            "describe('parseSpan', function () {\n"
                            "  it('parses valid and suffix ranges', function () {\n"
                            "    assert.deepStrictEqual(parseSpan(200, 'bytes=0-10'), { start: 0, end: 10 });\n"
                            "    assert.deepStrictEqual(parseSpan(200, 'bytes=-50'), { start: 150, end: 199 });\n"
                            "  });\n"
                            "  it('returns -2 for non-numeric start or end', function () {\n"
                            "    assert.strictEqual(parseSpan(200, 'bytes=x-10'), -2);\n"
                            "    assert.strictEqual(parseSpan(200, 'bytes=10-y'), -2);\n"
                            "  });\n"
                            "});\n"
                        ),
                    },
                )
                res_i = ML_SWE.solve_js_repository(root, ["test/span.js"], timeout_s=20.0)
                self.assertEqual(res_i["status"], "VERIFIED", res_i)
                self.assertEqual(res_i["winner"]["tier"], "JS_STRICT_PARSEINT_DECIMAL_GUARD")

        # 4. Mocha `this`-context fixtures + Op 0j (`JS_VAR_PARAM_SHADOW_TO_LET`) atomic multi-file repair via ONE Front Door
        with self.subTest(case="js_mocha_this_and_atomic_multifile_op0j_frontdoor"):
            with tempfile.TemporaryDirectory(prefix="brain_js_iter33_0j_") as td:
                root = pathlib.Path(td)
                mod_src = (
                    "module.exports = function parseEntry(str, i) {\n"
                    "  var parts = str.split(';');\n"
                    "  var q = 1;\n"
                    "  for (var i = 1; i < parts.length; i++) {\n"
                    "    var kv = parts[i].trim().split('=');\n"
                    "    if (kv[0] === 'q') q = parseFloat(kv[1]);\n"
                    "  }\n"
                    "  return { name: parts[0].trim(), q: q, i: i };\n"
                    "};\n"
                )
                _write_files(
                    root,
                    {
                        "package.json": '{"name":"neg-mini","devDependencies":{"mocha":"^10.0.0"}}\n',
                        "lib/alpha.js": mod_src,
                        "lib/beta.js": mod_src,
                        "test/alpha.js": (
                            "var assert = require('assert');\n"
                            "var parseAlpha = require('../lib/alpha');\n"
                            "describe('alpha with mocha this fixture', function () {\n"
                            "  beforeEach(function () { this.header = 'utf-8;level=1;q=0.8'; });\n"
                            "  it('preserves caller index parameter i', function () {\n"
                            "    var res = parseAlpha(this.header, 0);\n"
                            "    assert.strictEqual(res.i, 0);\n"
                            "    assert.strictEqual(res.q, 0.8);\n"
                            "  });\n"
                            "});\n"
                        ),
                        "test/beta.js": (
                            "var assert = require('assert');\n"
                            "var parseBeta = require('../lib/beta');\n"
                            "describe('beta sibling check', function () {\n"
                            "  beforeEach(function () { this.header = 'gzip;x=1;q=0.5'; });\n"
                            "  it('preserves caller index parameter i in sibling module', function () {\n"
                            "    var res = parseBeta(this.header, 2);\n"
                            "    assert.strictEqual(res.i, 2);\n"
                            "    assert.strictEqual(res.q, 0.5);\n"
                            "  });\n"
                            "});\n"
                        ),
                    },
                )
                model = open_model()
                out = model.solve(
                    "Fix failing Mocha test test/alpha.js in neg-mini",
                    mode="EPISTEMIC",
                    inputs={"workspace": str(root)},
                )
                er = out["epistemic_result"]
                self.assertEqual(er["status"], "VERIFIED", er)
                self.assertEqual(er["mode"], "CAUSAL_ANGELIC_JS_SWE")
                self.assertEqual(er["model_calls"], 0)
                self.assertEqual(er["parameters_stored"], 0)
                self.assertEqual(er["authority"], "NONE")
                w = er["swe_result"]["winner"]
                self.assertEqual(w["tier"], "JS_VAR_PARAM_SHADOW_TO_LET")
                self.assertIn("lib/beta.js", w["extra_patches"])
                self.assertIn("for (let i = 1;", (root / "lib/alpha.js").read_text(encoding="utf-8"))
                self.assertIn("for (let i = 1;", (root / "lib/beta.js").read_text(encoding="utf-8"))

    def test_12_iter37_js_switch_alias_coerce_cve_and_cpp_basic_ostream(self) -> None:
        """Iter 37 universal causal laws via ONE Front Door (`model_calls=0`, `parameters_stored=0`):
        1. `Op 0k` (`JS_SWITCH_CASE_ALIAS_FALLTHROUGH`): ASCII `0x20` -> `+0x09` (HTAB) & `'utf-8'` -> `+'utf8'`.
        2. `Op 0l` (`JS_COERCE_STRICT_STRING_GUARD`): atomic multi-file CVE prototype-pollution guard coercion (`uvu_shim`).
        3. `Pass 0w` (`CPP_BASIC_OSTREAM_CSTR_WRITE`): `std::basic_ostream<char, CustomTraits>` streaming `std::string`.
        """
        model = open_model()

        # 1. JS switch-case fall-through alias abduction (`0x20` + `0x09` HTAB)
        with self.subTest(case="js_switch_case_alias_htab"):
            with tempfile.TemporaryDirectory(prefix="brain_iter37_sw_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "package.json": '{"name": "tok-mini", "version": "1.0.0"}\n',
                        "index.js": (
                            "module.exports = function parseTokens (str) {\n"
                            "  var list = [], start = 0, end = 0;\n"
                            "  for (var i = 0; i < str.length; i++) {\n"
                            "    switch (str.charCodeAt(i)) {\n"
                            "      case 0x20:\n"
                            "        if (start === end) start = end = i + 1;\n"
                            "        break;\n"
                            "      case 0x2c:\n"
                            "        list.push(str.substring(start, end));\n"
                            "        start = end = i + 1;\n"
                            "        break;\n"
                            "      default:\n"
                            "        end = i + 1;\n"
                            "    }\n"
                            "  }\n"
                            "  list.push(str.substring(start, end));\n"
                            "  return list;\n"
                            "};\n"
                        ),
                        "test/tok.js": (
                            "var assert = require('assert');\n"
                            "var parseTokens = require('..');\n"
                            "describe('parseTokens', function () {\n"
                            "  it('handles HTAB optional whitespace', function () {\n"
                            "    assert.deepStrictEqual(parseTokens('a,\\tb'), ['a', 'b']);\n"
                            "  });\n"
                            "});\n"
                        ),
                    },
                )
                out = model.solve("Fix failing JS test test/tok.js", mode="EPISTEMIC", inputs={"workspace": str(root)})
                er = out["epistemic_result"]
                self.assertEqual(er["status"], "VERIFIED", er)
                self.assertEqual(er["swe_result"]["winner"]["tier"], "JS_SWITCH_CASE_ALIAS_FALLTHROUGH")
                self.assertIn("case 0x09:", (root / "index.js").read_text(encoding="utf-8"))

        # 2. JS implicit-string-coercion CVE guard + multi-file atomic patch via `uvu_shim`
        with self.subTest(case="js_coerce_strict_string_guard_multifile_uvu"):
            with tempfile.TemporaryDirectory(prefix="brain_iter37_cve_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "package.json": '{"name": "dset-mini", "version": "1.0.0", "devDependencies": {"uvu": "0.5.6"}}\n',
                        "src/index.js": (
                            "export function setPath(obj, keys, val) {\n"
                            "  var i = 0, t = obj, k;\n"
                            "  while (i < keys.length) {\n"
                            "    k = keys[i++];\n"
                            "    if (k === '__proto__' || k === 'constructor' || k === 'prototype') break;\n"
                            "    t = t[k] = (i === keys.length) ? val : (t[k] || {});\n"
                            "  }\n"
                            "}\n"
                        ),
                        "src/merge.js": (
                            "export function mergePath(obj, keys, val) {\n"
                            "  var i = 0, t = obj, k;\n"
                            "  while (i < keys.length) {\n"
                            "    k = keys[i++];\n"
                            "    if (k === '__proto__' || k === 'constructor' || k === 'prototype') break;\n"
                            "    t = t[k] = (i === keys.length) ? val : (t[k] || {});\n"
                            "  }\n"
                            "}\n"
                        ),
                        "test/index.js": (
                            "import { suite } from 'uvu';\n"
                            "import * as assert from 'uvu/assert';\n"
                            "import { setPath } from '../src';\n"
                            "import { mergePath } from '../src/merge';\n"
                            "const s = suite('cve');\n"
                            "s('blocks array-coerced __proto__ in both modules', () => {\n"
                            "  const a = {}, b = {};\n"
                            "  setPath(a, [['__proto__'], 'p1'], 1);\n"
                            "  mergePath(b, [['__proto__'], 'p2'], 2);\n"
                            "  assert.is(({}).p1, undefined);\n"
                            "  assert.is(({}).p2, undefined);\n"
                            "});\n"
                            "s.run();\n"
                        ),
                    },
                )
                out = model.solve("Fix failing JS test test/index.js", mode="EPISTEMIC", inputs={"workspace": str(root)})
                er = out["epistemic_result"]
                self.assertEqual(er["status"], "VERIFIED", er)
                self.assertEqual(er["swe_result"]["winner"]["tier"], "JS_COERCE_STRICT_STRING_GUARD")
                self.assertIn("'' + k === '__proto__'", (root / "src/index.js").read_text(encoding="utf-8"))
                self.assertIn("'' + k === '__proto__'", (root / "src/merge.js").read_text(encoding="utf-8"))

        # 3. C++17 `std::basic_ostream<char, CustomTraits>` streaming `std::string` (`Pass 0w`)
        with self.subTest(case="cpp_basic_ostream_custom_traits"):
            with tempfile.TemporaryDirectory(prefix="brain_iter37_os_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "include/ver.hpp": (
                            "#pragma once\n"
                            "#include <ostream>\n"
                            "#include <string>\n"
                            "struct Ver {\n"
                            "  int a, b;\n"
                            "  std::string to_string() const { return std::to_string(a) + \".\" + std::to_string(b); }\n"
                            "};\n"
                            "template <typename Traits>\n"
                            "std::basic_ostream<char, Traits>& operator<<(std::basic_ostream<char, Traits>& os, const Ver& v) {\n"
                            "  return os << v.to_string();\n"
                            "}\n"
                        ),
                        "test/test_stream.cpp": (
                            "#include <cassert>\n"
                            "#include <sstream>\n"
                            "#include \"ver.hpp\"\n"
                            "struct CustomTraits : std::char_traits<char> {};\n"
                            "int main() {\n"
                            "  std::basic_ostringstream<char, CustomTraits> oss;\n"
                            "  oss << Ver{1, 2};\n"
                            "  assert(oss.str().size() == 3);\n"
                            "  return 0;\n"
                            "}\n"
                        ),
                    },
                )
                out = model.solve("Fix failing C++ test test/test_stream.cpp", mode="EPISTEMIC", inputs={"workspace": str(root)})
                er = out["epistemic_result"]
                self.assertEqual(er["status"], "VERIFIED", er)
                self.assertEqual(er["swe_result"]["winner"]["tier"], "CPP_BASIC_OSTREAM_CSTR_WRITE")
                self.assertIn(".c_str()", (root / "include/ver.hpp").read_text(encoding="utf-8"))

    def test_iter42_c_heap_uaf_reorder_js_regex_backslash_and_precompile_cache(self) -> None:
        """Iter 42: C CWE-416 Heap-UAF compute-before-free reorder (Pass 0x), JS regex charclass backslash (Op 0m), and C static-obj caching with contrib/*.cpp."""
        model = open_model()

        # 1. C Pass 0x (`C_HEAP_UAF_FREE_BEFORE_USE_REORDER`): ASan heap-use-after-free when patch is subtree of target
        with self.subTest(case="c_heap_uaf_compute_before_free"):
            with tempfile.TemporaryDirectory(prefix="brain_iter42_uaf_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "node.h": (
                            "#pragma once\n"
                            "typedef struct Node { int val; struct Node *child; } Node;\n"
                            "Node *node_new(int val);\n"
                            "Node *node_dup(const Node *n);\n"
                            "void node_Delete(Node *n);\n"
                            "Node *replace_tree(Node *target, const Node *patch);\n"
                        ),
                        "node.c": (
                            "#include <stdlib.h>\n"
                            "#include \"node.h\"\n"
                            "Node *node_new(int val) {\n"
                            "    Node *n = (Node *)calloc(1, sizeof(Node));\n"
                            "    n->val = val;\n"
                            "    return n;\n"
                            "}\n"
                            "Node *node_dup(const Node *n) {\n"
                            "    if (!n) return NULL;\n"
                            "    Node *c = node_new(n->val);\n"
                            "    c->child = node_dup(n->child);\n"
                            "    return c;\n"
                            "}\n"
                            "void node_Delete(Node *n) {\n"
                            "    if (!n) return;\n"
                            "    node_Delete(n->child);\n"
                            "    free(n);\n"
                            "}\n"
                            "Node *replace_tree(Node *target, const Node *patch) {\n"
                            "    node_Delete(target);\n"
                            "    return node_dup(patch);\n"
                            "}\n"
                        ),
                        "test_uaf.c": (
                            "#include <assert.h>\n"
                            "#include <stddef.h>\n"
                            "#include \"node.h\"\n"
                            "int main(void) {\n"
                            "    Node *root = node_new(1);\n"
                            "    root->child = node_new(42);\n"
                            "    Node *res = replace_tree(root, root->child);\n"
                            "    assert(res != NULL && res->val == 42);\n"
                            "    node_Delete(res);\n"
                            "    return 0;\n"
                            "}\n"
                        ),
                    },
                )
                out = model.solve("Fix ASan heap-use-after-free in test_uaf.c", mode="EPISTEMIC", inputs={"workspace": str(root)})
                er = out["epistemic_result"]
                self.assertEqual(er["status"], "VERIFIED", er)
                self.assertEqual(er["swe_result"]["winner"]["tier"], "C_HEAP_UAF_FREE_BEFORE_USE_REORDER")
                self.assertIn("_brain_uaf_res", (root / "node.c").read_text(encoding="utf-8"))

        # 2. JS Op 0m (`JS_REGEX_CHARCLASS_ESCAPED_BACKSLASH`): POSIX [:punct:] missing literal backslash
        with self.subTest(case="js_regex_charclass_escaped_backslash"):
            with tempfile.TemporaryDirectory(prefix="brain_iter42_jsrx_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "package.json": '{"name":"punct-demo","version":"1.0.0"}\n',
                        "lib/constants.js": (
                            "const POSIX = {\n"
                            "  punct: '\\\\-!\"#$%&\\'()\\\\*+,./:;<=>?@[\\\\]^_`{|}~',\n"
                            "};\n"
                            "module.exports = { isPunct: (s) => new RegExp('^[' + POSIX.punct + ']+$').test(s) };\n"
                        ),
                        "test/punct.test.js": (
                            "const test = require('node:test');\n"
                            "const assert = require('node:assert/strict');\n"
                            "const { isPunct } = require('../lib/constants.js');\n"
                            "test('matches brackets and backslash', () => {\n"
                            "  assert.equal(isPunct('['), true);\n"
                            "  assert.equal(isPunct(']'), true);\n"
                            "  assert.equal(isPunct('\\\\'), true);\n"
                            "  assert.equal(isPunct('a'), false);\n"
                            "});\n"
                        ),
                    },
                )
                out = model.solve(
                    "Fix failing JS test test/punct.test.js",
                    mode="EPISTEMIC",
                    inputs={"workspace": str(root), "test_targets": ["test/punct.test.js"]},
                )
                er = out["epistemic_result"]
                self.assertEqual(er["status"], "VERIFIED", er)
                self.assertEqual(er["swe_result"]["winner"]["tier"], "JS_REGEX_CHARCLASS_ESCAPED_BACKSLASH")

        # 3. _precompile_c_static_objs caches unchanging test TU even when unrelated contrib/extra.cpp exists
        with self.subTest(case="c_precompile_ignores_unreferenced_contrib_cpp"):
            with tempfile.TemporaryDirectory(prefix="brain_iter42_prec_") as td:
                root = pathlib.Path(td)
                cache = root / "_obj_cache"
                cache.mkdir()
                _write_files(
                    root,
                    {
                        "mylib.h": "#pragma once\nint add_one(int x);\n",
                        "mylib.cpp": "#include \"mylib.h\"\nint add_one(int x) { return x + 1; }\n",
                        "contrib/unused.cpp": "int unused_fn() { return 0; }\n",
                        "test_lib.cpp": "#include <cassert>\n#include \"mylib.h\"\nint main() { assert(add_one(1) == 2); return 0; }\n",
                    },
                )
                src_files, _, _ = ML_SWE._discover_c_files(root)
                _, bcmd, _, _ = ML_SWE.detect_c_test_spec(root, ["test_lib.cpp"], sanitizer=True)
                pre = ML_SWE._precompile_c_static_objs(root, bcmd, set(src_files), cache, timeout_s=30.0)
                self.assertTrue(any(tok.endswith("_test_lib.o") for tok in pre), pre)

    def test_15_iter46_js_unicode_duality_and_c_linked_node_pointer_swap(self) -> None:
        """Iter 46: Verify JS `fromCharCode -> range-safe fromCodePoint` (multi-file fair quota)
        and C linked-list node pointer swap vs shallow field copy via ONE Front Door."""
        model = open_model()

        with self.subTest(case="js_fromcharcode_astral_codepoint_and_multifile_fair_quota"):
            with tempfile.TemporaryDirectory(prefix="brain_iter46_js_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "package.json": json.dumps({"name": "mini-decode", "version": "1.0.0"}),
                        "lib/helper.js": "\n".join(
                            f"exports.h{i} = function(x) {{ return x === {i} ? x : x + 1; }};" for i in range(40)
                        ) + "\n",
                        "lib/decode.js": (
                            "exports.decodeEntities = function (str) {\n"
                            "  return str.replace(/&#(\\d+);/g, function ($0, numStr) {\n"
                            "    return String.fromCharCode(parseInt(numStr, 10));\n"
                            "  });\n"
                            "};\n"
                        ),
                        "test/decode.test.js": (
                            "const test = require('node:test');\n"
                            "const assert = require('node:assert/strict');\n"
                            "const { decodeEntities } = require('../lib/decode.js');\n"
                            "test('decodes astral emoji U+1F600', () => {\n"
                            "  assert.equal(decodeEntities('&#128512;'), '\\uD83D\\uDE00');\n"
                            "  assert.equal(decodeEntities('&#65;'), 'A');\n"
                            "});\n"
                        ),
                    },
                )
                out = model.solve(
                    "Fix failing JS test test/decode.test.js",
                    mode="EPISTEMIC",
                    inputs={"workspace": str(root)},
                )
                er = out["epistemic_result"]
                self.assertEqual(er["status"], "VERIFIED", er)
                self.assertEqual(er["swe_result"]["winner"]["tier"], "JS_STDLIB_UNICODE_NUMERIC_DUALITY")

        with self.subTest(case="c_linked_node_pointer_swap_vs_shallow_field_copy"):
            with tempfile.TemporaryDirectory(prefix="brain_iter46_c_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "node_map.h": (
                            "#pragma once\n#include <stdbool.h>\n#include <string.h>\n"
                            "typedef struct Node { int tag; int len; const char *key; struct Node *next; } Node;\n"
                            "static inline bool map_replace(Node *head, const char *k, Node *val) {\n"
                            "  Node *cur = head;\n"
                            "  while (cur) {\n"
                            "    if (cur->key && strcmp(cur->key, k) == 0 && cur->next) {\n"
                            "      cur->next->tag = val->tag;\n"
                            "      cur->next->len = val->len;\n"
                            "      return true;\n"
                            "    }\n"
                            "    cur = cur->next ? cur->next->next : NULL;\n"
                            "  }\n"
                            "  return false;\n"
                            "}\n"
                        ),
                        "test_map.c": (
                            '#include <assert.h>\n#include <stddef.h>\n#include "node_map.h"\n'
                            "int main(void) {\n"
                            "  Node v_old = {1, 0, NULL, NULL};\n"
                            "  Node k_node = {0, 0, \"c\", &v_old};\n"
                            "  Node v_new = {2, 0, NULL, NULL};\n"
                            "  assert(map_replace(&k_node, \"c\", &v_new));\n"
                            "  v_new.len = 1;\n"
                            "  assert(k_node.next->len == 1);\n"
                            "  return 0;\n"
                            "}\n"
                        ),
                    },
                )
                res = ML_SWE.solve_c_repository(root, ["test_map.c"], timeout_s=20.0)
                self.assertEqual(res["status"], "VERIFIED", res)
                self.assertEqual(res["winner"]["tier"], "C_LINKED_NODE_POINTER_SWAP_VS_FIELD_COPY")
                self.assertEqual(res["model_calls"], 0)

    def test_18_sourcemap_v3_vlq_ts_interface_s3_and_js_len0_side_effect_guard(self) -> None:
        """Iter 49: ECMA-426 Source Map v3 VLQ decoder + TS Interface Peer-Expr S3 Guard + JS side-effect-preserving len0 S3 guard."""
        model = open_model()

        with self.subTest(case="sourcemap_v3_vlq_decoder_external_and_inline"):
            with tempfile.TemporaryDirectory(prefix="brain_iter49_sm_") as td:
                root = pathlib.Path(td)
                # VLQ: line 1 -> src 0 line 5 (AAAA + 4 lines = AAI A -> A=0,A=0,I=+4,A=0), line 2 -> src 0 line 6 (AACA)
                sm_obj = {
                    "version": 3,
                    "sources": ["../src/rules.ts"],
                    "mappings": "AAIA;AACA",
                }
                _write_files(
                    root,
                    {
                        "src/rules.ts": "//1\n//2\n//3\n//4\nexport const x = 1;\nexport const y = 2;\n",
                        "dist/bundle.mjs": "export const x = 1;\nexport const y = 2;\n//# sourceMappingURL=bundle.mjs.map\n",
                        "dist/bundle.mjs.map": json.dumps(sm_obj),
                    },
                )
                lmap = ML_SWE._load_sourcemap_line_map(root / "dist/bundle.mjs", root, {"src/rules.ts"})
                self.assertEqual(lmap.get(1), [("src/rules.ts", 5)])
                self.assertEqual(lmap.get(2), [("src/rules.ts", 6)])

        with self.subTest(case="ts_interface_peer_expr_s3_guard_via_sourcemap"):
            with tempfile.TemporaryDirectory(prefix="brain_iter49_ts_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "package.json": json.dumps(
                            {
                                "name": "mini-ts-rules",
                                "type": "module",
                                "main": "dist/bundle.mjs",
                                "scripts": {
                                    "build": "node scripts/build.mjs",
                                    "test": "node --test test/rules.test.mjs",
                                },
                            }
                        ),
                        "scripts/build.mjs": (
                            "import fs from 'node:fs';\n"
                            "fs.mkdirSync('dist', { recursive: true });\n"
                            "const src = fs.readFileSync('src/rules.ts', 'utf8');\n"
                            "// Strip simple TS parameter annotations for zero-dep bundle + emit 1:1 Source Map v3\n"
                            "const js = src\n"
                            "  .replace(/export interface[\\s\\S]*?^\\}/gm, '')\n"
                            "  .replace(/\\(ctx:\\s*RenderCtx\\):\\s*\\w+/g, '(ctx)')\n"
                            "  + '\\n//# sourceMappingURL=bundle.mjs.map\\n';\n"
                            "fs.writeFileSync('dist/bundle.mjs', js);\n"
                            "const nLines = js.split('\\n').length;\n"
                            "const mappings = Array.from({ length: nLines }, (_, i) => i === 0 ? 'AAAA' : 'AACA').join(';');\n"
                            "fs.writeFileSync('dist/bundle.mjs.map', JSON.stringify({ version: 3, sources: ['../src/rules.ts'], mappings }));\n"
                        ),
                        "src/types.ts": (
                            "export interface BaseToken {\n"
                            "  tag: string\n"
                            "  explicit: boolean\n"
                            "}\n"
                            "export interface ValueToken extends BaseToken {\n"
                            "  kind: 'scalar'\n"
                            "  text: string\n"
                            "}\n"
                            "export interface RenderOpts {\n"
                            "  forceWrap: boolean\n"
                            "  defaultTag: string\n"
                            "}\n"
                            "export interface RenderCtx {\n"
                            "  readonly token: Readonly<ValueToken>\n"
                            "  readonly isKey: boolean\n"
                            "  readonly opts: Readonly<RenderOpts>\n"
                            "  wrapped: boolean\n"
                            "}\n"
                        ),
                        "src/peer.ts": (
                            "export function isDefaultToken (ctx: RenderCtx): boolean {\n"
                            "  return ctx.token.tag === ctx.opts.defaultTag;\n"
                            "}\n"
                        ),
                        "src/rules.ts": (
                            "export function applyForceWrap (ctx: RenderCtx): boolean {\n"
                            "  if (!ctx.opts.forceWrap) return false;\n"
                            "  if (ctx.isKey || ctx.wrapped) return false;\n"
                            "  ctx.wrapped = true;\n"
                            "  return true;\n"
                            "}\n"
                        ),
                        "test/rules.test.mjs": (
                            "import test from 'node:test';\n"
                            "import assert from 'node:assert/strict';\n"
                            "import { applyForceWrap } from '../dist/bundle.mjs';\n"
                            "test('forceWrap only wraps default string tag, not int tag', () => {\n"
                            "  const strCtx = { token: { kind: 'scalar', tag: 'str', explicit: false, text: 'hi' }, isKey: false, opts: { forceWrap: true, defaultTag: 'str' }, wrapped: false };\n"
                            "  assert.equal(applyForceWrap(strCtx), true);\n"
                            "  const intCtx = { token: { kind: 'scalar', tag: 'int', explicit: false, text: '42' }, isKey: false, opts: { forceWrap: true, defaultTag: 'str' }, wrapped: false };\n"
                            "  assert.equal(applyForceWrap(intCtx), false);\n"
                            "});\n"
                        ),
                    },
                )
                subprocess.run(["node", "scripts/build.mjs"], cwd=str(root), check=True, capture_output=True)
                out = model.solve(
                    "Fix failing JS test test/rules.test.mjs",
                    mode="EPISTEMIC",
                    inputs={"workspace": str(root), "memory": UEK.new_universal_memory(), "timeout_s": 25.0},
                )
                er = out["epistemic_result"]
                self.assertEqual(er["status"], "VERIFIED", er)
                self.assertEqual(er["swe_result"]["winner"]["tier"], "JS_TS_INTERFACE_S3_GUARD")
                self.assertEqual(out["model_calls"], 0)
                self.assertEqual(out["parameters_stored"], 0)

        with self.subTest(case="js_len0_side_effect_preserving_s3_guard"):
            with tempfile.TemporaryDirectory(prefix="brain_iter49_qs_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "lib/encode.js": (
                            "function encodeVal(str) {\n"
                            "  if (str.length === 0) {\n"
                            "    return str;\n"
                            "  }\n"
                            "  return String(str);\n"
                            "}\n"
                            "module.exports = { encodeVal };\n"
                        ),
                        "test/encode.test.js": (
                            "const test = require('node:test');\n"
                            "const assert = require('node:assert/strict');\n"
                            "const { encodeVal } = require('../lib/encode.js');\n"
                            "test('encodeVal preserves null/undefined TypeError and coerces length-0 non-strings', () => {\n"
                            "  assert.equal(encodeVal(''), '');\n"
                            "  assert.equal(encodeVal('abc'), 'abc');\n"
                            "  assert.equal(encodeVal({ length: 0, toString: () => 'obj' }), 'obj');\n"
                            "  assert.throws(() => encodeVal(null), TypeError);\n"
                            "  assert.throws(() => encodeVal(undefined), TypeError);\n"
                            "});\n"
                        ),
                    },
                )
                out = model.solve(
                    "Fix failing JS test test/encode.test.js",
                    mode="EPISTEMIC",
                    inputs={"workspace": str(root), "memory": UEK.new_universal_memory(), "timeout_s": 25.0},
                )
                er = out["epistemic_result"]
                self.assertEqual(er["status"], "VERIFIED", er)
                self.assertEqual(er["swe_result"]["winner"]["tier"], "JS_S3_BRANCH_STRENGTHEN")
                self.assertEqual(out["model_calls"], 0)
                self.assertEqual(out["parameters_stored"], 0)

    def test_19_js_null_proto_container_sync_clobber_and_helper(self) -> None:
        """Iter 52: JS null-prototype container preservation (`JS_NULL_PROTO_CONTAINER_SYNC`).

        Covers both:
          (a) Null-proto variable initialized via `options.plainObjects ? { __proto__: null } : {}`
              and accidentally clobbered by single-key literal `obj = { 0: leaf };` -> `obj[0] = leaf;`.
          (b) Bare `var result = {};` inside a function calling sibling null-proto helper `emptyCopyOf`
              synced to `var result = emptyCopyOf(input);`.
        """
        model = open_model()
        with self.subTest(case="null_proto_clobber_fix"):
            with tempfile.TemporaryDirectory(prefix="iter52_js_np_clobber_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "lib/parse.js": (
                            "function wrapLeaf(leaf, options) {\n"
                            "  var obj = options.plainObjects ? { __proto__: null } : {};\n"
                            "  if (!options.parseArrays) {\n"
                            "    obj = { 0: leaf };\n"
                            "  } else {\n"
                            "    obj[0] = leaf;\n"
                            "  }\n"
                            "  return obj;\n"
                            "}\n"
                            "module.exports = { wrapLeaf };\n"
                        ),
                        "test/parse.test.js": (
                            "const test = require('node:test');\n"
                            "const assert = require('node:assert/strict');\n"
                            "const { wrapLeaf } = require('../lib/parse.js');\n"
                            "test('wrapLeaf preserves null prototype when parseArrays is false', () => {\n"
                            "  const res = wrapLeaf('b', { parseArrays: false, plainObjects: true });\n"
                            "  assert.equal(Object.getPrototypeOf(res), null);\n"
                            "  assert.equal(res[0], 'b');\n"
                            "  const norm = wrapLeaf('b', { parseArrays: false, plainObjects: false });\n"
                            "  assert.equal(Object.getPrototypeOf(norm), Object.prototype);\n"
                            "  assert.equal(norm[0], 'b');\n"
                            "});\n"
                        ),
                    },
                )
                out = model.solve(
                    "Fix failing JS test test/parse.test.js",
                    mode="EPISTEMIC",
                    inputs={"workspace": str(root), "memory": UEK.new_universal_memory(), "timeout_s": 25.0},
                )
                er = out["epistemic_result"]
                self.assertEqual(er["status"], "VERIFIED", er)
                self.assertEqual(er["swe_result"]["winner"]["tier"], "JS_NULL_PROTO_CONTAINER_SYNC")
                self.assertEqual(out["model_calls"], 0)
                self.assertEqual(out["parameters_stored"], 0)

        with self.subTest(case="null_proto_helper_sync"):
            with tempfile.TemporaryDirectory(prefix="iter52_js_np_helper_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "lib/clone.js": (
                            "var emptyCopyOf = function emptyCopyOf(value) {\n"
                            "  return Object.getPrototypeOf(value) === null ? { __proto__: null } : {};\n"
                            "};\n"
                            "var copyInput = function copyInput(input) {\n"
                            "  var result = {};\n"
                            "  for (var k of Object.keys(input)) {\n"
                            "    var v = input[k];\n"
                            "    result[k] = (v && typeof v === 'object') ? Object.assign(emptyCopyOf(v), v) : v;\n"
                            "  }\n"
                            "  return result;\n"
                            "};\n"
                            "module.exports = { copyInput };\n"
                        ),
                        "test/clone.test.js": (
                            "const test = require('node:test');\n"
                            "const assert = require('node:assert/strict');\n"
                            "const { copyInput } = require('../lib/clone.js');\n"
                            "test('copyInput preserves root null prototype', () => {\n"
                            "  const src = Object.assign(Object.create(null), { a: 1, nested: Object.assign(Object.create(null), { b: 2 }) });\n"
                            "  const dst = copyInput(src);\n"
                            "  assert.equal(Object.getPrototypeOf(dst), null);\n"
                            "  assert.equal(Object.getPrototypeOf(dst.nested), null);\n"
                            "  assert.equal(dst.a, 1);\n"
                            "});\n"
                        ),
                    },
                )
                out = model.solve(
                    "Fix failing JS test test/clone.test.js",
                    mode="EPISTEMIC",
                    inputs={"workspace": str(root), "memory": UEK.new_universal_memory(), "timeout_s": 25.0},
                )
                er = out["epistemic_result"]
                self.assertEqual(er["status"], "VERIFIED", er)
                self.assertEqual(er["swe_result"]["winner"]["tier"], "JS_NULL_PROTO_CONTAINER_SYNC")
                self.assertEqual(out["model_calls"], 0)
                self.assertEqual(out["parameters_stored"], 0)

    def test_20_js_sibling_normalizer_and_nonempty_string_guard(self) -> None:
        """Iter 53: JS Op 0r (`JS_ARG_SIBLING_NORMALIZER_WRAP`) & Op 0s (`JS_TYPEOF_STRING_NONEMPTY_GUARD`).

        Verifies through ONE Front Door (`model_calls=0`, `parameters_stored=0`):
          (a) Op 0r wraps bare key argument in sibling 1-arg string normalizer inside `has.call(Object.prototype, k)`.
          (b) Op 0s strengthens `if (typeof delim !== 'string' ...)` -> `typeof delim !== 'string' || !delim`
              to prevent empty-string infinite-loop / wrong fallback.
        """
        model = open_model()
        with self.subTest(case="sibling_normalizer_wrap"):
            with tempfile.TemporaryDirectory(prefix="iter53_js_norm_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "lib/keys.js": (
                            "var has = Object.prototype.hasOwnProperty;\n"
                            "var stripBrackets = function (s) {\n"
                            "  return s.charAt(0) === '[' && s.charAt(s.length - 1) === ']' ? s.slice(1, -1) : s;\n"
                            "};\n"
                            "function parseFlat(key) {\n"
                            "  if (has.call(Object.prototype, key)) return null;\n"
                            "  return stripBrackets(key);\n"
                            "}\n"
                            "module.exports = { parseFlat };\n"
                        ),
                        "test/keys.test.js": (
                            "const test = require('node:test');\n"
                            "const assert = require('node:assert/strict');\n"
                            "const { parseFlat } = require('../lib/keys.js');\n"
                            "test('blocks bracketed prototype keys', () => {\n"
                            "  assert.equal(parseFlat('toString'), null);\n"
                            "  assert.equal(parseFlat('[toString]'), null);\n"
                            "  assert.equal(parseFlat('[safe]'), 'safe');\n"
                            "});\n"
                        ),
                    },
                )
                out = model.solve(
                    "Fix failing JS test test/keys.test.js",
                    mode="EPISTEMIC",
                    inputs={"workspace": str(root), "memory": UEK.new_universal_memory(), "timeout_s": 25.0},
                )
                er = out["epistemic_result"]
                self.assertEqual(er["status"], "VERIFIED", er)
                self.assertEqual(er["swe_result"]["winner"]["tier"], "JS_ARG_SIBLING_NORMALIZER_WRAP")
                self.assertEqual(out["model_calls"], 0)
                self.assertEqual(out["parameters_stored"], 0)

        with self.subTest(case="typeof_string_nonempty_guard"):
            with tempfile.TemporaryDirectory(prefix="iter53_js_nonempty_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "lib/csv.js": (
                            "function splitRow(line, delim) {\n"
                            "  if (typeof delim !== 'string'\n"
                            "      || delim === '\\n') {\n"
                            "    delim = ',';\n"
                            "  }\n"
                            "  return line.split(delim);\n"
                            "}\n"
                            "module.exports = { splitRow };\n"
                        ),
                        "test/csv.test.js": (
                            "const test = require('node:test');\n"
                            "const assert = require('node:assert/strict');\n"
                            "const { splitRow } = require('../lib/csv.js');\n"
                            "test('empty delimiter falls back to comma', () => {\n"
                            "  assert.deepEqual(splitRow('a,b,c', ''), ['a', 'b', 'c']);\n"
                            "  assert.deepEqual(splitRow('a;b;c', ';'), ['a', 'b', 'c']);\n"
                            "  assert.deepEqual(splitRow('a,b,c', null), ['a', 'b', 'c']);\n"
                            "});\n"
                        ),
                    },
                )
                out = model.solve(
                    "Fix failing JS test test/csv.test.js",
                    mode="EPISTEMIC",
                    inputs={"workspace": str(root), "memory": UEK.new_universal_memory(), "timeout_s": 25.0},
                )
                er = out["epistemic_result"]
                self.assertEqual(er["status"], "VERIFIED", er)
                self.assertEqual(er["swe_result"]["winner"]["tier"], "JS_TYPEOF_STRING_NONEMPTY_GUARD")
                self.assertEqual(out["model_calls"], 0)
                self.assertEqual(out["parameters_stored"], 0)

    def test_21_js_fastpath_join_nullish_sync_and_ava_detection(self) -> None:
        """Iter 54: JS Op 0t (`JS_FASTPATH_JOIN_NULLISH_SYNC`) + AVA runner detection.

        Verifies through ONE Front Door (`model_calls=0`, `parameters_stored=0`) that a broken
        `if (args.length === 2)` string-concatenation fast path sitting above `args.join(' ')`
        is repaired to match ECMAScript `Array.prototype.join` coercion (`null`/`undefined` -> `''`
        and `toString()` precedence over `valueOf()`).
        """
        model = open_model()
        with tempfile.TemporaryDirectory(prefix="iter54_js_fpjoin_") as td:
            root = pathlib.Path(td)
            _write_files(
                root,
                {
                    "lib/fmt.js": (
                        "function formatArgs(...args) {\n"
                        "  if (args.length === 1) {\n"
                        "    return '' + args[0];\n"
                        "  }\n"
                        "  if (args.length === 2) {\n"
                        "    return args[0] + ' ' + args[1];\n"
                        "  }\n"
                        "  return args.join(' ');\n"
                        "}\n"
                        "module.exports = { formatArgs };\n"
                    ),
                    "test/fmt.test.js": (
                        "const test = require('node:test');\n"
                        "const assert = require('node:assert/strict');\n"
                        "const { formatArgs } = require('../lib/fmt.js');\n"
                        "test('two-arg coercion matches Array.prototype.join', () => {\n"
                        "  assert.equal(formatArgs(null, 'foo'), ' foo');\n"
                        "  assert.equal(formatArgs('foo', undefined), 'foo ');\n"
                        "  const obj = { valueOf: () => 42, toString: () => 'ok' };\n"
                        "  assert.equal(formatArgs(obj, 'x'), 'ok x');\n"
                        "  assert.equal(formatArgs('a', 'b', 'c'), 'a b c');\n"
                        "});\n"
                    ),
                },
            )
            out = model.solve(
                "Fix failing JS test test/fmt.test.js",
                mode="EPISTEMIC",
                inputs={"workspace": str(root), "memory": UEK.new_universal_memory(), "timeout_s": 25.0},
            )
            er = out["epistemic_result"]
            self.assertEqual(er["status"], "VERIFIED", er)
            self.assertEqual(er["swe_result"]["winner"]["tier"], "JS_FASTPATH_JOIN_NULLISH_SYNC")
            self.assertEqual(out["model_calls"], 0)
            self.assertEqual(out["parameters_stored"], 0)

    def test_22_js_regex_dotall_newline_law(self) -> None:
        """Op 0u (`JS_REGEX_DOTALL_NEWLINE_LAW`): Co-applies tempered-dot `.)` -> `[\\s\\S])`
        across both full and fast-path regex builders when inputs contain newlines (`model_calls == 0`).
        """
        from canonical.runtime.brain_unified_model_v1 import open_model

        model = open_model()
        with tempfile.TemporaryDirectory(prefix="iter57_js_dotall_") as td:
            root = pathlib.Path(td)
            _write_files(
                root,
                {
                    "lib/matcher.js": (
                        "const DOT = '\\\\.';\n"
                        "function buildFull() {\n"
                        "  return `^(?:(?!${DOT}).)*?$`;\n"
                        "}\n"
                        "function buildFast() {\n"
                        "  return `^(?:(?!${DOT}).)*?$`;\n"
                        "}\n"
                        "function matchAny(str, fast) {\n"
                        "  return new RegExp(fast ? buildFast() : buildFull()).test(str);\n"
                        "}\n"
                        "module.exports = { matchAny };\n"
                    ),
                    "test/matcher.test.js": (
                        "const test = require('node:test');\n"
                        "const assert = require('node:assert/strict');\n"
                        "const { matchAny } = require('../lib/matcher.js');\n"
                        "test('matches strings containing newlines in both full and fast paths', () => {\n"
                        "  assert.equal(matchAny('hello\\nworld', false), true);\n"
                        "  assert.equal(matchAny('hello\\nworld', true), true);\n"
                        "  assert.equal(matchAny('.hidden', false), false);\n"
                        "  assert.equal(matchAny('.hidden', true), false);\n"
                        "});\n"
                    ),
                },
            )
            out = model.solve(
                "Fix failing JS test test/matcher.test.js",
                mode="EPISTEMIC",
                inputs={"workspace": str(root), "memory": UEK.new_universal_memory(), "timeout_s": 25.0},
            )
            er = out["epistemic_result"]
            self.assertEqual(er["status"], "VERIFIED", er)
            self.assertEqual(er["swe_result"]["winner"]["tier"], "JS_REGEX_DOTALL_NEWLINE_LAW")
            self.assertEqual(out["model_calls"], 0)
            self.assertEqual(out["parameters_stored"], 0)

    def test_23_iter59_ts_raw_loop_key_and_reject_guard_drop(self) -> None:
        """Iter 59 JS/TS laws (`model_calls == 0`, `parameters_stored == 0`):
        1. Op 0v (`JS_NORMALIZED_KEY_PRESERVE_RAW_INPUT`): alpha-renames shadowed inner loop var
           and preserves raw outer input key across both array and scalar branches.
        2. Op 0w (`JS_GUARD_CONJUNCT_DROP_ON_REJECT`): widens rejection guard `(flag && pred(ch))`
           to `pred(ch)` when tests expect rejection (`Missing expected exception` / `forbid`).
        3. `_check_js_syntax`: comment/string-aware `.ts` delimiter balance check (`/* { */`).
        """
        # 3. Comment-aware TypeScript syntax check
        self.assertTrue(
            ML_SWE._check_js_syntax(
                "src/parser.ts",
                "export function f(ch: number) { return ch === 0x7B/* { */ || ch === 0x28/* ( */; }\n",
            )
        )

        # 1. Op 0v: JS_NORMALIZED_KEY_PRESERVE_RAW_INPUT
        with self.subTest(case="op_0v_raw_loop_key_preserve"):
            with tempfile.TemporaryDirectory(prefix="brain_js_iter59_0v_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "lib/matcher.js": (
                            "function expand(v) {\n"
                            "  if (v === 'multi') return ['a/1', 'a/2'];\n"
                            "  if (v === 'json') return 'application/json';\n"
                            "  return v;\n"
                            "}\n"
                            "function mk(pat) { return (x) => x === pat; }\n"
                            "class Matcher {\n"
                            "  constructor(inputs) {\n"
                            "    this.patterns = [];\n"
                            "    for (const t of inputs) {\n"
                            "      const norm = expand(t);\n"
                            "      if (Array.isArray(norm)) {\n"
                            "        for (const t of norm) {\n"
                            "          this.patterns.push({\n"
                            "            key: t,\n"
                            "            match: mk(t),\n"
                            "          });\n"
                            "        }\n"
                            "      } else {\n"
                            "        this.patterns.push({\n"
                            "          key: norm,\n"
                            "          match: mk(norm),\n"
                            "        });\n"
                            "      }\n"
                            "    }\n"
                            "  }\n"
                            "  find(x) {\n"
                            "    for (const p of this.patterns) { if (p.match(x)) return p.key; }\n"
                            "    return undefined;\n"
                            "  }\n"
                            "}\n"
                            "module.exports = { Matcher };\n"
                        ),
                        "test/matcher.test.js": (
                            "const test = require('node:test');\n"
                            "const assert = require('node:assert/strict');\n"
                            "const { Matcher } = require('../lib/matcher.js');\n"
                            "test('returns original user input string on scalar and array expansions', () => {\n"
                            "  const m = new Matcher(['json', 'multi']);\n"
                            "  assert.equal(m.find('application/json'), 'json');\n"
                            "  assert.equal(m.find('a/2'), 'multi');\n"
                            "});\n"
                        ),
                    },
                )
                res = ML_SWE.solve_js_repository(root, ["test/matcher.test.js"], timeout_s=20.0)
                self.assertTrue(res["verified"], res)
                self.assertEqual(res["winner"]["tier"], "JS_NORMALIZED_KEY_PRESERVE_RAW_INPUT")
                self.assertEqual(res["model_calls"], 0)
                self.assertEqual(res["parameters_stored"], 0)

        # 2. Op 0w: JS_GUARD_CONJUNCT_DROP_ON_REJECT
        with self.subTest(case="op_0w_reject_guard_drop"):
            with tempfile.TemporaryDirectory(prefix="brain_js_iter59_0w_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "lib/scalar.js": (
                            "function isFlowIndicator(ch) { return ch === 0x2C || ch === 0x5B || ch === 0x5D; }\n"
                            "function canStartScalar(ch, inFlow) {\n"
                            "  if (ch === 0 ||\n"
                            "      ch === 0x23 ||\n"
                            "      (inFlow && isFlowIndicator(ch))) {\n"
                            "    return false;\n"
                            "  }\n"
                            "  return true;\n"
                            "}\n"
                            "function parseScalar(str, inFlow) {\n"
                            "  if (!canStartScalar(str.charCodeAt(0), inFlow)) {\n"
                            "    throw new SyntaxError('invalid scalar start');\n"
                            "  }\n"
                            "  return str;\n"
                            "}\n"
                            "module.exports = { parseScalar };\n"
                        ),
                        "test/scalar.test.js": (
                            "const test = require('node:test');\n"
                            "const assert = require('node:assert/strict');\n"
                            "const { parseScalar } = require('../lib/scalar.js');\n"
                            "test('forbid flow indicators at start of block plain scalars', () => {\n"
                            "  assert.equal(parseScalar('hello', false), 'hello');\n"
                            "  assert.throws(() => parseScalar(',bad', false), SyntaxError);\n"
                            "  assert.throws(() => parseScalar(']bad', false), SyntaxError);\n"
                            "});\n"
                        ),
                    },
                )
                res = ML_SWE.solve_js_repository(root, ["test/scalar.test.js"], timeout_s=20.0)
                self.assertTrue(res["verified"], res)
                self.assertEqual(res["winner"]["tier"], "JS_GUARD_CONJUNCT_DROP_ON_REJECT")
                self.assertEqual(res["model_calls"], 0)
                self.assertEqual(res["parameters_stored"], 0)

    def test_24_iter60_c_unchecked_alloc_null_and_zero_consume_while_reject(self) -> None:
        """Iter 60 C laws (`model_calls == 0`, `parameters_stored == 0`):
        1. Pass 0z (`C_UNCHECKED_ALLOC_NULL_GUARD`, CWE-476): inserts NULL check after
           `malloc` / custom allocator assignment before dereference or pointer arithmetic.
        2. Pass 0aa (`C_ZERO_CONSUME_WHILE_REJECT`): rejects 0-length token when a cursor
           `while` loop consumes 0 bytes (`offset == state->offset`).
        """
        # 1. CWE-476: C_UNCHECKED_ALLOC_NULL_GUARD
        with self.subTest(case="c_unchecked_alloc_null_guard"):
            with tempfile.TemporaryDirectory(prefix="brain_c_iter60_alloc_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "buf.h": (
                            "#include <stdlib.h>\n"
                            "#include <string.h>\n"
                            "static void copy_into(char *dst, const char *src, size_t n) {\n"
                            "  memcpy(dst, src, n);\n"
                            "}\n"
                            "static char *dup_ex(const char *src, void *(*alloc_fn)(void *, size_t), void *ud) {\n"
                            "  void *allocation;\n"
                            "  size_t n;\n"
                            "  if (NULL == src) { return NULL; }\n"
                            "  n = strlen(src) + 1;\n"
                            "  if (NULL == alloc_fn) {\n"
                            "    allocation = malloc(n);\n"
                            "  } else {\n"
                            "    allocation = alloc_fn(ud, n);\n"
                            "  }\n"
                            "  copy_into((char *)allocation, src, n);\n"
                            "  return (char *)allocation;\n"
                            "}\n"
                        ),
                        "test_buf.c": (
                            "#include <assert.h>\n"
                            "#include <string.h>\n"
                            "#include \"buf.h\"\n"
                            "static void *fail_alloc(void *ud, size_t sz) { (void)ud; (void)sz; return NULL; }\n"
                            "int main(void) {\n"
                            "  char *ok = dup_ex(\"hi\", NULL, NULL);\n"
                            "  assert(ok != NULL && strcmp(ok, \"hi\") == 0);\n"
                            "  free(ok);\n"
                            "  assert(dup_ex(\"hi\", fail_alloc, NULL) == NULL);\n"
                            "  return 0;\n"
                            "}\n"
                        ),
                    },
                )
                res = ML_SWE.solve_c_repository(root, ["test_buf.c"], timeout_s=20.0)
                self.assertTrue(res["verified"], res)
                self.assertEqual(res["winner"]["tier"], "C_UNCHECKED_ALLOC_NULL_GUARD")
                self.assertEqual(res["model_calls"], 0)
                self.assertEqual(res["parameters_stored"], 0)

        # 2. C_ZERO_CONSUME_WHILE_REJECT
        with self.subTest(case="c_zero_consume_while_reject"):
            with tempfile.TemporaryDirectory(prefix="brain_c_iter60_zcon_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "tok.h": (
                            "#include <stddef.h>\n"
                            "typedef struct { const char *src; size_t size; size_t offset; } ParseState;\n"
                            "static int is_key_ch(char c) { return (c >= 'a' && c <= 'z') || c == '_'; }\n"
                            "static int scan_unquoted_key(ParseState *state) {\n"
                            "  size_t offset = state->offset;\n"
                            "  const size_t size = state->size;\n"
                            "  const char *src = state->src;\n"
                            "  while ((offset < size) && is_key_ch(src[offset])) {\n"
                            "    offset++;\n"
                            "  }\n"
                            "  state->offset = offset;\n"
                            "  return 0;\n"
                            "}\n"
                        ),
                        "test_tok.c": (
                            "#include <assert.h>\n"
                            "#include <stdio.h>\n"
                            "#include \"tok.h\"\n"
                            "int main(void) {\n"
                            "  ParseState s1 = {\"foo:1\", 5, 0};\n"
                            "  assert(scan_unquoted_key(&s1) == 0 && s1.offset == 3);\n"
                            "  ParseState s2 = {\":1\", 2, 0};\n"
                            "  if (scan_unquoted_key(&s2) == 0) {\n"
                            "    fprintf(stderr, \"empty_key_fails: expected rejection\\n\");\n"
                            "    return 1;\n"
                            "  }\n"
                            "  return 0;\n"
                            "}\n"
                        ),
                    },
                )
                res = ML_SWE.solve_c_repository(root, ["test_tok.c"], timeout_s=20.0)
                self.assertTrue(res["verified"], res)
                self.assertEqual(res["winner"]["tier"], "C_ZERO_CONSUME_WHILE_REJECT")
                self.assertEqual(res["model_calls"], 0)
                self.assertEqual(res["parameters_stored"], 0)

    def test_25_iter61_js_detached_this_and_regex_case_insensitive(self) -> None:
        """Iter 61 JS laws (`model_calls == 0`, `parameters_stored == 0`):
        1. Op 0x (`JS_DETACHED_THIS_TO_DEFINED_RECEIVER`): binds `this(` -> `target(`
           inside `Object.defineProperties(target, { ... })` so detached methods work.
        2. Op 0y (`JS_REGEX_CASE_INSENSITIVE_FLAG`): adds `/i` to regex literals when
           case-variation tests fail against case-sensitive patterns.
        """
        # 1. JS_DETACHED_THIS_TO_DEFINED_RECEIVER
        with self.subTest(case="js_detached_this_to_defined_receiver"):
            with tempfile.TemporaryDirectory(prefix="brain_js_iter61_this_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "lib.js": (
                            "function makeRunner() {\n"
                            "  const runner = (fn, x) => fn(x);\n"
                            "  Object.defineProperties(runner, {\n"
                            "    mapAll: {\n"
                            "      value(items, fn) {\n"
                            "        return items.map((x) => this(fn, x));\n"
                            "      },\n"
                            "    },\n"
                            "  });\n"
                            "  return runner;\n"
                            "}\n"
                            "module.exports = { makeRunner };\n"
                        ),
                        "test_lib.js": (
                            "const test = require('node:test');\n"
                            "const assert = require('node:assert/strict');\n"
                            "const { makeRunner } = require('./lib.js');\n"
                            "test('detached mapAll works', () => {\n"
                            "  const r = makeRunner();\n"
                            "  assert.deepStrictEqual(r.mapAll([1, 2], x => x * 2), [2, 4]);\n"
                            "  const { mapAll } = r;\n"
                            "  assert.deepStrictEqual(mapAll([3, 4], x => x + 1), [4, 5]);\n"
                            "});\n"
                        ),
                    },
                )
                res = ML_SWE.solve_js_repository(root, ["test_lib.js"], timeout_s=20.0)
                self.assertTrue(res["verified"], res)
                self.assertEqual(res["winner"]["tier"], "JS_DETACHED_THIS_TO_DEFINED_RECEIVER")
                self.assertEqual(res["model_calls"], 0)
                self.assertEqual(res["parameters_stored"], 0)

        # 2. JS_REGEX_CASE_INSENSITIVE_FLAG
        with self.subTest(case="js_regex_case_insensitive_flag"):
            with tempfile.TemporaryDirectory(prefix="brain_js_iter61_rx_i_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "cache.js": (
                            "const noTransformRegExp = /(?:^|,)\\s*no-transform\\s*(?:,|$)/;\n"
                            "function shouldCompress(header) {\n"
                            "  if (!header) return true;\n"
                            "  return !noTransformRegExp.test(header);\n"
                            "}\n"
                            "module.exports = { shouldCompress };\n"
                        ),
                        "test_cache.js": (
                            "const test = require('node:test');\n"
                            "const assert = require('node:assert/strict');\n"
                            "const { shouldCompress } = require('./cache.js');\n"
                            "test('no-transform directive is case-insensitive', () => {\n"
                            "  assert.strictEqual(shouldCompress('public, no-transform'), false);\n"
                            "  assert.strictEqual(shouldCompress('public, NO-TRANSFORM'), false);\n"
                            "  assert.strictEqual(shouldCompress('public, max-age=60'), true);\n"
                            "});\n"
                        ),
                    },
                )
                res = ML_SWE.solve_js_repository(root, ["test_cache.js"], timeout_s=20.0)
                self.assertTrue(res["verified"], res)
                self.assertEqual(res["winner"]["tier"], "JS_REGEX_CASE_INSENSITIVE_FLAG")
                self.assertEqual(res["model_calls"], 0)
                self.assertEqual(res["parameters_stored"], 0)

    def test_26_iter62_js_sort_guard_spread_undef_and_nullish_bool(self) -> None:
        """Iter 62 ECMA-262 laws (`model_calls == 0`, `parameters_stored == 0`):
        1. Op 0z (`JS_SORT_COMPARATOR_TYPEOF_FUNCTION_GUARD`): guards `.toSorted(cmp)` / `.sort(cmp)`
           when a non-function, non-undefined comparator throws TypeError.
        2. Op 0aa (`JS_OBJECT_SPREAD_STRIP_UNDEFINED_OPTIONS`): strips explicit `undefined`
           properties in `{ default: val, ...options }` so defaults are preserved.
        3. Op 0ab (`JS_NULLISH_BOOL_DEFAULT_STRICT_UNDEFINED`): replaces `expr ?? true` with
           strict-undefined boolean defaulting so `null` does not silently default to `true`.
        """
        # 1. JS_SORT_COMPARATOR_TYPEOF_FUNCTION_GUARD
        with self.subTest(case="js_sort_comparator_typeof_function_guard"):
            with tempfile.TemporaryDirectory(prefix="brain_js_iter62_sort_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "sorter.js": (
                            "function sortKeys(keys, options = {}) {\n"
                            "  if (options.sort === false) return keys;\n"
                            "  return options.sort === true ? keys.toSorted() : keys.toSorted(options.sort);\n"
                            "}\n"
                            "module.exports = { sortKeys };\n"
                        ),
                        "test_sorter.js": (
                            "const test = require('node:test');\n"
                            "const assert = require('node:assert/strict');\n"
                            "const { sortKeys } = require('./sorter.js');\n"
                            "test('non-function non-boolean sort falls back to default sort', () => {\n"
                            "  assert.deepStrictEqual(sortKeys(['b', 'a'], { sort: null }), ['a', 'b']);\n"
                            "  assert.deepStrictEqual(sortKeys(['b', 'a'], { sort: (a, b) => b.localeCompare(a) }), ['b', 'a']);\n"
                            "  assert.deepStrictEqual(sortKeys(['b', 'a'], { sort: false }), ['b', 'a']);\n"
                            "});\n"
                        ),
                    },
                )
                res = ML_SWE.solve_js_repository(root, ["test_sorter.js"], timeout_s=20.0)
                self.assertTrue(res["verified"], res)
                self.assertEqual(res["winner"]["tier"], "JS_SORT_COMPARATOR_TYPEOF_FUNCTION_GUARD")
                self.assertEqual(res["model_calls"], 0)
                self.assertEqual(res["parameters_stored"], 0)

        # 2. JS_OBJECT_SPREAD_STRIP_UNDEFINED_OPTIONS
        with self.subTest(case="js_object_spread_strip_undefined_options"):
            with tempfile.TemporaryDirectory(prefix="brain_js_iter62_spread_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "fmt.js": (
                            "function formatText(text, options) {\n"
                            "  options = {\n"
                            "    sep: '-',\n"
                            "    replacements: [],\n"
                            "    ...options,\n"
                            "  };\n"
                            "  for (const [k, v] of options.replacements) {\n"
                            "    text = text.replaceAll(k, v);\n"
                            "  }\n"
                            "  return text.split(' ').join(options.sep);\n"
                            "}\n"
                            "module.exports = { formatText };\n"
                        ),
                        "test_fmt.js": (
                            "const test = require('node:test');\n"
                            "const assert = require('node:assert/strict');\n"
                            "const { formatText } = require('./fmt.js');\n"
                            "test('undefined options preserve defaults', () => {\n"
                            "  assert.strictEqual(formatText('a b', { sep: undefined, replacements: undefined }), 'a-b');\n"
                            "  assert.strictEqual(formatText('a b', { sep: '_' }), 'a_b');\n"
                            "});\n"
                        ),
                    },
                )
                res = ML_SWE.solve_js_repository(root, ["test_fmt.js"], timeout_s=20.0)
                self.assertTrue(res["verified"], res)
                self.assertEqual(res["winner"]["tier"], "JS_OBJECT_SPREAD_STRIP_UNDEFINED_OPTIONS")
                self.assertEqual(res["model_calls"], 0)
                self.assertEqual(res["parameters_stored"], 0)

        # 3. JS_NULLISH_BOOL_DEFAULT_STRICT_UNDEFINED
        with self.subTest(case="js_nullish_bool_default_strict_undefined"):
            with tempfile.TemporaryDirectory(prefix="brain_js_iter62_nullish_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "codec.js": (
                            "function roundTrip(raw, options = {}) {\n"
                            "  const shouldDecode = options.encode ?? true;\n"
                            "  const mid = shouldDecode ? decodeURIComponent(raw) : raw;\n"
                            "  return options.encode === undefined || options.encode ? encodeURIComponent(mid) : mid;\n"
                            "}\n"
                            "module.exports = { roundTrip };\n"
                        ),
                        "test_codec.js": (
                            "const test = require('node:test');\n"
                            "const assert = require('node:assert/strict');\n"
                            "const { roundTrip } = require('./codec.js');\n"
                            "test('encode: null disables both decode and re-encode', () => {\n"
                            "  assert.strictEqual(roundTrip('x%26y', {}), 'x%26y');\n"
                            "  assert.strictEqual(roundTrip('x%26y', { encode: false }), 'x%26y');\n"
                            "  assert.strictEqual(roundTrip('x%26y', { encode: null }), 'x%26y');\n"
                            "});\n"
                        ),
                    },
                )
                res = ML_SWE.solve_js_repository(root, ["test_codec.js"], timeout_s=20.0)
                self.assertTrue(res["verified"], res)
                self.assertEqual(res["winner"]["tier"], "JS_NULLISH_BOOL_DEFAULT_STRICT_UNDEFINED")
                self.assertEqual(res["model_calls"], 0)
                self.assertEqual(res["parameters_stored"], 0)

    def test_27_iter63_js_hex_regex_i_nonzero_limit_and_ternary_drop(self) -> None:
        """Iter 63 JS laws: Op 0y hex-escape `/i`, Op 0ac nonzero lower bound, Op 0ad ternary drop."""
        # 1. Op 0y: single-letter hex escape `/%2E/g` -> `/%2E/gi`
        with self.subTest(case="js_hex_escape_regex_i"):
            with tempfile.TemporaryDirectory(prefix="brain_js_iter63_hex_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "dec.js": (
                            "function decodeKey(k, decodeDot) {\n"
                            "  return decodeDot ? k.replace(/%2E/g, '.') : k;\n"
                            "}\n"
                            "module.exports = { decodeKey };\n"
                        ),
                        "test_dec.js": (
                            "const test = require('node:test');\n"
                            "const assert = require('node:assert/strict');\n"
                            "const { decodeKey } = require('./dec.js');\n"
                            "test('decodes lowercase %2e dots case-insensitively', () => {\n"
                            "  assert.strictEqual(decodeKey('a%2Eb', true), 'a.b');\n"
                            "  assert.strictEqual(decodeKey('a%2eb', true), 'a.b');\n"
                            "});\n"
                        ),
                    },
                )
                res = ML_SWE.solve_js_repository(root, ["test_dec.js"], timeout_s=20.0)
                self.assertTrue(res["verified"], res)
                self.assertEqual(res["winner"]["tier"], "JS_REGEX_CASE_INSENSITIVE_FLAG")
                self.assertEqual(res["model_calls"], 0)

        # 2. Op 0ac: `count >= limit` throw guard must allow `count === 0` when `limit === 0`
        with self.subTest(case="js_throw_limit_nonzero_lower_bound"):
            with tempfile.TemporaryDirectory(prefix="brain_js_iter63_lim_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "arr.js": (
                            "function checkScalar(val, opts, currentLen) {\n"
                            "  if (opts.throwOnLimit && currentLen >= opts.arrayLimit) {\n"
                            "    throw new RangeError('Array limit exceeded');\n"
                            "  }\n"
                            "  return val;\n"
                            "}\n"
                            "module.exports = { checkScalar };\n"
                        ),
                        "test_arr.js": (
                            "const test = require('node:test');\n"
                            "const assert = require('node:assert/strict');\n"
                            "const { checkScalar } = require('./arr.js');\n"
                            "test('zero arrayLimit allows scalar at currentLen 0', () => {\n"
                            "  assert.strictEqual(checkScalar('ok', { throwOnLimit: true, arrayLimit: 0 }, 0), 'ok');\n"
                            "  assert.throws(() => checkScalar('x', { throwOnLimit: true, arrayLimit: 1 }, 1), RangeError);\n"
                            "});\n"
                        ),
                    },
                )
                res = ML_SWE.solve_js_repository(root, ["test_arr.js"], timeout_s=20.0)
                self.assertTrue(res["verified"], res)
                self.assertEqual(res["winner"]["tier"], "JS_THROW_LIMIT_NONZERO_LOWER_BOUND")
                self.assertEqual(res["model_calls"], 0)

        # 3. Op 0ad: conditional double-transform ternary simplification
        with self.subTest(case="js_ternary_fallback_branch_simplify"):
            with tempfile.TemporaryDirectory(prefix="brain_js_iter63_tern_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "enc.js": (
                            "function formatPrefix(prefix, encodeDotInKeys) {\n"
                            "  var encodedPrefix = encodeDotInKeys ? String(prefix).replace(/\\./g, '%2E') : String(prefix);\n"
                            "  return encodedPrefix + '.leaf';\n"
                            "}\n"
                            "module.exports = { formatPrefix };\n"
                        ),
                        "test_enc.js": (
                            "const test = require('node:test');\n"
                            "const assert = require('node:assert/strict');\n"
                            "const { formatPrefix } = require('./enc.js');\n"
                            "test('encodeDotInKeys does not re-encode structural separator dots', () => {\n"
                            "  assert.strictEqual(formatPrefix('a.b', true), 'a.b.leaf');\n"
                            "  assert.strictEqual(formatPrefix('a.b', false), 'a.b.leaf');\n"
                            "});\n"
                        ),
                    },
                )
                res = ML_SWE.solve_js_repository(root, ["test_enc.js"], timeout_s=20.0)
                self.assertTrue(res["verified"], res)
                self.assertEqual(res["winner"]["tier"], "JS_TERNARY_FALLBACK_BRANCH_SIMPLIFY")
                self.assertEqual(res["model_calls"], 0)

    def test_28_iter64_js_early_return_sibling_wrapper_and_proto_safe_define_property(self) -> None:
        """Iter 64 universal JS SWE laws:
        1. Op 0ae (`JS_EARLY_RETURN_SIBLING_WRAPPER_CONSISTENCY`): wrap raw variable in early
           return with the exact encoder/formatter pipeline used by sibling returns in the same function.
        2. Op 0af (`JS_PROTO_SAFE_DEFINE_PROPERTY`, ECMA-262 §10.1.9 / CWE-1321): replace
           `obj[key] = val` with `__proto__`-guarded `Object.defineProperty(...)` across coupled writes.
        """
        # 1. Op 0ae: early return missing sibling formatter/encoder pipeline
        with self.subTest(case="js_early_return_sibling_wrapper_consistency"):
            with tempfile.TemporaryDirectory(prefix="brain_js_iter64_0ae_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "fmt.js": (
                            "function serialize(val, key, encoder, formatter, encodeValuesOnly) {\n"
                            "  if (typeof val === 'string') {\n"
                            "    return formatter(encoder && !encodeValuesOnly ? encoder(key) : key) + '=' + formatter(val);\n"
                            "  }\n"
                            "  if (Array.isArray(val) && val.length === 0) {\n"
                            "    return key + '[]';\n"
                            "  }\n"
                            "  return '';\n"
                            "}\n"
                            "module.exports = { serialize };\n"
                        ),
                        "test_fmt.js": (
                            "const test = require('node:test');\n"
                            "const assert = require('node:assert/strict');\n"
                            "const { serialize } = require('./fmt.js');\n"
                            "test('empty array early return encodes and formats key', () => {\n"
                            "  const enc = s => s.replace(/\\s/g, '%20');\n"
                            "  const fmt = s => s.toUpperCase();\n"
                            "  assert.strictEqual(serialize([], 'my key', enc, fmt, false), 'MY%20KEY[]');\n"
                            "  assert.strictEqual(serialize([], 'my key', enc, fmt, true), 'MY KEY[]');\n"
                            "  assert.strictEqual(serialize('v', 'my key', enc, fmt, false), 'MY%20KEY=V');\n"
                            "});\n"
                        ),
                    },
                )
                res = ML_SWE.solve_js_repository(root, ["test_fmt.js"], timeout_s=20.0)
                self.assertTrue(res["verified"], res)
                self.assertEqual(res["winner"]["tier"], "JS_EARLY_RETURN_SIBLING_WRAPPER_CONSISTENCY")
                self.assertEqual(res["model_calls"], 0)

        # 2. Op 0af: ECMA-262 __proto__ own data-property preservation
        with self.subTest(case="js_proto_safe_define_property"):
            with tempfile.TemporaryDirectory(prefix="brain_js_iter64_0af_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "clone.js": (
                            "function cloneRecord(src) {\n"
                            "  var target = {};\n"
                            "  var keys = Object.keys(src);\n"
                            "  for (var j = 0; j < keys.length; j += 1) {\n"
                            "    var val = src[keys[j]];\n"
                            "    if (val && typeof val === 'object') {\n"
                            "      target[keys[j]] = cloneRecord(val);\n"
                            "    } else {\n"
                            "      target[keys[j]] = val;\n"
                            "    }\n"
                            "  }\n"
                            "  return target;\n"
                            "}\n"
                            "module.exports = { cloneRecord };\n"
                        ),
                        "test_clone.js": (
                            "const test = require('node:test');\n"
                            "const assert = require('node:assert/strict');\n"
                            "const { cloneRecord } = require('./clone.js');\n"
                            "test('__proto__ key does not mutate prototype of clone', () => {\n"
                            "  const src = JSON.parse('{\"__proto__\":{\"polluted\":true},\"ok\":1}');\n"
                            "  const out = cloneRecord(src);\n"
                            "  assert.strictEqual(out.polluted, undefined);\n"
                            "  assert.strictEqual(Object.getPrototypeOf(out), Object.prototype);\n"
                            "  assert.strictEqual(Object.prototype.hasOwnProperty.call(out, '__proto__'), true);\n"
                            "  assert.strictEqual(out.ok, 1);\n"
                            "});\n"
                        ),
                    },
                )
                res = ML_SWE.solve_js_repository(root, ["test_clone.js"], timeout_s=20.0)
                self.assertTrue(res["verified"], res)
                self.assertEqual(res["winner"]["tier"], "JS_PROTO_SAFE_DEFINE_PROPERTY")
                self.assertEqual(res["model_calls"], 0)

    def test_iter69_ts_nonempty_accum_lookahead_and_trailing_delim_ops(self) -> None:
        """Iter 69 JS/TS Ops 0s (msg align), 0ag (`JS_EMPTY_ACCUMULATOR_THROW_GUARD`),
        0ah (`JS_SKIP_EMPTY_TEXT_LOOKAHEAD`), and 0ai (`JS_TRAILING_DELIM_NEGATIVE_LOOKBEHIND`).
        """
        # 1. Op 0s (non-empty string + throw message alignment)
        with self.subTest(case="op_0s_nonempty_string_msg_align"):
            with tempfile.TemporaryDirectory(prefix="iter69_0s_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "param.js": (
                            "function fmtParam(name, value) {\n"
                            "  if (typeof value !== 'string') {\n"
                            "    throw new TypeError(`Expected \"${name}\" to be a string`);\n"
                            "  }\n"
                            "  return '/' + value;\n"
                            "}\n"
                            "module.exports = { fmtParam };\n"
                        ),
                        "test_param.js": (
                            "const test = require('node:test');\n"
                            "const assert = require('node:assert/strict');\n"
                            "const { fmtParam } = require('./param.js');\n"
                            "test('rejects empty string and non-string with aligned message', () => {\n"
                            "  assert.strictEqual(fmtParam('id', 'abc'), '/abc');\n"
                            "  assert.throws(() => fmtParam('id', ''), { name: 'TypeError', message: 'Expected \"id\" to be a non-empty string' });\n"
                            "  assert.throws(() => fmtParam('id', 123), { name: 'TypeError', message: 'Expected \"id\" to be a non-empty string' });\n"
                            "});\n"
                        ),
                    },
                )
                r1 = ML_SWE.solve_js_repository(root, ["test_param.js"], timeout_s=20.0)
                self.assertTrue(r1["verified"], r1)
                self.assertEqual(r1["winner"]["tier"], "JS_TYPEOF_STRING_NONEMPTY_GUARD")
                self.assertEqual(r1["model_calls"], 0)

        # 2. Op 0ag (empty accumulator throw guard)
        with self.subTest(case="op_0ag_empty_accum_throw"):
            with tempfile.TemporaryDirectory(prefix="iter69_0ag_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "wild.js": (
                            "function fmtWild(name, value) {\n"
                            "  if (!Array.isArray(value) || value.length === 0) {\n"
                            "    throw new TypeError(`Expected \"${name}\" to be a non-empty array`);\n"
                            "  }\n"
                            "  let result = '';\n"
                            "  for (let i = 0; i < value.length; i++) {\n"
                            "    if (i > 0) result += '/';\n"
                            "    result += value[i];\n"
                            "  }\n"
                            "  return result;\n"
                            "}\n"
                            "module.exports = { fmtWild };\n"
                        ),
                        "test_wild.js": (
                            "const test = require('node:test');\n"
                            "const assert = require('node:assert/strict');\n"
                            "const { fmtWild } = require('./wild.js');\n"
                            "test('rejects wildcard array yielding empty path', () => {\n"
                            "  assert.strictEqual(fmtWild('w', ['a', 'b']), 'a/b');\n"
                            "  assert.throws(() => fmtWild('w', ['']), TypeError);\n"
                            "});\n"
                        ),
                    },
                )
                r2 = ML_SWE.solve_js_repository(root, ["test_wild.js"], timeout_s=20.0)
                self.assertTrue(r2["verified"], r2)
                self.assertEqual(r2["winner"]["tier"], "JS_EMPTY_ACCUMULATOR_THROW_GUARD")
                self.assertEqual(r2["model_calls"], 0)

        # 3. Op 0ah (skip empty text lookahead)
        with self.subTest(case="op_0ah_skip_empty_text_lookahead"):
            with tempfile.TemporaryDirectory(prefix="iter69_0ah_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "tok.js": (
                            "function stringifyName(name, next) {\n"
                            "  if (next && next.type === 'text' && /^[a-z]/.test(next.value)) return '\"' + name + '\"';\n"
                            "  return name;\n"
                            "}\n"
                            "function stringifyTokens(tokens, index) {\n"
                            "  let out = '';\n"
                            "  while (index < tokens.length) {\n"
                            "    const tok = tokens[index++];\n"
                            "    if (tok.type === 'text') { out += tok.value; continue; }\n"
                            "    if (tok.type === 'param') { out += ':' + stringifyName(tok.name, tokens[index]); continue; }\n"
                            "  }\n"
                            "  return out;\n"
                            "}\n"
                            "module.exports = { stringifyTokens };\n"
                        ),
                        "test_tok.js": (
                            "const test = require('node:test');\n"
                            "const assert = require('node:assert/strict');\n"
                            "const { stringifyTokens } = require('./tok.js');\n"
                            "test('skips empty text tokens on lookahead', () => {\n"
                            "  const res = stringifyTokens([{type:'text',value:'/'},{type:'param',name:'foo'},{type:'text',value:''},{type:'text',value:'bar'}], 0);\n"
                            "  assert.strictEqual(res, '/:\"foo\"bar');\n"
                            "  const res2 = stringifyTokens([{type:'text',value:'/'},{type:'param',name:'foo'},{type:'text',value:''},{type:'text',value:'/x'}], 0);\n"
                            "  assert.strictEqual(res2, '/:foo/x');\n"
                            "});\n"
                        ),
                    },
                )
                r3 = ML_SWE.solve_js_repository(root, ["test_tok.js"], timeout_s=20.0)
                self.assertTrue(r3["verified"], r3)
                self.assertEqual(r3["winner"]["tier"], "JS_SKIP_EMPTY_TEXT_LOOKAHEAD")
                self.assertEqual(r3["model_calls"], 0)

        # 4. Op 0ai (trailing delimiter negative lookbehind deduplication)
        with self.subTest(case="op_0ai_trailing_delim_lookbehind"):
            with tempfile.TemporaryDirectory(prefix="iter69_0ai_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "rx.js": (
                            "function esc(s) { return s.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&'); }\n"
                            "function makeRe(src, delim = '/', trailing = true) {\n"
                            "  let pattern = '^(?:' + src + ')';\n"
                            "  if (trailing) pattern += '(?:' + esc(delim) + '$)?';\n"
                            "  pattern += '$';\n"
                            "  return new RegExp(pattern);\n"
                            "}\n"
                            "module.exports = { makeRe };\n"
                        ),
                        "test_rx.js": (
                            "const test = require('node:test');\n"
                            "const assert = require('node:assert/strict');\n"
                            "const { makeRe } = require('./rx.js');\n"
                            "test('does not match duplicate trailing slash', () => {\n"
                            "  const r1 = makeRe('/test/');\n"
                            "  assert.strictEqual(r1.test('/test/'), true);\n"
                            "  assert.strictEqual(r1.test('/test//'), false);\n"
                            "  const r2 = makeRe('/test');\n"
                            "  assert.strictEqual(r2.test('/test/'), true);\n"
                            "});\n"
                        ),
                    },
                )
                r4 = ML_SWE.solve_js_repository(root, ["test_rx.js"], timeout_s=20.0)
                self.assertTrue(r4["verified"], r4)
                self.assertEqual(r4["winner"]["tier"], "JS_TRAILING_DELIM_NEGATIVE_LOOKBEHIND")
                self.assertEqual(r4["model_calls"], 0)

    def test_iter70_c_five_general_repair_laws(self) -> None:
        """Verify all 5 Iter-70 general C/C++17 repair laws end-to-end with GCC (`model_calls == 0`):
        1. `C_STDIO_FERROR_POST_CHECK` (`FILE*` delegating wrapper `ferror(fp) ? -3 : error`)
        2. `C_SIBLING_DUAL_CASE_FOLD_COMPARE` (sibling `lwr`+`upr` dual-fold sync)
        3. `C_ADJACENT_IF_BLOCK_PRECEDENCE_SWAP` (trivia skip before unquoted-key dispatch)
        4. `C_FASTPATH_GOTO_SLOWPATH_BAILOUT` (`skip_<tag>:` fast-path bailout to `copy_<tag>:`)
        5. `C_PREFIX_SUBTREE_MOVE_GUARD` (RFC 6902 proper-prefix self-ancestry move rejection)
        """
        # 1. C_STDIO_FERROR_POST_CHECK
        with self.subTest(law="C_STDIO_FERROR_POST_CHECK"):
            with tempfile.TemporaryDirectory(prefix="brain_c_iter70_ferr_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "reader.c": (
                            "#include <stdio.h>\n"
                            "int read_stream(void *stream) {\n"
                            "    FILE *f = (FILE *)stream;\n"
                            "    int c = fgetc(f);\n"
                            "    if (c == '!') return -1;\n"
                            "    if (c == '?') return -2;\n"
                            "    return 0;\n"
                            "}\n"
                            "int read_file(FILE* file)\n"
                            "{\n"
                            "    return read_stream(file);\n"
                            "}\n"
                        ),
                        "tests/test_ferr.c": (
                            "#include <assert.h>\n"
                            "#include <stdio.h>\n"
                            "int read_file(FILE* file);\n"
                            "int main(void) {\n"
                            "    FILE *f = tmpfile();\n"
                            "    assert(f != NULL);\n"
                            "    fputc('x', f); rewind(f);\n"
                            "    assert(read_file(f) == 0);\n"
                            "    fclose(f);\n"
                            "    FILE *wo = fopen(\"/dev/null\", \"w\");\n"
                            "    assert(wo != NULL);\n"
                            "    int e = read_file(wo);\n"
                            "    assert(ferror(wo) != 0);\n"
                            "    assert(e == -3);\n"
                            "    fclose(wo);\n"
                            "    return 0;\n"
                            "}\n"
                        ),
                    },
                )
                r1 = ML_SWE.solve_c_repository(root, ["tests/test_ferr.c"], timeout_s=30.0)
                self.assertEqual(r1["status"], "VERIFIED", r1)
                self.assertEqual(r1["winner"]["tier"], "C_STDIO_FERROR_POST_CHECK")
                self.assertEqual(r1["model_calls"], 0)

        # 2. C_SIBLING_DUAL_CASE_FOLD_COMPARE
        with self.subTest(law="C_SIBLING_DUAL_CASE_FOLD_COMPARE"):
            with tempfile.TemporaryDirectory(prefix="brain_c_iter70_fold_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "fold.h": (
                            "#pragma once\n"
                            "static inline int foldlwr(int c) { return (c == 0x03A3) ? 0x03C3 : c; }\n"
                            "static inline int foldupr(int c) { return (c == 0x03C2 || c == 0x03C3) ? 0x03A3 : c; }\n"
                            "static inline int foldcasecmp(int a, int b) {\n"
                            "    if ((foldlwr(a) != foldlwr(b)) && (foldupr(a) != foldupr(b))) return 1;\n"
                            "    return 0;\n"
                            "}\n"
                            "static inline int foldcasematch(int a, int b) {\n"
                            "    if (foldlwr(a) != foldlwr(b)) {\n"
                            "        return 0;\n"
                            "    }\n"
                            "    return 1;\n"
                            "}\n"
                        ),
                        "tests/test_fold.c": (
                            "#include <assert.h>\n"
                            "#include \"fold.h\"\n"
                            "int main(void) {\n"
                            "    assert(foldcasecmp(0x03A3, 0x03C2) == 0);\n"
                            "    assert(foldcasematch(0x03A3, 0x03C2) == 1);\n"
                            "    assert(foldcasematch(0x03A3, 'x') == 0);\n"
                            "    return 0;\n"
                            "}\n"
                        ),
                    },
                )
                r2 = ML_SWE.solve_c_repository(root, ["tests/test_fold.c"], timeout_s=30.0)
                self.assertEqual(r2["status"], "VERIFIED", r2)
                self.assertEqual(r2["winner"]["tier"], "C_SIBLING_DUAL_CASE_FOLD_COMPARE")
                self.assertEqual(r2["model_calls"], 0)

        # 3. C_ADJACENT_IF_BLOCK_PRECEDENCE_SWAP
        with self.subTest(law="C_ADJACENT_IF_BLOCK_PRECEDENCE_SWAP"):
            with tempfile.TemporaryDirectory(prefix="brain_c_iter70_swap_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "parser.c": (
                            "#include <stdbool.h>\n"
                            "static bool is_id_start(unsigned char c) { return c >= 0x80 || (c >= 'a' && c <= 'z'); }\n"
                            "static bool is_trivia(unsigned char c) { return c == 0xC2 || c == ' '; }\n"
                            "static bool skip_trivia(const unsigned char **p) {\n"
                            "    if (**p == 0xC2 && (*p)[1] == 0xA0) { *p += 2; return true; }\n"
                            "    if (**p == ' ') { *p += 1; return true; }\n"
                            "    return false;\n"
                            "}\n"
                            "int parse_key(const unsigned char *cur) {\n"
                            "obj_key_begin:\n"
                            "    if (*cur == '\"') return 1;\n"
                            "    if (is_id_start(*cur)) {\n"
                            "        if (*cur >= 'a' && *cur <= 'z') return 2;\n"
                            "        return -1;\n"
                            "    }\n"
                            "    if (is_trivia(*cur)) {\n"
                            "        if (skip_trivia(&cur)) goto obj_key_begin;\n"
                            "        return -2;\n"
                            "    }\n"
                            "    return -3;\n"
                            "}\n"
                        ),
                        "tests/test_parser.c": (
                            "#include <assert.h>\n"
                            "int parse_key(const unsigned char *cur);\n"
                            "int main(void) {\n"
                            "    const unsigned char s1[] = {0xC2, 0xA0, '\"', 'a', '\"', 0};\n"
                            "    const unsigned char s2[] = {'a', 0};\n"
                            "    assert(parse_key(s1) == 1);\n"
                            "    assert(parse_key(s2) == 2);\n"
                            "    return 0;\n"
                            "}\n"
                        ),
                    },
                )
                r3 = ML_SWE.solve_c_repository(root, ["tests/test_parser.c"], timeout_s=30.0)
                self.assertEqual(r3["status"], "VERIFIED", r3)
                self.assertEqual(r3["winner"]["tier"], "C_ADJACENT_IF_BLOCK_PRECEDENCE_SWAP")
                self.assertEqual(r3["model_calls"], 0)

        # 4. C_FASTPATH_GOTO_SLOWPATH_BAILOUT
        with self.subTest(law="C_FASTPATH_GOTO_SLOWPATH_BAILOUT"):
            with tempfile.TemporaryDirectory(prefix="brain_c_iter70_bail_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "scan.c": (
                            "#include <stddef.h>\n"
                            "int scan_str(const unsigned char *src, int allow_invalid, int *marked_noesc) {\n"
                            "    const unsigned char *dst = src;\n"
                            "    *marked_noesc = 1;\n"
                            "skip_utf8:\n"
                            "    if (*src == 0) return 0;\n"
                            "    if (*src >= 0x80) {\n"
                            "        if (allow_invalid) ++src;\n"
                            "        else return -1;\n"
                            "        goto skip_utf8;\n"
                            "    }\n"
                            "    dst = src;\n"
                            "copy_utf8:\n"
                            "    if (*src >= 0x80) {\n"
                            "        *marked_noesc = 0;\n"
                            "        ++src;\n"
                            "        (void)dst;\n"
                            "        return 0;\n"
                            "    }\n"
                            "    return 0;\n"
                            "}\n"
                        ),
                        "tests/test_scan.c": (
                            "#include <assert.h>\n"
                            "int scan_str(const unsigned char *src, int allow_invalid, int *marked_noesc);\n"
                            "int main(void) {\n"
                            "    const unsigned char bad[] = {0xFF, 0};\n"
                            "    int noesc = 1;\n"
                            "    assert(scan_str(bad, 0, &noesc) == -1);\n"
                            "    assert(scan_str(bad, 1, &noesc) == 0);\n"
                            "    assert(noesc == 0);\n"
                            "    return 0;\n"
                            "}\n"
                        ),
                    },
                )
                r4 = ML_SWE.solve_c_repository(root, ["tests/test_scan.c"], timeout_s=30.0)
                self.assertEqual(r4["status"], "VERIFIED", r4)
                self.assertEqual(r4["winner"]["tier"], "C_FASTPATH_GOTO_SLOWPATH_BAILOUT")
                self.assertEqual(r4["model_calls"], 0)

        # 5. C_PREFIX_SUBTREE_MOVE_GUARD
        with self.subTest(law="C_PREFIX_SUBTREE_MOVE_GUARD"):
            with tempfile.TemporaryDirectory(prefix="brain_c_iter70_move_") as td:
                root = pathlib.Path(td)
                _write_files(
                    root,
                    {
                        "patch.c": (
                            "#include <string.h>\n"
                            "enum { PATCH_OP_MOVE = 1 };\n"
                            "static void *ptr_remove(const char *from) { return (void *)from; }\n"
                            "void *apply_move(int op, const char *from, const char *path) {\n"
                            "    size_t from_len = strlen(from);\n"
                            "    size_t path_len = strlen(path);\n"
                            "    void *val = NULL;\n"
                            "    switch (op) {\n"
                            "        case PATCH_OP_MOVE:\n"
                            "            if (from_len == 0 && path_len == 0) break;\n"
                            "            val = ptr_remove(from);\n"
                            "            return val;\n"
                            "    }\n"
                            "    return (void *)path;\n"
                            "}\n"
                        ),
                        "tests/test_patch.c": (
                            "#include <assert.h>\n"
                            "#include <stddef.h>\n"
                            "void *apply_move(int op, const char *from, const char *path);\n"
                            "int main(void) {\n"
                            "    assert(apply_move(1, \"/0\", \"/0/b\") == NULL);\n"
                            "    assert(apply_move(1, \"/a\", \"/ab\") != NULL);\n"
                            "    return 0;\n"
                            "}\n"
                        ),
                    },
                )
                r5 = ML_SWE.solve_c_repository(root, ["tests/test_patch.c"], timeout_s=30.0)
                self.assertEqual(r5["status"], "VERIFIED", r5)
                self.assertEqual(r5["winner"]["tier"], "C_PREFIX_SUBTREE_MOVE_GUARD")
                self.assertEqual(r5["model_calls"], 0)


if __name__ == "__main__":
    unittest.main()
