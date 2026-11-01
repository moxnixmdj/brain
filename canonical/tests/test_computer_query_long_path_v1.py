"""Long names must not turn a genuine one-value wc answer into a refusal."""
import shutil
import tempfile
from pathlib import Path
import unittest

from canonical.runtime import computer_env_v1 as cenv


@unittest.skipUnless(shutil.which('wc'), 'requires real wc')
class LongPathQueryTests(unittest.TestCase):
    def test_long_file_name_and_spaces(self):
        with tempfile.TemporaryDirectory(prefix='brain-long-query-') as tmp:
            source = Path(tmp) / ('long name ' + 'x' * 90 + '.txt')
            source.write_text('alpha\nbeta\ngamma\n')
            answer = cenv.answer_query('count the lines in the file', source, programs=['wc'], timeout=3)
            self.assertTrue(answer['pass'], answer)
            self.assertEqual(answer['value'], '3')

    def test_existing_value_shape_checks_remain(self):
        self.assertIsNone(cenv._bare_value(b'2 extra words'))
        self.assertIsNone(cenv._bare_value(b'2\n3'))
        self.assertIsNone(cenv._bare_value(b'x' * 65))
