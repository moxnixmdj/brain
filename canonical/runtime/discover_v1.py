"""Discover what is possible here, by looking -- not by being told.

The gap this closes: explore_v1 ranked actions I handed it. Ranking from a
menu is not exploration. Exploration means arriving somewhere unfamiliar and
working out, by observation, what can be done.

Two cheap universal sources of truth about any environment:

  binaries()      what executables exist on PATH
  entrypoints()   what this directory advertises about itself

Neither is programmed knowledge of the place. Both are read off it. That is
the difference between a system that needs a manual and one that reads the
room.

Everything is bounded and read-only. Discovery must never be the expensive
part, and must never mutate what it is discovering.
"""
from __future__ import annotations

import os
import stat
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_DISCOVER_V1"

_MAX_BINARIES = 400
_MAX_ENTRYPOINTS = 60
_SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", ".pytest_cache"}


def binaries(limit: int = _MAX_BINARIES) -> list[str]:
    """Executables visible on PATH. The local vocabulary of this machine."""
    found, seen = [], set()
    for d in (os.environ.get("PATH") or "").split(os.pathsep):
        if not d:
            continue
        try:
            entries = os.scandir(d)
        except OSError:
            continue
        with entries:
            for e in entries:
                if e.name in seen:
                    continue
                try:
                    if not e.is_file():
                        continue
                    if not os.access(e.path, os.X_OK):
                        continue
                    if not (os.stat(e.path).st_mode & stat.S_IXUSR):
                        continue
                except OSError:
                    continue
                seen.add(e.name)
                found.append(e.name)
                if len(found) >= limit:
                    return sorted(found)
    return sorted(found)


def entrypoints(root: str, limit: int = _MAX_ENTRYPOINTS) -> list[str]:
    """What the directory says about itself: scripts, targets, manifests."""
    rootp = Path(root)
    out: list[str] = []

    mk = rootp / "Makefile"
    if mk.is_file():
        try:
            for line in mk.read_text(errors="replace").splitlines()[:400]:
                if line and not line[0].isspace() and ":" in line:
                    tgt = line.split(":", 1)[0].strip()
                    if tgt and not tgt.startswith(".") and "=" not in tgt:
                        out.append("make:" + tgt)
        except OSError:
            pass

    pkg = rootp / "package.json"
    if pkg.is_file():
        try:
            import json
            for name in (json.loads(pkg.read_text(errors="replace"))
                         .get("scripts") or {}):
                out.append("npm:" + str(name))
        except Exception:
            pass

    # Executable scripts this project ships.
    for sub in ("scripts", "bin", "canonical/runtime", "tools"):
        d = rootp / sub
        if not d.is_dir():
            continue
        for fp in sorted(d.glob("*"))[:120]:
            if fp.suffix in {".sh", ".py"} or (
                    fp.is_file() and os.access(fp, os.X_OK)):
                out.append("run:" + str(fp.relative_to(rootp)))

    seen, uniq = set(), []
    for x in out:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq[:limit]


def candidates(root: str, binary_limit: int = 40) -> list[list[str]]:
    """Probe commands worth trying here, derived from observation.

    Every candidate is read-only or near-read-only: --version / --help.
    Discovery must not have side effects.
    """
    cmds: list[list[str]] = []
    for b in binaries()[:binary_limit]:
        cmds.append([b, "--version"])
    cmds.append(["make", "-n", "-f", "Makefile"]) if (Path(root) / "Makefile").is_file() else None
    if (Path(root) / "package.json").is_file():
        cmds.append(["npm", "run"])
    return cmds


def report(root: str) -> dict:
    b, e = binaries(), entrypoints(root)
    return {"schema": SCHEMA, "root": str(root),
            "binary_count": len(b), "binaries_head": b[:25],
            "entrypoint_count": len(e), "entrypoints": e,
            "candidate_count": len(candidates(root)),
            "model_dependency_count": 0}


if __name__ == "__main__":
    import json
    print(json.dumps(report("/home/user/brain"), indent=2)[:1200])
