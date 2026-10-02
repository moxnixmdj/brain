"""Pinned Tesseract TSV bridge for positioned OCR observations.

This module deliberately adds geometry, not semantics. It uses the exact dependency
surface verified by image_ocr_tesseract, parses Tesseract TSV word rows, validates
boxes against the source raster, and deterministically groups words into text lines
compatible with drawing_annotation_constraint_pipeline.
"""
from __future__ import annotations

import csv
import hashlib
import io
import pathlib
import subprocess
from typing import Any, Iterable, Mapping

from canonical.runtime.bound_capabilities.image_ocr_tesseract import (
    _safe_path,
    verify_dependency_surface,
)

SCHEMA="BRAIN_PINNED_POSITIONED_OCR_TSV_BRIDGE_V1"


def parse_tsv(tsv_text:str, *, image_width:int, image_height:int, min_confidence:float=0.0)->dict[str,Any]:
    if not isinstance(image_width,int) or not isinstance(image_height,int) or image_width<=0 or image_height<=0:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"IMAGE_DIMENSIONS_INVALID"}
    if not isinstance(min_confidence,(int,float)) or isinstance(min_confidence,bool):
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"CONFIDENCE_THRESHOLD_INVALID"}

    reader=csv.DictReader(io.StringIO(tsv_text))
    required={"level","page_num","block_num","par_num","line_num","word_num","left","top","width","height","conf","text"}
    if reader.fieldnames is None or not required.issubset(set(reader.fieldnames)):
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"TSV_SCHEMA_INVALID"}

    words=[]
    errors=[]
    for row_index,row in enumerate(reader, start=2):
        try:
            if int(row["level"]) != 5:
                continue
            text=" ".join(str(row.get("text") or "").split())
            if not text:
                continue
            left=int(row["left"]); top=int(row["top"])
            width=int(row["width"]); height=int(row["height"])
            conf=float(row["conf"])
            if conf < float(min_confidence):
                continue
            if left<0 or top<0 or width<=0 or height<=0:
                raise ValueError("NONPOSITIVE_OR_NEGATIVE_BOX")
            x1=left+width; y1=top+height
            if x1>image_width or y1>image_height:
                raise ValueError("BOX_OUT_OF_BOUNDS")
            key=(int(row["page_num"]),int(row["block_num"]),int(row["par_num"]),int(row["line_num"]))
            words.append({
                "line_key":key,
                "word_num":int(row["word_num"]),
                "text":text,
                "confidence":conf,
                "box":{"x0":left,"y0":top,"x1_exclusive":x1,"y1_exclusive":y1},
            })
        except Exception as exc:
            errors.append(f"ROW_{row_index}:{type(exc).__name__}:{exc}")

    if errors:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","errors":sorted(errors)}

    groups={}
    for w in words:
        groups.setdefault(w["line_key"],[]).append(w)

    text_items=[]
    for key in sorted(groups):
        group=sorted(groups[key],key=lambda x:(x["word_num"],x["box"]["x0"],x["text"]))
        x0=min(w["box"]["x0"] for w in group); y0=min(w["box"]["y0"] for w in group)
        x1=max(w["box"]["x1_exclusive"] for w in group); y1=max(w["box"]["y1_exclusive"] for w in group)
        text_items.append({
            "text":" ".join(w["text"] for w in group),
            "box":{"x0":x0,"y0":y0,"x1_exclusive":x1,"y1_exclusive":y1},
            "source_id":"tesseract-line:"+":".join(map(str,key)),
            "word_count":len(group),
            "mean_confidence":sum(w["confidence"] for w in group)/len(group),
        })

    return {
        "schema":SCHEMA,
        "status":"PARSED",
        "text_items":text_items,
        "word_count":len(words),
        "line_count":len(text_items),
        "terminal_authority":False,
        "scope":"PINNED_TESSERACT_TSV_WORD_BOX_EXTRACTION_AND_DETERMINISTIC_LINE_GROUPING_ONLY",
    }


def extract_positioned_text(args:Mapping[str,Any], root:str|pathlib.Path)->dict[str,Any]:
    src=_safe_path(root,args.get("path"))
    if not src.is_file():
        raise RuntimeError("IMAGE_NOT_FOUND")
    language=str(args.get("language") or "eng")
    if language!="eng":
        raise RuntimeError("OCR_LANGUAGE_OUTSIDE_PINNED_SCOPE")
    psm=str(args.get("psm") or "6")
    if psm not in {"3","6","7","11"}:
        raise RuntimeError("OCR_PSM_OUTSIDE_VERIFIED_SCOPE")

    dependency=verify_dependency_surface()
    try:
        import cv2
    except Exception as exc:
        raise RuntimeError("OPENCV_REQUIRED_FOR_IMAGE_BOUND_VALIDATION") from exc
    image=cv2.imread(str(src),cv2.IMREAD_GRAYSCALE)
    if image is None or image.ndim!=2:
        raise RuntimeError("IMAGE_DECODE_FAILED")
    height,width=image.shape

    proc=subprocess.run(
        ["tesseract",str(src),"stdout","-l","eng","--psm",psm,"tsv"],
        text=True,capture_output=True,timeout=180
    )
    if proc.returncode!=0:
        raise RuntimeError("TESSERACT_TSV_FAILED:"+proc.stderr[-800:])

    parsed=parse_tsv(
        proc.stdout,
        image_width=int(width),
        image_height=int(height),
        min_confidence=float(args.get("min_confidence",0.0)),
    )
    if parsed.get("status")!="PARSED":
        raise RuntimeError("TESSERACT_TSV_PARSE_FAILED:"+str(parsed))

    raw=src.read_bytes()
    return {
        **parsed,
        "source_path":str(src.relative_to(pathlib.Path(root).resolve())),
        "source_sha256":hashlib.sha256(raw).hexdigest(),
        "image_width":int(width),
        "image_height":int(height),
        "language":"eng",
        "psm":psm,
        "dependency":dependency,
        "terminal_semantic_authority":False,
    }
