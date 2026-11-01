"""A deterministic virtual desktop that satisfies the OSWorld environment contract.

WHY THIS EXISTS
---------------
The OSWorld stack (90 modules) could not be run here because the sandbox has no browser, no
chromedriver, no Xvfb and no tesseract. That is a *substrate* gap, and it blocked every claim
about whether the computer-use **loop** closes -- not whether it can drive a real OS.

But `osworld_computer_surface_v1.execute_typed_action` and `.observe` take `env: Any` and need
only four members:

    env.vm_screen_size   -> (width, height)
    env.instruction      -> str
    env.step(command)    -> (obs, reward, done, info), obs has "screenshot" and "instruction"
    env.render(mode)     -> screenshot bytes

That is a seam, not a wall. This module is a test double for it: a 1920x1080 screen drawn with
Pillow, a tiny command interpreter for the exact pyautogui strings the repo compiles to, and a
real state change that shows up in the next screenshot.

WHAT THIS PROVES AND WHAT IT DOES NOT
-------------------------------------
Proves: the policy's decision, the adapter's compilation, the surface validator's acceptance,
the observation contract, and that an action changes what the *next* screenshot looks like.
Does NOT prove: that pyautogui drives a real operating system. That still needs a desktop.

The interpreter raises on any command it does not recognise. A harness that silently ignores
a command would manufacture a passing loop out of nothing, which is the failure mode this
whole session has been about.
"""
from __future__ import annotations

import ast
import io
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

from PIL import Image, ImageDraw

SCHEMA = "PROJECT_BRAIN_VIRTUAL_DESKTOP_V1"

# The adapter refuses any screen that is not the matched protocol size.
WIDTH = 1920
HEIGHT = 1080

STATUS_STRIP_HEIGHT = 60
SELECTION_STROKE = 10

COLOR_RGB = {
    "red": (220, 45, 45),
    "green": (45, 170, 75),
    "blue": (50, 100, 220),
    "yellow": (225, 200, 45),
    "orange": (230, 130, 40),
    "purple": (145, 75, 190),
    "pink": (225, 105, 160),
    "black": (25, 25, 25),
    "white": (235, 235, 235),
    "gray": (130, 130, 130),
}


class VirtualDesktopError(RuntimeError):
    """Raised when the driver is handed something it cannot honestly honour."""


@dataclass
class Widget:
    widget_id: str
    rect: tuple[int, int, int, int]
    color: str = "red"
    selected: bool = False
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.color not in COLOR_RGB:
            raise VirtualDesktopError("WIDGET_COLOR_UNKNOWN:" + str(self.color))
        x0, y0, x1, y1 = self.rect
        if not (0 <= x0 < x1 <= WIDTH and 0 <= y0 < y1 <= HEIGHT):
            raise VirtualDesktopError("WIDGET_RECT_OUT_OF_SCREEN:" + self.widget_id)
        if y1 <= STATUS_STRIP_HEIGHT:
            raise VirtualDesktopError("WIDGET_UNDER_STATUS_STRIP:" + self.widget_id)

    def contains(self, x: int, y: int) -> bool:
        x0, y0, x1, y1 = self.rect
        return x0 <= x < x1 and y0 <= y < y1

    @property
    def center(self) -> tuple[int, int]:
        x0, y0, x1, y1 = self.rect
        return (x0 + x1) // 2, (y0 + y1) // 2


# --------------------------------------------------------------------------- command splitting
def split_commands(command: str) -> list[str]:
    """Split on ';' without breaking a quoted semicolon inside a typed string."""
    parts: list[str] = []
    buf: list[str] = []
    quote: str | None = None
    for ch in command:
        if quote is not None:
            buf.append(ch)
            if ch == quote:
                quote = None
        elif ch in {"'", '"'}:
            quote = ch
            buf.append(ch)
        elif ch == ";":
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))
    return [p.strip() for p in parts if p.strip()]


_CLICK = re.compile(r"^pyautogui\.click\(x=(-?\d+), y=(-?\d+), button=(.+)\)$")
_DOUBLE = re.compile(r"^pyautogui\.doubleClick\(x=(-?\d+), y=(-?\d+), button=(.+)\)$")
_MOVE = re.compile(r"^pyautogui\.moveTo\((-?\d+), (-?\d+)(?:, duration=(.+))?\)$")
_WRITE = re.compile(r"^pyautogui\.write\((.*), interval=(.+)\)$", re.DOTALL)
_PRESS = re.compile(r"^pyautogui\.press\((.+)\)$")
_HOTKEY = re.compile(r"^pyautogui\.hotkey\((.+)\)$")
_SCROLL = re.compile(r"^pyautogui\.scroll\((-?\d+)\)$")
_HSCROLL = re.compile(r"^pyautogui\.hscroll\((-?\d+)\)$")
_SLEEP = re.compile(r"^pyautogui\.sleep\((.+)\)$")
_MOUSEDOWN = re.compile(r"^pyautogui\.mouseDown\(button=(.+)\)$")
_MOUSEUP = re.compile(r"^pyautogui\.mouseUp\(button=(.+)\)$")


def _literal(text: str) -> Any:
    try:
        return ast.literal_eval(text.strip())
    except (ValueError, SyntaxError) as exc:
        raise VirtualDesktopError("COMMAND_ARGUMENT_NOT_A_LITERAL:" + text[:80]) from exc


class VirtualDesktop:
    """Deterministic 1920x1080 desktop honouring the OSWorld env contract.

    `success` is the task's own goal predicate; the env reports it as reward, exactly as a real
    OSWorld task config would.
    """

    vm_screen_size = (WIDTH, HEIGHT)

    def __init__(
        self,
        widgets: Sequence[Widget],
        *,
        instruction: str,
        success: Callable[["VirtualDesktop"], bool] | None = None,
    ) -> None:
        if not isinstance(instruction, str) or not instruction.strip():
            raise VirtualDesktopError("INSTRUCTION_REQUIRED")
        self.widgets: list[Widget] = list(widgets)
        ids = [w.widget_id for w in self.widgets]
        if len(ids) != len(set(ids)):
            raise VirtualDesktopError("WIDGET_IDS_NOT_UNIQUE")
        self.instruction = instruction
        self.success = success
        self.commands: list[str] = []
        self.clicks: list[dict[str, Any]] = []
        self.moves: list[tuple[int, int]] = []
        self.typed: list[str] = []
        self.keys: list[str] = []
        self.scrolls: list[tuple[int, int]] = []
        self.waits = 0
        self.done = False
        self.failed = False
        self.reward = 0.0
        self.selected: str | None = None

    # ---------------------------------------------------------------- observation
    def render(self, mode: str = "rgb_array") -> bytes:
        if mode != "rgb_array":
            raise VirtualDesktopError("RENDER_MODE_UNSUPPORTED:" + str(mode))
        img = Image.new("RGB", self.vm_screen_size, (255, 255, 255))
        draw = ImageDraw.Draw(img)
        if self.selected is not None:
            draw.rectangle(
                [0, 0, WIDTH, STATUS_STRIP_HEIGHT], fill=COLOR_RGB["green"]
            )
        for widget in self.widgets:
            draw.rectangle(list(widget.rect), fill=COLOR_RGB[widget.color])
            if widget.selected:
                x0, y0, x1, y1 = widget.rect
                draw.rectangle(
                    [x0, y0, x1, y1], outline=COLOR_RGB["black"], width=SELECTION_STROKE
                )
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def _observation(self) -> dict[str, Any]:
        return {
            "screenshot": self.render("rgb_array"),
            "instruction": self.instruction,
            "screen": {"width": WIDTH, "height": HEIGHT},
        }

    # ---------------------------------------------------------------- goal
    def _reward(self) -> float:
        if self.success is None:
            return 0.0
        return 1.0 if self.success(self) else 0.0

    def widget(self, widget_id: str) -> Widget:
        for widget in self.widgets:
            if widget.widget_id == widget_id:
                return widget
        raise VirtualDesktopError("WIDGET_UNKNOWN:" + widget_id)

    # ---------------------------------------------------------------- actuation
    def _click(self, x: int, y: int, button: str) -> None:
        if button not in {"left", "right", "middle"}:
            raise VirtualDesktopError("BUTTON_UNSUPPORTED:" + button)
        self.clicks.append({"x": x, "y": y, "button": button})
        hit: Widget | None = None
        for widget in reversed(self.widgets):  # later widgets are on top
            if widget.contains(x, y):
                hit = widget
                break
        for widget in self.widgets:
            widget.selected = False
        if hit is not None:
            hit.selected = True
            self.selected = hit.widget_id
        else:
            self.selected = None

    def _apply(self, piece: str) -> None:
        if piece == "WAIT":
            self.waits += 1
            return
        if piece == "DONE":
            self.done = True
            return
        if piece == "FAIL":
            self.failed = True
            self.done = True
            return

        match = _CLICK.match(piece)
        if match:
            self._click(int(match.group(1)), int(match.group(2)), _literal(match.group(3)))
            return
        match = _DOUBLE.match(piece)
        if match:
            self._click(int(match.group(1)), int(match.group(2)), _literal(match.group(3)))
            return
        match = _MOVE.match(piece)
        if match:
            self.moves.append((int(match.group(1)), int(match.group(2))))
            return
        match = _WRITE.match(piece)
        if match:
            text = _literal(match.group(1))
            if not isinstance(text, str):
                raise VirtualDesktopError("WRITE_TEXT_NOT_A_STRING")
            self.typed.append(text)
            return
        match = _PRESS.match(piece)
        if match:
            self.keys.append(_literal(match.group(1)))
            return
        match = _HOTKEY.match(piece)
        if match:
            keys = _literal("(" + match.group(1) + ",)")
            self.keys.append("+".join(str(k) for k in keys))
            return
        match = _SCROLL.match(piece)
        if match:
            self.scrolls.append((0, int(match.group(1))))
            return
        match = _HSCROLL.match(piece)
        if match:
            self.scrolls.append((int(match.group(1)), 0))
            return
        match = _SLEEP.match(piece)
        if match:
            return
        if _MOUSEDOWN.match(piece) or _MOUSEUP.match(piece):
            return
        raise VirtualDesktopError("COMMAND_UNRECOGNISED:" + piece[:120])

    def step(
        self, command: str, *, pause: float = 0.0
    ) -> tuple[dict[str, Any], float, bool, dict[str, Any]]:
        if not isinstance(command, str) or not command.strip():
            raise VirtualDesktopError("COMMAND_REQUIRED")
        # `pause` is accepted for contract compatibility and deliberately ignored: this desktop
        # has no timing, and pretending to wait would be a fiction.
        for piece in split_commands(command):
            self._apply(piece)
        self.commands.append(command)
        self.reward = self._reward()
        done = self.done or self.reward >= 1.0
        return self._observation(), self.reward, done, {"commands": list(self.commands)}
