import json
import os


MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "global.anthropic.claude-sonnet-4-6")


def call_bedrock_review(code, context=""):
    try:
        import boto3
    except ImportError as exc:
        raise RuntimeError("boto3 is required for Bedrock calls") from exc

    client = boto3.client("bedrock-runtime", region_name=os.environ.get("AWS_REGION", "ap-northeast-2"))
    prompt = f"""당신은 실무 경험이 많은 시니어 코드 리뷰어입니다.
다음 코드를 리뷰하고 JSON으로만 응답하세요.

분석 항목:
1. 버그 가능성
2. 보안 취약점
3. 코드 스타일
4. 성능 및 복잡도
5. 리팩토링 제안
6. 테스트 코드 제안

참고 문서:
{context}

코드:
```python
{code}
```

JSON 스키마:
{{
  "summary": "전체 평가",
  "findings": [
    {{
      "line": 1,
      "severity": "CRITICAL/HIGH/MEDIUM/LOW",
      "type": "분류",
      "description": "문제 설명",
      "suggestion": "수정 제안"
    }}
  ],
  "tests": ["테스트 제안"]
}}
"""
    response = client.converse(
        modelId=MODEL_ID,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"temperature": 0.2, "maxTokens": 3000},
    )
    text = response["output"]["message"]["content"][0]["text"]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"summary": text, "findings": [], "tests": []}

