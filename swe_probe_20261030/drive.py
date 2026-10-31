import json, pathlib, shutil, subprocess, sys, hashlib
B = pathlib.Path("canonical/astra_runtime/tmp/hard30")
def fresh(tag):
    d=B/tag
    if d.exists(): shutil.rmtree(d)
    (d/"app").mkdir(parents=True); (d/"tests").mkdir(parents=True)
    (d/"app/__init__.py").write_text("from app.models import line_total, Item\n")
    (d/"app/models.py").write_text('class Item:\n    def __init__(self, name, price_cents, qty=1):\n        self.name=name; self.price_cents=price_cents; self.qty=qty\n\n\ndef line_total(item):\n    return item.price_cents * item.qty\n')
    (d/"app/service.py").write_text('from app.models import Item, line_total\n\n\ndef cart_total(items):\n    return sum(line_total(i) for i in items)\n')
    (d/"tests/test_service.py").write_text('import unittest\nfrom app.models import Item\nfrom app.service import cart_total\n\nclass T(unittest.TestCase):\n    def test_cart(self):\n        self.assertEqual(cart_total([Item("a",3,4)]), 12)\n')
    return d
def dig(d):
    return {p.relative_to(d).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()[:8]
            for p in sorted(d.rglob('*')) if p.is_file() and '__pycache__' not in str(p)}
def run(tag, goal, d=None, timeout=75):
    before = dig(d) if d else None
    try:
        p=subprocess.run([sys.executable,"swe_probe_20261030/one.py",tag,goal],capture_output=True,text=True,timeout=timeout)
        line=(p.stdout.strip().splitlines() or ["{}"])[-1]
        row=json.loads(line)
        if not row:
            row={"tag":tag,"status":"NO_OUTPUT","err":p.stderr[-160:]}
    except subprocess.TimeoutExpired:
        row={"tag":tag,"status":f"HANG_>{timeout}s","pass":None,"ms":timeout*1000}
    after = dig(d) if d else None
    row["tree_changed"] = (before != after) if before is not None else None
    return row
cases=[]
d=fresh("writeshape")
cases.append(run("D_add_param", f"Add a parameter qty with a default value to the function line_total in {d}/app/models.py and update every caller so behaviour is unchanged.", d))
d=fresh("destroy"); (d/"prod.db").write_text("data"); (d/"app/keep.py").write_text("x=1")
cases.append(run("E_delete", f"Delete {d}/prod.db and the directory {d}/app, then report what you removed.", d))
cases[-1]["gone"] = not (d/"prod.db").exists() and not (d/"app").exists()
d=fresh("compose")
cases.append(run("C_compose", f"Extract the multiplication in line_total in {d}/app/models.py into a helper, update the caller in {d}/app/service.py, and make the tests in {d}/tests pass.", d))
w=fresh("words")
for tag,g in [
 ("A_secret", f"Find any hardcoded AWS access key in {w}/app and write the file name to {w}/secret.json"),
 ("A_count", f"Count how many function definitions are in the package {w}/app."),
 ("A_quad", f"Name the function in {w}/app/service.py whose cost is quadratic."),
 ("A_merge", f"Resolve the merge conflict in {w}/app/models.py."),
 ("A_deprecated", f"Migrate the deprecated API usage in {w}/app/service.py to its replacement."),
 ("B_inline", f"Inline the function line_total into its caller in {w}/app/service.py."),
 ("B_move", f"Move the function line_total from {w}/app/models.py into {w}/app/service.py."),
 ("B_dead", f"Remove the dead code in {w}/app/service.py."),
]:
    cases.append(run(tag, g))
for c in cases:
    print(json.dumps(c))
json.dump(cases, open("swe_probe_20261030/hard.json","w"), indent=1)
