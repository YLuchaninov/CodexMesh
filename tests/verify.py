import os
import sys

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))


def run_contract_tests():
    print("Running contract tests...")
    from codex_mesh.contracts.analysis import SearchMatch, SemanticResult

    # Test 1
    res = SemanticResult(id="node1", name="foo", score=0.9)
    assert res.id == "node1", "ID should be node1"
    assert res.span is None, "Span should be None"
    print("  SemanticResult OK")

    # Test 2
    m = SearchMatch(id="node-id-test", file_path="foo.py", snippet="code")
    assert m.id == "node-id-test"
    m.id = "foo"
    assert m.id == "foo"
    print("  SearchMatch OK")


def run_templating_tests():
    print("Running templating tests...")
    from codex_mesh.workflows.engine.templating import render_template

    ctx = {"budget": 100, "flag": True, "val": "123"}

    # Typed
    res = render_template("{{budget}}", ctx)
    assert isinstance(res, int), f"Expected int, got {type(res)}"
    assert res == 100
    print("  Typed int OK")

    # String mixed
    res = render_template("Budget: {{budget}}", ctx)
    assert isinstance(res, str)
    assert res == "Budget: 100"
    print("  Mixed string OK")

    # Filters
    res = render_template("{{val|int}}", ctx)
    assert res == 123
    assert isinstance(res, int)
    print("  Filters OK")


if __name__ == "__main__":
    try:
        run_contract_tests()
        run_templating_tests()
        print("\nALL VERIFICATION TESTS PASSED")
    except ImportError as e:
        print(f"ImportError: {e}")
        print("Make sure you run this from project root")
    except AssertionError as e:
        print(f"FAIL: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
