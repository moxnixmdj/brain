from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence
import math

class ComputerSurfaceError(ValueError):
    pass

_ALLOWED_BUTTONS={"left","right","middle"}
_KEY_ALIASES={
    "control":"ctrl","ctrl":"ctrl","alt":"alt","option":"alt","shift":"shift",
    "cmd":"command","command":"command","meta":"command","super":"win","win":"win",
    "enter":"enter","return":"enter","tab":"tab","esc":"esc","escape":"esc",
    "backspace":"backspace","delete":"delete","space":"space",
    "up":"up","down":"down","left":"left","right":"right",
    "arrowup":"up","arrowdown":"down","arrowleft":"left","arrowright":"right",
    "home":"home","end":"end","pageup":"pageup","pagedown":"pagedown",
}
_ALLOWED_NAMED_KEYS=set(_KEY_ALIASES.values()) | {f"f{i}" for i in range(1,13)}

@dataclass(frozen=True)
class Screen:
    width:int
    height:int
    def __post_init__(self):
        if isinstance(self.width,bool) or isinstance(self.height,bool) or self.width<=0 or self.height<=0:
            raise ComputerSurfaceError("SCREEN_INVALID")

def _num(v:Any,name:str)->float:
    if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(float(v)):
        raise ComputerSurfaceError(name+"_INVALID")
    return float(v)

def _coord(v:Any,limit:int,name:str)->int:
    x=_num(v,name)
    if x!=int(x): raise ComputerSurfaceError(name+"_NONINTEGER")
    x=int(x)
    if x<0 or x>=limit: raise ComputerSurfaceError(name+"_OUT_OF_BOUNDS")
    return x

def _action_type(a:Mapping[str,Any])->str:
    t=a.get("type")
    if not isinstance(t,str) or not t: raise ComputerSurfaceError("ACTION_TYPE_INVALID")
    return t

def _key(v:Any)->str:
    if not isinstance(v,str) or not v: raise ComputerSurfaceError("KEY_INVALID")
    k=v.strip().lower()
    if len(k)==1 and (k.isalnum() or k in "-=[]\\;',./"):
        return k
    k=_KEY_ALIASES.get(k,k)
    if k not in _ALLOWED_NAMED_KEYS: raise ComputerSurfaceError("KEY_UNSUPPORTED:"+v)
    return k

def _pt(p:Any,screen:Screen)->tuple[int,int]:
    if not isinstance(p,Mapping): raise ComputerSurfaceError("POINT_INVALID")
    return _coord(p.get("x"),screen.width,"X"),_coord(p.get("y"),screen.height,"Y")

def compile_osworld_pyautogui(action:Mapping[str,Any],screen:Screen)->str:
    if not isinstance(action,Mapping): raise ComputerSurfaceError("ACTION_INVALID")
    t=_action_type(action)
    if t=="click":
        x,y=_pt(action,screen)
        b=action.get("button","left")
        if b=="wheel": b="middle"
        if b not in _ALLOWED_BUTTONS: raise ComputerSurfaceError("BUTTON_INVALID")
        return f"pyautogui.click(x={x}, y={y}, button={b!r})"
    if t=="double_click":
        x,y=_pt(action,screen)
        return f"pyautogui.doubleClick(x={x}, y={y}, button='left')"
    if t=="move":
        x,y=_pt(action,screen)
        return f"pyautogui.moveTo({x}, {y})"
    if t=="scroll":
        x,y=_pt(action,screen)
        sx=_num(action.get("scroll_x",0),"SCROLL_X")
        sy=_num(action.get("scroll_y",0),"SCROLL_Y")
        if sx==0 and sy==0: raise ComputerSurfaceError("SCROLL_ZERO")
        if abs(sx)>10000 or abs(sy)>10000: raise ComputerSurfaceError("SCROLL_EXCESSIVE")
        parts=[f"pyautogui.moveTo({x}, {y})"]
        if sy: parts.append(f"pyautogui.scroll({int(sy)})")
        if sx: parts.append(f"pyautogui.hscroll({int(sx)})")
        return "; ".join(parts)
    if t=="keypress":
        raw=action.get("keys")
        if not isinstance(raw,Sequence) or isinstance(raw,(str,bytes)) or not raw:
            raise ComputerSurfaceError("KEYS_INVALID")
        keys=[_key(x) for x in raw]
        if len(keys)>4: raise ComputerSurfaceError("KEYS_TOO_MANY")
        if len(keys)==1: return f"pyautogui.press({keys[0]!r})"
        return "pyautogui.hotkey("+", ".join(repr(k) for k in keys)+")"
    if t=="type":
        text=action.get("text")
        if not isinstance(text,str) or not text: raise ComputerSurfaceError("TEXT_INVALID")
        if len(text)>20000: raise ComputerSurfaceError("TEXT_EXCESSIVE")
        interval=action.get("interval",0.01)
        interval=_num(interval,"TYPE_INTERVAL")
        if interval<0 or interval>1: raise ComputerSurfaceError("TYPE_INTERVAL_RANGE")
        return f"pyautogui.write({text!r}, interval={interval!r})"
    if t=="drag":
        path=action.get("path")
        if not isinstance(path,Sequence) or isinstance(path,(str,bytes)) or len(path)<2 or len(path)>128:
            raise ComputerSurfaceError("DRAG_PATH_INVALID")
        pts=[_pt(p,screen) for p in path]
        dur=_num(action.get("duration_per_segment",0.05),"DRAG_DURATION")
        if dur<0 or dur>2: raise ComputerSurfaceError("DRAG_DURATION_RANGE")
        parts=[f"pyautogui.moveTo({pts[0][0]}, {pts[0][1]})","pyautogui.mouseDown(button='left')"]
        parts.extend(f"pyautogui.moveTo({x}, {y}, duration={dur!r})" for x,y in pts[1:])
        parts.append("pyautogui.mouseUp(button='left')")
        return "; ".join(parts)
    if t=="wait":
        seconds=_num(action.get("duration",0),"WAIT_DURATION")
        if seconds<0 or seconds>30: raise ComputerSurfaceError("WAIT_DURATION_RANGE")
        return "WAIT" if seconds<=2 else f"pyautogui.sleep({seconds!r})"
    if t=="done": return "DONE"
    if t=="fail": return "FAIL"
    raise ComputerSurfaceError("ACTION_UNSUPPORTED:"+t)

def execute_typed_action(env:Any,action:Mapping[str,Any],*,pause:float=0.0):
    size=getattr(env,"vm_screen_size",None)
    if not isinstance(size,(tuple,list)) or len(size)!=2:
        raise ComputerSurfaceError("SCREEN_SIZE_UNAVAILABLE")
    screen=Screen(int(size[0]),int(size[1]))
    command=compile_osworld_pyautogui(action,screen)
    obs,reward,done,info=env.step(command,pause=pause)
    if not isinstance(obs,Mapping) or "screenshot" not in obs or "instruction" not in obs:
        raise ComputerSurfaceError("OBSERVATION_CONTRACT_BROKEN")
    return {"compiled_action":command,"observation":obs,"reward":reward,"done":bool(done),"info":info}

def observe(env:Any):
    obs=env.render("rgb_array")
    instruction=getattr(env,"instruction",None)
    if obs is None or not isinstance(instruction,str):
        raise ComputerSurfaceError("OBSERVATION_UNAVAILABLE")
    size=getattr(env,"vm_screen_size",None)
    if not isinstance(size,(tuple,list)) or len(size)!=2:
        raise ComputerSurfaceError("SCREEN_SIZE_UNAVAILABLE")
    return {"screenshot":obs,"instruction":instruction,"screen":{"width":int(size[0]),"height":int(size[1])}}
