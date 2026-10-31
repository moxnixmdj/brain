"""Derivation evidence follows current source bytes, not restorable metadata."""
import ast
import cProfile
import os
from pathlib import Path
import pstats
from tempfile import TemporaryDirectory
import unittest

from canonical.runtime import declared_input_derivation_v1 as derivation


DEFAULT = "def run(args, root):\n    return args.get('strict', True)\n"
NO_DEFAULT = DEFAULT.replace("args.get('strict', True)", "args['strict']".ljust(len("args.get('strict', True)")))


class DerivationContentCacheTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory(prefix="brain-derivation-content-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.path = self.root / "adapter.py"
        self.path.write_text(DEFAULT, encoding="utf-8")

    def defaults(self, root=None):
        return derivation.adapter_defaulted_keys(
            {"source": {"adapter_path": str(self.path)}}, self.root if root is None else root)

    def tree(self):
        return derivation._tree_of(self.root, "adapter.py")

    def rewrite(self, source):
        before = self.path.stat()
        self.assertEqual(len(source.encode("utf-8")), before.st_size)
        self.path.write_text(source, encoding="utf-8")
        os.utime(self.path, ns=(before.st_atime_ns, before.st_mtime_ns))
        self.assertEqual(self.path.stat().st_size, before.st_size)
        self.assertEqual(self.path.stat().st_mtime_ns, before.st_mtime_ns)

    def assert_current(self):
        self.assertEqual(ast.dump(self.tree()), ast.dump(ast.parse(self.path.read_text())))

    def test_default_removed_with_same_size_and_mtime(self):
        self.assertIn("strict", self.defaults())
        self.rewrite(NO_DEFAULT)
        self.assertEqual(self.defaults(), {})
        self.assert_current()

    def test_default_added_with_same_size_and_mtime(self):
        self.path.write_text(NO_DEFAULT, encoding="utf-8")
        self.assertEqual(self.defaults(), {})
        self.rewrite(DEFAULT)
        self.assertIn("strict", self.defaults())
        self.assert_current()

    def test_symbol_renamed_with_same_size_and_mtime(self):
        self.assertEqual(self.tree().body[0].name, "run")
        self.rewrite(DEFAULT.replace("def run", "def new"))
        self.assertEqual(self.tree().body[0].name, "new")
        self.assert_current()

    def test_atomic_replacement_with_preserved_metadata(self):
        self.assertIn("strict", self.defaults())
        self.tree()
        before = self.path.stat()
        replacement = self.root / "replacement.py"
        replacement.write_text(NO_DEFAULT, encoding="utf-8")
        os.utime(replacement, ns=(before.st_atime_ns, before.st_mtime_ns))
        replacement.replace(self.path)
        self.assertEqual(self.defaults(), {})
        self.assert_current()

    def test_malformed_source_cannot_leave_old_evidence(self):
        self.assertIn("strict", self.defaults())
        self.tree()
        bad = "def (".ljust(len(DEFAULT))
        self.rewrite(bad)
        self.assertEqual(self.defaults(), {})
        self.assertEqual(self.tree().body, [])
        self.rewrite(DEFAULT)
        self.assertIn("strict", self.defaults())
        self.assert_current()

    def test_invalid_utf8_fails_closed_even_in_comment(self):
        self.defaults()
        self.tree()
        self.path.write_bytes(DEFAULT.encode() + b"#\xff\n")
        self.assertEqual(self.defaults(), {})
        self.assertEqual(self.tree().body, [])

    def test_deleted_file_cannot_reuse_evidence(self):
        self.defaults()
        self.tree()
        self.path.unlink()
        self.assertEqual(self.defaults(), {})
        self.assertEqual(self.tree().body, [])

    def test_unchanged_bytes_share_parse_despite_metadata_change(self):
        first = self.tree()
        before = self.path.stat()
        os.utime(self.path, ns=(before.st_atime_ns, before.st_mtime_ns + 1_000_000))
        self.assertIs(self.tree(), first)
        self.assertIn("strict", self.defaults())

    def test_default_evidence_is_root_specific_and_defensively_copied(self):
        local = self.defaults()
        nested = self.defaults(self.root.parent)
        self.assertEqual(local["strict"], "adapter.py:2")
        self.assertEqual(nested["strict"], self.root.name + "/adapter.py:2")
        local["strict"] = "corrupted by caller"
        local.clear()
        self.assertNotEqual(self.defaults()["strict"], "corrupted by caller")

    def test_cold_consumers_share_one_parse_and_warm_calls_do_not_parse(self):
        def calls():
            self.defaults()
            self.tree()
        cold = cProfile.Profile()
        cold.runcall(calls)
        warm = cProfile.Profile()
        for _ in range(3):
            warm.runcall(calls)

        def parse_calls(profile):
            return sum(stats[1] for (file, _, name), stats in pstats.Stats(profile).stats.items()
                       if Path(file).name == "ast.py" and name == "parse")
        self.assertEqual(parse_calls(cold), 1)
        self.assertEqual(parse_calls(warm), 0)

    def test_many_revisions_keep_only_latest_entry_for_path(self):
        for n in range(40):
            source = DEFAULT.replace("def run", f"def f{n:03}")
            # Constant-width identifiers let every revision share size and mtime.
            if n == 0:
                self.path.write_text(source, encoding="utf-8")
            else:
                self.rewrite(source)
            self.assertIn("strict", self.defaults())
            self.assertEqual(self.tree().body[0].name, f"f{n:03}")
        key = str(self.path.resolve())
        self.assertEqual(sum(k == key for k in derivation._PARSED_TREE_CACHE), 1)
        self.assertEqual(sum(k[0] == key for k in derivation._ADAPTER_DEFAULTS_CACHE), 1)

    def test_both_caches_are_bounded_across_many_paths(self):
        for n in range(520):
            path = self.root / f"adapter_{n}.py"
            path.write_text(DEFAULT, encoding="utf-8")
            self.assertIn("strict", derivation.adapter_defaulted_keys({"source": {"adapter_path": path.name}}, self.root))
            self.assertEqual(derivation._tree_of(self.root, path.name).body[0].name, "run")
        self.assertLessEqual(len(derivation._ADAPTER_DEFAULTS_CACHE), 512)
        self.assertLessEqual(len(derivation._PARSED_TREE_CACHE), 512)


if __name__ == "__main__":
    unittest.main()
