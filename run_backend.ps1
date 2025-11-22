# Run FastAPI Backend
Write-Host "Starting AskDB FastAPI Backend..." -ForegroundColor Green

# Load environment variables
if (Test-Path .env) {
    Get-Content .env | ForEach-Object {
        if ($_ -match '^([^=]+)=(.*)$') {
            $name = $matches[1]
            $value = $matches[2]
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
    Write-Host "Loaded environment variables from .env" -ForegroundColor Yellow
} else {
    Write-Host "Warning: .env file not found. Using defaults." -ForegroundColor Yellow
}

# Run backend
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
