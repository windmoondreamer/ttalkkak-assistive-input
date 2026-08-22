$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$venvPath = Join-Path $repoRoot ".venv-build123d"
$venvPython = Join-Path $venvPath "Scripts\python.exe"
$requirements = Join-Path $repoRoot "requirements-build123d.txt"
$codexPython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if (-not (Test-Path -LiteralPath $venvPython)) {
    if ($env:ONEGRIP_PYTHON -and (Test-Path -LiteralPath $env:ONEGRIP_PYTHON)) {
        & $env:ONEGRIP_PYTHON -m venv $venvPath
    } elseif (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3.12 -m venv $venvPath
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        & python -m venv $venvPath
    } elseif (Test-Path -LiteralPath $codexPython) {
        & $codexPython -m venv $venvPath
    } else {
        throw "Python 3.12 was not found. Install Python or set ONEGRIP_PYTHON to python.exe."
    }
}

$env:XDG_CACHE_HOME = Join-Path $venvPath "cache"
& $venvPython -c "import sys; assert sys.version_info >= (3, 10) and sys.version_info < (3, 15)"
if ($LASTEXITCODE -ne 0) {
    throw "The existing .venv-build123d is not runnable. Remove only that directory and rerun setup."
}
& $venvPython -m pip install -r $requirements
if ($LASTEXITCODE -ne 0) {
    throw "build123d dependency installation failed."
}
& $venvPython -m build123d_workbench.smoke_test
if ($LASTEXITCODE -ne 0) {
    throw "build123d geometry smoke test failed."
}
