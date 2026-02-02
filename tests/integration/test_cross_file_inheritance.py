from codex_mesh.core.edges import EdgeType
from codex_mesh.core.graph import CodeGraphBuilder
from codex_mesh.core.nodes import ClassNode, FileNode


def test_cross_file_inheritance_resolution(tmp_path):
    """Test that inheritance is resolved across files via imports."""
    project_root = tmp_path / "project"
    project_root.mkdir()

    # 1. Create Base class file
    # base.py
    base_file = project_root / "base.py"
    base_file.write_text("class Base:\n    pass\n")

    # 2. Create Derived class file that imports Base
    # derived.py
    derived_file = project_root / "derived.py"
    derived_file.write_text("from base import Base\n\nclass Derived(Base):\n    pass\n")

    # 3. Build Graph
    builder = CodeGraphBuilder(project_root)
    graph = builder.build()

    # 4. Verify Nodes
    # Find the nodes
    base_node = None
    derived_node = None
    base_file_node = None
    derived_file_node = None

    for node in graph.nodes():
        if isinstance(node, ClassNode):
            if node.name == "Base":
                base_node = node
            elif node.name == "Derived":
                derived_node = node
        elif isinstance(node, FileNode):
            if node.relative_path == "base.py":
                base_file_node = node
            elif node.relative_path == "derived.py":
                derived_file_node = node

    assert base_node is not None, "Base class node not found"
    assert derived_node is not None, "Derived class node not found"
    assert base_file_node is not None, "Base file node not found"
    assert derived_file_node is not None, "Derived file node not found"

    # 5. Verify Edges
    # Check for IMPORTS edge: derived.py -> base.py (or base class if symbol resolution worked)
    # The new python extractor should properly identity the import.
    # The new _resolve_pending_imports handles file->symbol if imported_names is set.
    # In "from base import Base", imported_names=['Base'].
    # So we expect IMPORTS edge: derived.py -> Base class node

    # Check IMPORTS edge
    imports_found = False
    for _, tgt_idx, data in graph.out_edges(builder._node_id_to_index[derived_file_node.id]):
        if data.edge_type == EdgeType.IMPORTS:
            tgt = graph[tgt_idx]
            # Since we implemented file->symbol imports, detailed resolution might point to Base class
            if tgt.id == base_node.id:
                imports_found = True
            # Or fall back to file if some resolution failed (but here it should work)
            elif tgt.id == base_file_node.id:
                # If it points to file, that's also acceptable for this test context,
                # BUT strict cross-file inheritance logic I wrote checks file_imports.
                # My logic adds to file_imports if tgt is FileNode OR ClassNode.
                imports_found = True

    assert imports_found, "IMPORTS edge not found from derived.py"

    # Check INHERITS edge: Derived -> Base
    inherits_found = False
    for _, tgt_idx, data in graph.out_edges(builder._node_id_to_index[derived_node.id]):
        if data.edge_type == EdgeType.INHERITS:
            tgt = graph[tgt_idx]
            if tgt.id == base_node.id:
                inherits_found = True
                break

    assert inherits_found, "INHERITS edge not found between Derived and Base"
