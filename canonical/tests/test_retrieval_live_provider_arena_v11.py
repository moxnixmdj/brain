from canonical.runtime import retrieval_live_provider_arena_v11 as a

def fake_factory(mapping):
    def provider(query,*,limit=20,timeout=20.0,fetch=None):
        return list(mapping.get(query,[]))[:limit]
    return provider

a.validate_tasks()
assert len(a.TASKS)==30
assert len({x["provider"] for x in a.TASKS})==8
assert len({x["difficulty"] for x in a.TASKS})>=4
assert any(x["difficulty"]=="MULTILINGUAL" for x in a.TASKS)
assert any(x["provider"]=="maven" for x in a.TASKS)
assert any(x["provider"]=="nuget" for x in a.TASKS)
assert any(x["provider"]=="rubygems" for x in a.TASKS)
assert any(x["provider"]=="packagist" for x in a.TASKS)

# Deterministic mock run: hit every odd-indexed task and miss every even-indexed task.
orig=dict(a.PROVIDERS)
try:
    by_provider={}
    for i,row in enumerate(a.TASKS):
        by_provider.setdefault(row["provider"],{})[row["query"]]=[row["target"]] if i%2==0 else ["wrong/example"]
    for provider,mapping in by_provider.items():
        a.PROVIDERS[provider]=fake_factory(mapping)
    out=a.run(limit=20,timeout=1)
finally:
    a.PROVIDERS.clear();a.PROVIDERS.update(orig)

assert out["task_count"]==30
assert out["successful_task_count"]==30
assert out["target_hit_count"]==15
assert out["target_miss_count"]==15
assert out["target_recall_on_successful_tasks"]==0.5
assert out["answer_key_identity_used_for_query_generation"] is False
assert out["open_world_completeness_claim"] is False
assert len(out["difficulty_metrics"])>=4
assert len(out["provider_metrics"])==8
assert out["execution_authority"] is False
assert out["promotion_authority"] is False

# Provider parsers.
def fake_maven(url,timeout=0,headers=None):
    return {"response":{"docs":[{"id":"com.google.guava:guava"},{"id":"x:y"}]}}
assert a.maven("collections",fetch=fake_maven)[0]=="com.google.guava:guava"

def fake_nuget(url,timeout=0,headers=None):
    return {"data":[{"id":"Newtonsoft.Json"},{"id":"Serilog"}]}
assert a.nuget("json",fetch=fake_nuget)[0]=="Newtonsoft.Json"

def fake_ruby(url,timeout=0,headers=None):
    return [{"name":"nokogiri"},{"name":"faraday"}]
assert a.rubygems("xml",fetch=fake_ruby)[0]=="nokogiri"

def fake_pack(url,timeout=0,headers=None):
    return {"results":[{"name":"guzzlehttp/guzzle"},{"name":"monolog/monolog"}]}
assert a.packagist("http",fetch=fake_pack)[0]=="guzzlehttp/guzzle"

print("test_retrieval_live_provider_arena_v11: PASS")
