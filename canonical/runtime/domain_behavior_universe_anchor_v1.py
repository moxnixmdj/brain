from __future__ import annotations

from copy import deepcopy

DOMAINS = (
    "CYBERSECURITY",
    "BIOLOGY_RESEARCH_AND_DEVELOPMENT",
    "AUTOMATED_AI_RESEARCH_AND_DEVELOPMENT",
    "HEALTHCARE",
    "MATHEMATICAL_REASONING_ARXIVMATH",
)

class AnchorError(RuntimeError):
    pass

def default_manifest():
    return {
        "schema": "PROJECT_BRAIN_OPUS55_DOMAIN_BEHAVIOR_UNIVERSE_ANCHOR_V1",
        "model": "Claude Opus 5.5",
        "sources": [
            {
                "id": "ANTHROPIC_OPUS55_LAUNCH",
                "url": "https://www.anthropic.com/claude-opus-5-5",
                "authority": "PRIMARY_PROVIDER",
                "observed_scope": [
                    "CODING",
                    "AGENTS",
                    "KNOWLEDGE_WORK",
                    "FINANCIAL_ANALYSIS",
                    "VISION_AND_COMPUTER_USE",
                    "CYBERSECURITY_SAFEGUARDS",
                    "BIOLOGY_SAFEGUARDS",
                ],
            },
            {
                "id": "ANTHROPIC_TRANSPARENCY_OPUS55",
                "url": "https://www.anthropic.com/transparency",
                "authority": "PRIMARY_PROVIDER",
                "observed_scope": [
                    "AUTOMATED_AI_RESEARCH_AND_DEVELOPMENT",
                    "CHEMICAL_AND_BIOLOGICAL_RISK",
                    "MODALITIES",
                    "ALIGNMENT",
                ],
            },
            {
                "id": "ANTHROPIC_OPUS55_SYSTEM_CARD_INDEX",
                "url": "https://www.anthropic.com/system-cards",
                "authority": "PRIMARY_PROVIDER",
                "observed_scope": ["OPUS55_SYSTEM_CARD_EXISTS", "BENCHMARKED_CAPABILITIES_SECTION_8"],
            },
        ],
        "domains": {
            "CYBERSECURITY": {
                "state": "OPEN_SOURCE_DECOMPOSITION_REQUIRED",
                "observed_surfaces": ["CYBERSECURITY_SAFEGUARDS"],
                "exhaustive_behavior_universe": False,
                "lossless_transform_mapping": False,
            },
            "BIOLOGY_RESEARCH_AND_DEVELOPMENT": {
                "state": "OPEN_SOURCE_DECOMPOSITION_REQUIRED",
                "observed_surfaces": ["BIOLOGY_SAFEGUARDS", "CHEMICAL_AND_BIOLOGICAL_RISK"],
                "exhaustive_behavior_universe": False,
                "lossless_transform_mapping": False,
            },
            "AUTOMATED_AI_RESEARCH_AND_DEVELOPMENT": {
                "state": "OPEN_SOURCE_DECOMPOSITION_REQUIRED",
                "observed_surfaces": ["AUTOMATED_AI_RESEARCH_AND_DEVELOPMENT"],
                "exhaustive_behavior_universe": False,
                "lossless_transform_mapping": False,
            },
            "HEALTHCARE": {
                "state": "OPEN_SOURCE_DECOMPOSITION_REQUIRED",
                "observed_surfaces": [],
                "exhaustive_behavior_universe": False,
                "lossless_transform_mapping": False,
            },
            "MATHEMATICAL_REASONING_ARXIVMATH": {
                "state": "OPEN_SOURCE_DECOMPOSITION_REQUIRED",
                "observed_surfaces": [],
                "exhaustive_behavior_universe": False,
                "lossless_transform_mapping": False,
            },
        },
        "closure_rule": (
            "A_DOMAIN_MAY_CLOSE_ONLY_IF_ITS_LOAD_BEARING_OPUS55_BEHAVIOR_UNIVERSE_IS_"
            "CONTENT_ADDRESSED_AND_EXHAUSTIVE_AND_EVERY_LEAF_HAS_A_LOSSLESS_MAPPING_TO_"
            "EXISTING_OWNED_TRANSFORMS_OR_A_CONSTRUCTIVE_COUNTEREXAMPLE_IS_RECLASSIFIED"
        ),
    }

def validate_manifest(manifest):
    sources = manifest.get("sources")
    if not isinstance(sources, list) or not sources:
        raise AnchorError("AUTHORITATIVE_SOURCE_SET_EMPTY")
    for source in sources:
        if source.get("authority") != "PRIMARY_PROVIDER" or not source.get("url"):
            raise AnchorError("NONAUTHORITATIVE_OR_UNBOUND_SOURCE")

    domains = manifest.get("domains")
    if not isinstance(domains, dict) or set(domains) != set(DOMAINS):
        raise AnchorError("DOMAIN_FRONTIER_DRIFT")

    source_incomplete = []
    closed = []
    for domain in DOMAINS:
        record = domains[domain]
        exhaustive = record.get("exhaustive_behavior_universe") is True
        mapped = record.get("lossless_transform_mapping") is True
        state = record.get("state")
        observed = record.get("observed_surfaces")
        if not isinstance(observed, list):
            raise AnchorError("OBSERVED_SURFACES_NOT_LIST:" + domain)
        if not observed:
            source_incomplete.append(domain)
        if state == "CLOSED":
            if not exhaustive or not mapped:
                raise AnchorError("UNSOUND_DOMAIN_CLOSURE:" + domain)
            closed.append(domain)

    return {
        "status": "PASS__AUTHORITATIVE_SOURCE_ANCHOR_BOUND__ALL_DOMAIN_CLOSURE_REMAINS_FAIL_CLOSED",
        "domain_count": len(DOMAINS),
        "closed_domain_count": len(closed),
        "source_incomplete_domains": source_incomplete,
        "closed_domains": closed,
        "next_required": (
            "CONTENT_ADDRESS_THE_LOAD_BEARING_BEHAVIOR_UNIVERSE_PER_DOMAIN_FROM_PRIMARY_"
            "OPUS55_EVIDENCE_THEN_RUN_THE_SHARED_TRANSFORM_MAPPING_COMPILER"
        ),
    }

def compile_anchor():
    return validate_manifest(default_manifest())

if __name__ == "__main__":
    import json
    print(json.dumps(compile_anchor(), indent=2, sort_keys=True))
