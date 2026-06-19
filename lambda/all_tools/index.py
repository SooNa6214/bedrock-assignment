import json
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from codebuddy.agent_response import error_response, success_response
from codebuddy.complexity import analyze_complexity
from codebuddy.github_client import get_pull_request, post_pr_comment
from codebuddy.slack_client import send_slack_message


def _params(event):
    values = {}
    for item in event.get("parameters", []) or []:
        values[item.get("name")] = item.get("value")
    body = event.get("requestBody", {})
    content = body.get("content", {}).get("application/json", {})
    properties = content.get("properties", []) or []
    for item in properties:
        values[item.get("name")] = item.get("value")
    return values


def handler(event, context):
    api_path = event.get("apiPath")
    method = (event.get("httpMethod") or "").upper()
    params = _params(event)

    try:
        if api_path == "/pr" and method == "GET":
            result = get_pull_request(
                params.get("owner"),
                params.get("repo"),
                int(params.get("pr_number")),
                include_diff=params.get("include_diff", "true") != "false",
            )
            return success_response(event, result)

        if api_path == "/pr/comment" and method == "POST":
            result = post_pr_comment(
                params.get("owner"),
                params.get("repo"),
                int(params.get("pr_number")),
                params.get("comment"),
            )
            return success_response(event, result)

        if api_path == "/slack/send" and method == "POST":
            result = send_slack_message(params.get("channel"), params.get("message"))
            return success_response(event, result)

        if api_path == "/complexity" and method == "POST":
            result = analyze_complexity(params.get("code") or "")
            return success_response(event, result)

        return error_response(event, f"Unsupported route: {method} {api_path}", 404)
    except Exception as exc:
        return error_response(event, str(exc), 500)

