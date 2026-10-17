import json
# No explicit guard -- let it fail the way real code fails, naming what it lacked.
rows = json.load(open("data/raw.json"))["rows"]
open("out/report.txt", "w").write("report rows=%d" % len(rows))
print("transformed")
