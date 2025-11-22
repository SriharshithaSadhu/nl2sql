# Run Streamlit Frontend
Write-Host "Starting AskDB Streamlit Frontend..." -ForegroundColor Green

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

# Run Streamlit
streamlit run app.py
