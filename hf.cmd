@echo off
rem Windows: hf.cmd ... = python hf.py ... (Python 3.9+ с python.org)
where py >nul 2>nul && (py -3 "%~dp0hf.py" %* & exit /b)
python "%~dp0hf.py" %*
