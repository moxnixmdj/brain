"""Does hierarchical organisation survive a growing library, where flat routing dies?

Claim under test (arXiv 2601.04748; Princeton/UCSD, 8,135 runs): flat selection holds until a
capacity threshold and then falls off a cliff, driven by CONFUSABILITY rather than size, and
hierarchical coarse-to-fine routing mitigates it.  The claim is not mine.  This measures it
on a library I generate, with probes I write, mechanically, with no model anywhere -- so any
difference between flat and hierarchical is a property of the organisation.

Two deliberate design decisions, both of them corrections of a first attempt that measured
nothing:

 1. A probe names the SAME OBJECT with DIFFERENT VERBS and SYNTAX.  ("put the rows in order"
    for "sort the table": rows/table and order/sort both differ.)  A probe that shares no
    vocabulary with its target cannot be routed by any word-based method, so including one
    measures the experimenter's imagination, not the router.

 2. Three routers, not two:
      flat          word overlap over every skill at once
      hierarchical  category first, then skill inside it
      structure     SHAPE of the request (what happens to what) rather than words
"""
from __future__ import annotations

import random
import re
import sys

sys.path.insert(0, ".")

from canonical.runtime import compose_skills_v1 as C

SKILLS = {
    "file_rename": ("file", "rename the file", "give the FILE a new NAME",
                    ["file"], ["name"]),
    "file_delete": ("file", "delete the file", "get RID of the FILE",
                    ["file"], ["rid"]),
    "file_copy": ("file", "copy the file", "make a DUPLICATE of the FILE",
                  ["file"], ["duplicate"]),
    "file_move": ("file", "move the file", "put the FILE in ANOTHER DIRECTORY",
                  ["file"], ["directory"]),
    "file_compress": ("file", "compress the file", "make the FILE SMALLER",
                      ["file"], ["small"]),
    "file_open": ("file", "open the file", "SHOW me the FILE",
                  ["file"], ["show"]),
    "file_share": ("file", "share the file", "SEND the FILE to a COLLEAGUE",
                   ["file"], ["send"]),
    "file_lock": ("file", "lock the file", "STOP anyone EDITING the FILE",
                  ["file"], ["stop", "edit"]),
    "text_bold": ("text", "bold the text", "make this WORD HEAVIER",
                  ["word"], ["heavy"]),
    "text_italic": ("text", "italicise the text", "SLANT these LETTERS",
                    ["letter"], ["slant"]),
    "text_underline": ("text", "underline the text", "put a LINE under this",
                       ["line"], ["line"]),
    "text_search": ("text", "search the text", "FIND a WORD in this PARAGRAPH",
                    ["word"], ["find"]),
    "text_replace": ("text", "replace in the text", "SWAP one WORD for ANOTHER",
                     ["word"], ["swap"]),
    "text_count": ("text", "count words in the text", "HOW MANY WORDS is this",
                   ["word"], ["count"]),
    "text_translate": ("text", "translate the text", "turn this into FRENCH",
                       ["french"], []),
    "text_summarise": ("text", "summarise the text", "give me the GIST of this",
                       ["gist"], []),
    "web_navigate": ("web", "navigate to <site>", "GO to EXAMPLE dot com",
                     ["example"], ["go"]),
    "web_reload": ("web", "reload the page", "REFRESH what is on SCREEN",
                   ["screen"], ["refresh"]),
    "web_bookmark": ("web", "bookmark the page", "REMEMBER this PAGE for later",
                     ["page"], ["remember"]),
    "web_scroll": ("web", "scroll down", "move FURTHER down the PAGE",
                   ["page"], ["further"]),
    "web_fill": ("web", "fill the form", "TYPE my DETAILS into the BOXES",
                 ["box"], ["type"]),
    "web_submit": ("web", "submit the form", "SEND off the FORM",
                   ["form"], ["send"]),
    "web_screenshot": ("web", "take a screenshot", "CAPTURE what the SCREEN shows",
                       ["screen"], ["capture"]),
    "web_download": ("web", "download the page", "SAVE this PAGE to my COMPUTER",
                     ["page"], ["save"]),
    "data_sort": ("data", "sort the table", "put the ROWS in ORDER",
                  ["row"], ["order"]),
    "data_filter": ("data", "filter the table", "SHOW only SOME of the ROWS",
                    ["row"], ["show"]),
    "data_group": ("data", "group the rows", "COLLECT ROWS that BELONG together",
                   ["row"], ["collect"]),
    "data_pivot": ("data", "pivot the table", "TURN ROWS into COLUMNS",
                   ["row"], ["turn"]),
    "data_export": ("data", "export to csv", "WRITE the TABLE to a FILE",
                    ["table"], ["write"]),
    "data_import": ("data", "import from csv", "READ a TABLE from a FILE",
                    ["table"], ["read"]),
    "data_dedupe": ("data", "dedupe the rows", "REMOVE REPEATED ROWS",
                    ["row"], ["remove"]),
    "data_join": ("data", "join two tables", "COMBINE two TABLES on a KEY",
                  ["table"], ["combine"]),
    "media_crop": ("media", "crop the image", "CUT the EDGES off this PICTURE",
                   ["picture"], ["cut"]),
    "media_resize": ("media", "resize the image", "make this PICTURE BIGGER",
                     ["picture"], ["big"]),
    "media_rotate": ("media", "rotate the image", "TURN this PICTURE sideways",
                     ["picture"], ["turn"]),
    "media_brightness": ("media", "adjust brightness", "make this PICTURE LIGHTER",
                         ["picture"], ["light"]),
    "media_convert": ("media", "convert to png", "CHANGE this PICTURE format",
                      ["picture"], ["change"]),
    "media_watermark": ("media", "add a watermark", "STAMP my NAME on the PICTURE",
                        ["picture"], ["stamp"]),
    "media_trim": ("media", "trim the video", "CUT the CLIP shorter",
                   ["clip"], ["cut"]),
    "media_mute": ("media", "mute the audio", "SILENCE the SOUND",
                   ["sound"], ["silence"]),
    "system_install": ("system", "install the package", "ADD a LIBRARY to this MACHINE",
                       ["machine"], ["add"]),
    "system_disk": ("system", "check disk space", "HOW FULL is the DRIVE",
                    ["drive"], ["full"]),
    "system_ps": ("system", "list processes", "what is RUNNING right now",
                  ["running"], []),
    "system_kill": ("system", "kill the process", "STOP that RUNNING program",
                    ["program"], ["stop"]),
    "system_start": ("system", "start the service", "BRING the SERVER up",
                     ["server"], ["bring"]),
    "system_stop": ("system", "stop the service", "TAKE the SERVER down",
                    ["server"], ["take"]),
    "system_logs": ("system", "read the logs", "what did the SERVER say",
                    ["server"], []),
    "system_env": ("system", "set an env var", "DEFINE a VARIABLE for the SHELL",
                   ["shell"], ["define"]),
    "comms_send": ("comms", "send the email", "MAIL this to the TEAM",
                   ["team"], ["mail"]),
    "comms_reply": ("comms", "reply to the email", "ANSWER this MESSAGE",
                    ["message"], ["answer"]),
    "comms_forward": ("comms", "forward the email", "PASS this MESSAGE on",
                      ["message"], ["pass"]),
    "comms_archive": ("comms", "archive the email", "FILE this MESSAGE away",
                      ["message"], ["file"]),
    "comms_schedule": ("comms", "schedule a meeting", "put a MEETING in the CALENDAR",
                       ["meeting"], ["calendar"]),
    "comms_decline": ("comms", "decline the invite", "SAY NO to the INVITATION",
                      ["invitation"], ["say"]),
    "comms_post": ("comms", "post a message", "WRITE in the CHANNEL",
                   ["channel"], ["write"]),
    "comms_mention": ("comms", "mention a user", "TAG someone in the CHAT",
                      ["chat"], ["tag"]),
    "deploy_staging": ("deploy", "deploy to staging", "SHIP it to the TEST SERVERS",
                       ["servers"], ["ship"]),
    "deploy_prod": ("deploy", "deploy to production", "SHIP it to the LIVE SERVERS",
                    ["servers"], ["ship"]),
    "deploy_rollback": ("deploy", "roll back deploy", "UNDO the last RELEASE",
                        ["release"], ["undo"]),
    "deploy_tag": ("deploy", "tag a release", "MARK this VERSION",
                   ["version"], ["mark"]),
    "deploy_pipeline": ("deploy", "run the pipeline", "KICK off the BUILD JOBS",
                        ["build"], ["kick"]),
    "deploy_build": ("deploy", "check the build", "did the BUILD PASS",
                     ["build"], []),
    "deploy_scaleup": ("deploy", "scale up workers", "ADD more MACHINES",
                       ["machine"], ["add"]),
    "deploy_scaledown": ("deploy", "scale down workers", "REMOVE some MACHINES",
                         ["machine"], ["remove"]),
}

CATEGORY_WORDS = {
    "file": "file document folder disk directory",
    "text": "text word letter paragraph sentence writing",
    "web": "page site browser screen web tab url",
    "data": "table row column data spreadsheet csv",
    "media": "image picture video audio photo clip",
    "system": "server machine package process service logs shell variable",
    "comms": "email message meeting calendar channel chat invitation team",
    "deploy": "deploy release build pipeline version ship staging production",
}

VERB_SYNONYMS = {
    "rename": {"name", "call", "relabel"}, "delete": {"rid", "remove", "erase", "throw"},
    "copy": {"duplicate", "clone"}, "move": {"relocate", "directory"}, "compress": {"small"},
    "open": {"show", "look"}, "share": {"send", "colleague"}, "lock": {"stop", "editing"},
    "bold": {"heavy"}, "italicise": {"slant"}, "underline": {"line"}, "search": {"find"},
    "replace": {"swap"}, "count": {"many"}, "translate": {"french"},
    "summarise": {"gist"}, "navigate": {"go"}, "reload": {"refresh"},
    "bookmark": {"remember"}, "scroll": {"further"}, "fill": {"type"},
    "submit": {"send"}, "screenshot": {"capture"}, "download": {"save"},
    "sort": {"order"}, "filter": {"only", "some"}, "group": {"collect", "belong"},
    "pivot": {"turn", "column"}, "export": {"write"}, "import": {"read"},
    "dedupe": {"repeated"}, "join": {"combine"}, "crop": {"cut", "edges"},
    "resize": {"bigger"}, "rotate": {"turn", "sideways"}, "adjust": {"lighter"},
    "convert": {"change"}, "watermark": {"stamp"}, "trim": {"shorter"},
    "mute": {"silence"}, "install": {"add", "library"}, "check": {"full"},
    "list": {"running"}, "kill": {"stop"}, "start": {"bring", "up"}, "stop": {"take", "down"},
    "read": {"say"}, "set": {"define"}, "send": {"mail"}, "reply": {"answer"},
    "forward": {"pass"}, "archive": {"file"}, "schedule": {"calendar"},
    "decline": {"say", "no"}, "post": {"write"}, "mention": {"tag"},
    "deploy": {"ship"}, "roll": {"undo"}, "tag_": {"mark"}, "run": {"kick"},
    "scale": {"machines"}, "take": {"capture", "screenshot"}, "did": {"pass", "build"},
}
# Verbs whose synonym is a DERIVED form of the request word ("smaller" for "small",
# "shipping" for "ship").  Stemming only strips a trailing s, so these are added explicitly
# rather than pretending the stemmer handles English inflection -- it does not.
INFLECTIONS = {
    "small": {"smaller", "smallest"}, "big": {"bigger", "biggest"},
    "light": {"lighter", "lightest"}, "heavy": {"heavier", "heaviest"},
    "same": {"same"}, "full": {"fuller"}, "short": {"shorter"},
    "ship": {"shipping", "shipped"}, "tag": {"tagging", "tagged"},
    "run": {"running", "ran"}, "stop": {"stopping", "stopped"},
    "pass": {"passing", "passed"}, "build": {"building", "built"},
}


def build_library(n: int, rng: random.Random) -> dict:
    keys = sorted(SKILLS)
    rng.shuffle(keys)
    lib = {}
    for k in keys[:n]:
        cat, trig, probe, objects, verbs = SKILLS[k]
        lib[k] = {"trigger": trig, "binding": "present", "_cat": cat,
                  "_objects": objects, "_probe": probe}
    return lib


def flat_route(goal: str, lib: dict) -> str | None:
    r = C.route(goal, lib)
    if r["verdict"] != "ROUTED" or len(r["chosen"]) != 1:
        return None
    return r["chosen"][0]["skill"]


def hierarchical_route(goal: str, lib: dict) -> str | None:
    gw = C._stem_set(goal)
    cats: dict[str, list[str]] = {}
    for name, s in lib.items():
        cats.setdefault(s["_cat"], []).append(name)
    scored = sorted(((len(gw & C._stem_set(CATEGORY_WORDS[c])), c) for c in cats),
                    reverse=True)
    if not scored or scored[0][0] == 0:
        return None
    top = scored[0][0]
    for _, cat in [s for s in scored if s[0] == top]:
        sub = {k: v for k, v in lib.items() if v["_cat"] == cat}
        r = C.route(goal, sub)
        if r["verdict"] == "ROUTED" and len(r["chosen"]) == 1:
            return r["chosen"][0]["skill"]
    return None


_DET = frozenset({"the", "a", "an", "this", "that", "to", "from", "in", "on", "of", "off",
                  "up", "down", "into", "and", "for", "my", "some", "another", "two"})


def _verbs(trigger: str) -> set[str]:
    """The PREDICATE of a trigger, not all of it.

    Found by measuring: this used to return every token, so "open the file" contributed the
    verb "file" -- and then every file skill matched every file probe on the shared subject
    word, tied, and the tie rule refused.  The router was returning nothing for 26 of 64
    probes because it had no notion of which word was the action.
    """
    w = [t for t in trigger.lower().replace("<", " ").replace(">", " ").split()
         if t not in _DET]
    if not w:
        return set()
    head = {w[0]}
    if len(w) > 1 and w[1] not in _DET:
        head.add(w[0] + "_" + w[1])      # "roll back", "scale up"
    return head


def structure_route(goal: str, lib: dict) -> str | None:
    """Route by SHAPE: which object is acted on, and what happens to it.

    A request has a structure -- (verb-ish intent) applied to (object) -- and that structure
    is more stable than its words.  "put the rows in order" and "sort the table" share
    neither word but share the shape: ordering, applied to rows/table.  This router scores
    objects first and then looks for a trigger whose verb has a synonym in the request.
    """
    gw = C._stem_set(goal)
    best = []
    for name, s in lib.items():
        obj_hit = len(gw & set(s["_objects"]))
        verb_hit = 0
        for tok in _verbs(s["trigger"]):
            syn = set(VERB_SYNONYMS.get(tok, set()))
            for w in list(syn):
                syn |= INFLECTIONS.get(w, set())
            syn |= INFLECTIONS.get(tok, set())
            if tok in gw or (syn & gw):
                verb_hit = 1
                break
        if obj_hit or verb_hit:
            best.append((obj_hit * 2 + verb_hit, name))
    if not best:
        return None
    best.sort(reverse=True)
    if len(best) > 1 and best[0][0] == best[1][0]:
        return None                      # a tie is a refusal, not a guess
    return best[0][1]


def run(n: int, seed: int) -> dict:
    rng = random.Random(seed)
    lib = build_library(n, rng)
    probes = [(s["_probe"], k) for k, s in lib.items()]
    return {"n": n, "probes": len(probes),
            "flat": sum(flat_route(g, lib) == w for g, w in probes),
            "hier": sum(hierarchical_route(g, lib) == w for g, w in probes),
            "struct": sum(structure_route(g, lib) == w for g, w in probes)}


if __name__ == "__main__":
    print(f"{'skills':>7} {'flat':>9} {'hierarch':>10} {'structure':>11}")
    for n in (10, 25, 50, 64):
        acc = [run(n, s) for s in range(5)]
        p = sum(a["probes"] for a in acc)
        print(f"{n:>7} {sum(a['flat'] for a in acc)/p:>8.1%} "
              f"{sum(a['hier'] for a in acc)/p:>9.1%} "
              f"{sum(a['struct'] for a in acc)/p:>10.1%}")
