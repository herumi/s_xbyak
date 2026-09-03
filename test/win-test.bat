@echo off
for %%i in (gen_fmath string gen_ff_x64 gen_bint_x64 misc) do (
  set FILE=%%i
  call :test1
)
set FILE=gen_ff
call :test_llvm1

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
exit /b

:test_llvm1
echo test %FILE% (llvm)
python3 %FILE%.py -u 64 -type BLS12-381-p -add -sub -mul -mul128 -sqr -mod -mod128 -mulPre -sqrPre -fp2_mul -fp2_sqr > a.txt
diff -w %FILE%_64.txt a.txt
python3 %FILE%.py -u 32 -type BLS12-381-p -add -sub -mul > b.txt
diff -w %FILE%_32.txt b.txt
python3 %FILE%.py -u 64 -proto > c.txt
diff -w %FILE%_proto.txt c.txt
exit /b
