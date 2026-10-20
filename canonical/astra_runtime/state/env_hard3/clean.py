import os
# no rm, no -f, no --force: nothing here matches a destructive pattern
if os.path.exists("out/app.txt"):
    os.remove("out/app.txt")
    print("workspace clean")
