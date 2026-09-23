param(
    [Parameter(Position=0)]
    [ValidateSet('workspace','demo','verify','weekly','weekly-resume')]
    [string]$Command = 'workspace',
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$CommandArgs
)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$almaCandidates = @(
    (Join-Path $PSScriptRoot '.venv\Scripts\python.exe'),
    (Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe')
)
$almaPython = $null
foreach ($candidate in $almaCandidates) { if (Test-Path -LiteralPath $candidate) { $almaPython = $candidate; break } }
if (-not $almaPython) { $candidate = Get-Command python -ErrorAction SilentlyContinue; if ($candidate) { $almaPython = $candidate.Source } }
if (-not $almaPython) { throw 'Python 3.11+ required. See README.md.' }
$almaArgs = if ($Command -in @('weekly','weekly-resume')) {
    @('-m','alma.weekly',$Command) + $CommandArgs
} else {
    @('-m','alma',$Command) + $CommandArgs
}
& $almaPython @almaArgs
exit $LASTEXITCODE
