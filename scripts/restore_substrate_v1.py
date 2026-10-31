#!/usr/bin/env python3
"""Restore the software-engineering substrate in one command, and prove it landed.

Why this exists rather than a single requirements file: ``pip`` puts the WHOLE install set into
``--require-hashes`` mode as soon as any line carries a hash, so the pinned kernel manifest and the
unhashed review tools cannot be installed from one file.  Measured 2026-10-31 on ``5ad1222``: the
bootstrap mixed them, ``pip install -r substrate-requirements.txt`` refused outright, and the image
went from 6 of 10 tools to 0 of 10.  Two steps, one entry point.

Why it exists at all: pip installs outside ``/home/user`` evaporate between turns.  The repository
recorded that twice ("tree_sitter generation mismatch broke 3 tree-sitter capabilities"; "missing
mypy/ruff/bandit degraded the chain gates to PASS_BASELINE_ONLY") and then left the restore step as
a comment.  A comment cannot run, so the matrix silently measured a smaller machine than the one
the registry describes.  This script runs, verifies, and prints the verdict the census reads.

Usage:
    python3 scripts/restore_substrate_v1.py            # install what is missing, then verify
    python3 scripts/restore_substrate_v1.py --check     # verify only; exit 1 if anything is absent
"""
from __future__ import annotations

import argparse
import importlib.util
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
KERNEL_MANIFEST = ROOT / "requirements/software_engineering_kernel_v1.txt"
REVIEW_TOOLS = ROOT / "substrate-requirements.txt"

# The names the capability matrix measures by name, plus the three packages whose absence used to
# be invisible.  A tool that is absent makes a lane unmeasurable rather than red, which is how the
# gap stayed hidden; so absence is a failure of THIS script, loudly.
REQUIRED_MODULES = (
    ("pytest", "pytest"),
    ("hypothesis", "hypothesis"),
    ("tree_sitter", "tree-sitter"),
    ("tree_sitter_languages", "tree-sitter-languages"),
    ("coverage", "coverage"),
    ("mypy", "mypy"),
    ("ruff", "ruff"),
    ("bandit", "bandit"),
    ("crosshair", "crosshair-tool"),
    ("z3", "z3-solver"),
)
REQUIRED_BINARIES = ("git", "gcc", "g++", "make", "node", "npm")
RETURNCODE_OK = 0


def present() -> tuple[list[str], list[str]]:
    """(installed, missing) by import name, never by version."""
    good, missing = [], []
    for module, _package in REQUIRED_MODULES:
        (good if importlib.util.find_spec(module) else missing).append(module)
    return good, missing


def install(requirements: pathlib.Path) -> None:
    print("INSTALL %s" % requirements.relative_to(ROOT))
    subprocess.run([sys.executable, "-m", "pip", "install", "--break-system-packages",
                    "--quiet", "-r", str(requirements)], cwd=ROOT, check=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify only, install nothing")
    ns = ap.parse_args()

    good, missing = present()
    if missing and not ns.check:
        # Sequential on purpose: the manifest is hashed, the review tools are not.
        install(KERNEL_MANIFEST)
        install(REVIEW_TOOLS)
        good, missing = present()

    binaries = [b for b in REQUIRED_BINARIES if not _which(b)]
    print("SUBSTRATE  modules_present=%d/%d  binaries_missing=%s"
          % (len(good), len(REQUIRED_MODULES), ",".join(binaries) or "none"))
    if missing:
        print("  modules_missing:", ",".join(missing))
        print("  verdict: SUBSTRATE_INCOMPLETE -- lanes that need these measure an ENVIRONMENT gap,")
        print("           not a capability gap, and the matrix reports them as unmeasurable.")
        return 1
    # Load the kernel's own declared identity last: it is the authority on the parser generation,
    # and a mismatched generation is exactly the failure this script exists to prevent.
    sys.path.insert(0, str(ROOT))
    from canonical.runtime import tree_sitter_swe_kernel_v1 as kernel
    import importlib.metadata as md
    have = md.version("tree-sitter")
    want = kernel.SUBSTRATE["tree_sitter"]
    print("  parser: installed=%s expected=%s %s"
          % (have, want, "MATCH" if have == want else "MISMATCH"))
    if have != want:
        print("  verdict: SUBSTRATE_INCOMPLETE -- the kernel was harvested against %s" % want)
        return 1
    print("  verdict: SUBSTRATE_READY")
    return RETURNCODE_OK


def _which(binary: str) -> str | None:
    import shutil
    return shutil.which(binary)


if __name__ == "__main__":
    raise SystemExit(main())
