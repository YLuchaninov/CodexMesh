import pytest

from codex_mesh.core.graph import CodeGraphBuilder
from codex_mesh.core.nodes import DocSectionNode, FileNode
from codex_mesh.docs.extractor import MarkdownDocsExtractor
from codex_mesh.docs.parser import split_markdown_sections
from codex_mesh.extractors.protocols import ExtractorContext


def test_split_markdown_sections():
    content = """
# Title
Intro text.

## Section 1
Content 1.

## Section 2
Content 2.
    """.strip()

    sections = split_markdown_sections(content)
    assert len(sections) == 3
    assert sections[0].title == "Title"
    assert sections[0].level == 1
    assert "Intro text" in sections[0].content

    assert sections[1].title == "Section 1"
    assert sections[1].level == 2

    assert sections[2].title == "Section 2"
    assert sections[2].level == 2


def test_extractor(tmp_path):
    f = tmp_path / "README.md"
    f.write_text("# My Project\n\nCheck [[function::my_func]] for details.", encoding="utf-8")

    extractor = MarkdownDocsExtractor()
    file_node = FileNode.create(str(f), "README.md")
    ctx = ExtractorContext(tmp_path, f, "README.md", config={})

    result = extractor.extract(ctx, file_node, f.read_text(encoding="utf-8"))

    assert len(result.nodes) == 1
    node = result.nodes[0]
    assert isinstance(node, DocSectionNode)
    assert node.title == "My Project"
    assert "function::my_func" in node.refs or "[[function::my_func]]" in node.content


# Integration stub
@pytest.fixture
def graph_builder(tmp_path):
    return CodeGraphBuilder(str(tmp_path))


def test_integration_fake(graph_builder):
    # Verify we can add DocSectionNode to graph
    node = DocSectionNode.create(
        doc_rel_path="docs/api.md",
        title="API",
        level=1,
        line_start=1,
        line_end=10,
        content="API Docs",
    )
    idx = graph_builder._add_node(node)
    assert idx is not None
    fetched = graph_builder.get_node_by_id(node.id)
    assert fetched.id == node.id
