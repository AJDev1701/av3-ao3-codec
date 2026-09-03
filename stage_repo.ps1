# stage_repo.ps1 — AO3 Transport-Core Push Gate
# Spec: 23XXA03 | Pipeline: AO3_1.0_7_STEP_FAIL_CLOSED
# Execute from D:\workspace\av3-ao3-codec\

Set-Location "D:\workspace\av3-ao3-codec"

# Step 2: S4 Parity self-test gate
Write-Host "[STEP 2] Running S4 parity self-test..."
python ao3_codec.py
if ($LASTEXITCODE -ne 0) {
    Write-Error "[-] Parity self-test FAILED. Aborting."
    exit 1
}
Write-Host "[STEP 2] PASS`n"

# Step 3: Clean scan — no secrets in working tree
Write-Host "[STEP 3] Running clean scan..."
$hits = git grep -nEi 'api[_-]?key|secret|password|token|private' -- '*.py' '*.md' '*.ps1' 2>&1
if ($hits) {
    Write-Error "[-] Clean scan FAILED. Potential secret detected:`n$hits"
    exit 1
}
Write-Host "[STEP 3] CLEAN`n"

# Step 4: Generate SHA-256 manifest
Write-Host "[STEP 4] Generating SHA256MANIFEST.txt..."
Get-FileHash -Algorithm SHA256 SPEC.md, ao3_codec.py, stage_repo.ps1 |
    Format-Table -AutoSize |
    Out-File -FilePath SHA256MANIFEST.txt -Encoding ascii
Get-Content SHA256MANIFEST.txt
Write-Host "[STEP 4] MANIFEST LOCKED`n"

# Step 5: Stage, commit, push
Write-Host "[STEP 5] Staging files..."
git add SPEC.md ao3_codec.py stage_repo.ps1 SHA256MANIFEST.txt

Write-Host "[STEP 5] Committing..."
git commit -m "feat(ao3): deploy v1.0 transport core reference codec and specification"
if ($LASTEXITCODE -ne 0) { Write-Error "Commit failed."; exit 1 }

Write-Host "[STEP 5] Pushing to origin main..."
git push origin main
if ($LASTEXITCODE -ne 0) { Write-Error "Push failed."; exit 1 }

# Step 6: Emit commit SHA for mesh dispatch
$sha = git rev-parse HEAD
Write-Host ""
Write-Host "=========================================="
Write-Host "[STEP 6] PUSH COMPLETE"
Write-Host "  Commit SHA : $sha"
Write-Host "  Remote     : AJDev1701/av3-ao3-codec"
Write-Host "  Branch     : main"
Write-Host "  Dispatch to mesh for PPLX verification."
Write-Host "=========================================="
