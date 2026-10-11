from canonical.runtime.osworld_v21_runner_bridge_v1 import (
    RunnerBridgeError,
    bind_agent_environment,
    build_agent,
    run_native_example,
)


class _Browser:
    def __init__(self):
        self.env = None
    def bind_environment(self, env):
        self.env = env
    def run(self, op):
        return {"type": "OBSERVE"}


def test_build_and_bind():
    browser = _Browser()
    agent = build_agent(
        lambda _state: {"actions": [{"type": "DONE"}]},
        policy_id="p",
        browser_controller=browser,
    )
    env = object()
    bind_agent_environment(agent, env)
    assert browser.env is env


def test_native_runner_is_delegated_without_evaluator_replacement():
    browser = _Browser()
    agent = build_agent(
        lambda _state: {"actions": [{"type": "DONE"}]},
        policy_id="p",
        browser_controller=browser,
    )
    env = object()

    class Native:
        called = None
        @classmethod
        def run_single_example(cls, *args):
            cls.called = args
            return "native-result"

    result = run_native_example(
        lib_run_single=Native,
        agent=agent,
        env=env,
        example={"instruction": "x"},
        max_steps=500,
        instruction="x",
        args=object(),
        result_dir="/tmp/result",
        scores=[],
    )
    assert result == "native-result"
    assert browser.env is env
    assert Native.called[0] is agent
    assert Native.called[1] is env


def test_bridge_rejects_wrong_agent():
    try:
        bind_agent_environment(object(), object())
    except RunnerBridgeError as exc:
        assert str(exc) == "BRAIN_OSWORLD_AGENT_REQUIRED"
    else:
        raise AssertionError("expected rejection")
