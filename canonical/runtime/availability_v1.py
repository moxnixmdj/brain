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
    """Declared requirements that this environment does not satisfy."""
    reg = registry if registry is not None else load_registry()
    entry = reg.get(capability_id) or {}
    # `requires` was already in the registry with a DIFFERENT meaning --
    # abstract conditions like "node.runtime.available", not executables.
    # Checking those against PATH would report things blocked that are not.
    # Binaries get their own field so the two never mix.
    return [r for r in (entry.get("requires_binaries") or []) if not has(r)]


def load_registry() -> dict:
    import json
    p = Path(REGISTRY)
    snap = p.with_name("BOUND_CAPABILITY_REGISTRY_SNAPSHOT_V1.json")
    txt = p.read_text(encoding="utf-8") if p.is_file() else ""
    if not txt.lstrip().startswith("{") and snap.is_file():
        txt = snap.read_text(encoding="utf-8")
    caps = dict(json.loads(txt).get("capabilities") or {})
    if snap.is_file():
        caps.update(json.loads(snap.read_text(encoding="utf-8")).get("capabilities") or {})
    return caps


def available(registry: dict | None = None) -> dict[str, list[str]]:
    """capability_id -> unmet requirements. Empty list means runnable here.

    A capability whose verification evidence no longer describes the code that would run
    is not runnable, for the same reason a capability with no binary is not: offering it
    would be a claim nobody measured. `binding_pin_is_current_v1` derives that verdict
    (FRESH / STALE / UNVERIFIED) from the pins themselves, because the registry's own
    `verification.status` has been positive on 141 of 141 rows in every one of the 142
    commits that touched it -- a field that only ever takes one value is not a status.

    UNVERIFIED is deliberately NOT a blocker. 138 rows carry no checkable pin; calling
    them all unrunnable would delete 138 capabilities on a technicality. Only STALE is
    refuted, and refuted evidence is the thing that must cost the capability its offer.
    """
    reg = registry if registry is not None else load_registry()
    stale = _stale_ids(reg)
    out: dict[str, list[str]] = {}
    for cid in reg:
        unmet = missing(cid, reg)
        if cid in stale:
            unmet = unmet + ["verification_evidence_is_stale"]
        out[cid] = unmet
    return out


_STALE_CACHE: dict[int, frozenset[str]] = {}


def _stale_ids(reg: dict) -> frozenset[str]:
    """Capability ids whose pin the file contradicts. Empty on any failure to compute.

    Fails OPEN and only open: a broken audit must not remove capabilities, because
    silently deleting the option set is a worse error than not auditing it.
    """
    key = id(reg)
    if key in _STALE_CACHE:
        return _STALE_CACHE[key]
    try:
        from canonical.runtime import binding_pin_is_current_v1 as pins
        verdicts = pins.resolve(Path(__file__).resolve().parents[2])
        stale = frozenset(cid for cid, v in verdicts.items() if v.get("verdict") == pins.STALE)
    except Exception:
        stale = frozenset()
    _STALE_CACHE[key] = stale
    return stale


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
