$ErrorActionPreference = "Stop"

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Virtual environment not found. Create .venv and install requirements-dev.txt first."
}

Push-Location $projectRoot
try {
    & $python -m PyInstaller --noconfirm --clean KhalisDawa.spec
    if ($LASTEXITCODE -ne 0) {
        throw "The Windows build failed."
    }

    $executable = Join-Path $projectRoot "dist\KhalisDawa\KhalisDawa.exe"
    if (-not (Test-Path -LiteralPath $executable)) {
        throw "Build completed without producing KhalisDawa.exe."
    }

    Write-Host "Build created: $executable"
}
finally {
    Pop-Location
}
