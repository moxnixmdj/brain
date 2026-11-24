#!/usr/bin/env python3
"""Zero-model Harbor policy for the finite raw-instruction purpose bridge.

This is not a universal natural-language parser. It matches instruction text
against a small, external, inspectable and editable set of fully typed regex
templates. Each match supplies explicit quoted slots and a finite transformation
family. The policy then calls the raw-instruction binder and the existing
goal-directed sufficient-knowing kernel. A bounded file-name scan supplies one
K1 observation; the official Harbor verifier remains the distinct authority.

No model, network, hidden test, solution, verifier output, borrowed answer,
parameter write or exact action trajectory is used. Unmatched or ambiguous
instructions fail closed with no environment action.
"""
from __future__ import annotations

import copy
import hashlib
import json
import pathlib
import re
import shlex
from typing import Any

from canonical.runtime import goal_directed_sufficient_knowing_v1 as gdsk
from canonical.runtime import raw_instruction_purpose_binder_v1 as binder

SCHEMA = "BRAIN_RAW_INSTRUCTION_PURPOSE_HARBOR_POLICY_V1"
ROOT = pathlib.Path(__file__).resolve().parents[2]
STORE_PATH = ROOT / "canonical/astra_runtime/state/RAW_INSTRUCTION_PURPOSE_TEMPLATE_STORE_V1.json"

FORBIDDEN_PATH_MARKERS = (
    "tests/", "test/", "solution/", "verifier/", ".git/", "node_modules/", "__pycache__/",
)
FORBIDDEN_COMMAND_MARKERS = (
    "cat ", "curl", "wget", "pytest", "test.sh", "solve.sh", "oracle", "git clone",
    "pip install", "apt-get", " /tests/", " /solution/", " /verifier/", ";", "&", "|", "$",
    "`", "\\", "\n", "\r", "\x00",
)
ALLOWED_COMMAND_PREFIXES = ("printf ", "cp -f ", "mv -f ", "chmod ", "sed -i ")
_SAFE_ATOM = re.compile(r"^[A-Za-z0-9._/\-]{1,200}$")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()


def safe_path(value: str) -> bool:
    if not value or len(value) > 200 or not _SAFE_ATOM.fullmatch(value):
        return False
    if value.startswith("~") or ".." in pathlib.PurePosixPath(value).parts:
        return False
    if value.startswith("/") and not value.startswith(("/app/", "/workspace/", "/root/")):
        return False
    return not any(marker in value.casefold() for marker in FORBIDDEN_PATH_MARKERS)


def scan_command() -> str:
    """List visible file names only; prune hidden-test and verifier areas."""
    return (
        "for root in /app /workspace /root; do "
        "[ -d \"$root\" ] || continue; "
        "find \"$root\" -maxdepth 3 "
        "\\( -path '*/tests' -o -path '*/test' -o -path '*/solution' "
        "-o -path '*/verifier' -o -path '*/.git' -o -path '*/node_modules' "
        "-o -path '*/__pycache__' \\) -prune -o -type f -print; "
        "done | sort | head -n 200"
    )


def scan_is_safe(command: str) -> bool:
    lowered = command.casefold()
    return (
        "-prune" in lowered
        and "-type f -print" in lowered
        and not any(marker in lowered for marker in ("cat ", "pytest", "test.sh", "solve.sh", "curl", "wget", "git clone"))
    )


def command_is_safe(command: str) -> bool:
    """Approve only the finite command-template shapes; quoted text is data."""
    lowered = command.casefold()
    if any(marker in lowered for marker in FORBIDDEN_COMMAND_MARKERS):
        return False
    if not lowered.startswith(ALLOWED_COMMAND_PREFIXES):
        return False
    printf = re.fullmatch(r"printf '%s' '([^']*)' > (\S+)", command)
    if printf:
        literal, target = printf.groups()
        return (
            0 < len(literal) <= 4096
            and not any(marker in literal.casefold() for marker in FORBIDDEN_PATH_MARKERS)
            and safe_path(target)
        )
    copy_or_move = re.fullmatch(r"(?:cp|mv) -f (\S+) (\S+)", command)
    if copy_or_move:
        return all(safe_path(x) for x in copy_or_move.groups())
    chmod = re.fullmatch(r"chmod 0?[0-7]{3,4} (\S+)", command)
    if chmod:
        return safe_path(chmod.group(1))
    sed = re.fullmatch(r"sed -i '([^']*)' (\S+)", command)
    if sed:
        return 0 < len(sed.group(1)) <= 4096 and safe_path(sed.group(2))
    return False


def visible_scan_atoms(scan_stdout: str) -> list[str]:
    atoms: list[str] = []
    for line in scan_stdout.splitlines():
        value = line.strip()
        if not value:
            continue
        if not safe_path(value):
            continue
        atoms.append(value)
    if len(atoms) > 200:
        raise ValueError("SCAN_NOT_BOUNDED")
    return sorted(set(atoms))


def _match_templates(instruction: str, store: dict[str, Any]) -> list[tuple[dict[str, Any], dict[str, str]]]:
    matches: list[tuple[dict[str, Any], dict[str, str]]] = []
    for template in store["templates"]:
        for pattern in template.get("instruction_patterns") or []:
            match = re.fullmatch(pattern, instruction, flags=re.IGNORECASE | re.DOTALL)
            if match is None:
                continue
            slots = {key: value for key, value in match.groupdict().items() if value is not None}
            if set(slots) != set(template["required_slots"]):
                continue
            matches.append((template, slots))
    return matches


def _binding_request(instruction: str, template: dict[str, Any], slots: dict[str, str], atoms: list[str], scan_hash: str) -> dict[str, Any]:
    r = copy.deepcopy(template["binding_defaults"])
    r["schema"] = "BRAIN_TYPED_PURPOSE_BINDING_REQUEST_V1"
    r["raw_instruction"] = instruction
    r["template_id"] = template["template_id"]
    r["quoted_slots"] = dict(slots)
    r["visible_scan_atoms"] = list(atoms)
    r["environment_evidence"]["evidence_ref"] = "bounded-file-name-scan:" + scan_hash
    r["distinct_verifier"]["evidence_ref"] = "harbor-official-verifier:" + scan_hash[:16]
    return r


def _k1_fact(packet: dict[str, Any], template: dict[str, Any], slots: dict[str, str], atoms: list[str], scan_hash: str) -> dict[str, Any]:
    rule = template["observation_rule"]
    target = slots[rule["target_slot"]]
    target_present = any(atom == target or atom.endswith("/" + target) for atom in atoms)
    value = rule["value_when_target_present"] if target_present else rule["value_when_target_absent"]
    goal = packet["goal"]
    environment = packet["environment"]
    return {
        "id": "visible_scan_target_state",
        "unknown_id": rule["unknown"],
        "value": value,
        "authenticated": True,
        "source_bound": True,
        "source_class": "authenticated_observation",
        "evidence_hash": "sha256:bounded-file-name-scan:" + scan_hash,
        "policy_authority": False,
        "answer_authority": False,
        "capability_credit_delta": 0,
        "freshness_ok": True,
        "completeness_required": True,
        "bounded_enumeration": True,
        "scope": {
            "goal_effect": goal["effect"],
            "environment_class": environment["environment_class"],
            "environment_ids": [environment["id"]],
        },
    }


def _refusal(reason: str, instruction: str, scan_stdout: str, template_id: str | None = None) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "REFUSED__NO_ENVIRONMENT_ACTION",
        "reason": reason,
        "instruction_sha256": sha256_text(instruction),
        "scan_sha256": sha256_text(scan_stdout),
        "template_id": template_id,
        "commands": [],
        "refusals": [reason],
        "right_question": "No decision-relevant typed contrast was supplied by the finite external grammar.",
        "binding_result": None,
        "gdsk_decision": None,
        "model_calls": 0,
        "runtime_network_calls": 0,
        "parameters_written": 0,
        "hidden_test_reading": False,
        "borrowed_outputs": False,
        "benchmark_reward_claimed": False,
    }


def plan(instruction: str, scan_stdout: str, store_path: str | pathlib.Path = STORE_PATH) -> dict[str, Any]:
    """Bind one instruction or fail closed; return at most one safe command."""
    instruction = instruction if isinstance(instruction, str) else ""
    scan_stdout = scan_stdout if isinstance(scan_stdout, str) else ""
    scan_hash = sha256_text(scan_stdout)
    if not instruction.strip() or len(instruction) > 8192:
        return _refusal("INVALID_INSTRUCTION", instruction, scan_stdout)
    try:
        store = binder.load_external_store(store_path)
        atoms = visible_scan_atoms(scan_stdout)
    except (binder.BindingRefused, OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return _refusal("EXTERNAL_STORE_OR_SCAN_INVALID:" + type(exc).__name__, instruction, scan_stdout)
    if not atoms:
        return _refusal("EMPTY_BOUNDED_SCAN", instruction, scan_stdout)
    matches = _match_templates(instruction, store)
    if not matches:
        return _refusal("NO_FINITE_TYPED_TEMPLATE_MATCH", instruction, scan_stdout)
    if len(matches) != 1:
        return _refusal("AMBIGUOUS_TYPED_TEMPLATE_MATCH", instruction, scan_stdout)
    template, slots = matches[0]
    request = _binding_request(instruction, template, slots, atoms, scan_hash)
    result = binder.compile_request(request, store)
    if result["status"] != "BOUND__TYPED_ACTION_QUOTIENT":
        return _refusal("BINDER_REFUSED:" + str(result.get("reason", "")), instruction, scan_stdout, template["template_id"])
    packet = result["packet"]
    fact = _k1_fact(packet, template, slots, atoms, scan_hash)
    packet["store"]["facts"] = [fact]
    decision = gdsk.evaluate(packet)
    if decision["decision"] != gdsk.READY_FOR_DISTINCT_VERIFIER:
        return _refusal("GDSK_REFUSED:" + decision["decision"], instruction, scan_stdout, template["template_id"])
    selected = [a for a in packet["actions"] if a.get("requires_value") == fact["value"]]
    if len(selected) != 1:
        return _refusal("DECISION_ACTION_NOT_UNIQUE", instruction, scan_stdout, template["template_id"])
    command = str(selected[0]["command"])
    if not command_is_safe(command):
        return _refusal("GENERATED_COMMAND_NOT_SAFE", instruction, scan_stdout, template["template_id"])
    return {
        "schema": SCHEMA,
        "status": "BOUND__HARBOR_HARNESS_ACTION_AUTHORIZED",
        "instruction_sha256": sha256_text(instruction),
        "scan_sha256": scan_hash,
        "template_id": template["template_id"],
        "template_sha256": binder.canonical_sha256(template),
        "external_store_sha256": binder.canonical_sha256(store),
        "right_question": "Does the bounded visible scan contain the exact typed target path?",
        "k1_fact_value": fact["value"],
        "selected_action_id": selected[0]["id"],
        "commands": [command],
        "binding_result": result,
        "gdsk_decision": decision,
        "model_calls": 0,
        "runtime_network_calls": 0,
        "parameters_written": 0,
        "hidden_test_reading": False,
        "borrowed_outputs": False,
        "benchmark_reward_claimed": False,
        "trajectory_saved": False,
        "world_fact_warehouse": False,
    }
