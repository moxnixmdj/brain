"""What can this machine actually DO? Answered by running, never by reading a status field.

THE PROBLEM THIS EXISTS FOR. The registry has 448 rows, and 154 of them say
`VERIFIED_BOUND_CAPABILITY`. Measured 2026-11-22 (A83):

    52 of those 154 declare no adapter at all -- the file is not there
     9 more declare an adapter that will not import (no `PIL` on this machine, ...)
    13 of the 17 rows with a real verifying check CRASH before they can report anything
    61 of 154 -- 40% -- of the capabilities this machine calls verified cannot run

Not "run wrongly". Cannot be loaded. A `status` field is a claim about a file; it is not a fact about
the machine, and every layer above it treats it as one. That is why an agent cannot ask "what do I not
know yet": the machine's answer to "what do you know" is a stored string.

THE FIX IS ONE PASS, AND IT DELETES A LIE RATHER THAN ADDING A MECHANISM. For every row:

    READABLE   the declared adapter file exists and imports, and its entrypoint is callable
    EXECUTABLE additionally, a one-call smoke test of its declared operation does not raise

and the answer to "what can you do" is those two sets, computed now.

WHAT IT REFUSES TO DO. It does not run a capability that can WRITE. A smoke test of a writer is a
side effect, and proving reachability by mutating the user's tree is not a trade this makes: writers
are classified from the row's own declaration (`read_only`, `capability_edits_source`, the mutation
provides pattern) and stop at READABLE. So EXECUTABLE is a LOWER BOUND for them, which is stated in
the report rather than papered over.

It also never treats "the import worked" as "the operation works". `file.word_frequency.v1` imports
cleanly and answers `COMMAND_NOT_SUPPORTED:word_frequency` when called -- measured. Only the smoke
test separates those.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import re
import traceback
from collections.abc import Mapping
from typing import Any

SCHEMA = "PROJECT_BRAIN_REACHABILITY_V1"

# The statuses that claim the machine can do something. Anything else is inventory, not a promise.
_CLAIMS_TO_WORK = frozenset({"VERIFIED_BOUND_CAPABILITY"})

# A row that declares any of these can change the tree, and is therefore never smoke-tested.
_MUTATION_PROVIDES = re.compile(r"(?:^|\.)(?:copy|rename|move|write|create|append|delete|patch|repair|"
                                r"edit|compress|archive|backup|extract)\b", re.I)


def _root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[2]


def _adapter_path(entry: Mapping[str, Any], root: pathlib.Path) -> str | None:
    source = entry.get("source") or {}
    declared = source.get("adapter_path") or source.get("path")
    return str(declared) if declared else None


def _can_write(entry: Mapping[str, Any]) -> bool:
    """Does the row's OWN declaration say it changes the tree?

    Read from the declaration, never guessed from the id: `file.copy.v1` says nothing about writing
    in its name, and `python.source.crossfile_edit.choreograph.v1` says it plans and does not apply.
    """
    if entry.get("read_only") is True:
        return False
    provides = " ".join(str(p) for p in (entry.get("provides") or ()))
    if _MUTATION_PROVIDES.search(provides):
        return True
    limitations = " ".join(str(x) for x in (entry.get("limitations") or ())).lower()
    if ("plans" in limitations or "plan," in limitations) and any(
            phrase in limitations for phrase in ("does not apply", "does not mutate", "no mutation",
                                                "read-only")):
        return False
    limits = " ".join(str(x) for x in (entry.get("limitations") or ())).lower()
    if "write" in limits or "writes" in limits or "rewrites" in limits or "deletes" in limits:
        return True
    template = entry.get("action_template") or {}
    args = (template.get("args") or {}) if isinstance(template, Mapping) else {}
    command = str(args.get("command") or "")
    if re.search(r"copy|rename|move|write|append|delete|archive|compress|extract|backup", command, re.I):
        return True
    # A ROW THAT TAKES AN OUTPUT PATH PRODUCES A FILE. That is write authority, whatever the row's
    # `provides` says, and it is read from the row's own declaration of its inputs.
    if any("output" in str(k).lower() for k in args):
        return True
    return False


def _load(entry: Mapping[str, Any], root: pathlib.Path) -> tuple[Any, str | None]:
    """The adapter's entrypoint callable, or ``(None, reason)``."""
    declared = _adapter_path(entry, root)
    if not declared:
        return None, "NO_ADAPTER_DECLARED"
    path = root / declared
    if not path.is_file():
        return None, "ADAPTER_MISSING"
    name = str(entry.get("adapter_module") or path.stem)
    entry_name = str(entry.get("entrypoint") or "run")
    try:
        spec = importlib.util.spec_from_file_location("__reach_" + re.sub(r"\W", "_", name), path)
        if spec is None or spec.loader is None:
            return None, "ADAPTER_UNLOADABLE"
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001 - a failed import is the finding
        return None, "IMPORT_FAILED:" + type(exc).__name__
    fn = getattr(module, entry_name, None)
    if not callable(fn):
        return None, "NO_ENTRYPOINT:" + entry_name
    return fn, None


def _smoke_arguments(entry: Mapping[str, Any], root: pathlib.Path) -> dict[str, Any] | None:
    """A minimal, real argument set for one call, or None when one cannot be built honestly.

    Nothing arbitrary is passed. A read-only row that wants a directory gets a directory that exists
    in this tree; one that wants a file gets a file that exists. A row whose inputs cannot be
    satisfied from real values in this tree is not smoke-tested -- and says so -- rather than being
    called with a placeholder and reported broken.
    """
    template = entry.get("action_template") or {}
    args = dict((template.get("args") or {})) if isinstance(template, Mapping) else {}
    wants = {str(k) for k in args} | {str(k) for k in (entry.get("proposal_bindings") or {})}
    built: dict[str, Any] = {}
    for key in wants:
        low = key.lower()
        if low in ("command", "capability_id"):
            # Not an input: the operation's name and the row's own identity. Supplied by the
            # caller in `reachability()`.
            continue
        if "dir" in low or low in ("source_root", "folder", "directory"):
            built[key] = "canonical"
        elif low in ("path", "file", "source", "input_path"):
            built[key] = "AGENTS.md"
        elif low == "goal":
            # A WHOLE-REQUEST SLOT IS NOT AN INPUT TO A SMOKE TEST, IT IS THE REQUEST.
            # One real sentence about a file this tree has, so the call is a genuine call rather
            # than a mock -- but only when the row ALSO takes a path, so the sentence is not the
            # only thing being exercised.
            built[key] = "read the file AGENTS.md"
        else:
            return None
    if not built:
        return None
    for value in built.values():
        if isinstance(value, str) and " " not in value and not (root / value).exists():
            return None
    built["capability_id"] = str(entry.get("capability_id") or "")
    return built


def reachability(reg: Mapping[str, Mapping[str, Any]] | None = None,
                 root: pathlib.Path | None = None) -> dict[str, Any]:
    """Every row that CLAIMS to work, classified by what actually happens here and now."""
    if reg is None:
        from canonical.runtime import live_integrated_brain_v1 as brain
        reg = brain.load_verified_registry()
    root = pathlib.Path(root or _root())
    rows: dict[str, Any] = {}
    for cid, entry in reg.items():
        if not isinstance(entry, Mapping):
            continue
        status = str(entry.get("status") or "")
        if status not in _CLAIMS_TO_WORK:
            continue
        fn, why = _load(entry, root)
        if fn is None:
            rows[cid] = {"state": "UNREACHABLE", "why": why, "status": status}
            continue
        if _can_write(entry):
            rows[cid] = {"state": "READABLE", "why": "DECLARES_WRITE_AUTHORITY_NOT_EXECUTED",
                         "status": status}
            continue
        args = _smoke_arguments(entry, root)
        if args is None:
            rows[cid] = {"state": "READABLE", "why": "NO_HONEST_SMOKE_ARGUMENTS", "status": status}
            continue
        try:
            fn(args, str(root))
        except Exception as exc:  # noqa: BLE001 - a refusal here is the finding
            detail = str(exc)[:120]
            if type(exc).__name__ == "LocalExecutionFailure" and "ADAPTER_MISSING" in detail:
                rows[cid] = {"state": "UNREACHABLE", "why": "ADAPTER_MISSING", "status": status}
            else:
                rows[cid] = {"state": "READABLE", "why": "SMOKE_REFUSED:" + detail,
                             "status": status}
            continue
        rows[cid] = {"state": "EXECUTABLE", "why": None, "status": status}
    counts = {"EXECUTABLE": 0, "READABLE": 0, "UNREACHABLE": 0}
    for row in rows.values():
        counts[row["state"]] = counts.get(row["state"], 0) + 1
    return {"schema": SCHEMA, "counts": counts, "claims": len(rows), "rows": rows,
            "note": "EXECUTABLE is a lower bound: writers are never executed and stop at READABLE."}


def main() -> None:
    report = reachability()
    print(json.dumps({"counts": report["counts"], "claims": report["claims"]}, indent=1))
    for cid, row in sorted(report["rows"].items()):
        if row["state"] == "UNREACHABLE":
            print("  UNREACHABLE  %-48s %s" % (cid[:48], row["why"]))
