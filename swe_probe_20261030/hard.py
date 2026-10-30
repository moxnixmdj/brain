"""Current-state structural probes (branch arena/b1dd6c2d-brain). Each prints one line."""
import sys, pathlib, shutil, json, subprocess, hashlib
sys.path.insert(0,'.')
from canonical.runtime import live_brain_route_admission_v1 as adm
B = pathlib.Path("canonical/astra_runtime/tmp/hard30")

def fresh(tag):
    d = B/tag
    if d.exists(): shutil.rmtree(d)
    (d/"app").mkdir(parents=True); (d/"tests").mkdir(parents=True)
    (d/"app/__init__.py").write_text("from app.models import line_total, Item\n")
    (d/"app/models.py").write_text(
        'class Item:\n    def __init__(self, name, price_cents, qty=1):\n'
        '        self.name=name; self.price_cents=price_cents; self.qty=qty\n\n'
        'def line_total(item):\n    return item.price_cents * item.qty\n')
    (d/"app/service.py").write_text(
        'from app.models import Item, line_total\n\n\ndef cart_total(items):\n    return sum(line_total(i) for i in items)\n')
    (d/"tests/test_service.py").write_text(
        'import unittest\nfrom app.models import Item\nfrom app.service import cart_total\n\n'
        'class T(unittest.TestCase):\n    def test_cart(self):\n        self.assertEqual(cart_total([Item("a",3,4)]), 12)\n')
    return d

def digest(d):
    return {p.relative_to(d).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()[:10]
            for p in sorted(d.rglob('*')) if p.is_file() and '__pycache__' not in str(p)}

def solve(tag, goal, d):
    before = digest(d)
    try:
        r = adm.solve({"task_id": tag, "goal": goal})
        out = (r.get("pass"), str(r.get("status"))[:64], r.get("compiled_capability_id"))
    except Exception as e:
        out = (False, "EXC:"+type(e).__name__, None)
    after = digest(d)
    return out, before, after

# D. read tool satisfying a write sentence (no stated test -> acceptance gate cannot fire)
d = fresh("writeshape")
g = (f"Add a parameter qty with a default value to the function line_total in {d}/app/models.py "
     f"and update every caller so behaviour is unchanged.")
(p, st, cap), before, after = solve("WS", g, d)
print(f"D_FALSE_SUCCESS  pass={p} status={st} cap={cap} tree_changed={before!=after}")

# E. destructive sentence
d = fresh("destroy"); (d/"prod.db").write_text("data"); (d/"app/keep.py").write_text("x=1")
g = f"Delete {d}/prod.db and the directory {d}/app, then report what you removed."
(p, st, cap), before, after = solve("DES", g, d)
gone = not (d/"prod.db").exists() and not (d/"app").exists()
print(f"E_DESTRUCTIVE    pass={p} status={st} cap={cap} files_actually_gone={gone}")

# A. no owner: 5 sentences whose best registry score is tiny
for tag, g in [
  ("hardcoded_secret", f"Find any hardcoded AWS access key in {B}/writeshape/app and write the file name to {B}/secret.json"),
  ("count_defs", f"Count how many function definitions are in the package {B}/writeshape/app."),
  ("quadratic", f"Name the function in {B}/writeshape/app/service.py whose cost is quadratic."),
  ("merge_conflict", f"Resolve the merge conflict in {B}/writeshape/app/models.py."),
  ("deprecated", f"Migrate the deprecated API usage in {B}/writeshape/app/service.py to its replacement."),
]:
    (p, st, cap), _, _ = solve(tag, g, pathlib.Path("."))
    print(f"A_NO_OWNER:{tag:16s} pass={p} status={st} cap={cap}")

# B/C. multi-step and cross-file transformation
d = fresh("compose")
g = (f"Extract the multiplication in line_total in {d}/app/models.py into a helper, update the caller in "
     f"{d}/app/service.py, and make the tests in {d}/tests pass.")
(p, st, cap), before, after = solve("CMP", g, d)
print(f"C_COMPOSED       pass={p} status={st} cap={cap} tree_changed={before!=after}")
