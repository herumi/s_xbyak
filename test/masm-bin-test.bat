@echo off
set NAME=%1%
echo %NAME%

python3 %NAME%.py -m masm > c.txt
ml64 /nologo /c /Foa.obj %NAME%_masm.txt
ml64 /nologo /c /Fob.obj c.txt
objdump -d a.obj > a.txt
objdump -d b.obj > b.txt
diff -w a.txt b.txt