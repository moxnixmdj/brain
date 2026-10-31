"""The live registry is never a TRUNCATION of the snapshot.

Measured on main (521f1d5): ``canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json``
held a 33-row projection while its own snapshot held 140 (434 with the extended
registry), and nothing objected.  ``load_verified_registry`` reads that file
first, so 401 capabilities -- every SWE refactor and repair row among them --
became unreachable and the 28-task surface probe fell from 25/28 to 2/28.  The
loss is silent: a truncated registry looks like a registry.

The law, and it is the only one that needs stating:

  * the committed file is either the ``@`` POINTER (the tree's own idiom: the
    loader follows it to the snapshot), or a registry that is at least as
    complete as the snapshot it is supposed to project;
  * a partial projection is a lie about what the machine can do, so it fails
    here rather than at the tenth task that quietly returns "no capability".

Nothing here asserts a COUNT -- the registry legitimately grows and shrinks as
rows are added, retired or superseded.  It asserts the relation: the file the
loader reads may never contain less than the snapshot it stands for.
"""
from __future__ import annotations

import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIVE = ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
SNAPSHOT = ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_SNAPSHOT_V1.json"


def _capabilities(path: pathlib.Path) -> dict:
    doc = json.loads(path.read_text(encoding="utf-8"))
    rows = doc.get("capabilities")
    if not isinstance(rows, dict):
        raise AssertionError("REGISTRY_HAS_NO_CAPABILITIES:" + path.name)
    return rows


class TheLiveRegistryIsNotTruncatedTests(unittest.TestCase):
    def test_the_committed_file_is_a_pointer_or_a_complete_projection(self):
        raw = LIVE.read_bytes()
        if raw[:1] == b"@":
            # The pointer idiom: the loader resolves it to the snapshot, so no
            # projection exists to be stale.
            self.assertLess(len(raw), 4096, "a pointer is a pointer, not a payload")
            return
        live = _capabilities(LIVE)
        snapshot = _capabilities(SNAPSHOT)
        missing = sorted(set(snapshot) - set(live))
        self.assertEqual(
            missing, [],
            "the live registry drops %d capabilities the snapshot defines, "
            "and the loader reads this file first: %s" % (len(missing), missing[:8]))

    def test_the_loaded_registry_reaches_every_snapshot_capability(self):
        from canonical.runtime.live_integrated_brain_v1 import load_verified_registry

        snapshot = set(_capabilities(SNAPSHOT))
        loaded = set(load_verified_registry())
        missing = sorted(snapshot - loaded)
        self.assertEqual(
            missing, [],
            "these snapshot capabilities are not reachable through the loader: %s"
            % missing[:8])

    def test_the_swe_rows_the_census_counts_are_reachable(self):
        from canonical.runtime.live_integrated_brain_v1 import load_verified_registry

        loaded = load_verified_registry()
        for cid in ("python.refactor.move_function.v1",
                    "python.software.repair.apply.verified.v1",
                    "python.source.definition_count.v1"):
            self.assertIn(cid, loaded, cid)


if __name__ == "__main__":
    unittest.main()
