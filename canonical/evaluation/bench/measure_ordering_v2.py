"""v2 of the ordering measure. Same idea, three corrections to v1:

  1. v1 kept trailing punctuation inside the literal ("lacus,") so a correct match failed.
  2. v1 counted values-to-be-typed ("Leonie") as screen targets. They are not targets.
  3. v1 did not save the names, so the misses could not be checked by eye afterwards.

Still no parser: the classification uses only the goal's FIRST WORD.
"""
import json, sys, time, pathlib, re
sys.path.insert(0, "/home/user/brain")
from canonical.runtime import bench_miniwob_v1 as B, address_v1 as A

QUOTED = re.compile(r'["\u201c\u2018]([^"\u201d\u2019]{1,60})["\u201d\u2019]')
TYPE_VERB = re.compile(r"^\s*(enter|type|input|fill)\b", re.I)   # a VALUE, not a target

def norm(s):
    return re.sub(r"[^a-z0-9 ]", " ", s.lower()).strip()

tasks = sorted(p.stem for p in pathlib.Path("/tmp/miniwob++/miniwob/html/miniwob").glob("*.html"))
ch = B.ScoreChannel()
rows = []
for i, t in enumerate(tasks, 1):
    r = {"task": t}
    try:
        ch.navigate(B.BASE.format(task=t)); time.sleep(1.0)
        ch.click(80, 104); time.sleep(1.15)
        goal = ch.goal(); r["goal"] = goal[:110]
        m = QUOTED.search(goal)
        r["literal"] = m.group(1).strip().strip(".,;:") if m else None
        r["is_value_to_type"] = bool(TYPE_VERB.match(goal))
        a = A.Address(A.target_url())
        nodes = [n for n in A.ax_nodes(a) if n["box"]]
        a.close()
        r["nodes"] = len(nodes)
        r["roles"] = sorted({n["role"] for n in nodes})[:10]
        r["names"] = [n["name"][:40] for n in nodes if n["name"].strip()][:14]
        if r["literal"]:
            hay = norm(" || ".join(n["name"] for n in nodes))
            r["on_screen_at_t0"] = norm(r["literal"]) in hay
        else:
            r["on_screen_at_t0"] = None
    except Exception as e:
        r["error"] = str(e)[:90]
    rows.append(r)
    if i % 30 == 0: print(f"  {i}/{len(tasks)}", flush=True)
ch.close()
pathlib.Path("/home/user/brain/canonical/evaluation/bench/ordering_130_v2.json").write_text(
    json.dumps(rows, indent=1))

targets = [r for r in rows if r.get("literal") and not r["is_value_to_type"]]
values  = [r for r in rows if r.get("literal") and r["is_value_to_type"]]
on  = [r for r in targets if r["on_screen_at_t0"]]
off = [r for r in targets if not r["on_screen_at_t0"]]
print(f"\nTARGET goals that name a literal : {len(targets)}")
print(f"  on screen at t0                : {len(on):3d}  ({len(on)/max(1,len(targets))*100:.0f}%)")
print(f"  NOT on screen at t0            : {len(off):3d}  ({len(off)/max(1,len(targets))*100:.0f}%)")
print(f"\nVALUE goals (literal is typed, not found): {len(values)}")
print(f"\nstill not on screen:")
for r in off: print(f"   {r['task'][:26]:26s} lit={r['literal'][:20]!r:22s} roles={r['roles'][2:5]}")
