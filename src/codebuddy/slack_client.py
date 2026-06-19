import json
import os
import urllib.error
import urllib.request


class SlackError(RuntimeError):
    pass


def send_slack_message(channel, message, webhook_url=None):
    webhook_url = webhook_url or os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        raise SlackError("SLACK_WEBHOOK_URL is required")
    if not message:
        raise ValueError("message is required")

    payload = {"text": message}
    if channel:
        payload["channel"] = channel

    request = urllib.request.Request(
        webhook_url,
        method="POST",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8", errors="replace")
            if response.status >= 300:
                raise SlackError(f"Slack webhook returned {response.status}: {body}")
            return {"success": True, "status": response.status, "body": body}
    except urllib.error.URLError as exc:
        raise SlackError(f"Slack webhook request failed: {exc}") from exc

