from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path

from canonical.runtime import gdpval_objective_artifact_criteria_v2 as m
from canonical.runtime.gdpval_first_residual_mechanical_replay_v2 import replay


def test_v1_admissions_are_preserved():
    for criterion in [
        "Submission is a single-page PDF",
        "Provides an Excel .xlsx workbook with exactly four worksheets (tabs).",
        "The delivered file is a WAV file and not a compressed format (e.g., MP3/AAC).",
    ]:
        out = m.compile_criterion(criterion)
        assert out["status"] == "COMPILED_OBJECTIVE_CHECK", criterion
        assert out["compiler_origin"] == "V1_PRESERVED"


def test_new_generic_mechanical_forms_compile():
    cases = {
        "Deliverable is a Microsoft Word file.": ".docx",
        "Submission is provided as a Microsoft Word (.docx) document": ".docx",
        "The submitted deliverable is an Excel file.": ".xlsx",
        "The deliverable is an Excel workbook file with a .xlsx extension.": ".xlsx",
        "The deliverable is provided as a .pptx PowerPoint file.": ".pptx",
        "Final deliverable is a PDF document.": ".pdf",
        "The deliverable is provided as a PDF file.": ".pdf",
        "Final deliverable is an MP4 file (.mp4 extension)": ".mp4",
    }
    for criterion, ext in cases.items():
        out = m.compile_criterion(criterion)
        assert out["status"] == "COMPILED_OBJECTIVE_CHECK", criterion
        assert out["checks"][0]["args"]["extension"] == ext


def test_single_generic_forms_require_exactly_one_top_level_file():
    for criterion in [
        "A single PDF file is delivered.",
        "Submission is a single Word document in .docx format.",
        "The final deliverable is a single Excel workbook with file extension .xlsx.",
        "The final deliverable consists of a single file whose extension is .mp4 (case-insensitive).",
    ]:
        out = m.compile_criterion(criterion)
        assert out["status"] == "COMPILED_OBJECTIVE_CHECK", criterion
        check = out["checks"][0]
        assert check["kind"] == "EXACT_TOP_LEVEL_FILE_COUNT_BY_EXTENSION"
        assert check["args"]["count"] == 1
        assert check["args"]["total_files_must_equal_count"] is True


def test_allowed_legacy_formats_are_one_sided_not_overclaimed():
    for criterion in [
        "The deliverable is a Microsoft Word document (.docx or .doc).",
        "The submission is a Microsoft Word document file with extension .docx or .doc.",
        "Delivers a single Excel workbook file in .xlsx or .xls format",
        "The deliverable is a single PowerPoint file with extension .pptx or .ppt (not a PDF, image, link, Google Slides, or Keynote).",
    ]:
        out = m.compile_criterion(criterion)
        assert out["status"] == "COMPILED_OBJECTIVE_CHECK", criterion
        assert out["criterion_to_check_relation"] == "SOUND_SUFFICIENT_SUBSET__FALSE_NEGATIVES_ALLOWED"


def test_pure_total_file_count_is_machine_verified(tmp_path: Path):
    c = m.compile_criterion("Exactly one deliverable file is submitted.")
    assert c["status"] == "COMPILED_OBJECTIVE_CHECK"
    (tmp_path / "anything.bin").write_bytes(b"x")
    assert m.verify_compiled(c, tmp_path)["pass"] is True
    (tmp_path / "extra.txt").write_text("x", encoding="utf-8")
    assert m.verify_compiled(c, tmp_path)["pass"] is False


def test_single_zip_uses_native_validity_and_rejects_extra_file(tmp_path: Path):
    c = m.compile_criterion("All content in the deliverable is inside a single .zip archive.")
    assert c["status"] == "COMPILED_OBJECTIVE_CHECK"
    zpath = tmp_path / "bundle.zip"
    with zipfile.ZipFile(zpath, "w") as z:
        z.writestr("x.txt", "x")
    assert m.verify_compiled(c, tmp_path)["pass"] is True
    (tmp_path / "outside.txt").write_text("outside", encoding="utf-8")
    assert m.verify_compiled(c, tmp_path)["pass"] is False


def test_semantic_roles_and_mixed_content_remain_unresolved():
    rejected = [
        "Provides a PDF of IRS Form 1040 (tax year 2024) containing pages 1 and 2 for Robert (Bob) and Lisa Smith",
        "Exactly one checklist file is provided in PDF format.",
        "A memo file in PDF format ('.pdf') is submitted.",
        "Provides two separate .docx files: one escalation email and one vendor assessment report (not combined).",
        "Provides two distinct .pptx files: one presentation for Session 13 and one for Session 14.",
        "Provides a Word (.docx) document that contains the Proposed Architecture Summary",
        "Provides the scenario analysis as a single Excel workbook with .xlsx extension containing all required elements (three scenarios, computations, visual, and summary).",
        "Deliverable is a single multi-page PDF exported from a presentation tool (e.g., PowerPoint/Keynote/Google Slides).",
        "Provides a Python notebook file (.ipynb) as the deliverable implementing the American option pricing framework",
        "The updated quotation is delivered as a single Excel workbook saved with the exact filename Q9749821-revised_including_transport.xlsx.",
    ]
    for criterion in rejected:
        out = m.compile_criterion(criterion)
        assert out["status"] == "UNRESOLVED", (criterion, out)


def test_first_residual_replay_is_nonregressive_and_zero_credit():
    out = replay()
    assert out["status"].startswith("PASS__")
    assert out["source_population_task_count"] == 220
    assert out["v2_first_residual_compilable_count"] >= out["v1_first_residual_compilable_count"]
    assert out["v1_regression_count"] == 0
    assert out["acceptance_credit_delta"] == 0
    assert out["terminal_credit_delta"] == 0
