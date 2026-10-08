$taskRoot = $PSScriptRoot
$env:TEMP = Join-Path $taskRoot '.tmp'
$env:TMP = $env:TEMP
$env:UV_CACHE_DIR = Join-Path $taskRoot '.uv-cache'
$env:UV_PYTHON_INSTALL_DIR = Join-Path $taskRoot '.cache\python'
$env:MPLCONFIGDIR = Join-Path $taskRoot '.cache\matplotlib'
$env:JUPYTER_RUNTIME_DIR = Join-Path $taskRoot '.cache\jupyter\runtime'
$env:JUPYTER_CONFIG_DIR = Join-Path $taskRoot '.cache\jupyter\config'
$env:IPYTHONDIR = Join-Path $taskRoot '.cache\ipython'
$env:NLTK_DATA = Join-Path $taskRoot 'data\nltk_data'
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

@($env:TEMP, $env:UV_CACHE_DIR, $env:UV_PYTHON_INSTALL_DIR, $env:MPLCONFIGDIR,
  $env:JUPYTER_RUNTIME_DIR, $env:JUPYTER_CONFIG_DIR, $env:IPYTHONDIR, $env:NLTK_DATA) |
    ForEach-Object { New-Item -ItemType Directory -Path $_ -Force | Out-Null }
