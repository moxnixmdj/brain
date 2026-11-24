"""Tests for `canonical/runtime/epistemic_issue_reproducer_v1.py` and Iter 65 upgrades.

Proves zero-LLM (`model_calls == 0`, `parameters_stored == 0`) blind issue-to-reproducer
synthesis, F->P epistemic qualification, anti-overfit pass2pass verification, ONE Front Door
integration (`UnifiedModel.open_model().solve(...)`), and environment-scan memory-diff
acquisition for unseen `./bin/*` CLI tools.
"""
from __future__ import annotations

import os
import pathlib
import stat
import sys
import tempfile
import unittest

from canonical.runtime import brain_unified_model_v1 as UM
from canonical.runtime import epistemic_doc_compiler_agent_v1 as DCA
from canonical.runtime import epistemic_issue_reproducer_v1 as IR


def _write_files(root: pathlib.Path, files: dict[str, str]) -> None:
    for rel, content in files.items():
        fp = root / rel
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content, encoding="utf-8")


class TestEpistemicIssueReproducerV1(unittest.TestCase):
    def test_01_blind_python_prose_only_issue_and_hidden_gold_eval(self) -> None:
        """Zero hidden tests given: repo's existing tests all PASS on c_old; issue is prose-only."""
        with tempfile.TemporaryDirectory(prefix="ir_py_prose_") as td:
            root = pathlib.Path(td)
            _write_files(
                root,
                {
                    "pyproject.toml": "[project]\nname = 'tagger'\nversion = '0.1.0'\n",
                    "src/tagger/__init__.py": (
                        "import re\n\n"
                        "class InvalidTag(ValueError):\n"
                        "    pass\n\n"
                        "def canonicalize_tag(raw: str) -> str:\n"
                        "    low = raw.lower()\n"
                        "    if not re.fullmatch(r'[a-z0-9\\-]+', low):\n"
                        "        raise InvalidTag(f'bad tag: {raw}')\n"
                        "    return low\n"
                    ),
                    "tests/test_tagger.py": (
                        "import pytest\n"
                        "from tagger import InvalidTag, canonicalize_tag\n\n"
                        "def test_existing_valid_and_ascii_invalid():\n"
                        "    assert canonicalize_tag('Alpha-1') == 'alpha-1'\n"
                        "    with pytest.raises(InvalidTag):\n"
                        "        canonicalize_tag('bad!tag')\n"
                    ),
                },
            )
            issue = (
                'Calling `canonicalize_tag("Tag-\\u212austom")` fails to raise `InvalidTag` '
                "because the Kelvin sign lowercases to ASCII k.\n"
                "Valid tags like `canonicalize_tag('Custom-2')` should return `'custom-2'`."
            )
            res = IR.solve_issue_from_description(root, issue, python_exe=sys.executable, timeout_s=30.0)
            self.assertTrue(res["verified"], res)
            self.assertEqual(res["model_calls"], 0)
            self.assertEqual(res["parameters_stored"], 0)
            self.assertEqual(res["winner"]["tier"], "TIER3_NON_ASCII_VALIDATION_GUARD")
            self.assertIn("isascii()", res["patch_diff"])
            self.assertEqual(res["regression_tests"], ["tests/test_tagger.py"])
            # Original repo must remain untouched
            self.assertNotIn("isascii", (root / "src/tagger/__init__.py").read_text(encoding="utf-8"))

    def test_02_blind_js_fenced_and_prose_issues_with_pass2pass_regression(self) -> None:
        """Blind JS resolution for BOTH fenced (Op 0ae) and CWE-1321 __proto__ (Op 0af) issues."""
        # Case A: Fenced issue -> Op 0ae (JS_EARLY_RETURN_SIBLING_WRAPPER_CONSISTENCY)
        with tempfile.TemporaryDirectory(prefix="ir_js_0ae_") as td:
            root = pathlib.Path(td)
            _write_files(
                root,
                {
                    "package.json": '{"name": "miniqs", "main": "lib/index.js"}\n',
                    "lib/index.js": (
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
                    "test/basic.js": (
                        "const test = require('node:test');\n"
                        "const assert = require('node:assert/strict');\n"
                        "const { serialize } = require('../lib/index.js');\n"
                        "test('existing string serialize passes', () => {\n"
                        "  const enc = s => s.replace(/\\s/g, '%20');\n"
                        "  const fmt = s => s.toUpperCase();\n"
                        "  assert.strictEqual(serialize('v', 'my key', enc, fmt, false), 'MY%20KEY=V');\n"
                        "});\n"
                    ),
                },
            )
            issue_a = (
                "Empty array keys are not encoded or formatted:\n"
                "```js\n"
                "const miniqs = require('miniqs');\n"
                "const enc = s => s.replace(/\\s/g, '%20');\n"
                "const fmt = s => s.toUpperCase();\n"
                "miniqs.serialize([], 'my key', enc, fmt, false); // expected: 'MY%20KEY[]'\n"
                "miniqs.serialize([], 'my key', enc, fmt, true); // expected: 'MY KEY[]'\n"
                "```\n"
            )
            res_a = IR.solve_issue_from_description(root, issue_a, timeout_s=25.0)
            self.assertTrue(res_a["verified"], res_a)
            self.assertEqual(res_a["winner"]["tier"], "JS_EARLY_RETURN_SIBLING_WRAPPER_CONSISTENCY")
            self.assertEqual(res_a["model_calls"], 0)
            self.assertIn("formatter(", res_a["patch_diff"])

        # Case B: Fenced CWE-1321 __proto__ issue -> Op 0af (JS_PROTO_SAFE_DEFINE_PROPERTY)
        with tempfile.TemporaryDirectory(prefix="ir_js_0af_") as td:
            root = pathlib.Path(td)
            _write_files(
                root,
                {
                    "package.json": '{"name": "cloner", "main": "lib/index.js"}\n',
                    "lib/index.js": (
                        "function cloneObj(src) {\n"
                        "  var target = {};\n"
                        "  var keys = Object.keys(src);\n"
                        "  for (var j = 0; j < keys.length; j += 1) {\n"
                        "    var val = src[keys[j]];\n"
                        "    if (val && typeof val === 'object') {\n"
                        "      target[keys[j]] = cloneObj(val);\n"
                        "    } else {\n"
                        "      target[keys[j]] = val;\n"
                        "    }\n"
                        "  }\n"
                        "  return target;\n"
                        "}\n"
                        "module.exports = { cloneObj };\n"
                    ),
                    "test/basic.js": (
                        "const test = require('node:test');\n"
                        "const assert = require('node:assert/strict');\n"
                        "const { cloneObj } = require('../lib/index.js');\n"
                        "test('existing plain clone passes', () => {\n"
                        "  assert.deepStrictEqual(cloneObj({ a: 1, b: { c: 2 } }), { a: 1, b: { c: 2 } });\n"
                        "});\n"
                    ),
                },
            )
            issue_b = (
                "Cloning an object with an own `__proto__` property pollutes the clone prototype:\n"
                "```js\n"
                "const cloner = require('cloner');\n"
                "const src = JSON.parse('{\"__proto__\":{\"polluted\":true},\"ok\":1}');\n"
                "const out = cloner.cloneObj(src);\n"
                "assert.strictEqual(out.polluted, undefined);\n"
                "assert.strictEqual(Object.getPrototypeOf(out), Object.prototype);\n"
                "```\n"
            )
            res_b = IR.solve_issue_from_description(root, issue_b, timeout_s=25.0)
            self.assertTrue(res_b["verified"], res_b)
            self.assertEqual(res_b["winner"]["tier"], "JS_PROTO_SAFE_DEFINE_PROPERTY")
            self.assertIn("Object.defineProperty", res_b["patch_diff"])
            self.assertEqual(res_b["model_calls"], 0)

    def test_03_honest_rejection_when_issue_already_passes_on_c_old(self) -> None:
        """F->P Epistemic Gate MUST reject reproducers that already pass on c_old (no false positives)."""
        with tempfile.TemporaryDirectory(prefix="ir_reject_") as td:
            root = pathlib.Path(td)
            _write_files(
                root,
                {
                    "pyproject.toml": "[project]\nname = 'mathlib'\nversion = '0.1.0'\n",
                    "mathlib.py": "def double(x: int) -> int:\n    return x * 2\n",
                },
            )
            issue = "Calling `double(3)` should return `6`."
            res = IR.solve_issue_from_description(root, issue, python_exe=sys.executable, timeout_s=15.0)
            self.assertFalse(res["verified"])
            self.assertEqual(res["status"], "NO_QUALIFIED_REPRODUCER")
            self.assertTrue(any(r["reason"] == "PASSED_ON_C_OLD" for r in res["rejected_reproducers"]))

    def test_04_one_front_door_blind_swe_issue_and_custom_bin_memory_diff(self) -> None:
        """Verify BOTH:
        (A) ONE Front Door (`UnifiedModel.open_model().solve`) resolves a blind JS issue
            when all existing tests pass on c_old;
        (B) `scan_environment_boundary` + `compute_memory_epistemic_diff` discovers custom
            `./bin/*` tools, identifies the exact unknown gap, learns via live `--help`, and
            recognizes the tool as known on the second pass.
        """
        # (A) ONE Front Door blind JS issue resolution
        with tempfile.TemporaryDirectory(prefix="ir_ofd_js_") as td:
            root = pathlib.Path(td)
            _write_files(
                root,
                {
                    "package.json": '{"name": "dec", "main": "lib/index.js"}\n',
                    "lib/index.js": (
                        "function decodeDot(s) {\n"
                        "  return String(s).replace(/%2E/g, '.');\n"
                        "}\n"
                        "module.exports = { decodeDot };\n"
                    ),
                    "test/dec.test.js": (
                        "const test = require('node:test');\n"
                        "const assert = require('node:assert/strict');\n"
                        "const { decodeDot } = require('../lib/index.js');\n"
                        "test('uppercase %2E works', () => {\n"
                        "  assert.strictEqual(decodeDot('a%2Eb'), 'a.b');\n"
                        "});\n"
                    ),
                },
            )
            goal = (
                "Fix the JS bug in this repository: calling `dec.decodeDot('a%2eb')` "
                "returns `'a%2eb'` instead of `'a.b'` (lowercase hex escape)."
            )
            resp = UM.open_model().solve(goal, inputs={"workspace": str(root)}, mode="EPISTEMIC")
            self.assertTrue(resp.get("pass"), resp)
            ep = resp.get("epistemic_result") or {}
            self.assertEqual(ep.get("model_calls"), 0)
            self.assertIn("/%2E/gi", (root / "lib/index.js").read_text(encoding="utf-8"))

        # (B) Custom `./bin/ktool` scan -> memory diff -> live `--help` acquisition -> memory hit
        with tempfile.TemporaryDirectory(prefix="ir_bin_diff_") as td:
            ws = pathlib.Path(td)
            (ws / "bin").mkdir()
            ktool = ws / "bin" / "ktool"
            ktool.write_text(
                "#!/usr/bin/env python3\n"
                "import sys\n"
                "if '--help' in sys.argv or '-h' in sys.argv:\n"
                "    print('Usage: ktool --in FILE --out FILE --upper')\n"
                "    print('  --in FILE   input text file')\n"
                "    print('  --out FILE  output file path')\n"
                "    print('  --upper     convert text to uppercase')\n"
                "    sys.exit(0)\n"
                "args = sys.argv[1:]\n"
                "in_f = args[args.index('--in') + 1]\n"
                "out_f = args[args.index('--out') + 1]\n"
                "data = open(in_f, encoding='utf-8').read()\n"
                "if '--upper' in args:\n"
                "    data = data.upper()\n"
                "open(out_f, 'w', encoding='utf-8').write(data)\n",
                encoding="utf-8",
            )
            ktool.chmod(ktool.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            (ws / "msg.txt").write_text("hello world\n", encoding="utf-8")

            mem = DCA.EpistemicMemoryStore()
            goal_cli = "Convert msg.txt to uppercase and save into out.txt"
            b0 = DCA.scan_environment_boundary(ws, goal_cli)
            self.assertTrue(any(p.endswith("bin/ktool") for p in b0["binaries"]), b0["binaries"])
            diff0 = DCA.compute_memory_epistemic_diff(b0, mem)
            self.assertFalse(diff0["has_recalled_law"])
            self.assertGreater(diff0["epistemic_gap_count"], 0)

            sol = DCA.solve_with_instant_knowledge(goal_cli, workspace=ws, memory=mem)
            self.assertEqual(sol["status"], "VERIFIED", sol)
            self.assertEqual(sol["model_calls"], 0)
            self.assertEqual((ws / "out.txt").read_text(encoding="utf-8"), "HELLO WORLD\n")

            # After single verified experience, memory diff recalls the abstract law & shrinks epistemic gap!
            diff1 = DCA.compute_memory_epistemic_diff(b0, mem)
            self.assertTrue(diff1["has_recalled_law"], diff1)
            self.assertLess(diff1["epistemic_gap_count"], diff0["epistemic_gap_count"])


if __name__ == "__main__":
    unittest.main()
