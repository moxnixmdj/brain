"""Fail-closed sufficient-condition compiler for objective GDPval rubric structure.

This module recognizes only narrow rubric forms whose satisfaction can be checked
mechanically from the delivered artifact(s) or plain-text answer. It deliberately
does not interpret professional quality, semantic relevance, factual correctness,
visual quality, or domain judgment.

A compiled predicate is SUFFICIENT for the exact source criterion. Unsupported
wording stays unresolved. Compilation is never a claim that the criterion is
necessary, that the whole task is solved, or that GDPval-AA pairwise preference
is reproduced.
"""
from __future__ import annotations

from hashlib import sha256
import json
import math
from pathlib import Path
import re
import struct
import wave
import zipfile
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_GDPVAL_STRUCTURAL_RUBRIC_SUFFICIENT_V1"
COMPILED_SCHEMA = "PROJECT_BRAIN_GDPVAL_STRUCTURAL_RUBRIC_PREDICATE_V1"

_WS = re.compile(r"\s+")

def _norm(text: str) -> str:
    return _WS.sub(" ", text.strip())

def _src(text: str) -> dict[str, str]:
    return {"criterion": text, "criterion_sha256": sha256(text.encode("utf-8")).hexdigest()}

def _compiled(text: str, predicates: list[dict[str, Any]], rule: str) -> dict[str, Any]:
    return {
        "schema": COMPILED_SCHEMA,
        "status": "COMPILED_SUFFICIENT_CONDITION",
        **_src(text),
        "predicates": predicates,
        "rule": rule,
        "semantic_authority": "ONLY_THE_EXACT_BOUND_PREDICATES",
        "whole_task_authority": False,
        "pairwise_preference_authority": False,
        "terminal_authority": False,
    }

def compile_criterion(criterion: str) -> dict[str, Any]:
    if not isinstance(criterion, str) or not criterion.strip():
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "CRITERION_MISSING"}
    t = _norm(criterion)

    exact = {
        "Output is a PDF.": ([{"kind": "OUTPUT_FILE_COUNT_EQ", "value": 1}, {"kind": "FILE_FORMAT_EQ", "format": "PDF"}], "EXACT_OUTPUT_IS_PDF"),
        "Output is a PDF": ([{"kind": "OUTPUT_FILE_COUNT_EQ", "value": 1}, {"kind": "FILE_FORMAT_EQ", "format": "PDF"}], "EXACT_OUTPUT_IS_PDF"),
        "Deliverable is a PDF.": ([{"kind": "OUTPUT_FILE_COUNT_EQ", "value": 1}, {"kind": "FILE_FORMAT_EQ", "format": "PDF"}], "EXACT_DELIVERABLE_IS_PDF"),
        "Deliverable is a PDF": ([{"kind": "OUTPUT_FILE_COUNT_EQ", "value": 1}, {"kind": "FILE_FORMAT_EQ", "format": "PDF"}], "EXACT_DELIVERABLE_IS_PDF"),
        "The deliverable is a single file in PDF format": ([{"kind": "OUTPUT_FILE_COUNT_EQ", "value": 1}, {"kind": "FILE_FORMAT_EQ", "format": "PDF"}], "EXACT_SINGLE_PDF"),
        "The deliverable is a single file in PDF format.": ([{"kind": "OUTPUT_FILE_COUNT_EQ", "value": 1}, {"kind": "FILE_FORMAT_EQ", "format": "PDF"}], "EXACT_SINGLE_PDF"),
        "Article is in PDF format.": ([{"kind": "OUTPUT_FILE_COUNT_EQ", "value": 1}, {"kind": "FILE_FORMAT_EQ", "format": "PDF"}], "EXACT_ARTICLE_PDF"),
        "Article is in PDF format": ([{"kind": "OUTPUT_FILE_COUNT_EQ", "value": 1}, {"kind": "FILE_FORMAT_EQ", "format": "PDF"}], "EXACT_ARTICLE_PDF"),
        "The document is delivered as a Word document file (.docx).": ([{"kind": "OUTPUT_FILE_COUNT_EQ", "value": 1}, {"kind": "FILE_FORMAT_EQ", "format": "DOCX"}], "EXACT_SINGLE_DOCX"),
        "The document is delivered as a Word document file (.docx)": ([{"kind": "OUTPUT_FILE_COUNT_EQ", "value": 1}, {"kind": "FILE_FORMAT_EQ", "format": "DOCX"}], "EXACT_SINGLE_DOCX"),
        "The delivered file is a WAV file and not a compressed format (e.g., MP3/AAC).": ([{"kind": "OUTPUT_FILE_COUNT_EQ", "value": 1}, {"kind": "WAV_PCM_UNCOMPRESSED"}], "EXACT_UNCOMPRESSED_WAV"),
        "PDF contains selectable text on at least one slide (i.e., not exclusively raster images).": ([{"kind": "OUTPUT_FILE_COUNT_EQ", "value": 1}, {"kind": "PDF_ANY_PAGE_SELECTABLE_TEXT"}], "EXACT_PDF_SELECTABLE_TEXT"),
    }
    if t in exact:
        predicates, rule = exact[t]
        return _compiled(criterion, predicates, rule)

    m = re.fullmatch(r'An audio file named exactly "([^"\\/]+\.wav)" is delivered\.', t, re.I)
    if m:
        return _compiled(criterion, [
            {"kind": "OUTPUT_FILE_BASENAME_EXISTS", "basename": m.group(1)},
            {"kind": "NAMED_FILE_FORMAT_EQ", "basename": m.group(1), "format": "WAV"},
        ], "EXACT_NAMED_WAV")

    m = re.fullmatch(r"PDF slide count is between (\d+) and (\d+) inclusive\.", t, re.I)
    if m:
        lo, hi = map(int, m.groups())
        if 0 < lo <= hi <= 10000:
            return _compiled(criterion, [
                {"kind": "OUTPUT_FILE_COUNT_EQ", "value": 1},
                {"kind": "FILE_FORMAT_EQ", "format": "PDF"},
                {"kind": "PDF_PAGE_COUNT_BETWEEN", "min": lo, "max": hi},
            ], "EXACT_PDF_PAGE_COUNT_RANGE")

    m = re.fullmatch(r"The deck contains between (\d+) and (\d+) slides inclusive \(counting all slides\)\.?", t, re.I)
    if m:
        lo, hi = map(int, m.groups())
        if 0 < lo <= hi <= 10000:
            return _compiled(criterion, [
                {"kind": "OUTPUT_FILE_COUNT_EQ", "value": 1},
                {"kind": "FILE_FORMAT_EQ", "format": "PPTX"},
                {"kind": "PPTX_SLIDE_COUNT_BETWEEN", "min": lo, "max": hi},
            ], "EXACT_PPTX_SLIDE_COUNT_RANGE")

    m = re.fullmatch(r"The paragraph contains between (\d+) and (\d+) sentences inclusive\.", t, re.I)
    if m:
        lo, hi = map(int, m.groups())
        if 0 < lo <= hi <= 1000:
            return _compiled(criterion, [
                {"kind": "TEXT_SINGLE_PARAGRAPH"},
                {"kind": "TEXT_SENTENCE_COUNT_BETWEEN", "min": lo, "max": hi},
            ], "EXACT_SINGLE_PARAGRAPH_SENTENCE_RANGE")

    m = re.fullmatch(r"Sample rate of the delivered file is ([0-9]+(?:\.[0-9]+)?)\s*kHz\.", t, re.I)
    if m:
        hz = int(round(float(m.group(1)) * 1000))
        return _compiled(criterion, [{"kind": "OUTPUT_FILE_COUNT_EQ", "value": 1}, {"kind": "WAV_SAMPLE_RATE_EQ", "hz": hz}], "EXACT_WAV_SAMPLE_RATE")

    m = re.fullmatch(r"Bit depth of the delivered file is (\d+)[\-‑–]bit PCM\.", t, re.I)
    if m:
        bits = int(m.group(1))
        if bits in {8, 16, 24, 32}:
            return _compiled(criterion, [{"kind": "OUTPUT_FILE_COUNT_EQ", "value": 1}, {"kind": "WAV_PCM_BIT_DEPTH_EQ", "bits": bits}], "EXACT_WAV_PCM_BIT_DEPTH")

    if re.fullmatch(r"The delivered file is in stereo \(Left/Right channels\)\.", t, re.I):
        return _compiled(criterion, [{"kind": "OUTPUT_FILE_COUNT_EQ", "value": 1}, {"kind": "WAV_CHANNEL_COUNT_EQ", "channels": 2}], "EXACT_WAV_STEREO")

    m = re.fullmatch(r"The delivered file’s total length is (\d+) minutes and (\d+) seconds \(±(\d+(?:\.\d+)?)%\)\.", t, re.I)
    if m:
        mins, secs, pct = int(m.group(1)), int(m.group(2)), float(m.group(3))
        target = 60 * mins + secs
        if target > 0 and 0 <= pct <= 100:
            return _compiled(criterion, [{"kind": "OUTPUT_FILE_COUNT_EQ", "value": 1}, {"kind": "WAV_DURATION_TARGET_TOLERANCE", "seconds": target, "percent": pct}], "EXACT_WAV_DURATION_TOLERANCE")

    if re.fullmatch(r"No digital clipping: maximum sample peak of the delivered mix is strictly below 0\.0 dBFS on both channels\.", t, re.I):
        return _compiled(criterion, [{"kind": "OUTPUT_FILE_COUNT_EQ", "value": 1}, {"kind": "WAV_PEAK_DBFS_LT", "dbfs": 0.0, "per_channel": True}], "EXACT_WAV_NO_CLIPPING")

    m = re.fullmatch(r"Recommended headroom practice: sample peaks do not exceed (-?\d+(?:\.\d+)?) dBFS\.", t, re.I)
    if m:
        return _compiled(criterion, [{"kind": "OUTPUT_FILE_COUNT_EQ", "value": 1}, {"kind": "WAV_PEAK_DBFS_LE", "dbfs": float(m.group(1)), "per_channel": False}], "EXACT_WAV_HEADROOM")

    if re.fullmatch(r"Submission is a PowerPoint file with a \.pptx extension that opens without error in PowerPoint[‑-]compatible software", t, re.I):
        return _compiled(criterion, [{"kind": "OUTPUT_FILE_COUNT_EQ", "value": 1}, {"kind": "FILE_FORMAT_EQ", "format": "PPTX"}], "EXACT_OPENABLE_PPTX")


    # Generic but still narrow whole-criterion structural forms. Each accepted
    # form is intentionally stronger than (or exactly equal to) the source
    # wording; no role/content semantics are inferred.
    single_format_patterns = [
        (r"(?:The )?final deliverable is provided as an Excel workbook in \.xlsx format\\.?", "XLSX", "SINGLE_XLSX_FORMAT"),
        (r"Delivers a single Excel workbook file in \.xlsx format\\.?", "XLSX", "SINGLE_XLSX_FORMAT"),
        (r"The submitted file is an \.xlsx Excel workbook \(not \.xlsm or other formats\)\\.?", "XLSX", "SINGLE_XLSX_FORMAT"),
        (r"(?:The )?deliverable is provided as an Excel workbook file \(\.xlsx\)\\.?", "XLSX", "SINGLE_XLSX_FORMAT"),
        (r"(?:The )?deliverable is an Excel workbook in \.xlsx format\\.?", "XLSX", "SINGLE_XLSX_FORMAT"),
        (r"(?:The )?deliverable is an Excel workbook file with a \.xlsx extension\\.?", "XLSX", "SINGLE_XLSX_FORMAT"),
        (r"(?:The )?deliverable is provided as a single Excel workbook in \.xlsx format\\.?", "XLSX", "SINGLE_XLSX_FORMAT"),
        (r"(?:The )?deliverable is provided as a single Excel workbook with the \.xlsx extension\\.?", "XLSX", "SINGLE_XLSX_FORMAT"),
        (r"(?:The )?deliverable is a single Excel workbook saved with the \.xlsx extension\\.?", "XLSX", "SINGLE_XLSX_FORMAT"),
        (r"(?:The )?final deliverable is a single Excel workbook with file extension \.xlsx\\.?", "XLSX", "SINGLE_XLSX_FORMAT"),
        (r"Output contains a single Excel \(\.xlsx\) file\\.?", "XLSX", "SINGLE_XLSX_FORMAT"),
        (r"Delivers the final output as a single Excel workbook file with \.xlsx extension\\.?", "XLSX", "SINGLE_XLSX_FORMAT"),
        (r"(?:The )?deliverable is a PDF file\\.?", "PDF", "SINGLE_PDF_FORMAT"),
        (r"(?:The )?deliverable is provided as a PDF file\\.?", "PDF", "SINGLE_PDF_FORMAT"),
        (r"Final deliverable is provided as a PDF document \(\.pdf\)\\.?", "PDF", "SINGLE_PDF_FORMAT"),
        (r"A single PDF file is delivered\\.?", "PDF", "SINGLE_PDF_FORMAT"),
        (r"The submitted deliverable is a single PDF file \(filename ends with \.pdf\) and not a link to cloud slides or other formats\\.?", "PDF", "SINGLE_PDF_FORMAT"),
        (r"Submission is a single Word document in \.docx format\\.?", "DOCX", "SINGLE_DOCX_FORMAT"),
        (r"The deliverable is a single Microsoft Word \(\.docx\) file\\.?", "DOCX", "SINGLE_DOCX_FORMAT"),
        (r"The submission is delivered as a Microsoft Word document with a \.docx extension\\.?", "DOCX", "SINGLE_DOCX_FORMAT"),
        (r"The uploaded deliverable is a Microsoft Word document \(\.docx or \.doc\)\\.?", "DOCX", "DOCX_SUFFICIENT_FOR_WORD_FORMAT"),
        (r"Delivers a PowerPoint presentation file in \.pptx format that opens without errors\\.?", "PPTX", "SINGLE_PPTX_FORMAT"),
    ]
    for pattern, fmt, rule in single_format_patterns:
        if re.fullmatch(pattern, t, re.I):
            return _compiled(criterion, [
                {"kind": "OUTPUT_FILE_COUNT_EQ", "value": 1},
                {"kind": "FILE_FORMAT_EQ", "format": fmt},
            ], rule)

    m = re.fullmatch(r"(?:The )?submitted workbook file name is exactly ([A-Za-z0-9_.() #&+-]+\.xlsx)\\.?", t, re.I)
    if not m:
        m = re.fullmatch(r"The workbook file name exactly equals ['\"]([^'\"\\/]+\.xlsx)['\"]\\.?", t, re.I)
    if m:
        name=m.group(1)
        return _compiled(criterion, [
            {"kind": "OUTPUT_FILE_BASENAME_EXISTS", "basename": name},
            {"kind": "NAMED_FILE_FORMAT_EQ", "basename": name, "format": "XLSX"},
        ], "EXACT_XLSX_FILENAME")

    m = re.fullmatch(r"The workbook contains a worksheet named exactly ['\"]([^'\"]+)['\"] \(case-insensitive, ignoring surrounding spaces\)\\.?", t, re.I)
    if m:
        return _compiled(criterion, [
            {"kind": "UNIQUE_FORMAT_FILE", "format": "XLSX"},
            {"kind": "XLSX_SHEET_NAME_EQ_NORMALIZED", "name": m.group(1)},
        ], "EXACT_XLSX_SHEET_NAME")

    m = re.fullmatch(r"The PowerPoint contains ['\"]([^'\"]+)['\"] \(case-insensitive\) in the file name\\.?", t, re.I)
    if m:
        return _compiled(criterion, [
            {"kind": "UNIQUE_FORMAT_FILE", "format": "PPTX"},
            {"kind": "FORMAT_FILE_BASENAME_CONTAINS_CI", "format": "PPTX", "text": m.group(1)},
        ], "PPTX_FILENAME_CONTAINS")

    m = re.fullmatch(r"Submission is a single-page PDF\\.?", t, re.I)
    if m:
        return _compiled(criterion, [
            {"kind": "OUTPUT_FILE_COUNT_EQ", "value": 1},
            {"kind": "FILE_FORMAT_EQ", "format": "PDF"},
            {"kind": "PDF_PAGE_COUNT_EQ", "value": 1},
        ], "EXACT_SINGLE_PAGE_PDF")

    m = re.fullmatch(r"The PDF length is between (\d+) and (\d+) pages inclusive\\.?", t, re.I)
    if not m:
        m = re.fullmatch(r"The PDF is (\d+)[-–](\d+) pages in length, inclusive\\.?", t, re.I)
    if m:
        lo,hi=map(int,m.groups())
        if 0 < lo <= hi <= 10000:
            return _compiled(criterion, [
                {"kind": "UNIQUE_FORMAT_FILE", "format": "PDF"},
                {"kind": "PDF_PAGE_COUNT_BETWEEN", "min": lo, "max": hi},
            ], "EXACT_PDF_PAGE_COUNT_RANGE")

    m = re.fullmatch(r"The survey PDF contains exactly (\d+) pages\\.?", t, re.I)
    if m:
        n=int(m.group(1))
        if 0 < n <= 10000:
            return _compiled(criterion, [
                {"kind": "UNIQUE_FORMAT_FILE", "format": "PDF"},
                {"kind": "PDF_PAGE_COUNT_EQ", "value": n},
            ], "EXACT_UNIQUE_PDF_PAGE_COUNT")

    m = re.fullmatch(r"The zip archive contains a top-level file named ([A-Za-z0-9_.+-]+)\\.?", t, re.I)
    if m:
        return _compiled(criterion, [
            {"kind": "UNIQUE_ZIP_TOP_LEVEL_FILE_EXISTS", "basename": m.group(1)},
        ], "EXACT_ZIP_TOP_LEVEL_FILE")

    m = re.fullmatch(r"Deliverable includes a Terraform file named ([A-Za-z0-9_.+-]+)\\.?", t, re.I)
    if m:
        return _compiled(criterion, [
            {"kind": "OUTPUT_FILE_BASENAME_EXISTS", "basename": m.group(1)},
        ], "EXACT_DELIVERABLE_FILE_EXISTS")

    m = re.fullmatch(r'Deliverable includes a file named ([A-Za-z0-9_.+-]+) with file extension ["\'](\.[A-Za-z0-9]+)["\']\\.?', t, re.I)
    if m:
        name=m.group(1)
        ext=m.group(2)
        basename=name if name.lower().endswith(ext.lower()) else name+ext
        return _compiled(criterion, [
            {"kind": "OUTPUT_FILE_BASENAME_EXISTS", "basename": basename},
        ], "EXACT_DELIVERABLE_FILE_EXISTS")

    return {
        "schema": SCHEMA,
        "status": "UNRESOLVED",
        **_src(criterion),
        "reason": "OUTSIDE_BOUNDED_OBJECTIVE_STRUCTURAL_GRAMMAR",
        "terminal_authority": False,
    }

def _ooxml_kind(path: Path) -> str | None:
    try:
        with zipfile.ZipFile(path) as z:
            names = set(z.namelist())
            if "[Content_Types].xml" not in names:
                return None
            if "word/document.xml" in names:
                return "DOCX"
            if "ppt/presentation.xml" in names:
                return "PPTX"
            if "xl/workbook.xml" in names:
                return "XLSX"
    except Exception:
        return None
    return None

def _pdf_reader(path: Path):
    try:
        from pypdf import PdfReader
        return PdfReader(str(path))
    except Exception:
        return None

def _file_format(path: Path) -> str | None:
    if not path.is_file():
        return None
    if _ooxml_kind(path):
        return _ooxml_kind(path)
    try:
        with wave.open(str(path), "rb") as w:
            if w.getcomptype() == "NONE":
                return "WAV"
    except Exception:
        pass
    if _pdf_reader(path) is not None:
        return "PDF"
    return None

def _sentence_count(text: str) -> int:
    chunks = [x for x in re.split(r"(?<=[.!?])\s+", text.strip()) if x.strip()]
    return len(chunks)

def _wav_channel_peaks_dbfs(path: Path) -> list[float] | None:
    try:
        with wave.open(str(path), "rb") as w:
            if w.getcomptype() != "NONE":
                return None
            channels = w.getnchannels()
            width = w.getsampwidth()
            frames = w.readframes(w.getnframes())
    except Exception:
        return None
    if channels <= 0 or width not in {1,2,3,4}:
        return None
    vals=[0]*channels
    step=width*channels
    for off in range(0,len(frames)-step+1,step):
        for ch in range(channels):
            b=frames[off+ch*width:off+(ch+1)*width]
            if width==1:
                value=b[0]-128; full=128
            elif width==3:
                raw=int.from_bytes(b,"little",signed=False)
                if raw & 0x800000: raw-=1<<24
                value=raw; full=1<<23
            else:
                value=int.from_bytes(b,"little",signed=True); full=1<<(8*width-1)
            vals[ch]=max(vals[ch],abs(value))
    out=[]
    for peak in vals:
        if peak==0: out.append(float("-inf"))
        else: out.append(20*math.log10(peak/full))
    return out

def verify_compiled(compiled: Mapping[str, Any], *, output_paths: Sequence[str] = (), text_response: str | None = None) -> dict[str, Any]:
    if not isinstance(compiled, Mapping) or compiled.get("schema") != COMPILED_SCHEMA or compiled.get("status") != "COMPILED_SUFFICIENT_CONDITION":
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "COMPILED_PREDICATE_INVALID", "satisfied": False}
    paths=[Path(p) for p in output_paths]
    results=[]
    for pred in compiled.get("predicates", []):
        kind=pred.get("kind")
        ok=False; observed=None
        if kind=="OUTPUT_FILE_COUNT_EQ":
            observed=len(paths); ok=observed==pred["value"]
        elif kind=="FILE_FORMAT_EQ":
            observed=[_file_format(p) for p in paths]; ok=len(paths)==1 and observed[0]==pred["format"]
        elif kind=="OUTPUT_FILE_BASENAME_EXISTS":
            observed=[p.name for p in paths]; ok=pred["basename"] in observed
        elif kind=="NAMED_FILE_FORMAT_EQ":
            matches=[p for p in paths if p.name==pred["basename"]]
            observed=[_file_format(p) for p in matches]; ok=len(matches)==1 and observed[0]==pred["format"]
        elif kind=="UNIQUE_FORMAT_FILE":
            matches=[p for p in paths if _file_format(p)==pred["format"]]
            observed=[str(p) for p in matches]; ok=len(matches)==1
        elif kind=="FORMAT_FILE_BASENAME_CONTAINS_CI":
            matches=[p for p in paths if _file_format(p)==pred["format"]]
            observed=[p.name for p in matches]
            ok=len(matches)==1 and pred["text"].casefold() in matches[0].name.casefold()
        elif kind=="XLSX_SHEET_NAME_EQ_NORMALIZED":
            matches=[p for p in paths if _ooxml_kind(p)=="XLSX"]
            observed=[]
            if len(matches)==1:
                try:
                    with zipfile.ZipFile(matches[0]) as z:
                        import xml.etree.ElementTree as ET
                        root=ET.fromstring(z.read("xl/workbook.xml"))
                        ns={"m":"http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
                        observed=[x.attrib.get("name","") for x in root.findall(".//m:sheets/m:sheet",ns)]
                    want=pred["name"].strip().casefold()
                    ok=any(x.strip().casefold()==want for x in observed)
                except Exception:
                    ok=False
        elif kind=="UNIQUE_ZIP_TOP_LEVEL_FILE_EXISTS":
            zip_paths=[p for p in paths if p.is_file() and p.suffix.lower()==".zip"]
            observed=[]
            if len(zip_paths)==1:
                try:
                    with zipfile.ZipFile(zip_paths[0]) as z:
                        observed=sorted(n for n in z.namelist() if "/" not in n.rstrip("/"))
                    ok=pred["basename"] in observed
                except Exception:
                    ok=False
        elif kind=="PDF_PAGE_COUNT_EQ":
            matches=[p for p in paths if _file_format(p)=="PDF"]
            if len(matches)==1:
                reader=_pdf_reader(matches[0]); observed=None if reader is None else len(reader.pages)
                ok=observed==pred["value"]
        elif kind=="PDF_PAGE_COUNT_BETWEEN":
            if len(paths)==1:
                reader=_pdf_reader(paths[0]); observed=None if reader is None else len(reader.pages)
                ok=observed is not None and pred["min"]<=observed<=pred["max"]
        elif kind=="PPTX_SLIDE_COUNT_BETWEEN":
            if len(paths)==1 and _ooxml_kind(paths[0])=="PPTX":
                try:
                    with zipfile.ZipFile(paths[0]) as z:
                        observed=sum(1 for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n))
                    ok=pred["min"]<=observed<=pred["max"]
                except Exception: ok=False
        elif kind=="TEXT_SINGLE_PARAGRAPH":
            observed=text_response
            ok=isinstance(text_response,str) and bool(text_response.strip()) and "\n\n" not in text_response.strip()
        elif kind=="TEXT_SENTENCE_COUNT_BETWEEN":
            observed=None if not isinstance(text_response,str) else _sentence_count(text_response)
            ok=observed is not None and pred["min"]<=observed<=pred["max"]
        elif kind in {"WAV_SAMPLE_RATE_EQ","WAV_PCM_BIT_DEPTH_EQ","WAV_CHANNEL_COUNT_EQ","WAV_DURATION_TARGET_TOLERANCE"}:
            if len(paths)==1:
                try:
                    with wave.open(str(paths[0]),"rb") as w:
                        if kind=="WAV_SAMPLE_RATE_EQ": observed=w.getframerate(); ok=observed==pred["hz"]
                        elif kind=="WAV_PCM_BIT_DEPTH_EQ": observed=8*w.getsampwidth(); ok=w.getcomptype()=="NONE" and observed==pred["bits"]
                        elif kind=="WAV_CHANNEL_COUNT_EQ": observed=w.getnchannels(); ok=observed==pred["channels"]
                        else:
                            observed=w.getnframes()/w.getframerate()
                            tol=pred["seconds"]*pred["percent"]/100.0
                            ok=abs(observed-pred["seconds"])<=tol
                except Exception: ok=False
        elif kind=="WAV_PCM_UNCOMPRESSED":
            observed=_file_format(paths[0]) if len(paths)==1 else None; ok=observed=="WAV"
        elif kind in {"WAV_PEAK_DBFS_LT","WAV_PEAK_DBFS_LE"}:
            peaks=_wav_channel_peaks_dbfs(paths[0]) if len(paths)==1 else None; observed=peaks
            if peaks is not None:
                if kind=="WAV_PEAK_DBFS_LT": ok=all(x<pred["dbfs"] for x in peaks)
                else: ok=max(peaks)<=pred["dbfs"]
        elif kind=="PDF_ANY_PAGE_SELECTABLE_TEXT":
            if len(paths)==1:
                reader=_pdf_reader(paths[0])
                if reader is not None:
                    observed=[(p.extract_text() or "").strip() for p in reader.pages]
                    ok=any(bool(x) for x in observed)
        else:
            return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "UNKNOWN_PREDICATE:"+str(kind), "satisfied": False}
        results.append({"predicate":dict(pred),"satisfied":bool(ok),"observed":observed})
    satisfied=bool(results) and all(x["satisfied"] for x in results)
    return {
        "schema": SCHEMA,
        "status": "PASS" if satisfied else "NOT_SATISFIED",
        "satisfied": satisfied,
        "criterion_sha256": compiled.get("criterion_sha256"),
        "results": results,
        "scope": "BOUND_OBJECTIVE_STRUCTURAL_SUFFICIENT_CONDITIONS_ONLY",
        "whole_task_authority": False,
        "pairwise_preference_authority": False,
        "terminal_authority": False,
    }
