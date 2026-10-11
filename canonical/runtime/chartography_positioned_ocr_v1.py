from __future__ import annotations

import csv
import io
import pathlib
import subprocess
from typing import Any, Iterable

from canonical.runtime.bound_capabilities.image_ocr_tesseract import verify_dependency_surface

SCHEMA = "PROJECT_BRAIN_CHARTOGRAPHY_POSITIONED_OCR_V2"


class PositionedOCRError(ValueError):
    pass


def parse_tsv(raw: str, *, min_confidence: float = 0.0) -> list[dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(raw), delimiter="\t")
    required = {
        "level", "page_num", "block_num", "par_num", "line_num", "word_num",
        "left", "top", "width", "height", "conf", "text",
    }
    if reader.fieldnames is None or not required.issubset(set(reader.fieldnames)):
        raise PositionedOCRError("TESSERACT_TSV_SCHEMA_INVALID")
    out=[]
    for row in reader:
        text=str(row.get("text") or "").strip()
        if not text:
            continue
        try:
            conf=float(row["conf"]); left=int(row["left"]); top=int(row["top"])
            width=int(row["width"]); height=int(row["height"])
        except Exception as exc:
            raise PositionedOCRError("TESSERACT_TSV_ROW_INVALID") from exc
        if conf < min_confidence or width <= 0 or height <= 0:
            continue
        out.append({
            "text":text,"confidence":conf,
            "left":left,"top":top,"width":width,"height":height,
            "cx":left+width/2.0,"cy":top+height/2.0,
            "block_num":int(row["block_num"]),"par_num":int(row["par_num"]),
            "line_num":int(row["line_num"]),"word_num":int(row["word_num"]),
        })
    return out


def _same_observation(a: dict[str,Any], b: dict[str,Any]) -> bool:
    if str(a["text"]).lower() != str(b["text"]).lower():
        return False
    tolerance=max(4.0,0.5*max(float(a["height"]),float(b["height"])))
    return abs(float(a["cx"])-float(b["cx"]))<=tolerance and abs(float(a["cy"])-float(b["cy"]))<=tolerance


def _merge(candidates: Iterable[dict[str,Any]]) -> list[dict[str,Any]]:
    merged=[]
    for row in sorted(candidates,key=lambda x:(-float(x["confidence"]),str(x["text"]))):
        if any(_same_observation(row,old) for old in merged):
            continue
        merged.append(dict(row))
    return sorted(merged,key=lambda x:(float(x["top"]),float(x["left"]),str(x["text"])))


def extract_words(
    image_path: str | pathlib.Path,
    *,
    psm: int | None = None,
    psm_values: Iterable[int] | None = None,
    min_confidence: float = 0.0,
) -> dict[str, Any]:
    src=pathlib.Path(image_path).resolve(strict=True)
    if psm is not None and psm_values is not None:
        raise PositionedOCRError("PSM_AND_PSM_VALUES_MUTUALLY_EXCLUSIVE")
    modes=list(psm_values) if psm_values is not None else ([psm] if psm is not None else [11,6,3])
    if not modes or any(int(x) not in {3,6,7,11} for x in modes):
        raise PositionedOCRError("PSM_OUTSIDE_PINNED_SCOPE")
    dependency=verify_dependency_surface()
    attempts=[]
    all_words=[]
    for mode in [int(x) for x in modes]:
        proc=subprocess.run(
            ["tesseract",str(src),"stdout","-l","eng","--psm",str(mode),"tsv"],
            text=True,capture_output=True,timeout=180,
        )
        words=parse_tsv(proc.stdout,min_confidence=min_confidence) if proc.returncode==0 else []
        attempts.append({"psm":mode,"returncode":proc.returncode,"word_count":len(words),"stderr":proc.stderr[-800:]})
        for word in words:
            word=dict(word); word["psm"]=mode; all_words.append(word)
    successful=[x for x in attempts if x["returncode"]==0]
    if not successful:
        raise PositionedOCRError("TESSERACT_TSV_FAILED_ALL_PSM")
    words=_merge(all_words)
    if not words:
        raise PositionedOCRError("NO_POSITIONED_OCR_WORDS")
    return {
        "schema":SCHEMA,
        "status":"PASS__MULTI_PSM_POSITIONED_OCR_OBSERVATION",
        "source_path":str(src),
        "psm_values":[int(x) for x in modes],
        "word_count":len(words),
        "words":words,
        "attempts":attempts,
        "dependency":dependency,
        "producer_cognition":False,
        "semantic_authority":False,
        "terminal_authority":False,
    }
