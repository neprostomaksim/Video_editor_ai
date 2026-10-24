@echo off
rem Windows: setup.cmd ... = python setup.py ... (Python 3.9+ с python.org)
where py >nul 2>nul && (py -3 "%~dp0setup.py" %* & exit /b)
python "%~dp0setup.py" %*
