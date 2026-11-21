#!/usr/bin/env python3
"""One adversarial CLI environment: one atom creates two copies at once.

Real shell commands, no stored facts and no parameters. It exists so a claimed
question can be tested against a vocabulary that can actually separate it.
Authority: NONE.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS = ROOT / "canonical" / "tools"
for path in (str(ROOT), str(TOOLS)):
    if path not in sys.path:
        sys.path.insert(0, path)

import instant_learning_in_a_new_environment_v1 as env  # noqa: E402

SECOND = "probe_second_content"
BULK_STEPS = ("sh", "-c", 'printf %s "$0" > "$1" && cp "$1" "$2"',
              "{content}", "{name}", "{target}")


def build(root: pathlib.Path) -> env.Machine:
    def reset() -> None:
        for path in list(root.iterdir()):
            if path.is_file():
                path.unlink()
        (root / "seed").write_text(env.PROBE_OLD, encoding="utf-8")
        (root / "seed2").write_text(SECOND, encoding="utf-8")

    def read() -> list[tuple[str, str]]:
        return [(path.name, path.read_text(errors="replace").strip())
                for path in sorted(root.iterdir()) if path.is_file()]

    return env.Machine("BULK_COPY", root,
                       (env.Atom("BULK_A1", ((BULK_STEPS, None),)),), read, reset)
