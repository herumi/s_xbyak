PYTHON?=python3

SRC=add.cpp mem.cpp
TARGET=$(SRC:.cpp=.exe)

CFLAGS=-DNDEBUG -O2

NASM?=0

test: $(TARGET)
	@sh -ec 'for e in $(TARGET); do echo "run $$e"; ./$$e; done'

%_s.S: %.py
ifeq ($(NASM),1)
	$(PYTHON) $< -m nasm > $@
else
	$(PYTHON) $< -m gas > $@
endif

%_s.o: %_s.S
ifeq ($(NASM),1)
	nasm -f elf64 -o $@ $<
else
	$(CXX) -c $< -o $@
endif

%.exe: %.o %_s.o
	$(CXX) $(LDFLAGS) -o $@ $^

%.o: %.cpp
	$(CXX) $(CFLAGS) -c $< -o $@ -MMD -MP -MF $(@:.o=.d)
DEPEND_FILE=$(addsuffix .d,$(SRC))
-include $(DEPEND_FILE)

clean:
	rm -f *.o *.S *.exe *.d

.PHONY: clean test

# don't remove these files automatically
.SECONDARY: $(SRC:.cpp=.o) $(SRC:.cpp=_s.o) $(SRC:.cpp=_s.S)
