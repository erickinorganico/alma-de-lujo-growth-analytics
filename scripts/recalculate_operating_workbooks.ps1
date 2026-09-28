param(
    [string]$EvidenceDirectory = (Join-Path (Split-Path -Parent $PSScriptRoot) 'evidence/v1.0/excel')
)
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$evidenceRoot = [IO.Path]::GetFullPath($EvidenceDirectory)
if (-not $evidenceRoot.StartsWith($projectRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Evidence directory must stay inside the project.'
}
$books = @(
    @{ kind='blank'; file='Alma_de_Lujo_OPERACION_PLANTILLA.xlsx' },
    @{ kind='synthetic'; file='Alma_de_Lujo_OPERACION_EJEMPLO.xlsx' }
)
$bookRoot = Join-Path $projectRoot 'client/v1'
$normalizeCore = @'
import io,re,sys,zipfile
from pathlib import Path
p=Path(sys.argv[1]); out=io.BytesIO()
with zipfile.ZipFile(p) as source, zipfile.ZipFile(out,'w') as target:
    for info in source.infolist():
        data=source.read(info.filename)
        if info.filename=='docProps/core.xml':
            data,count=re.subn(rb'(<cp:lastModifiedBy>)[^<]*(</cp:lastModifiedBy>)',rb'\1Alma de Lujo\2',data)
            if count!=1: raise ValueError('Expected one cp:lastModifiedBy in Excel core properties')
        target.writestr(info,data)
p.write_bytes(out.getvalue())
'@
foreach ($book in $books) {
    if (-not (Test-Path -LiteralPath (Join-Path $bookRoot $book.file) -PathType Leaf)) { throw "Missing fixed workbook: $($book.file)" }
}
New-Item -ItemType Directory -Force -Path $evidenceRoot | Out-Null
$excel = $null
$opened = $null
$owned = $false
$receipts = @()
try {
    $excel = New-Object -ComObject Excel.Application
    if ($excel.Workbooks.Count -ne 0) { throw 'New Excel instance was not empty.' }
    $owned = $true
    $excel.Visible = $false
    $excel.DisplayAlerts = $false
    $excel.EnableEvents = $false
    $excel.AskToUpdateLinks = $false
    $excel.AutomationSecurity = 3  # msoAutomationSecurityForceDisable
    foreach ($book in $books) {
        $path = Join-Path $bookRoot $book.file
        $opened = $excel.Workbooks.Open($path, 0, $false)
        $excel.CalculateFullRebuild()
        while ($excel.CalculationState -ne 0) { Start-Sleep -Milliseconds 200 }
        $calculationMode = [int]$excel.Calculation
        $calculationState = [int]$excel.CalculationState
        if ($calculationMode -notin @(-4105, -4135, 2)) { throw "Excel returned invalid calculation mode: $calculationMode" }
        $opened.Save()
        $sheets = @()
        for ($index = 1; $index -le $opened.Worksheets.Count; $index++) {
            $sheet = $opened.Worksheets.Item($index)
            try {
                $area = [string]$sheet.PageSetup.PrintArea
                if (-not [string]::IsNullOrWhiteSpace($area)) {
                    $filename = "$($book.kind)__$($sheet.Name).pdf"
                    $pdf = Join-Path $evidenceRoot $filename
                    $sheet.Activate()
                    $sheet.ExportAsFixedFormat(0, $pdf, 0, $true, $false)
                    $sheets += [ordered]@{ sheet=$sheet.Name; print_area=$area; pdf=$filename; pdf_sha256=(Get-FileHash -LiteralPath $pdf -Algorithm SHA256).Hash.ToLowerInvariant() }
                }
            } finally { [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($sheet) }
        }
        if ($sheets.Count -ne 25) { throw "Expected 25 printed sheets in $($book.file), found $($sheets.Count)." }
        $opened.Close($false)
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($opened)
        $opened = $null
        & (Join-Path $projectRoot '.venv/Scripts/python.exe') -c $normalizeCore $path
        if ($LASTEXITCODE -ne 0) { throw 'Author metadata normalization failed.' }
        $receipts += [ordered]@{
            kind=$book.kind; file=$book.file; engine='Microsoft Excel'; version=[string]$excel.Version
            build=[string]$excel.Build; calculation_mode=$calculationMode
            calculation_state=$calculationState; calculate_full_rebuild=$true
            sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
            sheets=@($sheets)
        }
    }
    $receipt = [ordered]@{
        schema='operating-excel-recalculation-v1'
        timestamp_utc=[DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ')
        workbooks=@($receipts)
    }
    $json = ConvertTo-Json -InputObject $receipt -Depth 8
    [IO.File]::WriteAllText((Join-Path $evidenceRoot 'excel-recalculation.json'), $json + "`n", [Text.UTF8Encoding]::new($false))
    Write-Output $json
} finally {
    if ($null -ne $opened) { $opened.Close($false); [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($opened) }
    if ($null -ne $excel) { if ($owned) { $excel.Quit() }; [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($excel) }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
