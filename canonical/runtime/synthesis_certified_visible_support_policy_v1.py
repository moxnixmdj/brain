from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import bounded_claim_support as support
from canonical.runtime import synthesis_grounded_expression_ir_v1 as realizer

SCHEMA = "PROJECT_BRAIN_SYNTHESIS_CERTIFIED_VISIBLE_SUPPORT_POLICY_V1"
INPUT_SCHEMA = "PROJECT_BRAIN_SYNTHESIS_CERTIFIED_VISIBLE_SUPPORT_INPUT_V1"


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
            if row.get("required") is not True:
                return _fail("OUTSIDE_CELL_OPTIONAL_OR_NONREQUIRED_CLAIM")
            text = _token(row.get("text"))
            section = row.get("section")
            if section is not None:
                section = _token(section)
            claims.append({"claim_id": cid, "text": text, "section": section})

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

        items = []
        relation_audit = []
        supported_claim_ids = []
        conflict_pair_count = 0

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
                        details={"claim_id": claim["claim_id"], "evidence_id": ev["evidence_id"]},
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

            if not supports:
                return _fail("REQUIRED_CLAIM_LACKS_CERTIFIED_SUPPORT", details=claim["claim_id"])

            supported_claim_ids.append(claim["claim_id"])
            items.append({
                "id": "CLAIM_" + claim["claim_id"],
                "kind": "CLAIM",
                "text": claim["text"],
                "provenance": _merge_provenance(supports),
                "section": claim["section"],
            })
            for ev in conflicts:
                conflict_pair_count += 1
                items.append({
                    "id": "CONFLICT_" + claim["claim_id"] + "_" + ev["evidence_id"],
                    "kind": "CONFLICT",
                    "text": ev["text"],
                    "provenance": ev["provenance"],
                    "section": claim["section"],
                })

        profile_id = _token(profile.get("profile_id"))
        constraints = profile.get("constraints")
        if not isinstance(constraints, Mapping):
            return _fail("AUDIENCE_CONSTRAINTS_REQUIRED")
        c = dict(constraints)
        if "item_order" in c and c["item_order"] != "INPUT":
            return _fail("OUTSIDE_CELL_AUDIENCE_REQUIRES_SEMANTIC_REORDERING")
        c["item_order"] = "INPUT"

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

        return {
            "schema": SCHEMA,
            "status": "PASS",
            "scope": "EXPLICIT_REQUIRED_CLAIMS__VERIFIED_EVIDENCE__BOUNDED_FACT_GRAMMAR__EXPLICIT_TYPED_AUDIENCE_CONSTRAINTS",
            "audience_profile_id": profile_id,
            "rendered_text": rendered["rendered_text"],
            "render_trace": rendered["trace"],
            "relation_audit": relation_audit,
            "audit": {
                "required_claim_count": len(claims),
                "supported_required_claim_count": len(supported_claim_ids),
                "all_required_claims_supported": len(supported_claim_ids) == len(claims),
                "all_claim_evidence_relations_resolved": True,
                "conflict_pair_count": conflict_pair_count,
                "all_detected_conflicts_rendered": True,
                "unrelated_evidence_omitted": True,
                "audience_profile_applied": True,
                "all_rendered_items_provenance_bound": rendered["audit"]["all_items_provenance_bound"],
                "dropped_material_item_count": rendered["audit"]["dropped_item_count"],
                "new_material_claim_count": rendered["audit"]["new_material_claim_count"],
            },
            "semantic_boundary": {
                "general_paraphrase_entailment": "UNPROVED",
                "arbitrary_audience_meaning": "UNPROVED",
                "optional_claim_salience": "UNPROVED",
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
