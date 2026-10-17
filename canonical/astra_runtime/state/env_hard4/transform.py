import os,json
if not os.path.exists("data/raw.json"):
    raise SystemExit("transform: nothing to transform")   # fails alone
rows=json.load(open("data/raw.json"))["rows"]
open("out/report.txt","w").write("report rows=%d"%len(rows))
print("transformed")
