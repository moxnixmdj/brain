"""Measure a mechanism that changes the world, without measuring your own side effects.

THE FAILURE THIS EXISTS FOR, counted. Five separate probes in §A108–§A111 were invalid for ONE reason:

    the mechanism under test changes the world, and the probe then measured it again.

`pip install` in round 1 makes round 2's "is this module absent?" a question about a different world. In one
case that produced the belief that `repair_v1` could not classify `ModuleNotFoundError` — which was false, and
checking it cost more probes, each of which changed the world again.

WHY CARE, PRECISELY. The system's whole claim is that it acts in environments it has never seen. Acting
changes the environment. So *any* honest measurement of that claim runs straight into this problem, and a
measurement that silently drifts is worse than no measurement: it reports the world it happened to leave
behind as if it were the world it started with.

WHAT ISOLATION MEANS HERE, AND WHAT IT DOES NOT. Three things are separable and only one of them is cheap:

    the WORLD      a directory the mechanism reads and writes     -> copyable, cheaply, and this module does it
    the PROCESS    environment variables, cwd, imported modules   -> copyable via a subprocess
    the MACHINE    installed packages, system state               -> NOT copyable here

The third is the one that bit me. A `pip install` is a machine-wide fact and a copied directory cannot undo
it. So this module does not pretend to isolate it: it **records** the machine's state (which modules import,
which binaries exist) before and after, and reports a **drift** when a probe changed something outside the
world it was given. A measurement that changed the machine is reported as having changed the machine, which
is the honest thing and the thing that was missing.

WHAT IT REFUSES. It will not claim a world is "clean" when only the directory was copied. `isolated()` returns
what it actually isolated and what it did not, because a claim of isolation is the one thing a caller will
build a conclusion on.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Iterable, Iterator, Mapping
from contextlib import contextmanager
from typing import Any

SCHEMA = "PROJECT_BRAIN_WORLD_ISOLATION_V1"

#: Machines state that a directory copy cannot restore. Recorded, not claimed.
_MACHINE_PROBES = ("pip", "npm")


def fingerprint(root: str | pathlib.Path, *,
                skip: Iterable[str] = (".git", "node_modules", "__pycache__", ".venv")) -> dict[str, Any]:
    """A digest of a directory's files, so "did this change?" is a fact rather than a memory.

    Content is hashed, not mtimes: a touch is not a change and an edited file with an old mtime is.
    Reading is bounded so a large tree cannot make a check expensive enough to skip.
    """
    base = pathlib.Path(root)
    digest = hashlib.sha256()
    files = 0
    total = 0
    skipped = set(skip)
    if not base.is_dir():
        return {"root": str(base), "exists": False, "sha256": "", "files": 0, "bytes": 0}
    for path in sorted(base.rglob("*")):
        if any(part in skipped for part in path.parts):
            continue
        if not path.is_file() or path.is_symlink():
            continue
        try:
            data = path.read_bytes()
        except OSError:
            continue
        digest.update(str(path.relative_to(base)).encode())
        digest.update(b"\x00")
        digest.update(hashlib.sha256(data).digest())
        files += 1
        total += len(data)
    return {"root": str(base), "exists": True, "sha256": digest.hexdigest(),
            "files": files, "bytes": total}


def _site_packages() -> list[pathlib.Path]:
    found: list[pathlib.Path] = []
    for entry in sys.path:
        path = pathlib.Path(entry or ".")
        if path.name == "site-packages" and path.is_dir():
            found.append(path)
    return found


def machine_state() -> dict[str, Any]:
    """What a directory copy CANNOT restore: the installed packages, and the tools on PATH.

    THE FIRST VERSION ASKED THE WRONG QUESTION. It probed a fixed list of module names -- pip, pytest, PIL,
    toml -- and reported "no drift" after `pyjokes` had been installed, because `pyjokes` was not on the list.
    A snapshot of the names I thought to check is not a snapshot of the machine; it is a snapshot of my
    imagination, and it fails silently in exactly the direction that matters (it says nothing changed).

    So the packages are ENUMERATED rather than guessed: every distribution directory in site-packages is
    listed by name. That set changes when anything is installed, removed or upgraded, whatever it is called.
    """
    packages: list[str] = []
    for directory in _site_packages():
        try:
            for entry in directory.iterdir():
                if entry.is_dir() and not entry.name.startswith("_"):
                    packages.append(entry.name)
        except OSError:
            continue
    packages.sort()
    digest = hashlib.sha256("\n".join(packages).encode()).hexdigest()
    tools = {tool: shutil.which(tool) for tool in _MACHINE_PROBES}
    return {"package_count": len(packages), "packages_sha256": digest,
            "tools": tools, "executable": sys.executable}


@contextmanager
def isolated(source: str | pathlib.Path, *,
             label: str = "probe") -> Iterator[dict[str, Any]]:
    """Give a probe its own copy of a world, and report honestly what it did to the machine.

    Yields a record with:
        world          the copy to act in -- the ONLY path a probe should touch
        source_before  fingerprint of the original, before
        source_after   fingerprint of the original, after  (must equal before)
        machine_before / machine_after / machine_drift

    `machine_drift` is the point. If a probe installs a package, the world copy cannot undo it; the record
    says so, and a caller that ignores it is ignoring a stated fact rather than a hidden one.

    The copy is removed at exit even when the body raises, because a leak makes the NEXT measurement start
    from a world the previous one chose.
    """
    work = pathlib.Path(tempfile.mkdtemp(prefix="world_%s_" % label))
    world = work / "world"
    source_path = pathlib.Path(source).resolve()

    # A COPY MUST NOT CONTAIN ITSELF. §A101 filled the disk by copying /tmp into a temp dir inside /tmp.
    if source_path == work.parent or source_path in work.parents or source_path == pathlib.Path(
            tempfile.gettempdir()).resolve():
        shutil.rmtree(work, ignore_errors=True)
        raise ValueError("THE_SOURCE_CONTAINS_THE_ISOLATION_WORKSPACE")

    source_before = fingerprint(source_path)
    machine_before = machine_state()
    def _skip(directory: str, names: list[str]) -> set[str]:
        ignored = {"__pycache__", ".git"}
        for name in names:
            candidate = pathlib.Path(directory) / name
            try:
                if candidate.resolve() == work or candidate.name.startswith("world_probe_"):
                    ignored.add(name)
            except OSError:
                ignored.add(name)
        return ignored

    if source_path.is_dir():
        shutil.copytree(source_path, world, dirs_exist_ok=True, symlinks=True, ignore=_skip)
    else:
        world.mkdir(parents=True, exist_ok=True)

    record: dict[str, Any] = {"schema": SCHEMA, "world": str(world),
                              "source": str(source_path),
                              "source_before": source_before,
                              "machine_before": machine_before,
                              "isolated": ["the_world_directory"],
                              "not_isolated": ["the_process_environment", "installed_packages",
                                               "anything_outside_the_world"]}
    try:
        yield record
    finally:
        source_after = fingerprint(source_path)
        machine_after = machine_state()
        record["source_after"] = source_after
        record["machine_after"] = machine_after
        record["source_unchanged"] = (source_before.get("sha256") == source_after.get("sha256"))
        # ENUMERATED, so an install of ANY package shows up -- including one nobody thought to list.
        was = machine_before.get("package_count", 0)
        now = machine_after.get("package_count", 0)
        record["machine_drift"] = {
            "packages_before": was,
            "packages_after": now,
            "packages": now - was,
            "packages_sha256_changed": (machine_before.get("packages_sha256")
                                        != machine_after.get("packages_sha256")),
            "tools": sorted(tool for tool, path in machine_after["tools"].items()
                            if machine_before["tools"].get(tool) != path),
        }
        record["machine_changed"] = bool(record["machine_drift"]["packages_sha256_changed"]
                                         or record["machine_drift"]["tools"])
        shutil.rmtree(work, ignore_errors=True)


def report(record: Mapping[str, Any]) -> dict[str, Any]:
    """What a caller needs to know before believing a measurement taken inside `isolated`."""
    source_unchanged = record.get("source_unchanged")
    machine_changed = record.get("machine_changed")
    if source_unchanged is None:
        verdict = "THE_MEASUREMENT_DID_NOT_FINISH"
    elif source_unchanged is False:
        verdict = "THE_PROBE_CHANGED_THE_WORLD_IT_WAS_MEANT_TO_LEAVE_ALONE"
    elif machine_changed:
        verdict = "THE_WORLD_WAS_PROTECTED_BUT_THE_MACHINE_CHANGED"
    else:
        verdict = "THE_ORIGINAL_WORLD_AND_THE_MACHINE_ARE_BOTH_UNCHANGED"
    return {"schema": SCHEMA, "verdict": verdict,
            "source_unchanged": source_unchanged,
            "machine_changed": machine_changed,
            "machine_drift": record.get("machine_drift") or {},
            "isolated": record.get("isolated"),
            "not_isolated": record.get("not_isolated")}


def main(argv: list[str] | None = None) -> int:
    import json

    arguments = list(argv if argv is not None else sys.argv[1:])
    if not arguments:
        print(json.dumps({"schema": SCHEMA,
                          "usage": "world_isolation_v1 <dir>  (fingerprint, and say what is not isolated)"},
                         indent=1))
        return 0
    with isolated(arguments[0], label="cli") as record:
        pass
    print(json.dumps(report(record), indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
