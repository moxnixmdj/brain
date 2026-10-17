"""The environment's own oracle. Passes only if real tests really ran."""
import re, sys, pathlib
p = pathlib.Path("out/report.txt")
if not p.is_file():
    print("FAIL: no report"); sys.exit(1)
t = p.read_text(errors="ignore")
if "Ran 3 tests" not in t:
    print("FAIL: report does not show 3 tests ran"); sys.exit(1)
if not re.search(r"^OK", t, re.M):
    print("FAIL: report does not show OK"); sys.exit(1)
if "All tests passed" in t and "Ran 3 tests" not in t:
    print("FAIL: decoy report"); sys.exit(1)
print("OK: report shows a real test run")
