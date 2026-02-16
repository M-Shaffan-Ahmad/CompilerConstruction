@echo off
REM JFlex Build Script for Windows
REM This script builds the Scanner.jflex specification

setlocal enabledelayedexpansion

set JFLEX_PATH=C:\JFLEX\bin\jflex.bat

echo Checking for JFlex at %JFLEX_PATH%...
if not exist "%JFLEX_PATH%" (
    echo ERROR: JFlex not found at %JFLEX_PATH%
    echo.
    echo Please ensure JFlex is installed at C:\JFLEX
    echo Or modify JFLEX_PATH in this script if installed elsewhere
    goto :eof
)

cd /d "%~dp0src"
echo Building Scanner.jflex...

REM Run JFlex to generate Scanner.java
call "%JFLEX_PATH%" Scanner.jflex

if %errorlevel% equ 0 (
    echo.
    echo JFlex compilation successful!
    echo Scanner.java has been generated.
    echo.
    echo Next step: Compile Scanner.java with javac
    echo javac -cp . *.java
) else (
    echo.
    echo Error: JFlex compilation failed.
    echo Please check the error messages above.
)

pause
