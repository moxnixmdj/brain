"""A parser that is not installed must refuse, not silently narrow.

WHY THIS TEST EXISTS
  Ten production sites wrap an optional-substrate import in `try/except: pass`.
  When the parser is absent, a broadening path therefore skips and
  `recall_and_apply_verified` returns `None` -- which is indistinguishable from
  "this rule does not apply to this source". Those are different facts, and only
  one of them is about the rule.

  Measured 2026-11-03: two tests in `test_optimal_unified_creature_and_prc2_v1.py`
  failed with `compile_rule_to_cst_skeleton -> unexpectedly None` purely because
  the pinned `tree_sitter` was not installed in the sandbox. After installing the
  declared versions, 27 passed. The capability had always been there; the sandbox
  had made it invisible, and nothing said so.

WHAT THIS FILE PINS
  1. With the substrate genuinely absent, the result carries
     `SUBSTRATE_MISSING:<name>==<pin>` and `recall is None` -- and it is NOT
     `None`, so a caller cannot mistake it for "the rule did not apply".
  2. With the substrate present, the same call reaches the broadened tier, so the
     refusal is conditional on absence and not a blanket refusal.
  3. A path that needs no parser is never reported as missing, so the mechanism
     does not smear one missing dependency across unrelated capabilities.
  4. Substrate absence alone does not silently swallow a *different* exception:
     the helper names what failed.

HOW ABSENCE IS SIMULATED WITHOUT LYING
  `substrate_missing_reason` reaches the parser through the single call
  `tree_sitter_swe_kernel_v1.parser_for`, so the absence is produced by making
  that function raise, not by editing the file or faking an import. Nothing in
  the tree is modified, and no real capability is disabled for other tests.

  The import-level branch is exercised separately, against a module name that
  genuinely does not exist, so both halves of the helper are covered by real
  behaviour rather than by a mock.

Authority: NONE. This is a truth-telling test over an existing capability.
"""
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import tree_sitter_swe_kernel_v1 as tsk
from canonical.swe_kernel import verified_skill_crystallizer_v1 as K
from canonical.swe_kernel.skill_verification_contract_v1 import ProjectTestOracle

SCOPE = "substrate/exclusive-boundary/v1"
CONTRACT = {
    "schema_version": 1,
    "scope_id": SCOPE,
    "verification_kind": "TEST_SUITE",
    "dependencies": {"protocol": "1"},
    "preconditions": {"role": "boundary"},
}
CONTEXT = {"dependencies": {"protocol": "1"}, "preconditions": {"role": "boundary"}}
BUGGY = "def within(x, hi):\n    return x <= hi\n"
FIXED = "def within(x, hi):\n    return x < hi\n"
# This shape is reached only by the CST minimal-subtree candidate: the stored rule is
# `return ?a <= ?b`, and the bug sits inside a compound operand of a larger return.
NOVEL_IF = "def target(x, hi):\n    return (x * 2) <= hi\n"
NOVEL_FIXED_IF = "def target(x, hi):\n    return (x * 2) < hi\n"
SUITE = (
    "import unittest\n"
    "from subject import {fn}\n"
    "class Checks(unittest.TestCase):\n"
    "    def test_boundary(self):\n"
    "        for x in range(-8, 9):\n"
    "            for hi in range(-8, 9):\n"
    "                self.assertEqual({fn}(x, hi), {expr})\n"
)


def _project(root: pathlib.Path, source: str, fn: str, expr: str) -> pathlib.Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "subject.py").write_text(source, encoding="utf-8")
    (root / "test_subject.py").write_text(SUITE.format(fn=fn, expr=expr), encoding="utf-8")
    return root


def _substrate_available() -> bool:
    try:
        tsk.parser_for("python")
        return True
    except Exception:
        return False


@unittest.skipUnless(_substrate_available(), "pinned tree_sitter substrate is not installed here")
class MissingSubstrateRefuses(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.base = pathlib.Path(self._tmp.name)
        train = _project(self.base / "train", BUGGY, "within", "x < hi")
        self.store = K.VerifiedSkillStore(self.base / "skills.sqlite", seed=False)
        taught = self.store.crystallize_code_fix(
            before_snippet=BUGGY,
            after_snippet=FIXED,
            language="python",
            error_class="BOUNDARY",
            contract=CONTRACT,
            training_verifier=ProjectTestOracle(train, "subject.py", ["test_subject.py"], SCOPE),
        )
        self.assertTrue(taught.get("crystallized"), taught)
        self.novel = _project(self.base / "novel", NOVEL_IF, "target", "2 * x < hi")

    def _oracle(self):
        return ProjectTestOracle(self.novel, "subject.py", ["test_subject.py"], SCOPE)

    def _recall(self, oracle):
        return self.store.recall_and_apply_verified(
            source_text=NOVEL_IF,
            language="python",
            verifier=oracle,
            error_class="BOUNDARY",
            required_verification_kind="TEST_SUITE",
            scope_id=SCOPE,
            context=CONTEXT,
        )

    # ------------------------------------------------------------- the refusal
    def test_a_missing_parser_reports_a_reason_instead_of_narrowing_silently(self):
        def unavailable(language):
            raise tsk.TreeSitterSWEError("TREE_SITTER_SUBSTRATE_MISSING")

        with mock.patch.object(tsk, "parser_for", side_effect=unavailable):
            result = self._recall(self._oracle())

        self.assertIsNotNone(result, "a missing parser must not look like 'no rule applies'")
        self.assertIsNone(result["recall"])
        self.assertEqual(result["reason"], "BROADENING_SUBSTRATE_MISSING")
        self.assertIn("SCOPE_EXPRESSION_CST", result["substrate_missing"])
        reason = result["substrate_missing"]["SCOPE_EXPRESSION_CST"]
        self.assertIn("SUBSTRATE_MISSING", reason)
        self.assertIn("tree_sitter==", reason, "the reason must name the pin it needs, not just fail")
        self.assertIs(result["whole_task_correctness_proved"], False)

    def test_the_same_call_reaches_the_broadened_tier_when_the_parser_is_present(self):
        """The refusal is conditional on absence. Without this assertion, the
        refusal above would be satisfied by a blanket refusal and pin nothing."""
        result = self._recall(self._oracle())
        self.assertIsNotNone(result)
        self.assertNotIn("substrate_missing", result)
        self.assertEqual(result["patched_source"], NOVEL_FIXED_IF)
        self.assertEqual(result["scope_tier"], "SCOPE_EXPRESSION")
        self.assertIn(result["recall_strategy"], {"cst_minimal_subtree", "narrowed_pattern"})

    def test_a_path_needing_no_parser_is_never_reported_missing(self):
        self.assertIsNone(K.substrate_missing_reason("CROSS_LANGUAGE_LEXICAL"))
        self.assertIsNone(K.substrate_missing_reason("SCOPE_ALGEBRAIC_EGRAPH"))

    def test_a_missing_host_module_is_named_rather_than_crashing(self):
        reason = K.substrate_missing_reason(
            {"module": "definitely_not_a_module_v1", "substrate": ()}
        )
        self.assertIsNotNone(reason)
        self.assertIn("definitely_not_a_module_v1", reason)
        self.assertIn("ModuleNotFoundError", reason)

    def test_the_pin_comes_from_the_manifest_and_is_not_invented(self):
        pins = K._substrate_pins()
        # Both manifest spellings must resolve: the manifest writes `tree_sitter`,
        # and normalising to `tree-sitter` is exactly the silence this removes.
        self.assertEqual(K._pinned_version("tree_sitter"), pins["tree_sitter"])
        self.assertEqual(K._pinned_version("tree-sitter"), pins["tree_sitter"])
        self.assertEqual(K._pinned_version("tree_sitter_languages"), pins["tree_sitter_languages"])
        self.assertEqual(pins["tree_sitter"], pins["tree-sitter"])


if __name__ == "__main__":
    unittest.main()
