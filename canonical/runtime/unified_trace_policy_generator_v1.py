from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


class TracePolicyError(ValueError):
    pass


@dataclass(frozen=True)
class Observation:
    modality: str
    payload: bytes


@dataclass(frozen=True)
class PolicyStep:
    next_event: str
    next_payload: bytes
    next_state: bytes


Key = tuple[str, bytes, bytes]


class FiniteTracePolicy:
    """Finite representation kernel only.

    A policy conditions on task contract, persistent state, and opaque observation
    bytes. Modality names are metadata, not distinct policy interfaces.
    """

    def __init__(self, table: Mapping[Key, PolicyStep]):
        if not table:
            raise TracePolicyError("NONEMPTY_TABLE_REQUIRED")
        self._table = dict(table)

    @staticmethod
    def key(task_contract: str, state: bytes, observation: Observation) -> Key:
        if not isinstance(task_contract, str) or not task_contract:
            raise TracePolicyError("TASK_CONTRACT_REQUIRED")
        if not isinstance(state, bytes):
            raise TracePolicyError("STATE_BYTES_REQUIRED")
        if not isinstance(observation, Observation):
            raise TracePolicyError("OBSERVATION_REQUIRED")
        # Preserve modality inside lossless bytes rather than changing the semantic API.
        encoded = observation.modality.encode("utf-8") + b"\0" + observation.payload
        return task_contract, state, encoded

    def step(
        self,
        task_contract: str,
        state: bytes,
        observation: Observation,
    ) -> PolicyStep:
        k = self.key(task_contract, state, observation)
        if k not in self._table:
            raise TracePolicyError("UNBOUND_POLICY_STATE")
        return self._table[k]


def compile_finite_behavior(
    rows: Sequence[tuple[str, bytes, Observation, PolicyStep]],
) -> FiniteTracePolicy:
    table: dict[Key, PolicyStep] = {}
    for task, state, obs, out in rows:
        if not isinstance(out, PolicyStep):
            raise TracePolicyError("POLICY_STEP_REQUIRED")
        k = FiniteTracePolicy.key(task, state, obs)
        if k in table and table[k] != out:
            raise TracePolicyError("NONFUNCTIONAL_BEHAVIOR")
        table[k] = out
    return FiniteTracePolicy(table)


def representation_demo() -> dict[str, object]:
    rows = [
        (
            "answer_visible_relation",
            b"s0",
            Observation("image/png", b"opaque-image-bytes"),
            PolicyStep("answer", b"left", b"s1"),
        ),
        (
            "solve_text_task",
            b"s0",
            Observation("text/plain", b"2+2"),
            PolicyStep("answer", b"4", b"s1"),
        ),
        (
            "choose_ui_action",
            b"s0",
            Observation("ui/state", b"button=save"),
            PolicyStep("action", b"click:save", b"s1"),
        ),
    ]
    policy = compile_finite_behavior(rows)
    outputs = [
        policy.step(task, state, obs)
        for task, state, obs, _ in rows
    ]
    return {
        "schema": "PROJECT_BRAIN_UNIFIED_TRACE_POLICY_REPRESENTATION_DEMO_V1",
        "status": "PASS__FINITE_MULTIMODAL_BEHAVIORS_ONE_POLICY_INTERFACE",
        "row_count": len(rows),
        "all_exact": outputs == [r[3] for r in rows],
        "modalities": [r[2].modality for r in rows],
        "semantic_generator_count_claimed": 0,
        "terminal_credit_delta": 0,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(representation_demo(), sort_keys=True))
