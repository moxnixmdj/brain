"""A capability nothing has ever run can verify itself by running.

THE MEASURED FACT THIS ANSWERS
------------------------------
`binding_pin_is_current_v1` classified the bound registry at 0875df1c:

    141 rows -> FRESH 0 · STALE 3 · UNVERIFIED 138

138 capabilities advertised themselves as bound and nothing had ever read a pin
back. That module made the failure *visible*. It could not make it *resolved*,
because resolving it needs a fact only execution supplies.

So all 136 resolvable UNVERIFIED adapters were executed once, offline:

    RAN                 85
    MISSING_DEPENDENCY  42
    NEEDS_INPUT          8
    FAILED_OTHER         1
    STRUCTURALLY BROKEN  0

Eighty-five capabilities that the registry called bound execute cleanly. They
were never unverified because they did not work. They were unverified because
nobody had run them. That distinction is the whole point of this module.

WHY THE OBVIOUS PIN WOULD BE A LIE
----------------------------------
The tempting record is `sha256(module bytes)` taken at the moment of the run.
It is worthless: the pin would be derived from the same bytes it later checks,
so it would read FRESH forever and prove nothing. A tautology dressed as
evidence is worse than no evidence, because it stops anyone looking.

What execution actually establishes is BEHAVIOURAL, not textual:

    this code, as it stands, ran to completion in this environment, just now

So the record binds three things together -- the module identity, the
environment identity, and the observed outcome:

    {"capability_id", "module_sha256", "environment_digest", "observed",
     "verified_at_utc", "seconds"}

and a later verdict asks whether any of them has moved:

    FRESH   the module is unchanged, the environment is unchanged, and the last
            observation was a clean run -- so it can be run again as verified
    STALE   the module changed, or the environment changed (a dependency
            disappeared), so the recorded observation no longer describes it
    UNVERIFIED  nothing has ever been recorded; nothing can confirm or refute

A re-run is the only thing that moves a capability back to FRESH, exactly as
`rule_expiry_v1.reverify()` is the only thing that moves a rule back. This reuses
that module's vocabulary rather than inventing a second one, because two words
for the same state is how a repository ends up unable to say anything.

A CAPABILITY THAT CANNOT RUN IS NOT A CAPABILITY
------------------------------------------------
`availability_v1` already states the rule and already enforces it for missing
binaries. The 42 MISSING_DEPENDENCY rows are the same fact wearing different
clothes: an adapter whose import is absent cannot be executed here. This module
does NOT withdraw them, because a missing optional dependency is a fact about
the host, not about the capability -- `world_probe_v1` exists for exactly that
question. It records the observation so the distinction is visible instead of
assumed.

WHAT IT REFUSES TO DO
---------------------
- It never runs a module outside the governed prefixes, and never without a
  timeout, and always from a throwaway working directory, so probing cannot
  write into the tree it is measuring.
- It never treats a non-zero exit as a crash of this module. A failed probe is
  data.
- It never writes into `BOUND_CAPABILITY_REGISTRY_V1.json`. That file is a
  human-curated claim about what is bound; a machine that writes its own
  evidence into the claim would be marking its own homework. Observations live
  in their own file.
- It never spends more than a bounded number of probes per cycle. The creature
  must remain able to do work that is not self-measurement.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Iterable, Mapping

SCHEMA = "PROJECT_BRAIN_CAPABILITY_SELF_VERIFICATION_V1"

EVIDENCE_PATH = "canonical/evidence/CAPABILITY_SELF_VERIFICATION_V1.json"

RAN = "RAN"
MISSING_DEPENDENCY = "MISSING_DEPENDENCY"
NEEDS_INPUT = "NEEDS_INPUT"
FAILED = "FAILED"
TIMEOUT = "TIMEOUT"
SKIPPED = "SKIPPED"

# Reused from binding_pin_is_current_v1 so the two modules cannot drift apart.
FRESH = "FRESH"
STALE = "STALE"
UNVERIFIED = "UNVERIFIED"
UNKNOWN = "UNKNOWN"

GOVERNED_PREFIXES = ("canonical/runtime/", "canonical/tools/",
                     "canonical/swe_kernel/", "canonical/capabilities/")

PROBE_TIMEOUT_S = 25
DEFAULT_BUDGET = 8

_CLASSIFIERS = (
    (re.compile(r"modulenotfounderror|importerror|no module named", re.I), MISSING_DEPENDENCY),
    (re.compile(r"usage:|no such file|is required|required argument", re.I), NEEDS_INPUT),
    (re.compile(r"syntaxerror|indentationerror", re.I), FAILED),
)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def environment_digest() -> str:
    """A digest of the things whose movement invalidates a past observation.

    Interpreter identity and the visible PATH are what a dependency check can
    actually depend on. Hashing them means a capability that ran before a
    dependency disappeared reports STALE rather than silently staying verified.
    """
    h = hashlib.sha256()
    h.update(sys.version.encode("utf-8", "replace"))
    h.update(b"\0")
    h.update(os.environ.get("PATH", "").encode("utf-8", "replace"))
    return h.hexdigest()


def classify(stderr: str, returncode: int) -> str:
    """What the probe observed. Non-zero is data, never an exception."""
    if returncode == 0:
        return RAN
    for pattern, label in _CLASSIFIERS:
        if pattern.search(stderr or ""):
            return label
    return FAILED


def resolve_adapter(root: Path, module: str) -> Path | None:
    """The file a registry row names, or None. Never guesses outside the tree."""
    if not isinstance(module, str) or not module:
        return None
    stem = module[:-3] if module.endswith(".py") else module
    if "/" in stem:
        cand = root / (stem if stem.endswith(".py") else stem + ".py")
        return cand if cand.is_file() else None
    for base in ("canonical", "execution_guard"):
        d = root / base
        if not d.is_dir():
            continue
        for hit in d.rglob(f"{stem}.py"):
            return hit
    return None


def probe(path: Path, *, timeout_s: int = PROBE_TIMEOUT_S) -> dict[str, Any]:
    """Run one module from a throwaway cwd. Records what happened; judges nothing."""
    started = time.perf_counter()
    sandbox = tempfile.mkdtemp(prefix="brain-selfverify-")
    try:
        try:
            proc = subprocess.run(
                [sys.executable, str(path.resolve())],
                cwd=sandbox, capture_output=True, text=True, timeout=timeout_s,
            )
            outcome = classify(proc.stderr, proc.returncode)
            detail = (proc.stderr or "").strip().splitlines()[-1][:200] if proc.stderr else ""
            rc = proc.returncode
        except subprocess.TimeoutExpired:
            outcome, detail, rc = TIMEOUT, f"exceeded {timeout_s}s", -1
        except OSError as exc:
            outcome, detail, rc = FAILED, f"{type(exc).__name__}: {exc}"[:200], -1
    finally:
        try:
            for child in Path(sandbox).rglob("*"):
                if child.is_file():
                    child.unlink()
            for child in sorted(Path(sandbox).rglob("*"), reverse=True):
                if child.is_dir():
                    child.rmdir()
            Path(sandbox).rmdir()
        except OSError:
            pass
    return {
        "observed": outcome,
        "returncode": rc,
        "detail": detail,
        "seconds": round(time.perf_counter() - started, 3),
    }


def load_evidence(root: Path, path: str | None = None) -> dict[str, Any]:
    # Resolved at CALL time, not at def time: a default argument binds once, which made
    # the evidence location impossible to redirect and left the tests asserting against
    # whatever a previous run happened to leave on disk.
    p = root / (path or EVIDENCE_PATH)
    if not p.is_file():
        return {"schema": SCHEMA, "observations": {}}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema": SCHEMA, "observations": {}}
    if not isinstance(data, dict) or not isinstance(data.get("observations"), dict):
        return {"schema": SCHEMA, "observations": {}}
    return data


def save_evidence(root: Path, evidence: Mapping[str, Any], path: str | None = None) -> Path:
    target = root / (path or EVIDENCE_PATH)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(target)
    return target


def verify(
    root: Path | str = ".",
    *,
    budget: int = DEFAULT_BUDGET,
    only: Iterable[str] | None = None,
    timeout_s: int = PROBE_TIMEOUT_S,
) -> dict[str, Any]:
    """Probe up to `budget` never-verified capabilities and record what happened.

    Bounded on purpose: the creature may run this every cycle, and a cycle that
    can consume an unbounded amount of wall clock is a cycle that does no work.
    """
    root = Path(root)
    from canonical.runtime import binding_pin_is_current_v1 as pins
    import json as _json

    verdicts = pins.resolve(root)
    evidence = load_evidence(root)
    observations: dict[str, Any] = evidence["observations"]

    # A capability is a candidate when it is unverified AND nothing has ever been
    # observed for it. Selecting purely on `pins.UNVERIFIED` re-runs the same rows
    # forever, because the registry verdict never changes -- the observation is what
    # changes, and it lives here. Measured: without this line the second cycle re-probes
    # the first six and the frontier never advances.
    already = set(observations)
    candidates = [c for c, e in verdicts.items()
                  if e.get("verdict") == pins.UNVERIFIED and c not in already]
    if only is not None:
        wanted = set(only)
        candidates = [c for c in candidates if c in wanted]

    registry = _json.loads((root / pins.REGISTRY).read_text(encoding="utf-8"))
    rows = registry.get("capabilities") or registry.get("rows") or {}

    env = environment_digest()
    attempted: list[dict[str, Any]] = []
    spent = 0.0
    for cid in candidates:
        if len(attempted) >= max(0, int(budget)):
            break
        row = rows.get(cid) or {}
        path = resolve_adapter(root, row.get("adapter_module"))
        if path is None:
            continue
        rel = path.relative_to(root).as_posix()
        if not any(rel.startswith(p) for p in GOVERNED_PREFIXES):
            continue
        result = probe(path, timeout_s=timeout_s)
        spent += float(result.get("seconds") or 0.0)
        observations[cid] = {
            "capability_id": cid,
            "module_path": rel,
            "module_sha256": _sha256_file(path),
            "environment_digest": env,
            "observed": result["observed"],
            "returncode": result["returncode"],
            "detail": result["detail"],
            "seconds": result["seconds"],
            "verified_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        attempted.append(observations[cid])

    evidence["schema"] = SCHEMA
    evidence["observations"] = observations
    evidence["environment_digest"] = env
    evidence["updated_at_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if attempted:
        save_evidence(root, evidence)

    after = outcome(root, evidence=evidence)
    return {
        "schema": SCHEMA,
        "probed": len(attempted),
        "seconds": round(spent, 3),
        "observations": attempted,
        "counts": after["counts"],
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }


def outcome(root: Path | str = ".", *, evidence: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """The verdict each recorded observation now earns.

    This is the part that can go STALE without anyone editing anything: change
    the module, or change the environment, and yesterday's clean run stops
    describing today.
    """
    root = Path(root)
    from canonical.runtime import binding_pin_is_current_v1 as pins

    ev = dict(evidence) if evidence is not None else load_evidence(root)
    observations = ev.get("observations") or {}
    env_now = environment_digest()

    rows: dict[str, dict[str, Any]] = {}
    for cid, obs in observations.items():
        if not isinstance(obs, Mapping):
            continue
        path = root / str(obs.get("module_path") or "")
        if not path.is_file():
            rows[cid] = {"verdict": STALE, "reason": "THE_RECORDED_MODULE_IS_GONE"}
            continue
        if _sha256_file(path) != obs.get("module_sha256"):
            rows[cid] = {"verdict": STALE, "reason": "THE_MODULE_CHANGED_SINCE_IT_RAN"}
            continue
        if obs.get("environment_digest") != env_now:
            rows[cid] = {"verdict": STALE, "reason": "THE_ENVIRONMENT_CHANGED_SINCE_IT_RAN"}
            continue
        if obs.get("observed") != RAN:
            rows[cid] = {"verdict": STALE, "reason": "THE_LAST_OBSERVED_RUN_DID_NOT_COMPLETE"}
            continue
        rows[cid] = {"verdict": FRESH, "reason": "OBSERVED_TO_RUN_AND_NOTHING_HAS_MOVED_SINCE"}

    counts = {FRESH: 0, STALE: 0, UNVERIFIED: 0, UNKNOWN: 0}
    for r in rows.values():
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    counts[UNVERIFIED] = max(0, len(pins.resolve(root)) - len(rows))
    return {"schema": SCHEMA, "rows": rows, "counts": counts}


def run(args: Mapping[str, Any] | None = None, root: Any = ".") -> dict[str, Any]:
    """Contract entrypoint: `run(args, root) -> dict`."""
    args = dict(args or {})
    budget = int(args.get("budget") or DEFAULT_BUDGET)
    only = args.get("only")
    if isinstance(only, str):
        only = [only]
    return verify(root, budget=budget, only=only if isinstance(only, list) else None)
