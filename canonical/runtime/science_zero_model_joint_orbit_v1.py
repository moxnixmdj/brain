"""Deterministic zero-learned joint RV + sky-plane astrometric orbit fitter.

The nonlinear search is only over period, eccentricity and periastron phase.
For every nonlinear point, all RV and astrometric coefficients are solved by
weighted linear least squares. This keeps the search small, deterministic and
transparent. No learned model, random search, network access or hidden state.
"""
from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
from scipy.optimize import minimize

SCHEMA="PROJECT_BRAIN_SCIENCE_ZERO_MODEL_JOINT_ORBIT_V1"
TWOPI=2.0*math.pi

_TIME=("time","t","bjd","jd","mjd","epoch")
_RV=("rv","radial_velocity","radialvelocity","velocity")
_RVERR=("rv_err","rv_error","sigma_rv","erv","velocity_error")
_X=("dra","delta_ra","ra_offset","x","east","alpha_offset")
_Y=("ddec","delta_dec","dec_offset","y","north","delta_offset")
_XERR=("dra_err","ra_err","x_err","sigma_ra","sigma_x")
_YERR=("ddec_err","dec_err","y_err","sigma_dec","sigma_y")


def _norm(s: str)->str:
    return "_".join(str(s).strip().lower().replace("-","_").split())


def _pick(columns: Iterable[str], aliases: Sequence[str])->str|None:
    by={_norm(c):c for c in columns}
    for a in aliases:
        if a in by: return by[a]
    for n,c in by.items():
        if any(n.endswith("_"+a) or n.startswith(a+"_") for a in aliases): return c
    return None


def _finite(v: Any)->float:
    x=float(v)
    if not math.isfinite(x): raise ValueError("NONFINITE_OBSERVATION")
    return x


def load_csv(path: str|Path)->list[dict[str,float]]:
    rows=[]
    with open(path,newline="",encoding="utf-8") as f:
        for raw in csv.DictReader(f):
            row={}
            for k,v in raw.items():
                if v is None or str(v).strip()=="": continue
                try: row[k]=_finite(v)
                except Exception: pass
            if row: rows.append(row)
    return rows


def discover_observation_tables(root: str|Path="/data")->dict[str,Any]:
    root=Path(root)
    rv=[]; astro=[]; inspected=[]
    for p in sorted(root.glob("*.csv")):
        try: rows=load_csv(p)
        except Exception: continue
        if len(rows)<4: continue
        cols=list(rows[0])
        tc=_pick(cols,_TIME); rc=_pick(cols,_RV); xc=_pick(cols,_X); yc=_pick(cols,_Y)
        inspected.append({"path":str(p),"columns":cols,"rows":len(rows)})
        if tc and rc:
            ec=_pick(cols,_RVERR)
            rv.extend((row[tc],row[rc],row.get(ec,1.0) if ec else 1.0) for row in rows if tc in row and rc in row)
        if tc and xc and yc:
            ex=_pick(cols,_XERR); ey=_pick(cols,_YERR)
            astro.extend((row[tc],row[xc],row[yc],row.get(ex,1.0) if ex else 1.0,row.get(ey,1.0) if ey else 1.0) for row in rows if tc in row and xc in row and yc in row)
    return {"rv":rv,"astrometry":astro,"inspected":inspected}


def solve_kepler(mean_anomaly: np.ndarray,e: float)->np.ndarray:
    M=np.asarray(mean_anomaly,float)
    E=np.where(e<0.8,M,np.pi*np.ones_like(M))
    for _ in range(32):
        f=E-e*np.sin(E)-M
        d=1.0-e*np.cos(E)
        step=f/d
        E-=step
        if np.max(np.abs(step))<1e-13: break
    return E


def orbital_basis(times: np.ndarray,period: float,e: float,tau: float):
    M=np.mod(TWOPI*(np.asarray(times,float)-tau)/period,TWOPI)
    E=solve_kepler(M,e)
    X=np.cos(E)-e
    Y=np.sqrt(max(1e-14,1.0-e*e))*np.sin(E)
    nu=2.0*np.arctan2(np.sqrt(1+e)*np.sin(E/2),np.sqrt(1-e)*np.cos(E/2))
    return X,Y,np.cos(nu),np.sin(nu)


def _wls(A: np.ndarray,y: np.ndarray,sigma: np.ndarray):
    sigma=np.asarray(sigma,float)
    good=np.isfinite(sigma)&(sigma>0)
    scale=float(np.nanmedian(sigma[good])) if np.any(good) else 1.0
    sigma=np.where(good,sigma,max(scale,1e-12))
    Aw=A/sigma[:,None]; yw=y/sigma
    coef,*_=np.linalg.lstsq(Aw,yw,rcond=None)
    res=(A@coef-y)/sigma
    return coef,res


def _linear_fit(rv,astro,period,e,tau):
    total=[]; model={}
    tref=[]
    if rv: tref.extend(x[0] for x in rv)
    if astro: tref.extend(x[0] for x in astro)
    t0=float(np.mean(tref))
    if rv:
        a=np.asarray(rv,float); t,y,s=a[:,0],a[:,1],a[:,2]
        _,_,cnu,snu=orbital_basis(t,period,e,tau)
        A=np.column_stack([np.ones(len(t)),t-t0,cnu,snu])
        coef,res=_wls(A,y,s)
        total.extend(res.tolist()); model["rv"]={"coef":coef,"t":t,"A":A,"y":y,"sigma":s}
    if astro:
        a=np.asarray(astro,float); t,x,y,sx,sy=a[:,0],a[:,1],a[:,2],a[:,3],a[:,4]
        X,Y,_,_=orbital_basis(t,period,e,tau)
        A=np.column_stack([np.ones(len(t)),t-t0,X,Y])
        cx,rx=_wls(A,x,sx); cy,ry=_wls(A,y,sy)
        total.extend(rx.tolist()); total.extend(ry.tolist())
        model["astro"]={"cx":cx,"cy":cy,"t":t,"A":A,"x":x,"y":y,"sx":sx,"sy":sy}
    if not total: raise ValueError("NO_RV_OR_ASTROMETRY_OBSERVATIONS")
    return float(np.mean(np.square(total))),model,t0


def _period_bounds(rv,astro,explicit=None):
    ts=sorted({float(x[0]) for x in [*rv,*astro]})
    if len(ts)<4: raise ValueError("INSUFFICIENT_TIME_SAMPLES")
    span=max(ts)-min(ts)
    diffs=[b-a for a,b in zip(ts,ts[1:]) if b>a]
    dt=float(np.median(diffs)) if diffs else span/20
    lo=max(2.5*dt,span/100.0,1e-8); hi=max(lo*1.5,4.0*span)
    if explicit:
        elo,ehi=map(float,explicit)
        if 0<elo<ehi: lo,hi=elo,ehi
    return lo,hi


def _period_seed_scores(rv,astro,lo,hi,count=320):
    periods=np.geomspace(lo,hi,count)
    tref=np.mean([x[0] for x in [*rv,*astro]])
    scored=[]
    for P in periods:
        w=TWOPI/P; score=0.0; n=0
        if rv:
            a=np.asarray(rv,float); t,y,s=a[:,0],a[:,1],a[:,2]
            A=np.column_stack([np.ones(len(t)),t-tref,np.cos(w*t),np.sin(w*t)])
            _,res=_wls(A,y,s); score+=float(np.sum(res*res)); n+=len(res)
        if astro:
            a=np.asarray(astro,float); t=a[:,0]
            A=np.column_stack([np.ones(len(t)),t-tref,np.cos(w*t),np.sin(w*t)])
            for y,s in ((a[:,1],a[:,3]),(a[:,2],a[:,4])):
                _,res=_wls(A,y,s); score+=float(np.sum(res*res)); n+=len(res)
        scored.append((score/max(n,1),float(P)))
    scored.sort()
    seeds=[]
    for _,p in scored:
        if all(abs(math.log(p/q))>0.08 for q in seeds): seeds.append(p)
        if len(seeds)>=10: break
    return seeds


def _orientation_from_thiele(A:float,B:float,F:float,G:float):
    rp=math.hypot(A+G,B-F); rm=math.hypot(A-G,B+F)
    a=0.5*(rp+rm)
    if a<=1e-15: return {"semi_major_axis":0.0,"inclination":0.0,"ascending_node":0.0,"argument_periastron":0.0}
    ci=max(-1.0,min(1.0,(rp-rm)/(rp+rm)))
    plus=math.atan2(B-F,A+G); minus=math.atan2(B+F,A-G)
    return {"semi_major_axis":a,"inclination":math.acos(ci),"ascending_node":0.5*(plus+minus)%TWOPI,"argument_periastron":0.5*(plus-minus)%TWOPI}


def fit_joint_orbit(rv: Sequence[Sequence[float]],astro: Sequence[Sequence[float]],*,period_bounds=None)->dict[str,Any]:
    rv=[tuple(map(float,x)) for x in rv]; astro=[tuple(map(float,x)) for x in astro]
    if not rv and not astro: raise ValueError("NO_OBSERVATIONS")
    lo,hi=_period_bounds(rv,astro,period_bounds)
    seeds=_period_seed_scores(rv,astro,lo,hi)
    tmin=min(x[0] for x in [*rv,*astro]);
    best=None
    def unpack(z):
        P=math.exp(z[0]); e=0.95/(1.0+math.exp(-z[1])); phase=1.0/(1.0+math.exp(-z[2])); tau=tmin+phase*P
        return P,e,tau
    def objective(z):
        try:
            P,e,tau=unpack(z)
            if not (lo<=P<=hi): return 1e30
            return _linear_fit(rv,astro,P,e,tau)[0]
        except Exception: return 1e30
    def logit(x): return math.log(x/(1-x))
    starts=[]
    for P in seeds:
        for e in (0.02,0.15,0.35,0.6,0.82):
            for ph in (0.08,0.3,0.55,0.8): starts.append([math.log(P),logit(e/0.95),logit(ph)])
    bounds=[(math.log(lo),math.log(hi)),(-7,5),(-7,7)]
    for z0 in starts:
        r=minimize(objective,z0,method="L-BFGS-B",bounds=bounds,options={"maxiter":180,"ftol":1e-13})
        val=float(r.fun)
        if best is None or val<best[0]: best=(val,r.x)
    if best is None or not math.isfinite(best[0]): raise ValueError("ORBIT_SEARCH_FAILED")
    P,e,tau=unpack(best[1]); loss,model,tref=_linear_fit(rv,astro,P,e,tau)
    out={"schema":SCHEMA,"status":"FIT_COMPLETE","period":P,"eccentricity":e,"tau":tau,"t_ref":tref,"weighted_mse":loss,"period_bounds":[lo,hi],"period_seeds":seeds,"external_model_calls":0,"persistent_learned_bytes":0,"random_search":False}
    if "rv" in model:
        g,tr,c,s=map(float,model["rv"]["coef"]); K=math.hypot(c,s); omega=math.atan2(-s,c)%TWOPI; gamma=g-K*e*math.cos(omega)
        out["rv"]={"gamma":gamma,"trend":tr,"K":K,"omega":omega,"linear_coefficients":[g,tr,c,s]}
    if "astro" in model:
        cx=model["astro"]["cx"]; cy=model["astro"]["cy"]
        orient=_orientation_from_thiele(float(cx[2]),float(cy[2]),float(cx[3]),float(cy[3]))
        out["astrometry"]={"offset_x":float(cx[0]),"proper_motion_x":float(cx[1]),"offset_y":float(cy[0]),"proper_motion_y":float(cy[1]),"A":float(cx[2]),"B":float(cy[2]),"F":float(cx[3]),"G":float(cy[3]),**orient}
    return out


def predict(result: Mapping[str,Any],times: Sequence[float])->dict[str,list[float]]:
    t=np.asarray(times,float); P=float(result["period"]); e=float(result["eccentricity"]); tau=float(result["tau"]); dt=t-float(result["t_ref"])
    X,Y,cnu,snu=orbital_basis(t,P,e,tau); out={"time":t.tolist()}
    if "rv" in result:
        g,tr,c,s=result["rv"]["linear_coefficients"]; out["rv"]=(g+tr*dt+c*cnu+s*snu).tolist()
    if "astrometry" in result:
        a=result["astrometry"]; out["x"]=(a["offset_x"]+a["proper_motion_x"]*dt+a["A"]*X+a["F"]*Y).tolist(); out["y"]=(a["offset_y"]+a["proper_motion_y"]*dt+a["B"]*X+a["G"]*Y).tolist()
    return out


def _find_period_bounds_in_json(root: str|Path):
    def walk(v):
        if isinstance(v,Mapping):
            norm={_norm(k):val for k,val in v.items()}
            for key in ("period_bounds","period_range","orbital_period_bounds","orbital_period_range"):
                val=norm.get(key)
                if isinstance(val,(list,tuple)) and len(val)==2:
                    try:
                        lo,hi=map(float,val)
                        if 0<lo<hi: return (lo,hi)
                    except Exception: pass
            pairs=(("min_period","max_period"),("period_min","period_max"),("minimum_period","maximum_period"))
            for a,b in pairs:
                if a in norm and b in norm:
                    try:
                        lo,hi=float(norm[a]),float(norm[b])
                        if 0<lo<hi: return (lo,hi)
                    except Exception: pass
            for val in v.values():
                found=walk(val)
                if found: return found
        elif isinstance(v,list):
            for val in v:
                found=walk(val)
                if found: return found
        return None
    for p in sorted(Path(root).glob("*.json")):
        try: doc=json.loads(p.read_text(encoding="utf-8"))
        except Exception: continue
        found=walk(doc)
        if found: return found
    return None


def fit_from_directory(root: str|Path="/data",*,period_bounds=None)->dict[str,Any]:
    tables=discover_observation_tables(root)
    if period_bounds is None: period_bounds=_find_period_bounds_in_json(root)
    fit=fit_joint_orbit(tables["rv"],tables["astrometry"],period_bounds=period_bounds)
    fit["source_tables"]=tables["inspected"]
    fit["period_bounds_source"]="explicit_metadata" if period_bounds is not None else "time_sampling_fallback"
    return fit

_KEY_ALIASES={
    "period": lambda r:r["period"], "orbital_period":lambda r:r["period"], "p":lambda r:r["period"],
    "eccentricity":lambda r:r["eccentricity"], "e":lambda r:r["eccentricity"],
    "tau":lambda r:r["tau"], "t0":lambda r:r["tau"], "time_periastron":lambda r:r["tau"], "periastron_time":lambda r:r["tau"],
    "k":lambda r:r.get("rv",{}).get("K"), "semi_amplitude":lambda r:r.get("rv",{}).get("K"), "rv_semi_amplitude":lambda r:r.get("rv",{}).get("K"),
    "gamma":lambda r:r.get("rv",{}).get("gamma"), "systemic_velocity":lambda r:r.get("rv",{}).get("gamma"),
    "omega":lambda r:r.get("rv",{}).get("omega",r.get("astrometry",{}).get("argument_periastron")),
    "argument_periastron":lambda r:r.get("rv",{}).get("omega",r.get("astrometry",{}).get("argument_periastron")),
    "argument_of_periastron":lambda r:r.get("rv",{}).get("omega",r.get("astrometry",{}).get("argument_periastron")),
    "inclination":lambda r:r.get("astrometry",{}).get("inclination"), "i":lambda r:r.get("astrometry",{}).get("inclination"),
    "ascending_node":lambda r:r.get("astrometry",{}).get("ascending_node"), "longitude_ascending_node":lambda r:r.get("astrometry",{}).get("ascending_node"),
    "semi_major_axis":lambda r:r.get("astrometry",{}).get("semi_major_axis"), "astrometric_semi_major_axis":lambda r:r.get("astrometry",{}).get("semi_major_axis"),
    "proper_motion_x":lambda r:r.get("astrometry",{}).get("proper_motion_x"), "proper_motion_y":lambda r:r.get("astrometry",{}).get("proper_motion_y"),
    "weighted_mse":lambda r:r.get("weighted_mse"),
}

def _value_for_key(key: str,result: Mapping[str,Any]):
    n=_norm(key)
    deg=False
    for suffix in ("_deg","_degrees"):
        if n.endswith(suffix): n=n[:-len(suffix)]; deg=True; break
    fn=_KEY_ALIASES.get(n)
    if fn is None: return None
    v=fn(result)
    if v is None: return None
    v=float(v)
    return math.degrees(v) if deg and n in {"omega","argument_periastron","argument_of_periastron","inclination","i","ascending_node","longitude_ascending_node"} else v


def render_json_template(template: Mapping[str,Any],result: Mapping[str,Any]):
    unresolved=[]
    def walk(value,key=None):
        if isinstance(value,Mapping): return {k:walk(v,k) for k,v in value.items()}
        if isinstance(value,list): return [walk(v,key) for v in value]
        if key is not None:
            mapped=_value_for_key(key,result)
            if mapped is not None: return mapped
            nk=_norm(key)
            if nk in {"status","method"}: return "deterministic_zero_model_joint_orbit_fit"
        return value
    out=walk(dict(template))
    # Record numeric/string placeholders that remained zero/empty under parameter-like keys.
    def check(value,path=""):
        if isinstance(value,Mapping):
            for k,v in value.items(): check(v,path+"."+str(k) if path else str(k))
        elif isinstance(value,list):
            for i,v in enumerate(value): check(v,f"{path}[{i}]")
        elif value in (None,""):
            unresolved.append(path)
    check(out)
    return out,unresolved


def _prediction_rows(root: str|Path,result: Mapping[str,Any]):
    root=Path(root); candidates=[]
    for p in sorted(root.glob("*.csv")):
        name=p.name.lower()
        if not any(tag in name for tag in ("test","predict","query","forecast","initial")): continue
        try:
            with open(p,newline="",encoding="utf-8") as f: raw=list(csv.DictReader(f))
        except Exception: continue
        if not raw: continue
        tc=_pick(raw[0].keys(),_TIME)
        if not tc: continue
        try: times=[float(r[tc]) for r in raw]
        except Exception: continue
        candidates.append((p,raw,tc,times))
    if not candidates:
        times=sorted({float(x[0]) for x in []})
        return []
    p,raw,tc,times=candidates[0]; pred=predict(result,times); rows=[]
    for i,r in enumerate(raw):
        row=dict(r); row[tc]=times[i]
        if "rv" in pred:
            col=_pick(row.keys(),_RV) or "rv"; row[col]=pred["rv"][i]
        if "x" in pred:
            col=_pick(row.keys(),_X) or "x"; row[col]=pred["x"][i]
        if "y" in pred:
            col=_pick(row.keys(),_Y) or "y"; row[col]=pred["y"][i]
        rows.append(row)
    return rows


def execute_contract(contract: Mapping[str,Any],root: str|Path="/data")->dict[str,Any]:
    if str(contract.get("capability_class"))!="JOINT_RV_ASTROMETRY_FIT":
        raise ValueError("UNSUPPORTED_CAPABILITY_CLASS")
    fit=fit_from_directory(root)
    outputs=[str(x) for x in contract.get("output_paths",[]) if str(x).startswith("/results/")]
    templates=list(contract.get("json_templates",[]))
    Path("/results").mkdir(parents=True,exist_ok=True)
    written=[]; unresolved=[]
    json_i=0
    prediction_rows=None
    for target in outputs:
        p=Path(target); p.parent.mkdir(parents=True,exist_ok=True); low=p.name.lower()
        if p.suffix.lower()==".json":
            if json_i<len(templates):
                obj,miss=render_json_template(templates[json_i],fit); json_i+=1; unresolved.extend(miss)
            else:
                obj=dict(fit)
            p.write_text(json.dumps(obj,indent=2,sort_keys=True)+"
",encoding="utf-8")
        elif p.suffix.lower()==".csv":
            if prediction_rows is None: prediction_rows=_prediction_rows(root,fit)
            if not prediction_rows: raise ValueError("PREDICTION_TIME_TABLE_NOT_FOUND")
            cols=list(prediction_rows[0].keys())
            with p.open("w",newline="",encoding="utf-8") as f:
                w=csv.DictWriter(f,fieldnames=cols); w.writeheader(); w.writerows(prediction_rows)
        elif p.suffix.lower() in {".md",".txt"}:
            lines=["# Deterministic zero-model joint orbit fit","","No external learned model or network cognition was used.","",f"- Period: {fit['period']:.12g}",f"- Eccentricity: {fit['eccentricity']:.12g}",f"- Periastron epoch: {fit['tau']:.12g}",f"- Weighted mean-square residual: {fit['weighted_mse']:.12g}"]
            if "rv" in fit: lines += [f"- RV semi-amplitude: {fit['rv']['K']:.12g}",f"- Systemic velocity: {fit['rv']['gamma']:.12g}"]
            if "astrometry" in fit: lines += [f"- Astrometric semi-major axis: {fit['astrometry']['semi_major_axis']:.12g}",f"- Inclination (rad): {fit['astrometry']['inclination']:.12g}"]
            p.write_text("
".join(lines)+"
",encoding="utf-8")
        else:
            raise ValueError("UNSUPPORTED_OUTPUT_FORMAT:"+p.suffix)
        written.append(str(p))
    return {"schema":SCHEMA,"status":"CONTRACT_EXECUTED","fit":fit,"written":written,"unresolved_template_fields":unresolved,"external_model_calls":0,"network_calls":0}
