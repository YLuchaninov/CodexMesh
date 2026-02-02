"""
Web Tools API Router.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("")
async def list_web_tools():
    """List tools for UI rendering."""
    return {
        "tools": [
            {
                "id": "analysis.search",
                "title": "Lexical Search",
                "method": "POST",
                "endpoint": "/api/v1/analysis/search",
                "category": "Analyze",
                "ui": {
                    "form": [
                        {
                            "name": "query",
                            "label": "Search Query",
                            "type": "text",
                            "required": True,
                        },
                        {"name": "limit", "label": "Result Limit", "type": "number", "default": 10},
                    ]
                },
            },
            {
                "id": "analysis.semantic",
                "title": "Semantic Search",
                "method": "POST",
                "endpoint": "/api/v1/analysis/semantic",
                "category": "Analyze",
                "ui": {
                    "form": [
                        {
                            "name": "query",
                            "label": "Natural Language Query",
                            "type": "text",
                            "required": True,
                        },
                        {"name": "limit", "label": "Result Limit", "type": "number", "default": 5},
                    ]
                },
            },
            {
                "id": "fs.read",
                "title": "Read File",
                "method": "POST",
                "endpoint": "/api/v1/fs/read",
                "category": "Explore",
                "ui": {"form": [{"name": "path", "label": "File Path", "type": "text"}]},
            },
            {
                "id": "analysis.hotspots",
                "title": "Hotspots",
                "method": "POST",
                "endpoint": "/api/v1/analysis/hotspots",
                "category": "Analyze",
                "ui": {"form": []},
            },
            {
                "id": "analysis.docs-coverage",
                "title": "Documentation Coverage",
                "method": "GET",
                "endpoint": "/api/v1/analysis/docs/coverage",
                "category": "Analyze",
                "ui": {"form": []},
            },
            {
                "id": "graph.subgraph",
                "title": "Subgraph Explorer",
                "method": "POST",
                "endpoint": "/api/v1/graph/subgraph",
                "category": "Graph",
                "ui": {
                    "form": [
                        {
                            "name": "roots",
                            "label": "Root IDs (comma-separated)",
                            "type": "text",
                            "required": True,
                        },
                        {"name": "depth", "label": "Depth", "type": "number", "default": 1},
                        {
                            "name": "direction",
                            "label": "Direction",
                            "type": "select",
                            "options": ["in", "out", "both"],
                            "default": "both",
                        },
                    ]
                },
            },
            {
                "id": "graph.find_path",
                "title": "Find Path",
                "method": "POST",
                "endpoint": "/api/v1/graph/find-path",
                "category": "Graph",
                "ui": {
                    "form": [
                        {
                            "name": "source_id",
                            "label": "Source ID",
                            "type": "text",
                            "required": True,
                        },
                        {
                            "name": "target_id",
                            "label": "Target ID",
                            "type": "text",
                            "required": True,
                        },
                        {"name": "max_hops", "label": "Max Hops", "type": "number", "default": 20},
                    ]
                },
            },
            {
                "id": "graph.dependency_tree",
                "title": "Dependency Tree",
                "method": "POST",
                "endpoint": "/api/v1/graph/dependency-tree",
                "category": "Graph",
                "ui": {
                    "form": [
                        {"name": "root_id", "label": "Root ID", "type": "text", "required": True},
                        {"name": "depth", "label": "Depth", "type": "number", "default": 2},
                        {
                            "name": "direction",
                            "label": "Direction",
                            "type": "select",
                            "options": ["in", "out", "both"],
                            "default": "out",
                        },
                    ]
                },
            },
            {
                "id": "graph.cycles",
                "title": "Cycle Detection",
                "method": "GET",
                "endpoint": "/api/v1/graph/cycles",
                "category": "Analyze",
                "ui": {
                    "form": [
                        {"name": "scope", "label": "Scope", "type": "text", "default": "module"},
                        {
                            "name": "edge_type",
                            "label": "Edge Type",
                            "type": "text",
                            "default": "imports",
                        },
                    ]
                },
            },
            {
                "id": "project.status",
                "title": "Project Status",
                "method": "GET",
                "endpoint": "/api/v1/project/status",
                "category": "Project",
                "ui": {"form": []},
            },
            {
                "id": "workflows.intents.list",
                "title": "Workflows List",
                "method": "GET",
                "endpoint": "/api/v1/intents",
                "category": "Workflows",
                "ui": {"form": []},
            },
            {
                "id": "workflows.intents.execute",
                "title": "Run Workflow",
                "method": "POST",
                "endpoint": "/api/v1/intents/execute",
                "category": "Workflows",
                "ui": {
                    "form": [
                        {
                            "name": "intent_id",
                            "label": "Intent ID",
                            "type": "text",
                            "required": True,
                        },
                        {
                            "name": "input",
                            "label": "Input JSON",
                            "type": "json",
                            "default": "{}",
                        },
                        {
                            "name": "options.max_steps",
                            "label": "Max Steps",
                            "type": "number",
                            "default": 100,
                        },
                        {
                            "name": "options.include_trace",
                            "label": "Include Trace",
                            "type": "checkbox",
                            "default": True,
                        },
                    ]
                },
            },
            {
                "id": "chat.history",
                "title": "Chat History",
                "method": "GET",
                "endpoint": "/api/v1/chats",
                "category": "Chat",
                "ui": {"form": []},
            },
            {
                "id": "system.config",
                "title": "Settings",
                "method": "GET",
                "endpoint": "/api/v1/system/config",
                "category": "Settings",
                "ui": {"form": []},
            },
        ]
    }
