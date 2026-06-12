@echo off
REM Launch Chrome with CDP enabled on port 9222
REM This lets MAX control Chrome via cdp_action tool
REM Uses a SEPARATE profile so your normal Chrome session is untouched

set CHROME="C:\Program Files\Google\Chrome\Application\chrome.exe"
if not exist %CHROME% set CHROME="C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
if not exist %CHROME% (
    echo Chrome not found. Edit this file with your Chrome path.
    pause
    exit
)

%CHROME% --remote-debugging-port=9222 --user-data-dir="%USERPROFILE%\ChromeCDP" --no-first-run --no-default-browser-check
