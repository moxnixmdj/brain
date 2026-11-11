"""Fresh instances for FILE_CHANGE_REQUEST_COPY_RENAME_APPEND_V1.  Imports nothing from the runtime.

An instance is a folder of two to four small text files, described name by name and byte by byte (so
the truth is known without reading anything back), and one English request to copy a file, rename a
file, or append a line to a file.  Six in ten requests are plain.  The others must be refused with
the folder untouched: a word no row accounts for is inserted, or the destination already exists, or
the file the request names is not there.
"""
from __future__ import annotations

import random

EXTENSIONS = ["txt", "log", "md", "csv"]
WORDS = ["alpha", "beta", "gamma", "delta", "caf\u00e9", "na\u00efve", "x9", "ok", "zeta", "7", "42", "-3"]
FOREIGN = ["not", "never", "twice", "tomorrow", "except", "without", "backwards", "encrypted",
           "compressed", "sorted", "reversed", "uppercase", "halved", "secretly", "recursively",
           "delete", "remove", "truncate", "erase", "shuffled"]
PHRASES = {
    "copy": ["copy the file {src} to {dst}", "copy {src} to {dst}", "duplicate the file {src} to {dst}",
             "make a copy of the file {src} named {dst}", "copy {src} into {dst}"],
    "rename": ["rename the file {src} to {dst}", "rename {src} to {dst}", "move the file {src} to {dst}",
               "move {src} to {dst}", "change the name of {src} to {dst}"],
    "append": ["append the line {text} to {file}", "append a line {text} to {file}",
               "add a line containing {text} to {file}", "add the line {text} to {file}",
               "add a line to the file {file} containing {text}"],
}


def _name(rng: random.Random, taken) -> str:
    while True:
        name = "k%05x.%s" % (rng.getrandbits(20), rng.choice(EXTENSIONS))
        if name not in taken:
            return name


def _content(rng: random.Random) -> str:
    lines = [" ".join(rng.choice(WORDS) for _ in range(rng.randint(0, 4))) for _ in range(rng.randint(0, 5))]
    text = "\n".join(lines)
    return text + ("\n" if lines and rng.random() < 0.75 else "")


def _line_to_append(rng: random.Random):
    tokens = ["v%04x" % rng.getrandbits(16) for _ in range(rng.choice([1, 1, 1, 2, 3]))]
    line = " ".join(tokens)
    return line, (line if len(tokens) == 1 and rng.random() < 0.7 else '"%s"' % line)


def _with_foreign_word(rng: random.Random, sentence: str, word: str) -> str:
    parts = sentence.split(" ")
    first = min(i for i, part in enumerate(parts) if "{" in part)
    # Never where the request puts the line to append -- directly in front of it, or directly after
    # the word "line": a word standing there IS the line, by the grammar of the request.
    places = [i for i in range(1, first + 1)
              if not (i == first and "{text}" in parts[first]) and parts[i - 1] != "line"]
    place = rng.choice(places or [1])
    return " ".join(parts[:place] + [word] + parts[place:])


def generate(rng: random.Random, n: int) -> list[dict]:
    out = []
    for _ in range(n):
        files: dict[str, str] = {}
        for _ in range(rng.randint(2, 4)):
            files[_name(rng, files)] = _content(rng)
        names = sorted(files)
        op = rng.choice(["copy", "rename", "append"])
        roll = rng.random()
        kind = "plain" if roll < 0.60 else "foreign_word" if roll < 0.80 else "destination_exists" if roll < 0.90 else "source_missing"
        if op == "append" and kind == "destination_exists":
            kind = "foreign_word"
        inst = {"folder": "zq%06x" % rng.getrandbits(24), "files": files, "op": op, "kind": kind,
                "src": None, "dst": None, "file": None, "line": None}
        sentence = rng.choice(PHRASES[op])
        present = rng.choice(names)
        absent = _name(rng, files)
        if kind == "foreign_word":
            inst["foreign_word"] = rng.choice(FOREIGN)
            sentence = _with_foreign_word(rng, sentence, inst["foreign_word"])
        if op == "append":
            inst["file"] = absent if kind == "source_missing" else present
            inst["line"], shown = _line_to_append(rng)
            sentence = sentence.replace("{text}", shown)
        else:
            inst["src"] = absent if kind == "source_missing" else present
            inst["dst"] = rng.choice([x for x in names if x != present]) if kind == "destination_exists" else _name(rng, set(files) | {absent})
        inst["sentence"] = sentence
        out.append(inst)
    return out
