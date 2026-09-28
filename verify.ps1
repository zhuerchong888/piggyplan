$ErrorActionPreference = "Stop"
$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $projectDir
try {
    python -m py_compile piggyplan_desktop.py
    if ($LASTEXITCODE -ne 0) { throw "Python syntax check failed." }

    python piggyplan_desktop.py --self-test
    if ($LASTEXITCODE -ne 0) { throw "Database self-test failed." }

    python piggyplan_desktop.py --gui-smoke
    if ($LASTEXITCODE -ne 0) { throw "Native GUI smoke test failed." }

    $packagedExe = Join-Path $projectDir "dist\PiggyPlan\PiggyPlan.exe"
    if (Test-Path -LiteralPath $packagedExe) {
        foreach ($argument in @("--self-test", "--gui-smoke")) {
            $process = Start-Process -FilePath $packagedExe -ArgumentList $argument -Wait -PassThru
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
