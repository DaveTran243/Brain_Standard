@echo off
rem brain · Brain_Standard CLI on Windows. Needs Python 3.11 or later.
set "PYTHONPATH=%~dp0..\tools;%PYTHONPATH%"
python -m brain %*
