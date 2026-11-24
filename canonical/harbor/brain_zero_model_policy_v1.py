#!/usr/bin/env python3
"""Pure, stdlib-only policy for a Brain-owned Harbor custom agent.

This module is deliberately not a task solver. It receives only the instruction
text and a read-only file-name scan of the environment. It never imports a
model, never opens the network, never reads hidden tests, solutions or
verifiers, and never contains benchmark task answers. If the instruction does
not state one of a small set of inspectable, reversible, generic file
operations from its own quoted operands, the policy refuses rather than
inventing purpose or repair content.

The policy's "right question" is not a question to a user or model. It is the
one decision-relevant contrast the current machine can answer: whether a safe
workspace exists and whether the instruction supplies quoted operands for a
generic transformation. All commands are built from those operands and checked
against a forbidden-path/forbidden-tool allowlist.
"""
from __future__ import annotations

import hashlib
import re
import shlex
from pathlib import PurePosixPath
from typing import Any

SCHEMA = "BRAIN_NO_INFERENCE_HARBOR_POLICY_V1"

FORBIDDEN_PATH_MARKERS = (
    "tests/",
    "test/",
    "solution/",
    "verifier/",
    ".git/",
    "node_modules/",
    "__pycache__/",
)
FORBIDDEN_COMMAND_MARKERS = (
    "cat ",
    "curl",
    "wget",
    "pytest",
    "test.sh",
    "solve.sh",
    "oracle",
    "git clone",
    "pip install",
    "apt-get",
    " /tests/",
    " /solution/",
    " /verifier/",
)
ALLOWED_FAMILIES = {
    "CREATE_FILE",
    "REMOVE_LITERAL_LINES",
    "COPY_FILE",
    "MOVE_OR_RENAME_FILE",
    "CHMOD_FILE",
    "UNRESOLVED_PURPOSE",
}
_QUOTED_SPAN = re.compile(r"`([^`]{1,4096})`|\"([^\"]{1,4096})\"|'([^']{1,4096})'")
_SAFE_PATH = re.compile(r"^[A-Za-z0-9._/\-]{1,200}$")
_SAFE_MODE = re.compile(r"^0?[0-7]{3,4}$")


def instruction_fingerprint(instruction: str) -> dict[str, Any]:
    data = instruction.encode("utf-8", errors="replace")
    return {
        "instruction_sha256": hashlib.sha256(data).hexdigest(),
        "instruction_bytes": len(data),
        "instruction_words": len(instruction.split()),
    }


def quoted_spans(instruction: str) -> list[str]:
    out: list[str] = []
    for match in _QUOTED_SPAN.finditer(instruction):
        value = next(group for group in match.groups() if group is not None)
        out.append(value)
    return out


def safe_path(value: str) -> bool:
    if not value or len(value) > 200 or not _SAFE_PATH.fullmatch(value):
        return False
    lowered = value.casefold()
    if any(marker in lowered for marker in FORBIDDEN_PATH_MARKERS):
        return False
    parts = PurePosixPath(value).parts
    if ".." in parts or value.startswith("~"):
        return False
    if any(ch in value for ch in ("\\", "\n", "\r", "\x00")):
        return False
    return True


def safe_literal(value: str) -> bool:
    lowered = value.casefold()
    return (
        0 < len(value) <= 4096
        and "\x00" not in value
        and "\r" not in value
        and "\n" not in value
        and "\\" not in value
        and not any(marker in lowered for marker in FORBIDDEN_PATH_MARKERS)
    )


def _path_like(value: str) -> bool:
    """Require an explicit path shape so bare words stay literal operands."""
    return "/" in value or "." in value


def _single_path_and_literal(spans: list[str]) -> tuple[str, str, str | None]:
    indices = [i for i, span in enumerate(spans) if _path_like(span)]
    if len(indices) != 1:
        return "", "", "REFUSED__NEEDS_ONE_UNAMBIGUOUS_QUOTED_PATH"
    path = spans[indices[0]]
    if not safe_path(path):
        return "", "", "REFUSED__HIDDEN_OR_UNSAFE_QUOTED_PATH"
    literals = [
        span
        for i, span in enumerate(spans)
        if i != indices[0] and not _path_like(span) and safe_literal(span)
    ]
    if not literals:
        return "", "", "REFUSED__NEEDS_ONE_SAFE_QUOTED_LITERAL"
    return path, literals[0], None


def scan_command() -> str:
    """Return a read-only file-name scan that prunes hidden-test areas.

    The command lists paths only. It does not print file contents and does not
    invoke tests, solutions, verifiers, package managers, browsers or models.
    """
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
        and "cat " not in lowered
        and "pytest" not in lowered
        and "test.sh" not in lowered
        and "solve.sh" not in lowered
        and "curl" not in lowered
        and "wget" not in lowered
    )


def command_is_safe(command: str) -> bool:
    lowered = command.casefold()
    return not any(marker in lowered for marker in FORBIDDEN_COMMAND_MARKERS)


def classify_action(instruction: str) -> str:
    text = instruction.casefold()
    has_word = lambda word: re.search(r"\b" + re.escape(word) + r"\b", text) is not None
    if "chmod" in text or "permission" in text and "mode" in text:
        return "CHMOD_FILE"
    if has_word("copy"):
        return "COPY_FILE"
    if has_word("rename") or has_word("move"):
        return "MOVE_OR_RENAME_FILE"
    if has_word("remove") and ("line" in text or "containing" in text or "matching" in text):
        return "REMOVE_LITERAL_LINES"
    if has_word("create") or has_word("write") or "make a file" in text:
        return "CREATE_FILE"
    return "UNRESOLVED_PURPOSE"


def _parent(path: str) -> str:
    parent = str(PurePosixPath(path).parent)
    return parent or "."


def _build_commands(family: str, spans: list[str]) -> tuple[list[str], list[str]]:
    refusals: list[str] = []
    commands: list[str] = []
    if family == "CREATE_FILE":
        path, content, refusal = _single_path_and_literal(spans)
        if refusal:
            return [], ["REFUSED__CREATE_" + refusal.removeprefix("REFUSED__")]
        commands.append(
            "mkdir -p " + shlex.quote(_parent(path))
            + " && printf %s " + shlex.quote(content)
            + " > " + shlex.quote(path)
        )
    elif family == "REMOVE_LITERAL_LINES":
        path, literal, refusal = _single_path_and_literal(spans)
        if refusal:
            return [], ["REFUSED__REMOVE_" + refusal.removeprefix("REFUSED__")]
        tmp = path + ".brain_tmp"
        if not safe_path(tmp):
            return [], ["REFUSED__TEMP_PATH_NOT_SAFE"]
        commands.append(
            "grep -v -F -x -- " + shlex.quote(literal)
            + " " + shlex.quote(path)
            + " > " + shlex.quote(tmp)
            + " && mv -f " + shlex.quote(tmp) + " " + shlex.quote(path)
        )
    elif family in {"COPY_FILE", "MOVE_OR_RENAME_FILE"}:
        indices = [i for i, span in enumerate(spans) if _path_like(span)]
        if len(indices) != 2:
            return [], ["REFUSED__FILE_OPERATION_NEEDS_TWO_UNAMBIGUOUS_QUOTED_PATHS"]
        source, destination = spans[indices[0]], spans[indices[1]]
        if not safe_path(source) or not safe_path(destination):
            return [], ["REFUSED__HIDDEN_OR_UNSAFE_QUOTED_PATH"]
        verb = "cp -f" if family == "COPY_FILE" else "mv -f"
        commands.append(
            "mkdir -p " + shlex.quote(_parent(destination))
            + " && " + verb + " " + shlex.quote(source) + " " + shlex.quote(destination)
        )
    elif family == "CHMOD_FILE":
        indices = [i for i, span in enumerate(spans) if _path_like(span)]
        if len(indices) != 1:
            return [], ["REFUSED__CHMOD_NEEDS_ONE_UNAMBIGUOUS_QUOTED_PATH"]
        path = spans[indices[0]]
        if not safe_path(path):
            return [], ["REFUSED__HIDDEN_OR_UNSAFE_QUOTED_PATH"]
        mode = next(
            (
                span
                for i, span in enumerate(spans)
                if i != indices[0] and _SAFE_MODE.fullmatch(span)
            ),
            "",
        )
        if not mode:
            return [], ["REFUSED__CHMOD_NEEDS_A_SAFE_QUOTED_MODE"]
        commands.append("chmod " + shlex.quote(mode) + " " + shlex.quote(path))
    else:
        refusals.append("UNRESOLVED_PURPOSE__NO_ADMISSIBLE_GENERIC_TRANSFORMATION")
    unsafe = [command for command in commands if not command_is_safe(command)]
    if unsafe:
        return [], ["REFUSED__UNSAFE_GENERATED_COMMAND"]
    return commands, refusals


def plan(instruction: str, scan_stdout: str) -> dict[str, Any]:
    fingerprint = instruction_fingerprint(instruction)
    spans = quoted_spans(instruction)
    family = classify_action(instruction)
    scan = scan_command()
    if not scan_is_safe(scan):
        return {
            **fingerprint,
            "schema": SCHEMA,
            "goal_family": "REFUSED",
            "right_question": "Can the environment be scanned without reading hidden tests?",
            "commands": [],
            "refusals": ["REFUSED__SCAN_COMMAND_NOT_SAFE"],
            "zero_model": True,
            "hidden_test_reading": False,
        }
    if not scan_stdout.strip():
        right_question = "No admissible non-hidden file was observed; ask whether a safe workspace exists."
    else:
        right_question = (
            "Which generic transformation, if any, is stated by safe quoted operands "
            "in the current instruction?"
        )
    commands, refusals = _build_commands(family, spans)
    return {
        **fingerprint,
        "schema": SCHEMA,
        "goal_family": family,
        "right_question": right_question,
        "quoted_operand_count": len(spans),
        "scan_command_sha256": hashlib.sha256(scan.encode("utf-8")).hexdigest(),
        "scan_stdout_sha256": hashlib.sha256(scan_stdout.encode("utf-8")).hexdigest(),
        "commands": commands,
        "refusals": refusals,
        "allowed_families": sorted(ALLOWED_FAMILIES),
        "zero_model": True,
        "hidden_test_reading": False,
        "runtime_network_calls": 0,
    }
