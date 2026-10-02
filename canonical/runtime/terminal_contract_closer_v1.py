#!/usr/bin/env python3
"""Fail-closed terminal contract closure compiler.

Combines verified counterexample-envelope compression with prewave admission
requirements. It never grants terminal credit and never treats prediction,
simulation, or absence of a witness as proof.
"""
from __future__ import annotations
import json, argparse
from pathlib import Path
from canonical.runtime import terminal_counterexample_envelope_compiler as envelope

SCHEMA="PROJECT_BRAIN_TERMINAL_CONTRACT_CLOSER_V1"

def evaluate(data):
    if not isinstance(data,dict):
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","errors":["INPUT_MUST_BE_OBJECT"],
                "execution_authority":False,"terminal_credit_delta":0}
    rows=data.get("contracts")
    if not isinstance(rows,list) or not rows:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","errors":["CONTRACTS_MUST_BE_NONEMPTY_LIST"],
                "execution_authority":False,"terminal_credit_delta":0}
    out=[]; errors=[]
    for i,row in enumerate(rows):
        if not isinstance(row,dict):
            errors.append(f"CONTRACT_{i}_INVALID"); continue
        cid=row.get("contract_id")
        env_input=row.get("envelope_input")
        if not isinstance(cid,str) or not cid.strip() or not isinstance(env_input,dict):
            errors.append(f"CONTRACT_{i}_MISSING_ID_OR_ENVELOPE"); continue
        env=dict(env_input); env["contract_id"]=cid
        reduced=envelope.evaluate(env)
        residual=list(reduced.get("minimum_residual_proof_basis",[]))
        failed=list(reduced.get("failed_dimensions",[]))
        gate=bool(row.get("scope_gate_v2_independent_pass"))
        population=bool(row.get("terminal_population_binding_frozen"))
        population_verified=bool(row.get("terminal_population_binding_independent_pass"))
        acceptance=bool(row.get("terminal_acceptance_mode_frozen"))
        admissible=(not residual and not failed and
                    reduced.get("status")=="DECLARED_CONTRACT_DIMENSIONS_COVERED_BY_VERIFIED_EVIDENCE" and
                    gate and population and population_verified and acceptance)
        out.append({
            "contract_id":cid,
            "envelope_status":reduced.get("status"),
            "proved_dimensions":reduced.get("proved_dimensions_after_implication_closure",[]),
            "failed_dimensions":failed,
            "minimum_residual_proof_basis":residual,
            "counterexample_obligations":reduced.get("counterexample_obligations",[]),
            "scope_gate_v2_independent_pass":gate,
            "terminal_population_binding_frozen":population,
            "terminal_population_binding_independent_pass":population_verified,
            "terminal_acceptance_mode_frozen":acceptance,
            "prewave_route_admissible":admissible,
            "terminal_credit_delta":0,
        })
    if errors:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","errors":errors,"contracts":out,
                "execution_authority":False,"terminal_credit_delta":0}
    admissible=sum(int(x["prewave_route_admissible"]) for x in out)
    return {
        "schema":SCHEMA,
        "status":"ALL_PREWAVE_ROUTES_ADMISSIBLE" if admissible==len(out) else "PREWAVE_RESIDUAL_OPEN",
        "contract_count":len(out),
        "admissible_count":admissible,
        "contracts":out,
        "execution_authority":False,
        "terminal_credit_delta":0,
        "fresh_terminal_evidence_consumed":0,
        "authority_rule":"THIS_COMPILER_COMPRESSES_VERIFIED_RESIDUALS_AND_PREWAVE_BINDINGS_ONLY; TERMINAL_EXECUTION_REQUIRES_THE_CANONICAL_PREQUALIFICATION_REDUCER",
    }

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("input",type=Path)
    ns=ap.parse_args()
    result=evaluate(json.loads(ns.input.read_text(encoding="utf-8")))
    print(json.dumps(result,indent=2,sort_keys=True))
    return 1 if result["status"]=="FAIL_CLOSED" else 0

if __name__=="__main__": raise SystemExit(main())
