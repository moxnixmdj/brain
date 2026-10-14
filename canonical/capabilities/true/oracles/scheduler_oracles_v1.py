"""Independent oracles for the three scheduler specs (no scheduler import).

Reference models are written from the published contracts:

* ranking: exact-fraction leverage score (capability + efficiency + reliability)
  x breadth x generalization x success / total cost; eligible work before
  demoted work; benchmark bookkeeping, unproved new-primitive claims and
  open-world frontier work without a concrete defect are demoted; ties broken
  by checkpoint audit score (only while obligations are open) then work id;
  planning only, no authority or credit.
* Pareto: textbook dominance (no worse on every axis, strictly better on one).
"""
from __future__ import annotations

import copy
import hashlib
import json
import random
from collections.abc import Mapping
from fractions import Fraction

WORK_TYPES = {"CAPABILITY_BUILD", "EFFICIENCY_IMPROVEMENT", "RELIABILITY_IMPROVEMENT", "BENCHMARK_INSTRUMENTATION", "FALSIFICATION"}
BENCHMARK_ROLES_OK = {"CAPABILITY_DEFECT_LOCALIZATION", "NEW_CAPABILITY_VALIDATION", "CAPABILITY_CLAIM_FALSIFICATION", "MILESTONE_CERTIFICATION"}
BENEFITS = ("expected_capability_gain_lcb", "expected_efficiency_gain_lcb", "expected_reliability_gain_lcb")
COSTS = ("wall_clock_cost_ub", "compute_cost_ub", "memory_cost_ub", "complexity_cost_ub")
FRONTIER_BENEFITS = ("capability", "generalization", "reliability")
FRONTIER_COSTS = ("latency", "compute", "memory", "incremental_spend_usd")
AUTH_MAX = ("capability_gain_lcb", "generalization_lcb", "reliability_lcb", "reuse_breadth_lcb", "success_probability_lcb")
AUTH_MIN = ("latency_ms_ucb", "compute_units_ucb", "memory_mb_ucb", "cost_usd_ucb")


def _frac(x) -> Fraction:
    if isinstance(x, bool):
        raise ValueError("bool")
    v = Fraction(str(x))
    if v < 0:
        raise ValueError("negative")
    return v


def _txt(x) -> str:
    return " ".join(str(x or "").split())


def _id_list(raw: Mapping, key: str) -> list[str]:
    v = raw.get(key, [])
    if v is None:
        return []
    if not isinstance(v, list) or not all(isinstance(s, str) and _txt(s) for s in v):
        raise ValueError(key)
    return sorted({_txt(s) for s in v})


# ----------------------------------------------------------------------------- ranking model
def _eligibility(w: Mapping) -> str:
    if w.get("work_type") not in WORK_TYPES:
        raise ValueError("WORK_TYPE")
    if w.get("claims_new_primitive") is True:
        mechanisms = _id_list(w, "existing_mechanisms_searched")
        reasons = w.get("existing_mechanism_unsoundness_reasons")
        proof_ok = (
            bool(_txt(w.get("exact_unsatisfied_predicate")))
            and bool(mechanisms)
            and isinstance(reasons, Mapping)
            and all(_txt(reasons.get(m)) for m in mechanisms)
            and bool(_txt(w.get("independently_verified_missing_primitive_or_counterexample")))
            and bool(_txt(w.get("minimum_new_primitive_scope")))
            and bool(_txt(w.get("falsifier_and_promotion_criteria")))
        )
        if not proof_ok:
            return "DEMOTED_UNPROVED_NEW_PRIMITIVE_CLAIM"
    if _txt(w.get("frontier_class")) == "OPEN_WORLD_EVIDENCE_FRONTIER":
        if not _id_list(w, "task_local_counterexample_ids") and not _id_list(w, "verified_capability_defect_ids"):
            return "DEMOTED_OPEN_WORLD_EVIDENCE_FRONTIER_WITHOUT_CURRENT_CAPABILITY_DEFECT"
    if w.get("work_type") == "BENCHMARK_INSTRUMENTATION" and _txt(w.get("benchmark_role")) not in BENCHMARK_ROLES_OK:
        return "DEMOTED_BENCHMARK_BOOKKEEPING"
    return "ELIGIBLE"


def rank_model(inst: Mapping) -> dict:
    """Returns {'status': 'REJECTED'} or {'status': 'OK', 'ranked': [...]} (scores as Fractions)."""
    count = inst["checkpoint_open_obligation_count"]
    rows = []
    seen = set()
    try:
        for w in inst["work"]:
            wid = _txt(w.get("work_id"))
            if not wid or wid in seen:
                raise ValueError("id")
            seen.add(wid)
            elig = _eligibility(w)
            score = Fraction(0)
            audit = Fraction(0)
            if elig == "ELIGIBLE":
                success = _frac(w.get("success_probability_lcb", 0))
                if success > 1:
                    raise ValueError("success")
                cost = sum(_frac(w.get(k, 0)) for k in COSTS)
                if cost <= 0:
                    raise ValueError("cost")
                score = sum(_frac(w.get(k, 0)) for k in BENEFITS) * _frac(w.get("reuse_breadth_lcb", 0)) * _frac(w.get("generalization_lcb", 0)) * success / cost
                load_bearing = bool(_id_list(w, "open_obligation_ids") or _id_list(w, "constructive_gap_for_open_obligation_ids") or w.get("scope_complete_discharge") is True)
                if count > 0 and load_bearing:
                    wall = _frac(w.get("wall_clock_cost_ub", 0))
                    if wall <= 0:
                        raise ValueError("wall")
                    audit = (_frac(w.get("expected_obligation_discharge_lcb", 0)) + _frac(w.get("expected_obligation_unlock_lcb", 0))) * success / wall
            rows.append({"work_id": wid, "eligibility": elig, "score": score, "audit": audit})
    except (ValueError, ArithmeticError, TypeError):
        return {"status": "REJECTED"}
    rows.sort(key=lambda r: (0 if r["eligibility"] == "ELIGIBLE" else 1, -r["score"], -r["audit"], r["work_id"]))
    return {"status": "OK", "ranked": rows, "audit_active": count > 0}


def oracles_ranking():
    def reference_ranking(inst, out, solve):
        exp = rank_model(inst)
        if exp["status"] == "REJECTED":
            return out.get("status") == "REJECTED", f"invalid instance ({inst.get('defect')}): solver said {out.get('status')} {out.get('reason')}"
        if out.get("status") != "OK":
            return False, f"valid instance rejected: {out.get('reason')}"
        got = out.get("ranked") or []
        if len(got) != len(exp["ranked"]):
            return False, "row count differs"
        for k, (g, e) in enumerate(zip(got, exp["ranked"])):
            if g.get("rank") != k + 1 or g.get("work_id") != e["work_id"] or g.get("eligibility") != e["eligibility"]:
                return False, f"row {k}: {g.get('work_id')}/{g.get('eligibility')} expected {e['work_id']}/{e['eligibility']}"
            if Fraction(str(g.get("priority_score"))) != e["score"] or Fraction(str(g.get("checkpoint_audit_score"))) != e["audit"]:
                return False, f"row {k}: scores {g.get('priority_score')}/{g.get('checkpoint_audit_score')} expected {e['score']}/{e['audit']}"
        if bool(out.get("checkpoint_audit_active")) != exp["audit_active"]:
            return False, "audit flag"
        return True, f"{len(got)} rows ranked exactly as the contract says"

    def order_invariants(inst, out, solve):
        if out.get("status") != "OK":
            return True, "rejected instance; nothing to check"
        got = out.get("ranked") or []
        ids = [r.get("work_id") for r in got]
        if sorted(ids) != sorted(_txt(w.get("work_id")) for w in inst["work"]):
            return False, "ranked ids are not the input ids"
        seen_demoted = False
        last = None
        for r in got:
            score = Fraction(str(r.get("priority_score")))
            if r.get("eligibility") != "ELIGIBLE":
                seen_demoted = True
                if score != 0:
                    return False, f"demoted {r.get('work_id')} has a non-zero score"
            else:
                if seen_demoted:
                    return False, f"eligible {r.get('work_id')} ranked below demoted work"
                if last is not None and score > last:
                    return False, "priority scores increase down the ranking"
                last = score
        return True, "eligible first, scores non-increasing, demoted scored 0"

    def permutation_invariance(inst, out, solve):
        shuffled = copy.deepcopy(inst)
        random.Random(len(json.dumps(inst, sort_keys=True))).shuffle(shuffled["work"])
        out2 = solve(shuffled)
        same = out.get("status") == out2.get("status") and (out.get("status") != "OK" or out.get("ranked") == out2.get("ranked"))
        return same, "input order " + ("does not" if same else "DOES") + " change the ranking"

    def uniform_cost_scaling_invariance(inst, out, solve):
        if out.get("status") != "OK":
            return True, "rejected instance; nothing to check"
        k = 3
        scaled = copy.deepcopy(inst)
        for w in scaled["work"]:
            for key in COSTS:
                if key in w:
                    w[key] = str(Fraction(str(w[key])) * k)
        out2 = solve(scaled)
        if out2.get("status") != "OK":
            return False, "scaled instance rejected"
        same_order = [(r.get("work_id"), r.get("eligibility")) for r in out["ranked"]] == [(r.get("work_id"), r.get("eligibility")) for r in out2["ranked"]]
        same_scores = all(
            Fraction(str(a.get("priority_score"))) == k * Fraction(str(b.get("priority_score")))
            and Fraction(str(a.get("checkpoint_audit_score"))) == k * Fraction(str(b.get("checkpoint_audit_score")))
            for a, b in zip(out["ranked"], out2["ranked"])
        )
        return same_order and same_scores, f"costs x{k}: order {'kept' if same_order else 'CHANGED'}, scores {'divided exactly' if same_scores else 'NOT divided exactly'}"

    def no_authority_granted(inst, out, solve):
        if out.get("status") != "OK":
            return True, "rejected instance; nothing to check"
        ok = out.get("planning_only") is True and out.get("execution_authority") is False and list(out.get("credit_deltas") or [1]) == [0, 0, 0, 0]
        return ok, "planning only, no authority, zero credit" if ok else f"authority leak: {out}"

    return [
        {"id": "REFERENCE_RANKING", "check": reference_ranking},
        {"id": "ORDER_INVARIANTS", "check": order_invariants},
        {"id": "PERMUTATION_INVARIANCE", "check": permutation_invariance},
        {"id": "UNIFORM_COST_SCALING_INVARIANCE", "check": uniform_cost_scaling_invariance},
        {"id": "NO_AUTHORITY_GRANTED", "check": no_authority_granted},
    ]


# ----------------------------------------------------------------------------- frontier update model
def _fmetrics(c: Mapping) -> dict:
    return {k: _frac(c.get(k, 0)) for k in FRONTIER_BENEFITS + FRONTIER_COSTS}


def _fdominates(a: Mapping, b: Mapping) -> bool:
    ca, cb = _txt(a.get("semantic_contract_sha256")), _txt(b.get("semantic_contract_sha256"))
    if ca and cb and ca != cb:
        return False
    am, bm = _fmetrics(a), _fmetrics(b)
    weak = all(am[k] >= bm[k] for k in FRONTIER_BENEFITS) and all(am[k] <= bm[k] for k in FRONTIER_COSTS)
    strict = any(am[k] > bm[k] for k in FRONTIER_BENEFITS) or any(am[k] < bm[k] for k in FRONTIER_COSTS)
    return weak and strict


def frontier_model(inst: Mapping) -> dict:
    frontier: list[Mapping] = []
    steps = []
    for c in inst["candidates"]:
        if not _txt(c.get("capability_id")):
            steps.append({"status": "REJECTED"})
            continue
        if c.get("reusable_capability") is not True:
            steps.append({"status": "OK", "admitted": False, "reason": "REUSABLE_CAPABILITY_REQUIRED", "frontier_ids": [_txt(x["capability_id"]) for x in frontier]})
            continue
        if c.get("independently_verified") is not True:
            steps.append({"status": "OK", "admitted": False, "reason": "INDEPENDENT_VERIFICATION_REQUIRED", "frontier_ids": [_txt(x["capability_id"]) for x in frontier]})
            continue
        try:
            _fmetrics(c)
        except (ValueError, ArithmeticError):
            steps.append({"status": "REJECTED"})
            continue
        dominator = next((x for x in frontier if _fdominates(x, c)), None)
        if dominator is not None:
            steps.append({"status": "OK", "admitted": False, "reason": "DOMINATED_BY_EXISTING_FRONTIER", "dominated_by": _txt(dominator["capability_id"]), "frontier_ids": [_txt(x["capability_id"]) for x in frontier]})
            continue
        removed = sorted(_txt(x["capability_id"]) for x in frontier if _fdominates(c, x))
        frontier = [x for x in frontier if not _fdominates(c, x)] + [c]
        frontier.sort(key=lambda x: _txt(x["capability_id"]))
        steps.append({"status": "OK", "admitted": True, "reason": "NONDOMINATED_VERIFIED_REUSABLE_CAPABILITY", "removed": removed, "frontier_ids": [_txt(x["capability_id"]) for x in frontier]})
    return {"steps": steps, "final_frontier_ids": [_txt(x["capability_id"]) for x in frontier]}


def oracles_frontier():
    def reference_fold(inst, out, solve):
        exp = frontier_model(inst)
        got = out.get("steps") or []
        if len(got) != len(exp["steps"]):
            return False, "step count"
        for k, (g, e) in enumerate(zip(got, exp["steps"])):
            if g.get("status") != e["status"]:
                return False, f"step {k}: status {g.get('status')} expected {e['status']} ({g.get('reason')})"
            if e["status"] == "OK":
                for key in ("admitted", "reason", "frontier_ids"):
                    if g.get(key) != e[key]:
                        return False, f"step {k}: {key}={g.get(key)} expected {e[key]}"
                if "dominated_by" in e and g.get("dominated_by") != e["dominated_by"]:
                    return False, f"step {k}: dominated_by {g.get('dominated_by')} expected {e['dominated_by']}"
                if "removed" in e and sorted(g.get("removed") or []) != e["removed"]:
                    return False, f"step {k}: removed {g.get('removed')} expected {e['removed']}"
        if out.get("final_frontier_ids") != exp["final_frontier_ids"]:
            return False, "final frontier differs"
        return True, f"{len(got)} admissions match"

    def frontier_invariants(inst, out, solve):
        by_id = {_txt(c.get("capability_id")): c for c in inst["candidates"] if _txt(c.get("capability_id"))}
        final = out.get("final_frontier_ids") or []
        if len(set(final)) != len(final) or final != sorted(final):
            return False, "frontier ids not unique and sorted"
        members = [by_id[i] for i in final]
        for a in members:
            if a.get("reusable_capability") is not True or a.get("independently_verified") is not True:
                return False, f"unverified or non-reusable member {a.get('capability_id')}"
            for b in members:
                if a is not b and _fdominates(a, b):
                    return False, f"{a.get('capability_id')} dominates frontier member {b.get('capability_id')}"
        for step, c in zip(out.get("steps") or [], inst["candidates"]):
            if step.get("status") == "OK" and step.get("reason") == "DOMINATED_BY_EXISTING_FRONTIER":
                d = by_id.get(step.get("dominated_by"))
                if d is None or not _fdominates(d, c):
                    return False, f"{c.get('capability_id')} rejected as dominated by {step.get('dominated_by')}, which does not dominate it"
            if step.get("status") == "OK" and step.get("reason") in {"NONDOMINATED_VERIFIED_REUSABLE_CAPABILITY", "DOMINATED_BY_EXISTING_FRONTIER"}:
                if step.get("physical_deletion_authority") is not False or step.get("dominated_means_deleted") is not False:
                    return False, "retirement claimed deletion authority"
        return True, f"frontier of {len(final)} is an antichain of verified reusable capabilities"

    def uniform_scaling_invariance(inst, out, solve):
        scaled = copy.deepcopy(inst)
        for c in scaled["candidates"]:
            for k in FRONTIER_BENEFITS + FRONTIER_COSTS:
                if k in c:
                    try:
                        c[k] = str(Fraction(str(c[k])) * 5)
                    except (ValueError, ArithmeticError):
                        pass
        out2 = solve(scaled)
        same = out == out2
        return same, "scaling every metric x5 " + ("preserves" if same else "CHANGES") + " every admission"

    return [
        {"id": "REFERENCE_FOLD", "check": reference_fold},
        {"id": "FRONTIER_INVARIANTS", "check": frontier_invariants},
        {"id": "UNIFORM_SCALING_INVARIANCE", "check": uniform_scaling_invariance},
    ]


# ----------------------------------------------------------------------------- authenticated schedule model
def _subject(cid: str, metrics: Mapping) -> str:
    body = {"candidate_id": cid, "metrics": {k: metrics[k] for k in AUTH_MAX + AUTH_MIN}}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _adominates(a: Mapping, b: Mapping) -> bool:
    weak = all(a[k] >= b[k] for k in AUTH_MAX) and all(a[k] <= b[k] for k in AUTH_MIN)
    strict = any(a[k] > b[k] for k in AUTH_MAX) or any(a[k] < b[k] for k in AUTH_MIN)
    return weak and strict


def schedule_model(inst: Mapping) -> dict:
    rows = []
    ids = set()
    for c in inst["candidates"]:
        cid = c.get("candidate_id") if isinstance(c, Mapping) else None
        if not isinstance(cid, str) or not cid:
            return {"pass": False, "reason": "CANDIDATE_INVALID"}
        if cid in ids:
            return {"pass": False, "reason": "DUPLICATE_CANDIDATE_ID", "candidate_id": cid}
        ids.add(cid)
        m = c.get("metrics")
        r = c.get("measurement_receipt")
        if not isinstance(m, Mapping) or any(k not in m or isinstance(m[k], bool) or not isinstance(m[k], (int, float)) for k in AUTH_MAX + AUTH_MIN):
            return {"pass": False, "reason": "METRICS_INCOMPLETE", "candidate_id": cid}
        sha = r.get("sha256") if isinstance(r, Mapping) else None
        if not isinstance(r, Mapping) or r.get("independently_verified") is not True or not (isinstance(sha, str) and len(sha) == 64 and all(ch in "0123456789abcdef" for ch in sha)):
            return {"pass": False, "reason": "MEASUREMENT_RECEIPT_INVALID", "candidate_id": cid}
        if r.get("subject_sha256") != _subject(cid, m):
            return {"pass": False, "reason": "MEASUREMENT_RECEIPT_SUBJECT_MISMATCH", "candidate_id": cid}
        if float(m["cost_usd_ucb"]) != 0.0:
            return {"pass": False, "reason": "HARD_ZERO_SPEND_VIOLATION", "candidate_id": cid}
        rows.append((cid, {k: float(m[k]) for k in AUTH_MAX + AUTH_MIN}))
    if not rows:
        return {"pass": False, "reason": "NO_CANDIDATES"}
    nondominated = []
    dominated_by = {}
    for cid, m in rows:
        doms = sorted(o for o, om in rows if o != cid and _adominates(om, m))
        if doms:
            dominated_by[cid] = doms
        else:
            nondominated.append(cid)
    return {"pass": True, "reason": None, "nondominated_candidate_ids": sorted(nondominated), "dominated_by": dominated_by}


def oracles_schedule():
    def reference_schedule(inst, out, solve):
        exp = schedule_model(inst)
        if bool(out.get("pass")) != exp["pass"]:
            return False, f"pass={out.get('pass')} expected {exp['pass']} ({inst.get('defect')}; solver reason {out.get('reason')})"
        if not exp["pass"]:
            ok = out.get("reason") == exp["reason"] and out.get("candidate_id") == exp.get("candidate_id")
            return ok, f"fail-closed reason {out.get('reason')}/{out.get('candidate_id')} expected {exp['reason']}/{exp.get('candidate_id')}"
        ok = out.get("nondominated_candidate_ids") == exp["nondominated_candidate_ids"] and out.get("dominated_by") == exp["dominated_by"]
        return ok, f"frontier {out.get('nondominated_candidate_ids')} expected {exp['nondominated_candidate_ids']}"

    def authority_envelope(inst, out, solve):
        if out.get("promotion_authority") is not False or out.get("terminal_authority") is not False:
            return False, "promotion/terminal authority leaked"
        if out.get("terminal_credit_delta") != 0 or out.get("incremental_spend_usd") != 0:
            return False, "credit or spend reported"
        if out.get("schedule_authority") is not (True if out.get("pass") else False):
            return False, "schedule authority does not follow the verdict"
        if out.get("pass"):
            ids = [c["candidate_id"] for c in inst["candidates"]]
            nd = out.get("nondominated_candidate_ids") or []
            db = out.get("dominated_by") or {}
            if sorted(list(nd) + list(db)) != sorted(ids):
                return False, "every candidate must be either nondominated or dominated"
            if set(nd) & set(db):
                return False, "candidate both nondominated and dominated"
        return True, "no promotion/terminal authority, zero credit, partition holds"

    def tamper_after_receipt_is_refused(inst, out, solve):
        if not out.get("pass"):
            return True, "instance already fails closed; nothing to tamper"
        tampered = copy.deepcopy(inst)
        rng = random.Random(len(json.dumps(inst, sort_keys=True)))
        victim = rng.choice(tampered["candidates"])
        key = rng.choice(AUTH_MAX[:4])
        victim["metrics"][key] = victim["metrics"][key] + 1  # better numbers, same receipt
        out2 = solve(tampered)
        ok = out2.get("pass") is False and out2.get("reason") == "MEASUREMENT_RECEIPT_SUBJECT_MISMATCH" and out2.get("candidate_id") == victim["candidate_id"]
        return ok, "metrics improved after the receipt -> " + (f"refused ({out2.get('reason')})" if ok else f"NOT refused: {out2.get('reason')} {out2.get('candidate_id')}")

    def permutation_invariance(inst, out, solve):
        if not out.get("pass"):
            return True, "fail-closed instance; order-dependent reason is allowed"
        shuffled = copy.deepcopy(inst)
        random.Random(7 + len(inst["candidates"])).shuffle(shuffled["candidates"])
        out2 = solve(shuffled)
        same = out2.get("pass") is True and out2.get("nondominated_candidate_ids") == out.get("nondominated_candidate_ids") and out2.get("dominated_by") == out.get("dominated_by")
        return same, "input order " + ("does not" if same else "DOES") + " change the frontier"

    return [
        {"id": "REFERENCE_SCHEDULE", "check": reference_schedule},
        {"id": "AUTHORITY_ENVELOPE", "check": authority_envelope},
        {"id": "TAMPER_AFTER_RECEIPT_IS_REFUSED", "check": tamper_after_receipt_is_refused},
        {"id": "PERMUTATION_INVARIANCE", "check": permutation_invariance},
    ]
