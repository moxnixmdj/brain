"""All 130 again, with the parsed grammar. Same page, same reward rule, same reading rules.

Only the goal parser changed. Anything that improves here is attributable to reading the
instruction better, not to acting better -- the addressing and the gate are untouched.
"""
import json, sys, time, pathlib, re
re_ok = lambda s: bool(re.search(r"expand|more|show|tab|menu", s, re.I))
sys.path.insert(0, "/home/user/brain")
from canonical.runtime import bench_miniwob_v1 as B, address_v1 as A, bench_parse_v1 as PP
from canonical.runtime import bench_policy_v1 as P

T = PP
tasks = sorted(p.stem for p in pathlib.Path("/tmp/miniwob++/miniwob/html/miniwob").glob("*.html"))
ch = B.ScoreChannel()
rows = []
t0 = time.time()

def centre(n):
    b = n["box"]; return ((b["x0"] + b["x1"]) / 2.0, (b["y0"] + b["y1"]) / 2.0)

def nodes():
    a = A.Address(A.target_url()); ns = [n for n in A.ax_nodes(a) if n["box"]]; a.close(); return ns

def texts():
    a = A.Address(A.target_url()); ts = A.read_text(a); a.close(); return ts

def click_named(name, ns):
    low = name.strip().lower().rstrip(".")
    pool = [n for n in ns if n["role"] in ("button","link","option","tab","menuitem","listitem",
                                           "radio","checkbox","combobox","textbox")]
    for test in (lambda n: n["name"].strip().lower().rstrip(".") == low,
                 lambda n: low in n["name"].strip().lower(),
                 lambda n: n["name"].strip().lower().rstrip(".") in low):
        hit = [n for n in pool if test(n)]
        if hit: return hit[0]
    return None

def submit(ns):
    for n in ns:
        if n["role"] == "button" and n["name"].strip().lower() in ("submit","send","go","done"):
            return n
    return None

for i, t in enumerate(tasks, 1):
    r = {"task": t, "actions": 0, "rung": "ADDRESSED", "error": None}
    try:
        ch.navigate(B.BASE.format(task=t)); time.sleep(1.0)
        ch.click(80, 104); time.sleep(1.0)
        goal = ch.goal(); r["goal"] = goal[:110]
        if not goal:
            r["error"] = "NO_GOAL"; raise RuntimeError("no goal")
        plan = PP.parse(goal); r["plan"] = plan["kind"]; r["plan_detail"] = {k:v for k,v in plan.items() if k!="kind"}
        k = plan["kind"]
        if k in ("click_named", "click_set", "click_nth_tab", "click_single_button"):
            applied = 0
            if k == "click_set":
                for nm in plan["names"]:
                    hit = click_named(nm, nodes())
                    if hit: ch.click(*centre(hit)); applied += 1; time.sleep(0.25)
            elif k == "click_nth_tab":
                tabs = [n for n in nodes() if n["role"] in ("tab","listitem","option","link")]
                if 0 < plan["n"] <= len(tabs):
                    ch.click(*centre(tabs[plan["n"]-1])); applied += 1
            elif k == "click_single_button":
                hit = [n for n in nodes() if n["role"] == "button"]
                if hit: ch.click(*centre(hit[0])); applied += 1
            else:
                hit = click_named(plan["name"], nodes())
                if not hit and len(plan["name"].strip()) <= 2:
                    close = [n for n in nodes() if n["role"] == "button"
                             and n["name"].strip().lower() in ("close","dismiss","cancel","x")]
                    hit = close[0] if close else None
                if hit: ch.click(*centre(hit)); applied += 1; time.sleep(0.3)
                if not hit and plan.get("disclose"):
                    d = [n for n in nodes() if n["role"] in ("button","link","tab")
                         and re_ok(n["name"])]
                    if d: ch.click(*centre(d[0])); applied += 1; time.sleep(0.5)
                    hit = click_named(plan["name"], nodes())
                    if hit: ch.click(*centre(hit)); applied += 1
            r["actions"] = applied
            if plan.get("submit") and not ch.reward().get("done"):
                sb = submit(nodes())
                if sb: ch.click(*centre(sb)); r["actions"] += 1
        elif k in ("type_literal", "enter_date", "enter_time", "word_by_index", "read_table"):
            ns = nodes()
            tb = [n for n in ns if n["role"] in ("textbox","combobox","searchbox")]
            val = None
            if k in ("type_literal","enter_date","enter_time"): val = plan["text"]
            elif k == "word_by_index":
                ws = [w for n in texts() for w in n["name"].split()]
                if plan["n"] == -1 and ws: val = ws[-1].strip(".,;:")
                elif 0 < plan["n"] <= len(ws): val = ws[plan["n"]-1].strip(".,;:")
            elif k == "read_table":
                lab = plan["label"].lower()
                for n in texts():
                    if lab in n["name"].lower():
                        parts = n["name"].split()
                        if len(parts) > 1: val = parts[-1]; break
            if tb and val:
                ch.click(*centre(tb[0])); time.sleep(0.3); ch.type_text(val); r["actions"] += 1
                time.sleep(0.25)
                if plan.get("submit"):
                    sb = submit(nodes())
                    if sb: ch.click(*centre(sb)); r["actions"] += 1
        elif k == "search_then_click":
            # one shape, many sites: reveal, then look, then click. Bounded to 6 reveals.
            revealed, hit = 0, None
            if plan.get("name"):
                hit = click_named(plan["name"], nodes())
            for _ in range(6):
                if hit: break
                ns_all = nodes()
                # structural, not lexical: an expander is a tab/listitem/menuitem by ROLE.
                # MiniWob calls them "Section #1"; matching the word "expand" finds nothing.
                structural = [n for n in ns_all if n["role"] in
                              ("tab", "listitem", "menuitem", "option")]
                lexical = [n for n in ns_all if n["role"] in ("button", "link")
                           and re_ok(n["name"])]
                cand = structural or lexical
                if not cand: break
                ch.click(*centre(cand[revealed % len(cand)])); revealed += 1; time.sleep(0.35)
                r["actions"] += 1
                ns = nodes()
                if plan.get("name"):
                    hit = click_named(plan["name"], ns)
                    if not hit:   # some sites label the closer by what it does, not by "x"
                        hit = [n for n in ns if n["role"] == "button"
                               and n["name"].strip().lower() in ("close","x","dismiss","cancel")]
                        hit = hit[0] if hit else None
            if not hit and plan.get("name") and len(plan["name"].strip()) <= 2:
                close = [n for n in nodes() if n["role"] == "button"
                         and n["name"].strip().lower() in ("close", "dismiss", "cancel", "x")]
                hit = close[0] if close else None
            if not hit and plan.get("name"):
                # the name may only become addressable after a reveal
                pass
            if hit:
                ch.click(*centre(hit)); r["actions"] += 1; time.sleep(0.3)
            if plan.get("submit") and not ch.reward().get("done"):
                sb = submit(nodes())
                if sb: ch.click(*centre(sb)); r["actions"] += 1
        elif k == "copy_paste":
            ns = nodes(); tbs = [n for n in ns if n["role"] == "textbox"]
            if len(tbs) >= 2:
                src = tbs[min(plan["source_index"]-1, len(tbs)-1)]
                ch.click(*centre(src)); ch.call("Input.dispatchKeyEvent",
                    {"type":"keyDown","modifiers":2,"key":"a","code":"KeyA",
                     "windowsVirtualKeyCode":65,"nativeVirtualKeyCode":65})
                ch.call("Input.dispatchKeyEvent",
                    {"type":"keyDown","modifiers":2,"key":"c","code":"KeyC",
                     "windowsVirtualKeyCode":67,"nativeVirtualKeyCode":67})
                r["actions"] += 1
    except Exception as e:
        if not r["error"]: r["error"] = str(e)[:90]
    time.sleep(0.4)
    try: st = ch.reward()
    except Exception: st = {}
    r["done"] = bool(st.get("done")); r["reward"] = st.get("reward")
    rows.append(r)
    if i % 25 == 0: print(f"  {i}/{len(tasks)} ({time.time()-t0:.0f}s)", flush=True)
ch.close()
win = [x for x in rows if x["done"] and isinstance(x["reward"], (int,float)) and x["reward"] > 0]
out = pathlib.Path("/home/user/brain/canonical/evaluation/bench/result_all_130_v2_parser.json")
out.write_text(json.dumps({"n":len(rows),"success":len(win),"seconds":round(time.time()-t0,1),
                           "success_rate":round(len(win)/len(rows)*100,1),"tasks":rows}, indent=1))
print(f"\nPARSER: {len(win)}/130 = {len(win)/len(rows)*100:.1f}%  ({time.time()-t0:.0f}s)   [was 15/130=11.5%]")
bp={}
for x in rows:
    p=x.get("plan","none"); bp.setdefault(p,[0,0]); bp[p][1]+=1
    if x in win: bp[p][0]+=1
for p,(w,n) in sorted(bp.items(), key=lambda kv:-kv[1][1]):
    print(f"   {p:22s} {w:3d}/{n:3d}  {w/n*100:5.1f}%")
