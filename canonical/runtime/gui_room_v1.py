"""The GUI room: a real browser, a real page, observed structurally -- never from pixels alone.

WHAT THIS IS
------------
An arbitrary computer environment that is a web page in a real Chromium. The room
speaks CDP; the agent observes the page's own DOM (roles, accessible names,
bounding boxes, enabled state), acts with trusted input events (Input domain),
and observes the effect. No screenshot, no vision model, no model call of any
kind. A click is dispatched at the element's centre; text enters through
Input.insertText; the page's own state (its storage, its DOM) is the oracle for
every claim made here.

WHAT THIS IS NOT
----------------
Not a general RPA driver, not a benchmark harness, not a security boundary.
It observes one page at a time. It fails closed: a target that is not unique is
an ESCALATE, never a guess. It cannot see inside closed shadow roots (reported,
not hidden). It is an instrument for measuring what a model-free agent can do
in exactly the hardest browser environments that exist today.

The room works with ANY page. What is page-specific lives in the caller (the
task's goal predicate and the need), never here.

Model calls: 0. Network at decision time: 0 (the page itself is local).
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys
import time
from typing import Any

REPO = pathlib.Path(__file__).resolve().parents[2]
BRIDGE = pathlib.Path(__file__).resolve().parents[1] / "tools" / "cdp_bridge_v1.cjs"
NODE = "node"
DEFAULT_DEBUG_URL = "http://127.0.0.1:9222"

SCHEMA = "PROJECT_BRAIN_GUI_ROOM_V1"

# The observation: a JSON serializer injected into the page. Computes role and
# accessible name from the page's own DOM, plus geometry and enabled state.
# Honest limits: closed shadow roots are opaque; `contenteditable` text fields
# are reported as textbox; `li` keeps its implicit listitem role.
_OBSERVE_JS = r"""(() => {
  const out = [];
  const IMPLICIT = { INPUT: 'textbox', BUTTON: 'button', A: 'link', SELECT: 'combobox', TEXTAREA: 'textbox', LI: 'listitem' };
  function roleOf(el) {
    const explicit = el.getAttribute('role');
    if (explicit) return explicit;
    if (el.tagName === 'INPUT') {
      const t = (el.getAttribute('type') || 'text').toLowerCase();
      if (t === 'checkbox') return 'checkbox';
      if (t === 'radio') return 'radio';
      if (t === 'button' || t === 'submit' || t === 'reset') return 'button';
      if (t === 'search') return 'searchbox';
      return 'textbox';
    }
    if (el.tagName === 'BUTTON') return 'button';
    if (el.isContentEditable) return 'textbox';
    return IMPLICIT[el.tagName] || null;
  }
  function nameOf(el) {
    const aria = el.getAttribute('aria-label');
    if (aria && aria.trim()) return aria.trim();
    const labelledBy = el.getAttribute('aria-labelledby');
    if (labelledBy) {
      const ref = document.getElementById(labelledBy);
      if (ref && (ref.innerText || '').trim()) return ref.innerText.trim().slice(0, 200);
    }
    if (el.id) {
      const label = document.querySelector('label[for="' + CSS.escape(el.id) + '"]');
      if (label && (label.innerText || '').trim()) return label.innerText.trim().slice(0, 200);
    }
    const wrapping = el.closest('label');
    if (wrapping && (wrapping.innerText || '').trim()) return wrapping.innerText.trim().slice(0, 200);
    const placeholder = el.getAttribute('placeholder');
    if (placeholder && placeholder.trim()) return placeholder.trim();
    const title = el.getAttribute('title');
    if (title && title.trim()) return title.trim();
    const text = (el.innerText || '').trim();
    if (text) return text.slice(0, 200);
    return '';
  }
  function visibleRect(el) {
    const r = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    const visible = r.width > 0 && r.height > 0 && style.visibility !== 'hidden'
      && style.display !== 'none' && style.opacity !== '0';
    return { x: r.left + r.width / 2, y: r.top + r.height / 2,
             w: r.width, h: r.height, visible };
  }
  function enabledOf(el) {
    if (el.disabled) return false;
    if (el.closest('[aria-disabled="true"]')) return false;
    return true;
  }
  const seen = new Set();
  for (const el of document.querySelectorAll('*')) {
    const role = roleOf(el);
    if (!role) continue;
    const rect = visibleRect(el);
    if (!rect.visible) continue;
    const key = role + '|' + nameOf(el) + '|' + Math.round(rect.x) + ',' + Math.round(rect.y);
    if (seen.has(key)) continue;
    seen.add(key);
    // container text = the nearest enclosing listitem/row/section text, so a
    // control inside a todo item can be bound by the item's words
    const container = el.closest('li, [role="listitem"], tr, [role="row"]');
    out.push({
      role,
      name: nameOf(el),
      text: ((el.innerText || '').trim()).slice(0, 200),
      container_text: container ? ((container.innerText || '').trim()).slice(0, 300) : '',
      id: el.id || '',
      tag: el.tagName.toLowerCase(),
      x: Math.round(rect.x * 10) / 10,
      y: Math.round(rect.y * 10) / 10,
      w: Math.round(rect.w * 10) / 10,
      h: Math.round(rect.h * 10) / 10,
      enabled: enabledOf(el),
      actions: role === 'textbox' ? ['set_text', 'click'] : ['click'],
    });
  }
  return out;
})()"""


class GuiRoomError(RuntimeError):
    pass


class GuiRoom:
    """One page in one real Chromium tab, driven over CDP."""

    def __init__(self, url: str, *, debug_url: str = DEFAULT_DEBUG_URL,
                 settle_s: float = 0.4) -> None:
        self.url = url
        self.debug_url = debug_url.rstrip("/")
        self.settle_s = float(settle_s)
        self.proc: subprocess.Popen | None = None
        self._next_id = 0
        self._open()

    # -------------------------------------------------------------- #
    # transport
    # -------------------------------------------------------------- #
    def _open(self) -> None:
        self.proc = subprocess.Popen(
            [NODE, str(BRIDGE)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, cwd=str(REPO),
            env={"PATH": "/usr/local/bin:/usr/bin:/bin",
                 "CDP_DEBUG_URL": self.debug_url},
        )
        self._rpc("open", url=self.url)

    def _rpc(self, op: str, **kwargs: Any) -> Any:
        assert self.proc and self.proc.stdin and self.proc.stdout
        self._next_id += 1
        msg = {"id": self._next_id, "op": op, **kwargs}
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if not line:
            raise GuiRoomError("BRIDGE_EOF: " + (self.proc.stderr.read() if self.proc.stderr else ""))
        out = json.loads(line)
        if not out.get("ok"):
            raise GuiRoomError(str(out.get("error", "UNKNOWN"))[:500])
        return out

    def close(self) -> None:
        if not self.proc:
            return
        try:
            self._rpc("close")
        except Exception:
            pass
        try:
            self.proc.terminate()
        except Exception:
            pass
        self.proc = None

    # -------------------------------------------------------------- #
    # observation
    # -------------------------------------------------------------- #
    def evaluate(self, expression: str) -> Any:
        return self._rpc("evaluate", expression=expression).get("value")

    def navigate(self, url: str | None = None) -> None:
        self._rpc("open", url=url or self.url)

    def reset_app(self) -> None:
        """Back to a pristine app: same page, cleared storage, fresh boot."""
        self.evaluate("localStorage.clear()")
        self.navigate()
        time.sleep(self.settle_s)

    def observe(self) -> list[dict[str, Any]]:
        raw = self.evaluate(_OBSERVE_JS)
        return list(raw or [])

    def fingerprint(self, elements: list[dict[str, Any]]) -> str:
        canonical = [{k: e[k] for k in ("role", "name", "text", "container_text", "tag", "enabled")}
                     for e in elements]
        blob = json.dumps(canonical, sort_keys=True, ensure_ascii=True)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]

    def console_log(self, *, clear: bool = True) -> list[str]:
        return list(self._rpc("console", clear=clear).get("log", []))

    # -------------------------------------------------------------- #
    # actuation (trusted input events)
    # -------------------------------------------------------------- #
    def click(self, element: dict[str, Any]) -> None:
        self._rpc("click", x=element["x"], y=element["y"])
        time.sleep(self.settle_s)

    def set_text(self, element: dict[str, Any], text: str) -> None:
        # focus through the page itself, then insert with the Input domain:
        # the text is real input, not a value assignment
        if element.get("id"):
            self.evaluate(f"document.getElementById({json.dumps(element['id'])}).focus()")
        else:
            self.click(element)
        self._rpc("insert_text", text=text)
        time.sleep(self.settle_s)

    def press_enter(self) -> None:
        self._rpc("press", key="Enter")
        time.sleep(self.settle_s)

    # -------------------------------------------------------------- #
    # grounding: an element or NOTHING
    # -------------------------------------------------------------- #
    @staticmethod
    def ground_unique(elements: list[dict[str, Any]], *,
                      role: str | None = None,
                      name: str | None = None,
                      container_contains: str | None = None) -> dict[str, Any]:
        """Unique visible, enabled element matching the constraint, or an ESCALATE.

        `container_contains` joins an element to the one whose innerText carries
        the datum -- the honest way to find 'the checkbox for THIS todo' when
        checkboxes carry no accessible name of their own.
        """
        hits = []
        for e in elements:
            if not e.get("enabled", True):
                continue
            if role is not None and e.get("role") != role:
                continue
            if name is not None and e.get("name") != name:
                continue
            if container_contains is not None:
                if container_contains not in e.get("container_text", ""):
                    continue
            hits.append(e)
        if len(hits) == 1:
            return {"status": "SELECT", "element": hits[0]}
        return {"status": "ESCALATE",
                "reason": "NO_MATCH" if not hits else f"AMBIGUOUS:{len(hits)}",
                "candidates": len(hits)}
