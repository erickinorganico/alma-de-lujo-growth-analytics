[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$SchemaPath,
    [Parameter(Mandatory = $true)][string]$Definition,
    [Parameter(Mandatory = $true)][string]$InstancePath
)

$ErrorActionPreference = "Stop"
$allowedDefinitions = @(
    "current_cut",
    "request",
    "response",
    "query_trace",
    "dispatch_receipt",
    "packet",
    "decision_binding",
    "decision_anchor",
    "carried_decision"
)

function Write-Result([string]$Status) {
    [Console]::Out.WriteLine("definition=$Definition status=$Status")
}

try {
    if ($Definition -notin $allowedDefinitions) {
        throw "definition is not allowlisted"
    }
    if (-not (Test-Path -LiteralPath $SchemaPath -PathType Leaf) -or
        -not (Test-Path -LiteralPath $InstancePath -PathType Leaf)) {
        throw "schema or instance is unavailable"
    }

    $schemaText = [IO.File]::ReadAllText((Resolve-Path -LiteralPath $SchemaPath))
    $instanceText = [IO.File]::ReadAllText((Resolve-Path -LiteralPath $InstancePath))
    $schema = $schemaText | ConvertFrom-Json -Depth 100
    $definitions = $schema.'$defs'
    if ($null -eq $definitions -or $null -eq $definitions.PSObject.Properties[$Definition]) {
        throw "definition is absent"
    }

    $wrapper = [ordered]@{
        '$schema' = $schema.'$schema'
        '$defs' = $definitions
        '$ref' = "#/`$defs/$Definition"
    } | ConvertTo-Json -Depth 100 -Compress

    $valid = Test-Json -Json $instanceText -Schema $wrapper -ErrorAction Stop -WarningAction SilentlyContinue
    if (-not $valid) {
        Write-Result "INVALID"
        exit 1
    }
    Write-Result "VALID"
    exit 0
}
catch {
    Write-Result "INVALID"
    exit 1
}
