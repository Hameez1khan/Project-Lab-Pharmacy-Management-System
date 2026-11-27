$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$demoDatabase = Join-Path $root "database\demo_pharmacy.db"

if (-not (Test-Path -LiteralPath $demoDatabase)) {
    throw "The demonstration database is missing. Run scripts\data_tools\generate_demo_database.py first."
}

$env:KHALIS_DAWA_DB_PATH = $demoDatabase
& (Join-Path $root ".venv\Scripts\python.exe") (Join-Path $root "main.py")
