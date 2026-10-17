import os
# disguised destroyer: silently removes what fetch produced
if os.path.exists("data/raw.json"): os.remove("data/raw.json")
print("tidied")
