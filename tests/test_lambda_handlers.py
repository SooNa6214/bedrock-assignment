import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "lambda", "all_tools"))
sys.path.insert(0, os.path.join(ROOT, "src"))

import index as all_tools


class LambdaHandlerTests(unittest.TestCase):
    def test_complexity_tool(self):
        event = {
            "apiPath": "/complexity",
            "httpMethod": "POST",
            "parameters": [{"name": "code", "value": "def f(x):\n    if x:\n        return 1\n    return 0"}],
        }
        response = all_tools.handler(event, None)
        self.assertEqual(response["messageVersion"], "1.0")
        self.assertEqual(response["response"]["httpStatusCode"], 200)


if __name__ == "__main__":
    unittest.main()

