from types import SimpleNamespace

from canonical.runtime.osworld_v21_runner_binding_v1 import install


class Agent:
    def __init__(self):
        self.bound = None
    def bind_environment(self, env):
        self.bound = env


def test_install_binds_before_exact_delegate():
    calls = []
    def original(agent, env, value):
        calls.append((agent.bound is env, value))
        return "ok"

    module = SimpleNamespace(run_single_example=original)
    receipt = install(module)
    env = object()
    agent = Agent()
    out = module.run_single_example(agent, env, 7)
    assert out == "ok"
    assert calls == [(True, 7)]
    assert receipt["evaluator_changed"] is False
    assert receipt["scoring_changed"] is False


def test_install_is_idempotent():
    module = SimpleNamespace(run_single_example=lambda agent, env: None)
    first = install(module)
    wrapped = module.run_single_example
    second = install(module)
    assert first["status"] == "INSTALLED"
    assert second["status"] == "ALREADY_INSTALLED"
    assert module.run_single_example is wrapped
