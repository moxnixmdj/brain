"""The deciding machinery. Arithmetic only.

Harvested from LATS (Zhou et al., ICML 2024, arXiv:2310.04406), which runs
Monte Carlo Tree Search over an agent's actions.

Everything in this file is deterministic. Selection, backpropagation and
best-trajectory extraction are formulas. There is no model here, and none is
needed for these parts.

LATS needs a model for two things: proposing candidate actions, and scoring a
state. Both are injected here as functions, so they can be supplied by
Brain-owned machinery -- our two model-free oracles fill the scoring slot
directly.

    Q(node) <- ( Q(node) * (N(node) - 1) + V ) / N(node)
    UCB     <- Q + c * sqrt( ln(N(parent)) / N(node) )

The second term is what keeps an underexplored branch alive. That is the
structural answer to "agents abandon ambitious targets early": a branch that
has been tried once and scored well is not yet preferred over one never
tried, because the untried branch carries a larger exploration bonus.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class Node:
    state: object = None
    action: object = None
    parent: "Node | None" = None
    children: list["Node"] = field(default_factory=list)
    value: float = 0.0
    visits: int = 0
    reflection: str | None = None
    terminal: bool = False

    @property
    def mean_value(self) -> float:
        return self.value / self.visits if self.visits else 0.0

    @property
    def depth(self) -> int:
        return 0 if self.parent is None else self.parent.depth + 1


def ucb(node: Node, c: float = 1.4) -> float:
    """Upper confidence bound. Arithmetic, not a model."""
    if node.visits == 0:
        return float("inf")
    if node.parent is None or node.parent.visits == 0:
        return node.mean_value
    exploit = node.mean_value
    explore = c * math.sqrt(math.log(node.parent.visits) / node.visits)
    return exploit + explore


def select(root: Node, c: float = 1.4) -> Node:
    """Descend to a leaf, always choosing the highest UCB child."""
    node = root
    while node.children:
        node = max(node.children, key=lambda n: ucb(n, c))
    return node


def expand(node: Node, actions, make_state) -> list[Node]:
    """Attach a child per candidate action. No action is discarded."""
    fresh = []
    for action in actions:
        child = Node(state=make_state(node.state, action), action=action, parent=node)
        node.children.append(child)
        fresh.append(child)
    return fresh


def backpropagate(node: Node, value: float) -> None:
    """Running average up the tree. Arithmetic."""
    cur: Node | None = node
    while cur is not None:
        cur.visits += 1
        cur.value += (value - cur.value) / cur.visits
        cur = cur.parent


def best_trajectory(root: Node) -> list[Node]:
    """Most-visited path from root. Visits, not raw value, so a lucky single
    high score cannot beat a branch that consistently earned its visits."""
    path, node = [root], root
    while node.children:
        node = max(node.children, key=lambda n: n.visits)
        path.append(node)
    return path


def best_action(root: Node):
    """The first move of the best trajectory."""
    traj = best_trajectory(root)
    return traj[1].action if len(traj) > 1 else None


def search(root, actions_fn, evaluate_fn, iterations=30, c=1.4,
           make_state=lambda s, a: (s, a), reflect_fn=None):
    """Run the tree search.

    actions_fn(node)  -> candidate actions        (supply from our grounding)
    evaluate_fn(node) -> value in [0,1]           (supply from our oracles)
    reflect_fn(node)  -> reflection string/None   (supply from decision.synthesis)
    """
    root.visits = 1
    for _ in range(iterations):
        leaf = select(root, c)
        if leaf.terminal:
            backpropagate(leaf, evaluate_fn(leaf))
            continue
        children = expand(leaf, actions_fn(leaf), make_state)
        for child in children:
            value = evaluate_fn(child)
            if value <= 0.0 and reflect_fn is not None:
                # Failure is recorded, not discarded. This is the reflection
                # slot: the next attempt sees what failed and why.
                child.reflection = reflect_fn(child)
            backpropagate(child, value)
    return root


if __name__ == "__main__":
    # Deterministic demo: one branch is genuinely better, and the evaluator
    # is a plain function -- the slot our oracles occupy in real use.
    def actions(node):
        return [] if node.depth >= 2 else ["left", "right", "untried"]

    def evaluate(node):
        if node.depth == 0:
            return 0.0
        return {"left": 0.9, "right": 0.4, "untried": 0.6}.get(node.action, 0.0)

    root = Node(state="start")
    search(root, actions, evaluate, iterations=60)
    print("root visits:", root.visits)
    for ch in sorted(root.children, key=lambda n: -n.visits):
        print(f"  {ch.action:<9} visits={ch.visits:<4} mean={ch.mean_value:.3f}")
    print("DECISION:", best_action(root))
