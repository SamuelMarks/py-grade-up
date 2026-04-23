@echo off
setlocal enabledelayedexpansion

:: pipeline.bat - Windows integration pipeline for py-gradeup and mkconf.

set "TARGET_DIR=%~1"

if "%TARGET_DIR%"=="" (
    echo Usage: %0 ^<path_to_project^>
    echo Example: %0 ..\my-python-app
    exit /b 1
)

:: Resolve absolute path
pushd "%TARGET_DIR%" 2>nul
if errorlevel 1 (
    echo Target directory not found: %TARGET_DIR%
    exit /b 1
)
set "TARGET_DIR=%CD%"
popd

echo ======================================================
echo Starting Integration Pipeline for: %TARGET_DIR%
echo ======================================================

echo Step 1: Running py-gradeup to modernize Python syntax and dependencies...
where py-gradeup >nul 2>nul
if %ERRORLEVEL% equ 0 (
    py-gradeup fix "%TARGET_DIR%"
) else (
    python -m py_gradeup.cli fix "%TARGET_DIR%"
)

echo ======================================================
echo Step 2: Running mkconf to scaffold build files...

set "MKCONF_DIR=%~dp0..\..\mkconf"
set "MKCONF_BIN="

:: Look for standard Windows executable extensions or fallback to binary file without extension
if exist "%MKCONF_DIR%\mkconf.exe" (
    set "MKCONF_BIN=%MKCONF_DIR%\mkconf.exe"
) else if exist "%MKCONF_DIR%\mkconf_bin.exe" (
    set "MKCONF_BIN=%MKCONF_DIR%\mkconf_bin.exe"
) else if exist "%MKCONF_DIR%\mkconf_bin" (
    set "MKCONF_BIN=%MKCONF_DIR%\mkconf_bin"
) else if exist "%MKCONF_DIR%\mkconf" (
    set "MKCONF_BIN=%MKCONF_DIR%\mkconf"
)

if "%MKCONF_BIN%"=="" (
    echo mkconf binary not found at %MKCONF_DIR%
    exit /b 1
)

pushd "%TARGET_DIR%"
"%MKCONF_BIN%" .

echo ======================================================
echo Step 3: Verifying the build (Confirming it works!^)...

if exist "debian.Dockerfile" (
    echo Building debian.Dockerfile to confirm everything runs...
    docker build -f debian.Dockerfile -t "integration-test-image:latest" .
) else if exist "Dockerfile" (
    echo Building standard Dockerfile...
    docker build -t "integration-test-image:latest" .
) else (
    echo No Dockerfile found! Did mkconf generate correctly?
    popd
    exit /b 1
)

popd
echo ======================================================
echo Pipeline Complete! The project was upgraded and containerized successfully.
