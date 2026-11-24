@echo off
rem ======================================================================
rem  run_m1.bat - Milestone M1 in one go (Windows, Anaconda/Miniconda)
rem
rem  Usage, from any folder:
rem     scripts\run_m1.bat            download + check, config is NOT changed
rem     scripts\run_m1.bat accept     same, and if the AGS check matches,
rem                                   write ags_verified: true into the config
rem
rem  Steps:
rem   1. update the conda environment "kwp" (adds pytest; harmless if current)
rem   2. run the tests          -> stop if any test fails
rem   3. setup check, no DB     -> stop if Python/GDAL/PROJ are broken
rem   4. per municipality: dry run (plan + sizes), then the real download
rem  A failed step stops the script; running it again resumes the downloads.
rem ======================================================================
setlocal
cd /d "%~dp0.."

set ACCEPT=
if /i "%~1"=="accept" set ACCEPT=--accept-ags

echo [1/4] Updating conda environment kwp ...
call conda env update -n kwp -f environment.yml --prune || goto :fail
call conda activate kwp || goto :fail

echo [2/4] Running tests ...
python -m pytest -q || goto :fail

echo [3/4] Checking setup (without database) ...
python scripts\00_check_setup.py --gemeinde bubenreuth --skip-db || goto :fail

echo [4/4] Downloading ...
for %%G in (bubenreuth hemhofen) do (
    echo.
    echo ===== %%G : plan =====
    python scripts\01_download.py --gemeinde %%G --dry-run || goto :fail
    echo ===== %%G : download =====
    python scripts\01_download.py --gemeinde %%G %ACCEPT% || goto :fail
)

echo.
echo M1 finished. Log of all files: data\raw\manifest.json
exit /b 0

:fail
echo.
echo *** A step failed (see the message above). Fix it and run this file again. ***
exit /b 1
