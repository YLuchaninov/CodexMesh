"""
Tests for templating engine.
"""

from codex_mesh.workflows.engine.templating import render_template


def test_render_template_typed_interpolation():
    """Test that full-match templates return typed values."""
    ctx = {"budget": 100, "flag": True, "items": [1, 2, 3], "nested": {"x": 10}}

    # Int
    assert render_template("{{budget}}", ctx) == 100
    assert isinstance(render_template("{{budget}}", ctx), int)

    # Bool
    assert render_template("{{flag}}", ctx) is True

    # List
    assert render_template("{{items}}", ctx) == [1, 2, 3]

    # Mixed string (should be string)
    assert render_template("Limit is {{budget}}", ctx) == "Limit is 100"


def test_render_template_filters():
    """Test filters."""
    ctx = {"val": "123", "f": "1.5"}

    assert render_template("{{val|int}}", ctx) == 123
    assert render_template("{{f|float}}", ctx) == 1.5
    assert render_template("{{val|bool}}", ctx) is True
