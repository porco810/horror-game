@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "BLENDER=C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
if exist "%BLENDER%" goto :FOUND
for /f "delims=" %%I in ('where blender.exe 2^>nul') do (set "BLENDER=%%I"&goto :FOUND)
echo ERROR: Blender not found. Add it to PATH or edit BLENDER in this file.
pause
exit /b 1
:FOUND
set "MODEL=pursuer_glasses.blend"
if /I "%~1"=="cropped" set "MODEL=pursuer_cropped.blend"
if /I "%~1"=="original" set "MODEL=kuchikagura_game.blend"
if not exist "export\%MODEL%" (echo Run BUILD_AND_PREVIEW.bat first.&pause&exit /b 1)
start "" "%BLENDER%" "%CD%\export\%MODEL%"
