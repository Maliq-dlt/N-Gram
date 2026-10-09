$videoRoot = $PSScriptRoot
$env:TEMP = Join-Path $videoRoot '.tmp'
$env:TMP = $env:TEMP
$env:UV_CACHE_DIR = Join-Path $videoRoot '.uv-cache'
$env:HF_HOME = Join-Path $videoRoot '.cache\huggingface'
$env:TORCH_HOME = Join-Path $videoRoot '.cache\torch'
$env:YOLO_CONFIG_DIR = Join-Path $videoRoot '.cache\ultralytics'
$env:npm_config_cache = Join-Path $videoRoot '.cache/npm'
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
@($env:TEMP,$env:UV_CACHE_DIR,$env:HF_HOME,$env:TORCH_HOME,$env:YOLO_CONFIG_DIR,$env:npm_config_cache) |
    ForEach-Object { New-Item -ItemType Directory -Path $_ -Force | Out-Null }
