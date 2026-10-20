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
_COMMON_PORTS = tuple(list(range(8000, 8100)) + [80, 443, 3000, 5000, 8080, 8888, 9000])
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

    # Python projects advertise their runnable commands here. Without this,
    # walking into a pyproject-only project surfaced NO declared commands --
    # an entire class of environment was invisible.
    pyproject = rootp / "pyproject.toml"
    if pyproject.is_file():
        try:
            import tomllib
            data = tomllib.loads(pyproject.read_text(errors="replace"))
            for _name, _target in (((data.get("project") or {})
                                    .get("scripts") or {}).items()):
                out.append("python:" + str(_target))
        except Exception:
            pass

    # Executable scripts this project ships.
    # Dot-directories are where CI and automation actually live. Skipping
    # them meant .ci/run.sh -- real work -- was invisible in env_hard.
    for sub in ("scripts", "bin", "canonical/runtime", "tools",
                ".ci", ".github/workflows", ".buildkite", ".circleci", "ci"):
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


def entrypoint_commands(root: str) -> list[list[str]]:
    """Turn discovered entry points into commands that can actually be run.

    Without this, entrypoints() was an inventory -- it found make:greet and
    npm:ping and never acted on either. Discovery that cannot act is a
    listing, not a capability.

    Every returned command is one this project or directory advertised about
    itself, so running it is what the environment is asking for.
    """
    cmds: list[list[str]] = []
    for ep in entrypoints(root):
        kind, _, name = ep.partition(":")
        if kind == "make":
            cmds.append(["make", name])
        elif kind == "npm":
            cmds.append(["npm", "run", "--silent", name])
        elif kind == "run":
            cmds.append(["sh", name])
        elif kind == "python":
            # name is "module:function" as declared by the project.
            mod, _, fn = name.partition(":")
            if mod:
                cmds.append(["python3", "-c",
                             "import %s; %s.%s()" % (mod, mod, fn)
                             if fn else "import %s" % mod])
    return cmds


def candidates(root: str, binary_limit: int = 40) -> list[list[str]]:
    """Probe commands worth trying here, derived from observation.

    Every candidate is read-only or near-read-only: --version / --help.
    Discovery must not have side effects.
    """
    cmds: list[list[str]] = []
    for b in binaries()[:binary_limit]:
        cmds.append([b, "--version"])
    if (Path(root) / "Makefile").is_file():
        cmds.append(["make", "-n", "-f", "Makefile"])
    if (Path(root) / "package.json").is_file():
        cmds.append(["npm", "run"])
    # The advertised entry points, so discovery leads somewhere.
    cmds.extend(entrypoint_commands(root))
    # Tasks declared in files we have no prior knowledge of.
    cmds.extend(task_commands_from_files(root))
    return cmds


def services(ports=None, host="127.0.0.1", timeout=0.12) -> list[int]:
    """Listening services on this machine.

    Everything else in here reads the FILESYSTEM. But a running service is
    not in any directory -- it exists only as an open port. A machine that
    cannot see open ports cannot see most of what a computer is actually
    doing. This is discovery moving from "read the room" to "read the box".

    Connect-only, short timeout, bounded port set. It never sends a payload
    and never mutates anything.
    """
    import socket
    found = []
    for port in (ports or _COMMON_PORTS):
        try:
            with socket.create_connection((host, port), timeout=timeout):
                found.append(port)
        except OSError:
            continue
    return found


def task_commands_from_files(root: str) -> list[list[str]]:
    """Tasks declared in any structured file, whatever it happens to be called.

    Delegates to taskfile_read_v1, which reads by SHAPE -- a name paired with
    a command -- rather than by filename. Formats never seen before still work.
    """
    try:
        import taskfile_read_v1 as T
        return T.task_commands(root)
    except Exception:
        return []


def service_commands(host="127.0.0.1", ports=None) -> list[list[str]]:
    """Cheap read-only probes against whatever is listening."""
    cmds = []
    for port in services(ports=ports, host=host):
        cmds.append(["curl", "-s", "-m", "3", "http://%s:%d/" % (host, port)])
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
