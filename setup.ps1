param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:DOTNET_CLI_HOME = Join-Path $PSScriptRoot '.dotnet'
$env:DOTNET_SKIP_FIRST_TIME_EXPERIENCE = '1'
$env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
$env:PYTHONUTF8 = '1'
foreach ($tool in @('dotnet','ffmpeg','ffprobe','node','npm')) {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) { throw "Missing $tool in PATH. See README.md." }
}
npm install --ignore-scripts --no-audit --no-fund
if ($LASTEXITCODE -ne 0) { throw 'GSAP dependency installation failed.' }
npm run vendor
if ($LASTEXITCODE -ne 0) { throw 'Could not prepare the local GSAP runtime.' }
& $Python -m pip install --target 'engine/.packages' --upgrade -r 'engine/requirements.lock.txt'
if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }
dotnet restore 'src/SvgToMp4.Web/SvgToMp4.Web.csproj'
if ($LASTEXITCODE -ne 0) { throw '.NET dependency restore failed.' }
dotnet build 'src/SvgToMp4.Web/SvgToMp4.Web.csproj' --no-restore -m:1 -nodeReuse:false -p:UseSharedCompilation=false --verbosity quiet
if ($LASTEXITCODE -ne 0) { throw 'Build failed.' }
Write-Host 'Ready. Run .\start.ps1 and open http://127.0.0.1:5188'
