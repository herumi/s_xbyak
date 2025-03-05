@echo off
for %%i in (gen_fmath string gen_ff_x64 gen_bint_x64 misc) do (
  set FILE=%%i
  call :test1
)

exit /b

:test1
echo test %FILE%
echo gas
python3 %FILE%.py -m gas > a.txt
diff -w %FILE%_gas.txt a.txt
echo nasm
python3 %FILE%.py -win > b.txt
diff -w %FILE%_win.txt b.txt
echo masm
python3 %FILE%.py -win -m masm > c.txt
diff -w %FILE%_masm.txt c.txt
