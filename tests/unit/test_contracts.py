"""
Unit tests for contracts.

Tests that contract models serialize/deserialize correctly.
"""

from codex_mesh.contracts import (
    ConnectOptions,
    ConnectRequest,
    EdgeDTO,
    FSEntry,
    FSListRequest,
    FSReadResponse,
    HotspotItem,
    IntentExecuteRequest,
    IntentItem,
    NodeDTO,
    RepoMapResponse,
    SearchRequest,
    StatusSnapshot,
    SubgraphRequest,
    ToolTraceStep,
    dump_model,
)


class TestStatusContracts:
    """Tests for status-related contracts."""

    def test_status_snapshot_defaults(self):
        """Test StatusSnapshot with defaults."""
        snap = StatusSnapshot(status="IDLE")
        assert snap.status == "IDLE"
        assert snap.progress == 0.0
        assert snap.message == ""
        assert snap.project_path is None

    def test_status_snapshot_full(self):
        """Test StatusSnapshot with all fields."""
        snap = StatusSnapshot(
            status="READY", progress=100.0, message="Connected", project_path="/test"
        )
        assert snap.status == "READY"
        assert snap.progress == 100.0
        assert snap.project_path == "/test"

    def test_connect_request(self):
        """Test ConnectRequest model."""
        req = ConnectRequest(project_path="/test/path")
        assert req.project_path == "/test/path"
        assert req.options.auto_index is True
        assert req.options.force_reindex is False

    def test_connect_options(self):
        """Test ConnectOptions model."""
        opts = ConnectOptions(auto_index=False, force_reindex=True)
        assert opts.auto_index is False
        assert opts.force_reindex is True


class TestFSContracts:
    """Tests for file system contracts."""

    def test_fs_list_request_defaults(self):
        """Test FSListRequest defaults."""
        req = FSListRequest()
        assert req.path == "."
        assert req.recursive is False
        assert req.include_hidden is False

    def test_fs_entry(self):
        """Test FSEntry model."""
        entry = FSEntry(name="test.py", path="src/test.py", type="file", size=123)
        assert entry.name == "test.py"
        assert entry.type == "file"
        assert entry.size == 123

    def test_fs_read_response(self):
        """Test FSReadResponse model."""
        resp = FSReadResponse(path="test.py", content="print('hi')", truncated=False)
        assert resp.path == "test.py"
        assert resp.content == "print('hi')"
        assert resp.truncated is False


class TestAnalysisContracts:
    """Tests for analysis contracts."""

    def test_search_request_validation(self):
        """Test SearchRequest validation."""
        req = SearchRequest(query="test", limit=100)
        assert req.query == "test"
        assert req.limit == 100

    def test_hotspot_item_alias(self):
        """Test HotspotItem accepts 'total' alias."""
        item = HotspotItem(total=0.85, file_path="test.py")
        assert item.hotspot_score == 0.85
        assert item.file_path == "test.py"

    def test_repomap_response(self):
        """Test RepoMapResponse model."""
        resp = RepoMapResponse(map="# Repo\n- file.py", token_estimate=50.0)
        assert "Repo" in resp.map
        assert resp.token_estimate == 50.0


class TestGraphContracts:
    """Tests for graph contracts."""

    def test_node_dto(self):
        """Test NodeDTO model."""
        node = NodeDTO(id="n1", name="my_func", type="function", file_path="test.py")
        assert node.id == "n1"
        assert node.type == "function"

    def test_edge_dto(self):
        """Test EdgeDTO model."""
        edge = EdgeDTO(source="n1", target="n2", type="calls")
        assert edge.source == "n1"
        assert edge.target == "n2"

    def test_subgraph_request(self):
        """Test SubgraphRequest model."""
        req = SubgraphRequest(roots=["n1", "n2"], depth=2)
        assert len(req.roots) == 2
        assert req.depth == 2
        assert req.direction == "both"


class TestIntentContracts:
    """Tests for intent contracts."""

    def test_intent_item(self):
        """Test IntentItem model."""
        item = IntentItem(id="test.intent", title="Test Intent", description="A test")
        assert item.id == "test.intent"
        assert item.title == "Test Intent"

    def test_tool_trace_step(self):
        """Test ToolTraceStep model."""
        step = ToolTraceStep(tool="search", input={"q": "test"}, output_preview="result")
        assert step.tool == "search"
        assert step.input == {"q": "test"}

    def test_intent_execute_request(self):
        """Test IntentExecuteRequest model."""
        req = IntentExecuteRequest(intent_id="test", input={"query": "hello"})
        assert req.intent_id == "test"
        assert req.options.include_trace is True


class TestDumpModel:
    """Tests for dump_model utility."""

    def test_dump_model_with_pydantic(self):
        """Test dump_model with Pydantic model."""
        snap = StatusSnapshot(status="IDLE")
        result = dump_model(snap)
        assert isinstance(result, dict)
        assert result["status"] == "IDLE"

    def test_dump_model_with_dict(self):
        """Test dump_model with dict passthrough."""
        d = {"key": "value"}
        result = dump_model(d)
        assert result == d

    def test_dump_model_with_none(self):
        """Test dump_model with None."""
        result = dump_model(None)
        assert result is None
