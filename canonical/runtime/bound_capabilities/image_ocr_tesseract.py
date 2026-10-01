#!/usr/bin/env python3
"""Brain-bound direct image OCR using the already verified Tesseract inner route.

This adapter does not add a new OCR mechanism. It exposes the exact image-level
operation already exercised inside pdf_ocr_tesseract.py and its preserved receipt.
"""
from __future__ import annotations

import hashlib
import pathlib
import subprocess

CAPABILITY_ID="image.extract.ocr.tesseract"
VERIFIED_TESSERACT_PACKAGE={
    "origin":"Ubuntu",
    "name":"tesseract-ocr",
    "version":"5.3.4-1build5",
    "archive_sha256":"2dfac382d77215aee0c3de4a2a2205505d5f2195e72e79b54ad32154fc08da77",
}
SOURCE_VERIFICATION="canonical/astra_runtime/evidence/ASTRA-RUNTIME-BOUND-PDF-OCR-001__RECEIPT.json"
SOURCE_STATE="canonical/astra_runtime/state/ASTRA-RUNTIME-BOUND-PDF-OCR-001.json"


def _safe_path(root, raw):
    root=pathlib.Path(root).resolve()
    p=(root/str(raw or "")).resolve()
    if p != root and root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p


def run(args, root):
    src=_safe_path(root,args.get("path"))
    if not src.is_file():
        raise RuntimeError("IMAGE_NOT_FOUND")
    language=str(args.get("language") or "eng")
    if not language.replace("+","").isalnum():
        raise RuntimeError("OCR_LANGUAGE_INVALID")
    psm_values=args.get("psm_values") or ["6","7","11","3"]
    if not isinstance(psm_values,list) or not psm_values:
        raise RuntimeError("OCR_PSM_INVALID")
    candidates=[]
    for psm in psm_values:
        psm=str(psm)
        if not psm.isdigit():
            raise RuntimeError("OCR_PSM_INVALID")
        proc=subprocess.run(
            ["tesseract",str(src),"stdout","-l",language,"--psm",psm],
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
        "language":language,
        "selected_psm":best["psm"],
        "text":text[:20000],
        "text_truncated":len(text)>20000,
        "text_sha256":hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "text_bytes":len(text.encode("utf-8")),
        "attempts":candidates,
        "dependency":VERIFIED_TESSERACT_PACKAGE,
        "derivation":"EXACT_IMAGE_LEVEL_OPERATION_REUSED_FROM_VERIFIED_PDF_OCR_ROUTE",
        "source_verification":SOURCE_VERIFICATION,
        "source_state":SOURCE_STATE,
        "terminal_semantic_authority":False,
    }
