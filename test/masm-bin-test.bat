@echo off
set F1=%1%
set F2=%2%

echo F1=%F1%
echo F2=%F2%

ml64 /nologo /c /Foa.obj %F1%
ml64 /nologo /c /Fob.obj %F2%
objdump -d a.obj > a.txt
objdump -d b.obj > b.txt
diff -w a.txt b.txt