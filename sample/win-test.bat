@echo off
for %%i in (add mem avx ext) do (
    set NAME=%%i
    call :run
)


exit /b

:run
echo %NAME%
echo masm
python3 %NAME%.py -m masm > %NAME%_masm.asm
ml64 /nologo /c %NAME%_masm.asm
cl /nologo /EHsc /Zi %NAME%.cpp %NAME%_masm.obj
%NAME%.exe
echo nasm
python3 %NAME%.py -m nasm -win > %NAME%_nasm.asm
nasm -f win64 %NAME%_nasm.asm
cl /nologo /EHsc /Zi %NAME%.cpp %NAME%_nasm.obj
%NAME%.exe
