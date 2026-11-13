"""Procedure memory that generalizes, and the two ways it is allowed to be wrong.

THE PROBLEM. `experience_v1.record_resolution` stores a capability id under a key made of the
distinctive words in the sentence, sorted. Two consequences, both measured:

1. IT CANNOT GENERALIZE PAST WORDING. "convert the yaml file a.yaml to json using yq" hits;
   "turn report.yaml into json with yq" misses, and so does the plural "yaml files". The key is
   an exact set, so every paraphrase is a new question.

2. IT CANNOT TELL OPPOSITES APART. "convert yaml to json" and "convert json to yaml" are byte
   -identical keys -- both `convert|json|yaml` -- because sorting destroys order. Teaching the
   first makes the second a confident hit on the WRONG capability. Sorting a sentence destroys
   the one relation a conversion task is entirely made of.

3. IT CANNOT RESCUE A MISS. In `grounded_action_v1.act` the remembered id is consulted only
   inside `if survivors and len(survivors) > 1`, so it chooses among candidates the router has
   already narrowed to. Measured: it fires (`selected_because: REMEMBERED_RESOLUTION`) and
   changes nothing. A task the router cannot reach is never reached from memory either.

WHAT THIS MODULE IS. A second memory, kept beside the first rather than replacing it: the same
store, a new `procedures` section, so nothing that already works is disturbed.

THE TWO THINGS THAT MAKE IT HONEST, WHICH ARE NOT THE MATCHING.

    a) a remembered procedure is a CANDIDATE, never a decision. It must pass the same
       preconditions, the same binding, and the same verification as any other route.
    b) learning happens only on a VERIFIED receipt. A failure teaches nothing, because the
       capability that failed may have been the wrong one for a reason that has nothing to do
       with the next sentence that resembles it.

With (a) and (b) in place, a looser match costs at most a failed verification -- never a wrong
answer -- which is what makes it safe to loosen the match at all. Without them, generalizing
recall would be a way to make the machine confidently wrong faster, which is precisely the
failure the literature calls skill shadowing (a similar-looking skill crowds out the right one;
retrieval precision falls from 29.6% to 3.3% as the pool grows).

WHAT IT GENERALIZES OVER, and why each is a real dimension rather than a guess:

    formatting   convert / turn / export / make ... all mean "produce the target form"
    inflection   yaml / yamls / files / file -- plural and hyphenation are not new tasks
    direction    (yaml -> json) is preserved as an ordered pair, because it is the task
    literals     file names are typed arguments, not part of the question

WHAT IT DOES NOT DO. It does not embed, it does not call a model, and it adds no dependency:
the whole thing is a tokenizer, an ordered-pair detector, and a sorted-tuple comparison.
"""
from __future__ import annotations

import re

SCHEMA = "PROCEDURE_MEMORY_V1"

# ------------------------------------------------------------------------------------------
# The vocabulary. Deliberately small and auditable: every entry is a claim that two words do
# not make two questions. Anything not listed is compared literally, so an unlisted synonym
# costs a missed reuse (a slow answer) rather than a wrong one.
# ------------------------------------------------------------------------------------------
FORMAT_VERBS = {
    "convert": "format", "turn": "format", "transform": "format", "export": "format",
    "make": "format", "produce": "format", "save": "format", "render": "format",
    "write": "format", "generate": "format", "serialise": "format", "serialize": "format",
    "audit": "inspect", "inspect": "inspect", "analyze": "inspect", "analyse": "inspect",
    "check": "inspect", "examine": "inspect", "review": "inspect",
    "compute": "measure", "measure": "measure", "calculate": "measure",
    "evaluate": "measure", "assess": "measure",
    "extract": "extract", "pull": "extract", "obtain": "extract",
    "harvest": "extract", "get": "extract", "read": "extract",
    "total": "sum", "folder": "directory", "compare": "diff",
}
# Words that carry no task identity at all in this machine's sentences.
FILLER = {
    "the", "a", "an", "this", "that", "these", "those", "please", "using", "with", "via",
    "file", "files", "document", "documents", "report", "reports", "source", "module", "code",
    "cyclomatic", "out", "up", "into", "from", "to", "and", "then", "of", "for", "in", "on", "it",
    "canonical", "repository", "local", "path",
}
# Verbs that name a DIRECTION or an operation the register above must not absorb.
# "compress" and "extract" are opposites; mapping both to "format" would be a shadowing bug.
OPPOSITE_SENSITIVE = {
    "compress", "unpack", "pack", "archive", "expand",
    "write", "create", "delete", "remove", "add", "append", "prepend",
    "sort", "shuffle", "merge", "split", "encode", "decode", "encrypt", "decrypt",
    "minify", "pretty", "resize", "crop", "rotate", "sum", "count", "average",
    "upload", "download", "install", "uninstall", "start", "stop",
}

# `X to Y` / `X into Y` / `from X to Y`: the ordered pair IS the operation.
_DIRECTION = re.compile(
    r"\b(?:from\s+)?([a-z0-9_]+?)\s+(?:to|into)\s+([a-z0-9_]+)\b", re.IGNORECASE)

_FORGED_ID = re.compile(r"\bforged\.[a-z0-9_.]+\b", re.IGNORECASE)
_PATH_WITH_DIR = re.compile(r"\b(?:[\w.-]+/)+[\w.-]*?(?=\.[a-z0-9]{1,6}\b)", re.IGNORECASE)
_TOKEN = re.compile(r"[a-z0-9]+")


def _stem(word: str) -> str:
    """A conservative singular. Plurals are not new tasks; the stem must still be the word.

    THREE MEASURED FAILURES, all of this function, all found by running it:

      1. `files` -> `fil`. The `es` branch fired first and removed two characters, so the
         plural case this function exists for was the one case it broke.
      2. A floor on the STEM fixed nothing: `fil` is three characters, so the floor rejects
         the strip and leaves `files` -- which still does not match `file`. The floor has to
         sit on the result of the ONE-character rule, applied before the two-character one.
      3. `yaml` is four characters and takes an `s` cleanly; `gas` and `bus` are three and
         must not be touched, which is what the length test on the INPUT is for.

    So: try the single `s` first and keep it when the result is four or more characters --
    that covers `files`, `yamls`, `columns`. Only then try `ies`/`es`, which are language
    rules rather than character counts.
    """
    w = word
    # WHAT THIS MUST GUARANTEE is narrow and checkable: the singular and the plural of the
    # same word must land on the same string. Dictionary-correct stems are not required --
    # `cas` is an acceptable stem for `cases` as long as `case` also lands on `cas`.
    #
    # Getting that wrong took three attempts, so the rule is the standard English one rather
    # than a character count:
    #   `-ies`  -> `-y`      entries -> entry
    #   `-sses` -> `-es`     processes -> process
    #   `-ses`  -> `-s`      cases -> case      (the `-sses` case above is why this is separate)
    #   `-ches`, `-shes`, `-xes`, `-zes` -> `-es`   batches -> batch, boxes -> box
    #   any other `-s` -> `-s` when the stem keeps four characters
    if len(w) >= 5 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) >= 6 and w.endswith("sses"):
        return w[:-2]
    if len(w) >= 4 and w.endswith("ses"):
        return w[:-1]
    if len(w) >= 5 and (w.endswith("ches") or w.endswith("shes")
                        or w.endswith("xes") or w.endswith("zes")):
        return w[:-2]                       # `boxes` -> `box` (five characters is enough)
    if len(w) >= 5 and w.endswith("s") and not w.endswith("ss"):
        single = w[:-1]
        if len(single) >= 4:
            return single
    return w


def direction(text: str):
    """The ordered (verb, source, target) a sentence states, or None.

    THE VERB IS PART OF THE DIRECTION. The first version returned only (source, target).
    Endpoints alone are not an operation: "convert yaml to json" and "turn yaml to json" are
    the same request, but "compress X to tar" and "extract X to tar" are not, and neither is
    "read the spreadsheet" -- which names no pair at all. Naming the verb keeps the operation,
    not just its endpoints, and lets two sentences that both state a pair disagree on it.

    An ordered pair is the one thing a sorted token set cannot hold, and it is exactly what a
    conversion task is made of. "convert yaml to json" and "convert json to yaml" must never
    share a signature, however many words they share.
    """
    match = _DIRECTION.search(str(text or ""))
    if not match:
        return None
    source, target = (_stem(match.group(1).lower()), _stem(match.group(2).lower()))
    if not source or not target or source == target:
        return None
    if source in FILLER or target in FILLER:
        return None
    verb = ""
    before = str(text or "")[:match.start()].lower().split()
    for word in reversed(before):
        folded = FORMAT_VERBS.get(_stem(word))
        if folded:
            verb = "format"
            break
        if _stem(word) in OPPOSITE_SENSITIVE:
            verb = _stem(word)
            break
    return (verb, source, target)


def content_words(text: str) -> tuple:
    """The words that carry task identity, with formatting verbs folded and fillers dropped."""
    cleaned = _FORGED_ID.sub(" ", str(text or ""))
    cleaned = _PATH_WITH_DIR.sub(" ", cleaned)
    out = []
    for raw in _TOKEN.findall(cleaned.lower()):
        word = _stem(raw)
        if word in FILLER:
            continue
        if word in OPPOSITE_SENSITIVE:
            out.append(word)          # kept verbatim: these carry direction
            continue
        out.append(FORMAT_VERBS.get(word, word))
    return tuple(out)


def signature(text: str) -> str:
    """A generalized address for a question.

    Order-insensitive for ordinary words (so "using yq convert the yaml file" matches
    "convert the yaml file using yq") but ORDER-PRESERVING for a stated direction, which is
    appended as its own component. Every token is dropped that could not change what is asked.
    """
    words = sorted(set(content_words(text)))
    pair = direction(text)
    head = "+".join(words)
    if pair:
        verb, source, target = pair
        return f"{head} >>{verb}:{source}->{target}"
    return head


def similarity(a: str, b: str) -> float:
    """Jaccard over signature components. Only used to RANK candidates, never to decide."""
    left, right = set(str(a).split("+")), set(str(b).split("+"))
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def agrees_on_direction(a: str, b: str) -> bool:
    """True unless both state a direction and those directions differ.

    This is the gate that stops the collision measured in this repository: two sentences that
    both say "convert ... to ..." but in opposite directions must not be treated as the same
    procedure, however many words they share.
    """
    left = re.search(r">>(\w*):(\S+)->(\S+)$", str(a))
    right = re.search(r">>(\w*):(\S+)->(\S+)$", str(b))
    if not left or not right:
        return True                 # a sentence with no stated direction cannot contradict one
    if (left.group(2), left.group(3)) != (right.group(2), right.group(3)):
        return False
    # a stated verb must not be silently swapped for a different one; an unstated verb is
    # compatible with anything, because the sentence simply did not say.
    lv, rv = left.group(1), right.group(1)
    return not (lv and rv and lv != rv)


# ------------------------------------------------------------------------------------------
# Storage. A second section in the SAME file, so an existing state file is not migrated or
# invalidated and the exact-recall path keeps working exactly as it did.
# ------------------------------------------------------------------------------------------
def learn(goal: str, capability_id: str, verified: bool, path=None, root=None,
          verifier=None) -> dict:
    """Record a procedure, but only from a receipt that VERIFIED.

    `verified=False` records nothing and says so. A failed action is not a lesson about the
    next sentence that resembles it: the capability may have been the wrong candidate, the
    argument may have been missing, or the tool may be absent on this box. Learning from it
    would launder one failure into a confident preference -- the shadowing failure again, with
    the machine as its own teacher.
    """
    if not verified:
        return {"schema": SCHEMA, "learned": False,
                "why": "ONLY_A_VERIFIED_RECEIPT_MAY_TEACH_A_PROCEDURE",
                "capability_id": str(capability_id)}
    from canonical.runtime import experience_v1 as EXP

    sig = signature(goal)
    if not sig:
        return {"schema": SCHEMA, "learned": False, "why": "EMPTY_SIGNATURE"}
    state = EXP._load(path)
    procedures = state.setdefault("procedures", {})
    entry = procedures.setdefault(sig, {
        "signature": sig, "goal": str(goal), "capability_id": str(capability_id),
        "first_taught": __import__("time").time(), "uses": 0, "examples": [],
    })
    entry["capability_id"] = str(capability_id)
    if str(goal) not in entry["examples"]:
        entry["examples"] = (entry["examples"] + [str(goal)])[-8:]
    entry["last_taught"] = __import__("time").time()
    EXP._save(state, path)
    return {"schema": SCHEMA, "learned": True, "signature": sig,
            "capability_id": str(capability_id), "examples": len(entry["examples"])}


def _procedures(path=None):
    from canonical.runtime import experience_v1 as EXP
    state = EXP._load(path)
    return dict(state.get("procedures") or {})


def recall(goal: str, path=None, minimum: float = 0.5):
    """The best remembered procedure for this question, or None.

    Returns a CANDIDATE with its similarity, never a decision. The caller must run the same
    preconditions / binding / verification it runs for any other route -- that obligation is
    what makes it safe to be generous here.
    """
    sig = signature(goal)
    if not sig:
        return None
    best = None
    for other, entry in _procedures(path).items():
        if not agrees_on_direction(sig, other):
            continue
        score = similarity(sig, other)
        if score < minimum:
            continue
        if best is None or score > best["similarity"]:
            best = {"schema": SCHEMA, "similarity": round(score, 4),
                    "capability_id": entry.get("capability_id"),
                    "signature": other, "learned_goal": entry.get("goal"),
                    "examples": entry.get("examples") or []}
    return best


def recall_many(goal: str, path=None, minimum: float = 0.34, limit: int = 3):
    """Ranked candidates, best first. Several are returned on purpose: the router decides."""
    sig = signature(goal)
    if not sig:
        return []
    rows = []
    for other, entry in _procedures(path).items():
        if not agrees_on_direction(sig, other):
            continue
        score = similarity(sig, other)
        if score >= minimum:
            rows.append({"similarity": round(score, 4), "signature": other,
                         "capability_id": entry.get("capability_id"),
                         "learned_goal": entry.get("goal")})
    rows.sort(key=lambda r: (-r["similarity"], str(r["capability_id"])))
    out, seen = [], set()
    for row in rows:
        if row["capability_id"] in seen:
            continue
        seen.add(row["capability_id"])
        out.append(row)
        if len(out) >= limit:
            break
    return out
