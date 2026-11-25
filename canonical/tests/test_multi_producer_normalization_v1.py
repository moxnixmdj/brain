"""Generators must derive edits from observed names, not hardcode them."""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import multi_producer_normalization_v1 as mpn  # noqa: E402


SOURCE = '''class Option:
    def resolve(self):
        envvar = self.envvar
        if envvar is not None:
            return envvar
        return None

    def hint(self):
        if self.envvar is not None:
            return f" (env var: '{self.envvar}')"
        return ""
'''


class MultiProducerTests(unittest.TestCase):
    def test_normalizes_before_is_not_none(self):
        out = mpn.normalize_candidates(SOURCE, {"envvar"})
        self.assertTrue(out)
        self.assertIn("if not envvar:\n            envvar = None", out[0])

    def test_serializes_raw_fstring_value(self):
        out = mpn.serialize_candidates(SOURCE, {"envvar"})
        self.assertTrue(out)
        self.assertIn("_brain_serialize(self.envvar)", out[0])
        self.assertIn("def _brain_serialize", out[0])

    def test_tightening_and_serializer_come_from_observations(self):
        payloads = [{"file": "core.py", "line": 8, "function": "hint",
                     "name": "envvar", "kind": "tuple"}]
        guards = mpn.eps.tightenings(SOURCE, payloads)
        self.assertTrue(any("self.envvar" in how for _, how in guards))


if __name__ == "__main__":
    unittest.main()

FUTURE_SOURCE = '''from __future__ import annotations

import errno


class A:
    def show(self):
        return f"{self.title} "
'''

NONE_SOURCE = '''class A:
    def record(self):
        if self.help is None:
            return None
        return self.spec(), self.help
'''

HANDLER_SOURCE = '''def main():
    try:
        work()
    except Abort:
        echo("Aborted!")
        sys.exit(1)
'''


class ComposedTransitionTests(unittest.TestCase):
    def test_helper_is_placed_after_future_import(self):
        out = mpn.serialize_candidates(FUTURE_SOURCE, {"title"})
        self.assertTrue(out)
        lines = out[0].splitlines()
        self.assertEqual(lines[0], "from __future__ import annotations")
        self.assertIn("def _brain_serialize", "\n".join(lines))

    def test_whitespace_edit_comes_from_observed_pair(self):
        out = mpn.whitespace_candidates(FUTURE_SOURCE, [("Title ", "Title")])
        self.assertTrue(out)
        self.assertIn(".rstrip()", out[0])

    def test_none_return_uses_the_observed_empty_member(self):
        out = mpn.none_return_candidates(
            NONE_SOURCE, [(None, ("SPEC", ""))],
            [{"name": "help", "line": 3, "file": "a.py"}])
        self.assertTrue(out)
        self.assertIn("return self.spec(), ''", out[0])

    def test_fence_combinations_include_both_policies(self):
        fences = mpn.exception_fence_candidates(HANDLER_SOURCE)
        self.assertEqual(len(fences), 4)
        combos = mpn.fence_combinations(HANDLER_SOURCE, fences)
        self.assertEqual(len(combos), 4)
        self.assertTrue(all("except KeyboardInterrupt" in combo for combo in combos))

    def test_nearby_puts_shared_edited_token_first(self):
        parent = "if a is not None:\n    pass\nif envvar is not None:\n    pass\n"
        relevant = "if target is not None:\n    return _brain_serialize(envvar)\n"
        unrelated = "if target is not None:\n    return other\n"
        ranked = mpn._nearby([unrelated, relevant], parent, [[relevant]])
        self.assertEqual(ranked[0], relevant)
