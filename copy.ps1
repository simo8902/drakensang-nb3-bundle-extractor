$src = "C:\asd\new"
$baseDst = Join-Path $PSScriptRoot "diff"
$listFile = Join-Path $PSScriptRoot "diff_required.txt"

$dst = $baseDst
$i = 2
while (Test-Path $dst) {
    $items = Get-ChildItem -Path $dst -Recurse -ErrorAction SilentlyContinue
    if ($items.Count -gt 0) {
        $dst = "${baseDst}_$i"
        $i++
    } else {
        break
    }
}
New-Item -ItemType Directory -Force -Path $dst | Out-Null

Get-Content $listFile | ForEach-Object {
    if ($_ -match "^(.*?)\s*\|\s*([0-9a-fA-F]+)$") {
        $rel = $matches[1].Trim()
        $hash = $matches[2].Trim()

        $base = ($rel -replace "[\\/]", "_")
        $target = "$base._$hash"

        $file = Get-ChildItem -Path $src -Recurse -Filter "$target" -ErrorAction SilentlyContinue | Select-Object -First 1

        if ($file) {
            $dstFile = Join-Path $dst $file.Name
            Copy-Item -LiteralPath $file.FullName -Destination $dstFile -Force
            Write-Host "Copied -> $($file.Name)"
        } else {
            Write-Host "Missing -> $target"
        }
    }
}

Write-Host "Done. Copied files saved in: $dst"
