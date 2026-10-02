"""Information-safe clean diagnostic for M0A raw-source semantic acceptance.

The candidate receives only raw task specification text. Formal semantic structures,
transform classes, ambiguity truth, and acceptance consequences remain oracle-only.

This is a diagnostic reality query for A_M0A_MATCHED_CROSS_DOMAIN_SEMANTIC_PARITY_V2.
It grants no capability credit. A failed case is evidence, not infrastructure failure.
"""
from __future__ import annotations

from collections import defaultdict
import random
from typing import Any, Mapping

from canonical.runtime import independent_acceptance_model as iam

SCHEMA = "PROJECT_BRAIN_M0A_RAW_SOURCE_TERMINAL_SUITE_V2"

DOMAINS = (
    ("software", "Runner", "transition", "workflow state", "state_transition"),
    ("finance", "Ledger", "aggregate", "component exposures", "aggregate"),
    ("identity", "Resolver", "reconcile", "identifier variants", "entity_reconciliation"),
    ("hierarchy", "Ontology", "close", "superclass links", "hierarchy_closure"),
    ("geometry", "Builder", "reconstruct", "solid envelope", "geometry_reconstruction"),
    ("numeric", "Calculator", "compute", "method result", "numeric_formula"),
    ("artifact", "Editor", "preserve", "artifact schema", "artifact"),
    ("calibration", "Instrument", "calibrate", "measurement channels", "measurement_calibration"),
    ("signal", "Pipeline", "correct", "cross talk", "signal_correction"),
    ("method", "Analyst", "choose", "method variant", "method_model_selection"),
    ("records", "Selector", "select", "latest valid record", "selection"),
)
CASE_CLASSES = (
    "DIRECT_ACTIVE",
    "PASSIVE",
    "IF_CONDITION",
    "FLAT_COMPOUND",
    "PRONOUN_UNIQUE",
    "PRONOUN_AMBIGUOUS",
    "TEMPORAL_AFTER",
    "UNLESS_EXCEPTION",
)

PAST = {
    "transition": "transitioned",
    "aggregate": "aggregated",
    "reconcile": "reconciled",
    "close": "closed",
    "reconstruct": "reconstructed",
    "compute": "computed",
    "preserve": "preserved",
    "calibrate": "calibrated",
    "correct": "corrected",
    "choose": "chosen",
    "select": "selected",
}

def _req(subject: str, predicate: str, obj: str, kind: str, *, condition: str | None = None):
    row = {
        "subject": subject,
        "predicate": predicate,
        "object": obj,
        "polarity": "required",
        "transform_kind": kind,
    }
    if condition is not None:
        row["condition"] = condition
    return row

def generate_case(seed: int, ordinal: int) -> dict[str, Any]:
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("SEED")
    if not isinstance(ordinal, int) or ordinal < 0:
        raise ValueError("ORDINAL")
    r = random.Random((seed << 16) ^ ordinal ^ 0x5A17)
    domain, subject, verb, obj, kind = DOMAINS[r.randrange(len(DOMAINS))]
    cls = CASE_CLASSES[ordinal % len(CASE_CLASSES)]

    if cls == "DIRECT_ACTIVE":
        source = f"{subject} must {verb} {obj}."
        oracle = {"status": "RESOLVED", "requirements": [_req(subject, verb, obj, kind)]}
    elif cls == "PASSIVE":
        source = f"{obj.capitalize()} must be {PAST[verb]} by {subject}."
        oracle = {"status": "RESOLVED", "requirements": [_req(subject, verb, obj.capitalize(), kind)]}
    elif cls == "IF_CONDITION":
        cond = f"{domain} input is present"
        source = f"If {cond}, {subject} must {verb} {obj}."
        oracle = {"status": "RESOLVED", "requirements": [_req(subject, verb, obj, kind, condition=cond)]}
    elif cls == "FLAT_COMPOUND":
        second = "preserve"
        second_obj = "audit lineage"
        source = f"{subject} must {verb} {obj} and {second} {second_obj}."
        oracle = {
            "status": "RESOLVED",
            "requirements": [
                _req(subject, verb, obj, kind),
                _req(subject, second, second_obj, "artifact"),
            ],
        }
    elif cls == "PRONOUN_UNIQUE":
        source = f"{subject} is the authoritative processor. It must {verb} {obj}."
        oracle = {"status": "RESOLVED", "requirements": [_req(subject, verb, obj, kind)]}
    elif cls == "PRONOUN_AMBIGUOUS":
        alt = "Engine"
        source = f"{subject} is active. {alt} is active. It must {verb} {obj}."
        oracle = {"status": "AMBIGUOUS", "requirements": []}
    elif cls == "TEMPORAL_AFTER":
        cond = f"{domain} validation completes"
        source = f"After {cond}, {subject} must {verb} {obj}."
        oracle = {"status": "RESOLVED", "requirements": [_req(subject, verb, obj, kind, condition="after " + cond)]}
    elif cls == "UNLESS_EXCEPTION":
        cond = f"{domain} source is unavailable"
        source = f"Unless {cond}, {subject} must {verb} {obj}."
        oracle = {"status": "RESOLVED", "requirements": [_req(subject, verb, obj, kind, condition="unless " + cond)]}
    else:
        raise AssertionError(cls)

    expected_modes = []
    for row in oracle["requirements"]:
        expected_modes.append({
            "transform_kind": row["transform_kind"],
            "failure_modes": sorted(iam.OBLIGATIONS[row["transform_kind"]]),
        })
    oracle["acceptance"] = expected_modes
    return {
        "schema": SCHEMA,
        "case_id": f"M0A-{seed}-{ordinal}",
        "case_class": cls,
        "domain": domain,
        "raw_source": source,
        "_oracle": oracle,
    }

def public_task(case: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": case["schema"],
        "case_id": case["case_id"],
        "raw_source": case["raw_source"],
    }

def _canon_requirements(rows):
    out = []
    for r in rows or []:
        if not isinstance(r, Mapping):
            continue
        item = {
            "subject": str(r.get("subject") or ""),
            "predicate": str(r.get("predicate") or ""),
            "object": str(r.get("object") or ""),
            "polarity": str(r.get("polarity") or "").lower(),
            "transform_kind": str(r.get("transform_kind") or ""),
        }
        if r.get("condition") is not None:
            item["condition"] = str(r.get("condition"))
        out.append(item)
    return sorted(out, key=lambda x: repr(sorted(x.items())))

def score_case(case: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, Any]:
    oracle = case["_oracle"]
    expected_status = oracle["status"]
    got_status = candidate.get("status")
    if expected_status == "AMBIGUOUS":
        ok = got_status == "AMBIGUOUS"
        return {"pass": ok, "reason": "PASS" if ok else "AMBIGUITY_NOT_PRESERVED"}

    if got_status != "RESOLVED":
        return {"pass": False, "reason": "EXPECTED_RESOLUTION_GOT_" + str(got_status)}

    exp = _canon_requirements(oracle["requirements"])
    got = _canon_requirements(candidate.get("requirements"))
    if got != exp:
        return {"pass": False, "reason": "SEMANTIC_REQUIREMENT_MISMATCH", "expected": exp, "got": got}

    plans = candidate.get("acceptance", {}).get("plans", [])
    by_kind = {}
    for req, plan in zip(candidate.get("requirements", []), plans):
        kinds = req.get("transform_kinds") or []
        if len(kinds) == 1:
            by_kind.setdefault(kinds[0], set()).update(plan.get("required_failure_modes", []))
    for row in oracle["acceptance"]:
        if sorted(by_kind.get(row["transform_kind"], set())) != row["failure_modes"]:
            return {"pass": False, "reason": "ACCEPTANCE_CONSEQUENCE_MISMATCH", "kind": row["transform_kind"]}
    return {"pass": True, "reason": "PASS"}

def run_batch(seed: int, case_count: int = 96, solver=None) -> dict[str, Any]:
    if solver is None:
        raise ValueError("SOLVER_REQUIRED")
    rows = []
    by_class = defaultdict(lambda: {"pass": 0, "total": 0, "reasons": defaultdict(int)})
    for i in range(case_count):
        case = generate_case(seed, i)
        public = public_task(case)
        try:
            got = solver(public)
            verdict = score_case(case, got)
        except Exception as exc:
            got = {"status": "EXCEPTION", "exception": type(exc).__name__ + ":" + str(exc)}
            verdict = {"pass": False, "reason": "CANDIDATE_EXCEPTION"}
        cls = case["case_class"]
        by_class[cls]["total"] += 1
        by_class[cls]["pass"] += int(bool(verdict["pass"]))
        by_class[cls]["reasons"][verdict["reason"]] += 1
        rows.append({
            "case_id": case["case_id"],
            "class": cls,
            "domain": case["domain"],
            "pass": bool(verdict["pass"]),
            "reason": verdict["reason"],
            "candidate_status": got.get("status"),
        })
    summary = {}
    total_pass = 0
    for cls, v in sorted(by_class.items()):
        total_pass += v["pass"]
        summary[cls] = {
            "pass": v["pass"],
            "total": v["total"],
            "fraction": v["pass"] / v["total"] if v["total"] else 0.0,
            "reasons": dict(sorted(v["reasons"].items())),
        }
    return {
        "schema": "PROJECT_BRAIN_M0A_RAW_SOURCE_TERMINAL_DIAGNOSTIC_RESULT_V2",
        "seed": seed,
        "case_count": case_count,
        "passed": total_pass,
        "failed": case_count - total_pass,
        "pass_fraction": total_pass / case_count,
        "all_pass": total_pass == case_count,
        "by_class": summary,
        "failures": [x for x in rows if not x["pass"]],
        "terminal_authority": False,
        "capability_credit_delta": 0,
    }
