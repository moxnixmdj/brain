"""Verify frozen prewave binding for SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001.

This is prewave instrumentation verification only. It grants no terminal/capability credit.
"""
from __future__ import annotations
import ast, hashlib, json
from pathlib import Path

BIND="canonical/governance/SPECIFICATION_INDEPENDENT_ACCEPTANCE_PREWAVE_BINDING_V1.json"
FILES={
 "candidate":"canonical/runtime/m0a_raw_source_brain_candidate_v2.py",
 "hidden_oracle_and_scorer":"canonical/runtime/m0a_raw_source_terminal_suite_v2.py",
 "independent_failure_mode_model":"canonical/runtime/independent_acceptance_model.py",
 "acceptance_compiler":"canonical/runtime/requirement_acceptance_compiler.py",
 "multiplex_portfolios":"canonical/governance/OUTER_TERMINAL_MULTIPLEX_PORTFOLIOS_V1.json",
 "population_protocol":"canonical/governance/GLOBAL_TERMINAL_REPLACEMENT_POPULATION_PROTOCOL_V2.json",
}
def blob_sha(path:Path)->str:
    # Git blob SHA-1, matching GitHub contents sha.
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def verify(root:Path)->dict:
    errors=[]
    b=json.loads((root/BIND).read_text())
    if b.get("behavior_id")!="SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001":
        errors.append("BEHAVIOR_ID")
    for key,path in FILES.items():
        got=blob_sha(root/path)
        exp=b["exact_blobs"].get(key)
        if got!=exp: errors.append("BLOB_DRIFT:"+key)
    if b["information_boundary"].get("candidate_receives_hidden_oracle") is not False:
        errors.append("ORACLE_VISIBLE")
    if b["information_boundary"].get("candidate_receives_reference_solution") is not False:
        errors.append("REFERENCE_VISIBLE")
    if sorted(b["portfolio_binding"].get("portfolios",[]))!=["T0","T1","T2","T3"]:
        errors.append("PORTFOLIO_COVERAGE")
    if b["portfolio_binding"].get("behavior_id")!=b["behavior_id"]:
        errors.append("CROSS_BEHAVIOR_BIND")
    if b["post_freeze_selection_and_accounting"].get("adaptive_case_selection") is not False:
        errors.append("ADAPTIVE_SELECTION")
    if b["post_freeze_selection_and_accounting"].get("case_replacement") is not False:
        errors.append("CASE_REPLACEMENT")
    if b["post_freeze_selection_and_accounting"].get("tuning_replay") is not False:
        errors.append("TUNING_REPLAY")
    if b.get("open_domain_terminal_claim") is not False or b.get("execution_authority") is not False:
        errors.append("PREWAVE_OVERCLAIM")

    cand=(root/FILES["candidate"]).read_text()
    tree=ast.parse(cand)
    imports=[]
    for n in ast.walk(tree):
        if isinstance(n,(ast.Import,ast.ImportFrom)):
            if isinstance(n,ast.Import):
                imports += [a.name for a in n.names]
            elif n.module:
                imports.append(n.module)
    forbidden=("m0a_raw_source_terminal_suite_v2","_oracle")
    if any(x in cand for x in forbidden): errors.append("CANDIDATE_ORACLE_LEAK")
    if any("terminal_suite" in x for x in imports): errors.append("CANDIDATE_IMPORTS_ORACLE")

    suite=(root/FILES["hidden_oracle_and_scorer"]).read_text()
    if '"_oracle"' not in suite or "public_task" not in suite or "score_case" not in suite:
        errors.append("HIDDEN_SCORER_STRUCTURE")
    return {
      "schema":"PROJECT_BRAIN_SPECIFICATION_INDEPENDENT_ACCEPTANCE_PREWAVE_VERDICT_V1",
      "status":"PASS" if not errors else "FAIL_CLOSED",
      "errors":sorted(set(errors)),
      "execution_authority":False,
      "capability_credit_delta":0
    }
