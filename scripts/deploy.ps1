param(
    [Parameter(Mandatory=$true)][string]$Bucket,
    [string]$GitHubToken = $env:GITHUB_TOKEN,
    [string]$SlackWebhookUrl = "",
    [string]$SlackChannel = "#code-review",
    [string]$StackName = "CodeBuddyStack",
    [string]$Region = "ap-northeast-2",
    [string]$ProjectName = "codebuddy",
    [string]$AgentId = "",
    [string]$AgentAliasId = "",
    [ValidateSet("direct", "agent")][string]$Mode = "direct",
    [string]$Profile = "codebuddy-user",
    [string]$AwsCli = "C:\Program Files\Amazon\AWSCLIV2\aws.exe"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$dist = Join-Path $root "dist"

if (-not (Test-Path -LiteralPath $AwsCli)) {
    $AwsCli = "aws"
}

if (-not $GitHubToken) {
    throw "GitHubToken is required. Set `$env:GITHUB_TOKEN or pass -GitHubToken."
}

& (Join-Path $PSScriptRoot "package.ps1")

$prefix = "$ProjectName/$([DateTimeOffset]::UtcNow.ToUnixTimeSeconds())"
$orchestratorKey = "$prefix/orchestrator.zip"
$toolsKey = "$prefix/all-tools.zip"
$orchestratorZip = Get-ChildItem -LiteralPath $dist -Filter "orchestrator-*.zip" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
$toolsZip = Get-ChildItem -LiteralPath $dist -Filter "all-tools-*.zip" | Sort-Object LastWriteTime -Descending | Select-Object -First 1

if (-not $orchestratorZip -or -not $toolsZip) {
    throw "Lambda zip artifacts were not created."
}

& $AwsCli s3 cp $orchestratorZip.FullName "s3://$Bucket/$orchestratorKey" --region $Region --profile $Profile
& $AwsCli s3 cp $toolsZip.FullName "s3://$Bucket/$toolsKey" --region $Region --profile $Profile

& $AwsCli cloudformation deploy `
    --template-file (Join-Path $root "infra/cloudformation.yaml") `
    --stack-name $StackName `
    --region $Region `
    --profile $Profile `
    --capabilities CAPABILITY_NAMED_IAM `
    --parameter-overrides `
        ProjectName=$ProjectName `
        CodeBucket=$Bucket `
        OrchestratorCodeKey=$orchestratorKey `
        ToolsCodeKey=$toolsKey `
        GitHubToken=$GitHubToken `
        SlackWebhookUrl=$SlackWebhookUrl `
        SlackChannel=$SlackChannel `
        AgentId=$AgentId `
        AgentAliasId=$AgentAliasId `
        CodeBuddyMode=$Mode

& $AwsCli cloudformation describe-stacks `
    --stack-name $StackName `
    --region $Region `
    --profile $Profile `
    --query "Stacks[0].Outputs"
