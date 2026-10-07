from canonical.runtime.professional_source_authority_coverage_gate_v1 import verify

def _base():
    return {
      "sources":[
        {"source_id":"prompt","required":True,"parsed":True,"content_sha256":"p","parser_receipt":"rp","authority_rank":0},
        {"source_id":"assumptions","required":True,"parsed":True,"content_sha256":"a","parser_receipt":"ra","authority_rank":1},
      ],
      "required_dimension_ids":["scenario","fx"],
      "dimensions":[
        {"dimension_id":"scenario","source_ids":["prompt"],"coverage_receipt":"c1"},
        {"dimension_id":"fx","source_ids":["assumptions"],"coverage_receipt":"c2"},
      ],
      "required_convention_ids":["currency"],
      "conventions":[{"convention_id":"currency","source_id":"assumptions","binding_receipt":"b1"}],
    }

def test_complete_declared_cover_passes():
    x=verify(_base()); assert x["pass"] is True,x
    assert x["semantic_completeness_self_certified"] is False
    assert x["authority_discovery_self_certified"] is False

def test_required_unparsed_source_blocks():
    x=_base(); x["sources"][1]["parsed"]=False
    y=verify(x); assert y["pass"] is False
    assert "REQUIRED_SOURCE_NOT_PARSED:assumptions" in y["errors"]

def test_missing_dimension_blocks():
    x=_base(); x["dimensions"]=x["dimensions"][:1]
    y=verify(x); assert y["pass"] is False
    assert "REQUIRED_DIMENSION_UNCOVERED:fx" in y["errors"]

def test_unknown_dimension_source_blocks():
    x=_base(); x["dimensions"][1]["source_ids"]=["ghost"]
    y=verify(x); assert y["pass"] is False
    assert "DIMENSION_SOURCE_UNKNOWN:fx:ghost" in y["errors"]

def test_missing_convention_blocks():
    x=_base(); x["conventions"]=[]
    y=verify(x); assert y["pass"] is False
    assert "REQUIRED_CONVENTION_UNBOUND:currency" in y["errors"]

def test_undeclared_dimensions_do_not_silently_pass():
    x=_base(); x["dimensions"].append({"dimension_id":"roster","source_ids":["prompt"],"coverage_receipt":"c3"})
    y=verify(x); assert y["pass"] is False
    assert "UNDECLARED_DIMENSION:roster" in y["errors"]
