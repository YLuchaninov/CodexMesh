"""
Tests for Entrypoints 2.0 strategies.
"""

import unittest
from unittest.mock import MagicMock

from codex_mesh.analysis.entrypoints import EntrypointDetector


class TestEntrypointsV2(unittest.TestCase):
    def setUp(self):
        self.mock_server = MagicMock()
        self.detector = EntrypointDetector(self.mock_server)

    def test_detect_by_filename(self):
        f1 = MagicMock()
        f1.include = True
        f1.id = "f1"
        f1.relative_path = "src/main.py"
        f1.name = "main.py"

        f2 = MagicMock()
        f2.id = "f2"
        f2.relative_path = "utils/helper.py"
        f2.name = "helper.py"

        self.mock_server.graph_builder.get_files.return_value = [f1, f2]
        self.mock_server.graph_builder.get_functions.return_value = []

        res = self.detector.detect()
        eps = res["entrypoints"]

        # Should find main.py
        self.assertEqual(len(eps), 1)
        self.assertEqual(eps[0]["name"], "main.py")
        self.assertIn("main.py", eps[0]["reasons"][0])

    def test_detect_by_funcname(self):
        self.mock_server.graph_builder.get_files.return_value = []

        fn1 = MagicMock()
        fn1.id = "fn1"
        fn1.name = "main"
        fn1.is_method = False
        fn1.file_path = "script.py"
        fn1.decorators = []
        fn1.meta = {}  # Explicitly empty to avoid MagicMock truthiness

        fn2 = MagicMock()
        fn2.id = "fn2"
        fn2.name = "helper"
        fn2.is_method = False
        fn2.file_path = "script.py"
        fn2.decorators = []
        fn2.meta = {}

        self.mock_server.graph_builder.get_functions.return_value = [fn1, fn2]

        res = self.detector.detect()
        eps = res["entrypoints"]

        self.assertEqual(len(eps), 1)
        self.assertEqual(eps[0]["name"], "main")

    def test_detect_by_decorator(self):
        self.mock_server.graph_builder.get_files.return_value = []

        fn1 = MagicMock()
        fn1.id = "fn1"
        fn1.name = "create_user"
        fn1.file_path = "api.py"
        fn1.is_method = False
        fn1.decorators = ["@app.post('/users')"]

        self.mock_server.graph_builder.get_functions.return_value = [fn1]

        res = self.detector.detect()
        eps = res["entrypoints"]

        self.assertEqual(len(eps), 1)
        self.assertEqual(eps[0]["name"], "create_user")
        self.assertEqual(eps[0]["category"], "web")
        self.assertIn("@app.post", str(eps[0]["reasons"]))


if __name__ == "__main__":
    unittest.main()
