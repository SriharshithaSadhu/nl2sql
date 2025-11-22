# AskDB Setup Verification Script
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  AskDB Setup Verification" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$allGood = $true

# Check 1: Python
Write-Host "✓ Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  Found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Python not found!" -ForegroundColor Red
    $allGood = $false
}

# Check 2: Virtual Environment
Write-Host "`n✓ Checking Virtual Environment..." -ForegroundColor Yellow
if (Test-Path ".venv") {
    Write-Host "  Found: .venv directory" -ForegroundColor Green
} else {
    Write-Host "  ! Virtual environment not found (optional)" -ForegroundColor Yellow
}

# Check 3: .env file
Write-Host "`n✓ Checking Configuration..." -ForegroundColor Yellow
if (Test-Path ".env") {
    Write-Host "  Found: .env file" -ForegroundColor Green
    
    # Check DATABASE_URL
    $envContent = Get-Content .env -Raw
    if ($envContent -match "DATABASE_URL=") {
        Write-Host "  Found: DATABASE_URL configured" -ForegroundColor Green
    } else {
        Write-Host "  ✗ DATABASE_URL not found in .env" -ForegroundColor Red
        $allGood = $false
    }
    
    if ($envContent -match "JWT_SECRET_KEY=") {
        Write-Host "  Found: JWT_SECRET_KEY configured" -ForegroundColor Green
    } else {
        Write-Host "  ! JWT_SECRET_KEY not found (will use default)" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ✗ .env file not found!" -ForegroundColor Red
    Write-Host "    Copy .env.example to .env and configure it" -ForegroundColor Yellow
    $allGood = $false
}

# Check 4: Backend files
Write-Host "`n✓ Checking Backend Files..." -ForegroundColor Yellow
$backendFiles = @("backend/main.py", "backend/auth.py", "backend/models.py", "backend/upload.py", "backend/nl2sql.py", "backend/query_runner.py")
$backendOk = $true
foreach ($file in $backendFiles) {
    if (Test-Path $file) {
        Write-Host "  ✓ $file" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $file missing!" -ForegroundColor Red
        $backendOk = $false
        $allGood = $false
    }
}

# Check 5: Core files
Write-Host "`n✓ Checking Core Files..." -ForegroundColor Yellow
$coreFiles = @("database.py", "core.py", "app.py")
$coreOk = $true
foreach ($file in $coreFiles) {
    if (Test-Path $file) {
        Write-Host "  ✓ $file" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $file missing!" -ForegroundColor Red
        $coreOk = $false
        $allGood = $false
    }
}

# Check 6: Dependencies
Write-Host "`n✓ Checking Dependencies..." -ForegroundColor Yellow
try {
    $packages = @("fastapi", "uvicorn", "streamlit", "sqlalchemy", "pandas", "torch", "transformers")
    foreach ($pkg in $packages) {
        $installed = python -m pip show $pkg 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✓ $pkg installed" -ForegroundColor Green
        } else {
            Write-Host "  ✗ $pkg not installed" -ForegroundColor Red
            $allGood = $false
        }
    }
} catch {
    Write-Host "  ! Could not check packages" -ForegroundColor Yellow
}

# Check 7: PostgreSQL Connection
Write-Host "`n✓ Testing PostgreSQL Connection..." -ForegroundColor Yellow
try {
    # Load .env
    if (Test-Path .env) {
        Get-Content .env | ForEach-Object {
            if ($_ -match '^([^=]+)=(.*)$') {
                $name = $matches[1]
                $value = $matches[2]
                [Environment]::SetEnvironmentVariable($name, $value, "Process")
            }
        }
    }
    
    $dbTest = python -c "from database import init_db; print('SUCCESS' if init_db() else 'FAILED')" 2>&1
    if ($dbTest -match "SUCCESS") {
        Write-Host "  ✓ PostgreSQL connection successful!" -ForegroundColor Green
    } else {
        Write-Host "  ! Could not connect to PostgreSQL" -ForegroundColor Yellow
        Write-Host "    App will use local SQLite fallback" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ! Could not test database connection" -ForegroundColor Yellow
}

# Summary
Write-Host "`n========================================" -ForegroundColor Cyan
if ($allGood) {
    Write-Host "  ✓ All checks passed!" -ForegroundColor Green
    Write-Host "========================================`n" -ForegroundColor Cyan
    Write-Host "You're ready to go! Start with:`n" -ForegroundColor Green
    Write-Host "  streamlit run app.py`n" -ForegroundColor White
} else {
    Write-Host "  ! Some issues found" -ForegroundColor Yellow
    Write-Host "========================================`n" -ForegroundColor Cyan
    Write-Host "Please fix the issues above and try again." -ForegroundColor Yellow
    Write-Host "`nCommon fixes:" -ForegroundColor White
    Write-Host "  1. Install dependencies: pip install -e ." -ForegroundColor White
    Write-Host "  2. Copy .env.example to .env" -ForegroundColor White
    Write-Host "  3. Configure DATABASE_URL in .env`n" -ForegroundColor White
}

Write-Host "Documentation:" -ForegroundColor Cyan
Write-Host "  - QUICKSTART.md      : Get started in 3 steps" -ForegroundColor White
Write-Host "  - README_SETUP.md    : Detailed setup guide" -ForegroundColor White
Write-Host "  - IMPLEMENTATION_SUMMARY.md : What was built`n" -ForegroundColor White
