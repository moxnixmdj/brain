#!/usr/bin/env python3
"""Agent orientation: the fixed minimum every agent must know before acting on Project Brain.

Three commands, stdlib only, no network, no model:

  brief                      print the orientation card from the LIVE canon (objective,
                             permanent prohibitions, progress classes, route order, current
                             law versions, honest state numbers, contract sha256).
  verify                     fail closed unless the contract, the root README and the cited
                             laws agree byte-for-byte (objective verbatim, every prohibition
                             quote present in its law file, every cited law current).
  intent-check <intent.json> fail closed unless the action intent carries a valid
                             ``agent_orientation`` block acknowledging the live contract.

The same ``orientation_errors`` function is called by the load-bearing admission gate
(``execution_guard/enforce_load_bearing_primary_pr.py``) for every action intent a pull
request adds or changes, so no agent can land a consequential change without stating the
objective verbatim, the progress class it claims, the route class it chose, zero model
dependency and zero spend.  This file grants no credit and changes no scoreboard.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

SCHEMA = "PROJECT_BRAIN_AGENT_ORIENTATION_CHECK_V1"
CONTRACT_PATH = "canonical/governance/AGENT_ORIENTATION_CONTRACT_V1.json"
README_PATH = "README.md"
INTENT_FIELD = "agent_orientation"
MIN_EXHAUSTION_REASON_CHARS = 40
_VERSION_RE = re.compile(r"^(?P<family>.+)_V(?P<version>\d+)\.md$")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_text(root: Path, rel: str) -> str | None:
    try:
        return (root / rel).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _load_json(root: Path, rel: str) -> Any:
    text = _read_text(root, rel)
    if text is None:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def load_contract(root: Path) -> tuple[dict[str, Any] | None, str | None]:
    """Return (contract, sha256 of the contract bytes) or (None, None)."""
    try:
        raw = (root / CONTRACT_PATH).read_bytes()
    except OSError:
        return None, None
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, None
    if not isinstance(data, Mapping):
        return None, None
    return dict(data), _sha256(raw)


# --------------------------------------------------------------------------- law versions

def law_version_table(root: Path) -> dict[str, dict[str, Any]]:
    """Map law family -> {current, current_version, superseded_status, history[]}.

    Rule (contract.current_laws.rule): the highest version number in a family is current;
    a file whose ``Status:`` line says SUPERSEDED is never current.
    """
    laws_dir = root / "canonical" / "laws"
    families: dict[str, list[tuple[int, str]]] = {}
    for p in sorted(laws_dir.glob("*.md")):
        m = _VERSION_RE.match(p.name)
        if not m:
            families.setdefault(p.stem, []).append((0, p.name))
            continue
        families.setdefault(m.group("family"), []).append((int(m.group("version")), p.name))
    table: dict[str, dict[str, Any]] = {}
    for family, items in families.items():
        items.sort()
        version, name = items[-1]
        status_line = _status_line(root, "canonical/laws/" + name)
        table[family] = {
            "current": "canonical/laws/" + name,
            "current_version": version,
            "status": status_line,
            "current_is_superseded": "SUPERSEDED" in status_line.upper(),
            "history": ["canonical/laws/" + n for _, n in items[:-1]],
        }
    return table


def _status_line(root: Path, rel: str) -> str:
    text = _read_text(root, rel) or ""
    for line in text.splitlines():
        if line.strip().lower().startswith("status:"):
            return " ".join(line.strip().split())
    return ""


def is_current_law(root: Path, rel: str) -> tuple[bool, str]:
    """A cited law is current when it is the highest version of its family and not superseded."""
    name = Path(rel).name
    if rel == "AGENTS.md":
        return (root / rel).is_file(), "repository agent contract"
    m = _VERSION_RE.match(name)
    family = m.group("family") if m else Path(name).stem
    row = law_version_table(root).get(family)
    if row is None:
        return False, "unknown law family"
    if row["current"] != rel:
        return False, "superseded by " + row["current"]
    if row["current_is_superseded"]:
        return False, "status line says SUPERSEDED"
    return True, row["status"]


# --------------------------------------------------------------------------- verify

def verify_errors(root: Path) -> list[str]:
    """Contract <-> canon <-> README consistency. Empty list means consistent."""
    errors: list[str] = []
    contract, sha = load_contract(root)
    if contract is None:
        return ["ORIENTATION_CONTRACT_MISSING_OR_INVALID:" + CONTRACT_PATH]
    obj = contract.get("objective") if isinstance(contract.get("objective"), Mapping) else {}
    source = _load_json(root, str(obj.get("source", "")))
    if not isinstance(source, Mapping):
        errors.append("OBJECTIVE_SOURCE_UNREADABLE:" + str(obj.get("source")))
    else:
        for field_key, verbatim_key in (
            ("field", "verbatim"),
            ("terminality_field", "terminality_verbatim"),
            ("opus_5_5_role_field", "opus_5_5_role_verbatim"),
            ("spend_rule_field", "spend_rule_verbatim"),
        ):
            field = str(obj.get(field_key, ""))
            if source.get(field) != obj.get(verbatim_key):
                errors.append("OBJECTIVE_FIELD_DRIFT:" + field)
    prohibitions = contract.get("permanent_prohibitions")
    if not isinstance(prohibitions, list) or not prohibitions:
        errors.append("PROHIBITIONS_MISSING")
        prohibitions = []
    seen_ids: set[str] = set()
    for row in prohibitions:
        if not isinstance(row, Mapping):
            errors.append("PROHIBITION_ROW_INVALID")
            continue
        pid, law, quote = str(row.get("id", "")), str(row.get("law", "")), str(row.get("quote", ""))
        if not pid or pid in seen_ids:
            errors.append("PROHIBITION_ID_INVALID_OR_DUPLICATE:" + pid)
        seen_ids.add(pid)
        text = _read_text(root, law)
        if text is None:
            errors.append("PROHIBITION_LAW_MISSING:" + pid + ":" + law)
            continue
        if not quote or quote not in text:
            errors.append("PROHIBITION_QUOTE_NOT_VERBATIM_IN_LAW:" + pid)
        current, why = is_current_law(root, law)
        if not current:
            errors.append("PROHIBITION_CITES_NON_CURRENT_LAW:" + pid + ":" + why)
    for row in contract.get("no_longer_true_do_not_repeat") or []:
        if not isinstance(row, Mapping):
            continue
        text = _read_text(root, str(row.get("by", "")))
        if text is None or str(row.get("quote", "")) not in text:
            errors.append("SUPERSESSION_QUOTE_NOT_VERBATIM:" + str(row.get("claim", ""))[:60])
    progress = contract.get("progress") if isinstance(contract.get("progress"), Mapping) else {}
    classes = progress.get("classes")
    if not isinstance(classes, Mapping) or len(classes) < 4:
        errors.append("PROGRESS_CLASSES_MISSING")
    law_text = _read_text(root, str(progress.get("law", ""))) or ""
    for key in ("not_progress_quote",):
        if str(progress.get(key, "")) not in law_text:
            errors.append("PROGRESS_QUOTE_NOT_VERBATIM:" + key)
    dev_law = _read_text(root, "canonical/laws/GENERAL_CAPABILITY_FIRST_DEVELOPMENT_LAW_V1.md") or ""
    for key in ("route_order_quote", "development_loop_quote"):
        if str(contract.get(key, "")) not in dev_law:
            errors.append("QUOTE_NOT_VERBATIM:" + key)
    route_order = contract.get("route_order")
    if not isinstance(route_order, list) or " -> ".join(route_order) + "." != contract.get("route_order_quote"):
        errors.append("ROUTE_ORDER_DOES_NOT_MATCH_QUOTE")
    current_laws = contract.get("current_laws") if isinstance(contract.get("current_laws"), Mapping) else {}
    must_read = current_laws.get("must_read_before_consequential_action")
    if not isinstance(must_read, list) or not must_read:
        errors.append("MUST_READ_LIST_MISSING")
        must_read = []
    for rel in must_read:
        rel = str(rel)
        if not (root / rel).is_file():
            errors.append("MUST_READ_PATH_MISSING:" + rel)
        elif rel.startswith("canonical/laws/"):
            current, why = is_current_law(root, rel)
            if not current:
                errors.append("MUST_READ_CITES_NON_CURRENT_LAW:" + rel + ":" + why)
    for key, rel in (contract.get("live_state_sources") or {}).items():
        if not (root / str(rel)).is_file():
            errors.append("LIVE_STATE_SOURCE_MISSING:" + str(key))
    for rel in must_read:
        if str(rel).startswith("canonical/laws/") and _read_text(root, str(rel)) is None:
            errors.append("LAW_UNREADABLE:" + str(rel))
    errors.extend(readme_errors(root, contract))
    return sorted(set(errors))


def readme_errors(root: Path, contract: Mapping[str, Any]) -> list[str]:
    """The root README must carry the same objective, prohibitions, classes and route order."""
    text = _read_text(root, README_PATH)
    if text is None:
        return ["README_MISSING:" + README_PATH]
    errors: list[str] = []
    obj = contract.get("objective") if isinstance(contract.get("objective"), Mapping) else {}
    for key in ("verbatim", "terminality_verbatim", "opus_5_5_role_verbatim"):
        if str(obj.get(key, "")) not in text:
            errors.append("README_MISSING_OBJECTIVE_TEXT:" + key)
    for row in contract.get("permanent_prohibitions") or []:
        if isinstance(row, Mapping) and str(row.get("id", "")) not in text:
            errors.append("README_MISSING_PROHIBITION:" + str(row.get("id", "")))
    progress = contract.get("progress") if isinstance(contract.get("progress"), Mapping) else {}
    for name in (progress.get("classes") or {}):
        if str(name) not in text:
            errors.append("README_MISSING_PROGRESS_CLASS:" + str(name))
    if str(progress.get("not_progress_quote", "")) not in text:
        errors.append("README_MISSING_NOT_PROGRESS_QUOTE")
    if str(contract.get("route_order_quote", "")) not in text:
        errors.append("README_MISSING_ROUTE_ORDER")
    if "agent_orientation_check_v1.py brief" not in text:
        errors.append("README_MISSING_BRIEF_COMMAND")
    if CONTRACT_PATH not in text:
        errors.append("README_MISSING_CONTRACT_PATH")
    return errors


# --------------------------------------------------------------------------- intent check

def orientation_errors(
    intent: Any,
    contract: Mapping[str, Any] | None,
    contract_sha256: str | None,
    changed_paths: Iterable[str] = (),
    path_exists: Callable[[str], bool] | None = None,
) -> list[str]:
    """Validate the ``agent_orientation`` block of an action intent against the live contract.

    ``contract``/``contract_sha256`` must come from the trusted base tree (the gate reads
    them with ``git show <base>:...``), never from the pull request head.  ``changed_paths``
    are the paths the pull request touches; ``path_exists`` answers for the head tree.  When
    ``changed_paths`` is empty the diff requirement is skipped (local pre-flight).
    """
    if contract is None or not contract_sha256:
        return ["ORIENTATION_CONTRACT_UNAVAILABLE"]
    if not isinstance(intent, Mapping):
        return ["ORIENTATION_INTENT_INVALID"]
    block = intent.get(INTENT_FIELD)
    if not isinstance(block, Mapping):
        return ["ORIENTATION_BLOCK_MISSING:" + INTENT_FIELD]
    errors: list[str] = []
    if block.get("contract") != CONTRACT_PATH:
        errors.append("ORIENTATION_CONTRACT_PATH_MISMATCH")
    if block.get("contract_sha256") != contract_sha256:
        errors.append("ORIENTATION_CONTRACT_SHA_MISMATCH:expected:" + contract_sha256)
    obj = contract.get("objective") if isinstance(contract.get("objective"), Mapping) else {}
    if block.get("objective_verbatim") != obj.get("verbatim"):
        errors.append("ORIENTATION_OBJECTIVE_NOT_VERBATIM")
    progress = contract.get("progress") if isinstance(contract.get("progress"), Mapping) else {}
    classes = progress.get("classes") if isinstance(progress.get("classes"), Mapping) else {}
    progress_class = block.get("progress_class")
    if progress_class not in classes:
        errors.append("ORIENTATION_PROGRESS_CLASS_INVALID")
    elif progress_class == "GOVERNANCE_GUARD_NO_PROGRESS_CLAIM" and intent.get("action_kind") != "GOVERNANCE_GUARD":
        errors.append("ORIENTATION_NO_PROGRESS_CLASS_ONLY_FOR_GOVERNANCE_GUARD")
    evidence = block.get("progress_evidence_paths")
    if not isinstance(evidence, list) or not evidence or any(not isinstance(x, str) or not x.strip() for x in evidence):
        errors.append("ORIENTATION_EVIDENCE_PATHS_MISSING")
    else:
        if path_exists is not None:
            missing = [x for x in evidence if not path_exists(x)]
            if missing:
                errors.append("ORIENTATION_EVIDENCE_PATH_NOT_IN_HEAD:" + ",".join(sorted(missing)))
        changed = set(changed_paths)
        if changed and not (set(evidence) & changed):
            errors.append("ORIENTATION_EVIDENCE_NOT_CHANGED_BY_THIS_PR")
    route_order = contract.get("route_order") if isinstance(contract.get("route_order"), list) else []
    route_class = block.get("route_class")
    if route_class not in route_order:
        errors.append("ORIENTATION_ROUTE_CLASS_INVALID")
    elif route_class == "SYNTHESIZE_NEW_PRIMITIVE":
        reason = block.get("earlier_routes_exhausted_reason")
        if not isinstance(reason, str) or len(reason.strip()) < MIN_EXHAUSTION_REASON_CHARS:
            errors.append("ORIENTATION_EARLIER_ROUTES_EXHAUSTED_REASON_REQUIRED")
    count = block.get("producer_cognition_model_dependency_count")
    if isinstance(count, bool) or count != 0:
        errors.append("ORIENTATION_MODEL_DEPENDENCY_COUNT_NOT_ZERO")
    spend = block.get("incremental_spend_usd")
    if isinstance(spend, bool) or spend != 0:
        errors.append("ORIENTATION_INCREMENTAL_SPEND_NOT_ZERO")
    if block.get("conversation_memory_is_authority") is not False:
        errors.append("ORIENTATION_CONVERSATION_MEMORY_MUST_BE_DECLARED_NON_AUTHORITY")
    current_laws = contract.get("current_laws") if isinstance(contract.get("current_laws"), Mapping) else {}
    must_read = [str(x) for x in (current_laws.get("must_read_before_consequential_action") or [])]
    read = block.get("laws_read_this_session")
    if not isinstance(read, list):
        errors.append("ORIENTATION_LAWS_READ_MISSING")
    else:
        unread = sorted(set(must_read) - {str(x) for x in read})
        if unread:
            errors.append("ORIENTATION_MUST_READ_NOT_ACKNOWLEDGED:" + ",".join(unread))
    markers = [str(m).upper() for m in (contract.get("forbidden_selected_route_markers") or [])]
    for key in ("selected_route", "selected_surviving_route", "route", "chosen_route"):
        value = intent.get(key)
        if isinstance(value, str) and any(m in value.upper() for m in markers):
            errors.append("ORIENTATION_FORBIDDEN_ROUTE_SELECTED:" + key)
    return sorted(set(errors))


# --------------------------------------------------------------------------- brief

def _count(value: Any) -> int:
    return len(value) if isinstance(value, (list, dict)) else 0


def live_state(root: Path, contract: Mapping[str, Any]) -> dict[str, Any]:
    """Honest numbers read from the live canon. Nothing here is a capability claim."""
    src = contract.get("live_state_sources") if isinstance(contract.get("live_state_sources"), Mapping) else {}
    out: dict[str, Any] = {}
    authority = _load_json(root, str(src.get("terminal_authority", "")))
    if isinstance(authority, Mapping):
        truth = authority.get("truth") if isinstance(authority.get("truth"), Mapping) else {}
        out["terminal_truth_achieved"] = truth.get("achieved")
        out["terminal_authority_evaluated"] = authority.get("evaluated_utc") or authority.get("date")
    matrix = _load_json(root, str(src.get("ownership_matrix", "")))
    if isinstance(matrix, Mapping) and isinstance(matrix.get("rows"), list):
        hist: dict[str, int] = {}
        for row in matrix["rows"]:
            if isinstance(row, Mapping):
                hist[str(row.get("status"))] = hist.get(str(row.get("status")), 0) + 1
        out["ownership_matrix_families"] = len(matrix["rows"])
        out["ownership_matrix_status_histogram"] = dict(sorted(hist.items()))
    ledger = _load_json(root, str(src.get("true_capability_ledger", "")))
    if isinstance(ledger, Mapping):
        raw_rows = ledger.get("rows")
        rows = list(raw_rows.values()) if isinstance(raw_rows, Mapping) else (raw_rows if isinstance(raw_rows, list) else [])
        out["true_capability_ledger_rows"] = len(rows)
        out["true_capability_ledger_statuses"] = sorted({str(r.get("status")) for r in rows if isinstance(r, Mapping)})
        out["true_capability_ledger_authority"] = ledger.get("authority")
    audit = _load_json(root, str(src.get("true_capability_audit", "")))
    if isinstance(audit, Mapping):
        summary = audit.get("summary") if isinstance(audit.get("summary"), Mapping) else {}
        out["true_capability_audit_summary"] = summary or {k: audit.get(k) for k in ("verdict", "status") if k in audit}
    baseline = _load_json(root, str(src.get("honest_suite_baseline", "")))
    if isinstance(baseline, Mapping):
        totals = baseline.get("totals") if isinstance(baseline.get("totals"), Mapping) else {}
        out["honest_suite_totals"] = totals
    registry = _load_json(root, str(src.get("bound_capability_registry", "")))
    if isinstance(registry, Mapping):
        caps = registry.get("capabilities") or registry.get("entries") or registry.get("bound_capabilities")
        out["bound_capability_registry_entries"] = _count(caps)
    quotient = _load_json(root, str(src.get("open_obligations", "")))
    if isinstance(quotient, Mapping):
        open_ids = _open_obligation_ids(quotient)
        out["open_obligation_ids"] = len(open_ids)
    return out


def _open_obligation_ids(quotient: Mapping[str, Any]) -> list[str]:
    """Same field the load-bearing gate reads: ``independent_open_obligations``."""
    value = quotient.get("independent_open_obligations")
    if not isinstance(value, list):
        return []
    return sorted({x.strip() for x in value if isinstance(x, str) and x.strip()})


OWNER_GOAL_PATH = "canonical/governance/OWNER_ACTIVE_GOAL_20261018_V1.md"


def _owner_active_goal_lines(root: Path) -> list[str]:
    """The owner's current active goal, in the owner's own words, printed by `brief`.

    The objective was lost to session condensation four times, and each loss produced real
    misdirected work (most recently: an agent chased the alive-mass instrument reading and
    presented it as the mission). A summary is not durable; the place the agent is already
    required to look is. If this file ever goes missing, `brief` says so loudly instead of
    going quiet -- a missing goal must never look like a satisfied one.
    """
    path = root / OWNER_GOAL_PATH
    if not path.is_file():
        return [
            "CURRENT ACTIVE GOAL: MISSING -- " + OWNER_GOAL_PATH,
            "  The owner's active goal is not in the tree. Do not proceed on a remembered",
            "  or inferred version of it. Restore the file or ask the owner.",
            "",
        ]
    try:
        body = path.read_text(encoding="utf-8")
    except OSError as exc:
        return ["CURRENT ACTIVE GOAL: UNREADABLE -- " + str(exc), ""]
    lines = [
        "CURRENT ACTIVE GOAL (owner's own words, " + OWNER_GOAL_PATH + "):",
        "  This IS the mission. It is not a benchmark, a task, or an instrument reading.",
        "  Instrument readings are READ, never CHASED.",
    ]
    keep = False
    for raw in body.splitlines():
        if raw.startswith("## 1. What I want"):
            keep = True
        if raw.startswith("## 5. What this decomposes"):
            break
        if keep:
            lines.append("  " + raw.rstrip())
    lines.append("")
    return lines


def brief_text(root: Path) -> str:
    contract, sha = load_contract(root)
    lines: list[str] = []
    add = lines.append
    add("PROJECT BRAIN - AGENT ORIENTATION BRIEF (read before any consequential action)")
    add("=" * 78)
    if contract is None:
        add("CONTRACT MISSING OR INVALID: " + CONTRACT_PATH)
        return "\n".join(lines)
    obj = contract.get("objective") if isinstance(contract.get("objective"), Mapping) else {}
    add("OBJECTIVE (verbatim, " + str(obj.get("source")) + "):")
    add("  " + str(obj.get("verbatim")))
    add("  terminality: " + str(obj.get("terminality_verbatim")))
    add("  Opus 5.5:    " + str(obj.get("opus_5_5_role_verbatim")))
    add("  spend rule:  " + str(obj.get("spend_rule_verbatim")))
    add("  plain:       " + str(obj.get("plain")))
    add("")
    for row in _owner_active_goal_lines(root):
        add(row)
    add("WHAT BRAIN IS:")
    for row in contract.get("what_brain_is") or []:
        add("  - " + str(row))
    add("")
    add("PERMANENT PROHIBITIONS (verbatim law text; only the owner can rescind):")
    for row in contract.get("permanent_prohibitions") or []:
        if isinstance(row, Mapping):
            add("  [" + str(row.get("id")) + "] " + str(row.get("quote")))
            add("      law:   " + str(row.get("law")))
            add("      plain: " + str(row.get("plain")))
    add("")
    add("NO LONGER TRUE - DO NOT REPEAT:")
    for row in contract.get("no_longer_true_do_not_repeat") or []:
        if isinstance(row, Mapping):
            add("  x " + str(row.get("claim")) + "  -> " + str(row.get("status")) + " by " + str(row.get("by")))
    add("")
    progress = contract.get("progress") if isinstance(contract.get("progress"), Mapping) else {}
    add("PROGRESS CLASSES (the only things that count as a step):")
    for name, meaning in (progress.get("classes") or {}).items():
        add("  " + str(name) + ": " + str(meaning))
    add("  NOT progress: " + str(progress.get("not_progress_quote")))
    add("")
    add("ROUTE ORDER: " + str(contract.get("route_order_quote")))
    add("LOOP:        " + str(contract.get("development_loop_quote")))
    add("SCHEDULER:   " + str(contract.get("scheduler_objective_plain")))
    add("")
    add("CURRENT LAW VERSIONS (highest version per family is current; lower versions are history):")
    table = law_version_table(root)
    must_read = ((contract.get("current_laws") or {}).get("must_read_before_consequential_action") or [])
    for family in sorted(table):
        row = table[family]
        flag = "SUPERSEDED-DO-NOT-CITE" if row["current_is_superseded"] else ("MUST-READ" if row["current"] in must_read else "")
        hist = (" (history: " + ", ".join(Path(h).name for h in row["history"]) + ")") if row["history"] else ""
        add("  " + Path(row["current"]).name + "  " + flag + hist)
    add("")
    add("LIVE STATE (read from the canon now; none of this is a capability claim):")
    for key, value in live_state(root, contract).items():
        add("  " + key + ": " + json.dumps(value, sort_keys=True))
    add("")
    add("KNOWN TRAPS:")
    for row in contract.get("known_traps") or []:
        add("  - " + str(row))
    add("")
    add("MERGE RULE: " + str(contract.get("merge_rule")))
    add("")
    add("BEFORE ANY CONSEQUENTIAL ACTION:")
    for i, row in enumerate(contract.get("before_any_consequential_action") or [], 1):
        add("  " + str(i) + ". " + str(row))
    add("")
    add("ACTION-INTENT BLOCK `" + INTENT_FIELD + "` (required by the load-bearing admission gate):")
    add(json.dumps(example_block(contract, sha or ""), indent=2))
    add("")
    add("contract_sha256 (paste into the intent block): " + str(sha))
    verify = verify_errors(root)
    add("verify: " + ("CONSISTENT" if not verify else "INCONSISTENT " + json.dumps(verify)))
    return "\n".join(lines)


def example_block(contract: Mapping[str, Any], sha: str) -> dict[str, Any]:
    obj = contract.get("objective") if isinstance(contract.get("objective"), Mapping) else {}
    current_laws = contract.get("current_laws") if isinstance(contract.get("current_laws"), Mapping) else {}
    return {
        "contract": CONTRACT_PATH,
        "contract_sha256": sha,
        "objective_verbatim": obj.get("verbatim"),
        "progress_class": "<one of: " + ", ".join((contract.get("progress") or {}).get("classes", {}).keys()) + ">",
        "progress_evidence_paths": ["<repository path changed by this PR that carries the evidence>"],
        "route_class": "<one of: " + ", ".join(contract.get("route_order") or []) + ">",
        "earlier_routes_exhausted_reason": "<required when route_class is SYNTHESIZE_NEW_PRIMITIVE>",
        "producer_cognition_model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "conversation_memory_is_authority": False,
        "laws_read_this_session": list(current_laws.get("must_read_before_consequential_action") or []),
    }


# --------------------------------------------------------------------------- CLI

def _repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / CONTRACT_PATH).is_file() or (candidate / ".git").exists():
            return candidate
    return start


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    root = _repo_root(Path.cwd().resolve())
    if "--root" in args:
        i = args.index("--root")
        root = Path(args[i + 1]).resolve()
        del args[i:i + 2]
    command = args[0] if args else "brief"
    if command == "brief":
        print(brief_text(root))
        return 0
    if command == "verify":
        errors = verify_errors(root)
        print(json.dumps({"schema": SCHEMA, "command": "verify", "ok": not errors, "errors": errors}, indent=2))
        return 0 if not errors else 1
    if command == "intent-check":
        if len(args) < 2:
            print("usage: agent_orientation_check_v1.py intent-check <intent.json>", file=sys.stderr)
            return 2
        intent_path = Path(args[1])
        try:
            intent = json.loads(intent_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(json.dumps({"schema": SCHEMA, "command": "intent-check", "ok": False, "errors": ["INTENT_UNREADABLE:" + str(exc)]}))
            return 1
        contract, sha = load_contract(root)
        errors = orientation_errors(intent, contract, sha, (), lambda rel: (root / rel).exists())
        print(json.dumps({"schema": SCHEMA, "command": "intent-check", "intent": str(intent_path), "ok": not errors, "errors": errors}, indent=2))
        return 0 if not errors else 1
    print("usage: agent_orientation_check_v1.py [brief|verify|intent-check <intent.json>] [--root DIR]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
