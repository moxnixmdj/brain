from canonical.runtime import retrieval_progressive_query_relaxation_v1 as r

def test_regex_alias_and_progressive_relaxation():
    out=r.generate({"query":"fast recursive regular expression text search command line Rust"},provider="github")
    joined="\n".join(out["queries"]).casefold()
    assert "regex" in joined
    assert "cli" in joined or "terminal" in joined
    assert any("rust" in q.casefold() for q in out["queries"])
    assert all("in:name,description,readme" in q for q in out["queries"])

def test_multilingual_bridge_variants_are_used():
    out=r.generate({
        "query":"أدوات معالجة اللغة العربية صرف لهجات Python",
        "language_variants":[{"language":"en","text":"Arabic natural language processing morphology dialect toolkit Python"}],
    },provider="github")
    joined="\n".join(out["queries"]).casefold()
    assert "nlp" in joined
    assert "morphological" in joined or "morphology" in joined

def test_background_job_aliases():
    out=r.generate({"query":"Ruby background job processing Redis workers queues"},provider="rubygems")
    joined="\n".join(out["queries"]).casefold()
    assert "job queue" in joined
    assert "background jobs" in joined

def test_answer_key_field_rejected():
    try:
        r.generate({"query":"x","target":"secret"},provider="github")
        raise AssertionError("target accepted")
    except ValueError as e:
        assert "ANSWER_KEY_FIELD_FORBIDDEN" in str(e)

if __name__=="__main__":
    test_regex_alias_and_progressive_relaxation()
    test_multilingual_bridge_variants_are_used()
    test_background_job_aliases()
    test_answer_key_field_rejected()
    print("test_retrieval_progressive_query_relaxation_v1: PASS")
