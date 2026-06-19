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
                    "description": "SQL 문자열에 사용자 입력이 직접 삽입될 수 있습니다.",
                    "suggestion": "파라미터 바인딩 또는 ORM query builder를 사용하세요.",
                }
            )
        if SECRET_RE.search(stripped):
            findings.append(
                {
                    "line": index,
                    "severity": "CRITICAL",
                    "type": "Hardcoded Secret",
                    "description": "비밀값으로 보이는 문자열이 코드에 직접 포함되어 있습니다.",
                    "suggestion": "Secrets Manager, Parameter Store, Lambda 환경변수를 사용하세요.",
                }
            )
        if re.search(r"def\s+\w+\([^)]*,[^ )]", stripped):
            findings.append(
                {
                    "line": index,
                    "severity": "LOW",
                    "type": "Style",
                    "description": "쉼표 뒤 공백이 없어 PEP8 스타일과 맞지 않습니다.",
                    "suggestion": "예: def add(a, b):",
                }
            )
        if stripped.startswith("print("):
            findings.append(
                {
                    "line": index,
                    "severity": "LOW",
                    "type": "Logging",
                    "description": "운영 코드에서 print 사용은 추적성과 로그 레벨 관리가 어렵습니다.",
                    "suggestion": "logging 모듈을 사용하세요.",
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
                    "description": f"{item['name']} 함수의 복잡도는 {item['complexity']}입니다.",
                    "suggestion": item["recommendation"],
                }
            )

    return {"findings": findings, "complexity": complexity}


def render_markdown_review(pr, review):
    findings = review.get("findings", [])
    complexity = review.get("complexity", {})
    lines = [
        "## CodeBuddy 자동 리뷰 결과",
        "",
        f"- PR: {pr.get('title') or pr.get('pr_number')}",
        f"- 변경 파일: {pr.get('changed_files', 0)}개",
        f"- 추가/삭제: +{pr.get('additions', 0)} / -{pr.get('deletions', 0)}",
        "",
    ]

    if findings:
        lines.append("### 발견된 이슈")
        for item in findings:
            lines.extend(
                [
                    f"- `{item['severity']}` {item['type']} (line {item['line']})",
                    f"  - 문제: {item['description']}",
                    f"  - 제안: {item['suggestion']}",
                ]
            )
    else:
        lines.append("### 발견된 이슈")
        lines.append("- 자동 정적 분석 기준으로는 주요 이슈를 찾지 못했습니다.")

    functions = complexity.get("functions", [])
    if functions:
        lines.extend(["", "### 복잡도 분석"])
        for item in functions:
            lines.append(f"- `{item['name']}` line {item['line']}: {item['complexity']} ({item['label']})")

    lines.extend(
        [
            "",
            "### 테스트 코드 제안",
            "- SQL 실행 함수는 정상 입력과 악의적 입력을 모두 테스트하세요.",
            "- 복잡도가 높은 함수는 분기별 단위 테스트를 작성하세요.",
            "- 외부 API 호출은 mock을 사용해 성공/실패 케이스를 분리하세요.",
        ]
    )
    return "\n".join(lines)

