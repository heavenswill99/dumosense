@echo off
setlocal
set PYTHONUTF8=1
set PYTHONDONTWRITEBYTECODE=1
set OPENBLAS_NUM_THREADS=1
set OMP_NUM_THREADS=1
python "%~dp0src\engine_v3.py" %*
exit /b %errorlevel%
