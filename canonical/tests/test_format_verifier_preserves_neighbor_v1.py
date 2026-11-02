"""A format check must never write or delete a caller's neighboring files."""
from __future__ import annotations

import gzip
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import program_synthesis_v1 as synthesis


class FormatVerifierPreservesNeighborTests(unittest.TestCase):
    def test_valid_gzip_preserves_existing_verifier_named_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            protected = root / '_verify.py'
            protected.write_bytes(b'important user script\n')
            target = root / 'output.gz'
            target.write_bytes(gzip.compress(b'correct payload'))
            self.assertEqual(synthesis.verify_round_trip(target, '.gz'),
                             (True, 'ROUND_TRIP_OK'))
            self.assertEqual(protected.read_bytes(), b'important user script\n')
            self.assertEqual({p.name for p in root.iterdir()}, {'_verify.py', 'output.gz'})

    def test_invalid_gzip_preserves_existing_verifier_named_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            protected = root / '_verify.py'
            protected.write_bytes(b'keep on refusal\n')
            target = root / 'output.gz'
            target.write_bytes(b'not a gzip stream')
            passed, _ = synthesis.verify_round_trip(target, '.gz')
            self.assertFalse(passed)
            self.assertEqual(protected.read_bytes(), b'keep on refusal\n')
            self.assertEqual(target.read_bytes(), b'not a gzip stream')

    def test_verifier_named_symlink_cannot_overwrite_or_remove_anything(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            protected = root / 'important.txt'
            protected.write_bytes(b'never overwrite this\n')
            link = root / '_verify.py'
            link.symlink_to(protected)
            target = root / 'output.gz'
            target.write_bytes(gzip.compress(b'payload'))
            self.assertEqual(synthesis.verify_round_trip(target, '.gz'),
                             (True, 'ROUND_TRIP_OK'))
            self.assertEqual(protected.read_bytes(), b'never overwrite this\n')
            self.assertTrue(link.is_symlink())

    def test_target_itself_may_have_the_former_verifier_filename(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / '_verify.py'
            original = gzip.compress(b'the artifact itself')
            target.write_bytes(original)
            self.assertEqual(synthesis.verify_round_trip(target, '.gz'),
                             (True, 'ROUND_TRIP_OK'))
            self.assertEqual(target.read_bytes(), original)

    def test_missing_neighbor_is_not_created(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / 'output.gz'
            target.write_bytes(gzip.compress(b'payload'))
            self.assertEqual(synthesis.verify_round_trip(target, '.gz'),
                             (True, 'ROUND_TRIP_OK'))
            self.assertEqual([p.name for p in root.iterdir()], ['output.gz'])


if __name__ == '__main__':
    unittest.main()
