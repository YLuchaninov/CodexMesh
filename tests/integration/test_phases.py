import unittest
from unittest.mock import MagicMock

from codex_mesh.analysis.entrypoints import EntrypointDetector
from codex_mesh.core.nodes import FileNode, FunctionNode
from codex_mesh.services.analysis_service import AnalysisService
from codex_mesh.workflows.engine.templating import render_template


class TestPhases2to4(unittest.TestCase):
    def setUp(self):
        self.mock_pm = MagicMock(name="ProjectManager")
        self.mock_server = MagicMock(name="CodexMeshServer")
        self.mock_graph_builder = MagicMock(name="GraphBuilder")
        self.mock_graph_search = MagicMock(name="GraphSearch")

        self.mock_server.graph_builder = self.mock_graph_builder
        self.mock_server.graph_search = self.mock_graph_search

        # Crucial: AnalysisService._get_server uses .server property
        self.mock_pm.server = self.mock_server
        self.mock_pm.get_server.return_value = self.mock_server
        self.mock_pm.project_path = "/abs/src"
        self.mock_server.project_root = "/abs/src"

        self.service = AnalysisService(self.mock_pm)

        # Create real nodes
        self.f1 = FunctionNode.create(
            name="main", file_path="src/main.py", line_start=10, line_end=20
        )
        self.f1.meta["is_main_guard"] = True

        self.f2 = FunctionNode.create(
            name="helper", file_path="src/utils.py", line_start=5, line_end=15
        )
        self.f3 = FunctionNode.create(name="api", file_path="lib/api.py", line_start=1, line_end=10)
        self.file1 = FileNode.create(path="/abs/src/main.py", relative_path="src/main.py")

        self.nodes = [self.f1, self.f2, self.f3, self.file1]
        self.node_map = {n.id: n for n in self.nodes}

        # Setup GraphBuilder mocks
        self.mock_graph_builder.get_node_by_id.side_effect = lambda x: self.node_map.get(x)
        self.mock_graph_builder.get_functions.return_value = [self.f1, self.f2, self.f3]
        self.mock_graph_builder.get_files.return_value = [self.file1]

        # Setup GraphSearch mocks
        # AnalysisService.resolve_symbol uses graph_search.search_by_name (NOT graph_builder)
        self.mock_graph_search.search_by_name.side_effect = lambda q, limit=10: [
            n for n in self.nodes if q.lower() in n.name.lower()
        ]

        # Setup Reachability mock on graph_search (returns tuple of ids, count)
        def mock_reach(roots, max_depth=10, edge_types=None):
            if not roots:
                return [], 0
            root = roots[0]
            if root == self.f1.id:
                ids = [self.f1.id, self.f2.id, self.f3.id]
                return ids, len(ids)
            if root == self.f2.id:
                ids = [self.f2.id, self.f3.id]
                return ids, len(ids)
            if root in self.node_map:
                return [root], 1
            return [], 0

        self.mock_graph_search.compute_reachability.side_effect = mock_reach

        # Setup GraphSearch get_subgraph mock
        def mock_get_subgraph(root, depth=1, direction="both", edge_types=None):
            if root == self.f2.id:
                if direction == "in":
                    return (
                        [self.f1, self.f2],
                        [{"source": self.f1.id, "target": self.f2.id, "type": "calls"}],
                    )
                if direction == "out":
                    return (
                        [self.f2, self.f3],
                        [{"source": self.f2.id, "target": self.f3.id, "type": "calls"}],
                    )
            return ([self.node_map.get(root)] if root in self.node_map else [], [])

        self.mock_graph_search.get_subgraph.side_effect = mock_get_subgraph

    def test_entrypoint_reachability_scoring(self):
        detector = EntrypointDetector(self.mock_server)
        res = detector.detect(limit=10)

        main_entry = next(e for e in res["entrypoints"] if e["id"] == self.f1.id)
        # Verify score is reasonably high and reasons include reachability
        self.assertGreaterEqual(main_entry["score"], 0.67)
        self.assertTrue(any("Reachability" in r for r in main_entry["reasons"]))

    def test_call_graph_callers_callees(self):
        # Use service methods which should now correctly delegate
        res_callers = self.service.callers_of(self.f2.id)
        self.assertEqual(res_callers["count"], 1)
        self.assertEqual(res_callers["callers"][0]["id"], self.f1.id)

        res_callees = self.service.callees_of(self.f2.id)
        self.assertEqual(res_callees["count"], 1)
        self.assertEqual(res_callees["callees"][0]["id"], self.f3.id)

    def test_get_symbol_info_enhanced(self):
        # Resolve by name
        info = self.service.get_symbol_info("helper")
        self.assertTrue(info["found"])
        self.assertEqual(info["id"], self.f2.id)

        # Check canonical fields
        self.assertEqual(info["node_id"], info["id"])
        self.assertIn("span", info)
        self.assertEqual(info["span"]["start_line"], 5)

        # Check call stats
        self.assertIn("call_stats", info)
        self.assertEqual(info["call_stats"]["callers"], 1)
        self.assertEqual(info["call_stats"]["callees"], 1)

    def test_templating_map_join(self):
        ctx = {
            "entries": {
                "entrypoints": [
                    {"id": "e1", "name": "main", "reasons": ["a", "b"]},
                    {"id": "e2", "name": "app", "reasons": ["c"]},
                ]
            }
        }

        ids = render_template("{{entries.entrypoints|map(attribute='id')}}", ctx)
        self.assertEqual(ids, ["e1", "e2"])

        reasons = render_template("{{entries.entrypoints[0].reasons|join(', ')}}", ctx)
        self.assertEqual(reasons, "a, b")


if __name__ == "__main__":
    unittest.main()
