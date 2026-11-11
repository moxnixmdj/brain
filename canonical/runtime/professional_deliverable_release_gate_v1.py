from __future__ import annotations

import re
import zipfile
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_DELIVERABLE_RELEASE_GATE_V1"
_SHA = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")

_ARCHIVE_REQUIRED = {
    ".docx": {"[Content_Types].xml", "word/document.xml"},
    ".pptx": {"[Content_Types].xml", "ppt/presentation.xml"},
    ".xlsx": {"[Content_Types].xml", "xl/workbook.xml"},
}
_VISUAL_EXTENSIONS = {".pdf", ".docx", ".pptx", ".xlsx", ".png", ".jpg", ".jpeg"}


def _fail(errors: Sequence[str]) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "errors": sorted(set(errors)),
        "reusable_capability": True,
        "professional_quality_top": False,
        "owner_preference_equivalence": False,
        "semantic_premises_verified_by_runtime": False,
        "benchmark_credit_delta": 0,
        "capability_credit_delta": 0,
        "terminal_credit_delta": 0,
    }


def _ids(value: Any, label: str, errors: list[str]) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(x, str) or not x.strip() for x in value):
        errors.append(label + "_INVALID")
        return []
    out = [x.strip() for x in value]
    if len(set(out)) != len(out):
        errors.append(label + "_DUPLICATE")
    return out


def _sha(value: Any) -> bool:
    return isinstance(value, str) and _SHA.fullmatch(value) is not None


def _native_integrity(path: Path, expected_extension: str) -> tuple[bool, str | None]:
    try:
        data = path.read_bytes()
    except OSError:
        return False, "READ_FAILED"
    if not data:
        return False, "EMPTY_FILE"

    ext = expected_extension.lower()
    if ext == ".pdf":
        return (data.startswith(b"%PDF-") and b"%%EOF" in data[-2048:], "PDF_MAGIC_OR_EOF_INVALID")
    if ext == ".png":
        return (data.startswith(b"\x89PNG\r\n\x1a\n"), "PNG_MAGIC_INVALID")
    if ext in {".jpg", ".jpeg"}:
        return (data.startswith(b"\xff\xd8") and data.endswith(b"\xff\xd9"), "JPEG_MAGIC_INVALID")
    if ext == ".wav":
        return (len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WAVE", "WAV_CONTAINER_INVALID")
    if ext in {".mp4", ".mov"}:
        return (len(data) >= 12 and b"ftyp" in data[:32], "MP4_MOV_CONTAINER_INVALID")
    if ext == ".zip":
        try:
            with zipfile.ZipFile(path) as zf:
                return (zf.testzip() is None, "ZIP_CRC_INVALID")
        except (OSError, zipfile.BadZipFile):
            return False, "ZIP_INVALID"
    if ext in _ARCHIVE_REQUIRED:
        try:
            with zipfile.ZipFile(path) as zf:
                names = set(zf.namelist())
                if zf.testzip() is not None:
                    return False, "OFFICE_ZIP_CRC_INVALID"
                if not _ARCHIVE_REQUIRED[ext].issubset(names):
                    return False, "OFFICE_REQUIRED_PART_MISSING"
                return True, None
        except (OSError, zipfile.BadZipFile):
            return False, "OFFICE_CONTAINER_INVALID"
    return True, None


def verify(manifest: Mapping[str, Any], *, base_dir: str | Path = ".") -> dict[str, Any]:
    if not isinstance(manifest, Mapping):
        return _fail(["MANIFEST_NOT_OBJECT"])
    errors: list[str] = []
    base = Path(base_dir).resolve()

    sources = manifest.get("source_authority")
    if not isinstance(sources, list) or not sources:
        errors.append("SOURCE_AUTHORITY_REQUIRED")
        sources = []
    seen_sources: set[str] = set()
    for idx, row in enumerate(sources):
        if not isinstance(row, Mapping):
            errors.append(f"SOURCE_NOT_OBJECT:{idx}")
            continue
        sid = str(row.get("source_id") or "").strip()
        if not sid:
            errors.append(f"SOURCE_ID_MISSING:{idx}")
            continue
        if sid in seen_sources:
            errors.append("SOURCE_ID_DUPLICATE:" + sid)
        seen_sources.add(sid)
        if not _sha(row.get("content_sha")):
            errors.append("SOURCE_CONTENT_SHA_INVALID:" + sid)

    contract = manifest.get("contract")
    if not isinstance(contract, Mapping):
        return _fail(errors + ["CONTRACT_NOT_OBJECT"])
    required_deliverables = _ids(contract.get("required_deliverable_ids"), "REQUIRED_DELIVERABLE_IDS", errors)
    required_obligations = _ids(contract.get("required_obligation_ids"), "REQUIRED_OBLIGATION_IDS", errors)
    required_verifications = _ids(contract.get("required_verification_ids"), "REQUIRED_VERIFICATION_IDS", errors)
    visual_ids = _ids(contract.get("visual_deliverable_ids", []), "VISUAL_DELIVERABLE_IDS", errors)
    if not set(visual_ids).issubset(set(required_deliverables)):
        errors.append("VISUAL_IDS_NOT_SUBSET_OF_REQUIRED_DELIVERABLES")

    deliverables = manifest.get("deliverables")
    if not isinstance(deliverables, list):
        errors.append("DELIVERABLES_INVALID")
        deliverables = []
    seen_deliverables: set[str] = set()
    visual_by_id: dict[str, Mapping[str, Any]] = {}
    for idx, row in enumerate(deliverables):
        if not isinstance(row, Mapping):
            errors.append(f"DELIVERABLE_NOT_OBJECT:{idx}")
            continue
        did = str(row.get("deliverable_id") or "").strip()
        if not did:
            errors.append(f"DELIVERABLE_ID_MISSING:{idx}")
            continue
        if did in seen_deliverables:
            errors.append("DELIVERABLE_ID_DUPLICATE:" + did)
            continue
        seen_deliverables.add(did)

        rel = str(row.get("path") or "").strip()
        ext = str(row.get("expected_extension") or "").strip().lower()
        if not rel:
            errors.append("DELIVERABLE_PATH_MISSING:" + did)
            continue
        if not ext.startswith("."):
            errors.append("EXPECTED_EXTENSION_INVALID:" + did)
            continue
        path = (base / rel).resolve()
        try:
            path.relative_to(base)
        except ValueError:
            errors.append("DELIVERABLE_PATH_ESCAPES_BASE:" + did)
            continue
        if path.suffix.lower() != ext:
            errors.append("DELIVERABLE_EXTENSION_MISMATCH:" + did)
        if not path.is_file():
            errors.append("DELIVERABLE_FILE_MISSING:" + did)
            continue
        ok, reason = _native_integrity(path, ext)
        if not ok:
            errors.append("NATIVE_INTEGRITY_FAIL:" + did + ":" + str(reason))
        if ext in _VISUAL_EXTENSIONS:
            visual_by_id[did] = row

    if seen_deliverables != set(required_deliverables):
        for did in sorted(set(required_deliverables) - seen_deliverables):
            errors.append("REQUIRED_DELIVERABLE_MISSING:" + did)
        for did in sorted(seen_deliverables - set(required_deliverables)):
            errors.append("UNEXPECTED_DELIVERABLE:" + did)

    for did in visual_ids:
        row = visual_by_id.get(did)
        if row is None:
            errors.append("VISUAL_DELIVERABLE_EVIDENCE_MISSING:" + did)
            continue
        checks = row.get("visual_checks")
        if not isinstance(checks, Mapping):
            errors.append("VISUAL_CHECKS_MISSING:" + did)
            continue
        pages_total = checks.get("pages_total")
        pages_inspected = checks.get("pages_inspected")
        if not isinstance(pages_total, int) or isinstance(pages_total, bool) or pages_total <= 0:
            errors.append("VISUAL_PAGE_COUNT_INVALID:" + did)
        if pages_inspected != pages_total:
            errors.append("VISUAL_INSPECTION_INCOMPLETE:" + did)
        for flag in (
            "render_complete",
            "no_blank_pages",
            "no_cutoff",
            "no_unintended_overlap",
            "legible",
        ):
            if checks.get(flag) is not True:
                errors.append("VISUAL_CHECK_FAILED:" + did + ":" + flag)
        if not _sha(checks.get("visual_receipt_sha")):
            errors.append("VISUAL_RECEIPT_INVALID:" + did)

    obligations = manifest.get("obligations")
    if not isinstance(obligations, list):
        errors.append("OBLIGATIONS_INVALID")
        obligations = []
    seen_obligations: set[str] = set()
    for idx, row in enumerate(obligations):
        if not isinstance(row, Mapping):
            errors.append(f"OBLIGATION_NOT_OBJECT:{idx}")
            continue
        oid = str(row.get("obligation_id") or "").strip()
        if not oid:
            errors.append(f"OBLIGATION_ID_MISSING:{idx}")
            continue
        if oid in seen_obligations:
            errors.append("OBLIGATION_ID_DUPLICATE:" + oid)
        seen_obligations.add(oid)
        if row.get("covered") is not True:
            errors.append("OBLIGATION_NOT_COVERED:" + oid)
        if not _sha(row.get("coverage_receipt_sha")):
            errors.append("OBLIGATION_RECEIPT_INVALID:" + oid)
    if seen_obligations != set(required_obligations):
        for oid in sorted(set(required_obligations) - seen_obligations):
            errors.append("REQUIRED_OBLIGATION_MISSING:" + oid)
        for oid in sorted(seen_obligations - set(required_obligations)):
            errors.append("UNDECLARED_OBLIGATION:" + oid)

    verifications = manifest.get("verifications")
    if not isinstance(verifications, list):
        errors.append("VERIFICATIONS_INVALID")
        verifications = []
    seen_verifications: set[str] = set()
    for idx, row in enumerate(verifications):
        if not isinstance(row, Mapping):
            errors.append(f"VERIFICATION_NOT_OBJECT:{idx}")
            continue
        vid = str(row.get("verification_id") or "").strip()
        if not vid:
            errors.append(f"VERIFICATION_ID_MISSING:{idx}")
            continue
        if vid in seen_verifications:
            errors.append("VERIFICATION_ID_DUPLICATE:" + vid)
        seen_verifications.add(vid)
        if row.get("passed") is not True:
            errors.append("VERIFICATION_FAILED:" + vid)
        if not _sha(row.get("verification_receipt_sha")):
            errors.append("VERIFICATION_RECEIPT_INVALID:" + vid)
    if seen_verifications != set(required_verifications):
        for vid in sorted(set(required_verifications) - seen_verifications):
            errors.append("REQUIRED_VERIFICATION_MISSING:" + vid)
        for vid in sorted(seen_verifications - set(required_verifications)):
            errors.append("UNDECLARED_VERIFICATION:" + vid)

    grounding = manifest.get("grounding")
    if not isinstance(grounding, Mapping):
        errors.append("GROUNDING_STATE_MISSING")
    elif grounding.get("material_claims_present") is True:
        if grounding.get("claim_manifest_complete") is not True:
            errors.append("MATERIAL_CLAIM_MANIFEST_NOT_COMPLETE")
        if grounding.get("all_material_claims_grounded") is not True:
            errors.append("MATERIAL_CLAIMS_NOT_ALL_GROUNDED")
        if not _sha(grounding.get("claim_manifest_receipt_sha")):
            errors.append("CLAIM_MANIFEST_RECEIPT_INVALID")
        if not _sha(grounding.get("grounding_receipt_sha")):
            errors.append("GROUNDING_RECEIPT_INVALID")

    if contract.get("audience_fit_required") is True:
        audience = manifest.get("audience_fit")
        if not isinstance(audience, Mapping) or audience.get("passed") is not True:
            errors.append("AUDIENCE_FIT_NOT_PROVED")
        elif not _sha(audience.get("receipt_sha")):
            errors.append("AUDIENCE_FIT_RECEIPT_INVALID")

    final = manifest.get("final_submission")
    if not isinstance(final, Mapping):
        errors.append("FINAL_SUBMISSION_STATE_MISSING")
    else:
        if final.get("all_deliverables_opened_after_last_write") is not True:
            errors.append("FINAL_OPEN_CHECK_NOT_PROVED")
        if not _sha(final.get("receipt_sha")):
            errors.append("FINAL_SUBMISSION_RECEIPT_INVALID")

    if errors:
        return _fail(errors)
    return {
        "schema": SCHEMA,
        "status": "PASS__PROFESSIONAL_DELIVERABLE_RELEASE_FLOOR",
        "pass": True,
        "errors": [],
        "deliverable_count": len(seen_deliverables),
        "obligation_count": len(seen_obligations),
        "verification_count": len(seen_verifications),
        "reusable_capability": True,
        "capability_id": "PROFESSIONAL_DELIVERABLE_RELEASE_ASSURANCE_V1",
        "professional_quality_top": False,
        "owner_preference_equivalence": False,
        "semantic_premises_verified_by_runtime": False,
        "remaining_obligations": [
            "SEMANTIC_COMPLETENESS_OF_DECLARED_TASK_OBLIGATIONS_IS_EXTERNALLY_PROVED",
            "GROUNDING_AND_AUDIENCE_RECEIPTS_ARE_SEMANTICALLY_VALID",
            "OPEN_SUBJECTIVE_PRESENTATION_AESTHETIC_AND_RELEVANCE_ORDER_IS_NOT_CLOSED_BY_THIS_GATE",
        ],
        "benchmark_credit_delta": 0,
        "capability_credit_delta": 0,
        "terminal_credit_delta": 0,
    }
