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
if not exist "web\assets\models\kuchikagura.glb" (echo Run BUILD_AND_PREVIEW.bat first.&pause&exit /b 1)
if not exist "node_modules\three\build\three.module.js" (echo Run npm ci first, or use the complete ZIP.&pause&exit /b 1)
start "KUCHI KAGURA SERVER - close to stop" "%BLENDER%" --background --python-exit-code 1 --python "%CD%\tools\serve_preview.py"
timeout /t 3 /nobreak >nul
start "" "http://127.0.0.1:8765/"
