"""The declared substrate must be the verified substrate.

A bootstrap file that pins a different parser generation than the one the capabilities were
harvested and verified against is not a convenience: it is a silent capability loss.  Measured
2026-10-31 on `1f2f160`, installing `substrate-requirements.txt` alone:

    tree_sitter 0.21.3   where tree_sitter_swe_kernel_v1.SUBSTRATE names 0.20.4
    tools_present 6/10   so the matrix reported the toolchain lane unmeasurable
    matrix 22 REAL       where the pinned kernel manifest yields 24 REAL

and the repository's own comment in that file records the same failure twice before ("tree_sitter
generation mismatch broke 3 tree-sitter capabilities").  A note in a comment cannot fail, so the
agreement is a test.

The oracle is independent of this repository's prose: the kernel constant is compared against the
text of the manifest, and the manifest is compared against itself for the requirement that pipping
it would actually satisfy.  No installed version is read, because the image may hold any of them.
"""
from __future__ import annotations

import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import tree_sitter_swe_kernel_v1 as kernel  # noqa: E402

KERNEL_MANIFEST = ROOT / "requirements/software_engineering_kernel_v1.txt"
BOOTSTRAP = ROOT / "substrate-requirements.txt"
MATRIX_TOOLS = ("mypy", "ruff", "bandit", "coverage")


def _pins(path: pathlib.Path) -> dict[str, str]:
    """name -> version, from a pip requirements file (``-r`` lines and hashes ignored)."""
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip().rstrip("\\").strip()
        match = re.match(r"^([A-Za-z0-9_.\-]+)==([^\s;]+)", line)
        if match:
            out[match.group(1).lower().replace("_", "-")] = match.group(2)
    return out


def _includes(path: pathlib.Path) -> list[str]:
    return [ln.split(None, 1)[1].strip() for ln in path.read_text(encoding="utf-8").splitlines()
            if ln.strip().startswith("-r ")]


class TheKernelManifestNamesTheGenerationTheKernelWasVerifiedAgainst(unittest.TestCase):
    def test_parser_pins_equal_the_kernel_substrate_constant(self) -> None:
        pins = _pins(KERNEL_MANIFEST)
        self.assertEqual(pins.get("tree-sitter"), kernel.SUBSTRATE["tree_sitter"], pins)
        self.assertEqual(pins.get("tree-sitter-languages"),
                         kernel.SUBSTRATE["tree_sitter_languages"], pins)

    def test_every_pin_carries_a_hash(self) -> None:
        """A version without a digest is a version a resolver may substitute."""
        text = KERNEL_MANIFEST.read_text(encoding="utf-8")
        blocks = [b for b in text.splitlines() if re.match(r"^[A-Za-z0-9_.\-]+==", b)]
        self.assertGreater(len(blocks), 0)
        for index, line in enumerate(text.splitlines()):
            if not re.match(r"^[A-Za-z0-9_.\-]+==", line):
                continue
            # the hash must appear on this line (continuation) or the next one
            tail = text.splitlines()[index:index + 2]
            self.assertTrue(any("--hash=sha256:" in part for part in tail), line)


class TheBootstrapDoesNotCompeteWithTheManifest(unittest.TestCase):
    def test_the_restore_step_installs_both_files_in_order(self) -> None:
        """One entry point, two files, hashed first.

        pip switches the WHOLE set into --require-hashes mode as soon as any line carries a hash, so a
        single file that mixes the hashed manifest with unhashed tools is not installable at all.
        Measured 2026-10-31 on 5ad1222: that mix made `pip install -r substrate-requirements.txt`
        refuse outright and took the image from 6 of 10 tools to 0 of 10.
        """
        script = (ROOT / "scripts/restore_substrate_v1.py").read_text(encoding="utf-8")
        self.assertIn("software_engineering_kernel_v1.txt", script)
        self.assertIn("substrate-requirements.txt", script)
        self.assertLess(script.index("install(KERNEL_MANIFEST)"),
                        script.index("install(REVIEW_TOOLS)"),
                        "the hashed manifest must be installed before the unhashed tools")

    def test_no_file_mixes_hashed_and_unhashed_requirements(self) -> None:
        for path in (KERNEL_MANIFEST, BOOTSTRAP):
            hashed = any("--hash=" in line for line in path.read_text(encoding="utf-8").splitlines())
            pinned = bool(_pins(path))
            if hashed:
                for line in path.read_text(encoding="utf-8").splitlines():
                    text = line.split("#", 1)[0].strip().rstrip("\\").strip()
                    if not text or text.startswith("-") or "--hash=" in text:
                        continue
                    self.assertRegex(text, r"^[A-Za-z0-9_.\-]+==",
                                     "%s mixes hash mode with an unpinned line: %r" % (path.name, line))
            self.assertTrue(pinned, "%s pins nothing" % path.name)

    def test_bootstrap_pins_nothing_the_manifest_already_pins(self) -> None:
        """Two files may not both decide a version; that is how the drift happened."""
        manifest = _pins(KERNEL_MANIFEST)
        bootstrap = _pins(BOOTSTRAP)
        contested = sorted(set(bootstrap) & set(manifest))
        self.assertEqual(contested, [], "bootstrap re-pins: %s" % contested)
        # A pin in the bootstrap is fine when the manifest does not decide that name; it must be an
        # EXACT pin, because the matrix measures these tools by name and a resolver choosing another
        # major changes a verdict.
        for name, version in bootstrap.items():
            self.assertRegex(version, r"^[0-9]", "bootstrap must pin %s exactly, got %r" % (name, version))

    def test_bootstrap_declares_the_linters_the_matrix_measures(self) -> None:
        text = BOOTSTRAP.read_text(encoding="utf-8").lower()
        for tool in MATRIX_TOOLS:
            self.assertIn(tool, text, "matrix tool %r is not declared by the bootstrap" % tool)


class TheDriftCanBeSeen(unittest.TestCase):
    def test_a_conflicting_pin_is_detected(self) -> None:
        """Falsification: put the old 0.21.3 line back and the rule above must fire."""
        original = BOOTSTRAP.read_text(encoding="utf-8")
        try:
            BOOTSTRAP.write_text(original + "\ntree_sitter==0.21.3\n", encoding="utf-8")
            manifest = _pins(KERNEL_MANIFEST)
            bootstrap = _pins(BOOTSTRAP)
            self.assertTrue(set(bootstrap) & set(manifest), "the conflict must be visible")
        finally:
            BOOTSTRAP.write_text(original, encoding="utf-8")
        self.assertFalse(set(_pins(BOOTSTRAP)) & set(_pins(KERNEL_MANIFEST)))


if __name__ == "__main__":
    unittest.main()
