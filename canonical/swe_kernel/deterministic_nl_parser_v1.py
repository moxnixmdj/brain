#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic natural-language parser — zero model calls, zero network calls.

THE ARGUMENT
------------
Natural language input for computer-use tasks normally requires an LLM to
parse intent into actions. This module replaces the model with deterministic
pattern matching over a closed vocabulary of computer-use operations:

    copy X to Y          → cp X Y
    move X to Y          → mv X Y
    rename X to Y        → mv X Y
    delete X             → rm X
    create X             → touch X
    search X for Y       → grep Y X
    count lines in X     → wc -l X
    compress X           → gzip X
    decompress X         → gunzip X
    list directory       → ls
    show contents of X   → cat X

Each pattern is a compiled regex with named capture groups. Matching is
exact: if no pattern matches, the input is refused (fail-closed). No model,
no network, no fuzzy matching, no learned embeddings.

ELON'S RULE APPLIED
-------------------
The best part is no part: no model calls for parsing, no network calls for
vocabulary lookup, no knowledge house for pattern storage. Patterns are
compiled at import time from first principles (regex over a closed
operation vocabulary). Every parse is exact integer matching — no floating
point, no probabilities.

Authority: NONE. Producer-run deterministic calculation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ParsedCommand:
    """Result of deterministic NL parsing."""

    command: str          # The shell command to execute
    operation: str        # The matched operation name
    confidence: int       # 1 = exact match, 0 = no match (always 1 or 0)
    model_calls: int      # Always 0
    network_calls: int    # Always 0


# --------------------------------------------------------------------------- #
# Pattern registry — compiled regexes, closed vocabulary                      #
# --------------------------------------------------------------------------- #

# Each pattern: (operation, regex, command_template)
# command_template uses {group_name} substitution from regex match groups.
_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    # copy X to Y
    (
        "copy",
        re.compile(
            r"^\s*copy\s+(?P<src>\S+)\s+to\s+(?P<dst>\S+)\s*$",
            re.IGNORECASE,
        ),
        "cp {src} {dst}",
    ),
    # move X to Y
    (
        "move",
        re.compile(
            r"^\s*move\s+(?P<src>\S+)\s+to\s+(?P<dst>\S+)\s*$",
            re.IGNORECASE,
        ),
        "mv {src} {dst}",
    ),
    # rename X to Y (alias for move)
    (
        "rename",
        re.compile(
            r"^\s*rename\s+(?P<src>\S+)\s+to\s+(?P<dst>\S+)\s*$",
            re.IGNORECASE,
        ),
        "mv {src} {dst}",
    ),
    # delete X / remove X
    (
        "delete",
        re.compile(
            r"^\s*(?:delete|remove)\s+(?P<target>\S+)\s*$",
            re.IGNORECASE,
        ),
        "rm {target}",
    ),
    # create X / touch X
    (
        "create",
        re.compile(
            r"^\s*(?:create|touch)\s+(?P<target>\S+)\s*$",
            re.IGNORECASE,
        ),
        "touch {target}",
    ),
    # search X for Y
    (
        "search",
        re.compile(
            r"^\s*search\s+(?P<file>\S+)\s+for\s+(?P<pattern>\S+)\s*$",
            re.IGNORECASE,
        ),
        "grep {pattern} {file}",
    ),
    # count lines in X
    (
        "count_lines",
        re.compile(
            r"^\s*count\s+(?:lines\s+)?in\s+(?P<file>\S+)\s*$",
            re.IGNORECASE,
        ),
        "wc -l {file}",
    ),
    # compress X
    (
        "compress",
        re.compile(
            r"^\s*compress\s+(?P<file>\S+)\s*$",
            re.IGNORECASE,
        ),
        "gzip {file}",
    ),
    # decompress X
    (
        "decompress",
        re.compile(
            r"^\s*decompress\s+(?P<file>\S+)\s*$",
            re.IGNORECASE,
        ),
        "gunzip {file}",
    ),
    # list directory (optional path)
    (
        "list",
        re.compile(
            r"^\s*list(?:\s+(?P<dir>\S+))?\s*$",
            re.IGNORECASE,
        ),
        "ls {dir}",
    ),
    # show contents of X / cat X
    (
        "show",
        re.compile(
            r"^\s*(?:show|cat|display)\s+(?P<file>\S+)\s*$",
            re.IGNORECASE,
        ),
        "cat {file}",
    ),
    # make directory X
    (
        "mkdir",
        re.compile(
            r"^\s*(?:make\s+dir|mkdir)\s+(?P<dir>\S+)\s*$",
            re.IGNORECASE,
        ),
        "mkdir {dir}",
    ),
]


# Pre-compile the pattern list for fast lookup
_PATTERN_TABLE: list[tuple[str, re.Pattern[str], str]] = [
    (op, rx, tmpl) for op, rx, tmpl in _PATTERNS
]


def parse(command_text: str) -> ParsedCommand:
    """Parse a natural-language command into a shell command.

    Fail-closed: if no pattern matches exactly, returns a ParsedCommand
    with command="" and confidence=0. The caller must refuse.

    Zero model calls, zero network calls.
    """
    for operation, pattern, template in _PATTERN_TABLE:
        match = pattern.match(command_text.strip())
        if match:
            groups = match.groupdict()
            # Fill missing optional groups with empty string
            for key in groups:
                if groups[key] is None:
                    groups[key] = ""
            try:
                cmd = template.format(**groups)
            except (KeyError, IndexError):
                continue
            return ParsedCommand(
                command=cmd.strip(),
                operation=operation,
                confidence=1,
                model_calls=0,
                network_calls=0,
            )

    return ParsedCommand(
        command="",
        operation="",
        confidence=0,
        model_calls=0,
        network_calls=0,
    )


def parse_or_refuse(command_text: str) -> dict[str, Any]:
    """Parse and return a dict suitable for the engine run() interface.

    Returns:
        {"status": "PARSED", "command": "...", "operation": "...", ...}
        or
        {"status": "REFUSED", "reason": "NO_PATTERN_MATCH", ...}
    """
    result = parse(command_text)
    if result.confidence == 1:
        return {
            "status": "PARSED",
            "command": result.command,
            "operation": result.operation,
            "model_calls": result.model_calls,
            "network_calls": result.network_calls,
        }
    return {
        "status": "REFUSED",
        "reason": "NO_PATTERN_MATCH__CANNOT_PARSE_NATURAL_LANGUAGE",
        "command_text": command_text,
        "model_calls": 0,
        "network_calls": 0,
    }


def supported_operations() -> list[str]:
    """Return the list of supported operation names."""
    return [op for op, _, _ in _PATTERN_TABLE]
