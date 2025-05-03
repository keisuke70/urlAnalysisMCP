param(
    [Parameter(Position=0)]
    [string]$Target = "help",
    [string]$Input = "", # Add parameter for input file
    [string]$Output = "" # Add parameter for output file
)

function Install-Dependencies {
    Write-Host "Installing dependencies from mcp_server/requirements.txt..."
    pip install -r mcp_server/requirements.txt
}

function Update-Dependencies {
    Write-Host "Updating dependencies..."
    pip install --upgrade -r mcp_server/requirements.txt
}

function Invoke-Lint {
    Write-Host "Running linters..."
    python -m flake8 mcp_server company_analyzer.py
    python -m mypy mcp_server company_analyzer.py
}

function Invoke-Tests {
    Write-Host "Running tests..."
    python test_japanese_prompts.py
}

function Invoke-Analyze {
    Write-Host "Running company analysis script..."
    if (-not $Input) {
        Write-Error "Input file path is required. Use -Input <path>"
        return
    }
    $outputArg = if ($Output) { "--output $Output" } else { "" }
    $command = "python company_analyzer.py --input $Input $outputArg"
    Write-Host "Executing: $command"
    Invoke-Expression $command
}

function Invoke-Clean {
    Write-Host "Cleaning up temporary files..."
    Get-ChildItem -Path . -Include "__pycache__", "*.pyc", "*.pyo", "*.pyd", "*.egg-info", "*.egg", ".pytest_cache", ".coverage*", "htmlcov", "coverage.xml", "*.log", "*.csv", ".mypy_cache" -Recurse -Force | Remove-Item -Force -Recurse -ErrorAction SilentlyContinue
    Remove-Item -Path ".coverage*", "htmlcov", ".pytest_cache", ".mypy_cache" -Recurse -Force -ErrorAction SilentlyContinue
}

function Show-Help {
    Write-Host "Available commands:"
    Write-Host "  .\make.ps1 install        - Install dependencies"
    Write-Host "  .\make.ps1 update-deps    - Update dependencies"
    Write-Host "  .\make.ps1 lint           - Run linting tools"
    Write-Host "  .\make.ps1 test           - Run tests"
    Write-Host "  .\make.ps1 analyze        - Run the analysis script"
    Write-Host "      Parameters: -Input <path> [-Output <path>]"
    Write-Host "      Example: .\make.ps1 analyze -Input 'companies.csv' -Output 'results.csv'"
    Write-Host "  .\make.ps1 clean          - Clean up temporary files"
    Write-Host "  .\make.ps1 help           - Show this help message"
}

switch ($Target.ToLower()) {
    "install"     { Install-Dependencies }
    "update-deps" { Update-Dependencies }
    "lint"        { Invoke-Lint }
    "test"        { Invoke-Tests }
    "analyze"     { Invoke-Analyze }
    "clean"       { Invoke-Clean }
    "help"        { Show-Help }
    default       { Show-Help }
}
