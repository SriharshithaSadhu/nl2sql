# Start AskDB Application with PostgreSQL
Write-Host "Starting AskDB Application..." -ForegroundColor Green

# Set PostgreSQL Database URL
$env:DATABASE_URL = "postgresql://neondb_owner:npg_xYdFAOhRbu16@ep-dawn-credit-a1yk4hyz-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

# Load .env file if it exists
if (Test-Path .env) {
    Get-Content .env | ForEach-Object {
        if ($_ -match '^([^=]+)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
            Write-Host "Loaded: $name" -ForegroundColor Yellow
        }
    }
}

# Check if DATABASE_URL is set
if ($env:DATABASE_URL) {
    Write-Host "Database URL configured: $($env:DATABASE_URL.Substring(0, [Math]::Min(50, $env:DATABASE_URL.Length)))..." -ForegroundColor Green
} else {
    Write-Host "Warning: DATABASE_URL not set. Using SQLite fallback." -ForegroundColor Yellow
}

# Initialize database
Write-Host "Initializing database..." -ForegroundColor Cyan
python -c "from database import init_db; result = init_db(); print('Database initialized:', result)"

# Run Streamlit
Write-Host "`nStarting Streamlit on http://localhost:8501..." -ForegroundColor Green
Write-Host "Press Ctrl+C to stop the server`n" -ForegroundColor Yellow

streamlit run app.py --server.port 8501

