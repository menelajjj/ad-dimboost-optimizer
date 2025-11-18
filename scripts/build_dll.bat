g++ -shared -fPIC -o ../src/cpp_lib.dll ../src/cpp_lib.cpp -O3 -fopenmp -static -static-libgcc -static-libstdc++ -lm
@ECHO OFF
timeout /t 0 /nobreak
:loop
timeout /t 60 /nobreak > nul
goto loop