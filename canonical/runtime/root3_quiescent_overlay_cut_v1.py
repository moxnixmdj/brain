from __future__ import annotations

from collections import defaultdict
from typing import Iterable

SCHEMA = "PROJECT_BRAIN_ROOT3_QUIESCENT_OVERLAY_CUT_V1"

BASE_EDGES = {
    ("RUNTIME_ENTRY", "TRUSTED_TRANSACTION_SUPERVISOR"),
    ("TRUSTED_TRANSACTION_SUPERVISOR", "PHYSICAL_ZERO_AMBIENT_MEMBRANE"),
    ("PHYSICAL_ZERO_AMBIENT_MEMBRANE", "UNTRUSTED_RUNTIME_BLACK_BOX"),

    ("UNTRUSTED_RUNTIME_BLACK_BOX", "PROCESS_TERMINATION"),
    ("PROCESS_TERMINATION", "WORKER_QUIESCENT_GATE"),
    ("WORKER_QUIESCENT_GATE", "PRIVATE_OVERLAY_SNAPSHOT"),
    ("PRIVATE_OVERLAY_SNAPSHOT", "TYPED_JOURNAL_CLASSIFIER"),

    ("TYPED_JOURNAL_CLASSIFIER", "INFORMATION_REQUEST_ENTRY"),
    ("INFORMATION_REQUEST_ENTRY", "CONTINUOUS_OBS_INFORMATION_ADMISSION"),
    ("CONTINUOUS_OBS_INFORMATION_ADMISSION", "TRUSTED_INFORMATION_SERVICE"),
    ("TRUSTED_INFORMATION_SERVICE", "CONTENT_BOUND_RESPONSE"),
    ("CONTENT_BOUND_RESPONSE", "QUIESCENT_RESPONSE_INJECTION"),
    ("QUIESCENT_RESPONSE_INJECTION", "TRUSTED_TRANSACTION_SUPERVISOR"),

    ("TYPED_JOURNAL_CLASSIFIER", "RESULT_ENTRY"),
    ("RESULT_ENTRY", "COMPOSITION_STATE_CAPSULE"),
    ("COMPOSITION_STATE_CAPSULE", "PARENT_STATE_EVIDENCE_COMMIT"),
    ("COMPOSITION_STATE_CAPSULE", "USER_VISIBLE_LOAD_BEARING_OUTPUT"),

    ("TYPED_JOURNAL_CLASSIFIER", "DECLARED_ARTIFACT_ENTRY"),
    ("DECLARED_ARTIFACT_ENTRY", "DECLARED_ARTIFACT_EXTRACTOR"),
    ("DECLARED_ARTIFACT_EXTRACTOR", "CANONICAL_FINAL_AUTHORIZER"),
    ("CANONICAL_FINAL_AUTHORIZER", "EFFECT_CARRIER_GUARD_V2"),
    ("EFFECT_CARRIER_GUARD_V2", "TYPED_PARENT_FINALIZER"),
    ("TYPED_PARENT_FINALIZER", "DURABLE_DECLARED_ARTIFACT"),

    ("TYPED_JOURNAL_CLASSIFIER", "UNDECLARED_OVERLAY_STATE"),
    ("UNDECLARED_OVERLAY_STATE", "DISCARD"),
}

REQUIRED_DOMINATORS = {
    "TRUSTED_INFORMATION_SERVICE": {
        "PHYSICAL_ZERO_AMBIENT_MEMBRANE",
        "WORKER_QUIESCENT_GATE",
        "TYPED_JOURNAL_CLASSIFIER",
        "CONTINUOUS_OBS_INFORMATION_ADMISSION",
    },
    "PARENT_STATE_EVIDENCE_COMMIT": {
        "PHYSICAL_ZERO_AMBIENT_MEMBRANE",
        "WORKER_QUIESCENT_GATE",
        "TYPED_JOURNAL_CLASSIFIER",
        "COMPOSITION_STATE_CAPSULE",
    },
    "USER_VISIBLE_LOAD_BEARING_OUTPUT": {
        "PHYSICAL_ZERO_AMBIENT_MEMBRANE",
        "WORKER_QUIESCENT_GATE",
        "TYPED_JOURNAL_CLASSIFIER",
        "COMPOSITION_STATE_CAPSULE",
    },
    "DURABLE_DECLARED_ARTIFACT": {
        "PHYSICAL_ZERO_AMBIENT_MEMBRANE",
        "WORKER_QUIESCENT_GATE",
        "TYPED_JOURNAL_CLASSIFIER",
        "DECLARED_ARTIFACT_EXTRACTOR",
        "CANONICAL_FINAL_AUTHORIZER",
        "EFFECT_CARRIER_GUARD_V2",
        "TYPED_PARENT_FINALIZER",
    },
}

SEMANTIC_WORKER_CHANNELS = {"PRIVATE_OVERLAY_SNAPSHOT"}


class OverlayCutError(RuntimeError):
    pass


def _paths(
    edges: set[tuple[str, str]],
    start: str,
    goal: str,
    limit: int = 10000,
) -> list[tuple[str, ...]]:
    adjacency: dict[str, list[str]] = defaultdict(list)
    for left, right in edges:
        adjacency[left].append(right)
    out: list[tuple[str, ...]] = []

    def visit(node: str, path: list[str], seen: set[str]) -> None:
        if len(out) >= limit:
            raise OverlayCutError("PATH_LIMIT_EXCEEDED")
        if node == goal:
            out.append(tuple(path))
            return
        for nxt in adjacency.get(node, ()):
            if nxt in seen:
                continue
            visit(nxt, path + [nxt], seen | {nxt})

    visit(start, [start], {start})
    return out


def verify(extra_edges: Iterable[tuple[str, str]] = ()) -> dict:
    edges = set(BASE_EDGES) | set(extra_edges)
    failures: list[dict] = []
    evidence: dict[str, dict] = {}

    # The only semantic state crossing from a completed untrusted episode is the
    # private overlay snapshot. Process termination is a control event, not a
    # semantic payload channel.
    direct_from_untrusted = {
        right for left, right in edges if left == "UNTRUSTED_RUNTIME_BLACK_BOX"
    }
    allowed_direct = {"PROCESS_TERMINATION"}
    extra_direct = sorted(direct_from_untrusted - allowed_direct)
    if extra_direct:
        failures.append(
            {
                "sink": "UNTRUSTED_RUNTIME_BLACK_BOX",
                "reason": "LIVE_OR_DIRECT_WORKER_CHANNEL_ADDED",
                "channels": extra_direct,
            }
        )

    for sink, required in REQUIRED_DOMINATORS.items():
        paths = _paths(edges, "RUNTIME_ENTRY", sink)
        if not paths:
            failures.append({"sink": sink, "reason": "SINK_UNREACHABLE"})
            continue
        bypasses = []
        for path in paths:
            missing = sorted(required - set(path))
            if missing:
                bypasses.append({"path": list(path), "missing": missing})
        evidence[sink] = {
            "path_count": len(paths),
            "required_dominators": sorted(required),
            "all_paths_dominated": not bypasses,
            "bypass_paths": bypasses,
        }
        if bypasses:
            failures.append(
                {
                    "sink": sink,
                    "reason": "DOMINATOR_BYPASS",
                    "count": len(bypasses),
                }
            )

    # A resume is legal only from a content-bound response injected while
    # quiescent. Direct service-to-runtime edges are therefore bypasses.
    if ("TRUSTED_INFORMATION_SERVICE", "UNTRUSTED_RUNTIME_BLACK_BOX") in edges:
        failures.append(
            {
                "sink": "UNTRUSTED_RUNTIME_BLACK_BOX",
                "reason": "LIVE_INFORMATION_RESPONSE_BYPASS",
            }
        )

    return {
        "schema": SCHEMA,
        "status": "PASS" if not failures else "FAIL_CLOSED",
        "semantic_worker_channel_count": 1,
        "semantic_worker_channels": sorted(SEMANTIC_WORKER_CHANNELS),
        "process_termination_semantics": "CONTROL_ONLY__NO_LOAD_BEARING_PAYLOAD",
        "live_worker_broker_fd": "ABSENT_BY_DESIGN",
        "direct_worker_network": "ABSENT_BY_PHYSICAL_MEMBRANE_PREMISE",
        "direct_worker_durable_commit": "ABSENT_BY_PHYSICAL_MEMBRANE_PREMISE",
        "sink_evidence": evidence,
        "failures": failures,
        "hard_nonclaims": [
            "GRAPH_PASS_DOES_NOT_PROVE_PHYSICAL_MEMBRANE_TOTALITY",
            "GRAPH_PASS_DOES_NOT_PROVE_THE_ARCHITECTURE_IS_INSTALLED",
            "GRAPH_PASS_DOES_NOT_PROVE_PARENT_SEMANTIC_GUARDS_SOUND",
            "NO_C1_C2_C3_OR_ACCEPTANCE_CREDIT",
        ],
        "accounting": {
            "incremental_spend_usd": 0,
            "new_reality_units_consumed": 0,
            "terminal_cases_consumed": 0,
            "acceptance_credit_delta": 0,
        },
    }
