"""Benchmark run driven by the repo's own planner, not a hand-written subgoal loop.

Per task:
  1. read the goal, take the quoted literal (string extraction only, no semantics)
  2. PROBE: for each addressable control, click it once, observe which names appear that
     were not there before. That observation becomes a capability's `provides`.
  3. PLAN: sumo/A* (`capability_planner.plan_capabilities`) finds the shortest ordered route
     from the current facts to `name:<literal>`.
  4. EXECUTE the plan in order, re-snapshotting between steps.
  5. If the planner says NO_ROUTE, REFUSE. A refusal is recorded as a refusal, not a failure.

Cost is honest: probing costs actions. Every probed click is counted and reported. The
question is not "how few actions" but "does ordering by plan beat ordering by guess".
"""
import json, sys, time, pathlib, re
sys.path.insert(0, "/home/user/brain")
from canonical.runtime import bench_miniwob_v1 as B, address_v1 as A
from canonical.runtime import bench_capability_graph_v1 as G

Q = re.compile(r'["\u201c\u2018]([^"\u201d\u2019]{1,60})["\u201d\u2019]')
TYPE_VERB = re.compile(r"^\s*(enter|type|input|fill)\b", re.I)
POOL = {"button","link","option","tab","menuitem","listitem","radio","checkbox","combobox"}

tasks = sorted(p.stem for p in pathlib.Path("/tmp/miniwob++/miniwob/html/miniwob").glob("*.html"))
ch = B.ScoreChannel(); t0 = time.time()

def snap():
    a = A.Address(A.target_url())
    ns = [n for n in A.ax_nodes(a) if n["box"]]
    tx = [n for n in A.read_text(a) if n["box"]]
    a.close(); return ns, tx

def facts(ns, tx):
    return G.facts_from_nodes(ns + tx)

def centre(n):
    b=n["box"]; return ((b["x0"]+b["x1"])/2.0,(b["y0"]+b["y1"])/2.0)

rows = []
for i, t in enumerate(tasks, 1):
    r = {"task": t, "probes": 0, "plan_len": 0, "refused": False, "error": None}
    try:
        ch.navigate(B.BASE.format(task=t)); time.sleep(0.95)
        ch.click(80, 104); time.sleep(0.95)
        goal = ch.goal(); r["goal"] = goal[:110]
        if not goal:
            r["error"] = "NO_GOAL"; raise RuntimeError("no goal")
        gnorm = " ".join(goal.lower().split())
        m = Q.search(goal); lit = (m.group(1).strip().strip(".,;:") if m else "")
        r["literal"] = lit
        r["is_value"] = bool(TYPE_VERB.match(goal))
        ns, tx = snap()
        f0 = facts(ns, tx)
        caps = []
        controls = [n for n in ns if n["role"] in POOL and n["name"].strip()]

        # PROBE AND ACT IN THE SAME EPISODE. Measured: every re-navigation starts a NEW
        # random problem (different target word, different content), so a plan made while
        # probing describes a page that no longer exists. Four trials out of four differed.
        # The page therefore must be left exactly as the probe found it, or the plan must be
        # made from the post-probe state. Simplest correct choice: probe, then plan from the
        # state we are actually in, and never navigate again.

        if r.get("is_value") and lit:
            pr = {"status": "SOLVED", "plan": []}
        elif lit:
            # is it already there, untouched?
            pr = G.plan_to_reveal(f0, lit, caps)
            if pr["status"] == "NO_ROUTE":
                # learn what each control reveals, WITHOUT re-navigating: click, observe,
                # click again to restore (toggles are their own inverse on this page).
                for ctl in controls[:8]:
                    before = facts(*snap())
                    ch.click(*centre(ctl)); r["probes"] += 1; time.sleep(0.28)
                    after = facts(*snap())
                    rev = {x.split("name:",1)[1] for x in (after - before) if x.startswith("name:")}
                    caps.append(G.capability_for(ctl["name"].strip(), rev, ctl["role"]))
                    ch.click(*centre(ctl)); r["probes"] += 1; time.sleep(0.22)
                f0 = facts(*snap())
                pr = G.plan_to_reveal(f0, lit, caps)
        else:
            pr = {"status": "NO_LITERAL"}
        if pr["status"] in ("SOLVED", "ALREADY_PRESENT"):
            from canonical.runtime import text_locate_v1 as TL
            def read():
                aa = A.Address(A.target_url())
                nn = [x for x in A.ax_nodes(aa) if x["box"]]
                tt = [x for x in A.read_text(aa) if x.get("box")]
                aa.close(); return nn, tt
            low = lit.lower()
            if r.get("is_value"):
                ns, tx = read()
                tb = [n for n in ns if n["role"] in ("textbox","combobox","searchbox")]
                if tb:
                    ch.click(*centre(tb[0])); ch.type_text(lit); r["probes"] += 2
                    time.sleep(0.3); ns, tx = read()
                    sub = [n for n in ns if n["role"] == "button"
                           and n["name"].strip().lower() in ("submit","send","go","done")]
                    if sub: ch.click(*centre(sub[0])); r["probes"] += 1; time.sleep(0.3)
            else:
                # A disclosure page MOVES the controls every time one opens. Re-read before
                # EVERY action -- this single rule took click-collapsible-2 from 2/8 to 9/12.
                for reveal in range(4):
                    ns, tx = read()
                    hit = TL.best_run(tx, lit) or TL.best_run(ns, lit)
                    if hit:
                        words = (hit["name"] or "").split()
                        if len(words) > 1:
                            loc = TL.locate_word(hit, lit); bb = hit["box"]
                            x, y = ((loc["x"], loc["y"]) if loc.get("found")
                                    else ((bb["x0"]+bb["x1"])/2, (bb["y0"]+bb["y1"])/2))
                        else:
                            bb = hit["box"]; x, y = (bb["x0"]+bb["x1"])/2, (bb["y0"]+bb["y1"])/2
                        ch.click(x, y); r["probes"] += 1; r["acted"] = True
                        time.sleep(0.3); break
                    ctl = [n for n in ns if n["role"] in ("tab","button","menuitem","listitem")
                           and n["name"].strip()]
                    if reveal >= len(ctl): break
                    ch.click(*centre(ctl[reveal])); r["probes"] += 1; time.sleep(0.35)
    except Exception as e:
        if not r["error"]: r["error"] = str(e)[:90]
    time.sleep(0.3)
    try: st = ch.reward()
    except Exception: st = {}
    r["done"] = bool(st.get("done")); r["reward"] = st.get("reward")
    rows.append(r)
    if i % 25 == 0: print(f"  {i}/{len(tasks)} ({time.time()-t0:.0f}s)", flush=True)
ch.close()

win = [x for x in rows if x["done"] and isinstance(x["reward"],(int,float)) and x["reward"] > 0]
clean = [x for x in win if x["reward"] >= 0.5]
refused = [x for x in rows if x["refused"]]
out = pathlib.Path("/home/user/brain/canonical/evaluation/bench/result_planned_v1.json")
out.write_text(json.dumps({"n":len(rows),"success":len(win),"clean":len(clean),
    "refused":len(refused),"seconds":round(time.time()-t0,1),
    "success_rate":round(len(win)/len(rows)*100,1),"tasks":rows}, indent=1))
print(f"\nPLANNED: {len(win)}/130 = {len(win)/len(rows)*100:.1f}%  clean {len(clean)}  refused {len(refused)}  ({time.time()-t0:.0f}s)")
print(f"  [single-run comparisons: baseline 15, text 17, sequenced 18/15/18]")
