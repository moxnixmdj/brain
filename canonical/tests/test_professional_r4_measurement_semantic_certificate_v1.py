from canonical.runtime import professional_r4_measurement_semantic_certificate_v1 as s

SAMPLES=[
 {"id":"a","kind":"FILE_BASENAME"},
 {"id":"b","kind":"FILE_SUFFIX"},
 {"id":"c","kind":"FILE_SIZE_BYTES"},
 {"id":"d","kind":"OOXML_MEMBER_EXISTS","member":"word/document.xml"},
 {"id":"e","kind":"XLSX_SHEET_EXISTS","sheet_name":"Data"},
 {"id":"f","kind":"XLSX_SHEET_COUNT"},
 {"id":"g","kind":"DOCX_TEXT_CONTAINS","text":"Revenue"},
 {"id":"h","kind":"DOCX_PARAGRAPH_COUNT"},
 {"id":"i","kind":"DOCX_TABLE_COUNT"},
 {"id":"j","kind":"PPTX_SLIDE_COUNT"},
 {"id":"k","kind":"PPTX_TEXT_CONTAINS","text":"Summary","case_sensitive":False},
]

def test_all_supported_kinds_have_bounded_semantics():
    assert len(SAMPLES)==11
    assert {x["kind"] for x in SAMPLES}==set(s.supported_kinds())
    for req in SAMPLES:
        out=s.certify(req)
        assert out["pass"] is True, out
        assert out["bounded_semantic_evidence"] is True
        assert out["global_r4_semantic_leaf_closed"] is False
        assert out["task_contract_alignment_authority"] is False
        assert out["source_measurement_runtime_git_blob_sha"]==s.SOURCE_BLOB
        assert len(out["semantic_signature_sha256"])==64

def test_unknown_fields_fail_closed():
    out=s.certify({"id":"x","kind":"FILE_SIZE_BYTES","unit":"kb"})
    assert out["pass"] is False
    assert out["reason"]=="UNMODELED_FIELDS"

def test_invalid_ooxml_member_fails_closed():
    out=s.certify({"id":"x","kind":"OOXML_MEMBER_EXISTS","member":"../secret"})
    assert out["pass"] is False
    assert out["reason"]=="OOXML_MEMBER_INVALID"

def test_literal_is_content_addressed_and_changes_signature():
    a=s.certify({"id":"x","kind":"DOCX_TEXT_CONTAINS","text":"Alpha"})
    b=s.certify({"id":"x","kind":"DOCX_TEXT_CONTAINS","text":"Beta"})
    assert a["pass"] and b["pass"]
    assert a["parameters"]["text_sha256"] != b["parameters"]["text_sha256"]
    assert a["semantic_signature_sha256"] != b["semantic_signature_sha256"]

def test_case_insensitive_xlsx_semantics_are_explicit():
    exact=s.certify({"id":"x","kind":"XLSX_SHEET_EXISTS","sheet_name":"Data"})
    folded=s.certify({"id":"x","kind":"XLSX_SHEET_EXISTS","sheet_name":"Data","case_sensitive":False})
    assert exact["parameters"]["comparison_mode"]=="EXACT"
    assert folded["parameters"]["comparison_mode"]=="STRIP_CASEFOLD_EQUALITY"
    assert exact["semantic_signature_sha256"] != folded["semantic_signature_sha256"]

def test_missing_literal_and_bad_case_flag_fail_closed():
    assert s.certify({"id":"x","kind":"PPTX_TEXT_CONTAINS"})["pass"] is False
    assert s.certify({"id":"x","kind":"PPTX_TEXT_CONTAINS","text":"x","case_sensitive":"no"})["pass"] is False
