@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "BLENDER=C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
if exist "%BLENDER%" goto :FOUND
for /f "delims=" %%I in ('where blender.exe 2^>nul') do (set "BLENDER=%%I"&goto :FOUND)
echo ERROR: Blender not found. Edit BLENDER in this file or add Blender to PATH.
pause
exit /b 1
:FOUND
if exist "node_modules\three\build\three.module.js" goto :BUILD
where npm.cmd >nul 2>&1
if errorlevel 1 (echo ERROR: Install Node.js LTS and run npm ci, or use the complete ZIP with bundled Three.js.&pause&exit /b 1)
call npm ci --ignore-scripts --no-audit --no-fund
if errorlevel 1 (echo ERROR: Dependency installation failed.&pause&exit /b 1)
:BUILD
"%BLENDER%" --background --factory-startup --threads 4 --python-exit-code 1 --python "%CD%\blender\generate_kuchikagura.py" > "%CD%\build_log.txt" 2>&1
set "RC=%ERRORLEVEL%"
type "%CD%\build_log.txt"
if not "%RC%"=="0" (echo ERROR: See build_log.txt and build_python_error.txt.&pause&exit /b %RC%)
if not exist "%CD%\web\assets\models\kuchikagura.glb" (echo ERROR: GLB missing.&pause&exit /b 1)
"%BLENDER%" --background --factory-startup --threads 4 --python-exit-code 1 --python "%CD%\blender\generate_reference_pursuers.py" > "%CD%\reference_build_log.txt" 2>&1
set "RC=%ERRORLEVEL%"
type "%CD%\reference_build_log.txt"
if not "%RC%"=="0" (echo ERROR: See reference_build_log.txt and reference_build_python_error.txt.&pause&exit /b %RC%)
if not exist "%CD%\web\assets\models\pursuer_glasses.glb" (echo ERROR: Glasses pursuer GLB missing.&pause&exit /b 1)
if not exist "%CD%\web\assets\models\pursuer_cropped.glb" (echo ERROR: Cropped-hair pursuer GLB missing.&pause&exit /b 1)
call PREVIEW_ONLY.bat
