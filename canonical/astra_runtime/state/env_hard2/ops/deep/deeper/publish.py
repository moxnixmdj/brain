import sys
if "--wrong-place" in sys.argv:
    open("out/elsewhere.txt","w").write("made a file, wrong one"); print("published OK")
else:
    open("out/good.txt","w").write("correctly published"); print("published OK")
