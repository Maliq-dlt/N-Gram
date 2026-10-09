$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'setup_lokal.ps1')
$videoPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $videoPython)) {
    throw 'Environment belum dibuat. Ikuti langkah uv sync di README.md.'
}
Set-Location -LiteralPath $PSScriptRoot
& $videoPython access.py init --username owner --generate
if ($LASTEXITCODE -ne 0) { throw 'Bootstrap akses gagal; periksa audit/database.' }
Write-Host 'Buka http://127.0.0.1:8765 - Ctrl+C untuk menghentikan server.'
& $videoPython -m uvicorn app:app --host 127.0.0.1 --port 8765
if ($LASTEXITCODE -ne 0) { throw "Server berhenti dengan exit code $LASTEXITCODE." }
