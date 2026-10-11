"""Owner-run launcher for the OSWorld app-capable V2 subject."""
from canonical.runtime.osworld_v21_brain_subject_v2 import SUBJECT_ID, build_subject
from canonical.runtime.osworld_v21_runner_binding_v1 import install as install_binding

def install_into(upstream):
    upstream.PromptAgent=lambda *_args,**_kwargs: build_subject()
    upstream.args.model=SUBJECT_ID
    upstream.args.action_space="pyautogui"
    upstream.args.observation_type="screenshot"
    upstream.args.max_steps=500
    upstream.args.screen_width=1920
    upstream.args.screen_height=1080
    upstream.args.eval_version="v2"
    return install_binding(upstream.lib_run_single)
