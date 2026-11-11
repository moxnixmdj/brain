"""Mechanize finite adaptive-cover induction.

Structural only; no terminal authority. Every evidence receipt is bound to exact
repository bytes and to the exact state contract it certifies.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence
from pathlib import Path
import hashlib
import json
import math

SCHEMA = "PROJECT_BRAIN_ADAPTIVE_COVER_INDUCTION_GATE_V1"
RECEIPT_SCHEMA = "PROJECT_BRAIN_ADAPTIVE_COVER_BOUND_RECEIPT_V1"
REPO_ROOT = Path(__file__).resolve().parents[2]


def _hex40(x: Any) -> bool:
    return (
        isinstance(x, str)
        and len(x) == 40
        and all(c in "0123456789abcdef" for c in x)
    )


def _canon(v: Any) -> bytes:
    return json.dumps(
        v,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256(v: Any) -> str:
    return hashlib.sha256(_canon(v)).hexdigest()


def _git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def _load_receipt(
    r: Any,
    repo_root: Path,
    *,
    state_id: str,
    role: str,
    subject_sha256: str,
    claims: tuple[str, ...],
) -> bool:
    if not isinstance(r, Mapping):
        return False
    rel_text = r.get("path")
    claimed_sha = r.get("git_blob_sha")
    if (
        not isinstance(rel_text, str)
        or not rel_text.strip()
        or not _hex40(claimed_sha)
    ):
        return False

    rel = Path(rel_text)
    if rel.is_absolute():
        return False
    try:
        root = repo_root.resolve()
        candidate = (root / rel).resolve(strict=True)
        candidate.relative_to(root)
    except (OSError, RuntimeError, ValueError):
        return False

    if not candidate.is_file() or _git_blob_sha(candidate) != claimed_sha:
        return False
    try:
        doc = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False
    if not isinstance(doc, Mapping):
        return False

    return (
        doc.get("schema") == RECEIPT_SCHEMA
        and doc.get("state_id") == state_id
        and doc.get("receipt_role") == role
        and doc.get("subject_sha256") == subject_sha256
        and doc.get("independent_verified") is True
        and doc.get("exact_byte_bound") is True
        and doc.get("conclusion") == "success"
        and all(doc.get(claim) is True for claim in claims)
    )


def _cost(x: Any) -> float | None:
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        return None
    x = float(x)
    return x if math.isfinite(x) and x >= 0 else None


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "alpha_gamma_totality_bound": False,
        "total_terminal_or_progress_cover_bound": False,
        "global_well_founded_rank_bound": False,
        "global_resource_potential_bound": False,
        "adaptive_cover_structurally_closed": False,
        "u_empty_authorized": False,
        "abc_closed_authorized": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def _top_contract(initial: str, top: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "initial_state_id": initial,
        "alpha_total_on_scope": top.get("alpha_total_on_scope"),
        "true_context_preserved_in_gamma_top": top.get(
            "true_context_preserved_in_gamma_top"
        ),
    }


def _state_contract(row: Mapping[str, Any]) -> dict[str, Any] | None:
    sid = str(row.get("state_id") or "").strip()
    if row.get("terminal") is True:
        c = _cost(row.get("terminal_cost_units"))
        if c is None:
            return None
        return {
            "state_id": sid,
            "terminal": True,
            "terminal_policy_id": str(row.get("terminal_policy_id") or "").strip(),
            "terminal_cost_units": c,
        }

    outs = row.get("outcomes")
    if (
        not isinstance(outs, Sequence)
        or isinstance(outs, (str, bytes))
        or not outs
    ):
        return None
    normalized: list[dict[str, Any]] = []
    for o in outs:
        if not isinstance(o, Mapping):
            return None
        c = _cost(o.get("cost_units"))
        if c is None:
            return None
        normalized.append(
            {
                "outcome_id": str(o.get("outcome_id") or "").strip(),
                "successor_state_id": str(
                    o.get("successor_state_id") or ""
                ).strip(),
                "cost_units": c,
            }
        )
    return {
        "state_id": sid,
        "terminal": False,
        "refinement_policy_id": str(
            row.get("refinement_policy_id") or ""
        ).strip(),
        "outcomes": normalized,
    }


def evaluate(
    p: Mapping[str, Any], *, repo_root: Path = REPO_ROOT
) -> dict[str, Any]:
    if not isinstance(p, Mapping):
        return _fail("PAYLOAD_MAPPING_REQUIRED")

    initial = str(p.get("initial_state_id") or "").strip()
    if not initial:
        return _fail("INITIAL_STATE_REQUIRED")

    top = p.get("top_initialization")
    if not isinstance(top, Mapping):
        return _fail("TOP_INITIALIZATION_REQUIRED")
    if top.get("alpha_total_on_scope") is not True:
        return _fail("ALPHA_TOTALITY_UNPROVED")
    if top.get("true_context_preserved_in_gamma_top") is not True:
        return _fail("GAMMA_TOP_SOUNDNESS_UNPROVED")
    top_subject = _sha256(_top_contract(initial, top))
    if not _load_receipt(
        top.get("receipt"),
        repo_root,
        state_id="__SCOPE__",
        role="TOP_INITIALIZATION",
        subject_sha256=top_subject,
        claims=(
            "alpha_total_on_scope",
            "true_context_preserved_in_gamma_top",
        ),
    ):
        return _fail("TOP_INITIALIZATION_RECEIPT_INVALID")

    rows = p.get("states")
    if (
        not isinstance(rows, Sequence)
        or isinstance(rows, (str, bytes))
        or not rows
    ):
        return _fail("STATES_REQUIRED")

    states: dict[str, Mapping[str, Any]] = {}
    contracts: dict[str, dict[str, Any]] = {}
    for i, row in enumerate(rows):
        if not isinstance(row, Mapping):
            return _fail("STATE_NOT_MAPPING", index=i)
        sid = str(row.get("state_id") or "").strip()
        if not sid or sid in states:
            return _fail(
                "STATE_ID_INVALID_OR_DUPLICATE", index=i, state_id=sid
            )
        contract = _state_contract(row)
        if contract is None:
            return _fail("STATE_CONTRACT_INVALID", index=i, state_id=sid)
        states[sid] = row
        contracts[sid] = contract
    if initial not in states:
        return _fail("INITIAL_STATE_UNDECLARED", state_id=initial)

    edges: dict[str, list[tuple[str, float, str]]] = {}
    terminal_cost: dict[str, float] = {}
    terminal_policy: dict[str, str] = {}

    for sid, row in states.items():
        subject = _sha256(contracts[sid])
        if row.get("terminal") is True:
            pid = str(row.get("terminal_policy_id") or "").strip()
            c = _cost(row.get("terminal_cost_units"))
            if not pid:
                return _fail("TERMINAL_POLICY_REQUIRED", state_id=sid)
            if c is None:
                return _fail("TERMINAL_COST_INVALID", state_id=sid)
            if not _load_receipt(
                row.get("terminal_adequacy_receipt"),
                repo_root,
                state_id=sid,
                role="TERMINAL_ADEQUACY",
                subject_sha256=subject,
                claims=("policy_adequate_on_entire_concretization",),
            ):
                return _fail("TERMINAL_ADEQUACY_UNPROVED", state_id=sid)
            if not _load_receipt(
                row.get("terminal_safety_receipt"),
                repo_root,
                state_id=sid,
                role="TERMINAL_SAFETY",
                subject_sha256=subject,
                claims=("policy_safe_on_entire_concretization",),
            ):
                return _fail("TERMINAL_SAFETY_UNPROVED", state_id=sid)
            edges[sid] = []
            terminal_cost[sid] = c
            terminal_policy[sid] = pid
            continue

        if not str(row.get("refinement_policy_id") or "").strip():
            return _fail("REFINEMENT_POLICY_REQUIRED", state_id=sid)
        if not _load_receipt(
            row.get("refinement_soundness_receipt"),
            repo_root,
            state_id=sid,
            role="REFINEMENT_SOUNDNESS",
            subject_sha256=subject,
            claims=("true_context_preserved_in_every_actual_successor",),
        ):
            return _fail("REFINEMENT_SOUNDNESS_UNPROVED", state_id=sid)
        if not _load_receipt(
            row.get("refinement_safety_receipt"),
            repo_root,
            state_id=sid,
            role="REFINEMENT_SAFETY",
            subject_sha256=subject,
            claims=("refinement_safe_on_entire_concretization",),
        ):
            return _fail("REFINEMENT_SAFETY_UNPROVED", state_id=sid)
        if not _load_receipt(
            row.get("outcome_completeness_receipt"),
            repo_root,
            state_id=sid,
            role="OUTCOME_COMPLETENESS",
            subject_sha256=subject,
            claims=("outcome_model_complete",),
        ):
            return _fail("OUTCOME_COMPLETENESS_UNPROVED", state_id=sid)

        outs = row.get("outcomes")
        if (
            not isinstance(outs, Sequence)
            or isinstance(outs, (str, bytes))
            or not outs
        ):
            return _fail("OUTCOMES_REQUIRED", state_id=sid)
        seen: set[str] = set()
        e: list[tuple[str, float, str]] = []
        for j, o in enumerate(outs):
            if not isinstance(o, Mapping):
                return _fail(
                    "OUTCOME_NOT_MAPPING", state_id=sid, index=j
                )
            oid = str(o.get("outcome_id") or "").strip()
            dst = str(o.get("successor_state_id") or "").strip()
            c = _cost(o.get("cost_units"))
            if not oid or oid in seen:
                return _fail(
                    "OUTCOME_ID_INVALID_OR_DUPLICATE",
                    state_id=sid,
                    outcome_id=oid,
                )
            if dst not in states:
                return _fail(
                    "OUTCOME_SUCCESSOR_UNDECLARED",
                    state_id=sid,
                    outcome_id=oid,
                    successor_state_id=dst,
                )
            if c is None:
                return _fail(
                    "OUTCOME_COST_INVALID",
                    state_id=sid,
                    outcome_id=oid,
                )
            seen.add(oid)
            e.append((dst, c, oid))
        edges[sid] = e

    reached: set[str] = set()

    def mark(s: str) -> None:
        if s in reached:
            return
        reached.add(s)
        for d, _, _ in edges[s]:
            mark(d)

    mark(initial)

    visiting: set[str] = set()
    done: set[str] = set()
    order: list[str] = []
    path: list[str] = []

    def dfs(s: str) -> list[str] | None:
        if s in visiting:
            k = path.index(s) if s in path else 0
            return path[k:] + [s]
        if s in done:
            return None
        visiting.add(s)
        path.append(s)
        for d, _, _ in edges[s]:
            witness = dfs(d)
            if witness:
                return witness
        path.pop()
        visiting.remove(s)
        done.add(s)
        order.append(s)
        return None

    cycle = dfs(initial)
    if cycle:
        return _fail("WELL_FOUNDED_RANK_IMPOSSIBLE_CYCLE", cycle=cycle)

    rank: dict[str, int] = {}
    budget: dict[str, float] = {}
    for s in order:
        if not edges[s]:
            if s not in terminal_cost:
                return _fail("REACHED_DEAD_END_NONTERMINAL", state_id=s)
            rank[s] = 0
            budget[s] = terminal_cost[s]
        else:
            rank[s] = 1 + max(rank[d] for d, _, _ in edges[s])
            budget[s] = max(c + budget[d] for d, c, _ in edges[s])

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__FINITE_AUTHENTICATED_ADAPTIVE_COVER_INDUCTION_MECHANIZED",
        "initial_state_id": initial,
        "reached_state_count": len(reached),
        "declared_state_count": len(states),
        "unreachable_declared_state_ids": sorted(set(states) - reached),
        "derived_rank": {s: rank[s] for s in sorted(reached)},
        "derived_resource_potential_units": {
            s: budget[s] for s in sorted(reached)
        },
        "initial_worst_case_resource_bound_units": budget[initial],
        "terminal_policy_ids": {
            s: terminal_policy[s]
            for s in sorted(terminal_policy)
            if s in reached
        },
        "alpha_gamma_totality_bound": True,
        "total_terminal_or_progress_cover_bound": True,
        "global_well_founded_rank_bound": True,
        "global_resource_potential_bound": True,
        "adaptive_cover_structurally_closed": True,
        "u_empty_authorized": False,
        "abc_closed_authorized": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "receipt_binding": (
            "EXACT_REPOSITORY_GIT_BLOB_PLUS_EXACT_STATE_CONTRACT_SHA256"
        ),
        "boundary": (
            "EXACT_FINITE_REACHED_MANIFEST_ONLY__A_SEPARATE_SCOPE_COMPLETE_"
            "PARAMETERIZED_BINDING_MUST_COVER_EVERY_REACHED_ABSTRACT_STATE_"
            "IN_S_TRACE_BEFORE_U_EMPTY"
        ),
    }
