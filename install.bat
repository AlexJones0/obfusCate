@echo off

:: Determine which python executable path alias to use
WHERE python >nul 2>nul
IF %ERRORLEVEL% == 0 goto :aliaspython

WHERE python3 >nul 2>nul
IF %ERRORLEVEL% == 0 goto :aliaspython3

echo "Sorry, Python could not be found!"
goto :end

:aliaspython
FOR /F "tokens=2" %%g IN ('python -V') do (SET version=%%g)
SET pyexec=python
goto :checkversion

:aliaspython3
FOR /F "tokens=2" %%g IN ('python3 -V') do (SET version=%%g)
SET pyexec=python3

:: Check a valid python version is installed (> 3.10.0)
:checkversion
IF (%version% GEQ "3.10.0") goto :install

echo You are running an invalid python version: Python %version%. Please use version 3.10.0 or greater.
goto :end

:: Upgrade pip and install required packages through PyPi
:install
%pyexec% -m pip install -U -r requirements.txt

:end