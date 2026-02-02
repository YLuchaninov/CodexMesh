"""
Built-in multi-language extractors using tree-sitter-language-pack.

This module registers extractors for common programming languages using
tree-sitter queries. These are the default extractors used by CodexMesh.
"""

from .registry import ExtractorRegistry
from .treesitter_query import QueryBundle, TreeSitterQueryExtractor


def register_defaults(registry: ExtractorRegistry):
    """Register all built-in language extractors."""

    # JavaScript
    registry.register(
        TreeSitterQueryExtractor(
            language_id="javascript",
            extensions=(".js", ".jsx", ".mjs", ".cjs"),
            ts_lang_key="javascript",
            queries=QueryBundle(
                classes="(class_declaration name: (identifier) @name)",
                functions="(function_declaration name: (identifier) @name)",
                methods="(method_definition name: (property_identifier) @name)",
                decorators="(decorator) @decorator",
                # JS async detection
                modifiers=r"""
                (function_declaration "async" @modifier)
                (method_definition "async" @modifier)
                (arrow_function "async" @modifier)
            """,
                imports=r"""
                (import_statement
                  (import_clause
                    (named_imports
                      (import_specifier
                        name: (identifier) @imported_name
                        alias: (identifier) @alias)?
                      (import_specifier
                        name: (identifier) @imported_name)?))
                  source: (string) @source)

                (import_statement
                  (import_clause
                    (namespace_import
                      (identifier) @alias))
                  source: (string) @source)

                (import_statement
                  (import_clause
                    (identifier) @imported_name)
                  source: (string) @source)

                (import_statement
                  source: (string) @source)

                (call_expression
                  function: (identifier) @fn
                  arguments: (arguments (string) @source)
                  (#eq? @fn "require"))
            """,
                calls=r"""
                (call_expression function: (identifier) @callee)
                (call_expression
                   function: (member_expression
                     object: (identifier) @receiver
                     property: (property_identifier) @callee))
            """,
                bases=r"""
                (class_heritage (identifier) @base)
                (class_heritage (member_expression (property_identifier) @base))
            """,
                entrypoints=r"""
                (function_declaration name: (identifier) @name (#eq? @name "main"))
            """,
            ),
        )
    )

    # TypeScript
    registry.register(
        TreeSitterQueryExtractor(
            language_id="typescript",
            extensions=(".ts", ".tsx", ".mts", ".cts", ".d.ts"),
            ts_lang_key="typescript",
            queries=QueryBundle(
                classes="(class_declaration name: (type_identifier) @name)",
                functions="(function_declaration name: (identifier) @name)",
                methods="(method_definition name: (property_identifier) @name)",
                decorators="(decorator) @decorator",
                # TS accessibility + async modifiers
                modifiers=r"""
            (accessibility_modifier) @modifier
            (override_modifier) @modifier
            (function_declaration "async" @modifier)
            (method_definition "async" @modifier)
            (arrow_function "async" @modifier)
        """,
                imports=r"""
                (import_statement
                  (import_clause
                    (named_imports
                      (import_specifier
                        name: (identifier) @imported_name
                        alias: (identifier) @alias)?
                      (import_specifier
                        name: (identifier) @imported_name)?))
                  source: (string) @source)

                (import_statement
                  (import_clause
                    (namespace_import
                      (identifier) @alias))
                  source: (string) @source)

                (import_statement
                  (import_clause
                    (identifier) @imported_name)
                  source: (string) @source)

                (import_statement
                  source: (string) @source)

                (call_expression
                  function: (identifier) @fn
                  arguments: (arguments (string) @source)
                  (#eq? @fn "require"))
            """,
                calls=r"""
                (call_expression function: (identifier) @callee)
                (call_expression
                   function: (member_expression
                     object: (identifier) @receiver
                     property: (property_identifier) @callee))
            """,
                bases=r"""
                (extends_clause value: (identifier) @base)
                (extends_clause value: (member_expression) @base)
                (implements_clause (type_identifier) @base)
            """,
                entrypoints=r"""
                (function_declaration name: (identifier) @name (#eq? @name "main"))
            """,
            ),
        )
    )

    # Rust
    registry.register(
        TreeSitterQueryExtractor(
            language_id="rust",
            extensions=(".rs",),
            ts_lang_key="rust",
            queries=QueryBundle(
                classes="(struct_item name: (type_identifier) @name)",
                functions="""
                (function_item name: (identifier) @entrypoint @name (#eq? @name "main"))
                (function_item name: (identifier) @name (#not-eq? @name "main"))
            """,
                methods="(impl_item body: (declaration_list (function_item name: (identifier) @name)))",
                decorators="(attribute_item) @decorator",
                modifiers="(visibility_modifier) @modifier",
                imports=r"""
                (mod_item name: (identifier) @source)
                (use_declaration
                   argument: [
                     (identifier) @source
                     (scoped_identifier) @source
                   ])




            """,
                calls=r"""
                (call_expression function: (identifier) @callee)
                (call_expression
                   function: (field_expression
                     value: (identifier) @receiver
                     field: (field_identifier) @callee))
                (call_expression function: (scoped_identifier (identifier) @callee))
            """,
                bases=r"""
                (impl_item trait: (type_identifier) @base)
                (impl_item trait: (scoped_type_identifier) @base)
            """,
            ),
        )
    )

    # Java
    registry.register(
        TreeSitterQueryExtractor(
            language_id="java",
            extensions=(".java",),
            ts_lang_key="java",
            queries=QueryBundle(
                classes="""
                (class_declaration name: (identifier) @name)
                (interface_declaration name: (identifier) @name)
                (enum_declaration name: (identifier) @name)
                (record_declaration name: (identifier) @name)
            """,
                functions=None,
                methods="""
                (method_declaration name: (identifier) @name)
                (constructor_declaration name: (identifier) @name)
            """,
                decorators="(marker_annotation) @decorator (annotation) @decorator",
                modifiers="""
                (modifiers [
                   "public" "private" "protected" "static" "final"
                   "abstract" "synchronized" "native" "transient" "volatile"
                ] @modifier)
            """,
                imports=r"""
                (import_declaration
                   [(scoped_identifier) @source (identifier) @source])
            """,
                calls=r"""
                (method_invocation name: (identifier) @callee)
                (method_invocation

                   object: (identifier) @receiver
                   name: (identifier) @callee)
                (method_invocation
                   object: (this) @receiver
                   name: (identifier) @callee)
            """,
                bases=r"""
                (class_declaration superclass: (superclass (type_identifier) @base))
                (class_declaration superclass: (superclass (scoped_type_identifier) @base))




            """,
                entrypoints=r"""
                (method_declaration
                   (modifiers "public" "static")
                   type: (void_type)
                   name: (identifier) @name (#eq? @name "main")) @entrypoint
            """,
            ),
        )
    )

    # C++
    registry.register(
        TreeSitterQueryExtractor(
            language_id="cpp",
            extensions=(".cpp", ".cc", ".cxx", ".h", ".hpp", ".hh", ".hxx"),
            ts_lang_key="cpp",
            queries=QueryBundle(
                classes="""(struct_specifier name: (type_identifier) @name)
                       (class_specifier name: (type_identifier) @name)""",
                functions="""
                (function_definition declarator: (function_declarator declarator: (identifier) @entrypoint @name (#eq? @name "main")))
                (function_definition declarator: (function_declarator declarator: (identifier) @name (#not-eq? @name "main")))

            """,
                methods="(function_definition declarator: (function_declarator declarator: (field_identifier) @name))",
                imports=r"""
                (preproc_include path: (string_literal) @source)
                (preproc_include (string_literal) @source)
            """,
                calls=r"""
                (call_expression (identifier) @callee)



            """,
                bases=r"""
                (base_class_clause (type_identifier) @base)
                (base_class_clause (qualified_identifier) @base)
            """,
            ),
        )
    )

    # C
    registry.register(
        TreeSitterQueryExtractor(
            language_id="c",
            extensions=(".c",),
            ts_lang_key="c",
            queries=QueryBundle(
                classes=None,
                functions="""
                (function_definition declarator: (function_declarator declarator: (identifier) @entrypoint @name (#eq? @name "main")))
                (function_definition declarator: (function_declarator declarator: (identifier) @name (#not-eq? @name "main")))
            """,
                methods=None,
                imports=r"""
                (preproc_include path: (string_literal) @source)
                (preproc_include (string_literal) @source)
            """,
                calls=r"""
                (call_expression function: (identifier) @callee)
            """,
                bases=None,
            ),
        )
    )

    # C#
    registry.register(
        TreeSitterQueryExtractor(
            language_id="csharp",
            extensions=(".cs", ".csx"),
            ts_lang_key="csharp",
            queries=QueryBundle(
                classes="""
                (class_declaration name: (identifier) @name)
                (interface_declaration name: (identifier) @name)
                (struct_declaration name: (identifier) @name)
                (enum_declaration name: (identifier) @name)
            """,
                functions=None,
                methods="(method_declaration name: (identifier) @name)",
                decorators="(attribute_list) @decorator",
                modifiers=r"""
                (modifier) @modifier
            """,
                imports=r"""
                (using_directive (qualified_name) @source)
                (using_directive (identifier) @source)
            """,
                calls=r"""
                (invocation_expression function: (identifier) @callee)
                (invocation_expression function: (member_access_expression (identifier) @callee))

            """,
                bases=r"""
                (class_declaration (base_list (identifier) @base))
                (class_declaration (base_list (qualified_name) @base))

            """,
                entrypoints=r"""
                (method_declaration
                   (modifier) @m (#eq? @m "static")
                   name: (identifier) @name (#eq? @name "Main")) @entrypoint
            """,
            ),
        )
    )

    # Dart - Fully implemented
    registry.register(
        TreeSitterQueryExtractor(
            language_id="dart",
            extensions=(".dart",),
            ts_lang_key="dart",
            queries=QueryBundle(
                classes="(class_definition name: (identifier) @name)",
                functions="""
                (function_signature name: (identifier) @entrypoint @name (#eq? @name "main"))
                (function_signature name: (identifier) @name (#not-eq? @name "main"))
            """,
                methods="(class_body (method_signature (function_signature name: (identifier) @name)))",
                decorators="(annotation) @decorator",
                modifiers=r"""
                (function_body "async" @modifier)
                (function_body "async*" @modifier)
                (function_body "sync*" @modifier)
            """,
                imports=r"""
                (library_import (import_specification (configurable_uri (uri (string_literal) @source))))
            """,
                calls=None,
                bases=r"""
                (superclass (type_identifier) @base)
                (superclass (mixins (type_identifier) @base))
                (interfaces (type_identifier) @base)
            """,
            ),
        )
    )

    # Swift
    registry.register(
        TreeSitterQueryExtractor(
            language_id="swift",
            extensions=(".swift",),
            ts_lang_key="swift",
            queries=QueryBundle(
                classes="""
                (class_declaration name: (type_identifier) @name)
                (protocol_declaration name: (type_identifier) @name)
            """,
                functions="(function_declaration name: (simple_identifier) @name)",
                methods="(class_body (function_declaration name: (simple_identifier) @name))",
                decorators="(attribute) @decorator",
                modifiers="(visibility_modifier) @modifier",
                imports=r"""
                (import_declaration (identifier) @source)
            """,
                calls=r"""
                (call_expression (simple_identifier) @callee)
                (call_expression (navigation_expression (simple_identifier) @callee))
            """,
                bases=r"""
                (class_declaration (inheritance_specifier (user_type (type_identifier) @base)))
            """,
            ),
        )
    )

    # Kotlin
    registry.register(
        TreeSitterQueryExtractor(
            language_id="kotlin",
            extensions=(".kt", ".kts"),
            ts_lang_key="kotlin",
            queries=QueryBundle(
                classes="""
                (class_declaration (type_identifier) @name)
                (object_declaration (type_identifier) @name)
            """,
                functions="""
                (function_declaration (simple_identifier) @entrypoint @name (#eq? @name "main"))
                (function_declaration (simple_identifier) @name (#not-eq? @name "main"))
            """,
                methods="(class_body (function_declaration (simple_identifier) @name))",
                decorators="(annotation) @decorator",
                modifiers=r"""
                (visibility_modifier) @modifier
                (inheritance_modifier) @modifier
                (member_modifier) @modifier
                (function_modifier "suspend" @modifier)
            """,
                imports=r"""
                (import_header (identifier) @source)
            """,
                calls=r"""
                (call_expression (simple_identifier) @callee)
                (call_expression (navigation_expression (simple_identifier) @callee))
            """,
                bases=r"""
                (class_declaration (delegation_specifier (user_type (type_identifier) @base)))
                (class_declaration (delegation_specifier (constructor_invocation (user_type (type_identifier) @base))))
            """,
            ),
        )
    )

    # PHP
    registry.register(
        TreeSitterQueryExtractor(
            language_id="php",
            extensions=(".php",),
            ts_lang_key="php",
            queries=QueryBundle(
                classes="""
                (class_declaration name: (name) @name)
                (interface_declaration name: (name) @name)
                (trait_declaration name: (name) @name)
            """,
                functions="(function_definition name: (name) @name)",
                methods="(method_declaration name: (name) @name)",
                decorators="(attribute_group) @decorator",
                modifiers="(visibility_modifier) @modifier (static_modifier) @modifier",
                imports=r"""
                (namespace_use_declaration
                   (namespace_use_clause
                      [(name) @source (qualified_name) @source]))


                (require_expression (string) @source)
                (include_expression (string) @source)
                (require_once_expression (string) @source)
                (include_once_expression (string) @source)
            """,
                calls=r"""
                (function_call_expression function: (name) @callee)
                (function_call_expression function: (qualified_name) @callee)
                (member_call_expression name: (name) @callee)
                (scoped_call_expression name: (name) @callee)
            """,
                bases=r"""
                (class_declaration (base_clause (name) @base))
                (class_declaration (class_interface_clause (name) @base))

            """,
            ),
        )
    )

    # Ruby
    registry.register(
        TreeSitterQueryExtractor(
            language_id="ruby",
            extensions=(".rb",),
            ts_lang_key="ruby",
            queries=QueryBundle(
                classes="""
                (class name: (constant) @name)
                (module name: (constant) @name)
            """,
                functions=None,
                methods="(method name: (identifier) @name)",
                imports=r"""
                (call
                  method: (identifier) @m
                  (argument_list (string) @source)
                  (#eq? @m "require_relative"))
                (call
                  method: (identifier) @m
                  (argument_list (string) @source)
                  (#eq? @m "require"))
            """,
                calls=r"""
                (call method: (identifier) @callee)
                (call method: (constant) @callee)

            """,
                bases=r"""
                (class superclass: (_) @base)


            """,
            ),
        )
    )

    # Go
    registry.register(
        TreeSitterQueryExtractor(
            language_id="go",
            extensions=(".go",),
            ts_lang_key="go",
            queries=QueryBundle(
                classes="""
                (type_spec name: (type_identifier) @name type: (struct_type))
                (type_spec name: (type_identifier) @name type: (interface_type))
            """,
                functions="""
                (function_declaration name: (identifier) @entrypoint @name (#eq? @name "main"))
                (function_declaration name: (identifier) @name (#not-eq? @name "main"))
            """,
                methods="""
                (method_declaration
                   receiver: (parameter_list (parameter_declaration type: [ (type_identifier) @receiver_type (pointer_type (type_identifier) @receiver_type) ]))
                   name: (field_identifier) @name)
            """,
                imports=r"""
                (import_spec
                   name: (package_identifier)? @alias
                   path: [(interpreted_string_literal) @source (raw_string_literal) @source])
            """,
                calls=r"""
                (call_expression function: (identifier) @callee)
                (call_expression
                   function: (selector_expression
                      operand: (identifier) @receiver
                      field: (field_identifier) @callee))
            """,
                bases=r"""
                (field_declaration type: (type_identifier) @base !name)
                (field_declaration type: (pointer_type (type_identifier) @base) !name)
            """,
            ),
        )
    )

    # Scala
    registry.register(
        TreeSitterQueryExtractor(
            language_id="scala",
            extensions=(".scala",),
            ts_lang_key="scala",
            queries=QueryBundle(
                classes="""(class_definition name: (identifier) @name)
                       (object_definition name: (identifier) @name)
                       (trait_definition name: (identifier) @name)""",
                functions="(function_definition name: (identifier) @name)",
                methods="(template_body (function_definition name: (identifier) @name))",
                decorators="(annotation) @decorator",
                modifiers="(modifiers) @modifier",
                imports=r"""
                (import_declaration
                   [(identifier) @source (stable_identifier) @source])

            """,
                calls=r"""
                (call_expression function: (identifier) @callee)
            """,
                bases=r"""
                (class_definition (extends_clause (type_identifier) @base))
                (trait_definition (extends_clause (type_identifier) @base))
                (object_definition (extends_clause (type_identifier) @base))

            """,
            ),
        )
    )
