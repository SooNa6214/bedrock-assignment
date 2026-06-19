import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request


PR_URL_RE = re.compile(r"^https://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/pull/(?P<number>\d+)/?$")


class GitHubError(RuntimeError):
    pass


def parse_pr_url(pr_url):
    match = PR_URL_RE.match((pr_url or "").strip())
    if not match:
        raise ValueError("pr_url must look like https://github.com/owner/repo/pull/123")
    return {
        "owner": match.group("owner"),
        "repo": match.group("repo"),
        "pr_number": int(match.group("number")),
    }


def _request(method, path, token=None, body=None, accept="application/vnd.github+json"):
    token = token or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise GitHubError("GITHUB_TOKEN is required")

    url = f"https://api.github.com{path}"
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(url, method=method, data=data)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", accept)
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if body is not None:
        req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            payload = response.read().decode("utf-8")
            if not payload:
                return {}
            if "diff" in accept:
                return payload
            return json.loads(payload)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise GitHubError(f"GitHub API {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise GitHubError(f"GitHub API request failed: {exc}") from exc


def get_pull_request(owner, repo, pr_number, token=None, include_diff=True):
    encoded_repo = urllib.parse.quote(f"{owner}/{repo}", safe="/")
    pr = _request("GET", f"/repos/{encoded_repo}/pulls/{int(pr_number)}", token=token)
    files = _request("GET", f"/repos/{encoded_repo}/pulls/{int(pr_number)}/files?per_page=100", token=token)
    diff = ""
    if include_diff:
        diff = _request(
            "GET",
            f"/repos/{encoded_repo}/pulls/{int(pr_number)}",
            token=token,
            accept="application/vnd.github.v3.diff",
        )
        if isinstance(diff, (dict, list)):
            diff = json.dumps(diff, ensure_ascii=False)

    return {
        "owner": owner,
        "repo": repo,
        "pr_number": int(pr_number),
        "title": pr.get("title"),
        "body": pr.get("body") or "",
        "state": pr.get("state"),
        "author": (pr.get("user") or {}).get("login"),
        "html_url": pr.get("html_url"),
        "changed_files": pr.get("changed_files"),
        "additions": pr.get("additions"),
        "deletions": pr.get("deletions"),
        "files": [
            {
                "filename": item.get("filename"),
                "status": item.get("status"),
                "additions": item.get("additions"),
                "deletions": item.get("deletions"),
                "patch": item.get("patch") or "",
            }
            for item in files
        ],
        "diff": diff,
    }


def post_pr_comment(owner, repo, pr_number, comment, token=None):
    if not comment or not comment.strip():
        raise ValueError("comment is required")
    encoded_repo = urllib.parse.quote(f"{owner}/{repo}", safe="/")
    result = _request(
        "POST",
        f"/repos/{encoded_repo}/issues/{int(pr_number)}/comments",
        token=token,
        body={"body": comment},
    )
    return {
        "success": True,
        "comment_url": result.get("html_url"),
        "id": result.get("id"),
    }
