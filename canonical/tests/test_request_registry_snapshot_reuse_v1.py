"""Request-local registry reuse removes repeated work, not freshness checks."""
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from canonical.runtime import capability_composer_v1 as composer
from canonical.runtime import composer_route_v1 as route


class RequestRegistrySnapshotReuseTests(unittest.TestCase):
    def test_stated_command_loads_registry_once(self):
        with patch.object(composer, 'load_registry', wraps=composer.load_registry) as loader:
            result = route.route('Run the command "python3 --version"')
        self.assertTrue(result['pass'], result)
        self.assertEqual(result['chain'], ['shell.command.run'])
        self.assertEqual(loader.call_count, 1)

    def test_lexical_writer_loads_registry_once(self):
        with patch.object(composer, 'load_registry', wraps=composer.load_registry) as loader:
            result = route.route('Write the text hello to out.txt')
        self.assertTrue(result['pass'], result)
        self.assertEqual(result['chain'], ['text.file.write'])
        self.assertEqual(loader.call_count, 1)

    def test_standalone_candidate_ranking_loads_registry_once(self):
        with patch.object(composer, 'load_registry', wraps=composer.load_registry) as loader:
            tokens = route.candidate_tokens('Write the text hello to out.txt')
        self.assertTrue(tokens)
        self.assertEqual(tokens[0], 'text.file.available')
        self.assertEqual(loader.call_count, 1)

    def test_caller_supplied_snapshot_is_reused_without_mutation_or_reload(self):
        snapshot = composer.load_registry()
        graph = composer.graph(registry=snapshot)
        original = json.dumps(snapshot, sort_keys=True)
        with patch.object(composer, 'load_registry', wraps=composer.load_registry) as loader:
            tokens = route.candidate_tokens('Write the text hello to out.txt', graph,
                                           registry=snapshot)
        self.assertEqual(tokens[0], 'text.file.available')
        self.assertEqual(loader.call_count, 0)
        self.assertEqual(json.dumps(snapshot, sort_keys=True), original)

    def test_request_is_coherent_and_next_request_sees_same_mtime_rewrite(self):
        # Instrument actual reads; never substitute a fake loader result. The
        # fixture contains unchanged entries from the real registry, while the
        # on-disk rewrite happens after its first complete load.
        registry = composer.load_registry()
        command = json.dumps({'capabilities': {'shell.command.run': registry['shell.command.run']}})
        writer = json.dumps({'capabilities': {'text.file.write': registry['text.file.write']}})
        with TemporaryDirectory(prefix='registry_snapshot_') as tmp:
            path = Path(tmp) / 'registry.json'
            path.write_text(command)
            original = path.stat()
            actual_load = composer.load_registry
            reads = []

            def read_then_replace(*args, **kwargs):
                loaded = actual_load(*args, **kwargs)
                reads.append(loaded)
                if len(reads) == 1:
                    path.write_text(writer)
                    os.utime(path, ns=(original.st_atime_ns, original.st_mtime_ns))
                return loaded

            with patch.object(composer, 'REGISTRY', path):
                with patch.object(composer, 'load_registry', side_effect=read_then_replace):
                    first = route.route('Run the command "python3 --version"')
                    second = route.route('Run the command "python3 --version"')
            self.assertTrue(first['pass'], first)
            self.assertEqual(first['chain'], ['shell.command.run'])
            self.assertFalse(second['pass'], second)
            self.assertEqual(path.stat().st_mtime_ns, original.st_mtime_ns)
            self.assertEqual(len(reads), 2)
            self.assertIn('shell.command.run', reads[0])
            self.assertNotIn('shell.command.run', reads[1])


if __name__ == '__main__':
    unittest.main()
