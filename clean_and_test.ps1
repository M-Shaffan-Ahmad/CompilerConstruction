# Clean and Re-run Scanner Tests
# Usage: .\clean_and_test.ps1

Write-Host "================================" -ForegroundColor Cyan
Write-Host "Cleaning compiled files..." -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

cd src
Remove-Item *.class -Force -ErrorAction SilentlyContinue
Write-Host "✓ Cleaned .class files" -ForegroundColor Green

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Recompiling sources..." -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

javac -cp . *.java
if ($?) {
    Write-Host "✓ Compilation successful" -ForegroundColor Green
} else {
    Write-Host "✗ Compilation failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Running tests..." -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

cd ..
java -cp ./src JFlexScannerTest

Write-Host ""
Write-Host "✓ Done!" -ForegroundColor Green
