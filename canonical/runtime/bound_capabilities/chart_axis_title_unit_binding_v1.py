"""Brain-native bounded chart axis title and unit binding V1.

Binds explicit textual axis titles/units to x/y axes using positioned OCR evidence
and deterministic geometry. The semantic core is a finite ontology; unsupported,
conflicting, or ambiguous labels fail closed.

Rotated y-axis text is handled by rotating only the left axis band and invoking
the already-pinned Tesseract dependency surface. No general-purpose model,
network call, benchmark identifier, or open-world semantic inference is used.
"""
from __future__ import annotations

import math
import pathlib
import re
import subprocess
import tempfile
from typing import Any, Mapping, Sequence

from PIL import Image

from canonical.runtime.bound_capabilities.chart_raster_scene_graph_v1 import (
    ChartSceneGraphError,
    build_scene_graph,
)
from canonical.runtime.bound_capabilities.image_ocr_tesseract import (
    verify_dependency_surface,
)
from canonical.runtime.bound_capabilities.image_ocr_tesseract_positioned import (
    parse_tsv_positioned,
)

CAPABILITY_ID = "chart.raster.axis_title_unit_binding.v1"
SCHEMA = "PROJECT_BRAIN_CHART_AXIS_TITLE_UNIT_BINDING_V1"
MODEL_DEPENDENCY_COUNT = 0
EXTERNAL_GENERAL_PURPOSE_MODEL_RUNTIME_DEPENDENCY_COUNT = 0
DONOR_GENERAL_PURPOSE_MODEL_RUNTIME_DEPENDENCY_COUNT = 0
NETWORK_DEPENDENCY_COUNT = 0

_WS = re.compile(r"\s+")
_PURE_NUMBER = re.compile(r"^[+-]?(?:\d+(?:\.\d+)?|\.\d+)(?:e[+-]?\d+)?%?$", re.I)

# Ordered most-specific first. Overlapping shorter matches are ignored.
_UNIT_SPECS: tuple[tuple[str, str, re.Pattern[str]], ...] = (
    ("RAD_PER_SECOND", "ANGULAR_FREQUENCY", re.compile(r"(?<![A-Za-z])rad\s*/\s*s(?:ec(?:ond)?s?)?(?![A-Za-z])", re.I)),
    ("METER_PER_SECOND", "SPEED", re.compile(r"(?<![A-Za-z])m\s*/\s*s(?:ec(?:ond)?s?)?(?![A-Za-z])", re.I)),
    ("KILOMETER_PER_HOUR", "SPEED", re.compile(r"(?<![A-Za-z])km\s*/\s*h(?:r|our)?s?(?![A-Za-z])", re.I)),
    ("MILES_PER_HOUR", "SPEED", re.compile(r"(?<![A-Za-z])mph(?![A-Za-z])|\bmiles?\s+per\s+hour\b", re.I)),
    ("GIGAHERTZ", "FREQUENCY", re.compile(r"(?<![A-Za-z])ghz(?![A-Za-z])", re.I)),
    ("MEGAHERTZ", "FREQUENCY", re.compile(r"(?<![A-Za-z])mhz(?![A-Za-z])", re.I)),
    ("KILOHERTZ", "FREQUENCY", re.compile(r"(?<![A-Za-z])khz(?![A-Za-z])", re.I)),
    ("HERTZ", "FREQUENCY", re.compile(r"(?<![A-Za-z])hz(?![A-Za-z])|\bhertz\b", re.I)),
    ("GIGAPASCAL", "PRESSURE", re.compile(r"(?<![A-Za-z])gpa(?![A-Za-z])", re.I)),
    ("MEGAPASCAL", "PRESSURE", re.compile(r"(?<![A-Za-z])mpa(?![A-Za-z])", re.I)),
    ("KILOPASCAL", "PRESSURE", re.compile(r"(?<![A-Za-z])kpa(?![A-Za-z])", re.I)),
    ("PASCAL", "PRESSURE", re.compile(r"(?<![A-Za-z])pa(?![A-Za-z])|\bpascals?\b", re.I)),
    ("DECIBEL", "LEVEL", re.compile(r"(?<![A-Za-z])db(?![A-Za-z])|\bdecibels?\b", re.I)),
    ("DEGREE_CELSIUS", "TEMPERATURE", re.compile(r"°\s*c\b|\bdeg(?:ree)?s?\s*c\b|\bcelsius\b", re.I)),
    ("DEGREE_FAHRENHEIT", "TEMPERATURE", re.compile(r"°\s*f\b|\bdeg(?:ree)?s?\s*f\b|\bfahrenheit\b", re.I)),
    ("KELVIN", "TEMPERATURE", re.compile(r"\bkelvin\b|\(\s*k\s*\)", re.I)),
    ("DEGREE", "ANGLE", re.compile(r"(?<!°)\bdeg(?:ree)?s?\b|°(?!\s*[cf]\b)", re.I)),
    ("PERCENT", "FRACTION", re.compile(r"%|\bpercent(?:age)?\b", re.I)),
    ("MILLIMETER", "LENGTH", re.compile(r"(?<![A-Za-z])mm(?![A-Za-z])|\bmillimeters?\b|\bmillimetres?\b", re.I)),
    ("CENTIMETER", "LENGTH", re.compile(r"(?<![A-Za-z])cm(?![A-Za-z])|\bcentimeters?\b|\bcentimetres?\b", re.I)),
    ("KILOMETER", "LENGTH", re.compile(r"(?<![A-Za-z])km(?![A-Za-z])|\bkilometers?\b|\bkilometres?\b", re.I)),
    ("METER", "LENGTH", re.compile(r"(?<![A-Za-z])m(?![A-Za-z])|\bmeters?\b|\bmetres?\b", re.I)),
    ("INCH", "LENGTH", re.compile(r"(?<![A-Za-z])in(?![A-Za-z])|\binches?\b", re.I)),
    ("FOOT", "LENGTH", re.compile(r"(?<![A-Za-z])ft(?![A-Za-z])|\bfeet\b|\bfoot\b", re.I)),
    ("KILOGRAM", "MASS", re.compile(r"(?<![A-Za-z])kg(?![A-Za-z])|\bkilograms?\b", re.I)),
    ("GRAM", "MASS", re.compile(r"(?<![A-Za-z])g(?![A-Za-z])|\bgrams?\b", re.I)),
    ("MILLISECOND", "TIME", re.compile(r"(?<![A-Za-z])ms(?![A-Za-z])|\bmilliseconds?\b", re.I)),
    ("SECOND", "TIME", re.compile(r"(?<![A-Za-z])s(?![A-Za-z])|\bseconds?\b|\bsecs?\b", re.I)),
    ("MINUTE", "TIME", re.compile(r"(?<![A-Za-z])min(?![A-Za-z])|\bminutes?\b", re.I)),
    ("HOUR", "TIME", re.compile(r"(?<![A-Za-z])h(?:r)?(?![A-Za-z])|\bhours?\b", re.I)),
    ("DAY", "TIME", re.compile(r"\bdays?\b", re.I)),
    ("WEEK", "TIME", re.compile(r"\bweeks?\b|\bwks?\b", re.I)),
    ("MONTH", "TIME", re.compile(r"\bmonths?\b|\bmos?\b", re.I)),
    ("YEAR", "TIME", re.compile(r"\byears?\b|\byrs?\b", re.I)),
    ("RPM", "ROTATIONAL_SPEED", re.compile(r"(?<![A-Za-z])rpm(?![A-Za-z])|\brevolutions?\s+per\s+minute\b", re.I)),
)

_ROLE_SPECS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("SURVIVAL_PROBABILITY", re.compile(r"\bsurvival\s+(?:probability|rate|fraction|percent(?:age)?)\b", re.I)),
    ("FREQUENCY", re.compile(r"\bfrequency\b", re.I)),
    ("ANGULAR_FREQUENCY", re.compile(r"\bangular\s+frequency\b", re.I)),
    ("TIME", re.compile(r"\btime\b", re.I)),
    ("AGE", re.compile(r"\bage\b", re.I)),
    ("HEIGHT", re.compile(r"\bheight\b|\bstature\b", re.I)),
    ("WEIGHT", re.compile(r"\bweight\b|\bmass\b", re.I)),
    ("MAGNITUDE", re.compile(r"\bmagnitude\b|\bgain\b", re.I)),
    ("PHASE", re.compile(r"\bphase\b", re.I)),
    ("TEMPERATURE", re.compile(r"\btemperature\b|\btemp\b", re.I)),
    ("PRESSURE", re.compile(r"\bpressure\b", re.I)),
    ("SPEED", re.compile(r"\bspeed\b", re.I)),
    ("VELOCITY", re.compile(r"\bvelocity\b", re.I)),
    ("DISPLACEMENT", re.compile(r"\bdisplacement\b", re.I)),
    ("STRAIN", re.compile(r"\bstrain\b", re.I)),
    ("STRESS", re.compile(r"\bstress\b", re.I)),
    ("PERCENTILE", re.compile(r"\bpercentile\b", re.I)),
    ("AMPLITUDE", re.compile(r"\bamplitude\b", re.I)),
    ("COMPOSITION", re.compile(r"\bcomposition\b", re.I)),
    ("CONCENTRATION", re.compile(r"\bconcentration\b", re.I)),
    ("FLOW", re.compile(r"\bflow\b|\bthroughput\b", re.I)),
    ("VOLTAGE", re.compile(r"\bvoltage\b", re.I)),
    ("CURRENT", re.compile(r"\bcurrent\b", re.I)),
)


class AxisTitleUnitBindingError(ValueError):
    pass


def _clean_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return _WS.sub(" ", value.strip())


def _confidence(item: Mapping[str, Any]) -> float:
    for key in ("confidence_min", "confidence_mean", "confidence"):
        raw = item.get(key)
        if raw is None:
            continue
        try:
            value = float(raw)
        except Exception:
            continue
        if math.isfinite(value):
            return value
    return -1.0


def _overlaps(span: tuple[int, int], occupied: list[tuple[int, int]]) -> bool:
    a, b = span
    return any(max(a, x) < min(b, y) for x, y in occupied)


def extract_explicit_units(text: Any) -> list[dict[str, str]]:
    s = _clean_text(text)
    if not s:
        return []
    found: list[dict[str, str]] = []
    occupied: list[tuple[int, int]] = []
    for canonical, dimension, pattern in _UNIT_SPECS:
        for match in pattern.finditer(s):
            span = match.span()
            if _overlaps(span, occupied):
                continue
            occupied.append(span)
            found.append(
                {
                    "canonical_unit": canonical,
                    "dimension": dimension,
                    "surface": match.group(0),
                }
            )
    unique: dict[tuple[str, str], dict[str, str]] = {}
    for row in found:
        unique[(row["canonical_unit"], row["dimension"])] = row
    return list(unique.values())


def infer_explicit_role(text: Any) -> str | None:
    s = _clean_text(text)
    if not s:
        return None
    hits = [name for name, pattern in _ROLE_SPECS if pattern.search(s)]
    # Prefer the more specific survival phrase over its component vocabulary.
    if "SURVIVAL_PROBABILITY" in hits:
        hits = [x for x in hits if x == "SURVIVAL_PROBABILITY"]
    if "ANGULAR_FREQUENCY" in hits:
        hits = [x for x in hits if x != "FREQUENCY"]
    unique = sorted(set(hits))
    if len(unique) > 1:
        raise AxisTitleUnitBindingError("AXIS_ROLE_CONFLICT:" + ",".join(unique))
    return unique[0] if unique else None


def parse_axis_label(text: Any) -> dict[str, Any]:
    s = _clean_text(text)
    if not s or len(s) > 160:
        raise AxisTitleUnitBindingError("AXIS_LABEL_TEXT_INVALID")
    if _PURE_NUMBER.fullmatch(s.replace(",", "")):
        raise AxisTitleUnitBindingError("AXIS_LABEL_NUMERIC_ONLY")
    role = infer_explicit_role(s)
    units = extract_explicit_units(s)
    if len(units) > 1:
        distinct = sorted({(u["canonical_unit"], u["dimension"]) for u in units})
        if len(distinct) > 1:
            raise AxisTitleUnitBindingError(
                "AXIS_UNIT_CONFLICT:" + ",".join(x[0] for x in distinct)
            )
    unit = units[0] if units else None
    if role is None and unit is None:
        raise AxisTitleUnitBindingError("AXIS_LABEL_NO_BOUNDED_SEMANTIC_CUE")
    return {
        "text": s,
        "semantic_role": role,
        "canonical_unit": None if unit is None else unit["canonical_unit"],
        "unit_dimension": None if unit is None else unit["dimension"],
        "unit_surface": None if unit is None else unit["surface"],
    }


def _candidate_rows(ocr: Mapping[str, Any], source: str) -> list[dict[str, Any]]:
    items = ocr.get("text_items") if isinstance(ocr, Mapping) else None
    if not isinstance(items, list):
        raise AxisTitleUnitBindingError("OCR_TEXT_ITEMS_INVALID")
    rows: list[dict[str, Any]] = []
    combined_parts: list[str] = []
    combined_conf: list[float] = []
    for item in items:
        if not isinstance(item, Mapping):
            continue
        text = _clean_text(item.get("text"))
        if not text:
            continue
        conf = _confidence(item)
        if conf < 25:
            continue
        if not _PURE_NUMBER.fullmatch(text.replace(",", "")):
            combined_parts.append(text)
            combined_conf.append(conf)
        try:
            parsed = parse_axis_label(text)
        except AxisTitleUnitBindingError:
            continue
        rows.append(
            {
                **parsed,
                "confidence": conf,
                "source": source,
                "evidence_kind": "OCR_LINE",
            }
        )

    # Tesseract can split title and parenthesized unit across lines. A bounded
    # combined candidate recovers that case while still requiring explicit cues.
    if 1 < len(combined_parts) <= 6:
        combined = _clean_text(" ".join(combined_parts))
        try:
            parsed = parse_axis_label(combined)
        except AxisTitleUnitBindingError:
            pass
        else:
            rows.append(
                {
                    **parsed,
                    "confidence": min(combined_conf),
                    "source": source,
                    "evidence_kind": "OCR_COMBINED_NONNUMERIC_LINES",
                }
            )
    return rows


def _score_candidate(row: Mapping[str, Any]) -> float:
    score = max(0.0, min(100.0, float(row.get("confidence", 0)))) / 100.0
    if row.get("semantic_role") is not None:
        score += 5.0
    if row.get("canonical_unit") is not None:
        score += 4.0
    score += min(len(str(row.get("text") or "")), 60) / 200.0
    if row.get("evidence_kind") == "OCR_LINE":
        score += 0.10
    return score


def select_axis_binding(
    candidates: Sequence[Mapping[str, Any]],
    *,
    ambiguity_margin: float = 0.35,
) -> dict[str, Any]:
    if not isinstance(candidates, Sequence) or isinstance(candidates, (str, bytes)):
        raise AxisTitleUnitBindingError("AXIS_CANDIDATES_INVALID")
    dedup: dict[tuple[str, str | None, str | None], dict[str, Any]] = {}
    for raw in candidates:
        if not isinstance(raw, Mapping):
            continue
        text = _clean_text(raw.get("text"))
        if not text:
            continue
        try:
            parsed = parse_axis_label(text)
        except AxisTitleUnitBindingError:
            continue
        row = {
            **parsed,
            "confidence": _confidence(raw),
            "source": str(raw.get("source") or "UNKNOWN"),
            "evidence_kind": str(raw.get("evidence_kind") or "SUPPLIED_CANDIDATE"),
        }
        key = (
            text.casefold(),
            row["semantic_role"],
            row["canonical_unit"],
        )
        old = dedup.get(key)
        if old is None or _score_candidate(row) > _score_candidate(old):
            dedup[key] = row
    ranked = sorted(
        dedup.values(),
        key=lambda x: (-_score_candidate(x), str(x["text"]).casefold(), str(x["source"])),
    )
    if not ranked:
        return {
            "status": "OPEN__NO_BOUNDED_AXIS_TITLE_UNIT_BINDING",
            "pass": False,
            "reason": "NO_ELIGIBLE_AXIS_TITLE_UNIT_CANDIDATE",
            "candidates": [],
        }
    best = ranked[0]
    if len(ranked) > 1:
        delta = _score_candidate(best) - _score_candidate(ranked[1])
        if delta <= float(ambiguity_margin):
            # Same semantics expressed with slightly different OCR text is still
            # ambiguous evidence, not permission to guess which title is real.
            return {
                "status": "FAIL_CLOSED__AMBIGUOUS_AXIS_TITLE_UNIT_BINDING",
                "pass": False,
                "reason": "AMBIGUOUS_AXIS_TITLE_UNIT_CANDIDATES",
                "candidates": ranked,
            }
    return {
        "status": "PASS__BOUNDED_AXIS_TITLE_UNIT_BINDING",
        "pass": True,
        "binding": best,
        "candidate_count": len(ranked),
        "candidates": ranked,
    }


def bind_axis_candidates(
    x_candidates: Sequence[Mapping[str, Any]],
    y_candidates: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    x = select_axis_binding(x_candidates)
    y = select_axis_binding(y_candidates)
    bound = int(x.get("pass") is True) + int(y.get("pass") is True)
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__BOTH_AXIS_TITLE_UNIT_BINDINGS"
            if bound == 2
            else "PASS__PARTIAL_AXIS_TITLE_UNIT_BINDING"
            if bound == 1
            else "FAIL_CLOSED__NO_AXIS_TITLE_UNIT_BINDING"
        ),
        "pass": bound > 0,
        "bound_axis_count": bound,
        "x_axis": x,
        "y_axis": y,
        "semantic_authority": "EXPLICIT_AXIS_TITLE_AND_UNIT_BINDING_ONLY",
        "domain_semantic_authority": False,
        "benchmark_score_authority": False,
        "cognition_dependency_class": "MODEL_INDEPENDENT",
        "model_dependency_count": 0,
        "external_general_purpose_model_runtime_dependency_count": 0,
        "donor_general_purpose_model_runtime_dependency_count": 0,
        "network_dependency_count": 0,
        "incremental_spend_usd": 0,
    }


def _ocr_pil(image: Image.Image, *, source: str) -> list[dict[str, Any]]:
    verify_dependency_surface()
    rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="brain-chart-axis-") as td:
        path = pathlib.Path(td) / "axis.png"
        image.save(path)
        for psm in ("6", "11"):
            proc = subprocess.run(
                ["tesseract", str(path), "stdout", "-l", "eng", "--psm", psm, "tsv"],
                text=True,
                capture_output=True,
                timeout=90,
            )
            if proc.returncode != 0:
                continue
            try:
                parsed = parse_tsv_positioned(proc.stdout)
            except RuntimeError:
                continue
            rows.extend(_candidate_rows(parsed, source + ":PSM" + psm))
    return rows


def bind_axis_titles_and_units(image_path: str | pathlib.Path) -> dict[str, Any]:
    src = pathlib.Path(image_path)
    if not src.is_file():
        raise AxisTitleUnitBindingError("IMAGE_NOT_FOUND")
    try:
        scene = build_scene_graph(src)
    except ChartSceneGraphError as exc:
        raise AxisTitleUnitBindingError("PLOT_BOX_NOT_BOUND:" + str(exc)) from exc
    left, top, right, bottom = [int(round(float(v))) for v in scene["plot_box"]]
    with Image.open(src) as raw:
        image = raw.convert("RGB")
    w, h = image.size

    # Bottom band includes tick labels plus the x-axis title. Numeric-only OCR
    # rows are rejected by the semantic core.
    xb0 = max(0, left - int(0.06 * w))
    xb1 = min(w, right + int(0.06 * w) + 1)
    yb0 = min(h - 1, max(0, bottom + 1))
    x_band = image.crop((xb0, yb0, xb1, h))

    # Left band captures the conventional y-axis title. Rotate both directions;
    # only one orientation should yield a uniquely strong semantic candidate.
    xl1 = min(w, max(1, left))
    # Use full image height for the left axis band. Axis titles commonly
    # extend above/below the plot rectangle; x-position already isolates the
    # y-axis side, while vertical clipping can silently destroy leading/trailing
    # title tokens after rotation.
    yl0 = 0
    yl1 = h
    y_band = image.crop((0, yl0, xl1, yl1))

    x_candidates = _ocr_pil(x_band, source="BOTTOM_BAND")
    y_candidates = []
    y_candidates.extend(_ocr_pil(y_band.rotate(90, expand=True), source="LEFT_BAND_ROTATE_90"))
    y_candidates.extend(_ocr_pil(y_band.rotate(270, expand=True), source="LEFT_BAND_ROTATE_270"))

    out = bind_axis_candidates(x_candidates, y_candidates)
    return {
        **out,
        "capability_id": CAPABILITY_ID,
        "source_path": str(src),
        "image_size": [w, h],
        "plot_box": [left, top, right, bottom],
        "x_candidate_count": len(x_candidates),
        "y_candidate_count": len(y_candidates),
        "hard_nonclaims": [
            "NO_OPEN_WORLD_AXIS_SEMANTICS",
            "NO_UNIT_CONVERSION_AUTHORITY",
            "NO_DOMAIN_SEMANTIC_AUTHORITY",
            "NO_BENCHMARK_SCORE_AUTHORITY",
        ],
    }


def run(args: dict[str, Any], root: Any) -> dict[str, Any]:
    base = pathlib.Path(root).resolve()
    src = (base / str(args.get("path") or "")).resolve()
    if src == base or base not in src.parents:
        raise AxisTitleUnitBindingError("IMAGE_PATH_OUTSIDE_REPOSITORY")
    out = bind_axis_titles_and_units(src)
    return {
        **out,
        "source_path": str(src.relative_to(base)).replace("\\", "/"),
    }
