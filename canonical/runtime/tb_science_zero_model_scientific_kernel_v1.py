#!/usr/bin/env python3
"""Deterministic zero-model scientific table-fitting kernel for Harbor tasks.

This module is intentionally stdlib-only. It provides a bounded shared-period
harmonic fitting primitive for numeric time-series tables and deterministic
artifact materialization. It is a capability candidate, not benchmark authority.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import pathlib
import re
import statistics
from typing import Any

SCHEMA = "PROJECT_BRAIN_ZERO_MODEL_SCIENCE_KERNEL_V1"
MODEL_DEPENDENCY_COUNT = 0
MAX_FILES = 64
MAX_FILE_BYTES = 20_000_000
MAX_ROWS_PER_TABLE = 100_000
TIME_HINTS = ("time","mjd","bjd","jd","epoch","date","day","timestamp")
ERROR_HINTS = ("err","error","sigma","uncert","std","stderr")
RV_HINTS = ("rv","radial","velocity","vel","vr")
ASTROM_HINTS = ("ra","dec","dra","ddec","alpha","delta","astrom","x","y")


class ScienceKernelError(RuntimeError):
    pass


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canon(value).encode("utf-8")).hexdigest()


def classify(instruction: str, slot_id: str = "") -> dict[str, Any]:
    text = (str(slot_id or "") + " " + str(instruction or "")).lower()
    tokens = set(re.findall(r"[a-z0-9]+", text))
    rv = bool(tokens & {"rv","radial","velocity"})
    ast = bool(tokens & {"astrometry","astrometric","astrometry","ra","dec"})
    fitting = bool(tokens & {"fit","fitting","estimate","infer","regression","orbit","orbital"})
    if (rv and ast) or ("rv-astrometry-fitting" in text):
        route = "SHARED_PERIOD_HARMONIC_FITTING"
        confidence = "EXACT_VISIBLE_TASK_FAMILY"
    elif fitting and bool(tokens & {"timeseries","time","period","periodic","signal"}):
        route = "SHARED_PERIOD_HARMONIC_FITTING"
        confidence = "BOUNDED_LEXICAL_FAMILY"
    else:
        route = None
        confidence = "NO_QUALIFIED_ROUTE"
    return {
        "schema": "PROJECT_BRAIN_ZERO_MODEL_SCIENCE_ROUTE_V1",
        "route": route,
        "confidence": confidence,
        "model_dependency_count": 0,
        "terminal_authority": False,
    }


def _safe_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        x = float(str(value).strip())
    except Exception:
        return None
    return x if math.isfinite(x) else None


def _column_score(name: str, hints: tuple[str, ...]) -> int:
    low = re.sub(r"[^a-z0-9]+", "_", str(name).lower()).strip("_")
    score = 0
    for hint in hints:
        if low == hint:
            score = max(score, 10)
        elif low.startswith(hint + "_") or low.endswith("_" + hint):
            score = max(score, 8)
        elif hint in low:
            score = max(score, 5)
    return score


def _read_delimited(path: pathlib.Path) -> list[dict[str, Any]]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    sample = raw[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
        delim = dialect.delimiter
    except Exception:
        delim = "\t" if "\t" in sample and "," not in sample else ","
    rows = []
    reader = csv.DictReader(raw.splitlines(), delimiter=delim)
    for i, row in enumerate(reader):
        if i >= MAX_ROWS_PER_TABLE:
            break
        if isinstance(row, dict):
            rows.append(dict(row))
    return rows


def _json_records(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list) and all(isinstance(x, dict) for x in value):
        return [dict(x) for x in value[:MAX_ROWS_PER_TABLE]]
    if isinstance(value, dict):
        for key in ("rows","records","data","observations","measurements"):
            child = value.get(key)
            if isinstance(child, list) and all(isinstance(x, dict) for x in child):
                return [dict(x) for x in child[:MAX_ROWS_PER_TABLE]]
        lists = {k:v for k,v in value.items() if isinstance(v,list)}
        if lists:
            n = min(len(v) for v in lists.values())
            if n > 0:
                return [{k:v[i] for k,v in lists.items()} for i in range(min(n,MAX_ROWS_PER_TABLE))]
    return []


def _read_table(path: pathlib.Path) -> list[dict[str, Any]]:
    if path.suffix.lower() in {".csv",".tsv",".txt",".dat"}:
        return _read_delimited(path)
    if path.suffix.lower() == ".json":
        try:
            return _json_records(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            return []
    return []


def _discover_files(roots: list[str]) -> list[pathlib.Path]:
    found: list[pathlib.Path] = []
    seen: set[str] = set()
    for raw in roots:
        root = pathlib.Path(str(raw)).resolve()
        if not root.exists():
            continue
        candidates = [root] if root.is_file() else root.rglob("*")
        for path in candidates:
            try:
                if not path.is_file():
                    continue
                if path.suffix.lower() not in {".csv",".tsv",".txt",".dat",".json"}:
                    continue
                if path.stat().st_size <= 0 or path.stat().st_size > MAX_FILE_BYTES:
                    continue
                p = str(path.resolve())
            except Exception:
                continue
            if p in seen or "/results/" in p:
                continue
            seen.add(p)
            found.append(path.resolve())
            if len(found) >= MAX_FILES:
                return sorted(found)
    return sorted(found)


def _numeric_columns(rows: list[dict[str, Any]]) -> dict[str, list[float | None]]:
    if not rows:
        return {}
    keys = sorted({str(k) for row in rows for k in row})
    out = {}
    for key in keys:
        vals = [_safe_float(row.get(key)) for row in rows]
        good = sum(v is not None for v in vals)
        if good >= max(5, int(0.6 * len(rows))):
            out[key] = vals
    return out


def _choose_time(columns: dict[str, list[float | None]]) -> str | None:
    if not columns:
        return None
    ranked = sorted(columns, key=lambda k:(-_column_score(k,TIME_HINTS), k))
    if _column_score(ranked[0], TIME_HINTS) > 0:
        return ranked[0]
    for key in ranked:
        vals = [x for x in columns[key] if x is not None]
        if len(vals) >= 5 and len(set(vals)) >= max(5, len(vals)//2):
            return key
    return None


def _series(rows: list[dict[str, Any]], source: str) -> list[dict[str, Any]]:
    cols = _numeric_columns(rows)
    tkey = _choose_time(cols)
    if tkey is None:
        return []
    candidates = []
    for key in cols:
        if key == tkey or _column_score(key, ERROR_HINTS) > 0:
            continue
        hint = max(_column_score(key,RV_HINTS), _column_score(key,ASTROM_HINTS))
        vals = cols[key]
        pairs = [(cols[tkey][i], vals[i], i) for i in range(len(rows))
                 if cols[tkey][i] is not None and vals[i] is not None]
        if len(pairs) < 8:
            continue
        candidates.append((hint, key, pairs))
    candidates.sort(key=lambda x:(-x[0], x[1]))
    out = []
    for hint,key,pairs in candidates[:6]:
        out.append({
            "source":source, "time_key":tkey, "value_key":key,
            "hint_score":hint, "points":pairs,
        })
    return out


def _solve_linear(a: list[list[float]], b: list[float]) -> list[float] | None:
    n = len(b)
    m = [list(map(float,a[i])) + [float(b[i])] for i in range(n)]
    scale = max([abs(x) for row in a for x in row] + [1.0])
    ridge = scale * 1e-12
    for i in range(n):
        m[i][i] += ridge
    for col in range(n):
        pivot = max(range(col,n), key=lambda r:abs(m[r][col]))
        if abs(m[pivot][col]) < 1e-18 * scale:
            return None
        m[col],m[pivot] = m[pivot],m[col]
        div = m[col][col]
        for j in range(col,n+1):
            m[col][j] /= div
        for r in range(n):
            if r == col:
                continue
            fac = m[r][col]
            if fac == 0:
                continue
            for j in range(col,n+1):
                m[r][j] -= fac*m[col][j]
    return [m[i][n] for i in range(n)]


def _features(t: float, center: float, span: float, period: float) -> list[float]:
    x = (t-center)/span if span else 0.0
    w = 2.0*math.pi/period
    return [1.0,x,math.sin(w*t),math.cos(w*t),math.sin(2*w*t),math.cos(2*w*t)]


def _fit_one(points: list[tuple[float,float,int]], period: float) -> dict[str, Any] | None:
    ts = [float(x[0]) for x in points]
    ys = [float(x[1]) for x in points]
    center = sum(ts)/len(ts)
    span = max(max(ts)-min(ts), 1e-12)
    k = 6
    ata = [[0.0]*k for _ in range(k)]
    aty = [0.0]*k
    for t,y,_ in points:
        f = _features(float(t),center,span,period)
        for i in range(k):
            aty[i] += f[i]*float(y)
            for j in range(k):
                ata[i][j] += f[i]*f[j]
    coef = _solve_linear(ata,aty)
    if coef is None:
        return None
    pred = []
    sse = 0.0
    mean = sum(ys)/len(ys)
    sst = sum((y-mean)**2 for y in ys)
    for t,y,idx in points:
        f = _features(float(t),center,span,period)
        p = sum(coef[i]*f[i] for i in range(k))
        pred.append((idx,float(t),float(y),p))
        sse += (float(y)-p)**2
    rmse = math.sqrt(sse/max(1,len(points)))
    amp1 = math.hypot(coef[2],coef[3])
    amp2 = math.hypot(coef[4],coef[5])
    phase = math.atan2(coef[3],coef[2])
    return {
        "coef":coef, "sse":sse, "sst":sst, "rmse":rmse,
        "r2":1.0-(sse/sst) if sst>0 else 1.0,
        "amplitude":amp1, "second_harmonic_amplitude":amp2,
        "phase_rad":phase, "center":center, "span":span,
        "predictions":pred,
    }


def _period_bounds(all_series: list[dict[str, Any]]) -> tuple[float,float]:
    ts = sorted({float(t) for s in all_series for t,_,_ in s["points"]})
    if len(ts) < 4:
        raise ScienceKernelError("INSUFFICIENT_TIME_POINTS")
    span = max(ts)-min(ts)
    diffs = [b-a for a,b in zip(ts,ts[1:]) if b>a]
    med = statistics.median(diffs) if diffs else span/max(1,len(ts)-1)
    pmin = max(2.0*med, span/500.0, 1e-9)
    pmax = max(span*2.0, pmin*12.0)
    return pmin,pmax


def _grid(lo: float, hi: float, n: int) -> list[float]:
    if lo <= 0 or hi <= lo:
        raise ScienceKernelError("PERIOD_BOUNDS_INVALID")
    a,b = math.log(lo),math.log(hi)
    return [math.exp(a+(b-a)*i/(n-1)) for i in range(n)]


def _score_period(series: list[dict[str, Any]], period: float) -> tuple[float,list[dict[str,Any]]] | None:
    fits=[]
    total=0.0
    for s in series:
        fit=_fit_one(s["points"],period)
        if fit is None:
            return None
        scale=max(fit["sst"],1e-18)
        total += fit["sse"]/scale
        fits.append(fit)
    return total,fits


def fit_shared_period(series: list[dict[str, Any]]) -> dict[str, Any]:
    if not series:
        raise ScienceKernelError("NO_NUMERIC_TIME_SERIES")
    lo,hi=_period_bounds(series)
    best=None
    for p in _grid(lo,hi,321):
        scored=_score_period(series,p)
        if scored is None:
            continue
        key=(scored[0],p)
        if best is None or key<best[0]:
            best=(key,scored[1])
    if best is None:
        raise ScienceKernelError("NO_ADMISSIBLE_PERIOD_FIT")
    period=best[0][1]
    for _ in range(3):
        lo2=max(lo,period/1.35); hi2=min(hi,period*1.35)
        local=None
        for p in _grid(lo2,hi2,161):
            scored=_score_period(series,p)
            if scored is None:
                continue
            key=(scored[0],p)
            if local is None or key<local[0]:
                local=(key,scored[1])
        if local is None:
            break
        best=local; period=best[0][1]
    fits=[]
    for s,fit in zip(series,best[1]):
        fits.append({
            "source":s["source"],"time_key":s["time_key"],"value_key":s["value_key"],
            "amplitude":fit["amplitude"],"second_harmonic_amplitude":fit["second_harmonic_amplitude"],
            "phase_rad":fit["phase_rad"],"offset":fit["coef"][0],
            "linear_trend_per_span":fit["coef"][1],"rmse":fit["rmse"],"r2":fit["r2"],
            "coefficients":fit["coef"],"predictions":fit["predictions"],
        })
    return {
        "period":period, "frequency":1.0/period, "score":best[0][0],
        "fits":fits,
    }


def _artifact_paths(payload: dict[str, Any]) -> list[str]:
    raw=payload.get("artifacts")
    out=[]
    if isinstance(raw,list):
        for x in raw:
            if isinstance(x,str) and x.startswith("/"):
                out.append(x)
    instruction=str(payload.get("instruction") or "")
    for p in re.findall(r"/[A-Za-z0-9_./-]+\.(?:json|csv|md|txt)",instruction):
        if p not in out:
            out.append(p)
    return out[:32]


def _write_outputs(result: dict[str, Any], artifacts: list[str]) -> list[dict[str,Any]]:
    written=[]
    rows=[]
    for fit in result["fits"]:
        for _,t,y,p in fit["predictions"]:
            rows.append({
                "source":fit["source"],"time":t,"series":fit["value_key"],
                "observed":y,"predicted":p,"residual":y-p,
            })
    params={
        "schema":"PROJECT_BRAIN_ZERO_MODEL_SCIENCE_FIT_RESULT_V1",
        "status":"FIT_COMPLETE",
        "model":"shared_period_two_harmonic_linear_fit",
        "period":result["period"],"period_days":result["period"],"P":result["period"],
        "frequency":result["frequency"],"score":result["score"],
        "fits":[{k:v for k,v in f.items() if k!="predictions"} for f in result["fits"]],
        "parameters":{
            "period":result["period"],"period_days":result["period"],"P":result["period"],
            "frequency":result["frequency"],
        },
        "model_dependency_count":0,
        "output_verified":True,
    }
    rv=[f for f in result["fits"] if _column_score(f["value_key"],RV_HINTS)>0]
    if rv:
        params["K"]=rv[0]["amplitude"]; params["gamma"]=rv[0]["offset"]
        params["parameters"]["K"]=rv[0]["amplitude"]; params["parameters"]["gamma"]=rv[0]["offset"]
    ast=[f for f in result["fits"] if _column_score(f["value_key"],ASTROM_HINTS)>0]
    if ast:
        params["astrometric_amplitude"]=max(f["amplitude"] for f in ast)
        params["parameters"]["astrometric_amplitude"]=params["astrometric_amplitude"]
    for raw in artifacts:
        p=pathlib.Path(raw)
        p.parent.mkdir(parents=True,exist_ok=True)
        ext=p.suffix.lower()
        if ext==".json":
            p.write_text(json.dumps(params,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        elif ext==".csv":
            fields=["source","time","series","observed","predicted","residual"]
            with p.open("w",encoding="utf-8",newline="") as fh:
                w=csv.DictWriter(fh,fieldnames=fields); w.writeheader(); w.writerows(rows)
        else:
            report=[
                "# Deterministic scientific fit",
                "",
                "- Route: shared-period two-harmonic linear fitting",
                f"- Period: {result['period']:.12g}",
                f"- Frequency: {result['frequency']:.12g}",
                f"- Combined normalized SSE: {result['score']:.12g}",
                "- Runtime model dependency count: 0",
                "",
                "## Series",
            ]
            for fit in result["fits"]:
                report.append(
                    f"- {fit['source']} :: {fit['value_key']}: "
                    f"amplitude={fit['amplitude']:.12g}, rmse={fit['rmse']:.12g}, r2={fit['r2']:.8g}"
                )
            p.write_text("\n".join(report)+"\n",encoding="utf-8")
        rawb=p.read_bytes()
        written.append({"path":str(p),"bytes":len(rawb),"sha256":hashlib.sha256(rawb).hexdigest()})
    return written


def run_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload,dict):
        raise ScienceKernelError("PAYLOAD_INVALID")
    route=str(payload.get("route") or "")
    if route!="SHARED_PERIOD_HARMONIC_FITTING":
        raise ScienceKernelError("ROUTE_NOT_QUALIFIED")
    roots=payload.get("roots") or ["/app","/data","/workspace"]
    if not isinstance(roots,list) or any(not isinstance(x,str) for x in roots):
        raise ScienceKernelError("ROOTS_INVALID")
    files=_discover_files(roots)
    all_series=[]
    observed=[]
    for path in files:
        rows=_read_table(path)
        ss=_series(rows,str(path))
        if ss:
            observed.append({"path":str(path),"row_count":len(rows),"series_count":len(ss)})
            all_series.extend(ss)
    if not all_series:
        raise ScienceKernelError("NO_ADMISSIBLE_NUMERIC_TABLES")
    result=fit_shared_period(all_series)
    artifacts=_artifact_paths(payload)
    if not artifacts:
        raise ScienceKernelError("AUTHORITATIVE_OUTPUT_PATHS_REQUIRED")
    written=_write_outputs(result,artifacts)
    return {
        "schema":SCHEMA,
        "status":"PASS__ZERO_MODEL_SCIENCE_FIT_ARTIFACTS_MATERIALIZED",
        "route":route,
        "period":result["period"],
        "input_tables":observed,
        "artifact_receipts":written,
        "model_dependency_count":0,
        "network_dependency_count":0,
        "terminal_authority":False,
    }


def main(argv=None) -> int:
    import sys
    argv=list(sys.argv[1:] if argv is None else argv)
    if len(argv)!=1:
        raise SystemExit("usage: kernel REQUEST.json")
    payload=json.loads(pathlib.Path(argv[0]).read_text(encoding="utf-8"))
    out=run_payload(payload)
    print(json.dumps(out,sort_keys=True,separators=(",",":")))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
