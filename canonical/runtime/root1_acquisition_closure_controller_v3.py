from __future__ import annotations

import hashlib
import json
from fractions import Fraction
from itertools import combinations
from typing import Any, Iterable, Mapping, Sequence

from canonical.runtime import root1_acquisition_closure_controller_v2 as v2

SCHEMA = "PROJECT_BRAIN_ROOT1_ACQUISITION_CLOSURE_CONTROLLER_V3"
DEFAULT_SOURCE_CLASSES = (
    "CANONICAL_BRAIN_AND_PRIOR_RECEIPTS",
    "SOURCE_CODE_AND_PACKAGE_REGISTRIES",
    "OFFICIAL_DOCUMENTATION_AND_SPECIFICATIONS",
    "PAPERS_AND_CITATION_GRAPHS",
    "ISSUES_PULL_REQUESTS_AND_TECHNICAL_DISCUSSIONS",
    "COMMUNITY_AND_SOCIAL_DISCOVERY_LEADS",
)
MAX_EXACT_SET_COVER_PRIMITIVES = 24

class Root1V3Error(ValueError):
    pass

def _f(value: Any, name: str) -> Fraction:
    if isinstance(value, bool):
        raise Root1V3Error(name.upper() + "_INVALID")
    try:
        return value if isinstance(value, Fraction) else Fraction(str(value))
    except Exception as exc:
        raise Root1V3Error(name.upper() + "_INVALID") from exc

def _items(values: Iterable[Any]) -> tuple[str, ...]:
    return tuple(sorted({str(v).strip() for v in values if str(v).strip()}))

def _digest_obj(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return "sha256:" + hashlib.sha256(payload).hexdigest()

def extract_terminal_family_envelope(manifest: Mapping[str, Any]) -> dict[str, Any]:
    expected = int(manifest.get("expected_family_count") or 0)
    actual = int(manifest.get("actual_family_count") or 0)
    rows = manifest.get("families")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        raise Root1V3Error("FAMILIES_REQUIRED")
    normalized = []
    seen = set()
    for raw in rows:
        if not isinstance(raw, Mapping):
            raise Root1V3Error("FAMILY_ROW_INVALID")
        fid = str(raw.get("id") or "").strip()
        behavior = str(raw.get("target_behavior") or "").strip()
        if not fid or not behavior:
            raise Root1V3Error("FAMILY_ID_AND_TARGET_BEHAVIOR_REQUIRED")
        if fid in seen:
            raise Root1V3Error("DUPLICATE_FAMILY_ID:" + fid)
        seen.add(fid)
        normalized.append({"id": fid, "target_behavior": behavior})
    if expected <= 0 or expected != actual or actual != len(normalized):
        raise Root1V3Error("FAMILY_COUNT_NOT_LOSSLESS")
    normalized.sort(key=lambda x: x["id"])
    return {
        "schema": SCHEMA,
        "status": "TERMINAL_FAMILY_ENVELOPE_EXTRACTED",
        "expected_family_count": expected,
        "actual_family_count": actual,
        "family_ids": [x["id"] for x in normalized],
        "family_rows": normalized,
        "family_envelope_sha256": _digest_obj(normalized),
        "lossless_at_declared_family_boundary": True,
        "claim_scope": "DECLARED_TERMINAL_FAMILY_BOUNDARY_ONLY",
        "universal_semantic_learning_success_claimed": False,
    }

def audit_current_family_routes(
    *,
    manifest: Mapping[str, Any],
    ownership_matrix: Mapping[str, Any],
) -> dict[str, Any]:
    envelope = extract_terminal_family_envelope(manifest)
    rows = ownership_matrix.get("rows")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        raise Root1V3Error("OWNERSHIP_ROWS_REQUIRED")
    by_id: dict[str, Mapping[str, Any]] = {}
    for raw in rows:
        if isinstance(raw, Mapping):
            fid = str(raw.get("family") or "").strip()
            if fid and fid not in by_id:
                by_id[fid] = raw
    manifest_by_id = {
        str(row.get("id") or "").strip(): row
        for row in (manifest.get("families") or [])
        if isinstance(row, Mapping) and str(row.get("id") or "").strip()
    }
    verified_owned = []
    route_unproved = []
    missing_rows = []
    details = []
    for fid in envelope["family_ids"]:
        row = by_id.get(fid)
        mrow = manifest_by_id.get(fid)
        if row is None or mrow is None:
            missing_rows.append(fid)
            details.append({"family": fid, "classification": "MATRIX_OR_MANIFEST_ROW_MISSING_NOT_ROOT1"})
            continue
        ownership_status = str(mrow.get("ownership_status") or "").strip()
        owned = ownership_status == "VERIFIED_OWNED_EQUAL_OR_BETTER"
        if owned:
            verified_owned.append(fid)
            cls = "VERIFIED_OWNED"
        else:
            route_unproved.append(fid)
            cls = "ROUTE_COVERAGE_UNPROVED_NOT_MISSING"
        route_hints = []
        for key in ("internalized_configuration", "candidate_internalization_routes", "best_existing_routes"):
            value = row.get(key)
            if value:
                route_hints.append(key)
        details.append({
            "family": fid,
            "classification": cls,
            "ownership_status": ownership_status or None,
            "strict_acceptance_pass": mrow.get("opus55_acceptance_state") == "PASS",
            "route_hint_classes_present": route_hints,
        })
    if missing_rows:
        status = "AUDIT_INCOMPLETE_MATRIX_ROWS_MISSING"
    elif route_unproved:
        status = "FROZEN_ENVELOPE_ROUTE_COVERAGE_OPEN_NOT_ROOT1"
    else:
        status = "FROZEN_ENVELOPE_FAMILY_ROUTE_COVERAGE_COMPLETE"
    return {
        "schema": SCHEMA,
        "status": status,
        "family_envelope_sha256": envelope["family_envelope_sha256"],
        "family_count": len(envelope["family_ids"]),
        "verified_owned_families": verified_owned,
        "verified_owned_count": len(verified_owned),
        "route_coverage_unproved_families": route_unproved,
        "route_coverage_unproved_count": len(route_unproved),
        "missing_matrix_rows": missing_rows,
        "details": details,
        "root1_positive_gap_count_delta": 0,
        "hard_rule": "ROUTE_COVERAGE_UNPROVED_IS_NOT_CAPABILITY_MISSING",
        "root1_seal_authorized": not route_unproved and not missing_rows,
    }

def beta_posterior_mean(
    successes: Any,
    attempts: Any,
    *,
    alpha: Any = Fraction(1, 2),
    beta: Any = Fraction(1, 2),
) -> Fraction:
    s = _f(successes, "successes")
    n = _f(attempts, "attempts")
    a = _f(alpha, "alpha")
    b = _f(beta, "beta")
    if min(s, n, a, b) < 0 or s > n or a <= 0 or b <= 0:
        raise Root1V3Error("BETA_POSTERIOR_INPUT_INVALID")
    return (s + a) / (n + a + b)

def rank_probabilistic_actions(actions: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    ranked = []
    seen = set()
    for raw in actions:
        aid = str(raw.get("id") or "").strip()
        if not aid or aid in seen:
            raise Root1V3Error("ACTION_ID_INVALID_OR_DUPLICATE")
        seen.add(aid)
        if raw.get("safe") is not True:
            continue
        if _f(raw.get("incremental_spend_usd", 0), "incremental_spend_usd") != 0:
            continue
        p = beta_posterior_mean(
            raw.get("historical_successes", 0),
            raw.get("historical_attempts", 0),
            alpha=raw.get("prior_alpha", Fraction(1, 2)),
            beta=raw.get("prior_beta", Fraction(1, 2)),
        )
        mass = _f(raw.get("closure_mass", 0), "closure_mass")
        info = _f(raw.get("information_gain", 0), "information_gain")
        transfer_gain = _f(raw.get("transfer_gain", 0), "transfer_gain")
        proof_gain = _f(raw.get("proof_gain", 0), "proof_gain")
        wall = _f(raw.get("time", 0), "time")
        risk = _f(raw.get("risk", 0), "risk")
        correlation = _f(raw.get("correlation_penalty", 0), "correlation_penalty")
        if min(mass, info, transfer_gain, proof_gain, wall, risk, correlation) < 0:
            raise Root1V3Error("ACTION_DIMENSION_INVALID:" + aid)
        denom = wall + risk + correlation
        if denom <= 0:
            raise Root1V3Error("ACTION_TOTAL_COST_MUST_BE_POSITIVE:" + aid)
        expected = p * mass + info + transfer_gain + proof_gain
        density = expected / denom
        if density <= 0:
            continue
        ranked.append({
            "id": aid,
            "source_class": str(raw.get("source_class") or "UNSPECIFIED").strip() or "UNSPECIFIED",
            "dependency_cluster": str(raw.get("dependency_cluster") or aid).strip() or aid,
            "posterior_p_close": str(p),
            "expected_value": str(expected),
            "value_density": str(density),
            "incremental_spend_usd": "0",
        })
    ranked.sort(key=lambda x: (-Fraction(x["value_density"]), x["id"]))
    return ranked

def select_probabilistic_orthogonal_portfolio(
    actions: Sequence[Mapping[str, Any]],
    *,
    max_actions: int = 6,
) -> list[dict[str, Any]]:
    if isinstance(max_actions, bool) or max_actions < 1:
        raise Root1V3Error("MAX_ACTIONS_INVALID")
    out = []
    sources = set()
    clusters = set()
    for row in rank_probabilistic_actions(actions):
        if row["source_class"] in sources or row["dependency_cluster"] in clusters:
            continue
        out.append(row)
        sources.add(row["source_class"])
        clusters.add(row["dependency_cluster"])
        if len(out) >= max_actions:
            break
    return out

def minimum_weight_route_cover(
    *,
    missing_primitives: Iterable[Any],
    routes: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    missing = _items(missing_primitives)
    if not missing:
        return {
            "schema": SCHEMA,
            "status": "NO_ROUTE_ACTION_NEEDED",
            "selected_route_ids": [],
            "covered_primitives": [],
            "total_weight": "0",
            "exact_minimum": True,
        }
    if len(missing) > MAX_EXACT_SET_COVER_PRIMITIVES:
        raise Root1V3Error("EXACT_SET_COVER_PRIMITIVE_LIMIT_EXCEEDED")
    mset = set(missing)
    candidates = []
    seen = set()
    for raw in routes:
        rid = str(raw.get("id") or "").strip()
        if not rid or rid in seen:
            raise Root1V3Error("ROUTE_ID_INVALID_OR_DUPLICATE")
        seen.add(rid)
        if raw.get("safe") is not True:
            continue
        if _f(raw.get("incremental_spend_usd", 0), "incremental_spend_usd") != 0:
            continue
        covers = set(_items(raw.get("covers", ()))) & mset
        if not covers:
            continue
        weight = (
            _f(raw.get("time", 0), "time")
            + _f(raw.get("risk", 0), "risk")
            + _f(raw.get("complexity", 0), "complexity")
        )
        if weight <= 0:
            raise Root1V3Error("ROUTE_WEIGHT_MUST_BE_POSITIVE:" + rid)
        candidates.append((rid, frozenset(covers), weight))
    if not candidates:
        return {
            "schema": SCHEMA,
            "status": "NO_ADMISSIBLE_ROUTE_COVER",
            "selected_route_ids": [],
            "covered_primitives": [],
            "uncovered_primitives": list(missing),
            "exact_minimum": True,
        }

    # Exact dynamic program over reachable covered subsets. Objective:
    # minimum total weight, then minimum number of actions, then lexicographic IDs.
    best: dict[frozenset[str], tuple[Fraction, tuple[str, ...]]] = {frozenset(): (Fraction(0), ())}
    for rid, covers, weight in candidates:
        snapshot = list(best.items())
        for covered, (cost, ids) in snapshot:
            new_cov = covered | covers
            new_ids = tuple(sorted(ids + (rid,)))
            new = (cost + weight, new_ids)
            old = best.get(new_cov)
            if old is None or (new[0], len(new[1]), new[1]) < (old[0], len(old[1]), old[1]):
                best[new_cov] = new
    target = frozenset(mset)
    if target not in best:
        maximal = max(best, key=lambda x: (len(x), -float(best[x][0])))
        return {
            "schema": SCHEMA,
            "status": "NO_COMPLETE_ADMISSIBLE_ROUTE_COVER",
            "selected_route_ids": list(best[maximal][1]),
            "covered_primitives": sorted(maximal),
            "uncovered_primitives": sorted(mset - set(maximal)),
            "total_weight": str(best[maximal][0]),
            "exact_minimum": True,
        }
    cost, ids = best[target]
    return {
        "schema": SCHEMA,
        "status": "EXACT_MINIMUM_ADMISSIBLE_ROUTE_COVER",
        "selected_route_ids": list(ids),
        "covered_primitives": list(missing),
        "uncovered_primitives": [],
        "total_weight": str(cost),
        "exact_minimum": True,
    }

def root1_atomic_transaction(
    *,
    gap_evidence: Mapping[str, Any] | None,
    required_primitives: Iterable[Any],
    verified_primitives: Iterable[Any],
    transfer_mappings: Sequence[Mapping[str, Any]] = (),
    search_actions: Sequence[Mapping[str, Any]] = (),
    acquisition_routes: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    gate = v2.classify_root1(gap_evidence)
    if not gate["root1_active"]:
        return {
            "schema": SCHEMA,
            "status": "ROOT1_INACTIVE_ZERO_ACQUISITION_ACTIONS",
            "gate": gate,
            "minimum_delta": None,
            "search_portfolio": [],
            "route_cover": None,
            "fresh_reality_authority": False,
            "promotion_authority": False,
        }
    delta = v2.minimum_capability_delta(
        required_primitives=required_primitives,
        verified_primitives=verified_primitives,
        transfer_mappings=transfer_mappings,
    )
    missing = delta["missing_primitives"]
    if not missing:
        return {
            "schema": SCHEMA,
            "status": "ROOT1_GAP_COLLAPSED_BY_OWNED_OR_TRANSFERRED_CAPABILITY",
            "gate": gate,
            "minimum_delta": delta,
            "search_portfolio": [],
            "route_cover": minimum_weight_route_cover(missing_primitives=(), routes=()),
            "fresh_reality_authority": False,
            "promotion_authority": False,
        }
    portfolio = select_probabilistic_orthogonal_portfolio(search_actions)
    cover = minimum_weight_route_cover(missing_primitives=missing, routes=acquisition_routes)
    return {
        "schema": SCHEMA,
        "status": "ROOT1_MINIMUM_DELTA_ACQUISITION_REQUIRED",
        "gate": gate,
        "minimum_delta": delta,
        "search_portfolio": portfolio,
        "route_cover": cover,
        "fresh_reality_authority": False,
        "promotion_authority": False,
    }
