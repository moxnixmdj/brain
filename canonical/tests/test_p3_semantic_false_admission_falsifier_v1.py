"""Adversarial tests: caller-provided proof flags cannot confer context authority."""
from __future__ import annotations

import copy
import random

from canonical.runtime.p3_real_context_v3_admission_v1 import evaluate as check_v1
from canonical.runtime.p3_real_context_v3_admission_v2 import evaluate as check_v2
from canonical.tests.test_p3_real_context_v3_admission_v1 import admitted_payload as v1_payload
from canonical.tests.test_p3_real_context_v3_admission_v2 import admitted_payload as v2_payload


def _must_not_admit(result):
    assert result["pass"] is False
    assert result["v3_admission_authorized"] is False
    assert result["top_law_eligible"] is False
    assert result["policy_adequacy_authority"] is False
    assert result["db_admission_authority"] is False
    assert result["u_subtraction_authority"] is False
    assert result["terminal_authority"] is False
    assert result["terminal_credit_delta"] == 0
    assert result["unresolved_semantic_predicates"]


def test_forged_complete_proof_flags_and_metadata_are_not_authority():
    for checker, factory in ((check_v1, v1_payload), (check_v2, v2_payload)):
        payload = factory()
        for certificate in payload["semantic_certificates"].values():
            certificate.update({
                "pass": True,
                "predicate_truth": "TRUE",
                "truthful_precommitment_observation": True,
                "source_proof": {"status": "PROOF_CHECKED"},
                "independent_verification": {"verified": True},
                "content_digest": "f" * 64,
            })
        _must_not_admit(checker(payload))


def test_200_mutated_caller_certificates_never_authorize():
    rng = random.Random(90218)
    for i in range(200):
        checker, factory = ((check_v1, v1_payload), (check_v2, v2_payload))[i % 2]
        payload = copy.deepcopy(factory())
        for certificate in payload["semantic_certificates"].values():
            certificate["pass"] = rng.choice([True, False, None, 1])
            certificate["predicate_truth"] = rng.choice(["TRUE", "FALSE", "UNKNOWN", None])
            certificate["truthful_precommitment_observation"] = rng.choice([True, False, None, 1])
            certificate["source_proof"] = {"status": rng.choice(["PROOF_CHECKED", "VALIDATED", "TRUSTED"])}
            certificate["content_digest"] = str(rng.randrange(10**9))
        _must_not_admit(checker(payload))
