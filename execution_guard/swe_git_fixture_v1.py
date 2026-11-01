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
                    baseline: str = "baseline") -> bool:
    """Commit a baseline in ``base``, then leave ``dirty_rel`` modified.

    Returns True when the repository exists and carries one uncommitted change. Every git
    question the instruments ask then has an answer only a working implementation can give:
    a diff with a hunk, a commit to make, a branch to create, two revisions to compare.
    """
    env = dict(_ENV, HOME=str(base))
    try:
        for argv in (("git", "init", "-q"), ("git", "add", "-A"),
                     ("git", "-c", "commit.gpgsign=false", "commit", "-q", "-m", baseline)):
            if subprocess.run(argv, cwd=str(base), capture_output=True, text=True,
                              timeout=60, env=env).returncode != 0:
                return False
        dirty = base / dirty_rel
        if dirty.is_file():
            dirty.write_text(dirty.read_text(encoding="utf-8") + "\n# fixture: uncommitted\n",
                             encoding="utf-8")
        return True
    except (OSError, subprocess.SubprocessError):
        return False
