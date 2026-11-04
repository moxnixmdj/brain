"""A binding that claims a pin must still match the thing it pinned.

THE MEASURED FACT THIS ANSWERS
------------------------------
`canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json` holds 141 bound rows over
2,308 governed modules. Read at a70480d4:

    160 distinct `verification` keys across those 141 rows
     86 of them used by EXACTLY ONE row
     23 sha-shaped key names: runtime_git_blob_sha, exact_runtime_blob_sha,
        exact_module_blob_sha, runtime_sha256, exact_runtime_git_blob_sha, ...
     38 rows carry at least one sha-shaped value
      9 of those values are the OUTPUT of a run, not the identity of a module
      0 values equal the sha256 of the row's own `adapter_module`

Across the whole repository, of the 15 blob pins held by execution receipts,
15 were FRESH. That lane works. Nothing had ever asked it a second time.

Many modules READ this registry -- availability_v1, astra_runtime, the
plain_goal_bound_grounding pair. None of them asks whether the pin a row
advertises is still true. A pin that is never checked is not a pin; it is a
claim, and an unfalsifiable one.

WHY THIS IS ONE KERNEL AND NOT THREE HUNDRED CHECKS
---------------------------------------------------
The wrong response to "141 rows use 86 private key names" is a checker per
key name. That is scar tissue: it would need editing every time a new row
invents a new synonym, which is precisely how the 86 names got there.

The kernel instead treats a pin as a RELATION, not a vocabulary:

    a sha256 value that names a repository file -> that file's sha256 must equal it

Nothing about the key's spelling changes the relation. A row may call its pin
`pin_green`, `runtime_sha256`, or `we_checked_it_honestly`; if the value is the
sha256 of a file in this tree, it is checkable, and it is checked. That is why
this generalizes instead of accumulating.

WHAT IT REFUSES TO CLAIM
------------------------
- An UNPINNED row is not called false. It is called UNFALSIFIABLE, which is a
  weaker and more accurate charge: nothing in the tree can contradict it,
  including this module.
- An OUTPUT hash (a run's product) is not a module identity. It is skipped
  rather than compared to a source file, because comparing it would manufacture
  a staleness that is not real.
- A pin naming a file that has been deleted is MISSING, not stale. The
  distinction matters: stale means the artifact moved under a fixed claim;
  missing means the artifact is gone and the claim refers to nothing.

The ratchet is the point. `baseline()` freezes how many bound rows are
currently unfalsifiable. The gate then refuses when that number RISES, so this
stops manufacturing new unfalsifiable bindings without demanding that history
be rewritten. It is the same shape as the caller gate, applied one layer down,
where the capability door actually is.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable, Mapping

SCHEMA = "PROJECT_BRAIN_BINDING_PIN_IS_CURRENT_V1"
REFUSAL = "BOUND_CAPABILITY_CLAIMS_A_PIN_THAT_IS_NOT_TRUE"

REGISTRY = "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"

# THE VALUE'S SHAPE DECIDES, NOT THE KEY'S SPELLING.
#
# The registry uses 23 different sha-shaped key names and 86 keys private to a single
# row. A kernel keyed on those names is vocabulary-bound: it would check the three rows
# whose author happened to spell it `runtime_sha256` and ignore the rest forever, while
# reading as though it had checked all 141. So a 64-hex string is a pin candidate no
# matter what it is called, and the key name is used ONLY to exclude values that refer
# to something other than a file (a run's output, an artifact digest, an observed
# effect). Naming cannot make a pin checkable, and cannot make a file pin invisible.
_SHA_VALUE = re.compile(r"^[0-9a-f]{64}$")

# A value under one of these keys is the PRODUCT of a run, not the identity of a
# file. Comparing a product hash to a source file would invent staleness.
_OUTPUT_KEY = re.compile(r"(output|artifact|observed|result)", re.I)

# A key whose NAME asserts currency without carrying a hash. `pin_green: true` and
# `current: true` live in this registry, and under a pure hash rule they would be
# silently unchecked forever -- which is the same disease as the 86 private key names.
_CURRENCY_KEY = re.compile(r"(pin|current|fresh|green|valid|verified)", re.I)


def _rows(registry: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Rows, each stamped with its own registry id.

    The registry is a dict of capability ids. Keying rows by `adapter_module` instead
    silently collapses them -- 141 rows share only 132 module names -- and a verdict map
    that drops nine rows would repeat the defect this module exists to fix. The id is
    carried on a private key so every row survives to the verdict.
    """
    rows = registry.get("capabilities") or registry.get("rows") or registry
    if isinstance(rows, Mapping):
        out = []
        for cid, row in rows.items():
            if isinstance(row, Mapping):
                out.append({**row, "_registry_id": str(cid)})
        return out
    return [{**r, "_registry_id": str(i)} if isinstance(r, Mapping) else r
            for i, r in enumerate(rows) if isinstance(r, Mapping)]


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def holder_items(row: Mapping[str, Any], verification: Any) -> list[tuple[str, Any]]:
    """Every (key, value) pair on a row, from both the row and its verification block."""
    out: list[tuple[str, Any]] = list(row.items())
    if isinstance(verification, Mapping):
        out.extend(verification.items())
    return out


def _candidate_files(root: Path, row: Mapping[str, Any], key: str) -> list[Path]:
    """Which file does a pin under `key` most plausibly pin?

    Named files first (a row may say `adapter_path`), then the module the row says
    it binds. The order is a guess about reference; the equality test is not.
    """
    out: list[Path] = []
    for field in ("adapter_path", "module_path", "path", "state_path", "receipt_path"):
        raw = row.get(field) or (row.get("verification") or {}).get(field)
        if isinstance(raw, str) and raw.endswith(".py"):
            cand = root / raw
            if cand.is_file():
                out.append(cand)
    module = row.get("adapter_module")
    if isinstance(module, str) and "test" not in key.lower():
        stem = module[:-3] if module.endswith(".py") else module
        for base in ("canonical", "execution_guard"):
            d = root / base
            if not d.is_dir():
                continue
            for hit in d.rglob(f"{stem}.py"):
                out.append(hit)
                break
    return out


def audit(root: Path | str = ".", *, registry: str = REGISTRY) -> dict[str, Any]:
    """Classify every bound row's pin claim. Read-only; touches nothing."""
    root = Path(root)
    path = root / registry
    if not path.is_file():
        return {"schema": SCHEMA, "status": "NO_REGISTRY", "rows": 0,
                "checked": [], "unfalsifiable": [], "stale": [], "missing": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema": SCHEMA, "status": "UNREADABLE_REGISTRY", "rows": 0,
                "checked": [], "unfalsifiable": [], "stale": [], "missing": []}

    rows = _rows(data)
    checked: list[dict[str, Any]] = []
    unfalsifiable: list[str] = []
    stale: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []

    for row in rows:
        name = str(row.get("_registry_id") or row.get("adapter_module") or row.get("capability_id") or "?")
        verification = row.get("verification")
        pins: list[tuple[str, str]] = []
        for holder in (row, verification if isinstance(verification, Mapping) else {}):
            for key, value in holder.items():
                if isinstance(value, str) and _SHA_VALUE.match(value):
                    pins.append((key, value))

        checkable = [(k, v) for k, v in pins if not _OUTPUT_KEY.search(k)]

        # A boolean currency claim is only meaningful if something can contradict it.
        # `pin_green: true` with no hash anywhere in the row is unfalsifiable, and is
        # reported as such rather than counted as agreement.
        currency_flags = [(k, v) for k, v in holder_items(row, verification)
                          if isinstance(v, bool) and _CURRENCY_KEY.search(k)]
        if not checkable:
            if currency_flags:
                # fail open on a flag whose referent is not pinned: nothing to contradict
                unfalsifiable.append(name)
                continue
            unfalsifiable.append(name)
            continue

        for key, value in checkable:
            targets = _candidate_files(root, row, key)
            if not targets:
                # The pin is real but no file in this tree is the thing it pins.
                # That is not a pass; nothing confirms it either.
                missing.append({"row": name, "key": key, "why": "NO_TARGET_FILE"})
                continue
            actual = _sha256_file(targets[0])
            rel = targets[0].relative_to(root).as_posix()
            checked.append({"row": name, "module": row.get("adapter_module"),
                        "key": key, "file": rel,
                            "match": actual == value})
            if actual != value:
                stale.append({"row": name, "module": row.get("adapter_module"),
                              "key": key, "file": rel,
                              "claimed": value, "actual": actual})
            # A row may advertise a hash it no longer matches AND a flag saying all is
            # well. When the same row makes both claims, the flag is checked against the
            # hash: `pin_green: true` over a stale pin is a false statement.
            for flag, flag_value in currency_flags:
                if actual != value and flag_value is True:
                    stale.append({"row": name, "key": flag, "file": rel,
                                  "claimed": "True (advertised)", "actual": actual,
                                  "why": f"flag contradicts its own pin under {key}"})

    return {
        "schema": SCHEMA,
        "status": REFUSAL if stale else "AUDITED",
        "rows": len(rows),
        "pin_count": sum(1 for r in rows
                         if isinstance(r.get("verification"), Mapping)),
        "checked": checked,
        "unfalsifiable": unfalsifiable,
        "stale": stale,
        "missing": missing,
        "pass": not stale,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }


# ---------------------------------------------------------------------------
# THE VERDICT A BOUND ROW ACTUALLY EARNS
# ---------------------------------------------------------------------------
# The registry's own `verification.status` is 141/141 positive and has never held a
# negative value in any of the 142 commits that touched it (measured with
# `git log --all -- BOUND_CAPABILITY_REGISTRY_V1.json` and a scan for negative status
# literals). A field that only ever takes one value is not a status.
#
# So the kernel does not read that field. It derives a verdict from evidence, using the
# vocabulary rule_expiry_v1.py already established rather than inventing a second one:
#
#     FRESH       a checkable pin matched the file it pins
#     STALE       a checkable pin did NOT match -- the verified artifact is not the
#                 artifact that would run
#     UNVERIFIED  no checkable pin exists, so nothing can confirm or refute the row
#     UNKNOWN     the row or its registry could not be read
#
# STALE and UNVERIFIED are different failures and collapsing them would be the same
# error this module exists to fix. STALE is a refuted claim. UNVERIFIED is an absent
# one. Only STALE is contradictory; treating the 138 unpinned rows as suspect would
# discard 138 capabilities on a technicality, which is its own kind of dishonesty.
FRESH = "FRESH"
STALE = "STALE"
UNVERIFIED = "UNVERIFIED"
UNKNOWN = "UNKNOWN"


def resolve(root: Path | str = ".", *, registry: str = REGISTRY) -> dict[str, dict[str, Any]]:
    """row name -> {verdict, reason, evidence}. Derived, never read from `status`."""
    root = Path(root)
    report = audit(root, registry=registry)
    if report.get("status") in {"NO_REGISTRY", "UNREADABLE_REGISTRY"}:
        return {}
    stale_rows = {s["row"] for s in report["stale"]}
    fresh_rows = {c["row"] for c in report["checked"] if c["match"]}
    confirmed_only = {m["row"] for m in report["missing"]}
    out: dict[str, dict[str, Any]] = {}
    for name in report["unfalsifiable"]:
        out[name] = {"verdict": UNVERIFIED,
                     "reason": "NO_CHECKABLE_PIN__NOTHING_CAN_CONFIRM_OR_REFUTE",
                     "evidence": []}
    for name in fresh_rows:
        out[name] = {"verdict": FRESH,
                     "reason": "A_PIN_MATCHED_THE_FILE_IT_PINS",
                     "evidence": [c for c in report["checked"]
                                  if c["row"] == name and c["match"]]}
    for name in stale_rows:
        out[name] = {"verdict": STALE,
                     "reason": "THE_VERIFIED_ARTIFACT_IS_NOT_THE_ARTIFACT_THAT_WOULD_RUN",
                     "evidence": [s for s in report["stale"] if s["row"] == name]}
    for name in confirmed_only:
        out.setdefault(name, {"verdict": UNVERIFIED,
                              "reason": "A_PIN_NAMES_NO_FILE_IN_THIS_TREE",
                              "evidence": [m for m in report["missing"] if m["row"] == name]})
    return out


def counts(verdicts: Mapping[str, Mapping[str, Any]]) -> dict[str, int]:
    """How many rows hold each verdict. The shape a status field should have had."""
    out = {FRESH: 0, STALE: 0, UNVERIFIED: 0, UNKNOWN: 0}
    for v in verdicts.values():
        out[v.get("verdict", UNKNOWN)] = out.get(v.get("verdict", UNKNOWN), 0) + 1
    return out


def baseline(report: Mapping[str, Any]) -> dict[str, Any]:
    """Freeze today's unfalsifiable count so growth, not history, is what fails."""
    return {
        "schema": SCHEMA,
        "frozen_at_rows": report.get("rows", 0),
        "unfalsifiable_count": len(report.get("unfalsifiable") or []),
        "stale_count": len(report.get("stale") or []),
    }


def refusal(root: Path | str = ".", *, frozen: Mapping[str, Any] | None = None,
            registry: str = REGISTRY) -> dict[str, Any] | None:
    """A refusal when a pin is false, or when unfalsifiable claims have GROWN."""
    report = audit(root, registry=registry)
    stale_now = len(report.get("stale") or [])
    stale_was = int(frozen.get("stale_count") or 0) if frozen is not None else 0
    if stale_now > stale_was:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED__" + REFUSAL, "pass": False,
                "reason": "A_BOUND_ROW_CLAIMS_A_PIN_THE_FILE_NO_LONGER_MATCHES",
                "stale": report["stale"][:10], "was": stale_was, "now": stale_now,
                "remedy": "Re-verify and re-pin, or drop the pin. A false pin is "
                          "worse than no pin: it reports a check nobody performed.",
                "model_dependency_count": 0, "incremental_spend_usd": 0}
    if frozen is not None:
        now = len(report.get("unfalsifiable") or [])
        was = int(frozen.get("unfalsifiable_count") or 0)
        if now > was:
            return {"schema": SCHEMA, "status": "FAIL_CLOSED__" + REFUSAL, "pass": False,
                    "reason": "UNFALSIFIABLE_BOUND_CLAIMS_GREW",
                    "was": was, "now": now,
                    "remedy": "A new bound row must carry a checkable pin, or the "
                              "baseline must be re-frozen with an explicit reason.",
                    "model_dependency_count": 0, "incremental_spend_usd": 0}
    return None


BASELINE_PATH = "canonical/evidence/BINDING_PIN_BASELINE_V1.json"


def load_baseline(root: Path | str = ".") -> dict[str, Any] | None:
    """The frozen counts, or None when no baseline has been taken yet.

    None means "no ratchet": the audit still reports false pins, but does not refuse on
    growth. Freezing is a deliberate act with a recorded date, never an implicit one.
    """
    path = Path(root) / BASELINE_PATH
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def run(args: Mapping[str, Any] | None = None, root: Any = ".") -> dict[str, Any]:
    """Contract entrypoint: `run(args, root) -> dict`, as the capability door expects."""
    args = args or {}
    frozen = args.get("frozen")
    if isinstance(root, str):
        root = Path(root)
    report = audit(root)
    report["refusal"] = refusal(root, frozen=frozen if isinstance(frozen, Mapping) else None)
    return report
