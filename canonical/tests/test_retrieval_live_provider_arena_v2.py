from canonical.runtime import retrieval_live_provider_arena_v2 as a

a.validate_tasks()

def fake(url,timeout=0,headers=None):
    if "huggingface.co" in url:
        return [{"id":"sentence-transformers/all-MiniLM-L6-v2"},{"id":"x/y"}]
    if "crossref.org" in url:
        return {"message":{"items":[{"DOI":"10.18653/v1/N19-1423"},{"DOI":"10.x/y"}]}}
    raise AssertionError(url)

assert a.huggingface_pipeline("sentence-similarity",fetch=fake)[0]=="sentence-transformers/all-MiniLM-L6-v2"
assert a.crossref_title("transformer",fetch=fake)[0]=="10.18653/v1/n19-1423"

for row in a.TASKS:
    assert row["target"].casefold() not in row["query"].casefold()
    assert row["strategy_id"]

print("test_retrieval_live_provider_arena_v2: PASS")
