#!/usr/bin/env python3
"""Re-anchor registry/executor probe-site pins to CURRENT line numbers.

The confined-mediator registry pins (module, line, subprocess api) for the
acquisition contract probes. Any edit above those `subprocess.run(` call
lines invalidates the pins; this script computes authoritative positions and
rewrites the pin blocks in:

- root3_subprocess_effect_class_registry_v2.py (remap + narrowed entries)
- root3_bound_codec_child_executor_v1.py (executor sites)

Never inserts/removes semantics; only re-anchors. Fails loudly on mismatch.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
RT = ROOT / "canonical" / "runtime"

REG = RT / "root3_subprocess_effect_class_registry_v2.py"
EXEC = RT / "root3_bound_codec_child_executor_v1.py"
SRCM = "canonical/runtime/auto_python_source_codec_acquisition.py"
NPMM = "canonical/runtime/auto_npm_library_acquisition.py"


def probe_lines(path: pathlib.Path, pattern: str) -> list[int]:
    return [
        i + 1
        for i, line in enumerate(path.read_text().splitlines())
        if pattern in line
    ]


def rewrite(t: str, module: str, old_line_re: str, new_line: int) -> str:
    # match the 4-line tuple body: module, \n <spaces> NUMBER, \n <spaces> api,
    rx = re.compile(
        r'("' + re.escape(module) + r'"\s*,\s*\n\s*)(\d+)(\s*,\s*\n\s*"subprocess\.run")'
    )
    return rx.sub(lambda m: m.group(1) + str(new_line) + m.group(3), t)


def main() -> int:
    src_prime, src_dispatch = probe_lines(RT / "auto_python_source_codec_acquisition.py", "probe=subprocess.run(")
    (npm_probe,) = probe_lines(RT / "auto_npm_library_acquisition.py", "proc=subprocess.run(")

    # registry v2
    t = REG.read_text()
    # remap table entry maps current -> legacy 217
    t = re.sub(
        r"(\d+): 217,",
        "%d: 217," % src_dispatch,
        t,
        count=1,
    )
    # narrowed entries for the prime probe (two blocks)
    t = rewrite(t, SRCM, "", src_prime)
    npm_t = rewrite(t, NPMM, "", npm_probe)
    REG.write_text(npm_t)

    # executor sites — anchored per named const to avoid cross-assignment
    e = EXEC.read_text()
    def assign(e: str, const: str, line: int) -> str:
        rx = re.compile(
            r"(" + const + r" = \(\n\s*\"[^\"]+\",\n\s*)(\d+)(\s*,\n\s*\"subprocess\.run\",\n\s*\))"
        )
        e2, n = rx.subn(lambda m: m.group(1) + str(line) + m.group(3), e, count=1)
        if n != 1:
            raise RuntimeError("assign missing for " + const)
        return e2
    e = assign(e, "SRC_CODEC_PRIME_PROBE_SITE", src_prime)
    e = assign(e, "SRC_CODEC_PROBE_SITE", src_dispatch)
    e = assign(e, "NPM_PROBE_SITE", npm_probe)
    EXEC.write_text(e)

    print("pins: src.prime=%d src.dispatch=%d npm.probe=%d" % (src_prime, src_dispatch, npm_probe))
    return 0


if __name__ == "__main__":
    sys.exit(main())
