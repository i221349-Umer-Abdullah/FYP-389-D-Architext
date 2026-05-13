$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo = Split-Path -Parent $root
$zip = Join-Path $repo "frontend\public\plugins\architext-revit-plugin.zip"
$packageRoot = Join-Path $root "package"

if (Test-Path $packageRoot) {
  Remove-Item -Recurse -Force $packageRoot
}

New-Item -ItemType Directory -Force -Path $packageRoot | Out-Null
Copy-Item -Recurse -Force (Join-Path $root "src") $packageRoot
Copy-Item -Force (Join-Path $root "Architext.Revit.csproj") $packageRoot
Copy-Item -Force (Join-Path $root "README.md") $packageRoot
Copy-Item -Force (Join-Path $root "Architext.Revit.addin") $packageRoot
Copy-Item -Force (Join-Path $root "build.ps1") $packageRoot
Copy-Item -Force (Join-Path $root "install.ps1") $packageRoot

if (Test-Path (Join-Path $root "dist\Architext.Revit.dll")) {
  Copy-Item -Recurse -Force (Join-Path $root "dist") $packageRoot
}

if (Test-Path $zip) {
  Remove-Item -Force $zip
}

Compress-Archive -Path (Join-Path $packageRoot "*") -DestinationPath $zip
Write-Host "Packaged Revit plugin: $zip"
