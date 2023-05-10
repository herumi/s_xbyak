@echo off
rem set CFLAGS=/nologo -I ./ /EHsc /link /LARGEADDRESSAWARE:NO
set CFLAGS=/nologo -I ./ /EHsc
rem set CFLAGS=/nologo -I ./ /EHsc
echo gen exec.cpp
python3 exec.py -cpp > exec.cpp
echo nasm test
python3 exec.py -m nasm -win > exec_nasm.asm
nasm -f win64 exec_nasm.asm
cl exec.cpp exec_nasm.obj %CFLAGS%
exec.exe
echo masm test
python3 exec.py -m masm > exec_masm.asm
ml64 /nologo /c exec_masm.asm
cl exec.cpp exec_masm.obj %CFLAGS%
exec.exe
