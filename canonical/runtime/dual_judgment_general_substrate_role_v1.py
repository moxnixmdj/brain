"""Zero-reality role qualification for the dual judgment model dependency.

This proves only source-gate role admissibility. It does not prove terminal
Finance or Unknown-Domain performance.
"""
from __future__ import annotations
import ast, hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_DUAL_JUDGMENT_GENERAL_SUBSTRATE_ROLE_VERDICT_V1"

PATHS={
 "candidate":"canonical/governance/DUAL_JUDGMENT_GENERAL_SUBSTRATE_ROLE_QUALIFICATION_V1.json",
 "envelope":"canonical/capabilities/opus55/DUAL_JUDGMENT_CONTROL_ENVELOPE_V1.json",
 "runtime":"canonical/runtime/judgment_control_envelope_v1.py",
 "tests":"canonical/tests/test_judgment_control_envelope_v1.py",
 "source_gate":"canonical/runtime/acceptance_capability_source_gate_v2.py",
 "material":"canonical/verification/DUAL_JUDGMENT_CONTROL_CURRENT_MAIN_INDEPENDENT_VERIFICATION_20261003_V1.json",
 "law":"canonical/laws/GENERAL_COGNITION_SUBSTRATE_AND_CAPABILITY_OWNERSHIP_LAW_V3.md",
}
EXPECTED={
 PATHS["envelope"]:"6ea46314887a59de742e56f32893de9efce1103a",
 PATHS["runtime"]:"5ebfd1e7fa871da89ecca40ffeb8dd6575c21582",
 PATHS["tests"]:"e712746ecfb0c912779fc6436cbb4f2b51521c3d",
 PATHS["source_gate"]:"b168b131f6383e158bdc0d931439d14e61f2a5de",
 PATHS["material"]:"041b73f3c212d86d870554d2dc7b8ad0b691d921",
 PATHS["law"]:"7532aa0a5700fc061c9cf6b003fa8a9ac27d3972",
}

FORBIDDEN_IMPORT_PREFIXES=(
 "openai","anthropic","requests","httpx","aiohttp","socket","urllib",
 "google.generativeai","google.genai","ollama"
)
FORBIDDEN_PROVIDER_TOKENS=("claude","gpt-","openai","anthropic","gemini","mistral","pollinations")

def blob(path:str)->str:
    data=(ROOT/path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def load(path:str):
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

def evaluate():
    errors=[]
    drift={p:{"expected":h,"actual":blob(p)} for p,h in EXPECTED.items() if blob(p)!=h}
    if drift:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED__SOURCE_BLOB_DRIFT","pass":False,"errors":["SOURCE_BLOB_DRIFT"],"drift":drift}

    env=load(PATHS["envelope"])
    mat=load(PATHS["material"])
    source=(ROOT/PATHS["runtime"]).read_text(encoding="utf-8")
    tree=ast.parse(source)

    imports=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):
            imports.extend(a.name for a in node.names)
        elif isinstance(node,ast.ImportFrom) and node.module:
            imports.append(node.module)
    bad_imports=sorted({x for x in imports if any(x==p or x.startswith(p+".") for p in FORBIDDEN_IMPORT_PREFIXES)})
    if bad_imports:
        errors.append("OPERATIVE_RUNTIME_IMPORTS_MODEL_OR_NETWORK_PROVIDER:"+",".join(bad_imports))

    lowered=source.lower()
    bad_tokens=sorted({x for x in FORBIDDEN_PROVIDER_TOKENS if x in lowered})
    if bad_tokens:
        errors.append("OPERATIVE_RUNTIME_CONTAINS_PROVIDER_SPECIFIC_TOKEN:"+",".join(bad_tokens))

    # One mode-parametric configured decision path must serve both target families.
    if 'MODES = {"FINANCE", "UNKNOWN_DOMAIN"}' not in source:
        errors.append("SHARED_TWO_MODE_RUNTIME_NOT_BOUND")
    if "def configured_terminal_decision(proposal: Any, proof_bundle: Any, *, mode: str)" not in source:
        errors.append("GENERIC_PROPOSAL_PROOF_BUNDLE_INTERFACE_NOT_BOUND")
    if "def bare_terminal_decision(proposal:" not in source:
        errors.append("BARE_COUNTERFACTUAL_PATH_NOT_BOUND")

    verified=set(mat.get("verified") or [])
    required_material={
      "EXACT_CURRENT_MAIN_ENVELOPE_RUNTIME_AND_TEST_BYTES",
      "PROOF_CARRYING_CONFIGURATION_MATERIALLY_CONTROLS_FINANCE_AND_UNKNOWN_DOMAIN_TERMINAL_DECISIONS",
      "MATERIALITY_DOES_NOT_LAUNDER_GENERAL_SUBSTRATE_QUALIFICATION",
    }
    if not str(mat.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("MATERIAL_CONTROL_RECEIPT_NOT_INDEPENDENT_PASS")
    if not required_material.issubset(verified):
        errors.append("MATERIAL_CONTROL_REQUIRED_FACTS_MISSING")

    route=dict(env.get("source_gate_v2_candidate") or {})
    required_route={
      "benchmark_harness_zero_cost":True,
      "scorer_frozen":True,
      "brain_candidate_bound":True,
      "brain_owned_operative_configuration":True,
      "capability_package_contains_configuration":True,
      "promotion_evaluates_brain_configured_system":True,
      "external_hidden_target_capability_provider":False,
      "ownership_claim_relies_on_model_standalone_superiority":False,
      "future_use_requires_capability_rediscovery":False,
      "model_role":"GENERAL_COGNITION_SUBSTRATE",
      "model_dependency_count":1,
      "model_dependencies_declared":True,
      "incremental_spend_usd":0,
    }
    for k,v in required_route.items():
        if route.get(k)!=v:
            errors.append("ROUTE_FIELD_DRIFT:"+k)

    # The missing two fields are derived only after the independent structural theorem.
    structural_role_ok=not errors
    route["configuration_materially_constrains_execution"]=structural_role_ok
    route["general_substrate_test_pass"]=structural_role_ok

    from canonical.runtime.acceptance_capability_source_gate_v2 import evaluate as gate
    out=gate(route)
    if structural_role_ok and out.get("pass") is not True:
        errors.append("SOURCE_GATE_DID_NOT_PASS_AFTER_PROVED_ROLE_CLASSIFICATION:"+",".join(out.get("errors") or []))

    ok=not errors
    return {
      "schema":SCHEMA,
      "status":"PASS__GENERAL_SUBSTRATE_ROLE_PROVED__DUAL_SOURCE_GATE_V2_ADMISSIBLE__ZERO_REALITY" if ok else "FAIL_CLOSED",
      "pass":ok,
      "errors":sorted(set(errors)),
      "general_substrate_test_pass":ok,
      "configuration_materially_constrains_execution":ok,
      "source_gate_v2_pass":bool(ok and out.get("pass") is True),
      "source_gate_errors":[] if ok else out.get("errors",[]),
      "requirements_eligible_to_close":[
        "BRAIN_OWNED_OR_PERMISSIVELY_INTERNALIZED_FINANCE_JUDGMENT_SOURCE_GATE_PASS",
        "BRAIN_OWNED_OR_PERMISSIVELY_INTERNALIZED_UNKNOWN_DOMAIN_JUDGMENT_SOURCE_GATE_PASS",
      ] if ok else [],
      "direct_oracle_execution_authority":bool(ok and out.get("clean_case_execution_authority") is True),
      "new_reality_units_consumed":0,
      "terminal_case_content_read":0,
      "incremental_spend_usd":0,
      "acceptance_predicate_delta":0,
      "family_acceptance_delta":0,
      "ownership_delta":0,
      "execution_authority":False,
      "promotion_authority":False,
      "hard_nonclaims":[
        "NO_FINANCE_DIRECT_LEAF_PASS",
        "NO_UNKNOWN_DOMAIN_DIRECT_LEAF_PASS",
        "NO_OPUS55_ACCEPTANCE_PREDICATE_CLOSED",
        "NO_WHOLE_FAMILY_OWNERSHIP_CREDIT",
      ],
    }

if __name__=="__main__":
    print(json.dumps(evaluate(),indent=2,sort_keys=True))
