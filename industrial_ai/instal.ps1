param([switch]$SkipModels)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'setup_lokal.ps1')
Set-Location -LiteralPath $PSScriptRoot
foreach ($videoTool in @('uv', 'ffmpeg', 'ffprobe')) {
    if (-not (Get-Command $videoTool -ErrorAction SilentlyContinue)) {
        throw "$videoTool belum tersedia pada PATH. Ikuti prasyarat di README.md."
    }
}
# Keep managed Python downloads inside the workspace too.
$env:UV_PYTHON_INSTALL_DIR = Join-Path $PSScriptRoot '.cache/python'
& uv sync --frozen --python 3.11
if ($LASTEXITCODE -ne 0) { throw 'Instalasi library Python gagal.' }
if (-not $SkipModels) {
    & uv run --frozen python setup_models.py
    if ($LASTEXITCODE -ne 0) { throw 'Pengunduhan/verifikasi model gagal. Periksa koneksi lalu jalankan setup lagi.' }
}
Write-Host 'Setup selesai. Jalankan npm start untuk membuka server lokal.'
Write-Host 'Fine-tuning chat terpisah dan opsional; lihat README.md.'
