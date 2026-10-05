from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable

from canonical.runtime.opus55_causal_trace_ir_v1 import append_event


class BoundaryBindingError(ValueError):
    pass


class CaptureBoundary(str, Enum):
    USER_ENVIRONMENT_IN = "USER_ENVIRONMENT_IN"
    EXTERNAL_EXECUTOR_IN = "EXTERNAL_EXECUTOR_IN"
    OPUS55_VISIBLE_OUT = "OPUS55_VISIBLE_OUT"
    OPUS55_ACTION_OUT = "OPUS55_ACTION_OUT"
    OPUS55_OPAQUE_STATE_OUT = "OPUS55_OPAQUE_STATE_OUT"
    OPUS55_CONTROL_OUT = "OPUS55_CONTROL_OUT"
    WRAPPER_CONTROL_OUT = "WRAPPER_CONTROL_OUT"
    FALLBACK_VISIBLE_OUT = "FALLBACK_VISIBLE_OUT"
    FALLBACK_ACTION_OUT = "FALLBACK_ACTION_OUT"
    FALLBACK_OPAQUE_STATE_OUT = "FALLBACK_OPAQUE_STATE_OUT"
    FALLBACK_CONTROL_OUT = "FALLBACK_CONTROL_OUT"


@dataclass(frozen=True)
class BoundaryBinding:
    actor: str
    channel: str
    requires_model_id: bool = False


BOUNDARY_BINDINGS: dict[CaptureBoundary, BoundaryBinding] = {
    CaptureBoundary.USER_ENVIRONMENT_IN: BoundaryBinding(
        "USER_OR_ENVIRONMENT",
        "R0_EXTERNAL_OBSERVATION_OR_CONFIGURATION_IN",
    ),
    CaptureBoundary.EXTERNAL_EXECUTOR_IN: BoundaryBinding(
        "EXTERNAL_EXECUTOR",
        "R0_EXTERNAL_OBSERVATION_OR_CONFIGURATION_IN",
    ),
    CaptureBoundary.OPUS55_VISIBLE_OUT: BoundaryBinding(
        "OPUS55_POLICY",
        "R1_MODEL_VISIBLE_SEMANTIC_OUTPUT",
    ),
    CaptureBoundary.OPUS55_ACTION_OUT: BoundaryBinding(
        "OPUS55_POLICY",
        "R2_MODEL_ACTION_OR_TOOL_INTENT",
    ),
    CaptureBoundary.OPUS55_OPAQUE_STATE_OUT: BoundaryBinding(
        "OPUS55_POLICY",
        "R3_MODEL_OPAQUE_CONTINUATION_STATE",
    ),
    CaptureBoundary.OPUS55_CONTROL_OUT: BoundaryBinding(
        "OPUS55_POLICY",
        "R4_PROTOCOL_OR_TURN_CONTROL_SIGNAL",
    ),
    CaptureBoundary.WRAPPER_CONTROL_OUT: BoundaryBinding(
        "ANTHROPIC_WRAPPER_OR_CLASSIFIER",
        "R4_PROTOCOL_OR_TURN_CONTROL_SIGNAL",
    ),
    CaptureBoundary.FALLBACK_VISIBLE_OUT: BoundaryBinding(
        "FALLBACK_MODEL",
        "R1_MODEL_VISIBLE_SEMANTIC_OUTPUT",
        True,
    ),
    CaptureBoundary.FALLBACK_ACTION_OUT: BoundaryBinding(
        "FALLBACK_MODEL",
        "R2_MODEL_ACTION_OR_TOOL_INTENT",
        True,
    ),
    CaptureBoundary.FALLBACK_OPAQUE_STATE_OUT: BoundaryBinding(
        "FALLBACK_MODEL",
        "R3_MODEL_OPAQUE_CONTINUATION_STATE",
        True,
    ),
    CaptureBoundary.FALLBACK_CONTROL_OUT: BoundaryBinding(
        "FALLBACK_MODEL",
        "R4_PROTOCOL_OR_TURN_CONTROL_SIGNAL",
        True,
    ),
}


def boundary_binding(boundary: CaptureBoundary | str) -> BoundaryBinding:
    try:
        normalized = CaptureBoundary(boundary)
    except (TypeError, ValueError) as exc:
        raise BoundaryBindingError(f"UNKNOWN_CAPTURE_BOUNDARY {boundary}") from exc
    return BOUNDARY_BINDINGS[normalized]


def append_boundary_event(
    trace: dict[str, Any],
    value: Any,
    *,
    boundary: CaptureBoundary | str,
    schema_path: str,
    actor_model_id: str | None = None,
    causal_parent_hashes: Iterable[str] | None = None,
    state_ref_hashes: Iterable[str] = (),
    raw_wire_bytes: bytes | None = None,
) -> str:
    """
    Append a trace event with actor/channel provenance derived from a trusted
    capture boundary. Callers cannot self-declare actor or causal channel.

    This does not prove that instrumentation chose the correct physical hook,
    nor that every load-bearing event crossed an instrumented hook. Those are
    finite capture-coverage obligations outside this adapter.
    """
    binding = boundary_binding(boundary)
    if binding.requires_model_id and not actor_model_id:
        raise BoundaryBindingError("FALLBACK_BOUNDARY_REQUIRES_MODEL_ID")

    return append_event(
        trace,
        value,
        schema_path=schema_path,
        actor=binding.actor,
        channel=binding.channel,
        actor_model_id=actor_model_id,
        causal_parent_hashes=causal_parent_hashes,
        state_ref_hashes=state_ref_hashes,
        raw_wire_bytes=raw_wire_bytes,
    )
