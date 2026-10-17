"""Act in an unknown environment and learn what changed.

From first principles: a system that handles a NEW environment cannot rely on
a list of tools written for known ones. What generalises is a loop — act,
observe what changed, credit what helped.

`shell.command.run` supplies the act. This supplies the observe.

The signal is the DELTA. Not "did the command succeed" — a command can exit
zero and change nothing, and exit non-zero after changing everything. What
matters is the difference between the environment before and after.

Snapshot is deliberately shallow and cheap: path, size, mtime. Enough to see
that something changed, without reading content. Depth and extension filters
keep it bounded so the probe itself never becomes the expensive part.
"""
from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_ENVIRONMENT_PROBE_V1"

_SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", ".pytest_cache"}


def snapshot(root: str, max_files: int = 4000, max_depth: int = 4) -> dict:
    """Cheap fingerprint of the environment: path -> (size, mtime_ns)."""
    rootp = Path(root).resolve()
    out = {}
    count = 0
    for dirpath, dirnames, filenames in os.walk(rootp):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        depth = len(Path(dirpath).relative_to(rootp).parts)
        if depth >= max_depth:
            dirnames[:] = []
        for name in filenames:
            if count >= max_files:
                return out
            fp = Path(dirpath) / name
            try:
                st = fp.stat()
            except OSError:
                continue
            out[str(fp.relative_to(rootp))] = (st.st_size, st.st_mtime_ns)
            count += 1
    return out


def delta(before: dict, after: dict) -> dict:
    """What changed. The signal the whole loop runs on."""
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    modified = sorted(k for k in set(before) & set(after)
                      if before[k] != after[k])
    return {
        "schema": SCHEMA,
        "added": added[:50],
        "removed": removed[:50],
        "modified": modified[:50],
        "added_count": len(added),
        "removed_count": len(removed),
        "modified_count": len(modified),
        "changed": bool(added or removed or modified),
    }


def probe(root: str, argv: list[str], timeout_s: int = 60) -> dict:
    """Run one command and report what it did to the environment.

    Non-zero exit is recorded, not treated as disqualifying: a command that
    fails after changing state is still information.
    """
    before = snapshot(root)
    t0 = time.time()
    try:
        proc = subprocess.run(
            argv, cwd=root, capture_output=True, text=True,
            timeout=max(1, min(int(timeout_s), 300)))
        rc, err = proc.returncode, (proc.stderr or "")[-500:]
        out = (proc.stdout or "")[-2000:]
    except subprocess.TimeoutExpired:
        rc, err, out = None, "TIMEOUT", ""
    except Exception as exc:
        rc, err, out = None, f"{type(exc).__name__}: {exc}", ""
    after = snapshot(root)
    d = delta(before, after)
    d.update({
        "argv": argv,
        "returncode": rc,
        "stderr_tail": err,
        "stdout_tail": out,
        "elapsed_s": round(time.time() - t0, 3),
        "effected_change": d["changed"],
    })
    return d


if __name__ == "__main__":
    import json
    root = "/home/user/brain"
    # A command that changes nothing, and one that does.
    for argv in (["true"], ["touch", "canonical/astra_runtime/state/probe_marker"]):
        r = probe(root, argv)
        print(f"{str(argv):<52} rc={r['returncode']} "
              f"changed={r['effected_change']} "
              f"added={r['added_count']} modified={r['modified_count']}")
