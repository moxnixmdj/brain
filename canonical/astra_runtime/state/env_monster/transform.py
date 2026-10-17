import json
rows = json.load(open("data/raw.json"))["rows"]
open("out/report.txt","w").write("report rows=%d" % len(rows))
