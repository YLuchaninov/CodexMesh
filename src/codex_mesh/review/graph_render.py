"""
Graph rendering utilities.
"""

from typing import Any


def _get_val(obj: Any, keys: list[str], default: Any = None) -> Any:
    for k in keys:
        if isinstance(obj, dict):
            if k in obj:
                return obj[k]
        else:
            if hasattr(obj, k):
                return getattr(obj, k)
    return default


def to_mermaid(nodes: list[Any], edges: list[dict[str, Any]], direction: str = "TD") -> str:
    """
    Render graph to Mermaid markdown.
    Supports both object (node.id) and dict (node["id"]) inputs.
    """
    lines = [f"graph {direction}"]

    # 1. Helper to clean IDs
    def clean_id(raw_id: str) -> str:
        import hashlib

        safe = "".join(c if c.isalnum() else "_" for c in str(raw_id))
        if len(safe) > 30:
            h = hashlib.md5(str(raw_id).encode()).hexdigest()[:6]
            return f"{safe[:20]}_{h}"
        return safe

    node_id_map = {}

    # 2. Add nodes
    for node in nodes:
        raw_id = _get_val(node, ["id"])
        if raw_id is None:
            continue

        cid = clean_id(raw_id)
        node_id_map[raw_id] = cid

        name = _get_val(node, ["name"], raw_id)
        ntype = _get_val(node, ["type", "node_type"])
        if hasattr(ntype, "value"):
            ntype = ntype.value
        ntype = str(ntype) if ntype else "unknown"

        # Initial shape
        shape_open, shape_close = "[", "]"
        if ntype == "class":
            shape_open, shape_close = "((", "))"
        elif ntype == "function":
            shape_open, shape_close = "([", "])"
        elif ntype == "file":
            shape_open, shape_close = "[[", "]]"

        label = name.replace('"', "'")
        lines.append(f'    {cid}{shape_open}"{label}"{shape_close}')

    # 3. Add edges
    for edge in edges:
        src = _get_val(edge, ["source"])
        tgt = _get_val(edge, ["target"])
        etype = _get_val(edge, ["type"])
        if hasattr(etype, "value"):
            etype = etype.value

        if src not in node_id_map or tgt not in node_id_map:
            # Try to handle implicit nodes if they are just IDs
            csrc = node_id_map.get(src, clean_id(src))
            cdst = node_id_map.get(tgt, clean_id(tgt))
        else:
            csrc = node_id_map[src]
            cdst = node_id_map[tgt]

        arrow = "-->"
        if etype == "calls":
            arrow = "-->"
        elif etype == "imports":
            arrow = "-.->"
        elif etype == "contains":
            arrow = "---"

        if etype and etype not in ["calls", "imports", "contains"]:
            label = f"|{etype}|"
            lines.append(f"    {csrc}{arrow}{label}{cdst}")
        else:
            lines.append(f"    {csrc}{arrow}{cdst}")

    return "\n".join(lines)


def to_tree(nodes: list[Any], edges: list[dict[str, Any]], root_id: str) -> dict[str, Any]:
    """
    Convert flat graph to tree structure (recursive).
    Note: Graphs may have cycles; this handles it by tracking visited in current path (or simple visited).
    Since we want a "tree view" for UI, repeated nodes should probably be leaf refs.
    """

    # Build adjacency
    adj: dict[str, list[dict[str, Any]]] = {}
    for edge in edges:
        s = edge["source"]
        if s not in adj:
            adj[s] = []
        adj[s].append(edge)

    # Build node map
    node_map = {n.id if hasattr(n, "id") else n["id"]: n for n in nodes}

    def build_node(nid, visited_ids):
        node = node_map.get(nid)
        if not node:
            return {"id": nid, "error": "Node not found"}

        res = {
            "id": _get_val(node, ["id"]),
            "name": _get_val(node, ["name"]),
            "type": str(_get_val(node, ["type", "node_type"], "unknown")),
            "children": [],
        }
        if hasattr(res["type"], "value"):
            res["type"] = res["type"].value

        if nid in visited_ids:
            res["recursive"] = True
            return res

        new_visited = visited_ids | {nid}

        if nid in adj:
            for edge in adj[nid]:
                child_id = edge["target"]
                child_node = build_node(child_id, new_visited)
                child_node["edge_type"] = edge.get("type")
                res["children"].append(child_node)

        return res

    return build_node(root_id, set())
