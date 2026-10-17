"""Read the fields a UI exposes, and what each one demands.

There is no browser in this environment -- no chrome, no chromedriver, no
selenium. Rather than pretend otherwise, this reads a UI at the level that
still decides everything: what fields exist, what they are called, what
values they accept, which are required, and what hidden state must be
replayed.

Almost every failure in filling a form is one of:
  - not knowing a field exists
  - not knowing a hidden token must be sent back
  - not knowing which values are legal
  - not reading the error that tells you

So that is what gets parsed. Deliberately stdlib only, because a parser
that cannot be imported is a parser that does not exist.

Nothing here submits anything. Reading a form and filling a form are
separate acts, and this one only looks.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser

SCHEMA = "PROJECT_BRAIN_HTMLFORM_READ_V1"

# Roles that make an action dangerous to trigger while exploring.
_DESTRUCTIVE_WORDS = ("delete", "destroy", "drop", "reset", "wipe",
                      "purge", "remove", "cancel account")


class _FormParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.forms: list[dict] = []
        self._cur: dict | None = None
        self._sel: dict | None = None
        self._btn: dict | None = None

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if tag == "form":
            self._cur = {"action": a.get("action", ""),
                         "method": (a.get("method") or "get").upper(),
                         "fields": [], "buttons": []}
        elif tag in ("input", "select", "textarea") and self._cur is not None:
            f = {"tag": tag, "name": a.get("name", ""),
                 "type": (a.get("type") or ("text" if tag != "select"
                                            else "select")).lower(),
                 "value": a.get("value", ""),
                 "required": "required" in a,
                 "readonly": "readonly" in a,
                 "checked": "checked" in a,
                 "placeholder": a.get("placeholder", ""),
                 "options": []}
            self._cur["fields"].append(f)
            if tag == "select":
                self._sel = f
            if tag == "textarea":
                self._sel = None
        elif tag == "option" and self._sel is not None:
            self._sel["options"].append(a.get("value", ""))
        elif tag == "button" and self._cur is not None:
            self._btn = {"name": a.get("name", ""),
                         "type": (a.get("type") or "submit").lower(),
                         "value": a.get("value", ""),
                         "label": ""}
            self._cur["buttons"].append(self._btn)

    def handle_endtag(self, tag):
        if tag == "select":
            self._sel = None
        elif tag == "button":
            self._btn = None
        elif tag == "form" and self._cur is not None:
            self.forms.append(self._cur)
            self._cur = None

    def handle_data(self, data):
        if self._btn is not None:
            self._btn["label"] += data.strip()


def read_forms(html: str) -> list[dict]:
    """Every form on a page, with the fields it exposes."""
    p = _FormParser()
    try:
        p.feed(html or "")
    except Exception:
        return []
    return p.forms


def risk_of_action(button: dict) -> str:
    """Would pressing this plausibly destroy something?

    Same posture as taskfile_read_v1.risk_of: seeing it is information,
    pressing it is a decision. A UI that offers a delete affordance is not
    thereby asking to have it pressed by something that is only exploring.
    """
    text = " ".join(str(button.get(k) or "")
                    for k in ("name", "value", "label")).lower()
    return "destructive" if any(w in text for w in _DESTRUCTIVE_WORDS) \
        else "safe"


def fields_needing_input(form: dict) -> list[dict]:
    """Fields a caller must supply: not hidden, not readonly, not a button."""
    return [f for f in (form.get("fields") or [])
            if f.get("type") not in ("hidden", "submit", "button", "reset")
            and not f.get("readonly") and f.get("name")]


def hidden_fields(form: dict) -> list[dict]:
    """State that must be replayed -- tokens, CSRF, step markers."""
    return [f for f in (form.get("fields") or [])
            if f.get("type") == "hidden" and f.get("name")]


def describe(forms: list[dict]) -> dict:
    out = []
    for form in forms:
        out.append({
            "action": form.get("action"),
            "method": form.get("method"),
            "required_input": [f["name"] for f in fields_needing_input(form)
                               if f.get("required")],
            "optional_input": [f["name"] for f in fields_needing_input(form)
                               if not f.get("required")],
            "hidden_replay": {f["name"]: f["value"]
                              for f in hidden_fields(form)},
            "choices": {f["name"]: f["options"] for f in form.get("fields") or []
                        if f.get("options")},
            "buttons": [{"label": b.get("label") or b.get("value"),
                         "name": b.get("name"),
                         "risk": risk_of_action(b)} for b in form.get("buttons") or []],
        })
    return {"schema": SCHEMA, "forms": out}


if __name__ == "__main__":
    import sys, json
    print(json.dumps(describe(read_forms(sys.stdin.read())), indent=2))
