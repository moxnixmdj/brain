from __future__ import annotations
import unittest
from canonical.runtime.osworld_computer_surface_v1 import *

S=Screen(1920,1080)

class FakeEnv:
    vm_screen_size=(1920,1080)
    instruction="Do the task"
    def __init__(self): self.actions=[]
    def step(self,action,pause=0):
        self.actions.append((action,pause))
        return {"screenshot":b"png","instruction":self.instruction,"accessibility_tree":None},0,action=="DONE",{}
    def render(self,mode="rgb_array"): return b"png"

class Tests(unittest.TestCase):
    def test_click_exact(self):
        self.assertEqual(compile_osworld_pyautogui({"type":"click","x":10,"y":20,"button":"left"},S),"pyautogui.click(x=10, y=20, button='left')")
    def test_all_core_actions_compile(self):
        cases=[
          {"type":"double_click","x":1,"y":2},
          {"type":"move","x":3,"y":4},
          {"type":"scroll","x":5,"y":6,"scroll_y":-3,"scroll_x":2},
          {"type":"keypress","keys":["CTRL","L"]},
          {"type":"type","text":"hello"},
          {"type":"drag","path":[{"x":1,"y":1},{"x":9,"y":9}]},
          {"type":"wait","duration":1},
          {"type":"done"},
          {"type":"fail"},
        ]
        for a in cases: self.assertIsInstance(compile_osworld_pyautogui(a,S),str)
    def test_text_injection_remains_data(self):
        evil="'); __import__('os').system('id'); #"
        out=compile_osworld_pyautogui({"type":"type","text":evil},S)
        self.assertTrue(out.startswith("pyautogui.write("))
        self.assertIn(repr(evil),out)
        self.assertEqual(out.count("pyautogui."),1)
    def test_coordinate_bounds_fail_closed(self):
        for x,y in [(-1,0),(1920,0),(0,-1),(0,1080)]:
            with self.assertRaises(ComputerSurfaceError):
                compile_osworld_pyautogui({"type":"click","x":x,"y":y},S)
    def test_unknown_key_fails_closed(self):
        with self.assertRaisesRegex(ComputerSurfaceError,"KEY_UNSUPPORTED"):
            compile_osworld_pyautogui({"type":"keypress","keys":["CTRL","totally_not_a_key"]},S)
    def test_arbitrary_command_is_not_an_action(self):
        with self.assertRaisesRegex(ComputerSurfaceError,"ACTION_UNSUPPORTED"):
            compile_osworld_pyautogui({"type":"command","command":"import os; os.system('id')"},S)
    def test_zero_scroll_rejected(self):
        with self.assertRaisesRegex(ComputerSurfaceError,"SCROLL_ZERO"):
            compile_osworld_pyautogui({"type":"scroll","x":1,"y":1,"scroll_x":0,"scroll_y":0},S)
    def test_execute_roundtrip(self):
        e=FakeEnv()
        r=execute_typed_action(e,{"type":"click","x":50,"y":60},pause=0)
        self.assertEqual(r["observation"]["instruction"],"Do the task")
        self.assertEqual(len(e.actions),1)
    def test_observe_roundtrip(self):
        r=observe(FakeEnv())
        self.assertEqual(r["screen"],{"width":1920,"height":1080})
        self.assertEqual(r["instruction"],"Do the task")
    def test_done_maps_to_native_terminal(self):
        e=FakeEnv(); r=execute_typed_action(e,{"type":"done"})
        self.assertTrue(r["done"]); self.assertEqual(r["compiled_action"],"DONE")

if __name__=="__main__": unittest.main(verbosity=2)
