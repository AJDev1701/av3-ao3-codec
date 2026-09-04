$ErrorActionPreference = "Stop"
Set-Location "D:\workspace\av3-ao3-codec"
Write-Host "[*] Running codec self-test..."
python ao3_codec.py
if ($LASTEXITCODE -ne 0) { Write-Error "Codec test failed"; exit 1 }
Write-Host "[*] Generating deterministic SHA-256 manifest..."
$files = @("SPEC.md","ao3_codec.py","stage_repo.ps1")
$lines = foreach ($f in $files) {
    $h = (Get-FileHash -Algorithm SHA256 -LiteralPath $f).Hash.ToLowerInvariant()
    "$h  $f"
}
$utf8NoBom = New-Object System.Text.UTF8Encoding $False
[System.IO.File]::WriteAllLines("$PWD\SHA256MANIFEST.txt", $lines, $utf8NoBom)
Write-Host "[+] SHA256MANIFEST.txt written (UTF-8 No BOM, relative paths, lowercase hashes)"