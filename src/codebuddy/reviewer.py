import os

from .bedrock_review import call_bedrock_review
from .github_client import get_pull_request, post_pr_comment
from .slack_client import send_slack_message
from .static_review import extract_added_python_from_diff, render_markdown_review, static_review_code


def review_pull_request(owner, repo, pr_number, post_comment=False, notify_slack=False, slack_channel=None):
    pr = get_pull_request(owner, repo, pr_number, include_diff=True)
    code = extract_added_python_from_diff(pr.get("diff", ""))
    if not code.strip():
        review = {"findings": [], "complexity": {"functions": []}}
        comment = "## CodeBuddy 자동 리뷰 결과\n\nPython 변경 코드가 없어 자동 분석을 건너뛰었습니다."
    else:
        if os.environ.get("USE_BEDROCK_DIRECT", "false").lower() == "true":
            try:
                llm_review = call_bedrock_review(code)
                review = {
                    "findings": llm_review.get("findings", []),
                    "complexity": static_review_code(code)["complexity"],
                    "summary": llm_review.get("summary", ""),
                }
            except Exception:
                review = static_review_code(code)
        else:
            review = static_review_code(code)
        comment = render_markdown_review(pr, review)

    comment_result = None
    if post_comment:
        comment_result = post_pr_comment(owner, repo, pr_number, comment)

    slack_result = None
    if notify_slack:
        slack_result = send_slack_message(
            slack_channel or os.environ.get("SLACK_CHANNEL", "#code-review"),
            f"CodeBuddy 리뷰 완료: {owner}/{repo} PR #{pr_number}\n{pr.get('html_url')}",
        )

    return {
        "success": True,
        "pr": {k: pr.get(k) for k in ["owner", "repo", "pr_number", "title", "html_url", "changed_files"]},
        "review": review,
        "comment": comment,
        "comment_result": comment_result,
        "slack_result": slack_result,
    }

