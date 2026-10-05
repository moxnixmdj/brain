from __future__ import annotations
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_TB4_BUILDKITE_PROTOCOL_EQUIVALENCE_VERDICT_V1"
REQUIRED=(
    "P1_EXACT_HARBOR_RUNTIME_BINDING",
    "P2_SEPARATE_VERIFIER_ARTIFACT_REHYDRATION",
    "P3_COMPOSE_SIDECAR_MCP_AND_SERVICE_ARTIFACT",
    "P4_VERIFIER_NO_NETWORK_BASELINE",
    "P5_COLLECT_HOOK_ORDERING",
    "P6_CONTAINER_RESOURCE_LIMITS",
    "P7_TIMEOUT_ENVELOPE",
)
TARGET="CODING_TB4_GE_66_4"
FROZEN="452bf305c6daa62fc59061d22133a7cbc7c1572e"

def evaluate(spec: Mapping[str,Any], receipt: Mapping[str,Any]) -> dict[str,Any]:
    errors=[]
    if spec.get("schema")!="PROJECT_BRAIN_TB4_BUILDKITE_PROTOCOL_EQUIVALENCE_FALSIFICATION_20261006_V1":
        errors.append("SPEC_SCHEMA")
    if spec.get("target_predicate")!=TARGET:
        errors.append("TARGET_PREDICATE")
    subject=spec.get("frozen_public_subject") or {}
    if subject.get("commit")!=FROZEN:
        errors.append("FROZEN_SUBJECT")
    if receipt.get("target_predicate")!=TARGET:
        errors.append("RECEIPT_TARGET")
    if receipt.get("frozen_dataset_commit")!=FROZEN:
        errors.append("FROZEN_DATASET_NOT_EXACTLY_BOUND")
    if receipt.get("provider")!="Buildkite":
        errors.append("PROVIDER_NOT_BUILDKITE")
    probes=receipt.get("protocol_probe")
    if not isinstance(probes,Mapping):
        probes={}
    missing=[p for p in REQUIRED if probes.get(p) is not True]
    if missing:
        errors.extend("PROTOCOL_OBLIGATION_UNPROVED:"+p for p in missing)
    if receipt.get("terminal_cases_consumed",0)!=0:
        errors.append("TERMINAL_CASE_CONSUMPTION_NONZERO")
    if receipt.get("incremental_spend_usd",0)!=0:
        errors.append("INCREMENTAL_SPEND_NONZERO")
    passed=not errors
    return {
        "schema":SCHEMA,
        "status":"PASS__PUBLIC_HARBOR_CARRIER_PROTOCOL_EQUIVALENCE_ZERO_CASE_BOUND__NO_TARGET_HARNESS_CREDIT" if passed else "FAIL_CLOSED__PROTOCOL_EQUIVALENCE_NOT_ESTABLISHED",
        "pass":passed,
        "errors":sorted(set(errors)),
        "missing_protocol_obligations":missing,
        "public_harbor_carrier_protocol_equivalence_bound":passed,
        "anthropic_release_target_harness_relation_bound":False,
        "terminal_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
        "fresh_reality_authority":False,
    }

def current_runtime_receipt_projection(buildkite_receipt: Mapping[str,Any]) -> dict[str,Any]:
    pe=buildkite_receipt.get("provider_execution") or {}
    return {
        "schema":"PROJECT_BRAIN_TB4_BUILDKITE_PROTOCOL_PROBE_RECEIPT_V1",
        "target_predicate":TARGET,
        "provider":pe.get("provider"),
        "frozen_dataset_commit":None,
        "protocol_probe":{},
        "terminal_cases_consumed":(buildkite_receipt.get("accounting") or {}).get("terminal_cases_consumed",0),
        "incremental_spend_usd":(buildkite_receipt.get("accounting") or {}).get("incremental_spend_usd",0),
    }
