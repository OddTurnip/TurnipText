@echo off
REM Launch TurnipText with the test tabs file
REM Uses %~dp0 to get the directory containing this batch file
python "%~dp0..\..\app.py" "%~dp0test-doc.tabs"
