import sys
t = open("out/thing.txt").read()
sys.exit(0 if t.startswith("report rows=") else 1)   # the environment's own standard
