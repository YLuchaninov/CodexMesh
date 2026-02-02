import unittest
from unittest.mock import MagicMock

from codex_mesh.analysis.call_graph import CallGraphBuilder
from codex_mesh.analysis.entrypoints import EntrypointDetector
from codex_mesh.services.tracing_service import TracingService
from codex_mesh.workflows.engine.templating import render_template


class TestNewPhaseFeatures(unittest.TestCase):
    def test_typed_templating(self):
        ctx = {"budget": 1000, "flag": True, "items": [1, 2]}

        # Test int preservation
        self.assertEqual(render_template("{{budget}}", ctx), 1000)
        self.assertIsInstance(render_template("{{budget}}", ctx), int)

        # Test filters
        self.assertEqual(render_template("{{budget|int}}", ctx), 1000)
        self.assertEqual(render_template("{{budget|float}}", ctx), 1000.0)

        # Test list preservation
        self.assertEqual(render_template("{{items}}", ctx), [1, 2])

        # Test string interpolation (casts to str)
        self.assertEqual(render_template("Budget: {{budget}}", ctx), "Budget: 1000")

    def test_entrypoint_detector(self):
        mock_server = MagicMock()
        mock_graph_search = MagicMock()
        mock_server.graph_search = mock_graph_search

        # Mock search results for filenames
        mock_file = MagicMock()
        mock_file.id = "file_1"
        mock_file.name = "main.py"
        mock_file.node_type.value = "file"
        mock_file.relative_path = "src/main.py"

        mock_graph_search.search_by_name.return_value = [mock_file]

        # Mock graph_builder for iteration strategy
        mock_server.graph_builder.get_files.return_value = [mock_file]
        mock_server.graph_builder.get_functions.return_value = []  # no functions

        detector = EntrypointDetector(mock_server)
        result = detector.detect(limit=10)

        self.assertEqual(len(result["entrypoints"]), 1)
        self.assertEqual(result["entrypoints"][0]["name"], "main.py")
        self.assertEqual(result["entrypoints"][0]["kind"], "file")

    def test_node_fields(self):
        from codex_mesh.core.nodes import FunctionNode

        f = FunctionNode.create(
            name="test",
            file_path="t.py",
            line_start=1,
            line_end=10,
            decorators=["@app.get"],
            modifiers=["async"],
        )
        self.assertEqual(f.decorators, ["@app.get"])
        self.assertEqual(f.modifiers, ["async"])

    def test_call_graph_builder(self):
        mock_server = MagicMock()
        mock_graph_search = MagicMock()
        mock_server.graph_search = mock_graph_search

        # Mock subgraph
        n1 = MagicMock()
        n1.id = "root"
        n1.name = "main"
        n1.node_type.value = "function"

        n2 = MagicMock()
        n2.id = "child"
        n2.name = "helper"
        n2.node_type.value = "function"

        mock_graph_search.get_subgraph.return_value = ([n1, n2], [])

        builder = CallGraphBuilder(mock_server)
        res = builder.build(roots=["root"])

        self.assertEqual(len(res["nodes"]), 2)
        self.assertIn("root", [n["id"] for n in res["nodes"]])

    def test_tracing_service(self):
        tracing = TracingService()
        tid = tracing.start_trace()

        tracing.log_step("tool", "test_tool", {"a": 1}, "output", 0.1)

        subgraph = tracing.get_trace_subgraph(tid)
        self.assertTrue(len(subgraph["nodes"]) >= 2)  # start + step

        tracing.stop_trace(tid)


if __name__ == "__main__":
    unittest.main()
