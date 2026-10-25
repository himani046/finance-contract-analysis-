$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$localVenv = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
$bundledPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if (Test-Path -LiteralPath $localVenv) { $pythonExe = $localVenv }
elseif (Test-Path -LiteralPath $bundledPython) { $pythonExe = $bundledPython }
elseif (Get-Command python -ErrorAction SilentlyContinue) { $pythonExe = (Get-Command python).Source }
else { throw 'Install Python 3.11 or later, then follow README.md.' }
try {
  $health = Invoke-RestMethod 'http://127.0.0.1:8765/api/health' -TimeoutSec 2
  if ($health.ok) { Start-Process 'http://127.0.0.1:8765'; exit }
} catch { }
if (-not (Test-Path -LiteralPath '.env')) {
  Copy-Item -LiteralPath '.env.example' -Destination '.env'
  Write-Host 'Set GEMINI_API_KEY in .env to enable live analysis. Demo mode is ready.'
}
Start-Process -FilePath $pythonExe -ArgumentList 'server.py' -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
for ($attempt = 0; $attempt -lt 15; $attempt++) {
  Start-Sleep -Milliseconds 500
  try {
    $health = Invoke-RestMethod 'http://127.0.0.1:8765/api/health' -TimeoutSec 2
    if ($health.ok) { Start-Process 'http://127.0.0.1:8765'; exit }
  } catch { }
}
throw 'Odin did not start. Run Python server.py in this folder to inspect the error.'
