"""Compile the authorized V2 terminal wave into exact route-specific execution classes.

This module consumes *metadata only*.  It never generates a terminal case, invokes a
candidate, observes an oracle, creates a post-freeze beacon, or grants capability
credit.  Its purpose is to replace hand-maintained launcher assumptions with a
fail-closed derivation from the frozen Brain authorities.

Every active behavioral contract must compile to exactly one of:

* DIRECT_POPULATION: a frozen post-freeze population/source-pool with an explicit
  case count and deterministic selector semantics; or
* MULTIPLEX_INSTRUMENTATION: instrumentation whose terminal evidence is explicitly
  the frozen parent T0/T1/T2/T3 observations.

Unknown, ambiguous, missing, or contradictory state fails closed before any fresh
terminal evidence can be consumed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

REGISTRY = Path("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json")
BASIS = Path("canonical/governance/ACTIVE_TERMINAL_PROOF_BASIS_V1.json")
PROTOCOL = Path("canonical/governance/GLOBAL_TERMINAL_REPLACEMENT_POPULATION_PROTOCOL_V2.json")
AUTHORITY = Path("canonical/governance/TERMINAL_WAVE_EXECUTION_AUTHORITY_V1.json")
EXECUTOR_MANIFEST = Path("canonical/governance/TERMINAL_ROUTE_SPECIFIC_EXECUTOR_MANIFEST_V1.json")

SCHEMA = "PROJECT_BRAIN_TERMINAL_ROUTE_EXECUTION_PLAN_V1"


def _load(root: Path, rel: Path | str) -> dict[str, Any]:
    p = root / Path(rel)
    obj = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(f"NOT_OBJECT:{rel}")
    return obj


def _nonempty_str(v: Any) -> bool:
    return isinstance(v, str) and bool(v.strip())


def _false_or_absent(m: Mapping[str, Any], key: str) -> bool:
    return key not in m or m.get(key) is False


def _extract_count(m: Mapping[str, Any]) -> int | None:
    for key in ("terminal_sample_count", "sample_count", "slot_count", "case_count"):
        v = m.get(key)
        if isinstance(v, int) and not isinstance(v, bool) and v > 0:
            return v
    return None


def _extract_direct_descriptor(doc: Mapping[str, Any]) -> dict[str, Any] | None:
    candidates: list[Mapping[str, Any]] = []
    for key in ("population", "source_pool", "frozen_population", "terminal_population"):
        v = doc.get(key)
        if isinstance(v, Mapping):
            candidates.append(v)
    candidates.append(doc)

    for block in candidates:
        count = _extract_count(block)
        if count is None:
            continue
        generator = block.get("generator")
        version = (
            block.get("route_population_version")
            or block.get("version")
            or block.get("population_version")
        )
        case_id_rule = block.get("case_id_rule") or block.get("case_generation_rule")
        selector = doc.get("selector")
        if not isinstance(selector, Mapping):
            selector = {}
        seed_rule = (
            block.get("seed_rule")
            or selector.get("seed_rule")
            or selector.get("direct_seed_rule")
            or doc.get("seed_rule")
        )

        anti_adaptive = all(
            _false_or_absent(block, k) and _false_or_absent(selector, k)
            for k in ("adaptive_case_selection", "case_replacement", "replay_for_tuning", "tuning_replay")
        )
        return {
            "sample_count": count,
            "generator": generator if _nonempty_str(generator) else None,
            "population_version": version if _nonempty_str(version) else None,
            "case_id_rule": case_id_rule if _nonempty_str(case_id_rule) else None,
            "seed_rule": seed_rule if _nonempty_str(seed_rule) else None,
            "anti_adaptive": anti_adaptive,
        }
    return None


def _extract_multiplex_descriptor(doc: Mapping[str, Any]) -> dict[str, Any] | None:
    term = doc.get("terminal_acceptance")
    if isinstance(term, Mapping):
        source = term.get("terminal_evidence_source")
        rule = term.get("proof_rule")
        if _nonempty_str(source) and _nonempty_str(rule):
            return {
                "terminal_evidence_source": source,
                "proof_rule": rule,
                "evaluator_or_threshold_edit_after_first_terminal_result": term.get(
                    "evaluator_or_threshold_edit_after_first_terminal_result"
                ),
                "binding_form": "terminal_acceptance",
            }

    # Native artifact preservation encodes its multiplex terminal semantics under
    # terminal_surface: every frozen T1 case that uses the native-edit route must
    # pass the mechanical preservation gates.  Treat that as an explicit parent
    # observation binding rather than inventing a standalone sample population.
    surface = doc.get("terminal_surface")
    if isinstance(surface, Mapping):
        portfolio = surface.get("portfolio")
        gate = surface.get("mechanical_gate_rule")
        if _nonempty_str(portfolio) and _nonempty_str(gate):
            return {
                "terminal_evidence_source": {
                    "portfolio": portfolio,
                    "binding": "terminal_surface",
                },
                "proof_rule": gate,
                "evaluator_or_threshold_edit_after_first_terminal_result": doc.get(
                    "contamination", {}
                ).get("oracle_or_threshold_edit_after_first_terminal_result")
                if isinstance(doc.get("contamination"), Mapping)
                else None,
                "binding_form": "terminal_surface",
            }
    return None


def _contract_index(basis: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    rows = basis.get("contracts")
    if not isinstance(rows, list):
        raise ValueError("BASIS_CONTRACTS_INVALID")
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or not _nonempty_str(row.get("behavior_id")):
            raise ValueError("BASIS_CONTRACT_ROW_INVALID")
        bid = row["behavior_id"]
        if bid in out:
            raise ValueError("BASIS_CONTRACT_DUPLICATE:" + bid)
        out[bid] = row
    return out


def _manifest_index(manifest: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    rows = manifest.get("routes")
    if not isinstance(rows, list):
        raise ValueError("EXECUTOR_MANIFEST_ROUTES_INVALID")
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or not _nonempty_str(row.get("behavior_id")):
            raise ValueError("EXECUTOR_MANIFEST_ROW_INVALID")
        bid = row["behavior_id"]
        if bid in out:
            raise ValueError("EXECUTOR_MANIFEST_DUPLICATE:" + bid)
        out[bid] = row
    return out


def _candidate_binding_paths(
    bid: str,
    basis_row: Mapping[str, Any],
    protocol_row: Mapping[str, Any],
    manifest_row: Mapping[str, Any],
) -> list[str]:
    vals: list[Any] = [
        manifest_row.get("frozen_route"),
        protocol_row.get("route"),
        protocol_row.get("population_binding"),
        basis_row.get("route"),
        basis_row.get("post_refreeze_binding"),
        basis_row.get("terminal_population_binding"),
        basis_row.get("prewave_binding"),
        basis_row.get("terminal_route"),
    ]
    seen: set[str] = set()
    out: list[str] = []
    for v in vals:
        if _nonempty_str(v) and v not in seen:
            seen.add(v)
            out.append(v)
    if not out:
        raise ValueError("NO_BINDING_PATHS:" + bid)
    return out


def compile_plan(root: Path) -> dict[str, Any]:
    root = root.resolve()
    errors: list[str] = []
    registry = _load(root, REGISTRY)
    basis = _load(root, BASIS)
    protocol = _load(root, PROTOCOL)
    authority = _load(root, AUTHORITY)
    manifest = _load(root, EXECUTOR_MANIFEST)

    active_rows = registry.get("active_contracted_residuals")
    if not isinstance(active_rows, list):
        raise ValueError("ACTIVE_REGISTRY_INVALID")
    active = [
        row.get("behavior_id")
        for row in active_rows
        if isinstance(row, Mapping) and _nonempty_str(row.get("behavior_id"))
    ]
    if len(active) != len(active_rows) or len(active) != len(set(active)):
        errors.append("ACTIVE_REGISTRY_DUPLICATE_OR_INVALID")

    protocol_active = protocol.get("active_contracts")
    if not isinstance(protocol_active, list) or any(not _nonempty_str(x) for x in protocol_active):
        errors.append("PROTOCOL_ACTIVE_CONTRACTS_INVALID")
        protocol_active = []

    frozen = protocol.get("frozen_route_bindings")
    if not isinstance(frozen, Mapping):
        errors.append("PROTOCOL_FROZEN_ROUTE_BINDINGS_INVALID")
        frozen = {}

    try:
        basis_by_id = _contract_index(basis)
        manifest_by_id = _manifest_index(manifest)
    except ValueError as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "structural_ready": False,
            "launch_ready": False,
            "errors": [str(exc)],
            "terminal_results_observed": 0,
            "fresh_terminal_evidence_consumed": 0,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
        }

    sets = {
        "registry": set(active),
        "protocol": set(protocol_active),
        "basis": set(basis_by_id),
        "manifest": set(manifest_by_id),
        "frozen_bindings": set(frozen),
    }
    expected = sets["registry"]
    for name, value in sets.items():
        if value != expected:
            errors.append(
                "CONTRACT_SET_MISMATCH:"
                + name
                + ":missing="
                + ",".join(sorted(expected - value))
                + ":extra="
                + ",".join(sorted(value - expected))
            )

    if len(expected) != 12:
        errors.append(f"ACTIVE_CONTRACT_COUNT_NOT_12:{len(expected)}")
    if authority.get("execution_authority") is not True:
        errors.append("TERMINAL_EXECUTION_AUTHORITY_FALSE")

    rows: list[dict[str, Any]] = []
    for bid in sorted(expected):
        basis_row = basis_by_id.get(bid, {})
        protocol_row = frozen.get(bid, {})
        manifest_row = manifest_by_id.get(bid, {})
        if not isinstance(protocol_row, Mapping):
            errors.append("FROZEN_BINDING_ROW_INVALID:" + bid)
            continue

        paths = _candidate_binding_paths(bid, basis_row, protocol_row, manifest_row)
        loaded: list[tuple[str, dict[str, Any]]] = []
        for rel in paths:
            try:
                loaded.append((rel, _load(root, rel)))
            except (FileNotFoundError, json.JSONDecodeError, ValueError):
                errors.append("BINDING_READ_FAILURE:" + bid + ":" + rel)

        direct: tuple[str, dict[str, Any]] | None = None
        multiplex: tuple[str, dict[str, Any]] | None = None
        for rel, doc in loaded:
            d = _extract_direct_descriptor(doc)
            if d is not None and direct is None:
                direct = (rel, d)
            m = _extract_multiplex_descriptor(doc)
            if m is not None and multiplex is None:
                multiplex = (rel, m)

        if direct is not None and multiplex is not None:
            # A route may include parent acceptance metadata alongside an explicit
            # direct population.  Direct population wins only when its selector is
            # explicit enough to execute without guessing.
            dd = direct[1]
            if dd.get("case_id_rule") is None or not dd.get("anti_adaptive"):
                direct = None

        if direct is not None:
            mode = "DIRECT_POPULATION"
            rel, desc = direct
            if desc.get("case_id_rule") is None:
                errors.append("DIRECT_CASE_ID_RULE_MISSING:" + bid)
            if not desc.get("anti_adaptive"):
                errors.append("DIRECT_SELECTOR_NOT_FAIL_CLOSED:" + bid)
            execution = {"binding": rel, **desc}
        elif multiplex is not None:
            mode = "MULTIPLEX_INSTRUMENTATION"
            rel, desc = multiplex
            execution = {"binding": rel, **desc}
        else:
            mode = "UNRESOLVED"
            execution = {}
            errors.append("EXECUTION_CLASS_UNRESOLVED:" + bid)

        executor_status = manifest_row.get("executor_status")
        executor_path = manifest_row.get("executor_path") or manifest_row.get("executor")
        executor_bound = (
            isinstance(executor_status, str)
            and executor_status.startswith("BOUND")
            and _nonempty_str(executor_path)
        )

        rows.append(
            {
                "behavior_id": bid,
                "portfolio": basis_row.get("portfolio"),
                "proof_mode": protocol_row.get("proof_mode") or basis_row.get("proof_mode"),
                "execution_mode": mode,
                "execution": execution,
                "candidate": basis_row.get("candidate"),
                "executor_status": executor_status,
                "executor_path": executor_path,
                "executor_bound": executor_bound,
                "terminal_result_status": manifest_row.get("terminal_result_status", "NOT_EXECUTED"),
            }
        )

    unresolved = [r["behavior_id"] for r in rows if r["execution_mode"] == "UNRESOLVED"]
    unbound = [r["behavior_id"] for r in rows if not r["executor_bound"]]
    structural_ready = not errors and not unresolved and len(rows) == 12
    launch_ready = structural_ready and not unbound

    return {
        "schema": SCHEMA,
        "status": (
            "LAUNCH_READY__ZERO_TERMINAL_RESULTS"
            if launch_ready
            else "STRUCTURAL_PLAN_READY__EXECUTOR_BINDINGS_PENDING__ZERO_TERMINAL_RESULTS"
            if structural_ready
            else "FAIL_CLOSED"
        ),
        "structural_ready": structural_ready,
        "launch_ready": launch_ready,
        "active_contract_count": len(expected),
        "direct_population_count": sum(r["execution_mode"] == "DIRECT_POPULATION" for r in rows),
        "multiplex_instrumentation_count": sum(r["execution_mode"] == "MULTIPLEX_INSTRUMENTATION" for r in rows),
        "unresolved_contracts": unresolved,
        "unbound_executor_contracts": unbound,
        "contracts": rows,
        "errors": sorted(set(errors)),
        "rule": "DERIVE_EXECUTION_FROM_FROZEN_BINDINGS__NEVER_INVENT_GLOBAL_SAMPLE_COUNT__NO_TERMINAL_CASE_GENERATION",
        "terminal_results_observed": 0,
        "fresh_terminal_evidence_consumed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path, nargs="?", default=Path("."))
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    out = compile_plan(args.root)
    raw = json.dumps(out, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(raw, encoding="utf-8")
    print(raw, end="")
    return 0 if out.get("structural_ready") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
