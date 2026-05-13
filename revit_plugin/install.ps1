$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$dist = Join-Path $root "dist"
$dll = Join-Path $dist "Architext.Revit.dll"

if (!(Test-Path $dll)) {
  throw "Build output not found. Run .\build.ps1 first."
}

$addinRoot = Join-Path $env:APPDATA "Autodesk\Revit\Addins\2026"
$targetDir = Join-Path $addinRoot "Architext"
$targetDll = Join-Path $targetDir "Architext.Revit.dll"
$targetAddin = Join-Path $addinRoot "Architext.Revit.addin"

New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
Copy-Item -Force $dll $targetDll

$addinXml = @"
<?xml version="1.0" encoding="utf-8"?>
<RevitAddIns>
  <AddIn Type="Application">
    <Name>Architext Revit Plugin</Name>
    <Assembly>$targetDll</Assembly>
    <AddInId>8B22B2EC-AD09-45B5-A771-A3FD407E854A</AddInId>
    <FullClassName>Architext.Revit.App</FullClassName>
    <VendorId>ARCH</VendorId>
    <VendorDescription>Architext</VendorDescription>
  </AddIn>
</RevitAddIns>
"@

$addinXml | Set-Content -Encoding UTF8 $targetAddin

Write-Host "Installed Architext Revit add-in:"
Write-Host "  $targetDll"
Write-Host "  $targetAddin"
Write-Host "Restart Revit to load the add-in."

