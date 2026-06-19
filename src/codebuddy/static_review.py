import re

from .complexity import analyze_complexity


SQL_FSTRING_RE = re.compile(r"f[\"'].*SELECT\s+.*\{.+\}.*[\"']", re.IGNORECASE)
SECRET_RE = re.compile(r"(aws_access_key_id|aws_secret_access_key|api[_-]?key|token|password)\s*=\s*[\"'][^\"']+[\"']", re.IGNORECASE)


def extract_added_python_from_diff(diff):
    chunks = []
    current_file = None
    for line in (diff or "").splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:]
            continue
        if not current_file or not current_file.endswith(".py"):
            continue
        if line.startswith("+") and not line.startswith("+++"):
            chunks.append(line[1:])
    return "\n".join(chunks)


def static_review_code(code):
    findings = []
    lines = code.splitlines()
    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        if SQL_FSTRING_RE.search(stripped):
            findings.append(
                {
                    "line": index,
                    "severity": "HIGH",
                    "type": "SQL Injection",
                    "description": "User input may be inserted directly into an SQL query string.",
                    "suggestion": "Use parameter binding or an ORM query builder.",
                }
            )
        if SECRET_RE.search(stripped):
            findings.append(
                {
                    "line": index,
                    "severity": "CRITICAL",
                    "type": "Hardcoded Secret",
                    "description": "A value that looks like a secret is hardcoded in the source code.",
                    "suggestion": "Use Secrets Manager, Parameter Store, or Lambda environment variables.",
                }
            )
        if re.search(r"def\s+\w+\([^)]*,[^ )]", stripped):
            findings.append(
                {
                    "line": index,
                    "severity": "LOW",
                    "type": "Style",
                    "description": "A comma is missing a following space, which violates common PEP8 style.",
                    "suggestion": "Example: def add(a, b):",
                }
            )
        if stripped.startswith("print("):
            findings.append(
                {
                    "line": index,
                    "severity": "LOW",
                    "type": "Logging",
                    "description": "Using print in application code makes log levels and traceability harder to manage.",
                    "suggestion": "Use the logging module.",
                }
            )

    complexity = analyze_complexity(code)
    for item in complexity.get("functions", []):
        if item["complexity"] > 10:
            findings.append(
                {
                    "line": item["line"],
                    "severity": "MEDIUM" if item["complexity"] <= 20 else "HIGH",
                    "type": "Complexity",
                    "description": f"Function {item['name']} has cyclomatic complexity {item['complexity']}.",
                    "suggestion": item["recommendation"],
                }
            )

    return {"findings": findings, "complexity": complexity}


def render_markdown_review(pr, review):
    findings = review.get("findings", [])
    complexity = review.get("complexity", {})
    lines = [
        "## CodeBuddy Automated Review",
        "",
        f"- PR: {pr.get('title') or pr.get('pr_number')}",
        f"- Changed files: {pr.get('changed_files', 0)}",
        f"- Additions/Deletions: +{pr.get('additions', 0)} / -{pr.get('deletions', 0)}",
        "",
    ]

    if findings:
        lines.append("### Findings")
        for item in findings:
            lines.extend(
                [
                    f"- `{item['severity']}` {item['type']} (line {item['line']})",
                    f"  - Problem: {item['description']}",
                    f"  - Suggestion: {item['suggestion']}",
                ]
            )
    else:
        lines.append("### Findings")
        lines.append("- No major issues were found by the static review checks.")

    functions = complexity.get("functions", [])
    if functions:
        lines.extend(["", "### Complexity"])
        for item in functions:
            lines.append(f"- `{item['name']}` line {item['line']}: {item['complexity']} ({item['level']})")

    lines.extend(
        [
            "",
            "### Test Suggestions",
            "- Test SQL execution code with both normal input and malicious input.",
            "- Add branch-level unit tests for functions with nested conditions.",
            "- Mock external API calls and cover both success and failure cases.",
        ]
    )
    return "\n".join(lines)
