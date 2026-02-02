import tree_sitter_language_pack

from codex_mesh.extractors.treesitter_query import QueryBundle, TreeSitterQueryExtractor


def debug_rust():
    queries = QueryBundle(
        classes="(struct_item (type_identifier) @name)",
        functions=None,
        methods=None,
        decorators="(attribute_item) @decorator",
        imports=None,
        bases=r"""
            (impl_item trait: (type_identifier) @base)
            (impl_item trait: (scoped_type_identifier) @base)
        """,
    )

    extractor = TreeSitterQueryExtractor(
        language_id="rust", extensions=(".rs",), ts_lang_key="rust", queries=queries
    )

    code = """
    #[derive(Debug)]
    pub struct MyStruct {}

    impl MyTrait for MyStruct {
        fn my_method(&self) {}
    }
    """

    # We want to inspect captures logic manually
    tree = extractor._parser.parse(bytes(code, "utf8"))
    print("SEXP:", str(tree.root_node))

    print("queries.bases repr:", repr(queries.bases))

    # Run query manually to get the node context
    import tree_sitter

    q = tree_sitter.Query(extractor._language, queries.bases)
    cursor = tree_sitter.QueryCursor(q)
    captures = cursor.captures(tree.root_node)

    for n_list in captures.values() if isinstance(captures, dict) else [c[0] for c in captures]:
        node = n_list[0] if isinstance(n_list, list) else n_list
        # Assume node is @base
        p = node.parent
        if p.type == "impl_item":
            print("Found impl_item parent")
            type_node = p.child_by_field_name("type")
            trait_node = p.child_by_field_name("trait")
            print(
                f"  Field 'type': {extractor._safe_node_text(type_node) if type_node else 'None'}"
            )
            print(
                f"  Field 'trait': {extractor._safe_node_text(trait_node) if trait_node else 'None'}"
            )

            for i in range(p.child_count):
                c = p.child(i)
                print(f"  Child {i}: {c.type} text='{extractor._safe_node_text(c)}'")

    print("Running bases query again:")
    bases_map = extractor._run_bases_query(tree.root_node, queries.bases)
    print("Bases map:", bases_map)

    return
    extractor._compile_query(queries.classes + " " + queries.decorators)

    cursor = tree_sitter_language_pack.get_language("rust").query(
        queries.classes + " " + queries.decorators
    )
    # Wait, get_language returns a Language object.
    # extractor._compile_query uses tree_sitter.Query(lang, src)

    # Let's use extractor's internal query logic
    # But extract() runs multiple queries separately?
    # NO! _queries.classes, _queries.functions are run separately in _run_symbol_query!

    # Ah! _run_symbol_query takes ONE query string.
    # In my tests/code, I passed `queries.classes` (only the class query string!).
    # Does `queries.classes` CONTAIN `queries.decorators`?
    # The `extract()` method calls `_run_symbol_query` with `self._queries.classes`.

    # The `self._queries.classes` ONLY contains the class pattern! It does NOT contain the decorator pattern!
    # The `QueryBundle` has separate fields.
    # `TreeSitterQueryExtractor` logic must MERGE them?

    # Start checking `treesitter_query.py` at line 66 (original) / line 77 (new).
    # `class_nodes = self._run_symbol_query(..., self._queries.classes, ...)`

    # If `_queries.classes` is just `(struct_item ... @name)`, then the cursor ONLY looks for that.
    # It does NOT look for decorators!

    print("Queries passed to _run_symbol_query:", queries.classes)


if __name__ == "__main__":
    debug_rust()
