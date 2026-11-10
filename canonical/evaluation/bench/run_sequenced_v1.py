"""The r76 prediction, tested: give the benchmark policy the per-step gate it never had.

Predicted before running (r76): if sequencing is the constraint, a per-step causal gate plus
a retry on a no-op should recover a meaningful part of the 37 parsed-but-failed tasks.

Design, and why each part is honest:

  SUBGOALS   from the goal's parse: one per named target, then submit if the goal says so.
  CANDIDATES ranked addressings for each subgoal (exact name, text equal, text contains).
  GATE       act_loop_v1.causal_check between screenshots, per step. A step that changes
             nothing is a FAILED step, not a step that happened.
  RETRY      on a failed step, the next candidate is tried. This is the whole experiment.
  SCORING    the page's reward, read ONCE at the end. Never during. Never to choose.

The only difference from v3 is the gate and the retry. Everything else is held fixed.
"""
import json, sys, time, pathlib
SUFFIX = sys.argv[1] if len(sys.argv) > 1 else "v1"
sys.path.insert(0, "/home/user/brain")
from canonical.runtime import bench_miniwob_v1 as B, address_v1 as A, bench_parse_v1 as PP
from canonical.runtime import act_loop_v1 as L

tasks = sorted(p.stem for p in pathlib.Path("/tmp/miniwob++/miniwob/html/miniwob").glob("*.html"))
ch = B.ScoreChannel()
t0 = time.time()

def centre(n):
    b = n["box"]; return ((b["x0"]+b["x1"])/2.0, (b["y0"]+b["y1"])/2.0)

def snap():
    a = A.Address(A.target_url())
    ns = [n for n in A.ax_nodes(a) if n["box"]]
    tx = [n for n in A.read_text(a) if n["box"]]
    a.close(); return ns, tx

POOL = ("button","link","option","tab","menuitem","listitem","radio","checkbox",
        "combobox","textbox","switch","treeitem","cell","gridcell")

def candidates(name, ns, tx, goal_norm):
    low = " ".join(name.lower().split()).strip(" .,;:")
    if not low: return []
    out = []
    pool = [n for n in ns if n["role"] in POOL]
    for n in pool:
        if n["name"].strip().lower().strip(" .,;:") == low: out.append(n)
    for n in tx:
        got = " ".join(n["name"].lower().split()).strip(" .,;:")
        if got and got != goal_norm and got == low: out.append(n)
    for n in pool:
        if low in n["name"].strip().lower() and n not in out: out.append(n)
    for n in tx:
        got = " ".join(n["name"].lower().split()).strip(" .,;:")
        if got and goal_norm not in got and low in got and n not in out: out.append(n)
    return out[:4]

def subgoals(plan, ns, tx, gnorm):
    k = plan["kind"]
    sg = []
    if k in ("click_set",):
        for nm in plan["names"]: sg.append({"do": "click_name", "name": nm})
        if plan.get("submit"): sg.append({"do": "submit"})
    elif k in ("click_named", "search_then_click"):
        if plan.get("name"): sg.append({"do": "click_name", "name": plan["name"]})
        if plan.get("submit"): sg.append({"do": "submit"})
    elif k == "click_single_button":
        sg.append({"do": "submit"})
    elif k == "click_nth_tab":
        sg.append({"do": "nth_tab", "n": plan["n"]})
    elif k in ("type_literal","enter_date","enter_time","word_by_index","read_table"):
        sg.append({"do": "type", "plan": plan})
        if plan.get("submit"): sg.append({"do": "submit"})
    return sg

def do_step(s, ns, tx, gnorm):
    if s["do"] == "submit":
        if not any(w in gnorm for w in ("submit", "press", "hit")):
            return []          # the goal never asked for it
        for n in ns:
            if n["role"] == "button" and n["name"].strip().lower() in ("submit","send","go","done"):
                return [n]
        return []
    if s["do"] == "nth_tab":
        tabs = [n for n in ns if n["role"] in ("tab","listitem","option","link")]
        return [tabs[s["n"]-1]] if 0 < s["n"] <= len(tabs) else []
    if s["do"] == "type":
        tb = [n for n in ns if n["role"] in ("textbox","combobox","searchbox")]
        return tb[:1]
    return candidates(s["name"], ns, tx, gnorm)

rows = []
for i, t in enumerate(tasks, 1):
    r = {"task": t, "steps_ok": 0, "steps_failed": 0, "actions": 0, "error": None}
    try:
        ch.navigate(B.BASE.format(task=t)); time.sleep(0.95)
        ch.click(80, 104); time.sleep(0.95)
        goal = ch.goal(); r["goal"] = goal[:110]
        if not goal:
            r["error"] = "NO_GOAL"; raise RuntimeError("no goal")
        gnorm = " ".join(goal.lower().split())
        plan = PP.parse(goal); r["plan"] = plan["kind"]
        ns, tx = snap()
        sg = subgoals(plan, ns, tx, gnorm)
        r["subgoals"] = len(sg)
        cur = f"/tmp/seq/{t}_00.png"
        pathlib.Path("/tmp/seq").mkdir(exist_ok=True)
        ch.screenshot(cur)
        for si, s in enumerate(sg, 1):
            done = False
            for ci, cand in enumerate(do_step(s, ns, tx, gnorm)):
                nxt = f"/tmp/seq/{t}_{si}_{ci}.png"
                ch.click(*centre(cand)); r["actions"] += 1
                time.sleep(0.45); ch.screenshot(nxt)
                box = cand["box"]
                cc = L.causal_check(cur, nxt, [box["x0"]-4, box["y0"]-4, box["x1"]+4, box["y1"]+4],
                                    expect="some")
                if cc["verdict"] == "CAUSAL_OK":
                    r["steps_ok"] += 1; done = True; cur = nxt; break
                r["steps_failed"] += 1
                if s["do"] == "type" and ci == 0:
                    ch.type_text(s["plan"]["text"]); r["actions"] += 1
                    time.sleep(0.3); ch.screenshot(nxt)
                    cc2 = L.causal_check(cur, nxt, None, expect="some")
                    if cc2["verdict"] == "CAUSAL_OK":
                        r["steps_ok"] += 1; done = True; cur = nxt; break
            if s["do"] == "type" and done:
                nxt2 = f"/tmp/seq/{t}_{si}_type.png"
                ch.type_text(s["plan"]["text"]); r["actions"] += 1
                time.sleep(0.35); ch.screenshot(nxt2)
                cc3 = L.causal_check(cur, nxt2, None, expect="some")
                if cc3["verdict"] == "CAUSAL_OK":
                    r["steps_ok"] += 1; cur = nxt2
                else:
                    r["steps_failed"] += 1
            ns, tx = snap()
    except Exception as e:
        if not r["error"]: r["error"] = str(e)[:90]
    time.sleep(0.35)
    try: st = ch.reward()
    except Exception: st = {}
    r["done"] = bool(st.get("done")); r["reward"] = st.get("reward")
    rows.append(r)
    if i % 25 == 0: print(f"  {i}/{len(tasks)} ({time.time()-t0:.0f}s)", flush=True)
ch.close()

win = [x for x in rows if x["done"] and isinstance(x["reward"],(int,float)) and x["reward"] > 0]
out = pathlib.Path(f"/home/user/brain/canonical/evaluation/bench/result_sequenced_{SUFFIX}.json")
out.write_text(json.dumps({"n":len(rows),"success":len(win),"seconds":round(time.time()-t0,1),
                           "success_rate":round(len(win)/len(rows)*100,1),"tasks":rows}, indent=1))
print(f"\nSEQUENCED+GATED: {len(win)}/130 = {len(win)/len(rows)*100:.1f}%  ({time.time()-t0:.0f}s)")
print(f"  [v3 policy: 17, baseline: 15]")
print("WINNERS:", ", ".join(x["task"] for x in win))
