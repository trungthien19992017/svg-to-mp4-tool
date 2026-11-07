$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
$env:DOTNET_CLI_HOME = Join-Path (Get-Location) '.dotnet'
$env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
$env:PYTHONUTF8 = '1'
dotnet build 'src/SvgToMp4.Web/SvgToMp4.Web.csproj' --no-restore -m:1 -nodeReuse:false -p:UseSharedCompilation=false --verbosity quiet
if ($LASTEXITCODE -ne 0) { throw 'App build failed.' }
dotnet run --project 'tests/StoryChecks/StoryChecks.csproj' -- (Get-Location).Path
if ($LASTEXITCODE -ne 0) { throw 'Story core checks failed.' }
node 'tests/story-timeline.mjs'
if ($LASTEXITCODE -ne 0) { throw 'Timeline checks failed.' }
python 'tests/test_story_audio.py'
if ($LASTEXITCODE -ne 0) { throw 'Audio checks failed.' }
Write-Host 'Core checks passed. Keep start.ps1 running in a separate window, then run python tests/test_story_e2e.py.'
