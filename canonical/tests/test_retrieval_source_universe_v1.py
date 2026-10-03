from pathlib import Path
from canonical.runtime import retrieval_source_universe_v1 as su
from canonical.runtime import global_retrieval_entrypoint_v3 as e

ROOT=Path(__file__).resolve().parents[2]
reg=su.load_registry(ROOT)
assert len(reg["sources"])==9
ids={x["source_id"] for x in reg["sources"]}
assert {
    "PYPI_PUBLIC_PROJECTS","HUGGING_FACE_PUBLIC_HUB","GITLAB_PUBLIC_PROJECTS",
    "CROSSREF_WORKS","COMMON_CRAWL_CDX_SNAPSHOT",
    "GITHUB_SCOPED_REPOSITORY_LIST","GITHUB_GLOBAL_SEARCH",
    "NPM_PUBLIC_REGISTRY","GENERAL_OPEN_WEB",
}==ids

bound=su.bind_sources(reg,epoch="2026-10-03T21:00Z")
by={x["source_id"]:x for x in bound["sources"]}
assert by["PYPI_PUBLIC_PROJECTS"]["authoritative_enumeration"] is True
assert by["PYPI_PUBLIC_PROJECTS"]["queryless_default_enabled"] is True
assert by["HUGGING_FACE_PUBLIC_HUB"]["queryless_default_enabled"] is True
assert by["GITLAB_PUBLIC_PROJECTS"]["scope_id"]=="GITLAB_PUBLIC_PROJECTS:gitlab.com@2026-10-03T21:00Z"
assert by["CROSSREF_WORKS"]["queryless_default_enabled"] is False
assert "COMMON_CRAWL_CDX_SNAPSHOT" not in by
assert any(x["source_id"]=="COMMON_CRAWL_CDX_SNAPSHOT" and x["reason"]=="MISSING_RUNTIME_SCOPE_BINDING" for x in bound["skipped_sources"])
assert any(x["source_id"]=="GITHUB_SCOPED_REPOSITORY_LIST" and x["reason"]=="MISSING_RUNTIME_SCOPE_BINDING" for x in bound["skipped_sources"])

cc=su.bind_sources(
    reg,epoch="E0",
    include_source_ids=["COMMON_CRAWL_CDX_SNAPSHOT"],
    runtime_bindings={"COMMON_CRAWL_CDX_SNAPSHOT":{"crawl_id":"CC-MAIN-2026-39"}},
)
assert cc["sources"][0]["scope_id"]=="COMMON_CRAWL:CC-MAIN-2026-39"
assert cc["sources"][0]["queryless_default_enabled"] is False

ctrl=su.controller_sources(bound)
cb={x["source_id"]:x for x in ctrl}
assert cb["CROSSREF_WORKS"]["authoritative_enumeration"] is False
assert "COMMON_CRAWL_CDX_SNAPSHOT" not in cb
ccctrl=su.controller_sources(cc)
assert ccctrl[0]["source_id"]=="COMMON_CRAWL_CDX_SNAPSHOT"
assert ccctrl[0]["authoritative_enumeration"] is False

scoped=su.bind_sources(
    reg,epoch="E1",
    include_source_ids=["GITHUB_SCOPED_REPOSITORY_LIST"],
    runtime_bindings={"GITHUB_SCOPED_REPOSITORY_LIST":{"scope_kind":"org","scope_value":"openai"}},
)
assert scoped["sources"][0]["scope_id"]=="GITHUB_SCOPE:org:openai@E1"

out=e.compile_authorized_plan(
    root=ROOT,
    query_actions=[{"action_id":"web-q1","source_id":"GENERAL_OPEN_WEB"}],
    source_epoch="E2",
)
assert out["status"]=="PASS__AUTHORIZED_CANONICAL_SOURCE_EMPIRICAL_GLOBAL_RETRIEVAL_PLAN_COMPILED",out
assert out["authority_gate"]["pass"] is True
assert out["plan"]["queryless_enumeration_action_count"]==3
assert out["bound_source_universe"]["nonexistence_claim_authorized"] is False
assert out["plan"]["open_world_nonexistence_claim_authorized"] is False

bad=e.compile_authorized_plan(
    root=ROOT,
    query_actions=[{"action_id":"bad","source_id":"INVENTED_MAGIC_SEARCH"}],
    source_epoch="E3",
)
assert bad["status"]=="FAIL_CLOSED__QUERY_ACTION_REFERENCES_SOURCE_OUTSIDE_CANONICAL_UNIVERSE"
assert bad["unknown_source_ids"]==["INVENTED_MAGIC_SEARCH"]

print("test_retrieval_source_universe_v1: PASS")
