import unittest

from canonical.runtime.universal_semantic_hypergraph import (
    RoleBinding,
    SemanticHypergraph,
    SemanticNode,
    SemanticRelation,
    canonical_dict,
    graph_from_canonical_dict,
    roundtrip_is_lossless,
    validate_graph,
)


class Tests(unittest.TestCase):
    def test_unseen_type_and_relation_labels_require_no_code_change(self):
        g = SemanticHypergraph(
            nodes=(
                SemanticNode("n1", "PreviouslyUnseenEntityType::QX-937", ("src:1",), "alpha"),
                SemanticNode("n2", "AnotherNovelType/λ", ("src:2",), "beta"),
            ),
            relations=(
                SemanticRelation(
                    "r1",
                    "novel_relation_label::hypercausal-ish",
                    (
                        RoleBinding("left", "n1"),
                        RoleBinding("right", "n2"),
                    ),
                    ("src:3",),
                    "CANDIDATE",
                ),
            ),
        )
        out = canonical_dict(g)
        self.assertEqual(out["status"], "PASS", out)
        self.assertTrue(out["novel_labels_are_data"])
        self.assertFalse(out["semantic_truth_authority"])

    def test_arbitrary_finite_arity_is_preserved_within_bound(self):
        nodes = tuple(SemanticNode(f"n{i}", f"T{i}", (f"src:{i}",), i) for i in range(10))
        args = tuple(RoleBinding(f"arg{i}", f"n{i}") for i in range(10))
        g = SemanticHypergraph(
            nodes=nodes,
            relations=(SemanticRelation("r", "TenAryRelation", args, ("src:r",), "SUPPORTED"),),
        )
        out = roundtrip_is_lossless(g)
        self.assertEqual(out["status"], "PASS", out)
        self.assertTrue(out["lossless"])
        rel = out["canonical"]["relations"][0]
        self.assertEqual([a["target_id"] for a in rel["arguments"]], [f"n{i}" for i in range(10)])

    def test_higher_order_relation_can_reference_relation(self):
        g = SemanticHypergraph(
            nodes=(
                SemanticNode("a", "Agent", ("src:a",)),
                SemanticNode("b", "Event", ("src:b",)),
            ),
            relations=(
                SemanticRelation("r1", "causes", (RoleBinding("cause", "a"), RoleBinding("effect", "b")), ("src:r1",)),
                SemanticRelation("r2", "reported_by", (RoleBinding("claim", "r1"), RoleBinding("reporter", "a")), ("src:r2",)),
            ),
        )
        self.assertEqual(validate_graph(g)["status"], "PASS")

    def test_finite_cycles_are_representable(self):
        g = SemanticHypergraph(
            nodes=(SemanticNode("anchor", "Anchor", ("src:a",)),),
            relations=(
                SemanticRelation("r1", "refers_to", (RoleBinding("target", "r2"),), ("src:1",), "UNKNOWN"),
                SemanticRelation("r2", "refers_to", (RoleBinding("target", "r1"),), ("src:2",), "UNKNOWN"),
            ),
        )
        self.assertEqual(roundtrip_is_lossless(g)["status"], "PASS")

    def test_conflict_and_ambiguity_status_is_preserved(self):
        g = SemanticHypergraph(
            nodes=(
                SemanticNode("x", "Entity", ("doc:1",)),
                SemanticNode("y", "Entity", ("doc:2",)),
            ),
            relations=(
                SemanticRelation("r1", "same_as", (RoleBinding("a", "x"), RoleBinding("b", "y")), ("doc:1", "doc:2"), "CONFLICT"),
            ),
        )
        enc = canonical_dict(g)
        dec = graph_from_canonical_dict(enc)
        self.assertEqual(dec["status"], "PASS", dec)
        self.assertEqual(dec["graph"].relations[0].status, "CONFLICT")

    def test_missing_provenance_fails_closed(self):
        g = SemanticHypergraph(
            nodes=(SemanticNode("x", "Entity", ()),),
            relations=(),
        )
        out = validate_graph(g)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("PROVENANCE", out["reason"])

    def test_dangling_target_fails_closed(self):
        g = SemanticHypergraph(
            nodes=(SemanticNode("x", "Entity", ("src:x",)),),
            relations=(
                SemanticRelation("r", "uses", (RoleBinding("target", "missing"),), ("src:r",)),
            ),
        )
        out = validate_graph(g)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("DANGLING", out["reason"])

    def test_global_identifier_collision_fails_closed(self):
        g = SemanticHypergraph(
            nodes=(SemanticNode("same", "Entity", ("src:n",)),),
            relations=(
                SemanticRelation("same", "relation", (RoleBinding("x", "same"),), ("src:r",)),
            ),
        )
        out = validate_graph(g)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "GLOBAL_IDENTIFIER_COLLISION_OR_DUPLICATE")

    def test_nonfinite_literal_fails_closed(self):
        g = SemanticHypergraph(
            nodes=(SemanticNode("x", "Number", ("src:x",), float("nan")),),
            relations=(),
        )
        self.assertEqual(validate_graph(g)["status"], "FAIL_CLOSED")

    def test_canonical_roundtrip_exact(self):
        g = SemanticHypergraph(
            nodes=(
                SemanticNode("z", "Zed", ("src:2", "src:1"), 7),
                SemanticNode("a", "Aye", ("src:a",), None),
            ),
            relations=(
                SemanticRelation(
                    "r",
                    "ordered_relation",
                    (RoleBinding("second", "z"), RoleBinding("first", "a")),
                    ("src:r2", "src:r1"),
                    "SUPPORTED",
                ),
            ),
        )
        out = roundtrip_is_lossless(g)
        self.assertEqual(out["status"], "PASS", out)
        self.assertEqual([n["node_id"] for n in out["canonical"]["nodes"]], ["a", "z"])
        self.assertEqual(
            [a["role_label"] for a in out["canonical"]["relations"][0]["arguments"]],
            ["second", "first"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
