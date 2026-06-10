@echo off
setlocal enabledelayedexpansion

REM Disable Ctrl+C prompt
if not defined CTRL_C_HANDLED (
    set "CTRL_C_HANDLED=1"
    cmd /V:ON /C "set "CTRL_C_HANDLED=1" & "%~f0" %*"
    exit /b %errorlevel%
)

echo Starting health check for https://chat-ui-uat.scg-wedo.tech/v1/_debug/healthz
echo Press Ctrl+C twice to stop

REM Define the cookie value
set "COOKIE_VALUE="

:loop
    set /p=^[%time%^] Checking health status... <nul
    for /f "tokens=*" %%a in ('curl -s -o nul -w "%%{http_code}" --connect-timeout 1 --cookie "%COOKIE_VALUE%" https://chat-ui-uat.scg-wedo.tech/v1/_debug/healthz') do (
        echo %%a
        if not "%%a"=="200" (
            echo ERROR: Health check failed with status code %%a. Stopping script.
            exit /b 1
        )
    )

    REM Use ping instead of timeout for cross-platform compatibility
    ping -n 1 -w 500 127.0.0.1 > nul

    goto loop

endlocal
