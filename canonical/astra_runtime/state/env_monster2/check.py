import sys
c = open("out/report.txt").read()
sys.exit(0 if c.startswith("report rows=") else 1)
