$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$dist = Join-Path $root "dist"
$src = Join-Path $root "src"
$revit = "C:\Program Files\Autodesk\Revit 2026"
$csc = "C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
$project = Join-Path $root "Architext.Revit.csproj"

$sdks = (& dotnet --list-sdks 2>$null)
if ($sdks) {
  dotnet build $project -c Release "/p:RevitInstallDir=$revit"
  if ($LASTEXITCODE -ne 0) {
    throw "dotnet build failed with exit code $LASTEXITCODE"
  }
  Write-Host "Built Architext Revit add-in in $dist"
  exit 0
}

if (!(Test-Path $csc)) {
  throw "C# compiler not found at $csc"
}

if (!(Test-Path (Join-Path $revit "RevitAPI.dll"))) {
  throw "Revit 2026 API not found at $revit"
}

Write-Warning "No .NET SDK was found. Revit 2026 requires the .NET 8 SDK to compile this add-in."
Write-Warning "Falling back to the legacy .NET Framework compiler, which only works for older Revit API targets."

New-Item -ItemType Directory -Force -Path $dist | Out-Null

$outDll = Join-Path $dist "Architext.Revit.dll"
$revitApi = Join-Path $revit "RevitAPI.dll"
$revitApiUi = Join-Path $revit "RevitAPIUI.dll"
$revitApiIfc = Join-Path $revit "RevitAPIIFC.dll"
$sources = @(
  (Join-Path $src "App.cs"),
  (Join-Path $src "GenerateCommand.cs"),
  (Join-Path $src "GenerateForm.cs"),
  (Join-Path $src "ArchitextClient.cs"),
  (Join-Path $src "IfcImportHelper.cs"),
  (Join-Path $src "AssemblyInfo.cs")
)

& $csc `
  /target:library `
  "/out:$outDll" `
  "/reference:$revitApi" `
  "/reference:$revitApiUi" `
  "/reference:$revitApiIfc" `
  /reference:System.dll `
  /reference:System.Core.dll `
  /reference:System.Drawing.dll `
  /reference:System.Windows.Forms.dll `
  $sources

if ($LASTEXITCODE -ne 0) {
  throw "C# compilation failed with exit code $LASTEXITCODE"
}

Copy-Item -Force (Join-Path $root "Architext.Revit.addin") (Join-Path $dist "Architext.Revit.addin")
Copy-Item -Force (Join-Path $root "README.md") (Join-Path $dist "README.md")

Write-Host "Built Architext Revit add-in in $dist"
