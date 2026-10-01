#!/usr/bin/env python3
import importlib.util
from pathlib import Path

p=Path(__file__).with_name("cognitive_tool_router.py")
spec=importlib.util.spec_from_file_location("router", p)
m=importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name]=m
spec.loader.exec_module(m)

def fake(_q, texts):
    return [float(len(x)) for x in texts]

routes=[
    m.ToolRoute("dropbox","Find files in connected Dropbox.","dropbox"),
    m.ToolRoute("gdrive","Find files in connected Google Drive.","google_drive"),
    m.ToolRoute("web","Search public webpages.","web"),
]
assert m.select_route("Find my budget",routes,fake,required_provider="dropbox").route_id=="dropbox"
assert m.select_route("Find my budget",routes,fake,allowed_route_ids={"dropbox","web"}).route_id in {"dropbox","web"}
blocked=[m.ToolRoute("dropbox","Dropbox","dropbox",authorized=False)]
r=m.select_route("Find file",blocked,fake,required_provider="dropbox")
assert r.status=="ESCALATE" and r.route_id is None
unavailable=[m.ToolRoute("gdrive","Drive","google_drive",available=False)]
r=m.select_route("Find file",unavailable,fake)
assert r.status=="ESCALATE"
single=[m.ToolRoute("github","Private GitHub repository file fetch","github")]
r=m.select_route("Read file",single,fake)
assert r.route_id=="github" and r.score is None
print("5/5 cognitive_tool_router deterministic contract checks passed")
