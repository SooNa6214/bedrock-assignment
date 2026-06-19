import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from codebuddy.complexity import analyze_complexity
from codebuddy.github_client import parse_pr_url
from codebuddy.static_review import extract_added_python_from_diff, static_review_code


class CoreTests(unittest.TestCase):
    def test_parse_pr_url(self):
        parsed = parse_pr_url("https://github.com/acme/demo/pull/123")
        self.assertEqual(parsed["owner"], "acme")
        self.assertEqual(parsed["repo"], "demo")
        self.assertEqual(parsed["pr_number"], 123)

    def test_parse_pr_url_rejects_invalid_url(self):
        with self.assertRaises(ValueError):
            parse_pr_url("https://example.com/acme/demo/pull/123")

    def test_extract_added_python_from_diff(self):
        diff = """diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -0,0 +1,2 @@
+def add(a,b):
+    return a+b
diff --git a/README.md b/README.md
+++ b/README.md
+hello
"""
        self.assertEqual(extract_added_python_from_diff(diff), "def add(a,b):\n    return a+b")

    def test_static_review_finds_sql_injection_and_style(self):
        code = """def add(a,b):
    return a+b

def get_user(id):
    query = f"SELECT * FROM users WHERE id = {id}"
    return execute(query)
"""
        result = static_review_code(code)
        types = {item["type"] for item in result["findings"]}
        self.assertIn("SQL Injection", types)
        self.assertIn("Style", types)

    def test_complexity(self):
        code = """def process(value):
    if value:
        for item in value:
            if item:
                return item
    return None
"""
        result = analyze_complexity(code)
        self.assertTrue(result["success"])
        self.assertEqual(result["functions"][0]["name"], "process")
        self.assertGreaterEqual(result["functions"][0]["complexity"], 4)


if __name__ == "__main__":
    unittest.main()

