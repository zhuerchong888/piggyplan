$ErrorActionPreference = "Stop"
$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $projectDir
try {
    $env:PYTHONDONTWRITEBYTECODE = "1"
    python -B -c "import ast; from pathlib import Path; files=list(Path('piggyplan').rglob('*.py'))+list(Path('tools').rglob('*.py'))+list(Path('tests').rglob('*.py'))+list(Path('.').glob('*.py')); [ast.parse(p.read_text(encoding='utf-8-sig'),filename=str(p)) for p in files]; print(f'{len(files)} Python files: syntax ok')"
    if ($LASTEXITCODE -ne 0) { throw "Python syntax check failed." }

    python -B -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw "Regression tests failed." }

    python -B piggyplan_desktop.py --self-test
    if ($LASTEXITCODE -ne 0) { throw "Database self-test failed." }

    python -B piggyplan_desktop.py --gui-smoke
    if ($LASTEXITCODE -ne 0) { throw "Native GUI smoke test failed." }

    $packagedExe = Join-Path $projectDir "dist\PiggyPlan\PiggyPlan.exe"
    if (Test-Path -LiteralPath $packagedExe) {
        foreach ($argument in @("--self-test", "--gui-smoke")) {
            $process = Start-Process -FilePath $packagedExe -ArgumentList $argument -WindowStyle Hidden -Wait -PassThru
            if ($process.ExitCode -ne 0) {
                throw "Packaged executable test failed: $argument"
            }
        }
        Write-Host "Packaged executable verification passed." -ForegroundColor Green
    }

    Write-Host "PiggyPlan verification passed." -ForegroundColor Green
}
finally {
    Pop-Location
}
