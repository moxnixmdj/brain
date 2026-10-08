from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Mapping
import re

HEX64 = re.compile(r"^[0-9a-f]{64}$")

REQUIRED_TRUE = (
    "task_identity_bound",
    "actor_configuration_bound",
    "output_sha256_bound_before_certifier_exposure",
    "actor_write_closed_before_certifier_exposure",
    "hidden_verifier_not_exposed_to_actor",
    "certifier_identity_separate_from_actor",
    "certifier_cannot_mutate_actor_output",
    "proof_object_is_post_hoc_only",
    "proof_object_grants_no_trial_receipt_credit",
    "stronger_proof_promotion_requires_separate_acceptance_compiler",
)
REQUIRED_FALSE = (
    "certifier_to_actor_same_task_channel",
    "same_task_replay_after_certifier_exposure",
)

@dataclass(frozen=True)
class Verdict:
    admissible: bool
    reason: str
    acceptance_credit_delta: int = 0
    execution_authority: bool = False
    promotion_authority: bool = False

def evaluate(spec: Mapping[str, Any]) -> Verdict:
    if spec.get("schema") != "PROJECT_BRAIN_TB4_POST_FREEZE_CERTIFIER_SPEC_V1":
        return Verdict(False, "SCHEMA_INVALID")
    task = spec.get("task")
    if not isinstance(task, str) or not task:
        return Verdict(False, "TASK_IDENTITY_MISSING")
    actor = spec.get("actor_config_sha256")
    output = spec.get("output_sha256")
    certifier = spec.get("certifier_identity")
    if not isinstance(actor, str) or not HEX64.fullmatch(actor):
        return Verdict(False, "ACTOR_CONFIG_HASH_INVALID")
    if not isinstance(output, str) or not HEX64.fullmatch(output):
        return Verdict(False, "OUTPUT_HASH_INVALID")
    if not isinstance(certifier, str) or not certifier:
        return Verdict(False, "CERTIFIER_IDENTITY_MISSING")

    gate = spec.get("gate")
    if not isinstance(gate, Mapping):
        return Verdict(False, "GATE_MISSING")
    for key in REQUIRED_TRUE:
        if gate.get(key) is not True:
            return Verdict(False, "REQUIRED_TRUE_MISSING:" + key)
    for key in REQUIRED_FALSE:
        if gate.get(key) is not False:
            return Verdict(False, "REQUIRED_FALSE_VIOLATED:" + key)

    order = spec.get("temporal_order")
    if order != [
        "ACTOR_EXECUTION",
        "OUTPUT_HASH_COMMIT",
        "ACTOR_WRITE_CLOSE",
        "CERTIFIER_EVALUATOR_EXPOSURE",
        "PROOF_OBJECT_EMISSION",
    ]:
        return Verdict(False, "TEMPORAL_ORDER_INVALID")

    channels = spec.get("channels")
    if channels != {
        "evaluator_to_actor": False,
        "certifier_to_actor_same_task": False,
        "certifier_to_frozen_output": False,
        "proof_to_actor_same_task": False,
    }:
        return Verdict(False, "CHANNEL_FIREWALL_INVALID")

    return Verdict(True, "POST_FREEZE_CERTIFIER_NONINTERFERENCE_PASS")

if __name__ == "__main__":
    import json, sys
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        doc = json.load(f)
    print(json.dumps(asdict(evaluate(doc)), sort_keys=True))
