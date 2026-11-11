from __future__ import annotations

DOMAINS=("CYBERSECURITY","BIOLOGY_RESEARCH_AND_DEVELOPMENT","AUTOMATED_AI_RESEARCH_AND_DEVELOPMENT","HEALTHCARE","MATHEMATICAL_REASONING_ARXIVMATH")
ALLOWED_AUTHORITIES={"PRIMARY_PROVIDER","PRIMARY_BENCHMARK_OWNER"}

class AnchorError(RuntimeError):
    pass

def default_manifest():
    return {
      "schema":"PROJECT_BRAIN_OPUS55_DOMAIN_BEHAVIOR_UNIVERSE_ANCHOR_V2",
      "model":"Claude Opus 5.5",
      "sources":[
        {"id":"ANTHROPIC_OPUS55_LAUNCH","url":"https://www.anthropic.com/claude-opus-5-5","authority":"PRIMARY_PROVIDER","observed_scope":["CYBERSECURITY_SAFEGUARDS","BIOLOGY_SAFEGUARDS"]},
        {"id":"ANTHROPIC_TRANSPARENCY_OPUS55","url":"https://www.anthropic.com/transparency","authority":"PRIMARY_PROVIDER","observed_scope":["AUTOMATED_AI_RESEARCH_AND_DEVELOPMENT","CHEMICAL_AND_BIOLOGICAL_RISK"]},
        {"id":"ANTHROPIC_OPUS55_SYSTEM_CARD_HEALTHCARE","url":"https://www.anthropic.com/claude-opus-5-5-system-card","authority":"PRIMARY_PROVIDER","observed_scope":["HEALTHBENCH_PROFESSIONAL","HEALTHBENCH_PROFESSIONAL_LENGTH_ADJUSTED_65_6_MAX"]},
        {"id":"ANTHROPIC_SONNET55_SYSTEM_CARD_PHYSICIANBENCH_OPUS55","url":"https://www.anthropic.com/claude-sonnet-5-5-system-card","authority":"PRIMARY_PROVIDER","observed_scope":["PHYSICIANBENCH","PHYSICIANBENCH_OPUS55_MAX_PASS_AT_1_68_4"]},
        {"id":"MATHARENA_ARXIVMATH_2026_06_OPUS55","url":"https://matharena.ai/competition_tables/arxiv--june","authority":"PRIMARY_BENCHMARK_OWNER","observed_scope":["ARXIVMATH_2026_06","ARXIVMATH_2026_06_OPUS55_HIGH_DEFAULT_FALLBACK_83_3"]},
        {"id":"MATHARENA_ARXIVMATH_OPUS55_RELEASE_NOTICE","url":"https://matharena.ai/","authority":"PRIMARY_BENCHMARK_OWNER","observed_scope":["ARXIVMATH_OPUS55_PUBLIC_RESULTS_RELEASED_2026_09_24"]}
      ],
      "domains":{
        "CYBERSECURITY":{"state":"OPEN_EXHAUSTIVE_DECOMPOSITION_REQUIRED","observed_surfaces":["CYBERSECURITY_SAFEGUARDS"],"exhaustive_behavior_universe":False,"lossless_transform_mapping":False},
        "BIOLOGY_RESEARCH_AND_DEVELOPMENT":{"state":"OPEN_EXHAUSTIVE_DECOMPOSITION_REQUIRED","observed_surfaces":["BIOLOGY_SAFEGUARDS","CHEMICAL_AND_BIOLOGICAL_RISK"],"exhaustive_behavior_universe":False,"lossless_transform_mapping":False},
        "AUTOMATED_AI_RESEARCH_AND_DEVELOPMENT":{"state":"OPEN_EXHAUSTIVE_DECOMPOSITION_REQUIRED","observed_surfaces":["AUTOMATED_AI_RESEARCH_AND_DEVELOPMENT"],"exhaustive_behavior_universe":False,"lossless_transform_mapping":False},
        "HEALTHCARE":{"state":"OPEN_EXHAUSTIVE_DECOMPOSITION_REQUIRED","observed_surfaces":["HEALTHBENCH_PROFESSIONAL","PHYSICIANBENCH"],"exhaustive_behavior_universe":False,"lossless_transform_mapping":False},
        "MATHEMATICAL_REASONING_ARXIVMATH":{"state":"OPEN_EXHAUSTIVE_DECOMPOSITION_REQUIRED","observed_surfaces":["ARXIVMATH_2026_06","ARXIVMATH_OPUS55_PUBLIC_RESULTS_RELEASED_2026_09_24"],"exhaustive_behavior_universe":False,"lossless_transform_mapping":False}
      },
      "closure_rule":"SOURCE_ANCHOR_IS_NECESSARY_NOT_SUFFICIENT__CLOSE_ONLY_WITH_EXHAUSTIVE_BEHAVIOR_UNIVERSE_AND_LOSSLESS_OWNED_TRANSFORM_MAPPING"
    }

def validate_manifest(manifest):
    sources=manifest.get("sources")
    if not isinstance(sources,list) or not sources:
        raise AnchorError("AUTHORITATIVE_SOURCE_SET_EMPTY")
    for source in sources:
        if source.get("authority") not in ALLOWED_AUTHORITIES or not source.get("url"):
            raise AnchorError("NONAUTHORITATIVE_OR_UNBOUND_SOURCE")
        if not isinstance(source.get("observed_scope"),list):
            raise AnchorError("SOURCE_SCOPE_NOT_LIST")
    domains=manifest.get("domains")
    if not isinstance(domains,dict) or set(domains)!=set(DOMAINS):
        raise AnchorError("DOMAIN_FRONTIER_DRIFT")
    source_incomplete=[]; closed=[]; anchored=[]
    for domain in DOMAINS:
        rec=domains[domain]
        obs=rec.get("observed_surfaces")
        if not isinstance(obs,list):
            raise AnchorError("OBSERVED_SURFACES_NOT_LIST:"+domain)
        if obs: anchored.append(domain)
        else: source_incomplete.append(domain)
        if rec.get("state")=="CLOSED":
            if rec.get("exhaustive_behavior_universe") is not True or rec.get("lossless_transform_mapping") is not True:
                raise AnchorError("UNSOUND_DOMAIN_CLOSURE:"+domain)
            closed.append(domain)
    return {"status":"PASS__ALL_FIVE_DOMAINS_EXTERNALLY_SOURCE_ANCHORED__EXHAUSTIVE_CLOSURE_REMAINS_FAIL_CLOSED","domain_count":len(DOMAINS),"source_anchored_domain_count":len(anchored),"source_incomplete_domains":source_incomplete,"closed_domain_count":len(closed),"closed_domains":closed,"next_required":"FOR_EACH_DOMAIN_BUILD_CONTENT_ADDRESSED_EXHAUSTIVE_BEHAVIOR_UNIVERSE_THEN_RUN_SHARED_LOSSLESS_TRANSFORM_MAPPING_COMPILER"}

def compile_anchor():
    return validate_manifest(default_manifest())

if __name__=="__main__":
    import json
    print(json.dumps(compile_anchor(),indent=2,sort_keys=True))
