param(
    [string]$Preset = '',
    [string]$Output = '',
    [string]$Blender = 'C:\Users\Jason\AppData\Local\Programs\Blender\blender-5.2.1-windows-x64\blender.exe',
    [switch]$NoRender
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not $Preset) { $Preset = Join-Path $projectRoot 'presets/human/maxine.json' }
if (-not $Output) { $Output = Join-Path $projectRoot ('outputs/human-runs/' + (Get-Date -Format 'yyyyMMdd-HHmmss')) }
if (-not (Test-Path -LiteralPath $Blender -PathType Leaf)) { throw 'Blender executable missing; pass -Blender with the installed executable path.' }
$versionText = & $Blender --version
if ($LASTEXITCODE -ne 0 -or $versionText[0] -notmatch '^Blender 5\.2\.1') { throw 'This workflow is validated with Blender 5.2.1.' }
$scriptPath = Join-Path $projectRoot 'scripts/build_surface_human.py'
$buildArgs = @('--background','--factory-startup','--python-exit-code','1','--python',$scriptPath,'--','--preset',$Preset,'--output',$Output)
if ($NoRender) { $buildArgs += '--no-render' }
& $Blender @buildArgs
if ($LASTEXITCODE -ne 0) { throw 'Generation failed. Inspect the error; do not bypass validation.' }
& $Blender --background (Join-Path $Output 'character.blend') --python-exit-code 1 --python (Join-Path $Output 'source_snapshot/scripts/verify_surface_human.py')
if ($LASTEXITCODE -ne 0) { throw 'Saved-file verification failed.' }
Write-Output ('Verified character package: ' + $Output)
