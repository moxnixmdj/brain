"""Independent oracles for FILE_CHANGE_REQUEST_COPY_RENAME_APPEND_V1.  No runtime import, no file is read.

* FOLDER_BY_CONSTRUCTION - what the folder must hold afterwards follows from the instance's own
  description of the files and of the request (operation, names, line).  The sentence is never parsed
  here.  Copy adds one file with the source's bytes.  Rename moves those bytes to the new name.
  Append ends the file's last line if it was not ended, then adds the line and a newline.  A request
  that must be refused leaves the folder exactly as it was.
* ASKED_AGAIN_RELATION   - the same request asked again in the folder the first request left: a copy
  or a rename must now be refused (its destination exists, or its source is gone) and change nothing;
  an append must add the line a second time; a refused request must be refused again.
* UNTOUCHED_AND_BY_THE_ROW - every file the request does not name keeps its bytes, nothing that is
  not a file appears, and an answer comes from the row declared for that operation.
"""
from __future__ import annotations

ROWS = {"copy": "file.copy.v1", "rename": "file.rename.v1", "append": "file.line.appended.v1"}


def _after(inst):
    files = dict(inst["files"])
    if inst["kind"] != "plain":
        return files
    if inst["op"] == "copy":
        files[inst["dst"]] = files[inst["src"]]
    elif inst["op"] == "rename":
        files[inst["dst"]] = files.pop(inst["src"])
    else:
        old = files[inst["file"]]
        files[inst["file"]] = old + ("" if old == "" or old.endswith("\n") else "\n") + inst["line"] + "\n"
    return files


def _by_construction(inst, out, solve):
    want = _after(inst)
    should_answer = inst["kind"] == "plain"
    ok = (out.get("answered") is True) == should_answer and out.get("state") == want
    return (ok, "kind %s: answered %r, folder %r, wanted %r (%s)" % (inst["kind"], out.get("answered"), out.get("state"), want, out.get("status")))


def _asked_again(inst, out, solve):
    again = dict(inst)
    again["files"] = _after(inst)
    again["folder"] = "r" + inst["folder"]
    second = solve(again)
    if inst["kind"] == "plain" and inst["op"] == "append":
        want = dict(again["files"])
        want[inst["file"]] = want[inst["file"]] + inst["line"] + "\n"
        return (second.get("answered") is True and second.get("state") == want, "second append: %r, wanted %r" % (second.get("state"), want))
    return (second.get("answered") is not True and second.get("state") == again["files"],
            "asked again: answered %r, folder %r, wanted it untouched %r" % (second.get("answered"), second.get("state"), again["files"]))


def _untouched(inst, out, solve):
    state = out.get("state")
    if not isinstance(state, dict) or out.get("not_files"):
        return (False, "folder not readable as plain files: %r" % (out,))
    named = {inst.get("src"), inst.get("dst"), inst.get("file")} - {None}
    for name, text in inst["files"].items():
        if name not in named and state.get(name) != text:
            return (False, "a file the request does not name changed: %s" % name)
    extra = set(state) - set(inst["files"]) - named
    if extra:
        return (False, "files nobody asked for: %r" % sorted(extra))
    if out.get("answered") is True:
        return (out.get("capability") == ROWS[inst["op"]], "answered by %r" % (out.get("capability"),))
    return (state == inst["files"], "refused, yet the folder changed: %r" % (state,))


def oracles():
    return [
        {"id": "FOLDER_BY_CONSTRUCTION", "check": _by_construction},
        {"id": "ASKED_AGAIN_RELATION", "check": _asked_again},
        {"id": "UNTOUCHED_AND_BY_THE_ROW", "check": _untouched},
    ]
