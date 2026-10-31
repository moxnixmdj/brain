"""Input boundary and a shell sink."""

import json
import os


def handle(raw):
    payload = json.loads(raw)
    name = payload["name"]
    os.system("echo " + name)
