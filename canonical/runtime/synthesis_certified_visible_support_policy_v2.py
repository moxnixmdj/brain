from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import bounded_claim_support as support
from canonical.runtime import synthesis_grounded_expression_ir_v1 as realizer

SCHEMA = "PROJECT_BRAIN_SYNTHESIS_CERTIFIED_VISIBLE_SUPPORT_POLICY_V2"
INPUT_SCHEMA = "PROJECT_BRAIN_SYNTHESIS_CERTIFIED_VISIBLE_SUPPORT_INPUT_V2"


def _fail(reason: str, *, details: Any = None) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "terminal_authority": False,
        "promotion_authority": False,
        "terminal_credit_delta": 0,
    }
    if details is not None:
        out["details"] = details
    return out


def _token(value: Any) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError("NORMALIZED_NONEMPTY_STRING_REQUIRED")
    return value


def _provenance(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        raise ValueError("PROVENANCE_REQUIRED")
    out = []
    seen = set()
    for row in value:
        if not isinstance(row, Mapping):
            raise ValueError("PROVENANCE_ROW_INVALID")
        source_id = _token(row.get("source_id"))
        locator = row.get("locator")
        if locator is not None:
            locator = _token(locator)
        key = (source_id, locator or "")
        if key in seen:
            continue
        seen.add(key)
        item = {"source_id": source_id}
        if locator is not None:
            item["locator"] = locator
        out.append(item)
    if not out:
        raise ValueError("PROVENANCE_REQUIRED")
    return out


def _merge_provenance(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    out = []
    seen = set()
    for row in rows:
        for p in row["provenance"]:
            key = (p["source_id"], p.get("locator", ""))
            if key in seen:
                continue
            seen.add(key)
            out.append(dict(p))
    return out


def _claim_selection(row: Mapping[str, Any]) -> tuple[bool, bool]:
    required = row.get("required")
    if required not in (True, False):
        raise ValueError("CLAIM_REQUIRED_FLAG_MUST_BE_BOOLEAN")
    if required is True:
        include = row.get("include", True)
        if include is not True:
            raise ValueError("REQUIRED_CLAIM_CANNOT_BE_EXCLUDED")
        return True, True
    include = row.get("include")
    if include not in (True, False):
        raise ValueError("OPTIONAL_CLAIM_REQUIRES_EXPLICIT_INCLUDE_BOOLEAN")
    return False, bool(include)


def solve(public: Any) -> dict[str, Any]:
    try:
        if not isinstance(public, Mapping) or public.get("schema") != INPUT_SCHEMA:
            return _fail("INPUT_SCHEMA_INVALID")
        task = public.get("task")
        if not isinstance(task, Mapping):
            return _fail("TASK_INVALID")

        raw_claims = task.get("claims")
        raw_evidence = task.get("evidence")
        profile = task.get("audience_profile")
        if not isinstance(raw_claims, list) or not raw_claims:
            return _fail("CLAIMS_REQUIRED")
        if not isinstance(raw_evidence, list) or not raw_evidence:
            return _fail("EVIDENCE_REQUIRED")
        if not isinstance(profile, Mapping):
            return _fail("AUDIENCE_PROFILE_REQUIRED")

        claims = []
        claim_ids = set()
        for row in raw_claims:
            if not isinstance(row, Mapping):
                return _fail("CLAIM_ROW_INVALID")
            cid = _token(row.get("claim_id"))
            if cid in claim_ids:
                return _fail("DUPLICATE_CLAIM_ID")
            claim_ids.add(cid)
            required, include = _claim_selection(row)
            text = _token(row.get("text"))
            section = row.get("section")
            if section is not None:
                section = _token(section)
            claims.append({
                "claim_id": cid,
                "text": text,
                "section": section,
                "required": required,
                "include": include,
            })

        selected = [c for c in claims if c["include"]]
        if not selected:
            return _fail("NO_SELECTED_CLAIMS")

        evidence = []
        evidence_ids = set()
        for row in raw_evidence:
            if not isinstance(row, Mapping):
                return _fail("EVIDENCE_ROW_INVALID")
            eid = _token(row.get("evidence_id"))
            if eid in evidence_ids:
                return _fail("DUPLICATE_EVIDENCE_ID")
            evidence_ids.add(eid)
            if row.get("verified") is not True:
                return _fail("UNVERIFIED_EVIDENCE_UNIT")
            evidence.append({
                "evidence_id": eid,
                "text": _token(row.get("text")),
                "provenance": _provenance(row.get("provenance")),
            })

        claim_items: dict[str, list[dict[str, Any]]] = {}
        relation_audit = []
        selected_supported = []
        excluded_optional = []
        conflict_pair_count = 0

        # Resolve all claim/evidence relations, including explicitly excluded
        # optional claims. Exclusion is allowed to remove salience work, not to
        # hide an unresolved semantic relation from the declared cell.
        for claim in claims:
            supports = []
            conflicts = []
            for ev in evidence:
                relation = support.classify_support(
                    claim["text"], ev["text"], evidence_id=ev["evidence_id"]
                )
                if relation.get("status") != "RESOLVED":
                    return _fail(
                        "OUTSIDE_CELL_UNRESOLVED_CLAIM_EVIDENCE_RELATION",
                        details={
                            "claim_id": claim["claim_id"],
                            "evidence_id": ev["evidence_id"],
                        },
                    )
                rel = relation.get("relation")
                relation_audit.append({
                    "claim_id": claim["claim_id"],
                    "evidence_id": ev["evidence_id"],
                    "relation": rel,
                })
                if rel == "SUPPORTS":
                    supports.append(ev)
                elif rel == "CONFLICTS":
                    conflicts.append(ev)

            if not claim["include"]:
                excluded_optional.append(claim["claim_id"])
                claim_items[claim["claim_id"]] = []
                continue

            if not supports:
                return _fail(
                    "SELECTED_CLAIM_LACKS_CERTIFIED_SUPPORT",
                    details=claim["claim_id"],
                )

            selected_supported.append(claim["claim_id"])
            items = [{
                "id": "CLAIM_" + claim["claim_id"],
                "kind": "CLAIM",
                "text": claim["text"],
                "provenance": _merge_provenance(supports),
                "section": claim["section"],
            }]
            for ev in conflicts:
                conflict_pair_count += 1
                items.append({
                    "id": "CONFLICT_" + claim["claim_id"] + "_" + ev["evidence_id"],
                    "kind": "CONFLICT",
                    "text": ev["text"],
                    "provenance": ev["provenance"],
                    "section": claim["section"],
                })
            claim_items[claim["claim_id"]] = items

        selected_ids = [c["claim_id"] for c in selected]
        raw_claim_order = task.get("claim_order")
        if raw_claim_order is None:
            claim_order = list(selected_ids)
            order_mode = "EXPLICIT_INPUT_CLAIM_ORDER"
        else:
            if (
                not isinstance(raw_claim_order, list)
                or any(not isinstance(x, str) or not x.strip() for x in raw_claim_order)
            ):
                return _fail("CLAIM_ORDER_INVALID")
            claim_order = [str(x) for x in raw_claim_order]
            if (
                len(claim_order) != len(selected_ids)
                or len(set(claim_order)) != len(claim_order)
                or set(claim_order) != set(selected_ids)
            ):
                return _fail("CLAIM_ORDER_MUST_BE_EXACT_SELECTED_CLAIM_PERMUTATION")
            order_mode = "EXPLICIT_CLAIM_ORDER_FIELD"

        items = []
        item_order = []
        for cid in claim_order:
            group = claim_items[cid]
            items.extend(group)
            item_order.extend(x["id"] for x in group)

        profile_id = _token(profile.get("profile_id"))
        constraints = profile.get("constraints")
        if not isinstance(constraints, Mapping):
            return _fail("AUDIENCE_CONSTRAINTS_REQUIRED")
        c = dict(constraints)
        # The selection/order policy owns the exact order. The realizer only
        # enforces it; no semantic reordering is delegated downstream.
        existing_order = c.get("item_order")
        if existing_order not in (None, "INPUT") and existing_order != item_order:
            return _fail("AUDIENCE_ITEM_ORDER_CONFLICTS_WITH_EXPLICIT_CLAIM_ORDER")
        c["item_order"] = item_order

        rendered = realizer.solve({
            "schema": realizer.INPUT_SCHEMA,
            "task": {
                "items": items,
                "constraints": c,
                "title": profile.get("title"),
            },
        })
        if rendered.get("status") != "PASS":
            return _fail(
                "AUDIENCE_OR_FORMAT_REALIZATION_FAILED",
                details={"profile_id": profile_id, "realizer": rendered},
            )

        trace_ids = [x.get("item_id") for x in rendered.get("trace", [])]
        if trace_ids != item_order:
            return _fail("REALIZER_ORDER_DRIFT")

        return {
            "schema": SCHEMA,
            "status": "PASS",
            "scope": (
                "EXPLICIT_REQUIRED_OR_EXPLICITLY_SELECTED_OPTIONAL_CLAIMS__"
                "VERIFIED_EVIDENCE__BOUNDED_FACT_GRAMMAR__"
                "EXPLICIT_SELECTED_CLAIM_ORDER_OR_INPUT_ORDER__"
                "EXPLICIT_TYPED_AUDIENCE_CONSTRAINTS"
            ),
            "audience_profile_id": profile_id,
            "rendered_text": rendered["rendered_text"],
            "render_trace": rendered["trace"],
            "relation_audit": relation_audit,
            "selection_audit": {
                "required_claim_ids": [c["claim_id"] for c in claims if c["required"]],
                "selected_claim_ids": selected_ids,
                "excluded_optional_claim_ids": excluded_optional,
                "claim_order": claim_order,
                "claim_order_mode": order_mode,
                "optional_selection_inferred": False,
                "semantic_reordering_inferred": False,
            },
            "audit": {
                "claim_count": len(claims),
                "selected_claim_count": len(selected_ids),
                "supported_selected_claim_count": len(selected_supported),
                "all_selected_claims_supported": len(selected_supported) == len(selected_ids),
                "all_claim_evidence_relations_resolved": True,
                "conflict_pair_count": conflict_pair_count,
                "all_selected_detected_conflicts_rendered": True,
                "excluded_optional_claims_rendered": False,
                "unrelated_evidence_omitted": True,
                "audience_profile_applied": True,
                "exact_selected_order_applied": trace_ids == item_order,
                "all_rendered_items_provenance_bound": rendered["audit"]["all_items_provenance_bound"],
                "dropped_selected_material_item_count": rendered["audit"]["dropped_item_count"],
                "new_material_claim_count": rendered["audit"]["new_material_claim_count"],
            },
            "semantic_boundary": {
                "general_paraphrase_entailment": "UNPROVED",
                "arbitrary_optional_salience": "UNPROVED",
                "arbitrary_semantic_reordering": "UNPROVED",
                "arbitrary_audience_meaning": "UNPROVED",
                "outside_bounded_fact_grammar": "FAIL_CLOSED",
            },
            "terminal_authority": False,
            "promotion_authority": False,
            "terminal_credit_delta": 0,
        }
    except ValueError as exc:
        return _fail(str(exc))


def run(args: Mapping[str, Any] | None = None, root: Any = None) -> dict[str, Any]:
    return solve(args or {})
