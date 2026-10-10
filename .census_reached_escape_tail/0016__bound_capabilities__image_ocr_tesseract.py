#!/usr/bin/env python3
"""Brain-bound direct image OCR on an exact pinned Ubuntu/Tesseract surface.

Ownership scope is deliberately narrow: English raster text extraction using
Tesseract 5.3.4 on the declared Ubuntu package/model bytes. This adapter is not
semantic authority and fails closed if the package or traineddata surface drifts.
"""
from __future__ import annotations

import hashlib
import pathlib
import subprocess

CAPABILITY_ID="image.extract.ocr.tesseract"
EXPECTED_TESSERACT_VERSION="5.3.4"
EXPECTED_PACKAGES={
    "tesseract-ocr":"5.3.4-1build5",
    "libtesseract5":"5.3.4-1build5",
    "tesseract-ocr-eng":"1:4.1.0-2",
}
EXPECTED_ENG_MODEL_PATH=pathlib.Path("/usr/share/tesseract-ocr/5/tessdata/eng.traineddata")
EXPECTED_ENG_MODEL_SHA256="7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2"
VERIFIED_TESSERACT_ARCHIVE_SHA256="2dfac382d77215aee0c3de4a2a2205505d5f2195e72e79b54ad32154fc08da77"
SOURCE_VERIFICATION="canonical/astra_runtime/evidence/ASTRA-RUNTIME-BOUND-PDF-OCR-001__RECEIPT.json"
SOURCE_STATE="canonical/astra_runtime/state/ASTRA-RUNTIME-BOUND-PDF-OCR-001.json"
SURFACE_DISCOVERY_RUN_ID=36942751400


def _safe_path(root, raw):
    root=pathlib.Path(root).resolve()
    p=(root/str(raw or "")).resolve()
    if p != root and root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p


def _run_text(cmd):
    proc=subprocess.run(cmd,text=True,capture_output=True,timeout=30)
    if proc.returncode!=0:
        raise RuntimeError("OCR_DEPENDENCY_QUERY_FAILED:"+proc.stderr[-800:])
    return proc.stdout.strip()


def verify_dependency_surface(*, model_path=EXPECTED_ENG_MODEL_PATH):
    version_line=_run_text(["tesseract","--version"]).splitlines()[0].strip()
    if version_line != f"tesseract {EXPECTED_TESSERACT_VERSION}":
        raise RuntimeError("TESSERACT_VERSION_MISMATCH:"+version_line)

    observed_packages={}
    for name,expected in EXPECTED_PACKAGES.items():
        observed=_run_text(["dpkg-query","-W","-f=${Version}",name])
        observed_packages[name]=observed
        if observed != expected:
            raise RuntimeError(f"OCR_PACKAGE_VERSION_MISMATCH:{name}:{observed}")

    model_path=pathlib.Path(model_path)
    if not model_path.is_file():
        raise RuntimeError("OCR_ENG_MODEL_MISSING")
    model_sha=hashlib.sha256(model_path.read_bytes()).hexdigest()
    if model_sha != EXPECTED_ENG_MODEL_SHA256:
        raise RuntimeError("OCR_ENG_MODEL_HASH_MISMATCH:"+model_sha)

    return {
        "status":"PINNED_DEPENDENCY_SURFACE_VERIFIED",
        "tesseract_version":EXPECTED_TESSERACT_VERSION,
        "packages":observed_packages,
        "eng_model_path":str(model_path),
        "eng_model_sha256":model_sha,
        "tesseract_archive_sha256":VERIFIED_TESSERACT_ARCHIVE_SHA256,
        "surface_discovery_run_id":SURFACE_DISCOVERY_RUN_ID,
    }


def run(args, root):
    src=_safe_path(root,args.get("path"))
    if not src.is_file():
        raise RuntimeError("IMAGE_NOT_FOUND")

    language=str(args.get("language") or "eng")
    if language != "eng":
        raise RuntimeError("OCR_LANGUAGE_OUTSIDE_PINNED_SCOPE")

    psm_values=args.get("psm_values") or ["6","7","11","3"]
    if not isinstance(psm_values,list) or not psm_values:
        raise RuntimeError("OCR_PSM_INVALID")
    allowed={"3","6","7","11"}
    normalized=[str(x) for x in psm_values]
    if any(x not in allowed for x in normalized):
        raise RuntimeError("OCR_PSM_OUTSIDE_VERIFIED_SCOPE")

    dependency=verify_dependency_surface()
    candidates=[]
    for psm in normalized:
        proc=subprocess.run(
            ["tesseract",str(src),"stdout","-l","eng","--psm",psm],
            text=True,capture_output=True,timeout=180
        )
        candidates.append({
            "psm":psm,
            "returncode":proc.returncode,
            "text":proc.stdout.strip() if proc.returncode==0 else "",
            "stderr":proc.stderr[-800:],
        })
    successful=[x for x in candidates if x["returncode"]==0]
    if not successful:
        raise RuntimeError("TESSERACT_FAILED_ALL_PSM")
    best=max(successful,key=lambda x:(len(x["text"].split()),len(x["text"])))

    raw=src.read_bytes()
    text=best["text"]
    return {
        "adapter":"bound_capability",
        "capability_id":CAPABILITY_ID,
        "source_path":str(src.relative_to(pathlib.Path(root).resolve())),
        "source_sha256":hashlib.sha256(raw).hexdigest(),
        "language":"eng",
        "selected_psm":best["psm"],
        "text":text[:20000],
        "text_truncated":len(text)>20000,
        "text_sha256":hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "text_bytes":len(text.encode("utf-8")),
        "attempts":candidates,
        "dependency":dependency,
        "derivation":"EXACT_IMAGE_LEVEL_OPERATION_REUSED_FROM_VERIFIED_PDF_OCR_ROUTE__MODEL_DATA_PINNED_AND_RUNTIME_CHECKED",
        "source_verification":SOURCE_VERIFICATION,
        "source_state":SOURCE_STATE,
        "terminal_semantic_authority":False,
        "scope":"ENGLISH_RASTER_TEXT_EXTRACTION_ONLY__NO_CALLOUT_OR_ENGINEERING_SEMANTIC_AUTHORITY",
    }
