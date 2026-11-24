"""Pure parsing/path checks; no Docker, Harbor daemon, or mocked executable."""
import tempfile
from pathlib import Path
import unittest

from canonical.runtime import harbor_live_compose_diagnostic_v1 as live


class ComposeDiagnosticTests(unittest.TestCase):
    def test_single_full_id_required(self):
        cid = 'a' * 64
        self.assertEqual(live.parse_single_id(cid + '\n'), cid)
        for output in ('', 'a' * 12, cid + '\n' + 'b' * 64, cid.upper(), None):
            with self.subTest(output=output):
                with self.assertRaises(live.ComposeDiagnosticError):
                    live.parse_single_id(output)

    def test_compose_service_and_project_must_both_match(self):
        doc = [{'Config': {'Labels': {'com.docker.compose.project': 'job-abc',
                                      'com.docker.compose.service': 'main'}}}]
        self.assertTrue(live.compose_labels_match(doc, project='job-abc', service='main'))
        self.assertFalse(live.compose_labels_match(doc, project='other', service='main'))
        self.assertFalse(live.compose_labels_match(doc, project='job-abc', service='sidecar'))
        self.assertFalse(live.compose_labels_match(doc * 2, project='job-abc', service='main'))
        self.assertFalse(live.compose_labels_match([{'Config': None}], project='job-abc', service='main'))

    def test_host_paths_are_resolved_and_missing_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source'
            source.mkdir()
            link = root / 'alias'
            link.symlink_to(source, target_is_directory=True)
            self.assertEqual(live._real_directory(link), str(source.resolve()))
            for path in ('/', root / 'missing', None):
                with self.subTest(path=path), self.assertRaises(live.ComposeDiagnosticError):
                    live._real_directory(path)


if __name__ == '__main__':
    unittest.main()
