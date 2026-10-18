#!/usr/bin/env python3
"""The machine must be able to learn to use a program it has never seen.

This is the path from "70 things it was born with" to "anything on the
computer". A fixed menu can never be everything, so the way the machine does a
new thing is to meet an unknown program and infer a usable contract from the
program's own help text -- instantly, with no model in the loop.

These tests cover the part that was silently broken: naming a destination the
natural way.

    "encode text into out.png"

The path pattern required a slash, so a bare filename matched nothing, the
output path came back empty, and the machine concluded the output format was
unverifiable and gave up -- on the most common way anyone states a task. It
could use /tmp/out.png but not out.png, which is not "anything".
"""

from __future__ import annotations

import unittest

from canonical.runtime import cli_contract_inference as ci


class _FakePngCapability(unittest.TestCase):
    """A program that declares an output flag and a format, like zint does."""

    HELP = (
        "Usage: fakepng [options]\n"
        "  -o, --output=FILE     Send output to FILE. Default is out.png\n"
        "  -d, --data=DATA       Data content to encode\n"
        "  Supported formats: PNG.\n"
    )

    def probe(self) -> dict:
        return {"executables": [{"executable": "fakepng",
                                 "help_attempts": [{"text": self.HELP}]}]}

    def infer(self, goal: str) -> dict:
        return ci.infer_contract(self.probe(), goal)


class BareFilenameTests(_FakePngCapability):
    """The regression: a destination named without a directory."""

    def test_bare_filename_is_accepted(self):
        """'into out.png' must work. It did not, and that is the whole bug."""
        c = self.infer("encode text into out.png")
        self.assertEqual(c["output_prefix_hex"], "89504e470d0a1a0a")
        self.assertIn("${input.output_path}", c["argv_template"])

    def test_slashed_path_still_works(self):
        """No regression on the case that already worked."""
        c = self.infer("encode text into /tmp/out.png")
        self.assertEqual(c["output_prefix_hex"], "89504e470d0a1a0a")

    def test_relative_directory_works(self):
        c = self.infer("encode text into build/out.png")
        self.assertEqual(c["output_prefix_hex"], "89504e470d0a1a0a")

    def test_destination_is_chosen_by_cue_not_position(self):
        """With an input and an output named, the destination is the one after
        'into', not merely the last path mentioned."""
        c = self.infer("encode notes.txt into out.png")
        self.assertEqual(c["output_prefix_hex"], "89504e470d0a1a0a")

    def test_contract_carries_a_full_invocation(self):
        c = self.infer("encode text into out.png")
        self.assertEqual(c["executable"], "fakepng")
        self.assertIn("-o", c["argv_template"])
        self.assertIn("-d", c["argv_template"])
        self.assertEqual(set(c["required_inputs"]), {"text", "output_path"})

    def test_contract_is_a_candidate_not_a_fact(self):
        """It must be verified before it is trusted. Nothing self-certifies."""
        c = self.infer("encode text into out.png")
        self.assertEqual(c["status"], "CANDIDATE_REQUIRES_EFFECT_VERIFICATION")


class FailClosedTests(_FakePngCapability):
    """Refusing is correct. The machine must not invent a contract."""

    def test_unverifiable_format_is_refused(self):
        with self.assertRaises(ci.ContractInferenceFailure):
            self.infer("do something with the data")

    def test_format_the_program_does_not_declare_is_refused(self):
        """.txt is a known text format, but this program never claims to write
        text, so inferring a text contract from it would be invention."""
        with self.assertRaises(ci.ContractInferenceFailure):
            self.infer("encode text into out.txt")

    def test_no_help_text_is_refused(self):
        probe = {"executables": [{"executable": "x", "help_attempts": [{"text": ""}]}]}
        with self.assertRaises(ci.ContractInferenceFailure):
            ci.infer_contract(probe, "encode into out.png")

    def test_two_paths_and_no_cue_stay_unresolved(self):
        """Guessing which of two paths is the destination would produce a
        confident contract for possibly the wrong thing."""
        with self.assertRaises(ci.ContractInferenceFailure):
            self.infer("convert out.png result.txt")


if __name__ == "__main__":
    unittest.main()
