from canonical.runtime.specification_consensus_gate import assess_consensus, source_sentences

SOURCE="The service must retain records for 30 days. Logging is informational. If deletion is requested, the service must delete the record within 24 hours."

def good_outputs():
    a=[
      {"source_sentence_id":"S1","source_quote":"The service must retain records for 30 days.","class":"requirement","requirement_id":"R1","actor":"service","action":"retain","object":"records","constraints":["30 days"]},
      {"source_sentence_id":"S2","source_quote":"Logging is informational.","class":"non_requirement"},
      {"source_sentence_id":"S3","source_quote":"If deletion is requested, the service must delete the record within 24 hours.","class":"requirement","requirement_id":"R2","actor":"service","action":"delete","object":"record","condition":"deletion is requested","constraints":["within 24 hours"]},
    ]
    b=[dict(x) for x in a]
    return [{"extractor_id":"A","sentences":a},{"extractor_id":"B","sentences":b}]

def test_two_independent_matching_extractors_pass():
    out=assess_consensus(SOURCE,good_outputs())
    assert out["pass"] is True
    assert len(out["accepted_requirements"])==2

def test_missing_sentence_fails_closed():
    x=good_outputs(); x[1]["sentences"]=x[1]["sentences"][:-1]
    out=assess_consensus(SOURCE,x)
    assert out["pass"] is False
    assert any("UNCLASSIFIED_SOURCE_SENTENCE" in f for f in out["failures"])

def test_requirement_class_disagreement_fails_closed():
    x=good_outputs(); x[1]["sentences"][0]["class"]="non_requirement"
    out=assess_consensus(SOURCE,x)
    assert out["pass"] is False
    assert "CLASS_DISAGREEMENT:S1" in out["failures"]

def test_semantic_disagreement_fails_closed():
    x=good_outputs(); x[1]["sentences"][2]["constraints"]=["within 48 hours"]
    out=assess_consensus(SOURCE,x)
    assert out["pass"] is False
    assert "SEMANTIC_SIGNATURE_DISAGREEMENT:S3" in out["failures"]

def test_bad_source_quote_fails_closed():
    x=good_outputs(); x[1]["sentences"][0]["source_quote"]="similar but not exact"
    assert assess_consensus(SOURCE,x)["pass"] is False

def test_one_extractor_is_insufficient():
    x=good_outputs()[:1]
    out=assess_consensus(SOURCE,x)
    assert out["pass"] is False
    assert "FEWER_THAN_TWO_INDEPENDENT_EXTRACTORS" in out["failures"]


def test_source_segmentation_preserves_decimals_dotted_code_and_fenced_schema():
    src = """Material index is 2.85. Use `mp.ODD_Z`, not `mp.EVEN_Z`. Write `design.npy`.

Schema:

```
{"fdtd_resolution": 20}
```

The minimum diameter is 0.12 um, i.e. preserve the feature."""
    units = source_sentences(src)
    texts = [x["text"] for x in units]
    assert any("2.85" in x for x in texts)
    assert any("mp.ODD_Z" in x and "mp.EVEN_Z" in x for x in texts)
    assert any("design.npy" in x for x in texts)
    assert any('"fdtd_resolution": 20' in x for x in texts)
    assert any("0.12 um, i.e. preserve the feature." in x for x in texts)
    assert not any(x in {"85", "ODD_Z", "npy"} for x in texts)
