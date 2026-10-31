import subprocess, sys, json, pathlib, shutil
B=pathlib.Path("canonical/astra_runtime/tmp/comp")
if B.exists(): shutil.rmtree(B)
B.mkdir(parents=True)
(B/"calc.py").write_text("def add(a,b):\n    return a+b\n\n\ndef mul(a,b):\n    return a*b\n")
GOALS=[
 ("index", f"Index the symbols in {B}/calc.py and write the index to {B}/symbols.json."),
 ("callers_then", f"Find the callers of add in {B}/calc.py and then write them to {B}/c.json."),
 ("run_tests", f"Run the tests in {B} and save a pass-rate report to {B}/rate.json."),
 ("report_fns", f"Create a report of the functions in {B}/calc.py as JSON at {B}/f.json."),
]
for k,g in GOALS:
    try:
        p=subprocess.run([sys.executable,".arena_probe/one_goal.py",g,k],capture_output=True,text=True,timeout=75)
        print(f"{k:12s} {p.stdout.strip().splitlines()[-1] if p.stdout.strip() else 'NOOUT '+p.stderr[-120:]}")
    except subprocess.TimeoutExpired:
        print(f"{k:12s} HANG_>75s")
