param([Parameter(ValueFromRemainingArguments=$true)][string[]]$GitHubArgs)
$ErrorActionPreference = 'Stop'
$almaRoot = Split-Path -Parent $PSScriptRoot
$almaConfig = Join-Path $almaRoot '.local\github'
$almaPrevious = @{}
foreach ($almaKey in @('GH_CONFIG_DIR','GH_TOKEN','GITHUB_TOKEN','GH_HOST')) {
    $almaPrevious[$almaKey] = [Environment]::GetEnvironmentVariable($almaKey, 'Process')
}
$almaExit = 1
try {
    $env:GH_CONFIG_DIR = $almaConfig
    Remove-Item Env:GH_TOKEN,Env:GITHUB_TOKEN,Env:GH_HOST -ErrorAction SilentlyContinue
    if (-not $GitHubArgs -or $GitHubArgs[0] -ne 'auth') {
        $almaLogin = & gh api user --jq .login
        if ($LASTEXITCODE -ne 0 -or $almaLogin.Trim() -ne 'erickinorganico') {
            throw 'This project requires erickinorganico. Authenticate using this wrapper: .\scripts\github-personal.ps1 auth login --hostname github.com --git-protocol https --web'
        }
    }
    & gh @GitHubArgs
    $almaExit = $LASTEXITCODE
}
finally {
    foreach ($almaKey in $almaPrevious.Keys) {
        [Environment]::SetEnvironmentVariable($almaKey, $almaPrevious[$almaKey], 'Process')
    }
}
exit $almaExit
