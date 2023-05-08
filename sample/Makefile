PYTHON?=python3

SRC=add.cpp
TARGET=$(SRC:.cpp=.exe)

test: $(TARGET)
	@sh -ec 'for e in $(TARGET); do echo "run $$e"; ./$$e; done'

%_s.S: %.py
	$(PYTHON) $< -m gas > $@

%_s.o: %_s.S
	$(CXX) -c $< -o $@

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
