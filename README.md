# CodeBuddy

Amazon Bedrock 강의 1장부터 10장까지의 최종 결과물 형태로 만든 GitHub PR 자동 코드리뷰 프로젝트입니다.

CodeBuddy는 PR URL을 입력받아 GitHub 변경 내용을 읽고, 코드 스타일/보안/복잡도/테스트 제안을 생성한 뒤 PR 댓글과 Slack 알림까지 연결할 수 있습니다.

## 구성

- `src/codebuddy`: 공통 로직
- `lambda/orchestrator`: API Gateway에서 호출되는 Lambda
- `lambda/all_tools`: Bedrock Agent Action Group용 Tool Lambda
- `openapi/agent_tools_schema.json`: Bedrock Agent Action Group 스키마
- `prompts/agent_instructions.md`: Agent Instructions
- `infra/cloudformation.yaml`: Lambda, API Gateway, IAM 배포 템플릿
- `scripts/package.ps1`: Lambda ZIP 생성
- `scripts/deploy.ps1`: S3 업로드 및 CloudFormation 배포
- `tests`: 로컬 단위 테스트

## 동작 모드

`direct` 모드:

- Bedrock Agent 없이 Orchestrator Lambda가 직접 GitHub PR을 조회하고 정적 리뷰를 수행합니다.
- 먼저 안정적으로 API와 GitHub/Slack 연동을 확인하기 좋습니다.

`agent` 모드:

- Orchestrator Lambda가 Bedrock Agent를 호출합니다.
- Agent는 `get_github_pr`, `post_pr_comment`, `send_slack_message`, `analyze_complexity` Tool을 사용합니다.

## 필요한 값

아래 값은 사용자가 준비해야 합니다.

- AWS 계정 및 `ap-northeast-2` 리전 권한
- AWS CLI 로그인 또는 `aws configure`
- GitHub Personal Access Token: `repo` 권한 필요
- Slack Incoming Webhook URL: Slack 알림을 쓸 때 필요
- S3 버킷: Lambda ZIP 업로드용
- Bedrock Agent ID/Alias ID: `agent` 모드에서 필요

비밀값은 코드에 넣지 말고 환경변수 또는 CloudFormation 파라미터로 전달하세요.

## 로컬 테스트

현재 PC의 기본 `python`이 Windows Store 별칭이면 실제 Python을 설치하거나, 설치된 Python 경로로 실행하세요.

```powershell
python -m unittest discover -s tests
```

이 프로젝트의 핵심 로직은 표준 라이브러리만 사용합니다. Lambda 런타임에서는 `boto3`가 기본 제공됩니다.

## 패키징

```powershell
.\scripts\package.ps1
```

생성물:

- `dist/orchestrator.zip`
- `dist/all-tools.zip`

## 배포

먼저 Lambda ZIP을 올릴 S3 버킷을 준비합니다.

```powershell
& "C:\Program Files\Amazon\AWSCLIV2\aws.exe" s3 mb s3://YOUR_BUCKET_NAME --region ap-northeast-2
```

직접 모드 배포:

```powershell
.\scripts\deploy.ps1 `
  -Bucket YOUR_BUCKET_NAME `
  -SlackWebhookUrl "https://hooks.slack.com/services/xxx" `
  -SlackChannel "#code-review" `
  -Profile codebuddy-user `
  -Mode direct
```

Agent 모드 배포:

```powershell
.\scripts\deploy.ps1 `
  -Bucket YOUR_BUCKET_NAME `
  -SlackWebhookUrl "https://hooks.slack.com/services/xxx" `
  -SlackChannel "#code-review" `
  -AgentId "AGENT_ID" `
  -AgentAliasId "ALIAS_ID" `
  -Profile codebuddy-user `
  -Mode agent
```

배포가 끝나면 CloudFormation Output의 `ReviewApiUrl`을 확인합니다.

## API 호출

```powershell
$body = @{
  pr_url = "https://github.com/owner/repo/pull/123"
  action = "review"
  mode = "direct"
  post_comment = $true
  notify_slack = $true
} | ConvertTo-Json

Invoke-RestMethod `
  -Uri "https://YOUR_API_ID.execute-api.ap-northeast-2.amazonaws.com/prod/review" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body
```

처음 테스트할 때는 실수로 댓글이 달리지 않도록 `post_comment = $false`로 시작하는 것을 권장합니다.

## Bedrock Agent 연결 순서

1. Bedrock Agent를 생성합니다.
2. `prompts/agent_instructions.md` 내용을 Instructions에 넣습니다.
3. Knowledge Base를 연결합니다.
4. Action Group을 생성하고 `openapi/agent_tools_schema.json`을 등록합니다.
5. Action Group Executor에는 CloudFormation Output의 `AllToolsLambdaArn`을 지정합니다.
6. Agent Prepare를 실행합니다.
7. Alias를 생성하거나 업데이트합니다.
8. `agent` 모드로 API를 호출합니다.

## 오류를 줄이는 체크리스트

- `GITHUB_TOKEN`은 코드에 커밋하지 않습니다.
- Slack Webhook URL도 코드에 커밋하지 않습니다.
- PR URL은 `https://github.com/owner/repo/pull/123` 형식이어야 합니다.
- Agent Action Group 수정 후에는 반드시 Prepare를 다시 실행합니다.
- Lambda CloudWatch 로그에서 GitHub 401/403 오류를 확인합니다.
- API 테스트 초반에는 `post_comment=false`, `notify_slack=false`로 dry run을 먼저 합니다.
