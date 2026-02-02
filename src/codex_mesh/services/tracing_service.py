"""
Tracing Service.

Records execution steps of workflows for visualization and debugging.
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TraceStep:
    id: str
    timestamp: float
    type: str  # 'tool', 'thought', 'decision'
    name: str
    input: dict[str, Any] | None = None
    output: dict[str, Any] | None = None
    duration: float = 0.0


@dataclass
class TraceSession:
    id: str
    start_time: float
    steps: list[TraceStep] = field(default_factory=list)
    status: str = "running"  # running, completed, failed


class TracingService:
    def __init__(self):
        self._traces: dict[str, TraceSession] = {}
        self._active_trace: str | None = None

    def start_trace(self, trace_id: str | None = None) -> str:
        """
        Start a new trace session.

        Args:
            trace_id: Optional fixed ID for the trace. Generates a UUID if None.

        Returns:
            The ID of the started trace session.
        """
        tid = trace_id or str(uuid.uuid4())
        self._traces[tid] = TraceSession(id=tid, start_time=time.time())
        self._active_trace = tid
        return tid

    def stop_trace(self, trace_id: str | None = None) -> None:
        """Stop a trace session."""
        tid = trace_id or self._active_trace
        if tid and tid in self._traces:
            self._traces[tid].status = "completed"

    def log_step(
        self,
        step_type: str,
        name: str,
        input_data: Any = None,
        output_data: Any = None,
        duration: float = 0.0,
    ) -> None:
        """
        Log an execution step to the active trace.

        Args:
            step_type: Category of the step (e.g., 'tool', 'thought').
            name: Descriptive name of the step.
            input_data: Optional input parameters/data for the step.
            output_data: Optional output result/data from the step.
            duration: Time taken to execute the step in seconds.
        """
        if not self._active_trace:
            return

        trace = self._traces[self._active_trace]
        step = TraceStep(
            id=str(uuid.uuid4()),
            timestamp=time.time(),
            type=step_type,
            name=name,
            input=input_data if isinstance(input_data, dict) else {"value": str(input_data)},
            output=output_data if isinstance(output_data, dict) else {"value": str(output_data)},
            duration=duration,
        )
        trace.steps.append(step)

    def get_trace_subgraph(self, trace_id: str | None = None) -> dict[str, Any]:
        """Convert trace to graph structure (nodes=steps, edges=time flow)."""
        tid = trace_id or self._active_trace
        if not tid or tid not in self._traces:
            return {"nodes": [], "edges": []}

        session = self._traces[tid]
        nodes = []
        edges = []

        # Add start node
        nodes.append(
            {
                "id": "start",
                "name": "Start",
                "type": "start",
                "data": {"timestamp": session.start_time},
            }
        )

        last_id = "start"

        for i, step in enumerate(session.steps):
            node_id = f"step_{i}"
            nodes.append(
                {
                    "id": node_id,
                    "name": step.name,
                    "type": step.type,
                    "data": {"input": step.input, "output": step.output, "duration": step.duration},
                }
            )

            edges.append({"source": last_id, "target": node_id, "type": "flow"})
            last_id = node_id

        return {"nodes": nodes, "edges": edges, "trace_id": tid}
