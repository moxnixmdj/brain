"""Fresh-goal EXECUTION families, wave 6 (heartbeat).  Same contract as waves 2-5: fresh
inputs, one plain sentence, an oracle that judges the real artifact with the standard library.

  CHART_RASTER_READERS                chart.raster.scene_graph.v1
                                      a synthetic chart drawn from scratch every instance
                                      (PIL in the GENERATOR only); the oracle judges the
                                      returned scene graph against the exact geometry that
                                      was drawn: plot box, axis fits over the stated
                                      (pixel, value) tick pairs, the curve's per-column
                                      median rows, and both saturated components.  Scope is
                                      the non-OCR raster reader; the OCR-bound chart caps
                                      (curve value/x-at-y, legend style, axis title, direct
                                      label rank) need the tesseract binary this sandbox
                                      cannot install and are still unmeasured HERE.
  KNOWLEDGE_FETCH_ASSESS_ASSERT        knowledge.json.fetch.external / knowledge.consistency.assess /
                                      knowledge.status.assert - real https fetches of immutable
                                      versioned pypi.org metadata (K1 knowledge, allowlisted
                                      host), evidence records built from real bytes, and the
                                      assessment status recomputed independently by the oracle
                                      from the evidence files.
  HTTP_JSON_FETCH__PYPI_AUDIT__WEB_RELEASE
                                      http.json.fetch_from_state (URL named inside repository
                                      state), pypi.provenance.audit_live_artifact (live
                                      metadata + real wheel download, sha256 re-computed by the
                                      oracle), web.release.verify.independent_http (claim file
                                      against the live python/cpython releases atom feed).

Every network fetch is timeout-bounded; a fetch that fails during generation leaves the
fixture absent and the oracle reports that exact cause instead of crashing the run.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import math
import random
import re
import urllib.request
from pathlib import Path
from typing import Any, Callable

from execution_guard.live_solver_end_to_end_measurement_v1 import Case, ROOT, _rel, _word
from execution_guard.live_solver_families_v2 import _passed

_UA = {"User-Agent": "ProjectBrain-HeartbeatWave6/1"}
_ATOM_URL = "https://github.com/python/cpython/releases.atom"
# immutable versioned pypi metadata: (project, version) - every URL below was live-verified
_PACKAGES = (("six", "1.17.0"), ("idna", "3.10"), ("attrs", "25.2.0"))


def _fetch(url: str, max_bytes: int = 4_000_000, tries: int = 3) -> bytes:
    last: Exception | None = None
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers=_UA)
            with urllib.request.urlopen(req, timeout=25) as resp:
                return resp.read(max_bytes)
        except Exception as exc:  # noqa: BLE001 - network truth, retried then surfaced
            last = exc
    raise RuntimeError(f"WAVE6_FETCH_FAILED:{type(last).__name__}:{last}")


def _cap_result(result: dict[str, Any], *, capability_id: str | None = None,
                action_type: str | None = None) -> dict[str, Any] | None:
    """The capability's own result dict from either execution path of solve()."""
    for row in result.get("execution") or []:
        if isinstance(row, dict) and capability_id and row.get("capability_id") == capability_id:
            inner = row.get("result")
            if isinstance(inner, dict):
                return inner
    ctl = result.get("controller_execution") or {}
    if isinstance(ctl, dict):
        for step in ctl.get("trace") or []:
            plan = (step or {}).get("plan") or {}
            if action_type and plan.get("type") == action_type and isinstance(step.get("result"), dict):
                return step["result"]
            if capability_id and plan.get("args", {}).get("capability_id") == capability_id \
                    and isinstance(step.get("result"), dict):
                return step["result"]
    return None


def _failed(result: dict[str, Any]) -> str | None:
    if _passed(result):
        return None
    return "runtime did not pass: " + str(result.get("failure_class") or result.get("status"))


# ------------------------------------------------------------------ chart scene graph

def _y_value_at_row(row: float, t: int, b: int, v_top: float, v_bottom: float, log: bool) -> float:
    frac = (b - row) / float(b - t)
    if log:
        lv = math.log10(v_bottom) + frac * (math.log10(v_top) - math.log10(v_bottom))
        return 10.0 ** lv
    return v_bottom + frac * (v_top - v_bottom)


def _row_for_value(v: float, t: int, b: int, v_top: float, v_bottom: float, log: bool) -> float:
    if log:
        span = math.log10(v_top) - math.log10(v_bottom)
        frac = (math.log10(v) - math.log10(v_bottom)) / span
    else:
        frac = (v - v_bottom) / (v_top - v_bottom)
    return b - frac * (b - t)


def _fit_line(points: list[list[float]]) -> tuple[float, float]:
    """Exact ordinary-least-squares y = a*x + b over the (pixel, value) pairs."""
    n = len(points)
    mx = sum(p for p, _ in points) / n
    mv = sum(v for _, v in points) / n
    den = sum((p - mx) ** 2 for p, _ in points)
    a = sum((p - mx) * (v - mv) for p, v in points) / den
    return a, mv - a * mx


def gen_chart_raster_readers(rng: random.Random, work: Path, i: int) -> Case:
    from PIL import Image, ImageDraw

    work.mkdir(parents=True, exist_ok=True)
    w, h = 360, 260
    left = rng.randint(50, 70)
    right = rng.randint(left + 95, 335)
    top = rng.randint(24, 40)
    bottom = rng.randint(max(top + 70, 120), 214)

    # y axis: LINEAR with a modest span, or LOG10 with a >100x geometric span (so the
    # log fit is exact and the linear fit is decisively worse - the tool must choose).
    log_mode = rng.random() < 0.4
    if log_mode:
        decades = rng.randint(2, 4)
        v_bottom = float(10 ** rng.randint(0, 3))
        v_top = v_bottom * (10 ** decades)
        n_ticks = 3
        rows_y = [top + (bottom - top) * k // (n_ticks - 1) for k in range(n_ticks)]
        y_ticks = [[r, _y_value_at_row(r, top, bottom, v_top, v_bottom, True)] for r in rows_y]
        y_ticks = [[r, round(v, 6)] for r, v in y_ticks]
    else:
        step = rng.randint(4, 12)
        v_bottom = float(rng.randint(-30, 30))
        v_top = v_bottom + step * 3
        n_ticks = 3
        rows_y = [top + (bottom - top) * k // (n_ticks - 1) for k in range(n_ticks)]
        y_ticks = [[r, v_bottom + step * 3 * (bottom - r) / (bottom - top)] for r in rows_y]
        y_ticks = [[r, round(v, 6)] for r, v in y_ticks]

    # x axis: colinear linear ticks, increasing values
    n_x = rng.randint(3, 4)
    cols_x = [left + (right - left) * k // (n_x - 1) for k in range(n_x)]
    x0 = rng.randint(-20, 20)
    x_step = rng.randint(3, 9)
    x_ticks = [[c, x0 + x_step * k] for k, c in enumerate(cols_x)]

    # curve: LINEAR y -> straight line in the bottom half of the box; LOG y -> geometric.
    a_curve = rng.choice([0.3, 0.5, 0.8, -0.3, -0.5])
    b_frac = rng.uniform(0.05, 0.40)   # start in the BOTTOM half: rows >= mid box
    xs_all = [c for c in range(left + 1, right)]

    def curve_value(px: int) -> float:
        t = (px - left) / float(right - left)
        if log_mode:
            # geometric between v_bottom and sqrt(v_bottom*v_top): stays in the low half
            v_mid = math.sqrt(v_bottom * v_top)
            return v_bottom * (v_mid / v_bottom) ** t
        span = (v_top - v_bottom)
        v = v_bottom + span * (b_frac + a_curve * 0.35 * t)
        return min(max(v, v_bottom + 1e-9), v_bottom + 0.55 * span)

    im = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(im)
    d.line((left, top, left, bottom), fill="black", width=2)
    d.line((left, bottom, right, bottom), fill="black", width=2)
    swatch = (right - 60, top + 6, right - 44, top + 22)
    d.rectangle(swatch, fill=(30, 80, 220))
    red = (230, 30, 30)
    expected_rows: dict[int, int] = {}
    for px in xs_all:
        v = curve_value(px)
        row = int(round(_row_for_value(v, top, bottom, y_ticks[0][1], y_ticks[-1][1], log_mode)))
        row = min(max(row, top + 1), bottom - 1)
        expected_rows[px] = row
        d.line((px, row, px, row), fill=red, width=2)
    chart = work / f"chart_{i}_{_word(rng, 4)}.png"
    im.save(chart)

    x_pairs = [[int(p), int(v)] for p, v in x_ticks]
    y_pairs = [[int(p), float(v)] for p, v in y_ticks]
    goal = rng.choice([
        f"Read the raster scene graph of the chart image {_rel(chart)} "
        f"with x ticks {json.dumps(x_pairs)} and y ticks {json.dumps(y_pairs)}",
        f"Analyse the chart image {_rel(chart)} by reading its raster scene graph, "
        f"with x axis ticks {json.dumps(x_pairs)} and y axis ticks {json.dumps(y_pairs)}",
        f"Read the raster scene graph of {_rel(chart)}, calibrating the axes with "
        f"x ticks {json.dumps(x_pairs)} and y ticks {json.dumps(y_pairs)}",
        f"Given the chart image {_rel(chart)}, read its raster scene graph using "
        f"x ticks {json.dumps(x_pairs)} and y ticks {json.dumps(y_pairs)}",
        f"Produce the raster scene graph of the chart image {_rel(chart)} with "
        f"x ticks {json.dumps(x_pairs)} and y ticks {json.dumps(y_pairs)}",
    ])

    exp_x = _fit_line([[float(p), float(v)] for p, v in x_pairs])
    exp_y = _fit_line(
        [[float(p), math.log10(float(v))] for p, v in y_pairs] if log_mode
        else [[float(p), float(v)] for p, v in y_pairs]
    )
    exp_scale = "LOG10" if log_mode else "LINEAR"

    def oracle(result: dict[str, Any]) -> tuple[bool, str]:
        why = _failed(result)
        if why:
            return False, why
        if result.get("compiled_capability_id") != "chart.raster.scene_graph.v1":
            return False, "wrong capability: " + str(result.get("compiled_capability_id"))
        scene = _cap_result(result, capability_id="chart.raster.scene_graph.v1")
        if not isinstance(scene, dict):
            return False, "scene graph result missing"
        if scene.get("schema") != "PROJECT_BRAIN_CHART_RASTER_SCENE_GRAPH_V1":
            return False, "scene schema: " + str(scene.get("schema"))
        if scene.get("status") != "PASS__RASTER_SCENE_GRAPH" or scene.get("pass") is not True:
            return False, "scene not PASS: " + str(scene.get("status"))
        box = scene.get("plot_box") or []
        if len(box) != 4:
            return False, "plot_box malformed"
        for got, exp, name in zip(box, (left, top, right, bottom), "ltrb"):
            if abs(int(got) - int(exp)) > 2:
                return False, f"plot_box {name}: drew {exp} got {got} (tol 2 = line width)"
        if scene.get("axis_errors"):
            return False, "axis_errors: " + json.dumps(scene["axis_errors"])[:160]
        axes = scene.get("axes") or {}
        for key, exp_fit in (("x", exp_x), ("y", exp_y)):
            axis = axes.get(key) or {}
            if axis.get("scale") != exp_scale and key == "y":
                return False, f"y scale: expected {exp_scale} got {axis.get('scale')}"
            if key == "x" and axis.get("scale") != "LINEAR":
                return False, f"x scale must be LINEAR, got {axis.get('scale')}"
            got_fit = axis.get("transformed_value_from_pixel") or []
            if len(got_fit) != 2:
                return False, f"{key} transform missing"
            if not math.isclose(float(got_fit[0]), exp_fit[0], rel_tol=1e-9, abs_tol=1e-9) or \
               not math.isclose(float(got_fit[1]), exp_fit[1], rel_tol=1e-9, abs_tol=1e-9):
                return False, f"{key} transform: expected {exp_fit} got {tuple(float(g) for g in got_fit)}"
            if axis.get("tick_count") != len(x_pairs if key == "x" else y_pairs):
                return False, f"{key} tick_count wrong"
        traces = scene.get("color_polylines") or []
        red_trace = None
        for tr in traces:
            bucket = tr.get("color_bucket") or []
            if len(bucket) == 3 and abs(bucket[0] - 216) <= 48 and bucket[1] < 72 and bucket[2] < 72:
                red_trace = tr
                break
        if red_trace is None:
            return False, "red curve trace not found"
        if red_trace.get("x_range") not in ([left + 1, right - 1], [left, right],
                                             [left, right - 1], [left + 1, right]):
            return False, "curve x_range: " + json.dumps(red_trace.get("x_range"))
        points = red_trace.get("points") or []
        if len(points) < (right - left - 3):
            return False, f"curve too short: {len(points)} columns"
        checked = 0
        for px, row in points:
            exp_row = expected_rows.get(int(px))
            if exp_row is None:
                continue
            checked += 1
            if abs(float(row) - exp_row) > 2:
                return False, f"curve row at px {px}: drew {exp_row} got {row} (tol 2 = line width)"
        if checked < (right - left - 5):
            return False, f"curve columns checked {checked}"
        comps = scene.get("saturated_components") or []
        blue = [c for c in comps
                if len(c.get("bbox") or []) == 4
                and abs(c["bbox"][0] - swatch[0]) <= 3 and abs(c["bbox"][1] - swatch[1]) <= 3
                and abs(c["bbox"][2] - swatch[2]) <= 3 and abs(c["bbox"][3] - swatch[3]) <= 3
                and (c.get("color_bucket") or [0])[0] < 72 and (c.get("color_bucket") or [0, 0, 999])[2] > 150]
        if not blue:
            return False, "blue legend swatch component not found at its drawn box"
        return True, ""

    return Case("CHART_RASTER_READERS", goal, oracle, True, [])


# ------------------------------------------------------------ knowledge fetch/assess/assert

def _evidence_record(url: str, json_path: list[Any]) -> dict[str, Any]:
    raw = _fetch(url, 2_000_000)
    payload = json.loads(raw.decode("utf-8"))
    selected: Any = payload
    for part in json_path:
        selected = selected[str(part)] if isinstance(selected, dict) else selected[int(part)]
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
    return {
        "schema": "PROJECT_BRAIN_KNOWLEDGE_EVIDENCE_V1",
        "source_url": url,
        "final_url": url,
        "http_status": 200,
        "retrieved_at_utc": now,
        "body_sha256": hashlib.sha256(raw).hexdigest(),
        "json_path": list(json_path),
        "value": selected,
        "source_type": "authoritative_external_json",
    }


def _expected_assessment(records: list[dict[str, Any]], max_age_s: float,
                         now: datetime.datetime) -> dict[str, Any]:
    """The assess contract, re-implemented independently from the evidence files."""
    fresh_rows = []
    for rec in records:
        ts = datetime.datetime.fromisoformat(rec["retrieved_at_utc"].replace("Z", "+00:00"))
        age = max(0.0, (now - ts).total_seconds())
        fresh_rows.append((rec, age <= float(max_age_s), age))
    fresh = [r for r, ok, _ in fresh_rows if ok]
    identities = {r["source_url"] + "|" + json.dumps(r["json_path"]) for r in fresh}
    values = {json.dumps(r["value"], sort_keys=True, separators=(",", ":")) for r in fresh}
    if records and not fresh:
        status = "STALE"
    elif len(fresh) < 2:
        status = "INSUFFICIENT"
    elif len(values) > 1:
        status = "CONFLICTED"
    elif len(identities) < 2:
        status = "INSUFFICIENT"
    else:
        status = "SUPPORTED"
    return {
        "status": status,
        "evidence_count": len(records),
        "fresh_evidence_count": len(fresh),
        "distinct_fresh_values": len(values),
        "distinct_fresh_source_identities": len(identities),
    }


def gen_knowledge_fetch_assess_assert(rng: random.Random, work: Path, i: int) -> Case:
    work.mkdir(parents=True, exist_ok=True)
    mode = rng.choice(["fetch", "fetch", "assess", "assert"])
    out = work / f"know_{i}_{_word(rng, 4)}.json"

    if mode == "fetch":
        project, version = rng.choice(_PACKAGES)
        url = f"https://pypi.org/pypi/{project}/{version}/json"
        selector = rng.choice([[], ["info", "version"], ["info", "name"]])
        shown = json.dumps(selector)
        goal = rng.choice([
            f"Fetch the external knowledge JSON from {url} with json path {shown} "
            f"as authoritative true and save it to {_rel(out)}",
            f"Retrieve the external knowledge JSON at {url} with json path {shown}, "
            f"treat it as authoritative true, and save the evidence to {_rel(out)}",
            f"Download the knowledge JSON at {url} with json path {shown} as authoritative true "
            f"and write the evidence record to {_rel(out)}",
            f"Collect the external knowledge JSON document {url} with json path {shown} "
            f"as authoritative true and store it in {_rel(out)}",
        ])
        expected_value: Any = _SENTINEL
        try:
            payload = json.loads(_fetch(url, 2_000_000))
            sel: Any = payload
            for part in selector:
                sel = sel[str(part)]
            expected_value = sel
            expected_sha = hashlib.sha256(_fetch(url, 2_000_000)).hexdigest()
        except Exception:
            expected_value, expected_sha = _SENTINEL, None

        def oracle(result: dict[str, Any]) -> tuple[bool, str]:
            why = _failed(result)
            if why:
                return False, why
            if result.get("compiled_capability_id") != "knowledge.json.fetch.external":
                return False, "wrong capability: " + str(result.get("compiled_capability_id"))
            if not out.is_file():
                return False, "knowledge evidence file not written"
            rec = json.loads(out.read_text(encoding="utf-8"))
            if rec.get("schema") != "PROJECT_BRAIN_KNOWLEDGE_EVIDENCE_V1":
                return False, "evidence schema: " + str(rec.get("schema"))
            if rec.get("source_url") != url or rec.get("http_status") != 200:
                return False, "source_url/http_status wrong"
            if rec.get("json_path") != selector:
                return False, "json_path: expected " + json.dumps(selector)
            if rec.get("source_type") != "authoritative_external_json":
                return False, "source_type: " + str(rec.get("source_type"))
            if expected_sha is not None and rec.get("body_sha256") != expected_sha:
                return False, "body_sha256 mismatch against an independent fetch of the same immutable URL"
            if expected_value is not _SENTINEL and rec.get("value") != expected_value:
                return False, "selected value mismatch against an independent selection"
            try:
                datetime.datetime.fromisoformat(str(rec.get("retrieved_at_utc")).replace("Z", "+00:00"))
            except ValueError:
                return False, "retrieved_at_utc not a timestamp"
            return True, ""

        return Case("KNOWLEDGE_FETCH_ASSESS_ASSERT", goal, oracle, True, [out])

    # assess / assert: two REAL evidence records from two DIFFERENT immutable sources
    (p1, v1), (p2, v2) = rng.sample(list(_PACKAGES), 2)
    paths = [[], ["info", "version"]]
    chosen = rng.choice(paths)
    e1_path = work / f"evidence_{i}_{_word(rng, 4)}.json"
    e2_path = work / f"evidence_{i}_{_word(rng, 4)}_b.json"
    records: list[dict[str, Any]] = []
    network_ok = True
    try:
        records = [
            _evidence_record(f"https://pypi.org/pypi/{p1}/{v1}/json", chosen),
            _evidence_record(f"https://pypi.org/pypi/{p2}/{v2}/json", chosen),
        ]
    except Exception:
        network_ok = False
    if network_ok:
        e1_path.write_text(json.dumps(records[0]), encoding="utf-8")
        e2_path.write_text(json.dumps(records[1]), encoding="utf-8")
    max_age = 600
    expected = _expected_assessment(records, max_age, datetime.datetime.now(datetime.timezone.utc)) if network_ok else None

    if mode == "assess":
        assess_path = work / f"assessment_{i}_{_word(rng, 4)}.json"
        goal = rng.choice([
            f"Assess knowledge consistency on {_rel(e1_path)} and {_rel(e2_path)} "
            f"with max age seconds {max_age} and save it to {_rel(assess_path)}",
            f"Assess the knowledge consistency of {_rel(e1_path)} and {_rel(e2_path)} "
            f"with max age seconds {max_age} and write the assessment to {_rel(assess_path)}",
            f"Check whether the knowledge in {_rel(e1_path)} and {_rel(e2_path)} is "
            f"consistent, with max age seconds {max_age}, and save the result to {_rel(assess_path)}",
            f"Assess knowledge consistency on {_rel(e1_path)} and {_rel(e2_path)} "
            f"with max age seconds {max_age} and save the assessment to {_rel(assess_path)}",
        ])

        def oracle(result: dict[str, Any]) -> tuple[bool, str]:
            why = _failed(result)
            if why:
                return False, why
            if result.get("compiled_capability_id") != "knowledge.consistency.assess":
                return False, "wrong capability: " + str(result.get("compiled_capability_id"))
            if not network_ok or expected is None:
                return False, "FIXTURE_NETWORK_FAILURE: evidence could not be fetched"
            if not assess_path.is_file():
                return False, "assessment file not written"
            got = json.loads(assess_path.read_text(encoding="utf-8"))
            if got.get("schema") != "PROJECT_BRAIN_KNOWLEDGE_ASSESSMENT_V1":
                return False, "assessment schema: " + str(got.get("schema"))
            for key in ("status", "evidence_count", "fresh_evidence_count",
                        "distinct_fresh_values", "distinct_fresh_source_identities"):
                if got.get(key) != expected[key]:
                    return False, f"{key}: expected {expected[key]!r} got {got.get(key)!r}"
            if got.get("invalid"):
                return False, "invalid evidence rows: " + json.dumps(got["invalid"])[:160]
            return True, ""

        return Case("KNOWLEDGE_FETCH_ASSESS_ASSERT", goal, oracle, True, [assess_path])

    # assert: the expected status is derived from the SAME contract over the SAME records
    assess_path = work / f"assessment_{i}_{_word(rng, 4)}.json"
    if network_ok and expected is not None:
        assessment = {
            "schema": "PROJECT_BRAIN_KNOWLEDGE_ASSESSMENT_V1",
            **expected,
            "records": records,
            "invalid": [],
            "assessed_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        assess_path.write_text(json.dumps(assessment), encoding="utf-8")
    status = (expected or {"status": "SUPPORTED"})["status"]
    goal = rng.choice([
        f'Assert the knowledge status on {_rel(assess_path)} with expected status "{status}"',
        f'Verify the knowledge status on {_rel(assess_path)} with expected status "{status}"',
        f'Assert that the assessment {_rel(assess_path)} has the expected status "{status}"',
        f'Check the expected status "{status}" of the knowledge assessment {_rel(assess_path)}',
    ])

    def oracle(result: dict[str, Any]) -> tuple[bool, str]:
        why = _failed(result)
        if why:
            return False, why
        if result.get("compiled_capability_id") != "knowledge.status.assert":
            return False, "wrong capability: " + str(result.get("compiled_capability_id"))
        if not network_ok or expected is None:
            return False, "FIXTURE_NETWORK_FAILURE: evidence could not be fetched"
        row = _cap_result(result, action_type="assert_knowledge_status")
        if not isinstance(row, dict):
            return False, "assert result missing from controller trace"
        if row.get("verified") is not True:
            return False, "assert verified False: " + json.dumps(row)[:200]
        if row.get("observed_status") != status or row.get("expected_status") != status:
            return False, "status mismatch: " + json.dumps(row)[:200]
        return True, ""

    return Case("KNOWLEDGE_FETCH_ASSESS_ASSERT", goal, oracle, True, [])


_SENTINEL = object()


# --------------------------------------- http state fetch / pypi audit / web release verify

def gen_http_pypi_web(rng: random.Random, work: Path, i: int) -> Case:
    work.mkdir(parents=True, exist_ok=True)
    mode = rng.choice(["http", "audit", "audit", "web"])
    project, version = rng.choice(_PACKAGES)
    url = f"https://pypi.org/pypi/{project}/{version}/json"

    if mode == "http":
        key = "release_url" if rng.random() < 0.5 else "metadata_endpoint"
        src = work / f"state_{i}_{_word(rng, 4)}.json"
        nested = rng.random() < 0.5
        payload = {key: url} if not nested else {"sources": [{key: url}]}
        src.write_text(json.dumps(payload), encoding="utf-8")
        out = work / f"http_{i}_{_word(rng, 4)}.json"
        goal = rng.choice([
            f"Fetch the HTTP JSON live metadata from the source json {_rel(src)} "
            f"with url key \"{key}\" and save it to {_rel(out)}",
            f"Fetch the HTTP JSON live metadata from the state json {_rel(src)} "
            f"with url key \"{key}\" and save it to {_rel(out)}",
            f"Read the URL stored under the url key \"{key}\" in the source json {_rel(src)}, "
            f"fetch it over HTTP, and save the response to {_rel(out)}",
            f"Fetch the JSON document whose URL is under the url key \"{key}\" in {_rel(src)} "
            f"and write it to {_rel(out)}",
        ])

        def oracle(result: dict[str, Any]) -> tuple[bool, str]:
            why = _failed(result)
            if why:
                return False, why
            if result.get("compiled_capability_id") != "http.json.fetch_from_state":
                return False, "wrong capability: " + str(result.get("compiled_capability_id"))
            if not out.is_file():
                return False, "fetched JSON not written"
            try:
                fresh = _fetch(url, 2_000_000)
            except Exception as exc:
                return False, f"oracle fetch failed: {exc}"
            got = out.read_bytes()
            if hashlib.sha256(got).hexdigest() != hashlib.sha256(fresh).hexdigest():
                return False, "written bytes differ from an independent fetch of the same immutable URL"
            if json.loads(got.decode("utf-8")) is None:
                return False, "written bytes are not JSON"
            row = _cap_result(result, capability_id="http.json.fetch_from_state")
            if not isinstance(row, dict) or row.get("output_verified") is not True:
                return False, "http fetch output_verified not True"
            if row.get("url_key") != key or row.get("requested_url") != url:
                return False, "url_key/requested_url wrong: " + json.dumps({k: row.get(k) for k in ("url_key", "requested_url")})
            return True, ""

        return Case("HTTP_JSON_FETCH__PYPI_AUDIT__WEB_RELEASE", goal, oracle, True, [out])

    if mode == "audit":
        meta_path = work / f"meta_{i}_{_word(rng, 4)}.json"
        sel_path = work / f"sel_{i}_{_word(rng, 4)}.json"
        rep_path = work / f"rep_{i}_{_word(rng, 4)}.json"
        wheel_meta: dict[str, Any] | None = None
        try:
            meta = json.loads(_fetch(url, 3_000_000))
            wheels = [u for u in meta.get("urls") or [] if str(u.get("filename") or "").endswith(".whl")]
            if not wheels:
                raise RuntimeError("WAVE6_NO_WHEEL_IN_METADATA")
            wheel_meta = wheels[0]
            meta_path.write_text(json.dumps(meta), encoding="utf-8")
            sel_path.write_text(json.dumps({
                "id": f"cap.{project}",
                "record": {"source": {
                    "type": "pypi",
                    "project": project,
                    "version": version,
                    "wheel_filename": wheel_meta["filename"],
                    "wheel_sha256": wheel_meta["digests"]["sha256"],
                    "metadata_url": url,
                }},
            }), encoding="utf-8")
        except Exception:
            wheel_meta = None

        goal = rng.choice([
            f"Audit the pypi wheel artifact provenance and sha256 download hash on {_rel(meta_path)} "
            f"with selection {_rel(sel_path)} and save the report to {_rel(rep_path)}",
            f"Audit the pypi wheel artifact provenance and sha256 download hash on {_rel(meta_path)} "
            f"with the selection {_rel(sel_path)} and save the report to {_rel(rep_path)}",
            f"Check the provenance of the pypi wheel recorded in {_rel(sel_path)} against the "
            f"live metadata {_rel(meta_path)} and save the report to {_rel(rep_path)}",
            f"Verify the sha256 of the pypi wheel that {_rel(sel_path)} selects, using the live "
            f"pypi metadata {_rel(meta_path)}, and save the report to {_rel(rep_path)}",
        ])

        def oracle(result: dict[str, Any]) -> tuple[bool, str]:
            why = _failed(result)
            if why:
                return False, why
            if result.get("compiled_capability_id") != "pypi.provenance.audit_live_artifact":
                return False, "wrong capability: " + str(result.get("compiled_capability_id"))
            if wheel_meta is None or not rep_path.is_file():
                return False, "FIXTURE_NETWORK_FAILURE: metadata/wheel selection not built"
            report = json.loads(rep_path.read_text(encoding="utf-8"))
            if report.get("schema") != "PROJECT_BRAIN_PYPI_PROVENANCE_AUDIT_V1":
                return False, "report schema: " + str(report.get("schema"))
            if report.get("verified") is not True:
                return False, "report verified False: " + json.dumps({k: report.get(k) for k in ("recorded_hash", "live_metadata_hash", "downloaded_artifact_hash")})
            recorded = str(wheel_meta["digests"]["sha256"]).lower()
            if not (report.get("recorded_hash") == report.get("live_metadata_hash") == report.get("downloaded_artifact_hash") == recorded):
                return False, "three-way sha256 equality broken against independent metadata"
            try:
                wheel_bytes = _fetch(wheel_meta["url"], 20_000_000)
            except Exception as exc:
                return False, f"oracle wheel fetch failed: {exc}"
            if hashlib.sha256(wheel_bytes).hexdigest() != recorded:
                return False, "independent wheel download hash differs from the recorded pin"
            if report.get("wheel_filename") != wheel_meta["filename"]:
                return False, "wheel_filename wrong"
            if report.get("project") != project or report.get("pinned_version") != version:
                return False, "project/pinned_version wrong"
            return True, ""

        return Case("HTTP_JSON_FETCH__PYPI_AUDIT__WEB_RELEASE", goal, oracle, True, [rep_path])

    # web release: claim file written from the LIVE atom feed, then independently re-verified
    claim_path = work / f"claim_{i}_{_word(rng, 4)}.json"
    claimed: str | None = None
    try:
        text = _fetch(_ATOM_URL, 3_000_000).decode("utf-8", "replace")
        m = re.search(r"Python\s+3\.\d+\.\d+", text)
        if not m:
            raise RuntimeError("WAVE6_ATOM_NO_VERSION")
        claimed = m.group(0).split()[-1]
        claim_path.write_text(json.dumps({"version": claimed, "source_url": _ATOM_URL}), encoding="utf-8")
    except Exception:
        claimed = None

    goal = rng.choice([
        f'Verify the independent web release version latest stable for product "python" '
        f'major version 3 version field "version" on {_rel(claim_path)}',
        f'Verify the independent web release version latest stable for product "python" '
        f'major version 3 version field "version" on the claim file {_rel(claim_path)}',
        f'Check the latest stable release of the product "python" (major version 3, '
        f'version field "version") against the claim file {_rel(claim_path)}',
        f'Confirm the claimed version of the product "python" in {_rel(claim_path)} against '
        f'the live release page, with major version 3 and version field "version"',
    ])

    def oracle(result: dict[str, Any]) -> tuple[bool, str]:
        why = _failed(result)
        if why:
            return False, why
        if result.get("compiled_capability_id") != "web.release.verify.independent_http":
            return False, "wrong capability: " + str(result.get("compiled_capability_id"))
        if claimed is None or not claim_path.is_file():
            return False, "FIXTURE_NETWORK_FAILURE: atom feed unavailable at generation"
        row = _cap_result(result, capability_id="web.release.verify.independent_http")
        if not isinstance(row, dict):
            return False, "release verifier result missing"
        if row.get("verified") is not True:
            return False, "verified False: " + json.dumps({k: row.get(k) for k in ("claimed_version", "observed_version")})
        if row.get("claimed_version") != claimed or row.get("observed_version") != claimed:
            return False, f"claimed/observed != generation claim {claimed}: {row.get('claimed_version')}/{row.get('observed_version')}"
        try:
            fresh_text = _fetch(_ATOM_URL, 3_000_000).decode("utf-8", "replace")
        except Exception as exc:
            return False, f"oracle atom fetch failed: {exc}"
        fresh = re.search(r"Python\s+3\.\d+\.\d+", fresh_text)
        if fresh is None or fresh.group(0).split()[-1] != claimed:
            return False, "live atom feed no longer shows the claimed version (release changed mid-run)"
        if claimed not in fresh_text:
            return False, "claimed version string absent from the live feed"
        return True, ""

    return Case("HTTP_JSON_FETCH__PYPI_AUDIT__WEB_RELEASE", goal, oracle, True, [])


# --------------------------------------- two-step pipeline: fetch the live metadata, then audit it


def gen_pipeline_fetch_audit(rng: random.Random, work: Path, i: int) -> Case:
    """One sentence, TWO capabilities, and the second one reads what the first one wrote.

    The request is only answerable if the machine plans the two steps as ONE graph with an
    explicit artifact edge: the audit's metadata input IS the fetched file.  Before F26 the
    consumer bound the selection record instead (it was the only file on disk), the producer's
    artifact was claimed as the consumer's OUTPUT, and the request silently dropped a step.
    """
    work.mkdir(parents=True, exist_ok=True)
    project, version = rng.choice(_PACKAGES)
    url = f"https://pypi.org/pypi/{project}/{version}/json"
    sel_path = work / f"sel_{i}_{_word(rng, 4)}.json"
    state_path = work / f"state_{i}_{_word(rng, 4)}.json"
    fetched = work / f"fetched_{i}_{_word(rng, 4)}.json"
    rep_path = work / f"rep_{i}_{_word(rng, 4)}.json"
    wheel_meta: dict[str, Any] | None = None
    try:
        state_path.write_text(json.dumps({"release_url": url}), encoding="utf-8")
        meta = json.loads(_fetch(url, 3_000_000))
        wheels = [u for u in meta.get("urls") or [] if str(u.get("filename") or "").endswith(".whl")]
        if not wheels:
            raise RuntimeError("WAVE6_NO_WHEEL_IN_METADATA")
        wheel_meta = wheels[0]
        sel_path.write_text(json.dumps({
            "id": f"cap.{project}",
            "record": {"source": {
                "type": "pypi",
                "project": project,
                "version": version,
                "wheel_filename": wheel_meta["filename"],
                "wheel_sha256": wheel_meta["digests"]["sha256"],
                "metadata_url": url,
            }},
        }), encoding="utf-8")
    except Exception:
        wheel_meta = None

    goal = (f"Fetch the HTTP JSON live metadata from the source json {_rel(state_path)} with url key "
            f"\"release_url\" and save it to {_rel(fetched)}. Then audit the pypi wheel artifact "
            f"provenance and sha256 download hash on {_rel(fetched)} with selection {_rel(sel_path)} "
            f"and save the report to {_rel(rep_path)}")

    def oracle(result: dict[str, Any]) -> tuple[bool, str]:
        why = _failed(result)
        if why:
            return False, why
        if wheel_meta is None or not rep_path.is_file():
            return False, "FIXTURE_NETWORK_FAILURE: metadata/wheel selection not built"
        if not fetched.is_file():
            return False, "the first step did not write the fetched metadata"
        try:
            fresh = _fetch(url, 3_000_000)
        except Exception as exc:
            return False, f"oracle fetch failed: {exc}"
        if hashlib.sha256(fetched.read_bytes()).hexdigest() != hashlib.sha256(fresh).hexdigest():
            return False, "the fetched artifact differs from an independent fetch of the same immutable URL"
        report = json.loads(rep_path.read_text(encoding="utf-8"))
        if report.get("schema") != "PROJECT_BRAIN_PYPI_PROVENANCE_AUDIT_V1":
            return False, "report schema: " + str(report.get("schema"))
        if report.get("verified") is not True:
            return False, "report verified False: " + json.dumps({k: report.get(k) for k in ("recorded_hash", "live_metadata_hash", "downloaded_artifact_hash")})
        recorded = str(wheel_meta["digests"]["sha256"]).lower()
        if not (report.get("recorded_hash") == report.get("live_metadata_hash") == report.get("downloaded_artifact_hash") == recorded):
            return False, "three-way sha256 equality broken against independent metadata"
        row = _cap_result(result, capability_id="pypi.provenance.audit_live_artifact")
        if not isinstance(row, dict) or row.get("verified") is not True:
            return False, "the audit step did not report verified"
        caps = [str(r.get("capability_id") or "") for r in (result.get("execution") or []) if isinstance(r, dict)]
        if "http.json.fetch_from_state" not in caps:
            return False, "the fetch step did not run: " + json.dumps(caps)
        return True, ""

    return Case("PIPELINE_FETCH_THEN_AUDIT", goal, oracle, True, [fetched, rep_path])


GENERATORS_V6: dict[str, Callable[[random.Random, Path, int], Case]] = {
    "CHART_RASTER_READERS": gen_chart_raster_readers,
    "KNOWLEDGE_FETCH_ASSESS_ASSERT": gen_knowledge_fetch_assess_assert,
    "HTTP_JSON_FETCH__PYPI_AUDIT__WEB_RELEASE": gen_http_pypi_web,
    "PIPELINE_FETCH_THEN_AUDIT": gen_pipeline_fetch_audit,
}
