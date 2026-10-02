"""Deterministic command policy for Project Brain Harbor task environments."""
from __future__ import annotations
import re
from typing import Any

MAX_COMMAND_CHARS=12000
FORBIDDEN_COMMAND_PATTERNS=(
    r"(?i)\b(curl|wget)\b",
    r"(?i)\bgit\s+(clone|fetch|pull)\b",
    r"(?i)\b(pip|pip3|uv|poetry)\s+install\b",
    r"(?i)\b(apt|apt-get|dnf|yum|apk)\s+.*\binstall\b",
    r"(?i)\bssh\b",
    r"(?i)\bscp\b",
)

def validate_environment_command(command:Any)->str:
    if not isinstance(command,str) or not command.strip():
        raise ValueError("HARBOR_COMMAND_REQUIRED")
    command=command.strip()
    if len(command)>MAX_COMMAND_CHARS:
        raise ValueError("HARBOR_COMMAND_TOO_LONG")
    if "\x00" in command:
        raise ValueError("HARBOR_COMMAND_NUL")
    for pattern in FORBIDDEN_COMMAND_PATTERNS:
        if re.search(pattern,command):
            raise ValueError("HARBOR_COMMAND_EXTERNAL_ACQUISITION_FORBIDDEN")
    return command
