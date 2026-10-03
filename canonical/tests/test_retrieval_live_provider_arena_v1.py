from canonical.runtime import retrieval_live_provider_arena_v1 as a

a.validate_tasks()

def fake(url,timeout=0,headers=None):
    if "github.com" in url:
        return {"items":[{"full_name":"tesseract-ocr/tesseract"},{"full_name":"x/y"}]}
    if "npmjs.org" in url:
        return {"objects":[{"package":{"name":"typescript"}},{"package":{"name":"x"}}]}
    if "crates.io" in url:
        return {"crates":[{"id":"serde"},{"id":"x"}]}
    if "huggingface.co" in url:
        return [{"id":"sentence-transformers/all-MiniLM-L6-v2"},{"id":"x/y"}]
    if "crossref.org" in url:
        return {"message":{"items":[{"DOI":"10.18653/v1/N19-1423"},{"DOI":"10.x/y"}]}}
    if "openalex.org" in url:
        return {"results":[{"doi":"https://doi.org/10.18653/v1/N19-1423"},{"doi":"https://doi.org/10.x/y"}]}
    raise AssertionError(url)

assert a.github("behavior",fetch=fake)[0]=="tesseract-ocr/tesseract"
assert a.npm("behavior",fetch=fake)[0]=="typescript"
assert a.crates("behavior",fetch=fake)[0]=="serde"
assert a.huggingface("behavior",fetch=fake)[0]=="sentence-transformers/all-MiniLM-L6-v2"
assert a.crossref("behavior",fetch=fake)[0]=="10.18653/v1/n19-1423"
assert a.openalex("behavior",fetch=fake)[0]=="10.18653/v1/n19-1423"

for row in a.TASKS:
    assert row["target"].casefold() not in row["query"].casefold()

print("test_retrieval_live_provider_arena_v1: PASS")
