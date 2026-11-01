#!/usr/bin/env python3
"""A census on an empty substrate is not a census.

Measured 2026-11-01, same commit, same sentences, one variable:

    bare image                      advanced census 36 of 49 served   54-case matrix 42 REAL
    after scripts/restore_substrate_v1.py   36 of 49 served            44 REAL

The two cases that move are ``type_check`` (``PASS_BASELINE_ONLY`` -> ``PASS``) and ``lint``
(``PASS_SYNTAX_ONLY`` -> ``PASS``).  Nothing in the repository changed; a tool was installed.
So two of those 42 "not real" verdicts were facts about the machine, and the board printed
them in the same column as facts about the capability.  A reader cannot tell them apart, and
the fix was a command nobody had to run.

The restore script is one command and it verifies itself.  What was missing is that no
INSTRUMENT read its verdict: ``scripts/restore_substrate_v1.py`` existed, and the census never
called it.  This module is the gate -- it asks the one owner of the measurement
(``scripts/restore_substrate_v1.py:verify``) and refuses to let an instrument print a number it
cannot stand behind.

Three outcomes, and the difference between them is the whole point:

    SUBSTRATE_READY                  measure; the number is a fact about the tree.
    SUBSTRATE_INCOMPLETE             do not measure.  Exit non-zero with the reason, because a
                                     board printed here would be a fact about the image.
    SUBSTRATE_INCOMPLETE_ALLOWED     measure anyway, on purpose, and say so first.

The third exists because "how much does the substrate buy" is a real question, and answering it
requires running the board without it.  It has to be asked explicitly, and the banner is printed
before any number, so a log can never show that board without its caveat.

Usage::

    from substrate_precondition_v1 import precondition
    status = precondition()                 # restores once if needed, then verifies
    if not status.usable:
        print("NOT_MEASURED:", status.verdict, status.reason)
        return 2

Authority: NONE.  This reads an installed environment; it proves nothing about capability.
"""
from __future__ import annotations

import dataclasses
import importlib.util
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
RESTORE_SCRIPT = ROOT / "scripts" / "restore_substrate_v1.py"
RESTORE_TIMEOUT_S = 600


@dataclasses.dataclass(frozen=True)
class Substrate:
    """What the image holds, as the restore script measured it."""

    verdict: str
    ready: bool
    modules_present: int
    modules_total: int
    modules_missing: tuple[str, ...]
    binaries_missing: tuple[str, ...]
    parser_installed: str | None
    parser_expected: str | None
    restored: bool

    @property
    def usable(self) -> bool:
        """May an instrument print a capability number after this?"""
        return self.verdict in ("SUBSTRATE_READY", "SUBSTRATE_INCOMPLETE_ALLOWED")

    @property
    def reason(self) -> str:
        bits = []
        if self.modules_missing:
            bits.append("modules_missing=" + ",".join(self.modules_missing))
        if self.binaries_missing:
            bits.append("binaries_missing=" + ",".join(self.binaries_missing))
        if self.parser_installed != self.parser_expected:
            bits.append("parser_installed=%s parser_expected=%s"
                        % (self.parser_installed, self.parser_expected))
        return " ".join(bits) or "unknown"

    def banner(self) -> str:
        return ("SUBSTRATE %s  modules_present=%d/%d  restored=%s"
                % (self.verdict, self.modules_present, self.modules_total, self.restored))


def _load_restore_module():
    """Import the restore script by path: it is the owner, and scripts/ is not a package."""
    spec = importlib.util.spec_from_file_location("brain_restore_substrate_v1", RESTORE_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def probe() -> dict[str, object]:
    """The measurement.  A module-level name so a test can substitute a different image."""
    return _load_restore_module().verify()


def restore() -> bool:
    """Run the repository's own one command.  Returns whether it claimed success."""
    try:
        done = subprocess.run([sys.executable, str(RESTORE_SCRIPT)], cwd=str(ROOT),
                              capture_output=True, text=True, timeout=RESTORE_TIMEOUT_S)
    except (OSError, subprocess.SubprocessError):
        return False
    return done.returncode == 0


def precondition(*, allow_incomplete: bool = False, restore_if_missing: bool = True,
                 probe_fn=None, restore_fn=None, out=None) -> Substrate:
    """Measure the substrate, restoring it once if it is absent, and decide.

    ``allow_incomplete`` is the only way to get a usable verdict on an incomplete image, and it
    prints its caveat before returning.  Every other path either returns READY or returns
    something ``usable == False``.
    """
    out = sys.stdout if out is None else out
    probe_fn = probe if probe_fn is None else probe_fn
    restore_fn = restore if restore_fn is None else restore_fn

    state = probe_fn()
    restored = False
    if not _ready(state) and restore_if_missing and not allow_incomplete:
        restored = bool(restore_fn())
        state = probe_fn()

    missing = tuple(str(m) for m in state.get("modules_missing") or ())
    binaries = tuple(str(b) for b in state.get("binaries_missing") or ())
    status = Substrate(
        verdict=("SUBSTRATE_READY" if _ready(state)
                 else "SUBSTRATE_INCOMPLETE_ALLOWED" if allow_incomplete
                 else "SUBSTRATE_INCOMPLETE"),
        ready=_ready(state),
        modules_present=int(state.get("modules_present") or 0),  # type: ignore[arg-type]
        modules_total=int(state.get("modules_total") or 0),  # type: ignore[arg-type]
        modules_missing=missing,
        binaries_missing=binaries,
        parser_installed=state.get("parser_installed"),  # type: ignore[arg-type]
        parser_expected=state.get("parser_expected"),  # type: ignore[arg-type]
        restored=restored,
    )
    print(status.banner(), file=out)
    if not status.ready:
        if allow_incomplete:
            print("SUBSTRATE_CAVEAT: the numbers below measure an ENVIRONMENT gap, not a "
                  "capability gap -- " + status.reason, file=out)
        else:
            print("SUBSTRATE_CAVEAT: refusing to measure -- " + status.reason, file=out)
            print("  run: python3 scripts/restore_substrate_v1.py", file=out)
    return status


def _ready(state: dict[str, object]) -> bool:
    return bool(state.get("ready"))


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Is this image able to be measured at all?")
    ap.add_argument("--allow-incomplete", action="store_true")
    ap.add_argument("--no-restore", action="store_true")
    ns = ap.parse_args(argv)
    status = precondition(allow_incomplete=ns.allow_incomplete,
                          restore_if_missing=not ns.no_restore)
    return 0 if status.usable else 1


if __name__ == "__main__":
    raise SystemExit(main())
