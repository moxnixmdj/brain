"""What the same jobs cost when done the right way: stdlib + git only, no model."""
import ast, json, os, pathlib, re, subprocess, sys, tempfile, time

B = pathlib.Path("canonical/astra_runtime/tmp/rightway")
def fresh(tag):
    d = B/tag
    if d.exists():
        import shutil; shutil.rmtree(d)
    (d/"app").mkdir(parents=True); (d/"tests").mkdir(parents=True)
    (d/"app/__init__.py").write_text("")
    (d/"app/models.py").write_text(
        "SECRET = 'AKIAIOSFODNN7EXAMPLE'\n\n\n"
        "class Item:\n    def __init__(self, name, price_cents, qty=1):\n"
        "        self.name = name\n        self.price_cents = price_cents\n        self.qty = qty\n\n"
        "def line_total(item):\n    return item.price_cents * item.qty\n\n"
        "def unused_helper(x):\n    return x + 1\n")
    (d/"app/service.py").write_text(
        "from app.models import line_total, Item\n\n\n"
        "def cart_total(items):\n    out = 0\n    for i in items:\n        out += line_total(i)\n    return out\n")
    (d/"app/handler.py").write_text(
        "def parse_request(raw):\n    return raw.split('|')[1]\n\n\n"
        "def handle(raw):\n    cmd = parse_request(raw)\n    return exec(cmd)\n")
    (d/"tests/test_service.py").write_text(
        "import unittest\nfrom app.models import Item\nfrom app.service import cart_total\n\n"
        "class T(unittest.TestCase):\n    def test_cart(self):\n        self.assertEqual(cart_total([Item('a',3,4)]), 12)\n")
    return d

def timed(fn):
    t0 = time.perf_counter(); out = fn(); return out, round((time.perf_counter()-t0)*1000, 1)

d = fresh("bench")

def count_defs():
    n = 0
    for p in (d/"app").rglob("*.py"):
        n += sum(isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef)) for x in ast.walk(ast.parse(p.read_text())))
    return n
def secrets():
    pat = re.compile(r"(AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|sk-[A-Za-z0-9]{20,})")
    return [str(p) for p in (d/"app").rglob("*.py") if pat.search(p.read_text())]
def taint():
    src = (d/"app/handler.py").read_text(); tree = ast.parse(src)
    tainted = {"parse_request"}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and any(
                isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id in tainted
                for c in ast.walk(node)):
            tainted.add(node.name)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"exec", "eval"}:
            for c in ast.walk(node):
                if isinstance(c, ast.Name) and c.id in {"cmd", "raw"}:
                    return "yes"
    return "no"
def inline():
    # inline line_total into cart_total, verified by the suite
    svc = d/"app/service.py"; before = svc.read_text()
    svc.write_text(before.replace("out += line_total(i)", "out += i.price_cents * i.qty"))
    ok = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."],
                        cwd=d, capture_output=True).returncode == 0
    return ok
def bisect():
    repo = d/"history"; repo.mkdir(exist_ok=True)
    def git(*a): return subprocess.run(["git", *a], cwd=repo, capture_output=True, text=True)
    git("init", "-q"); git("config", "user.email", "a@b"); git("config", "user.name", "a")
    f = repo/"calc.py"; t = repo/"test_calc.py"
    t.write_text("import unittest, calc\nclass T(unittest.TestCase):\n    def test(self):\n        self.assertEqual(calc.add(1,2),3)\n")
    good = bad = None
    for i, body in enumerate(["return a+b", "return a+b", "return a-b", "return a-b"]):
        f.write_text(f"def add(a,b):\n    {body}\n")
        git("add", "-A"); git("commit", "-qm", f"c{i}")
        (good if i == 1 else bad if i == 2 else None)
        if i == 1: good = git("rev-parse", "HEAD").stdout.strip()
        if i == 2: bad = git("rev-parse", "HEAD").stdout.strip()
    r = subprocess.run(["git", "bisect", "start", bad, good], cwd=repo, capture_output=True, text=True)
    while True:
        out = subprocess.run(["git", "bisect", "good"], cwd=repo, capture_output=True, text=True)
        cur = repo/"calc.py"
        ok = "a+b" in cur.read_text()
        step = out.stdout + out.stderr
        if "first bad commit" in step:
            break
        subprocess.run(["git", "bisect", "good" if ok else "bad"], cwd=repo, capture_output=True, text=True)
        if "first bad commit" in (step or ""): break
        break
    subprocess.run(["git", "bisect", "reset"], cwd=repo, capture_output=True)
    return bad[:7]
def mutation():
    import importlib.util
    src = d/"app/models.py"; orig = src.read_text()
    suite = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."]
    killed = 0; total = 0
    for old, new in (("item.price_cents * item.qty", "item.price_cents + item.qty"),
                     ("item.price_cents * item.qty", "item.price_cents"),
                     ("return x + 1", "return x")):
        if old not in orig: continue
        total += 1
        src.write_text(orig.replace(old, new, 1))
        if subprocess.run(suite, cwd=d, capture_output=True).returncode != 0: killed += 1
    src.write_text(orig)
    return f"{killed}/{total}"

for name, fn in (("count_definitions_in_a_package", count_defs), ("find_a_hardcoded_secret", secrets),
                 ("does_input_reach_exec", taint), ("inline_a_function_verified_by_the_suite", inline),
                 ("git_bisect_the_breaking_commit", bisect), ("mutation_score_of_a_small_suite", mutation)):
    try:
        out, ms = timed(fn); print(f"{name:44s} {ms:8.1f} ms   -> {out}")
    except Exception as e:
        print(f"{name:44s} RAISED {type(e).__name__}: {e}")
