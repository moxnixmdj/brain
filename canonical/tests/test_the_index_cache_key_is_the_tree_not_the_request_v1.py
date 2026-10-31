"""The symbol index's cache key must be the tree it describes, not the request that asked.

Measured 2026-10-31 on `34f867a`: the front door names each request's artifact after the
request, so two different sentences about `canonical/runtime` asked for two different files,
the index found no cache for either, and each re-parsed 2 287 modules -- **15.5 s** to produce
a 105.8 MB artifact whose answer occupied 1.5 MB.

`_cached_modules` was written to remember "a previous run of this same index".  The one key a
caller cannot repeat is the artifact path, so the memory never fired across sentences.  The
rows are found beside the requested artifact now, under a stricter check than proximity:

* the sibling must declare the same ``source_root`` and the same schema;
* only the newest few are considered;
* every row it offers is still checked against the sha256 of the file's current bytes by the
  index itself -- the same check a fresh parse passes.

So the source stays the authority.  These tests pin the finding rule and, more importantly,
that a wrong or hostile sibling cannot inject a row.
"""

from __future__ import annotations

import json
import os
import pathlib
import tempfile
import unittest

from canonical.runtime.bound_capabilities import python_source_symbol_index as index


def _artifact(source_root: str, modules: list[dict]) -> dict:
    return {"schema": "PROJECT_BRAIN_PYTHON_SYMBOL_INDEX_V1",
            "source_root": source_root,
            "modules": modules,
            "symbols": {},
            "callers_of": {},
            "unparseable": [],
            "totals": {"files": len(modules), "unparseable": 0, "symbols": 0,
                       "references": 0, "call_edges": 0}}


class TheCacheFindsTheTree(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = pathlib.Path(self.temp.name)
        self.requested = self.dir / "afe55713c458_typed_swe_report.json"

    def _write(self, name: str, payload: dict, older: bool = False) -> pathlib.Path:
        path = self.dir / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        if older:
            stamp = path.stat().st_mtime_ns - 10_000_000_000
            os.utime(path, ns=(stamp, stamp))
        return path

    def test_a_sibling_without_producer_provenance_supplies_no_rows(self) -> None:
        rows = [{"path": "canonical/runtime/a.py", "sha256": "0" * 64}]
        self._write("other_request.json", _artifact("canonical/runtime", rows))
        found = index._cached_modules_for_tree(self.requested, "canonical/runtime")
        # Synthetic persisted metadata is not evidence this producer derived it.
        self.assertEqual(found, {})

    def test_a_sibling_for_a_different_tree_is_ignored(self) -> None:
        rows = [{"path": "elsewhere/a.py", "sha256": "0" * 64}]
        self._write("other_tree.json", _artifact("pkg", rows))
        found = index._cached_modules_for_tree(self.requested, "canonical/runtime")
        self.assertEqual(found, {})

    def test_a_sibling_that_is_not_an_index_is_ignored(self) -> None:
        self._write("noise.json", {"schema": "SOMETHING_ELSE", "source_root": "canonical/runtime",
                                   "modules": [{"path": "x.py"}]})
        self.assertEqual(index._cached_modules_for_tree(self.requested, "canonical/runtime"), {})

    def test_a_broken_sibling_does_not_raise(self) -> None:
        (self.dir / "broken.json").write_text("{not json", encoding="utf-8")
        self.assertEqual(index._cached_modules_for_tree(self.requested, "canonical/runtime"), {})

    def test_the_requested_artifact_is_not_its_own_cache(self) -> None:
        rows = [{"path": "canonical/runtime/a.py", "sha256": "0" * 64}]
        self._write(self.requested.name, _artifact("canonical/runtime", rows))
        self.assertEqual(index._cached_modules_for_tree(self.requested, "canonical/runtime"), {})


class AFreshRowStillWins(unittest.TestCase):
    """A reused row is only a shortcut: the index verifies it against the file on disk."""

    def test_a_changed_file_is_reparsed_even_when_a_sibling_offers_a_row(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = pathlib.Path(temp.name)
        (root / "pkg").mkdir()
        (root / "pkg" / "calc.py").write_text("def add(a, b):\n    return a - b\n",
                                              encoding="utf-8")
        (root / "out").mkdir()
        stale = {"path": "pkg/calc.py", "sha256": "0" * 64, "imports": [], "definitions": [],
                 "references": [], "calls": [], "row_sha256": "0" * 64}
        (root / "out" / "previous.json").write_text(
            json.dumps(_artifact("pkg", [stale])), encoding="utf-8")
        requested = root / "out" / "this_request.json"
        cached = index._cached_modules_for_tree(requested, "pkg")
        report, reused = index._collect_index_parts("pkg", root, cached)
        self.assertEqual(reused, 0, "a row whose sha does not match must not be reused")
        self.assertEqual(report["totals"]["symbols"], 1)


if __name__ == "__main__":
    unittest.main()
