import json
import os
import sys
import uuid

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from codebuddy.agent_response import api_response
from codebuddy.github_client import parse_pr_url
from codebuddy.reviewer import review_pull_request


def _body(event):
    raw = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        import base64

        raw = base64.b64decode(raw).decode("utf-8")
    return json.loads(raw)


def _invoke_agent(prompt, session_id):
    try:
        import boto3
    except ImportError as exc:
        raise RuntimeError("boto3 is required to invoke Bedrock Agent") from exc

    agent_id = os.environ.get("AGENT_ID")
    alias_id = os.environ.get("AGENT_ALIAS_ID")
    if not agent_id or not alias_id:
        raise RuntimeError("AGENT_ID and AGENT_ALIAS_ID are required for agent mode")

    client = boto3.client("bedrock-agent-runtime", region_name=os.environ.get("AWS_REGION", "ap-northeast-2"))
    response = client.invoke_agent(
        agentId=agent_id,
        agentAliasId=alias_id,
        sessionId=session_id,
        inputText=prompt,
        enableTrace=True,
    )
    chunks = []
    traces = []
    for event in response.get("completion", []):
        if "chunk" in event:
            chunks.append(event["chunk"]["bytes"].decode("utf-8"))
        if "trace" in event:
            traces.append(event["trace"])
    return {"answer": "".join(chunks), "trace_count": len(traces)}


def handler(event, context):
    if (event.get("httpMethod") or "").upper() == "OPTIONS":
        return api_response(200, {"ok": True})

    try:
        body = _body(event)
    except Exception:
        return api_response(400, {"message": "Invalid JSON body", "status": "failed"})

    pr_url = body.get("pr_url")
    action = body.get("action", "review")
    mode = body.get("mode") or os.environ.get("CODEBUDDY_MODE", "direct")
    post_comment = bool(body.get("post_comment", True))
    notify_slack = bool(body.get("notify_slack", bool(os.environ.get("SLACK_WEBHOOK_URL"))))
    slack_channel = body.get("slack_channel") or os.environ.get("SLACK_CHANNEL", "#code-review")

    try:
        parsed = parse_pr_url(pr_url)
    except Exception as exc:
        return api_response(400, {"message": str(exc), "status": "failed"})

    session_id = body.get("session_id") or str(uuid.uuid4())

    try:
        if mode == "agent":
            prompt = (
                f"{parsed['owner']}/{parsed['repo']}의 PR #{parsed['pr_number']}을 리뷰하고 "
                "보안, 스타일, 복잡도, 테스트 제안을 정리해줘. "
            )
            if post_comment:
                prompt += "리뷰 결과를 GitHub PR 댓글로 남겨줘. "
            if notify_slack:
                prompt += f"완료되면 {slack_channel} 채널에 Slack 알림을 보내줘."
            result = _invoke_agent(prompt, session_id)
        else:
            result = review_pull_request(
                parsed["owner"],
                parsed["repo"],
                parsed["pr_number"],
                post_comment=post_comment,
                notify_slack=notify_slack,
                slack_channel=slack_channel,
            )

        return api_response(
            200,
            {
                "message": "리뷰가 완료되었습니다.",
                "status": "completed",
                "action": action,
                "mode": mode,
                "session_id": session_id,
                "result": result,
            },
        )
    except Exception as exc:
        return api_response(500, {"message": str(exc), "status": "failed", "session_id": session_id})

