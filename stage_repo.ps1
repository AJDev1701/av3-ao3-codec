# stage_repo.ps1 v1.0.2 -- relative path manifest
$ErrorActionPreference = "Stop"
Set-Location "D:\workspace\av3-ao3-codec"
Write-Host "[*] Running codec self-test..."
python ao3_codec.py
if ($LASTEXITCODE -ne 0) { Write-Error "Codec test failed"; exit 1 }
Write-Host "[*] Generating relative-path SHA-256 manifest..."
$files = @("SPEC.md","ao3_codec.py","stage_repo.ps1")
$rows  = foreach ($f in $files) {
    $h = (Get-FileHash -Algorithm SHA256 -Path $f).Hash
    [PSCustomObject]@{Algorithm="SHA256";Hash=$h;Path=$f}
}
$rows | Format-Table -AutoSize | Out-String | Set-Content -Path "SHA256MANIFEST.txt" -Encoding utf8
Write-Host "[+] Manifest written with relative paths."