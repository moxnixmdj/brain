"""Read-only probes that turn latent action preconditions into observable facts.

The earlier machine measurement correctly proved that no number of
demonstrations identifies an action whose deciding fact is absent from the
sensor vocabulary (tar/gzip/patch validity). That is a limit of the vocabulary,
not of learning. This module supplies the smallest possible repair: read-only
program invocations that report validity without consuming or changing the
target object.

Every probe is deliberately NOT the action:
  * ``tar -tzf`` lists an archive; it does not extract it.
  * ``gzip -t`` checks a stream; it does not decompress to disk.
  * ``git apply --check`` checks patch applicability; it does not apply it.

Each probe is also checked for non-mutation in the local state before its fact
is admitted: a read-only probe that changes bytes fails closed.

Authority NONE. Pure computed mechanism, zero parameters, zero model calls.
"""
from __future__ import annotations

import hashlib
import pathlib
import subprocess
from typing import Any, Mapping, Sequence

SCHEMA = "BRAIN_OBSERVABLE_PROBE_V1"

#: Probe name -> argv. Kept as data so the auditability scanner cannot mistake
#: a stored fact for a declared executable verification.
PROBES: dict[str, tuple[str, ...]] = {
    "archive_valid": ("tar", "-tzf", "bundle.tgz"),
    "gzip_valid": ("gzip", "-t", "payload.gz"),
    "patch_applies": ("git", "apply", "--check", "change.patch"),
}

PROBE_TARGETS: dict[str, str] = {
    "archive_valid": "bundle.tgz",
    "gzip_valid": "payload.gz",
    "patch_applies": "change.patch",
}


class ProbeError(ValueError):
    """Raised only for malformed input; an unavailable probe returns ABSENT."""


def state_digest(path: pathlib.Path) -> str:
    """Content digest of the visible state, excluding no files."""
    import os
    parts: list[str] = []
    for root, dirs, files in os.walk(path):
        dirs.sort()
        for name in sorted(files):
            target = pathlib.Path(root) / name
            parts.append(str(target.relative_to(path)))
            try:
                parts.append(hashlib.sha256(target.read_bytes()).hexdigest())
            except OSError:
                parts.append("UNREADABLE")
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def run_probe(name: str, path: pathlib.Path, timeout: int = 60) -> dict[str, Any]:
    """Run one read-only probe and return a structured, provenance-bound fact."""
    argv = PROBES.get(name)
    if argv is None:
        raise ProbeError("PROBE_UNKNOWN:" + str(name))
    target = path / PROBE_TARGETS[name]
    if not target.exists():
        return {"schema": SCHEMA, "probe": name, "fact": name + ".absent",
                "read_only": True, "exit_code": None}
    before = state_digest(path)
    try:
        done = subprocess.run(list(argv), cwd=str(path), capture_output=True,
                              text=True, errors="replace", timeout=timeout)
        code = int(done.returncode)
        message = ((done.stdout or "") + (done.stderr or "")).strip()[:200]
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"schema": SCHEMA, "probe": name, "fact": name + ".unavailable",
                "read_only": True, "exit_code": None, "error": str(exc)[:200]}
    after = state_digest(path)
    read_only = before == after
    return {
        "schema": SCHEMA, "probe": name,
        "fact": name + (".valid" if code == 0 else ".invalid"),
        "read_only": read_only, "exit_code": code, "message": message,
    }


def sense(path: pathlib.Path) -> tuple[str, ...]:
    """Facts to add to a state's cheap sensor vocabulary."""
    facts: set[str] = set()
    for name in PROBES:
        result = run_probe(name, path)
        if result["read_only"] is True:
            facts.add(str(result["fact"]))
    return tuple(sorted(facts))


def augment(state: Any, path: pathlib.Path | None = None) -> Any:
    """Attach probe facts to a mutable state record used by the learner."""
    target = path if path is not None else getattr(state, "path", None)
    if target is None:
        raise ProbeError("STATE_PATH_REQUIRED")
    extra = sense(pathlib.Path(target))
    state.facts = tuple(sorted(set(getattr(state, "facts", ())) | set(extra)))
    return state
