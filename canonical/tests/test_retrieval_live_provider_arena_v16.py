from canonical.runtime import retrieval_live_provider_arena_v16 as v16

def test_behavior_concepts_are_generic():
    c=v16.behavior_concepts("Java collections caching primitives utilities")
    assert "collection" in c
    assert "cach" in c
    assert "primitive" in c
    assert "java" not in c

def test_graph_links_rank_by_local_behavior_context():
    md="""
    [Unrelated](https://github.com/acme/unrelated) generic web framework.
    [CacheKit](https://github.com/example/cachekit) Collections, caching,
    primitives support, concurrency utilities and common helpers.
    [Other](https://github.com/example/other) logging facade.
    """
    rows=v16.behavior_link_candidates(
        md,"Java collections caching primitives utilities",max_links=10
    )
    assert rows
    assert rows[0]["repository"]=="example/cachekit"
    assert len(rows[0]["matched_behavior_concepts"])>=3

def test_graph_link_extraction_is_target_parameter_free():
    # The graph function takes only candidate text + behavior query. There is no
    # expected-target argument available to leak into ranking.
    import inspect
    sig=str(inspect.signature(v16.behavior_link_candidates))
    assert "target" not in sig

def test_validate_answer_key_blind_seed_queries():
    v16.validate()

def test_snowball_dedupes_and_ranks():
    old=v16.repository_readme
    docs={
        "seed/a":"[A](https://github.com/example/a) collections caching primitives utilities",
        "seed/b":"[A2](https://github.com/example/a) collections cache\n[B](https://github.com/example/b) primitives",
    }
    v16.repository_readme=lambda repo,timeout=1:docs.get(repo,"")
    try:
        repos,traces=v16.graph_snowball(
            "Java collections caching primitives utilities",
            ["seed/a","seed/b"],timeout=1,max_seed_repos=2,max_links_per_seed=10
        )
    finally:
        v16.repository_readme=old
    assert repos.count("example/a")==1
    assert "example/b" in repos
    assert repos[0]=="example/a"

if __name__=="__main__":
    test_behavior_concepts_are_generic()
    test_graph_links_rank_by_local_behavior_context()
    test_graph_link_extraction_is_target_parameter_free()
    test_validate_answer_key_blind_seed_queries()
    test_snowball_dedupes_and_ranks()
    print("test_retrieval_live_provider_arena_v16: PASS")
