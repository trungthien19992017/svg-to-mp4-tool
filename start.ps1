param([string]$Python = 'python', [switch]$NoBuild)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:DOTNET_CLI_HOME = Join-Path $PSScriptRoot '.dotnet'
$env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
$env:PYTHONUTF8 = '1'
$env:Renderer__Python = (Get-Command $Python -ErrorAction Stop).Source
if (-not (Test-Path -LiteralPath 'engine/.packages/playwright')) { throw 'Run .\setup.ps1 first.' }
if (-not (Test-Path -LiteralPath 'src/SvgToMp4.Web/wwwroot/story/vendor/gsap.min.js')) {
    Write-Warning 'Story preview/render needs GSAP. Run setup.ps1. The legacy whiteboard remains available at /whiteboard.'
}
if (-not $NoBuild) {
    dotnet build 'src/SvgToMp4.Web/SvgToMp4.Web.csproj' --no-restore -m:1 -nodeReuse:false -p:UseSharedCompilation=false --verbosity quiet
    if ($LASTEXITCODE -ne 0) { throw 'Build failed. Run .\setup.ps1 if dependencies are missing.' }
}
Write-Host 'Net Studio: http://127.0.0.1:5188 (Ctrl+C to stop)'
Write-Host 'Story preview origin: http://127.0.0.1:5189 (asset runtime only, no application API)'
dotnet run --no-build --project 'src/SvgToMp4.Web/SvgToMp4.Web.csproj'
if ($LASTEXITCODE -ne 0) { throw 'Application failed to start. Run .\setup.ps1 if no build exists.' }
