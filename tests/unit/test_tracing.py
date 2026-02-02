"""
Unit tests for TracingService.
"""

from codex_mesh.services.tracing_service import TracingService


def test_tracing_basic_flow():
    tracing = TracingService()

    # Start trace
    tid = tracing.start_trace("test-trace")
    assert tid == "test-trace"

    # Log steps
    tracing.log_step("tool", "search_code", {"query": "foo"}, {"count": 5}, duration=0.1)
    tracing.log_step("thought", "analysis", {"context": "foo"}, duration=0.5)

    # Verify graph
    graph = tracing.get_trace_subgraph("test-trace")
    assert len(graph["nodes"]) == 3  # Start + 2 steps
    assert len(graph["edges"]) == 2

    assert graph["nodes"][1]["name"] == "search_code"
    assert graph["nodes"][2]["type"] == "thought"

    # Stop trace
    tracing.stop_trace("test-trace")
    assert tracing._traces["test-trace"].status == "completed"


def test_tracing_subgraph_empty():
    tracing = TracingService()
    graph = tracing.get_trace_subgraph("non-existent")
    assert graph["nodes"] == []


def test_tracing_multi_session():
    tracing = TracingService()
    tracing.start_trace("t1")
    tracing.log_step("action", "step1")

    tracing.start_trace("t2")
    tracing.log_step("action", "step2")

    # Steps should be isolated to active trace (t2)
    g1 = tracing.get_trace_subgraph("t1")
    g2 = tracing.get_trace_subgraph("t2")

    # t1 has Start + step1
    assert len(g1["nodes"]) == 2
    # t2 has Start + step2
    assert len(g2["nodes"]) == 2
