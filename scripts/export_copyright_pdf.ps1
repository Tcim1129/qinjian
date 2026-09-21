param(
    [string]$PackagePath = (Join-Path $PSScriptRoot '..\output\copyright_work\package'),
    [string]$NameFilter = '*.docx'
)
$ErrorActionPreference = 'Stop'
$package = (Resolve-Path -LiteralPath $PackagePath).Path
$word = $null
$current = $null
try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $word.AutomationSecurity = 3
    foreach ($inputFile in Get-ChildItem -LiteralPath $package -Filter $NameFilter -File) {
        $current = $word.Documents.Open($inputFile.FullName, $false, $false, $false)
        $current.Repaginate()
        $current.Fields.Update() | Out-Null
        foreach ($toc in $current.TablesOfContents) { $toc.Update() }
        foreach ($styleNumber in @(-20, -21)) {
            $style = $current.Styles.Item($styleNumber)
            $style.Font.Name = '宋体'
            $style.Font.NameFarEast = '宋体'
            $style.Font.Color = 0
            $style.Font.Size = 12
            $style.ParagraphFormat.FirstLineIndent = 0
            $style.ParagraphFormat.SpaceAfter = 8
        }
        $current.Repaginate()
        foreach ($toc in $current.TablesOfContents) { $toc.UpdatePageNumbers() }
        $current.Content.Font.Name = '宋体'
        $current.Content.Font.NameAscii = '宋体'
        $current.Content.Font.NameOther = '宋体'
        $current.Content.Font.NameFarEast = '宋体'
        $current.Content.Font.Color = 0
        foreach ($section in $current.Sections) {
            foreach ($header in $section.Headers) { $header.Range.Fields.Update() | Out-Null }
            foreach ($footer in $section.Footers) { $footer.Range.Fields.Update() | Out-Null }
        }
        $current.Save()
        $pdf = [IO.Path]::ChangeExtension($inputFile.FullName, '.pdf')
        $current.ExportAsFixedFormat($pdf, 17)
        [pscustomobject]@{ Name = $inputFile.Name; Pages = $current.ComputeStatistics(2); Pdf = $pdf } | ConvertTo-Json -Compress
        $current.Close(0)
        [void][Runtime.InteropServices.Marshal]::ReleaseComObject($current)
        $current = $null
    }
} finally {
    if ($null -ne $current) { $current.Close(0); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($current) }
    if ($null -ne $word) { $word.Quit(); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($word) }
}
