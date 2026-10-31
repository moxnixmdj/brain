"""A row's declared requirement must name a token some row really publishes.

Measured 2026-10-31 on fabf28c: six SWE rows required the string
``python.source.symbols.index.ast``.  That string is a **capability id**, and the row it
names publishes ``python.source.symbol_index`` -- not its own id.  So the producer existed,
was verified and was indexed, and every one of the six consumers was unable to bind it,
because the binder keys providers by published effect token.  One of the six was
``software.repair.choreograph.crossfile.v1``, the most-selected row in the advanced census.

The defect was invisible to every existing check: the row loads, the token is a string, and
nothing ever compared a requirement against what the registry actually publishes.  The law
is therefore written on the registry, and it is structural rather than a list of typos:

    if a requirement spells a capability id, that id must be a published token.

Zero false positives by construction.  Rows such as ``python.source.crossfile_edit.choreograph.v1``
publish their own id as an effect token on purpose, and a requirement naming that id is
satisfiable and legal; ``python.source.symbols.index.ast`` does not, and a requirement naming
it is a mistyped effect.
"""

from __future__ import annotations

import json
import pathlib
import unittest

REGISTRY_DIR = pathlib.Path(__file__).resolve().parents[1] / "runtime"
REGISTRY_FILES = ("BOUND_CAPABILITY_REGISTRY_V1.json",
                  "BOUND_CAPABILITY_REGISTRY_SNAPSHOT_V1.json")

# Requirements that no row publishes and that no caller can supply either.  These are dead
# rows, not mistyped effects: nothing in the tree produces these tokens.  Pinned so a new one
# cannot appear silently, and phrased as a subset so repairing them keeps the law green.
_KNOWN_UNPROVIDED = frozenset({"source.candidate.provenance.verified"})


def _rows(path: pathlib.Path) -> dict[str, dict]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    rows = doc.get("capabilities")
    if not isinstance(rows, dict):
        raise AssertionError(f"{path.name} has no capabilities object")
    return {cid: row for cid, row in rows.items() if isinstance(row, dict)}


def _published(rows: dict[str, dict]) -> set[str]:
    return {str(token) for row in rows.values() for token in (row.get("provides") or [])}


def missing_publications(rows: dict[str, dict]) -> list[tuple[str, str]]:
    """(consumer, requirement) pairs where the requirement names an id nothing publishes."""
    published = _published(rows)
    out: list[tuple[str, str]] = []
    for cid, row in rows.items():
        for need in row.get("requires") or []:
            need = str(need)
            if need in rows and need not in published:
                out.append((cid, need))
    return out


class DeclaredRequirementNamesAPublishedToken(unittest.TestCase):
    def test_no_shipped_row_requires_an_id_nothing_publishes(self):
        for name in REGISTRY_FILES:
            path = REGISTRY_DIR / name
            if not path.is_file():
                continue
            with self.subTest(registry=name):
                bad = missing_publications(_rows(path))
                self.assertEqual(
                    bad, [],
                    "a requirement naming a capability id must be a token that id publishes: "
                    + ", ".join(f"{cid} requires {need}" for cid, need in bad))

    def test_every_requirement_is_published_or_an_environment_fact(self):
        """The same question for tokens that are not ids.

        ``*.available`` tokens are preconditions the caller supplies (a file exists, a node
        runtime exists); no capability can publish them and they are not effects.
        """
        from canonical.runtime import live_brain_route_admission_v1 as door

        rows = dict(door.load_verified_registry())
        published = _published(rows)
        orphans = {str(need) for row in rows.values()
                   for need in (row.get("requires") or [])
                   if str(need) not in published and not str(need).endswith(".available")}
        self.assertLessEqual(orphans, set(_KNOWN_UNPROVIDED),
                             "new unprovided requirement(s): "
                             + ", ".join(sorted(orphans - set(_KNOWN_UNPROVIDED))))

    def test_the_symbol_index_is_named_by_the_effect_it_publishes(self):
        """The specific row, so a future rename cannot silently re-open the same hole."""
        from canonical.runtime import live_brain_route_admission_v1 as door

        rows = dict(door.load_verified_registry())
        producer = rows.get("python.source.symbols.index.ast")
        self.assertIsNotNone(producer, "the symbol-index row must exist")
        self.assertIn("python.source.symbol_index", producer.get("provides") or [])
        self.assertNotIn("python.source.symbols.index.ast", producer.get("provides") or [],
                         "the id is a name, not an effect; consumers must name the effect")
        consumers = sorted(cid for cid, row in rows.items()
                           if "python.source.symbol_index" in (row.get("requires") or []))
        self.assertTrue(consumers, "at least one row must consume the published effect")
        self.assertIn("software.repair.choreograph.crossfile.v1", consumers,
                      "the crossfile choreographer must be able to bind its index")
        for cid in consumers:
            self.assertNotIn("python.source.symbols.index.ast",
                             rows[cid].get("requires") or [],
                             f"{cid} still requires the capability id")


if __name__ == "__main__":
    unittest.main()
