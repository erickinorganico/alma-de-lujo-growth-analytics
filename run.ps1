param(
    [ValidateSet('demo', 'verify')][string]$Command = 'demo',
    [ValidateSet('normal','missing_cost','negative_stock','missing_payment','duplicate_event')][string]$Scenario = 'normal'
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
$almaArgs = @('-m','alma',$Command)
if ($Command -eq 'demo') { $almaArgs += @('--scenario',$Scenario); if ($Scenario -ne 'normal') { $almaArgs += @('--output',"build/$Scenario") } }
& $almaPython @almaArgs
exit $LASTEXITCODE
