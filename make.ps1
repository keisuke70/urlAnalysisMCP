param(
    [Parameter(Position=0)]
    [string]$Target = "help"
)

function Update-Dependencies {
    pip install --upgrade -r mcp_server/requirements.txt
}

function Invoke-Lint {
    # Check and install required linting packages if missing
    try {
        python -c "import flake8" 2>$null
    } catch {
        Write-Host "Installing flake8..."
        pip install flake8
    }
    
    try {
        python -c "import mypy" 2>$null
    } catch {
        Write-Host "Installing mypy..."
        pip install mypy
    }

    python -m flake8 mcp_server
    python -m mypy mcp_server
}

function Invoke-Tests {
    python -m pytest mcp_server/tests
}

function Invoke-Run {
    python -m mcp_server.server
}

function Invoke-Clean {
    Get-ChildItem -Path . -Include "__pycache__", "*.pyc", "*.pyo", "*.pyd", "*.egg-info", "*.egg", ".pytest_cache", ".coverage", "htmlcov", "coverage.xml", "*.log" -Recurse | Remove-Item -Force -Recurse
}

function Show-Help {
    Write-Host "Available commands:"
    Write-Host "  .\make.ps1 update-deps  - Update dependencies"
    Write-Host "  .\make.ps1 lint         - Run linting tools"
    Write-Host "  .\make.ps1 test         - Run tests"
    Write-Host "  .\make.ps1 run          - Run the application"
    Write-Host "  .\make.ps1 clean        - Clean up temporary files"
}

switch ($Target) {
    "update-deps" { Update-Dependencies }
    "lint" { Invoke-Lint }
    "test" { Invoke-Tests }
    "run" { Invoke-Run }
    "clean" { Invoke-Clean }
    "help" { Show-Help }
    default { Show-Help }
}
