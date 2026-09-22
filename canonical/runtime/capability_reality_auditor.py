#!/usr/bin/env python3
import argparse, html, json, sys
from pathlib import Path
from datetime import datetime, timezone

def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise RuntimeError(f"cannot read {path}: {e}")

def add(checks, check_id, ok, severity, message, evidence=None):
    checks.append({
        "id": check_id,
        "ok": bool(ok),
        "severity": severity,
        "message": message,
        "evidence": evidence or {}
    })

def audit(root: Path):
    c = root / "canonical"
    pointer_path = c / "CANONICAL_POINTER.json"
    pointer = load_json(pointer_path)
    checks = []

    # 1. Mission lock must exist and explicitly subordinate proxies.
    ml = pointer.get("mission_lock") or {}
    add(checks, "MISSION_LOCK_PRESENT",
        bool(ml.get("terminal_objective")) and "CAPABIL" in ml.get("terminal_objective",""),
        "critical",
        "Canonical mission lock must target real capability realization.",
        {"terminal_objective": ml.get("terminal_objective")})
    add(checks, "PREDICATES_SUBORDINATE",
        "SUBORDINATE" in ml.get("predicates_role",""),
        "critical",
        "Predicates must be subordinate evidence, not the mission.",
        {"predicates_role": ml.get("predicates_role")})
    add(checks, "BENCHMARKS_SUBORDINATE",
        "SUBORDINATE" in ml.get("benchmarks_role",""),
        "critical",
        "Benchmarks must be subordinate diagnostics, not the mission.",
        {"benchmarks_role": ml.get("benchmarks_role")})

    # 2. Internal Astra suite must never be promoted into external parity.
    aa = pointer.get("active_agent") or {}
    cf = pointer.get("current_frontier") or {}
    external = str(aa.get("external_astra_parity", cf.get("astra_external_parity",""))).upper()
    full_claim = aa.get("full_astra_claim")
    internal_scope = str(aa.get("astra_qualification_scope",""))
    bad_external = full_claim is True or external in {"VERIFIED","PROVEN","PASS","TRUE"}
    add(checks, "NO_INTERNAL_TO_EXTERNAL_ASTRA_PARITY",
        not bad_external and "61_PREDICATE_SUITE_ONLY" in internal_scope,
        "critical",
        "Internal Astra-themed suite completion must not be represented as external Astra parity.",
        {"full_astra_claim": full_claim, "external_astra_parity": external, "scope": internal_scope})

    # 3. Real-superworker population must equal active identities that actually count.
    active = pointer.get("active_superworkers") or []
    if isinstance(active, dict): active = [active]
    counted = [x for x in active if isinstance(x, dict) and x.get("counts_as_real_superworker") is True]
    declared = cf.get("superworker_real")
    add(checks, "P_REAL_MATCHES_ACTIVE_IDENTITIES",
        isinstance(declared, int) and declared == len(counted),
        "critical",
        "P_real must equal the number of active identities explicitly counted as real.",
        {"declared_p_real": declared, "counted_active_identities": len(counted)})

    # 4. If composition-error correction exists, composite identities cannot still count as real.
    correction_path = c / "qualification" / "SUPERWORKER_COMPOSITION_ERROR_CORRECTION_V1.json"
    correction_exists = correction_path.exists()
    composite_bad = []
    for name in ("SUPERWORKER_INTEGRATED_1.json","SUPERWORKER_INTEGRATED_2.json"):
        p = c / "agents" / name
        if p.exists():
            ident = load_json(p)
            if ident.get("counts_as_real_superworker") is True:
                composite_bad.append(ident.get("agent_id", name))
    add(checks, "NO_COMPOSITE_WORKER_PROMOTION",
        not correction_exists or not composite_bad,
        "critical",
        "Component evidence from different executors cannot be composed into one real worker.",
        {"correction_exists": correction_exists, "still_counted_as_real": composite_bad})

    # 5. Provider bans must remain enforced.
    pr = pointer.get("provider_rules") or {}
    val_rule = str(pr.get("val_town","")).upper()
    add(checks, "VAL_TOWN_FORBIDDEN",
        "DO_NOT_USE" in val_rule or "UNAVAILABLE" in val_rule,
        "high",
        "Val Town must remain noncanonical/forbidden unless explicitly superseded by a newer authority decision.",
        {"val_town": pr.get("val_town")})
    allowed = json.dumps((pointer.get("execution_governance") or {}).get("only_current_allowed_frontier_actions",[])).lower()
    add(checks, "NO_FORBIDDEN_PROVIDER_IN_ALLOWED_ACTIONS",
        "val_town" not in allowed and "sprites" not in allowed,
        "high",
        "Current allowed frontier actions must not route through forbidden providers.",
        {"allowed_actions": (pointer.get("execution_governance") or {}).get("only_current_allowed_frontier_actions",[])})

    # 6. Frontier must be capability-first, not scaling/proxy-first.
    blocker = str(cf.get("critical_blocker",""))
    next_step = str(cf.get("next_step",""))
    proxy_terms = ("PREDICATE","BENCHMARK_SCORE","61_OF_61","SCALE_TO_","WORKER_COUNT")
    proxy_hit = [t for t in proxy_terms if t in next_step.upper()]
    add(checks, "FRONTIER_NOT_PROXY_GOAL",
        not proxy_hit,
        "critical",
        "Next step must target a real capability gap, not a proxy metric.",
        {"critical_blocker": blocker, "next_step": next_step, "proxy_terms_found": proxy_hit})

    # 7. Current truth after composition correction should not claim a real integrated cognitive worker yet.
    correction_flag = str(cf.get("superworker_truth_scope","")).upper()
    if correction_exists:
        add(checks, "COMPOSITION_CORRECTION_RECONCILED",
            declared == 0 and ("NO_SINGLE_INTEGRATED" in correction_flag or "NO_REAL_INTEGRATED" in correction_flag),
            "critical",
            "After the composition correction, P_real must remain zero until one identity proves the full loop.",
            {"p_real": declared, "superworker_truth_scope": cf.get("superworker_truth_scope")})

    # 8. Generation and governance must include truth-first and capability realization laws.
    laws = pointer.get("mandatory_laws") or []
    add(checks, "TRUTH_FIRST_LAW_BOUND",
        any("TRUTH_FIRST_AND_NO_DUPLICATE_EXECUTION_LAW_V1" in x for x in laws),
        "high",
        "Truth-first/no-duplicate law must be mandatory.")
    add(checks, "CAPABILITY_REALIZATION_LAW_BOUND",
        any("CAPABILITY_REALIZATION_MISSION_LOCK_V1" in x for x in laws),
        "critical",
        "Capability-realization mission lock must be mandatory.")

    failures = [x for x in checks if not x["ok"]]
    result = {
        "schema": "PROJECT_BRAIN_CAPABILITY_REALITY_AUDIT_V1",
        "audited_at_utc": datetime.now(timezone.utc).isoformat(),
        "canonical_generation": pointer.get("canonical_generation"),
        "status": "PASS" if not failures else "FAIL",
        "check_count": len(checks),
        "pass_count": len(checks)-len(failures),
        "fail_count": len(failures),
        "checks": checks
    }
    return result

def render_html(result):
    rows=[]
    for c in result["checks"]:
        rows.append(
            "<tr><td>"+html.escape(c["id"])+"</td><td>"+("PASS" if c["ok"] else "FAIL")+
            "</td><td>"+html.escape(c["severity"])+"</td><td>"+html.escape(c["message"])+
            "</td><td><pre>"+html.escape(json.dumps(c.get("evidence",{}),ensure_ascii=False,indent=2))+"</pre></td></tr>"
        )
    return """<!doctype html><html><head><meta charset='utf-8'><title>Project Brain Capability Reality Audit</title>
<style>body{font-family:system-ui,Segoe UI,Arial,sans-serif;max-width:1200px;margin:32px auto;padding:0 16px}table{border-collapse:collapse;width:100%%}th,td{border:1px solid #bbb;padding:8px;vertical-align:top}pre{white-space:pre-wrap;margin:0}.summary{font-size:1.1rem;font-weight:600}</style></head>
<body><h1>Project Brain Capability Reality Audit</h1>
<p class='summary'>Status: %s | Pass: %s | Fail: %s | Generation: %s</p>
<table><thead><tr><th>Check</th><th>Result</th><th>Severity</th><th>Meaning</th><th>Evidence</th></tr></thead><tbody>%s</tbody></table></body></html>""" % (
        html.escape(result["status"]), result["pass_count"], result["fail_count"],
        html.escape(str(result.get("canonical_generation"))), "".join(rows))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--json-out", default="capability_reality_audit.json")
    ap.add_argument("--html-out", default="capability_reality_audit.html")
    args=ap.parse_args()
    result=audit(Path(args.root))
    Path(args.json_out).write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    Path(args.html_out).write_text(render_html(result),encoding="utf-8")
    print(json.dumps({"status":result["status"],"pass_count":result["pass_count"],"fail_count":result["fail_count"]}))
    sys.exit(0 if result["status"]=="PASS" else 2)

if __name__=="__main__":
    main()
