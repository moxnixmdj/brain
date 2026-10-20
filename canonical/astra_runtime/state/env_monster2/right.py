import os, sys
if "--describe" in sys.argv:
    print("produces: out/report.txt containing 'report rows=3'"); sys.exit(0)
if os.path.exists("out/.lock"):
    sys.exit("refusing: environment already used")
open("out/report.txt","w").write("report rows=3")
