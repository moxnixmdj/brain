import csv, io, math, re, urllib.parse, urllib.request
from difflib import SequenceMatcher

STOP={"the","a","an","of","in","on","to","and","is","was","what","which","who","does","do","did","has","have","had","from","by","for","at","this","that","graph","chart","bar","bars","line","value","values","percentage","percent","rate","share","year","years"}

def norm(s):
    return " ".join(re.findall(r"[a-z0-9]+(?:[./'-][a-z0-9]+)*",str(s).lower()))

def tokens(s):
    return [t for t in norm(s).split() if t not in STOP]

def num(s):
    t=str(s).strip().replace(",","").replace("$","").replace("%","")
    if not t or t.lower() in {"nan","na","n/a","null","none"}: return None
    try: v=float(t)
    except: return None
    return v if math.isfinite(v) else None

def fmt(v):
    if v is None: return None
    if abs(v-round(v))<1e-9: return str(int(round(v)))
    return ("%.8f"%v).rstrip("0").rstrip(".")

def table(rows):
    if not rows: return None
    w=max(len(r) for r in rows)
    rows=[list(r)+[""]*(w-len(r)) for r in rows]
    return {
      "headers":rows[0],
      "row_labels":[r[0] for r in rows[1:]],
      "rows":rows[1:],
      "matrix":[[num(c) for c in r[1:]] for r in rows[1:]]
    }

def label_score(label,q):
    nl=norm(label); nq=norm(q)
    if not nl: return 0
    if nl in nq: return 100+len(nl)
    lt=tokens(label); qt=set(tokens(q))
    if not lt: return 0
    overlap=sum(t in qt for t in lt)
    frac=overlap/len(lt)
    if frac==1: return 80+len(lt)
    if frac>=0.67: return 50*frac
    # useful for punctuation/date variants
    rat=SequenceMatcher(None,nl,nq).ratio()
    return 10*rat if rat>0.55 else 0

def matches(labels,q,minscore=1):
    out=[]
    for i,l in enumerate(labels):
        s=label_score(l,q)
        if s>=minscore: out.append((s,i,l))
    out.sort(reverse=True)
    return out

def numeric_cells(t):
    out=[]
    for ri,row in enumerate(t["matrix"]):
        for ci,v in enumerate(row):
            if v is not None: out.append((ri,ci,v))
    return out

def row_values(t,ri):
    return [(ci,v) for ci,v in enumerate(t["matrix"][ri]) if v is not None]

def col_values(t,ci):
    return [(ri,row[ci]) for ri,row in enumerate(t["matrix"]) if ci<len(row) and row[ci] is not None]

def get_value(t,ri,ci):
    if ri is None or ci is None: return None
    if ri>=len(t["matrix"]) or ci>=len(t["matrix"][ri]): return None
    return t["matrix"][ri][ci]

def best_row(t,q):
    m=matches(t["row_labels"],q)
    return m[0][1] if m else None

def best_col(t,q):
    # exclude first header cell; returned matrix col index
    m=matches(t["headers"][1:],q)
    return m[0][1] if m else None

def years_in_question(q):
    return re.findall(r"\b(?:19|20)\d{2}(?:/\d{2})?\b",q)

def threshold_in_question(q):
    vals=re.findall(r"(?<!\d)(\d+(?:\.\d+)?)\s*(?:\$|%|/barrel)?",q.replace(",",""))
    return [float(x) for x in vals]

def all_numeric(t):
    return [v for _,_,v in numeric_cells(t)]

def solve(q,rows):
    t=table(rows)
    if not t: return None
    qn=norm(q)
    qlow=q.lower()
    r=best_row(t,q)
    c=best_col(t,q)

    # direct one-row identity questions
    if any(p in qlow for p in ["which country is represented","which country does","which animal is represented"]):
        if len(t["row_labels"])==1:
            return t["row_labels"][0]

    # yes/no starting value vs lowest
    if ("starting value" in qlow and "lowest" in qlow):
        truths=[]
        for ri in range(len(t["matrix"])):
            vals=[v for _,v in row_values(t,ri)]
            if vals: truths.append(abs(vals[0]-min(vals))<1e-9)
        if truths and all(x==truths[0] for x in truths):
            return "Yes" if truths[0] else "No"

    # ratio
    if "ratio" in qlow:
        rms=matches(t["row_labels"],q)
        cms=matches(t["headers"][1:],q)
        if len(rms)>=2 and len(t["headers"])==2:
            a=get_value(t,rms[0][1],0); b=get_value(t,rms[1][1],0)
            if a is not None and b not in (None,0): return fmt(a/b)
        if r is not None and len(cms)>=2:
            a=get_value(t,r,cms[0][1]); b=get_value(t,r,cms[1][1])
            if a is not None and b not in (None,0): return fmt(a/b)

    # counts
    if "how many" in qlow or "covers how many" in qlow:
        if ("year" in qlow and any(x in qlow for x in ["smaller","less","below","under"])):
            ri=r if r is not None else (0 if len(t["row_labels"])==1 else None)
            ths=threshold_in_question(q)
            if ri is not None and ths:
                # ignore year tokens; last numerical threshold usually threshold
                th=ths[-1]
                return str(sum(v<th for _,v in row_values(t,ri)))
        if "bars" in qlow:
            vals=all_numeric(t)
            # one series by rows -> one bar per data row
            if len(t["headers"])==2: return str(sum(1 for ri in range(len(t["rows"])) if row_values(t,ri)))
            return str(len(vals))
        if "years" in qlow or "year" in qlow:
            # count row labels that look years, else year columns
            yrrows=[x for x in t["row_labels"] if re.search(r"\b(?:19|20)\d{2}",str(x))]
            yrcols=[x for x in t["headers"][1:] if re.search(r"\b(?:19|20)\d{2}",str(x))]
            if yrrows: return str(len(yrrows))
            if yrcols and ("how many years" in qlow or "covers how many" in qlow): return str(len(yrcols))
        if any(w in qlow for w in ["countries","regions","stations","firms","categories"]):
            return str(len([x for x in t["row_labels"] if str(x).strip()]))

    # averages
    if "average" in qlow:
        if "first two" in qlow:
            vals=all_numeric(t)
            if len(vals)>=2: return fmt((vals[0]+vals[1])/2)
        if r is not None:
            vals=[v for _,v in row_values(t,r)]
            if vals: return fmt(sum(vals)/len(vals))
        if "all the years" in qlow or "all years" in qlow:
            vals=all_numeric(t)
            if vals: return fmt(sum(vals)/len(vals))
        if any(x in qlow for x in ["lowest","least","highest","most"]):
            avgs=[]
            for ri,lbl in enumerate(t["row_labels"]):
                vals=[v for _,v in row_values(t,ri)]
                if vals: avgs.append((sum(vals)/len(vals),lbl))
            if avgs:
                avgs.sort()
                return avgs[-1][1] if any(x in qlow for x in ["highest","most"]) else avgs[0][1]

    # sum / total
    if "sum" in qlow or "total" in qlow:
        rms=matches(t["row_labels"],q)
        cms=matches(t["headers"][1:],q)
        if "top two" in qlow:
            vals=sorted(all_numeric(t),reverse=True)
            if len(vals)>=2: return fmt(vals[0]+vals[1])
        if len(rms)>=2 and len(t["headers"])==2:
            vals=[get_value(t,x[1],0) for x in rms[:2]]
            if all(v is not None for v in vals): return fmt(sum(vals))
        if r is not None:
            vals=[v for _,v in row_values(t,r)]
            # if explicit matched columns, sum those
            if len(cms)>=2:
                vv=[get_value(t,r,x[1]) for x in cms]
                vv=[x for x in vv if x is not None]
                if vv: return fmt(sum(vv))
            if vals: return fmt(sum(vals))
        if len(cms)>=2 and len(t["row_labels"])==1:
            vals=[get_value(t,0,x[1]) for x in cms]
            vals=[x for x in vals if x is not None]
            if vals: return fmt(sum(vals))

    # difference
    if "difference" in qlow or "differencebetween" in qlow:
        rms=matches(t["row_labels"],q)
        cms=matches(t["headers"][1:],q)
        if len(rms)>=2 and len(t["headers"])==2:
            a=get_value(t,rms[0][1],0); b=get_value(t,rms[1][1],0)
            if a is not None and b is not None: return fmt(abs(a-b))
        if r is not None and len(cms)>=2:
            a=get_value(t,r,cms[0][1]); b=get_value(t,r,cms[1][1])
            if a is not None and b is not None: return fmt(abs(a-b))
        if len(cms)>=1 and len(t["row_labels"])>=2:
            ci=cms[0][1]; vals=[v for _,v in col_values(t,ci)]
            if len(vals)>=2: return fmt(abs(vals[0]-vals[1]))

    # trend/order condition
    if "increasing order" in qlow:
        cms=matches(t["headers"][1:],q)
        if len(cms)>=3:
            # restore order as mentioned in question
            ordered=sorted(cms,key=lambda x: qlow.find(norm(x[2])))
            for ri,lbl in enumerate(t["row_labels"]):
                vals=[get_value(t,ri,x[1]) for x in ordered]
                if all(v is not None for v in vals) and all(vals[i]<vals[i+1] for i in range(len(vals)-1)):
                    return lbl

    # extrema / rank
    high_words=["highest","maximum","longest","biggest","most","busiest","largest"]
    low_words=["lowest","minimum","least","shortest"]
    want_high=any(w in qlow for w in high_words)
    want_low=any(w in qlow for w in low_words)
    if "second largest" in qlow:
        vals=[]
        for ri,lbl in enumerate(t["row_labels"]):
            rv=[v for _,v in row_values(t,ri)]
            if rv: vals.append((max(rv),lbl))
        vals.sort(reverse=True)
        if len(vals)>=2:return vals[1][1]
    if want_high or want_low:
        # named row -> return time/header of extremum
        if r is not None and len(row_values(t,r))>1 and any(x in qlow for x in ["which period","which year","between which two years","when"]):
            vals=row_values(t,r)
            ci,v=(max(vals,key=lambda x:x[1]) if want_high else min(vals,key=lambda x:x[1]))
            return t["headers"][ci+1]
        # named years -> category with smallest diff etc handled above
        yrs=years_in_question(q)
        if len(yrs)>=2 and ("difference" in qlow or "least" in qlow):
            idx=[]
            for y in yrs:
                for ci,h in enumerate(t["headers"][1:]):
                    if y in str(h): idx.append(ci); break
            if len(idx)>=2:
                choices=[]
                for ri,lbl in enumerate(t["row_labels"]):
                    a=get_value(t,ri,idx[0]); b=get_value(t,ri,idx[1])
                    if a is not None and b is not None: choices.append((abs(a-b),lbl))
                if choices:
                    choices.sort()
                    return choices[0][1]
        # simple category argmax/min
        choices=[]
        for ri,lbl in enumerate(t["row_labels"]):
            vals=[v for _,v in row_values(t,ri)]
            if vals:
                score=max(vals) if len(vals)>1 else vals[0]
                choices.append((score,lbl))
        if choices:
            choices.sort()
            # if query asks "what is highest value" return numeric
            if re.search(r"\b(?:what|what's)\b.*\b(?:highest|lowest|maximum|minimum)\s+value",qlow):
                vals=all_numeric(t)
                if vals: return fmt(max(vals) if want_high else min(vals))
            return choices[-1][1] if want_high else choices[0][1]

    # named value lookup
    if r is not None:
        if c is not None:
            v=get_value(t,r,c)
            if v is not None: return fmt(v)
        vals=[v for _,v in row_values(t,r)]
        if len(vals)==1: return fmt(vals[0])
    if c is not None and len(t["row_labels"])==1:
        v=get_value(t,0,c)
        if v is not None:return fmt(v)

    # one-row country represented
    if len(t["row_labels"])==1 and any(x in qlow for x in ["which country","represented by"]):
        return t["row_labels"][0]

    return None
