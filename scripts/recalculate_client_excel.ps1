param(
    [Parameter(Mandatory=$true)][string]$InputDirectory,
    [Parameter(Mandatory=$true)][string]$EvidenceDirectory,
    [switch]$ExportPdf
)
$ErrorActionPreference = 'Stop'
$almaRoot = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$almaInput = [IO.Path]::GetFullPath($InputDirectory)
$almaEvidence = [IO.Path]::GetFullPath($EvidenceDirectory)
foreach ($almaTarget in @($almaInput, $almaEvidence)) {
    if (-not $almaTarget.StartsWith($almaRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Excel verification targets must stay within this project.'
    }
}
New-Item -ItemType Directory -Path $almaEvidence -Force | Out-Null
$almaExcel = $null
$almaOwned = $false
$almaBook = $null
$almaReceipts = @()
try {
    # Always create a separate instance. Never attach to the client's open Excel.
    $almaExcel = New-Object -ComObject Excel.Application
    if ($almaExcel.Workbooks.Count -ne 0) { throw 'Expected an empty, newly created Excel instance.' }
    $almaOwned = $true
    $almaExcel.Visible = $false
    $almaExcel.DisplayAlerts = $false
    $almaExcel.EnableEvents = $false
    $almaExcel.AskToUpdateLinks = $false
    $almaExcel.AutomationSecurity = 3
    foreach ($almaFile in (Get-ChildItem -LiteralPath $almaInput -Filter '*.xlsx' -File)) {
        $almaBook = $almaExcel.Workbooks.Open($almaFile.FullName, 0, $false)
        $almaExcel.CalculateFullRebuild()
        if ($almaExcel.CalculationState -ne 0) { throw 'Excel calculation has not finished.' }
        $almaBook.Save()
        $almaExports = @()
        if ($ExportPdf) {
            foreach ($almaSheetName in @('INICIO', 'DECISIONES', 'FLUJO_13_SEMANAS')) {
                $almaPdf = Join-Path $almaEvidence ($almaFile.BaseName + '_' + $almaSheetName + '.pdf')
                $almaBook.Worksheets.Item($almaSheetName).ExportAsFixedFormat(0, $almaPdf)
                $almaExports += [IO.Path]::GetFileName($almaPdf)
            }
        }
        $almaBook.Close($false)
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($almaBook)
        $almaBook = $null
        $almaPython = Join-Path $almaRoot '.venv\Scripts\python.exe'
        if (-not (Test-Path -LiteralPath $almaPython)) { $almaPython = 'python' }
        & $almaPython (Join-Path $PSScriptRoot 'normalize_client_metadata.py') $almaFile.FullName
        if ($LASTEXITCODE -ne 0) { throw 'Office metadata normalization failed.' }
        $almaReceipts += [pscustomobject]@{
            file=$almaFile.Name
            engine='Microsoft Excel'
            version=$almaExcel.Version
            build=$almaExcel.Build
            sha256=(Get-FileHash -LiteralPath $almaFile.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
            recalculated=$true
            exported_pdf=$almaExports
        }
    }
    if ($almaReceipts.Count -eq 0) { throw 'No workbooks were found.' }
    $almaJson = ConvertTo-Json -InputObject @($almaReceipts) -Depth 6
    [IO.File]::WriteAllText((Join-Path $almaEvidence 'excel-recalculation.json'), $almaJson, [Text.UTF8Encoding]::new($false))
    $almaJson
} finally {
    if ($null -ne $almaBook) { $almaBook.Close($false); [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($almaBook) }
    if ($null -ne $almaExcel) { if ($almaOwned) { $almaExcel.Quit() }; [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($almaExcel) }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
