"""Does the target exist before any action? A measurement with no parser in it.

The only thing read from the goal is a QUOTED LITERAL -- pure string extraction with no
semantic decision. Then: does that literal appear in the accessible names of the settled
initial screen? No parsing means no tuning set. The answer cannot be improved by editing the
parser, which is exactly what makes it evidence.

Also records, for tasks with no quoted literal, that they are out of scope for this measure.
"""
import json, sys, time, pathlib, re
sys.path.insert(0, "/home/user/brain")
from canonical.runtime import bench_miniwob_v1 as B, address_v1 as A

QUOTED = re.compile(r'["\u201c\u2018]([^"\u201d\u2019]{1,60})["\u201d\u2019]')
tasks = sorted(p.stem for p in pathlib.Path("/tmp/miniwob++/miniwob/html/miniwob").glob("*.html"))
ch = B.ScoreChannel()
rows = []
t0 = time.time()
for i, t in enumerate(tasks, 1):
    r = {"task": t}
    try:
        ch.navigate(B.BASE.format(task=t)); time.sleep(1.0)
        ch.click(80, 104); time.sleep(1.15)
        goal = ch.goal(); r["goal"] = goal[:110]
        m = QUOTED.search(goal)
        r["literal"] = m.group(1).strip() if m else None
        a = A.Address(A.target_url())
        nodes = [n for n in A.ax_nodes(a) if n["box"]]
        a.close()
        r["nodes"] = len(nodes)
        r["roles"] = sorted({n["role"] for n in nodes})[:10]
        if r["literal"]:
            low = r["literal"].lower()
            names = " || ".join(n["name"].lower() for n in nodes)
            r["on_screen_at_t0"] = low in names
        else:
            r["on_screen_at_t0"] = None
    except Exception as e:
        r["error"] = str(e)[:90]
    rows.append(r)
    if i % 30 == 0:
        print(f"  {i}/{len(tasks)} ({time.time()-t0:.0f}s)", flush=True)
ch.close()
out = pathlib.Path("/home/user/brain/canonical/evaluation/bench/ordering_130_v1.json")
out.write_text(json.dumps(rows, indent=1))

named = [r for r in rows if r.get("literal")]
on = [r for r in named if r.get("on_screen_at_t0")]
off = [r for r in named if not r.get("on_screen_at_t0")]
print(f"\ntasks {len(rows)}")
print(f"  goal names a literal          {len(named):3d}")
print(f"    literal ON screen at t0     {len(on):3d}   ({len(on)/max(1,len(named))*100:.0f}% of named)")
print(f"    literal NOT on screen at t0 {len(off):3d}   ({len(off)/max(1,len(named))*100:.0f}%)")
print(f"  goal names no literal         {len(rows)-len(named):3d}")
