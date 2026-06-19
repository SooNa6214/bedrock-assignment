param(
    [string]$OutDir = "dist"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$dist = Join-Path $root $OutDir

New-Item -ItemType Directory -Force -Path $dist | Out-Null
$stamp = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()

function Copy-PythonSource {
    param(
        [string]$Source,
        [string]$Destination
    )

    Get-ChildItem -LiteralPath $Source -Recurse -File -Filter "*.py" | ForEach-Object {
        $relative = $_.FullName.Substring($Source.Length).TrimStart('\')
        $target = Join-Path $Destination $relative
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
        Copy-Item -LiteralPath $_.FullName -Destination $target -Force
    }
}

function New-LambdaZip {
    param(
        [string]$LambdaName,
        [string]$HandlerSource
    )

    $build = Join-Path $dist "$LambdaName-build-$([Guid]::NewGuid().ToString('N'))"
    New-Item -ItemType Directory -Force -Path $build | Out-Null
    Copy-Item -LiteralPath (Join-Path $root $HandlerSource) -Destination (Join-Path $build "index.py")
    Copy-PythonSource -Source (Join-Path $root "src") -Destination (Join-Path $build "src")

    $zip = Join-Path $dist "$LambdaName-$stamp.zip"
    Compress-Archive -Path (Join-Path $build "*") -DestinationPath $zip -Force
    Remove-Item -LiteralPath $build -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "Created $zip"
}

New-LambdaZip -LambdaName "orchestrator" -HandlerSource "lambda/orchestrator/index.py"
New-LambdaZip -LambdaName "all-tools" -HandlerSource "lambda/all_tools/index.py"
