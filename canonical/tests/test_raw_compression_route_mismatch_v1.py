"""A gzip-file request must not run an unrelated tar-manifest archive."""
from __future__ import annotations

import unittest

from canonical.runtime.live_integrated_brain_v1 import _raw_compression_output_mismatch


class RawCompressionRouteMismatchTests(unittest.TestCase):
    def test_explicit_single_file_gzip_rejects_generated_tar_destination(self):
        self.assertTrue(_raw_compression_output_mismatch(
            'compress notes.txt into notes.txt.gz',
            'archive.tar_gz.create_from_manifest',
            {'output_path': 'canonical/astra_runtime/tmp/generated.tar.gz'}))

    def test_tar_goal_and_other_capability_are_not_reclassified(self):
        inputs = {'output_path': 'canonical/astra_runtime/tmp/generated.tar.gz'}
        self.assertFalse(_raw_compression_output_mismatch(
            'compress notes.txt into notes.tar.gz', 'archive.tar_gz.create_from_manifest', inputs))
        self.assertFalse(_raw_compression_output_mismatch(
            'compress notes.txt into notes.txt.gz with a tar archive',
            'archive.tar_gz.create_from_manifest', inputs))
        self.assertFalse(_raw_compression_output_mismatch(
            'compress notes.txt into notes.txt.gz', 'other.capability', inputs))
        self.assertFalse(_raw_compression_output_mismatch(
            'audit the archive notes.txt.gz', 'archive.tar_gz.create_from_manifest', inputs))

    def test_matching_destination_is_not_this_specific_mismatch(self):
        self.assertFalse(_raw_compression_output_mismatch(
            'compress notes.txt into notes.txt.gz',
            'archive.tar_gz.create_from_manifest', {'output_path': 'notes.txt.gz'}))


if __name__ == '__main__':
    unittest.main()
