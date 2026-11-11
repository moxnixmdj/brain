"""All 130, addresser now able to see TEXT and not only names.

ONE change from v2 (which scored 13/130): click_named falls back to find_text, and a value or
literal that appears only as StaticText is now addressable.

Prediction made in r75 before running: this beats 15/130, because most of the 22 literals
recorded as 'off screen at t0' were found at t0 once text nodes were included.
"""
import json, sys, time, pathlib, re
sys.path.insert(0, "/home/user/brain")
from canonical.runtime import bench_miniwob_v1 as B, address_v1 as A, bench_parse_v1 as PP

tasks = sorted(p.stem for p in pathlib.Path("/tmp/miniwob++/miniwob/html/miniwob").glob("*.html"))
ch = B.ScoreChannel()
rows, t0 = [], time.time()

def centre(n):
    b = n["box"]; return ((b["x0"] + b["x1"]) / 2.0, (b["y0"] + b["y1"]) / 2.0)

def snap():
    a = A.Address(A.target_url())
    ns = [n for n in A.ax_nodes(a) if n["box"]]
    tx = [n for n in A.read_text(a) if n["box"]]
    a.close(); return ns, tx

NAMED_POOL = ("button","link","option","tab","menuitem","listitem","radio","checkbox",
              "combobox","textbox","switch","treeitem","cell","gridcell")

def click_named(name, ns, tx, goal_norm=""):
    low = " ".join(name.lower().split()).strip(" .,;:")
    if not low: return None
    pool = [n for n in ns if n["role"] in NAMED_POOL]
    for test in (lambda n: n["name"].strip().lower().strip(" .,;:") == low,
                 lambda n: low in n["name"].strip().lower()):
        hit = [n for n in pool if test(n)]
        if hit: return hit[0]
    # TEXT fallback: the label is a StaticText sibling with no accessible name
    best = None
    for n in tx:
        got = " ".join(n["name"].lower().split()).strip(" .,;:")
        if not got or goal_norm and goal_norm in got:   # never match the instruction itself
            continue
        if got == low: return n
        if best is None and low in got: best = n
    return best

def submit(ns):
    for n in ns:
        if n["role"] == "button" and n["name"].strip().lower() in ("submit","send","go","done"):
            return n
    return None

for i, t in enumerate(tasks, 1):
    r = {"task": t, "actions": 0, "rung": "ADDRESSED", "error": None, "via": None}
    try:
        ch.navigate(B.BASE.format(task=t)); time.sleep(1.0)
        ch.click(80, 104); time.sleep(1.0)
        goal = ch.goal(); r["goal"] = goal[:110]
        if not goal:
            r["error"] = "NO_GOAL"; raise RuntimeError("no goal")
        gnorm = " ".join(goal.lower().split())
        plan = PP.parse(goal); r["plan"] = plan["kind"]
        k = plan["kind"]
        ns, tx = snap()

        if k in ("click_named","click_set","click_nth_tab","click_single_button","disclose_then_submit","search_then_click"):
            names = plan.get("names") or ([plan["name"]] if plan.get("name") else [])
            applied, hit_any = 0, False
            for nm in names:
                h = click_named(nm, ns, tx, gnorm)
                if h:
                    ch.click(*centre(h)); applied += 1; hit_any = True; time.sleep(0.3)
                    ns, tx = snap()
            if not hit_any and k in ("click_single_button",):
                btn = [n for n in ns if n["role"] == "button"]
                if btn: ch.click(*centre(btn[0])); applied += 1
            # reveal once, then retry (structural roles, no words)
            if not hit_any:
                for _ in range(6):
                    cands = [n for n in ns if n["role"] in ("tab","listitem","menuitem","button","option")
                             and not any(x in n["name"].lower() for x in ("submit","cancel"))]
                    if not cands: break
                    ch.click(*centre(cands[r.get("_r", 0) % len(cands)])); r["_r"] = r.get("_r", 0) + 1
                    applied += 1; time.sleep(0.3); ns, tx = snap()
                    for nm in names:
                        h = click_named(nm, ns, tx, gnorm)
                        if h:
                            ch.click(*centre(h)); applied += 1; hit_any = True; time.sleep(0.3)
                            ns, tx = snap(); break
                    if hit_any: break
            r["actions"] = applied
            if plan.get("submit") and not ch.reward().get("done"):
                sb = submit(ns)
                if sb: ch.click(*centre(sb)); r["actions"] += 1
        elif k in ("type_literal","enter_date","enter_time","word_by_index","read_table"):
            tb = [n for n in ns if n["role"] in ("textbox","combobox","searchbox")]
            val = None
            if k in ("type_literal","enter_date","enter_time"): val = plan["text"]
            elif k == "word_by_index":
                ws = [w for n in tx for w in n["name"].split()]
                if plan["n"] == -1 and ws: val = ws[-1].strip(".,;:")
                elif 0 < plan["n"] <= len(ws): val = ws[plan["n"]-1].strip(".,;:")
            elif k == "read_table":
                lab = plan["label"].lower()
                for n in tx:
                    if lab in n["name"].lower():
                        parts = n["name"].split()
                        if len(parts) > 1: val = parts[-1]; break
            if tb and val:
                ch.click(*centre(tb[0])); time.sleep(0.3); ch.type_text(val); r["actions"] += 1
                time.sleep(0.25)
                if plan.get("submit"):
                    ns2, _ = snap(); sb = submit(ns2)
                    if sb: ch.click(*centre(sb)); r["actions"] += 1
    except Exception as e:
        if not r["error"]: r["error"] = str(e)[:90]
    r.pop("_r", None)
    time.sleep(0.4)
    try: st = ch.reward()
    except Exception: st = {}
    r["done"] = bool(st.get("done")); r["reward"] = st.get("reward")
    rows.append(r)
    if i % 25 == 0: print(f"  {i}/{len(tasks)} ({time.time()-t0:.0f}s)", flush=True)
ch.close()

win = [x for x in rows if x["done"] and isinstance(x["reward"], (int,float)) and x["reward"] > 0]
out = pathlib.Path("/home/user/brain/canonical/evaluation/bench/result_all_130_v3_text.json")
out.write_text(json.dumps({"n":len(rows),"success":len(win),"seconds":round(time.time()-t0,1),
                           "success_rate":round(len(win)/len(rows)*100,1),"tasks":rows}, indent=1))
print(f"\nWITH TEXT: {len(win)}/130 = {len(win)/len(rows)*100:.1f}%   ({time.time()-t0:.0f}s)")
print(f"           [baseline 15/130 = 11.5%]")
print("WINNERS:", ", ".join(x["task"] for x in win))
