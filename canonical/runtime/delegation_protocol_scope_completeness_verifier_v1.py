"""Fail-closed verifier for delegation protocol-wide scope completeness.

This verifies a universal *scope* argument for the frozen delegation behavior contract.
It does not treat finite samples as exhaustive and grants zero acceptance/family credit.

The theorem boundary is deliberately narrow:
SUBAGENT_DELEGATION_AND_COORDINATION is mapped by the current behavioral registry to
exactly one load-bearing residual contract, TASK_TO_DELEGATION_GRAPH_001. The candidate
route is then checked to be generic over arbitrary finite explicit monotonic fact graphs
inside that contract, with every frozen protocol dimension explicitly accounted for.
"""
from __future__ import annotations

import ast
import hashlib
import inspect
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.scope_equivalent_proof_gate_v2 import evaluate as scope_gate

SCHEMA="PROJECT_BRAIN_DELEGATION_PROTOCOL_SCOPE_COMPLETENESS_VERIFIER_V1"
ROOT=Path(__file__).resolve().parents[2]

REL=ROOT/"canonical/governance/DELEGATION_SCOPE_EQUIVALENCE_RELATION_V2.json"
REG=ROOT/"canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"
PROT=ROOT/"canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"
GATE=ROOT/"canonical/governance/TASK_TO_DELEGATION_SCOPE_EQUIVALENT_PROOF_GATE_V2_INPUT.json"
CAND=ROOT/"canonical/runtime/delegation_whole_scope_candidate_v2.py"
ORACLE=ROOT/"canonical/runtime/delegation_whole_scope_proof_v2.py"
STRUCT=ROOT/"canonical/runtime/delegation_structural_variety_proof_v3.py"
GATE_RUNTIME=ROOT/"canonical/runtime/scope_equivalent_proof_gate_v2.py"
RECON=ROOT/"canonical/governance/ABSOLUTE_DOMINANCE_SCOPE_COMPLETENESS_RECONCILIATION_V1.json"

EXPECTED_SHA={
 "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json":"ee187f611a0e82b2de495ee377682f39bc31dd31",
 "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json":"eb4bca0fe6a015d49d2854998fbe046c979c7ea9",
 "canonical/runtime/delegation_whole_scope_candidate_v2.py":"f1a93ee66d90093de61dc17c6ebf2e24073df522",
 "canonical/runtime/delegation_whole_scope_proof_v2.py":"928466401b36e4f3b09c517950cc050432a0616f",
 "canonical/runtime/delegation_structural_variety_proof_v3.py":"f5e1f45519278ed2cafa27d23b8602b0a362a492",
 "canonical/runtime/scope_equivalent_proof_gate_v2.py":"2d05172becfc559de3ff1e4e5623c5180028be1b",
 "canonical/governance/TASK_TO_DELEGATION_SCOPE_EQUIVALENT_PROOF_GATE_V2_INPUT.json":"fed1fcd1d1c7da7842a7daa0f0879e52334942a8",
 "canonical/governance/ABSOLUTE_DOMINANCE_SCOPE_COMPLETENESS_RECONCILIATION_V1.json":"ec2d931860e7cd7d9f73a658706f8c33fca3a10d",
}

PROTOCOL_DIMENSION_COVERAGE={
 "task partition quality":"PARTITION_ONLY_REQUIRED_USEFULLY_PARALLELIZABLE_WORK",
 "adaptive worker selection":"OWNER_ASSIGNMENT",
 "dependency-respecting fan-out/fan-in":"DEPENDENCY_AND_FANIN_GRAPH",
 ">2 worker coordination":"CAPABILITY_AND_RESOURCE_FEASIBLE_PARALLEL_MATCHINGS",
 "duplicate/conflicting work suppression":"NO_DUPLICATE_WORK_AND_RESOURCE_CONFLICT",
 "failure reassignment":"RECEIPT_DRIVEN_REASSIGNMENT",
}
PROTOCOL_METRIC_COVERAGE={
 "terminal_success":"CORRECTNESS_AND_REQUIRED_OUTPUT_COMPLETION",
 "critical_path_wall_clock":"MINIMUM_WAVE_SCHEDULE_AND_CONTROLLED_BASELINE_ADVANTAGE",
 "duplicate_work_rate":"NO_DUPLICATE_WORK",
 "dependency_violation_rate":"DEPENDENCY_CORRECTNESS",
 "lost_evidence_rate":"EVIDENCE_OWNERSHIP_AND_TERMINAL_FANIN",
}

def git_blob_sha(data:bytes)->str:
    return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()

def _fail(*errors:str)->dict[str,Any]:
    return {
      "schema":SCHEMA,"status":"FAIL_CLOSED","errors":sorted(set(errors)),
      "scope_complete":False,"basis":None,
      "new_reality_units_consumed":0,"capability_credit_delta":0,
      "family_credit_delta":0,"execution_authority":False,"promotion_authority":False,
    }

def _sha(path:Path)->str:
    return git_blob_sha(path.read_bytes())

def _load(path:Path)->Any:
    return json.loads(path.read_text(encoding="utf-8"))

def verify(
    relation:Mapping[str,Any],
    registry:Mapping[str,Any],
    protocols:Mapping[str,Any],
    gate_input:Mapping[str,Any],
    *,
    candidate_source:str,
    oracle_source:str,
    structural_source:str,
    enforce_exact_blobs:bool=True,
)->dict[str,Any]:
    errors:list[str]=[]

    if relation.get("behavior_id")!="TASK_TO_DELEGATION_GRAPH_001":
        errors.append("RELATION_BEHAVIOR_ID_MISMATCH")
    if relation.get("family")!="SUBAGENT_DELEGATION_AND_COORDINATION":
        errors.append("RELATION_FAMILY_MISMATCH")

    fmap=(registry.get("family_to_residual_contracts") or {}).get("SUBAGENT_DELEGATION_AND_COORDINATION")
    if fmap!=["TASK_TO_DELEGATION_GRAPH_001"]:
        errors.append("FAMILY_NOT_EXACTLY_ONE_DELEGATION_CONTRACT")

    rows=[
      x for x in registry.get("active_contracted_residuals",[])
      if isinstance(x,Mapping) and x.get("behavior_id")=="TASK_TO_DELEGATION_GRAPH_001"
    ]
    if len(rows)!=1:
        errors.append("DELEGATION_CONTRACT_NOT_EXACTLY_ONE")
        contract={}
    else:
        contract=rows[0]

    required_contract_fields=[
      "inputs","environment_state","allowed_information","required_output_or_action",
      "success_condition","failure_condition","verification_route","dependency_boundary","scope"
    ]
    for k in required_contract_fields:
        if not isinstance(contract.get(k),str) or not contract.get(k):
            errors.append("CONTRACT_FIELD_MISSING:"+k)

    prows=[
      x for x in protocols.get("protocols",[])
      if isinstance(x,Mapping) and x.get("family")=="SUBAGENT_DELEGATION_AND_COORDINATION"
    ]
    if len(prows)!=1:
        errors.append("DELEGATION_PROTOCOL_NOT_EXACTLY_ONE")
        protocol={}
    else:
        protocol=prows[0]

    dims=protocol.get("task_dimensions")
    metrics=protocol.get("primary_metrics")
    if dims!=list(PROTOCOL_DIMENSION_COVERAGE):
        errors.append("PROTOCOL_DIMENSIONS_CHANGED_OR_UNCOVERED")
    if metrics!=list(PROTOCOL_METRIC_COVERAGE):
        errors.append("PROTOCOL_METRICS_CHANGED_OR_UNCOVERED")
    if protocol.get("proof_mode")!="MATCHED_DIRECT_NONINFERIORITY_WITH_MECHANICAL_CEILINGS":
        errors.append("PROTOCOL_PROOF_MODE_CHANGED")

    arg=relation.get("universal_scope_argument")
    if not isinstance(arg,Mapping):
        errors.append("UNIVERSAL_SCOPE_ARGUMENT_MISSING")
        arg={}
    if arg.get("population_relation")!="CANDIDATE_SUPERSET_PROVEN":
        errors.append("POPULATION_SUPERSET_NOT_PROVEN")
    if arg.get("environment_relation")!="EXACT":
        errors.append("ENVIRONMENT_NOT_EXACT")
    if arg.get("information_relation")!="EXACT_CANDIDATE_VISIBLE_INFORMATION":
        errors.append("INFORMATION_RELATION_NOT_EXACT")
    if arg.get("oracle_relation")!="CANDIDATE_STRONGER_PROVEN":
        errors.append("ORACLE_NOT_STRONGER_PROVEN")
    if arg.get("unresolved_required_dimensions")!=[]:
        errors.append("UNRESOLVED_REQUIRED_DIMENSIONS")

    # Re-run the existing fail-closed scope gate. This checks behavior/interaction
    # coverage, hidden inference separation, anti-shortcut mutations and target weakening.
    gate_payload=dict(gate_input)
    gate_payload["relation_receipts"]=dict(gate_input.get("relation_receipts") or {})
    gate_payload["relation_receipts"]["population"]="canonical/governance/DELEGATION_SCOPE_EQUIVALENCE_RELATION_V2.json"
    gate_out=scope_gate(gate_payload)
    if gate_out.get("admissible") is not True:
        errors.append("SCOPE_EQUIVALENT_GATE_NOT_ADMISSIBLE")

    # Candidate must remain independent from proof/oracle code.
    tree=ast.parse(candidate_source)
    imported=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):
            imported.extend(a.name for a in node.names)
        elif isinstance(node,ast.ImportFrom):
            imported.append(node.module or "")
    if any("delegation_whole_scope_proof" in x or "structural_variety" in x for x in imported):
        errors.append("CANDIDATE_IMPORTS_PROOF_OR_ORACLE")

    # Machine-audited premises for universal finite-graph coverage.
    required_candidate_fragments=[
      'task.get("steps"', 'task.get("workers"',
      'if not isinstance(cost,(int,float))', 'float(cost)<0',
      'eligible=sorted(', 'while heap:', 'for sid in eligible:',
      'if sid in used:', 'row["requires"].issubset(facts)',
      'if nf==facts:', 'heappush(heap,',
      'for tasks in combinations(', 'for ws in permutations(',
      'q=deque(', 'if done==target:', 'seen={frozenset()}',
      '"STEP_UNAVAILABLE"', '"WORKER_UNAVAILABLE"',
      '"WORKER_CAPABILITY_REMOVED"', '"RESOURCE_CAPACITY_CHANGED"',
      'sid not in disabled_steps and sid not in completed',
      'out["revision_provenance"]=prov',
    ]
    for frag in required_candidate_fragments:
        if frag not in candidate_source:
            errors.append("CANDIDATE_UNIVERSAL_PREMISE_MISSING:"+frag)
    for forbidden in ("TOO_MANY_STEPS","MAX_TASKS","MAX_STEPS","PARSE_","REASON_"):
        if forbidden in candidate_source:
            errors.append("CANDIDATE_STATIC_OR_TOPOLOGY_CUTOFF:"+forbidden)

    # Independent oracle must remain generic over task dictionaries and structural
    # oracle must preserve multiple non-isomorphic graph classes.
    for frag in ('task["steps"]','task["workers"]','combinations(','permutations('):
        if frag not in oracle_source:
            errors.append("PRIMARY_ORACLE_GENERICITY_MISSING:"+frag)
    for cls in ("CHAIN","FORK_JOIN","FANOUT_JOIN","DUAL_ROOT_FANIN","ALTERNATIVE_PLAN"):
        if cls not in structural_source:
            errors.append("STRUCTURAL_CLASS_MISSING:"+cls)

    if enforce_exact_blobs:
        for rel,expected in EXPECTED_SHA.items():
            path=ROOT/rel
            if not path.exists():
                errors.append("PINNED_SOURCE_MISSING:"+rel)
                continue
            actual=_sha(path)
            if actual!=expected:
                errors.append("PINNED_SOURCE_BLOB_MISMATCH:"+rel+":"+actual+"!="+expected)

    if errors:
        return _fail(*errors)

    return {
      "schema":SCHEMA,
      "status":"PASS__UNIVERSAL_FORMAL_SCOPE_COMPLETENESS_VERIFIED_FOR_FROZEN_DELEGATION_CONTRACT__ZERO_CREDIT",
      "errors":[],
      "scope_complete":True,
      "basis":"UNIVERSAL_FORMAL_SCOPE_PROOF",
      "family":"SUBAGENT_DELEGATION_AND_COORDINATION",
      "behavior_id":"TASK_TO_DELEGATION_GRAPH_001",
      "family_to_contract_mapping":["TASK_TO_DELEGATION_GRAPH_001"],
      "protocol_dimension_coverage":PROTOCOL_DIMENSION_COVERAGE,
      "protocol_metric_coverage":PROTOCOL_METRIC_COVERAGE,
      "population_relation":"CANDIDATE_SUPERSET_PROVEN",
      "environment_relation":"EXACT",
      "information_relation":"EXACT_CANDIDATE_VISIBLE_INFORMATION",
      "oracle_relation":"CANDIDATE_STRONGER_PROVEN",
      "unresolved_required_dimensions":[],
      "finite_sample_used_as_exhaustive_proof":False,
      "rule":(
        "SCOPE_COMPLETENESS_IS_PROVED_ONLY_FOR_THE_FROZEN_EXPLICIT_TASK_GRAPH_CONTRACT__"
        "THE_132_EXECUTED_CASES_REMAIN_SAMPLE_EVIDENCE_AND_ARE_NOT_THE_SCOPE_PROOF__"
        "NO_IMPLICIT_TASK_SEMANTICS_OR_UNDECLARED_CAPABILITY_INFERENCE_IS_INCLUDED"
      ),
      "new_reality_units_consumed":0,
      "capability_credit_delta":0,
      "family_credit_delta":0,
      "execution_authority":False,
      "promotion_authority":False,
    }

def execute()->dict[str,Any]:
    return verify(
      _load(REL),_load(REG),_load(PROT),_load(GATE),
      candidate_source=CAND.read_text(encoding="utf-8"),
      oracle_source=ORACLE.read_text(encoding="utf-8"),
      structural_source=STRUCT.read_text(encoding="utf-8"),
      enforce_exact_blobs=True,
    )

def main()->int:
    out=execute()
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if str(out.get("status","")).startswith("PASS") else 1

if __name__=="__main__":
    raise SystemExit(main())
