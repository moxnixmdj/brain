#!/usr/bin/env python3
"""A layer is matched to a program by what the program does, not by its name.

Measured 2026-11-24, both directions of the failure:

  * generous name matching let `tar` stand in for the `gz` layer, and a plain
    tar named `out.gz` came back EFFECT_VERIFIED;
  * strict name matching refuses an alias that really is gzip (a wrapper called
    `zpack`), so a store holding the right contract could never compose.

Both dissolve if the question is behavioural: encode the source, decode the
artifact back to the same bytes, and write the header the format actually has.
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import tempfile
import unittest

from canonical.runtime import effect_oracle_v1 as oracle
from canonical.runtime import lifted_operator_v1 as lifted
from canonical.swe_kernel import perfect_algorithm_v1 as pa

HAS_GZIP = bool(shutil.which("gzip"))
HAS_TAR = bool(shutil.which("tar"))


class ProofTests(unittest.TestCase):
    def setUp(self):
        if not (HAS_GZIP and HAS_TAR):
            self.skipTest("gzip and tar are both needed")
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="layer-proof-test-"))
        (self.root / "input.txt").write_bytes(b"layers are behaviour\n")
        self.scratch = pathlib.Path(tempfile.mkdtemp(prefix="layer-proof-room-"))

    def test_gzip_is_the_machines_implementation_of_the_gz_layer(self):
        proof = oracle.prove_layer("gzip", "gz", self.root / "input.txt", self.scratch)
        self.assertTrue(proof["proved"], proof)

    def test_tar_is_not_the_machines_implementation_of_the_gz_layer(self):
        proof = oracle.prove_layer("tar", "gz", self.root / "input.txt", self.scratch)
        self.assertFalse(proof["proved"], proof)

    def test_an_alias_is_accepted_because_it_behaves_like_the_layer(self):
        alias = self.root / "zpack"
        alias.write_text("#!/bin/sh\nexec gzip \"$@\"\n", encoding="utf-8")
        alias.chmod(0o755)
        proof = oracle.prove_layer(str(alias), "gz", self.root / "input.txt",
                                   self.scratch)
        self.assertTrue(proof["proved"], proof)


class CompositionWithAnAliasTests(unittest.TestCase):
    class Env:
        def __init__(self, root):
            self.root = pathlib.Path(root)

        def reset(self):
            pass

    def setUp(self):
        if not (HAS_GZIP and HAS_TAR):
            self.skipTest("gzip and tar are both needed")
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="alias-compose-"))
        (self.root / "input.txt").write_bytes(b"alias composition\n")
        self.alias = self.root / "zpack"
        self.alias.write_text("#!/bin/sh\nexec gzip \"$@\"\n", encoding="utf-8")
        self.alias.chmod(0o755)

    def _store(self):
        tar_op = lifted.lift(goal="pack into out.tar", goal_family="pack",
                             env_kind="posix_dir", action="tar", program="tar",
                             observation={}, source_name="input.txt",
                             output_name="out.tar", argv=["tar", "-c", "{source}"])
        gz_op = lifted.lift(goal="pack into out.tar.gz", goal_family="pack",
                            env_kind="posix_dir", action="zpack",
                            program=str(self.alias), observation={},
                            source_name="input.txt", output_name="out.tar.gz",
                            argv=[str(self.alias), "-c", "{source}"])
        return {"rules": [tar_op, gz_op]}

    def test_a_contract_named_nothing_like_the_layer_still_composes(self):
        result = pa._compose_from_store(
            self._store(), self.Env(self.root), "pack the input into out.tar.gz",
            contract=lambda env: {"source": "input.txt", "output": "out.tar.gz"})
        self.assertEqual(result["status"], "COMPOSED__EFFECT_VERIFIED_ON_A_NEW_FORMAT",
                         result)
        self.assertEqual(result["effect"]["reader_chain"], ["gzip", "tar"])

    def test_the_verdict_comes_from_the_oracle_not_from_the_names(self):
        result = pa._compose_from_store(
            self._store(), self.Env(self.root), "pack the input into out.tar.gz",
            contract=lambda env: {"source": "input.txt", "output": "out.tar.gz"})
        self.assertTrue((self.root / "out.tar.gz").is_file())
        back = subprocess.run(["gzip", "-dc", "out.tar.gz"], cwd=str(self.root),
                              capture_output=True)
        inner = subprocess.run(["tar", "-xOf", "-"], cwd=str(self.root),
                               input=back.stdout, capture_output=True)
        self.assertEqual(inner.stdout, (self.root / "input.txt").read_bytes())


if __name__ == "__main__":
    unittest.main()
