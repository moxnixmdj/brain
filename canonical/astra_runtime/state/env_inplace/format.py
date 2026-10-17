p = "src/code.txt"
s = open(p).read()
open(p, "w").write(s.upper())     # the entire effect is in-place
print("formatted")
