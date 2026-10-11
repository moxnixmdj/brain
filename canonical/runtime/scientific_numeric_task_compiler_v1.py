"""Fail-closed compiler from explicit numeric science tasks to typed controller inputs."""
from __future__ import annotations
import math,re
from typing import Any,Mapping,Sequence

SCHEMA="PROJECT_BRAIN_SCIENTIFIC_NUMERIC_TASK_COMPILER_V1"
FIELD=re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
TARGETS=(
 re.compile(r"\btarget\s*(?::|=|\bis\b)?\s*([A-Za-z_][A-Za-z0-9_]*)\b",re.I),
 re.compile(r"\bpredict\s+([A-Za-z_][A-Za-z0-9_]*)\b",re.I),
 re.compile(r"\bmodel\s+([A-Za-z_][A-Za-z0-9_]*)\b",re.I),
 re.compile(r"\bfit\s+([A-Za-z_][A-Za-z0-9_]*)\s+(?:from|using|against)\b",re.I),
)
PERIOD=re.compile(r"\b(period|periodic|periodicity|frequency|oscillation|cycle|cyclic)\b",re.I)
TIME=("time","t","mjd","bjd","jd","epoch","day","days","timestamp")
ERROR=("err","error","sigma","stderr","std","uncert")

def _fail(reason,details=None):
 out={"schema":SCHEMA,"status":"FAIL_CLOSED","reason":reason,"task_problem":None,"terminal_authority":False}
 if details: out["details"]=details
 return out

def _num(v):
 if v is None or isinstance(v,bool): return None
 try: x=float(v)
 except Exception: return None
 return x if math.isfinite(x) else None

def _rows(raw):
 if not isinstance(raw,Sequence) or isinstance(raw,(str,bytes)) or not 4<=len(raw)<=100000:
  raise ValueError("ROWS_INVALID")
 if any(not isinstance(x,Mapping) for x in raw): raise ValueError("ROW_NOT_MAPPING")
 names=sorted({str(k) for row in raw for k in row})
 if not names or len(names)>128 or any(not FIELD.fullmatch(x) for x in names):
  raise ValueError("COLUMN_NAMES_INVALID")
 rows=[dict(x) for x in raw]
 numeric={}
 for name in names:
  vals=[_num(r.get(name)) for r in rows]
  if sum(x is not None for x in vals)>=max(4,int(.75*len(rows))): numeric[name]=vals
 return rows,numeric

def _target(text,names):
 hits=[]
 for p in TARGETS:
  m=p.search(text)
  if m and m.group(1) in names: hits.append(m.group(1))
 u=sorted(set(hits))
 return u[0] if len(u)==1 else None

def _time(names):
 exact=[x for x in names if x.lower() in TIME]
 if len(exact)==1:return exact[0]
 scored=[]
 for name in names:
  low=name.lower()
  s=max(5 if low==h else 3 if low.startswith(h+"_") or low.endswith("_"+h) else 1 if h in low else 0 for h in TIME)
  if s: scored.append((s,name))
 scored.sort(key=lambda x:(-x[0],x[1]))
 return scored[0][1] if scored and (len(scored)==1 or scored[0][0]>scored[1][0]) else None

def _error(name):
 low=name.lower()
 return any(h in low for h in ERROR)

def compile_numeric_task(instruction:str,raw_rows:Any)->dict[str,Any]:
 if not isinstance(instruction,str) or not instruction.strip() or len(instruction)>20000:
  return _fail("INSTRUCTION_INVALID")
 try: rows,cols=_rows(raw_rows)
 except ValueError as exc:return _fail(str(exc))
 if len(cols)<2:return _fail("INSUFFICIENT_NUMERIC_COLUMNS")
 names=set(cols); target=_target(instruction,names); tcol=_time(names)
 symbolic=target is not None; periodic=bool(PERIOD.search(instruction)) and tcol is not None
 if symbolic and periodic:return _fail("AMBIGUOUS_SYMBOLIC_AND_PERIODIC_INTENT")
 if not symbolic and not periodic:return _fail("NO_SUPPORTED_NUMERIC_SCIENCE_INTENT")

 if symbolic:
  inputs=sorted(names-{target}); typed=[]; dropped=0
  for row in rows:
   vals={n:_num(row.get(n)) for n in inputs+[target]}
   if all(v is not None for v in vals.values()):typed.append(vals)
   else:dropped+=1
  if len(typed)<8:return _fail("SYMBOLIC_COMPLETE_ROWS_INSUFFICIENT")
  return {"schema":SCHEMA,"status":"COMPILED","family":"SYMBOLIC_REGRESSION",
          "task_problem":{"rows":typed,"target":target,"inputs":inputs,"max_depth":1},
          "provenance":{"target":target,"inputs":inputs,"rows_used":len(typed),"rows_dropped":dropped},
          "terminal_authority":False}

 signals=[x for x in sorted(names-{tcol}) if not _error(x)]
 series=[]
 for name in signals:
  pts=[[_num(r.get(tcol)),_num(r.get(name))] for r in rows]
  pts=[p for p in pts if p[0] is not None and p[1] is not None]
  if len(pts)>=8:series.append({"name":name,"points":pts})
 if not series:return _fail("PERIODIC_COMPLETE_SERIES_INSUFFICIENT")
 return {"schema":SCHEMA,"status":"COMPILED","family":"SHARED_PERIOD_FITTING",
         "task_problem":{"series":series,"acceptance":{"min_r2":0.0}},
         "provenance":{"time_column":tcol,"signal_columns":[x["name"] for x in series]},
         "terminal_authority":False}
