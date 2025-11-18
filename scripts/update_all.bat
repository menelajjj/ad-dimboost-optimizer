cd ../src
python update_all.py
@ECHO OFF
timeout /t 0 /nobreak
:loop
timeout /t 60 /nobreak > nul
goto loop