"""Independent oracles for FILE_QUESTION_TAUGHT_WORDS_V1.  No runtime import, no file is read.

* VALUE_BY_CONSTRUCTION  - the answer follows from the instance's own description of the file (its
  lines, its numbers) and the structured question.  The sentence is never parsed here.
* DOUBLED_FILE_RELATION  - the same question about the file written twice must change the answer in
  a way that follows from arithmetic alone (a count doubles, a count of distinct things does not).
* ANSWER_ENVELOPE        - an answer is a whole number inside the bounds the file allows, comes from
  the declared row, and a sentence with an untaught word gets no answer at all.
"""
from __future__ import annotations

ROW = "file.question.taught_words.v1"


def _text(lines, trailing):
    return "\n".join(lines) + ("\n" if trailing else "")


def _things(world, unit):
    if unit == "numbers":
        return list(world["numbers"])
    if unit == "lines":
        return list(world["lines"])
    if unit == "words":
        return [word for line in world["lines"] for word in line.split(" ") if word != ""]
    text = _text(world["lines"], world["trailing_newline"])
    return [ch for ch in text] if unit == "characters" else [b for b in text.encode("utf-8")]


def _expected(world, q):
    things = _things(world, q["unit"])
    if q["rest"]:
        things = things[1:]
    if q["containing"] is not None:
        things = [t for t in things if q["containing"] in t]
    if q["blank"]:
        things = [t for t in things if t == ""]
    if q["lengths"]:
        sizes = sorted(len(t) for t in things)
        return sizes[-1] if q["reduce"] == "max" else sizes[0]
    if q["reduce"] == "count":
        return len(set(things)) if q["unique"] else len(things)
    if q["reduce"] == "sum":
        return sum(set(things)) if q["unique"] else sum(things)
    ordered = sorted(things)
    return ordered[-1] if q["reduce"] == "max" else ordered[0]


def _is_whole_number(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _by_construction(inst, out, solve):
    if inst["kind"] == "untaught":
        return (out.get("answered") is not True, "answered a sentence that contains %r: %r" % (inst["untaught_word"], out.get("answer")))
    want = _expected(inst["world"], inst["question"])
    got = out.get("answer")
    return (out.get("answered") is True and _is_whole_number(got) and got == want, "want %r got %r (%s)" % (want, got, out.get("status")))


def _doubled(inst):
    world = dict(inst["world"])
    world["lines"] = list(inst["world"]["lines"]) * 2
    if world["kind"] == "numbers":
        world["numbers"] = list(inst["world"]["numbers"]) * 2
    twice = dict(inst)
    twice["world"] = world
    twice["file_text"] = _text(world["lines"], world["trailing_newline"])
    twice["file_name"] = "d" + inst["file_name"]
    return twice


def _doubled_file(inst, out, solve):
    if inst["kind"] == "untaught":
        other = dict(inst)
        other["sentence"] = inst["sentence"].replace(" " + inst["untaught_word"] + " ", " " + inst["other_untaught_word"] + " ", 1)
        again = solve(other)
        return (again.get("answered") is not True, "answered with %r in place of %r" % (inst["other_untaught_word"], inst["untaught_word"]))
    q, world, a = inst["question"], inst["world"], out.get("answer")
    b = solve(_doubled(inst)).get("answer")
    if not _is_whole_number(a) or not _is_whole_number(b):
        return (False, "no whole numbers to relate: %r, %r" % (a, b))
    things = _things(world, q["unit"])
    if q["rest"] and not things:
        want = a                      # nothing to drop: "after the first" of nothing is nothing, twice over
    elif q["lengths"]:
        size = len(things[0])
        want = a if not q["rest"] else (max(a, size) if q["reduce"] == "max" else min(a, size))
    elif q["reduce"] in ("max", "min"):
        want = a if not q["rest"] else (max(a, things[0]) if q["reduce"] == "max" else min(a, things[0]))
    elif q["unique"]:
        want = a
    elif q["reduce"] == "sum":
        want = 2 * a + (things[0] if q["rest"] else 0)
    elif q["unit"] in ("characters", "bytes"):
        # the second copy starts on a new line, which costs one newline when the file had none at its end
        want = 2 * a + (0 if world["trailing_newline"] else 1) + (1 if q["rest"] else 0)
    else:
        want = 2 * a + (1 if q["rest"] else 0)
    return (b == want, "file twice: want %r got %r (once: %r)" % (want, b, a))


def _envelope(inst, out, solve):
    if inst["kind"] == "untaught":
        return (out.get("answered") is not True and out.get("answer") is None, "an untaught word still produced %r" % (out,))
    q, world, a = inst["question"], inst["world"], out.get("answer")
    if out.get("answered") is not True or not _is_whole_number(a):
        return (False, "no whole-number answer: %r" % (out,))
    if out.get("capability") != ROW:
        return (False, "answered by %r" % (out.get("capability"),))
    things = _things(world, q["unit"])
    if q["lengths"]:
        low, high = 0, max(len(t) for t in things)
    elif q["reduce"] == "count":
        low, high = 0, len(things)
    elif q["reduce"] == "sum":
        low, high = -sum(abs(t) for t in things), sum(abs(t) for t in things)
    else:
        low, high = min(things), max(things)
    return (low <= a <= high, "answer %r outside [%r, %r]" % (a, low, high))


def oracles():
    return [
        {"id": "VALUE_BY_CONSTRUCTION", "check": _by_construction},
        {"id": "DOUBLED_FILE_RELATION", "check": _doubled_file},
        {"id": "ANSWER_ENVELOPE", "check": _envelope},
    ]
