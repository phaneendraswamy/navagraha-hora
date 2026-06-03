$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv")) {
    py -3.12 -m venv .venv
}

Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force
& ".\.venv\Scripts\Activate.ps1"

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if (-not (Test-Path ".env")) {
    Copy-Item ".env.sqlite.example" ".env"
}

Write-Host ""
Write-Host "Setup complete. Start the API with:"
Write-Host "python -m uvicorn backend.main:app --reload"
