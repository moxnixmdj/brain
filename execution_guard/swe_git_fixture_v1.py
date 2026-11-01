"""A git tree for a fixture, in one place.

A question about history cannot be asked of a directory that has none. Measured 2026-10-31 in the
capability matrix, where this fixture was written: "Show the diff of <f>" was answered and then
re-judged as a false claim because the diff was empty, and "no hunk" cannot be distinguished from
"no diff was produced" -- a case that cannot tell those apart certifies nothing.

The advanced census next door builds the same scratch project and seeds nothing, so its five git
sentences and its two history questions ("benchmark against git HEAD~1", "find the commit that
broke the test") were asked of plain directories. That is a defect in the instrument, not in the
machine: it measures the absence of a fixture. This module is the one owner of the fixture, used
by both instruments, and it never raises -- on failure the case simply has no repository and the
honest result is a refusal, because a raising fixture is scored as a machine defect.
"""
from __future__ import annotations

import pathlib
import subprocess

SCHEMA = "PROJECT_BRAIN_SWE_GIT_FIXTURE_V1"

_ENV = {
    "PATH": "/usr/bin:/bin:/usr/local/bin",
    "GIT_AUTHOR_NAME": "fixture",
    "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
    "GIT_COMMITTER_NAME": "fixture",
    "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
}


def seed_repository(base: pathlib.Path, dirty_rel: str = "pkg/calc.py",
                    baseline: str = "baseline", history: str = "repair") -> bool:
    """Seed TWO commits in ``base`` and leave a third, uncommitted change behind.

    A repository with ONE commit cannot answer a question about a revision.  Measured
    2026-11-01: the advanced census asked "Show me the diff of <f> against HEAD~1" of a tree
    whose history was a single commit, so ``HEAD~1`` did not resolve -- and before the row had
    a ``rev`` slot the same sentence was answered with the empty diff against ``HEAD`` and
    certified VERIFIED.  A fixture that cannot express "the previous revision" makes both
    readings unfalsifiable: an honest refusal and a false pass look the same.

    Three states, so every sentence the instruments ask has exactly one true answer:

    ==========================  =============================  =======================
    question                    answer                         state
    ==========================  =============================  =======================
    diff against HEAD~1         the two commits' difference,   ``history`` change,
                                plus the pending one           committed
    diff against HEAD           the pending change only        ``dirty`` change
    find the commit that broke  the second commit               two commits to bisect
    commit / create a branch    ``.git`` in a known state      uncommitted change
    ==========================  =============================  =======================

    ``history`` names the change the second commit makes, so the committed difference is
    visible, revertible and bisectable rather than an empty commit.
    """
    env = dict(_ENV, HOME=str(base))
    dirty = base / dirty_rel
    try:
        if subprocess.run(("git", "init", "-q"), cwd=str(base), capture_output=True,
                          text=True, timeout=60, env=env).returncode != 0:
            return False

        def commit(message: str) -> bool:
            steps = (("git", "add", "-A"),
                     ("git", "-c", "commit.gpgsign=false", "commit", "-q", "-m", message))
            return all(subprocess.run(argv, cwd=str(base), capture_output=True, text=True,
                                      timeout=60, env=env).returncode == 0 for argv in steps)

        if not commit(baseline):
            return False
        if dirty.is_file():
            # Commit a real difference, so HEAD~1 is a revision with something to show.
            text = dirty.read_text(encoding="utf-8")
            change = ("\n# fixture: committed %s\n" % history
                      if history == "repair" else "\n# fixture: %s\n" % history)
            dirty.write_text(text + change, encoding="utf-8")
            if not commit("fixture: " + history):
                return False
            # ...and leave the pending change, so the working tree still has one.
            dirty.write_text(dirty.read_text(encoding="utf-8") + "\n# fixture: uncommitted\n",
                             encoding="utf-8")
        return True
    except (OSError, subprocess.SubprocessError):
        return False
