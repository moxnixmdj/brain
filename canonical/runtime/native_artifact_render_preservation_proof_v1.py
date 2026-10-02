"""Verifier-only render/layout preservation preflight for native artifact edits.

Uses the existing information-safe native-artifact candidate and hidden-oracle structural
proof, then independently renders source/output. DOCX/XLSX/PPTX are converted by
LibreOffice; all formats are rasterized with Poppler. The verifier requires equal page
geometry and confines visual differences to a small region consistent with the declared
text mutation.

Bounded preflight only. No whole-contract or terminal authority.
"""
from __future__ import annotations

import base64
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any, Mapping

from PIL import Image, ImageChops

from canonical.runtime import native_artifact_cross_format_candidate_v1 as candidate
from canonical.runtime import native_artifact_cross_format_proof_v1 as structural


FORMATS = ("docx", "xlsx", "pptx", "pdf")
MAX_DIFF_PIXEL_FRACTION = 0.025
MAX_DIFF_BBOX_FRACTION = 0.10
PIXEL_DELTA_THRESHOLD = 8


def _require_tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise RuntimeError("RENDER_DEPENDENCY_MISSING:" + name)
    return path


def _to_pdf(payload: bytes, fmt: str, root: Path, stem: str) -> Path:
    if fmt == "pdf":
        out = root / f"{stem}.pdf"
        out.write_bytes(payload)
        return out

    libre = _require_tool("libreoffice")
    src = root / f"{stem}.{fmt}"
    src.write_bytes(payload)
    outdir = root / (stem + "_pdf")
    outdir.mkdir()
    profile = root / (stem + "_lo_profile")
    cmd = [
        libre,
        "--headless",
        f"-env:UserInstallation=file://{profile}",
        "--convert-to", "pdf",
        "--outdir", str(outdir),
        str(src),
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=90)
    pdf = outdir / f"{stem}.pdf"
    if proc.returncode != 0 or not pdf.is_file() or pdf.stat().st_size == 0:
        raise RuntimeError(
            "LIBREOFFICE_RENDER_FAILED:"
            + str(proc.returncode)
            + ":"
            + (proc.stderr or proc.stdout)[-500:]
        )
    return pdf


def _rasterize(pdf: Path, root: Path, stem: str) -> list[Path]:
    pdftoppm = _require_tool("pdftoppm")
    prefix = root / stem
    proc = subprocess.run(
        [pdftoppm, "-png", "-r", "96", str(pdf), str(prefix)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=90,
    )
    pages = sorted(root.glob(stem + "-*.png"))
    if proc.returncode != 0 or not pages:
        raise RuntimeError("PDF_RASTER_FAILED:" + str(proc.returncode) + ":" + proc.stderr[-500:])
    return pages


def _page_diff(a: Image.Image, b: Image.Image) -> dict[str, Any]:
    if a.size != b.size:
        return {
            "pass":False,
            "reason":"PAGE_PIXEL_DIMENSIONS_CHANGED",
            "source_size":list(a.size),
            "output_size":list(b.size),
        }
    aa = a.convert("RGB")
    bb = b.convert("RGB")
    diff = ImageChops.difference(aa, bb)
    gray = diff.convert("L")
    mask = gray.point(lambda p: 255 if p > PIXEL_DELTA_THRESHOLD else 0)
    hist = mask.histogram()
    changed = hist[255]
    total = a.size[0] * a.size[1]
    pixel_fraction = changed / total if total else 1.0
    bbox = mask.getbbox()
    if bbox is None:
        bbox_fraction = 0.0
    else:
        bbox_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
        bbox_fraction = bbox_area / total if total else 1.0
    if changed == 0:
        return {
            "pass":True,
            "changed":False,
            "reason":"UNCHANGED_PAGE_PRESERVED",
            "pixel_fraction":0.0,
            "bbox_fraction":0.0,
            "bbox":None,
            "page_size":list(a.size),
        }
    localized = (
        pixel_fraction <= MAX_DIFF_PIXEL_FRACTION
        and bbox_fraction <= MAX_DIFF_BBOX_FRACTION
    )
    return {
        "pass":localized,
        "changed":True,
        "reason":"PASS" if localized else "VISUAL_DIFF_OUTSIDE_BOUNDED_EDIT_REGION",
        "pixel_fraction":pixel_fraction,
        "bbox_fraction":bbox_fraction,
        "bbox":list(bbox) if bbox else None,
        "page_size":list(a.size),
    }


def compare_renders(source: bytes, output: bytes, fmt: str) -> dict[str, Any]:
    if fmt not in FORMATS:
        return {"pass":False,"reason":"FORMAT_UNSUPPORTED"}
    try:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_pdf = _to_pdf(source, fmt, root, "source")
            output_pdf = _to_pdf(output, fmt, root, "output")
            source_pages = _rasterize(source_pdf, root, "source_page")
            output_pages = _rasterize(output_pdf, root, "output_page")
            if len(source_pages) != len(output_pages):
                return {
                    "pass":False,
                    "reason":"PAGE_COUNT_CHANGED",
                    "source_pages":len(source_pages),
                    "output_pages":len(output_pages),
                }
            rows = []
            for sp, op in zip(source_pages, output_pages):
                with Image.open(sp) as a, Image.open(op) as b:
                    rows.append(_page_diff(a, b))
            if not all(x["pass"] for x in rows):
                return {"pass":False,"reason":"PAGE_RENDER_DIFF_FAILED","pages":rows}
            changed_pages = sum(1 for x in rows if x.get("changed") is True)
            if changed_pages == 0:
                return {"pass":False,"reason":"NO_VISIBLE_EDIT","pages":rows}
            return {
                "pass":True,
                "reason":"PASS",
                "page_count":len(rows),
                "changed_page_count":changed_pages,
                "pages":rows,
                "max_pixel_fraction":max(x["pixel_fraction"] for x in rows),
                "max_bbox_fraction":max(x["bbox_fraction"] for x in rows),
            }
    except Exception as exc:
        return {"pass":False,"reason":"RENDER_EXCEPTION","error":type(exc).__name__+":"+str(exc)}


def run_case(fmt: str, seed: int) -> dict[str, Any]:
    case = structural.generate_case(fmt, seed)
    public = structural.public_task(case)
    out = candidate.solve(public)
    structural_verdict = structural.score_case(case, out)
    if not structural_verdict.get("pass"):
        return {
            "pass":False,
            "format":fmt,
            "reason":"STRUCTURAL_PREFLIGHT_FAILED:"+str(structural_verdict),
        }
    try:
        source = base64.b64decode(case["task"]["document_b64"], validate=True)
        output = base64.b64decode(out["output_b64"], validate=True)
    except Exception as exc:
        return {"pass":False,"format":fmt,"reason":"BASE64:"+type(exc).__name__}
    visual = compare_renders(source, output, fmt)
    return {
        "pass":bool(visual.get("pass")),
        "format":fmt,
        "reason":visual.get("reason"),
        "visual":visual,
        "terminal_authority":False,
        "capability_credit_delta":0,
    }


def run_grid(seeds=(1701, 1702)) -> dict[str, Any]:
    rows = [run_case(fmt, seed) for fmt in FORMATS for seed in seeds]
    passed = sum(int(x["pass"]) for x in rows)
    return {
        "schema":"PROJECT_BRAIN_NATIVE_ARTIFACT_RENDER_PRESERVATION_PREFLIGHT_RESULT_V1",
        "case_count":len(rows),
        "passed":passed,
        "failed":len(rows)-passed,
        "all_pass":passed == len(rows),
        "by_format":{
            fmt:{
                "pass":sum(int(x["pass"]) for x in rows if x["format"] == fmt),
                "total":sum(1 for x in rows if x["format"] == fmt),
            }
            for fmt in FORMATS
        },
        "failures":[x for x in rows if not x["pass"]],
        "terminal_authority":False,
        "capability_credit_delta":0,
    }
