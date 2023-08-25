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

## Sample of Adding Function
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

  with FuncProc('add2'):
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
- `FuncProc('add2')`
  - Declare that the function `add2` starts here.
- `StackFrame(2)`
  - Declare that the function has two integer-type arguments
  - Remark : The current version supports only integer-(pointer)-type and the max number is four.
  - `sf.p[0]` : The register corresponding to the 1st argument.
  - `sf.p[1]` : The register corresponding to the 2nd argument.
- `lea(rax, ptr(x + y))`
  - `s_xbyak` uses `ptr(...)` instead of `ptr[...]`.
- `ret()` is automatically inserted when the `StackFrame` ends.
- `term()`
  - Terminates code generation.

## How to generate an ASM for GAS

```shell-session
$ python3 add.py -m gas > add_s.S
```

```gas
.text
.global PRE(add2)
PRE(add2):
TYPE(add2)
lea (%rdi,%rsi,1), %rax
ret
SIZE(add2)
```

- `PRE`, `TYPE`, `SIZE` are macros to absorb OS differences.

## How to generate an ASM for NASM

For Linux/Intel macOS
```python
python3 add.py -m nasm
```

```nasm
segment .text
_global add2
lea rax, [rdi+rsi]
ret
```

For Windows
```shell-session
> python3 add.py -m nasm -win
```

```nasm
segment .text
export add2
_global add2
lea rax, [rcx+rdx]
ret
```

## How to generate an ASM for MASM

```shell-shession
$ python3 add.py -m masm
```

```nasm
_text segment
add2 proc export
lea rax, qword ptr [rcx+rdx]
ret
add2 endp
_text ends
end
```
## Sample of Memory Aaccess
[sample/mem.py](sample/mem.py)
```python
def main():
  parser = getDefaultParser()
  param = parser.parse_args()

  init(param)
  segment('data')
  global_('g_x')
  dd_(123)
  segment('text')

  with FuncProc('inc_and_add'):
    with StackFrame(1) as sf:
      inc(dword(rip+'g_x'))
      y = sf.p[0]
      mov(eax, ptr(rip+'g_x'))
      add(rax, y)

  term()
```

Commentaries:
- `segment('data')`
  - Declare that the data starts here.
- `global_('g_x')`
  - The memory named `g_x` can be accessed from the other files.
- `dd_(123)`
  - Put `123` as 32-bit integer.
- `(rip+'g_x')`
  - Use `rip+` to access by relative addressing.
- `inc(dword(...))`
  - Use `qword(64-bit)/dword(32-bit)/word(16-bit)/byte(8-bit)` instead of `ptr` to specify the memory size.

## Sample of AVX
[sample/avx.py](sample/avx.py)
```python
def main():
  parser = getDefaultParser()
  param = parser.parse_args()

  init(param)
  segment('text')

  with FuncProc('add_avx'):
    with StackFrame(4) as sf:
      pz = sf.p[0]
      px = sf.p[1]
      py = sf.p[2]
      n = sf.p[3]
      lpL = Label()

      L(lpL)
      vmovups(xmm0, ptr(px))
      vaddps(xmm0, xmm0, ptr(py))
      vmovups(ptr(pz), xmm0)
      add(px, 16)
      add(py, 16)
      add(pz, 16)
      sub(n, 4)
      jnz(lpL)

  term()
```

This is a tiny sample of a label and AVX. This is not fast code.

Commentaries:
- `lpL = Label()`
  - Define a label instance.
- `L(lpL)`
  - Set lpL here.
- `jnz(lpL)`
  - Jump to lpL if non-zero.

# Mnemonics

Most of the mnemonics are the same as defined in the Intel manual except for `and_`, `or_`, `xor_`, `not_`, `in_`, `out_`, `int_`.

# Label

```python
lpL = Label()
nextL = Label()
L(lpL)  # lpL is set here
ja(nextL)
jmp(lpL)
L(nextL)
```

# db, dw, dd, dq

Use `db_`, `dw_`, `dd_`, `dq_`.

# rip

```python
makeLabel('varX')
dq_(12345)
mov(rax, ptr(rip+'varX'))`
```

# AVX-512

- Merge-masking
  - `vaddps(xmm1 | k1, xmm2, xmm3)`
  - `vmovups(ptr(rax+rcx*4+123)|k1, zmm0)`
- Zero-masking
  - `vsubps(ymm0 | k4 | T_z, ymm1, ymm2)`
- Broadcast
  - `vmulps(zmm0, zmm1, ptr_b(rax))`
  - `ptr_b` is converted to `{1toX}` according to the mnemonics.
- Rounding
  - `vdivps(zmm0, zmm1, zmm2|T_rz_sae)`
- Suppress all exceptions
  - `vmaxss(xmm1, xmm2, xmm3|T_sae)`
- Distinguish `m128` and `m256`
  - `vcvtpd2dq(xmm16, xword (eax+32))` # `m128`
  - `vcvtpd2dq(xmm0, yword (eax+32))`  # `m256`
  - `vcvtpd2dq(xmm21, ptr_b (eax+32))` # `m128` + broadcast
  - `vcvtpd2dq(xmm19, yword_b (eax+32))` # `m256` + broadcast

# License

[modified new BSD License](http://opensource.org/licenses/BSD-3-Clause)

# Author

MITSUNARI Shigeo(herumi@nifty.com)

# Sponsors welcome
[GitHub Sponsor](https://github.com/sponsors/herumi)
