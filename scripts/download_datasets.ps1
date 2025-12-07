# Architext Dataset Download Script
# Run this in PowerShell to download all datasets

Write-Host "===================================" -ForegroundColor Cyan
Write-Host "Architext Dataset Download Script" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan
Write-Host ""

$projectRoot = "d:\Work\Uni\FYP\architext"
Set-Location $projectRoot

# Create directory structure
Write-Host "[1/5] Creating directory structure..." -ForegroundColor Yellow
$directories = @(
    "datasets\raw",
    "datasets\processed\layouts",
    "datasets\processed\text_pairs",
    "datasets\processed\ifc_metadata",
    "datasets\ifc_models",
    "scripts"
)

foreach ($dir in $directories) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
}
Write-Host "[OK] Directories created" -ForegroundColor Green

# Download HouseExpo
Write-Host "`n[2/5] Downloading HouseExpo dataset..." -ForegroundColor Yellow
Set-Location datasets\raw

if (Test-Path "HouseExpo") {
    Write-Host "HouseExpo already exists, skipping..." -ForegroundColor Gray
} else {
    git clone https://github.com/TeaganLi/HouseExpo.git
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] HouseExpo downloaded" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Failed to download HouseExpo" -ForegroundColor Red
    }
}

Set-Location $projectRoot

# Download IFC sample models
Write-Host "`n[3/5] Downloading IFC sample models..." -ForegroundColor Yellow

$ifcSamples = @(
    "https://raw.githubusercontent.com/IfcOpenShell/IfcOpenShell/v0.7.0/test/input/IfcOpenHouse.ifc",
    "https://raw.githubusercontent.com/IfcOpenShell/IfcOpenShell/v0.7.0/test/input/wall_with_opening.ifc"
)

foreach ($url in $ifcSamples) {
    $filename = Split-Path $url -Leaf
    $output = "datasets\ifc_models\$filename"
    
    if (Test-Path $output) {
        Write-Host "  $filename already exists, skipping..." -ForegroundColor Gray
    } else {
        try {
            Invoke-WebRequest -Uri $url -OutFile $output
            Write-Host "  ✓ Downloaded $filename" -ForegroundColor Green
        } catch {
            Write-Host "  ✗ Failed to download $filename" -ForegroundColor Red
        }
    }
}

# Check if git-lfs is installed for CubiCasa
Write-Host "`n[4/5] Checking for CubiCasa5k prerequisites..." -ForegroundColor Yellow
$gitLfs = Get-Command git-lfs -ErrorAction SilentlyContinue

if ($gitLfs) {
    Write-Host "Git LFS is installed" -ForegroundColor Green
    Write-Host "You can download CubiCasa5k manually from:" -ForegroundColor Cyan
    Write-Host "https://zenodo.org/record/2613548" -ForegroundColor Cyan
} else {
    Write-Host "Git LFS not installed. Install from:" -ForegroundColor Yellow
    Write-Host "https://git-lfs.github.com/" -ForegroundColor Cyan
}

# Install Python dependencies
Write-Host "`n[5/5] Installing Python dependencies..." -ForegroundColor Yellow
$pythonPath = "d:\Work\Uni\FYP\architext\venv\Scripts\python"

if (Test-Path $pythonPath) {
    & $pythonPath -m pip install ifcopenshell lxml beautifulsoup4 --quiet
    Write-Host "✓ Python dependencies installed" -ForegroundColor Green
} else {
    Write-Host "✗ Virtual environment not found" -ForegroundColor Red
    Write-Host "Run: python -m venv venv" -ForegroundColor Yellow
}

# Summary
Write-Host "`n===================================" -ForegroundColor Cyan
Write-Host "Download Summary" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan

$houseExpoCount = (Get-ChildItem -Path "datasets\raw\HouseExpo\json\train" -ErrorAction SilentlyContinue | Measure-Object).Count
$ifcCount = (Get-ChildItem -Path "datasets\ifc_models\*.ifc" -ErrorAction SilentlyContinue | Measure-Object).Count

Write-Host "HouseExpo layouts: $houseExpoCount" -ForegroundColor Green
Write-Host "IFC models: $ifcCount" -ForegroundColor Green

Write-Host "`nNext steps:" -ForegroundColor Yellow
Write-Host "1. Review downloaded datasets" -ForegroundColor White
Write-Host "2. Download CubiCasa5k from: https://zenodo.org/record/2613548" -ForegroundColor White
Write-Host "3. Run processing scripts (we'll create these next)" -ForegroundColor White
Write-Host "4. Generate text descriptions" -ForegroundColor White

Write-Host "`n✓ Setup complete!" -ForegroundColor Green
