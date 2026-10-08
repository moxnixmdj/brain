import json
import pathlib
import tempfile

from canonical.runtime.professional_archetype_brand_distribution_onboarding_v1 import select
from canonical.runtime.professional_questionnaire_pdf_stdlib_v1 import render


PROMPT = """You are a Sales Manager for a distribution company. Create a 3-page text-based PDF document titled "Brand Data Gathering." The document should collect operational and sales information from potential or new brand partners and support onboarding and brand readiness."""


def test_selector_is_narrow_and_model_independent():
    out = select(PROMPT, [])
    assert out["status"] == "SELECTED"
    assert out["model_dependency_count"] == 0
    assert out["spec"]["generation_boundary"].endswith("NO_BENCHMARK_RUBRIC_OR_GOLD_DELIVERABLE_INPUT")


def test_selector_rejects_unrelated_document():
    out = select("Create a three-page PDF about astronomy.", [])
    assert out["status"] == "UNSUPPORTED"


def test_selector_rejects_reference_files():
    out = select(PROMPT, ["secret.xlsx"])
    assert out["status"] == "UNSUPPORTED"


def test_render_exact_three_pages():
    out = select(PROMPT, [])
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td) / "Brand Data Gathering.pdf"
        result = render(out["spec"], p)
        raw = p.read_bytes()
        assert result["page_count"] == 3
        assert result["question_count"] >= 35
        assert raw.startswith(b"%PDF-1.4")
        assert raw.count(b"/Type /Page ") == 3
        assert b"Brand Data Gathering" in raw
