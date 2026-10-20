import sys, os
p = "out/report.txt"
if not os.path.exists(p): sys.exit("no report produced")
if not open(p).read().startswith("report rows="): sys.exit("report malformed")
print("validation passed")
