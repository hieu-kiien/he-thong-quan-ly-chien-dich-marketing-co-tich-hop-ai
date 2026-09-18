$ErrorActionPreference = "Stop"
$docxPath = Join-Path $PSScriptRoot "BAO_CAO_DU_AN_AIA331_80300_ICTU_V5.docx"
$pdfPath = Join-Path $PSScriptRoot "BAO_CAO_DU_AN_AIA331_80300_ICTU_V5_word_preview.pdf"

$word = $null
$doc = $null
try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $doc = $word.Documents.Open($docxPath, $false, $true)
    # SaveAs2 ổn định hơn ExportAsFixedFormat trên máy này khi Word có nhiều bảng.
    $doc.SaveAs2($pdfPath, 17)
    Write-Output "Rendered Word preview"
}
finally {
    if ($doc -ne $null) {
        $doc.Close($false)
        [void][Runtime.InteropServices.Marshal]::ReleaseComObject($doc)
    }
    if ($word -ne $null) {
        $word.Quit()
        [void][Runtime.InteropServices.Marshal]::ReleaseComObject($word)
    }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
