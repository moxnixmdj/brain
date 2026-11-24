#!/usr/bin/env python3
"""A store can be an effect. The oracle must be able to read it back.

Every effect this system could verify before today was a byte stream. A database
row, an accessibility tree, a DOM are the same question in a different material:
did the world end up holding what the goal asked for? These tests pin the second
shape, and the two things that are easy to get wrong:

  * the reader must be schema-blind -- it is told nothing about table or column
    names and has to find a reading that reproduces the source;
  * a renamed source must still bind, which means the bound role has to reach the
    action rather than stopping at the plan.
"""
from __future__ import annotations

import pathlib
import sqlite3
import subprocess
import tempfile
import unittest

from canonical.runtime import computer_env_v1 as cenv
from canonical.runtime import effect_oracle_v1 as oracle

SOURCE = b"one line\nsecond line\n"


class StateShapeTests(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="state-shape-"))
        (self.root / "input.txt").write_bytes(SOURCE)

    def _store(self, name, table, column, values):
        path = self.root / name
        connection = sqlite3.connect(path)
        connection.execute('CREATE TABLE "%s"("%s")' % (table, column))
        connection.executemany('INSERT INTO "%s" VALUES (?)' % table,
                               [(value,) for value in values])
        connection.commit()
        connection.close()
        return path

    def test_one_row_per_line_reproduces_the_source(self):
        self._store("out.db", "notes", "body", ["one line", "second line"])
        verdict = oracle.verify_state(self.root, "out.db", "input.txt")
        self.assertEqual(verdict["verdict"], oracle.EFFECT_VERIFIED, verdict)
        self.assertEqual(verdict["reading"]["table"], "notes")

    def test_one_row_holding_everything_also_reproduces_the_source(self):
        self._store("out.db", "all_of_it", "text", ["one line\nsecond line"])
        verdict = oracle.verify_state(self.root, "out.db", "input.txt")
        self.assertEqual(verdict["verdict"], oracle.EFFECT_VERIFIED, verdict)

    def test_the_reader_knows_no_schema_and_still_finds_it(self):
        self._store("out.db", "zzz_unlikely", "qqq_unknown", ["one line", "second line"])
        verdict = oracle.verify_state(self.root, "out.db", "input.txt")
        self.assertEqual(verdict["verdict"], oracle.EFFECT_VERIFIED, verdict)
        self.assertEqual(verdict["reading"]["column"], "qqq_unknown")

    def test_a_store_that_does_not_hold_the_source_is_refused(self):
        self._store("out.db", "notes", "body", ["something else entirely"])
        verdict = oracle.verify_state(self.root, "out.db", "input.txt")
        self.assertEqual(verdict["verdict"], oracle.WRONG_STATE, verdict)

    def test_a_file_that_is_not_a_store_is_not_judged_as_one(self):
        (self.root / "out.db").write_bytes(b"plain bytes, no store here")
        verdict = oracle.verify_state(self.root, "out.db", "input.txt")
        self.assertEqual(verdict["verdict"], oracle.NO_STATE_READER, verdict)

    def test_the_shape_is_read_off_the_artifact_not_its_name(self):
        self._store("out.db", "notes", "body", ["one line", "second line"])
        reached, verdict = oracle.verify_any(self.root, "out.db", "input.txt")
        self.assertTrue(reached, verdict)
        self.assertEqual(verdict["shape"], "state")

    def test_a_compressed_artifact_is_still_judged_as_bytes(self):
        blob = subprocess.run(["gzip", "-c", "input.txt"], cwd=str(self.root),
                              capture_output=True).stdout
        (self.root / "out.gz").write_bytes(blob)
        reached, verdict = oracle.verify_any(self.root, "out.gz", "input.txt")
        self.assertTrue(reached, verdict)
        self.assertEqual(verdict["shape"], "bytes")


class RolesReachTheActionTests(unittest.TestCase):
    """A contract that binds a source and lets the action choose is not a contract."""

    def test_a_two_parameter_action_receives_the_bound_roles(self):
        root = pathlib.Path(tempfile.mkdtemp(prefix="roles-"))
        (root / "report.txt").write_bytes(b"renamed\n")
        seen = {}

        def action(env, roles=None):
            seen.update(roles or {})
            return True

        env = cenv.ComputerEnv(root=root, seed={"report.txt": b"renamed\n"})
        env.register([("act", action)])
        self.assertTrue(env.act("act", roles={"source": "report.txt",
                                              "output": "out.db"}))
        self.assertEqual(seen, {"source": "report.txt", "output": "out.db"})

    def test_a_one_parameter_action_is_called_exactly_as_before(self):
        root = pathlib.Path(tempfile.mkdtemp(prefix="roles-old-"))
        env = cenv.ComputerEnv(root=root, seed={"input.txt": b"x\n"})
        calls = []
        env.register([("act", lambda env: calls.append(True) or True)])
        self.assertTrue(env.act("act", roles={"source": "input.txt"}))
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
