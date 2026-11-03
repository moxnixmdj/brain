#!/usr/bin/env python3
"""Request-scoped storage-chokepoint memory policy (`memory_policy_v1`).

Replaces fragile caller-by-caller ``learn: bool`` parameter plumbing with one
thread- and coroutine-safe ``contextvars.ContextVar`` enforced directly at the
storage and process-cache chokepoints (`transfer_learning_v1`, `computer_env_v1`,
`VerifiedSkillStore`, `causal_trace_to_skill_compiler_v1`, `associative_memory_v1`,
`flywheel_v1`, `ignorance_ledger_v1`, and `unified_cognitive_fabric_v1`).

Modes
-----
- ``READ_WRITE`` (default): normal operation; memory stores may be read and updated.
- ``READ_ONLY``: previously verified skills/entries may be read, but ALL persistent
  writes, hit-counter mutations, access-count saves, and cache flushes are blocked.
- ``OFF``: strict zero-memory cold evaluation; BOTH learned-memory reads AND all
  persistent/in-process learned cache writes are blocked across the entire call tree.

Containment invariant
---------------------
Nested scopes are monotonically restrictive by default (`READ_WRITE > READ_ONLY > OFF`):
an inner helper entering ``READ_WRITE`` inside an outer ``OFF`` or ``READ_ONLY`` scope
cannot escalate privilege unless ``allow_escalation=True`` is explicitly passed.
"""
from __future__ import annotations

import contextlib
import contextvars
from typing import Iterator

SCHEMA = "PROJECT_BRAIN_MEMORY_POLICY_V1"

READ_WRITE = "READ_WRITE"
READ_ONLY = "READ_ONLY"
OFF = "OFF"

VALID_MODES = frozenset({READ_WRITE, READ_ONLY, OFF})
_RANK = {OFF: 0, READ_ONLY: 1, READ_WRITE: 2}

_ACTIVE_MEMORY_MODE: contextvars.ContextVar[str] = contextvars.ContextVar(
    "brain_active_memory_policy_mode",
    default=READ_WRITE,
)


class MemoryPolicyError(ValueError):
    """Raised when a caller requests an unknown or conflicting memory policy."""


def validate_memory_mode(mode: object) -> str:
    if not isinstance(mode, str):
        raise MemoryPolicyError("MEMORY_POLICY_INVALID")
    norm = mode.strip().upper()
    if norm not in VALID_MODES:
        raise MemoryPolicyError(f"MEMORY_POLICY_INVALID:{mode}")
    return norm


def effective_memory_mode() -> str:
    return _ACTIVE_MEMORY_MODE.get()


def can_read_memory() -> bool:
    return _ACTIVE_MEMORY_MODE.get() != OFF


def can_write_memory() -> bool:
    return _ACTIVE_MEMORY_MODE.get() == READ_WRITE


@contextlib.contextmanager
def memory_policy_scope(
    mode: str,
    *,
    allow_escalation: bool = False,
    fail_on_escalation: bool = False,
) -> Iterator[str]:
    """Enter a request-scoped memory policy for the current thread/task."""
    requested = validate_memory_mode(mode)
    current = _ACTIVE_MEMORY_MODE.get()
    if fail_on_escalation and not allow_escalation and _RANK[requested] > _RANK[current]:
        raise MemoryPolicyError(f"MEMORY_POLICY_ESCALATION_DENIED:{current}->{requested}")
    if allow_escalation:
        chosen = requested
    else:
        chosen = requested if _RANK[requested] < _RANK[current] else current
    token = _ACTIVE_MEMORY_MODE.set(chosen)
    try:
        yield chosen
    finally:
        _ACTIVE_MEMORY_MODE.reset(token)
