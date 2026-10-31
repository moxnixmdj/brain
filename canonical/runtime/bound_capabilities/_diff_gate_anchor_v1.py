# PROJECT_BRAIN
"""Where a diff-gate may safely stand, and where it may put its scratch tree.

Two laws, learned from the same measurement twice.

**1. The anchor is the tree the diff's own paths resolve in.**

A unified diff names its targets the way git writes them: relative to the root of the
tree the change was taken from.  A sentence says "gate the diff <D>" and usually names
no worktree at all, so the binding layer anchors at the repository -- and a diff written
against `<world>/` (`a/pkg/calc.py`) then does not apply at the repository root, because
`pkg/calc.py` is not there.  Every gate refused it with DIFF_DOES_NOT_APPLY while the
diff itself was perfectly good.

The resolving tree is computable without guessing: walk from the diff's own directory
upward to the stated anchor and take the first directory where `git apply --check`
succeeds.  A diff that applies nowhere still fails closed, with the stated anchor, which
is the honest diagnosis.

**2. Scratch state never lives inside the tree it copies.**

Every gate compares an untouched anchor against a patched COPY of it, and the output
artifact usually sits inside the anchor.  A scratch directory beside the output is
therefore inside the copy, gets copied into the next copy, into the next ... until the
kernel refuses the path for length.  Measured on the repository as the anchor: a
single perf-gate call left thirty nested copies and died with ENAMETOOLONG.  Scratch
goes outside the anchor, still deterministic in the anchor's own digest, so a rerun
reuses the same place instead of scattering new ones.
"""
from __future__ import annotations

import hashlib
import subprocess
import tempfile
from pathlib import Path


def _applies(tree: Path, diff_abs: Path, timeout_s: int) -> bool:
    try:
        check = subprocess.run(["git", "apply", "--check", str(diff_abs)],
                               cwd=tree, capture_output=True, text=True,
                               timeout=max(5, min(int(timeout_s), 60)))
    except (OSError, subprocess.SubprocessError):
        return False
    return check.returncode == 0


def resolve_anchor(repo: Path, stated_anchor: Path, diff_abs: Path,
                   timeout_s: int = 60, must_contain=()) -> Path:
    """The directory the diff applies to: the stated anchor, or the nearest one that does.

    Cheap and bounded: at most one `git apply --check` per directory between the diff's
    own directory and the stated anchor.  The stated anchor always wins when it works,
    so a sentence that named the right tree keeps exactly the behaviour it had.
    """
    repo = Path(repo).resolve()
    stated_anchor = Path(stated_anchor).resolve()
    diff_abs = Path(diff_abs).resolve()
    required = [Path(p).resolve() for p in (must_contain or ()) if p]

    def _has_everything(tree: Path) -> bool:
        return all(item == tree or tree in item.parents for item in required)

    if _applies(stated_anchor, diff_abs, timeout_s) and _has_everything(stated_anchor):
        return stated_anchor
    if required and not _has_everything(stated_anchor):
        # The stated anchor does not hold everything this gate has to run; moving
        # it cannot help, and moving it would silently break the gate's own paths.
        return stated_anchor
    candidate = diff_abs.parent
    seen = set()
    while True:
        if candidate not in seen and candidate != stated_anchor \
                and (candidate == repo or repo in candidate.parents) \
                and candidate.is_dir() and _applies(candidate, diff_abs, timeout_s):
            return candidate
        seen.add(candidate)
        if candidate == stated_anchor or candidate == repo or candidate.parent == candidate:
            return stated_anchor
        candidate = candidate.parent


def scratch_base(anchor_abs: Path, preferred: Path) -> Path:
    """Where a gate may copy the anchor: never inside the anchor itself."""
    anchor_abs = Path(anchor_abs).resolve()
    base = Path(preferred).resolve()
    if base == anchor_abs or anchor_abs in base.parents:
        base = Path(tempfile.gettempdir()) / (
            "project_brain_gate_" + hashlib.sha256(str(anchor_abs).encode()).hexdigest()[:12])
    base.mkdir(parents=True, exist_ok=True)
    return base


def rebase_arg(arg: str, repo: Path, anchor_abs: Path) -> str:
    """A stated path, re-expressed relative to the tree a child process runs in."""
    text = str(arg or "")
    if not text or text.startswith("-") or "::" in text:
        return text
    candidate = Path(text)
    if not candidate.is_absolute():
        candidate = Path(repo) / candidate
    try:
        candidate = candidate.resolve()
    except OSError:
        return text
    anchor_abs = Path(anchor_abs).resolve()
    if candidate == anchor_abs or anchor_abs in candidate.parents:
        return candidate.relative_to(anchor_abs).as_posix()
    return text
