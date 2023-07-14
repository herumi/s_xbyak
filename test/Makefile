UNAME_S=$(shell uname -s)
ifeq ($(UNAME_S),Darwin)
 NASM_OPT=-f macho64
else
 NASM_OPT=-f elf64
endif
PYTHON?=python3
DIFF_OPT=-urN
#DIFF_OPT=-urNw # ignore all blank

test:
	make test1 FILE=gen_ff_x64
	make test1 FILE=gen_bint_x64
	make test1 FILE=gen_fmath
	make test1 FILE=string
	make test1 FILE=misc
#	$(PYTHON) misc.py

update:
	$(MAKE) test UPDATE=1

test_misc:
	$(PYTHON) misc.py

test1_gas:
	$(PYTHON) $(FILE).py -m gas > a.txt
	diff $(DIFF_OPT) $(FILE)_gas.txt a.txt

test1_win:
	$(PYTHON) $(FILE).py -win > b.txt
	diff $(DIFF_OPT) $(FILE)_win.txt b.txt

test1_masm:
	$(PYTHON) $(FILE).py -m masm > c.txt
	diff $(DIFF_OPT) $(FILE)_masm.txt c.txt

update1:
ifeq ($(UPDATE),1)
	$(PYTHON) $(FILE).py -m gas > $(FILE)_gas.txt
	$(PYTHON) $(FILE).py -win > $(FILE)_win.txt
	$(PYTHON) $(FILE).py -m masm > $(FILE)_masm.txt
endif

test1:
	$(MAKE) update1
	$(MAKE) test1_gas
	$(MAKE) test1_win
	$(MAKE) test1_masm

test_string_run:
	make clean
	make mie_string_test
	make clean
	make mie_string_test MODE=gas

run_nasm:
	@$(PYTHON) misc.py -run -m nasm
run_gas:
	@$(PYTHON) misc.py -run -m gas
run_masm:
	@$(PYTHON) misc.py -run -m masm

exec_gas.S: exec.py
	$(PYTHON) exec.py -m gas > exec_gas.S

exec_nasm.nasm: exec.py
	$(PYTHON) exec.py -m nasm > exec_nasm.nasm

exec_gas.exe: exec.o exec_gas.o
	$(CXX) -o $@ $^

exec_nasm.exe: exec.o exec_nasm.o
	$(CXX) -o $@ $^

exec_test: exec_gas.exe exec_nasm.exe
	./exec_nasm.exe
	./exec_gas.exe

exec.cpp: exec.py
	$(PYTHON) exec.py -cpp > exec.cpp

SRC=mie_string_test.cpp

MIE_STRING_DIR?=../../mie_string/
CYBOZULIB_DIR?=../../cybozulib/
CFLAGS=-g -O2 -DNDEBUG -mavx2 -I $(MIE_STRING_DIR) -I $(CYBOZULIB_DIR)/include

VPATH=$(MIE_STRING_DIR)

%.o: %.nasm
	nasm $(NASM_OPT) $<

%.o: %.S
	$(CXX) -c $<

%.o: %.cpp
	$(PRE)$(CXX) $(CFLAGS) -c $< -o $@ -MMD -MP -MF $(@:.o=.d)
DEPEND_FILE=$(addsuffix .d,$(SRC))
-include $(DEPEND_FILE)

MODE?=nasm
mie_string_test.exe: string.py mie_string_test.o
ifeq ($(MODE),nasm)
	$(PYTHON) string.py -m nasm > string.asm
	nasm $(NASM_OPT) string.asm
endif
ifeq ($(MODE),gas)
	$(PYTHON) string.py -m gas > string.S
	$(CXX) -c string.S
endif
	$(CXX) -o $@ mie_string_test.o string.o $(CFLAGS)

mie_string_test: ./mie_string_test.exe
	echo $(MODE)
	./mie_string_test.exe

clean:
	rm -f a.txt b.txt c.txt *.o *.S *.exe *.d *.nasm

.PHONY: clean test

# don't remove these files automatically
.SECONDARY: $(addprefix $(OBJ_DIR)/, $(ALL_SRC:.cpp=.o))
