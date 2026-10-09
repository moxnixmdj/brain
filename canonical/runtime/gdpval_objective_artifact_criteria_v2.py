"""Conservative V2 compiler for objective GDPval artifact criteria.

V2 preserves every V1 admission and adds only whole-criterion mechanical forms
whose truth can be independently checked from top-level artifact bytes.

The compiler is deliberately one-sided.  Some criteria allow several formats
(e.g. .doc or .docx); V2 may admit only a verified subset such as .docx.  Such a
check may create false negatives but must not create false positives.

Semantic roles, content quality, provenance/origin claims, and mixed mechanical
plus semantic criteria remain unresolved.
"""
from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Mapping

from canonical.runtime import gdpval_objective_artifact_criteria_v1 as v1

SCHEMA = "PROJECT_BRAIN_GDPVAL_OBJECTIVE_ARTIFACT_CRITERIA_V2"
V1_SCHEMA = v1.SCHEMA
_NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}


def _norm(value: Any) -> str:
    return " ".join(str(value or "").split())


def _base(text: str, criterion_id: str | None) -> dict[str, Any]:
    import hashlib
    return {
        "schema": SCHEMA,
        "criterion_id": criterion_id,
        "criterion": text,
        "criterion_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "terminal_authority": False,
        "acceptance_credit_authority": False,
    }


def _compiled(
    base: Mapping[str, Any],
    *,
    kind: str,
    args: Mapping[str, Any],
    relation: str = "EXACT_MECHANICAL_EQUIVALENCE",
) -> dict[str, Any]:
    return {
        **dict(base),
        "status": "COMPILED_OBJECTIVE_CHECK",
        "checks": [{"kind": kind, "args": dict(args)}],
        "compiler_origin": "V2",
        "criterion_to_check_relation": relation,
        "soundness_boundary": (
            "WHOLE_CRITERION_CONTROLLED_MECHANICAL_GRAMMAR_ONLY__"
            "NO_IGNORED_CONJUNCTS__NO_SEMANTIC_ROLE_IDENTITY__"
            "NO_CONTENT_QUALITY_PROVENANCE_OR_ORIGIN_INFERENCE__"
            "SUFFICIENT_SUBSET_CHECKS_MAY_FALSE_NEGATIVE_BUT_MUST_NOT_FALSE_POSITIVE"
        ),
    }


def _single_ext(base: Mapping[str, Any], ext: str, *, subset: bool = False) -> dict[str, Any]:
    return _compiled(
        base,
        kind="EXACT_TOP_LEVEL_FILE_COUNT_BY_EXTENSION",
        args={"count": 1, "extension": ext, "total_files_must_equal_count": True},
        relation=(
            "SOUND_SUFFICIENT_SUBSET__FALSE_NEGATIVES_ALLOWED"
            if subset else "EXACT_MECHANICAL_EQUIVALENCE"
        ),
    )


def _at_least_ext(base: Mapping[str, Any], ext: str, *, subset: bool = False) -> dict[str, Any]:
    return _compiled(
        base,
        kind="AT_LEAST_ONE_VALID_FILE_BY_EXTENSION",
        args={"extension": ext},
        relation=(
            "SOUND_SUFFICIENT_SUBSET__FALSE_NEGATIVES_ALLOWED"
            if subset else "EXACT_MECHANICAL_EQUIVALENCE"
        ),
    )


_PDF_SINGLE = (
    r"A single PDF file is delivered[.]?",
    r"(?:The )?(?:final )?deliverable is (?:provided as )?a single PDF (?:file|document)[.]?",
    r"(?:The )?submission is (?:provided as )?a single PDF (?:file|document)[.]?",
    r"(?:The )?submission is a single file in PDF format(?: \(\.pdf\))?[.]?",
    r"(?:The )?submitted deliverable is a single PDF file(?: \(filename ends with \.pdf\) and not a link to cloud slides or other formats)?[.]?",
    r"Exactly one (?:attached|deliverable) file is (?:provided|submitted) and (?:its filename ends with|its extension is) \.pdf(?: \(single PDF deliverable\))?[.]?",
    r"Exactly one PDF file is submitted and it opens successfully without a password or corruption \(\.pdf extension present\)[.]?",
    r"(?:The )?deliverable is exactly one PDF file \(not multiple files or a ZIP\)[.]?",
    r"Provides deliverable as a single PDF file[.]?",
)

_PDF_EXISTS = (
    r"(?:The )?(?:final )?deliverable is (?:provided as )?(?:a )?PDF(?: file| document)?(?: \(\.pdf\))?[.]?",
    r"(?:The )?submission is (?:provided as )?(?:a )?PDF(?: file| document)?[.]?",
    r"(?:The )?deliverable is in PDF format[.]?",
    r"Final deliverable is a PDF file[.]?",
    r"Creates the document as a PDF file[.]?",
)

_WORD_SINGLE = (
    r"(?:The )?(?:final )?deliverable is a single (?:Microsoft Word|Word)(?: document| file)?(?: \(\.docx\))?(?: with (?:a |the )?\.docx extension)?[.]?",
    r"(?:The )?submission is a single (?:Microsoft Word|Word)(?: document| file)?(?: in \.docx format| \(\.docx\))?[.]?",
    r"Provides exactly one deliverable file in Word format \(\.docx\)[.]?",
    r"Exactly one deliverable file is provided and its extension is \.docx \(Microsoft Word\)[.]?",
)

_WORD_EXISTS_EXACT = (
    r"Deliverable is a Microsoft Word file[.]?",
    r"(?:The )?(?:final )?deliverable is (?:provided as )?a (?:Microsoft Word|Word)(?: document| file)(?: with a \.docx file extension| with the \.docx extension| \(\.docx\))?[.]?",
    r"(?:The )?submission is (?:provided as )?a (?:Microsoft Word|Word)(?: document| file)(?: with a \.docx extension| \(\.docx\))?[.]?",
    r"(?:The )?submitted deliverable is a \.docx Word document \(file extension \.docx\)[.]?",
    r"(?:The )?submission includes a Word document file with a \.docx extension[.]?",
    r"A Word document \(\.docx\) is attached as the deliverable[.]?",
    r"At least one Microsoft Word \.docx file is provided as the deliverable[.]?",
    r"Submission is provided as a Microsoft Word \(\.docx\) document[.]?",
    r"(?:The )?(?:final )?deliverable is (?:provided as )?a (?:Microsoft Word|Word) document with (?:a |the )?\.docx extension[.]?",
)

_WORD_EXISTS_SUBSET = (
    r"(?:The )?(?:final )?deliverable is (?:provided as )?a (?:Microsoft Word|Word) document \(\.docx or \.doc\)[.]?",
    r"(?:The )?submission is a Microsoft Word document file with extension \.docx or \.doc[.]?",
    r"Provides the deliverable as a Microsoft Word file \(\.docx or \.doc\)[.]?",
    r"Provides a Word document \(\.docx or \.doc\) as the final attached deliverable[.]?",
)

_XLSX_SINGLE = (
    r"Delivers a single Excel workbook file(?: in \.xlsx format| \(\.xlsx\))?[.]?",
    r"(?:The )?(?:final )?deliverable is (?:provided as )?a single Excel workbook(?: file)?(?: in \.xlsx format| with (?:a |the )?\.xlsx extension| with file extension \.xlsx| \(\.xlsx\))?[.]?",
    r"(?:The )?submission is (?:provided as )?a single Excel workbook(?: file)?(?: in \.xlsx format| with (?:a |the )?\.xlsx extension| \(\.xlsx\))?[.]?",
    r"Output (?:is|contains) a single Excel(?: workbook| file)?(?: \(\.xlsx\))?(?: file)?(?: with the \.xlsx extension)?[.]?",
    r"Delivers the final output as a single Excel workbook file with \.xlsx extension[.]?",
)

_XLSX_EXISTS_EXACT = (
    r"(?:The )?(?:final )?deliverable is (?:provided as )?an? Excel workbook(?: file)?(?: in \.xlsx format| with (?:a |the )?\.xlsx extension| \(\.xlsx\))?[.]?",
    r"(?:The )?submission is (?:provided as )?an? Excel workbook(?: file)?(?: in \.xlsx format| with (?:a |the )?\.xlsx extension| \(\.xlsx\))?[.]?",
    r"(?:The )?submitted deliverable is an Excel file[.]?",
    r"Deliverable is (?:provided as )?an Excel (?:file|workbook file|spreadsheet)(?: \(\.xlsx\))?[.]?",
    r"An Excel workbook \(\.xlsx\) is present in the deliverable files[.]?",
    r"The spreadsheet deliverable is an Excel workbook in \.xlsx format[.]?",
    r"Provides an Excel workbook \(\.xlsx\) in the deliverable[.]?",
)

_XLSX_EXISTS_SUBSET = (
    r"(?:The )?(?:final )?deliverable is (?:provided as )?an? Excel (?:file|workbook|spreadsheet)[.]?",
    r"(?:The )?submission is (?:provided as )?an? Excel (?:file|workbook|spreadsheet)[.]?",
    r"Delivers a single Excel workbook[.]?",
    r"Delivers a single Excel workbook file in \.xlsx or \.xls format[.]?",
    r"Provides an Excel spreadsheet file \(\.xlsx or \.xls\) as the deliverable[.]?",
)

_PPTX_SINGLE_SUBSET = (
    r"(?:The )?(?:final )?deliverable is a single PowerPoint file with extension \.pptx or \.ppt \(not a PDF, image, link, Google Slides, or Keynote\)[.]?",
)

_PPTX_EXISTS = (
    r"(?:The )?(?:final )?deliverable is (?:provided as )?(?:a )?(?:\.pptx )?PowerPoint(?: presentation)? file(?: in \.pptx format| with (?:a |the )?\.pptx extension)?[.]?",
    r"Delivers a PowerPoint presentation file in \.pptx format that opens without errors[.]?",
)

_MP4_SINGLE = (
    r"(?:The )?final deliverable consists of a single file whose extension is \.mp4 \(case-insensitive\)[.]?",
)

_MP4_EXISTS = (
    r"Final deliverable is an MP4 file \(\.mp4 extension\)[.]?",
)


def _matches(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.fullmatch(pattern, text, re.I) is not None for pattern in patterns)


def compile_criterion(criterion: str, *, criterion_id: str | None = None) -> dict[str, Any]:
    text = _norm(criterion)
    base = _base(text, criterion_id)
    if not text:
        return {**base, "status": "FAIL_CLOSED", "reason": "CRITERION_MISSING"}

    prior = v1.compile_criterion(text, criterion_id=criterion_id)
    if prior.get("status") == "COMPILED_OBJECTIVE_CHECK":
        return {
            **prior,
            "schema": SCHEMA,
            "compiler_origin": "V1_PRESERVED",
            "v1_schema": V1_SCHEMA,
            "criterion_to_check_relation": "V1_VERIFIED_RELATION_PRESERVED",
        }

    if re.fullmatch(
        r"(?:Exactly one submitted file exists|Exactly one deliverable file is submitted)[.]?",
        text,
        re.I,
    ):
        return _compiled(base, kind="EXACT_TOP_LEVEL_TOTAL_FILE_COUNT", args={"count": 1})

    if _matches(text, _PDF_SINGLE):
        return _single_ext(base, ".pdf")
    if _matches(text, _PDF_EXISTS):
        return _at_least_ext(base, ".pdf")

    if _matches(text, _WORD_SINGLE):
        return _single_ext(base, ".docx")
    if _matches(text, _WORD_EXISTS_EXACT):
        return _at_least_ext(base, ".docx")
    if _matches(text, _WORD_EXISTS_SUBSET):
        return _at_least_ext(base, ".docx", subset=True)

    if _matches(text, _XLSX_SINGLE):
        return _single_ext(base, ".xlsx")
    if _matches(text, _XLSX_EXISTS_EXACT):
        return _at_least_ext(base, ".xlsx")
    if _matches(text, _XLSX_EXISTS_SUBSET):
        return _at_least_ext(base, ".xlsx", subset=True)

    if _matches(text, _PPTX_SINGLE_SUBSET):
        return _single_ext(base, ".pptx", subset=True)
    if _matches(text, _PPTX_EXISTS):
        return _at_least_ext(base, ".pptx")

    m = re.fullmatch(r"Provides an Excel \.xlsx workbook with exactly (\d+|one|two|three|four|five|six|seven|eight|nine|ten) worksheets? \(tabs\)[.]?", text, re.I)
    if m:
        token = m.group(1).lower()
        count = int(token) if token.isdigit() else _NUMBER_WORDS[token]
        return _compiled(base, kind="SINGLE_XLSX_SHEET_COUNT", args={"sheet_count": count})

    if _matches(text, _MP4_SINGLE):
        return _single_ext(base, ".mp4")
    if _matches(text, _MP4_EXISTS):
        return _at_least_ext(base, ".mp4")

    if re.fullmatch(r"The submission is a \.zip archive that opens successfully[.]?", text, re.I):
        return _at_least_ext(base, ".zip")
    if re.fullmatch(r"All content in the deliverable is inside a single \.zip archive[.]?", text, re.I):
        return _single_ext(base, ".zip")

    return {
        **base,
        "status": "UNRESOLVED",
        "reason": "OUTSIDE_V2_CONTROLLED_OBJECTIVE_ARTIFACT_GRAMMAR",
        "v1_status": prior.get("status"),
        "v1_reason": prior.get("reason"),
    }


def verify_compiled(compiled: Mapping[str, Any], artifact_dir: str | Path) -> dict[str, Any]:
    if compiled.get("status") != "COMPILED_OBJECTIVE_CHECK":
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": ["CRITERION_NOT_COMPILED"],
            "terminal_authority": False,
        }

    checks = list(compiled.get("checks") or [])
    if len(checks) == 1 and checks[0].get("kind") == "EXACT_TOP_LEVEL_TOTAL_FILE_COUNT":
        root = Path(artifact_dir)
        if not root.is_dir():
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED",
                "pass": False,
                "errors": ["ARTIFACT_DIR_INVALID"],
                "terminal_authority": False,
            }
        files = sorted((p for p in root.iterdir() if p.is_file()), key=lambda p: p.name.casefold())
        target = int((checks[0].get("args") or {}).get("count", -1))
        ok = len(files) == target
        return {
            "schema": SCHEMA,
            "status": "PASS__OBJECTIVE_CRITERION_VERIFIED" if ok else "FALSIFIED_OR_FAIL_CLOSED",
            "pass": ok,
            "criterion_id": compiled.get("criterion_id"),
            "criterion_sha256": compiled.get("criterion_sha256"),
            "evidence": [{"kind": "EXACT_TOP_LEVEL_TOTAL_FILE_COUNT", "observed": len(files), "expected": target, "pass": ok}],
            "errors": [] if ok else ["CHECK_FAILED:EXACT_TOP_LEVEL_TOTAL_FILE_COUNT"],
            "terminal_authority": False,
            "u_deletion_authority": False,
        }

    delegated = dict(compiled)
    delegated["schema"] = V1_SCHEMA
    out = dict(v1.verify_compiled(delegated, artifact_dir))
    out["schema"] = SCHEMA
    out["verification_origin"] = "V1_INDEPENDENT_ARTIFACT_VERIFIER"
    return out
