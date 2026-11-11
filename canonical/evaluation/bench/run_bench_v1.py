"""Score on the public benchmark. Fixed task list, fixed seeds, no per-task tuning."""
import json, sys, time, pathlib
sys.path.insert(0, "/home/user/brain")
from canonical.runtime import bench_miniwob_v1 as B, bench_policy_v1 as P, address_v1 as A

TASKS = ["click-button", "click-button-sequence", "click-checkboxes", "click-option",
         "click-link", "click-tab", "click-dialog", "click-dialog-2", "choose-list",
         "enter-text", "enter-text-2", "simple-arithmetic", "login-user", "email-inbox",
         "terminal", "choose-date-easy", "click-checkboxes-soft", "click-menu",
         "click-menu-2", "enter-date", "enter-password", "enter-text-dynamic",
         "click-radio", "click-collapsible", "click-scroll-list"]

ch = B.ScoreChannel()
rows = []
t0 = time.time()
for t in TASKS:
    r = {"task": t, "actions": 0, "rung": "ADDRESSED"}
    try:
        ch.navigate(B.BASE.format(task=t)); time.sleep(1.05)
        ch.click(80, 104); time.sleep(1.05)
        goal = ch.goal()
        r["goal"] = goal[:110]
        if not goal:
            r["error"] = "NO_GOAL: the page did not start (cover never dismissed)"
        plan = P.want(goal)
        r["plan"] = plan["kind"]
        a = A.Address(A.target_url())
        nodes = [n for n in A.ax_nodes(a) if n["box"]]
        a.close()
        if plan["kind"] == "click_two":
            for nm in plan["names"]:
                a = A.Address(A.target_url())
                ns = [n for n in A.ax_nodes(a) if n["box"]]
                a.close()
                hit = P.choose(ns, {"kind": "click_named", "name": nm})
                if hit:
                    ch.click(*P.centre(hit)); r["actions"] += 1
                    time.sleep(2.1)
                else:
                    break
        elif plan["kind"] == "type_named":
            tb = P.textbox(nodes)
            if tb:
                ch.click(*P.centre(tb)); time.sleep(0.25)
                ch.type_text(plan["text"]); r["actions"] += 1
                time.sleep(0.2)
                sb = P.submit_button(nodes)
                if sb:
                    ch.click(*P.centre(sb)); r["actions"] += 1
        elif plan["kind"] in ("click_named", "click_first", "click_nth_tab"):
            tgt = P.choose(nodes, plan)
            if tgt:
                ch.click(*P.centre(tgt)); r["actions"] += 1
                time.sleep(0.3)
                # some tasks need an explicit submit after the choice
                if not ch.reward().get("done"):
                    a = A.Address(A.target_url())
                    nodes2 = [n for n in A.ax_nodes(a) if n["box"]]
                    a.close()
                    sb = P.submit_button(nodes2)
                    if sb and sb["name"].strip().lower() == "submit":
                        ch.click(*P.centre(sb)); r["actions"] += 1
    except Exception as e:
        r["error"] = str(e)[:100]
    time.sleep(0.45)
    st = ch.reward()
    r["done"] = bool(st.get("done"))
    r["reward"] = st.get("reward")
    r["reason"] = st.get("reason")
    rows.append(r)
    print(f"  {t:26s} {str(r['plan']):12s} done={r['done']!s:5s} reward={r['reward']}  goal={r.get('goal','')[:44]!r}", flush=True)
ch.close()

ok = [x for x in rows if x["done"] and isinstance(x["reward"], (int, float)) and x["reward"] > 0]
out = pathlib.Path("/home/user/brain/canonical/evaluation/bench/result_miniwob_v1.json")
out.write_text(json.dumps({"tasks": rows, "n": len(rows), "success": len(ok),
                           "seconds": round(time.time() - t0, 1),
                           "success_rate": round(len(ok) / len(rows) * 100, 1)}, indent=1))
print(f"\nSUCCESS {len(ok)}/{len(rows)} = {len(ok)/len(rows)*100:.1f}%   ({time.time()-t0:.0f}s)")
