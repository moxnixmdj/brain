#!/usr/bin/env python3
import json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"canonical"/"runtime"))
import verify_pending_cli_binding as v
goal="Generate a Data Matrix barcode image for the text PROJECT BRAIN V4."
terms=v._semantic_verifier_terms(goal,"PROJECT BRAIN V4")
local=v._raw_apt_family_seeds(terms,per_token_limit=500)
web=v._ubuntu_web_family_seeds(terms,per_token_limit=200)
def summarize(items):
    return [{
      "name":x.get("name"),
      "description":x.get("description"),
      "seed_token":x.get("seed_token"),
      "families":v._package_family_tokens(x.get("name"))
    } for x in items]
out={"terms":terms,"local":summarize(local),"web":summarize(web)}
print(json.dumps(out,sort_keys=True))
