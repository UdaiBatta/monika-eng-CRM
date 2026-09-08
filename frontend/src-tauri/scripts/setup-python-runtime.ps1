# Rebuilds frontend/src-tauri/python-runtime/ — a self-contained Python
# distribution bundled into the desktop installer so the app doesn't need
# Postgres, Redis, or a separately-installed Python. Not committed to git
# (see .gitignore); run this once before `tauri build`/`tauri dev` on a
# fresh checkout, or whenever backend/requirements-desktop.txt changes.

$ErrorActionPreference = "Stop"

$PythonVersion = "3.11.9"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RuntimeDir = Join-Path $ScriptDir "..\python-runtime"
$BackendRequirements = Join-Path $ScriptDir "..\..\..\backend\requirements-desktop.txt"

if (Test-Path $RuntimeDir) {
    Remove-Item -Recurse -Force $RuntimeDir
}
New-Item -ItemType Directory -Force $RuntimeDir | Out-Null

$EmbedZip = Join-Path $env:TEMP "python-$PythonVersion-embed-amd64.zip"
Invoke-WebRequest -Uri "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-embed-amd64.zip" -OutFile $EmbedZip
Expand-Archive -Path $EmbedZip -DestinationPath $RuntimeDir -Force

$PthFile = Join-Path $RuntimeDir "python311._pth"
@"
python311.zip
.
Lib\site-packages

import site
"@ | Set-Content -Encoding ascii $PthFile

$GetPip = Join-Path $env:TEMP "get-pip.py"
Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile $GetPip
& "$RuntimeDir\python.exe" $GetPip --no-warn-script-location

& "$RuntimeDir\python.exe" -m pip install --no-warn-script-location -r $BackendRequirements

Write-Host "Python runtime ready at $RuntimeDir"
