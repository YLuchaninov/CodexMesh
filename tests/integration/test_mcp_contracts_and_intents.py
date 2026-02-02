import unittest
from unittest.mock import MagicMock, patch

from codex_mesh.api.tools import register_tools
from codex_mesh.services.analysis_service import AnalysisService


class TestMCPContractsAndIntents(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mock_server = MagicMock()
        self.mock_pm = MagicMock()

        # Setup AnalysisService mock
        self.mock_analysis_service = MagicMock(spec=AnalysisService)

        # Mock project manager to return our mock service
        # NOTE: register_tools creates a NEW AnalysisService(pm).
        # So we need to patch AnalysisService class to return our mock instance
        # OR we just test the tools by inspecting the registered functions.
        # But register_tools uses decorators.

        # Let's verify contracts by calling the service methods directly first (since we saw they implement logic)
        # AND then verify tool wrappers if possible.
        pass

    def test_semantic_search_contract(self):
        """Part 1.3: Fix semantic_search (line_end error) and align fields."""
        service = AnalysisService(self.mock_pm)
        service._get_server = MagicMock()

        # Mock vector search result (dict or object)
        mock_result_dict = {
            "id": "node_1",
            "name": "test_func",
            "file_path": "src/test.py",
            "line_start": 10,
            # line_end missing
            "score": 0.9,
            "content": "def test_func():\n    pass",
        }

        service._get_server().vector_search.search.return_value = [mock_result_dict]

        results = service.semantic_search("query")

        self.assertEqual(len(results), 1)
        item = results[0]

        # Check mandatory fields
        self.assertIn("id", item)
        self.assertIn("span", item)
        self.assertIn("line_end", item)

        # Check padding logic (line_end = line_start if missing)
        self.assertEqual(item["line_end"], 10)
        self.assertEqual(item["span"], {"start_line": 10, "end_line": 10})

    def test_templating_numbers(self):
        """Part 1.2: Typed templating."""
        from codex_mesh.workflows.engine.templating import render_template

        ctx = {"token_budget": 2000}

        # 1. Exact match returns int
        val = render_template("{{token_budget}}", ctx)
        self.assertIsInstance(val, int)
        self.assertEqual(val, 2000)

        # 2. String interpolation returns str
        val_str = render_template("Budget: {{token_budget}}", ctx)
        self.assertIsInstance(val_str, str)
        self.assertEqual(val_str, "Budget: 2000")

        # 3. Filter |int
        ctx2 = {"budget_str": "1500"}
        val_int = render_template("{{budget_str|int}}", ctx2)
        self.assertIsInstance(val_int, int)
        self.assertEqual(val_int, 1500)

    def test_strict_input_validation(self):
        """Part 1.4: Strict input validation (resolve_symbol)."""
        service = AnalysisService(self.mock_pm)

        # Test None query
        res = service.resolve_symbol(None)
        self.assertIsNone(res["best"])
        self.assertEqual(res["error"], "Query string is empty or None")

        # Test empty query
        res = service.resolve_symbol("   ")
        self.assertIsNone(res["best"])
        self.assertEqual(res["error"], "Query string is empty or None")

    @patch("codex_mesh.api.tools.ProjectService")
    @patch("codex_mesh.api.tools.AnalysisService")
    async def test_api_tool_signatures(self, MockServiceClass, MockProjectServiceClass):
        """Part 5.17: Contract tests for MCP tool wrappers."""
        # We want to check that api/tools.py functions actually call service with correct args
        mock_service = MockServiceClass.return_value

        # Ensure ensure_ready passes
        mock_ps = MockProjectServiceClass.return_value
        mock_ps.ensure_ready.return_value = None

        # Create a fake server to capture tool registrations
        class FakeFastMCP:
            def __init__(self):
                self.tools = {}

            def tool(self):
                def decorator(func):
                    self.tools[func.__name__] = func
                    return func

                return decorator

        fake_server = FakeFastMCP()
        mock_pm = MagicMock()

        register_tools(fake_server, mock_pm)

        # Check specific tools existence
        self.assertIn("read_span", fake_server.tools)
        self.assertIn("build_call_graph", fake_server.tools)
        self.assertIn("detect_entrypoints", fake_server.tools)

        # Test read_span wrapper
        await fake_server.tools["read_span"](path="foo.py", start_line=1, end_line=10)
        mock_service.read_span.assert_called_with("foo.py", 1, 10, context=0)

        # Test new deep tool: build_call_graph
        await fake_server.tools["build_call_graph"](roots=["root1"], depth=2)
        mock_service.build_call_graph.assert_called_with(["root1"], 2, "out", 200)


if __name__ == "__main__":
    unittest.main()
