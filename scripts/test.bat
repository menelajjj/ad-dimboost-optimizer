cd ../src
python test.py
@ECHO OFF
timeout /t 0 /nobreak
:loop
timeout /t 60 /nobreak > nul
goto loop