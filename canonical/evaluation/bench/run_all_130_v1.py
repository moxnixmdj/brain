"""All 130 tasks. No selection by me -- the list is `ls *.html`. This is the honest number."""
import json, sys, time, pathlib
sys.path.insert(0, "/home/user/brain")
from canonical.runtime import bench_miniwob_v1 as B, bench_policy_v1 as P, address_v1 as A

tasks = sorted(p.stem for p in pathlib.Path("/tmp/miniwob++/miniwob/html/miniwob").glob("*.html"))
ch = B.ScoreChannel()
rows = []
t0 = time.time()
for i, t in enumerate(tasks, 1):
    r = {"task": t, "actions": 0, "rung": "ADDRESSED", "error": None}
    try:
        ch.navigate(B.BASE.format(task=t)); time.sleep(1.0)
        ch.click(80, 104); time.sleep(1.0)
        goal = ch.goal()
        r["goal"] = goal[:110]
        if not goal:
            r["error"] = "NO_GOAL"
            raise RuntimeError("no goal")
        plan = P.want(goal); r["plan"] = plan["kind"]
        a = A.Address(A.target_url()); nodes = [n for n in A.ax_nodes(a) if n["box"]]; a.close()
        r["nodes"] = len(nodes)
        if plan["kind"] == "click_two":
            for nm in plan["names"]:
                a = A.Address(A.target_url()); ns = [n for n in A.ax_nodes(a) if n["box"]]; a.close()
                hit = P.choose(ns, {"kind": "click_named", "name": nm})
                if not hit: break
                ch.click(*P.centre(hit)); r["actions"] += 1; time.sleep(2.0)
        elif plan["kind"] == "type_named":
            tb = P.textbox(nodes)
            if tb:
                ch.click(*P.centre(tb)); time.sleep(0.25)
                ch.type_text(plan["text"]); r["actions"] += 1; time.sleep(0.2)
                sb = P.submit_button(nodes)
                if sb: ch.click(*P.centre(sb)); r["actions"] += 1
        elif plan["kind"] in ("click_named", "click_first", "click_nth_tab"):
            tgt = P.choose(nodes, plan)
            if tgt:
                ch.click(*P.centre(tgt)); r["actions"] += 1; time.sleep(0.3)
                if not ch.reward().get("done"):
                    a = A.Address(A.target_url()); n2 = [n for n in A.ax_nodes(a) if n["box"]]; a.close()
                    sb = P.submit_button(n2)
                    if sb and sb["name"].strip().lower() == "submit":
                        ch.click(*P.centre(sb)); r["actions"] += 1
    except Exception as e:
        if not r["error"]: r["error"] = str(e)[:90]
    time.sleep(0.4)
    try:
        st = ch.reward()
    except Exception:
        st = {}
    r["done"] = bool(st.get("done")); r["reward"] = st.get("reward")
    rows.append(r)
    if i % 20 == 0: print(f"  {i}/{len(tasks)}  ({time.time()-t0:.0f}s)", flush=True)
ch.close()
win = [x for x in rows if x["done"] and isinstance(x["reward"], (int, float)) and x["reward"] > 0]
out = pathlib.Path("/home/user/brain/canonical/evaluation/bench/result_all_130_v1.json")
out.write_text(json.dumps({"n": len(rows), "success": len(win), "seconds": round(time.time()-t0,1),
                           "success_rate": round(len(win)/len(rows)*100,1), "tasks": rows}, indent=1))
print(f"\nALL 130: success {len(win)}/{len(rows)} = {len(win)/len(rows)*100:.1f}%  ({time.time()-t0:.0f}s)")
byplan = {}
for x in rows:
    p = x.get("plan", "none"); byplan.setdefault(p, [0,0]); byplan[p][1]+=1
    if x in win: byplan[p][0]+=1
for p,(w,n) in sorted(byplan.items(), key=lambda kv:-kv[1][1]):
    print(f"   {p:14s} {w:3d}/{n:3d}  {w/n*100:5.1f}%")
