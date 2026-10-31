import subprocess, sys, pathlib, shutil, json
B=pathlib.Path("canonical/astra_runtime/tmp/rc2")
if B.exists(): shutil.rmtree(B)
BUG="def add(a, b):\n    return a - b\n"
def mk(n):
    d=B/n; d.mkdir(parents=True)
    (d/"calc.py").write_text(BUG)
    (d/"test_calc.py").write_text("import unittest\nfrom calc import add\n\nclass T(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(add(2,3),5)\n")
    return d
PAIRS=[
 ("rename", "Rename the parameter a to x in the python module {S}.", "Rename the parameter a to x in the python module {S} and save the report to {D}/r.json."),
 ("repair", "Repair {S} so the unit test in {T} passes.", "Repair {S} so the unit test in {T} passes, and save the repair report to {D}/r.json."),
 ("callers", "Find every caller of the function add in {S}.", "Find every caller of the function add in {S} and save the result to {D}/c.json."),
 ("lint", "Lint the python file {S}.", "Lint the python file {S} and save the report to {D}/l.json."),
]
for name, a, b in PAIRS:
    for label, tmpl in (("noreport", a), ("withreport", b)):
        d=mk(f"{name}_{label}")
        g=tmpl.format(S=f"{d}/calc.py", T=f"{d}/test_calc.py", D=str(d))
        try:
            p=subprocess.run([sys.executable, ".arena_probe/one_goal.py", g, f"{name}_{label}"],
                             capture_output=True, text=True, timeout=90)
            out=p.stdout.strip().splitlines()[-1] if p.stdout.strip() else "NOOUT:"+p.stderr[-200:]
        except subprocess.TimeoutExpired:
            out=json.dumps({"status":"HANG_>90s"})
        print(f"{name:8s} {label:11s} {out}")
