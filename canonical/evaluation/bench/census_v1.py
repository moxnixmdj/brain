import json, sys, time, pathlib
sys.path.insert(0, "/home/user/brain")
from canonical.runtime import bench_miniwob_v1 as B, address_v1 as A

HTML = pathlib.Path("/tmp/miniwob++/miniwob/html/miniwob")
tasks = sorted(p.stem for p in HTML.glob("*.html"))

ch = B.ScoreChannel()
rows = []
for i, t in enumerate(tasks, 1):
    try:
        ch.navigate(B.BASE.format(task=t)); time.sleep(1.1)
        ch.click(80, 104)
        time.sleep(1.05)
        goal = ch.goal()
        a = A.Address(A.target_url())
        nodes = [n for n in A.ax_nodes(a) if n["box"]]
        a.close()
        roles = sorted({n["role"] for n in nodes})
        named = [n for n in nodes if n["name"].strip()]
        interactive = [n for n in nodes if n["role"] in
                       ("button","textbox","checkbox","radio","combobox","link",
                        "listbox","option","menuitem","tab","slider","spinbutton")]
        rows.append({"task": t, "goal": goal[:120], "nodes": len(nodes),
                     "named": len(named), "interactive": len(interactive),
                     "roles": roles[:8], "addressable": bool(named or interactive),
                     "canvas_only": (not roles) or roles == ["Canvas"]})
    except Exception as e:
        rows.append({"task": t, "error": str(e)[:120]})
    if i % 25 == 0:
        print(f"  {i}/{len(tasks)}", flush=True)
ch.close()

out = pathlib.Path("/home/user/brain/canonical/evaluation/bench/census_130_v1.json")
out.write_text(json.dumps(rows, indent=1))
ok = [r for r in rows if r.get("addressable")]
bad = [r for r in rows if r.get("canvas_only")]
err = [r for r in rows if r.get("error")]
print(f"\ntasks {len(rows)} | addressable {len(ok)} | canvas-only {len(bad)} | errors {len(err)}")
print(f"addressable fraction: {len(ok)/len(rows)*100:.1f}%")
print("canvas-only:", ", ".join(r["task"] for r in bad[:16]))
