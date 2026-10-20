"""Know what you CANNOT do here.

From first principles, handling a NEW environment is not only working out
what is possible -- it is knowing what is not. A capability that is
registered but cannot run is not a capability. Offering it is the same class
of lie as reporting a status nobody measured.

The browser exposed this: its registry named `chromedriver` as the system
executable, but availability checked only `requires_binaries`, so the tool
appeared runnable even when that executable was absent. Availability now
checks explicit binary requirements and the executable declared by a
`system_tool` source. When that executable is absent, an adapter may expose a
checked `availability_fallback_missing_executables()` hook for a real alternate
route; only that route's prerequisites are then checked. Abstract `requires`
conditions remain a separate capability-planning contract and are never
interpreted as PATH names.

Missing any required executable, the tool is not offered -- not scored lower,
not warned about: absent. The live route repeats this check before execution.

Absence is information. "There is no browser on this box" is a true and
useful thing for the machine to know about where it is.
"""
from __future__ import annotations

import importlib.util
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


def _fallback_missing(entry: dict) -> list[str] | None:
    """Return prerequisites for an explicitly implemented adapter fallback."""
    module_name = entry.get("adapter_module")
    if not isinstance(module_name, str) or not module_name.isidentifier():
        return None
    path = Path(__file__).resolve().parent / "bound_capabilities" / (module_name + ".py")
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("brain_availability_" + module_name, path)
    if spec is None or spec.loader is None:
        return None
    try:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        check = getattr(module, "availability_fallback_missing_executables", None)
        if not callable(check):
            return None
        result = check()
    except Exception:
        return None
    if not isinstance(result, list) or any(not isinstance(x, str) or not x.strip() for x in result):
        return None
    return list(dict.fromkeys(x.strip() for x in result))


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
            executable = executable.strip()
            if has(executable):
                required.append(executable)
            else:
                fallback = _fallback_missing(entry)
                if fallback is None:
                    required.append(executable)
                else:
                    required.extend(fallback)
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
