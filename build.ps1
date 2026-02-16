# JFlex Scanner Build Script
# This script automates the build process for the JFlex Scanner implementation

param(
    [ValidateSet("build", "clean", "test", "clean-test")]
    [string]$Action = "build"
)

$ErrorActionPreference = "Stop"

# Configuration
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$SrcDir = Join-Path $ProjectRoot "src"
$JFlexFile = Join-Path $SrcDir "Scanner.jflex"
$GeneratedScanner = Join-Path $SrcDir "Scanner.java"
$OutputDir = Join-Path $ProjectRoot "bin"
$TestsDir = Join-Path $ProjectRoot "tests"
$JFlexExe = "C:\JFLEX\bin\jflex.bat"

Write-Host "JFlex Scanner Build Script"
Write-Host "===========================" -ForegroundColor Cyan
Write-Host "Action: $Action"
Write-Host "Project Root: $ProjectRoot"
Write-Host ""

function Test-JFlexInstalled {
    if (-not (Test-Path $JFlexExe)) {
        Write-Host "ERROR: JFlex not found at $JFlexExe" -ForegroundColor Red
        exit 1
    }
    return $true
}

function Build {
    Write-Host "Building JFlex Scanner..." -ForegroundColor Cyan
    
    # Test JFlex installation
    if (-not (Test-JFlexInstalled)) {
        exit 1
    }
    
    # Generate Scanner.java from Scanner.jflex
    Write-Host "Running JFlex on $JFlexFile..." -ForegroundColor Yellow
    Push-Location $SrcDir
    try {
        & $JFlexExe Scanner.jflex
        if ($LASTEXITCODE -ne 0) {
            Write-Host "ERROR: JFlex compilation failed" -ForegroundColor Red
            exit 1
        }
    }
    finally {
        Pop-Location
    }
    
    if (-not (Test-Path $GeneratedScanner)) {
        Write-Host "ERROR: Scanner.java was not generated" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "✓ Scanner.java generated successfully" -ForegroundColor Green
    
    # Create output directory
    if (-not (Test-Path $OutputDir)) {
        New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
    }
    
    # Compile Java files
    Write-Host "Compiling Java files..." -ForegroundColor Yellow
    $JavaFiles = @(
        "Token.java",
        "TokenType.java",
        "SymbolTable.java",
        "ErrorHandler.java",
        "ManualScanner.java",
        "Scanner.java",
        "JFlexScannerTest.java"
    )
    
    $ClassPath = $SrcDir
    $CompileFiles = @()
    foreach ($file in $JavaFiles) {
        $FilePath = Join-Path $SrcDir $file
        if (Test-Path $FilePath) {
            $CompileFiles += $FilePath
        }
        else {
            Write-Host "Warning: $file not found" -ForegroundColor Yellow
        }
    }
    
    if ($CompileFiles.Count -eq 0) {
        Write-Host "ERROR: No Java files found to compile" -ForegroundColor Red
        exit 1
    }
    
    javac -cp $ClassPath -d $OutputDir $CompileFiles
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Java compilation failed" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "✓ Java compilation successful" -ForegroundColor Green
    Write-Host ""
    Write-Host "Build completed successfully!" -ForegroundColor Green
    Write-Host "Compiled classes are in: $OutputDir"
    Write-Host ""
    Write-Host "To run the scanner tests, use:" -ForegroundColor Cyan
    Write-Host "  cd bin"
    Write-Host "  java -cp . JFlexScannerTest"
}

function Clean {
    Write-Host "Cleaning build artifacts..." -ForegroundColor Cyan
    
    # Remove generated Scanner.java
    if (Test-Path $GeneratedScanner) {
        Remove-Item $GeneratedScanner -Force
        Write-Host "✓ Removed generated Scanner.java"
    }
    
    # Remove compiled classes
    if (Test-Path $OutputDir) {
        Remove-Item $OutputDir -Recurse -Force
        Write-Host "✓ Removed output directory"
    }
    
    # Remove __pycache__ from nfa_output
    $PyCache = Join-Path $ProjectRoot "nfa_output" "__pycache__"
    if (Test-Path $PyCache) {
        Remove-Item $PyCache -Recurse -Force -ErrorAction SilentlyContinue
    }
    
    Write-Host "Clean completed!" -ForegroundColor Green
}

function Test {
    Write-Host "Running tests..." -ForegroundColor Cyan
    
    if (-not (Test-Path (Join-Path $OutputDir "JFlexScannerTest.class"))) {
        Write-Host "ERROR: Tests not compiled. Please build first." -ForegroundColor Red
        exit 1
    }
    
    Push-Location $OutputDir
    try {
        java -cp . JFlexScannerTest
    }
    finally {
        Pop-Location
    }
}

function CleanAndTest {
    Clean
    Build
    Test
}

# Execute the requested action
switch ($Action) {
    "build" { Build }
    "clean" { Clean }
    "test" { Test }
    "clean-test" { CleanAndTest }
    default { 
        Write-Host "Unknown action: $Action" -ForegroundColor Red
        exit 1
    }
}
