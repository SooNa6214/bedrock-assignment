import ast


BRANCH_NODES = (
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.Try,
    ast.ExceptHandler,
    ast.With,
    ast.AsyncWith,
    ast.IfExp,
    ast.Match,
)


class ComplexityVisitor(ast.NodeVisitor):
    def __init__(self):
        self.functions = []
        self._stack = []

    def visit_FunctionDef(self, node):
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node):
        self._visit_function(node)

    def _visit_function(self, node):
        frame = {"name": node.name, "line": node.lineno, "complexity": 1}
        self._stack.append(frame)
        for child in node.body:
            self.visit(child)
        self.functions.append(self._stack.pop())

    def generic_visit(self, node):
        if self._stack and isinstance(node, BRANCH_NODES):
            self._stack[-1]["complexity"] += 1
        if self._stack and isinstance(node, ast.BoolOp):
            self._stack[-1]["complexity"] += max(1, len(node.values) - 1)
        super().generic_visit(node)


def grade_complexity(score):
    if score <= 10:
        return {"level": "GOOD", "label": "Good", "recommendation": "Keep as is"}
    if score <= 20:
        return {"level": "WARNING", "label": "Warning", "recommendation": "Consider refactoring"}
    if score <= 50:
        return {"level": "COMPLEX", "label": "Complex", "recommendation": "Split the function"}
    return {"level": "DANGER", "label": "Danger", "recommendation": "Rewrite recommended"}


def analyze_complexity(code):
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return {
            "success": False,
            "error": f"SyntaxError line {exc.lineno}: {exc.msg}",
            "functions": [],
        }

    visitor = ComplexityVisitor()
    visitor.visit(tree)
    functions = []
    for item in sorted(visitor.functions, key=lambda row: row["line"]):
        grade = grade_complexity(item["complexity"])
        functions.append({**item, **grade})

    max_score = max([row["complexity"] for row in functions], default=0)
    return {
        "success": True,
        "max_complexity": max_score,
        "functions": functions,
    }
