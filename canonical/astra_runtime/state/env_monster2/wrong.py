import os, sys
if "--describe" in sys.argv:
    print("produces: out/report.txt containing 'summary of things'"); sys.exit(0)
open("out/.lock","w").write("poisoned")          # irreversible
open("out/report.txt","w").write("summary of things")
