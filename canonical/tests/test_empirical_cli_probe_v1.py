#!/usr/bin/env python3
"""Learning a program that will not tell you how to use it.

cli_contract_inference needs structured help. Plenty of programs have none,
and every one of those ended in CLI_HELP_CONTRACT_TEXT_REQUIRED -- the machine
learning nothing about a program sitting right there on the disk.

These are real executables written to disk, none of which print any help.
"""

from __future__ import annotations

import os
import pathlib
import stat
import tempfile
import textwrap
import unittest

from canonical.runtime import empirical_cli_probe_v1 as probe


class _Makes:
    def __init__(self, tmp: str) -> None:
        self.tmp = pathlib.Path(tmp)

    def make(self, name: str, body: str) -> str:
        p = self.tmp / name
        p.write_text("#!/usr/bin/env python3\n" + textwrap.dedent(body),
                     encoding="utf-8")
        p.chmod(p.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        return str(p)


class EmpiricalProbeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="brain-empirical-test-")
        self.m = _Makes(self.tmp)
        from canonical.runtime import ignorance_ledger_v1 as led
        self.led = led
        self._real = led.DEFAULT_STATE
        self.led.DEFAULT_STATE = os.path.join(self.tmp, "ledger.json")

    def tearDown(self) -> None:
        self.led.DEFAULT_STATE = self._real
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    # --- it learns without documentation ---------------------------------------

    def test_a_program_with_no_help_at_all_is_learned(self):
        """The case that was previously impossible."""
        exe = self.m.make("silent", """
            import sys
            a = sys.argv[1:]
            # no --help handling whatsoever
            for i, t in enumerate(a):
                if t == "-o":
                    open(a[i+1], "wb").write(bytes.fromhex("89504e470d0a1a0a") + b"payload")
        """)
        r = probe.probe(exe, suffix=".png")
        self.assertEqual(r["status"], probe.PASS, str(r.get("trials"))[:200])
        self.assertEqual(r["output_flag"], "-o")
        self.assertIn("${input.output_path}", r["argv_template"])

    def test_a_program_that_writes_to_stdout_is_learned(self):
        """No output flag exists; the effect is on stdout."""
        exe = self.m.make("toterminal", """
            import sys
            sys.stdout.write("hello from the program\\n")
        """)
        r = probe.probe(exe, suffix=".txt")
        self.assertEqual(r["status"], probe.PASS, str(r.get("trials"))[:200])

    def test_the_contract_is_derived_from_effect_not_claims(self):
        """It runs and produces a PNG, so it is learned -- but the label must
        say what that does and does not prove. Producing bytes once is not the
        same as being correct for real work."""
        exe = self.m.make("plain", """
            import sys
            a = sys.argv[1:]
            for i, t in enumerate(a):
                if t == "-o":
                    open(a[i+1], "wb").write(bytes.fromhex("89504e470d0a1a0a") + b"x")
        """)
        r = probe.probe(exe, suffix=".png")
        self.assertEqual(r["status"], probe.PASS)
        self.assertEqual(r["authority"], "EFFECT_OBSERVED_NOT_SEMANTICALLY_PROVEN")

    # --- refusing ---------------------------------------------------------------

    def test_a_program_that_does_nothing_is_not_learned(self):
        exe = self.m.make("inert", """
            import sys
            sys.exit(0)
        """)
        r = probe.probe(exe, suffix=".png")
        self.assertEqual(r["status"], probe.NO_EFFECT)
        self.assertTrue(r["trials"])

    def test_missing_executable_is_reported(self):
        r = probe.probe("definitely-not-real-binary-xyz", suffix=".png")
        self.assertIn("NOT_FOUND", r["status"])

    def test_it_does_not_claim_success_on_a_zero_byte_file(self):
        exe = self.m.make("emptyfile", """
            import sys
            a = sys.argv[1:]
            for i, t in enumerate(a):
                if t == "-o":
                    open(a[i+1], "wb").close()
        """)
        r = probe.probe(exe, suffix=".png")
        self.assertEqual(r["status"], probe.NO_EFFECT)

    # --- the ordering is learned, not written -----------------------------------

    def test_a_working_pattern_is_tried_earlier_next_time(self):
        """Across programs, it should get better at guessing."""
        exe = self.m.make("uses_outfile", """
            import sys
            a = sys.argv[1:]
            for i, t in enumerate(a):
                if t == "--outfile":
                    open(a[i+1], "wb").write(bytes.fromhex("89504e470d0a1a0a") + b"x")
        """)
        before = probe._ordered_patterns()
        r = probe.probe(exe, suffix=".png")
        self.assertEqual(r["status"], probe.PASS, str(r.get("trials"))[:200])
        after = probe._ordered_patterns()
        pos_before = before.index(("--outfile", "positional"))
        pos_after = after.index(("--outfile", "positional"))
        self.assertLessEqual(pos_after, pos_before)

    def test_patterns_are_never_lost(self):
        order = probe._ordered_patterns()
        self.assertEqual(sorted(order), sorted(probe.PATTERNS))

    def test_probe_survives_a_broken_ledger(self):
        self.led.DEFAULT_STATE = "/nonexistent/broken/path.json"
        try:
            self.assertEqual(probe._ordered_patterns(), list(probe.PATTERNS))
        finally:
            self.led.DEFAULT_STATE = os.path.join(self.tmp, "ledger.json")


if __name__ == "__main__":
    unittest.main()
