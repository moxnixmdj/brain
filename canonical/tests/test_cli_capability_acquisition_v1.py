#!/usr/bin/env python3
"""Learning a program must end in proof, not in a well-mannered guess.

cli_contract_inference hands back CANDIDATE_REQUIRES_EFFECT_VERIFICATION --
honest, and useless on its own. Acquisition runs it and checks the effect.

These tests use real executables created on disk, because the only way to know
a program does what its help text claims is to run it.
"""

from __future__ import annotations

import json
import os
import pathlib
import stat
import tempfile
import textwrap
import unittest

from canonical.runtime import cli_capability_acquisition_v1 as acq

PNG_MAGIC = "89504e470d0a1a0a"


class _BinaryFactory:
    """Real executables, written to disk, that behave like real tools."""

    def __init__(self, tmp: str) -> None:
        self.tmp = pathlib.Path(tmp)

    def make(self, name: str, body: str) -> str:
        path = self.tmp / name
        path.write_text("#!/usr/bin/env python3\n" + textwrap.dedent(body),
                        encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        return str(path)

    def probe_for(self, path: str, args=("--help",)) -> dict:
        import subprocess
        r = subprocess.run([path, *args], capture_output=True, timeout=30)
        return {"executables": [{"executable": path, "help_attempts": [
            {"text": (r.stdout + r.stderr).decode("utf-8", "replace")}]}]}


class IsolatedStores:
    """Keep acquisition's side effects out of the real memory and ledger.

    acquire() remembers what it learned and notes gaps on failure, both to the
    real default state. Left alone, that pollutes the ledger tests, which then
    see gaps they never created -- a test that fails depending on which other
    tests ran first.
    """

    def _isolate(self) -> None:
        from canonical.runtime import associative_memory_v1 as mem
        from canonical.runtime import ignorance_ledger_v1 as led
        self.mem, self.led = mem, led
        self._mp, self._lp = mem.DEFAULT_STATE, led.DEFAULT_STATE
        self.mp = os.path.join(self.tmp, "mem.json")
        self.lp = os.path.join(self.tmp, "ledger.json")
        mem.DEFAULT_STATE, led.DEFAULT_STATE = self.mp, self.lp

    def _unisolate(self) -> None:
        self.mem.DEFAULT_STATE, self.led.DEFAULT_STATE = self._mp, self._lp


class AcquisitionTests(IsolatedStores, unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="brain-cli-acq-test-")
        self.bin = _BinaryFactory(self.tmp)
        self._isolate()

    def tearDown(self) -> None:
        self._unisolate()
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    # --- the loop closes ------------------------------------------------------

    def test_a_program_that_does_what_it_says_is_acquired(self):
        exe = self.bin.make("honest", """
            import sys
            a = sys.argv[1:]
            if "--help" in a:
                print("Usage: honest [options]")
                print("  -o, --output=FILE     Send output to FILE")
                print("  -d, --data=DATA       Data content to encode")
                print("  Supported formats: PNG.")
                sys.exit(0)
            out, data = None, "x"
            for i, t in enumerate(a):
                if t in ("-o", "--output"): out = a[i+1]
                if t in ("-d", "--data"): data = a[i+1]
            if out:
                open(out, "wb").write(bytes.fromhex("89504e470d0a1a0a") + data.encode())
        """)
        r = acq.acquire(self.bin.probe_for(exe), "encode text into out.png")
        self.assertEqual(r["status"], acq.PASS, json.dumps(r.get("attempts"), default=str)[:300])
        self.assertTrue(r["verified"])
        self.assertEqual(r["output_prefix_hex"], PNG_MAGIC)
        self.assertEqual(r["evidence"]["verified_against"], "magic")

    def test_verification_reads_the_actual_bytes(self):
        """It must check the file, not trust the exit code."""
        exe = self.bin.make("zeroexit", """
            import sys
            if "--help" in sys.argv:
                print("Usage: zeroexit [options]")
                print("  -o, --output=FILE  Send output to FILE")
                print("  -d, --data=DATA    Data content")
                print("  Supported formats: PNG.")
                sys.exit(0)
            sys.exit(0)   # claims success, writes nothing
        """)
        r = acq.acquire(self.bin.probe_for(exe), "encode into out.png")
        self.assertNotEqual(r["status"], acq.PASS)
        self.assertFalse(r["verified"])

    def test_a_program_that_lies_about_its_format_is_rejected(self):
        exe = self.bin.make("liar", """
            import sys
            a = sys.argv[1:]
            if "--help" in a:
                print("Usage: liar [options]")
                print("  -o, --output=FILE  Send output to FILE")
                print("  -d, --data=DATA    Data content")
                print("  Supported formats: PNG.")
                sys.exit(0)
            for i, t in enumerate(a):
                if t in ("-o", "--output"):
                    open(a[i+1], "wb").write(b"NOT A PNG AT ALL")
        """)
        r = acq.acquire(self.bin.probe_for(exe), "encode into out.png")
        self.assertEqual(r["status"], acq.NOT_VERIFIED)
        self.assertIn("MAGIC_MISMATCH", json.dumps(r["attempts"]))

    def test_it_tries_alternatives_instead_of_stopping_at_one_guess(self):
        """The short flag fails; the long one works. It should find the long one.

        A fixed sequence would try one thing and give up. This is the machine
        testing its own hypotheses against reality.
        """
        exe = self.bin.make("picky", """
            import sys
            a = sys.argv[1:]
            if "--help" in a:
                print("Usage: picky [options]")
                print("  -o, --output=FILE  (accepted, writes nothing)")
                print("  --outfile=FILE     Send output to FILE")
                print("  -d, --data=DATA    Data content")
                print("  Supported formats: PNG.")
                sys.exit(0)
            for i, t in enumerate(a):
                if t == "--outfile" or t.startswith("--outfile="):
                    p = a[i+1] if t == "--outfile" else t.split("=", 1)[1]
                    open(p, "wb").write(bytes.fromhex("89504e470d0a1a0a") + b"ok")
        """)
        r = acq.acquire(self.bin.probe_for(exe), "encode text into out.png")
        self.assertEqual(r["status"], acq.PASS, json.dumps(r.get("attempts"), default=str)[:300])
        self.assertTrue(len(r["evidence"]["attempts"]) >= 1)

    # --- refusing ---------------------------------------------------------------

    def test_unrunnable_program_is_reported_not_guessed(self):
        probe = {"executables": [{"executable": "definitely-not-a-real-binary-xyz",
                                  "help_attempts": [{"text":
                                      "Usage: x [options]\n"
                                      "  -o, --output=FILE  Send output to FILE\n"
                                      "  -d, --data=DATA    Data content\n"
                                      "  Supported formats: PNG.\n"}]}]}
        r = acq.acquire(probe, "encode into out.png")
        self.assertEqual(r["status"], acq.UNRUNNABLE)

    def test_no_inferable_contract_is_reported(self):
        r = acq.acquire({"executables": [{"executable": "ls",
                                          "help_attempts": [{"text": ""}]}]},
                        "do something")
        self.assertEqual(r["status"], acq.NO_CONTRACT)

    # --- banking ----------------------------------------------------------------

    def test_verified_acquisition_becomes_an_invocable_capability(self):
        exe = self.bin.make("honest2", """
            import sys
            a = sys.argv[1:]
            if "--help" in a:
                print("Usage: honest2 [options]")
                print("  -o, --output=FILE     Send output to FILE")
                print("  -d, --data=DATA       Data content to encode")
                print("  Supported formats: PNG.")
                sys.exit(0)
            out, data = None, "x"
            for i, t in enumerate(a):
                if t in ("-o", "--output"): out = a[i+1]
                if t in ("-d", "--data"): data = a[i+1]
            if out:
                open(out, "wb").write(bytes.fromhex("89504e470d0a1a0a") + data.encode())
        """)
        r = acq.acquire(self.bin.probe_for(exe), "encode text into out.png")
        entry = acq.to_registry_entry(r, "acquired.fake_png")
        self.assertIsNotNone(entry)
        self.assertEqual(entry["id"], "acquired.fake_png")
        self.assertEqual(entry["action_template"]["expect"]["value"], True)
        self.assertIn("${input.output_path}", json.dumps(entry["action_template"]["args"]["argv"]))

    def test_unverified_acquisition_is_never_banked(self):
        entry = acq.to_registry_entry({"status": acq.NOT_VERIFIED, "verified": False},
                                      "nope")
        self.assertIsNone(entry)

    def test_even_verified_acquisition_is_not_called_semantically_proven(self):
        """Running once on a probe input proves it runs. Nothing more."""
        exe = self.bin.make("h3", """
            import sys
            a = sys.argv[1:]
            if "--help" in a:
                print("Usage: h3 [options]")
                print("  -o, --output=FILE  Send output to FILE")
                print("  -d, --data=DATA    Data")
                print("  Supported formats: PNG.")
                sys.exit(0)
            for i, t in enumerate(a):
                if t in ("-o", "--output"):
                    open(a[i+1], "wb").write(bytes.fromhex("89504e470d0a1a0a") + b"ok")
        """)
        r = acq.acquire(self.bin.probe_for(exe), "encode into out.png")
        self.assertEqual(r["evidence"]["authority"],
                         "EFFECT_VERIFIED_NOT_SEMANTICALLY_PROVEN")


if __name__ == "__main__":
    unittest.main()


class WiringTests(unittest.TestCase):
    """Learned capability is remembered; a failure becomes a known gap."""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="brain-cli-acq-wire-")
        self.bin = _BinaryFactory(self.tmp)
        from canonical.runtime import associative_memory_v1 as mem
        from canonical.runtime import ignorance_ledger_v1 as led
        self.mem, self.led = mem, led
        self._mp, self._lp = mem.DEFAULT_STATE, led.DEFAULT_STATE
        fd, self.mp = tempfile.mkstemp(suffix=".json"); os.close(fd); os.unlink(self.mp)
        fd, self.lp = tempfile.mkstemp(suffix=".json"); os.close(fd); os.unlink(self.lp)
        mem.DEFAULT_STATE, led.DEFAULT_STATE = self.mp, self.lp

    def tearDown(self) -> None:
        self.mem.DEFAULT_STATE, self.led.DEFAULT_STATE = self._mp, self._lp
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)
        for f in (self.mp, self.lp):
            try:
                os.unlink(f)
            except OSError:
                pass

    def _honest(self, name="wired"):
        return self.bin.make(name, """
            import sys
            a = sys.argv[1:]
            if "--help" in a:
                print("Usage: %s [options]")
                print("  -o, --output=FILE  Send output to FILE")
                print("  -d, --data=DATA    Data content")
                print("  Supported formats: PNG.")
                sys.exit(0)
            for i, t in enumerate(a):
                if t in ("-o", "--output"):
                    open(a[i+1], "wb").write(bytes.fromhex("89504e470d0a1a0a") + b"ok")
        """.replace("%s", name))

    def test_acquired_capability_is_remembered(self):
        exe = self._honest()
        r = acq.acquire(self.bin.probe_for(exe), "encode text into out.png")
        self.assertEqual(r["status"], acq.PASS)
        hits = self.mem.recall("encode png output", path=self.mp)
        self.assertTrue(hits, "learned capability was not remembered")

    def test_failure_becomes_a_gap_it_knows_about(self):
        exe = self.bin.make("liar2", """
            import sys
            a = sys.argv[1:]
            if "--help" in a:
                print("Usage: liar2 [options]")
                print("  -o, --output=FILE  Send output to FILE")
                print("  -d, --data=DATA    Data content")
                print("  Supported formats: PNG.")
                sys.exit(0)
            for i, t in enumerate(a):
                if t in ("-o", "--output"):
                    open(a[i+1], "wb").write(b"not a png")
        """)
        acq.acquire(self.bin.probe_for(exe), "encode into out.png")
        self.assertGreaterEqual(self.led.stats(path=self.lp)["gaps"], 1)


class RegistrationTests(unittest.TestCase):
    """A learned capability has to become reachable, or learning was theatre."""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="brain-cli-reg-")
        self.bin = _BinaryFactory(self.tmp)
        # a copy of the real registry shape, never the real registry
        from canonical.runtime import capability_type_surface_v1 as ts
        self.real = pathlib.Path(ts.REGISTRY)
        doc = json.loads(self.real.read_text(encoding="utf-8"))
        self.reg = pathlib.Path(self.tmp) / "REG.json"
        self.reg.write_text(json.dumps(doc), encoding="utf-8")

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _acquired(self, name="regme"):
        exe = self.bin.make(name, """
            import sys
            a = sys.argv[1:]
            if "--help" in a:
                print("Usage: REGM [options]")
                print("  -o, --output=FILE  Send output to FILE")
                print("  -d, --data=DATA    Data content")
                print("  Supported formats: PNG.")
                sys.exit(0)
            for i, t in enumerate(a):
                if t in ("-o", "--output"):
                    open(a[i+1], "wb").write(bytes.fromhex("89504e470d0a1a0a") + b"ok")
        """.replace("REGM", name))
        return acq.acquire(self.bin.probe_for(exe), "encode text into out.png")

    def test_verified_acquisition_becomes_reachable(self):
        """The last mile: it shows up where capabilities are looked up."""
        from canonical.runtime import capability_type_surface_v1 as ts
        r = self._acquired()
        self.assertEqual(r["status"], acq.PASS)
        out = acq.register(r, "acquired.regme", registry_path=str(self.reg))
        self.assertTrue(out["registered"], out)

        doc = json.loads(self.reg.read_text())
        self.assertIn("acquired.regme", doc["capabilities"])
        # and the surface can now derive a signature for it, which is what
        # makes it invocable rather than merely present
        sigs = ts.signatures(doc["capabilities"])
        self.assertIn("acquired.regme", sigs)

    def test_it_refuses_to_overwrite_an_existing_capability(self):
        """Growth must not be able to destroy what already worked."""
        r = self._acquired()
        acq.register(r, "acquired.regme", registry_path=str(self.reg))
        again = acq.register(r, "acquired.regme", registry_path=str(self.reg))
        self.assertFalse(again["registered"])
        self.assertEqual(again["reason"], "CAPABILITY_ALREADY_EXISTS")

    def test_overwrite_requires_saying_so_explicitly(self):
        r = self._acquired()
        acq.register(r, "acquired.regme", registry_path=str(self.reg))
        out = acq.register(r, "acquired.regme", registry_path=str(self.reg),
                           overwrite=True)
        self.assertTrue(out["registered"])

    def test_unverified_is_never_registered(self):
        out = acq.register({"status": acq.NOT_VERIFIED, "verified": False}, "nope",
                           registry_path=str(self.reg))
        self.assertFalse(out["registered"])
        self.assertIn("NOT_VERIFIED", out["reason"])

    def test_registry_is_left_untouched_on_refusal(self):
        before = self.reg.read_text(encoding="utf-8")
        acq.register({"status": acq.NOT_VERIFIED, "verified": False}, "nope",
                     registry_path=str(self.reg))
        self.assertEqual(self.reg.read_text(encoding="utf-8"), before)

    def test_the_real_registry_is_not_modified_by_any_test(self):
        """Guard against the obvious catastrophic mistake."""
        self.assertEqual(json.loads(self.real.read_text())["capabilities"]
                         .get("acquired.regme"), None)


class NoDocumentationTests(IsolatedStores, unittest.TestCase):
    """Programs that will not say how to use themselves.

    Reading help is one way to learn. Failing to read help is not a reason to
    give up on a program that is sitting on the disk and can be run.
    """

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="brain-cli-nodoc-")
        self.bin = _BinaryFactory(self.tmp)
        self._isolate()

    def tearDown(self) -> None:
        self._unisolate()
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _probe_for(self, exe: str) -> dict:
        return {"executables": [{"executable": exe, "help_attempts": [{"text": ""}]}]}

    def test_a_program_with_no_help_is_still_learned(self):
        """Previously: CLI_HELP_CONTRACT_TEXT_REQUIRED, and nothing learned."""
        exe = self.bin.make("mute", """
            import sys
            a = sys.argv[1:]
            for i, t in enumerate(a):
                if t == "-o":
                    open(a[i+1], "wb").write(bytes.fromhex("89504e470d0a1a0a") + b"ok")
        """)
        r = acq.acquire(self._probe_for(exe), "encode text into out.png")
        self.assertEqual(r["status"], acq.PASS, json.dumps(r, default=str)[:300])
        self.assertEqual(r["route"], "empirical")
        self.assertIn("observed_effect", json.dumps(r["evidence"]))

    def test_it_stays_honest_about_how_it_knows(self):
        exe = self.bin.make("mute2", """
            import sys
            a = sys.argv[1:]
            for i, t in enumerate(a):
                if t == "-o":
                    open(a[i+1], "wb").write(bytes.fromhex("89504e470d0a1a0a") + b"ok")
        """)
        r = acq.acquire(self._probe_for(exe), "encode text into out.png")
        self.assertEqual(r["evidence"]["authority"],
                         "EFFECT_OBSERVED_NOT_SEMANTICALLY_PROVEN")

    def test_a_program_that_cannot_be_driven_is_reported_not_invented(self):
        exe = self.bin.make("inert2", """
            import sys
            sys.exit(0)
        """)
        r = acq.acquire(self._probe_for(exe), "encode text into out.png")
        self.assertEqual(r["status"], acq.NO_CONTRACT)
        self.assertTrue(r.get("tried_empirically"))

    def test_help_route_is_still_preferred_when_it_works(self):
        """Reading is cheaper than trying; the fallback must not replace it."""
        exe = self.bin.make("documented", """
            import sys
            a = sys.argv[1:]
            if "--help" in a:
                print("Usage: documented [options]")
                print("  -o, --output=FILE  Send output to FILE")
                print("  -d, --data=DATA    Data content")
                print("  Supported formats: PNG.")
                sys.exit(0)
            for i, t in enumerate(a):
                if t in ("-o", "--output"):
                    open(a[i+1], "wb").write(bytes.fromhex("89504e470d0a1a0a") + b"ok")
        """)
        r = acq.acquire(self.bin.probe_for(exe), "encode text into out.png")
        self.assertEqual(r["route"], "help_text")


class NoOutputFormatTests(IsolatedStores, unittest.TestCase):
    """A goal that never says what it wants cannot be verified against anything."""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="brain-cli-nofmt-")
        self.bin = _BinaryFactory(self.tmp)
        self._isolate()

    def tearDown(self) -> None:
        self._unisolate()
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_a_goal_naming_no_output_is_refused(self):
        """Otherwise any program that prints anything counts as learned --
        ls would be acquired as a capability."""
        probe_doc = {"executables": [{"executable": "ls",
                                      "help_attempts": [{"text": ""}]}]}
        r = acq.acquire(probe_doc, "do something")
        self.assertEqual(r["status"], acq.NO_CONTRACT)
        self.assertIn("NO_OUTPUT_FORMAT", r["reason"])

    def test_a_goal_naming_an_output_is_still_learned(self):
        exe = self.bin.make("quiet", """
            import sys
            a = sys.argv[1:]
            for i, t in enumerate(a):
                if t == "-o":
                    open(a[i+1], "wb").write(bytes.fromhex("89504e470d0a1a0a") + b"ok")
        """)
        r = acq.acquire({"executables": [{"executable": exe,
                                          "help_attempts": [{"text": ""}]}]},
                        "encode text into out.png")
        self.assertEqual(r["status"], acq.PASS)
