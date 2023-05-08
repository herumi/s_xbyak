# s_xbyak

ASM generation tool for GAS/NASM/MASM with Xbyak-like syntax in Python.

# Abstract

This file provides an Xbyak-like DSL to generate ASM code for GAS/NASM/MASM.
i.e., A static version of Xbyak

# Supported Assembler

- gas : GNU Assembler
- nasm : [Netwide Assembler (NASM)](https://www.nasm.us/)
- masm : [Microsoft Macro Assembler](https://learn.microsoft.com/vi-vn/cpp/assembler/masm/microsoft-macro-assembler-reference)

# How to use

There are several samples in the `sample/` directory.

## An add function
[sample/add.py](sample/add.py)
```python
import sys
sys.path.append('../')
from s_xbyak import *

def main():
  parser = getDefaultParser()
  param = parser.parse_args()

  init(param)
  segment('text')

  with FuncProc('add'):
    with StackFrame(2) as sf:
      x = sf.p[0]
      y = sf.p[1]
      lea(rax, ptr(x + y))

  term()

if __name__ == '__main__':
  main()
```

Commentaries:
- `getDefaultParser()` parses some options.
  - `-win` : use Win64 ABI (default : AMD64 ABI)
  - `-m mode` : mode = gas/nasm/masm (default : nasm)
- `param` must have the following keys.
  - `win : bool`
  - `mode : str`

- `segment('text')`
  - Declare that the code starts here.
- `FuncProc('add')`
  - Declare that the function `add` starts here.
- `StackFrame(2)`
  - Declare that the function has two integer-type arguments
  - Remark : The current version supports only integer-(pointer)-type
  - `sf.p[0]` : The register corresponding to the 1st argument.
  - `sf.p[1]` : The register corresponding to the 2nd argument.
- `lea(rax, ptr(x + y))`
  - `s_xbyak` uses `ptr(...)` instead of `ptr[...]`.
- `ret()` is automatically inserted when the `StackFrame` ends.
- `term()`
  - Terminates code generation.

## How to generate an ASM for GAS

```
python3 add.py -m gas > add_s.S
```

```gas
.text
.global PRE(add)
PRE(add):
TYPE(add)
lea (%rdi,%rsi,1), %rax
ret
SIZE(add)
```

- `PRE`, `TYPE`, `SIZE` are macros to absorb OS differences.

## How to generate an ASM for NASM

For Linux/Intel macOS
```
python3 add.py -m nasm
```

```nasm
segment .text
_global add
lea rax, [rdi+rsi]
ret
```

For Windows
```
python3 add.py -m nasm -win
```

```nasm
segment .text
export add
_global add
lea rax, [rcx+rdx]
ret
```

## How to generate an ASM for MASM

```
python3 add.py -m masm
```

```nasm
_text segment
add proc export
lea rax, [rcx+rdx]
ret
add endp
_text ends
end
```

# Author

MITSUNARI Shigeo(herumi@nifty.com)

# Sponsors welcome
[GitHub Sponsor](https://github.com/sponsors/herumi)
