@echo off
setlocal enabledelayedexpansion

echo =========================================
echo     System Monitor Client Installer      
echo =========================================

:: Default server address
set DEFAULT_SERVER=ghoest:8000

:: Check for Python 3
echo.
echo Checking for Python 3...
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Python not found. Please install Python 3 to continue.
    exit /b 1
)

:: Verify Python version
for /f "tokens=2" %%I in ('python --version 2^>^&1') do set PYVER=%%I
for /f "tokens=1 delims=." %%I in ("!PYVER!") do set PYMAJOR=%%I
if !PYMAJOR! neq 3 (
    echo Python 3 is required, but found version !PYVER!
    exit /b 1
)

echo Python 3 found!

:: Install required packages
echo.
echo Installing required Python packages...
python -m pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo Failed to install required packages. Please check your internet connection and try again.
    exit /b 1
)
echo Packages installed successfully!

:: Configure server address
echo.
echo Configuring server address...
set /p SERVER_ADDRESS=Enter server address (default: %DEFAULT_SERVER%): 
if "!SERVER_ADDRESS!"=="" set SERVER_ADDRESS=%DEFAULT_SERVER%

echo Updating server address to: !SERVER_ADDRESS!
powershell -Command "(Get-Content system_monitor.py) -replace 'WEBSOCKET_URL = \"ws://.*\"', 'WEBSOCKET_URL = \"ws://!SERVER_ADDRESS!/ws/system/metrics/\"' | Set-Content system_monitor.py"

:: Get the full path to the script
set SCRIPT_PATH=%~dp0system_monitor.py

:: Setup Task Scheduler job
echo.
echo Setting up auto-start using Task Scheduler...
echo.
echo Do you want to create a scheduled task to run at startup? (Y/N)
set /p CREATE_TASK=

if /i "!CREATE_TASK!"=="Y" (
    echo Creating scheduled task...
    
    :: Create XML file for the task
    echo ^<?xml version="1.0" encoding="UTF-16"?^> > task.xml
    echo ^<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task"^> >> task.xml
    echo   ^<RegistrationInfo^> >> task.xml
    echo     ^<Description^>System Monitor Client^</Description^> >> task.xml
    echo   ^</RegistrationInfo^> >> task.xml
    echo   ^<Triggers^> >> task.xml
    echo     ^<LogonTrigger^> >> task.xml
    echo       ^<Enabled^>true^</Enabled^> >> task.xml
    echo     ^</LogonTrigger^> >> task.xml
    echo   ^</Triggers^> >> task.xml
    echo   ^<Principals^> >> task.xml
    echo     ^<Principal id="Author"^> >> task.xml
    echo       ^<LogonType^>InteractiveToken^</LogonType^> >> task.xml
    echo       ^<RunLevel^>LeastPrivilege^</RunLevel^> >> task.xml
    echo     ^</Principal^> >> task.xml
    echo   ^</Principals^> >> task.xml
    echo   ^<Settings^> >> task.xml
    echo     ^<MultipleInstancesPolicy^>IgnoreNew^</MultipleInstancesPolicy^> >> task.xml
    echo     ^<DisallowStartIfOnBatteries^>false^</DisallowStartIfOnBatteries^> >> task.xml
    echo     ^<StopIfGoingOnBatteries^>false^</StopIfGoingOnBatteries^> >> task.xml
    echo     ^<AllowHardTerminate^>true^</AllowHardTerminate^> >> task.xml
    echo     ^<StartWhenAvailable^>false^</StartWhenAvailable^> >> task.xml
    echo     ^<RunOnlyIfNetworkAvailable^>false^</RunOnlyIfNetworkAvailable^> >> task.xml
    echo     ^<IdleSettings^> >> task.xml
    echo       ^<StopOnIdleEnd^>true^</StopOnIdleEnd^> >> task.xml
    echo       ^<RestartOnIdle^>false^</RestartOnIdle^> >> task.xml
    echo     ^</IdleSettings^> >> task.xml
    echo     ^<AllowStartOnDemand^>true^</AllowStartOnDemand^> >> task.xml
    echo     ^<Enabled^>true^</Enabled^> >> task.xml
    echo     ^<Hidden^>false^</Hidden^> >> task.xml
    echo     ^<RunOnlyIfIdle^>false^</RunOnlyIfIdle^> >> task.xml
    echo     ^<WakeToRun^>false^</WakeToRun^> >> task.xml
    echo     ^<ExecutionTimeLimit^>PT0S^</ExecutionTimeLimit^> >> task.xml
    echo     ^<Priority^>7^</Priority^> >> task.xml
    echo   ^</Settings^> >> task.xml
    echo   ^<Actions Context="Author"^> >> task.xml
    echo     ^<Exec^> >> task.xml
    echo       ^<Command^>pythonw.exe^</Command^> >> task.xml
    echo       ^<Arguments^>"!SCRIPT_PATH!"^</Arguments^> >> task.xml
    echo     ^</Exec^> >> task.xml
    echo   ^</Actions^> >> task.xml
    echo ^</Task^> >> task.xml
    
    :: Import the task
    schtasks /create /tn "SystemMonitorClient" /xml task.xml
    
    if %ERRORLEVEL% neq 0 (
        echo Failed to create the scheduled task. You may need administrator privileges.
    ) else (
        echo Scheduled task created successfully!
        del task.xml
    )
) else (
    echo Skipping task creation.
    echo To set up auto-start manually:
    echo 1. Open Task Scheduler
    echo 2. Create a new Basic Task
    echo 3. Set the trigger to 'When I log on'
    echo 4. Select 'Start a program' as the action
    echo 5. Browse to select 'pythonw.exe'
    echo 6. Add the script path as an argument: "!SCRIPT_PATH!"
)

echo.
echo =========================================
echo     Installation Complete!               
echo =========================================
echo.
echo The system monitor client is now ready to use.
echo You can manually start it by running: python "!SCRIPT_PATH!"
echo.

pause
