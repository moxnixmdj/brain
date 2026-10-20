"""Know what you CANNOT do here.

From first principles, handling a NEW environment is not only working out
what is possible -- it is knowing what is not. A capability that is
registered but cannot run is not a capability. Offering it is the same class
of lie as reporting a status nobody measured.

The browser exposed this: bound at 9fa2fdad, advertised, and unrunnable --
no chrome, no chromedriver, no selenium. It would have sat in the option set
looking available forever.

So a capability may declare `requires`: the executables that must exist on
PATH for it to run. available() checks them. Missing anything, it is not
offered -- not scored lower, not warned about: absent.

Absence is information. "There is no browser on this box" is a true and
useful thing for the machine to know about where it is.
"""
from __future__ import annotations

import os
import stat
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_AVAILABILITY_V1"
REGISTRY = Path(__file__).resolve().parent / "BOUND_CAPABILITY_REGISTRY_V1.json"


def has(exe: str) -> bool:
    """Is this executable present and runnable on PATH?"""
    if not exe:
        return False
    for d in (os.environ.get("PATH") or "").split(os.pathsep):
        if not d:
            continue
        fp = Path(d) / exe
        try:
            st = fp.stat()
        except OSError:
            continue
        if fp.is_file() and (st.st_mode & (stat.S_IXUSR | stat.S_IXGRP
                                           | stat.S_IXOTH)):
            return True
    return False


def missing(capability_id: str, registry: dict | None = None) -> list[str]:
    """Executables required by this route but absent from this environment.

    ``requires`` is an abstract capability-precondition list, not a list of
    executable names.  ``requires_binaries`` is the explicit binary contract;
    a ``system_tool`` source also has an implicit executable contract.  Include
    both so a registered system tool cannot appear runnable merely because its
    author omitted a duplicate ``requires_binaries`` entry.
    """
    reg = registry if registry is not None else load_registry()
    entry = reg.get(capability_id) or {}
    required = list(entry.get("requires_binaries") or [])
    source = entry.get("source")
    if isinstance(source, dict) and source.get("type") == "system_tool":
        executable = source.get("executable")
        if isinstance(executable, str) and executable.strip():
            required.append(executable.strip())
        else:
            required.append("<invalid-system-tool-executable>")
    missing = []
    for executable in required:
        if executable not in missing and not has(executable):
            missing.append(executable)
    return missing


def load_registry() -> dict:
    import json
    data = json.loads(Path(REGISTRY).read_text(encoding="utf-8"))
    return data.get("capabilities", data)


def available(registry: dict | None = None) -> dict[str, list[str]]:
    """capability_id -> unmet requirements. Empty list means runnable here."""
    reg = registry if registry is not None else load_registry()
    return {cid: missing(cid, reg) for cid in reg}


def runnable(registry: dict | None = None) -> list[str]:
    """Capabilities this environment can actually execute."""
    return sorted(cid for cid, m in available(registry).items() if not m)


if __name__ == "__main__":
    import json
    av = available()
    ok = [c for c, m in av.items() if not m]
    bad = {c: m for c, m in av.items() if m}
    print(json.dumps({"schema": SCHEMA,
                      "runnable_here": len(ok),
                      "blocked_here": bad}, indent=2)[:800])
