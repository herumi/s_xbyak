UNAME_S=$(shell uname -s)
ifeq ($(UNAME_S),Darwin)
 NASM_OPT=-f macho64 -DADD_UNDERSCORE
else
 NASM_OPT=-f elf64
endif
PYTHON?=python3
DIFF_OPT=-urN
#DIFF_OPT=-urNw # ignore all blank

%_nasm.o: %_nasm.nasm
	nasm $(NASM_OPT) $<

%_gas.o: %_gas.S
	$(CXX) -c $<


SRC=avx.cpp add.cpp mem.cpp ext.cpp
TARGET=$(SRC:.cpp=.exe)

CFLAGS=-DNDEBUG -O2

NASM?=0

ifeq ($(NASM),1)
  MODE=nasm
  SUF=nasm
else
  MODE=gas
  SUF=S
endif

test: $(TARGET)
	@sh -ec 'for e in $(TARGET); do echo "run $$e"; ./$$e; done'

%_gas.S: %.py
	$(PYTHON) $< -m gas > $@

%_nasm.nasm: %.py
	$(PYTHON) $< -m nasm > $@

%.exe: %.o %_$(MODE).o
	$(CXX) $(LDFLAGS) -o $@ $^

%.o: %.cpp
	$(CXX) $(CFLAGS) -c $< -o $@ -MMD -MP -MF $(@:.o=.d)

DEPEND_FILE=$(addsuffix .d,$(SRC))
-include $(DEPEND_FILE)

clean:
	rm -f *.o *.S *.exe *.d *.nasm

.PHONY: clean test

# don't remove these files automatically
.SECONDARY: $(SRC:.cpp=.o) $(SRC:.cpp=_s.o) $(SRC:.cpp=_$(MODE).$(SUF))
