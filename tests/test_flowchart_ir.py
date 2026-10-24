import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from flowchart_ir import render_mermaid, validate_ir


class FlowchartValidationTest(unittest.TestCase):
    def sample(self):
        return json.loads((ROOT / "examples/sample_flow.json").read_text(encoding="utf-8"))

    def test_examples_have_scopes_annotated_nodes_and_edges(self):
        for filename in ("sample_flow.json",):
            path = ROOT / "examples" / filename
            model = json.loads(path.read_text(encoding="utf-8"))
            with self.subTest(filename=filename):
                self.assertEqual(validate_ir(model), [])
                out = render_mermaid(model)
                self.assertEqual(out.count("  subgraph scope_"), len(model["functions"]))
                self.assertEqual(out.count("<br/>P:"), sum(len(f["nodes"]) for f in model["functions"]))
                self.assertEqual(out.count("<br/>Δ:"), sum(len(f["nodes"]) for f in model["functions"]))

    def test_reject_duplicate_node_across_function_boxes(self):
        m = self.sample()
        m["functions"][1]["nodes"][0]["id"] = m["functions"][0]["nodes"][0]["id"]
        self.assertTrue(any("duplicate node" in e for e in validate_ir(m)))

    def test_reject_unlabeled_edge(self):
        m = self.sample()
        m["edges"][0]["label"] = ""
        self.assertTrue(any("explicit label" in e for e in validate_ir(m)))

    def test_reject_missing_parameter_causality(self):
        m = self.sample()
        node = next(n for f in m["functions"] for n in f["nodes"] if n["params"])
        node["params"][0]["controls"] = "affects output"
        self.assertTrue(any("too vague" in e for e in validate_ir(m)))

    def test_reject_unknown_node_in_edge(self):
        m = self.sample()
        m["edges"][0]["from"] = "not_a_declared_node"
        self.assertTrue(any("unknown node" in e for e in validate_ir(m)))

    def test_reject_decision_with_one_outgoing_edge(self):
        m = self.sample()
        decision = next(n["id"] for f in m["functions"] for n in f["nodes"] if n["kind"] == "decision")
        m["edges"] = [e for e in m["edges"] if e["from"] != decision] + [{"from": decision, "to": m["functions"][0]["nodes"][0]["id"], "label": "one"}]
        self.assertTrue(any("at least two" in e for e in validate_ir(m)))


if __name__ == "__main__":
    unittest.main()
