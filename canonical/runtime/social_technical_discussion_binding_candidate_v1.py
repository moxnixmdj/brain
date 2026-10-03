#!/usr/bin/env python3
"""Zero-credit binding candidate for the social technical discussion provider.

Uses the existing verified router's external-provider contract. Importing this
module does not mutate global routing; callers must invoke bind().
"""
from __future__ import annotations
from typing import Any

from canonical.runtime import residual_witness_backend_router_v1 as router
from canonical.runtime import social_technical_discussion_provider_v1 as social

SCHEMA="PROJECT_BRAIN_SOCIAL_TECHNICAL_DISCUSSION_BINDING_CANDIDATE_V1"

def bind()->dict[str,Any]:
    router.set_external_provider(
        "SOCIAL_TECHNICAL_DISCUSSION",
        lambda action: social.search(action),
    )
    return {
        "schema":SCHEMA,
        "status":"BOUND_CANDIDATE_ONLY__ZERO_CREDIT",
        "surface":"SOCIAL_TECHNICAL_DISCUSSION",
        "provider":"HN_ALGOLIA_PUBLIC_SEARCH_V1",
        "material_source_epoch":"HN_ALGOLIA_PUBLIC_SEARCH_V1",
        "candidate_only":True,
        "complete":False,
        "independently_complete":False,
        "no_result_means_nonexistence":False,
        "acceptance_credit":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
    }
