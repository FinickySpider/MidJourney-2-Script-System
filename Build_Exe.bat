@echo off
setlocal enabledelayedexpansion

:: Set script name
set SCRIPT_NAME=midjourney_automation.py
set ICON=Icon.ico

:: Ask for console or hidden mode
echo Do you want a console or hidden window?
echo [1] Console (default)
echo [2] Hidden (windowed)
set /p WINDOW_CHOICE=Enter your choice (1/2): 

if "%WINDOW_CHOICE%"=="2" (
    set WINDOWED=--windowed
) else (
    set WINDOWED=
)

:: Ask for debug mode
echo Do you want to enable "--log-level=DEBUG"?
echo [1] No (default)
echo [2] Yes
set /p DEBUG_CHOICE=Enter your choice (1/2): 

if "%DEBUG_CHOICE%"=="2" (
    set DEBUG=--log-level=DEBUG
) else (
    set DEBUG=
)

:: Ask for clean build
echo Do you want to use "--clean" to remove old build files?
echo [1] No (default)
echo [2] Yes
set /p CLEAN_CHOICE=Enter your choice (1/2): 

if "%CLEAN_CHOICE%"=="2" (
    set CLEAN=--clean
) else (
    set CLEAN=
)

:: Construct the PyInstaller command
set COMMAND=pyinstaller --onefile %WINDOWED% --icon=%ICON% %DEBUG% %CLEAN% %SCRIPT_NAME%

:: Display final command
echo.
echo Running: %COMMAND%
echo.

:: Run the command
%COMMAND%

echo.
echo Build complete! Check the "dist" folder.
pause
