"""Public request binding must preserve whole identifiers, never prefixes."""
import contextlib
import io
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from canonical.runtime import goal_compiler as compiler
from canonical.runtime import goal_front_compiler_v1 as front
from canonical.runtime import declared_input_derivation_v1 as derivation
from canonical.runtime.live_integrated_brain_v1 import load_verified_registry
from canonical.runtime import swe_typed_plan_v1 as swe
from canonical.runtime.bound_capabilities import python_refactor_rename_symbol as rename
from canonical.runtime.bound_capabilities import python_repair_apply_verified_v1 as delivery

CID = 'python.refactor.rename_symbol.v1'


class RequestIdentifierBindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(prefix='request-identifier-binding-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'pkg').mkdir()
        self.source = self.root / 'pkg/core.py'
        self.original = b'def helper(x): return x+1\n'
        self.source.write_bytes(self.original)
        self.registry = compiler._platform_admissible_registry(dict(load_verified_registry()))

    def goal(self, replacement):
        return f'Rename the function helper to {replacement} in pkg/core.py and update every caller.'

    def test_public_front_preserves_complete_unicode_replacements(self):
        for name in ('résultat', 'compute_雪', 're\u0301sultat'):
            with self.subTest(name=name):
                result = front.compile_goal(self.goal(name), self.registry, self.root)
                self.assertEqual(result['selected_capability'], CID)
                self.assertEqual(result['inputs']['new_symbol'], name)
                self.assertEqual(self.source.read_bytes(), self.original)

    def test_public_compilation_reaches_existing_unicode_executor(self):
        for name in ('résultat', 'compute_雪'):
            with self.subTest(name=name):
                self.source.write_bytes(self.original)
                goal = self.goal(name)
                compiled = front.compile_goal(goal, self.registry, self.root)
                self.assertEqual(compiled['selected_capability'], CID)
                args = dict(compiled['inputs'])
                # Reuse existing report relocation, not the unsafe file alias.
                args['output_path'] = swe._fresh_output_path(goal, self.root, args)
                self.assertIsNotNone(args['output_path'])
                with contextlib.redirect_stdout(io.StringIO()):
                    result = rename.run(args, self.root)
                self.assertEqual(result['new_symbol'], name)
                self.assertFalse(result['verified'])  # No suite was stated.
                rc, output = delivery._run_test(
                    [sys.executable, '-B', '-c',
                     'import core; assert getattr(core,' + repr(name) + ')(2)==3; '
                     'assert not hasattr(core,"helper")'], self.source.parent, 10)
                self.assertEqual(rc, 0, output.decode(errors='replace'))

    def test_invalid_token_does_not_select_a_partial_rename(self):
        for name in ('valid-name', 'valid.name', 'valid+name'):
            with self.subTest(name=name):
                result = front.compile_goal(self.goal(name), self.registry, self.root)
                self.assertNotEqual(result['selected_capability'], CID)
                self.assertNotIn('new_symbol', result.get('inputs', {}))
                self.assertEqual(self.source.read_bytes(), self.original)

    def test_declared_rename_grammar_preserves_complete_replacement(self):
        for name in ('résultat', 'compute_雪', 're\u0301sultat'):
            with self.subTest(name=name):
                rows = derivation.derive(self.goal(name), self.registry[CID], self.root)
                self.assertEqual(rows['new_symbol']['value'], name)
                self.assertEqual(rows['new_symbol']['evidence'], name)

    def test_named_replacement_preserves_whole_unicode_token(self):
        for name in ('résultat', 'compute_雪', 're\u0301sultat'):
            with self.subTest(name=name):
                goal = f'Create a new function named `{name}` in pkg/core.py.'
                rows = derivation.derive(goal, self.registry[CID], self.root)
                self.assertEqual(rows['new_symbol']['value'], name)
                self.assertEqual(rows['new_symbol']['evidence'], name)

    def test_replacement_reader_does_not_accept_invalid_prefix(self):
        for name in ('valid-name', 'valid.name', 'valid+name', 'valid/name'):
            with self.subTest(name=name):
                self.assertIsNone(front.declared_replacement_identifier(self.goal(name)))

    def test_ambiguity_remains_unbound_and_sentence_punctuation_is_supported(self):
        self.assertIsNone(front.declared_replacement_identifier('Rename helper to first and rename other to second.'))
        self.assertEqual(front.declared_replacement_identifier('Rename helper to résultat.'), 'résultat')
        self.assertEqual(front.declared_replacement_identifier('Rename helper to `compute_雪`.'), 'compute_雪')

    def test_invalid_replacement_does_not_emit_partial_declared_name(self):
        for name in ('valid-name', 'valid.name', 'valid+name'):
            with self.subTest(name=name):
                rows = derivation.derive(self.goal(name), self.registry[CID], self.root)
                self.assertNotIn('new_symbol', rows)


if __name__ == '__main__':
    unittest.main()
